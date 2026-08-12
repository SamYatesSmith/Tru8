"""Grant (or inspect) complimentary DASHBOARD checks for a user, by email.

Founder/admin utility for the outreach comp (audit/OUTREACH.md prerequisite D:
~30 checks for recipients who bite, so nobody hits the 3-check wall
mid-evaluation).

This is the DASHBOARD allowance, not the agent rail: the trial gate reads
``max(3, user.credits + user.total_credits_used)`` (usage_ledger.get_usage_snapshot),
so adding N to ``user.credits`` raises a trial user's lifetime limit by N and
every gate, refund and display path honours it with no other change. The
usage_events ledger records USAGE; allocation for trial users lives in these
User fields by design — a grant therefore writes no ledger row.

For agent-API credit (pence), use scripts/grant_credits.py instead.

Run against production (``railway run`` cannot reach the prod DB — its
hostname only resolves inside Railway's network):
    railway ssh "python -m scripts.grant_checks --email someone@example.com"              # inspect
    railway ssh "python -m scripts.grant_checks --email someone@example.com --checks 30"  # grant
"""

import argparse
import asyncio
import sys

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


async def main() -> int:
    parser = argparse.ArgumentParser(
        description="Grant complimentary dashboard checks by email"
    )
    parser.add_argument("--email", required=True)
    parser.add_argument(
        "--checks",
        type=int,
        default=0,
        help="Checks to ADD to the trial allowance (omit to just inspect)",
    )
    args = parser.parse_args()

    if args.checks < 0:
        print("--checks must be positive (this tool only grants)", file=sys.stderr)
        return 2

    from app.core.config import settings  # deferred: import cost + env validation

    db_url = getattr(settings, "DATABASE_URL", "")
    if not db_url:
        print("DATABASE_URL not configured", file=sys.stderr)
        return 2
    if db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

    engine = create_async_engine(db_url)
    try:
        async with engine.begin() as conn:
            row = (
                await conn.execute(
                    text(
                        'SELECT id, email, credits, total_credits_used FROM "user" '
                        "WHERE email = :email"
                    ),
                    {"email": args.email},
                )
            ).first()
            if not row:
                print(f"No user found for email {args.email}", file=sys.stderr)
                return 1

            limit = max(3, row.credits + row.total_credits_used)
            print(
                f"user={row.id} email={row.email} credits={row.credits} "
                f"used={row.total_credits_used} trial_limit={limit}"
            )

            sub = (
                await conn.execute(
                    text(
                        "SELECT status, credits_per_month FROM subscription "
                        "WHERE user_id = :uid AND status IN ('active', 'trialing')"
                    ),
                    {"uid": row.id},
                )
            ).first()
            if sub:
                # The gate uses credits_per_month for subscribers; the trial
                # fields are ignored, so a grant here would change nothing.
                print(
                    f"WARNING: user has an {sub.status} subscription "
                    f"({sub.credits_per_month}/month) — a trial grant has NO effect "
                    "while it is active. Not granting.",
                    file=sys.stderr,
                )
                return 1

            if args.checks:
                updated = (
                    await conn.execute(
                        text(
                            'UPDATE "user" SET credits = credits + :n, '
                            "updated_at = now() WHERE email = :email "
                            "RETURNING credits, total_credits_used"
                        ),
                        {"n": args.checks, "email": args.email},
                    )
                ).first()
                new_limit = max(3, updated.credits + updated.total_credits_used)
                print(
                    f"granted {args.checks} checks -> credits={updated.credits}, "
                    f"trial_limit={new_limit}"
                )
    finally:
        await engine.dispose()

    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
