"""
PR-E06: Evidence classifier tests.

Tests for:
- Heuristic classification (URL patterns, source names, provider flags)
- LLM batch classification with fallback to heuristics
- Validation of tier and evidence_type values
"""

import pytest
from unittest.mock import AsyncMock, patch

from app.pipeline.evidence_classifier import (
    _classify_heuristic,
    EvidenceClassifier,
    VALID_TIERS,
    VALID_TYPES,
)


# ============================================================
# Class: TestEvidenceClassifierHeuristic
# ============================================================


class TestEvidenceClassifierHeuristic:
    """Tests for the _classify_heuristic module-level fallback function."""

    @pytest.mark.unit
    def test_gov_url_classified_as_primary_official(self):
        """Evidence with URL containing .gov should be tier=primary, type=official_statement."""
        evidence = {
            "evidence_id": "ev-gov",
            "title": "White House Briefing Statement",
            "source": "whitehouse.gov",
            "url": "https://www.whitehouse.gov/briefing-room/statement",
            "snippet": "The President announced today...",
        }

        tier, evidence_type = _classify_heuristic(evidence)

        assert tier == "primary"
        assert evidence_type == "official_statement"

    @pytest.mark.unit
    def test_edu_url_classified_as_primary_academic(self):
        """Evidence with .edu or .ac.uk URL should be tier=primary, type=academic."""
        # Test .edu
        evidence_edu = {
            "evidence_id": "ev-edu",
            "title": "Research Paper on Employment",
            "source": "mit.edu",
            "url": "https://economics.mit.edu/research/paper-123",
            "snippet": "Our analysis shows employment trends...",
        }

        tier, evidence_type = _classify_heuristic(evidence_edu)
        assert tier == "primary"
        assert evidence_type == "academic"

        # Test .ac.uk
        evidence_acuk = {
            "evidence_id": "ev-acuk",
            "title": "Oxford Labour Market Study",
            "source": "ox.ac.uk",
            "url": "https://www.economics.ox.ac.uk/paper/labour-study",
            "snippet": "Labour market analysis from Oxford...",
        }

        tier, evidence_type = _classify_heuristic(evidence_acuk)
        assert tier == "primary"
        assert evidence_type == "academic"

    @pytest.mark.unit
    def test_news_source_classified_as_reporting(self):
        """Evidence from BBC or Reuters should be tier=reporting, type=news_reporting."""
        evidence_bbc = {
            "evidence_id": "ev-bbc",
            "title": "UK Employment Update",
            "source": "BBC News",
            "url": "https://www.bbc.co.uk/news/business-99999",
            "snippet": "The latest employment figures show...",
        }

        tier, evidence_type = _classify_heuristic(evidence_bbc)
        assert tier == "reporting"
        assert evidence_type == "news_reporting"

        evidence_reuters = {
            "evidence_id": "ev-reuters",
            "title": "Global Jobs Report",
            "source": "Reuters",
            "url": "https://www.reuters.com/world/jobs-report",
            "snippet": "Reuters reports on global employment...",
        }

        tier, evidence_type = _classify_heuristic(evidence_reuters)
        assert tier == "reporting"
        assert evidence_type == "news_reporting"

    @pytest.mark.unit
    def test_api_adapter_classified_as_primary_data(self):
        """Evidence with external_source_provider set should be tier=primary, type=data."""
        evidence = {
            "evidence_id": "ev-api",
            "title": "ONS Employment Data",
            "source": "ons.gov.uk",
            "url": "https://www.ons.gov.uk/data",
            "snippet": "Official statistics...",
            "external_source_provider": "ONS Economic Statistics",
        }

        tier, evidence_type = _classify_heuristic(evidence)
        assert tier == "primary"
        assert evidence_type == "data"

    @pytest.mark.unit
    def test_factcheck_classified_as_reporting(self):
        """Evidence with is_factcheck=True should be tier=reporting, type=news_reporting."""
        evidence = {
            "evidence_id": "ev-fc",
            "title": "Fact Check: Employment Claims",
            "source": "Snopes",
            "url": "https://www.snopes.com/fact-check/employment",
            "snippet": "We rated this claim...",
            "is_factcheck": True,
        }

        tier, evidence_type = _classify_heuristic(evidence)
        assert tier == "reporting"
        assert evidence_type == "news_reporting"

    @pytest.mark.unit
    def test_unknown_defaults_to_commentary(self):
        """Evidence with no recognizable patterns should default to tier=commentary, type=news_reporting."""
        evidence = {
            "evidence_id": "ev-unknown",
            "title": "Some Blog Post About Jobs",
            "source": "randomblog.com",
            "url": "https://www.randomblog.com/my-thoughts-on-jobs",
            "snippet": "I think the job market is doing well...",
        }

        tier, evidence_type = _classify_heuristic(evidence)
        assert tier == "commentary"
        assert evidence_type == "news_reporting"

    @pytest.mark.unit
    def test_academic_urls(self):
        """Evidence from pubmed, arxiv, nature.com, sciencedirect should be tier=primary, type=academic."""
        academic_urls = [
            ("https://arxiv.org/abs/2025.12345", "arxiv.org"),
            ("https://www.nature.com/articles/s41586-025-00001-1", "nature.com"),
            (
                "https://www.sciencedirect.com/science/article/pii/S0001",
                "sciencedirect.com",
            ),
            ("https://link.springer.com/article/10.1007/s00001", "springer.com"),
        ]

        for url, source in academic_urls:
            evidence = {
                "evidence_id": f"ev-{source}",
                "title": f"Paper from {source}",
                "source": source,
                "url": url,
                "snippet": "Academic content...",
            }

            tier, evidence_type = _classify_heuristic(evidence)
            assert tier == "primary", f"Expected tier=primary for {source}, got {tier}"
            assert (
                evidence_type == "academic"
            ), f"Expected type=academic for {source}, got {evidence_type}"

    @pytest.mark.unit
    def test_opinion_in_wire_service_classified_as_commentary(self):
        """Wire service URL with opinion/editorial markers should be commentary/opinion."""
        evidence = {
            "evidence_id": "ev-opinion",
            "title": "Opinion: Why employment numbers mislead",
            "source": "theguardian.com",
            "url": "https://www.theguardian.com/commentisfree/opinion-piece",
            "snippet": "In my view, these figures are misleading...",
        }

        tier, evidence_type = _classify_heuristic(evidence)
        assert tier == "commentary"
        assert evidence_type == "opinion"

    @pytest.mark.unit
    def test_data_portal_classified_as_primary_data(self):
        """Data portals (ONS, BLS, World Bank) should be tier=primary, type=data."""
        evidence = {
            "evidence_id": "ev-worldbank",
            "title": "GDP Data",
            "source": "worldbank.org",
            "url": "https://data.worldbank.org/indicator/NY.GDP",
            "snippet": "World Bank GDP data...",
        }

        tier, evidence_type = _classify_heuristic(evidence)
        assert tier == "primary"
        assert evidence_type == "data"


