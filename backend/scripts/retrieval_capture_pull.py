"""Read-only artefact pull for the retrieval-quality investigation (F-R1/F-R2).

Pulls everything check TRU-C051-3024 (uuid prefix c0513024) recorded about its
own retrieval: claims + claim_map elements, shown Evidence rows (with
llm_relevance_score / rationale / tier / classification), RawEvidence filter
cascade receipts, provider_status, and the telemetry search block.

READ-ONLY: SELECT statements only. Scoped to the single check.

Run against production (Railway):
    cd backend && railway run --service Postgres python -m scripts.retrieval_capture_pull

Writes full JSON to scripts/.c051_capture_artefacts.json and prints a compact
summary to stdout.
"""

import asyncio
import json
import os
import sys
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

PREFIX = "c0513024"
OUT = Path(__file__).resolve().parent / ".c051_capture_artefacts.json"

CHECK_SQL = """
SELECT id, created_at, status, entry_mode, input_type, executed_tier,
       article_domain, article_secondary_domains, article_jurisdiction,
       article_classification_source,
       raw_sources_count, total_search_results,
       api_sources_used, api_call_count,
       provider_status,
       cost_telemetry
FROM "check"
WHERE replace(id::text, '-', '') LIKE :prefix
"""

CLAIMS_SQL = """
SELECT id, position, text, claim_type, time_reference, is_time_sensitive,
       temporal_markers, key_entities, subject_context, claim_map_input_hash,
       claim_map
FROM claim
WHERE check_id = :check_id
ORDER BY position
"""

EVIDENCE_SQL = """
SELECT claim_id, evidence_id, source, external_source_provider, url, title,
       left(snippet, 200)                AS snippet_head,
       published_date, date_basis,
       tier, evidence_type, classification_method,
       llm_relevance_score, llm_relevance_rationale,
       receipt_status, exclusion_reason, relevance_score,
       is_primary_source, primary_indicators, content_basis
FROM evidence
WHERE claim_id = ANY(:claim_ids)
ORDER BY claim_id, llm_relevance_score DESC NULLS LAST
"""

RAW_SQL = """
SELECT claim_position, source, external_source_provider, url,
       left(title, 140)                  AS title_head,
       published_date, relevance_score,
       is_included, filter_stage, filter_reason, tier, is_factcheck
FROM rawevidence
WHERE check_id = :check_id
ORDER BY claim_position, is_included DESC, filter_stage
"""


def _default(o):
    return str(o)


async def main() -> int:
    db_url = (
        os.environ.get("COST_DB_URL")
        or os.environ.get("DATABASE_PUBLIC_URL")
        or os.environ.get("DATABASE_URL")
        or ""
    )
    if not db_url:
        print("DATABASE_URL not configured", file=sys.stderr)
        return 2
    if db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

    engine = create_async_engine(db_url)
    try:
        async with engine.connect() as conn:
            check_rows = (
                (await conn.execute(text(CHECK_SQL), {"prefix": f"{PREFIX}%"}))
                .mappings()
                .all()
            )
            if not check_rows:
                print(f"No check found with id prefix {PREFIX}")
                return 1
            if len(check_rows) > 1:
                print(f"WARNING: {len(check_rows)} checks match prefix {PREFIX}")
            check = dict(check_rows[0])
            check_id = str(check["id"])

            claims = [
                dict(r)
                for r in (
                    await conn.execute(text(CLAIMS_SQL), {"check_id": check_id})
                ).mappings()
            ]
            claim_ids = [str(c["id"]) for c in claims]

            evidence = [
                dict(r)
                for r in (
                    await conn.execute(
                        text(
                            EVIDENCE_SQL.replace("ANY(:claim_ids)", "ANY(:claim_ids)")
                        ),
                        {"claim_ids": claim_ids},
                    )
                ).mappings()
            ]

            raw = [
                dict(r)
                for r in (
                    await conn.execute(text(RAW_SQL), {"check_id": check_id})
                ).mappings()
            ]
    finally:
        await engine.dispose()

    blob = {"check": check, "claims": claims, "evidence": evidence, "raw_evidence": raw}
    OUT.write_text(json.dumps(blob, indent=2, default=_default), encoding="utf-8")

    # ---- compact stdout summary ----
    print(f"check {check_id}  status={check['status']}  created={check['created_at']}")
    print(
        f"domain={check['article_domain']}  jurisdiction={check['article_jurisdiction']}  "
        f"raw_sources={check['raw_sources_count']}  total_search_results={check['total_search_results']}"
    )
    ps = check.get("provider_status") or {}
    if isinstance(ps, str):
        ps = json.loads(ps)
    print("\nprovider_status:")
    for name, st in sorted(ps.items()):
        print(f"  {name:<28} {st}")

    tel = check.get("cost_telemetry") or {}
    if isinstance(tel, str):
        tel = json.loads(tel)
    print("\ncost_telemetry.search:")
    print(json.dumps(tel.get("search"), indent=2, default=_default)[:1500])

    by_claim_ev: dict = {}
    for e in evidence:
        by_claim_ev.setdefault(str(e["claim_id"]), []).append(e)
    by_pos_raw: dict = {}
    for r in raw:
        by_pos_raw.setdefault(r["claim_position"], []).append(r)

    for c in claims:
        cid = str(c["id"])
        print(f"\n=== claim {c['position']}: {c['text'][:100]}")
        print(
            f"    type={c['claim_type']}  time_ref={c['time_reference']}  "
            f"time_sensitive={c['is_time_sensitive']}  markers={c['temporal_markers']}"
        )
        cm = c.get("claim_map") or {}
        if isinstance(cm, str):
            cm = json.loads(cm)
        print(f"    claim_map keys: {sorted(cm.keys()) if cm else None}")
        for el in (cm or {}).get("elements", []):
            refs = el.get("evidence_refs")
            if isinstance(refs, dict):
                refs_s = (
                    f"s/c/x={len(refs.get('supports', []))}/"
                    f"{len(refs.get('challenges', []))}/{len(refs.get('context', []))}"
                )
            elif isinstance(refs, list):
                stances: dict = {}
                for r in refs:
                    st = (
                        r.get("stance", r.get("relationship", "?"))
                        if isinstance(r, dict)
                        else "?"
                    )
                    stances[st] = stances.get(st, 0) + 1
                refs_s = f"refs={stances}"
            else:
                refs_s = f"refs={refs!r}"
            desc = el.get("description") or el.get("text") or ""
            print(
                f"    element {el.get('element_id', el.get('id', '?'))}: "
                f"state={el.get('state')}  {refs_s}  text={str(desc)[:100]}"
            )
        evs = by_claim_ev.get(cid, [])
        print(f"    shown evidence: {len(evs)}")
        for e in evs:
            print(
                f"      [{e['llm_relevance_score']}] {e['tier']}/{e['evidence_type']} "
                f"({e['classification_method']}) prov={e['external_source_provider']} "
                f"{e['source']} :: {str(e['title'])[:70]}"
            )
        pos = c["position"]
        raws = by_pos_raw.get(pos, [])
        agg: dict = {}
        for r in raws:
            k = (r["is_included"], r["filter_stage"], r["external_source_provider"])
            agg[k] = agg.get(k, 0) + 1
        print(
            f"    raw_evidence rows: {len(raws)}  (included/filter_stage/provider -> n)"
        )
        for k, n in sorted(agg.items(), key=lambda kv: str(kv[0])):
            print(f"      {k} -> {n}")

    print(f"\nFull JSON written to {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
