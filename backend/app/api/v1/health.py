from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.core.database import get_session
from app.core.build_info import get_build_info
from app.core.config import settings
from app.services.cache import get_sync_cache_service
from app.services.circuit_breaker import get_circuit_breaker_registry
from app.services.email_notifications import email_notification_service
import redis.asyncio as redis

router = APIRouter()


@router.get("/")
async def health_check():
    """Liveness, plus WHICH COMMIT is answering.

    `version` is a static string and always has been; it says nothing about the
    deployed code. The commit fields are the ones that let you tell "the fix is
    not deployed" from "the fix is deployed and did not fire" — a distinction
    that cost 30p and an hour on 2026-08-05 for want of exactly this.
    `commit_source` is reported so a caller can see whether the value came from
    the platform or from a local working tree; `unknown` means we could not
    establish it, and is never filled with a placeholder.
    """
    return {
        "status": "healthy",
        "environment": settings.ENVIRONMENT,
        "version": "0.1.0",
        **get_build_info(),
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

    return {"ready": all_healthy, "checks": checks}


@router.get("/cache-metrics")
async def get_cache_metrics(
    api_name: str = Query(None, description="Optional: Get metrics for specific API")
):
    """
    Get API cache hit/miss statistics.

    Week 4 - Government API Integration: Monitor cache performance to ensure 60%+ hit rate target.

    Args:
        api_name: Optional - filter metrics for specific API adapter

    Returns:
        Cache metrics including hit rate percentage
    """
    try:
        cache_service = get_sync_cache_service()
        metrics = cache_service.get_cache_metrics(api_name)

        # Add status indicator based on hit rate
        if "error" not in metrics:
            if api_name:
                hit_rate = metrics.get("hit_rate_percentage", 0)
                metrics["status"] = _evaluate_cache_performance(hit_rate)
            else:
                overall_hit_rate = metrics.get("overall", {}).get(
                    "hit_rate_percentage", 0
                )
                metrics["overall"]["status"] = _evaluate_cache_performance(
                    overall_hit_rate
                )

        return metrics
    except Exception as e:
        return {"error": f"Failed to retrieve cache metrics: {str(e)}"}


def _evaluate_cache_performance(hit_rate: float) -> str:
    """
    Evaluate cache performance against targets.

    Args:
        hit_rate: Cache hit rate percentage

    Returns:
        Status string: "excellent", "good", "acceptable", or "needs_optimization"
    """
    if hit_rate >= 75:
        return "excellent"  # Well above 60% target
    elif hit_rate >= 60:
        return "good"  # Meeting target
    elif hit_rate >= 40:
        return "acceptable"  # Below target but functional
    else:
        return "needs_optimization"  # Significantly below target


@router.get("/circuit-breakers")
async def get_circuit_breakers(
    api_name: str = Query(None, description="Optional: Get state for specific API")
):
    """
    Get circuit breaker states for API adapters.

    Week 4 - Government API Integration: Monitor API health and circuit breaker status.

    Args:
        api_name: Optional - filter for specific API adapter

    Returns:
        Circuit breaker states
    """
    try:
        registry = get_circuit_breaker_registry()

        if api_name:
            breaker = registry.get_breaker(api_name)
            return breaker.get_state()
        else:
            return registry.get_all_states()

    except Exception as e:
        return {"error": f"Failed to retrieve circuit breaker states: {str(e)}"}


@router.get("/email-config")
async def check_email_config():
    """
    Diagnostic endpoint to check email notification configuration.
    """
    service = email_notification_service

    # Check if resend module is available
    resend_available = False
    try:
        import resend

        resend_available = True
    except ImportError:
        pass

    return {
        "enabled": service.enabled,
        "api_key_configured": bool(service.api_key),
        "api_key_prefix": service.api_key[:8] + "..." if service.api_key else None,
        "from_address": service.from_address,
        "from_name": service.from_name,
        "resend_package_installed": resend_available,
        "status": (
            "ready"
            if (service.enabled and service.api_key and resend_available)
            else "not_configured"
        ),
    }
