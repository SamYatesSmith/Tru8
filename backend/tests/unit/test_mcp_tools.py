"""Tests for tru8_mcp.tools — Tru8APIClient unit tests.

Covers constructor behaviour, HTTP method dispatch, payload construction,
and error handling for the MCP API client wrapper.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from tru8_mcp.tools import CLIENT_HEADER, Tru8APIClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_httpx_client(*, status_code=200, json_body=None, text=""):
    """Return a mock httpx.AsyncClient that supports async context manager."""
    mock_response = MagicMock()
    mock_response.status_code = status_code
    mock_response.json.return_value = json_body or {}
    mock_response.text = text

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_response)
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_client.patch = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    return mock_client, mock_response


# ===========================================================================
# Constructor tests
# ===========================================================================


class TestConstructor:
    """Tru8APIClient.__init__ — parameter resolution and validation."""

    def test_explicit_params(self):
        client = Tru8APIClient(api_url="http://localhost:8000", api_key="sk-test")
        assert client.base_url == "http://localhost:8000"
        assert client.api_key == "sk-test"

    def test_env_vars(self, monkeypatch):
        monkeypatch.setenv("TRU8_API_URL", "http://env-host:9000")
        monkeypatch.setenv("TRU8_API_KEY", "sk-from-env")
        client = Tru8APIClient()
        assert client.base_url == "http://env-host:9000"
        assert client.api_key == "sk-from-env"

    def test_default_url(self, monkeypatch):
        monkeypatch.setenv("TRU8_API_KEY", "sk-test")
        monkeypatch.delenv("TRU8_API_URL", raising=False)
        client = Tru8APIClient()
        assert client.base_url == "https://api.trueight.com"

    def test_no_key_raises(self, monkeypatch):
        monkeypatch.delenv("TRU8_API_KEY", raising=False)
        monkeypatch.delenv("TRU8_API_URL", raising=False)
        with pytest.raises(ValueError, match="TRU8_API_KEY"):
            Tru8APIClient()

    def test_trailing_slash_stripped(self):
        client = Tru8APIClient(api_url="http://localhost:8000/", api_key="sk-test")
        assert client.base_url == "http://localhost:8000"

    def test_headers(self):
        client = Tru8APIClient(api_url="http://localhost:8000", api_key="sk-test")
        headers = client._headers()
        assert headers == {
            "X-API-Key": "sk-test",
            "Accept": "application/json",
            "X-Tru8-Client": CLIENT_HEADER,
        }


# ===========================================================================
# submit_check_sync tests
# ===========================================================================


class TestSubmitCheckSync:
    """Tru8APIClient.submit_check_sync — payload construction and response handling."""

    async def test_text_input(self):
        mock_client, _ = _mock_httpx_client(
            status_code=200, json_body={"id": "check-1"}
        )
        with patch("tru8_mcp.tools.httpx.AsyncClient", return_value=mock_client):
            client = Tru8APIClient(api_key="sk-test")
            await client.submit_check_sync("The earth is round")

        call_kwargs = mock_client.post.call_args
        payload = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
        assert payload["input_type"] == "text"
        assert payload["content"] == "The earth is round"
        assert "url" not in payload

    async def test_url_input(self):
        mock_client, _ = _mock_httpx_client(
            status_code=200, json_body={"id": "check-2"}
        )
        with patch("tru8_mcp.tools.httpx.AsyncClient", return_value=mock_client):
            client = Tru8APIClient(api_key="sk-test")
            await client.submit_check_sync("https://example.com/article")

        call_kwargs = mock_client.post.call_args
        payload = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
        assert payload["input_type"] == "url"
        assert payload["url"] == "https://example.com/article"
        assert "content" not in payload

    async def test_api_error_raises(self):
        mock_client, _ = _mock_httpx_client(
            status_code=500, text="Internal Server Error"
        )
        with patch("tru8_mcp.tools.httpx.AsyncClient", return_value=mock_client):
            client = Tru8APIClient(api_key="sk-test")
            with pytest.raises(RuntimeError, match="API error 500"):
                await client.submit_check_sync("test claim")

    async def test_returns_json(self):
        expected = {"id": "check-42", "status": "completed", "claims": []}
        mock_client, _ = _mock_httpx_client(status_code=200, json_body=expected)
        with patch("tru8_mcp.tools.httpx.AsyncClient", return_value=mock_client):
            client = Tru8APIClient(api_key="sk-test")
            result = await client.submit_check_sync("test claim")
        assert result == expected


# ===========================================================================
# _select_claims tests
# ===========================================================================


class TestSelectClaims:
    """Tru8APIClient._select_claims — PATCH request construction."""

    async def test_sends_positions(self):
        mock_client, _ = _mock_httpx_client(status_code=200)
        with patch("tru8_mcp.tools.httpx.AsyncClient", return_value=mock_client):
            client = Tru8APIClient(api_key="sk-test")
            await client._select_claims("check-abc", [0, 2, 4])

        call_kwargs = mock_client.patch.call_args
        body = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
        assert body == {"selected_positions": [0, 2, 4]}

        # Verify URL contains the check ID
        url_arg = (
            call_kwargs.args[0]
            if call_kwargs.args
            else call_kwargs.kwargs.get("url", "")
        )
        assert "check-abc" in url_arg
        assert "select-claims" in url_arg


# ===========================================================================
# get_check tests
# ===========================================================================


class TestGetCheck:
    """Tru8APIClient.get_check — query parameter handling and errors."""

    async def test_without_computed(self):
        mock_client, _ = _mock_httpx_client(
            status_code=200, json_body={"id": "check-99"}
        )
        with patch("tru8_mcp.tools.httpx.AsyncClient", return_value=mock_client):
            client = Tru8APIClient(api_key="sk-test")
            await client.get_check("check-99", computed=False)

        call_kwargs = mock_client.get.call_args
        params = call_kwargs.kwargs.get("params") or call_kwargs[1].get("params", {})
        assert params == {}

    async def test_with_computed(self):
        mock_client, _ = _mock_httpx_client(
            status_code=200, json_body={"id": "check-99", "_computed": {}}
        )
        with patch("tru8_mcp.tools.httpx.AsyncClient", return_value=mock_client):
            client = Tru8APIClient(api_key="sk-test")
            await client.get_check("check-99", computed=True)

        call_kwargs = mock_client.get.call_args
        params = call_kwargs.kwargs.get("params") or call_kwargs[1].get("params", {})
        assert params == {"computed": "true"}

    async def test_error_raises(self):
        mock_client, _ = _mock_httpx_client(status_code=404, text="Not found")
        with patch("tru8_mcp.tools.httpx.AsyncClient", return_value=mock_client):
            client = Tru8APIClient(api_key="sk-test")
            with pytest.raises(RuntimeError, match="API error 404"):
                await client.get_check("nonexistent-id")
