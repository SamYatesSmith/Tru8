"""Tests for X402AuditMiddleware — settlement audit logic.

Validates the _audit_settlement method behaviour:
  - 200 + PAYMENT-RESPONSE header → tx.status = "completed"
  - 200 without PAYMENT-RESPONSE   → tx.status = "unsettled", reason = "missing_header"
  - 500                             → tx.status = "failed"
  - No agent_tx_id in scope state   → no DB update
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.middleware.x402_audit import X402AuditMiddleware


@pytest.fixture
def middleware():
    inner_app = AsyncMock()
    return X402AuditMiddleware(inner_app)


def _make_mock_tx(status="pending", tx_metadata=None):
    """Create a mock AgentTransaction with settable attributes."""
    tx = MagicMock()
    tx.status = status
    tx.transaction_ref = None
    tx.tx_metadata = tx_metadata
    return tx


# ---------------------------------------------------------------------------
# _audit_settlement tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_completed_on_200_with_payment_response(middleware):
    """200 + PAYMENT-RESPONSE header → tx.status='completed', transaction_ref set."""
    mock_tx = _make_mock_tx()
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_tx
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.commit = AsyncMock()

    mock_ctx = AsyncMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
    mock_ctx.__aexit__ = AsyncMock(return_value=False)

    with patch("app.core.database.async_session", return_value=mock_ctx):
        await middleware._audit_settlement(
            agent_tx_id="tx-123",
            status_code=200,
            headers={"payment-response": "0xdeadbeef"},
            body_message={"type": "http.response.body", "body": b""},
        )

    assert mock_tx.status == "completed"
    assert mock_tx.transaction_ref == "0xdeadbeef"
    mock_session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_unsettled_on_200_without_payment_response(middleware):
    """200 without PAYMENT-RESPONSE → tx.status='unsettled', reason='missing_header'."""
    mock_tx = _make_mock_tx()
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_tx
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.commit = AsyncMock()

    mock_ctx = AsyncMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
    mock_ctx.__aexit__ = AsyncMock(return_value=False)

    with patch("app.core.database.async_session", return_value=mock_ctx):
        await middleware._audit_settlement(
            agent_tx_id="tx-456",
            status_code=200,
            headers={},  # No payment-response header
            body_message={"type": "http.response.body", "body": b""},
        )

    assert mock_tx.status == "unsettled"
    assert mock_tx.tx_metadata["settlement_reason"] == "missing_header"
    mock_session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_failed_on_error_status(middleware):
    """500 → tx.status='failed', reason='http_500'."""
    mock_tx = _make_mock_tx()
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_tx
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.commit = AsyncMock()

    mock_ctx = AsyncMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
    mock_ctx.__aexit__ = AsyncMock(return_value=False)

    with patch("app.core.database.async_session", return_value=mock_ctx):
        await middleware._audit_settlement(
            agent_tx_id="tx-789",
            status_code=500,
            headers={},
            body_message={"type": "http.response.body", "body": b""},
        )

    assert mock_tx.status == "failed"
    assert mock_tx.tx_metadata["settlement_reason"] == "http_500"
    mock_session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_no_audit_without_tx_id(middleware):
    """When no agent_tx_id is in scope state, _audit_settlement should NOT be called."""
    # Simulate the full middleware __call__ with a scope that has no agent_tx_id
    messages_sent = []

    async def mock_inner_app(scope, receive, send):
        """Simulate a handler that sends response start + body WITHOUT setting agent_tx_id."""
        await send(
            {
                "type": "http.response.start",
                "status": 200,
                "headers": [(b"content-type", b"application/json")],
            }
        )
        await send(
            {
                "type": "http.response.body",
                "body": b'{"ok": true}',
            }
        )

    real_send = AsyncMock()

    middleware_instance = X402AuditMiddleware(mock_inner_app)
    scope = {"type": "http", "path": "/api/v1/agent/x402/quick", "state": {}}

    with patch.object(
        middleware_instance, "_audit_settlement", new_callable=AsyncMock
    ) as mock_audit:
        await middleware_instance(scope, AsyncMock(), real_send)

        # _audit_settlement should NOT have been called because no agent_tx_id
        mock_audit.assert_not_awaited()
