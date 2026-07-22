"""Regression tests for GET /checks/{id}/progress (SSE).

Born from the 2026-07-22 P0: the 2521b97 SSE-session change referenced
``async_session`` inside ``stream_check_progress`` without importing it —
every reconnect to the progress stream 500'd with NameError in prod, while
the initial-submission stream (a different code path) kept working. No test
executed the handler body, so it shipped.

These tests run the REAL handler through the ASGI stack: only auth and the
DB session factory are overridden. A missing import (or any handler-scope
NameError) fails loudly here.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.checks import router
from app.core.auth import get_current_user_or_api_key_sse

MOCK_USER = {"id": "user-001", "email": "test@tru8.app"}


def _make_app():
    app = FastAPI()
    app.include_router(router, prefix="/api/v1/checks")

    async def _auth_override():
        return MOCK_USER

    app.dependency_overrides[get_current_user_or_api_key_sse] = _auth_override
    return app


class _FakeSessionCtx:
    """Async context manager standing in for async_session()."""

    def __init__(self, check):
        self._check = check

    async def __aenter__(self):
        session = MagicMock()
        result = MagicMock()
        result.scalar_one_or_none.return_value = self._check
        session.execute = AsyncMock(return_value=result)
        return session

    async def __aexit__(self, *exc):
        return False


def _check_row(status="completed", error_message=None):
    check = MagicMock()
    check.status = status
    check.error_message = error_message
    return check


def _events(body: str):
    """Parse SSE body into a list of event dicts."""
    return [
        json.loads(line[len("data: ") :])
        for line in body.splitlines()
        if line.startswith("data: ")
    ]


def _get_progress(check):
    app = _make_app()
    with patch("app.core.database.async_session", new=lambda: _FakeSessionCtx(check)):
        client = TestClient(app)
        return client.get("/api/v1/checks/some-check-id/progress")


class TestProgressEndpointExecutesHandler:
    def test_completed_check_streams_connected_then_completed(self):
        """The full handler body runs — a handler-scope NameError fails here."""
        response = _get_progress(_check_row(status="completed"))
        assert response.status_code == 200

        events = _events(response.text)
        assert [e["type"] for e in events] == ["connected", "completed"]
        assert events[1]["progress"] == 100

    def test_failed_check_streams_error_event(self):
        response = _get_progress(_check_row(status="failed", error_message="boom"))
        assert response.status_code == 200

        events = _events(response.text)
        assert [e["type"] for e in events] == ["connected", "error"]
        assert events[1]["error"] == "boom"

    def test_unknown_check_returns_404(self):
        response = _get_progress(None)
        assert response.status_code == 404
