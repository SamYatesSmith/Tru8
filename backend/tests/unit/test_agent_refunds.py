"""Agent-rail refunds for stranded checks (app/services/agent_refunds.py, 2026-09-11).

Why: the shutdown guard and the stale sweep refund via the dashboard usage
ledger, a no-op for agent checks, and agent runs never registered in-flight —
so a tru8_check killed by a deploy (5525b573) kept its 15p and its
`processing` row forever.
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.agent_transaction import AgentTransaction
from app.services.agent_refunds import (
    STRANDED_REASON,
    refund_stranded_agent_transaction,
)


def _tx(*, provider="credit", status="pending", amount=15, payer="user-1"):
    tx = MagicMock(spec=AgentTransaction)
    tx.id = "tx-1"
    tx.provider = provider
    tx.status = status
    tx.amount_pence = amount
    tx.payer_id = payer
    tx.tx_metadata = {"claim_text_hash": "h"}
    return tx


def _session(txs):
    session = MagicMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = txs
    session.execute = AsyncMock(return_value=result)
    session.add = MagicMock()
    return session


@pytest.mark.unit
@pytest.mark.asyncio
class TestRefundStrandedAgentTransaction:
    async def test_credit_tx_is_refunded_to_the_checks_owner(self):
        tx = _tx()
        session = _session([tx])
        with patch(
            "app.services.payments.credit_provider.refund_credits", AsyncMock()
        ) as refund:
            n = await refund_stranded_agent_transaction(
                session, "chk", user_id="owner-1"
            )
        assert n == 1
        refund.assert_awaited_once_with("owner-1", 15, session)
        assert tx.status == "refunded"
        assert tx.tx_metadata["settlement_reason"] == STRANDED_REASON
        assert tx.tx_metadata["claim_text_hash"] == "h"  # existing metadata kept
        session.add.assert_called_once_with(tx)

    async def test_falls_back_to_the_payer_when_owner_unknown(self):
        tx = _tx(payer="payer-9")
        with patch(
            "app.services.payments.credit_provider.refund_credits", AsyncMock()
        ) as refund:
            await refund_stranded_agent_transaction(_session([tx]), "chk")
        refund.assert_awaited_once()
        assert refund.call_args.args[0] == "payer-9"

    async def test_already_refunded_or_failed_left_alone(self):
        done = [_tx(status="refunded"), _tx(status="failed")]
        with patch(
            "app.services.payments.credit_provider.refund_credits", AsyncMock()
        ) as refund:
            n = await refund_stranded_agent_transaction(_session(done), "chk")
        assert n == 0
        refund.assert_not_awaited()

    async def test_unsettled_stale_pending_tx_is_still_refunded(self):
        """The stale-pending sweeper marks a stranded tx `unsettled` without
        returning the money; that must not count as settled."""
        tx = _tx(status="unsettled")
        tx.tx_metadata = {"settlement_reason": "stale_pending"}
        with patch(
            "app.services.payments.credit_provider.refund_credits", AsyncMock()
        ) as refund:
            n = await refund_stranded_agent_transaction(_session([tx]), "chk")
        assert n == 1
        refund.assert_awaited_once()
        assert tx.status == "refunded"

    async def test_non_credit_rail_is_marked_unsettled_not_refunded(self):
        tx = _tx(provider="skyfire")
        with patch(
            "app.services.payments.credit_provider.refund_credits", AsyncMock()
        ) as refund:
            n = await refund_stranded_agent_transaction(_session([tx]), "chk")
        assert n == 1
        refund.assert_not_awaited()
        assert tx.status == "unsettled"
        assert tx.tx_metadata["settlement_reason"] == STRANDED_REASON

    async def test_never_raises_when_the_read_fails(self):
        session = MagicMock()
        session.execute = AsyncMock(side_effect=RuntimeError("db down"))
        assert await refund_stranded_agent_transaction(session, "chk") == 0

    async def test_rows_that_are_not_transactions_are_ignored(self):
        """The sweeps' unit tests feed a fake session whose only select
        returns Check rows; the helper must not mistake them for money."""
        session = _session([SimpleNamespace(id="c1", status="processing")])
        assert await refund_stranded_agent_transaction(session, "chk") == 0
