"""F-SEC-02: SSRF defence for any outbound URL fetch.

Public surface:

- ``assert_public_url(url)`` — raises ``UnsafeUrlError`` if the URL resolves to
  a private/internal/reserved address. Use BEFORE every outbound fetch
  (pipeline ingest, webhook delivery) and at the input boundary for any
  user-supplied URL (webhook registration).
- ``safe_get(url, …)`` — synchronous ``requests.get`` wrapper that validates
  the URL, follows redirects manually, and re-validates each hop.
- ``safe_async_post(client, url, …)`` — async ``httpx`` POST that validates
  before send (redirects are disabled — webhook receivers shouldn't redirect).
- ``safe_async_client(…)`` — an ``httpx.AsyncClient`` whose CONNECTIONS are
  validated (2026-11-02, audit/2026-11-02_safe_fetch_design.md). Every TCP
  connect resolves the host once, refuses it if ANY address is internal, and
  connects to the exact address it checked. Redirects are followed by httpx
  as before, but each new host is a new connection, so every hop is checked,
  and DNS rebinding between check and connect is impossible. TLS still
  verifies the real hostname (httpcore takes SNI from the request origin).
  Use it for every fetch of a URL we did not hard-code.

Known limitation: ``safe_get`` (``requests``, user-submitted ingest) still
resolves twice, so a rebinding host can pass its check and connect elsewhere.
"""

from __future__ import annotations

import ipaddress
import logging
import socket
from typing import Any, Iterable, Optional
from urllib.parse import urljoin, urlparse

import anyio
import httpcore
import httpx
import requests

logger = logging.getLogger(__name__)


class UnsafeUrlError(ValueError):
    """Raised when a URL targets a private, internal, or otherwise unsafe address."""


# Blocked ranges per RFC 1918, RFC 6598 (CGNAT), RFC 3927 (link-local),
# RFC 4193 (ULA), plus loopback, multicast, reserved, and IPv4-mapped IPv6.
_BLOCKED_V4 = [
    ipaddress.IPv4Network("0.0.0.0/8"),  # "this network"
    ipaddress.IPv4Network("10.0.0.0/8"),
    ipaddress.IPv4Network("100.64.0.0/10"),  # CGNAT
    ipaddress.IPv4Network("127.0.0.0/8"),  # loopback
    ipaddress.IPv4Network(
        "169.254.0.0/16"
    ),  # link-local (incl. cloud metadata 169.254.169.254)
    ipaddress.IPv4Network("172.16.0.0/12"),
    ipaddress.IPv4Network("192.0.0.0/24"),  # IETF reserved
    ipaddress.IPv4Network("192.0.2.0/24"),  # TEST-NET-1
    ipaddress.IPv4Network("192.168.0.0/16"),
    ipaddress.IPv4Network("198.18.0.0/15"),  # benchmark testing
    ipaddress.IPv4Network("198.51.100.0/24"),  # TEST-NET-2
    ipaddress.IPv4Network("203.0.113.0/24"),  # TEST-NET-3
    ipaddress.IPv4Network("224.0.0.0/4"),  # multicast
    ipaddress.IPv4Network("240.0.0.0/4"),  # reserved
    ipaddress.IPv4Network("255.255.255.255/32"),
]

_BLOCKED_V6 = [
    ipaddress.IPv6Network("::1/128"),  # loopback
    ipaddress.IPv6Network("::/128"),  # unspecified
    ipaddress.IPv6Network("::ffff:0:0/96"),  # IPv4-mapped — defer to v4 check
    ipaddress.IPv6Network("64:ff9b::/96"),  # IPv4/IPv6 translation
    ipaddress.IPv6Network("100::/64"),  # discard
    ipaddress.IPv6Network("2001::/23"),  # IETF reserved
    # 6to4 embeds an IPv4 address; covered by is_private on current Python but
    # not guaranteed across versions (the image tag floats), so stated here.
    ipaddress.IPv6Network("2002::/16"),
    ipaddress.IPv6Network("fc00::/7"),  # ULA
    ipaddress.IPv6Network("fe80::/10"),  # link-local
    ipaddress.IPv6Network("ff00::/8"),  # multicast
]

