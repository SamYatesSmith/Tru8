"""Tests for agent idempotency key handling.

Covers:
- Duplicate idempotency key with same request hash → returns cached transaction
- Duplicate idempotency key with different request hash → 409 Conflict
"""

import hashlib
import json
import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.core.agent_auth import AgentPaymentContext, compute_request_hash
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
        existing_tx.amount_cents = 7
        existing_tx.tier = "quick"

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
            amount_cents=7,
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
                amount_cents=15,
                tier="full",
                description="claim-hash-xyz",
                idempotency_key="idem-key-002",
                request_hash="hash-different",
            )

        assert exc_info.value.status_code == 409
        assert "already used" in exc_info.value.detail.lower()


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
