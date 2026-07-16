"""Artefact-1 — pool-balance probe (Decoupling build plan §15.3, 2026-07-16).

THE QUESTION (the D1 evidence): do the gate-v4-passing BALANCED route sets
retrieve balanced evidence POOLS through the EXISTING topical retrieval — with
no challenge lane? This is the plan's central unproven bet; its answer decides
whether the non-sycophancy floor may stay reactive (Phase 2) or must enter
Phase 1 as a scoped challenge lane (verification finding B4).

Design:
  * Input = the v4 transcript's final (balanced) route sets for the three
    normative probe claims, plus each claim's BASELINE decomposition as the
    contrast condition (what today's pipeline would do if it kept the opinion).
  * Each condition runs the REAL path: element-level retrieval
    (retrieve_evidence_with_cache — planner, augmentation, filter cascade,
    API adapters) → LLM relevance scoring (score_evidence_batch) → mapping
    (map_evidence_to_elements — mechanical state derivation).
  * Read = per-element supports/challenges/context counts from evidence_refs,
    state + rule_applied from state_basis, pool sizes, scorer exclusions.

Known divergences from the full pipeline (recorded, acceptable for a probe):
  * CLASSIFY stage omitted — evidence carries no tier at mapping time, so
    tier-weighted STATE labels are indicative only; the probe's signal is the
    raw supports/challenges COUNTS, which do not depend on tier.
  * FACTCHECK, coverage recovery, and Stage 3.8 post-filter recovery lanes
    are not exercised.

This is a PROBE, not a bench: qualitative, transcript-recorded, founder-
eyeballed. Makes real search-provider + LLM calls.

Run:  cd backend && python -m scripts.pool_balance_probe
      # zero web yield locally → run via: railway run python -m scripts.pool_balance_probe
Writes backend/scripts/.pool_balance_probe.json
"""

from __future__ import annotations

import asyncio
import json
import os
from typing import Any, Dict, List

from app.pipeline.claim_map_analyzer import ClaimMapAnalyzer
from app.pipeline.relevance_scorer import score_evidence_batch
from app.workers.pipeline import retrieve_evidence_with_cache

TRANSCRIPT = os.path.join(os.path.dirname(__file__), ".decompose_symmetry_eval_v4.json")
PROBE_LABELS = ["origin/opinion", "everyday/opinion", "opinion/positive-valence"]


def _load_cases() -> List[Dict[str, Any]]:
    with open(TRANSCRIPT, encoding="utf-8") as fh:
        rows = json.load(fh)
    by_label = {r["label"]: r for r in rows}
    cases = []
    for label in PROBE_LABELS:
        r = by_label.get(label)
        if not r or r.get("skipped") or not r.get("pass"):
            raise SystemExit(
                f"Transcript case '{label}' missing or not gate-green — "
                f"re-run scripts.decompose_symmetry_eval_v4 first."
            )
        cases.append(
            {
                "label": label,
                "claim": r["claim"],
                "balanced_elements": r["final_elements"],
                "balanced_leans": r["final_assess"]["leans"],
                "baseline_elements": r["baseline_elements"],
            }
        )
    return cases


def _build_claim_map(
    analyzer: ClaimMapAnalyzer,
    claim: str,
    claim_type: str,
    elements: List[str],
    cid: str,
):
    """Build a real ClaimMap through the pipeline's own parser (element ids etc.)."""
    parsed = {
        "normalised_claim": claim,
        "claim_type": claim_type,
        "elements": [{"description": d} for d in elements],
    }
    # _parse_decomposition_response reads _last_model_used, normally set by
    # _call_llm; the probe injects elements without a decompose call.
    if not hasattr(analyzer, "_last_model_used"):
        analyzer._last_model_used = "probe-injected"
    return analyzer._parse_decomposition_response(parsed, cid)


def _ref_counts(elem: Dict[str, Any]) -> Dict[str, int]:
    counts = {"supports": 0, "challenges": 0, "context": 0}
    for ref in elem.get("evidence_refs") or []:
        rel = (ref.get("relationship") if isinstance(ref, dict) else None) or ""
        if rel in counts:
            counts[rel] += 1
    return counts


