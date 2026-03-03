"""Track L: Credit payment provider unit tests.

Tests for CreditPaymentProvider (can_handle), plus the module-level
helper functions: check_credit_balance, debit_credits, refund_credits.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.payments.credit_provider import (
    CreditPaymentProvider,
    check_credit_balance,
    debit_credits,
    refund_credits,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def provider():
    return CreditPaymentProvider()


def _make_request(headers: dict) -> MagicMock:
    """Build a minimal mock Request with the given headers."""
    req = MagicMock()
    req.headers = headers
    return req


def _make_mock_session(user=None):
    """Build an AsyncMock session whose execute returns the given user.

    If user is None, scalar_one_or_none returns None (user not found).
    """
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = user

    session = AsyncMock()
    session.execute.return_value = mock_result
    session.flush = AsyncMock()
    return session


def _make_user(credit_balance_cents: int) -> MagicMock:
    """Build a mock User with the given credit balance."""
    user = MagicMock()
    user.credit_balance_cents = credit_balance_cents
    return user


# ---------------------------------------------------------------------------
# can_handle
# ---------------------------------------------------------------------------


class TestCanHandle:
    """Tests for CreditPaymentProvider.can_handle()."""

    @pytest.mark.asyncio
    async def test_can_handle_with_api_key(self, provider):
        """Returns True when x-api-key header is present."""
        request = _make_request({"x-api-key": "tru8_key_abc123"})

        result = await provider.can_handle(request)

        assert result is True

    @pytest.mark.asyncio
    async def test_can_handle_without_api_key(self, provider):
        """Returns False when x-api-key header is missing."""
        request = _make_request({"authorization": "Bearer tok123"})

        result = await provider.can_handle(request)

        assert result is False


# ---------------------------------------------------------------------------
# check_credit_balance
# ---------------------------------------------------------------------------


class TestCheckCreditBalance:
    """Tests for the check_credit_balance helper function."""

    @pytest.mark.asyncio
    async def test_check_balance_sufficient(self):
        """Returns True when balance >= requested amount."""
        user = _make_user(credit_balance_cents=500)
        session = _make_mock_session(user=user)

        result = await check_credit_balance("user-001", 200, session)

        assert result is True

    @pytest.mark.asyncio
    async def test_check_balance_exact(self):
        """Returns True when balance equals the exact requested amount."""
        user = _make_user(credit_balance_cents=200)
        session = _make_mock_session(user=user)

        result = await check_credit_balance("user-001", 200, session)

        assert result is True

    @pytest.mark.asyncio
    async def test_check_balance_insufficient(self):
        """Returns False when balance < requested amount."""
        user = _make_user(credit_balance_cents=50)
        session = _make_mock_session(user=user)

        result = await check_credit_balance("user-001", 200, session)

        assert result is False

    @pytest.mark.asyncio
    async def test_check_balance_user_not_found(self):
        """Returns False when user does not exist."""
        session = _make_mock_session(user=None)

        result = await check_credit_balance("nonexistent-user", 100, session)

        assert result is False


# ---------------------------------------------------------------------------
# debit_credits
# ---------------------------------------------------------------------------


class TestDebitCredits:
    """Tests for the debit_credits helper function."""

    @pytest.mark.asyncio
    async def test_debit_success(self):
        """Decrements balance and returns True when funds are sufficient."""
        user = _make_user(credit_balance_cents=500)
        session = _make_mock_session(user=user)

        result = await debit_credits("user-001", 200, session)

        assert result is True
        assert user.credit_balance_cents == 300
        session.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_debit_insufficient(self):
        """Returns False and leaves balance unchanged when funds are insufficient."""
        user = _make_user(credit_balance_cents=50)
        session = _make_mock_session(user=user)

        result = await debit_credits("user-001", 200, session)

        assert result is False
        assert user.credit_balance_cents == 50
        session.flush.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_debit_user_not_found(self):
        """Returns False when user does not exist."""
        session = _make_mock_session(user=None)

        result = await debit_credits("nonexistent-user", 100, session)

        assert result is False
        session.flush.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_debit_exact_balance(self):
        """Debiting the exact balance succeeds and leaves zero."""
        user = _make_user(credit_balance_cents=200)
        session = _make_mock_session(user=user)

        result = await debit_credits("user-001", 200, session)

        assert result is True
        assert user.credit_balance_cents == 0


# ---------------------------------------------------------------------------
# refund_credits
# ---------------------------------------------------------------------------


class TestRefundCredits:
    """Tests for the refund_credits helper function."""

    @pytest.mark.asyncio
    async def test_refund_success(self):
        """Increments balance by the refund amount."""
        user = _make_user(credit_balance_cents=300)
        session = _make_mock_session(user=user)

        await refund_credits("user-001", 200, session)

        assert user.credit_balance_cents == 500
        session.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_refund_user_not_found(self):
        """Silently does nothing when user does not exist."""
        session = _make_mock_session(user=None)

        # Should not raise
        await refund_credits("nonexistent-user", 100, session)

        session.flush.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_refund_from_zero(self):
        """Refunding to a zero-balance account works correctly."""
        user = _make_user(credit_balance_cents=0)
        session = _make_mock_session(user=user)

        await refund_credits("user-001", 150, session)

        assert user.credit_balance_cents == 150
