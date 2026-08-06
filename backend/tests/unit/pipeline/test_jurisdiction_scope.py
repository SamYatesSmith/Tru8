"""Jurisdiction-scope tagger — the mechanism, pinned to the production failure.

Check `757f02c2` returned a TRUE, ONS-verbatim claim ("UK consumer price inflation
fell to 1.7 percent in the twelve months to September 2024") as `disputed`. Its
sole `challenges` item was the IRISH CSO. The decisive detail, and the reason this
cannot be a prompt rule: the snippet names neither Ireland nor the UK, so only the
domain carries the mismatch.

These tests cover the tagger alone. The wiring is guarded separately.
"""

import pytest

from app.utils.jurisdiction_scope import (
    claim_target_country,
    evidence_country,
    is_out_of_jurisdiction,
    mentions_jurisdiction,
)

# The live failure, verbatim in shape.
CSO_URL = "https://www.cso.ie/en/releasesandpublications/ep/p-cpi/consumerpriceindexseptember2025/"
CSO_TEXT = (
    "Consumer Price Index September 2025 - Central Statistics Office "
    "The Consumer Price Index (CPI) rose by 2.7% between September 2024 and "
    "September 2025, up from an annual increase of 2.0% in the 12 months to "
    "August 2025."
)


# ---------------------------------------------------------------------------
# Which claims are in scope at all
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("value,expected", [("UK", "UK"), ("US", "US"), ("uk", "UK")])
def test_country_level_jurisdictions_are_recognised(value, expected):
    assert claim_target_country(value) == expected


@pytest.mark.parametrize("value", ["EU", "Global", None, "", "ZZ", "unknown"])
def test_non_country_jurisdictions_never_arm_the_gate(value):
    """EU and Global are excluded on purpose.

    A member state's figures are partly in scope for an EU-wide claim — that is a
    composition problem, not a jurisdiction mismatch — and any country's data can
    be an instance of a global claim.
    """
    assert claim_target_country(value) is None


# ---------------------------------------------------------------------------
# Reading a country off a domain
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "url,expected",
    [
        (CSO_URL, "IE"),
        ("https://www.ons.gov.uk/economy/inflationandpriceindices", "UK"),
        ("https://www.bls.gov/opub/ted/2024/consumer-prices.htm", "US"),
        ("https://www.destatis.de/EN/Home/_node.html", "DE"),
        ("https://www.stats.govt.nz/indicators/cpi", "NZ"),
        ("https://www.abs.gov.au/statistics/cpi", "AU"),
        # A bare .gov TLD is US federal or state.
        ("https://www.sec.gov/edgar", "US"),
        # gov.uk ends in its own ccTLD and must NOT fall through to the .gov rule.
        ("https://www.gov.uk/government/statistics", "UK"),
    ],
)
def test_official_domains_resolve_to_their_country(url, expected):
    assert evidence_country(url) == expected


@pytest.mark.parametrize(
    "url",
    [
        # Foreign PRESS is not a jurisdiction mismatch — an Irish paper reporting
        # on UK inflation is legitimate evidence.
        "https://www.irishtimes.com/business/2024/10/16/uk-inflation-falls/",
        "https://www.bbc.com/news/articles/c17rgd8e9gjo",
        # Supranational bodies report ON many countries including ours.
        "https://data.worldbank.org/indicator/FP.CPI.TOTL.ZG?locations=GBR",
        "https://www.imf.org/en/Publications/WEO",
        "https://ec.europa.eu/eurostat/databrowser/view/prc_hicp_manr",
        "https://www.oecd.org/economy/",
        # Ordinary web sources.
        "https://tradingeconomics.com/united-kingdom/inflation-cpi",
        "https://en.wikipedia.org/wiki/Inflation",
        None,
        "",
        "not-a-url",
    ],
)
def test_press_supranational_and_unknown_hosts_yield_no_country(url):
    """None means the gate leaves the item alone — the safe direction."""
    assert evidence_country(url) is None


# ---------------------------------------------------------------------------
# The gate
# ---------------------------------------------------------------------------


def test_the_production_failure_is_now_out_of_jurisdiction():
    """The whole point: Irish CPI cannot challenge a UK claim."""
    assert is_out_of_jurisdiction("UK", CSO_URL, CSO_TEXT) is True


def test_our_own_official_source_is_never_scoped():
    ons = "The Consumer Prices Index rose by 1.7% in the 12 months to September 2024."
    assert (
        is_out_of_jurisdiction(
            "UK",
            "https://www.ons.gov.uk/economy/inflationandpriceindices/bulletins/consumerpriceinflation/september2024",
            ons,
        )
        is False
    )


def test_foreign_press_about_our_jurisdiction_is_never_scoped():
    assert (
        is_out_of_jurisdiction(
            "UK",
            "https://www.irishtimes.com/business/uk-inflation-falls/",
            "UK inflation fell to 1.7% in September.",
        )
        is False
    )


def test_a_foreign_office_publishing_about_us_is_left_alone():
    """The mention guard.

    A foreign statistics office running an international comparison that includes
    the United Kingdom IS talking about the United Kingdom. Mirrors F1's "one
    matching mention is enough".
    """
    assert (
        is_out_of_jurisdiction(
            "UK",
            "https://www.bls.gov/opub/ted/international-comparison.htm",
            "Consumer prices in the United Kingdom rose 1.7% over the year.",
        )
        is False
    )


def test_the_gate_is_symmetric_on_direction():
    """Direction is not an input, which is what stops this being a sycophancy dial.

    The tagger is a property of (jurisdiction, url, text) alone — the caller
    applies it to `supports` and `challenges` identically. Pinned here so a future
    change that adds a direction parameter has to break a test first.
    """
    import inspect

    params = list(inspect.signature(is_out_of_jurisdiction).parameters)
    assert params == ["target_country", "url", "evidence_text"]


@pytest.mark.parametrize(
    "text,expected",
    [
        ("Inflation in Britain rose", True),
        ("UK CPI was 1.7%", True),
        ("figures for England and Wales", True),
        ("Prices rose in Dublin", False),
        ("The Consumer Price Index rose by 2.7%", False),
    ],
)
def test_uk_mention_detection(text, expected):
    assert mentions_jurisdiction(text, "UK") is expected


def test_the_us_pronoun_is_not_a_country_mention():
    """A case-insensitive "us" would fire on ordinary prose and suppress the gate
    everywhere — safe, but useless."""
    assert mentions_jurisdiction("this affects us all", "US") is False
    assert mentions_jurisdiction("US consumer prices rose", "US") is True
    assert mentions_jurisdiction("in the United States, prices rose", "US") is True
