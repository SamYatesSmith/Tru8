"""Connection-level SSRF defence (security sweep 2026-11-02, #2).

Design + review: audit/2026-11-02_safe_fetch_design.md. Evidence, PDF,
fact-check, Compare and title-recovery fetches follow URLs we did not choose;
before this, a search result could 302 our fetcher to 169.254.169.254 or a
*.railway.internal service and the response text was stored in a public
record. Every connection is now validated at the httpcore network backend:
every redirect hop, pinned to the exact address checked.
"""

import http.server
import ipaddress
import socket
import threading
from pathlib import Path

import httpcore
import httpx
import pytest

from app.core import url_safety as us
from app.core.url_safety import SafeNetworkBackend, UnsafeUrlError, safe_async_client

PUBLIC_A = "93.184.216.34"
PUBLIC_B = "93.184.216.35"


def _infos(*ips, port=80):
    out = []
    for ip in ips:
        fam = socket.AF_INET6 if ":" in ip else socket.AF_INET
        out.append((fam, socket.SOCK_STREAM, 6, "", (ip, port)))
    return out


class _FakeStream(httpcore.AsyncNetworkStream):
    def __init__(self):
        self.tls_hostname = None

    async def read(self, max_bytes, timeout=None):
        return b""

    async def write(self, buffer, timeout=None):
        return None

    async def aclose(self):
        return None

    async def start_tls(self, ssl_context, server_hostname=None, timeout=None):
        self.tls_hostname = server_hostname
        raise httpcore.ConnectError("stop after recording SNI")


class _RecordingInner(httpcore.AsyncNetworkBackend):
    def __init__(self, fail_first=0):
        self.calls = []
        self.fail_first = fail_first
        self.stream = _FakeStream()

    async def connect_tcp(
        self, host, port, timeout=None, local_address=None, socket_options=None
    ):
        self.calls.append(host)
        if len(self.calls) <= self.fail_first:
            raise httpcore.ConnectError("unreachable")
        return self.stream

    async def connect_unix_socket(self, *a, **k):  # pragma: no cover
        raise AssertionError("never")

    async def sleep(self, seconds):
        return None


@pytest.fixture
def resolver(monkeypatch):
    table = {}
    calls = []

    async def fake_getaddrinfo(host, port, **kw):
        calls.append(host)
        answer = table[host]
        if callable(answer):
            answer = answer()
        return _infos(*answer, port=port)

    monkeypatch.setattr(us.anyio, "getaddrinfo", fake_getaddrinfo)
    return table, calls


# --- the backend ------------------------------------------------------------


@pytest.mark.parametrize(
    "addrs",
    [
        ["10.0.0.5"],
        ["169.254.169.254"],
        ["::1"],
        ["::ffff:10.0.0.1"],
        ["fd12::1"],
        ["2002:0a00:0001::1"],
    ],
)
@pytest.mark.asyncio
async def test_host_resolving_to_internal_is_refused_before_connect(resolver, addrs):
    table, _ = resolver
    table["attacker.example"] = addrs
    inner = _RecordingInner()
    with pytest.raises(UnsafeUrlError):
        await SafeNetworkBackend(inner).connect_tcp("attacker.example", 80)
    assert inner.calls == []


@pytest.mark.asyncio
async def test_mixed_public_and_private_answers_are_refused(resolver):
    table, _ = resolver
    table["mixed.example"] = [PUBLIC_A, "10.1.2.3"]
    inner = _RecordingInner()
    with pytest.raises(UnsafeUrlError):
        await SafeNetworkBackend(inner).connect_tcp("mixed.example", 80)
    assert inner.calls == []


@pytest.mark.parametrize(
    "host",
    [
        "qdrant.railway.internal",
        "localhost",
        "localhost.",
        "x.railway.internal.",
        "box.local",
    ],
)
@pytest.mark.asyncio
async def test_internal_names_are_refused_without_dns(resolver, host):
    _, calls = resolver
    with pytest.raises(UnsafeUrlError):
        await SafeNetworkBackend(_RecordingInner()).connect_tcp(host, 80)
    assert calls == []


@pytest.mark.parametrize(
    "ip", ["127.0.0.1", "10.0.0.1", "169.254.169.254", "[::1]", "0.0.0.0"]
)
@pytest.mark.asyncio
async def test_internal_ip_literals_are_refused(ip):
    with pytest.raises(UnsafeUrlError):
        await SafeNetworkBackend(_RecordingInner()).connect_tcp(ip, 80)


