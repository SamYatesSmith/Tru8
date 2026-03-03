"""Track L: Payment provider resolution / priority tests.

Tests that get_agent_identity in agent_auth.py resolves providers in
the correct priority order: Skyfire header -> API key -> 401.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.core.agent_auth import get_agent_identity


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_request(headers: dict) -> MagicMock:
    """Build a minimal mock Request with the given headers."""
    req = MagicMock()
    req.headers = headers
    return req


def _make_session():
    """Build an AsyncMock session for dependency injection."""
    session = AsyncMock()
    return session


def _make_mock_user(user_id: str = "user-001"):
    """Build a mock User row returned from DB lookup."""
    user = MagicMock()
    user.id = user_id
    return user


# ---------------------------------------------------------------------------
# Provider priority tests
# ---------------------------------------------------------------------------


class TestProviderPriority:
    """Tests for get_agent_identity provider resolution order."""

    @pytest.mark.asyncio
    @patch("app.core.agent_auth.settings")
    async def test_skyfire_header_takes_priority(self, mock_settings):
        """With both skyfire-pay-id and x-api-key, Skyfire provider is tried first."""
        mock_settings.SKYFIRE_ENABLED = True
        mock_settings.MAX_CONCURRENT_ANALYSES = 3

        request = _make_request(
            {
                "skyfire-pay-id": "eyJ.skyfire.token",
                "x-api-key": "tru8_key_abc123",
            }
        )
        session = _make_session()

        # Mock the Skyfire provider to succeed
        mock_skyfire_instance = AsyncMock()
        mock_skyfire_instance.can_handle.return_value = True
        mock_skyfire_instance.verify_jwt_only.return_value = {
            "sub": "skyfire_agent_001",
            "service_id": "svc_tru8",
        }

        # Mock DB user lookup for Skyfire identity
        mock_user = _make_mock_user("skyfire_skyfire_agent_001")
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        session.execute.return_value = mock_result

        with patch(
            "app.services.payments.skyfire_provider.SkyfirePaymentProvider",
            return_value=mock_skyfire_instance,
        ):
            identity = await get_agent_identity(request, session)

        assert identity.provider == "skyfire"
        assert identity.payer_id == "skyfire_agent_001"
        # Skyfire was used, so _verify_api_key should NOT have been called
        mock_skyfire_instance.can_handle.assert_awaited_once()
        mock_skyfire_instance.verify_jwt_only.assert_awaited_once_with(
            "eyJ.skyfire.token"
        )

    @pytest.mark.asyncio
    @patch("app.core.agent_auth.settings")
    async def test_api_key_fallback(self, mock_settings):
        """Without Skyfire header, falls back to API key authentication."""
        mock_settings.SKYFIRE_ENABLED = True
        mock_settings.MAX_CONCURRENT_ANALYSES = 3

        request = _make_request({"X-API-Key": "tru8_key_abc123"})
        session = _make_session()

        # Mock the Skyfire provider to NOT handle (no skyfire header)
        mock_skyfire_instance = AsyncMock()
        mock_skyfire_instance.can_handle.return_value = False

        # Mock _verify_api_key to return a user dict
        mock_user_data = {"id": "user-001", "email": "agent@test.com"}

        with patch(
            "app.services.payments.skyfire_provider.SkyfirePaymentProvider",
            return_value=mock_skyfire_instance,
        ), patch(
            "app.core.auth._verify_api_key",
            new_callable=AsyncMock,
            return_value=mock_user_data,
        ) as mock_verify:
            identity = await get_agent_identity(request, session)

        assert identity.provider == "credit"
        assert identity.payer_id == "user-001"
        assert identity.user_id == "user-001"
        mock_verify.assert_awaited_once_with("tru8_key_abc123", session)

    @pytest.mark.asyncio
    @patch("app.core.agent_auth.settings")
    async def test_no_credentials_401(self, mock_settings):
        """Without any authentication headers, raises 401 HTTPException."""
        mock_settings.SKYFIRE_ENABLED = True
        mock_settings.MAX_CONCURRENT_ANALYSES = 3

        request = _make_request({})  # No auth headers
        session = _make_session()

        # Mock the Skyfire provider to NOT handle
        mock_skyfire_instance = AsyncMock()
        mock_skyfire_instance.can_handle.return_value = False

        with patch(
            "app.services.payments.skyfire_provider.SkyfirePaymentProvider",
            return_value=mock_skyfire_instance,
        ):
            with pytest.raises(HTTPException) as exc_info:
                await get_agent_identity(request, session)

        assert exc_info.value.status_code == 401
        assert "Agent authentication required" in exc_info.value.detail

    @pytest.mark.asyncio
    @patch("app.core.agent_auth.settings")
    async def test_skyfire_disabled_falls_to_api_key(self, mock_settings):
        """When SKYFIRE_ENABLED=False, Skyfire is skipped even with header present."""
        mock_settings.SKYFIRE_ENABLED = False
        mock_settings.MAX_CONCURRENT_ANALYSES = 3

        request = _make_request(
            {
                "skyfire-pay-id": "eyJ.skyfire.token",
                "X-API-Key": "tru8_key_abc123",
            }
        )
        session = _make_session()

        # Mock the Skyfire provider — can_handle will return False because
        # SKYFIRE_ENABLED is False (the real implementation checks settings)
        mock_skyfire_instance = AsyncMock()
        mock_skyfire_instance.can_handle.return_value = False

        # Mock _verify_api_key
        mock_user_data = {"id": "user-002", "email": "agent@test.com"}

        with patch(
            "app.services.payments.skyfire_provider.SkyfirePaymentProvider",
            return_value=mock_skyfire_instance,
        ), patch(
            "app.core.auth._verify_api_key",
            new_callable=AsyncMock,
            return_value=mock_user_data,
        ) as mock_verify:
            identity = await get_agent_identity(request, session)

        assert identity.provider == "credit"
        assert identity.user_id == "user-002"
        # Skyfire can_handle was called but returned False
        mock_skyfire_instance.can_handle.assert_awaited_once()
        # verify_jwt_only should NOT have been called
        mock_skyfire_instance.verify_jwt_only.assert_not_awaited()
        # API key was used instead
        mock_verify.assert_awaited_once_with("tru8_key_abc123", session)

    @pytest.mark.asyncio
    @patch("app.core.agent_auth.settings")
    async def test_skyfire_jwt_failure_returns_401(self, mock_settings):
        """When Skyfire JWT verification fails, raises 401 (does not fall through)."""
        mock_settings.SKYFIRE_ENABLED = True
        mock_settings.MAX_CONCURRENT_ANALYSES = 3

        request = _make_request({"skyfire-pay-id": "bad.jwt.token"})
        session = _make_session()

        mock_skyfire_instance = AsyncMock()
        mock_skyfire_instance.can_handle.return_value = True
        mock_skyfire_instance.verify_jwt_only.side_effect = ValueError(
            "Skyfire token has expired"
        )

        with patch(
            "app.services.payments.skyfire_provider.SkyfirePaymentProvider",
            return_value=mock_skyfire_instance,
        ):
            with pytest.raises(HTTPException) as exc_info:
                await get_agent_identity(request, session)

        assert exc_info.value.status_code == 401
        assert "Skyfire token has expired" in exc_info.value.detail
