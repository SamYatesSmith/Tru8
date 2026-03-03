"""Regression runner — re-run mapper on golden cases, compare to expected.

Re-runs the mapping prompt on golden (audited) cases and compares actual
model output to the expected relationships and states.

Usage:
    # Run regression with current production model
    python scripts/audit_regress.py

    # Run with different model or snippet length
    python scripts/audit_regress.py --model gpt-4o
    python scripts/audit_regress.py --snippet-length 800
    python scripts/audit_regress.py --model gpt-4o --snippet-length 800

    # Dry-run (no LLM calls, just validate golden set)
    python scripts/audit_regress.py --dry-run
"""

import argparse
import asyncio
import hashlib
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from scripts.eval_mapping_model import (
    build_mapping_prompt,
    call_google_model,
    call_openai_model,
    validate_mapping_output,
)

logger = logging.getLogger(__name__)

REGRESSION_DIR = backend_dir / "audit" / "track-n" / "regression"
GOLDEN_DIR = REGRESSION_DIR / "golden"
RUNS_DIR = REGRESSION_DIR / "runs"

DEFAULT_SNIPPET_LENGTH = 400
DEFAULT_MODEL = "gemini-2.5-flash-lite"


# ---------------------------------------------------------------------------
# Golden case loading
# ---------------------------------------------------------------------------


def load_golden_cases() -> List[Dict[str, Any]]:
    """Load all golden cases from the regression/golden directory."""
    GOLDEN_DIR.mkdir(parents=True, exist_ok=True)
    cases = []
    for path in sorted(GOLDEN_DIR.glob("case-*.json")):
        with open(path) as f:
            cases.append(json.load(f))
    return cases


# ---------------------------------------------------------------------------
# Comparison logic
# ---------------------------------------------------------------------------


