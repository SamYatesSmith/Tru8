"""Agent auth dependencies for /api/v1/agent/* routes.

Two dependencies:
  get_agent_identity  — verifies Skyfire token or API key, returns AgentIdentity.
                        No balance check, no charge. Used by retrieval endpoints.
  get_agent_payment   — wraps identity + adds charge() callable + concurrency check.
                        Used by tier endpoints that require payment.

This split prevents accidental balance mutations on retrieval routes.
"""

import hashlib
import logging
from dataclasses import dataclass, field
from typing import Callable, Optional

from fastapi import Depends, HTTPException, Request
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.agent_pricing import get_tier_price
from app.core.config import settings
from app.core.database import get_session
from app.models.agent_transaction import AgentTransaction
from app.models.check import generate_uuid

logger = logging.getLogger(__name__)


@dataclass
class AgentIdentity:
    """Verified agent identity — no payment capability."""

    provider: str  # "skyfire" | "credit"
    payer_id: str
    user_id: str  # resolved tru8 user ID (for lookup scoping)
    token_exp: Optional[float] = None  # JWT expiry (Skyfire only)


@dataclass
class AgentPaymentContext(AgentIdentity):
    """Verified agent identity with payment capability."""

    session: AsyncSession = field(default=None, repr=False)

    async def charge(
        self,
        amount_cents: int,
        tier: str,
        description: str,
        idempotency_key: Optional[str] = None,
        request_hash: Optional[str] = None,
        check_id: Optional[str] = None,
    ) -> AgentTransaction:
        """Create an AgentTransaction and charge the agent.

        Handles idempotency: duplicate key with same request_hash returns cached
        response; duplicate with different request_hash raises 409 Conflict.

        For credit provider: checks and debits balance before creating transaction.
        """
        # Idempotency check
        if idempotency_key:
            if not request_hash:
                raise HTTPException(
                    status_code=400,
                    detail="request_hash required when Idempotency-Key is provided",
                )
            existing = await self.session.execute(
                select(AgentTransaction).where(
                    AgentTransaction.idempotency_key == idempotency_key
                )
            )
            existing_tx = existing.scalar_one_or_none()
            if existing_tx:
                if existing_tx.request_hash != request_hash:
                    raise HTTPException(
                        status_code=409,
                        detail="Idempotency-Key already used with different parameters",
                    )
                return existing_tx

        # Credit provider: check and debit balance
        if self.provider == "credit":
            from app.services.payments.credit_provider import debit_credits

            debited = await debit_credits(self.user_id, amount_cents, self.session)
            if not debited:
                raise HTTPException(
                    status_code=402,
                    detail="Insufficient credit balance. Top up at /agent/credits/purchase.",
                )

        tx = AgentTransaction(
            id=generate_uuid(),
            check_id=check_id,
            provider=self.provider,
            payer_id=self.payer_id,
            tier=tier,
            amount_cents=amount_cents,
            status="pending",
            idempotency_key=idempotency_key,
            request_hash=request_hash,
            tx_metadata={"claim_text_hash": description} if description else None,
        )
        self.session.add(tx)
        await self.session.flush()
        return tx


def compute_request_hash(tier: str, claim_hash: str, compact: bool) -> str:
    """SHA256 of (tier + claim_hash + compact) for idempotency conflict detection."""
    raw = f"{tier}:{claim_hash}:{compact}"
    return hashlib.sha256(raw.encode()).hexdigest()


async def get_agent_identity(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> AgentIdentity:
    """Verify agent credentials — identity only, no balance check, no charge.

    Provider priority: Skyfire header -> API key.
    Used by retrieval endpoints and read-only routes.
    """
    from app.services.payments.skyfire_provider import SkyfirePaymentProvider

    # Try Skyfire first
    skyfire = SkyfirePaymentProvider()
    if await skyfire.can_handle(request):
        token = request.headers["skyfire-pay-id"]
        try:
            payload = await skyfire.verify_jwt_only(token)
        except ValueError as e:
            raise HTTPException(status_code=401, detail=str(e))

        skyfire_user_id = payload.get("sub", "")
        if not skyfire_user_id:
            raise HTTPException(
                status_code=401, detail="Skyfire token missing 'sub' claim"
            )

        # Lazy-create Tru8 user for Skyfire identity
        from app.models.user import User

        result = await session.execute(
            select(User).where(User.external_id == f"skyfire:{skyfire_user_id}")
        )
        user = result.scalar_one_or_none()
        if not user:
            try:
                user = User(
                    id=f"skyfire_{skyfire_user_id}",
                    email=f"{skyfire_user_id}@skyfire.agent",
                    external_id=f"skyfire:{skyfire_user_id}",
                    credits=0,
                )
                session.add(user)
                await session.flush()
                logger.info(f"Created Tru8 user for Skyfire agent: {user.id}")
            except IntegrityError:
                await session.rollback()
                result = await session.execute(
                    select(User).where(User.external_id == f"skyfire:{skyfire_user_id}")
                )
                user = result.scalar_one()

        return AgentIdentity(
            provider="skyfire",
            payer_id=skyfire_user_id,
            user_id=user.id,
            token_exp=payload.get("exp"),
        )

    # Try API key
    api_key = request.headers.get("X-API-Key")
    if api_key:
        from app.core.auth import _verify_api_key

        user_data = await _verify_api_key(api_key, session)
        return AgentIdentity(
            provider="credit",
            payer_id=user_data["id"],
            user_id=user_data["id"],
        )

    raise HTTPException(
        status_code=401,
        detail="Agent authentication required. Use skyfire-pay-id header or X-API-Key.",
    )


async def get_agent_payment(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> AgentPaymentContext:
    """Verify agent credentials + check concurrency limits.

    Used by tier endpoints that require payment.
    """
    identity = await get_agent_identity(request, session)

    # Concurrency limit: max concurrent pipeline runs per principal
    # Only enforced for quick/full (not lookup — lookup doesn't run pipeline)
    concurrent_result = await session.execute(
        text(
            'SELECT COUNT(*) FROM "check" '
            "WHERE user_id = :uid AND status = 'processing'"
        ),
        {"uid": identity.user_id},
    )
    concurrent_count = concurrent_result.scalar()
    if concurrent_count >= settings.MAX_CONCURRENT_ANALYSES:
        raise HTTPException(
            status_code=429,
            detail=f"Max {settings.MAX_CONCURRENT_ANALYSES} concurrent pipeline runs. Retry later.",
            headers={"Retry-After": "30"},
        )

    return AgentPaymentContext(
        provider=identity.provider,
        payer_id=identity.payer_id,
        user_id=identity.user_id,
        token_exp=identity.token_exp,
        session=session,
    )
