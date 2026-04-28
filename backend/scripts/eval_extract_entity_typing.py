#!/usr/bin/env python3
"""Extract-stage entity typing accuracy probe (NF-15).

Measures per-type precision/recall on a hand-labelled corpus of claims with
expected typed entities. Phase 1 of NF-15 (typed entities proposal,
2026-04-28): establish baseline of the current heuristic labeller before the
LLM-typed-extraction cutover.

Two modes:

    --mode heuristic
        Runs the existing _label_entities_for_api on each entity text from
        the ground-truth corpus. Measures heuristic accuracy.

    --mode llm        (added after Commit 2 lands)
        Runs the new typed-extract LLM on each claim text, extracts typed
        entities, matches by entity text against ground truth.

For each entity in the corpus (matched on text), record:
  - true_type   (ground truth label)
  - pred_type   (what the system emitted)

Compute:
  - per-type precision, recall
  - confusion matrix
  - "matched" coverage (entities the system found in the claim)

Acceptance thresholds (heuristic baseline expected to fail; LLM target):
  - per-type precision >= 0.85 for ORG/PERSON/LAW/AMOUNT/DATE/LOCATION
  - per-type precision >= 0.70 for EVENT/PRODUCT
  - stability >= 0.95 across N=5 runs (LLM mode only)

Usage:
    python scripts/eval_extract_entity_typing.py --mode heuristic
    python scripts/eval_extract_entity_typing.py --mode llm --runs 5

Output:
    backend/data/extract_entity_typing_<mode>_<timestamp>.json
"""

import argparse
import asyncio
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add backend to path so app.* imports work
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv  # type: ignore

load_dotenv(Path(__file__).resolve().parent.parent / ".env")


# ---------------------------------------------------------------------------
# CORPUS (12 claims): hand-labelled typed entities.
# Spans: UK Law (Acts), US Bills, companies (plc/Inc/Ltd/single-name),
# people, events, products, locations, amounts, dates. Each claim has
# 2-5 entities. Type vocabulary: ORG | PERSON | LAW | EVENT | PRODUCT |
# LOCATION | AMOUNT | DATE | OTHER.
# ---------------------------------------------------------------------------

