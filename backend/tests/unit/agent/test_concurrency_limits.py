"""Tests for agent concurrency limits — max concurrent pipeline runs.

Covers:
- Max concurrent pipeline runs exceeded → 429 Too Many Requests
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.core.agent_auth import AgentIdentity, AgentPaymentContext, get_agent_payment


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _MockResult:
    """Mock for SQLAlchemy execute() result."""

    def __init__(self, scalar=None):
        self._scalar_value = scalar

    def scalar_one_or_none(self):
        return self._scalar_value

    def scalar(self):
        return self._scalar_value


def _mock_session(concurrent_count=0):
    """Build a mock async session where concurrent check count is configurable."""
    session = AsyncMock()
    session.execute = AsyncMock(return_value=_MockResult(scalar=concurrent_count))
    session.commit = AsyncMock()
    session.flush = AsyncMock()
    session.add = MagicMock()
    return session


# ---------------------------------------------------------------------------
# Concurrency limit exceeded → 429
# ---------------------------------------------------------------------------


class TestConcurrencyLimit:
    """get_agent_payment enforces max concurrent pipeline runs."""

    @pytest.mark.asyncio
    async def test_concurrent_limit_exceeded_429(self):
        """Max concurrent pipeline runs reached → 429 Too Many Requests.

        get_agent_payment checks the count of processing checks for the user.
        When at or above MAX_CONCURRENT_ANALYSES, it raises HTTPException 429.
        """
        mock_request = MagicMock()
        # Set up headers to simulate API key auth
        mock_request.headers = {"x-api-key": "test-key-123"}

        # Mock get_agent_identity to return a valid identity
        mock_identity = AgentIdentity(
            provider="credit",
            payer_id="user-concurrent-001",
            user_id="user-concurrent-001",
        )

        # Session returns concurrent_count >= MAX_CONCURRENT_ANALYSES
        session = _mock_session(concurrent_count=3)

        with (
            patch(
                "app.core.agent_auth.get_agent_identity",
                new_callable=AsyncMock,
                return_value=mock_identity,
            ),
            patch("app.core.agent_auth.settings") as mock_settings,
        ):
            mock_settings.MAX_CONCURRENT_ANALYSES = 3

            with pytest.raises(HTTPException) as exc_info:
                await get_agent_payment(mock_request, session)

            assert exc_info.value.status_code == 429
            assert "concurrent" in exc_info.value.detail.lower()
            assert exc_info.value.headers.get("Retry-After") == "30"

    @pytest.mark.asyncio
    async def test_concurrent_limit_not_exceeded(self):
        """Below max concurrent runs → returns AgentPaymentContext normally."""
        mock_request = MagicMock()
        mock_request.headers = {"x-api-key": "test-key-123"}

        mock_identity = AgentIdentity(
            provider="credit",
            payer_id="user-concurrent-002",
            user_id="user-concurrent-002",
        )

        # Only 1 concurrent (below limit of 3)
        session = _mock_session(concurrent_count=1)

        with (
            patch(
                "app.core.agent_auth.get_agent_identity",
                new_callable=AsyncMock,
                return_value=mock_identity,
            ),
            patch("app.core.agent_auth.settings") as mock_settings,
        ):
            mock_settings.MAX_CONCURRENT_ANALYSES = 3

            result = await get_agent_payment(mock_request, session)

            assert isinstance(result, AgentPaymentContext)
            assert result.user_id == "user-concurrent-002"
            assert result.provider == "credit"
