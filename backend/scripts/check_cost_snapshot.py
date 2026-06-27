"""COGS snapshot — check volume + per-check cost telemetry from the prod DB.

Read-only. Two things the Railway dashboard can't show:
  1. How many checks have run (the denominator for a top-down cost/check).
  2. The per-check cost telemetry captured since 2026-06-15 (partial LLM cost,
     tokens, search results, wall time) — a grounded bottom-up sample.

Run locally:
    cd backend && python -m scripts.check_cost_snapshot

Run against production (Railway):
    railway run python -m scripts.check_cost_snapshot

NOTE: estimated_cost_usd.llm_partial UNDERCOUNTS — it covers only the
analyzer+classifier+distiller stages (extract/relevance/query not yet wired,
~20-30% gap) and search cost is not included. Treat as a floor, not the answer.
"""

import asyncio
import os
import sys

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


VOLUME_SQL = """
SELECT
    COALESCE(status, '(none)')                                           AS status,
    COUNT(*)                                                             AS total,
    COUNT(*) FILTER (WHERE created_at > now() - interval '24 hours')     AS last_24h,
    COUNT(*) FILTER (WHERE created_at > now() - interval '7 days')       AS last_7d,
    COUNT(*) FILTER (WHERE created_at > now() - interval '30 days')      AS last_30d,
    COUNT(*) FILTER (WHERE created_at >= '2026-03-01')                   AS since_mar1,
    COUNT(*) FILTER (WHERE cost_telemetry IS NOT NULL)                   AS with_telemetry
FROM "check"
GROUP BY COALESCE(status, '(none)')
ORDER BY total DESC;
"""

# Aggregate the telemetry blob over rows that have it. ->> yields text; ::numeric
# of a missing key is NULL, which AVG/percentile ignore — so partial blobs are safe.
TELEMETRY_SQL = """
SELECT
    COUNT(*)                                                                          AS n,
    COUNT(*) FILTER (WHERE created_at > now() - interval '30 days')                   AS n_30d,
    AVG((cost_telemetry->'estimated_cost_usd'->>'llm_partial')::numeric)             AS avg_llm_usd,
    percentile_cont(0.5) WITHIN GROUP (
        ORDER BY (cost_telemetry->'estimated_cost_usd'->>'llm_partial')::numeric)    AS median_llm_usd,
    MIN((cost_telemetry->'estimated_cost_usd'->>'llm_partial')::numeric)             AS min_llm_usd,
    MAX((cost_telemetry->'estimated_cost_usd'->>'llm_partial')::numeric)             AS max_llm_usd,
    AVG((cost_telemetry->'llm'->>'input_tokens')::numeric)                           AS avg_in_tok,
    AVG((cost_telemetry->'llm'->>'output_tokens')::numeric)                          AS avg_out_tok,
    AVG((cost_telemetry->'llm'->>'calls')::numeric)                                  AS avg_llm_calls,
    AVG((cost_telemetry->'search'->>'web_results_reviewed')::numeric)               AS avg_web_results,
    AVG((cost_telemetry->'search'->>'api_adapters_with_results')::numeric)          AS avg_api_adapters,
    AVG((cost_telemetry->'timing'->>'wall_time_ms')::numeric)                       AS avg_wall_ms
FROM "check"
WHERE cost_telemetry IS NOT NULL;
"""


def _fmt(v, places=4):
    return f"{float(v):.{places}f}" if v is not None else "-"


async def main() -> int:
    # Resolve the DB URL from env only (no app config import, so this runs under
    # any Railway service env). From a laptop, Railway's DATABASE_URL points at
    # the *internal* host (*.railway.internal) which won't resolve — prefer the
    # public TCP-proxy URL. Running `railway run --service <Postgres> ...` injects
    # DATABASE_PUBLIC_URL automatically, so no secret needs typing.
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
            vol = (await conn.execute(text(VOLUME_SQL))).all()
            tele = (await conn.execute(text(TELEMETRY_SQL))).one()
    finally:
        await engine.dispose()

    print("=== CHECK VOLUME (by status) ===")
    header = f"{'status':<20}{'total':>8}{'24h':>7}{'7d':>7}{'30d':>7}{'sinceMar1':>11}{'w/telem':>9}"
    print(header)
    print("-" * len(header))
    totals = [0, 0, 0, 0, 0, 0]
    for r in vol:
        status, total, h24, d7, d30, mar1, telem = r
        print(f"{status:<20}{total:>8}{h24:>7}{d7:>7}{d30:>7}{mar1:>11}{telem:>9}")
        for i, v in enumerate((total, h24, d7, d30, mar1, telem)):
            totals[i] += v
    print("-" * len(header))
    print(
        f"{'ALL':<20}{totals[0]:>8}{totals[1]:>7}{totals[2]:>7}{totals[3]:>7}{totals[4]:>11}{totals[5]:>9}"
    )

    print("\n=== PER-CHECK COST TELEMETRY (rows with cost_telemetry; PARTIAL) ===")
    (
        n,
        n_30d,
        avg_usd,
        med_usd,
        min_usd,
        max_usd,
        avg_in,
        avg_out,
        avg_calls,
        avg_web,
        avg_api,
        avg_ms,
    ) = tele
    print(f"sample size           : {n}  (last 30d: {n_30d})")
    print(
        f"llm_partial USD  avg  : {_fmt(avg_usd, 5)}   median {_fmt(med_usd, 5)}   "
        f"min {_fmt(min_usd, 5)}   max {_fmt(max_usd, 5)}"
    )
    print(f"llm tokens  avg in/out: {_fmt(avg_in, 0)} / {_fmt(avg_out, 0)}")
    print(f"llm calls   avg       : {_fmt(avg_calls, 1)}")
    print(f"web results avg       : {_fmt(avg_web, 1)}")
    print(f"api adapters avg      : {_fmt(avg_api, 1)}")
    print(
        f"wall time   avg (s)   : {_fmt((float(avg_ms) / 1000.0) if avg_ms is not None else None, 1)}"
    )
    print(
        "\nNOTE: llm_partial excludes extract/relevance/query stages (~20-30% undercount)"
    )
    print("      and search cost. A floor, not the full per-check cost.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
