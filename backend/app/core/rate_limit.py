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


def _client_ip(request: Request) -> str:
    """The caller's address, not our proxy's.

    Production is Cloudflare -> Railway's proxy -> uvicorn, and uvicorn is not
    told to trust forwarded headers, so `request.client.host` is a proxy
    address shared by every caller: each IP-keyed limit was one bucket for the
    whole site (verifier, 2026-11-02). Cloudflare sets CF-Connecting-IP itself
    (a client cannot forge it through Cloudflare); X-Forwarded-For's first hop
    covers other proxies. A forged header can only dodge a limit, never borrow
    someone else's privileges.
    """
    cf = request.headers.get("cf-connecting-ip")
    if cf and cf.strip():
        return cf.strip()
    xff = request.headers.get("x-forwarded-for")
    if xff and xff.split(",")[0].strip():
        return xff.split(",")[0].strip()
    return get_remote_address(request)


def _get_rate_limit_key(request: Request) -> str:
    """Rate limit by API key if present, otherwise by the caller's IP."""
    api_key = request.headers.get("X-API-Key")
    if api_key:
        # Use prefix only — full key should not be stored in Redis
        return f"apikey:{api_key[:20]}"
    return _client_ip(request)


# Shared limiter instance - uses Redis in production, in-memory in development
limiter = Limiter(
    key_func=_get_rate_limit_key,
    default_limits=[f"{settings.RATE_LIMIT_PER_MINUTE}/minute"],
    storage_uri=settings.REDIS_URL if settings.ENVIRONMENT != "development" else None,
)
