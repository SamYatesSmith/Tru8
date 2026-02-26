"""Tests for tru8_mcp.tools — SSE streaming in submit_check_sse.

Covers SSE event parsing: completed, error, timeout, progress-ignored,
and malformed data resilience.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from tru8_mcp.tools import Tru8APIClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_sse_client(lines, status_code=200, check_id_header="check-123"):
    """Build mock httpx.AsyncClient that yields SSE `lines` from stream().

    Returns the mock client class (to be patched as tru8_mcp.tools.httpx.AsyncClient).
    """
    mock_response = AsyncMock()
    mock_response.status_code = status_code
    mock_response.headers = {"x-check-id": check_id_header}

    async def mock_aiter_lines():
        for line in lines:
            yield line

    mock_response.aiter_lines = mock_aiter_lines

    # .aread() for error branch
    mock_response.aread = AsyncMock(return_value=b"error body")

    # stream() returns an async context manager
    mock_stream_ctx = AsyncMock()
    mock_stream_ctx.__aenter__ = AsyncMock(return_value=mock_response)
    mock_stream_ctx.__aexit__ = AsyncMock(return_value=False)

    mock_client = AsyncMock()
    mock_client.stream = MagicMock(return_value=mock_stream_ctx)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    mock_client_cls = MagicMock(return_value=mock_client)
    return mock_client_cls


# ===========================================================================
# SSE event parsing tests
# ===========================================================================


class TestSubmitCheckSSE:
    """Tru8APIClient.submit_check_sse — SSE event handling."""

    @pytest.mark.asyncio
    async def test_sse_completed_event(self):
        """Completed SSE event returns the check_id."""
        lines = [
            'data: {"type": "connected", "checkId": "check-123"}',
            'data: {"type": "progress", "stage": "extract"}',
            'data: {"type": "completed", "checkId": "check-123"}',
        ]
        mock_cls = _make_sse_client(lines)

        with patch("tru8_mcp.tools.httpx.AsyncClient", mock_cls):
            client = Tru8APIClient(api_url="http://localhost", api_key="sk-test")
            result = await client.submit_check_sse("The earth is flat")

        assert result == "check-123"

    @pytest.mark.asyncio
    async def test_sse_error_event(self):
        """Error SSE event raises RuntimeError with the error message."""
        lines = [
            'data: {"type": "connected", "checkId": "check-456"}',
            'data: {"type": "error", "error": "LLM quota exceeded"}',
        ]
        mock_cls = _make_sse_client(lines, check_id_header="check-456")

        with patch("tru8_mcp.tools.httpx.AsyncClient", mock_cls):
            client = Tru8APIClient(api_url="http://localhost", api_key="sk-test")
            with pytest.raises(RuntimeError, match="LLM quota exceeded"):
                await client.submit_check_sse("test claim")

    @pytest.mark.asyncio
    async def test_sse_timeout_event(self):
        """Timeout SSE event raises RuntimeError."""
        lines = [
            'data: {"type": "connected", "checkId": "check-789"}',
            'data: {"type": "timeout"}',
        ]
        mock_cls = _make_sse_client(lines, check_id_header="check-789")

        with patch("tru8_mcp.tools.httpx.AsyncClient", mock_cls):
            client = Tru8APIClient(api_url="http://localhost", api_key="sk-test")
            with pytest.raises(RuntimeError, match="timed out"):
                await client.submit_check_sse("test claim")

    @pytest.mark.asyncio
    async def test_sse_progress_events_ignored(self):
        """Progress events are skipped; only terminal event matters."""
        lines = [
            'data: {"type": "connected", "checkId": "check-prog"}',
            'data: {"type": "progress", "stage": "ingest"}',
            'data: {"type": "progress", "stage": "extract"}',
            'data: {"type": "progress", "stage": "retrieve"}',
            'data: {"type": "progress", "stage": "analyze"}',
            'data: {"type": "completed", "checkId": "check-prog"}',
        ]
        mock_cls = _make_sse_client(lines, check_id_header="check-prog")

        with patch("tru8_mcp.tools.httpx.AsyncClient", mock_cls):
            client = Tru8APIClient(api_url="http://localhost", api_key="sk-test")
            result = await client.submit_check_sse("test claim")

        assert result == "check-prog"

    @pytest.mark.asyncio
    async def test_sse_malformed_data_skipped(self):
        """Bad JSON in SSE data lines are silently skipped."""
        lines = [
            'data: {"type": "connected", "checkId": "check-bad"}',
            "data: NOT VALID JSON {{{",
            "data: ",
            'data: {"type": "completed", "checkId": "check-bad"}',
        ]
        mock_cls = _make_sse_client(lines, check_id_header="check-bad")

        with patch("tru8_mcp.tools.httpx.AsyncClient", mock_cls):
            client = Tru8APIClient(api_url="http://localhost", api_key="sk-test")
            result = await client.submit_check_sse("test claim")

        assert result == "check-bad"
