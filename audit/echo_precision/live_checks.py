"""Two LOCAL live checks with echo link confirmation ON (build plan §13 step 3).

PAID (~10-15p each), founder-approved 2026-10-05. Full pipeline, real
retrieval and models, LOCAL database only (asserted). Saves each owner payload
(claim-map metadata carries `echoLinks`) and prints every echo record, every
echo-scoped ref, the stage timings, and the check's estimated cost.

Run from backend/ (Docker up):  python ../audit/echo_precision/live_checks.py
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
        "echo1_galway_reefs",
        "A team from University of Galway, with colleagues from France, placed 23 3D-printed reef structures on the seabed of the Porcupine Bank 200km off the Kerry coast, and in the Bay of Biscay off France.",
    ),
    (
        "echo2_uk_cpi",
        "UK consumer price inflation rose to 3.8% in the 12 months to July 2025.",
    ),
]


async def main():
    from sqlalchemy import select
    from sqlalchemy.engine import make_url

    from app.core.config import settings

    assert make_url(settings.DATABASE_URL).host in {"localhost", "127.0.0.1"}
    settings.ENABLE_ECHO_LINK_CONFIRMATION = True
    settings.ENABLE_ECHO_SCOPE_GATE = True
    settings.ENABLE_DERIVATION_CHAINS = True

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
            f"echo run {timings.get('echo_link_confirmation')}s "
            f"wait {timings.get('echo_link_wait')}s analyze {timings.get('analyze')}s"
        )
        for claim in owner.get("claims") or []:
            cm = claim.get("claimMap") or {}
            urls = {
                ev.get("evidenceId"): ev.get("url", "")[:70]
                for ev in claim.get("evidence") or []
            }
            echo = (cm.get("metadata") or {}).get("echoLinks") or {}
            print(f"  totals {echo.get('totals')}")
            for r in echo.get("records") or []:
                print(
                    f"  [{r.get('status')}/{r.get('detail') or r.get('extent')}] "
                    f"{urls.get(r.get('original_id'))} <- {urls.get(r.get('derivative_id'))}\n"
                    f"      cue ({r.get('cue_kind')}): {(r.get('cue') or '')[:110]!r}"
                )
            for el in cm.get("elements") or []:
                scoped = (
                    (el.get("basis") or {}).get("echoScope")
                    or (el.get("basis") or {}).get("echo_scope")
                    or {}
                ).get("scoped") or []
                print(f"  element [{el.get('state')}] {el.get('description', '')[:90]}")
                for s in scoped:
                    print(
                        f"      echo-scoped {urls.get(s.get('evidence_id'))} (was {s.get('was')}, original {urls.get(s.get('original_id'))})"
                    )


if __name__ == "__main__":
    logging.disable(logging.CRITICAL)
    asyncio.run(main())
