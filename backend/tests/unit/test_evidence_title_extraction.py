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


# ── Breadcrumb titles (2026-10-06, grader check S6) ─────────────────────────
# A University of Galway news page was titled "September - University of
# Galway" (its <title>; no og:title) instead of its headline.

GALWAY = (
    "<html><head><title>September  - University of Galway</title></head><body>"
    '<h1 class="pageTitle"><span><span class="hidden">September </span> '
    "University of Galway part of international mission to restore deep-sea "
    "coral reefs</span></h1></body></html>"
)


def test_breadcrumb_title_gives_way_to_the_visible_h1():
    assert (
        _extractor()._extract_title_from_html(GALWAY)
        == "University of Galway part of international mission to restore "
        "deep-sea coral reefs"
    )


def test_a_real_short_headline_survives():
    # is_shell_title would reject this (body under five words); the breadcrumb
    # rule must not.
    html = (
        "<html><head><title>Inflation hits 10% - ONS</title></head>"
        "<body><h1>Consumer price inflation, UK: September 2022</h1></body></html>"
    )
    assert _extractor()._extract_title_from_html(html) == "Inflation hits 10% - ONS"
    wiki = (
        "<html><head><title>Climate change - Wikipedia</title></head>"
        "<body><h1>Climate change</h1></body></html>"
    )
    assert _extractor()._extract_title_from_html(wiki) == "Climate change - Wikipedia"


def test_a_good_og_title_is_still_preferred():
    html = (
        "<html><head>"
        '<meta property="og:title" content="Reef restoration begins off Ireland">'
        "<title>September - University of Galway</title></head>"
        "<body><h1>Something else entirely in the header</h1></body></html>"
    )
    assert (
        _extractor()._extract_title_from_html(html)
        == "Reef restoration begins off Ireland"
    )


def test_h1_is_used_when_og_and_title_are_both_breadcrumbs():
    html = (
        "<html><head>"
        '<meta property="og:title" content="News | Example Council">'
        "<title>2026 - Example Council</title></head>"
        "<body><h1>Council approves new flood defences for the harbour</h1>"
        "</body></html>"
    )
    assert (
        _extractor()._extract_title_from_html(html)
        == "Council approves new flood defences for the harbour"
    )


def test_breadcrumb_kept_when_no_better_candidate_exists():
    # No <h1>, or an <h1> that is only the site name: the old title stands,
    # so nothing becomes title-less.
    bare = "<html><head><title>September - University of Galway</title></head></html>"
    assert (
        _extractor()._extract_title_from_html(bare)
        == "September - University of Galway"
    )
    logo = bare.replace("</html>", "<body><h1>University of Galway</h1></body></html>")
    assert (
        _extractor()._extract_title_from_html(logo)
        == "September - University of Galway"
    )


def test_a_bot_wall_h1_never_becomes_the_title():
    # Cloudflare's interstitial puts the hostname in an <h1>; the <title> is
    # junk, so the caller keeps the search title, exactly as before.
    html = (
        "<html><head><title>Just a moment...</title></head>"
        "<body><h1>www.example-news-site.com</h1></body></html>"
    )
    assert _extractor()._extract_title_from_html(html) is None


def test_wayback_recovery_shares_the_rule():
    from app.services.title_recovery import _headline_from_html

    assert _headline_from_html(GALWAY).startswith("University of Galway part of")


# ── Verifier findings (2026-10-06, MEDIUM-2/3) ──────────────────────────────


def _crumb(h1, title="News | Acme", url=None):
    html = f"<html><head><title>{title}</title></head><body><h1>{h1}</h1></body></html>"
    return _extractor()._extract_title_from_html(html, url)


def test_an_error_heading_is_not_promoted():
    assert _crumb("Page not found") == "News | Acme"
    assert _crumb("Sorry, the page you requested was not found") == "News | Acme"


def test_a_cookie_heading_is_not_promoted():
    assert _crumb("Cookies on this site", title="Media | Ofcom") == "Media | Ofcom"
    assert (
        _crumb("We use cookies on this website", title="Media | Ofcom")
        == "Media | Ofcom"
    )


def test_a_masthead_variant_of_the_site_name_is_not_promoted():
    # From the <title> suffix...
    assert (
        _crumb("The Example Gazette News Online UK", title="News | The Example Gazette")
        == "News | The Example Gazette"
    )
    # ...and from the host when the suffix is an abbreviation.
    assert (
        _crumb(
            "The Example Gazette Official Website Home",
            title="2026 - EG",
            url="https://www.examplegazette.co.uk/news/2026/x",
        )
        == "2026 - EG"
    )
    # A headline that merely NAMES its publisher is still a headline.
    assert (
        _crumb(
            "Example Gazette wins regional award for local reporting",
            title="News | The Example Gazette",
        )
        == "Example Gazette wins regional award for local reporting"
    )


def test_a_responsive_hidden_span_is_visible_text():
    h1 = (
        '<span class="hidden md:inline">Acme wins </span>'
        "contract for harbour bridge works"
    )
    assert _crumb(h1) == "Acme wins contract for harbour bridge works"


def test_aria_hidden_text_is_visible_text():
    h1 = 'Storm <span aria-hidden="true">Eunice</span> closes schools across Wales'
    assert _crumb(h1) == "Storm Eunice closes schools across Wales"


def test_a_short_h1_is_not_promoted():
    # Under five words an <h1> is as likely a section banner as a headline.
    assert _crumb("Latest from Acme Group") == "News | Acme"
