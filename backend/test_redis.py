import redis.asyncio as redis
from app.core.config import settings
import asyncio

async def test_redis():
    try:
        r = redis.from_url(settings.REDIS_URL)
        await r.ping()
        print('Redis connection successful')
        await r.aclose()
    except Exception as e:
        print(f'Redis connection failed: {e}')

asyncio.run(test_redis())