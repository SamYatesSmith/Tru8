"""Offline evaluation of the relationship review on stored public records (A− M1).

Design: audit/2026-09-24_a_minus_mapping_{design,review}.md §4.

Replays `review_relationship_scope` over the directional refs of stored public
payloads, exactly as the pipeline would call it (the payload's claim map,
title, snippet and retained passages), and scores its demotions against a
three-way labelled set (must_survive / should_demote / either).

One run records every pair's model decision, so BOTH policies are scored from
the same draws:
  * demote_unknown   — `mismatch` and `unknown` both demote (as built)
  * mismatch_only    — only `mismatch` demotes; `unknown` is recorded

Costs model calls (GOOGLE_LLM_MODEL). Use --dry-run to validate the
conversion and the scoring without any call.

Usage:
  python scripts/eval_relationship_review.py --payloads <dir> \
      --labels ../audit/a_minus/review_eval/labels.csv --repeats 3 \
      --out ../audit/a_minus/review_eval/results.json [--dry-run]
"""

from __future__ import annotations

import argparse
import asyncio
import copy
import csv
import glob
import json
import os
import sys
import time
from collections import Counter, defaultdict
from typing import Any, Dict, List, Tuple
from unittest.mock import AsyncMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings  # noqa: E402


def _to_internal(
    payload: Dict[str, Any]
) -> List[Tuple[Dict[str, Any], List[Dict[str, Any]]]]:
    """(claim_map, evidence) per claim, in the pipeline's snake_case shape."""
    out = []
    for claim in payload.get("claims") or []:
        cm_src = claim.get("claimMap") or {}
        elements = []
        for el in cm_src.get("elements") or []:
            elements.append(
                {
                    "element_id": el["elementId"],
                    "description": el["description"],
                    "state": el.get("state"),
                    "uncertainty": el.get("uncertainty"),
                    "basis": copy.deepcopy(el.get("basis") or {}),
                    "evidence_refs": [
                        {
                            "evidence_id": r["evidenceId"],
                            "relationship": r["relationship"],
                            "reasoning": r.get("reasoning"),
                        }
                        for r in el.get("evidenceRefs") or []
                    ],
                }
            )
        claim_map = {
            "claim_id": claim.get("id"),
            "normalised_claim": cm_src.get("normalisedClaim") or claim.get("text"),
            "elements": elements,
            "metadata": {},
        }
        evidence = [
            {
                "evidence_id": e.get("evidenceId"),
                "title": e.get("title"),
                "snippet": e.get("snippet"),
                "url": e.get("url"),
                "tier": e.get("tier"),
                "published_date": e.get("publishedDate"),
                "date_basis": e.get("dateBasis"),
                "content_basis": e.get("contentBasis"),
                "receipt_status": e.get("receiptStatus"),
                "text_provenance": e.get("textProvenance"),
            }
            for e in claim.get("evidence") or []
        ]
        out.append((claim_map, evidence))
    return out


async def _run_one(analyzer, claim_map, evidence):
    from app.services.relationship_scope_review import review_relationship_scope

    cm = copy.deepcopy(claim_map)
    started = time.monotonic()
    await review_relationship_scope(analyzer, cm, evidence)
    receipt = cm["metadata"].get("scope_review") or {}
    return receipt, time.monotonic() - started


def _decision(record: Dict[str, Any]) -> str:
    status = record.get("status")
    if status == "compatible":
        return "compatible"
    if status == "scoped":
        return record.get("decision") or "scoped"
    if status == "unknown_kept":
        return "unknown"
    return "invalid"


def _load_labels(path: str) -> Dict[str, Dict[str, str]]:
    with open(path, encoding="utf-8") as f:
        return {row["pair_key"]: row for row in csv.DictReader(f)}


