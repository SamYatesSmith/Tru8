"""MAP-stage evaluation harness — element_state_accuracy scoring.

Loads golden checks (frozen claim scaffolds + evidence), runs each through
the ClaimMapAnalyzer mapper, and scores element states against expected values.

Single metric: element_state_accuracy = correct_states / total_elements

Usage:
    # Default (production mapper, golden checks):
    python scripts/eval_score.py

    # With a tag for experiments.tsv logging:
    python scripts/eval_score.py --tag "baseline-flash-thinking"

    # Override model:
    python scripts/eval_score.py --model gemini-2.5-flash-lite --tag "flash-lite-test"

    # Dry run (no LLM calls — prints what would be tested):
    python scripts/eval_score.py --dry-run

    # Specific golden checks file:
    python scripts/eval_score.py --golden-file harness/golden_checks.json
"""

import argparse
import asyncio
import csv
import json
import logging
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Add backend to path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.core.config import settings
from app.pipeline.claim_map_analyzer import ClaimMapAnalyzer
from app.models.claim_map import ClaimType, ElementState

logger = logging.getLogger(__name__)

HARNESS_DIR = backend_dir / "harness"
DEFAULT_GOLDEN = HARNESS_DIR / "golden_checks.json"
EXPERIMENTS_TSV = HARNESS_DIR / "experiments.tsv"


# ---------------------------------------------------------------------------
# Golden check loading
# ---------------------------------------------------------------------------


def load_golden_checks(path: Path) -> List[Dict[str, Any]]:
    """Load golden checks from JSON file."""
    with open(path) as f:
        checks = json.load(f)

    # Validate structure
    for check in checks:
        assert "claim_id" in check, f"Missing claim_id in golden check"
        assert (
            "normalised_claim" in check
        ), f"Missing normalised_claim in {check['claim_id']}"
        assert "elements" in check, f"Missing elements in {check['claim_id']}"
        assert "evidence" in check, f"Missing evidence in {check['claim_id']}"
        assert (
            "expected_states" in check
        ), f"Missing expected_states in {check['claim_id']}"
        for elem in check["elements"]:
            eid = elem["element_id"]
            assert (
                eid in check["expected_states"]
            ), f"Element {eid} missing from expected_states in {check['claim_id']}"

    return checks


def build_claim_map(golden: Dict[str, Any]) -> Dict[str, Any]:
    """Build a ClaimMap dict from a golden check definition."""
    return {
        "claim_id": golden["claim_id"],
        "normalised_claim": golden["normalised_claim"],
        "claim_type": ClaimType.empirical,
        "elements": [
            {
                "element_id": e["element_id"],
                "description": e["description"],
                "evidence_refs": [],
                "state": None,
                "uncertainty": None,
                "bounty_text": None,
                "basis": None,
            }
            for e in golden["elements"]
        ],
        "orientation": None,
        "orientation_basis": None,
        "metadata": {
            "decomposition_model": "golden-synthetic",
            "mapping_model": None,
            "element_count": len(golden["elements"]),
            "completed_at": None,
        },
    }


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------


def score_claim(
    golden: Dict[str, Any],
    actual_claim_map: Dict[str, Any],
) -> Dict[str, Any]:
    """Score a single claim's mapping output against expected states.

    Returns per-element results and aggregate accuracy.
    """
    expected = golden["expected_states"]
    results = []

    for elem in actual_claim_map["elements"]:
        eid = elem["element_id"]
        actual_state = elem.get("state")
        # Normalise enum to string
        if hasattr(actual_state, "value"):
            actual_state = actual_state.value
        expected_state = expected.get(eid)

        correct = actual_state == expected_state
        results.append(
            {
                "element_id": eid,
                "expected": expected_state,
                "actual": actual_state,
                "correct": correct,
                "evidence_refs_count": len(elem.get("evidence_refs", [])),
                "uncertainty": elem.get("uncertainty"),
            }
        )

    correct_count = sum(1 for r in results if r["correct"])
    total = len(results)

    return {
        "claim_id": golden["claim_id"],
        "normalised_claim": golden["normalised_claim"],
        "element_results": results,
        "correct": correct_count,
        "total": total,
        "accuracy": correct_count / total if total > 0 else 0.0,
    }


# ---------------------------------------------------------------------------
# Experiment logging
# ---------------------------------------------------------------------------


def get_git_hash() -> str:
    """Get current git commit hash."""
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except Exception:
        return "unknown"


def log_experiment(
    tag: str,
    model: str,
    accuracy: float,
    correct: int,
    total: int,
    wall_time: float,
    token_usage: Dict[str, int],
    notes: str = "",
) -> None:
    """Append a row to experiments.tsv."""
    file_exists = EXPERIMENTS_TSV.exists()

    with open(EXPERIMENTS_TSV, "a", newline="") as f:
        writer = csv.writer(f, delimiter="\t")
        if not file_exists:
            writer.writerow(
                [
                    "timestamp",
                    "tag",
                    "git_hash",
                    "model",
                    "accuracy",
                    "correct",
                    "total",
                    "wall_time_s",
                    "input_tokens",
                    "output_tokens",
                    "notes",
                ]
            )

        writer.writerow(
            [
                datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                tag,
                get_git_hash(),
                model,
                f"{accuracy:.4f}",
                correct,
                total,
                f"{wall_time:.1f}",
                token_usage.get("input_tokens", 0),
                token_usage.get("output_tokens", 0),
                notes,
            ]
        )

    print(f"\nLogged to {EXPERIMENTS_TSV}")


