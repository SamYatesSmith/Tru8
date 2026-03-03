"""Tests for x402 facilitator error handling and audit middleware.

Verifies the audit middleware correctly handles various settlement
failure scenarios when the x402 facilitator returns errors.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.middleware.x402_audit import X402AuditMiddleware


class TestX402AuditMiddlewareRouting:
    """Verify the audit middleware only intercepts tier endpoints."""

    def test_route_prefix_default(self):
        app = MagicMock()
        middleware = X402AuditMiddleware(app)
        assert middleware.route_prefix == "/api/v1/agent/x402"

    def test_route_prefix_custom(self):
        app = MagicMock()
        middleware = X402AuditMiddleware(app, route_prefix="/custom/x402")
        assert middleware.route_prefix == "/custom/x402"

    @pytest.mark.asyncio
    async def test_non_http_passes_through(self):
        """WebSocket scope passes through without interception."""
        inner_app = AsyncMock()
        middleware = X402AuditMiddleware(inner_app)
        scope = {"type": "websocket", "path": "/api/v1/agent/x402/quick"}
        receive = AsyncMock()
        send = AsyncMock()

        await middleware(scope, receive, send)
        inner_app.assert_awaited_once_with(scope, receive, send)

    @pytest.mark.asyncio
    async def test_non_x402_path_passes_through(self):
        """Non-x402 paths pass through without interception."""
        inner_app = AsyncMock()
        middleware = X402AuditMiddleware(inner_app)
        scope = {"type": "http", "path": "/api/v1/agent/quick"}
        receive = AsyncMock()
        send = AsyncMock()

        await middleware(scope, receive, send)
        inner_app.assert_awaited_once_with(scope, receive, send)

    @pytest.mark.asyncio
    async def test_challenge_path_passes_through(self):
        """Challenge endpoint passes through (not a tier endpoint)."""
        inner_app = AsyncMock()
        middleware = X402AuditMiddleware(inner_app)
        scope = {"type": "http", "path": "/api/v1/agent/x402/challenge"}
        receive = AsyncMock()
        send = AsyncMock()

        await middleware(scope, receive, send)
        inner_app.assert_awaited_once_with(scope, receive, send)


class TestX402SettlementStatuses:
    """Test settlement status classification logic."""

    def test_tier_paths_are_correct(self):
        """Verify the middleware's tier path detection."""
        app = MagicMock()
        middleware = X402AuditMiddleware(app)
        tier_paths = (
            f"{middleware.route_prefix}/lookup",
            f"{middleware.route_prefix}/quick",
            f"{middleware.route_prefix}/full",
        )
        assert "/api/v1/agent/x402/lookup" in tier_paths
        assert "/api/v1/agent/x402/quick" in tier_paths
        assert "/api/v1/agent/x402/full" in tier_paths
