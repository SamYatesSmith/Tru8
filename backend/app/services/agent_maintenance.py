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
    """Infinite loop that sweeps stale pending transactions every 5 minutes."""
    while True:
        await asyncio.sleep(SWEEP_INTERVAL_SECONDS)
        try:
            async with async_session() as session:
                await sweep_stale_pending_transactions(session)
        except Exception:
            logger.exception("Stale-pending sweep failed")


def start_stale_pending_cleanup() -> asyncio.Task:
    """Launch the stale-pending cleanup loop. Call from lifespan()."""
    return asyncio.create_task(_stale_pending_loop())
