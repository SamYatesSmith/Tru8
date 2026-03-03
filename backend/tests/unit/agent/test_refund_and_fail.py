"""Track L hardening: tests for _refund_and_fail_tx() in agent.py.

Verifies credit refund vs non-credit failure marking and session commit.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.core.agent_auth import AgentPaymentContext


@pytest.fixture
def mock_session():
    session = AsyncMock()
    session.commit = AsyncMock()
    return session


def _make_tx():
    tx = MagicMock()
    tx.status = "pending"
    return tx


def _make_payment(provider: str, session: AsyncMock) -> AgentPaymentContext:
    return AgentPaymentContext(
        provider=provider,
        payer_id="test_payer",
        user_id="test_user",
        session=session,
    )


class TestRefundAndFailTx:
    """Tests for _refund_and_fail_tx()."""

    @pytest.mark.asyncio
    @patch(
        "app.services.payments.credit_provider.refund_credits", new_callable=AsyncMock
    )
    async def test_credit_provider_refunds(self, mock_refund, mock_session):
        """Credit provider: calls refund_credits and sets tx.status='refunded'."""
        from app.api.v1.agent import _refund_and_fail_tx

        tx = _make_tx()
        payment = _make_payment("credit", mock_session)

        await _refund_and_fail_tx(tx, payment, 700, mock_session)

        mock_refund.assert_called_once_with("test_user", 700, mock_session)
        assert tx.status == "refunded"
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_non_credit_provider_fails_without_refund(self, mock_session):
        """Non-credit provider (skyfire/x402): sets tx.status='failed', no refund."""
        from app.api.v1.agent import _refund_and_fail_tx

        tx = _make_tx()
        payment = _make_payment("skyfire", mock_session)

        with patch(
            "app.services.payments.credit_provider.refund_credits",
            new_callable=AsyncMock,
        ) as mock_refund:
            await _refund_and_fail_tx(tx, payment, 1500, mock_session)

            mock_refund.assert_not_called()

        assert tx.status == "failed"
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_x402_provider_fails_without_refund(self, mock_session):
        """x402 provider: sets tx.status='failed', no refund call."""
        from app.api.v1.agent import _refund_and_fail_tx

        tx = _make_tx()
        payment = _make_payment("x402", mock_session)

        await _refund_and_fail_tx(tx, payment, 1500, mock_session)

        assert tx.status == "failed"
        mock_session.commit.assert_called_once()