@pytest.mark.asyncio
async def test_connects_to_the_exact_address_it_validated(resolver):
    """DNS rebinding: a later answer pointing inside must never be used."""
    table, calls = resolver
    answers = iter([[PUBLIC_A], ["10.0.0.5"]])
    table["rebind.example"] = lambda: next(answers)
    inner = _RecordingInner()
    await SafeNetworkBackend(inner).connect_tcp("rebind.example", 80)
    assert inner.calls == [PUBLIC_A]
    assert calls == ["rebind.example"]  # one lookup per connection


@pytest.mark.asyncio
async def test_falls_back_across_validated_addresses(resolver):
    """Review finding 2: a dual-stack site whose first address is unreachable
    must still connect on the next one, as anyio's own connect would."""
    table, _ = resolver
    table["dual.example"] = ["2606:2800:220:1::1", PUBLIC_A]
    inner = _RecordingInner(fail_first=1)
    await SafeNetworkBackend(inner).connect_tcp("dual.example", 443)
    assert inner.calls == ["2606:2800:220:1::1", PUBLIC_A]


@pytest.mark.asyncio
async def test_unix_sockets_are_refused():
    with pytest.raises(UnsafeUrlError):
        await SafeNetworkBackend(_RecordingInner()).connect_unix_socket(
            "/var/run/x.sock"
        )


@pytest.mark.asyncio
async def test_decimal_ip_literal_resolving_to_loopback_is_refused():
    """httpx passes http://2130706433/ to the resolver as a hostname; the
    resolver turns it into 127.0.0.1. Validation runs on the resolved address."""
    try:
        socket.getaddrinfo("2130706433", 80)
    except OSError:
        pytest.skip("platform resolver does not parse decimal IPv4")
    with pytest.raises(UnsafeUrlError):
        await SafeNetworkBackend(_RecordingInner()).connect_tcp("2130706433", 80)


# --- through httpx (redirects, TLS) -----------------------------------------


@pytest.mark.asyncio
async def test_tls_still_verifies_the_real_hostname(resolver, monkeypatch):
    """We connect to an IP, but SNI/certificate checks use the URL's host."""
    table, _ = resolver
    table["news.example"] = [PUBLIC_A]
    inner = _RecordingInner()
    monkeypatch.setattr(us.httpcore, "AnyIOBackend", lambda: inner)
    async with safe_async_client(timeout=5) as client:
        with pytest.raises(httpx.ConnectError):
            await client.get("https://news.example/story")
    assert inner.calls == [PUBLIC_A]
    assert inner.stream.tls_hostname == "news.example"


class _Redirector(http.server.BaseHTTPRequestHandler):
    hits = []
    target = ""

    def do_GET(self):
        _Redirector.hits.append(self.path)
        self.send_response(302)
        self.send_header("Location", _Redirector.target)
        self.end_headers()

    def log_message(self, *a):
        pass


@pytest.mark.asyncio
async def test_redirect_to_an_internal_host_is_stopped_mid_chain(resolver, monkeypatch):
    """The first hop is a real public-looking page; its 302 points at a name
    that resolves inside. The chain must stop at the second connection."""
    server = http.server.HTTPServer(("127.0.0.1", 0), _Redirector)
    port = server.server_address[1]
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        table, _ = resolver
        table["public-page.test"] = ["127.0.0.1"]
        table["evil-internal.test"] = ["10.0.0.5"]
        real_blocked = us._ip_is_blocked
        # Loopback stands in for "public" for this one test server only.
        monkeypatch.setattr(
            us,
            "_ip_is_blocked",
            lambda ip: (
                False if ip == ipaddress.ip_address("127.0.0.1") else real_blocked(ip)
            ),
        )
        _Redirector.hits = []
        _Redirector.target = f"http://evil-internal.test:{port}/secrets"
        async with safe_async_client(timeout=5, follow_redirects=True) as client:
            with pytest.raises(UnsafeUrlError):
                await client.get(f"http://public-page.test:{port}/article")
        assert _Redirector.hits == ["/article"]  # first hop really fetched
    finally:
        server.shutdown()


# --- the client factory ------------------------------------------------------


@pytest.mark.parametrize(
    "kw", ["mounts", "verify", "proxy", "http2", "limits", "transport"]
)
def test_settings_httpx_would_silently_ignore_are_refused(kw):
    with pytest.raises(TypeError):
        safe_async_client(**{kw: None})