CORPUS: List[Dict[str, Any]] = [
    {
        "id": "uk-law-act-1",
        "claim": "The Climate Change Act 2008 set the UK's target of net zero emissions by 2050",
        "entities": [
            {"text": "Climate Change Act 2008", "type": "LAW"},
            {"text": "UK", "type": "LOCATION"},
            {"text": "2050", "type": "DATE"},
        ],
        "notes": "Canonical UK Law claim; 'Climate Change Act 2008' must type as LAW",
    },
    {
        "id": "uk-law-act-2",
        "claim": "The Online Safety Act 2023 requires platforms to verify users' ages",
        "entities": [
            {"text": "Online Safety Act 2023", "type": "LAW"},
        ],
        "notes": "Recent UK statute; no other strong entities",
    },
    {
        "id": "uk-finance-currency",
        "claim": "BP plc reported record profits of GBP 28 billion in 2022",
        "entities": [
            {"text": "BP plc", "type": "ORG"},
            {"text": "GBP 28 billion", "type": "AMOUNT"},
            {"text": "2022", "type": "DATE"},
        ],
        "notes": "Lowercase plc — heuristic misses this as ORG; LLM should not",
    },
    {
        "id": "us-finance-org-1",
        "claim": "ExxonMobil reported record profits of $56 billion in 2022",
        "entities": [
            {"text": "ExxonMobil", "type": "ORG"},
            {"text": "$56 billion", "type": "AMOUNT"},
            {"text": "2022", "type": "DATE"},
        ],
        "notes": "Single-word ORG — heuristic misses; LLM should not",
    },
    {
        "id": "tech-product",
        "claim": "Tesla delivered 1.3 million Model Y vehicles in 2022",
        "entities": [
            {"text": "Tesla", "type": "ORG"},
            {"text": "Model Y", "type": "PRODUCT"},
            {"text": "1.3 million", "type": "AMOUNT"},
            {"text": "2022", "type": "DATE"},
        ],
        "notes": "Mixed ORG + PRODUCT + AMOUNT — Model Y is PRODUCT not ORG",
    },
    {
        "id": "us-bill",
        "claim": "The Inflation Reduction Act of 2022 allocated $369 billion to US climate programmes",
        "entities": [
            {"text": "Inflation Reduction Act of 2022", "type": "LAW"},
            {"text": "$369 billion", "type": "AMOUNT"},
            {"text": "US", "type": "LOCATION"},
        ],
        "notes": "US statute with 'of YYYY' suffix variant",
    },
    {
        "id": "person-title",
        "claim": "Prime Minister Keir Starmer announced new defence spending in October 2024",
        "entities": [
            {"text": "Keir Starmer", "type": "PERSON"},
            {"text": "October 2024", "type": "DATE"},
        ],
        "notes": "Title prefix; PERSON not ORG",
    },
    {
        "id": "person-event",
        "claim": "Joe Biden signed the CHIPS and Science Act at a White House ceremony in August 2022",
        "entities": [
            {"text": "Joe Biden", "type": "PERSON"},
            {"text": "CHIPS and Science Act", "type": "LAW"},
            {"text": "White House", "type": "LOCATION"},
            {"text": "August 2022", "type": "DATE"},
        ],
        "notes": "White House is LOCATION here (the building); also tests Act-no-year suffix",
    },
    {
        "id": "named-event",
        "claim": "The 2024 Paris Olympics drew 9.5 million spectators and US$5.7 billion in revenue",
        "entities": [
            {"text": "2024 Paris Olympics", "type": "EVENT"},
            {"text": "Paris", "type": "LOCATION"},
            {"text": "9.5 million", "type": "AMOUNT"},
            {"text": "US$5.7 billion", "type": "AMOUNT"},
        ],
        "notes": "Named event vs location disambiguation",
    },
    {
        "id": "academic-product",
        "claim": "JWST detected sulfur dioxide in WASP-39b's atmosphere in November 2022",
        "entities": [
            {"text": "JWST", "type": "PRODUCT"},
            {"text": "WASP-39b", "type": "OTHER"},
            {"text": "sulfur dioxide", "type": "OTHER"},
            {"text": "November 2022", "type": "DATE"},
        ],
        "notes": "JWST is a PRODUCT (instrument); WASP-39b/sulfur dioxide are domain concepts → OTHER",
    },
    {
        "id": "uk-org-ltd",
        "claim": "Aviva Investors Ltd manages over £225 billion in assets across global markets",
        "entities": [
            {"text": "Aviva Investors Ltd", "type": "ORG"},
            {"text": "£225 billion", "type": "AMOUNT"},
        ],
        "notes": "Title-Case + Ltd suffix; should be ORG",
    },
    {
        "id": "international-org",
        "claim": "The European Central Bank raised its main refinancing rate to 4.5% in September 2024",
        "entities": [
            {"text": "European Central Bank", "type": "ORG"},
            {"text": "4.5%", "type": "AMOUNT"},
            {"text": "September 2024", "type": "DATE"},
        ],
        "notes": "International organisation; multi-word ORG without traditional suffix",
    },
]


# ---------------------------------------------------------------------------
# Heuristic baseline: replicates retrieve.py:1882 _label_entities_for_api
# (copied here so the eval can run without instantiating the retrieve class
# and to keep this script independent for post-cutover comparison runs)
# ---------------------------------------------------------------------------


