"""Tests for POST /api/v1/agent/quick — reduced pipeline tier.

Covers:
- Quick returns response with _meta block including limitations
- _meta.limitations contains exactly 6 items
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

from app.api.v1.agent import QUICK_LIMITATIONS, router
from app.core.agent_auth import AgentPaymentContext, get_agent_payment
from app.core.database import get_session
from app.core.rate_limit import limiter


# ---------------------------------------------------------------------------
# Test app + helpers
# ---------------------------------------------------------------------------

MOCK_USER_ID = "user-quick-001"


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
# POST /agent/quick — response with _meta
# ---------------------------------------------------------------------------


class TestQuickEndpoint:
    """POST /api/v1/agent/quick — reduced pipeline with limitations."""

    @pytest.mark.asyncio
    async def test_quick_returns_response_with_meta(self):
        """Quick pipeline returns response with _meta block containing limitations."""
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

        # Mock _run_agent_pipeline directly — it handles all internal pipeline logic
        mock_response = JSONResponse(
            content={
                "id": "check-quick-001",
                "status": "completed",
                "claims": [{"text": "Test claim"}],
                "_meta": {
                    "executedTier": "quick",
                    "chargedCents": 7,
                    "limitations": QUICK_LIMITATIONS,
                    "landscape": {},
                },
            },
            headers={
                "X-Check-Id": "check-quick-001",
                "X-Tru8-Tx-Id": "tx-quick-001",
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
                    "/api/v1/agent/quick",
                    json={"claim": "The earth is round"},
                )

        assert resp.status_code == 200
        data = resp.json()
        assert "_meta" in data
        assert data["_meta"]["executedTier"] == "quick"
        assert data["_meta"]["chargedCents"] == 7
        assert isinstance(data["_meta"]["limitations"], list)
        assert len(data["_meta"]["limitations"]) > 0

    @pytest.mark.asyncio
    async def test_quick_meta_limitations(self):
        """QUICK_LIMITATIONS contains exactly 6 items."""
        assert len(QUICK_LIMITATIONS) == 6
        assert "heuristic_classification" in QUICK_LIMITATIONS
        assert "no_factcheck_lookup" in QUICK_LIMITATIONS
        assert "no_api_sources" in QUICK_LIMITATIONS
        assert "no_llm_relevance_scoring" in QUICK_LIMITATIONS
        assert "no_coverage_recovery" in QUICK_LIMITATIONS
        assert "no_query_answering" in QUICK_LIMITATIONS
