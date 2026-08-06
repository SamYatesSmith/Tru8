"""Tests for health API endpoints.

Covers all five endpoints on the health router:
- GET /           — basic health status
- GET /ready      — readiness (DB + Redis)
- GET /cache-metrics  — API cache hit/miss stats
- GET /circuit-breakers — circuit breaker states
- GET /email-config    — email configuration diagnostic
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.v1.health import router, _evaluate_cache_performance
from app.core.database import get_session


# ---------------------------------------------------------------------------
# Test app setup
# ---------------------------------------------------------------------------


def _create_test_app():
    """Build a minimal FastAPI app with the health router mounted."""
    app = FastAPI()
    app.include_router(router, prefix="/health")
    return app


def _mock_session_override(mock_session):
    """Dependency override that returns the given mock session."""

    async def _override():
        yield mock_session

    return _override


# ---------------------------------------------------------------------------
# TestHealthCheck — GET /
# ---------------------------------------------------------------------------


class TestHealthCheck:
    """Tests for the basic health endpoint."""

    @pytest.mark.asyncio
    async def test_returns_healthy(self):
        """GET / returns status 'healthy'."""
        app = _create_test_app()
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/health/")
            assert resp.status_code == 200
            body = resp.json()
            assert body["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_includes_environment_and_version(self):
        """GET / response includes environment and version fields."""
        app = _create_test_app()
        with patch("app.api.v1.health.settings") as mock_settings:
            mock_settings.ENVIRONMENT = "testing"
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.get("/health/")
                body = resp.json()
                assert body["environment"] == "testing"
                assert body["version"] == "0.1.0"

    @pytest.mark.asyncio
    async def test_names_the_commit_that_is_answering(self):
        """The seam, not the helper — 2026-08-05's unanswerable question.

        `version` is static and says nothing about the deployed code. Without
        these fields on the response itself, a live check that behaves
        unexpectedly cannot be attributed to "not deployed" vs "deployed but
        wrong" — which cost 30p and an hour.
        """
        app = _create_test_app()

        with patch(
            "app.api.v1.health.get_build_info",
            return_value={
                "commit": "27fc5dc",
                "commit_full": "27fc5dc4737fefeeee5e018cd92617f6bf2020ed",
                "commit_source": "RAILWAY_GIT_COMMIT_SHA",
                "branch": "main",
            },
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                body = (await client.get("/health/")).json()

        assert body["commit"] == "27fc5dc"
        assert body["commit_source"] == "RAILWAY_GIT_COMMIT_SHA"
        assert body["branch"] == "main"
        # The monitor asserts on this string; adding fields must not disturb it.
        assert body["status"] == "healthy"


# ---------------------------------------------------------------------------
# TestReadinessCheck — GET /ready
# ---------------------------------------------------------------------------


class TestReadinessCheck:
    """Tests for the readiness endpoint that probes DB and Redis."""

    @pytest.mark.asyncio
    async def test_ready_when_db_and_redis_ok(self):
        """GET /ready returns ready=True when both DB and Redis respond."""
        app = _create_test_app()

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock()

        app.dependency_overrides[get_session] = _mock_session_override(mock_session)

        mock_redis_instance = AsyncMock()
        mock_redis_instance.ping = AsyncMock(return_value=True)
        mock_redis_instance.close = AsyncMock()

        with patch("app.api.v1.health.redis") as mock_redis_module:
            mock_redis_module.from_url.return_value = mock_redis_instance

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.get("/health/ready")
                assert resp.status_code == 200
                body = resp.json()
                assert body["ready"] is True
                assert body["checks"]["database"] == "ok"
                assert body["checks"]["redis"] == "ok"

    @pytest.mark.asyncio
    async def test_not_ready_when_db_fails(self):
        """GET /ready returns ready=False when DB probe raises."""
        app = _create_test_app()

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(side_effect=Exception("connection refused"))

        app.dependency_overrides[get_session] = _mock_session_override(mock_session)

        mock_redis_instance = AsyncMock()
        mock_redis_instance.ping = AsyncMock(return_value=True)
        mock_redis_instance.close = AsyncMock()

        with patch("app.api.v1.health.redis") as mock_redis_module:
            mock_redis_module.from_url.return_value = mock_redis_instance

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.get("/health/ready")
                assert resp.status_code == 200
                body = resp.json()
                assert body["ready"] is False
                assert "error" in body["checks"]["database"]
                assert "connection refused" in body["checks"]["database"]
                assert body["checks"]["redis"] == "ok"

    @pytest.mark.asyncio
    async def test_not_ready_when_redis_fails(self):
        """GET /ready returns ready=False when Redis probe raises."""
        app = _create_test_app()

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock()

        app.dependency_overrides[get_session] = _mock_session_override(mock_session)

        with patch("app.api.v1.health.redis") as mock_redis_module:
            mock_redis_module.from_url.side_effect = Exception("redis unreachable")

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.get("/health/ready")
                assert resp.status_code == 200
                body = resp.json()
                assert body["ready"] is False
                assert body["checks"]["database"] == "ok"
                assert "error" in body["checks"]["redis"]
                assert "redis unreachable" in body["checks"]["redis"]


# ---------------------------------------------------------------------------
# TestCacheMetrics — GET /cache-metrics
# ---------------------------------------------------------------------------


class TestCacheMetrics:
    """Tests for the cache-metrics endpoint."""

    @pytest.mark.asyncio
    async def test_returns_metrics_for_all_apis(self):
        """GET /cache-metrics with no filter returns overall + per-API data."""
        app = _create_test_app()

        mock_cache = MagicMock()
        mock_cache.get_cache_metrics.return_value = {
            "overall": {
                "total_hits": 120,
                "total_misses": 30,
                "total_queries": 150,
                "hit_rate_percentage": 80.0,
            },
            "by_api": {
                "serper": {
                    "hits": 80,
                    "misses": 20,
                    "total_queries": 100,
                    "hit_rate_percentage": 80.0,
                },
                "brave": {
                    "hits": 40,
                    "misses": 10,
                    "total_queries": 50,
                    "hit_rate_percentage": 80.0,
                },
            },
        }

        with patch("app.api.v1.health.get_sync_cache_service", return_value=mock_cache):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.get("/health/cache-metrics")
                assert resp.status_code == 200
                body = resp.json()
                assert "overall" in body
                assert "by_api" in body
                assert body["overall"]["total_hits"] == 120
                assert body["overall"]["status"] == "excellent"

    @pytest.mark.asyncio
    async def test_filters_by_api_name(self):
        """GET /cache-metrics?api_name=serper returns single-API metrics."""
        app = _create_test_app()

        mock_cache = MagicMock()
        mock_cache.get_cache_metrics.return_value = {
            "api_name": "serper",
            "hits": 50,
            "misses": 50,
            "total_queries": 100,
            "hit_rate_percentage": 50.0,
        }

        with patch("app.api.v1.health.get_sync_cache_service", return_value=mock_cache):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.get(
                    "/health/cache-metrics", params={"api_name": "serper"}
                )
                assert resp.status_code == 200
                body = resp.json()
                assert body["api_name"] == "serper"
                assert body["hit_rate_percentage"] == 50.0
                assert body["status"] == "acceptable"
                mock_cache.get_cache_metrics.assert_called_once_with("serper")

    @pytest.mark.asyncio
    async def test_evaluates_performance(self):
        """_evaluate_cache_performance returns correct labels for thresholds."""
        assert _evaluate_cache_performance(90) == "excellent"
        assert _evaluate_cache_performance(75) == "excellent"
        assert _evaluate_cache_performance(65) == "good"
        assert _evaluate_cache_performance(60) == "good"
        assert _evaluate_cache_performance(50) == "acceptable"
        assert _evaluate_cache_performance(40) == "acceptable"
        assert _evaluate_cache_performance(30) == "needs_optimization"
        assert _evaluate_cache_performance(0) == "needs_optimization"

    @pytest.mark.asyncio
    async def test_cache_metrics_error_handling(self):
        """GET /cache-metrics returns error dict when cache service raises."""
        app = _create_test_app()

        with patch(
            "app.api.v1.health.get_sync_cache_service",
            side_effect=Exception("Redis down"),
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.get("/health/cache-metrics")
                assert resp.status_code == 200
                body = resp.json()
                assert "error" in body
                assert "Redis down" in body["error"]


# ---------------------------------------------------------------------------
# TestCircuitBreakers — GET /circuit-breakers
# ---------------------------------------------------------------------------


class TestCircuitBreakers:
    """Tests for the circuit-breakers endpoint."""

    @pytest.mark.asyncio
    async def test_returns_breaker_states(self):
        """GET /circuit-breakers returns state dict for all registered breakers."""
        app = _create_test_app()

        mock_registry = MagicMock()
        mock_registry.get_all_states.return_value = {
            "ONS": {
                "api_name": "ONS",
                "state": "closed",
                "failure_count": 0,
                "success_count": 0,
                "failure_threshold": 5,
                "success_threshold": 2,
            },
            "GovUK": {
                "api_name": "GovUK",
                "state": "open",
                "failure_count": 5,
                "success_count": 0,
                "failure_threshold": 5,
                "success_threshold": 2,
                "time_open_seconds": 12.3,
                "time_until_retry_seconds": 47.7,
            },
        }

        with patch(
            "app.api.v1.health.get_circuit_breaker_registry",
            return_value=mock_registry,
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.get("/health/circuit-breakers")
                assert resp.status_code == 200
                body = resp.json()
                assert "ONS" in body
                assert "GovUK" in body
                assert body["ONS"]["state"] == "closed"
                assert body["GovUK"]["state"] == "open"
                assert body["GovUK"]["failure_count"] == 5

    @pytest.mark.asyncio
    async def test_filters_by_api_name(self):
        """GET /circuit-breakers?api_name=ONS returns single breaker state."""
        app = _create_test_app()

        mock_breaker = MagicMock()
        mock_breaker.get_state.return_value = {
            "api_name": "ONS",
            "state": "closed",
            "failure_count": 1,
            "success_count": 0,
            "failure_threshold": 5,
            "success_threshold": 2,
        }

        mock_registry = MagicMock()
        mock_registry.get_breaker.return_value = mock_breaker

        with patch(
            "app.api.v1.health.get_circuit_breaker_registry",
            return_value=mock_registry,
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.get(
                    "/health/circuit-breakers", params={"api_name": "ONS"}
                )
                assert resp.status_code == 200
                body = resp.json()
                assert body["api_name"] == "ONS"
                assert body["state"] == "closed"
                mock_registry.get_breaker.assert_called_once_with("ONS")

    @pytest.mark.asyncio
    async def test_circuit_breakers_error_handling(self):
        """GET /circuit-breakers returns error dict when registry raises."""
        app = _create_test_app()

        with patch(
            "app.api.v1.health.get_circuit_breaker_registry",
            side_effect=Exception("registry failure"),
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.get("/health/circuit-breakers")
                assert resp.status_code == 200
                body = resp.json()
                assert "error" in body
                assert "registry failure" in body["error"]


# ---------------------------------------------------------------------------
# TestEmailConfig — GET /email-config
# ---------------------------------------------------------------------------


class TestEmailConfig:
    """Tests for the email-config diagnostic endpoint."""

    @pytest.mark.asyncio
    async def test_returns_config_status(self):
        """GET /email-config returns email configuration details."""
        app = _create_test_app()

        mock_service = MagicMock()
        mock_service.enabled = True
        mock_service.api_key = "re_1234567890abcdef"
        mock_service.from_address = "hello@trueight.com"
        mock_service.from_name = "Tru8"

        with patch("app.api.v1.health.email_notification_service", mock_service):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.get("/health/email-config")
                assert resp.status_code == 200
                body = resp.json()
                assert body["enabled"] is True
                assert body["api_key_configured"] is True
                assert body["api_key_prefix"] == "re_12345..."
                assert body["from_address"] == "hello@trueight.com"
                assert body["from_name"] == "Tru8"
                assert body["resend_package_installed"] in (True, False)

    @pytest.mark.asyncio
    async def test_returns_not_configured_when_disabled(self):
        """GET /email-config returns status 'not_configured' when disabled."""
        app = _create_test_app()

        mock_service = MagicMock()
        mock_service.enabled = False
        mock_service.api_key = ""
        mock_service.from_address = "hello@trueight.com"
        mock_service.from_name = "Tru8"

        with patch("app.api.v1.health.email_notification_service", mock_service):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.get("/health/email-config")
                assert resp.status_code == 200
                body = resp.json()
                assert body["enabled"] is False
                assert body["api_key_configured"] is False
                assert body["api_key_prefix"] is None
                assert body["status"] == "not_configured"

    @pytest.mark.asyncio
    async def test_returns_ready_when_fully_configured(self):
        """GET /email-config returns status 'ready' when enabled + key + resend."""
        app = _create_test_app()

        mock_service = MagicMock()
        mock_service.enabled = True
        mock_service.api_key = "re_abcdefgh12345678"
        mock_service.from_address = "hello@trueight.com"
        mock_service.from_name = "Tru8"

        with patch(
            "app.api.v1.health.email_notification_service", mock_service
        ), patch.dict("sys.modules", {"resend": MagicMock()}):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.get("/health/email-config")
                assert resp.status_code == 200
                body = resp.json()
                assert body["status"] == "ready"
                assert body["resend_package_installed"] is True
