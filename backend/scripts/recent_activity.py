"""Who has been in Tru8 - every account, when they FIRST logged in, what they did.

What a row in "user" means: the frontend calls GET /api/v1/users/me on first
login, which auto-creates the row (app/api/v1/users.py::get_or_create_user).
So an account existing IS proof that person signed in at least once, even if
they never ran a check. created_at is that first login.

What this CANNOT see: repeat logins. get_or_create_user returns early for an
existing user without touching updated_at, and Clerk - not us - owns sessions.
So this reports FIRST login, never latest. For latest, use the Clerk Dashboard
-> Users -> sort by "Last active".

Companion to scripts/signup_sources.py (WHY they came) and scripts/mcp_usage.py
(HOW checks arrived). Run locally:
    cd backend && python -m scripts.recent_activity [--days 3]

Against production (railway run cannot reach the prod DB - it is the internal
host; use command-mode ssh, which is non-interactive):
    railway ssh "python -m scripts.recent_activity --days 3"
"""

import argparse
import asyncio
import sys

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import settings


ALL_USERS_SQL = """
SELECT u.email,
       u.created_at                           AS first_login,
       COALESCE(u.signup_source, '(unknown)') AS source,
       COUNT(c.id)                            AS checks,
       MAX(c.created_at)                      AS last_check
FROM "user" u
LEFT JOIN "check" c ON c.user_id = u.id
GROUP BY u.email, u.created_at, u.signup_source
ORDER BY u.created_at DESC
LIMIT 200;
"""

SIGNUPS_SQL = """
SELECT u.email,
       u.created_at,
       COALESCE(u.signup_source, '(unknown)') AS source
FROM "user" u
WHERE u.created_at > now() - make_interval(days => :days)
ORDER BY u.created_at DESC;
"""

ACTIVITY_SQL = """
SELECT u.email,
       COUNT(c.id)                                        AS checks,
       COUNT(*) FILTER (WHERE c.status = 'completed')      AS completed,
       MAX(c.created_at)                                   AS last_check,
       STRING_AGG(DISTINCT COALESCE(c.client, 'web'), ',') AS clients
FROM "check" c
JOIN "user" u ON u.id = c.user_id
WHERE c.created_at > now() - make_interval(days => :days)
GROUP BY u.email
ORDER BY last_check DESC;
"""

TOTALS_SQL = """
SELECT (SELECT COUNT(*) FROM "user")  AS users_total,
       (SELECT COUNT(*) FROM "check") AS checks_total,
       (SELECT MAX(created_at) FROM "check") AS last_check_ever;
"""


def _fmt(dt) -> str:
    return dt.strftime("%Y-%m-%d %H:%M") if dt else "-"


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=3, help="window in days (default 3)")
    args = ap.parse_args()

    db_url = getattr(settings, "DATABASE_URL", "")
    if not db_url:
        print("DATABASE_URL not configured", file=sys.stderr)
        return 2
    if db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

    engine = create_async_engine(db_url)
    try:
        async with engine.connect() as conn:
            p = {"days": args.days}
            everyone = (await conn.execute(text(ALL_USERS_SQL))).all()
            signups = (await conn.execute(text(SIGNUPS_SQL), p)).all()
            activity = (await conn.execute(text(ACTIVITY_SQL), p)).all()
            totals = (await conn.execute(text(TOTALS_SQL))).one()
    finally:
        await engine.dispose()

    print()
    print(f"=== EVERY ACCOUNT ({len(everyone)}), newest first ===")
    print("An account exists => that person logged in at least once.")
    print("first_login is their FIRST sign-in; repeat logins are not recorded.")
    print()
    for r in everyone:
        checks = f"{r.checks} checks" if r.checks else "no checks"
        last = f", last {_fmt(r.last_check)}" if r.checks else ""
        print(
            f"   {r.email:<40} first login {_fmt(r.first_login)}  "
            f"src={r.source:<12} {checks}{last}"
        )

    print()
    print(f"=== Last {args.days} days ===")
    print("(check activity is NOT login activity - see module docstring)")
    print()

    print(f"-- First logged in ({len(signups)}) --")
    if not signups:
        print("   none")
    for r in signups:
        print(f"   {r.email:<40} {_fmt(r.created_at)}  src={r.source}")

    print()
    print(f"-- Ran a check ({len(activity)}) --")
    if not activity:
        print("   none")
    for r in activity:
        print(
            f"   {r.email:<40} {r.checks:>3} checks "
            f"({r.completed} completed)  last {_fmt(r.last_check)}  [{r.clients}]"
        )

    print()
    print(
        f"All time: {totals.users_total} users, {totals.checks_total} checks, "
        f"last check ever {_fmt(totals.last_check_ever)}"
    )
    print("Latest logins: Clerk Dashboard -> Users -> sort by 'Last active'.")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
