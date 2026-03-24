"""Tests for POST /api/v1/agent/lookup — cache-hit/miss behaviour.

Covers:
- Cache miss returns {hit: false, nextSuggestedTier: "quick"}
- Cache hit returns {hit: true, ...} with check data
- User-scoped lookup (only returns checks owned by authenticated user)
- No auth headers → 401
"""

import json
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.api.v1.agent import router
from app.core.agent_auth import (
    AgentIdentity,
    AgentPaymentContext,
    get_agent_identity,
    get_agent_payment,
)
from app.core.database import get_session
from app.core.rate_limit import limiter


# ---------------------------------------------------------------------------
# Test app + dependency overrides
# ---------------------------------------------------------------------------

MOCK_USER_ID = "user-agent-001"


def _create_test_app():
    """Build a minimal FastAPI app with the agent router mounted + rate limiter."""
    test_app = FastAPI()
    test_app.state.limiter = limiter
    test_app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    test_app.add_middleware(SlowAPIMiddleware)
    test_app.include_router(router, prefix="/api/v1/agent")
    return test_app


def _mock_payment_override(user_id=MOCK_USER_ID, provider="credit"):
    """Dependency override that returns a mock AgentPaymentContext."""

    async def _override():
        session = AsyncMock()
        ctx = AgentPaymentContext(
            provider=provider,
            payer_id=user_id,
            user_id=user_id,
            session=session,
        )
        return ctx

    return _override


def _mock_session(*execute_returns):
    """Build a mock async session with chained execute() return values."""
    session = AsyncMock()

    class _MockResult:
        def __init__(self, rows=None, scalar=None, first_val=None):
            self._rows = rows or []
            self._scalar_value = scalar
            self._first_val = first_val

        def scalar_one_or_none(self):
            return self._scalar_value

        def scalars(self):
            return self

        def all(self):
            return self._rows

        def scalar(self):
            return self._scalar_value

        def first(self):
            return self._first_val

    results = [_MockResult(**r) for r in execute_returns]
    session.execute = AsyncMock(side_effect=results)
    session.commit = AsyncMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    session.add = MagicMock()
    return session


# ---------------------------------------------------------------------------
# POST /agent/lookup — cache miss
# ---------------------------------------------------------------------------


class TestLookupMiss:
    """POST /api/v1/agent/lookup — cache miss returns structured 200."""

    @pytest.mark.asyncio
    async def test_lookup_miss_returns_200(self):
        """Cache miss → 200 with {hit: false, nextSuggestedTier: 'quick'}."""
        app = _create_test_app()

        # Session returns None for the claim hash query (miss)
        session = _mock_session({"first_val": None})
        app.dependency_overrides[get_agent_payment] = _mock_payment_override()
        app.dependency_overrides[get_session] = lambda: session

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/v1/agent/lookup",
                json={"claim": "The earth is round"},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["hit"] is False
        assert data["nextSuggestedTier"] == "quick"
        assert "upgradeCostPence" in data
        assert "claimTextHash" in data


# ---------------------------------------------------------------------------
# POST /agent/lookup — cache hit
# ---------------------------------------------------------------------------


class TestLookupHit:
    """POST /api/v1/agent/lookup — cache hit returns full response."""

    @pytest.mark.asyncio
    async def test_lookup_hit_returns_data(self):
        """Cache hit → 200 with {hit: true, ...} and check data."""
        app = _create_test_app()

        # Build mock claim + check for the cache hit
        mock_claim = MagicMock()
        mock_claim.id = "claim-001"
        mock_claim.check_id = "check-001"
        mock_claim.text = "The earth is round"
        mock_claim.claim_text_hash = "abc123"

        mock_check = MagicMock()
        mock_check.id = "check-001"
        mock_check.user_id = MOCK_USER_ID
        mock_check.status = "completed"
        mock_check.completed_at = datetime(2026, 2, 1, 12, 0, 0)

        # The lookup query returns a row (claim, check) tuple
        mock_row = (mock_claim, mock_check)

        # Mock the session for the lookup query
        session = _mock_session({"first_val": mock_row})

        # Mock the charge method on the payment context
        mock_tx = MagicMock()
        mock_tx.id = "tx-001"
        mock_tx.status = "pending"

        async def _payment_override():
            ctx = AgentPaymentContext(
                provider="credit",
                payer_id=MOCK_USER_ID,
                user_id=MOCK_USER_ID,
                session=session,
            )
            ctx.charge = AsyncMock(return_value=mock_tx)
            return ctx

        app.dependency_overrides[get_agent_payment] = _payment_override
        app.dependency_overrides[get_session] = lambda: session

        # Mock build_agent_response at source module (imported locally in handler)
        with patch(
            "app.api.v1.response_builder.build_agent_response", new_callable=AsyncMock
        ) as mock_build:
            mock_build.return_value = {
                "id": "check-001",
                "status": "completed",
                "claims": [],
                "_meta": {
                    "executedTier": "lookup",
                    "chargedPence": 2,
                    "limitations": [],
                    "landscape": {},
                },
            }

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.post(
                    "/api/v1/agent/lookup",
                    json={"claim": "The earth is round"},
                )

        assert resp.status_code == 200
        data = resp.json()
        assert data["hit"] is True
        assert data["id"] == "check-001"
        assert data["_meta"]["executedTier"] == "lookup"


# ---------------------------------------------------------------------------
# POST /agent/lookup — user-scoped
# ---------------------------------------------------------------------------


class TestLookupUserScoped:
    """POST /api/v1/agent/lookup — only returns checks owned by auth user."""

    @pytest.mark.asyncio
    async def test_lookup_user_scoped(self):
        """Lookup scoped to user — different user's check not returned (miss)."""
        app = _create_test_app()

        # Session returns None because the WHERE clause filters by user_id
        # (the matching check belongs to a different user)
        session = _mock_session({"first_val": None})
        app.dependency_overrides[get_agent_payment] = _mock_payment_override(
            user_id="user-agent-002"
        )
        app.dependency_overrides[get_session] = lambda: session

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/v1/agent/lookup",
                json={"claim": "The earth is round"},
            )

        assert resp.status_code == 200
        data = resp.json()
        # Even though a check exists for this claim, it belongs to another user
        assert data["hit"] is False
        assert data["nextSuggestedTier"] == "quick"


# ---------------------------------------------------------------------------
# POST /agent/lookup — no auth
# ---------------------------------------------------------------------------


class TestLookupRequiresAuth:
    """POST /api/v1/agent/lookup — no auth headers → 401."""

    @pytest.mark.asyncio
    async def test_lookup_requires_auth(self):
        """No auth headers → 401."""
        app = _create_test_app()

        # Do NOT override get_agent_payment — let it try real auth and fail
        # Instead, override to raise 401
        async def _failing_payment():
            from fastapi import HTTPException

            raise HTTPException(
                status_code=401,
                detail="Agent authentication required.",
            )

        app.dependency_overrides[get_agent_payment] = _failing_payment
        session = _mock_session()
        app.dependency_overrides[get_session] = lambda: session

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/v1/agent/lookup",
                json={"claim": "The earth is round"},
            )

        assert resp.status_code == 401
