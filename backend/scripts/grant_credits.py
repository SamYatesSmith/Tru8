"""Grant (or inspect) prepaid agent credit for a user, by email.

Founder/admin utility — used when Stripe credit packs are unavailable
(e.g. STRIPE_PRICE_ID_CREDIT_PACK_* not configured) or for comp credits.

Run against production (``railway run`` cannot reach the prod DB — its
hostname only resolves inside Railway's network; use ``railway ssh``):
    railway ssh "python -m scripts.grant_credits --email someone@example.com"              # inspect
    railway ssh "python -m scripts.grant_credits --email someone@example.com --pence 500"  # grant £5.00

Adds to User.credit_balance_pence (the agent-credit balance, NOT the
subscription `credits` column).
"""

import argparse
import asyncio
import sys

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import settings


async def main() -> int:
    parser = argparse.ArgumentParser(description="Grant agent credit by email")
    parser.add_argument("--email", required=True)
    parser.add_argument(
        "--pence",
        type=int,
        default=0,
        help="Pence to ADD to credit_balance_pence (omit to just inspect)",
    )
    args = parser.parse_args()

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
                        'SELECT id, email, credit_balance_pence FROM "user" WHERE email = :email'
                    ),
                    {"email": args.email},
                )
            ).first()
            if not row:
                print(f"No user found for email {args.email}", file=sys.stderr)
                return 1

            print(
                f"user={row.id} email={row.email} balance={row.credit_balance_pence}p"
            )

            if args.pence:
                updated = (
                    await conn.execute(
                        text(
                            'UPDATE "user" SET credit_balance_pence = credit_balance_pence + :pence, '
                            "updated_at = now() WHERE email = :email "
                            "RETURNING credit_balance_pence"
                        ),
                        {"pence": args.pence, "email": args.email},
                    )
                ).scalar_one()
                print(
                    f"granted {args.pence}p -> new balance {updated}p (GBP {updated / 100:.2f})"
                )
    finally:
        await engine.dispose()

    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
