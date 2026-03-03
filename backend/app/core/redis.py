import redis.asyncio as redis

from app.core.config import settings

_redis_client: redis.Redis | None = None


async def get_redis() -> redis.Redis | None:
    """Get or create async Redis client for caching."""
    global _redis_client
    if _redis_client is None:
        try:
            _redis_client = redis.from_url(
                settings.REDIS_URL,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
            )
            await _redis_client.ping()
        except Exception:
            _redis_client = None
            return None
    return _redis_client
