"""Signups by source — can any channel be credited with a stranger?

The companion to scripts/mcp_usage.py: that one reads Check.client (HOW a
check arrived), this one reads User.signup_source (WHY the person came — the
?src= tag their signup carried). NULL prints as "(unknown)" and is NEVER
folded into a channel: an absent attribution is honest, a fabricated one
kills the wrong channel (audit/OUTREACH.md).

Run locally:
    cd backend && python -m scripts.signup_sources

Run against production (Railway):
    railway run python -m scripts.signup_sources
"""

import asyncio
import sys

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import settings


REPORT_SQL = """
SELECT
    COALESCE(u.signup_source, '(unknown)')                                  AS source,
    COUNT(*)                                                                AS signups,
    COUNT(*) FILTER (WHERE u.created_at > now() - interval '24 hours')      AS last_24h,
    COUNT(*) FILTER (WHERE u.created_at > now() - interval '7 days')        AS last_7d,
    COUNT(*) FILTER (WHERE u.created_at > now() - interval '30 days')       AS last_30d,
    COUNT(c.id)                                                             AS checks,
    COUNT(DISTINCT c.user_id)                                               AS ran_check,
    MAX(u.created_at)                                                       AS last_signup
FROM "user" u
LEFT JOIN "check" c ON c.user_id = u.id
GROUP BY COALESCE(u.signup_source, '(unknown)')
ORDER BY signups DESC;
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
        print("No users recorded yet.")
        return 0

    header = (
        f"{'source':<22}{'signups':>8}{'24h':>6}{'7d':>6}{'30d':>6}"
        f"{'checks':>8}{'ran one':>9}  last signup"
    )
    print(header)
    print("-" * len(header))
    attributed = 0
    for r in rows:
        source, signups, h24, d7, d30, checks, ran, last = r
        if source != "(unknown)":
            attributed += signups
        last_s = last.strftime("%Y-%m-%d") if last else "-"
        print(
            f"{source:<22}{signups:>8}{h24:>6}{d7:>6}{d30:>6}"
            f"{checks:>8}{ran:>9}  {last_s}"
        )

    print()
    if attributed:
        print(f"✅ {attributed} signup(s) carry a source tag.")
    else:
        print(
            "ℹ️  No attributed signups yet — every account predates tagging "
            "or arrived untagged."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
