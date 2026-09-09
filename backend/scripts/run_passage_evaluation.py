"""Bounded 2x2 evaluation on frozen sources using existing pipeline methods.

Dry-run prepares inputs only. --execute authorises model API requests for this
run, never application writes, live retrieval or persistent setting changes.
"""

import argparse
import asyncio
import copy
import hashlib
import json
import logging
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
# Logging is disabled in main() (never spill provider URLs/API credentials),
# NOT at import: test_passage_factorial_evaluation imports this module, and a
# module-level logging.disable() silenced every later test in the process
# (the Sentry behavioural tests went red whole-suite only). Found 2026-09-09.

from app.core.config import settings
from app.pipeline.claim_map_analyzer import ClaimMapAnalyzer
from app.pipeline.evidence_classifier import EvidenceClassifier
from app.pipeline.evidence_distiller import EvidenceDistiller
from app.services.text_provenance import (
    capture_text_provenance,
    finalize_distilled_payload,
)


def dump(path, value):
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False, default=str), encoding="utf-8"
    )


def sha(text):
    return hashlib.sha256(text.encode()).hexdigest()


class EvaluationStop(BaseException):
    pass


def prepare(pack, extraction):
    spec = json.loads((pack / "spec.json").read_text(encoding="utf-8"))
    manifest = json.loads((pack / "manifest.json").read_text(encoding="utf-8"))
    sources = {}
    for source in manifest["sources"]:
        if source["status"] != "captured":
            continue
        raw = (pack / source["file"]).read_bytes()
        if hashlib.sha256(raw).hexdigest() != source["sha256"]:
            raise ValueError("Captured source hash mismatch")
        sources[source["id"]] = source
    report = json.loads((extraction / "report.json").read_text(encoding="utf-8"))
    texts = {}
    for row in report["sources"]:
        if "arms" not in row:
            continue
        for arm in ("legacy", "structured"):
            text = (extraction / f"{row['id']}-{arm}.txt").read_text(encoding="utf-8")
            if (
                sha(text) != row["arms"][arm]["sha256"]
                or row["source_sha256"] != sources[row["id"]]["sha256"]
            ):
                raise ValueError("Extraction hash mismatch")
            texts[row["id"], arm] = text
    cases = []
    for case in spec["cases"]:
        cases.append(
            {
                "id": case["id"],
                "claim": case["claim"],
                "elements": case["elements"],
                "missing": [sid for sid in case["source_ids"] if sid not in sources],
                "sources": [
                    {
                        "id": sid,
                        "url": sources[sid]["url"],
                        "title": sources[sid]["title"],
                        "legacy": texts[sid, "legacy"],
                        "structured": texts[sid, "structured"],
                    }
                    for sid in case["source_ids"]
                    if sid in sources
                ],
            }
        )
    synthetic = json.loads(
        (pack / "prepared/synthetic_inputs.json").read_text(encoding="utf-8")
    )
    for case in synthetic["cases"]:
        cases.append(
            {
                "id": case["case_id"],
                "claim": case["claim"],
                "elements": case["elements"],
                "missing": [],
                "sources": [
                    {
                        "id": s["id"],
                        "url": s["url"],
                        "title": "Fictional test source",
                        "legacy": s["text"],
                        "structured": s["text"],
                    }
                    for s in case["sources"]
                ],
            }
        )
    return cases


