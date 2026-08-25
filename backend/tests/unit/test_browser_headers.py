"""Outbound identity for third-party page fetches (2026-08-25).

`evidence.py` and `pdf_evidence.py` built their httpx clients with NO headers,
so every fetch announced itself as "python-httpx/<version>". Measured over the
82 non-200 URLs in the replay corpus: 3/82 succeeded that way, 24/82 with a
self-identifying UA. A blocked fetch is not cosmetic — retrieval falls back to
the search snippet, degrading evidence TEXT as well as the title.
"""

from app.utils.browser_headers import (
    TRU8_USER_AGENT,
    binary_fetch_headers,
    browser_headers,
)


def test_we_identify_ourselves_and_do_not_impersonate_chrome():
    """Measured: honest UA 24/82 vs Chrome 25/82 — and sec.gov serves the
    honest one while 403ing Chrome. Impersonation buys ~1% and costs primary
    sources, so the UA must stay self-identifying and contactable."""
    ua = browser_headers()["User-Agent"]
    assert ua == TRU8_USER_AGENT
    assert "Tru8Bot" in ua
    assert "trueight.com" in ua
    assert "Chrome/" not in ua
    assert "Safari/" not in ua


def test_html_and_pdf_header_sets_are_populated():
    h = browser_headers()
    assert h["Accept"].startswith("text/html")
    assert "Accept-Language" in h

    b = binary_fetch_headers()
    assert "application/pdf" in b["Accept"]
    assert b["User-Agent"] == TRU8_USER_AGENT
    # a document fetch is not a navigation
    assert not any(k.startswith("Sec-Fetch") for k in b)


def test_evidence_and_pdf_fetches_actually_send_them():
    """Guards the seam, not just the helper: both clients must be constructed
    WITH headers. Passing no headers is what caused the defect."""
    import inspect

    from app.services import evidence as ev_mod
    from app.services import pdf_evidence as pdf_mod

    ev_src = inspect.getsource(ev_mod.EvidenceExtractor._extract_from_page)
    assert "headers=browser_headers()" in ev_src

    pdf_src = inspect.getsource(pdf_mod.PDFEvidenceExtractor.extract_evidence_from_pdf)
    assert "headers=binary_fetch_headers()" in pdf_src
