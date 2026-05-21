from typing import Optional
from fastapi import Depends, HTTPException, status, Request, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
import hashlib
import asyncio
import httpx
import json
import jwt
import logging
import redis.asyncio as aioredis
from jwt import PyJWKClient
from datetime import datetime, timezone
from app.core.config import settings
from app.core.database import get_session, async_session

logger = logging.getLogger(__name__)

security = HTTPBearer()

# Clerk JWKS client with cache refresh
jwks_client = PyJWKClient(
    f"https://{settings.CLERK_JWT_ISSUER}/.well-known/jwks.json",
    cache_keys=True,
    max_cached_keys=16,
    cache_jwk_set=300,  # Cache for 5 minutes, then refresh
)

API_KEY_PREFIX = "tru8_sk_"


# ---------------------------------------------------------------------------
# JWT verification (unchanged)
# ---------------------------------------------------------------------------


async def _verify_jwt_token(token: str) -> dict:
    """Shared JWT verification logic.

    F-AUTH-03: when ``settings.CLERK_JWT_AUDIENCE`` is set, the ``aud`` claim
    is enforced. When unset, the legacy permissive behaviour is retained so
    operators not yet running a Clerk JWT template with an audience aren't
    locked out — set it as part of the launch checklist.
    """
    try:
        signing_key = jwks_client.get_signing_key_from_jwt(token)

        expected_issuer = f"https://{settings.CLERK_JWT_ISSUER}"
        expected_audience = settings.CLERK_JWT_AUDIENCE or None

        decode_options = {"verify_aud": bool(expected_audience)}
        decode_kwargs = {
            "algorithms": ["RS256"],
            "issuer": expected_issuer,
            "leeway": 60,
            "options": decode_options,
        }
        if expected_audience:
            decode_kwargs["audience"] = expected_audience

        payload = jwt.decode(token, signing_key.key, **decode_kwargs)

        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has expired"
        )
    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Invalid token: {str(e)}"
        )


async def verify_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    return await _verify_jwt_token(credentials.credentials)


# ---------------------------------------------------------------------------
# Clerk user data fetch (unchanged)
# ---------------------------------------------------------------------------


async def _fetch_user_data_from_clerk(user_id: str, token_payload: dict) -> dict:
    """
    Fetch user email and name from JWT claims or Clerk API.

    Fallback chain: JWT fields → Clerk API → email prefix.
    """
    email = token_payload.get("email")
    name = token_payload.get("name")

    if not email or not name:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"https://api.clerk.com/v1/users/{user_id}",
                    headers={
                        "Authorization": f"Bearer {settings.CLERK_SECRET_KEY}",
                        "Content-Type": "application/json",
                    },
                )
                if response.status_code == 200:
                    user_data = response.json()

                    if not email:
                        email = user_data.get("email_addresses", [{}])[0].get(
                            "email_address"
                        )

                    if not name:
                        first_name = (
                            user_data.get("first_name", "").strip()
                            if user_data.get("first_name")
                            else ""
                        )
                        last_name = (
                            user_data.get("last_name", "").strip()
                            if user_data.get("last_name")
                            else ""
                        )

                        if first_name or last_name:
                            name = f"{first_name} {last_name}".strip()

                        if not name:
                            username = user_data.get("username")
                            if username:
                                name = username

                        if not name and email:
                            name = (
                                email.split("@")[0]
                                .replace(".", " ")
                                .replace("_", " ")
                                .title()
                            )
                else:
                    pass
        except Exception as e:
            pass

    return {
        "id": user_id,
        "email": email,
        "name": name,
    }


# ---------------------------------------------------------------------------
# API key verification
# ---------------------------------------------------------------------------


def _hash_api_key(raw_key: str) -> str:
    """SHA-256 hash — used for storage and lookup. Raw key is never persisted."""
    return hashlib.sha256(raw_key.encode()).hexdigest()


async def _verify_api_key(raw_key: str, session: AsyncSession) -> dict:
    """
    Verify an API key and return a user dict identical in shape to JWT auth.

    Looks up the key hash, checks active/expiry status, resolves the owning
    user from our DB (no Clerk call needed — user already exists).
    """
    from app.models.api_key import APIKey
    from app.models.user import User

    if not raw_key.startswith(API_KEY_PREFIX):
        raise HTTPException(status_code=401, detail="Invalid API key")

    key_hash = _hash_api_key(raw_key)

    result = await session.execute(
        select(APIKey).where(APIKey.key_hash == key_hash, APIKey.is_active == True)
    )
    key_record = result.scalar_one_or_none()

    if not key_record:
        raise HTTPException(status_code=401, detail="Invalid API key")

    if key_record.expires_at and key_record.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="API key has expired")

    user_result = await session.execute(
        select(User).where(User.id == key_record.user_id)
    )
    user = user_result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=401, detail="Invalid API key")

    # Best-effort usage tracking — separate session so it never blocks the request
    asyncio.create_task(_record_api_key_usage(key_record.id))

    return {"id": user.id, "email": user.email, "name": user.name}


