"""Harvest a FRESH originator test set cheaply: the real pipeline up to CLASSIFY.

PAID (Serper + Gemini), founder-approved 2026-09-30 (~30p for ~50 claims).
Each claim runs the production path (extract → select → decompose → retrieve
→ fetch → score → classify) and HALTS at the transition to `analyze`, so
mapping, reviews and coverage recovery never run. Distillation is off: it
runs beside classify and never changes the classifier's input. A hook on
`classify_batch` captures every item the classifier model itself called
PRIMARY on a non-identity host, with the page opening the runtime review
reads. Gemini tokens are metered per model from the responses; Serper units
are counted per request. LOCAL database only (asserted).

Run from backend/ (Docker up):
    python ../audit/originator_eval/run_fresh_harvest.py
"""

import asyncio
import json
import logging
import os
import sys
import time
from collections import defaultdict

sys.path.insert(0, ".")

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "fresh_inputs.json")  # appends to the 3 full checks' 11
SUMMARY = os.path.join(HERE, "fresh_runs", "harvest_summary.json")

# None repeats an Astra, A−, replay-corpus or earlier fresh claim.
CLAIMS = [
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
    ("n16_eiffel", "The Eiffel Tower was completed in 1889."),
    ("n17_coal_record", "Global coal consumption reached a record high in 2023."),
    ("n18_westphalia", "The Peace of Westphalia was signed in 1648."),
    ("n19_http3", "HTTP/3 runs over the QUIC transport protocol."),
    (
        "n20_four_day_week",
        "The UK four-day week pilot in 2022 involved around 60 companies.",
    ),
    (
        "n21_vitamin_d",
        "Vitamin D supplementation does not reduce fracture risk in healthy adults.",
    ),
    (
        "n22_india_population",
        "India overtook China as the world's most populous country in 2023.",
    ),
    ("n23_amazon_oxygen", "The Amazon rainforest produces 20% of the world's oxygen."),
    ("n24_linux_1991", "Linux was first released by Linus Torvalds in 1991."),
    (
        "n25_paris_agreement",
        "The Paris Agreement aims to limit global warming to well below 2°C above pre-industrial levels.",
    ),
    (
        "n26_german_nuclear",
        "Germany shut down its last three nuclear power plants in April 2023.",
    ),
    (
        "n27_hpv_scotland",
        "HPV vaccination has substantially reduced cervical cancer rates in Scotland.",
    ),
    ("n28_bolt_record", "Usain Bolt's 100 metres world record is 9.58 seconds."),
    ("n29_magna_carta", "Magna Carta was sealed in 1215."),
    ("n30_tesla_2023", "Tesla delivered about 1.8 million vehicles in 2023."),
    (
        "n31_reef_bleaching",
        "The Great Barrier Reef suffered a mass bleaching event in 2024.",
    ),
    ("n32_git_2005", "Git was created by Linus Torvalds in 2005."),
    ("n33_argentina_inflation", "Argentina's annual inflation exceeded 200% in 2023."),
    (
        "n34_amr_deaths",
        "Antimicrobial resistance was directly responsible for over a million deaths worldwide in 2019.",
    ),
    ("n35_burj_khalifa", "The Burj Khalifa is more than 800 metres tall."),
    ("n36_wasm", "WebAssembly became a W3C Recommendation in 2019."),
    ("n37_chile_copper", "Chile is the world's largest producer of copper."),
    (
        "n38_pig_kidney",
        "The first transplant of a pig kidney into a living human took place in 2024.",
    ),
    ("n39_bitcoin_cap", "Bitcoin's supply is capped at 21 million coins."),
    (
        "n40_ecb_hikes",
        "The European Central Bank raised interest rates ten consecutive times between July 2022 and September 2023.",
    ),
    (
        "n41_predimed",
        "The PREDIMED trial found a Mediterranean diet reduced major cardiovascular events.",
    ),
    ("n42_voyager", "Voyager 1 entered interstellar space in 2012."),
    (
        "n43_online_safety_act",
        "The UK Online Safety Act received Royal Assent in October 2023.",
    ),
    (
        "n44_nz_smoking",
        "New Zealand repealed its law banning tobacco sales to people born after 2008.",
    ),
    (
        "n45_gb_wind",
        "Wind generated more electricity than gas in Great Britain in 2023.",
    ),
    ("n46_titanic", "The Titanic sank in April 1912."),
    (
        "n47_black_sea_grain",
        "Ukraine resumed grain exports through a Black Sea corridor in 2023 after the grain deal ended.",
    ),
    ("n48_microplastics", "Microplastics have been found in human placentas."),
    ("n49_rosetta", "The Rosetta Stone is held in the British Museum."),
    (
        "n50_japan_debt",
        "Japan's government debt is more than twice the size of its economy.",
    ),
]


class HaltAfterClassify(BaseException):
    """BaseException so the pipeline's `except Exception` handlers let it out."""


captured = {}
current = {"case": None}
usage = defaultdict(lambda: {"input": 0, "output": 0, "thinking": 0})
serper = {"requests": 0}


