"""Tests for agent idempotency key handling.

Covers:
- Duplicate idempotency key with same request hash → returns cached transaction
- Duplicate idempotency key with different request hash → 409 Conflict
"""

import hashlib
import json
import uuid
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.core.agent_auth import (
    AgentPaymentContext,
    compute_request_hash,
    idempotency_disposition,
)
from app.models.agent_transaction import AgentTransaction


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_session():
    """Build a mock async session."""
    session = AsyncMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.flush = AsyncMock()
    session.add = MagicMock()
    return session


class _MockResult:
    """Mock for SQLAlchemy execute() result."""

    def __init__(self, scalar=None):
        self._scalar_value = scalar

    def scalar_one_or_none(self):
        return self._scalar_value


# ---------------------------------------------------------------------------
# Idempotency: same key + same hash → cached
# ---------------------------------------------------------------------------


class TestIdempotencySameHash:
    """Duplicate Idempotency-Key with same request_hash returns cached tx."""

    @pytest.mark.asyncio
    async def test_duplicate_key_same_hash_returns_cached(self):
        """Same idempotency key + same request hash → returns existing transaction."""
        session = _mock_session()

        # Existing transaction in DB
        existing_tx = MagicMock(spec=AgentTransaction)
        existing_tx.id = "tx-existing-001"
        existing_tx.idempotency_key = "idem-key-001"
        existing_tx.request_hash = "hash-abc"
        existing_tx.status = "completed"
        existing_tx.amount_pence = 7
        existing_tx.tier = "quick"
        existing_tx.payer_id = "user-001"
        existing_tx.created_at = datetime.utcnow()

        # Session returns the existing tx on idempotency lookup
        session.execute = AsyncMock(return_value=_MockResult(scalar=existing_tx))

        ctx = AgentPaymentContext(
            provider="credit",
            payer_id="user-001",
            user_id="user-001",
            session=session,
        )

        # Call charge with same idempotency key and same request hash
        result = await ctx.charge(
            amount_pence=7,
            tier="quick",
            description="claim-hash-abc",
            idempotency_key="idem-key-001",
            request_hash="hash-abc",
        )

        # Should return the cached transaction, not create a new one
        assert result.id == "tx-existing-001"
        assert result.status == "completed"
        # session.add should NOT be called (no new tx created)
        session.add.assert_not_called()


# ---------------------------------------------------------------------------
# Idempotency: same key + different hash → 409
# ---------------------------------------------------------------------------


class TestIdempotencyDifferentHash:
    """Duplicate Idempotency-Key with different request_hash → 409 Conflict."""

    @pytest.mark.asyncio
    async def test_duplicate_key_different_hash_returns_409(self):
        """Same idempotency key + different request hash → 409."""
        session = _mock_session()

        # Existing transaction with a DIFFERENT request_hash
        existing_tx = MagicMock(spec=AgentTransaction)
        existing_tx.id = "tx-existing-002"
        existing_tx.idempotency_key = "idem-key-002"
        existing_tx.request_hash = "hash-original"
        existing_tx.status = "completed"
        existing_tx.payer_id = "user-001"
        existing_tx.created_at = datetime.utcnow()

        session.execute = AsyncMock(return_value=_MockResult(scalar=existing_tx))

        ctx = AgentPaymentContext(
            provider="credit",
            payer_id="user-001",
            user_id="user-001",
            session=session,
        )

        # Call charge with same idempotency key but DIFFERENT request hash
        with pytest.raises(HTTPException) as exc_info:
            await ctx.charge(
                amount_pence=15,
                tier="full",
                description="claim-hash-xyz",
                idempotency_key="idem-key-002",
                request_hash="hash-different",
            )

        assert exc_info.value.status_code == 409
        assert "already used" in exc_info.value.detail.lower()


# ---------------------------------------------------------------------------
# Sliding window, payer check, key retirement (2026-09-11)
# ---------------------------------------------------------------------------


def _existing(
    *,
    payer_id="user-001",
    request_hash="hash-abc",
    status="completed",
    age_s=0,
    tx_id="tx-existing",
):
    tx = MagicMock(spec=AgentTransaction)
    tx.id = tx_id
    tx.idempotency_key = "idem-key"
    tx.request_hash = request_hash
    tx.status = status
    tx.payer_id = payer_id
    tx.tier = "full"
    tx.amount_pence = 15
    tx.created_at = datetime.utcnow() - timedelta(seconds=age_s)
    return tx


def _ctx(session, payer_id="user-001"):
    return AgentPaymentContext(
        provider="credit", payer_id=payer_id, user_id=payer_id, session=session
    )