# ============================================================
# Class: TestEvidenceClassifierBatch
# ============================================================


class TestEvidenceClassifierBatch:
    """Tests for the classify_batch async method (LLM-based with fallback)."""

    @pytest.fixture
    def classifier(self):
        """Create an EvidenceClassifier instance with mocked settings."""
        with patch("app.pipeline.evidence_classifier.settings") as mock_settings:
            mock_settings.OPENAI_API_KEY = "test-key"
            mock_settings.GOOGLE_AI_API_KEY = ""
            mock_settings.LLM_MODEL_NAME = "gpt-4o-mini"
            mock_settings.GOOGLE_LLM_MODEL = "gemini-2.5-flash-lite"
            return EvidenceClassifier()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_classify_batch_calls_llm(self, classifier):
        """Mock _call_llm, verify classify_batch parses the response and applies classification."""
        evidence_items = [
            {
                "evidence_id": "ev-001",
                "title": "Government Report",
                "source": "gov.uk",
                "url": "https://www.gov.uk/report",
                "snippet": "Official data...",
            },
            {
                "evidence_id": "ev-002",
                "title": "News Article",
                "source": "BBC News",
                "url": "https://bbc.co.uk/news/123",
                "snippet": "Reporting on...",
            },
        ]

        # Mock _call_llm to return valid classification JSON
        llm_response = {
            "classifications": [
                {"index": 0, "tier": "primary", "type": "official_statement"},
                {"index": 1, "tier": "reporting", "type": "news_reporting"},
            ]
        }

        classifier._call_llm = AsyncMock(return_value=llm_response)

        result = await classifier.classify_batch(evidence_items)

        # Verify LLM was called
        classifier._call_llm.assert_awaited_once()

        # Verify classifications were applied
        assert len(result) == 2
        assert result[0]["tier"] == "primary"
        assert result[0]["evidence_type"] == "official_statement"
        assert result[0]["classification_method"] == "llm"
        assert result[1]["tier"] == "reporting"
        assert result[1]["evidence_type"] == "news_reporting"
        assert result[1]["classification_method"] == "llm"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_classify_batch_llm_failure_falls_back_to_heuristic(self, classifier):
        """When _call_llm returns None, heuristic classification is used as fallback."""
        evidence_items = [
            {
                "evidence_id": "ev-gov",
                "title": "Government Stats",
                "source": "census.gov",
                "url": "https://www.census.gov/data/population",
                "snippet": "Population statistics...",
            },
        ]

        # Make the LLM call return None (failure)
        classifier._call_llm = AsyncMock(return_value=None)

        result = await classifier.classify_batch(evidence_items)

        assert len(result) == 1
        # .gov URL should be classified by heuristic as primary/official_statement
        assert result[0]["tier"] == "primary"
        assert result[0]["evidence_type"] == "official_statement"
        assert result[0]["classification_method"] == "heuristic"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_classify_batch_skips_already_classified(self, classifier):
        """Items that already have both tier and evidence_type set should be skipped."""
        evidence_items = [
            {
                "evidence_id": "ev-pre",
                "title": "Pre-classified Item",
                "source": "example.com",
                "url": "https://example.com/article",
                "snippet": "Already classified...",
                "tier": "primary",
                "evidence_type": "data",
            },
            {
                "evidence_id": "ev-new",
                "title": "Needs Classification",
                "source": "unknown.com",
                "url": "https://unknown.com/page",
                "snippet": "Not yet classified...",
            },
        ]

        llm_response = {
            "classifications": [
                {"index": 0, "tier": "commentary", "type": "opinion"},
            ]
        }

        classifier._call_llm = AsyncMock(return_value=llm_response)

        result = await classifier.classify_batch(evidence_items)

        assert len(result) == 2

        # Pre-classified item should retain its original classification
        pre_classified = next(r for r in result if r["evidence_id"] == "ev-pre")
        assert pre_classified["tier"] == "primary"
        assert pre_classified["evidence_type"] == "data"

        # New item should get LLM classification
        new_classified = next(r for r in result if r["evidence_id"] == "ev-new")
        assert new_classified["tier"] == "commentary"
        assert new_classified["evidence_type"] == "opinion"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_classify_batch_validates_tier_values(self, classifier):
        """If LLM returns invalid tier value, it should be corrected to default."""
        evidence_items = [
            {
                "evidence_id": "ev-bad-tier",
                "title": "Test Item",
                "source": "census.gov",
                "url": "https://www.census.gov/data",
                "snippet": "Some content...",
            },
        ]

        # LLM returns invalid tier "tier1"
        llm_response = {
            "classifications": [
                {"index": 0, "tier": "tier1", "type": "data"},
            ]
        }

        classifier._call_llm = AsyncMock(return_value=llm_response)

        result = await classifier.classify_batch(evidence_items)

        assert len(result) == 1
        # Invalid tier should be corrected to a valid value
        assert result[0]["tier"] in VALID_TIERS

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_classify_batch_validates_type_values(self, classifier):
        """If LLM returns invalid type value, it should be corrected to default."""
        evidence_items = [
            {
                "evidence_id": "ev-bad-type",
                "title": "Test Item",
                "source": "BBC News",
                "url": "https://www.bbc.co.uk/news/123",
                "snippet": "Some content...",
            },
        ]

        # LLM returns invalid evidence_type "news" (should be "news_reporting")
        llm_response = {
            "classifications": [
                {"index": 0, "tier": "reporting", "type": "news"},
            ]
        }

        classifier._call_llm = AsyncMock(return_value=llm_response)

        result = await classifier.classify_batch(evidence_items)

        assert len(result) == 1
        # Invalid type should be corrected to a valid value
        assert result[0]["evidence_type"] in VALID_TYPES

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_classify_batch_empty_list(self, classifier):
        """Empty evidence list should be returned as-is."""
        result = await classifier.classify_batch([])
        assert result == []

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_classify_batch_all_already_classified(self, classifier):
        """If all items are already classified, LLM should not be called."""
        evidence_items = [
            {
                "evidence_id": "ev-1",
                "title": "Item 1",
                "tier": "primary",
                "evidence_type": "data",
            },
            {
                "evidence_id": "ev-2",
                "title": "Item 2",
                "tier": "reporting",
                "evidence_type": "news_reporting",
            },
        ]

        classifier._call_llm = AsyncMock()

        result = await classifier.classify_batch(evidence_items)

        # LLM should NOT have been called
        classifier._call_llm.assert_not_awaited()
        assert len(result) == 2
        assert result[0]["tier"] == "primary"
        assert result[1]["tier"] == "reporting"


