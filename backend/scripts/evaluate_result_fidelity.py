"""Bounded, opt-in paid evaluation on frozen sources; never activates settings globally."""

import argparse
import asyncio
import copy
import hashlib
import json
import logging
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "backend/tests/evaluation/passage_quality"


def save(path, value):
    path.write_text(json.dumps(value, indent=2, default=str) + "\n", encoding="utf-8")


def result_cases():
    frozen = json.loads((FIXTURES / "result_fragment_failure.json").read_text())
    endpoint = json.loads(
        (FIXTURES / "unestablished_endpoint_failure.json").read_text()
    )
    qualitative = json.loads(
        (FIXTURES / "qualitative_effect_failures.json").read_text(encoding="utf-8")
    )
    claim = "In the FIELD trial, treatment N reduced hospital admissions by 30% relative to placebo in adults."
    return [
        # 2026-09-09 integrated failure pair: quantitative support on
        # qualitative / different-endpoint text. Expected context.
        *[
            {
                "id": "qualitative_effect_" + e["evidence_id"].split("-")[1][:6],
                "claim": qualitative["claim"],
                "evidence": e,
                "initial": "supports",
                "expected": qualitative["expected"],
            }
            for e in qualitative["evidence"]
        ],
        {
            "id": "unestablished_endpoint",
            "claim": endpoint["claim"],
            "evidence": endpoint["evidence"],
            "initial": "challenges",
            "expected": "context",
        },
        {
            "id": "captured_pdf_fragment",
            "claim": frozen["claim"],
            "evidence": frozen["evidence"],
            "initial": "supports",
            "expected": "context",
        },
        *[
            {
                "id": name,
                "claim": claim,
                "initial": initial,
                "expected": expected,
                "evidence": {
                    "evidence_id": "ev-" + name,
                    "title": "FIELD trial",
                    "url": "https://example.org/" + name,
                    "snippet": text,
                    "content_basis": "snippet",
                    "tier": "primary",
                    "evidence_type": "academic",
                },
            }
            for name, text, initial, expected in [
                (
                    "equivalent_measure",
                    "The FIELD randomized adult trial reported a hospital admission risk ratio of 0.70 for N versus placebo, a 30% relative reduction.",
                    "supports",
                    "supports",
                ),
                (
                    "null_result",
                    "The FIELD randomized adult trial reported identical hospital admission rates with N and placebo, with narrow intervals excluding a 30% relative reduction.",
                    "challenges",
                    "challenges",
                ),
                (
                    "planned_result",
                    "The FIELD adult trial randomly assigned N or placebo and was designed to detect a 30% relative reduction in hospital admissions. Results are not reported here.",
                    "supports",
                    "context",
                ),
                (
                    "wrong_measure",
                    "The FIELD adult trial reported a 30 percentage point absolute reduction in hospital admissions with N versus placebo; the relative reduction was 50%.",
                    "supports",
                    "context",
                ),
                (
                    "background_result",
                    "This review reports that the FIELD randomized adult trial observed a 30% relative reduction in hospital admissions with N versus placebo. This is a citation of FIELD, not a new replication.",
                    "supports",
                    "supports",
                ),
            ]
        ],
    ]


