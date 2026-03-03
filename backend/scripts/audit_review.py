"""Summarise, validate, and promote mapping audit judgments.

Reads completed judgment files, produces the failure mode frequency table,
validates review completeness, and promotes audited cases to golden set.

Usage:
    # Summarise all completed judgments
    python scripts/audit_review.py --summarise

    # Validate judgment files (check schema, flag incomplete reviews)
    python scripts/audit_review.py --validate

    # Promote audited cases to golden set
    python scripts/audit_review.py --promote case-001 case-005 case-012
"""

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

logger = logging.getLogger(__name__)

AUDIT_DIR = backend_dir / "audit" / "track-n" / "audit"
CASES_DIR = AUDIT_DIR / "cases"
JUDGMENTS_DIR = AUDIT_DIR / "judgments"
SUMMARY_PATH = AUDIT_DIR / "summary.json"

REGRESSION_DIR = backend_dir / "audit" / "track-n" / "regression"
GOLDEN_DIR = REGRESSION_DIR / "golden"

VALID_FAILURE_MODES = {"A", "B", "C", "D"}


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def validate_judgment(judgment: Dict[str, Any]) -> List[str]:
    """Validate a judgment file for completeness.

    Returns list of validation error strings. Empty = valid.
    """
    errors = []
    case_id = judgment.get("case_id", "unknown")

    # Check ref_judgments
    for i, rj in enumerate(judgment.get("ref_judgments", [])):
        prefix = f"{case_id} ref_judgments[{i}]"

        if rj.get("correct") is None:
            errors.append(f"{prefix}: 'correct' is null (review incomplete)")

        if rj.get("correct") is False:
            if not rj.get("failure_mode"):
                errors.append(f"{prefix}: incorrect but no failure_mode set")
            elif rj["failure_mode"] not in VALID_FAILURE_MODES:
                errors.append(
                    f"{prefix}: invalid failure_mode '{rj['failure_mode']}' "
                    f"(must be A/B/C/D)"
                )

            if rj.get("window_sufficient") is None:
                errors.append(f"{prefix}: incorrect but window_sufficient not set")

    # Check missing_refs
    for i, mr in enumerate(judgment.get("missing_refs", [])):
        prefix = f"{case_id} missing_refs[{i}]"

        if not mr.get("failure_mode"):
            errors.append(f"{prefix}: no failure_mode set")
        elif mr["failure_mode"] not in VALID_FAILURE_MODES:
            errors.append(f"{prefix}: invalid failure_mode '{mr['failure_mode']}'")

        if mr.get("window_sufficient") is None:
            errors.append(f"{prefix}: window_sufficient not set")

    # Check state_judgments
    for i, sj in enumerate(judgment.get("state_judgments", [])):
        prefix = f"{case_id} state_judgments[{i}]"

        if sj.get("correct") is None:
            errors.append(f"{prefix}: 'correct' is null (review incomplete)")

        if sj.get("correct") is False:
            if not sj.get("failure_mode"):
                errors.append(f"{prefix}: incorrect but no failure_mode set")
            elif sj["failure_mode"] not in VALID_FAILURE_MODES:
                errors.append(f"{prefix}: invalid failure_mode '{sj['failure_mode']}'")

    return errors


def is_judgment_complete(judgment: Dict[str, Any]) -> bool:
    """Check if all review fields in a judgment have been filled in."""
    for rj in judgment.get("ref_judgments", []):
        if rj.get("correct") is None:
            return False
    for sj in judgment.get("state_judgments", []):
        if sj.get("correct") is None:
            return False
    return True


# ---------------------------------------------------------------------------
# Summary aggregation
# ---------------------------------------------------------------------------


def build_failure_mode_table(
    judgments: List[Dict[str, Any]],
) -> Dict[str, Dict[str, int]]:
    """Build failure mode frequency table from completed judgments.

    Returns: {mode: {window_sufficient: N, window_insufficient: N}}
    """
    table = {
        "A_missed_contradiction": {"window_sufficient": 0, "window_insufficient": 0},
        "B_phantom_support": {"window_sufficient": 0, "window_insufficient": 0},
        "C_misattributed_scope": {"window_sufficient": 0, "window_insufficient": 0},
        "D_state_inflation": {"window_sufficient": 0, "window_insufficient": 0},
    }

    mode_key_map = {
        "A": "A_missed_contradiction",
        "B": "B_phantom_support",
        "C": "C_misattributed_scope",
        "D": "D_state_inflation",
    }

    for j in judgments:
        # Count from ref_judgments
        for rj in j.get("ref_judgments", []):
            mode = rj.get("failure_mode")
            if mode and mode in mode_key_map:
                key = mode_key_map[mode]
                ws = rj.get("window_sufficient")
                if ws is True:
                    table[key]["window_sufficient"] += 1
                elif ws is False:
                    table[key]["window_insufficient"] += 1

        # Count from missing_refs
        for mr in j.get("missing_refs", []):
            mode = mr.get("failure_mode")
            if mode and mode in mode_key_map:
                key = mode_key_map[mode]
                ws = mr.get("window_sufficient")
                if ws is True:
                    table[key]["window_sufficient"] += 1
                elif ws is False:
                    table[key]["window_insufficient"] += 1

        # Count from state_judgments (only D applies typically, but count all)
        for sj in j.get("state_judgments", []):
            mode = sj.get("failure_mode")
            if mode and mode in mode_key_map:
                key = mode_key_map[mode]
                # State judgments don't have window_sufficient
                # Count as window_sufficient (model issue, not input issue)
                table[key]["window_sufficient"] += 1

    return table


