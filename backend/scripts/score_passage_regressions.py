"""Check manually reviewed, fixed-source expectations; never a general accuracy score.

This is an offline rollout prerequisite, not a production relationship rule.
Missing cases and missing positive controls fail closed. Expectations are never
passed to a model. Exit 1 means at least one checked expectation failed.
"""

import argparse
import hashlib
import json
from pathlib import Path


def input_signature(result):
    """Bind the review to its claim, element wording and captured source versions."""
    data = {
        "claim": result["claim_map"]["normalised_claim"],
        "elements": sorted(
            (e["element_id"], e["description"]) for e in result["claim_map"]["elements"]
        ),
        "sources": sorted(
            (e["evidence_id"], e["url"], e["text_provenance"]["extraction_sha256"])
            for e in result["evidence"]
        ),
    }
    return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()


def assess(result, checks):
    elements = result.get("claim_map", {}).get("elements", [])
    outcomes = []
    for check in checks:
        matches = [e for e in elements if e.get("element_id") == check["element"]]
        if len(matches) != 1:
            outcomes.append(
                {
                    "check": check["id"],
                    "passed": False,
                    "reason": "missing or duplicate element",
                }
            )
            continue
        refs = matches[0].get("evidence_refs", [])
        observed = [
            r.get("relationship")
            for r in refs
            if check["source"] == "*" or r.get("evidence_id") == check["source"]
        ]
        passed = all(r not in check.get("forbid", []) for r in observed) and all(
            r in observed for r in check.get("require", [])
        )
        outcomes.append({"check": check["id"], "passed": passed, "observed": observed})
    return outcomes


def score(run, expectations):
    rows = []
    for case, checks in expectations["cases"].items():
        for structured, passage in ((0, 0), (1, 0), (0, 1), (1, 1)):
            path = run / f"{case}-s{structured}-p{passage}.json"
            row = {
                "case": case,
                "structured": bool(structured),
                "passage": bool(passage),
            }
            try:
                raw = path.read_bytes()
                result = json.loads(raw)
                if (
                    result["case_id"] != case
                    or result["structured"] is not bool(structured)
                    or result["passage"] is not bool(passage)
                ):
                    raise ValueError("result identity mismatch")
                row["sha256"] = hashlib.sha256(raw).hexdigest()
                expected_input = expectations["input_signatures"][case][str(structured)]
                if input_signature(result) != expected_input:
                    raise ValueError(
                        "review expectations do not match source/element versions"
                    )
                row["checks"] = assess(result, checks)
                row["passed"] = bool(checks) and all(c["passed"] for c in row["checks"])
            except (OSError, ValueError, KeyError, TypeError) as error:
                row.update(passed=False, error=str(error))
            rows.append(row)
    return {
        "scope": "Targeted, manually reviewed fixed-source regressions; not overall accuracy.",
        "expectations_version": expectations["version"],
        "passed": all(row["passed"] for row in rows) and bool(rows),
        "combined_arm_passed": all(
            row["passed"] for row in rows if row["structured"] and row["passage"]
        )
        and bool(rows),
        "rows": rows,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--expectations", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    raw = args.expectations.read_bytes()
    report = score(args.run, json.loads(raw))
    report["expectations_sha256"] = hashlib.sha256(raw).hexdigest()
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("passed", "combined_arm_passed")}))
    raise SystemExit(0 if report["combined_arm_passed"] else 1)
