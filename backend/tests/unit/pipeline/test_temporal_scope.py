"""Temporal-scope tagger — the mechanism behind the F1 fix.

Pinned to the production failure it exists to prevent (check `618efbc4`):
"UK CPI inflation dropped under 2 percent in September 2024" is TRUE — ONS
reports 1.7% — and the element came back `disputed` on six figures from other
periods. The mapping prompt already forbade exactly that; the evidence payload
carried no dates, so the instruction was unaskable.

These tests cover the tagger alone. The wiring is guarded separately.
"""

import pytest

from app.utils.temporal_scope import (
    Period,
    element_period,
    extract_periods,
    is_out_of_period,
)

SEPT_2024 = Period(2024, 9)


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
