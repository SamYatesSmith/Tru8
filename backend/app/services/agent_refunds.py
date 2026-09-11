"""Agent-rail refunds for checks that died without their request handler.

Why (2026-09-11): the deploy-shutdown guard and the stale sweep
(`app/core/inflight.py`) refund through the DASHBOARD usage ledger
(`refund_usage`), which is a no-op for agent checks (`credits_used=0`), and
agent runs never registered in-flight at all. A `tru8_check` that landed on
the old container seconds before a deploy (check 5525b573, 12:27:02 UTC)
charged 15p, died mid-pipeline, stayed `processing` forever and was never
refunded; the stale-pending sweeper marked its transaction `unsettled` and
returned nothing. Same class as the 2026-07-21 fix (57e7dcde), which only
covered dashboard credits.

This helper is the agent-rail twin of `refund_usage`: given a stranded check,
find its AgentTransaction(s), refund the credit balance where the money is
ours to return (credit provider), mark the transaction refunded, and record
why. It never raises — a refund failure on this rail must not block the
dashboard refund + fail marking in the sweep — but it logs at ERROR so the
loss is visible.
"""

from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.agent_transaction import AgentTransaction

logger = logging.getLogger(__name__)

# Transactions that already settled the money question one way or the other.
_ALREADY_SETTLED = ("refunded", "failed")

STRANDED_REASON = "stranded"


async def refund_stranded_agent_transaction(
    session: AsyncSession,
    check_id: str,
    *,
    user_id: Optional[str] = None,
    reason: str = STRANDED_REASON,
) -> int:
    """Refund the agent-rail charge(s) behind a check that will never finish.

    Returns the number of transactions refunded (credit rail) or marked
    unsettled (rails we cannot refund from here). Idempotent: a transaction
    already `refunded`/`failed` is left alone.
    """
    try:
        result = await session.execute(
            select(AgentTransaction).where(AgentTransaction.check_id == check_id)
        )
        txs = [tx for tx in result.scalars().all() if isinstance(tx, AgentTransaction)]
    except Exception as e:  # noqa: BLE001 — never block the sweep
        logger.error(f"[AGENT REFUND] Could not read transactions for {check_id}: {e}")
        return 0

    touched = 0
    for tx in txs:
        if tx.status in _ALREADY_SETTLED:
            continue
        try:
            if tx.provider == "credit":
                from app.services.payments.credit_provider import refund_credits

                # For the credit rail the payer IS the tru8 user who owns the
                # check; prefer the check's owner when the caller knows it.
                await refund_credits(user_id or tx.payer_id, tx.amount_pence, session)
                tx.status = "refunded"
                logger.warning(
                    f"[AGENT REFUND] Refunded {tx.amount_pence}p for stranded check "
                    f"{check_id} (tx {tx.id}, reason={reason})"
                )
            else:
                # Skyfire / x402: nothing to return from here; make the
                # settlement question visible instead of leaving 'pending'.
                tx.status = "unsettled"
                logger.warning(
                    f"[AGENT REFUND] Marked {tx.provider} tx {tx.id} unsettled for "
                    f"stranded check {check_id} (reason={reason})"
                )
            meta = dict(tx.tx_metadata or {})
            meta["settlement_reason"] = reason
            tx.tx_metadata = meta
            session.add(tx)
            touched += 1
        except Exception as e:  # noqa: BLE001
            logger.error(
                f"[AGENT REFUND] Could not refund tx {getattr(tx, 'id', '?')} for "
                f"check {check_id}: {e}"
            )
    return touched