def compute_accuracy(judgments: List[Dict[str, Any]]) -> Dict[str, float]:
    """Compute relationship and state accuracy percentages."""
    refs_total = 0
    refs_correct = 0
    states_total = 0
    states_correct = 0

    for j in judgments:
        for rj in j.get("ref_judgments", []):
            if rj.get("correct") is not None:
                refs_total += 1
                if rj["correct"]:
                    refs_correct += 1

        for sj in j.get("state_judgments", []):
            if sj.get("correct") is not None:
                states_total += 1
                if sj["correct"]:
                    states_correct += 1

    return {
        "relationship_correct_pct": (
            round(refs_correct / refs_total, 2) if refs_total > 0 else 0.0
        ),
        "state_correct_pct": (
            round(states_correct / states_total, 2) if states_total > 0 else 0.0
        ),
        "refs_total": refs_total,
        "refs_correct": refs_correct,
        "states_total": states_total,
        "states_correct": states_correct,
    }


def identify_dominant_mode(
    table: Dict[str, Dict[str, int]],
) -> Tuple[str, str, str]:
    """Identify the dominant failure mode and generate a decision signal.

    Returns: (dominant_mode, dominant_cause, decision_signal)
    """
    # Total errors per mode
    mode_totals = {}
    for mode, counts in table.items():
        total = counts["window_sufficient"] + counts["window_insufficient"]
        mode_totals[mode] = total

    # Find dominant mode (highest total)
    if not mode_totals or max(mode_totals.values()) == 0:
        return ("none", "none", "No failures detected")

    dominant_mode = max(mode_totals, key=mode_totals.get)

    # Determine if window-insufficient or window-sufficient dominates
    ws = table[dominant_mode]["window_sufficient"]
    wi = table[dominant_mode]["window_insufficient"]

    if wi > ws:
        dominant_cause = "window_insufficient"
        decision_signal = (
            "Fix input pipeline (more text / element-targeted selection) "
            "before model upgrade"
        )
    elif ws > wi:
        dominant_cause = "window_sufficient"
        decision_signal = "Model weakness — consider prompt tuning or model upgrade"
    else:
        dominant_cause = "mixed"
        decision_signal = "Mixed causes — address both input pipeline and model quality"

    return dominant_mode, dominant_cause, decision_signal


