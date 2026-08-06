"""Temporal-scope tagger — the mechanism behind the F1 fix.

Pinned to the production failure it exists to prevent (check `618efbc4`):
"UK CPI inflation dropped under 2 percent in September 2024" is TRUE — ONS
reports 1.7% — and the element came back `disputed` on six figures from other
periods. The mapping prompt already forbade exactly that; the evidence payload
carried no dates, so the instruction was unaskable.

These tests cover the tagger alone. The wiring is guarded separately.
"""

from datetime import datetime

import pytest

from app.utils.temporal_scope import (
    Period,
    element_period,
    extract_periods,
    is_out_of_period,
    read_evidence_periods,
    resolve_bare_month,
)

SEPT_2024 = Period(2024, 9)

# The live miss of 2026-08-06 (check b0a720f8), verbatim in shape: a report on
# September 2025 used to challenge a September 2024 element.
LIVE_MISS_TITLE = "UK September-25 CPI Inflation Report"
LIVE_MISS_SNIPPET = "CPI increased by 3.8% YoY in September, ONS said."
LIVE_MISS_PUBLISHED = datetime(2025, 10, 22)


# ---------------------------------------------------------------------------
# Reading periods out of text
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text,expected",
    [
        ("September 2024", {Period(2024, 9)}),
        ("Sept 2024", {Period(2024, 9)}),
        ("Sep. 2024", {Period(2024, 9)}),
        ("26 October 2023", {Period(2023, 10)}),
        ("October 26, 2023", {Period(2023, 10)}),
        ("2024-09", {Period(2024, 9)}),
        ("2024-09-16", {Period(2024, 9)}),
        ("in 2024", {Period(2024, None)}),
    ],
)
def test_reads_periods_at_their_stated_granularity(text, expected):
    assert extract_periods(text) == expected


def test_a_month_year_does_not_also_read_as_a_bare_year():
    """Otherwise every month-level mention would also match itself as a year.

    "September 2024" is one period, not two, and treating it as also (2024,
    None) would make an annual figure look like a match for a monthly element.
    """
    assert extract_periods("CPI rose by 1.7% in the 12 months to September 2024") == {
        Period(2024, 9)
    }


def test_numbers_that_are_not_years_are_not_years():
    """The corpus is full of figures. 1.7, 2%, 12 months must not read as dates."""
    assert (
        extract_periods("inflation was 1.7% against a 2% target over 12 months")
        == set()
    )


def test_no_text_yields_no_periods():
    assert extract_periods(None) == set()
    assert extract_periods("") == set()


# ---------------------------------------------------------------------------
# What an element pins
# ---------------------------------------------------------------------------


def test_element_pinned_to_one_month_is_recognised():
    described = "The measured consumer price index inflation rate in the UK in September 2024 was less than 2 percent."
    assert element_period(described) == SEPT_2024


def test_element_spanning_two_periods_is_not_pinned():
    """A range is not a point — scoping against it would be wrong.

    Returning None here means the gate does not fire, which is the safe
    direction.
    """
    assert element_period("Emissions fell between March 2020 and June 2021.") is None


def test_element_with_no_month_is_not_pinned():
    assert element_period("The UK Online Safety Act exists.") is None
    assert element_period("Something happened in 2024.") is None


# ---------------------------------------------------------------------------
# The gate itself — the six items from check 618efbc4
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "evidence_text",
    [
        "UK inflation eased to 2.6% in June 2025.",
        "The inflation rate dropped to 2.0% in May 2024.",
    ],
)
def test_other_months_are_out_of_period(evidence_text):
    assert is_out_of_period(SEPT_2024, evidence_text) is True


def test_an_annual_figure_does_not_bear_on_a_monthly_element():
    """ "3.27% for 2024" challenged a September figure in production.

    A bare year is not a match for a month-level element: an annual average
    neither establishes nor refutes a single month.
    """
    assert is_out_of_period(SEPT_2024, "The inflation rate for 2024 was 3.27%.") is True


def test_matching_period_is_left_alone():
    ons = "The Consumer Prices Index (CPI) rose by 1.7% in the 12 months to September 2024."
    assert is_out_of_period(SEPT_2024, ons) is False


def test_undated_evidence_is_left_alone():
    """The deliberate limit of this fix.

    "still well above the Bank of England's 2% target" carries no period, so it
    keeps whatever the mapper labelled it. Inferring a period from silence is
    guessing, and over-firing hides genuine disputes.
    """
    assert (
        is_out_of_period(SEPT_2024, "Inflation is still well above the 2% target.")
        is False
    )


def test_evidence_mentioning_the_element_period_among_others_is_left_alone():
    """One matching mention is enough — the source is talking about our period."""
    text = "Inflation was 2.0% in May 2024 before falling to 1.7% in September 2024."
    assert is_out_of_period(SEPT_2024, text) is False


# ---------------------------------------------------------------------------
# 2026-08-06, miss 1 — delimited and two-digit years (purely lexical)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text,expected",
    [
        ("September-25", {Period(2025, 9)}),
        ("Sep-25", {Period(2025, 9)}),
        ("Sept/25", {Period(2025, 9)}),
        # The separator used to have to be whitespace, so these were missed too.
        ("September-2025", {Period(2025, 9)}),
        ("Sep/2025", {Period(2025, 9)}),
        ("September - 2025", {Period(2025, 9)}),
        # Pre-2000 two-digit years land in the right century.
        ("Jan-99", {Period(1999, 1)}),
    ],
)
def test_delimited_and_two_digit_years_are_read(text, expected):
    assert extract_periods(text) == expected


