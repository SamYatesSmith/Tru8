"""Tests for stale pending transaction cleanup.

Covers:
- sweep_stale_pending_transactions marks old pending transactions as unsettled
"""

import json
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.agent_maintenance import (
    STALE_THRESHOLD_MINUTES,
    sweep_stale_pending_transactions,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _MockExecuteResult:
    """Mock for SQLAlchemy execute() result with rowcount."""

    def __init__(self, rowcount=0):
        self.rowcount = rowcount


def _mock_session(rowcount=0):
    """Build a mock async session for the sweep function."""
    session = AsyncMock()
    session.execute = AsyncMock(return_value=_MockExecuteResult(rowcount=rowcount))
    session.commit = AsyncMock()
    return session


# ---------------------------------------------------------------------------
# Stale pending cleanup
# ---------------------------------------------------------------------------


class TestStalePendingCleanup:
    """sweep_stale_pending_transactions marks stale pending txs as unsettled."""

    @pytest.mark.asyncio
    async def test_stale_pending_cleanup(self):
        """Stale pending transactions (>10 min old) are marked unsettled."""
        # Session simulates 2 rows being updated
        session = _mock_session(rowcount=2)

        count = await sweep_stale_pending_transactions(session)

        assert count == 2

        # Verify execute was called with UPDATE query
        session.execute.assert_called_once()
        call_args = session.execute.call_args
        # First arg is the text() SQL
        sql_text = str(call_args[0][0])
        assert "unsettled" in sql_text.lower()
        assert "stale_pending" in sql_text.lower()

        # Verify commit was called
        session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_stale_pending_no_matches(self):
        """No stale transactions → 0 rows updated, still commits."""
        session = _mock_session(rowcount=0)

        count = await sweep_stale_pending_transactions(session)

        assert count == 0
        session.execute.assert_called_once()
        session.commit.assert_called_once()

    def test_stale_threshold_is_10_minutes(self):
        """STALE_THRESHOLD_MINUTES is configured to 10."""
        assert STALE_THRESHOLD_MINUTES == 10
