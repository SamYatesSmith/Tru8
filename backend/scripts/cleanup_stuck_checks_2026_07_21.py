"""One-off cleanup: 2026-07-21 deploy outage.

The fa35465 deploy cutover killed two in-flight checks mid-pipeline
(confirmed in Railway logs: 'Started server process [1]' lands mid-retrieval
for f2f97f6e; 57e7dcde died in an earlier restart). Both rows are stuck
'processing' with 1 credit burned each.

Marks both failed with an honest error message + refunds via
usage_ledger.refund_usage (idempotent — safe to re-run).

Run: railway run python -m scripts.cleanup_stuck_checks_2026_07_21
"""

import asyncio
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

STUCK = [
    "57e7dcde-76fc-46fc-b938-3c6a31ea4310",
    "f2f97f6e-d6cd-4342-9b85-2f259c0eae74",
]

ERROR_MSG = (
    "This check was interrupted by a platform deployment and could not "
    "complete. Your credit has been refunded."
)


async def main() -> None:
    from sqlmodel import select

    from app.core.database import async_session
    from app.models.check import Check
    from app.services.usage_ledger import refund_usage

    async with async_session() as session:
        for check_id in STUCK:
            result = await session.execute(select(Check).where(Check.id == check_id))
            check = result.scalar_one_or_none()
            if not check:
                print(f"NOT FOUND: {check_id}")
                continue
            print(
                f"{check_id}: status={check.status} credits_used={check.credits_used}"
            )
            if check.status not in ("processing", "pending", "waiting_for_selection"):
                print("  -> not stuck, skipping")
                continue

            refunded = await refund_usage(session, check_id)
            check.status = "failed"
            check.error_message = ERROR_MSG
            session.add(check)
            print(f"  -> marked failed, refund={'OK' if refunded else 'FAILED'}")

        await session.commit()
        print("committed")


if __name__ == "__main__":
    asyncio.run(main())
