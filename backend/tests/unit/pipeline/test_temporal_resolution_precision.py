"""Regression guards: abstain when publication precision or tense is uncertain."""

import pytest

from app.utils.temporal_scope import Period, interval_ends, read_evidence_periods


@pytest.mark.parametrize(
    "publication", ["2025", "Published in 2025", "2025-99-12", "2025-02-30", "unknown"]
)
def test_incomplete_or_invalid_publication_cannot_invent_a_month(publication):
    assert not read_evidence_periods(
        "Prices rose in September.", publication, "engine"
    ).inferred
    assert not interval_ends("the year to September", publication, "engine")


@pytest.mark.parametrize(
    "publication", ["2025-10", "2025-10-22", "2025-10-22T10:00:00Z", "22 October 2025"]
)
def test_explicit_publication_month_can_resolve_retrospective_text(publication):
    assert read_evidence_periods(
        "Prices rose in September.", publication, "engine"
    ).inferred == {Period(2025, 9)}
    assert interval_ends("the year to September", publication, "engine") == {
        Period(2025, 9)
    }


@pytest.mark.parametrize(
    "text",
    [
        "The target for December is 2%.",
        "Prices will rise in December.",
        "Prices in December are expected to rise.",
        "The forecast for the year to December is 2%.",
        "Prices in the year to December are projected to rise.",
    ],
)
def test_prospective_month_does_not_become_previous_year(text):
    assert not read_evidence_periods(text, "2025-10-22", "page_metadata").inferred
    assert not interval_ends(text, "2025-10-22", "page_metadata")


def test_abstention_is_sentence_local_and_preserves_explicit_dates():
    text = "Prices rose in September. The forecast for December 2025 is 2%."
    reading = read_evidence_periods(text, "2025-10-22", "engine")
    assert reading.inferred == {Period(2025, 9)}
    assert reading.stated == {Period(2025, 12)}
    assert interval_ends(
        "Forecast for the year to December 2025", "2025-10-22", "engine"
    ) == {Period(2025, 12)}