async def _run_condition(
    analyzer: ClaimMapAnalyzer,
    label: str,
    condition: str,
    claim: str,
    claim_type: str,
    elements: List[str],
    leans: List[str] | None,
) -> Dict[str, Any]:
    cid = f"probe-{condition}"
    claim_map = _build_claim_map(analyzer, claim, claim_type, elements, cid)
    claims = [
        {
            "text": claim,
            "position": 0,
            "elements": [
                {"element_id": el["element_id"], "description": el["description"]}
                for el in claim_map["elements"]
            ],
            "key_entities": [],
        }
    ]

    print(f"\n  [{condition}] retrieving over {len(elements)} elements …")
    retrieval = await retrieve_evidence_with_cache(claims, None, {})
    evidence = retrieval.get("evidence_by_claim", {})
    pool = evidence.get("0", []) or evidence.get(0, [])
    raw_count = retrieval.get("raw_sources_count", 0)
    print(f"  [{condition}] pool={len(pool)} (raw reviewed {raw_count}) — scoring …")

    scored = await score_evidence_batch(
        claims=[claim], evidence={"0": pool}, article_context=""
    )
    excluded = scored.pop("_excluded", [])
    pool_scored = scored.get("0", [])
    print(
        f"  [{condition}] scored pool={len(pool_scored)} "
        f"(excluded {len(excluded)}) — mapping …"
    )

    mapped = await analyzer.map_evidence_to_elements(claim_map, pool_scored)

    per_element = []
    totals = {"supports": 0, "challenges": 0, "context": 0}
    for i, elem in enumerate(mapped["elements"]):
        counts = _ref_counts(elem)
        for k in totals:
            totals[k] += counts[k]
        basis = (elem.get("basis") or {}).get("state_derivation") or {}
        per_element.append(
            {
                "description": elem["description"],
                "lean": (leans[i] if leans and i < len(leans) else None),
                "counts": counts,
                "state": str(elem.get("state")),
                "rule_applied": basis.get("rule_applied"),
            }
        )

    return {
        "condition": condition,
        "claim_type": claim_type,
        "pool_retrieved": len(pool),
        "raw_reviewed": raw_count,
        "pool_scored": len(pool_scored),
        "scorer_excluded": len(excluded),
        "totals": totals,
        "per_element": per_element,
    }


async def main() -> None:
    try:
        import sys

        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:
        pass

    # Local runs without Redis emit one connection error PER cache lookup —
    # hundreds of junk lines that bury the probe's own output. Drop them at
    # the handler level (results are unaffected either way: cache-miss path).
    import logging

    class _RedisNoiseFilter(logging.Filter):
        def filter(self, record: logging.LogRecord) -> bool:
            msg = str(record.getMessage())
            return "6379" not in msg and "connecting to localhost" not in msg

    for h in logging.getLogger().handlers or []:
        h.addFilter(_RedisNoiseFilter())
    logging.getLogger("app.services.cache").setLevel(logging.CRITICAL)

    cases = _load_cases()
    analyzer = ClaimMapAnalyzer()
    results: List[Dict[str, Any]] = []
    zero_yield = 0

    for case in cases:
        print("\n" + "=" * 78)
        print(f"[{case['label']}]  {case['claim']}")

        balanced = await _run_condition(
            analyzer,
            case["label"],
            "balanced",
            case["claim"],
            "normative_flagged",
            case["balanced_elements"],
            case["balanced_leans"],
        )
        baseline = await _run_condition(
            analyzer,
            case["label"],
            "baseline",
            case["claim"],
            "empirical",
            case["baseline_elements"],
            None,
        )
        if balanced["pool_retrieved"] == 0 and baseline["pool_retrieved"] == 0:
            zero_yield += 1

        results.append({**case, "balanced": balanced, "baseline": baseline})

        for cond in (balanced, baseline):
            t = cond["totals"]
            print(
                f"\n  {cond['condition'].upper():9s} pool {cond['pool_scored']:3d} "
                f"→ supports={t['supports']} challenges={t['challenges']} "
                f"context={t['context']}"
            )
            for pe in cond["per_element"]:
                c = pe["counts"]
                lean = f"[{pe['lean'][:4]}] " if pe["lean"] else ""
                print(
                    f"      {lean}+{c['supports']}/−{c['challenges']}/○{c['context']} "
                    f"({pe['state']}, {pe['rule_applied']}) {pe['description'][:80]}"
                )

    out_path = os.path.join(os.path.dirname(__file__), ".pool_balance_probe.json")
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(results, fh, indent=2, ensure_ascii=False)

    print("\n" + "=" * 78)
    print("READ (probe, not verdict): does the BALANCED condition's pool contain")
    print("challenge-side material — especially on disconfirm-leaning routes —")
    print("without a challenge lane? Compare against BASELINE per claim above.")
    if zero_yield == len(cases):
        print(
            "\n⚠️  ZERO web yield on every claim — search providers unreachable "
            "locally.\n    Run against prod creds:  railway run python -m "
            "scripts.pool_balance_probe"
        )
    print(f"Saved transcript → {out_path}")


if __name__ == "__main__":
    asyncio.run(main())