_ALLOWED_SCHEMES = frozenset({"http", "https"})


def _ip_is_blocked(ip: ipaddress._BaseAddress) -> bool:
    if isinstance(ip, ipaddress.IPv4Address):
        # ipaddress's is_private already covers the common cases, but
        # is_reserved/is_multicast/is_loopback/is_link_local cover the rest.
        if (
            ip.is_loopback
            or ip.is_link_local
            or ip.is_multicast
            or ip.is_reserved
            or ip.is_private
            or ip.is_unspecified
        ):
            return True
        return any(ip in net for net in _BLOCKED_V4)
    if isinstance(ip, ipaddress.IPv6Address):
        if ip.ipv4_mapped is not None:
            return _ip_is_blocked(ip.ipv4_mapped)
        if (
            ip.is_loopback
            or ip.is_link_local
            or ip.is_multicast
            or ip.is_reserved
            or ip.is_private
            or ip.is_unspecified
            or ip.is_site_local
        ):
            return True
        return any(ip in net for net in _BLOCKED_V6)
    return True  # unknown family — refuse


def _resolve_all(host: str) -> Iterable[ipaddress._BaseAddress]:
    addrs = []
    try:
        for info in socket.getaddrinfo(host, None):
            family, _, _, _, sockaddr = info
            addr = sockaddr[0]
            try:
                addrs.append(ipaddress.ip_address(addr.split("%")[0]))  # strip zone id
            except ValueError:
                continue
    except socket.gaierror as exc:
        raise UnsafeUrlError(f"DNS resolution failed for {host}: {exc}") from exc
    if not addrs:
        raise UnsafeUrlError(f"DNS returned no addresses for {host}")
    return addrs


def _is_internal_hostname(host: str) -> bool:
    """True for names that only exist inside our network. A trailing dot
    (`localhost.`) is the same name, so it is stripped first."""
    lower = host.rstrip(".").lower()
    return (
        lower == "localhost"
        or lower.endswith(".local")
        or lower.endswith(".internal")
        or lower.endswith(".localhost")
        or lower.endswith(".railway.internal")
    )


def assert_public_url(url: str) -> None:
    """Raise UnsafeUrlError if the URL targets a private/internal address.

    Validates: scheme (http/https only), host present, DNS resolves, every
    resolved address is publicly routable. Hostnames that resolve to MIXED
    public+private addresses (a common DNS-rebinding precursor) are refused —
    we require ALL resolved addresses to be public.
    """
    if not isinstance(url, str) or not url:
        raise UnsafeUrlError("URL is empty or not a string")

    parsed = urlparse(url)
    if parsed.scheme.lower() not in _ALLOWED_SCHEMES:
        raise UnsafeUrlError(f"URL scheme not allowed: {parsed.scheme!r}")

    host = parsed.hostname
    if not host:
        raise UnsafeUrlError("URL has no host")

    # Reject literal IPs we already know are blocked, without DNS.
    try:
        literal = ipaddress.ip_address(host)
        if _ip_is_blocked(literal):
            raise UnsafeUrlError(f"URL targets blocked address: {literal}")
        return
    except ValueError:
        pass  # not a literal — fall through to DNS

    # Block obvious internal hostnames before DNS to avoid leaking resolution
    # attempts on internal names.
    if _is_internal_hostname(host):
        raise UnsafeUrlError(f"URL targets internal hostname: {host}")

    for addr in _resolve_all(host):
        if _ip_is_blocked(addr):
            raise UnsafeUrlError(f"URL host {host} resolves to blocked address {addr}")


# ---------------------------------------------------------------------------
# Fetcher wrappers — validate-before-connect, validate-each-redirect-hop
# ---------------------------------------------------------------------------

# Cap manual redirect following to match the existing ingest session limit.
_MAX_REDIRECTS = 5


