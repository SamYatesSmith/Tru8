"""Four LOCAL live checks with the cited-source GAP NOTE on (design §17 next step).

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
OUT_DIR = os.path.join(HERE, "live_checks")
CLAIMS = [
    ("h3_01_reform_72m", "Reform UK received £72 million in the space of one weekend, consisting of £36 million from Ben Delo and £36 million from Christopher Harborne."),
    ("h3_06_trump_trades", "Donald Trump has made almost 28,700 trades of securities with a total value of $898 million to $2.87 billion since 2025."),
    ("h3_15_nhs_app_triage", "AI triage through the NHS App reduced the number of people queuing on the phone at GP practices by 29 per cent in a Sussex pilot"),
    ("h3_17_wildfires", "2026 is the quietest year for wildfires in Europe by some distance"),
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
