"""Prepaid credit payment provider — API key agents with GBP balance.

Agents with API keys can use prepaid GBP balance (stored as integer pence).
On pipeline failure, the caller (agent.py) refunds by incrementing
credit_balance_pence and marking AgentTransaction.status = "refunded".

All balance mutations use atomic SQL (UPDATE ... WHERE balance >= amount)
to prevent race conditions on concurrent requests.
"""

import logging

from fastapi import Request
from sqlalchemy import select, update as sa_update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User

from .base import PaymentProvider, PaymentVerification

logger = logging.getLogger(__name__)


class CreditPaymentProvider(PaymentProvider):
    """Prepaid GBP balance via API key."""

    async def can_handle(self, request: Request) -> bool:
        return "x-api-key" in request.headers

    async def verify_and_charge(
        self, request: Request, amount_pence: int, description: str
    ) -> PaymentVerification:
        raise NotImplementedError(
            "Credit charges are handled via AgentPaymentContext.charge(). "
            "This method is not used directly."
        )


async def check_credit_balance(
    user_id: str, amount_pence: int, session: AsyncSession
) -> bool:
    """Check if user has sufficient credit balance. Returns True if sufficient."""
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        return False
    return user.credit_balance_pence >= amount_pence


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
