"""Track L hardening: tests for handle_agent_credit_purchase() in payments.py.

Verifies atomic credit balance increment, user-not-found handling, and
zero-value early return.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture
def mock_session():
    session = AsyncMock()
    session.commit = AsyncMock()
    return session


class TestHandleAgentCreditPurchase:
    """Tests for handle_agent_credit_purchase()."""

    @pytest.mark.asyncio
    async def test_successful_credit_increment(self, mock_session):
        """Successful purchase executes atomic DB increment and commits."""
        from app.api.v1.payments import handle_agent_credit_purchase

        # Mock execute to return rowcount=1 (user found, row updated)
        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_session.execute = AsyncMock(return_value=mock_result)

        session_data = {
            "client_reference_id": "user_1",
            "metadata": {
                "purchase_type": "agent_credits",
                "pence_value": "2000",
                "credit_pack": "20",
            },
        }

        await handle_agent_credit_purchase(session_data, mock_session)

        # Should have executed the atomic update and committed
        mock_session.execute.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_user_not_found_returns_without_crash(self, mock_session):
        """User not found (rowcount=0) logs error and returns without commit."""
        from app.api.v1.payments import handle_agent_credit_purchase

        # Mock execute to return rowcount=0 (user not found)
        mock_result = MagicMock()
        mock_result.rowcount = 0
        mock_session.execute = AsyncMock(return_value=mock_result)

        session_data = {
            "client_reference_id": "nonexistent_user",
            "metadata": {
                "purchase_type": "agent_credits",
                "pence_value": "2000",
                "credit_pack": "20",
            },
        }

        # Should not raise
        await handle_agent_credit_purchase(session_data, mock_session)

        # Execute was called but commit was NOT (user not found)
        mock_session.execute.assert_called_once()
        mock_session.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_zero_pence_returns_early(self, mock_session):
        """Missing or zero pence_value returns early without DB write."""
        from app.api.v1.payments import handle_agent_credit_purchase

        session_data = {
            "client_reference_id": "user_1",
            "metadata": {
                "purchase_type": "agent_credits",
                "pence_value": "0",
                "credit_pack": "unknown",
            },
        }

        await handle_agent_credit_purchase(session_data, mock_session)

        # Should return early — no DB query
        mock_session.execute.assert_not_called()
        mock_session.commit.assert_not_called()
