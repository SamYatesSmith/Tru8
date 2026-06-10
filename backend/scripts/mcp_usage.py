"""Show how much the tru8-mcp package (and other first-party clients) is used.

Reads Check.client (set from the X-Tru8-Client header) and prints a compact
report: totals by client, recent activity windows, and distinct users.

Run locally:
    cd backend && python -m scripts.mcp_usage

Run against production (Railway):
    railway run python -m scripts.mcp_usage

`client` is NULL for ordinary web/raw-API traffic and 'mcp' for MCP submissions,
so "Is the MCP package being used?" == the mcp row being non-zero.
"""

import asyncio
import sys

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import settings


REPORT_SQL = """
SELECT
    COALESCE(client, '(web / raw api)')                                   AS client,
    COUNT(*)                                                              AS total,
    COUNT(*) FILTER (WHERE created_at > now() - interval '24 hours')      AS last_24h,
    COUNT(*) FILTER (WHERE created_at > now() - interval '7 days')        AS last_7d,
    COUNT(*) FILTER (WHERE created_at > now() - interval '30 days')       AS last_30d,
    COUNT(DISTINCT user_id)                                               AS users,
    MAX(created_at)                                                       AS last_seen
FROM "check"
GROUP BY COALESCE(client, '(web / raw api)')
ORDER BY total DESC;
"""


async def main() -> int:
    db_url = getattr(settings, "DATABASE_URL", "")
    if not db_url:
        print("DATABASE_URL not configured", file=sys.stderr)
        return 2
    if db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

    engine = create_async_engine(db_url)
    try:
        async with engine.connect() as conn:
            rows = (await conn.execute(text(REPORT_SQL))).all()
    finally:
        await engine.dispose()

    if not rows:
        print("No checks recorded yet.")
        return 0

    header = f"{'client':<18}{'total':>8}{'24h':>7}{'7d':>7}{'30d':>7}{'users':>7}  last seen"
    print(header)
    print("-" * len(header))
    mcp_total = 0
    for r in rows:
        client, total, h24, d7, d30, users, last_seen = r
        if client == "mcp":
            mcp_total = total
        last = last_seen.strftime("%Y-%m-%d %H:%M") if last_seen else "-"
        print(f"{client:<18}{total:>8}{h24:>7}{d7:>7}{d30:>7}{users:>7}  {last}")

    print()
    if mcp_total:
        print(
            f"✅ MCP package is being used — {mcp_total} check(s) attributed to 'mcp'."
        )
    else:
        print("ℹ️  No MCP-attributed checks yet (client='mcp' count is 0).")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
