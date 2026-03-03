"""Track L hardening: tests for handle_agent_credit_purchase() in payments.py.

Verifies credit balance increment, user-not-found handling, and zero-value early return.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime


@pytest.fixture
def mock_session():
    session = AsyncMock()
    session.commit = AsyncMock()
    return session


def _make_user(user_id: str = "user_1", balance: int = 500) -> MagicMock:
    user = MagicMock()
    user.id = user_id
    user.credit_balance_cents = balance
    user.updated_at = None
    return user


class TestHandleAgentCreditPurchase:
    """Tests for handle_agent_credit_purchase()."""

    @pytest.mark.asyncio
    async def test_successful_credit_increment(self, mock_session):
        """Successful purchase increments credit_balance_cents."""
        from app.api.v1.payments import handle_agent_credit_purchase

        user = _make_user(balance=500)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = user
        mock_session.execute = AsyncMock(return_value=mock_result)

        session_data = {
            "client_reference_id": "user_1",
            "metadata": {
                "purchase_type": "agent_credits",
                "cents_value": "2000",
                "credit_pack": "20",
            },
        }

        await handle_agent_credit_purchase(session_data, mock_session)

        assert user.credit_balance_cents == 2500  # 500 + 2000
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_user_not_found_returns_without_crash(self, mock_session):
        """User not found logs error and returns without crashing."""
        from app.api.v1.payments import handle_agent_credit_purchase

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        session_data = {
            "client_reference_id": "nonexistent_user",
            "metadata": {
                "purchase_type": "agent_credits",
                "cents_value": "2000",
                "credit_pack": "20",
            },
        }

        # Should not raise
        await handle_agent_credit_purchase(session_data, mock_session)

        # No commit since no user was found
        mock_session.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_zero_cents_returns_early(self, mock_session):
        """Missing or zero cents_value returns early without DB write."""
        from app.api.v1.payments import handle_agent_credit_purchase

        session_data = {
            "client_reference_id": "user_1",
            "metadata": {
                "purchase_type": "agent_credits",
                "cents_value": "0",
                "credit_pack": "unknown",
            },
        }

        await handle_agent_credit_purchase(session_data, mock_session)

        # Should return early — no DB query
        mock_session.execute.assert_not_called()
        mock_session.commit.assert_not_called()
