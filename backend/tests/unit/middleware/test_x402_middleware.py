"""Tests for X402AuditMiddleware — scope filtering and path interception.

Validates that the middleware:
  - Passes through non-HTTP scopes (websocket)
  - Passes through non-x402 paths
  - Passes through x402 paths that are NOT tier endpoints (e.g. /challenge)
  - Intercepts tier endpoint paths (lookup, quick, full)
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.middleware.x402_audit import X402AuditMiddleware


@pytest.fixture
def inner_app():
    """Mock ASGI app that records whether it was called."""
    app = AsyncMock()
    return app


@pytest.fixture
def middleware(inner_app):
    return X402AuditMiddleware(inner_app)


# ---------------------------------------------------------------------------
# Scope filtering
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_non_http_scope_passes_through(middleware, inner_app):
    """type='websocket' should pass straight through without interception."""
    scope = {"type": "websocket", "path": "/api/v1/agent/x402/quick"}
    receive = AsyncMock()
    send = AsyncMock()

    await middleware(scope, receive, send)

    # Inner app called with the original send (no wrapper)
    inner_app.assert_awaited_once_with(scope, receive, send)


@pytest.mark.asyncio
async def test_non_x402_path_passes_through(middleware, inner_app):
    """Paths outside /api/v1/agent/x402 should not be intercepted."""
    scope = {"type": "http", "path": "/api/v1/checks"}
    receive = AsyncMock()
    send = AsyncMock()

    await middleware(scope, receive, send)

    inner_app.assert_awaited_once_with(scope, receive, send)


@pytest.mark.asyncio
async def test_non_tier_x402_path_passes_through(middleware, inner_app):
    """x402 sub-paths that are NOT tier endpoints (challenge, result) should pass through."""
    scope = {"type": "http", "path": "/api/v1/agent/x402/challenge"}
    receive = AsyncMock()
    send = AsyncMock()

    await middleware(scope, receive, send)

    inner_app.assert_awaited_once_with(scope, receive, send)


@pytest.mark.asyncio
async def test_tier_path_intercepted(middleware, inner_app):
    """Tier endpoints (/lookup, /quick, /full) should be intercepted with a send_wrapper."""
    scope = {"type": "http", "path": "/api/v1/agent/x402/quick", "state": {}}
    receive = AsyncMock()
    send = AsyncMock()

    await middleware(scope, receive, send)

    # Inner app should be called, but with a DIFFERENT send callable (the wrapper)
    inner_app.assert_awaited_once()
    call_args = inner_app.await_args
    assert call_args[0][0] is scope
    assert call_args[0][1] is receive
    # The send argument should NOT be the original send — it's the wrapper
    assert call_args[0][2] is not send