class TestIdempotencyDisposition:
    """The pure decision, one case per branch."""

    def test_inside_window_replays(self):
        assert (
            idempotency_disposition(
                _existing(age_s=599), payer_id="user-001", request_hash="hash-abc"
            )
            == "replay"
        )

    def test_straddling_a_clock_boundary_still_replays(self):
        """The 2026-09-11 failure shape: first call 09:58:40, resend 10:04:20.
        The window is measured from the FIRST transaction, not the clock."""
        first = datetime(2026, 9, 11, 9, 58, 40)
        resend = datetime(2026, 9, 11, 10, 4, 20)
        tx = _existing()
        tx.created_at = first
        assert (
            idempotency_disposition(
                tx, payer_id="user-001", request_hash="hash-abc", now=resend
            )
            == "replay"
        )

    def test_past_window_and_terminal_expires(self):
        assert (
            idempotency_disposition(
                _existing(age_s=601), payer_id="user-001", request_hash="hash-abc"
            )
            == "expired"
        )

    def test_past_window_but_still_pending_replays(self):
        assert (
            idempotency_disposition(
                _existing(age_s=601, status="pending"),
                payer_id="user-001",
                request_hash="hash-abc",
            )
            == "replay"
        )

    def test_other_payer_is_a_conflict_never_a_replay(self):
        assert (
            idempotency_disposition(
                _existing(payer_id="someone-else"),
                payer_id="user-001",
                request_hash="hash-abc",
            )
            == "other_payer"
        )

    def test_different_request_is_a_conflict(self):
        assert (
            idempotency_disposition(
                _existing(request_hash="other"),
                payer_id="user-001",
                request_hash="hash-abc",
            )
            == "different_request"
        )

    def test_ttl_is_configurable(self):
        assert (
            idempotency_disposition(
                _existing(age_s=50),
                payer_id="user-001",
                request_hash="hash-abc",
                ttl_s=10,
            )
            == "expired"
        )


class TestChargeWindow:
    """charge() wired to the disposition."""

    @pytest.mark.asyncio
    async def test_aged_599_returns_existing_without_adding(self):
        session = _mock_session()
        existing = _existing(age_s=599)
        session.execute = AsyncMock(return_value=_MockResult(scalar=existing))
        out = await _ctx(session).charge(
            amount_pence=15,
            tier="full",
            description="h",
            idempotency_key="idem-key",
            request_hash="hash-abc",
        )
        assert out is existing
        session.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_aged_601_terminal_retires_key_and_charges_afresh(self):
        session = _mock_session()
        existing = _existing(age_s=601)
        session.execute = AsyncMock(return_value=_MockResult(scalar=existing))
        with patch(
            "app.services.payments.credit_provider.debit_credits",
            AsyncMock(return_value=True),
        ):
            out = await _ctx(session).charge(
                amount_pence=15,
                tier="full",
                description="h",
                idempotency_key="idem-key",
                request_hash="hash-abc",
            )
        assert out is not existing
        assert existing.idempotency_key == "idem-key#tx-existing"
        session.add.assert_called_once()
        assert session.add.call_args.args[0].idempotency_key == "idem-key"

    @pytest.mark.asyncio
    async def test_aged_601_pending_is_replayed(self):
        session = _mock_session()
        existing = _existing(age_s=601, status="pending")
        session.execute = AsyncMock(return_value=_MockResult(scalar=existing))
        out = await _ctx(session).charge(
            amount_pence=15,
            tier="full",
            description="h",
            idempotency_key="idem-key",
            request_hash="hash-abc",
        )
        assert out is existing
        session.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_other_payer_gets_409_and_no_replay(self):
        session = _mock_session()
        existing = _existing(payer_id="someone-else")
        session.execute = AsyncMock(return_value=_MockResult(scalar=existing))
        with pytest.raises(HTTPException) as exc_info:
            await _ctx(session).charge(
                amount_pence=15,
                tier="full",
                description="h",
                idempotency_key="idem-key",
                request_hash="hash-abc",
            )
        assert exc_info.value.status_code == 409
        assert "another caller" in exc_info.value.detail
        session.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_lost_insert_race_returns_the_winner(self):
        """Two resends race the unique index: the loser rolls back (undoing
        its debit) and returns the winner's transaction."""
        from sqlalchemy.exc import IntegrityError

        session = _mock_session()
        winner = _existing(age_s=1)
        # first lookup: nothing; after the failed flush: the winner
        session.execute = AsyncMock(
            side_effect=[_MockResult(scalar=None), _MockResult(scalar=winner)]
        )
        session.flush = AsyncMock(side_effect=IntegrityError("dup", None, None))
        session.rollback = AsyncMock()
        with patch(
            "app.services.payments.credit_provider.debit_credits",
            AsyncMock(return_value=True),
        ):
            out = await _ctx(session).charge(
                amount_pence=15,
                tier="full",
                description="h",
                idempotency_key="idem-key",
                request_hash="hash-abc",
            )
        assert out is winner
        session.rollback.assert_awaited_once()


# ---------------------------------------------------------------------------
# compute_request_hash determinism
# ---------------------------------------------------------------------------


class TestRequestHash:
    """compute_request_hash produces deterministic SHA256."""

    def test_same_inputs_same_hash(self):
        """Same (tier, claim_hash, compact) → same hash."""
        h1 = compute_request_hash("quick", "abc123", False)
        h2 = compute_request_hash("quick", "abc123", False)
        assert h1 == h2

    def test_different_tier_different_hash(self):
        """Different tier → different hash."""
        h1 = compute_request_hash("quick", "abc123", False)
        h2 = compute_request_hash("full", "abc123", False)
        assert h1 != h2

    def test_different_compact_different_hash(self):
        """Different compact flag → different hash."""
        h1 = compute_request_hash("quick", "abc123", False)
        h2 = compute_request_hash("quick", "abc123", True)
        assert h1 != h2

    def test_hash_is_sha256(self):
        """Output is a valid 64-char hex SHA256 digest."""
        h = compute_request_hash("lookup", "test", False)
        assert len(h) == 64
        # Verify it's a valid hex string
        int(h, 16)
