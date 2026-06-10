"""Tests for X-Tru8-Client header resolution (Check.client attribution)."""

from app.core.client_origin import resolve_client


class _FakeRequest:
    def __init__(self, headers: dict):
        self.headers = headers


def _req(value=None):
    return _FakeRequest({"X-Tru8-Client": value} if value is not None else {})


def test_mcp_versioned_header_resolves_to_mcp():
    assert resolve_client(_req("mcp/1.0.1")) == "mcp"


def test_name_only_no_version():
    assert resolve_client(_req("mcp")) == "mcp"


def test_case_insensitive():
    assert resolve_client(_req("MCP/2.0")) == "mcp"


def test_missing_header_returns_none():
    assert resolve_client(_req()) is None


def test_none_request_returns_none():
    assert resolve_client(None) is None


def test_empty_header_returns_none():
    assert resolve_client(_req("")) is None


def test_strips_unsafe_chars():
    # spaces and punctuation dropped; safe chars kept
    assert resolve_client(_req("my client!/1.0")) == "myclient"


def test_oversized_tag_truncated_to_32():
    out = resolve_client(_req("a" * 100 + "/1.0"))
    assert out == "a" * 32


def test_hyphen_and_underscore_preserved():
    assert resolve_client(_req("tru8-cli_v2/1.0")) == "tru8-cli_v2"
