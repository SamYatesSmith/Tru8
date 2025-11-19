"""
Clear ALL cache entries from Redis
"""
import asyncio
import redis.asyncio as redis
from app.core.config import settings

async def clear_all_cache():
    """Clear all cache entries"""
    try:
        # Connect to Redis
        client = redis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5
        )

        # Test connection
        await client.ping()
        print("[OK] Connected to Redis")

        # Pattern for ALL tru8 keys
        pattern = "tru8:*"

        # Scan for matching keys
        keys_to_delete = []
        async for key in client.scan_iter(match=pattern, count=100):
            keys_to_delete.append(key)

        if not keys_to_delete:
            print("[INFO] No cache entries found")
            await client.aclose()
            return

        print(f"[DELETE] Found {len(keys_to_delete)} cached entries")

        # Delete all matching keys
        deleted_count = await client.delete(*keys_to_delete)
        print(f"[OK] Deleted {deleted_count} cache entries")

        # Verify deletion
        remaining = 0
        async for key in client.scan_iter(match=pattern, count=100):
            remaining += 1

        if remaining == 0:
            print("[OK] All cache entries successfully cleared")
        else:
            print(f"[WARNING] {remaining} cache entries still remain")

        await client.aclose()

    except Exception as e:
        print(f"[ERROR] Error clearing cache: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(clear_all_cache())
