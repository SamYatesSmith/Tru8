from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.core.database import get_session
from app.core.config import settings
import redis.asyncio as redis

router = APIRouter()

@router.get("/")
async def health_check():
    return {
        "status": "healthy",
        "environment": settings.ENVIRONMENT,
        "version": "0.1.0"
    }

@router.get("/ready")
async def readiness_check(session: AsyncSession = Depends(get_session)):
    checks = {}
    
    # Check database
    try:
        await session.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = f"error: {str(e)}"
    
    # Check Redis
    try:
        r = redis.from_url(settings.REDIS_URL)
        await r.ping()
        await r.close()
        checks["redis"] = "ok"
    except Exception as e:
        checks["redis"] = f"error: {str(e)}"
    
    all_healthy = all(v == "ok" for v in checks.values())
    
    return {
        "ready": all_healthy,
        "checks": checks
    }