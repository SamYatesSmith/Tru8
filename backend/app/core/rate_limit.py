"""
Rate limiting configuration.

Shared limiter instance used by both main.py and route handlers.
Keys by API key (X-API-Key header) when present, falls back to IP address.
This prevents agents behind shared cloud IPs from interfering with each other.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request

from app.core.config import settings


def _get_rate_limit_key(request: Request) -> str:
    """Rate limit by API key if present, otherwise by IP address."""
    api_key = request.headers.get("X-API-Key")
    if api_key:
        # Use prefix only — full key should not be stored in Redis
        return f"apikey:{api_key[:20]}"
    return get_remote_address(request)


# Shared limiter instance - uses Redis in production, in-memory in development
limiter = Limiter(
    key_func=_get_rate_limit_key,
    default_limits=[f"{settings.RATE_LIMIT_PER_MINUTE}/minute"],
    storage_uri=settings.REDIS_URL if settings.ENVIRONMENT != "development" else None,
)
