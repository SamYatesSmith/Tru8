"""User-submitted ingest URLs are connected to the address that was checked.

Security sweep 2026-11-02, #2 (remainder): `safe_get` validated each hop with
`assert_public_url`, then `requests` resolved the host AGAIN to connect. A
DNS-rebinding host answers public to the check and private to the connect.
`safe_get` now mounts `_PinnedHTTPAdapter`: urllib3 dials only an address it
has just validated, and TLS still verifies the real hostname.
"""

import http.server
import ipaddress
import socket
import threading

import pytest
import requests

from app.core import url_safety as us
from app.core.url_safety import UnsafeUrlError, safe_get

_REAL_GETADDRINFO = socket.getaddrinfo


def _answer(ip, port):
    fam = socket.AF_INET6 if ":" in ip else socket.AF_INET
    return [(fam, socket.SOCK_STREAM, 6, "", (ip, port or 0))]


@pytest.fixture
def dns(monkeypatch):
    """Per-host answers; a list of answers is consumed one lookup at a time."""
    table, calls = {}, []

    def fake(host, port, *a, **kw):
        try:
            ipaddress.ip_address(str(host).strip("[]"))
            return _REAL_GETADDRINFO(host, port, *a, **kw)
        except ValueError:
            pass
        calls.append(host)
        ans = table[host]
        ip = (
            ans.pop(0)
            if isinstance(ans, list) and len(ans) > 1
            else (ans[0] if isinstance(ans, list) else ans)
        )
        return _answer(ip, port)

    monkeypatch.setattr(socket, "getaddrinfo", fake)
    return table, calls


def test_rebinding_between_check_and_connect_is_refused(dns, monkeypatch):
    """The check sees a public address; the connect would see a private one.
    Before this fix the connection went to the private address."""
    table, _ = dns
    table["rebind.example"] = ["93.184.216.34", "10.0.0.5"]
    dialled = []
    import urllib3.util.connection as u3

    monkeypatch.setattr(
        u3,
        "create_connection",
        lambda addr, *a, **k: dialled.append(addr)
        or (_ for _ in ()).throw(OSError("x")),
    )
    with pytest.raises(UnsafeUrlError):
        safe_get("http://rebind.example/page", timeout=5)
    assert dialled == []  # never dialled the private address


def test_connection_goes_to_the_validated_ip_not_the_name(dns, monkeypatch):
    table, _ = dns
    table["news.example"] = ["93.184.216.34"]
    dialled = []
    import urllib3.util.connection as u3

    def record(addr, *a, **k):
        dialled.append(addr)
        raise OSError("stop here")

    monkeypatch.setattr(u3, "create_connection", record)
    with pytest.raises(requests.ConnectionError):
        safe_get("http://news.example/page", timeout=5)
    assert dialled and dialled[0][0] == "93.184.216.34"


def test_internal_name_never_resolves(dns):
    _, calls = dns
    with pytest.raises(UnsafeUrlError):
        safe_get("http://qdrant.railway.internal:6333/", timeout=5)
    assert calls == []


def test_session_ignores_environment_proxies(dns, monkeypatch):
    """An HTTP(S)_PROXY would dial the proxy, not the target, bypassing the pin."""
    table, _ = dns
    table["news.example"] = ["93.184.216.34"]
    monkeypatch.setenv("HTTP_PROXY", "http://127.0.0.1:9")
    session = requests.Session()
    import urllib3.util.connection as u3

    monkeypatch.setattr(
        u3, "create_connection", lambda *a, **k: (_ for _ in ()).throw(OSError("x"))
    )
    with pytest.raises(requests.ConnectionError):
        safe_get("http://news.example/", session=session, timeout=5)
    assert session.trust_env is False


class _Redirector(http.server.BaseHTTPRequestHandler):
    hits, target = [], ""

    def do_GET(self):
        _Redirector.hits.append(self.path)
        self.send_response(302)
        self.send_header("Location", _Redirector.target)
        self.end_headers()

    def log_message(self, *a):
        pass


def test_real_redirect_to_internal_host_is_stopped(dns, monkeypatch):
    server = http.server.HTTPServer(("127.0.0.1", 0), _Redirector)
    port = server.server_address[1]
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        table, _ = dns
        table["public-page.test"] = ["127.0.0.1"]
        table["evil-internal.test"] = ["10.0.0.5"]
        real = us._ip_is_blocked
        monkeypatch.setattr(
            us,
            "_ip_is_blocked",
            lambda ip: False if ip == ipaddress.ip_address("127.0.0.1") else real(ip),
        )
        _Redirector.hits = []
        _Redirector.target = f"http://evil-internal.test:{port}/secrets"
        with pytest.raises(UnsafeUrlError):
            safe_get(f"http://public-page.test:{port}/article", timeout=5)
        assert _Redirector.hits == ["/article"]
    finally:
        server.shutdown()


def test_adapter_is_mounted_once_per_session(dns, monkeypatch):
    """Ingest retries safe_get on one session; each call must not stack a
    fresh adapter (and a fresh connection pool)."""
    table, _ = dns
    table["news.example"] = ["93.184.216.34"]
    import urllib3.util.connection as u3

    monkeypatch.setattr(
        u3, "create_connection", lambda *a, **k: (_ for _ in ()).throw(OSError("x"))
    )
    session = requests.Session()
    for _ in range(2):
        with pytest.raises(requests.ConnectionError):
            safe_get("http://news.example/", session=session, timeout=5)
    first = session.get_adapter("https://x")
    with pytest.raises(requests.ConnectionError):
        safe_get("http://news.example/", session=session, timeout=5)
    assert session.get_adapter("https://x") is first


def test_dns_failure_reads_as_a_resolution_error(monkeypatch):
    def nx(*a, **k):
        raise socket.gaierror("Name or service not known")

    monkeypatch.setattr(us, "_validated_addresses", lambda h, p: nx())
    # Past the pre-check (it would report a DNS failure itself), so the
    # connection layer's own lookup is what fails.
    monkeypatch.setattr(us, "assert_public_url", lambda url: None)
    with pytest.raises(requests.ConnectionError) as exc:
        safe_get("http://nxdomain.example/", timeout=5)
    assert "resolve" in str(exc.value).lower()
