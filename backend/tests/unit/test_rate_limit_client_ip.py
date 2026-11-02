"""IP-keyed rate limits key on the CALLER, not our proxy (2026-11-02).

Production is Cloudflare -> Railway proxy -> uvicorn without trusted forwarded
headers, so request.client.host was one proxy address for everyone: every
IP-keyed limit (waitlist 5/min, public PDF 6/min, defaults) was a single
site-wide bucket.
"""

from types import SimpleNamespace

from starlette.datastructures import Headers

from app.core.rate_limit import _get_rate_limit_key


def _req(headers, host="10.250.0.7"):
    return SimpleNamespace(
        headers=Headers(headers=headers),  # case-insensitive, like a real request
        client=SimpleNamespace(host=host),
    )


def test_cloudflare_header_wins():
    r = _req({"CF-Connecting-IP": "203.0.113.9", "X-Forwarded-For": "198.51.100.1"})
    assert _get_rate_limit_key(r) == "203.0.113.9"


def test_forwarded_for_first_hop_when_no_cloudflare_header():
    r = _req({"X-Forwarded-For": "198.51.100.1, 10.0.0.2"})
    assert _get_rate_limit_key(r) == "198.51.100.1"


def test_two_callers_behind_one_proxy_get_separate_buckets():
    a = _req({"CF-Connecting-IP": "203.0.113.9"})
    b = _req({"CF-Connecting-IP": "203.0.113.10"})
    assert _get_rate_limit_key(a) != _get_rate_limit_key(b)


def test_direct_connection_falls_back_to_the_socket_address():
    assert _get_rate_limit_key(_req({}, host="192.0.2.5")) == "192.0.2.5"


def test_api_key_still_takes_precedence():
    r = _req(
        {"X-API-Key": "tru8_sk_abcdefghijklmnop", "CF-Connecting-IP": "203.0.113.9"}
    )
    assert _get_rate_limit_key(r).startswith("apikey:")
