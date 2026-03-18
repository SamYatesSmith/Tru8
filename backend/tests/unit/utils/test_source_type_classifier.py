"""Tests for SourceTypeClassifier."""

import pytest

from app.utils.source_type_classifier import SourceTypeClassifier


@pytest.fixture
def classifier():
    return SourceTypeClassifier()


class TestClassifySource:
    """Tests for classify_source method."""

    def test_academic_journal(self, classifier):
        """URLs containing academic journal domains are classified as primary."""
        result_nature = classifier.classify_source(
            "https://www.nature.com/articles/s41586-025-01234"
        )
        assert result_nature["source_type"] == "primary"

        result_sd = classifier.classify_source(
            "https://www.sciencedirect.com/science/article/pii/S0140"
        )
        assert result_sd["source_type"] == "primary"

    def test_government_data(self, classifier):
        """URLs containing government domains are classified as primary."""
        result_govuk = classifier.classify_source(
            "https://www.ons.gov.uk/data/population"
        )
        assert result_govuk["source_type"] == "primary"

        result_gov = classifier.classify_source("https://www.census.gov/data/tables")
        assert result_gov["source_type"] == "primary"

    def test_news_outlet(self, classifier):
        """URLs containing major news outlets are classified as secondary."""
        result_bbc = classifier.classify_source(
            "https://www.bbc.co.uk/news/uk-politics-12345"
        )
        assert result_bbc["source_type"] == "secondary"

        result_reuters = classifier.classify_source(
            "https://www.reuters.com/world/uk/some-article"
        )
        assert result_reuters["source_type"] == "secondary"

    def test_wikipedia(self, classifier):
        """Wikipedia URLs are classified as tertiary."""
        result = classifier.classify_source(
            "https://en.wikipedia.org/wiki/Climate_change"
        )
        assert result["source_type"] == "tertiary"

    def test_factcheck_site(self, classifier):
        """Fact-check sites are classified as tertiary."""
        result_snopes = classifier.classify_source(
            "https://www.snopes.com/fact-check/some-claim"
        )
        assert result_snopes["source_type"] == "tertiary"

        result_ff = classifier.classify_source(
            "https://fullfact.org/economy/some-claim"
        )
        assert result_ff["source_type"] == "tertiary"

    def test_unknown_source(self, classifier):
        """Random URLs with no matching patterns are classified as unknown."""
        result = classifier.classify_source("https://randomsite.xyz/some-page")
        assert result["source_type"] == "unknown"
        assert result["primary_indicators"] == []
        assert result["is_original_research"] is False
        assert result["credibility_boost"] == 0.0

    def test_peer_reviewed_detection(self, classifier):
        """Content with peer-review indicators triggers is_original_research."""
        result = classifier.classify_source(
            url="https://randomsite.xyz/paper",
            title="Published in Journal of Medicine",
            snippet="doi: 10.1234/example.5678 - a randomised trial",
        )
        assert result["is_original_research"] is True

    def test_credibility_boost_values(self, classifier):
        """Credibility boost values match expected tier values."""
        primary = classifier.classify_source("https://www.nature.com/articles/12345")
        assert primary["credibility_boost"] == pytest.approx(0.25)

        secondary = classifier.classify_source("https://www.bbc.co.uk/news/article-1")
        assert secondary["credibility_boost"] == pytest.approx(0.0)

        tertiary = classifier.classify_source("https://en.wikipedia.org/wiki/Test")
        assert tertiary["credibility_boost"] == pytest.approx(-0.15)


class TestGetSourceQualityLabel:
    """Tests for get_source_quality_label method."""

    def test_primary_original_research(self, classifier):
        """Primary source with original research returns 'Original Research'."""
        label = classifier.get_source_quality_label("primary", True)
        assert label == "Original Research"

    def test_primary_not_original(self, classifier):
        """Primary source without original research returns 'Primary Source'."""
        label = classifier.get_source_quality_label("primary", False)
        assert label == "Primary Source"

    def test_secondary(self, classifier):
        """Secondary source returns 'News Report'."""
        label = classifier.get_source_quality_label("secondary", False)
        assert label == "News Report"

    def test_unknown(self, classifier):
        """Unknown source returns 'General Source'."""
        label = classifier.get_source_quality_label("unknown", False)
        assert label == "General Source"
