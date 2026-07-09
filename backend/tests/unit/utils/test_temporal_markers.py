"""Tests for the mechanical historical-marker lexicon (F-R2a/R2f, 2026-07-09).

The lexicon exists for one live failure shape (TRU-C051-3024): a claim that is
historical WITHOUT naming a year, so no DATE entity fires and every
recency-window default silently excludes the period literature.
"""

import pytest

from app.utils.temporal_markers import has_historical_marker


class TestHasHistoricalMarker:
    @pytest.mark.parametrize(
        "text",
        [
            # The live TRU-C051-3024 claim
            "Many doctors historically recommended a daily glass of red wine",
            "Historical records show physicians prescribed mercury",
            "Historical accounts describe the treatment",
            "Bloodletting was traditionally used to treat fever",
            "Doctors used to recommend smoking for stress",
            "In the past, radium was added to consumer products",
            "For centuries, willow bark treated pain",
            "For decades, margarine was considered healthier than butter",
            "Centuries ago, physicians balanced the four humours",
            "Decades ago, asbestos was a standard building material",
            "In ancient times, honey dressed wounds",
            "In Victorian times, arsenic coloured wallpaper",
            "Throughout history, midwives delivered most babies",
            "Leeches were once widely believed to cure disease",
            "It was once recommended that infants sleep face-down",
            "Formerly, the drug was sold over the counter",
            "In earlier times, barbers performed surgery",
        ],
    )
    def test_historical_phrasings_match(self, text):
        assert has_historical_marker(text) is True

    @pytest.mark.parametrize(
        "text",
        [
            # Present-tense / current-events claims must NOT match
            "Moderate alcohol consumption protects against heart disease",
            "The Bank of England raised interest rates today",
            "A historic victory for the underdogs",  # 'historic' alone excluded
            "The history department hired three lecturers",
            "This history-making launch happened yesterday",
            "Storm Bert caused flooding across Wales last week",
            "",
        ],
    )
    def test_non_historical_phrasings_do_not_match(self, text):
        assert has_historical_marker(text) is False

    def test_none_safe(self):
        assert has_historical_marker(None) is False

    def test_case_insensitive(self):
        assert has_historical_marker("HISTORICALLY, this was common") is True