def test_client_is_wired_to_the_safe_backend():
    """Guards the private `_pool` wiring: a library upgrade that changes it
    must fail here, loudly, not quietly fall back to unchecked connects."""
    client = safe_async_client(timeout=5)
    pool = client._transport._pool
    assert isinstance(pool, httpcore.AsyncConnectionPool)
    assert isinstance(pool._network_backend, SafeNetworkBackend)
    assert client._trust_env is False


# --- every attacker-influenced fetch uses it ---------------------------------

APP = Path(__file__).resolve().parents[2] / "app"


@pytest.mark.parametrize(
    "rel",
    [
        "services/evidence.py",
        "services/pdf_evidence.py",
        "services/factcheck_api.py",
        "services/article_reader.py",
        "services/title_recovery.py",
        "services/webhooks.py",
    ],
)
def test_untrusted_url_fetchers_use_the_safe_client(rel):
    src = (APP / rel).read_text(encoding="utf-8")
    assert "safe_async_client(" in src
    assert "httpx.AsyncClient(" not in src


# --- verifier round 2 (2026-11-02) ------------------------------------------


class _HangsFirst(_RecordingInner):
    async def connect_tcp(
        self, host, port, timeout=None, local_address=None, socket_options=None
    ):
        self.calls.append((host, timeout))
        if len(self.calls) == 1:
            await us.anyio.sleep(timeout if timeout is not None else 60)
            raise httpcore.ConnectTimeout("silently dropped")
        return self.stream


@pytest.mark.asyncio
async def test_an_address_that_hangs_does_not_eat_the_whole_budget(
    resolver, monkeypatch
):
    """The first address drops packets silently; the next must still be tried
    well inside the overall timeout (anyio races them 250 ms apart)."""
    monkeypatch.setattr(us, "_PER_ADDRESS_CAP_S", 0.3)
    table, _ = resolver
    table["v6broken.example"] = ["2606:2800:220:1::1", PUBLIC_A]
    inner = _HangsFirst()
    start = us.anyio.current_time()
    await SafeNetworkBackend(inner).connect_tcp("v6broken.example", 443, timeout=10)
    elapsed = us.anyio.current_time() - start
    assert [h for h, _ in inner.calls] == ["2606:2800:220:1::1", PUBLIC_A]
    assert inner.calls[0][1] <= 0.3
    assert elapsed < 2


def test_clients_share_one_ssl_context():
    """Building a context loads the CA bundle; ~40 fetches per claim each make
    a client, so it is built once."""
    a = safe_async_client(timeout=5)._transport._pool._ssl_context
    b = safe_async_client(timeout=5)._transport._pool._ssl_context
    assert a is b


@pytest.mark.asyncio
async def test_evidence_fetch_drops_a_hostile_page_with_a_receipt(resolver, caplog):
    """Site level: a search result whose host resolves inside is dropped
    outright (no snippet fallback) and leaves a [URL LEDGER] receipt."""
    import asyncio
    import logging

    from app.services.evidence import EvidenceExtractor
    from app.services.search import SearchResult

    table, _ = resolver
    table["hostile.example"] = ["169.254.169.254"]
    caplog.set_level(logging.WARNING)
    result = await EvidenceExtractor()._extract_from_page(
        SearchResult(title="t", url="http://hostile.example/page", snippet="bait"),
        "a claim",
        asyncio.Semaphore(1),
    )
    assert result is None
    assert any(
        "stage=unsafe_url" in r.getMessage() and "hostile.example" in r.getMessage()
        for r in caplog.records
    )


@pytest.mark.asyncio
async def test_title_recovery_refusal_leaves_a_receipt(resolver, caplog, monkeypatch):
    import logging

    from app.services import title_recovery as tr

    monkeypatch.delenv(tr._CASSETTE_ACTIVE_ENV, raising=False)
    table, _ = resolver
    table["archive.org"] = ["10.9.9.9"]
    caplog.set_level(logging.WARNING)
    items = [
        {
            "url": "https://news.example/a",
            "title": "Breaking: something happened in ...",
        }
    ]
    monkeypatch.setattr(tr, "is_truncated_title", lambda t: True)
    await tr.recover_truncated_titles(items)
    assert any("stage=unsafe_url" in r.getMessage() for r in caplog.records)
