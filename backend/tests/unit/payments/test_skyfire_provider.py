"""Track L: Skyfire payment provider unit tests.

Tests for SkyfirePaymentProvider — JWT verification via JWKS,
expiry headroom validation, and charge API calls.
"""

import time
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import jwt as pyjwt
import pytest

from app.services.payments.skyfire_provider import (
    SkyfirePaymentProvider,
    _get_jwks_client,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def provider():
    return SkyfirePaymentProvider()


def _make_request(headers: dict) -> MagicMock:
    """Build a minimal mock Request with the given headers."""
    req = MagicMock()
    req.headers = headers
    return req


# ---------------------------------------------------------------------------
# can_handle
# ---------------------------------------------------------------------------


class TestCanHandle:
    """Tests for SkyfirePaymentProvider.can_handle()."""

    @pytest.mark.asyncio
    @patch("app.services.payments.skyfire_provider.settings")
    async def test_can_handle_with_header_and_enabled(self, mock_settings, provider):
        """Returns True when skyfire-pay-id header is present and SKYFIRE_ENABLED=True."""
        mock_settings.SKYFIRE_ENABLED = True
        request = _make_request({"skyfire-pay-id": "tok_abc123"})

        result = await provider.can_handle(request)

        assert result is True

    @pytest.mark.asyncio
    @patch("app.services.payments.skyfire_provider.settings")
    async def test_can_handle_without_header(self, mock_settings, provider):
        """Returns False when skyfire-pay-id header is missing."""
        mock_settings.SKYFIRE_ENABLED = True
        request = _make_request({"x-api-key": "tru8_key_abc"})

        result = await provider.can_handle(request)

        assert result is False

    @pytest.mark.asyncio
    @patch("app.services.payments.skyfire_provider.settings")
    async def test_can_handle_disabled(self, mock_settings, provider):
        """Returns False when SKYFIRE_ENABLED=False, even with header present."""
        mock_settings.SKYFIRE_ENABLED = False
        request = _make_request({"skyfire-pay-id": "tok_abc123"})

        result = await provider.can_handle(request)

        assert result is False


# ---------------------------------------------------------------------------
# _verify_jwt
# ---------------------------------------------------------------------------


class TestVerifyJWT:
    """Tests for SkyfirePaymentProvider._verify_jwt()."""

    @pytest.mark.asyncio
    @patch("app.services.payments.skyfire_provider._get_jwks_client")
    @patch("app.services.payments.skyfire_provider.jwt.decode")
    async def test_verify_jwt_valid(self, mock_decode, mock_get_client, provider):
        """Valid JWT returns decoded payload."""
        mock_signing_key = MagicMock()
        mock_signing_key.key = "test-key"
        mock_client = MagicMock()
        mock_client.get_signing_key_from_jwt.return_value = mock_signing_key
        mock_get_client.return_value = mock_client

        expected_payload = {
            "sub": "skyfire_agent_001",
            "service_id": "svc_tru8",
            "exp": int(time.time()) + 300,
        }
        mock_decode.return_value = expected_payload

        payload = await provider._verify_jwt("valid.jwt.token")

        assert payload == expected_payload
        mock_client.get_signing_key_from_jwt.assert_called_once_with("valid.jwt.token")
        mock_decode.assert_called_once_with(
            "valid.jwt.token",
            "test-key",
            algorithms=["ES256"],
            options={"verify_aud": False},
            leeway=10,
        )

    @pytest.mark.asyncio
    @patch("app.services.payments.skyfire_provider._get_jwks_client")
    @patch("app.services.payments.skyfire_provider.jwt.decode")
    async def test_verify_jwt_expired(self, mock_decode, mock_get_client, provider):
        """Expired JWT raises ValueError with descriptive message."""
        mock_signing_key = MagicMock()
        mock_signing_key.key = "test-key"
        mock_client = MagicMock()
        mock_client.get_signing_key_from_jwt.return_value = mock_signing_key
        mock_get_client.return_value = mock_client

        mock_decode.side_effect = pyjwt.ExpiredSignatureError("token expired")

        with pytest.raises(ValueError, match="Skyfire token has expired"):
            await provider._verify_jwt("expired.jwt.token")

    @pytest.mark.asyncio
    @patch("app.services.payments.skyfire_provider._get_jwks_client")
    @patch("app.services.payments.skyfire_provider.jwt.decode")
    async def test_verify_jwt_invalid(self, mock_decode, mock_get_client, provider):
        """Invalid JWT raises ValueError with error detail."""
        mock_signing_key = MagicMock()
        mock_signing_key.key = "test-key"
        mock_client = MagicMock()
        mock_client.get_signing_key_from_jwt.return_value = mock_signing_key
        mock_get_client.return_value = mock_client

        mock_decode.side_effect = pyjwt.InvalidTokenError("bad signature")

        with pytest.raises(ValueError, match="Invalid Skyfire token"):
            await provider._verify_jwt("invalid.jwt.token")

    @pytest.mark.asyncio
    @patch("app.services.payments.skyfire_provider._get_jwks_client")
    async def test_verify_jwt_jwks_network_error(self, mock_get_client, provider):
        """JWKS network error (connection refused) raises ValueError."""
        mock_client = MagicMock()
        mock_client.get_signing_key_from_jwt.side_effect = Exception(
            "connection refused"
        )
        mock_get_client.return_value = mock_client

        with pytest.raises(ValueError, match="Skyfire JWT verification failed"):
            await provider._verify_jwt("some.jwt.token")


# ---------------------------------------------------------------------------
# validate_expiry_headroom
# ---------------------------------------------------------------------------


class TestValidateExpiryHeadroom:
    """Tests for SkyfirePaymentProvider.validate_expiry_headroom()."""

    def test_validate_expiry_headroom_ok(self, provider):
        """Token with sufficient expiry passes validation."""
        payload = {"exp": time.time() + 200}

        # Should not raise — full tier needs 150s and we have 200s
        provider.validate_expiry_headroom(payload, "full")

    def test_validate_expiry_headroom_insufficient(self, provider):
        """Token expiring too soon raises ValueError with tier details."""
        payload = {"exp": time.time() + 10}  # Only 10s left

        with pytest.raises(ValueError, match="needs at least 150s"):
            provider.validate_expiry_headroom(payload, "full")

    def test_validate_expiry_headroom_lookup_tier(self, provider):
        """Lookup tier has the smallest headroom requirement (30s)."""
        payload = {"exp": time.time() + 35}

        # Should not raise — lookup needs only 30s and we have 35s
        provider.validate_expiry_headroom(payload, "lookup")

    def test_validate_expiry_headroom_quick_tier_insufficient(self, provider):
        """Quick tier (60s) fails when token has less headroom."""
        payload = {"exp": time.time() + 20}

        with pytest.raises(ValueError, match="needs at least 60s"):
            provider.validate_expiry_headroom(payload, "quick")


# ---------------------------------------------------------------------------
# _charge
# ---------------------------------------------------------------------------


class TestCharge:
    """Tests for SkyfirePaymentProvider._charge()."""

    @pytest.mark.asyncio
    @patch("app.services.payments.skyfire_provider.settings")
    @patch("app.services.payments.skyfire_provider.httpx.AsyncClient")
    async def test_charge_success(self, mock_client_cls, mock_settings, provider):
        """Successful charge returns transaction_id from response."""
        mock_settings.SKYFIRE_CHARGE_URL = "https://api.skyfire.xyz/v1/charges"
        mock_settings.SKYFIRE_API_KEY = "sk_test_key"
        mock_settings.SKYFIRE_SERVICE_ID = "svc_tru8"
        mock_settings.SKYFIRE_ENVIRONMENT = "sandbox"

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"transaction_id": "tx_sf_001"}

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        payload = {"sub": "skyfire_agent_001"}
        tx_ref = await provider._charge(payload, 7, "Lookup tier query")

        assert tx_ref == "tx_sf_001"
        mock_client.post.assert_called_once()
        call_kwargs = mock_client.post.call_args
        assert call_kwargs.kwargs["json"]["amount_pence"] == 7
        assert call_kwargs.kwargs["json"]["payer_id"] == "skyfire_agent_001"

    @pytest.mark.asyncio
    @patch("app.services.payments.skyfire_provider.settings")
    @patch("app.services.payments.skyfire_provider.httpx.AsyncClient")
    async def test_charge_failure(self, mock_client_cls, mock_settings, provider):
        """Failed charge (HTTP 500) raises ValueError."""
        mock_settings.SKYFIRE_CHARGE_URL = "https://api.skyfire.xyz/v1/charges"
        mock_settings.SKYFIRE_API_KEY = "sk_test_key"
        mock_settings.SKYFIRE_SERVICE_ID = "svc_tru8"
        mock_settings.SKYFIRE_ENVIRONMENT = "sandbox"

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        payload = {"sub": "skyfire_agent_001"}

        with pytest.raises(ValueError, match="Skyfire charge failed"):
            await provider._charge(payload, 7, "Lookup tier query")

    @pytest.mark.asyncio
    @patch("app.services.payments.skyfire_provider.settings")
    @patch("app.services.payments.skyfire_provider.httpx.AsyncClient")
    async def test_charge_network_error(self, mock_client_cls, mock_settings, provider):
        """Network error (connection refused, DNS failure) raises RuntimeError."""
        mock_settings.SKYFIRE_CHARGE_URL = "https://api.skyfire.xyz/v1/charges"
        mock_settings.SKYFIRE_API_KEY = "sk_test_key"
        mock_settings.SKYFIRE_SERVICE_ID = "svc_tru8"
        mock_settings.SKYFIRE_ENVIRONMENT = "sandbox"

        mock_client = AsyncMock()
        mock_client.post.side_effect = httpx.ConnectError("connection refused")
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        payload = {"sub": "skyfire_agent_001"}

        with pytest.raises(RuntimeError, match="Skyfire charge failed"):
            await provider._charge(payload, 7, "Lookup tier query")


# ---------------------------------------------------------------------------
# JWKS singleton
# ---------------------------------------------------------------------------


class TestJWKSSingleton:
    """Tests for the module-level _get_jwks_client singleton."""

    @patch("app.services.payments.skyfire_provider._jwks_client", None)
    @patch("app.services.payments.skyfire_provider.settings")
    @patch("app.services.payments.skyfire_provider.PyJWKClient")
    def test_jwks_singleton(self, mock_pyjwk_cls, mock_settings):
        """_get_jwks_client returns the same instance on repeated calls."""
        mock_settings.SKYFIRE_JWKS_URL = (
            "https://auth.skyfire.xyz/.well-known/jwks.json"
        )
        mock_settings.SKYFIRE_JWKS_CACHE_SECONDS = 300

        mock_instance = MagicMock()
        mock_pyjwk_cls.return_value = mock_instance

        first = _get_jwks_client()
        second = _get_jwks_client()

        assert first is second
        # PyJWKClient should only be instantiated once
        mock_pyjwk_cls.assert_called_once()
