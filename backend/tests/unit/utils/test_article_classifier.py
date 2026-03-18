"""
Tests for app.utils.article_classifier

Covers pure-logic paths only: URL pattern cache, dataclass serialization,
constants, and synchronous classification.  No async LLM / Redis tests.
"""

import pytest

from app.utils.article_classifier import (
    ArticleClassification,
    VALID_DOMAINS,
    VALID_JURISDICTIONS,
    URL_PATTERN_CACHE,
    _check_url_pattern_cache,
    classify_article_sync,
)


# ── ArticleClassification dataclass ─────────────────────────────────────


class TestArticleClassificationDataclass:
    """ArticleClassification to_dict / from_dict round-trip."""

    def _make_classification(self, **overrides) -> ArticleClassification:
        defaults = dict(
            primary_domain="Politics",
            secondary_domains=["Finance"],
            jurisdiction="UK",
            confidence=85,
            reasoning="Matched by test",
            source="cache_pattern",
            temporal_context="March 2026",
            key_entities=["Parliament", "Budget"],
            evidence_guidance="Official Hansard records",
            classification_failed=False,
        )
        defaults.update(overrides)
        return ArticleClassification(**defaults)

    def test_to_dict_returns_all_fields(self):
        c = self._make_classification()
        d = c.to_dict()

        assert d["primary_domain"] == "Politics"
        assert d["secondary_domains"] == ["Finance"]
        assert d["jurisdiction"] == "UK"
        assert d["confidence"] == 85
        assert d["reasoning"] == "Matched by test"
        assert d["source"] == "cache_pattern"
        assert d["temporal_context"] == "March 2026"
        assert d["key_entities"] == ["Parliament", "Budget"]
        assert d["evidence_guidance"] == "Official Hansard records"
        assert d["classification_failed"] is False

    def test_from_dict_round_trip(self):
        original = self._make_classification()
        restored = ArticleClassification.from_dict(original.to_dict())

        assert restored.primary_domain == original.primary_domain
        assert restored.secondary_domains == original.secondary_domains
        assert restored.jurisdiction == original.jurisdiction
        assert restored.confidence == original.confidence
        assert restored.reasoning == original.reasoning
        assert restored.source == original.source
        assert restored.temporal_context == original.temporal_context
        assert restored.key_entities == original.key_entities
        assert restored.evidence_guidance == original.evidence_guidance
        assert restored.classification_failed == original.classification_failed

    def test_from_dict_with_missing_keys_uses_defaults(self):
        c = ArticleClassification.from_dict({})
        assert c.primary_domain == "General"
        assert c.secondary_domains == []
        assert c.jurisdiction == "Global"
        assert c.confidence == 0.0
        assert c.reasoning == ""
        assert c.source == "unknown"
        assert c.temporal_context == ""
        assert c.key_entities == []
        assert c.evidence_guidance == ""
        assert c.classification_failed is False

    def test_to_dict_from_dict_preserves_classification_failed(self):
        c = self._make_classification(classification_failed=True)
        d = c.to_dict()
        restored = ArticleClassification.from_dict(d)
        assert restored.classification_failed is True

    def test_key_entities_default_is_empty_list(self):
        """key_entities=None in constructor should become [] via __post_init__."""
        c = ArticleClassification(
            primary_domain="General",
            secondary_domains=[],
            jurisdiction="Global",
            confidence=50,
            reasoning="test",
            source="test",
        )
        assert c.key_entities == []


# ── _check_url_pattern_cache ────────────────────────────────────────────