def compare_states(
    golden: Dict[str, Any],
    actual_elements: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Compare actual element states to expected states.

    Returns list of state comparison results.
    """
    expected = golden.get("expected", {}).get("elements", [])
    expected_by_id = {e["element_id"]: e for e in expected}
    actual_by_id = {e["element_id"]: e for e in actual_elements}

    results = []
    for eid, exp in expected_by_id.items():
        actual = actual_by_id.get(eid, {})
        actual_state = actual.get("state", "unresolved")
        expected_state = exp.get("expected_state", "unresolved")

        results.append(
            {
                "element_id": eid,
                "expected": expected_state,
                "actual": actual_state,
                "match": actual_state == expected_state,
            }
        )

    return results


def compare_refs(
    golden: Dict[str, Any],
    actual_elements: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Compare actual evidence_ref relationships to expected.

    Returns list of ref comparison results.
    """
    expected = golden.get("expected", {}).get("elements", [])
    expected_by_id = {e["element_id"]: e for e in expected}
    actual_by_id = {e["element_id"]: e for e in actual_elements}

    results = []
    for eid, exp in expected_by_id.items():
        actual_elem = actual_by_id.get(eid, {})
        actual_refs = actual_elem.get("evidence_refs", [])
        actual_ref_map = {r["evidence_id"]: r for r in actual_refs}

        for exp_ref in exp.get("expected_refs", []):
            ev_id = exp_ref["evidence_id"]
            expected_rel = exp_ref.get("expected_relationship", "context")
            actual_ref = actual_ref_map.get(ev_id)

            if actual_ref:
                actual_rel = actual_ref.get("relationship", "")
                results.append(
                    {
                        "element_id": eid,
                        "evidence_id": ev_id,
                        "expected_rel": expected_rel,
                        "actual_rel": actual_rel,
                        "match": actual_rel == expected_rel,
                    }
                )
            else:
                results.append(
                    {
                        "element_id": eid,
                        "evidence_id": ev_id,
                        "expected_rel": expected_rel,
                        "actual_rel": None,
                        "match": False,
                    }
                )

    return results


def collect_regressions(
    state_results: List[Dict[str, Any]],
    ref_results: List[Dict[str, Any]],
) -> List[str]:
    """Collect regression descriptions from comparison results."""
    regressions = []
    for sr in state_results:
        if not sr["match"]:
            regressions.append(
                f"{sr['element_id']}: state expected={sr['expected']}, "
                f"actual={sr['actual']}"
            )
    for rr in ref_results:
        if not rr["match"]:
            regressions.append(
                f"{rr['element_id']}/{rr['evidence_id']}: "
                f"rel expected={rr['expected_rel']}, actual={rr['actual_rel']}"
            )
    return regressions


def compute_regression_summary(
    all_case_results: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Compute aggregate accuracy from all case results."""
    total_states = 0
    correct_states = 0
    total_refs = 0
    correct_refs = 0
    total_regressions = 0

    for cr in all_case_results:
        for sr in cr.get("state_results", []):
            total_states += 1
            if sr["match"]:
                correct_states += 1
        for rr in cr.get("ref_results", []):
            total_refs += 1
            if rr["match"]:
                correct_refs += 1
        total_regressions += len(cr.get("regressions", []))

    return {
        "cases_tested": len(all_case_results),
        "state_accuracy": (
            round(correct_states / total_states, 2) if total_states > 0 else 0.0
        ),
        "ref_accuracy": round(correct_refs / total_refs, 2) if total_refs > 0 else 0.0,
        "regressions": total_regressions,
    }


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------


async def run_regression(
    golden_cases: List[Dict[str, Any]],
    model: str = DEFAULT_MODEL,
    snippet_length: int = DEFAULT_SNIPPET_LENGTH,
    dry_run: bool = False,
    include_metadata: bool = False,
    max_tokens: int = 4000,
) -> Dict[str, Any]:
    """Run the mapper on golden cases and compare to expected outputs."""
    case_results = []

    for i, golden in enumerate(golden_cases):
        case_id = golden["case_id"]
        claim = golden["claim"]
        evidence = golden["evidence"]

        # Build evidence list in the format expected by build_mapping_prompt
        evidence_for_prompt = [
            {
                "evidence_id": ev["evidence_id"],
                "title": ev["title"],
                "snippet": ev.get("mapper_window") or ev.get("full_text", ""),
                "text": ev.get("full_text", ""),
            }
            for ev in evidence
        ]

        prompt = build_mapping_prompt(
            normalised_claim=claim["normalised_claim"],
            elements=claim["elements"],
            evidence_list=evidence_for_prompt,
            snippet_length=snippet_length,
            include_metadata=include_metadata,
        )
        prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()[:12]

        print(
            f"[{i+1}/{len(golden_cases)}] {case_id}: {claim['normalised_claim'][:60]}..."
        )

        if dry_run:
            print(f"  [DRY RUN] Prompt built ({len(prompt)} chars, hash={prompt_hash})")
            case_results.append(
                {
                    "case_id": case_id,
                    "dry_run": True,
                    "state_results": [],
                    "ref_results": [],
                    "regressions": [],
                }
            )
            continue

        # Call the model
        if model.startswith("gpt"):
            result = await call_openai_model(
                prompt=prompt, model=model, max_tokens=max_tokens
            )
        else:
            result = await call_google_model(
                prompt=prompt, model=model, max_tokens=max_tokens
            )

        if result.get("error"):
            print(f"  ERROR: {result['error']}")
            case_results.append(
                {
                    "case_id": case_id,
                    "error": result["error"],
                    "state_results": [],
                    "ref_results": [],
                    "regressions": [f"LLM call failed: {result['error']}"],
                }
            )
            continue

        # Validate output
        validated = validate_mapping_output(
            result.get("parsed"),
            claim["elements"],
            evidence_for_prompt,
        )

        # Compare to expected
        state_results = compare_states(golden, validated["elements"])
        ref_results = compare_refs(golden, validated["elements"])
        regressions = collect_regressions(state_results, ref_results)

        state_matches = sum(1 for sr in state_results if sr["match"])
        ref_matches = sum(1 for rr in ref_results if rr["match"])

        print(
            f"  States: {state_matches}/{len(state_results)} match, "
            f"Refs: {ref_matches}/{len(ref_results)} match"
        )
        if regressions:
            for r in regressions:
                print(f"  REGRESSION: {r}")

        case_results.append(
            {
                "case_id": case_id,
                "state_results": state_results,
                "ref_results": ref_results,
                "regressions": regressions,
            }
        )

    # Build run result
    summary = compute_regression_summary(case_results)

    run_id = (
        f"{datetime.now(timezone.utc).strftime('%Y-%m-%d')}_{model.replace('/', '_')}"
    )
    run_result = {
        "run_id": run_id,
        "model": model,
        "snippet_length": snippet_length,
        "prompt_hash": prompt_hash if golden_cases else None,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "cases": case_results,
        "summary": summary,
    }

    return run_result


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description="Run mapper regression on golden cases"
    )
    parser.add_argument(
        "--model",
        type=str,
        default=DEFAULT_MODEL,
        help=f"Model to use (default: {DEFAULT_MODEL})",
    )
    parser.add_argument(
        "--snippet-length",
        type=int,
        default=DEFAULT_SNIPPET_LENGTH,
        help=f"Snippet truncation length (default: {DEFAULT_SNIPPET_LENGTH})",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=4000,
        help="Max output tokens for LLM calls (default: 4000)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate golden set without LLM calls",
    )
    parser.add_argument(
        "--include-metadata",
        action="store_true",
        help="Include tier/type metadata in evidence formatting (matches pipeline)",
    )
    parser.add_argument("--verbose", action="store_true", help="Enable debug logging")

    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO, format="%(message)s")

    golden_cases = load_golden_cases()
    if not golden_cases:
        print(f"No golden cases found in {GOLDEN_DIR}")
        return

    print(f"Loaded {len(golden_cases)} golden cases")
    print(f"Model: {args.model}, snippet length: {args.snippet_length}")
    if args.dry_run:
        print("[DRY RUN MODE]")
    print()

    run_result = asyncio.run(
        run_regression(
            golden_cases=golden_cases,
            model=args.model,
            snippet_length=args.snippet_length,
            dry_run=args.dry_run,
            include_metadata=args.include_metadata,
            max_tokens=args.max_tokens,
        )
    )

    # Save run results
    if not args.dry_run:
        RUNS_DIR.mkdir(parents=True, exist_ok=True)
        run_path = RUNS_DIR / f"{run_result['run_id']}.json"
        with open(run_path, "w", encoding="utf-8") as f:
            json.dump(run_result, f, indent=2, default=str)
        print(f"\nRun results saved to {run_path}")

    # Print summary
    s = run_result["summary"]
    print(f"\nSummary:")
    print(f"  Cases tested: {s['cases_tested']}")
    print(f"  State accuracy: {s['state_accuracy']:.0%}")
    print(f"  Ref accuracy: {s['ref_accuracy']:.0%}")
    print(f"  Regressions: {s['regressions']}")


if __name__ == "__main__":
    main()
