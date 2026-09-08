"""Offline evaluation preparation; never calls models or writes application data.

capture fetches public sources once; prepare reuses those exact saved bytes.
All expected behaviours live in the reviewer sheet, outside model inputs.
"""

import argparse
import hashlib
import json
import random
import subprocess
import sys
from datetime import datetime, timezone
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def digest(data):
    return hashlib.sha256(data).hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")


def synthetic_controls(seed=419):
    """Fictional values/dates for generality tests; never real-source edits."""
    rng = random.Random(seed)
    cases, review = [], []
    for index in range(4):
        old, new = rng.sample(range(10, 95), 2)
        changed = date(2020, 1, 1) + timedelta(days=rng.randrange(300, 2200))
        prior, target = changed - timedelta(days=30), changed + timedelta(days=5)
        for reversed_claim in (False, True):
            value = old if reversed_claim else new
            cid = f"synthetic-{index}-{'reversed' if reversed_claim else 'new'}"
            texts = [
                f"Fictional record keeper: the reservoir release setting was {old} units as of {prior}.",
                f"Fictional dated operational record: the setting changed to {new} units effective from {changed}, replacing {old} units.",
            ]
            guidance = (
                "Older record-keeper text must not override the explicit later change."
            )
            if index == 1:
                texts[1] = (
                    f"Page clock: {target}. The reservoir release setting is {new} units."
                )
                guidance = "The page clock cannot date the body claim; current applicability is unestablished."
            elif index == 2:
                texts[1] = (
                    f"As of {target}, the proposed {new}-unit setting is not effective from {changed}; the change has not occurred."
                )
                guidance = "Do not elide negation or infer that the proposed setting took effect."
            elif index == 3:
                texts[1] = (
                    f"As of {target}, a change to {new} units is planned for {target + timedelta(days=20)}; no change has occurred yet."
                )
                guidance = (
                    "A future plan does not establish the new value at the target date."
                )
            cases.append(
                {
                    "case_id": cid,
                    "synthetic": True,
                    "claim": f"The fictional reservoir release setting was {value} units on {target}.",
                    "elements": [
                        {
                            "element_id": "e1",
                            "description": f"The setting was {value} units on {target}.",
                        }
                    ],
                    "sources": [
                        {
                            "id": f"fiction-{i}",
                            "url": f"https://source-{i}.invalid",
                            "text": text,
                        }
                        for i, text in enumerate(texts)
                    ],
                }
            )
            review.append(
                {
                    "case_id": cid,
                    "review_guidance": guidance,
                    "quality_result": "not_run",
                }
            )
    return {"seed": seed, "cases": cases}, review


def capture(spec, output):
    import httpx
    from app.utils.browser_headers import browser_headers

    output.mkdir(parents=True, exist_ok=False)
    manifest = {
        "version": 1,
        "kind": "new_public_fetch_not_original_run",
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "sources": [],
    }
    with httpx.Client(
        timeout=25, follow_redirects=True, headers=browser_headers()
    ) as client:
        for source in spec["sources"]:
            row = dict(source)
            row["fetched_at"] = datetime.now(timezone.utc).isoformat()
            try:
                response = client.get(source["url"])
                data = response.content
                filename = source["id"] + ".html"
                (output / filename).write_bytes(data)
                row.update(
                    http_status=response.status_code,
                    final_url=str(response.url),
                    content_type=response.headers.get("content-type"),
                    encoding=response.encoding,
                    file=filename,
                    sha256=digest(data),
                    response_date=response.headers.get("date"),
                    last_modified=response.headers.get("last-modified"),
                )
                row["status"] = (
                    "captured" if response.status_code == 200 else "http_error"
                )
            except httpx.HTTPError as error:
                row.update(status="fetch_error", error=type(error).__name__)
            manifest["sources"].append(row)
            write_json(output / "manifest.json", manifest)
            print(source["id"], row["status"], row.get("http_status", ""))
    write_json(output / "spec.json", spec)


