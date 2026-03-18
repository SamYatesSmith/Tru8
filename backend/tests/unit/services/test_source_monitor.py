"""
Tests for SourceMonitor service.

Tests cover domain extraction, frequency tracking, trending queries,
and the review workflow.
"""

import logging
from unittest.mock import MagicMock, patch

import pytest

from app.services.source_monitor import SourceMonitor


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_unknown_source(**overrides):
    """Return a lightweight mock that behaves like an UnknownSource row."""
    defaults = dict(
        id="fake-id",
        domain="example.com",
        full_url="https://www.example.com/page",
        claim_topic=None,
        evidence_title=None,
        evidence_snippet=None,
        frequency=1,
        reviewed=False,
        assigned_tier=None,
        review_notes=None,
        added_to_credibility_list=False,
        has_https=False,
        has_author_byline=None,
        has_primary_sources=None,
    )
    defaults.update(overrides)
    obj = MagicMock()
    for k, v in defaults.items():
        setattr(obj, k, v)
    return obj


def _mock_session(existing_row=None):
    """Return a MagicMock session whose exec().first() returns *existing_row*."""
    session = MagicMock()
    result = MagicMock()
    result.first.return_value = existing_row
    result.all.return_value = [existing_row] if existing_row else []
    result.one.return_value = 0
    session.exec.return_value = result
    return session


# ===========================================================================
# TestLogUnknownSource
# ===========================================================================


class TestLogUnknownSource:
    """Tests for SourceMonitor.log_unknown_source."""

    @patch("app.services.source_monitor.select")
    def test_extracts_domain_from_url(self, mock_select):
        """Domain is extracted from a full URL via tldextract."""
        session = _mock_session(existing_row=None)
        monitor = SourceMonitor(session)

        monitor.log_unknown_source(url="https://www.example.com/page")

        # session.add should have been called with an UnknownSource whose domain == "example.com"
        session.add.assert_called_once()
        added_obj = session.add.call_args[0][0]
        assert added_obj.domain == "example.com"
        session.commit.assert_called_once()

    def test_increments_frequency_on_duplicate(self):
        """Logging the same domain twice increments the existing row's frequency."""
        existing = _make_unknown_source(frequency=1)
        session = _mock_session(existing_row=existing)
        monitor = SourceMonitor(session)

        monitor.log_unknown_source(url="https://www.example.com/other-page")

        assert existing.frequency == 2
        session.commit.assert_called_once()
        # Should NOT add a new object — it updates in-place
        session.add.assert_not_called()

    @patch("app.services.source_monitor.select")
    def test_truncates_long_snippet(self, mock_select):
        """Evidence snippets longer than 500 characters are truncated."""
        session = _mock_session(existing_row=None)
        monitor = SourceMonitor(session)
        long_snippet = "x" * 1000

        monitor.log_unknown_source(
            url="https://longsnippet.com/article",
            evidence_snippet=long_snippet,
        )

        added_obj = session.add.call_args[0][0]
        assert len(added_obj.evidence_snippet) == 500

    def test_handles_invalid_url(self, caplog):
        """An invalid URL (no extractable domain) logs a warning and does not crash."""
        session = _mock_session(existing_row=None)
        monitor = SourceMonitor(session)

        with caplog.at_level(logging.WARNING):
            # tldextract on a bare string with no TLD yields empty registered_domain
            monitor.log_unknown_source(url="not-a-url")

        # Should not have committed anything
        session.commit.assert_not_called()


# ===========================================================================
# TestGetTrendingUnknowns
# ===========================================================================


class TestGetTrendingUnknowns:
    """Tests for SourceMonitor.get_trending_unknowns."""

    def test_returns_sources_above_threshold(self):
        """Only sources with frequency >= min_frequency are returned."""
        high_freq = _make_unknown_source(domain="popular.com", frequency=5)
        session = MagicMock()
        result = MagicMock()
        result.all.return_value = [high_freq]
        session.exec.return_value = result

        monitor = SourceMonitor(session)
        trending = monitor.get_trending_unknowns(min_frequency=3)

        assert len(trending) == 1
        assert trending[0].domain == "popular.com"
        # Verify the session.exec was called (query was built and executed)
        session.exec.assert_called_once()

    def test_respects_limit(self):
        """The limit parameter caps the number of results."""
        sources = [
            _make_unknown_source(domain=f"site{i}.com", frequency=10) for i in range(5)
        ]
        session = MagicMock()
        result = MagicMock()
        result.all.return_value = sources[:2]  # simulate DB returning limited results
        session.exec.return_value = result

        monitor = SourceMonitor(session)
        trending = monitor.get_trending_unknowns(min_frequency=1, limit=2)

        assert len(trending) == 2


# ===========================================================================
# TestMarkAsReviewed
# ===========================================================================


class TestMarkAsReviewed:
    """Tests for SourceMonitor.mark_as_reviewed."""

    def test_marks_domain_reviewed(self):
        """A found domain is marked reviewed with the assigned tier."""
        source = _make_unknown_source(
            domain="newsite.com", reviewed=False, assigned_tier=None
        )
        session = _mock_session(existing_row=source)
        monitor = SourceMonitor(session)

        monitor.mark_as_reviewed(domain="newsite.com", assigned_tier="news_tier2")

        assert source.reviewed is True
        assert source.assigned_tier == "news_tier2"
        session.commit.assert_called_once()

    def test_handles_missing_domain(self, caplog):
        """Attempting to review a domain that doesn't exist logs a warning and doesn't crash."""
        session = _mock_session(existing_row=None)
        monitor = SourceMonitor(session)

        with caplog.at_level(logging.WARNING):
            monitor.mark_as_reviewed(domain="nonexistent.com", assigned_tier="tier1")

        session.commit.assert_not_called()
