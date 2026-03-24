"""Tests for /api/v1/agent/credits/* — balance and purchase endpoints.

Covers:
- GET /agent/credits/balance returns correct balance
- GET /agent/credits/balance requires auth → 401
- POST /agent/credits/purchase creates Stripe Checkout session
"""

import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.api.v1.agent import router
from app.core.agent_auth import AgentIdentity, get_agent_identity
from app.core.database import get_session
from app.core.rate_limit import limiter


# ---------------------------------------------------------------------------
# Test app + helpers
# ---------------------------------------------------------------------------

MOCK_USER_ID = "user-credits-001"


def _create_test_app():
    """Build a minimal FastAPI app with the agent router mounted + rate limiter."""
    test_app = FastAPI()
    test_app.state.limiter = limiter
    test_app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    test_app.add_middleware(SlowAPIMiddleware)
    test_app.include_router(router, prefix="/api/v1/agent")
    return test_app


class _MockResult:
    """Mock for SQLAlchemy execute() result."""

    def __init__(self, rows=None, scalar=None):
        self._rows = rows or []
        self._scalar_value = scalar

    def scalar_one_or_none(self):
        return self._scalar_value

    def scalars(self):
        return self

    def all(self):
        return self._rows

    def scalar(self):
        return self._scalar_value


def _mock_session(*execute_returns):
    """Build a mock async session with chained execute() return values."""
    session = AsyncMock()
    results = [_MockResult(**r) for r in execute_returns]
    session.execute = AsyncMock(side_effect=results)
    session.commit = AsyncMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    session.add = MagicMock()
    return session


def _mock_identity_override(user_id=MOCK_USER_ID):
    """Dependency override for get_agent_identity."""

    async def _override():
        return AgentIdentity(
            provider="credit",
            payer_id=user_id,
            user_id=user_id,
        )

    return _override


# ---------------------------------------------------------------------------
# GET /agent/credits/balance
# ---------------------------------------------------------------------------


class TestCreditBalance:
    """GET /api/v1/agent/credits/balance — credit balance query."""

    @pytest.mark.asyncio
    async def test_balance_returns_pence(self):
        """Returns balance in pence and formatted GBP."""
        app = _create_test_app()

        mock_user = MagicMock()
        mock_user.id = MOCK_USER_ID
        mock_user.email = "test@tru8.app"
        mock_user.credit_balance_pence = 1500  # £15.00

        session = _mock_session({"scalar": mock_user})
        app.dependency_overrides[get_agent_identity] = _mock_identity_override()
        app.dependency_overrides[get_session] = lambda: session

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/v1/agent/credits/balance")

        assert resp.status_code == 200
        data = resp.json()
        assert data["balancePence"] == 1500
        assert data["balanceGbp"] == "£15.00"

    @pytest.mark.asyncio
    async def test_balance_requires_auth(self):
        """No auth headers → 401."""
        app = _create_test_app()

        async def _failing_identity():
            from fastapi import HTTPException

            raise HTTPException(
                status_code=401,
                detail="Agent authentication required.",
            )

        app.dependency_overrides[get_agent_identity] = _failing_identity
        session = _mock_session()
        app.dependency_overrides[get_session] = lambda: session

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/v1/agent/credits/balance")

        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# POST /agent/credits/purchase
# ---------------------------------------------------------------------------


class TestCreditPurchase:
    """POST /api/v1/agent/credits/purchase — Stripe Checkout session creation."""

    @pytest.mark.asyncio
    async def test_purchase_valid_pack(self):
        """Valid pack ('20') → creates Stripe Checkout session, returns URL."""
        app = _create_test_app()

        mock_user = MagicMock()
        mock_user.id = MOCK_USER_ID
        mock_user.email = "test@tru8.app"
        mock_user.credit_balance_pence = 0

        session = _mock_session({"scalar": mock_user})
        app.dependency_overrides[get_agent_identity] = _mock_identity_override()
        app.dependency_overrides[get_session] = lambda: session

        mock_checkout_session = MagicMock()
        mock_checkout_session.id = "cs_test_123"
        mock_checkout_session.url = "https://checkout.stripe.com/test"

        from app.core.config import settings as real_settings

        with (
            patch("stripe.checkout.Session.create") as mock_stripe_create,
            patch.object(
                real_settings, "STRIPE_PRICE_ID_CREDIT_PACK_20", "price_20_test"
            ),
            patch.object(
                real_settings, "STRIPE_PRICE_ID_CREDIT_PACK_100", "price_100_test"
            ),
            patch.object(real_settings, "STRIPE_SECRET_KEY", "sk_test_xxx"),
            patch.object(real_settings, "FRONTEND_URL", "http://localhost:3000"),
        ):
            mock_stripe_create.return_value = mock_checkout_session

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.post(
                    "/api/v1/agent/credits/purchase",
                    json={"pack": "20"},
                )

        assert resp.status_code == 200
        data = resp.json()
        assert data["sessionId"] == "cs_test_123"
        assert data["url"] == "https://checkout.stripe.com/test"

    @pytest.mark.asyncio
    async def test_purchase_invalid_pack(self):
        """Invalid pack name → 400."""
        app = _create_test_app()

        session = _mock_session()
        app.dependency_overrides[get_agent_identity] = _mock_identity_override()
        app.dependency_overrides[get_session] = lambda: session

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/v1/agent/credits/purchase",
                json={"pack": "999"},
            )

        assert resp.status_code == 400
        assert "Invalid pack" in resp.json()["detail"]
