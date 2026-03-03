"""Prepaid credit payment provider — API key agents with USD balance.

Agents with API keys can use prepaid USD balance (stored as integer cents).
On pipeline failure, the caller (agent.py) refunds by incrementing
credit_balance_cents and marking AgentTransaction.status = "refunded".
"""

import logging

from fastapi import Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User

from .base import PaymentProvider, PaymentVerification

logger = logging.getLogger(__name__)


class CreditPaymentProvider(PaymentProvider):
    """Prepaid USD balance via API key."""

    async def can_handle(self, request: Request) -> bool:
        return "x-api-key" in request.headers

    async def verify_and_charge(
        self, request: Request, amount_cents: int, description: str
    ) -> PaymentVerification:
        raise NotImplementedError(
            "Credit charges are handled via AgentPaymentContext.charge(). "
            "This method is not used directly."
        )


async def check_credit_balance(
    user_id: str, amount_cents: int, session: AsyncSession
) -> bool:
    """Check if user has sufficient credit balance. Returns True if sufficient."""
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        return False
    return user.credit_balance_cents >= amount_cents


async def debit_credits(user_id: str, amount_cents: int, session: AsyncSession) -> bool:
    """Atomically decrement credit balance. Returns True on success, False if insufficient."""
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or user.credit_balance_cents < amount_cents:
        return False
    user.credit_balance_cents -= amount_cents
    await session.flush()
    logger.info(
        f"Debited {amount_cents} cents from user {user_id}. New balance: {user.credit_balance_cents}"
    )
    return True


async def refund_credits(
    user_id: str, amount_cents: int, session: AsyncSession
) -> None:
    """Refund credits by incrementing balance."""
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user:
        user.credit_balance_cents += amount_cents
        await session.flush()
        logger.info(
            f"Refunded {amount_cents} cents to user {user_id}. New balance: {user.credit_balance_cents}"
        )
