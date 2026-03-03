"""Tests for SIWE challenge/verify helpers in app.core.siwe_verifier.

Validates:
  - generate_challenge stores nonce in Redis with correct key/TTL
  - generate_challenge raises RuntimeError when Redis is unavailable
  - verify_signature succeeds with valid signature + nonce
  - verify_signature fails on expired nonce (Redis returns None)
  - verify_signature fails on replayed nonce (second attempt returns None)
  - verify_signature fails on URI mismatch
  - verify_signature fails when nonce was issued for a different address
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.core.siwe_verifier import generate_challenge, verify_signature


MOCK_DOMAIN = "app.tru8.com"
MOCK_NONCE_TTL = 300
MOCK_ADDRESS = "0xabcdef1234567890abcdef1234567890abcdef12"
MOCK_CHECK_ID = "check-001"


@pytest.fixture
def mock_redis():
    """Return an AsyncMock Redis client."""
    r = AsyncMock()
    r.setex = AsyncMock()
    r.getdel = AsyncMock()
    return r


@pytest.fixture
def mock_settings():
    """Patch settings with test values."""
    with patch("app.core.siwe_verifier.settings") as s:
        s.SIWE_DOMAIN = MOCK_DOMAIN
        s.SIWE_NONCE_TTL_SECONDS = MOCK_NONCE_TTL
        yield s


# ---------------------------------------------------------------------------
# generate_challenge
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_generate_challenge_stores_nonce(mock_redis, mock_settings):
    """generate_challenge should store the nonce in Redis with setex and correct TTL."""
    with patch("app.core.siwe_verifier.get_redis", return_value=mock_redis), patch(
        "app.core.siwe_verifier.SiweMessage"
    ) as MockSiweMessage:
        mock_msg_instance = MagicMock()
        mock_msg_instance.prepare_message.return_value = "siwe-message-text"
        MockSiweMessage.return_value = mock_msg_instance

        result = await generate_challenge(MOCK_ADDRESS, MOCK_CHECK_ID)

    # Redis setex should have been called
    mock_redis.setex.assert_awaited_once()
    call_args = mock_redis.setex.await_args[0]
    redis_key = call_args[0]
    ttl = call_args[1]
    stored_value = call_args[2]

    assert redis_key.startswith("siwe:nonce:")
    assert ttl == MOCK_NONCE_TTL
    assert stored_value == f"{MOCK_ADDRESS}:{MOCK_CHECK_ID}"

    # Result should contain message and nonce
    assert "message" in result
    assert "nonce" in result
    assert result["message"] == "siwe-message-text"


@pytest.mark.asyncio
async def test_generate_challenge_redis_unavailable(mock_settings):
    """generate_challenge should raise RuntimeError when Redis returns None."""
    with patch("app.core.siwe_verifier.get_redis", return_value=None), patch(
        "app.core.siwe_verifier.SiweMessage"
    ) as MockSiweMessage:
        MockSiweMessage.return_value = MagicMock(
            prepare_message=MagicMock(return_value="msg")
        )
        with pytest.raises(RuntimeError, match="Redis unavailable"):
            await generate_challenge(MOCK_ADDRESS, MOCK_CHECK_ID)


# ---------------------------------------------------------------------------
# verify_signature — success
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_verify_valid_signature(mock_redis, mock_settings):
    """Valid signature + valid nonce → returns the verified wallet address (lowercased)."""
    nonce = "abc123deadbeef"
    expected_uri = f"https://{MOCK_DOMAIN}/api/v1/agent/x402/result/{MOCK_CHECK_ID}"

    # Mock SiweMessage.from_message
    mock_message = MagicMock()
    mock_message.nonce = nonce
    mock_message.uri = expected_uri
    mock_message.address = MOCK_ADDRESS
    mock_message.verify = MagicMock()  # Does not raise → verification passes

    # Redis returns the valid stored value, then deletes it
    mock_redis.getdel = AsyncMock(return_value=f"{MOCK_ADDRESS}:{MOCK_CHECK_ID}")

    with patch("app.core.siwe_verifier.get_redis", return_value=mock_redis), patch(
        "app.core.siwe_verifier.SiweMessage"
    ) as MockSiweMessage:
        MockSiweMessage.from_message.return_value = mock_message

        address = await verify_signature(
            message_str="siwe-message-text",
            signature="0xsignature",
            expected_check_id=MOCK_CHECK_ID,
        )

    assert address == MOCK_ADDRESS.lower()
    mock_message.verify.assert_called_once()
    mock_redis.getdel.assert_awaited_once_with(f"siwe:nonce:{nonce}")


# ---------------------------------------------------------------------------
# verify_signature — failure: expired nonce
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_verify_expired_nonce(mock_redis, mock_settings):
    """Redis getdel returns None (nonce expired/missing) → raises ValueError."""
    nonce = "expired-nonce"
    expected_uri = f"https://{MOCK_DOMAIN}/api/v1/agent/x402/result/{MOCK_CHECK_ID}"

    mock_message = MagicMock()
    mock_message.nonce = nonce
    mock_message.uri = expected_uri
    mock_message.address = MOCK_ADDRESS
    mock_message.verify = MagicMock()

    mock_redis.getdel = AsyncMock(return_value=None)

    with patch("app.core.siwe_verifier.get_redis", return_value=mock_redis), patch(
        "app.core.siwe_verifier.SiweMessage"
    ) as MockSiweMessage:
        MockSiweMessage.from_message.return_value = mock_message

        with pytest.raises(ValueError, match="Nonce expired or already used"):
            await verify_signature(
                message_str="siwe-message-text",
                signature="0xsignature",
                expected_check_id=MOCK_CHECK_ID,
            )


# ---------------------------------------------------------------------------
# verify_signature — failure: replayed nonce (second use)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_verify_replayed_nonce(mock_redis, mock_settings):
    """Second verify attempt with the same nonce fails — Redis returns None after first getdel."""
    nonce = "one-time-nonce"
    expected_uri = f"https://{MOCK_DOMAIN}/api/v1/agent/x402/result/{MOCK_CHECK_ID}"

    mock_message = MagicMock()
    mock_message.nonce = nonce
    mock_message.uri = expected_uri
    mock_message.address = MOCK_ADDRESS
    mock_message.verify = MagicMock()

    # First call succeeds, second call returns None (nonce already consumed)
    mock_redis.getdel = AsyncMock(side_effect=[f"{MOCK_ADDRESS}:{MOCK_CHECK_ID}", None])

    with patch("app.core.siwe_verifier.get_redis", return_value=mock_redis), patch(
        "app.core.siwe_verifier.SiweMessage"
    ) as MockSiweMessage:
        MockSiweMessage.from_message.return_value = mock_message

        # First call — should succeed
        address = await verify_signature(
            message_str="siwe-message-text",
            signature="0xsignature",
            expected_check_id=MOCK_CHECK_ID,
        )
        assert address == MOCK_ADDRESS.lower()

        # Second call — nonce already consumed → ValueError
        with pytest.raises(ValueError, match="Nonce expired or already used"):
            await verify_signature(
                message_str="siwe-message-text",
                signature="0xsignature",
                expected_check_id=MOCK_CHECK_ID,
            )


# ---------------------------------------------------------------------------
# verify_signature — failure: URI mismatch
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_verify_uri_mismatch(mock_redis, mock_settings):
    """message.uri does not match expected URI → raises ValueError."""
    nonce = "uri-mismatch-nonce"

    mock_message = MagicMock()
    mock_message.nonce = nonce
    mock_message.uri = "https://evil.com/api/v1/agent/x402/result/wrong-check"
    mock_message.address = MOCK_ADDRESS
    mock_message.verify = MagicMock()

    with patch("app.core.siwe_verifier.get_redis", return_value=mock_redis), patch(
        "app.core.siwe_verifier.SiweMessage"
    ) as MockSiweMessage:
        MockSiweMessage.from_message.return_value = mock_message

        with pytest.raises(ValueError, match="SIWE URI mismatch"):
            await verify_signature(
                message_str="siwe-message-text",
                signature="0xsignature",
                expected_check_id=MOCK_CHECK_ID,
            )

    # Redis getdel should NOT have been called — URI check happens before nonce check
    mock_redis.getdel.assert_not_awaited()


# ---------------------------------------------------------------------------
# verify_signature — failure: nonce issued for wrong address
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_verify_wrong_address(mock_redis, mock_settings):
    """Nonce was issued for a different address → raises ValueError."""
    nonce = "wrong-addr-nonce"
    expected_uri = f"https://{MOCK_DOMAIN}/api/v1/agent/x402/result/{MOCK_CHECK_ID}"
    different_address = "0x9999999999999999999999999999999999999999"

    mock_message = MagicMock()
    mock_message.nonce = nonce
    mock_message.uri = expected_uri
    mock_message.address = MOCK_ADDRESS  # Signer claims to be MOCK_ADDRESS
    mock_message.verify = MagicMock()

    # But the nonce was issued for a DIFFERENT address
    mock_redis.getdel = AsyncMock(return_value=f"{different_address}:{MOCK_CHECK_ID}")

    with patch("app.core.siwe_verifier.get_redis", return_value=mock_redis), patch(
        "app.core.siwe_verifier.SiweMessage"
    ) as MockSiweMessage:
        MockSiweMessage.from_message.return_value = mock_message

        with pytest.raises(ValueError, match="different address or check"):
            await verify_signature(
                message_str="siwe-message-text",
                signature="0xsignature",
                expected_check_id=MOCK_CHECK_ID,
            )
