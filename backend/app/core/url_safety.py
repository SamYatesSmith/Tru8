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

Known limitations:

- Time-of-check / time-of-use DNS rebinding mid-connection is NOT defended
  against here. The full defence is to resolve once and connect to the
  resolved IP directly while preserving the Host header for SNI. That is a
  meaningful refactor of ``requests``/``httpx`` adapters; flagged for
  post-launch hardening. The current defence is sufficient against the
  audit's stated threats (user submits ``http://10.0.0.1/``,
  ``http://qdrant.railway.internal:6333/``, ``http://169.254.169.254/`` etc.)
  and against single-step redirect-to-internal attacks.
"""

from __future__ import annotations

import ipaddress
import logging
import socket
from typing import Any, Iterable, Optional
from urllib.parse import urljoin, urlparse

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
    lower = host.lower()
    if (
        lower == "localhost"
        or lower.endswith(".local")
        or lower.endswith(".internal")
        or lower.endswith(".localhost")
        or lower.endswith(".railway.internal")
    ):
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
        last_response: Optional[requests.Response] = None
        for hop in range(max_redirects + 1):
            assert_public_url(current)
            response = session.get(
                current,
                timeout=timeout,
                headers=headers,
                allow_redirects=False,
                **kwargs,
            )
            last_response = response
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
