"""Tests for GET /api/v1/agent/result/{check_id} — unpaid result retrieval.

Covers:
- Success: returns check data for completed check owned by user
- Wrong user: check owned by different user → 404
- Not completed: check still processing → 409
"""

import json
import uuid
from datetime import datetime
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

MOCK_USER_ID = "user-retrieval-001"


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


def _make_check(check_id="check-001", user_id=MOCK_USER_ID, status="completed"):
    """Build a MagicMock resembling a Check DB row."""
    c = MagicMock()
    c.id = check_id
    c.user_id = user_id
    c.status = status
    c.input_type = "text"
    c.input_content = json.dumps({"content": "test claim"})
    c.completed_at = datetime(2026, 2, 1, 12, 0, 0)
    return c


# ---------------------------------------------------------------------------
# GET /agent/result/{check_id} — success
# ---------------------------------------------------------------------------


class TestGetResultSuccess:
    """GET /api/v1/agent/result/{id} — returns check data."""

    @pytest.mark.asyncio
    async def test_get_result_success(self):
        """Completed check owned by user → 200 with check data."""
        app = _create_test_app()

        check = _make_check(check_id="check-ret-001", user_id=MOCK_USER_ID)
        session = _mock_session({"scalar": check})

        app.dependency_overrides[get_agent_identity] = _mock_identity_override()
        app.dependency_overrides[get_session] = lambda: session

        with patch(
            "app.api.v1.response_builder.build_agent_response", new_callable=AsyncMock
        ) as mock_build:
            mock_build.return_value = {
                "id": "check-ret-001",
                "status": "completed",
                "claims": [{"text": "Test claim"}],
                "_meta": {
                    "executedTier": "full",
                    "chargedPence": 0,
                    "limitations": [],
                    "landscape": {},
                },
            }

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.get("/api/v1/agent/result/check-ret-001")

        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == "check-ret-001"
        assert data["status"] == "completed"
        assert data["_meta"]["chargedPence"] == 0  # Retrieval is free


# ---------------------------------------------------------------------------
# GET /agent/result/{check_id} — wrong user
# ---------------------------------------------------------------------------


class TestGetResultWrongUser:
    """GET /api/v1/agent/result/{id} — check owned by different user → 404."""

    @pytest.mark.asyncio
    async def test_get_result_wrong_user_404(self):
        """Check owned by different user → 404."""
        app = _create_test_app()

        # Check belongs to user-other, but auth is user-retrieval-001
        check = _make_check(
            check_id="check-ret-002",
            user_id="user-other",
            status="completed",
        )
        session = _mock_session({"scalar": check})

        app.dependency_overrides[get_agent_identity] = _mock_identity_override()
        app.dependency_overrides[get_session] = lambda: session

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/v1/agent/result/check-ret-002")

        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()


# ---------------------------------------------------------------------------
# GET /agent/result/{check_id} — not completed
# ---------------------------------------------------------------------------


class TestGetResultNotCompleted:
    """GET /api/v1/agent/result/{id} — check still processing → 200 with status (O-06)."""

    @pytest.mark.asyncio
    async def test_get_result_not_completed_returns_status(self):
        """Check still processing → 200 with processing status for async polling."""
        app = _create_test_app()

        check = _make_check(
            check_id="check-ret-003",
            user_id=MOCK_USER_ID,
            status="processing",
        )
        session = _mock_session({"scalar": check})

        app.dependency_overrides[get_agent_identity] = _mock_identity_override()
        app.dependency_overrides[get_session] = lambda: session

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/v1/agent/result/check-ret-003")

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "processing"
        assert data["checkId"] == "check-ret-003"
        assert data["hit"] is False
