"""Tests for POST /api/v1/agent/full — complete pipeline tier.

Covers:
- Full returns response with _meta block
- _meta.limitations is empty list (full pipeline has no limitations)
"""

import json
import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from httpx import ASGITransport, AsyncClient

from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.api.v1.agent import router
from app.core.agent_auth import AgentPaymentContext, get_agent_payment
from app.core.database import get_session
from app.core.rate_limit import limiter


# ---------------------------------------------------------------------------
# Test app + helpers
# ---------------------------------------------------------------------------

MOCK_USER_ID = "user-full-001"


def _create_test_app():
    """Build a minimal FastAPI app with the agent router mounted + rate limiter."""
    test_app = FastAPI()
    test_app.state.limiter = limiter
    test_app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    test_app.add_middleware(SlowAPIMiddleware)
    test_app.include_router(router, prefix="/api/v1/agent")
    return test_app


def _mock_session():
    """Build a mock async session."""
    session = AsyncMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    session.add = MagicMock()
    return session


# ---------------------------------------------------------------------------
# POST /agent/full — response with _meta
# ---------------------------------------------------------------------------


class TestFullEndpoint:
    """POST /api/v1/agent/full — complete pipeline with no limitations."""

    @pytest.mark.asyncio
    async def test_full_returns_response_with_meta(self):
        """Full pipeline returns response with _meta block."""
        app = _create_test_app()
        session = _mock_session()

        async def _payment_override():
            ctx = AgentPaymentContext(
                provider="credit",
                payer_id=MOCK_USER_ID,
                user_id=MOCK_USER_ID,
                session=session,
            )
            return ctx

        app.dependency_overrides[get_agent_payment] = _payment_override
        app.dependency_overrides[get_session] = lambda: session

        mock_response = JSONResponse(
            content={
                "id": "check-full-001",
                "status": "completed",
                "claims": [{"text": "Test claim"}],
                "_meta": {
                    "executedTier": "full",
                    "chargedCents": 15,
                    "limitations": [],
                    "landscape": {},
                },
            },
            headers={
                "X-Check-Id": "check-full-001",
                "X-Tru8-Tx-Id": "tx-full-001",
            },
        )

        with patch(
            "app.api.v1.agent._run_agent_pipeline",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.post(
                    "/api/v1/agent/full",
                    json={"claim": "The earth is round"},
                )

        assert resp.status_code == 200
        data = resp.json()
        assert "_meta" in data
        assert data["_meta"]["executedTier"] == "full"
        assert data["_meta"]["chargedCents"] == 15

    @pytest.mark.asyncio
    async def test_full_meta_limitations_empty(self):
        """Full pipeline _meta.limitations is empty list (no limitations)."""
        app = _create_test_app()
        session = _mock_session()

        async def _payment_override():
            ctx = AgentPaymentContext(
                provider="credit",
                payer_id=MOCK_USER_ID,
                user_id=MOCK_USER_ID,
                session=session,
            )
            return ctx

        app.dependency_overrides[get_agent_payment] = _payment_override
        app.dependency_overrides[get_session] = lambda: session

        mock_response = JSONResponse(
            content={
                "id": "check-full-002",
                "status": "completed",
                "claims": [],
                "_meta": {
                    "executedTier": "full",
                    "chargedCents": 15,
                    "limitations": [],
                    "landscape": {},
                },
            },
            headers={
                "X-Check-Id": "check-full-002",
                "X-Tru8-Tx-Id": "tx-full-002",
            },
        )

        with patch(
            "app.api.v1.agent._run_agent_pipeline",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.post(
                    "/api/v1/agent/full",
                    json={"claim": "Testing limitations"},
                )

        assert resp.status_code == 200
        data = resp.json()
        assert data["_meta"]["limitations"] == []