def _score(results, labels):
    """Per policy: demotion rates on positives/negatives, split by direction."""
    report = {}
    for policy in ("demote_unknown", "mismatch_only"):
        demoting = (
            {"mismatch", "unknown"} if policy == "demote_unknown" else {"mismatch"}
        )
        tally = defaultdict(Counter)
        wrong_demotions = []
        for key, runs in results.items():
            lab = labels.get(key)
            if not lab or not lab.get("label"):
                continue
            for decision in runs:
                demoted = decision in demoting
                group = f"{lab['label']}|{lab['relationship']}"
                tally[group]["n"] += 1
                tally[group]["demoted"] += demoted
                tally[group]["invalid"] += decision == "invalid"
                if lab["label"] == "should_demote":
                    tally[f"class:{lab.get('class') or '?'}"]["n"] += 1
                    tally[f"class:{lab.get('class') or '?'}"]["demoted"] += demoted
                if lab["label"] == "must_survive" and demoted:
                    wrong_demotions.append(key)
        report[policy] = {
            "groups": {g: dict(c) for g, c in sorted(tally.items())},
            "must_survive_demoted": sorted(Counter(wrong_demotions).items()),
        }
    return report


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--payloads", required=True)
    ap.add_argument("--labels", required=True)
    ap.add_argument("--repeats", type=int, default=3)
    ap.add_argument("--out", required=True)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--model", default=None, help="override GOOGLE_LLM_MODEL")
    args = ap.parse_args()

    if args.model:
        settings.GOOGLE_LLM_MODEL = args.model
    settings.ENABLE_RELATIONSHIP_REVIEW = True
    settings.RELATIONSHIP_REVIEW_DEMOTE_UNKNOWN = True

    from app.pipeline.claim_map_analyzer import ClaimMapAnalyzer

    analyzer = ClaimMapAnalyzer()
    if args.dry_run:
        analyzer._call_llm = AsyncMock(return_value={"pairs": []})

    files = sorted(glob.glob(os.path.join(args.payloads, "*.json")))
    results: Dict[str, List[str]] = defaultdict(list)
    timings, statuses = [], Counter()
    records_out = []

    async def run():
        for path in files:
            payload = json.load(open(path, encoding="utf-8"))
            if "claims" not in payload:
                continue
            short = os.path.basename(path)[:8]
            for claim_map, evidence in _to_internal(payload):
                for rep in range(args.repeats):
                    receipt, seconds = await _run_one(analyzer, claim_map, evidence)
                    timings.append(seconds)
                    statuses[receipt.get("status")] += 1
                    for call in receipt.get("calls") or []:
                        statuses[f"call:{call['status']}"] += 1
                    for record in receipt.get("pairs") or []:
                        key = f"{short}|{record['element_id']}|{record['evidence_id']}"
                        results[key].append(_decision(record))
                        records_out.append(
                            {
                                "key": key,
                                "repeat": rep,
                                **{
                                    k: record.get(k)
                                    for k in (
                                        "status",
                                        "decision",
                                        "dimension",
                                        "decision_basis",
                                        "model_decision",
                                        "reasoning",
                                        "invalid_reason",
                                        "quote",
                                    )
                                },
                            }
                        )

    asyncio.run(run())
    labels = _load_labels(args.labels)
    timings.sort()
    summary = {
        "records": len(files),
        "pairs": len(results),
        "repeats": args.repeats,
        "dry_run": args.dry_run,
        "latency_s": {
            "p50": timings[len(timings) // 2] if timings else None,
            "p90": timings[int(len(timings) * 0.9)] if timings else None,
        },
        "statuses": dict(statuses),
        "model": settings.GOOGLE_LLM_MODEL,
        "invalid_reasons": dict(
            Counter(
                r.get("invalid_reason")
                for r in records_out
                if r.get("status") == "invalid"
            )
        ),
        "score": _score(results, labels),
    }
    json.dump(
        {"summary": summary, "records": records_out},
        open(args.out, "w", encoding="utf-8"),
        indent=1,
    )
    print(json.dumps(summary, indent=1)[:6000])


if __name__ == "__main__":
    main()