def safe_get(
    url: str,
    *,
    session: Optional[requests.Session] = None,
    timeout: Optional[float] = None,
    headers: Optional[dict] = None,
    max_redirects: int = _MAX_REDIRECTS,
    **kwargs: Any,
) -> requests.Response:
    """``requests.get`` with SSRF protection on the URL AND every redirect hop.

    Mirrors the previous ``session.get(url, allow_redirects=True)`` shape but:
    - validates ``url`` first;
    - disables automatic redirect following;
    - follows up to ``max_redirects`` manually, validating each hop;
    - returns the final (non-redirect) response.

    If a redirect targets a blocked address the chain stops and
    ``UnsafeUrlError`` is raised — the response that triggered the redirect
    is discarded.
    """
    own_session = session is None
    if own_session:
        session = requests.Session()

    try:
        current = url
        for hop in range(max_redirects + 1):
            assert_public_url(current)
            response = session.get(
                current,
                timeout=timeout,
                headers=headers,
                allow_redirects=False,
                **kwargs,
            )
            if response.is_redirect or response.is_permanent_redirect:
                location = response.headers.get("Location")
                if not location:
                    return response
                current = urljoin(response.url, location)
                continue
            return response

        raise UnsafeUrlError(
            f"Exceeded max redirects ({max_redirects}) starting from {url}"
        )
    finally:
        if own_session:
            session.close()


async def safe_async_post(
    client: httpx.AsyncClient,
    url: str,
    *,
    content: bytes,
    headers: Optional[dict] = None,
) -> httpx.Response:
    """``httpx.AsyncClient.post`` with SSRF protection.

    Webhook delivery is the only caller; we deliberately do NOT follow
    redirects (a webhook receiver redirecting elsewhere is the textbook
    exfiltration vector). The receiver must accept the POST at its
    registered URL or the delivery fails.
    """
    assert_public_url(url)
    return await client.post(
        url,
        content=content,
        headers=headers,
        follow_redirects=False,
    )


# ---------------------------------------------------------------------------
# Connection-level validation — every hop, pinned to the checked address
# ---------------------------------------------------------------------------


# Ceiling on any one address's connect attempt when more addresses remain.
_PER_ADDRESS_CAP_S = 2.0


