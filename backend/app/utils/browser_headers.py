"""Outbound request headers for third-party page fetches.

Why this exists (2026-08-25)
----------------------------
``EvidenceExtractor._extract_from_page`` and the PDF downloader built their
httpx clients with **no headers at all**, so every evidence fetch announced
itself as ``python-httpx/<version>``. Publishers reject that on sight.

Measured over the 82 non-200 URLs in the replay corpus:

===========================================  ==========  ==========
arm                                          HTTP 200    headline
===========================================  ==========  ==========
no headers (what we sent until now)               3/82        2/82
Tru8Bot self-identifying UA                      24/82       21/82
Chrome-impersonating UA (ingest.py's set)        25/82       23/82
===========================================  ==========  ==========

A blocked fetch is not merely a cosmetic problem: retrieval falls back to the
search-engine *snippet*, so the evidence TEXT degrades along with the title
(Google/Serper cut titles at ~54 chars, and 43% of results arrive pre-cut).

Why the honest UA rather than the Chrome disguise
-------------------------------------------------
One URL separates them (24 vs 25), and the honest agent is strictly better
where it matters most to an evidence product: **sec.gov serves us on the
identifying UA and 403s the Chrome one** — its policy requires callers to
declare themselves. Impersonation buys ~1% and costs us primary sources, so we
declare ourselves and stay blockable by name.

``ingest.py`` keeps its own Chrome-UA rotation for the *user-submitted* URL.
That path is not broken and is deliberately left alone; this module is for
third-party evidence fetches.
"""

from __future__ import annotations

from typing import Dict

# Self-identifying, with a contact URL. Keep the "Mozilla/5.0 (compatible; ...)"
# shape: a bare token trips naive UA filters that a compatible-string clears.
TRU8_USER_AGENT = "Mozilla/5.0 (compatible; Tru8Bot/1.0; +https://www.trueight.com/bot)"


def browser_headers(user_agent: str = TRU8_USER_AGENT) -> Dict[str, str]:
    """Headers for fetching a third-party HTML page.

    Mirrors the shape ``ingest.py`` already proved out, minus the Chrome
    identity. ``Accept-Encoding`` is left to httpx, which negotiates (and
    correctly decodes) brotli — the hand-set ``gzip, deflate`` in ingest.py is
    a workaround for the *requests* library's broken brotli support and would
    only cost us bandwidth here.
    """
    return {
        "User-Agent": user_agent,
        "Accept": (
            "text/html,application/xhtml+xml,application/xml;q=0.9,"
            "image/webp,*/*;q=0.8"
        ),
        "Accept-Language": "en-GB,en;q=0.9,en-US;q=0.8",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
    }


def binary_fetch_headers(user_agent: str = TRU8_USER_AGENT) -> Dict[str, str]:
    """Headers for fetching a PDF (or other non-HTML document).

    Same identity, but an ``Accept`` that asks for the document rather than a
    web page, and no ``Sec-Fetch-*`` navigation hints (this is not a navigation).
    """
    return {
        "User-Agent": user_agent,
        "Accept": "application/pdf,application/octet-stream;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-GB,en;q=0.9,en-US;q=0.8",
    }
