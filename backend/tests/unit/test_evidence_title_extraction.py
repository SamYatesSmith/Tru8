"""Unit tests for EvidenceExtractor._extract_title_from_html (2026-07-01).

The evidence fetcher already downloads + parses every page; this prefers the
page's own complete title over the search provider's ellipsis-truncated one.
"""

from app.services.evidence import EvidenceExtractor


def _extractor() -> EvidenceExtractor:
    # Skip __init__ (which builds a SearchService); the method under test only
    # needs the class-level junk-marker list + BeautifulSoup.
    return EvidenceExtractor.__new__(EvidenceExtractor)


def test_prefers_og_title_over_document_title():
    html = """
    <html><head>
      <meta property="og:title"
            content="Fault-mediated magma propagation and triggered seismicity at Kilauea" />
      <title>Fault-mediated magma... - Nature</title>
    </head><body></body></html>
    """
    assert (
        _extractor()._extract_title_from_html(html)
        == "Fault-mediated magma propagation and triggered seismicity at Kilauea"
    )


def test_twitter_title_when_no_og():
    html = (
        "<html><head>"
        '<meta name="twitter:title" content="Volcano-tectonic earthquake focal mechanisms">'
        "<title>x - Site</title></head></html>"
    )
    assert (
        _extractor()._extract_title_from_html(html)
        == "Volcano-tectonic earthquake focal mechanisms"
    )


def test_falls_back_to_document_title():
    html = "<html><head><title>Seismological observations of the 2011 Nabro eruption</title></head></html>"
    assert (
        _extractor()._extract_title_from_html(html)
        == "Seismological observations of the 2011 Nabro eruption"
    )


def test_collapses_whitespace():
    html = "<html><head><title>Long-period   microseismicity\n  reveals cryptic events</title></head></html>"
    assert (
        _extractor()._extract_title_from_html(html)
        == "Long-period microseismicity reveals cryptic events"
    )


def test_rejects_bot_wall_titles():
    for junk in (
        "Just a moment...",
        "Access Denied",
        "Attention Required! | Cloudflare",
        "Please enable JavaScript to continue",
        # F7c: Reddit's network-verification interstitial + generic wait screens.
        "Reddit - Please wait for verification",
        "Please wait...",
        "Wait for verification",
    ):
        html = f"<html><head><title>{junk}</title></head></html>"
        assert _extractor()._extract_title_from_html(html) is None, junk


def test_rejects_too_short_and_missing():
    assert (
        _extractor()._extract_title_from_html(
            "<html><head><title>Hi</title></head></html>"
        )
        is None
    )
    assert (
        _extractor()._extract_title_from_html(
            "<html><head></head><body>x</body></html>"
        )
        is None
    )
    assert _extractor()._extract_title_from_html("") is None