async def run(output, case_ids=None):
    from app.core.config import settings
    from app.pipeline.claim_map_analyzer import ClaimMapAnalyzer
    from app.services.relationship_scope_review import review_relationship_scope

    assert not settings.ENABLE_PASSAGE_MAPPING, "Start from the disabled default."
    assert not output.exists(), "Use a fresh output directory; preserve prior results."
    output.mkdir(parents=True)
    broad = json.loads((FIXTURES / "broader_scope_results.json").read_text())[
        "protocol"
    ]["cases"]
    focused = result_cases()
    if case_ids:
        known = {c["id"] for c in [*broad, *focused]}
        if set(case_ids) - known:
            raise ValueError("Unknown evaluation case")
        broad = [c for c in broad if c["id"] in case_ids]
        focused = [c for c in focused if c["id"] in case_ids]
    protocol = {
        "broad_cases": broad,
        "result_cases": focused,
        "repeats": 2,
        "scope": "Frozen broader mapping repeats and isolated result-review controls; no retrieval, deployment or human benchmark.",
        "limits": "120 seconds per case; stop on error; no automatic retries.",
        "source_sha256": {
            p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in [
                FIXTURES / "broader_scope_results.json",
                FIXTURES / "result_fragment_failure.json",
                FIXTURES / "unestablished_endpoint_failure.json",
                FIXTURES / "qualitative_effect_failures.json",
            ]
        },
    }
    save(output / "protocol.json", protocol)
    settings.ENABLE_PASSAGE_MAPPING = True
    results = []
    try:
        for repeat in range(2):
            for case in [*broad, *focused]:
                cm = {
                    "claim_id": case["id"],
                    "normalised_claim": case["claim"],
                    "claim_type": "empirical",
                    "metadata": {},
                    "elements": [
                        {
                            "element_id": "e1",
                            "description": case["claim"],
                            "evidence_refs": [],
                            "state": None,
                        }
                    ],
                }
                full_mapping = "sources" in case
                if full_mapping:
                    evidence = [
                        {
                            "evidence_id": "ev-" + sid,
                            "title": title,
                            "url": "https://example.org/" + case["id"] + "/" + sid,
                            "snippet": text,
                            "text": text,
                            "content_basis": "snippet",
                            "tier": "primary",
                            "evidence_type": "academic",
                        }
                        for sid, title, text, _ in case["sources"]
                    ]
                    expected = {
                        "ev-" + sid: label for sid, _, _, label in case["sources"]
                    }
                else:
                    evidence = [copy.deepcopy(case["evidence"])]
                    expected = {evidence[0]["evidence_id"]: case["expected"]}
                    cm["elements"][0]["evidence_refs"] = [
                        {
                            "evidence_id": evidence[0]["evidence_id"],
                            "relationship": case["initial"],
                            "reasoning": "Prior mapping under review.",
                        }
                    ]
                before = copy.deepcopy(evidence)
                analyzer = ClaimMapAnalyzer()
                responses = []
                original = analyzer._call_llm

                async def capture(*args, **kwargs):
                    response = await original(*args, **kwargs)
                    responses.append(
                        {"label": kwargs.get("label"), "response": response}
                    )
                    return response

                analyzer._call_llm = capture
                start = time.monotonic()
                work = (
                    analyzer.map_evidence_to_elements(cm, evidence)
                    if full_mapping
                    else review_relationship_scope(analyzer, cm, evidence)
                )
                await asyncio.wait_for(work, timeout=120)
                refs = {
                    r["evidence_id"]: r["relationship"]
                    for r in cm["elements"][0]["evidence_refs"]
                }
                checks = [
                    {
                        "id": eid,
                        "expected": label,
                        "actual": refs.get(eid),
                        "pass": refs.get(eid) == label,
                    }
                    for eid, label in expected.items()
                ]
                results.append(
                    {
                        "case": case["id"],
                        "repeat": repeat,
                        "seconds": time.monotonic() - start,
                        "checks": checks,
                        "sources_preserved": before == evidence,
                        "map": cm,
                        "responses": responses,
                    }
                )
                save(output / "results.json", results)
                if not responses or any(r["response"] is None for r in responses):
                    raise RuntimeError(
                        "Missing model response; stop rather than score fallback output as model quality."
                    )
                print(
                    case["id"],
                    repeat,
                    sum(c["pass"] for c in checks),
                    "/",
                    len(checks),
                    flush=True,
                )
    finally:
        settings.ENABLE_PASSAGE_MAPPING = False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--case", action="append", dest="case_ids")
    args = parser.parse_args()
    logging.disable(logging.CRITICAL)
    asyncio.run(run(args.output.resolve(), args.case_ids))
