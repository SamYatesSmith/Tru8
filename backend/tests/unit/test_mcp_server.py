"""Tests for tru8_mcp.server — MCP tool functions and helpers.

Covers JSON formatting, lazy client initialization, and the three
registered MCP tool functions (tru8_check, tru8_get_result, tru8_get_result_raw).
"""

import json
from datetime import datetime

import pytest
from unittest.mock import AsyncMock, patch

# DELIBERATELY A HARD IMPORT, NOT importorskip.
#
# This module used to open with `pytest.importorskip("mcp.server.fastmcp")`,
# added when requirements.txt pinned pydantic-settings==2.1.0 — a pin that
# forced pip outside the mcp range containing FastMCP, so these tests could
# not run and were skipped instead.
#
# That skip is how a real breakage stayed invisible for days. It was written
# for mcp being too OLD and silently absorbed mcp 2.0.0 being too NEW (2.0.0
# removed mcp.server.fastmcp), all while the PUBLISHED tru8-mcp package was
# dead on arrival for every new user. The suite stayed green throughout.
#
# requirements.txt now pins `pydantic-settings>=2.6.1,<3` and `mcp[cli]>=1.2,<2`,
# so the import is guaranteed in any environment built from it. If this line
# raises, the dependency floor has moved and that is EXACTLY what we want to
# hear about — loudly, not as a skipped module. Do not soften it back.
from mcp.server.fastmcp import FastMCP  # noqa: F401

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


# The `_reset_client` fixture that used to live here is gone with the
# singleton it existed to reset. It set `server_module._client = None`
# between tests — which, once the real attribute was removed, was the only
# thing still CREATING it, and it leaked across files: the guard in
# tests/unit/test_mcp_request_auth.py that asserts no module-level client
# survives caught exactly that. Do not reinstate it.


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
    """_get_client — a fresh client per request, never a shared one."""

    def test_get_client_is_never_cached(self, monkeypatch):
        """DELIBERATELY INVERTED on 2026-08-04.

        This asserted `first is second` — that the client was a lazily-built
        singleton. That was correct while the server only ever ran over stdio
        (one process, one user, one env var), and became a credential-crossing
        bug the moment the same process began serving many callers over HTTP:
        whichever key initialised the singleton would then have been used for
        everyone else's requests.

        A fresh client per call is now the contract. Fuller coverage of the
        per-request behaviour lives in tests/unit/test_mcp_request_auth.py.
        """
        monkeypatch.setenv("TRU8_API_KEY", "sk-lazy")
        first = _get_client()
        second = _get_client()
        assert first is not second

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
    def _inject_mock_client(self, monkeypatch):
        """Stub the client the tools resolve for this request.

        This used to assign `server_module._client = mock`, reaching into the
        module-level singleton. That singleton is gone — it was the
        credential-crossing bug — so the seam to stub is now the resolver
        itself.
        """
        mock = AsyncMock()
        mock.submit_with_fallback = AsyncMock(
            return_value={"id": "chk-1", "status": "completed"}
        )
        mock.get_check = AsyncMock(return_value={"id": "chk-1", "claims": []})
        monkeypatch.setattr(server_module, "_get_client", lambda: mock)
        self.mock_client = mock
        yield

    async def test_tru8_check_calls_submit_with_fallback(self):
        """An omitted max_tier means "full" — the CEILING, not the price.

        This asserted "quick" and had been failing since 749ff13 deliberately
        raised the default, so the suite carried a red test that described
        behaviour we had chosen against. The ceiling is safe to default high
        because the fallback still serves cached and consensus hits at their
        own lower price; only a never-researched claim reaches ~£0.15.
        """
        result = await tru8_check("The earth is round")
        self.mock_client.submit_with_fallback.assert_awaited_once_with(
            "The earth is round",
            max_tier="full",
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