class TestCheckUrlPatternCache:

    def test_bbc_uk_politics(self):
        result = _check_url_pattern_cache("https://www.bbc.co.uk/news/politics-123")
        assert result is not None
        assert result.primary_domain == "Politics"
        assert result.jurisdiction == "UK"
        assert result.source == "cache_pattern"
        assert result.confidence == 95

    def test_reuters_global(self):
        result = _check_url_pattern_cache(
            "https://www.reuters.com/business/some-article"
        )
        assert result is not None
        assert result.primary_domain == "Finance"
        assert result.jurisdiction == "Global"

    def test_gov_uk(self):
        result = _check_url_pattern_cache("https://www.gov.uk/government/policies")
        assert result is not None
        assert result.primary_domain == "Politics"
        assert result.jurisdiction == "UK"

    def test_unknown_url_returns_none(self):
        result = _check_url_pattern_cache("https://random-blog.com/post")
        assert result is None

    def test_pubmed_health(self):
        result = _check_url_pattern_cache("https://pubmed.ncbi.nlm.nih.gov/12345678/")
        assert result is not None
        assert result.primary_domain == "Health"
        assert result.jurisdiction == "Global"

    def test_empty_url_returns_none(self):
        assert _check_url_pattern_cache("") is None

    def test_none_url_returns_none(self):
        assert _check_url_pattern_cache(None) is None

    def test_espn_sports_us(self):
        result = _check_url_pattern_cache("https://www.espn.com/nfl/story/_/id/123")
        assert result is not None
        assert result.primary_domain == "Sports"
        assert result.jurisdiction == "US"

    def test_nhs_health_uk(self):
        result = _check_url_pattern_cache("https://www.nhs.uk/conditions/diabetes/")
        assert result is not None
        assert result.primary_domain == "Health"
        assert result.jurisdiction == "UK"

    def test_nature_science_global(self):
        result = _check_url_pattern_cache("https://www.nature.com/articles/s12345")
        assert result is not None
        assert result.primary_domain == "Science"
        assert result.jurisdiction == "Global"

    def test_ft_finance_global(self):
        result = _check_url_pattern_cache("https://www.ft.com/content/some-article")
        assert result is not None
        assert result.primary_domain == "Finance"
        assert result.jurisdiction == "Global"

    def test_noaa_climate_us(self):
        result = _check_url_pattern_cache("https://www.noaa.gov/climate-data")
        assert result is not None
        assert result.primary_domain == "Climate"
        assert result.jurisdiction == "US"

    def test_legislation_gov_uk_law(self):
        """legislation.gov.uk (Law) must match BEFORE generic gov.uk (Politics)."""
        result = _check_url_pattern_cache("https://www.legislation.gov.uk/ukpga/2020/1")
        assert result is not None
        assert result.primary_domain == "Law"
        assert result.jurisdiction == "UK"

    def test_ons_gov_uk_finance(self):
        """ons.gov.uk (Finance) must match BEFORE generic gov.uk (Politics)."""
        result = _check_url_pattern_cache("https://www.ons.gov.uk/economy/inflation")
        assert result is not None
        assert result.primary_domain == "Finance"
        assert result.jurisdiction == "UK"

    def test_gbif_animals_global(self):
        result = _check_url_pattern_cache("https://www.gbif.org/species/12345")
        assert result is not None
        assert result.primary_domain == "Animals"
        assert result.jurisdiction == "Global"

    def test_loc_gov_history_us(self):
        result = _check_url_pattern_cache("https://www.loc.gov/collections/")
        assert result is not None
        assert result.primary_domain == "History"
        assert result.jurisdiction == "US"

    def test_bailii_law_uk(self):
        result = _check_url_pattern_cache("https://www.bailii.org/uk/cases/2024/")
        assert result is not None
        assert result.primary_domain == "Law"
        assert result.jurisdiction == "UK"

    def test_case_insensitivity(self):
        """URL matching should be case-insensitive."""
        result = _check_url_pattern_cache("https://WWW.BBC.CO.UK/NEWS/POLITICS-456")
        assert result is not None
        assert result.primary_domain == "Politics"
        assert result.jurisdiction == "UK"

    def test_pattern_result_fields_are_fully_populated(self):
        """Every pattern match should set all expected fields."""
        result = _check_url_pattern_cache("https://www.who.int/news-room/")
        assert result is not None
        assert result.primary_domain == "Health"
        assert result.jurisdiction == "Global"
        assert result.confidence == 95
        assert result.source == "cache_pattern"
        assert result.secondary_domains == []
        assert result.key_entities == []
        assert result.temporal_context == ""
        assert result.evidence_guidance == ""
        assert result.classification_failed is False


