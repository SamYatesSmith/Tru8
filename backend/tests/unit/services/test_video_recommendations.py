"""Tests for video_recommendations service — channel classification heuristic."""

import pytest

from app.services.video_recommendations import classify_channel, CHANNEL_HEURISTICS


class TestClassifyChannel:
    """classify_channel maps YouTube channel names to (tier, type) tuples."""

    def test_known_channel_exact_match(self):
        """Exact match for a known channel returns its classification."""
        tier, etype = classify_channel("BBC News")
        assert tier == "reporting"
        assert etype == "news_reporting"

    def test_known_channel_case_insensitive(self):
        """Lookup is case-insensitive — lowercased input still matches."""
        tier, etype = classify_channel("bbc news")
        assert tier == "reporting"
        assert etype == "news_reporting"

    def test_unknown_channel_defaults(self):
        """Unknown channels default to (commentary, analysis)."""
        tier, etype = classify_channel("Random Channel XYZ")
        assert tier == "commentary"
        assert etype == "analysis"

    def test_partial_match(self):
        """A channel name containing a known channel as a substring matches."""
        # "reuters" is in CHANNEL_HEURISTICS; a longer name containing it should match
        tier, etype = classify_channel("Reuters UK Edition")
        assert tier == "reporting"
        assert etype == "news_reporting"