def _install_hooks():
    from app.pipeline import evidence_classifier as ec
    from app.pipeline import runner
    from app.services import google_ai
    from app.services import originator_review as orv

    original_classify = ec.EvidenceClassifier.classify_batch

    async def capturing(self, evidence_items, review_originators=True):
        openings = {
            id(i): (i.get("_full_text") or "")[: orv.TEXT_CHARS] for i in evidence_items
        }
        result = await original_classify(self, evidence_items, review_originators)
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
                },
            )
            if current["case"] not in row["records"]:
                row["records"].append(current["case"])
        return result

    ec.EvidenceClassifier.classify_batch = capturing

    original_transition = runner._log_stage_transition

    async def halting(check_id, from_stage, to_stage, *args, **kwargs):
        if to_stage == "analyze":
            raise HaltAfterClassify()
        return await original_transition(
            check_id, from_stage, to_stage, *args, **kwargs
        )

    runner._log_stage_transition = halting

    original_client = google_ai._get_client

    class _MeteredClient:
        def __init__(self, inner):
            self._inner = inner

        def __getattr__(self, name):
            return getattr(self._inner, name)

        async def post(self, url, *args, **kwargs):
            response = await self._inner.post(url, *args, **kwargs)
            try:
                model = url.split("models/")[1].split(":")[0]
                meta = response.json().get("usageMetadata", {})
                usage[model]["input"] += meta.get("promptTokenCount", 0)
                usage[model]["output"] += meta.get("candidatesTokenCount", 0)
                usage[model]["thinking"] += meta.get("thoughtsTokenCount", 0)
            except Exception:
                pass
            return response

    async def metered_client():
        return _MeteredClient(await original_client())

    google_ai._get_client = metered_client

    import httpx

    original_send = httpx.AsyncClient.send

    async def counting_send(self, request, *args, **kwargs):
        if "serper.dev" in str(request.url):
            serper["requests"] += 1
        return await original_send(self, request, *args, **kwargs)

    httpx.AsyncClient.send = counting_send


def _cost_usd():
    from app.core.cost_constants import _rate

    total = 0.0
    for model, u in usage.items():
        rate = _rate(model)
        total += (
            u["input"] * rate["input"] + (u["output"] + u["thinking"]) * rate["output"]
        ) / 1e6
    return total


def _save(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1, default=str)


async def main():
    from sqlalchemy import select
    from sqlalchemy.engine import make_url

    from app.core.config import settings

    assert make_url(settings.DATABASE_URL).host in {"localhost", "127.0.0.1"}
    assert not settings.ENABLE_ORIGINATOR_REVIEW
    settings.ENABLE_EVIDENCE_DISTILLATION = False
    _install_hooks()

    from app.core.database import async_session
    from app.models import Check, Claim
    from app.pipeline.progress import ProgressReporter
    from app.pipeline.runner import run_pipeline, run_pipeline_phase2
    from scripts.replay_bench.runner import _create_check, _ensure_bench_user

    # Keep the 11 captured by the three full checks earlier the same day.
    for row in json.load(open(OUT, encoding="utf-8")) if os.path.exists(OUT) else []:
        captured.setdefault(row["url"], {k: v for k, v in row.items() if k != "id"})

    summary = []
    for name, text in CLAIMS:
        current["case"] = name
        before = (len(captured), _cost_usd(), serper["requests"])
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
        status = "halted_after_classify"
        try:
            result = await asyncio.wait_for(
                run_pipeline(cid, uid, data, ProgressReporter(cid)), timeout=300
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
                await asyncio.wait_for(
                    run_pipeline_phase2(
                        check_id=cid,
                        user_id=uid,
                        input_data={**data, "content": None},
                        progress_reporter=ProgressReporter(cid),
                    ),
                    timeout=300,
                )
            status = "completed_without_halt"
        except HaltAfterClassify:
            pass
        except Exception as e:  # record, never abort the sweep
            status = f"error:{type(e).__name__}:{str(e)[:120]}"
        async with async_session() as session:  # the halted row is bench-local
            ck = (
                await session.execute(select(Check).where(Check.id == cid))
            ).scalar_one()
            ck.status = "failed"
            await session.commit()
        entry = {
            "case": name,
            "check_id": cid,
            "status": status,
            "seconds": round(time.monotonic() - start),
            "new_candidates": len(captured) - before[0],
            "gemini_usd": round(_cost_usd() - before[1], 5),
            "serper_requests": serper["requests"] - before[2],
        }
        summary.append(entry)
        print(
            "DONE",
            entry,
            "| total candidates",
            len(captured),
            "| gemini $",
            round(_cost_usd(), 4),
            flush=True,
        )
        rows = [dict(r, id=f"n{n:03d}") for n, r in enumerate(captured.values())]
        _save(OUT, rows)
        _save(
            SUMMARY,
            {
                "claims": summary,
                "usage_by_model": dict(usage),
                "gemini_usd": round(_cost_usd(), 4),
                "serper_requests": serper["requests"],
            },
        )
        if os.path.exists(os.path.join(HERE, "STOP")):
            print("STOP file found", flush=True)
            break
    print(f"captured {len(captured)} fresh candidates", flush=True)


if __name__ == "__main__":
    logging.disable(logging.CRITICAL)
    asyncio.run(main())
