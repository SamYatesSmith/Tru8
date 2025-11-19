"""
Unit tests for Primary Source Detection (Tier 1 Improvement)

Tests the SourceTypeClassifier which distinguishes primary sources (original research,
government data) from secondary sources (news) and tertiary sources (fact-checks).
"""

import pytest
from app.utils.source_type_classifier import SourceTypeClassifier


class TestSourceTypeClassifier:
    """Test primary source detection and classification"""

    @pytest.fixture
    def classifier(self):
        """Create SourceTypeClassifier instance"""
        return SourceTypeClassifier()

    def test_academic_journal_detection(self, classifier):
        """Test: Classifies academic journals as primary sources"""
        result = classifier.classify_source(
            url="https://www.nature.com/articles/s41586-024-12345",
            title="Climate change impacts on biodiversity",
            snippet="Published in Nature. DOI: 10.1038/s41586-024-12345. Vol. 625, Issue 7993."
        )

        assert result['source_type'] == 'primary'
        assert 'academic_journal' in result['primary_indicators']
        assert result['credibility_boost'] == 0.25
        assert result['is_original_research'] == True

    def test_peer_review_detection_from_content(self, classifier):
        """Test: Detects peer-reviewed research from content cues"""
        result = classifier.classify_source(
            url="https://example.com/article",
            title="Effects of drug X on disease Y",
            snippet="Published in the Journal of Medicine. Vol. 123, Issue 4. DOI: 10.1234/jmed.2024. Peer reviewed."
        )

        assert result['source_type'] == 'primary'
        assert 'peer_reviewed' in result['primary_indicators']
        assert result['is_original_research'] == True

    def test_government_data_detection(self, classifier):
        """Test: Classifies .gov data sources as primary"""
        result = classifier.classify_source(
            url="https://www.census.gov/data/tables/2024/demo/popest.html",
            title="Census Bureau Population Estimates",
            snippet="Official statistics from the U.S. Census Bureau. Annual dataset release."
        )

        assert result['source_type'] == 'primary'
        assert 'government_data' in result['primary_indicators']
        assert result['credibility_boost'] == 0.25

    def test_statistical_report_detection(self, classifier):
        """Test: Detects statistical reports from content"""
        result = classifier.classify_source(
            url="https://www.ons.gov.uk/economy/report",
            title="ONS Economic Statistics Bulletin",
            snippet="Official statistics showing unemployment data for Q4 2024. Census survey data."
        )

        assert result['source_type'] == 'primary'
        assert 'statistical_report' in result['primary_indicators']

    def test_research_institution_detection(self, classifier):
        """Test: Classifies research institutions as primary"""
        result = classifier.classify_source(
            url="https://www.nber.org/papers/w12345",
            title="Economic impact study",
            snippet="National Bureau of Economic Research working paper."
        )

        assert result['source_type'] == 'primary'
        assert 'research_institution' in result['primary_indicators']

    def test_official_government_report(self, classifier):
        """Test: Classifies official government reports as primary"""
        result = classifier.classify_source(
            url="https://www.whitehouse.gov/briefing-room/statements/2024/policy-report",
            title="White House Policy Report",
            snippet="Official statement from the White House on economic policy."
        )

        assert result['source_type'] == 'primary'
        assert 'official_report' in result['primary_indicators']

    def test_news_article_classification(self, classifier):
        """Test: Classifies news articles as secondary sources"""
        result = classifier.classify_source(
            url="https://www.bbc.com/news/article-12345",
            title="New study finds climate change accelerating",
            snippet="According to researchers at the University of Oxford..."
        )

        assert result['source_type'] == 'secondary'
        assert result['credibility_boost'] == 0.0
        assert result['is_original_research'] == False

    def test_factcheck_classification(self, classifier):
        """Test: Classifies fact-checks as tertiary sources"""
        result = classifier.classify_source(
            url="https://www.snopes.com/fact-check/example-claim",
            title="Fact Check: Did X happen?",
            snippet="Rating: Mostly False. We investigated this claim..."
        )

        assert result['source_type'] == 'tertiary'
        assert result['credibility_boost'] == -0.15
        assert result['is_original_research'] == False

    def test_wikipedia_classification(self, classifier):
        """Test: Classifies Wikipedia as tertiary"""
        result = classifier.classify_source(
            url="https://en.wikipedia.org/wiki/Climate_change",
            title="Climate change - Wikipedia",
            snippet="Climate change includes both global warming..."
        )

        assert result['source_type'] == 'tertiary'
        assert result['credibility_boost'] == -0.15

    def test_unknown_source_classification(self, classifier):
        """Test: Unknown sources get neutral classification"""
        result = classifier.classify_source(
            url="https://random-blog.com/post/my-opinion",
            title="My thoughts on topic X",
            snippet="In my experience, I think that..."
        )

        assert result['source_type'] == 'unknown'
        assert result['credibility_boost'] == 0.0
        assert result['is_original_research'] == False

    def test_legal_source_detection(self, classifier):
        """Test: Classifies legal databases as primary"""
        result = classifier.classify_source(
            url="https://www.supremecourt.gov/opinions/24pdf/case.pdf",
            title="Supreme Court Opinion",
            snippet="The Court holds that..."
        )

        assert result['source_type'] == 'primary'
        assert 'legal_source' in result['primary_indicators']

    def test_quality_label_generation(self, classifier):
        """Test: Generates appropriate quality labels"""
        assert classifier.get_source_quality_label('primary', True) == "Original Research"
        assert classifier.get_source_quality_label('primary', False) == "Primary Source"
        assert classifier.get_source_quality_label('secondary', False) == "News Report"
        assert classifier.get_source_quality_label('tertiary', False) == "Meta-Analysis"
        assert classifier.get_source_quality_label('unknown', False) == "General Source"

    def test_multiple_indicators(self, classifier):
        """Test: Detects multiple primary indicators"""
        result = classifier.classify_source(
            url="https://www.nature.com/articles/research-123",
            title="Climate study",
            snippet="Published in Nature journal. Peer reviewed. DOI: 10.1038/nature.2024. Statistical analysis of census data."
        )

        assert result['source_type'] == 'primary'
        # Should detect multiple indicators
        assert len(result['primary_indicators']) >= 2
        assert 'academic_journal' in result['primary_indicators']

    def test_empty_url_handling(self, classifier):
        """Test: Handles empty URL gracefully"""
        result = classifier.classify_source(url="", title="Test", snippet="Test")

        assert result['source_type'] == 'unknown'
        assert result['credibility_boost'] == 0.0

    def test_case_insensitivity(self, classifier):
        """Test: Pattern matching is case-insensitive"""
        result = classifier.classify_source(
            url="https://WWW.NATURE.COM/ARTICLES/12345",
            title="STUDY TITLE",
            snippet="PUBLISHED IN JOURNAL"
        )

        # Should still detect as primary source despite uppercase
        assert result['source_type'] == 'primary'