def prepare(pack):
    from app.services.evidence import EvidenceExtractor
    from app.services.text_provenance import capture_text_provenance

    manifest = json.loads((pack / "manifest.json").read_text(encoding="utf-8"))
    spec = json.loads((pack / "spec.json").read_text(encoding="utf-8"))
    output = pack / "prepared"
    output.mkdir(exist_ok=False)  # a new run must not silently replace frozen inputs
    # This extraction method is stateless; avoid constructing search/API clients.
    extractor = object.__new__(EvidenceExtractor)
    sources = {}
    extraction_report = []
    for source in manifest["sources"]:
        row = {"id": source["id"], "fetch_status": source["status"]}
        if source["status"] == "captured" and "html" in (
            source.get("content_type") or ""
        ):
            data = (pack / source["file"]).read_bytes()
            if digest(data) != source["sha256"]:
                raise ValueError(f"Source bytes changed: {source['id']}")
            html = data.decode(source.get("encoding") or "utf-8", errors="replace")
            text = extractor._extract_main_content(html, source["url"]) or ""
            blocked = any(
                marker in text[:500].lower() for marker in extractor._JUNK_TITLE_MARKERS
            )
            row.update(
                extraction_characters=len(text),
                extracted_sha256=digest(text.encode()),
                status=(
                    "blocked_or_empty" if blocked or len(text) < 200 else "extracted"
                ),
            )
            (output / (source["id"] + ".txt")).write_text(text, encoding="utf-8")
            if row["status"] == "extracted":
                sources[source["id"]] = {
                    "evidence_id": source["id"],
                    "url": source["url"],
                    "title": source["title"],
                    "text": text[:1000],
                    "snippet": text[:1000],
                    "_full_text": text,
                    "content_basis": "full",
                }
        else:
            row["status"] = "unavailable"
        extraction_report.append(row)
    inputs, review = [], []
    for case in spec["cases"]:
        evidence = [dict(sources[sid]) for sid in case["source_ids"] if sid in sources]
        for item in evidence:
            capture_text_provenance(item, case["claim"], case["elements"])
        missing = [sid for sid in case["source_ids"] if sid not in sources]
        inputs.append(
            {
                "case_id": case["id"],
                "claim": case["claim"],
                "elements": case["elements"],
                "evidence": evidence,
                "missing_source_ids": missing,
            }
        )
        review.append(
            {
                "case_id": case["id"],
                "review_guidance": case["review_guidance"],
                "source_availability": "incomplete" if missing else "available",
                "missing_source_ids": missing,
                "reviewer": None,
                "legacy": None,
                "passage_aware": None,
                "quality_result": "not_run",
                "checks": {
                    key: None
                    for key in (
                        "decisive_passage_retained",
                        "missed_relationships",
                        "false_directional_additions",
                        "quote_exactness",
                        "quote_entailment",
                        "temporal_applicability",
                        "population_endpoint_effect_scope",
                        "duplicate_study_independence",
                        "frontend_basis_access",
                        "latency_seconds",
                        "input_tokens",
                        "output_tokens",
                    )
                },
            }
        )
    write_json(output / "inputs.json", inputs)
    write_json(output / "review.json", review)
    write_json(output / "extraction_report.json", extraction_report)
    controls, controls_review = synthetic_controls()
    write_json(output / "synthetic_inputs.json", controls)
    write_json(output / "synthetic_review.json", controls_review)
    write_json(
        output / "run_contract.json",
        {
            "pipeline_commit": subprocess.check_output(
                ["git", "rev-parse", "HEAD"], text=True
            ).strip(),
            "inputs_sha256": digest((output / "inputs.json").read_bytes()),
            "arms": [
                {"label": "legacy", "ENABLE_PASSAGE_MAPPING": False},
                {"label": "passage_aware", "ENABLE_PASSAGE_MAPPING": True},
            ],
            "model_policy": "same configured models and source pool in both arms",
            "model_execution": "not_run",
            "retrieval_during_evaluation": False,
            "classification": "not_run; classify once and freeze shared results before model comparison",
            "review_guidance_must_not_be_model_input": True,
        },
    )
    print(json.dumps({"cases": len(inputs), "sources": extraction_report}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["capture", "prepare"])
    parser.add_argument("--pack", type=Path, required=True)
    parser.add_argument("--spec", type=Path)
    args = parser.parse_args()
    if args.mode == "capture":
        if not args.spec:
            parser.error("capture requires --spec")
        capture(json.loads(args.spec.read_text(encoding="utf-8")), args.pack)
    else:
        prepare(args.pack)