async def evaluate(args):
    import httpx

    cases = prepare(args.pack, args.extraction)
    if args.cases:
        wanted = set(args.cases.split(","))
        cases = [case for case in cases if case["id"] in wanted]
        if {c["id"] for c in cases} != wanted:
            raise ValueError("Unknown case")
    args.output.mkdir(parents=True, exist_ok=False)
    dump(args.output / "inputs.json", cases)
    plan = {
        "cases": len(cases),
        "arms_per_case": 4,
        "inputs_sha256": sha((args.output / "inputs.json").read_text(encoding="utf-8")),
        "models": {
            key: getattr(settings, key)
            for key in (
                "GOOGLE_LLM_MODEL",
                "MAPPING_GOOGLE_MODEL",
                "DISTIL_MODEL",
                "ANALYZER_MODEL",
            )
        },
        "max_http_requests": args.max_requests,
        "max_request_characters": args.max_characters,
        "classification": "once on shared legacy source snippets; frozen for all arms",
        "scope": "controlled fixed-element mapping; not live retrieval/decomposition/end-to-end evaluation",
        "status": "prepared",
        "requests": 0,
    }
    dump(args.output / "plan.json", plan)
    print(json.dumps(plan), flush=True)
    if not args.execute:
        return
    original_post = httpx.AsyncClient.post
    original_flags = (
        settings.ENABLE_STRUCTURED_EXTRACTION,
        settings.ENABLE_PASSAGE_MAPPING,
    )
    # External error monitoring must not receive test prompts or provider errors.
    original_sentry = settings.SENTRY_DSN
    settings.SENTRY_DSN = ""
    count, characters = 0, 0
    active = "classification"
    results = []

    async def traced_post(client, url, **kwargs):
        nonlocal count, characters
        if (args.output / "STOP").exists():
            raise EvaluationStop("Operator stopped this evaluation between requests")
        parsed = urlparse(str(url))
        if parsed.hostname not in {
            "generativelanguage.googleapis.com",
            "api.openai.com",
        }:
            raise EvaluationStop("Unexpected network destination")
        body = kwargs.get("json", {})
        size = len(json.dumps(body))
        if count >= args.max_requests or characters + size > args.max_characters:
            raise EvaluationStop("Request budget exhausted")
        count += 1
        characters += size
        request_id = count
        plan.update(status="running", requests=count, request_characters=characters)
        dump(args.output / "plan.json", plan)
        record = {
            "stage": active,
            "provider": parsed.hostname,
            "path": parsed.path,
            "request": body,
            "request_sha256": sha(json.dumps(body, sort_keys=True)),
        }
        started = time.perf_counter()
        try:
            response = await original_post(client, url, **kwargs)
            record["status"] = response.status_code
            if response.status_code >= 400:
                raise EvaluationStop(
                    f"Provider HTTP {response.status_code}; no automatic retry or model substitution"
                )
            record["response"] = response.json()
            return response
        except httpx.HTTPError as error:
            raise EvaluationStop(f"Provider transport error: {type(error).__name__}")
        finally:
            record["seconds"] = time.perf_counter() - started
            dump(args.output / f"request-{request_id:03d}.json", record)

    httpx.AsyncClient.post = traced_post
    try:
        shared = {}
        for case in cases:
            for source in case["sources"]:
                key = sha(source["url"] + source["legacy"])
                source["classification_key"] = key
                shared.setdefault(
                    key,
                    {
                        "evidence_id": key,
                        "url": source["url"],
                        "title": source["title"],
                        "source": urlparse(source["url"]).hostname,
                        "text": source["legacy"][:1000],
                        "snippet": source["legacy"][:1000],
                    },
                )
        if args.classifications:
            frozen = json.loads(args.classifications.read_text(encoding="utf-8"))
            for key, item in shared.items():
                if key not in frozen or any(
                    frozen[key][field] != item[field]
                    for field in ("url", "snippet", "title")
                ):
                    raise ValueError("Frozen classification input mismatch")
            shared = {key: frozen[key] for key in shared}
            plan["classification_source"] = str(args.classifications)
        else:
            classifier = EvidenceClassifier()
            await classifier.classify_batch(list(shared.values()))
        dump(args.output / "classifications.json", shared)
        for index, case in enumerate(cases):
            arms = [(False, False), (True, False), (False, True), (True, True)]
            if index % 2:
                arms.reverse()
            for structured, passage in arms:
                active = f"{case['id']}-s{int(structured)}-p{int(passage)}"
                settings.ENABLE_STRUCTURED_EXTRACTION = structured
                settings.ENABLE_PASSAGE_MAPPING = passage
                evidence = []
                for source in case["sources"]:
                    item = copy.deepcopy(shared[source["classification_key"]])
                    text = source["structured" if structured else "legacy"]
                    item.update(
                        evidence_id=source["id"],
                        text=text[:1000],
                        snippet=text[:1000],
                        _full_text=text,
                        content_basis="full",
                    )
                    capture_text_provenance(item, case["claim"], case["elements"])
                    evidence.append(item)
                cm = {
                    "claim_id": case["id"],
                    "normalised_claim": case["claim"],
                    "elements": [
                        {**copy.deepcopy(e), "evidence_refs": [], "state": None}
                        for e in case["elements"]
                    ],
                    "metadata": {},
                }
                started = time.perf_counter()
                distiller = EvidenceDistiller()
                if passage:
                    await distiller.distil_evidence_for_claim(
                        case["claim"], evidence, case["elements"]
                    )
                else:
                    await distiller.distil_evidence_for_claim(case["claim"], evidence)
                for item in evidence:
                    finalize_distilled_payload(item)
                analyzer = ClaimMapAnalyzer()
                await analyzer.map_evidence_to_elements(cm, evidence)
                result = {
                    "case_id": case["id"],
                    "structured": structured,
                    "passage": passage,
                    "seconds": time.perf_counter() - started,
                    "claim_map": cm,
                    "evidence": evidence,
                    "missing_sources": case["missing"],
                    "mapping_usage": analyzer.get_token_usage(),
                    "distillation_usage": distiller.get_token_usage(),
                    "models_used": analyzer.get_models_used(),
                    "fallbacks": analyzer.get_fallback_status(),
                }
                dump(args.output / f"{active}.json", result)
                results.append(
                    {
                        key: result[key]
                        for key in (
                            "case_id",
                            "structured",
                            "passage",
                            "seconds",
                            "mapping_usage",
                            "distillation_usage",
                        )
                    }
                )
                dump(args.output / "progress.json", results)
                print(active, "completed", flush=True)
        plan["status"] = "completed"
    except EvaluationStop as error:
        plan["status"] = "stopped"
        plan["reason"] = str(error)
        print(plan["reason"], flush=True)
    except BaseException as error:
        plan["status"] = "error"
        plan["reason"] = type(error).__name__
        raise
    finally:
        httpx.AsyncClient.post = original_post
        settings.ENABLE_STRUCTURED_EXTRACTION, settings.ENABLE_PASSAGE_MAPPING = (
            original_flags
        )
        settings.SENTRY_DSN = original_sentry
        plan.update(
            requests=count, request_characters=characters, completed_arms=len(results)
        )
        dump(args.output / "plan.json", plan)


if __name__ == "__main__":
    logging.disable(logging.CRITICAL)  # never spill provider URLs/API credentials
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pack", type=Path, required=True)
    parser.add_argument("--extraction", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cases")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--classifications", type=Path)
    parser.add_argument("--max-requests", type=int, default=180)
    parser.add_argument("--max-characters", type=int, default=1500000)
    asyncio.run(evaluate(parser.parse_args()))