# ---------------------------------------------------------------------------
# Main runner
# ---------------------------------------------------------------------------


async def run_eval(
    golden_checks: List[Dict[str, Any]],
    model_override: Optional[str] = None,
    dry_run: bool = False,
) -> Tuple[float, int, int, float, Dict[str, int]]:
    """Run MAP-stage evaluation on golden checks.

    Returns (accuracy, correct, total, wall_time, token_usage).
    """
    analyzer = ClaimMapAnalyzer()

    # Apply model override if specified
    if model_override:
        analyzer.model = model_override
        analyzer.primary_model = model_override

    all_results = []
    t0 = time.monotonic()

    for i, golden in enumerate(golden_checks):
        claim_id = golden["claim_id"]
        print(
            f"\n[{i+1}/{len(golden_checks)}] {claim_id}: {golden['normalised_claim'][:60]}..."
        )

        if dry_run:
            expected = golden["expected_states"]
            for eid, state in expected.items():
                print(f"  {eid}: expected={state}")
            all_results.append(
                {
                    "claim_id": claim_id,
                    "correct": 0,
                    "total": len(golden["elements"]),
                    "accuracy": 0.0,
                    "element_results": [],
                }
            )
            continue

        # Build claim map and run mapper
        claim_map = build_claim_map(golden)
        evidence_list = golden["evidence"]

        try:
            result_map = await analyzer.map_evidence_to_elements(
                claim_map, evidence_list
            )
        except Exception as e:
            print(f"  ERROR: {e}")
            # Score as all wrong
            all_results.append(
                {
                    "claim_id": claim_id,
                    "correct": 0,
                    "total": len(golden["elements"]),
                    "accuracy": 0.0,
                    "element_results": [],
                    "error": str(e),
                }
            )
            continue

        # Score
        scored = score_claim(golden, result_map)
        all_results.append(scored)

        # Print per-element results
        for er in scored["element_results"]:
            status = "PASS" if er["correct"] else "FAIL"
            print(
                f"  {er['element_id']}: expected={er['expected']}, "
                f"actual={er['actual']} [{status}]"
            )

    wall_time = time.monotonic() - t0
    token_usage = analyzer.get_token_usage()

    # Aggregate
    total_correct = sum(r["correct"] for r in all_results)
    total_elements = sum(r["total"] for r in all_results)
    accuracy = total_correct / total_elements if total_elements > 0 else 0.0

    # Print summary
    print(f"\n{'='*60}")
    print(f"ELEMENT STATE ACCURACY: {accuracy:.1%} ({total_correct}/{total_elements})")
    print(f"{'='*60}")
    print(f"  Claims tested:  {len(golden_checks)}")
    print(f"  Wall time:      {wall_time:.1f}s")
    if not dry_run:
        print(f"  Input tokens:   {token_usage.get('input_tokens', 0):,}")
        print(f"  Output tokens:  {token_usage.get('output_tokens', 0):,}")
        model_used = model_override or getattr(analyzer, "model", "default")
        print(f"  Model:          {model_used}")

    # Per-claim breakdown
    print(f"\nPer-claim breakdown:")
    for r in all_results:
        status = "PERFECT" if r["accuracy"] == 1.0 else f"{r['accuracy']:.0%}"
        print(f"  {r['claim_id']}: {r['correct']}/{r['total']} [{status}]")

    # Show failures
    failures = [
        (r["claim_id"], er)
        for r in all_results
        for er in r.get("element_results", [])
        if not er["correct"]
    ]
    if failures:
        print(f"\nFailures ({len(failures)}):")
        for claim_id, er in failures:
            print(
                f"  {claim_id}.{er['element_id']}: "
                f"expected={er['expected']}, got={er['actual']}"
            )

    return accuracy, total_correct, total_elements, wall_time, token_usage


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description="MAP-stage evaluation harness — element_state_accuracy"
    )
    parser.add_argument(
        "--golden-file",
        type=str,
        default=str(DEFAULT_GOLDEN),
        help=f"Path to golden checks JSON (default: {DEFAULT_GOLDEN})",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="Override mapping model (e.g. gemini-2.5-flash-lite)",
    )
    parser.add_argument(
        "--tag",
        type=str,
        default="eval",
        help="Tag for experiments.tsv logging (default: eval)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print expected states without calling LLM",
    )
    parser.add_argument(
        "--no-log",
        action="store_true",
        help="Skip writing to experiments.tsv",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable debug logging",
    )

    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO, format="%(message)s")

    # Load golden checks
    golden_path = Path(args.golden_file)
    if not golden_path.is_absolute():
        golden_path = backend_dir / golden_path
    golden_checks = load_golden_checks(golden_path)
    print(f"Loaded {len(golden_checks)} golden checks from {golden_path.name}")

    # Run evaluation
    accuracy, correct, total, wall_time, token_usage = asyncio.run(
        run_eval(golden_checks, model_override=args.model, dry_run=args.dry_run)
    )

    # Log experiment
    if not args.dry_run and not args.no_log:
        model_label = args.model or "production-default"
        log_experiment(
            tag=args.tag,
            model=model_label,
            accuracy=accuracy,
            correct=correct,
            total=total,
            wall_time=wall_time,
            token_usage=token_usage,
        )


if __name__ == "__main__":
    main()
