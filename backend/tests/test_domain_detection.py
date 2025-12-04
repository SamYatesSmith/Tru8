"""
Unit Tests for Article Classification
Phase 5: Government API Integration - LLM-based article-level classification

Tests for article_classifier module.
Replaces old per-claim spaCy NER domain detection with ~95% accuracy LLM classification.
"""

import pytest
from app.utils.article_classifier import (
    ArticleClassification,
    _check_url_pattern_cache,
    classify_article_sync,
    VALID_DOMAINS,
    VALID_JURISDICTIONS,
)


class TestArticleClassification:
    """Test suite for ArticleClassification dataclass."""

    def test_article_classification_creation(self):
        """Test creating an ArticleClassification instance."""
        classification = ArticleClassification(
            primary_domain="Sports",
            secondary_domains=["Politics"],
            jurisdiction="UK",
            confidence=0.95,
            reasoning="Football article from BBC Sport",
            source="cache_pattern"
        )

        assert classification.primary_domain == "Sports"
        assert classification.secondary_domains == ["Politics"]
        assert classification.jurisdiction == "UK"
        assert classification.confidence == 0.95
        assert classification.source == "cache_pattern"

    def test_article_classification_to_dict(self):
        """Test converting ArticleClassification to dictionary."""
        classification = ArticleClassification(
            primary_domain="Finance",
            secondary_domains=[],
            jurisdiction="Global",
            confidence=0.8,
            reasoning="Financial news",
            source="llm_primary"
        )

        result = classification.to_dict()

        assert isinstance(result, dict)
        assert result["primary_domain"] == "Finance"
        assert result["jurisdiction"] == "Global"
        assert result["confidence"] == 0.8
        assert result["source"] == "llm_primary"

    def test_article_classification_from_dict(self):
        """Test creating ArticleClassification from dictionary."""
        data = {
            "primary_domain": "Health",
            "secondary_domains": ["Science"],
            "jurisdiction": "UK",
            "confidence": 0.9,
            "reasoning": "NHS article",
            "source": "cache_url"
        }

        classification = ArticleClassification.from_dict(data)

        assert classification.primary_domain == "Health"
        assert classification.secondary_domains == ["Science"]
        assert classification.jurisdiction == "UK"
        assert classification.confidence == 0.9
        assert classification.source == "cache_url"

    def test_article_classification_from_dict_defaults(self):
        """Test ArticleClassification handles missing fields with defaults."""
        data = {}

        classification = ArticleClassification.from_dict(data)

        assert classification.primary_domain == "General"
        assert classification.secondary_domains == []
        assert classification.jurisdiction == "Global"
        assert classification.confidence == 0.0


