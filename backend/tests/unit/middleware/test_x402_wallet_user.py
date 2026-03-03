"""Tests for x402 wallet → User resolution in the get_x402_payment dependency.

Validates:
  - New wallet address creates a Tru8 User with correct external_id
  - Same wallet address resolves to the same User (no duplicate creation)
  - Wallet address matching is case-insensitive (lowercased on input)
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

from app.api.v1.agent_x402 import get_x402_payment
from app.models.user import User


def _make_request(payer_address: str = "") -> MagicMock:
    """Build a mock Request with x-payer-address header."""
    request = MagicMock()
    request.headers = {"x-payer-address": payer_address}
    return request


def _make_session(existing_user=None):
    """Build a mock AsyncSession that optionally returns an existing user."""
    session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = existing_user
    session.execute = AsyncMock(return_value=mock_result)
    session.add = MagicMock()
    session.flush = AsyncMock()
    return session


# ---------------------------------------------------------------------------
# Wallet user creation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@patch("app.api.v1.agent_x402.settings")
async def test_wallet_user_creation(mock_settings):
    """New wallet address should create a User with external_id='x402:{network}:{address}'."""
    mock_settings.X402_NETWORK = "eip155:84532"
    wallet = "0xabcdef1234567890abcdef1234567890abcdef12"

    request = _make_request(wallet)
    session = _make_session(existing_user=None)

    ctx = await get_x402_payment(request=request, session=session)

    # User should have been added to the session
    session.add.assert_called_once()
    created_user = session.add.call_args[0][0]
    assert isinstance(created_user, User)
    assert created_user.external_id == f"x402:eip155:84532:{wallet}"
    assert created_user.email.endswith("@x402.agent")
    assert created_user.credits == 0

    # Context should reflect x402 provider
    assert ctx.provider == "x402"
    assert ctx.payer_id == wallet
    session.flush.assert_awaited_once()


@pytest.mark.asyncio
@patch("app.api.v1.agent_x402.settings")
async def test_wallet_user_reuse(mock_settings):
    """Same wallet address should resolve to the existing User without creating a new one."""
    mock_settings.X402_NETWORK = "eip155:84532"
    wallet = "0xabcdef1234567890abcdef1234567890abcdef12"

    existing = User(
        id=f"x402_{wallet[:16]}",
        email=f"{wallet[:16]}@x402.agent",
        external_id=f"x402:eip155:84532:{wallet}",
        credits=0,
    )

    request = _make_request(wallet)
    session = _make_session(existing_user=existing)

    ctx = await get_x402_payment(request=request, session=session)

    # No new user should be added
    session.add.assert_not_called()
    assert ctx.user_id == existing.id
    assert ctx.payer_id == wallet


@pytest.mark.asyncio
@patch("app.api.v1.agent_x402.settings")
async def test_wallet_case_insensitive(mock_settings):
    """Different-case wallet addresses should resolve to the same user (lowercased)."""
    mock_settings.X402_NETWORK = "eip155:84532"
    # Mixed-case input — should be normalised to lowercase
    wallet_mixed = "0xABCDEF1234567890ABCDEF1234567890ABCDEF12"
    wallet_lower = wallet_mixed.lower()

    existing = User(
        id=f"x402_{wallet_lower[:16]}",
        email=f"{wallet_lower[:16]}@x402.agent",
        external_id=f"x402:eip155:84532:{wallet_lower}",
        credits=0,
    )

    request = _make_request(wallet_mixed)
    session = _make_session(existing_user=existing)

    ctx = await get_x402_payment(request=request, session=session)

    # The payer_id should be lowercased
    assert ctx.payer_id == wallet_lower
    # No new user created — existing one reused
    session.add.assert_not_called()