def test_the_live_miss_title_now_reads_as_september_2025():
    """The title alone is enough — no inference needed for this half."""
    assert extract_periods(LIVE_MISS_TITLE) == {Period(2025, 9)}
    assert is_out_of_period(SEPT_2024, LIVE_MISS_TITLE) is True


@pytest.mark.parametrize(
    "text",
    [
        "The report was published on September 25.",
        "Figures were released September 25 and revised later.",
    ],
)
def test_a_bare_space_before_two_digits_is_a_day_not_a_year(text):
    """ "September 25" is the 25th far more often than it is 2025.

    Reading a day-of-month as a year would place the item in the wrong period
    and scope out evidence that genuinely bears on the element — the over-firing
    direction, which hides real disputes. Hence delimiter-strict.
    """
    assert extract_periods(text) == set()


def test_a_two_digit_year_does_not_eat_a_four_digit_one():
    """ "September-2025" must be 2025, never 20 expanded to 2020."""
    assert extract_periods("September-2025") == {Period(2025, 9)}


# ---------------------------------------------------------------------------
# 2026-08-06, miss 2 — a bare month placed by its publication date
# ---------------------------------------------------------------------------


def test_a_bare_month_resolves_against_the_publication_date():
    """A report published 22 Oct 2025 saying "in September" means Sept 2025."""
    reading = read_evidence_periods(
        LIVE_MISS_SNIPPET, LIVE_MISS_PUBLISHED, "page_metadata"
    )

    assert reading.stated == set()
    assert reading.inferred == {Period(2025, 9)}
    assert (
        is_out_of_period(SEPT_2024, LIVE_MISS_SNIPPET, LIVE_MISS_PUBLISHED, "engine")
        is True
    )


def test_a_month_later_than_the_publication_month_is_the_previous_year():
    """December named in an October report is last December, not next one."""
    assert resolve_bare_month(12, datetime(2025, 10, 22)) == Period(2024, 12)
    assert resolve_bare_month(9, datetime(2025, 10, 22)) == Period(2025, 9)


def test_a_bare_month_resolving_ONTO_the_element_period_is_left_alone():
    """The guard against the new half over-firing.

    Same undated snippet, published a year earlier — now it IS about September
    2024 and must keep whatever the mapper labelled it.
    """
    assert (
        is_out_of_period(
            SEPT_2024,
            "CPI increased by 1.7% YoY in September, ONS said.",
            datetime(2024, 10, 16),
            "page_metadata",
        )
        is False
    )


@pytest.mark.parametrize("basis", ["url_inferred_suspect", None, "", "guessed"])
def test_untrusted_provenance_does_not_resolve_anything(basis):
    """Trust is opt-in, and `url_inferred_suspect` is refused by name.

    F2 classified that basis as probably the host's upload path rather than a
    publication date. Inferring a period from it would place the item in a year
    nobody asserted.
    """
    reading = read_evidence_periods(LIVE_MISS_SNIPPET, LIVE_MISS_PUBLISHED, basis)

    assert reading.inferred == set()
    assert (
        is_out_of_period(SEPT_2024, LIVE_MISS_SNIPPET, LIVE_MISS_PUBLISHED, basis)
        is False
    )


def test_no_publication_date_resolves_nothing():
    """Trusted basis but no usable date is still no inference."""
    assert read_evidence_periods(LIVE_MISS_SNIPPET, None, "engine").inferred == set()
    assert (
        read_evidence_periods(LIVE_MISS_SNIPPET, "not a date", "engine").inferred
        == set()
    )


def test_withholding_the_date_reduces_to_the_shipped_behaviour():
    """How the rollback works: the caller simply stops passing the date."""
    assert read_evidence_periods(LIVE_MISS_SNIPPET).inferred == set()
    assert is_out_of_period(SEPT_2024, LIVE_MISS_SNIPPET) is False


# ---------------------------------------------------------------------------
# The words that are not months
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        # "may" the modal — by far the biggest collision in ordinary prose.
        "Analysts warn the rate may rise again before the year ends.",
        "Tariffs may increase inflation in the months ahead.",
        # "march" the verb, reached via a preposition — the case that makes
        # capitalisation necessary as well as the preposition.
        "Protesters continued to march through the capital.",
        "The union voted to march in protest at the figures.",
    ],
)
def test_verbs_and_modals_are_not_read_as_months(text):
    """Over-firing here would scope out genuine evidence on a false period."""
    reading = read_evidence_periods(text, LIVE_MISS_PUBLISHED, "page_metadata")

    assert reading.inferred == set()
    assert (
        is_out_of_period(SEPT_2024, text, LIVE_MISS_PUBLISHED, "page_metadata") is False
    )


def test_a_month_with_no_preposition_is_not_resolved():
    """Deliberately conservative: failing to fire is the safe direction."""
    reading = read_evidence_periods(
        "September figures showed a rise.", LIVE_MISS_PUBLISHED, "page_metadata"
    )

    assert reading.inferred == set()


def test_a_capitalised_month_behind_a_preposition_still_resolves():
    """The guards must not be so tight that the real phrasing stops working."""
    for text in (
        "Prices rose in May, the ONS said.",
        "The rate held steady during March.",
        "Inflation eased in the 12 months to August.",
    ):
        reading = read_evidence_periods(text, datetime(2025, 10, 22), "engine")
        assert len(reading.inferred) == 1, text
