"""Run NEW claims through the local pipeline to build a fresh originator test set.

PAID (Serper + Gemini), founder-approved 2026-09-30 (~45-50p for 15 checks).
Writes Check rows to the LOCAL database only (asserted). The originator review
is OFF; a `classify_batch` hook captures every item the classifier model
itself called PRIMARY on a non-identity host, with the page's first 1,200
chars exactly as the runtime review reads them. None of these claims is an
Astra, A− or replay-corpus claim (design §17-18).

Run from backend/ (Docker up):
    python ../audit/originator_eval/run_fresh_checks.py
"""

import asyncio
import json
import logging
import os
import sys
import time

sys.path.insert(0, ".")

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(HERE, "fresh_runs")

# Chosen for spread (economics, health, law, software, climate, sport, history)
# and to avoid every topic in the Astra, A− and corpus sets.
CLAIMS = [
    (
        "n01_japan_population",
        "Japan's population fell for the 15th consecutive year in 2024.",
    ),
    (
        "n02_sea_level",
        "Global mean sea level rose by about 10 cm between 1993 and 2023.",
    ),
    (
        "n03_statins",
        "Statins reduce the risk of major vascular events by about a fifth for each 1 mmol/L reduction in LDL cholesterol.",
    ),
    ("n04_eu_ai_act", "The EU AI Act entered into force on 1 August 2024."),
    (
        "n05_python_gil",
        "Python 3.13 introduced an experimental free-threaded build that can run without the GIL.",
    ),
    (
        "n06_rust_races",
        "Rust's ownership and borrowing rules prevent data races at compile time.",
    ),
    (
        "n07_measles_england",
        "Measles cases in England rose sharply in 2024 compared with 2023.",
    ),
    ("n08_qatar_final", "The 2022 World Cup final in Qatar was decided on penalties."),
    (
        "n09_great_fire",
        "The Great Fire of London in 1666 destroyed the old St Paul's Cathedral.",
    ),
    (
        "n10_antarctic_ice",
        "Antarctic sea ice reached a record low extent in February 2023.",
    ),
    (
        "n11_uk_minimum_wage",
        "The UK National Living Wage for workers aged 21 and over rose to £12.21 an hour in April 2025.",
    ),
    (
        "n12_lecanemab",
        "Lecanemab slowed cognitive decline in early Alzheimer's disease by about 27% over 18 months.",
    ),
    ("n13_kubernetes", "Kubernetes was originally designed at Google."),
    ("n14_roe_v_wade", "The US Supreme Court overturned Roe v. Wade in June 2022."),
    (
        "n15_coffee_diabetes",
        "Drinking coffee is associated with a lower risk of type 2 diabetes.",
    ),
]

captured = {}
current = {"case": None}


def _install_capture():
    from app.pipeline import evidence_classifier as ec
    from app.services import originator_review as orv

    original = ec.EvidenceClassifier.classify_batch

    async def capturing(self, evidence_items, review_originators=True):
        # Snapshot at entry: the distiller pops `_full_text` once classify yields.
        openings = {
            id(i): (i.get("_full_text") or "")[: orv.TEXT_CHARS] for i in evidence_items
        }
        result = await original(self, evidence_items, review_originators)
        for item in result:
            if not orv.is_candidate(item):
                continue
            opening = openings.get(id(item), "")
            row = captured.setdefault(
                item.get("url"),
                {
                    "url": item.get("url"),
                    "host": ec._url_host(item.get("url") or ""),
                    "title": item.get("title") or "",
                    "text": opening or (item.get("snippet") or "")[: orv.TEXT_CHARS],
                    "input_kind": "page_opening" if opening else "snippet",
                    "records": [],
                    "overlap": False,
                    "stored_type": item.get("evidence_type"),
                    "path": "main" if review_originators else "recovery",
                },
            )
            if current["case"] not in row["records"]:
                row["records"].append(current["case"])
        return result

    ec.EvidenceClassifier.classify_batch = capturing


def _save(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1, default=str)


async def main():
    from sqlalchemy import select
    from sqlalchemy.engine import make_url

    from app.core.config import settings

    assert make_url(settings.DATABASE_URL).host in {"localhost", "127.0.0.1"}
    assert not settings.ENABLE_ORIGINATOR_REVIEW
    _install_capture()

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
    summary = []
    for name, text in CLAIMS:
        current["case"] = name
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
        print("START", name, cid, flush=True)
        try:
            result = await asyncio.wait_for(
                run_pipeline(cid, uid, data, ProgressReporter(cid)), timeout=600
            )
            if result is None:  # paused for selection: select every claim
                async with async_session() as session:
                    rows = (
                        (
                            await session.execute(
                                select(Claim).where(Claim.check_id == cid)
                            )
                        )
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
            from app.core.cost_constants import build_cost_telemetry

            estimate = build_cost_telemetry(result or {}).get("estimated_cost_usd", {})
            status = {
                "case": name,
                "check_id": cid,
                "status": "completed",
                "seconds": round(time.monotonic() - start),
                "cost_usd": estimate.get("total_partial"),
                "llm_usd": estimate.get("llm_partial"),
            }
        except Exception as e:  # record, never abort the sweep
            status = {
                "case": name,
                "check_id": cid,
                "status": "error",
                "type": type(e).__name__,
                "detail": str(e)[:300],
            }
        summary.append(status)
        print("DONE", status, flush=True)
        rows = [dict(r, id=f"n{n:03d}") for n, r in enumerate(captured.values())]
        _save(os.path.join(HERE, "fresh_inputs.json"), rows)
        _save(os.path.join(OUT_DIR, "summary.json"), summary)
    print(f"captured {len(captured)} fresh candidates", flush=True)


if __name__ == "__main__":
    logging.disable(logging.CRITICAL)
    asyncio.run(main())
