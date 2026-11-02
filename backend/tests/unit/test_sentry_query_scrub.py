"""API keys in a query string never reach Sentry (security sweep 2026-11-02, #6).

The hosted /mcp accepts ?apiKey= (Smithery passes config that way). The scrubber
only redacted query strings containing `token=`, so an exception on
/mcp/?apiKey=tru8_sk_... shipped the key to Sentry.
"""

import pytest

from main import _filter_breadcrumb, _scrub_event_pii


@pytest.mark.parametrize(
    "query",
    [
        "apiKey=tru8_sk_secret",
        "api_key=tru8_sk_secret",
        "TRU8_API_KEY=tru8_sk_secret",
        "x=1&ApiKey=tru8_sk_secret",
        "token=abc",
    ],
)
def test_credential_query_strings_are_redacted(query):
    event = {"request": {"query_string": query}}
    out = _scrub_event_pii(event, None)
    assert "tru8_sk_secret" not in str(out)
    assert out["request"]["query_string"] == "[REDACTED]"


def test_harmless_query_string_is_kept():
    event = {"request": {"query_string": "compact=true"}}
    assert _scrub_event_pii(event, None)["request"]["query_string"] == "compact=true"


def test_httpx_breadcrumb_query_is_redacted():
    """httpx crumbs record `http.query`; our own Gemini calls use ?key=."""
    crumb = {
        "category": "httplib",
        "data": {
            "url": "https://x.googleapis.com/v1/m",
            "http.query": "key=AIzaSyFAKEFAKEFAKEFAKEFAKE123",
        },
    }
    out = _filter_breadcrumb(crumb, None)
    assert "AIzaSy" not in str(out)


def test_log_breadcrumb_with_mcp_key_is_redacted():
    crumb = {
        "category": "uvicorn",
        "message": "POST /mcp/?apiKey=tru8_sk_secret HTTP/1.1",
    }
    assert "tru8_sk_secret" not in str(_filter_breadcrumb(crumb, None))


def test_exception_value_quoting_a_keyed_url_is_redacted():
    event = {
        "exception": {
            "values": [
                {
                    "type": "HTTPStatusError",
                    "value": "Client error '429' for url 'https://g.example/v1?key=AIzaSyFAKEFAKEFAKEFAKEFAKE123&x=1'",
                }
            ]
        },
        "breadcrumbs": {"values": [{"message": "auth tru8_sk_abcdef123"}]},
    }
    out = _scrub_event_pii(event, None)
    assert "AIzaSy" not in str(out) and "tru8_sk_abcdef" not in str(out)
    assert "x=1" in str(out)  # non-secret context survives


def test_ordinary_text_is_untouched():
    crumb = {"category": "x", "message": "monkey business, keyboard=qwerty"}
    assert _filter_breadcrumb(crumb, None) == crumb
