"""Prepaid credit balance helpers — API key agents with GBP balance.

Agents with API keys can use prepaid GBP balance (stored as integer pence).
On pipeline failure, the caller (agent.py) refunds by incrementing
credit_balance_pence and marking AgentTransaction.status = "refunded".

All balance mutations use atomic SQL (UPDATE ... WHERE balance >= amount)
to prevent race conditions on concurrent requests.
"""

import logging

from sqlalchemy import update as sa_update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User

logger = logging.getLogger(__name__)


async def debit_credits(user_id: str, amount_pence: int, session: AsyncSession) -> bool:
    """Atomically decrement credit balance using SQL-level WHERE guard.

    Uses UPDATE ... WHERE balance >= amount so two concurrent requests
    cannot both pass the check — the second will see rowcount=0.
    Returns True on success, False if insufficient or user not found.
    """
    result = await session.execute(
        sa_update(User)
        .where(User.id == user_id, User.credit_balance_pence >= amount_pence)
        .values(credit_balance_pence=User.credit_balance_pence - amount_pence)
    )
    await session.flush()
    if result.rowcount == 0:
        logger.warning(
            f"Debit failed for user {user_id}: insufficient balance or user not found "
            f"(attempted {amount_pence}p)"
        )
        return False
    logger.info(f"Debited {amount_pence}p from user {user_id}")
    return True


async def refund_credits(
    user_id: str, amount_pence: int, session: AsyncSession
) -> None:
    """Refund credits by atomically incrementing balance at SQL level."""
    result = await session.execute(
        sa_update(User)
        .where(User.id == user_id)
        .values(credit_balance_pence=User.credit_balance_pence + amount_pence)
    )
    await session.flush()
    if result.rowcount == 0:
        logger.error(
            f"Refund failed: user {user_id} not found (attempted {amount_pence}p refund)"
        )
        return
    logger.info(f"Refunded {amount_pence}p to user {user_id}")
