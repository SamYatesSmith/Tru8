"""SIWE (Sign-In With Ethereum) challenge/verify helpers for x402 result retrieval.

Nonces are stored in Redis with a configurable TTL (default 5 minutes)
and are single-use (deleted on first successful verification).

Critical: siwe-py does NOT validate ``message.uri`` — we check it manually
to ensure the signature is bound to the specific check retrieval URL.
"""

import logging
import secrets
import time
from typing import Optional

from app.core.config import settings
from app.core.redis import get_redis

try:
    from siwe import SiweMessage
except ImportError:
    SiweMessage = None  # type: ignore[assignment,misc]

logger = logging.getLogger(__name__)


async def generate_challenge(
    address: str, check_id: str, domain: Optional[str] = None
) -> dict:
    """Create a SIWE challenge message and store the nonce in Redis.

    Returns ``{"message": str, "nonce": str}`` or raises on Redis failure.
    """
    if SiweMessage is None:
        raise RuntimeError("siwe package is not installed — pip install siwe")
    domain = domain or settings.SIWE_DOMAIN
    nonce = secrets.token_hex(16)
    uri = f"https://{domain}/api/v1/agent/x402/result/{check_id}"
    issued_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    message = SiweMessage(
        domain=domain,
        address=address,
        statement=f"Retrieve Tru8 check result {check_id}",
        uri=uri,
        version="1",
        chain_id=1,
        nonce=nonce,
        issued_at=issued_at,
    )

    # Store nonce in Redis (single-use, TTL-bounded)
    redis = await get_redis()
    if redis is None:
        raise RuntimeError("Redis unavailable — cannot issue SIWE challenge")

    redis_key = f"siwe:nonce:{nonce}"
    try:
        await redis.setex(
            redis_key, settings.SIWE_NONCE_TTL_SECONDS, f"{address}:{check_id}"
        )
    except Exception as e:
        raise RuntimeError(f"Failed to store SIWE nonce: {e}")

    return {"message": message.prepare_message(), "nonce": nonce}


async def verify_signature(
    message_str: str,
    signature: str,
    expected_check_id: str,
    domain: Optional[str] = None,
) -> str:
    """Verify a SIWE signature and return the verified wallet address.

    Raises ``ValueError`` on any verification failure.
    """
    if SiweMessage is None:
        raise RuntimeError("siwe package is not installed — pip install siwe")
    domain = domain or settings.SIWE_DOMAIN

    try:
        message = SiweMessage.from_message(message_str)
    except Exception as e:
        raise ValueError(f"Invalid SIWE message: {e}")

    # Verify signature (checks address, domain, expiration, not-before)
    try:
        message.verify(signature, domain=domain)
    except Exception as e:
        raise ValueError(f"SIWE signature verification failed: {e}")

    # Manual URI binding check — siwe-py does NOT validate uri
    expected_uri = f"https://{domain}/api/v1/agent/x402/result/{expected_check_id}"
    if message.uri != expected_uri:
        raise ValueError(
            f"SIWE URI mismatch: expected {expected_uri}, got {message.uri}"
        )

    # Single-use nonce check via Redis
    redis = await get_redis()
    if redis is None:
        raise ValueError("Redis unavailable — cannot verify nonce")

    redis_key = f"siwe:nonce:{message.nonce}"
    stored = await redis.getdel(redis_key)  # Atomic get-and-delete (single-use)

    if stored is None:
        raise ValueError("Nonce expired or already used")

    # Verify the nonce was issued for this address + check_id
    expected_stored = f"{message.address}:{expected_check_id}"
    if stored != expected_stored:
        raise ValueError("Nonce was issued for a different address or check")

    return message.address.lower()
