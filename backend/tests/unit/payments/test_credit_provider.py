"""Track L: Credit payment provider unit tests.

Tests for CreditPaymentProvider (can_handle), plus the module-level
helper functions: check_credit_balance, debit_credits, refund_credits.

debit_credits and refund_credits use atomic SQL UPDATE statements
(not ORM attribute mutation), so tests verify rowcount-based logic.
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

    For check_credit_balance (SELECT), scalar_one_or_none returns user.
    """
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = user

    session = AsyncMock()
    session.execute.return_value = mock_result
    session.flush = AsyncMock()
    return session


def _make_atomic_session(rowcount: int):
    """Build an AsyncMock session for atomic UPDATE operations.

    Returns a result whose .rowcount matches the given value.
    """
    mock_result = MagicMock()
    mock_result.rowcount = rowcount

    session = AsyncMock()
    session.execute.return_value = mock_result
    session.flush = AsyncMock()
    return session


def _make_user(credit_balance_pence: int) -> MagicMock:
    """Build a mock User with the given credit balance."""
    user = MagicMock()
    user.credit_balance_pence = credit_balance_pence
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
        user = _make_user(credit_balance_pence=500)
        session = _make_mock_session(user=user)

        result = await check_credit_balance("user-001", 200, session)

        assert result is True

    @pytest.mark.asyncio
    async def test_check_balance_exact(self):
        """Returns True when balance equals the exact requested amount."""
        user = _make_user(credit_balance_pence=200)
        session = _make_mock_session(user=user)

        result = await check_credit_balance("user-001", 200, session)

        assert result is True

    @pytest.mark.asyncio
    async def test_check_balance_insufficient(self):
        """Returns False when balance < requested amount."""
        user = _make_user(credit_balance_pence=50)
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
# debit_credits (atomic SQL UPDATE)
# ---------------------------------------------------------------------------


class TestDebitCredits:
    """Tests for the debit_credits helper function.

    Uses atomic UPDATE ... WHERE balance >= amount, so we test via rowcount.
    """

    @pytest.mark.asyncio
    async def test_debit_success(self):
        """Returns True when atomic UPDATE matches a row (sufficient balance)."""
        session = _make_atomic_session(rowcount=1)

        result = await debit_credits("user-001", 200, session)

        assert result is True
        session.execute.assert_awaited_once()
        session.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_debit_insufficient(self):
        """Returns False when atomic UPDATE matches no rows (insufficient balance)."""
        session = _make_atomic_session(rowcount=0)

        result = await debit_credits("user-001", 200, session)

        assert result is False
        session.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_debit_user_not_found(self):
        """Returns False when atomic UPDATE matches no rows (user doesn't exist)."""
        session = _make_atomic_session(rowcount=0)

        result = await debit_credits("nonexistent-user", 100, session)

        assert result is False

    @pytest.mark.asyncio
    async def test_debit_exact_balance(self):
        """Debiting the exact balance succeeds (WHERE balance >= amount includes equality)."""
        session = _make_atomic_session(rowcount=1)

        result = await debit_credits("user-001", 200, session)

        assert result is True


# ---------------------------------------------------------------------------
# refund_credits (atomic SQL UPDATE)
# ---------------------------------------------------------------------------


class TestRefundCredits:
    """Tests for the refund_credits helper function.

    Uses atomic UPDATE to increment balance at SQL level.
    """

    @pytest.mark.asyncio
    async def test_refund_success(self):
        """Increments balance atomically when user exists (rowcount=1)."""
        session = _make_atomic_session(rowcount=1)

        await refund_credits("user-001", 200, session)

        session.execute.assert_awaited_once()
        session.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_refund_user_not_found(self):
        """Logs error but does not raise when user does not exist (rowcount=0)."""
        session = _make_atomic_session(rowcount=0)

        # Should not raise
        await refund_credits("nonexistent-user", 100, session)

        session.execute.assert_awaited_once()
        session.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_refund_from_zero(self):
        """Refunding to a zero-balance account works (atomic increment from 0)."""
        session = _make_atomic_session(rowcount=1)

        await refund_credits("user-001", 150, session)

        session.execute.assert_awaited_once()
        session.flush.assert_awaited_once()


# ---------------------------------------------------------------------------
# Webhook: handle_agent_credit_purchase
# ---------------------------------------------------------------------------


class TestWebhookAmountValidation:
    """Tests for Stripe amount cross-check in handle_agent_credit_purchase."""

    @pytest.mark.asyncio
    async def test_amount_mismatch_rejects(self):
        """Webhook rejects when Stripe amount_total != metadata pence_value."""
        from app.api.v1.payments import handle_agent_credit_purchase

        session = _make_atomic_session(rowcount=1)
        session_data = {
            "client_reference_id": "user-001",
            "metadata": {
                "purchase_type": "agent_credits",
                "pence_value": "300",
                "credit_pack": "20",
            },
            "amount_total": 9999,  # Mismatch!
        }

        await handle_agent_credit_purchase(session_data, session)

        # Should NOT have called execute (rejected before DB write)
        session.execute.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_amount_match_proceeds(self):
        """Webhook proceeds when Stripe amount_total matches metadata pence_value."""
        from app.api.v1.payments import handle_agent_credit_purchase

        session = _make_atomic_session(rowcount=1)
        session.commit = AsyncMock()
        session_data = {
            "client_reference_id": "user-001",
            "metadata": {
                "purchase_type": "agent_credits",
                "pence_value": "300",
                "credit_pack": "20",
            },
            "amount_total": 300,
        }

        await handle_agent_credit_purchase(session_data, session)

        session.execute.assert_awaited_once()
        session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_invalid_pence_value_rejects(self):
        """Webhook rejects when pence_value is not a valid integer."""
        from app.api.v1.payments import handle_agent_credit_purchase

        session = _make_atomic_session(rowcount=1)
        session_data = {
            "client_reference_id": "user-001",
            "metadata": {
                "purchase_type": "agent_credits",
                "pence_value": "abc",
                "credit_pack": "20",
            },
        }

        await handle_agent_credit_purchase(session_data, session)

        session.execute.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_missing_pence_value_rejects(self):
        """Webhook rejects when pence_value is missing from metadata."""
        from app.api.v1.payments import handle_agent_credit_purchase

        session = _make_atomic_session(rowcount=1)
        session_data = {
            "client_reference_id": "user-001",
            "metadata": {"purchase_type": "agent_credits", "credit_pack": "20"},
        }

        await handle_agent_credit_purchase(session_data, session)

        session.execute.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_amount_total_absent_proceeds(self):
        """Webhook proceeds when amount_total is absent (backwards compat)."""
        from app.api.v1.payments import handle_agent_credit_purchase

        session = _make_atomic_session(rowcount=1)
        session.commit = AsyncMock()
        session_data = {
            "client_reference_id": "user-001",
            "metadata": {
                "purchase_type": "agent_credits",
                "pence_value": "300",
                "credit_pack": "20",
            },
            # No amount_total key
        }

        await handle_agent_credit_purchase(session_data, session)

        session.execute.assert_awaited_once()
        session.commit.assert_awaited_once()
