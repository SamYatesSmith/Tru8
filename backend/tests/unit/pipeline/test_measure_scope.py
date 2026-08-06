"""Interval-measure mismatch — the third defect in production check 757f02c2.

A rate of change is identified by the interval's END, not by the months it happens
to mention:

    element : "the twelve months to September 2024"        end = 2024-09
    evidence: "between September 2024 and September 2025"   end = 2025-09

Both name September 2024, so the F1 period rule correctly declines — one matching
mention means the source is talking about our period. But the evidence measures a
DIFFERENT twelve months, and a UK source making the same period-pair error would
still have been counted as a challenge.

Strings here are the ones production actually returned.
"""

from datetime import datetime

import pytest

from app.utils.temporal_scope import (
    Period,
    element_interval_end,
    interval_ends,
    is_measure_mismatch,
    is_out_of_period,
)

ELEMENT = (
    "The rate of consumer price inflation in the UK for the twelve months to "
    "September 2024 was 1.7 percent."
)
CSO = (
    "The Consumer Price Index (CPI) rose by 2.7% between September 2024 and "
    "September 2025, up from an annual increase of 2.0% in the 12 months to "
    "August 2025."
)
ONS = (
    "The Consumer Prices Index (CPI) rose by 1.7% in the 12 months to "
    "September 2024, down from 2.2% in August."
)
SEPT_2024 = Period(2024, 9)


# ---------------------------------------------------------------------------
# Why the period rule cannot reach this
# ---------------------------------------------------------------------------


def test_the_period_rule_correctly_declines_to_act():
    """Pins the gap this gate exists to fill.

    If this ever starts returning True, the period rule has begun over-firing on
    sources that genuinely mention our period, and this gate is redundant.
    """
    assert is_out_of_period(SEPT_2024, CSO) is False


# ---------------------------------------------------------------------------
# Reading interval ends
# ---------------------------------------------------------------------------


def test_the_element_pins_its_interval_end():
    assert element_interval_end(ELEMENT) == SEPT_2024


@pytest.mark.parametrize(
    "text,expected",
    [
        ("in the 12 months to September 2024", {Period(2024, 9)}),
        ("in the twelve months to September 2024", {Period(2024, 9)}),
        ("between September 2024 and September 2025", {Period(2025, 9)}),
        ("from September 2023 to September 2024", {Period(2024, 9)}),
        ("the annual rate to August 2025", {Period(2025, 8)}),
    ],
)
def test_interval_constructs_yield_their_end(text, expected):
    assert interval_ends(text) == expected


def test_a_clause_boundary_stops_the_end_leaking():
    """ "…September 2025, up from … August 2025" is two intervals, not one.

    Without the punctuation bound the first interval's end would swallow the
    second figure's period and the comparison would silently widen.
    """
    assert interval_ends(CSO) == {Period(2025, 9), Period(2025, 8)}


def test_text_with_no_interval_yields_nothing():
    """Which disarms the gate — the safe direction."""
    assert interval_ends("Inflation is still above the 2% target.") == set()
    assert interval_ends("CPI was 1.7% in September 2024.") == set()
    assert interval_ends(None) == set()


def test_an_element_expressing_two_intervals_is_not_pinned():
    """A range of measures is not one measure; scoping against it would be wrong."""
    assert (
        element_interval_end(
            "Inflation in the 12 months to June 2024 and the 12 months to June 2025."
        )
        is None
    )


def test_an_element_with_no_interval_is_not_pinned():
    assert element_interval_end("The UK Online Safety Act exists.") is None
    assert element_interval_end("CPI was 1.7% in September 2024.") is None


# ---------------------------------------------------------------------------
# The gate
# ---------------------------------------------------------------------------


def test_the_production_failure_is_a_measure_mismatch():
    assert is_measure_mismatch(SEPT_2024, CSO) is True


def test_the_matching_measure_is_left_alone():
    """The ONS primary measures exactly our interval and must survive."""
    assert is_measure_mismatch(SEPT_2024, ONS) is False


def test_evidence_with_no_interval_is_left_alone():
    """No measure to compare, so no judgement to make."""
    assert (
        is_measure_mismatch(SEPT_2024, "Inflation remains above the 2% target.")
        is False
    )


def test_a_bare_month_interval_resolves_against_publication():
    """ "in the year to September" is ordinary phrasing, not an edge case.

    The interval connective already supplies the temporal context, so the month
    needs no preposition of its own — only a capital.
    """
    text = (
        "UK inflation fell unexpectedly to 1.7% in the year to September, the "
        "lowest rate in three-and-a-half years."
    )
    assert interval_ends(text, datetime(2024, 10, 18), "page_metadata") == {SEPT_2024}
    assert (
        is_measure_mismatch(SEPT_2024, text, datetime(2024, 10, 18), "page_metadata")
        is False
    )


def test_a_bare_month_interval_on_the_WRONG_year_is_caught():
    text = "CPI rose 3.8% in the year to September."
    assert (
        is_measure_mismatch(SEPT_2024, text, datetime(2025, 10, 22), "engine") is True
    )