def build_summary(judgments: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Build the full summary.json from completed judgments."""
    table = build_failure_mode_table(judgments)
    accuracy = compute_accuracy(judgments)
    dominant_mode, dominant_cause, decision_signal = identify_dominant_mode(table)

    refs_reviewed = accuracy["refs_total"]
    states_reviewed = accuracy["states_total"]

    return {
        "audit_id": f"pilot-{datetime.now(timezone.utc).strftime('%Y%m%d')}",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "cases_reviewed": len(judgments),
        "refs_reviewed": refs_reviewed,
        "states_reviewed": states_reviewed,
        "failure_mode_table": table,
        "accuracy": {
            "relationship_correct_pct": accuracy["relationship_correct_pct"],
            "state_correct_pct": accuracy["state_correct_pct"],
        },
        "dominant_mode": dominant_mode,
        "dominant_cause": dominant_cause,
        "decision_signal": decision_signal,
    }


# ---------------------------------------------------------------------------
# Golden case promotion
# ---------------------------------------------------------------------------


def promote_to_golden(case_ids: List[str]) -> List[str]:
    """Promote audited cases to golden set for regression testing.

    Reads case file + judgment file, merges into golden case format.
    Returns list of promoted case IDs.
    """
    GOLDEN_DIR.mkdir(parents=True, exist_ok=True)

    promoted = []
    for case_id in case_ids:
        case_path = CASES_DIR / f"{case_id}.json"
        judgment_path = JUDGMENTS_DIR / f"{case_id}.json"

        if not case_path.exists():
            logger.warning(f"Case file not found: {case_path}")
            continue
        if not judgment_path.exists():
            logger.warning(f"Judgment file not found: {judgment_path}")
            continue

        with open(case_path) as f:
            case = json.load(f)
        with open(judgment_path) as f:
            judgment = json.load(f)

        # Validate judgment is complete
        if not is_judgment_complete(judgment):
            logger.warning(f"Judgment for {case_id} is incomplete, skipping")
            continue

        # Build expected outputs from judgment
        expected_elements = _build_expected_from_judgment(judgment)

        golden = {**case, "expected": {"elements": expected_elements}}

        golden_path = GOLDEN_DIR / f"{case_id}.json"
        with open(golden_path, "w", encoding="utf-8") as f:
            json.dump(golden, f, indent=2, default=str)

        promoted.append(case_id)
        logger.info(f"Promoted {case_id} to golden set")

    return promoted


def _build_expected_from_judgment(judgment: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Derive expected outputs from a completed judgment."""
    # Group by element_id
    elements_map: Dict[str, Dict[str, Any]] = {}

    # Process state judgments to get expected states
    for sj in judgment.get("state_judgments", []):
        eid = sj["element_id"]
        if eid not in elements_map:
            elements_map[eid] = {
                "element_id": eid,
                "expected_state": None,
                "expected_refs": [],
            }

        if sj.get("correct"):
            elements_map[eid]["expected_state"] = sj["mapper_state"]
        elif sj.get("expected_state"):
            elements_map[eid]["expected_state"] = sj["expected_state"]
        else:
            elements_map[eid]["expected_state"] = sj["mapper_state"]

    # Process ref judgments to get expected relationships
    for rj in judgment.get("ref_judgments", []):
        eid = rj["element_id"]
        if eid not in elements_map:
            elements_map[eid] = {
                "element_id": eid,
                "expected_state": "unresolved",
                "expected_refs": [],
            }

        if rj.get("correct"):
            rel = rj["mapper_relationship"]
        elif rj.get("expected_relationship"):
            rel = rj["expected_relationship"]
        else:
            rel = rj["mapper_relationship"]

        elements_map[eid]["expected_refs"].append(
            {
                "evidence_id": rj["evidence_id"],
                "expected_relationship": rel,
            }
        )

    # Process missing_refs
    for mr in judgment.get("missing_refs", []):
        eid = mr["element_id"]
        if eid not in elements_map:
            elements_map[eid] = {
                "element_id": eid,
                "expected_state": "unresolved",
                "expected_refs": [],
            }
        elements_map[eid]["expected_refs"].append(
            {
                "evidence_id": mr["evidence_id"],
                "expected_relationship": mr.get("expected_relationship", "context"),
            }
        )

    # Sort by element_id for consistency
    return sorted(elements_map.values(), key=lambda x: x["element_id"])


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description="Validate, summarise, and promote mapping audit judgments"
    )
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument(
        "--validate", action="store_true", help="Validate judgment files"
    )
    action.add_argument(
        "--summarise", action="store_true", help="Summarise completed judgments"
    )
    action.add_argument(
        "--promote", nargs="+", metavar="CASE_ID", help="Promote cases to golden set"
    )
    parser.add_argument("--verbose", action="store_true", help="Enable debug logging")

    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO, format="%(message)s")

    if args.validate:
        judgment_files = sorted(JUDGMENTS_DIR.glob("case-*.json"))
        if not judgment_files:
            print("No judgment files found.")
            return

        total_errors = 0
        for jf in judgment_files:
            with open(jf) as f:
                judgment = json.load(f)

            complete = is_judgment_complete(judgment)
            errors = validate_judgment(judgment)

            status = "COMPLETE" if complete else "INCOMPLETE"
            case_id = judgment.get("case_id", jf.stem)

            if errors:
                print(f"  {case_id}: {status}, {len(errors)} issues")
                for e in errors:
                    print(f"    - {e}")
                total_errors += len(errors)
            else:
                print(f"  {case_id}: {status}, valid")

        print(
            f"\n{len(judgment_files)} judgment files checked, {total_errors} issues found"
        )

    elif args.summarise:
        judgment_files = sorted(JUDGMENTS_DIR.glob("case-*.json"))
        completed = []
        for jf in judgment_files:
            with open(jf) as f:
                judgment = json.load(f)
            if is_judgment_complete(judgment):
                completed.append(judgment)

        if not completed:
            print("No completed judgments found.")
            return

        summary = build_summary(completed)

        AUDIT_DIR.mkdir(parents=True, exist_ok=True)
        with open(SUMMARY_PATH, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, default=str)

        print(f"Summary ({summary['cases_reviewed']} cases):")
        print(f"  Refs reviewed: {summary['refs_reviewed']}")
        print(f"  States reviewed: {summary['states_reviewed']}")
        print(
            f"  Relationship accuracy: {summary['accuracy']['relationship_correct_pct']:.0%}"
        )
        print(f"  State accuracy: {summary['accuracy']['state_correct_pct']:.0%}")
        print(f"\nFailure mode table:")
        for mode, counts in summary["failure_mode_table"].items():
            total = counts["window_sufficient"] + counts["window_insufficient"]
            if total > 0:
                print(
                    f"  {mode}: {total} "
                    f"(ws={counts['window_sufficient']}, wi={counts['window_insufficient']})"
                )
        print(f"\nDominant mode: {summary['dominant_mode']}")
        print(f"Dominant cause: {summary['dominant_cause']}")
        print(f"Decision signal: {summary['decision_signal']}")
        print(f"\nWritten to {SUMMARY_PATH}")

    elif args.promote:
        promoted = promote_to_golden(args.promote)
        print(f"Promoted {len(promoted)} cases to golden set at {GOLDEN_DIR}")
        for cid in promoted:
            print(f"  {cid}")


if __name__ == "__main__":
    main()
