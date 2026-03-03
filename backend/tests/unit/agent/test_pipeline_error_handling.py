"""Track L hardening: tests for error paths in _run_agent_pipeline().

Verifies TimeoutError, PipelineError, and generic Exception all trigger
_refund_and_fail_tx and raise appropriate HTTPExceptions.
"""

import asyncio
import json

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import HTTPException

from app.core.agent_auth import AgentPaymentContext


def _make_payment_context(session: AsyncMock) -> AgentPaymentContext:
    ctx = AgentPaymentContext(
        provider="credit",
        payer_id="test_user",
        user_id="test_user",
        session=session,
    )
    return ctx


def _make_body():
    from app.api.v1.agent import AgentClaimRequest

    return AgentClaimRequest(claim="The sky is blue", compact=False)


@pytest.fixture
def mock_session():
    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.flush = AsyncMock()
    return session


@pytest.fixture
def mock_tx():
    tx = MagicMock()
    tx.id = "tx_test_001"
    tx.status = "pending"
    tx.check_id = None
    tx.tx_metadata = None
    return tx


# We patch _refund_and_fail_tx to avoid DB/credit_provider calls,
# and patch run_pipeline at the runner module level to raise errors.
# The lazy import inside _run_agent_pipeline picks up the patched version.

_PATCHES = [
    "app.api.v1.agent._refund_and_fail_tx",
    "app.pipeline.runner.handle_pipeline_failure",
    "app.pipeline.runner.run_pipeline",
    "app.pipeline.progress.ProgressReporter",
    "app.core.database.async_session",
]


class TestPipelineErrorHandling:
    """Tests for error paths in _run_agent_pipeline()."""

    @pytest.mark.asyncio
    async def test_timeout_returns_504(self, mock_session, mock_tx):
        """TimeoutError → HTTPException 504 + _refund_and_fail_tx called."""
        with (
            patch(_PATCHES[0], new_callable=AsyncMock) as mock_refund,
            patch(_PATCHES[1], new_callable=AsyncMock),
            patch(_PATCHES[2], new_callable=AsyncMock) as mock_run,
            patch(_PATCHES[3]),
            patch(_PATCHES[4]),
        ):
            from app.api.v1.agent import _run_agent_pipeline

            mock_run.side_effect = asyncio.TimeoutError()
            payment = _make_payment_context(mock_session)
            payment.charge = AsyncMock(return_value=mock_tx)

            with pytest.raises(HTTPException) as exc_info:
                await _run_agent_pipeline(
                    body=_make_body(),
                    tier="quick",
                    amount_cents=700,
                    claim_hash="abc123",
                    request_hash="hash123",
                    limitations=[],
                    payment=payment,
                    session=mock_session,
                    idempotency_key=None,
                )

            assert exc_info.value.status_code == 504
            mock_refund.assert_called_once()

    @pytest.mark.asyncio
    async def test_pipeline_error_returns_502(self, mock_session, mock_tx):
        """PipelineError → HTTPException 502 + _refund_and_fail_tx called."""
        with (
            patch(_PATCHES[0], new_callable=AsyncMock) as mock_refund,
            patch(_PATCHES[1], new_callable=AsyncMock),
            patch(_PATCHES[2], new_callable=AsyncMock) as mock_run,
            patch(_PATCHES[3]),
            patch(_PATCHES[4]),
        ):
            from app.api.v1.agent import _run_agent_pipeline
            from app.pipeline.runner import PipelineError

            mock_run.side_effect = PipelineError("retrieve stage failed")
            payment = _make_payment_context(mock_session)
            payment.charge = AsyncMock(return_value=mock_tx)

            with pytest.raises(HTTPException) as exc_info:
                await _run_agent_pipeline(
                    body=_make_body(),
                    tier="full",
                    amount_cents=1500,
                    claim_hash="abc123",
                    request_hash="hash123",
                    limitations=[],
                    payment=payment,
                    session=mock_session,
                    idempotency_key=None,
                )

            assert exc_info.value.status_code == 502
            mock_refund.assert_called_once()

    @pytest.mark.asyncio
    async def test_generic_exception_returns_502(self, mock_session, mock_tx):
        """Generic Exception → HTTPException 502 + _refund_and_fail_tx called."""
        with (
            patch(_PATCHES[0], new_callable=AsyncMock) as mock_refund,
            patch(_PATCHES[1], new_callable=AsyncMock),
            patch(_PATCHES[2], new_callable=AsyncMock) as mock_run,
            patch(_PATCHES[3]),
            patch(_PATCHES[4]),
        ):
            from app.api.v1.agent import _run_agent_pipeline

            mock_run.side_effect = RuntimeError("unexpected failure")
            payment = _make_payment_context(mock_session)
            payment.charge = AsyncMock(return_value=mock_tx)

            with pytest.raises(HTTPException) as exc_info:
                await _run_agent_pipeline(
                    body=_make_body(),
                    tier="full",
                    amount_cents=1500,
                    claim_hash="abc123",
                    request_hash="hash123",
                    limitations=[],
                    payment=payment,
                    session=mock_session,
                    idempotency_key=None,
                )

            assert exc_info.value.status_code == 502
            mock_refund.assert_called_once()