def test_untrusted_provenance_resolves_no_bare_month_interval():
    """Same allowlist as the period rule: url_inferred_suspect earns nothing."""
    text = "CPI rose 3.8% in the year to September."
    assert interval_ends(text, datetime(2025, 10, 22), "url_inferred_suspect") == set()
    assert (
        is_measure_mismatch(
            SEPT_2024, text, datetime(2025, 10, 22), "url_inferred_suspect"
        )
        is False
    )


# ---------------------------------------------------------------------------
# The words that are not months
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        # "to march" behind an interval-shaped phrase — capitalisation is the
        # only thing standing between this and a false period.
        "Protesters continued to march through the capital.",
        "The union voted to march in protest.",
        # "annual … to <not a month>" must not invent an interval.
        "the annual report to shareholders",
        "a 12 month contract to supply parts",
    ],
)
def test_verbs_and_non_periods_do_not_become_interval_ends(text):
    assert interval_ends(text, datetime(2025, 10, 1), "engine") == set()


@pytest.mark.parametrize(
    "text",
    [
        # These DO satisfy the interval prefix and DO put a month-word after
        # "to", so only capitalisation stands between them and a false interval
        # end. The cases above are rejected earlier, by the prefix, so they do
        # not exercise this guard at all — a mutation removing it survived them.
        "the annual attempt to march on the capital",
        "an annual campaign to march through town",
    ],
)
def test_a_lowercase_month_after_an_interval_connective_is_not_an_end(text):
    assert interval_ends(text, datetime(2025, 10, 1), "engine") == set()


def test_a_month_range_resolves_to_its_end_not_its_start():
    """ "from January to December" published October means December of LAST year."""
    assert interval_ends(
        "spending from January to December", datetime(2025, 10, 1), "engine"
    ) == {Period(2024, 12)}


# ---------------------------------------------------------------------------
# The wired seam — and the case NEITHER other gate can reach
# ---------------------------------------------------------------------------


def _parse_one(evidence, relationship="challenges", jurisdiction="UK"):
    """Drive one ref through the real parser and hand back the element."""
    from app.pipeline.claim_map_analyzer import ClaimMapAnalyzer

    claim_map = {
        "claim_id": "0",
        "normalised_claim": "UK CPI inflation was 1.7% in the twelve months to September 2024.",
        "elements": [
            {
                "element_id": "e1",
                "description": ELEMENT,
                "evidence_refs": [],
                "state": None,
            }
        ],
        "metadata": {"jurisdiction": jurisdiction},
    }
    response = {
        "elements": [
            {
                "element_id": "e1",
                "state": "disputed",
                "evidence_refs": [
                    {
                        "evidence_id": evidence[0]["evidence_id"],
                        "relationship": relationship,
                        "reasoning": "…",
                    }
                ],
            }
        ]
    }
    ClaimMapAnalyzer()._parse_mapping_response(response, claim_map, evidence)
    return claim_map["elements"][0]


UK_WRONG_MEASURE = [
    {
        "evidence_id": "ev-uk-wrong-measure",
        "url": "https://www.ons.gov.uk/economy/inflationandpriceindices/bulletins/consumerpriceinflation/september2025",
        "title": "Consumer price inflation, UK: September 2025",
        "snippet": (
            "The Consumer Prices Index rose by 3.8% between September 2024 and "
            "September 2025."
        ),
        "tier": "primary",
        "evidence_type": "data",
    }
]


def _rel(elem):
    ref = elem["evidence_refs"][0]
    return getattr(ref["relationship"], "value", ref["relationship"])


def test_a_UK_source_with_the_wrong_measure_is_scoped():
    """The reason this gate exists in ADDITION to the jurisdiction gate.

    The jurisdiction gate removed the Irish item for being Irish. A UK source
    making the SAME period-pair error would still have been counted: ons.gov.uk is
    our own country, and the text names September 2024, so neither the jurisdiction
    gate nor the period rule can act. Only the interval end separates them.
    """
    elem = _parse_one(UK_WRONG_MEASURE)

    assert _rel(elem) == "context"
    receipt = elem["basis"]["measure_scope"]
    assert receipt["element_interval_end"] == "2024-09"
    assert receipt["scoped"][0]["evidence_interval_ends"] == ["2025-09"]
    assert receipt["scoped"][0]["was"] == "challenges"
    # Not the jurisdiction gate — this source is our own country.
    assert "jurisdiction_scope" not in elem["basis"]


def test_the_measure_gate_is_symmetric():
    """A wrong-measure SUPPORT is scoped just as readily, or the gate is a dial."""
    elem = _parse_one(UK_WRONG_MEASURE, relationship="supports")

    assert _rel(elem) == "context"
    assert elem["basis"]["measure_scope"]["scoped"][0]["was"] == "supports"


def test_the_flag_rolls_the_measure_gate_back_alone(monkeypatch):
    from app.core import config

    monkeypatch.setattr(config.settings, "ENABLE_MEASURE_SCOPE_GATE", False)
    elem = _parse_one(UK_WRONG_MEASURE)

    assert _rel(elem) == "challenges"
    assert "measure_scope" not in elem["basis"]
