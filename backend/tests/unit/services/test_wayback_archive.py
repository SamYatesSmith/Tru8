"""Tests for wayback_archive service — URL extraction and single-URL archiving."""

import pytest
import httpx

from app.services.wayback_archive import _extract_archive_url, _archive_single_url


# ---------------------------------------------------------------------------
# TestExtractArchiveUrl
# ---------------------------------------------------------------------------


class TestExtractArchiveUrl:
    """_extract_archive_url pulls the archive snapshot URL from response headers."""

    def _make_response(
        self, headers: dict, url: str = "https://web.archive.org/save/example.com"
    ) -> httpx.Response:
        """Build a minimal httpx.Response with the given headers."""
        request = httpx.Request("GET", url)
        return httpx.Response(200, headers=headers, request=request)

    def test_extracts_from_content_location(self):
        """Content-Location with a relative path is expanded to a full URL."""
        resp = self._make_response(
            {"Content-Location": "/web/20260301120000/https://example.com"}
        )
        result = _extract_archive_url(resp)
        assert (
            result == "https://web.archive.org/web/20260301120000/https://example.com"
        )

    def test_extracts_from_location(self):
        """Location header with an absolute archive URL is returned as-is."""
        archive = "https://web.archive.org/web/20260301120000/https://example.com"
        resp = self._make_response({"Location": archive})
        result = _extract_archive_url(resp)
        assert result == archive

    def test_returns_none_when_missing(self):
        """No Content-Location / Location and non-archive final URL -> None."""
        resp = self._make_response(
            {},
            url="https://web.archive.org/save/example.com",  # not a /web/ URL
        )
        result = _extract_archive_url(resp)
        assert result is None


# ---------------------------------------------------------------------------
# TestArchiveSingleUrl
# ---------------------------------------------------------------------------


class TestArchiveSingleUrl:
    """_archive_single_url wraps a single Wayback Save request with retries."""

    @pytest.mark.asyncio
    async def test_successful_archive(self):
        """200 response with Content-Location returns the archive URL."""
        archive_path = "/web/20260301120000/https://example.com"

        transport = httpx.MockTransport(
            lambda request: httpx.Response(
                200,
                headers={"Content-Location": archive_path},
                request=request,
            )
        )

        async with httpx.AsyncClient(transport=transport) as client:
            result = await _archive_single_url(client, "https://example.com")

        assert result == f"https://web.archive.org{archive_path}"

    @pytest.mark.asyncio
    async def test_returns_none_on_timeout(self):
        """httpx.TimeoutException on both attempts returns None."""

        def _raise_timeout(request: httpx.Request) -> httpx.Response:
            raise httpx.TimeoutException("read timed out")

        transport = httpx.MockTransport(_raise_timeout)

        async with httpx.AsyncClient(transport=transport) as client:
            # Patch the retry delay to avoid slow tests
            import app.services.wayback_archive as mod

            original = mod.DEFAULT_RETRY_DELAY
            mod.DEFAULT_RETRY_DELAY = 0.0
            try:
                result = await _archive_single_url(client, "https://example.com")
            finally:
                mod.DEFAULT_RETRY_DELAY = original

        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_on_error(self):
        """Non-retriable 500 response returns None immediately."""

        transport = httpx.MockTransport(
            lambda request: httpx.Response(500, request=request)
        )

        async with httpx.AsyncClient(transport=transport) as client:
            result = await _archive_single_url(client, "https://example.com")

        assert result is None