async def _record_api_key_usage(key_id: str):
    """Background: increment usage_count and touch last_used_at."""
    try:
        async with async_session() as session:
            await session.execute(
                text(
                    "UPDATE api_key SET last_used_at = :now, usage_count = usage_count + 1 "
                    "WHERE id = :id"
                ),
                {"now": datetime.now(timezone.utc), "id": key_id},
            )
            await session.commit()
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Auth dependencies — JWT only (unchanged, used by upload + key management)
# ---------------------------------------------------------------------------


async def get_current_user(token_payload: dict = Depends(verify_token)) -> dict:
    """
    JWT-only auth. Used by endpoints that should never accept API keys
    (file upload, API key management).
    """
    user_id = token_payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload"
        )

    return await _fetch_user_data_from_clerk(user_id, token_payload)


async def get_current_user_sse(
    request: Request, token: Optional[str] = Query(None)
) -> dict:
    """
    JWT-only SSE auth. Kept for backwards compatibility — only used by
    endpoints that don't need API key support (currently none, but available).
    """
    jwt_token = None

    if token:
        jwt_token = token
    else:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            jwt_token = auth_header[7:]

    if not jwt_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No authentication token provided",
        )

    payload = await _verify_jwt_token(jwt_token)

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload"
        )

    return await _fetch_user_data_from_clerk(user_id, payload)


# ---------------------------------------------------------------------------
# Dual auth dependencies — JWT or API key (new, used by most check endpoints)
# ---------------------------------------------------------------------------


async def get_current_user_or_api_key(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """
    Dual auth: Clerk JWT (Authorization: Bearer) or API key (X-API-Key).

    Dashboard sends JWT. Agent/developer consumers send API key.
    Returns the same {id, email, name} dict regardless of auth method.
    """
    # Bearer JWT
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        jwt_token = auth_header[7:]
        payload = await _verify_jwt_token(jwt_token)
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token payload")
        return await _fetch_user_data_from_clerk(user_id, payload)

    # API key
    api_key = request.headers.get("X-API-Key")
    if api_key:
        return await _verify_api_key(api_key, session)

    raise HTTPException(
        status_code=401,
        detail="Authentication required. Use Authorization: Bearer <jwt> or X-API-Key: <key>.",
    )


async def _verify_stream_token(
    token_value: str, check_id: Optional[str]
) -> Optional[dict]:
    """
    Try to validate a stream token from Redis.

    Returns a user dict if valid, or None if the token is not a stream token
    (caller should fall back to JWT verification).
    """
    try:
        r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        token_key = f"sse-token:{token_value}"
        payload_json = await r.get(token_key)
        if payload_json:
            await r.delete(token_key)  # Single-use: consume on first verification
        await r.aclose()

        if not payload_json:
            return None

        payload = json.loads(payload_json)

        # Scope check: token must match the requested check_id
        if check_id and payload.get("check_id") != check_id:
            logger.warning(
                f"[AUTH] Stream token check_id mismatch: "
                f"token={payload.get('check_id')}, request={check_id}"
            )
            raise HTTPException(
                status_code=403, detail="Stream token not valid for this check"
            )

        return {"id": payload["user_id"], "email": None, "name": None}

    except HTTPException:
        raise
    except Exception as e:
        logger.warning(f"[AUTH] Stream token Redis lookup failed: {e}")
        return None


async def get_current_user_or_api_key_sse(
    request: Request,
    token: Optional[str] = Query(None),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """
    Dual auth for SSE/streaming endpoints.

    Accepts (in priority order):
    1. ?token=<stream_token>  — short-lived, check-scoped token from POST /sse-token
    2. ?token=<jwt>  — deprecated fallback, logs warning
    3. Authorization: Bearer <jwt>
    4. X-API-Key: <key>  — agents use standard HTTP clients, not EventSource
    """
    # Stream token or JWT from query param
    if token:
        # Try as stream token first (Redis lookup)
        check_id = request.path_params.get("check_id")
        stream_user = await _verify_stream_token(token, check_id)
        if stream_user:
            return stream_user

        # Fall back to JWT (deprecated path)
        logger.warning(
            "[AUTH] DEPRECATION: JWT passed as query parameter. "
            "Use POST /checks/{id}/sse-token to get a stream token."
        )
        payload = await _verify_jwt_token(token)
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token payload")
        return await _fetch_user_data_from_clerk(user_id, payload)

    # Bearer JWT from header
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        jwt_token = auth_header[7:]
        payload = await _verify_jwt_token(jwt_token)
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token payload")
        return await _fetch_user_data_from_clerk(user_id, payload)

    # API key from header
    api_key = request.headers.get("X-API-Key")
    if api_key:
        return await _verify_api_key(api_key, session)

    raise HTTPException(
        status_code=401,
        detail="No authentication provided.",
    )
