"""Tests for tru8_mcp.server — MCP tool functions and helpers.

Covers JSON formatting, lazy client initialization, and the three
registered MCP tool functions (tru8_check, tru8_get_result, tru8_get_result_raw).
"""

import json
from datetime import datetime

import pytest
from unittest.mock import AsyncMock, patch

# tru8_mcp.server imports mcp.server.fastmcp (FastMCP), which exists only in
# mcp >= 1.2 AND < 2 — mcp 2.0.0 REMOVED it.
#
# The backend cannot install that range: mcp 1.2+ requires
# pydantic-settings>=2.6.1 and requirements.txt pins pydantic-settings==2.1.0,
# so pip resolves *outside* the working window in this environment and this
# module skips.
#
# ⚠️ This skip is why a real breakage stayed invisible. The original note here
# said pip resolves an OLDER mcp; as of 2026-08-04 it resolves mcp 2.0.0
# instead — a different failure with the same symptom, and the skip absorbed
# both silently while the PUBLISHED tru8-mcp package was dead on arrival for
# every new user (`mcp>=1.0.0` → 2.0.0 → ImportError). Fixed in tru8_mcp
# 1.0.3 by pinning `mcp>=1.2,<2` in the package's own pyproject.toml, which
# has no pydantic-settings constraint.
#
# These tests therefore still do NOT run here. The package is verified on its
# own build instead (clean-container install + MCP initialize handshake).
# Making them run requires upgrading pydantic-settings across the backend —
# its own change. See OPEN_WORK 2026-08-04.
pytest.importorskip("mcp.server.fastmcp")

import tru8_mcp.server as server_module
from tru8_mcp.server import (
    _format,
    _get_client,
    tru8_check,
    tru8_get_result,
    tru8_get_result_raw,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_client():
    """Reset the module-level _client singleton between tests."""
    server_module._client = None
    yield
    server_module._client = None


# ===========================================================================
# _format tests
# ===========================================================================


class TestFormat:
    """_format — JSON serialization for agent consumption."""

    def test_format_indented_json(self):
        data = {"key": "val", "num": 42}
        result = _format(data)
        parsed = json.loads(result)
        assert parsed == data
        # Verify indentation (indent=2 produces leading spaces on nested lines)
        assert "\n" in result
        assert '  "key"' in result

    def test_format_datetime_serialization(self):
        """default=str should serialize datetime without raising."""
        data = {"dt": datetime(2026, 1, 1, 12, 0, 0)}
        result = _format(data)
        parsed = json.loads(result)
        assert "2026" in parsed["dt"]


# ===========================================================================
# _get_client tests
# ===========================================================================


class TestGetClient:
    """_get_client — lazy singleton initialization."""

    def test_get_client_lazy_init(self, monkeypatch):
        monkeypatch.setenv("TRU8_API_KEY", "sk-lazy")
        first = _get_client()
        second = _get_client()
        assert first is second

    def test_get_client_reads_env(self, monkeypatch):
        monkeypatch.setenv("TRU8_API_KEY", "sk-env-check")
        monkeypatch.delenv("TRU8_API_URL", raising=False)
        client = _get_client()
        assert client.api_key == "sk-env-check"
        assert client.base_url == "https://api.trueight.com"


# ===========================================================================
# Tool function tests
# ===========================================================================


class TestToolFunctions:
    """MCP tool wrappers — delegation and argument forwarding."""

    @pytest.fixture(autouse=True)
    def _inject_mock_client(self):
        """Replace _client with a mock for all tool-function tests."""
        mock = AsyncMock()
        mock.submit_with_fallback = AsyncMock(
            return_value={"id": "chk-1", "status": "completed"}
        )
        mock.get_check = AsyncMock(return_value={"id": "chk-1", "claims": []})
        server_module._client = mock
        self.mock_client = mock
        yield

    async def test_tru8_check_calls_submit_with_fallback(self):
        result = await tru8_check("The earth is round")
        self.mock_client.submit_with_fallback.assert_awaited_once_with(
            "The earth is round",
            max_tier="quick",
            max_age_hours=None,
            compact=False,
        )
        parsed = json.loads(result)
        assert parsed["id"] == "chk-1"

    async def test_tru8_check_respects_max_tier(self):
        result = await tru8_check("Claim text", max_tier="full", compact=True)
        self.mock_client.submit_with_fallback.assert_awaited_once_with(
            "Claim text",
            max_tier="full",
            max_age_hours=None,
            compact=True,
        )
        parsed = json.loads(result)
        assert parsed["id"] == "chk-1"

    async def test_tru8_get_result_requests_computed(self):
        result = await tru8_get_result("chk-1")
        self.mock_client.get_check.assert_awaited_once_with("chk-1", computed=True)
        parsed = json.loads(result)
        assert parsed["id"] == "chk-1"

    async def test_tru8_get_result_raw_no_computed(self):
        result = await tru8_get_result_raw("chk-1")
        self.mock_client.get_check.assert_awaited_once_with("chk-1", computed=False)
        parsed = json.loads(result)
        assert parsed["id"] == "chk-1"
