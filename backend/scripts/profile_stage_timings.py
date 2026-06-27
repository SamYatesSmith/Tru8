"""Profile per-stage wall-clock for a real full-pipeline check.

The pipeline already records ``stage_timings`` (seconds per stage) into
``result["pipeline_stats"]["stage_timings"]`` (runner.py:2513-2521) but never
logs the breakdown as a single line. This script runs one or more real checks
in *focused* (single text claim) mode — which flows straight through phase 2
with no selection pause — busts the Redis caches before each run so we profile
the cold path the user actually feels (30-90s), and prints a per-stage table.

Usage (needs Postgres + Redis + Qdrant up; i.e. `docker compose up -d`):

    cd backend
    python -m scripts.profile_stage_timings                       # default claim, 3 runs
    python -m scripts.profile_stage_timings --runs 2
    python -m scripts.profile_stage_timings --claim "your claim text here" --runs 1

Cost: ~$0.10-0.25 per run (LLM + search calls); cache-busted each run.
"""

from __future__ import annotations

import argparse
import asyncio
import time
from typing import Any, Dict, List, Optional

# Reuse the proven bench harness helpers so setup matches a real bench run.
from scripts.replay_bench.runner import (
    _bust_pipeline_caches,
    _cleanup_check,
    _create_check,
    _ensure_bench_user,
)

DEFAULT_CLAIM = (
    "The 2022 UK mini-budget caused a sharp rise in government borrowing costs."
)


async def _run_once(claim_text: str, run_idx: int) -> Optional[Dict[str, Any]]:
    """Run one full check and return its pipeline_stats dict (timings + wall)."""
    from app.core.database import async_session
    from app.pipeline.progress import ProgressReporter
    from app.pipeline.runner import run_pipeline

    await _bust_pipeline_caches()

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

    reporter = ProgressReporter(check_id)
    wall_start = time.monotonic()
    try:
        result = await asyncio.wait_for(
            run_pipeline(check_id, user_id, pipeline_input, reporter),
            timeout=300,
        )
    finally:
        wall = time.monotonic() - wall_start

    if result is None:
        print(
            f"  run {run_idx}: returned None (article mode pause) — "
            "expected focused mode for a single text claim. Skipping."
        )
        async with async_session() as s:
            await _cleanup_check(s, check_id)
        return None

    stats = dict(result.get("pipeline_stats", {}))
    stats["_observed_wall_s"] = wall
    stats["_processing_time_ms"] = result.get("processing_time_ms")
    stats["_check_id"] = check_id

    # Best-effort cleanup so repeated runs don't accumulate bench rows.
    async with async_session() as s:
        await _cleanup_check(s, check_id)

    return stats


def _print_run(run_idx: int, stats: Dict[str, Any]) -> None:
    timings: Dict[str, float] = stats.get("stage_timings", {}) or {}
    total_stage = stats.get("total_stage_time") or sum(timings.values())
    wall = stats.get("_observed_wall_s") or 0.0

    print(f"\n=== Run {run_idx}  (check {stats.get('_check_id')}) ===")
    print(f"  observed wall-clock : {wall:6.1f}s")
    print(f"  sum of stage timings: {total_stage:6.1f}s")
    print(f"  unaccounted overhead: {wall - total_stage:6.1f}s")
    print(f"  {'stage':<22}{'seconds':>9}   {'% of staged':>11}")
    print(f"  {'-'*22}{'-'*9}   {'-'*11}")
    for stage, secs in sorted(timings.items(), key=lambda kv: kv[1], reverse=True):
        pct = (secs / total_stage * 100) if total_stage else 0.0
        print(f"  {stage:<22}{secs:>9.2f}   {pct:>10.1f}%")


def _print_summary(runs: List[Dict[str, Any]]) -> None:
    if not runs:
        return
    # Aggregate mean per stage across runs.
    agg: Dict[str, List[float]] = {}
    walls: List[float] = []
    for st in runs:
        walls.append(st.get("_observed_wall_s") or 0.0)
        for stage, secs in (st.get("stage_timings") or {}).items():
            agg.setdefault(stage, []).append(secs)

    print("\n" + "=" * 52)
    print(f"SUMMARY across {len(runs)} run(s)")
    print(
        f"  wall-clock min/mean/max: "
        f"{min(walls):.1f} / {sum(walls)/len(walls):.1f} / {max(walls):.1f}s"
    )
    print(f"  {'stage':<22}{'mean s':>9}{'min':>8}{'max':>8}")
    print(f"  {'-'*22}{'-'*9}{'-'*8}{'-'*8}")
    means = {s: sum(v) / len(v) for s, v in agg.items()}
    for stage in sorted(means, key=lambda s: means[s], reverse=True):
        v = agg[stage]
        print(f"  {stage:<22}{means[stage]:>9.2f}{min(v):>8.2f}{max(v):>8.2f}")
    top = max(means, key=means.get) if means else None
    if top:
        print(
            f"\n  Dominant stage: '{top}' "
            f"(mean {means[top]:.1f}s, "
            f"{means[top]/sum(means.values())*100:.0f}% of staged time)"
        )


async def _main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--claim", default=DEFAULT_CLAIM, help="claim text to check")
    ap.add_argument("--runs", type=int, default=3, help="number of runs (variance)")
    args = ap.parse_args()

    print(f"Profiling full pipeline — {args.runs} run(s)")
    print(f"Claim: {args.claim!r}")

    collected: List[Dict[str, Any]] = []
    for i in range(1, args.runs + 1):
        print(f"\n--- starting run {i}/{args.runs} (cache-busted) ---")
        try:
            stats = await _run_once(args.claim, i)
        except asyncio.TimeoutError:
            print(f"  run {i}: TIMED OUT after 300s")
            continue
        except Exception as exc:  # noqa: BLE001 - surface any setup failure
            print(f"  run {i}: ERROR {type(exc).__name__}: {exc}")
            continue
        if stats:
            _print_run(i, stats)
            collected.append(stats)

    _print_summary(collected)


if __name__ == "__main__":
    asyncio.run(_main())
