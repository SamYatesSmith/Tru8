"""Two LOCAL live checks with the originator review ON (design §7.7).

PAID (~5-7p each), founder-approved 2026-09-30 (route A). Full pipeline, real
retrieval and models, LOCAL database only (asserted). Saves each owner payload
(which carries `originatorReview` receipts) and prints every receipt, the
review's stage time, and the check's estimated cost.

Run from backend/ (Docker up):  python ../audit/originator_eval/live_checks.py
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
    (
        "live1_python_gil",
        "Python 3.13 introduced an experimental free-threaded build that can run without the GIL.",
    ),
    (
        "live2_sea_level",
        "Global mean sea level rose by about 10 cm between 1993 and 2023.",
    ),
]


async def main():
    from sqlalchemy import select
    from sqlalchemy.engine import make_url

    from app.core.config import settings

    assert make_url(settings.DATABASE_URL).host in {"localhost", "127.0.0.1"}
    settings.ENABLE_ORIGINATOR_REVIEW = True

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
        print(
            f"== {name} {cid} {round(time.monotonic() - start)}s "
            f"cost ${telemetry['estimated_cost_usd'].get('total_partial')} "
            f"review stage {telemetry['timing']['stage_timings_s'].get('originator_review')}s"
        )
        for claim in owner.get("claims") or []:
            refs = {
                r.get("evidenceId"): (
                    el.get("description", "")[:50],
                    r.get("relationship"),
                    el.get("state"),
                )
                for el in (claim.get("claimMap") or {}).get("elements") or []
                for r in el.get("evidenceRefs") or []
            }
            for ev in claim.get("evidence") or []:
                receipt = ev.get("originatorReview")
                if not receipt:
                    continue
                print(
                    f"  [{receipt.get('status')}/{receipt.get('role')}] "
                    f"{receipt.get('from_tier')}->{receipt.get('to_tier')} {ev.get('url', '')[:70]}\n"
                    f"      originator: {receipt.get('originator', '')[:60]} | cue: {receipt.get('cue', '')[:90]!r}\n"
                    f"      mapped: {refs.get(ev.get('evidenceId'))}"
                )
            for el in (claim.get("claimMap") or {}).get("elements") or []:
                print(f"  element [{el.get('state')}] {el.get('description', '')[:90]}")


if __name__ == "__main__":
    logging.disable(logging.CRITICAL)
    asyncio.run(main())