# ── Constants ───────────────────────────────────────────────────────────


class TestConstants:

    def test_valid_domains_contains_expected(self):
        expected = [
            "Sports",
            "Politics",
            "Finance",
            "Health",
            "Science",
            "Law",
            "Climate",
        ]
        for domain in expected:
            assert domain in VALID_DOMAINS, f"{domain} missing from VALID_DOMAINS"

    def test_valid_domains_contains_general(self):
        assert "General" in VALID_DOMAINS

    def test_valid_domains_no_duplicates(self):
        assert len(VALID_DOMAINS) == len(set(VALID_DOMAINS))

    def test_valid_jurisdictions(self):
        assert "UK" in VALID_JURISDICTIONS
        assert "US" in VALID_JURISDICTIONS
        assert "EU" in VALID_JURISDICTIONS
        assert "Global" in VALID_JURISDICTIONS

    def test_valid_jurisdictions_length(self):
        assert len(VALID_JURISDICTIONS) == 4

    def test_url_pattern_cache_is_nonempty(self):
        assert len(URL_PATTERN_CACHE) > 100

    def test_url_pattern_cache_tuples_are_valid(self):
        """Every entry should be a 3-tuple with domain in VALID_DOMAINS
        and jurisdiction in VALID_JURISDICTIONS."""
        for i, entry in enumerate(URL_PATTERN_CACHE):
            assert len(entry) == 3, f"Pattern index {i} is not a 3-tuple: {entry}"
            pattern, domain, jurisdiction = entry
            assert (
                domain in VALID_DOMAINS
            ), f"Pattern index {i} has invalid domain '{domain}'"
            assert (
                jurisdiction in VALID_JURISDICTIONS
            ), f"Pattern index {i} has invalid jurisdiction '{jurisdiction}'"


# ── classify_article_sync ───────────────────────────────────────────────


class TestClassifyArticleSync:

    def test_known_url_returns_classification(self):
        """BBC politics URL should be classified without LLM."""
        result = classify_article_sync(
            title="PM faces questions on budget",
            url="https://www.bbc.co.uk/news/politics-789",
            content="The Prime Minister faced tough questions...",
        )
        assert result.primary_domain == "Politics"
        assert result.jurisdiction == "UK"
        assert result.source == "cache_pattern"
        assert result.confidence == 95

    def test_unknown_url_returns_general(self):
        """Unknown URL should fall back to General domain."""
        result = classify_article_sync(
            title="Something obscure",
            url="https://random-blog.com/post",
            content="Some random content",
        )
        assert result.primary_domain == "General"
        assert result.jurisdiction == "Global"
        assert result.source == "fallback_general"
        assert result.confidence == 0
        assert (
            result.classification_failed is False
        )  # Not an error, just sync limitation

    def test_empty_url_returns_general(self):
        result = classify_article_sync(
            title="No URL article",
            url="",
            content="Content without URL",
        )
        assert result.primary_domain == "General"
        assert result.source == "fallback_general"

    def test_none_url_returns_general(self):
        result = classify_article_sync(
            title="None URL",
            url=None,
            content="Content",
        )
        assert result.primary_domain == "General"
        assert result.source == "fallback_general"

    def test_sky_sports_returns_sports(self):
        result = classify_article_sync(
            title="Transfer news",
            url="https://www.skysports.com/football/transfer-news",
            content="Latest transfer rumours...",
        )
        assert result.primary_domain == "Sports"
        assert result.jurisdiction == "UK"

    def test_congress_gov_returns_politics_us(self):
        result = classify_article_sync(
            title="New bill introduced",
            url="https://www.congress.gov/bill/118th-congress/hr-1234",
            content="A new bill was introduced...",
        )
        assert result.primary_domain == "Politics"
        assert result.jurisdiction == "US"

    def test_arxiv_returns_science_global(self):
        result = classify_article_sync(
            title="Quantum paper",
            url="https://arxiv.org/abs/2401.12345",
            content="We present a novel quantum computing approach...",
        )
        assert result.primary_domain == "Science"
        assert result.jurisdiction == "Global"
