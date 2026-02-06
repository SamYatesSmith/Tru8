"""Tests for _get_recency_score() — dynamic year-based recency scoring.

All tests patch datetime.now to return 2026-06-15 UTC for determinism.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock


# We need a minimal instance of EvidenceRetriever to call _get_recency_score.
# Import the class and create a lightweight instance.
from app.pipeline.retrieve import EvidenceRetriever


@pytest.fixture
def retriever():
    """Create a minimal EvidenceRetriever for testing _get_recency_score."""
    # EvidenceRetriever.__init__ may require args; use object.__new__ to skip __init__
    obj = object.__new__(EvidenceRetriever)
    return obj


# Fixed "now" for all tests: 2026-06-15 UTC
FIXED_NOW = datetime(2026, 6, 15, tzinfo=timezone.utc)


def _patch_now():
    """Return a patch that makes datetime.now(tz) return FIXED_NOW."""
    return patch("app.pipeline.retrieve.datetime", wraps=datetime,
                 **{"now": MagicMock(return_value=FIXED_NOW)})


class TestRecencyScore:

    def test_current_year_2026(self, retriever):
        with _patch_now():
            assert retriever._get_recency_score("2026-03-15") == 1.0

    def test_last_year_2025(self, retriever):
        with _patch_now():
            assert retriever._get_recency_score("2025-06-01") == 1.0

    def test_two_years_ago_2024(self, retriever):
        with _patch_now():
            assert retriever._get_recency_score("2024-01-15") == 0.95

    def test_three_years_ago_2023(self, retriever):
        with _patch_now():
            assert retriever._get_recency_score("2023-11-01") == 0.90

    def test_four_years_ago_2022(self, retriever):
        with _patch_now():
            assert retriever._get_recency_score("2022-05-20") == 0.85

    def test_old_2020(self, retriever):
        with _patch_now():
            assert retriever._get_recency_score("2020-01-01") == 0.80

    def test_none_date(self, retriever):
        assert retriever._get_recency_score(None) == 0.80

    def test_empty_string(self, retriever):
        assert retriever._get_recency_score("") == 0.80

    def test_invalid_string(self, retriever):
        assert retriever._get_recency_score("no date here") == 0.80

    def test_future_date_2027(self, retriever):
        with _patch_now():
            assert retriever._get_recency_score("2027-01-01") == 1.0

    def test_iso_format(self, retriever):
        with _patch_now():
            assert retriever._get_recency_score("2026-03-15") == 1.0

    def test_slash_format(self, retriever):
        with _patch_now():
            assert retriever._get_recency_score("2026/03/15") == 1.0

    def test_human_format(self, retriever):
        with _patch_now():
            assert retriever._get_recency_score("Jan 15, 2025") == 1.0

    def test_bare_year(self, retriever):
        with _patch_now():
            assert retriever._get_recency_score("2023") == 0.90
