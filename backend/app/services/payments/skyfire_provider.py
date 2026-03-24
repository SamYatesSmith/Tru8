"""Skyfire KYAPay payment provider — JWT verification + charge API (L-06).

Skyfire issues short-lived JWTs with usage entitlements.  We verify the token
via Skyfire's JWKS endpoint, validate that the expiry leaves enough headroom
for the requested pipeline tier, then POST a charge to the Skyfire settlement
API after the pipeline completes.

Pattern reused from ``app.core.auth`` (Clerk JWKS verification, lines 20-59).
"""

import logging
import time
from typing import Optional

import httpx
import jwt
from fastapi import Request
from jwt import PyJWKClient

from app.core.config import settings

from .base import PaymentProvider, PaymentVerification

logger = logging.getLogger(__name__)

# Module-level singleton — created once, cached forever.
# ``cache_jwk_set`` controls TTL-based refresh (default 300s from settings).
_jwks_client: Optional[PyJWKClient] = None


def _get_jwks_client() -> PyJWKClient:
    """Lazy singleton — avoids import-time network calls when Skyfire is off."""
    global _jwks_client
    if _jwks_client is None:
        _jwks_client = PyJWKClient(
            settings.SKYFIRE_JWKS_URL,
            cache_keys=True,
            max_cached_keys=16,
            cache_jwk_set=settings.SKYFIRE_JWKS_CACHE_SECONDS,
        )
    return _jwks_client


# Minimum seconds of token validity required per tier.
# Includes a 30-second safety margin for clock skew / network latency.
_TIER_HEADROOM_SECONDS = {
    "lookup": 30,
    "quick": 60,
    "full": 150,
}


class SkyfirePaymentProvider(PaymentProvider):
    """Skyfire JWT identity + payment tokens.

    ``can_handle`` checks both header presence AND the feature flag, so when
    ``SKYFIRE_ENABLED=False`` the provider is invisible to the auth chain.
    """

    async def can_handle(self, request: Request) -> bool:
        return settings.SKYFIRE_ENABLED and "skyfire-pay-id" in request.headers

    async def verify_and_charge(
        self, request: Request, amount_pence: int, description: str
    ) -> PaymentVerification:
        """Verify JWT, check expiry headroom, and charge via Skyfire API."""
        token = request.headers["skyfire-pay-id"]

        # --- JWT verification via JWKS ---
        payload = await self._verify_jwt(token)

        # --- Charge via Skyfire settlement API ---
        tx_ref = await self._charge(payload, amount_pence, description)

        return PaymentVerification(
            provider="skyfire",
            payer_id=payload.get("sub", "unknown"),
            amount_pence=amount_pence,
            transaction_ref=tx_ref,
            metadata={
                "skyfire_service_id": payload.get("service_id"),
                "skyfire_env": settings.SKYFIRE_ENVIRONMENT,
            },
        )

    async def verify_jwt_only(self, token: str) -> dict:
        """Verify JWT and return payload — identity only, no charge.

        Used by ``get_agent_identity`` for retrieval endpoints that don't
        need to settle a payment.
        """
        return await self._verify_jwt(token)

    async def _verify_jwt(self, token: str) -> dict:
        """Verify Skyfire JWT via JWKS.  Raises on invalid/expired token."""
        try:
            client = _get_jwks_client()
            signing_key = client.get_signing_key_from_jwt(token)

            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=["ES256"],
                options={"verify_aud": False},
                leeway=10,
            )
            return payload

        except jwt.ExpiredSignatureError:
            raise ValueError("Skyfire token has expired")
        except jwt.InvalidTokenError as e:
            raise ValueError(f"Invalid Skyfire token: {e}")
        except Exception as e:
            raise ValueError(f"Skyfire JWT verification failed: {e}")

    def validate_expiry_headroom(self, payload: dict, tier: str) -> None:
        """Raise if the token will expire before the tier can finish.

        Called by the agent endpoint handler BEFORE starting the pipeline,
        so we fail fast rather than running and failing to settle.
        """
        exp = payload.get("exp", 0)
        headroom = _TIER_HEADROOM_SECONDS.get(tier, 150)
        remaining = exp - time.time()

        if remaining < headroom:
            raise ValueError(
                f"Skyfire token expires in {remaining:.0f}s but tier '{tier}' "
                f"needs at least {headroom}s.  Request a longer-lived token."
            )

    async def _charge(self, payload: dict, amount_pence: int, description: str) -> str:
        """POST charge to Skyfire settlement API.  Returns transaction ref."""
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.post(
                    settings.SKYFIRE_CHARGE_URL,
                    headers={
                        "Authorization": f"Bearer {settings.SKYFIRE_API_KEY}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "service_id": settings.SKYFIRE_SERVICE_ID,
                        "payer_id": payload.get("sub"),
                        "amount_pence": amount_pence,
                        "currency": "GBP",
                        "description": description,
                        "environment": settings.SKYFIRE_ENVIRONMENT,
                    },
                )
        except httpx.HTTPError as e:
            raise RuntimeError(f"Skyfire charge failed: {e}")

        if response.status_code not in (200, 201):
            logger.error(
                "Skyfire charge failed: %d %s", response.status_code, response.text
            )
            raise ValueError(f"Skyfire charge failed (HTTP {response.status_code})")

        data = response.json()
        return data.get("transaction_id", data.get("id", ""))
