"""Agent transaction maintenance — stale-pending cleanup.

Lightweight periodic sweep that marks orphaned pending transactions
as unsettled. Catches process crashes between handler commit and
audit middleware update.

Launched as an asyncio.create_task() loop from the FastAPI lifespan
context — same pattern as video recommendations and auto-archiving.
No Celery dependency.
"""

import asyncio
import logging
from datetime import datetime, timedelta

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session

logger = logging.getLogger(__name__)

SWEEP_INTERVAL_SECONDS = 300  # 5 minutes
STALE_THRESHOLD_MINUTES = 10


async def sweep_stale_pending_transactions(session: AsyncSession) -> int:
    """Mark stale pending AgentTransactions as unsettled.

    Returns the number of rows updated.
    """
    threshold = datetime.utcnow() - timedelta(minutes=STALE_THRESHOLD_MINUTES)

    result = await session.execute(
        text(
            """
            UPDATE agent_transaction
            SET status = 'unsettled',
                metadata = COALESCE(metadata, '{}'::jsonb) || '{"settlement_reason": "stale_pending"}'::jsonb
            WHERE status = 'pending'
              AND created_at < :threshold
        """
        ),
        {"threshold": threshold},
    )
    await session.commit()

    count = result.rowcount
    if count > 0:
        logger.warning(
            "stale_pending_sweep",
            extra={"updated_count": count, "threshold": threshold.isoformat()},
        )
    return count


async def _stale_pending_loop() -> None:
    """Infinite loop, every 5 minutes: sweep stale pending transactions, then
    stale checks.

    The check sweep used to run at boot only (hang-proofing W2). A check
    stranded by a deploy seconds after it started was too young for the boot
    sweep of the NEW instance (cutoff = watchdog + grace) and then had no
    second chance — check 5525b573 sat `processing` with its 15p unrefunded
    (2026-09-11). Running the same sweep on this loop closes that gap; it is
    deploy-overlap safe by construction (only rows older than the ceiling are
    ever touched), so a periodic run is as safe as the boot run.
    """
    while True:
        await asyncio.sleep(SWEEP_INTERVAL_SECONDS)
        try:
            async with async_session() as session:
                await sweep_stale_pending_transactions(session)
        except Exception:
            logger.exception("Stale-pending sweep failed")
        try:
            from app.core.inflight import sweep_stale_checks

            await sweep_stale_checks()
        except Exception:
            logger.exception("Periodic stale-check sweep failed")


def start_stale_pending_cleanup() -> asyncio.Task:
    """Launch the stale-pending cleanup loop. Call from lifespan()."""
    return asyncio.create_task(_stale_pending_loop())
