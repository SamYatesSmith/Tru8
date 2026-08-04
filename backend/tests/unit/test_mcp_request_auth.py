"""Per-request credential resolution for the MCP server.

WHY THIS FILE EXISTS
--------------------
`tru8_mcp.server` used to hold the API client in a module-level global:

    _client: Tru8APIClient | None = None

That is correct under stdio, where one process serves exactly one user from
one environment variable. It becomes a credential-crossing bug the moment the
same process serves more than one caller over HTTP — whichever key happened to
initialise the singleton would then have been used for *everybody else's*
requests, silently, with no error and no log line.

These tests are the acceptance criterion for the hosted transport. The
isolation test below is the one that matters; the rest describe how a key is
found. If any of them are ever weakened, the hosted endpoint must not ship.
"""

from types import SimpleNamespace
from unittest.mock import patch

import pytest

from mcp.server.fastmcp import (
    FastMCP,
)  # noqa: F401  (hard import — see test_mcp_server.py)

import tru8_mcp.server as server


def _http_request(headers=None, query=None):
    """A stand-in for the Starlette request FastMCP exposes over HTTP."""
    return SimpleNamespace(
        headers={k.lower(): v for k, v in (headers or {}).items()},
        query_params=query or {},
    )


def _ctx(request):
    """Shape of mcp.get_context() — ctx.request_context.request."""
    return SimpleNamespace(request_context=SimpleNamespace(request=request))


# ---------------------------------------------------------------------------
# Finding the caller's key
# ---------------------------------------------------------------------------


class TestRequestApiKey:
    def test_reads_x_api_key_header(self):
        """The same header the Tru8 API itself authenticates with."""
        with patch.object(
            server.mcp,
            "get_context",
            return_value=_ctx(_http_request(headers={"X-API-Key": "tru8_sk_alice"})),
        ):
            assert server._request_api_key() == "tru8_sk_alice"

    def test_reads_authorization_bearer(self):
        with patch.object(
            server.mcp,
            "get_context",
            return_value=_ctx(
                _http_request(headers={"Authorization": "Bearer tru8_sk_bob"})
            ),
        ):
            assert server._request_api_key() == "tru8_sk_bob"

    @pytest.mark.parametrize("param", ["apiKey", "api_key", "TRU8_API_KEY"])
    def test_reads_query_param(self, param):
        """Gateways such as Smithery pass session config in the query string."""
        with patch.object(
            server.mcp,
            "get_context",
            return_value=_ctx(_http_request(query={param: "tru8_sk_carol"})),
        ):
            assert server._request_api_key() == "tru8_sk_carol"

    def test_header_wins_over_query_param(self):
        with patch.object(
            server.mcp,
            "get_context",
            return_value=_ctx(
                _http_request(
                    headers={"X-API-Key": "tru8_sk_header"},
                    query={"apiKey": "tru8_sk_query"},
                )
            ),
        ):
            assert server._request_api_key() == "tru8_sk_header"

    def test_whitespace_is_stripped(self):
        with patch.object(
            server.mcp,
            "get_context",
            return_value=_ctx(
                _http_request(headers={"X-API-Key": "  tru8_sk_padded  "})
            ),
        ):
            assert server._request_api_key() == "tru8_sk_padded"

    def test_no_http_request_means_stdio(self):
        """Under stdio there is no request; the env var is the right source."""
        with patch.object(server.mcp, "get_context", return_value=_ctx(None)):
            assert server._request_api_key() is None

    def test_no_context_at_all_is_survivable(self):
        """Outside a request FastMCP raises — that must not propagate."""
        with patch.object(
            server.mcp, "get_context", side_effect=RuntimeError("no ctx")
        ):
            assert server._request_api_key() is None

    def test_absent_credentials_return_none_not_empty_string(self):
        """None falls back to the env var; '' would look like a real key."""
        with patch.object(
            server.mcp, "get_context", return_value=_ctx(_http_request())
        ):
            assert server._request_api_key() is None


# ---------------------------------------------------------------------------
# THE test — one caller's key must never serve another's request
# ---------------------------------------------------------------------------


class TestCredentialIsolation:
    def test_two_callers_get_their_own_keys(self):
        """The regression that the module-level singleton would have caused.

        Mutation check: reintroduce a cached client in _get_client() and this
        fails — the second caller receives the first caller's credential.
        """
        with patch.object(
            server.mcp,
            "get_context",
            return_value=_ctx(_http_request(headers={"X-API-Key": "tru8_sk_alice"})),
        ):
            alice = server._get_client()

        with patch.object(
            server.mcp,
            "get_context",
            return_value=_ctx(_http_request(headers={"X-API-Key": "tru8_sk_bob"})),
        ):
            bob = server._get_client()

        assert alice.api_key == "tru8_sk_alice"
        assert bob.api_key == "tru8_sk_bob"
        assert alice is not bob, "clients must not be shared between callers"

    def test_client_is_never_cached_across_requests(self):
        """Even for the SAME key, a fresh client — no cross-request state."""
        ctx = _ctx(_http_request(headers={"X-API-Key": "tru8_sk_same"}))
        with patch.object(server.mcp, "get_context", return_value=ctx):
            first = server._get_client()
            second = server._get_client()
        assert first is not second

    def test_no_module_level_client_survives(self):
        """The singleton itself must stay gone, not merely be unused."""
        assert not hasattr(server, "_client"), (
            "a module-level client is exactly the credential-crossing bug this "
            "file exists to prevent"
        )


# ---------------------------------------------------------------------------
# stdio must keep working — the published package depends on it
# ---------------------------------------------------------------------------


class TestStdioUnchanged:
    def test_falls_back_to_environment(self, monkeypatch):
        monkeypatch.setenv("TRU8_API_KEY", "tru8_sk_from_env")
        with patch.object(server.mcp, "get_context", return_value=_ctx(None)):
            assert server._get_client().api_key == "tru8_sk_from_env"

    def test_request_key_overrides_environment(self, monkeypatch):
        """A hosted caller's key must win over whatever the host has set."""
        monkeypatch.setenv("TRU8_API_KEY", "tru8_sk_host_env")
        with patch.object(
            server.mcp,
            "get_context",
            return_value=_ctx(_http_request(headers={"X-API-Key": "tru8_sk_caller"})),
        ):
            assert server._get_client().api_key == "tru8_sk_caller"

    def test_no_key_anywhere_raises(self, monkeypatch):
        """Failing closed is the point — never fall through unauthenticated."""
        monkeypatch.delenv("TRU8_API_KEY", raising=False)
        with patch.object(server.mcp, "get_context", return_value=_ctx(None)):
            with pytest.raises(ValueError, match="TRU8_API_KEY"):
                server._get_client()