def _heuristic_label(entity_text: str) -> str:
    """Mirror of retrieve.py:1882 _label_entities_for_api logic for one entity."""
    org_suffixes = (
        "FC",
        "United",
        "City",
        "Rovers",
        "Wanderers",
        "Athletic",
        "Dortmund",
        "Arsenal",
        "Chelsea",
        "Munich",
        "Madrid",
        "Barcelona",
        "Milan",
        "Inter",
        "Juventus",
        "PSG",
        "Bayern",
        "Liverpool",
        "Tottenham",
        "Spurs",
        "Hotspur",
        "Rangers",
        "Celtic",
        "Club",
        "Association",
        "Federation",
        "League",
        "UEFA",
        "FIFA",
        "Inc",
        "Ltd",
        "Corp",
        "Company",
        "Organization",
        "Government",
    )
    person_prefixes = (
        "Mr",
        "Mrs",
        "Ms",
        "Dr",
        "Prof",
        "Sir",
        "Lord",
        "Lady",
        "President",
        "Prime Minister",
        "Minister",
        "Senator",
        "Governor",
    )

    entity_stripped = entity_text.strip()
    words = entity_stripped.split()

    if any(entity_stripped.endswith(suffix) for suffix in org_suffixes):
        return "ORG"
    if (
        len(words) >= 2
        and all(w[0].isupper() for w in words if w)
        and not any(suffix in entity_stripped for suffix in org_suffixes)
    ):
        return "PERSON"
    if any(entity_stripped.startswith(prefix) for prefix in person_prefixes):
        return "PERSON"
    return "ENTITY"


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------


def evaluate_predictions(
    corpus: List[Dict[str, Any]],
    predictions: Dict[str, List[Dict[str, str]]],
) -> Dict[str, Any]:
    """Compute per-type precision/recall + confusion matrix.

    predictions[claim_id] = list of {text, type} the system emitted for that
    claim. We match by entity text (case-insensitive substring or exact) to
    ground-truth entities.
    """
    # Pair (true_type, pred_type) for each ground-truth entity that matches
    pairs: List[tuple[str, Optional[str]]] = []
    # Predictions that didn't match any ground-truth entity (false-add noise)
    unmatched_preds: List[Dict[str, str]] = []

    for claim in corpus:
        cid = claim["id"]
        truth = {e["text"].lower(): e["type"] for e in claim["entities"]}
        pred = predictions.get(cid, [])
        pred_by_text = {e["text"].lower(): e["type"] for e in pred}

        for truth_text, truth_type in truth.items():
            # Exact-text match first
            if truth_text in pred_by_text:
                pairs.append((truth_type, pred_by_text[truth_text]))
            else:
                # Substring match (either direction) for tolerant comparison
                hit = None
                for pt, pty in pred_by_text.items():
                    if truth_text in pt or pt in truth_text:
                        hit = pty
                        break
                pairs.append((truth_type, hit))

        # Track preds that don't correspond to any truth entity
        for pred_text, pred_type in pred_by_text.items():
            if pred_text not in truth and not any(
                pred_text in t or t in pred_text for t in truth
            ):
                unmatched_preds.append(
                    {"claim_id": cid, "text": pred_text, "type": pred_type}
                )

    # Per-type precision/recall
    types = sorted({t for t, _ in pairs} | {p for _, p in pairs if p is not None})
    per_type: Dict[str, Dict[str, Any]] = {}
    for t in types:
        tp = sum(1 for tt, pt in pairs if tt == t and pt == t)
        fn = sum(1 for tt, pt in pairs if tt == t and pt != t)
        fp = sum(1 for tt, pt in pairs if tt != t and pt == t and tt is not None)
        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        per_type[t] = {
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "precision": round(precision, 3),
            "recall": round(recall, 3),
        }

    # Confusion matrix: rows = true, cols = pred (None for missed)
    confusion: Dict[str, Counter] = defaultdict(Counter)
    for true_type, pred_type in pairs:
        confusion[true_type][pred_type or "MISSED"] += 1

    # Coverage: fraction of ground-truth entities the system found
    matched = sum(1 for _, pt in pairs if pt is not None)
    total = len(pairs)
    coverage = matched / total if total else 0.0

    return {
        "n_claims": len(corpus),
        "n_truth_entities": total,
        "n_matched": matched,
        "coverage": round(coverage, 3),
        "per_type": per_type,
        "confusion": {k: dict(v) for k, v in confusion.items()},
        "unmatched_preds_sample": unmatched_preds[:10],
        "unmatched_preds_count": len(unmatched_preds),
    }


