"""
Rate limiting configuration.

Shared limiter instance used by both main.py and route handlers.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import settings

# Shared limiter instance - uses Redis in production, in-memory in development
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[f"{settings.RATE_LIMIT_PER_MINUTE}/minute"],
    storage_uri=settings.REDIS_URL if settings.ENVIRONMENT != "development" else None,
)
