"""Show or release payment holds (Stripe disputes).

    python -m scripts.payment_hold show <user_id>
    python -m scripts.payment_hold release <dispute_id>

A hold lifts by itself when Stripe closes a dispute as won (or an inquiry
closes with no funds moved). Use `release` for anything else — e.g. a lost
dispute settled with the customer directly. Against production:
`railway ssh` into the backend and run it there.

Design: audit/2026-11-02_payment_hold_design.md.
"""

import asyncio
import sys
from datetime import datetime, timezone

from sqlalchemy import select

from app.core.database import async_session
from app.models.payment_dispute import PaymentDispute
from app.services.payment_hold import RESOLVED_STATUSES


async def show(user_id: str) -> int:
    async with async_session() as session:
        rows = (
            (
                await session.execute(
                    select(PaymentDispute).where(PaymentDispute.user_id == user_id)
                )
            )
            .scalars()
            .all()
        )
    if not rows:
        print(f"No disputes recorded for {user_id}.")
        return 0
    held = any(r.status not in RESOLVED_STATUSES for r in rows)
    print(f"{user_id}: {'ON HOLD' if held else 'not held'}")
    for r in rows:
        print(
            f"  {r.id}  charge={r.charge_id}  status={r.status}  updated={r.updated_at}"
        )
    return 0


async def release(dispute_id: str) -> int:
    async with async_session() as session:
        row = await session.get(PaymentDispute, dispute_id)
        if row is None:
            print(f"No dispute {dispute_id}.")
            return 1
        before = row.status
        row.status = "released"
        row.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
        await session.commit()
        print(f"Released {dispute_id} (user {row.user_id}): {before} -> released")
    return 0


def main(argv) -> int:
    if len(argv) != 3 or argv[1] not in ("show", "release"):
        print(__doc__)
        return 2
    action, arg = argv[1], argv[2]
    return asyncio.run(show(arg) if action == "show" else release(arg))


if __name__ == "__main__":
    sys.exit(main(sys.argv))