# ---------------------------------------------------------------------------
# Mode runners
# ---------------------------------------------------------------------------


def run_heuristic() -> Dict[str, List[Dict[str, str]]]:
    """For each claim, run heuristic on the ground-truth entity texts.

    The heuristic only labels — it doesn't extract. So the fairest way to
    measure it is to give it the same entity strings the LLM would have
    extracted. We use the ground-truth texts as the input set; that
    over-states heuristic recall (LLM may extract slightly different
    entities) but cleanly isolates the typing question.
    """
    out: Dict[str, List[Dict[str, str]]] = {}
    for claim in CORPUS:
        out[claim["id"]] = [
            {"text": e["text"], "type": _heuristic_label(e["text"])}
            for e in claim["entities"]
        ]
    return out


async def run_llm(runs: int = 1) -> List[Dict[str, List[Dict[str, str]]]]:
    """Run typed-extract LLM N times. Implemented after Commit 2."""
    raise NotImplementedError(
        "LLM mode requires Commit 2 (typed extract.py) to land first. "
        "Run with --mode heuristic for now to record the baseline."
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mode",
        choices=["heuristic", "llm"],
        default="heuristic",
        help="heuristic = current labeller baseline; llm = new typed-extract",
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=1,
        help="LLM mode only: number of repeats for stability",
    )
    args = parser.parse_args()

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    out_path = (
        Path(__file__).resolve().parent.parent
        / "data"
        / f"extract_entity_typing_{args.mode}_{timestamp}.json"
    )

    if args.mode == "heuristic":
        predictions = run_heuristic()
        metrics = evaluate_predictions(CORPUS, predictions)
        report = {
            "mode": args.mode,
            "timestamp": timestamp,
            "corpus_size": len(CORPUS),
            "metrics": metrics,
            "predictions": predictions,
        }
    else:
        runs_data = asyncio.run(run_llm(runs=args.runs))
        # Stability: consensus type per (claim_id, entity_text) across runs
        # Reported when N>1; for N=1 just evaluate the single run.
        first = runs_data[0]
        metrics = evaluate_predictions(CORPUS, first)
        report = {
            "mode": args.mode,
            "timestamp": timestamp,
            "corpus_size": len(CORPUS),
            "n_runs": args.runs,
            "metrics": metrics,
            "all_runs": runs_data,
        }

    out_path.write_text(json.dumps(report, indent=2))

    # Human-readable summary
    print()
    print("=" * 72)
    print(
        f"Mode: {args.mode}  |  Corpus: {len(CORPUS)} claims  "
        f"|  Output: {out_path.name}"
    )
    print("=" * 72)
    print(
        f"Coverage: {metrics['coverage']:.1%}  "
        f"({metrics['n_matched']}/{metrics['n_truth_entities']} truth entities matched)"
    )
    print()
    print("Per-type precision / recall:")
    print(f"  {'TYPE':<10} {'P':>6} {'R':>6}  {'TP':>4} {'FP':>4} {'FN':>4}")
    for t, m in sorted(metrics["per_type"].items()):
        print(
            f"  {t:<10} {m['precision']:>6.2f} {m['recall']:>6.2f}  "
            f"{m['tp']:>4} {m['fp']:>4} {m['fn']:>4}"
        )
    print()
    print("Confusion (true -> pred):")
    for true_type, preds in sorted(metrics["confusion"].items()):
        preds_str = ", ".join(f"{k}={v}" for k, v in sorted(preds.items()))
        print(f"  {true_type:<10} -> {preds_str}")
    print()
    if metrics["unmatched_preds_count"]:
        print(
            f"Unmatched predictions: {metrics['unmatched_preds_count']} "
            f"(sample: {metrics['unmatched_preds_sample'][:3]})"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