class TestURLPatternCache:
    """Test suite for URL pattern cache functionality."""

    # ========== SPORTS DOMAIN ==========

    def test_bbc_sport_pattern(self):
        """Test BBC Sport URL detection."""
        url = "https://www.bbc.co.uk/sport/football/12345"
        result = _check_url_pattern_cache(url)

        assert result is not None
        assert result.primary_domain == "Sports"
        assert result.jurisdiction == "UK"
        assert result.source == "cache_pattern"
        assert result.confidence >= 0.9

    def test_skysports_pattern(self):
        """Test Sky Sports URL detection."""
        url = "https://www.skysports.com/football/news/12345"
        result = _check_url_pattern_cache(url)

        assert result is not None
        assert result.primary_domain == "Sports"
        assert result.jurisdiction == "UK"

    def test_espn_pattern(self):
        """Test ESPN URL detection."""
        url = "https://www.espn.com/soccer/match/12345"
        result = _check_url_pattern_cache(url)

        assert result is not None
        assert result.primary_domain == "Sports"
        assert result.jurisdiction == "US"

    def test_athletic_pattern(self):
        """Test The Athletic URL detection."""
        url = "https://theathletic.com/article/12345"
        result = _check_url_pattern_cache(url)

        assert result is not None
        assert result.primary_domain == "Sports"
        assert result.jurisdiction == "Global"

    # ========== POLITICS DOMAIN ==========

    def test_bbc_politics_pattern(self):
        """Test BBC Politics URL detection."""
        url = "https://www.bbc.co.uk/news/politics/12345"
        result = _check_url_pattern_cache(url)

        assert result is not None
        assert result.primary_domain == "Politics"
        assert result.jurisdiction == "UK"

    def test_gov_uk_pattern(self):
        """Test GOV.UK URL detection."""
        url = "https://www.gov.uk/government/news/12345"
        result = _check_url_pattern_cache(url)

        assert result is not None
        assert result.primary_domain == "Politics"
        assert result.jurisdiction == "UK"

    def test_parliament_pattern(self):
        """Test UK Parliament URL detection."""
        url = "https://www.parliament.uk/business/bills/12345"
        result = _check_url_pattern_cache(url)

        assert result is not None
        assert result.primary_domain == "Politics"
        assert result.jurisdiction == "UK"

    # ========== FINANCE DOMAIN ==========

    def test_ft_pattern(self):
        """Test Financial Times URL detection."""
        url = "https://www.ft.com/content/12345"
        result = _check_url_pattern_cache(url)

        assert result is not None
        assert result.primary_domain == "Finance"
        assert result.jurisdiction == "Global"

    def test_bloomberg_pattern(self):
        """Test Bloomberg URL detection."""
        url = "https://www.bloomberg.com/news/articles/12345"
        result = _check_url_pattern_cache(url)

        assert result is not None
        assert result.primary_domain == "Finance"
        assert result.jurisdiction == "Global"

    def test_ons_pattern(self):
        """Test ONS URL detection."""
        url = "https://www.ons.gov.uk/economy/12345"
        result = _check_url_pattern_cache(url)

        assert result is not None
        assert result.primary_domain == "Finance"
        assert result.jurisdiction == "UK"

    # ========== HEALTH DOMAIN ==========

    def test_nhs_pattern(self):
        """Test NHS URL detection."""
        url = "https://www.nhs.uk/conditions/covid-19"
        result = _check_url_pattern_cache(url)

        assert result is not None
        assert result.primary_domain == "Health"
        assert result.jurisdiction == "UK"

    def test_who_pattern(self):
        """Test WHO URL detection."""
        url = "https://www.who.int/news/12345"
        result = _check_url_pattern_cache(url)

        assert result is not None
        assert result.primary_domain == "Health"
        assert result.jurisdiction == "Global"

    def test_cdc_pattern(self):
        """Test CDC URL detection."""
        url = "https://www.cdc.gov/disease/12345"
        result = _check_url_pattern_cache(url)

        assert result is not None
        assert result.primary_domain == "Health"
        assert result.jurisdiction == "US"

    def test_pubmed_pattern(self):
        """Test PubMed URL detection."""
        url = "https://pubmed.ncbi.nlm.nih.gov/12345"
        result = _check_url_pattern_cache(url)

        assert result is not None
        assert result.primary_domain == "Health"
        assert result.jurisdiction == "Global"

    # ========== SCIENCE DOMAIN ==========

    def test_nature_pattern(self):
        """Test Nature journal URL detection."""
        url = "https://www.nature.com/articles/12345"
        result = _check_url_pattern_cache(url)

        assert result is not None
        assert result.primary_domain == "Science"
        assert result.jurisdiction == "Global"

    def test_arxiv_pattern(self):
        """Test arXiv URL detection."""
        url = "https://arxiv.org/abs/2401.12345"
        result = _check_url_pattern_cache(url)

        assert result is not None
        assert result.primary_domain == "Science"
        assert result.jurisdiction == "Global"

    # ========== CLIMATE DOMAIN ==========

    def test_met_office_pattern(self):
        """Test Met Office URL detection."""
        url = "https://www.metoffice.gov.uk/weather/12345"
        result = _check_url_pattern_cache(url)

        assert result is not None
        assert result.primary_domain == "Climate"
        assert result.jurisdiction == "UK"

    def test_noaa_pattern(self):
        """Test NOAA URL detection."""
        url = "https://www.noaa.gov/climate/12345"
        result = _check_url_pattern_cache(url)

        assert result is not None
        assert result.primary_domain == "Climate"
        assert result.jurisdiction == "US"

    # ========== LAW DOMAIN ==========

    def test_legislation_gov_pattern(self):
        """Test legislation.gov.uk URL detection."""
        url = "https://www.legislation.gov.uk/ukpga/2020/1"
        result = _check_url_pattern_cache(url)

        assert result is not None
        assert result.primary_domain == "Law"
        assert result.jurisdiction == "UK"

    def test_supremecourt_gov_pattern(self):
        """Test Supreme Court URL detection."""
        url = "https://www.supremecourt.gov/opinions/12345"
        result = _check_url_pattern_cache(url)

        assert result is not None
        assert result.primary_domain == "Law"
        assert result.jurisdiction == "US"

    # ========== NO MATCH (FALLBACK) ==========

    def test_unknown_url_no_match(self):
        """Test that unknown URLs return None (no cache match)."""
        url = "https://www.random-news-site.com/article/12345"
        result = _check_url_pattern_cache(url)

        assert result is None

    def test_empty_url(self):
        """Test handling of empty URL."""
        url = ""
        result = _check_url_pattern_cache(url)

        assert result is None

    def test_none_url(self):
        """Test handling of None URL."""
        url = None
        result = _check_url_pattern_cache(url)

        assert result is None


