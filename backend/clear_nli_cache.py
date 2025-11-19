"""
Clear NLI verification cache to remove stale verdicts

This script clears all cached NLI verification results to ensure fresh API calls
are made with the working rate limiter.
"""
import asyncio
import redis.asyncio as redis
from app.core.config import settings

async def clear_nli_cache():
    """Clear all NLI verification cache entries"""
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

        # Pattern for NLI verification keys
        pattern = "tru8:nli_verification:*"

        # Scan for matching keys
        keys_to_delete = []
        async for key in client.scan_iter(match=pattern, count=100):
            keys_to_delete.append(key)

        if not keys_to_delete:
            print("[INFO] No NLI verification cache entries found")
            await client.close()
            return

        print(f"[DELETE] Found {len(keys_to_delete)} cached NLI verification entries")

        # Delete all matching keys
        deleted_count = await client.delete(*keys_to_delete)
        print(f"[OK] Deleted {deleted_count} cache entries")

        # Verify deletion
        remaining = 0
        async for key in client.scan_iter(match=pattern, count=100):
            remaining += 1

        if remaining == 0:
            print("[OK] All NLI cache entries successfully cleared")
        else:
            print(f"[WARNING] {remaining} cache entries still remain")

        await client.close()

    except Exception as e:
        print(f"[ERROR] Error clearing cache: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(clear_nli_cache())
