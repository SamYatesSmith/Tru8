"""F1 Phase C eval — evidence date distribution before/after the recency fix.

Design: audit/2026-07-03_f1f2_design_review.md §3 (F1 measurement).
Pool: historical claims (LHC no-year, LHC range, 1989 privatisation, 2016 BoE,
moon landing, 2024 hurricane) + controls (current-affairs, timeless).

Metric per claim: share of retrieved evidence whose published_date falls
within/near the claim's event era. Expect >0 after the fix where it was 0;
controls unchanged (current-affairs stays recent-dominated).

Usage:
    python -m scripts.f1_recency_eval --label before
    python -m scripts.f1_recency_eval --label after
    python -m scripts.f1_recency_eval --compare   # prints before/after table

LIVE runs (real LLM + search spend, ~9 full-pipeline checks per label).
Results land in scripts/.f1_recency_eval_<label>.json (gitignored dot-file).
Local-only tooling — not part of the shipped product.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
from datetime import datetime
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

# Era = (start_year, end_year) inclusive. "era_share" counts evidence dated
# inside it. Controls carry expect="recent"/"any" instead of an era test.
POOL = [
    {
        "key": "lhc_noyear",
        "claim": "Only European countries contributed to building the Large Hadron Collider.",
        "era": (1994, 2012),
        "expect": "era>0",
        "why": "Founder's real failure shape (TRU-EAB8-2652): historical, NO year token — tests D3 hedge alone.",
    },
    {
        "key": "lhc_range",
        "claim": "The Large Hadron Collider was built between 1998 and 2008 with contributions from countries around the world.",
        "era": (1994, 2012),
        "expect": "era>0",
        "why": "Year-RANGE token (1998..2008) — tests D1 range-anchor (old anchor required exactly one year).",
    },
    {
        "key": "water_1989",
        "claim": "England's water industry was privatised in 1989 under the Thatcher government.",
        "era": (1988, 1994),
        "expect": "era>=0",
        "why": "Single past year — B4 + single-year anchor already cover; regression guard.",
    },
    {
        "key": "boe_2016",
        "claim": "The Bank of England cut interest rates to 0.25% in August 2016 following the Brexit referendum.",
        "era": (2016, 2017),
        "expect": "era>=0",
        "why": "TRU-04E3 shape; single past year; regression guard.",
    },
    {
        "key": "moon",
        "claim": "The United States remains the only country to have landed people on the Moon.",
        "era": (1969, 1980),
        "expect": "era>=0",
        "why": "Historical, no year token, but pre-web era — period documents scarce online; honest low bar.",
    },
    {
        "key": "hurricane_2024",
        "claim": "The 2024 Atlantic hurricane season produced multiple category 5 hurricanes.",
        "era": (2024, 2025),
        "expect": "era>0",
        "why": "Recent-past with year token; B4 path; regression guard.",
    },
    {
        "key": "ctrl_inflation",
        "claim": "UK inflation is currently above the Bank of England's 2% target.",
        "era": None,
        "expect": "recent",
        "why": "Current-affairs CONTROL — recent share must stay high; the hedge must not degrade breaking/current retrieval.",
    },
    {
        "key": "ctrl_nhs",
        "claim": "NHS waiting lists in England have fallen over the past year.",
        "era": None,
        "expect": "recent",
        "why": "Current-affairs CONTROL #2 (design asks for two).",
    },
    {
        "key": "ctrl_light",
        "claim": "The speed of light in a vacuum is approximately 299,792 kilometres per second.",
        "era": None,
        "expect": "any",
        "why": "Timeless CONTROL — date distribution unconstrained; watch for pathological shifts only.",
    },
]

RECENT_MONTHS = 18  # "recent" = within this many months of today


class _EvalCaptured(Exception):
    """Sentinel: retrieval output captured — abort the rest of phase 2.

    The F1 metric measures what RETRIEVAL returns (date distribution of the
    retrieved pool); mapping/analyze add nothing to it. Aborting after capture
    also makes the eval immune to the analyze-stage LLM flakiness that zeroed
    the first two attempts (Gemini 503 storm + dead local OpenAI fallback key
    -> phase 2 aborted before its final save -> 0 DB rows for every claim).
    """


async def _run_claim(claim_text: str) -> dict:
    """Run the pipeline through RETRIEVE on one claim; capture the pool."""
    import app.workers.pipeline as wp
    from app.core.database import async_session
    from app.pipeline.progress import ProgressReporter
    from app.pipeline.runner import run_pipeline
    from scripts.replay_bench.runner import (
        _cleanup_check,
        _create_check,
        _ensure_bench_user,
    )

    input_data = {
        "input_type": "text",
        "content": claim_text,
        "url": None,
        "user_query": None,
    }

    async with async_session() as session:
        user = await _ensure_bench_user(session)
        check = await _create_check(session, user.id, input_data)
        check_id = check.id
        user_id = user.id

    pipeline_input = {
        "input_type": "text",
        "content": claim_text,
        "url": None,
        "file_path": None,
        "user_query": None,
    }

    # Capture at the retrieve seam: wrap the real retrieve_evidence_with_cache,
    # keep its result, abort phase 2. run_pipeline_phase2 does
    # `from app.workers.pipeline import retrieve_evidence_with_cache` at call
    # time, so patching the module attribute beforehand reaches it.
    captured: dict = {}
    real_retrieve = wp.retrieve_evidence_with_cache

    async def _capturing(*args, **kwargs):
        res = await real_retrieve(*args, **kwargs)
        captured["result"] = res
        raise _EvalCaptured()

    error = None
    wp.retrieve_evidence_with_cache = _capturing
    try:
        result = await asyncio.wait_for(
            run_pipeline(check_id, user_id, pipeline_input, ProgressReporter(check_id)),
            timeout=300,
        )
        # Text-mode checks ALSO pause at waiting_for_selection (verified live
        # 2026-07-06 — the CLAUDE.md "article mode only" note is stale).
        # Select every extracted claim and run phase 2, like the bench runner.
        if result is None:
            from sqlalchemy import select as _select
            from app.models.check import Claim as _Claim
            from app.pipeline.runner import run_pipeline_phase2
            from scripts.replay_bench.runner import _apply_claim_selection

            async with async_session() as session:
                res = await session.execute(
                    _select(_Claim.position).where(_Claim.check_id == check_id)
                )
                positions = [r[0] for r in res.all()]
            async with async_session() as session:
                await _apply_claim_selection(session, check_id, positions)
            await asyncio.wait_for(
                run_pipeline_phase2(
                    check_id=check_id,
                    user_id=user_id,
                    input_data=pipeline_input,
                    progress_reporter=ProgressReporter(check_id),
                ),
                timeout=300,
            )
    except _EvalCaptured:
        pass  # expected — retrieval captured, rest of phase 2 skipped
    except Exception as e:
        # Phase 2 may also swallow/convert _EvalCaptured into its own failure
        # path — the capture already happened either way. Only report an error
        # if we genuinely captured nothing.
        error = f"{type(e).__name__}: {e}"
    finally:
        wp.retrieve_evidence_with_cache = real_retrieve

    rows = []
    res = captured.get("result")
    if res:
        error = None  # capture succeeded; any post-capture exception is noise
        for _pos, items in (res.get("evidence_by_claim") or {}).items():
            for ev in items or []:
                pd = ev.get("published_date")
                if pd is not None and not isinstance(pd, str):
                    pd = pd.isoformat()
                rows.append(
                    {
                        "url": ev.get("url"),
                        "published_date": pd,
                        "date_basis": ev.get("date_basis"),
                    }
                )
    elif error is None:
        error = "retrieval was never reached (no capture, no exception)"

    async with async_session() as session:
        await _cleanup_check(session, check_id)

    return {"evidence": rows, "error": error}


def _year_of(published_date) -> "int | None":
    """Extract a 4-digit year from a published_date string.

    Fixes a metric under-count (2026-07-07): ``int(pd[:4])`` only parsed
    ISO-prefixed dates and silently dropped engine-format strings like
    "May 7, 2015" or "Dec 16, 2025" — they counted toward ``dated`` (the
    era/recent denominators) but never toward the numerators, deflating
    every era_share. ISO prefix first, then a bounded year regex.
    """
    if not isinstance(published_date, str):
        return None
    head = published_date[:4]
    if head.isdigit():
        return int(head)
    m = re.search(r"\b(19|20)\d{2}\b", published_date)
    return int(m.group(0)) if m else None


def _summarise(entry: dict, rows: list, error) -> dict:
    now = datetime.now()
    dated = [r for r in rows if r["published_date"]]
    years = []
    for r in dated:
        y = _year_of(r["published_date"])
        if y is not None:
            years.append(y)
    era = entry["era"]
    in_era = sum(1 for y in years if era and era[0] <= y <= era[1])
    recent_cut = (
        now.year
        - (RECENT_MONTHS // 12)
        - (1 if now.month <= (RECENT_MONTHS % 12) else 0)
    )
    recent = sum(1 for y in years if y >= recent_cut)
    return {
        "key": entry["key"],
        "expect": entry["expect"],
        "total_evidence": len(rows),
        "dated": len(dated),
        "in_era": in_era,
        "era_share": round(in_era / len(dated), 3) if dated else None,
        "recent": recent,
        "recent_share": round(recent / len(dated), 3) if dated else None,
        "year_histogram": {str(y): years.count(y) for y in sorted(set(years))},
        "error": error,
    }


async def run_label(label: str) -> None:
    out_path = BACKEND_DIR / "scripts" / f".f1_recency_eval_{label}.json"
    results = []
    for entry in POOL:
        # Cold-cache every claim (same bust the bench uses, incl. the
        # api_response + raw-relevance fixes). Without this the second label
        # replays the first label's cached search/extract/adapter results and
        # the A/B compares nothing — caught 2026-07-06 when before/after came
        # back byte-identical across all nine claims.
        from scripts.replay_bench.runner import _bust_pipeline_caches

        await _bust_pipeline_caches()
        print(f"... running {entry['key']} ...", flush=True)
        r = await _run_claim(entry["claim"])
        summary = _summarise(entry, r["evidence"], r["error"])
        summary["evidence"] = r["evidence"]
        results.append(summary)
        print(
            f"    {entry['key']}: {summary['total_evidence']} evidence, "
            f"{summary['dated']} dated, era={summary['in_era']}, "
            f"recent={summary['recent']}"
            + (f"  [ERROR: {summary['error']}]" if summary["error"] else ""),
            flush=True,
        )
    out_path.write_text(
        json.dumps(
            {"label": label, "at": datetime.now().isoformat(), "results": results},
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"\nwrote {out_path}")


def compare() -> None:
    b = json.loads(
        (BACKEND_DIR / "scripts" / ".f1_recency_eval_before.json").read_text(
            encoding="utf-8"
        )
    )
    a = json.loads(
        (BACKEND_DIR / "scripts" / ".f1_recency_eval_after.json").read_text(
            encoding="utf-8"
        )
    )
    bd = {r["key"]: r for r in b["results"]}
    ad = {r["key"]: r for r in a["results"]}
    print(
        f"{'claim':16} {'expect':8} | {'era B':>6} {'era A':>6} | {'recent B':>8} {'recent A':>8} | {'dated B':>7} {'dated A':>7}"
    )
    for entry in POOL:
        k = entry["key"]
        rb, ra = bd.get(k, {}), ad.get(k, {})
        print(
            f"{k:16} {entry['expect']:8} | "
            f"{str(rb.get('in_era')):>6} {str(ra.get('in_era')):>6} | "
            f"{str(rb.get('recent')):>8} {str(ra.get('recent')):>8} | "
            f"{str(rb.get('dated')):>7} {str(ra.get('dated')):>7}"
        )


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--label", choices=["before", "after"])
    g.add_argument("--compare", action="store_true")
    args = p.parse_args()
    if args.compare:
        compare()
    else:
        asyncio.run(run_label(args.label))
