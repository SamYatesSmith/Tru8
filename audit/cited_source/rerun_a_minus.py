"""A− re-grade of #7, #8, #13 on the LOCAL pipeline (2026-10-06), after S6 fixes,
the mapping date context and the shared-total decomposition rule. Gap note ON.

PAID (~10-15p each), founder-approved 2026-10-06. Full pipeline, real
retrieval and models, LOCAL database only (asserted). Inputs are the A− H3
records whose pooled copies name the missing original (#1, #6, #15, #17).
Saves each owner payload and prints the cited-source receipts and notes.

Run from backend/ (Docker up):  python ../audit/cited_source/live_checks.py
"""

import asyncio
import json
import logging
import os
import sys
import time

sys.path.insert(0, ".")

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(HERE, "..", "a_minus", "2026-10-06_s6_rerun", "payloads")
CLAIMS = [
    ("07_cook_poll", "Cook Political Report, GS Strategy Group and New River Strategies surveyed 1,052 likely voters from September 8-11, 2026 across the 37 House districts Cook rates as competitive; the generic ballot in them is Democrats 49, Republicans 47, and Trump's job approval is 42-58."),
    ("08_galway_reefs", "A team from University of Galway, with colleagues from France, placed 23 3D-printed reef structures on the seabed of the Porcupine Bank 200km off the Kerry coast, and in the Bay of Biscay off France."),
    ("13_heatwaves_pollution", "Europe's recent heatwaves are being caused by declining air pollution rather than climate change"),
]


async def main():
    from sqlalchemy import select
    from sqlalchemy.engine import make_url

    from app.core.config import settings

    assert make_url(settings.DATABASE_URL).host in {"localhost", "127.0.0.1"}
    settings.ENABLE_CITED_SOURCE_GAP_NOTE = True

    from app.api.v1.response_builder import build_check_response
    from app.core.cost_constants import build_cost_telemetry
    from app.core.database import async_session
    from app.models import Check, Claim
    from app.pipeline.progress import ProgressReporter
    from app.pipeline.runner import (
        run_pipeline,
        run_pipeline_phase2,
        save_check_results_async,
    )
    from scripts.replay_bench.runner import _create_check, _ensure_bench_user

    os.makedirs(OUT_DIR, exist_ok=True)
    for name, text in CLAIMS:
        data = {
            "input_type": "text",
            "content": text,
            "url": None,
            "file_path": None,
            "user_query": None,
        }
        async with async_session() as session:
            user = await _ensure_bench_user(session)
            check = await _create_check(session, user.id, data)
            cid, uid = check.id, user.id
        start = time.monotonic()
        result = await asyncio.wait_for(
            run_pipeline(cid, uid, data, ProgressReporter(cid)), timeout=600
        )
        if result is None:  # paused for selection: select every claim
            async with async_session() as session:
                rows = (
                    (await session.execute(select(Claim).where(Claim.check_id == cid)))
                    .scalars()
                    .all()
                )
                for c in rows:
                    c.is_selected = True
                ck = (
                    await session.execute(select(Check).where(Check.id == cid))
                ).scalar_one()
                ck.selected_claims_count = len(rows)
                await session.commit()
            result = await asyncio.wait_for(
                run_pipeline_phase2(
                    check_id=cid,
                    user_id=uid,
                    input_data={**data, "content": None},
                    progress_reporter=ProgressReporter(cid),
                ),
                timeout=600,
            )
        async with async_session() as session:
            await save_check_results_async(cid, result, session)
            await session.commit()
            owner = await build_check_response(cid, uid, session)
        with open(os.path.join(OUT_DIR, f"{name}.json"), "w", encoding="utf-8") as f:
            json.dump(owner, f, ensure_ascii=False, indent=1, default=str)
        telemetry = build_cost_telemetry(result)
        timings = telemetry["timing"]["stage_timings_s"]
        print(
            f"== {name} {cid} {round(time.monotonic() - start)}s "
            f"cost ${telemetry['estimated_cost_usd'].get('total_partial')} "
            f"cited_source {timings.get('cited_source')}s analyze {timings.get('analyze')}s",
            flush=True,
        )
        for claim in owner.get("claims") or []:
            cm = claim.get("claimMap") or {}
            cs = (cm.get("metadata") or {}).get("citedSources") or (cm.get("metadata") or {}).get("cited_sources") or {}
            print(f"  claim: {(claim.get('text') or '')[:90]}")
            print(f"  totals {cs.get('totals')}")
            for n in cs.get("names") or []:
                print(f"   name [{n.get('status')}] {n.get('name')} <- {(n.get('cue') or '')[:100]!r}")
            print(f"  missing {json.dumps(cs.get('missing'), ensure_ascii=False) if 'missing' in cs else '(no key)'}", flush=True)

if __name__ == "__main__":
    logging.disable(logging.CRITICAL)
    asyncio.run(main())