class TestSyncClassification:
    """Test suite for synchronous classification (URL pattern only)."""

    def test_sync_sports_classification(self):
        """Test sync classification for sports URL."""
        result = classify_article_sync(
            title="Arsenal transfer news",
            url="https://www.skysports.com/football/arsenal",
            content="Arsenal are looking to sign a new striker..."
        )

        assert result.primary_domain == "Sports"
        assert result.jurisdiction == "UK"
        assert result.source == "cache_pattern"

    def test_sync_fallback_classification(self):
        """Test sync classification falls back to General for unknown URLs."""
        result = classify_article_sync(
            title="Random article",
            url="https://www.unknown-site.com/article",
            content="Some random content..."
        )

        assert result.primary_domain == "General"
        assert result.jurisdiction == "Global"
        assert result.source == "fallback_general"
        assert result.confidence == 0.0


class TestDomainConstants:
    """Test domain and jurisdiction constants."""

    def test_valid_domains_complete(self):
        """Test that all expected domains are defined."""
        expected_domains = [
            "Sports", "Politics", "Finance", "Health", "Science",
            "Law", "Climate", "Demographics", "Entertainment", "General"
        ]

        for domain in expected_domains:
            assert domain in VALID_DOMAINS

    def test_valid_jurisdictions_complete(self):
        """Test that all expected jurisdictions are defined."""
        expected_jurisdictions = ["UK", "US", "EU", "Global"]

        for jurisdiction in expected_jurisdictions:
            assert jurisdiction in VALID_JURISDICTIONS


class TestURLPatternCacheCoverage:
    """Test URL pattern cache coverage for major publishers."""

    # Test major UK sports publishers
    @pytest.mark.parametrize("url,expected_domain", [
        ("https://www.bbc.co.uk/sport/football/12345", "Sports"),
        ("https://www.bbc.com/sport/cricket/12345", "Sports"),
        ("https://www.skysports.com/football", "Sports"),
        ("https://www.espn.co.uk/football/12345", "Sports"),
        ("https://www.premierleague.com/match/12345", "Sports"),
        ("https://www.goal.com/en/news/12345", "Sports"),
        ("https://www.football365.com/news/12345", "Sports"),
    ])
    def test_sports_coverage(self, url, expected_domain):
        """Test sports URL pattern coverage."""
        result = _check_url_pattern_cache(url)
        assert result is not None, f"URL not matched: {url}"
        assert result.primary_domain == expected_domain

    # Test major news publishers by section
    @pytest.mark.parametrize("url,expected_domain,expected_jurisdiction", [
        ("https://www.bbc.co.uk/news/politics/12345", "Politics", "UK"),
        ("https://www.bbc.co.uk/news/health/12345", "Health", "UK"),
        ("https://www.bbc.co.uk/news/science-environment/12345", "Science", "UK"),
        ("https://www.bbc.co.uk/news/business/12345", "Finance", "UK"),
    ])
    def test_bbc_section_coverage(self, url, expected_domain, expected_jurisdiction):
        """Test BBC section URL pattern coverage."""
        result = _check_url_pattern_cache(url)
        assert result is not None, f"URL not matched: {url}"
        assert result.primary_domain == expected_domain
        assert result.jurisdiction == expected_jurisdiction


# ========== ASYNC TESTS (require event loop) ==========

class TestAsyncClassification:
    """Test suite for async classification (requires async fixtures)."""

    @pytest.mark.asyncio
    async def test_async_classification_with_cache_hit(self):
        """Test async classification with URL pattern cache hit."""
        from app.utils.article_classifier import classify_article

        result = await classify_article(
            title="Premier League Match Report",
            url="https://www.bbc.co.uk/sport/football/12345",
            content="Arsenal won 2-0 against Chelsea..."
        )

        assert result.primary_domain == "Sports"
        assert result.jurisdiction == "UK"
        assert result.source == "cache_pattern"
        assert result.confidence >= 0.9
