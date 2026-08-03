"""Post-deploy verification for M1 (mapping thinking OFF) + D1 (distil batches).

READ-ONLY, TELEMETRY-ONLY. Returns nothing but numeric per-stage timings and
token counts from the most recent checks — no claim text, no URLs, no evidence
content, no user identifiers beyond a short check-id prefix for correlation.

What it answers:
  * Did the mapping/distil Gemini calls fire on real checks since the deploy?
  * Did M1 take effect?  -> analyzer.thinking_tokens == 0
  * Did D1 run?          -> distiller present + stage_timings_s.distil populated

Run against production (Railway):
    cd backend && railway run --service Postgres python -m scripts.verify_m1_d1_prod

M1 (MAPPING_THINKING_BUDGET=0) went live 2026-07-02 ~15:32 UTC; only checks
after that carry thinking_tokens == 0. V1 telemetry (stage_timings_s) began the
same day, so older rows may lack these keys — shown as '-'.
"""

import asyncio
import json
import os
import sys

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


# Only telemetry sub-objects are selected. No user content columns are touched.
RECENT_SQL = """
SELECT
    left(id::text, 8)                                                     AS check_id,
    created_at,
    COALESCE(status, '(none)')                                           AS status,
    cost_telemetry->'timing'->'stage_timings_s'                          AS stage_timings_s,
    cost_telemetry->'llm'->'by_stage'->'analyzer'                        AS analyzer,
    cost_telemetry->'llm'->'by_stage'->'distiller'                       AS distiller,
    cost_telemetry->'llm'->>'calls'                                      AS llm_calls
FROM "check"
WHERE cost_telemetry IS NOT NULL
ORDER BY created_at DESC
LIMIT 25;
"""


def _stage(blob, key):
    if not blob:
        return "-"
    try:
        d = blob if isinstance(blob, dict) else json.loads(blob)
        v = d.get(key)
        return f"{float(v):.1f}" if v is not None else "-"
    except Exception:
        return "?"


def _as_dict(blob):
    if not blob:
        return None
    try:
        return blob if isinstance(blob, dict) else json.loads(blob)
    except Exception:
        return None


def _thinking(analyzer_blob):
    """Analyzer thinking tokens. 'ABSENT' = no analyzer block at all;
    'none' = block present but no thinking_tokens key (M1 thinking OFF emits
    no key when zero); a number = thinking tokens actually spent."""
    d = _as_dict(analyzer_blob)
    if d is None:
        return "ABSENT"
    v = d.get("thinking_tokens")
    return "none" if v is None else str(int(v))


def _distil_out(blob):
    """distiller input/output tokens. 'ABSENT' = D1 by_stage fix not present."""
    d = _as_dict(blob)
    if d is None:
        return "ABSENT"
    return f"{int(d.get('input_tokens', 0))}/{int(d.get('output_tokens', 0))}"


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
            rows = (await conn.execute(text(RECENT_SQL))).all()
    finally:
        await engine.dispose()

    if not rows:
        print("No checks with cost_telemetry found.")
        return 0

    print("=== LAST 25 CHECKS WITH TELEMETRY (newest first) ===")
    print("M1 confirm: think=0   D1 confirm: distil timing + distiller tok non-zero\n")
    hdr = (
        f"{'check':<9}{'created (UTC)':<20}{'status':<12}"
        f"{'analyze_s':>10}{'distil_s':>9}{'retr_s':>8}"
        f"{'think':>7}{'distil_in/out':>15}{'calls':>6}"
    )
    print(hdr)
    print("-" * len(hdr))
    for r in rows:
        cid, created, status, stages, analyzer, distiller, calls = r
        created_s = str(created)[:19]
        print(
            f"{cid:<9}{created_s:<20}{status:<12}"
            f"{_stage(stages, 'analyze'):>10}{_stage(stages, 'distil'):>9}"
            f"{_stage(stages, 'retrieve'):>8}"
            f"{_thinking(analyzer):>7}"
            f"{_distil_out(distiller):>15}{(calls if calls is not None else '-'):>6}"
        )
    print(
        "\nRead: think='none' or '0' AND analyze_s ~11-20 => M1 live (thinking OFF) + mapping API fired."
        "\n      think=<positive number> => M1 NOT effective on that check (thinking still on)."
        "\n      distil_in/out non-zero => D1 by_stage telemetry live + distil API fired."
        "\n      *_ABSENT or blank stage => telemetry block not written (pre-V1/pre-D1 code path)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
