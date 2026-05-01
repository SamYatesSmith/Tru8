"""Tests for Sentry capture in the FastAPI HTTP exception handler.

Background: app.core.exceptions.http_exception_handler used to log
HTTPException at WARNING but never call sentry_sdk.capture_exception,
so any code path doing `raise HTTPException(status_code=500, ...)`
was invisible in production. The fix captures 5xx (server errors)
while leaving 4xx (client errors — auth, validation, not-found)
untouched, since those are expected traffic and would be noise.
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from fastapi.exceptions import HTTPException

from app.core.exceptions import http_exception_handler


def _build_request(path="/api/v1/test", method="GET", request_id="req-123"):
    """Construct a minimal Request stub for the handler."""
    request = MagicMock()
    request.url = MagicMock()
    request.url.path = path
    request.method = method
    state = MagicMock()
    state.request_id = request_id
    request.state = state
    return request


@pytest.fixture
def sentry_mock():
    """Patch sentry_sdk so we can assert capture calls without sending."""
    with patch("app.core.exceptions.sentry_sdk") as mock_sdk:
        # push_scope returns a context manager; tags set inside it land on
        # a Scope mock we can introspect.
        scope = MagicMock()
        ctx = MagicMock()
        ctx.__enter__ = MagicMock(return_value=scope)
        ctx.__exit__ = MagicMock(return_value=False)
        mock_sdk.push_scope.return_value = ctx
        yield mock_sdk, scope


@pytest.fixture
def sentry_enabled():
    """Patch settings.SENTRY_DSN to a truthy value so the capture branch fires."""
    with patch("app.core.exceptions.settings") as mock_settings:
        mock_settings.SENTRY_DSN = "https://fake@sentry.io/1"
        mock_settings.DEBUG = False
        yield mock_settings


@pytest.fixture
def sentry_disabled():
    """Patch settings.SENTRY_DSN to empty so the capture branch is gated off."""
    with patch("app.core.exceptions.settings") as mock_settings:
        mock_settings.SENTRY_DSN = ""
        mock_settings.DEBUG = False
        yield mock_settings


class TestHTTPExceptionSentryCapture:
    """5xx HTTPExceptions are captured to Sentry; 4xx are not."""

    @pytest.mark.asyncio
    async def test_500_captures_to_sentry(self, sentry_mock, sentry_enabled):
        mock_sdk, scope = sentry_mock
        request = _build_request(path="/api/v1/checks", method="POST")
        exc = HTTPException(status_code=500, detail="Database is down")

        await http_exception_handler(request, exc)

        mock_sdk.capture_exception.assert_called_once_with(exc)

        # Tags propagated for triage
        scope.set_tag.assert_any_call("path", "/api/v1/checks")
        scope.set_tag.assert_any_call("method", "POST")
        scope.set_tag.assert_any_call("status_code", 500)
        scope.set_tag.assert_any_call("error_code", "INTERNAL_ERROR")
        scope.set_tag.assert_any_call("request_id", "req-123")

    @pytest.mark.asyncio
    async def test_502_captures_to_sentry(self, sentry_mock, sentry_enabled):
        mock_sdk, _scope = sentry_mock
        exc = HTTPException(status_code=502, detail="Upstream Gemini API down")

        await http_exception_handler(_build_request(), exc)

        mock_sdk.capture_exception.assert_called_once_with(exc)

    @pytest.mark.asyncio
    async def test_503_captures_to_sentry(self, sentry_mock, sentry_enabled):
        mock_sdk, _scope = sentry_mock
        exc = HTTPException(status_code=503, detail="Service Unavailable")

        await http_exception_handler(_build_request(), exc)

        mock_sdk.capture_exception.assert_called_once_with(exc)

    @pytest.mark.asyncio
    async def test_400_does_not_capture(self, sentry_mock, sentry_enabled):
        mock_sdk, _scope = sentry_mock
        exc = HTTPException(status_code=400, detail="Bad request payload")

        await http_exception_handler(_build_request(), exc)

        mock_sdk.capture_exception.assert_not_called()

    @pytest.mark.asyncio
    async def test_401_does_not_capture(self, sentry_mock, sentry_enabled):
        """401 is normal — expired tokens, missing auth — do not page on it."""
        mock_sdk, _scope = sentry_mock
        exc = HTTPException(status_code=401, detail="Token has expired")

        await http_exception_handler(_build_request(), exc)

        mock_sdk.capture_exception.assert_not_called()

    @pytest.mark.asyncio
    async def test_404_does_not_capture(self, sentry_mock, sentry_enabled):
        mock_sdk, _scope = sentry_mock
        exc = HTTPException(status_code=404, detail="Resource not found")

        await http_exception_handler(_build_request(), exc)

        mock_sdk.capture_exception.assert_not_called()

    @pytest.mark.asyncio
    async def test_429_does_not_capture(self, sentry_mock, sentry_enabled):
        """Rate limiting is normal traffic — we have metrics for that."""
        mock_sdk, _scope = sentry_mock
        exc = HTTPException(status_code=429, detail="Rate limit exceeded")

        await http_exception_handler(_build_request(), exc)

        mock_sdk.capture_exception.assert_not_called()


class TestHTTPExceptionSentryGating:
    """Capture is skipped when SENTRY_DSN is empty (e.g. local dev)."""

    @pytest.mark.asyncio
    async def test_500_does_not_capture_when_dsn_unset(
        self, sentry_mock, sentry_disabled
    ):
        mock_sdk, _scope = sentry_mock
        exc = HTTPException(status_code=500, detail="boom")

        await http_exception_handler(_build_request(), exc)

        mock_sdk.capture_exception.assert_not_called()
        mock_sdk.push_scope.assert_not_called()


class TestHTTPExceptionResponseShape:
    """Capture must not change the response — it's purely additive."""

    @pytest.mark.asyncio
    async def test_response_status_unchanged_on_capture(
        self, sentry_mock, sentry_enabled
    ):
        exc = HTTPException(status_code=500, detail="Database is down")
        response = await http_exception_handler(_build_request(), exc)

        assert response.status_code == 500

    @pytest.mark.asyncio
    async def test_response_status_unchanged_on_skip(self, sentry_mock, sentry_enabled):
        exc = HTTPException(status_code=404, detail="Not found")
        response = await http_exception_handler(_build_request(), exc)

        assert response.status_code == 404