# ============================================================
# Class: TestParseClassificationResponse
# ============================================================


class TestParseClassificationResponse:
    """Tests for _parse_classification_response edge cases."""

    @pytest.fixture
    def classifier(self):
        with patch("app.pipeline.evidence_classifier.settings") as mock_settings:
            mock_settings.OPENAI_API_KEY = "test-key"
            mock_settings.GOOGLE_AI_API_KEY = ""
            mock_settings.LLM_MODEL_NAME = "gpt-4o-mini"
            mock_settings.GOOGLE_LLM_MODEL = "gemini-2.5-flash-lite"
            return EvidenceClassifier()

    @pytest.mark.unit
    def test_parse_alternative_list_format(self, classifier):
        """Parser should handle raw list format (no 'classifications' wrapper)."""
        raw = [
            {"index": 0, "tier": "primary", "type": "data"},
            {"index": 1, "tier": "reporting", "type": "news_reporting"},
        ]

        results = classifier._parse_classification_response(raw, 2)

        assert results[0] == ("primary", "data")
        assert results[1] == ("reporting", "news_reporting")

    @pytest.mark.unit
    def test_parse_out_of_range_index_ignored(self, classifier):
        """Items with index out of range should be silently ignored."""
        raw = {
            "classifications": [
                {"index": 0, "tier": "primary", "type": "data"},
                {"index": 99, "tier": "reporting", "type": "news_reporting"},
            ]
        }

        results = classifier._parse_classification_response(raw, 2)

        assert results[0] == ("primary", "data")
        assert results[1] is None  # Index 99 out of range, so index 1 is None

    @pytest.mark.unit
    def test_parse_empty_response(self, classifier):
        """Empty response should return all None."""
        raw = {}

        results = classifier._parse_classification_response(raw, 3)

        assert all(r is None for r in results)
        assert len(results) == 3