class SafeNetworkBackend(httpcore.AsyncNetworkBackend):
    """httpcore network backend that validates every TCP connection.

    For a hostname: resolve once, refuse if ANY address is blocked, then try
    each validated address in turn (keeps the fallback across addresses that
    anyio's own connect performs — a dual-stack site whose IPv6 is unreachable
    still connects over IPv4). The inner backend receives an IP literal, so it
    does no second lookup: what we checked is what we connect to.
    """

    def __init__(self, inner: Optional[httpcore.AsyncNetworkBackend] = None):
        self._inner = inner or httpcore.AnyIOBackend()

    async def connect_tcp(
        self,
        host: str,
        port: int,
        timeout: Optional[float] = None,
        local_address: Optional[str] = None,
        socket_options: Optional[Iterable] = None,
    ) -> httpcore.AsyncNetworkStream:
        now = anyio.current_time
        deadline = None if timeout is None else now() + timeout

        try:
            literal = ipaddress.ip_address(host.strip("[]"))
        except ValueError:
            literal = None

        if literal is not None:
            if _ip_is_blocked(literal):
                raise UnsafeUrlError(
                    f"Connection to blocked address refused: {literal}"
                )
            addresses = [str(literal)]
        else:
            if _is_internal_hostname(host):
                raise UnsafeUrlError(f"Connection to internal hostname refused: {host}")
            try:
                with anyio.fail_after(timeout):
                    infos = await anyio.getaddrinfo(host, port, type=socket.SOCK_STREAM)
            except TimeoutError as exc:
                raise httpcore.ConnectTimeout(f"DNS timed out for {host}") from exc
            except OSError as exc:
                raise httpcore.ConnectError(f"DNS failed for {host}: {exc}") from exc
            addresses = []
            for info in infos:
                addr = info[4][0].split("%")[0]
                if addr not in addresses:
                    addresses.append(addr)
            if not addresses:
                raise httpcore.ConnectError(f"DNS returned no addresses for {host}")
            for addr in addresses:
                if _ip_is_blocked(ipaddress.ip_address(addr)):
                    raise UnsafeUrlError(
                        f"Host {host} resolves to blocked address {addr}"
                    )

        last_error: Optional[Exception] = None
        for i, addr in enumerate(addresses):
            remaining = None
            if deadline is not None:
                remaining = deadline - now()
                if remaining <= 0:
                    break
            # An address that silently drops packets must not eat the whole
            # budget before the next is tried (anyio's own connect races them
            # 250 ms apart). Every address but the last gets a bounded share;
            # the last gets whatever is left. Verifier, 2026-11-02.
            attempt = remaining
            if i < len(addresses) - 1:
                share = (
                    _PER_ADDRESS_CAP_S
                    if remaining is None
                    else max(0.25, remaining / (len(addresses) - i))
                )
                attempt = min(share, _PER_ADDRESS_CAP_S)
                if remaining is not None:
                    attempt = min(attempt, remaining)
            try:
                return await self._inner.connect_tcp(
                    addr,
                    port,
                    timeout=attempt,
                    local_address=local_address,
                    socket_options=socket_options,
                )
            except (httpcore.ConnectError, httpcore.ConnectTimeout) as exc:
                last_error = exc
        if last_error is None or isinstance(last_error, httpcore.ConnectTimeout):
            raise httpcore.ConnectTimeout(f"Connect timed out for {host}")
        raise last_error

    async def connect_unix_socket(self, *args, **kwargs):
        raise UnsafeUrlError("Unix-socket connections are not allowed")

    async def sleep(self, seconds: float) -> None:
        await self._inner.sleep(seconds)


_SAFE_CLIENT_KWARGS = frozenset({"timeout", "headers", "follow_redirects", "cookies"})

# Built once and shared: creating an SSL context loads the CA bundle (hundreds
# of ms of event-loop CPU on Windows), and every evidence fetch makes a client.
# Sharing is safe — httpcore only ever sets the same ALPN value on it.
_SSL_CONTEXT = None


def _ssl_context():
    global _SSL_CONTEXT
    if _SSL_CONTEXT is None:
        _SSL_CONTEXT = httpx.create_ssl_context(verify=True, trust_env=False)
    return _SSL_CONTEXT


def safe_async_client(**kwargs: Any) -> httpx.AsyncClient:
    """An ``httpx.AsyncClient`` whose every connection is validated.

    Only ``timeout``, ``headers``, ``follow_redirects`` and ``cookies`` are
    accepted: with a custom transport httpx silently ignores ``verify``,
    ``cert``, ``http2``, ``limits`` and ``proxy``, and ``mounts`` would route
    around the safe backend entirely — so anything else is an error, not a
    quiet no-op. Transport settings match httpx's defaults (verify on,
    HTTP/1.1, 100/20 connections, 5 s keep-alive, no retries, no proxies).

    ``httpx.AsyncClient`` is looked up at call time so tests that patch it on
    a module still intercept the client.
    """
    unknown = set(kwargs) - _SAFE_CLIENT_KWARGS
    if unknown:
        raise TypeError(f"safe_async_client does not accept: {sorted(unknown)}")
    ctx = _ssl_context()
    transport = httpx.AsyncHTTPTransport(verify=ctx, trust_env=False)
    transport._pool = httpcore.AsyncConnectionPool(
        ssl_context=ctx,
        max_connections=100,
        max_keepalive_connections=20,
        keepalive_expiry=5.0,
        http1=True,
        http2=False,
        retries=0,
        network_backend=SafeNetworkBackend(),
    )
    return httpx.AsyncClient(transport=transport, trust_env=False, **kwargs)
