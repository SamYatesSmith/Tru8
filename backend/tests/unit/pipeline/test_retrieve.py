"""
Evidence Retrieval Stage Tests - Phase 1 Pipeline Coverage

Created: 2025-11-03 16:00:00 UTC
Last Updated: 2026-02-17 (E03: credibility scoring removed)
Test Count: 23
Coverage Target: 80%+
MVP Scope: URL/TEXT inputs only (no image/video)

Tests the evidence retrieval stage which:
- Searches for relevant evidence using Brave Search / SERP API
- Retrieves fact-check claims from Google Fact Check Explorer
- Filters by temporal relevance for time-sensitive claims
- Aggregates and ranks evidence from multiple sources

CRITICAL for MVP:
- Must respect rate limits
- Must handle API failures gracefully
- Must deduplicate evidence
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from datetime import datetime, timedelta
import json

from app.pipeline.retrieve import EvidenceRetriever
from app.services.evidence import EvidenceSnippet
from mocks.models import Claim, Evidence

from mocks.search_results import (
    MOCK_SEARCH_RESULTS_STANDARD,
    MOCK_SEARCH_RESULTS_DUPLICATES,
    MOCK_SEARCH_RESULTS_DOMAIN_DOMINATED,
    MOCK_SEARCH_RESULTS_TEMPORAL,
    create_search_result,
)
from mocks.factcheck_data import (
    MOCK_FACTCHECK_TRUE,
    MOCK_FACTCHECK_FALSE,
    MOCK_FACTCHECK_MULTIPLE_REVIEWERS,
    MOCK_FACTCHECK_CONFLICTING,
    MOCK_FACTCHECK_RECENT,
    get_factcheck_by_rating,
    create_factcheck_claim,
)
from mocks.sample_content import SAMPLE_CLAIMS


def _extract_evidence(result, position="0"):
    """Extract evidence list from retrieve_evidence_for_claims return value.

    The method returns:
        {"evidence_by_claim": {"0": [...]}, "raw_evidence": [...], ...}
    """
    return result.get("evidence_by_claim", {}).get(position, [])


@pytest.fixture
def retriever_env():
    """Fixture that provides a fully-mocked EvidenceRetriever.

    Yields a dict with keys:
        retriever: EvidenceRetriever instance (mocked externals)
        mock_extractor: The mocked EvidenceExtractor instance
        mock_search_service: The mocked SearchService instance
    """
    with (
        patch("app.pipeline.retrieve.SearchService") as MockSearchService,
        patch("app.pipeline.retrieve.EvidenceExtractor") as MockExtractor,
        patch("app.pipeline.retrieve.get_api_registry", return_value=MagicMock()),
        patch("app.pipeline.retrieve.get_embedding_service", return_value=MagicMock()),
        patch("app.pipeline.retrieve.get_vector_store", return_value=MagicMock()),
        patch("app.pipeline.retrieve.settings") as mock_settings,
        patch(
            "app.utils.deduplication.EvidenceDeduplicator.deduplicate",
            side_effect=lambda evidence_list: (evidence_list, {"removed": 0}),
        ),
        patch(
            "app.utils.corroboration.apply_corroboration_boost",
            side_effect=lambda evidence_list: (
                evidence_list,
                {
                    "items_annotated": 0,
                    "corroboration_pairs": 0,
                    "groups": 0,
                    "derivation_chains": 0,
                },
            ),
        ),
    ):
        # Configure settings to isolate from environment
        mock_settings.MAX_SOURCES_PER_CLAIM = 20
        mock_settings.MAX_CONCURRENT_URL_FETCHES = 15
        mock_settings.ENABLE_QUERY_PLANNING = False
        mock_settings.ENABLE_API_RETRIEVAL = True
        mock_settings.ENABLE_RECOVERY_QUERY_PLANNING = False
        mock_settings.ENABLE_RECOVERY_ENRICHMENT = False
        mock_settings.RECOVERY_MAX_RESULTS_PER_ELEMENT = 5
        mock_settings.RECOVERY_PLANNER_TIMEOUT = 10.0
        mock_settings.MAX_EVIDENCE_FOR_RANKING = 100
        mock_settings.ALLOW_SNIPPET_FALLBACK = True

        mock_extractor = MockExtractor.return_value
        mock_search_service = MockSearchService.return_value

        # Default: government API returns nothing
        mock_search_service.search_for_evidence = AsyncMock(return_value=[])

        retriever = EvidenceRetriever()

        # Mock _retrieve_from_government_apis to return empty
        retriever._retrieve_from_government_apis = AsyncMock(
            return_value={"evidence": [], "api_stats": {}}
        )

        # Mock _store_evidence_embeddings to no-op
        retriever._store_evidence_embeddings = AsyncMock(return_value=None)

        retriever.search_service = mock_search_service

        yield {
            "retriever": retriever,
            "mock_extractor": mock_extractor,
            "mock_search_service": mock_search_service,
        }


def _make_snippets(
    count,
    text_prefix="Evidence text",
    source_prefix="Source",
    url_prefix="https://source",
    published_date="2024-11-01",
    relevance_score=0.9,
):
    """Helper to create a list of EvidenceSnippet instances."""
    return [
        EvidenceSnippet(
            text=f"{text_prefix} {i}",
            source=f"{source_prefix} {i}",
            url=f"{url_prefix}{i}.org",
            title=f"Title {i}",
            published_date=published_date,
            relevance_score=relevance_score,
        )
        for i in range(count)
    ]


@pytest.mark.unit
@pytest.mark.phase1
@pytest.mark.stage_retrieve
class TestEvidenceRetrieval:
    """Test suite for evidence retrieval stage - CRITICAL for MVP accuracy"""

    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_successful_evidence_retrieval_standard_claim(self, retriever_env):
        """
        Test: Successful evidence retrieval for standard factual claim
        CRITICAL: Main evidence retrieval path for MVP
        """
        retriever = retriever_env["retriever"]
        mock_extractor = retriever_env["mock_extractor"]

        mock_snippets = _make_snippets(
            5, text_prefix="Evidence text about climate agreement"
        )
        mock_extractor.extract_evidence_for_claim = AsyncMock(
            return_value=mock_snippets
        )

        claim_dict = {
            "text": "195 countries agreed to reduce carbon emissions by 45% by 2030",
            "subject_context": "Climate agreement",
            "key_entities": ["195 countries", "45%", "2030"],
            "is_time_sensitive": True,
            "claim_type": "factual",
            "position": 0,
        }
        result = await retriever.retrieve_evidence_for_claims([claim_dict])
        evidence_list = _extract_evidence(result)

        assert isinstance(evidence_list, list)
        assert len(evidence_list) >= 3, "Must return at least 3 evidence items"

        for evidence in evidence_list:
            assert "text" in evidence
            assert "url" in evidence
            assert "source" in evidence
            assert evidence["url"].startswith("http")

    @pytest.mark.asyncio
    async def test_duplicate_evidence_deduplication(self, retriever_env):
        """
        Test: Deduplicate evidence from same source or with identical content
        """
        retriever = retriever_env["retriever"]
        mock_extractor = retriever_env["mock_extractor"]

        mock_snippets = [
            EvidenceSnippet(
                text=f"Unique evidence text {i}",
                source=f"Source {i}",
                url=f"https://source{i}.org",
                title=f"Title {i}",
                published_date="2024-11-01",
                relevance_score=0.9,
            )
            for i in range(8)
        ]
        mock_extractor.extract_evidence_for_claim = AsyncMock(
            return_value=mock_snippets
        )

        claim_dict = {
            "text": "Test claim",
            "claim_type": "factual",
            "position": 0,
        }

        result = await retriever.retrieve_evidence_for_claims([claim_dict])
        evidence_list = _extract_evidence(result)

        urls = [e.get("url") for e in evidence_list]
        assert len(urls) == len(set(urls)), "Should not return duplicate URLs"

        content_hashes = []
        for evidence in evidence_list:
            content_preview = evidence["text"][:100].lower().strip()
            content_hashes.append(content_preview)

        assert len(content_hashes) == len(
            set(content_hashes)
        ), "Should not return evidence with identical content"

    @pytest.mark.asyncio
    async def test_temporal_filtering_for_time_sensitive_claims(self, retriever_env):
        """
        Test: Filter evidence by date for time-sensitive claims
        """
        retriever = retriever_env["retriever"]
        mock_extractor = retriever_env["mock_extractor"]

        recent_date = (datetime.utcnow() - timedelta(days=5)).strftime("%Y-%m-%d")
        mock_snippets = [
            EvidenceSnippet(
                text=f"Recent unemployment data {i}",
                source="Bureau of Labor Statistics",
                url=f"https://bls.gov/data{i}",
                title=f"Recent Data {i}",
                published_date=recent_date,
                relevance_score=0.9,
            )
            for i in range(3)
        ]
        mock_extractor.extract_evidence_for_claim = AsyncMock(
            return_value=mock_snippets
        )

        claim_dict = {
            "text": "Unemployment rate is at 5.2% as of October 2025",
            "is_time_sensitive": True,
            "temporal_markers": ["October 2025"],
            "claim_type": "factual",
            "position": 0,
        }
        result = await retriever.retrieve_evidence_for_claims([claim_dict])
        evidence_list = _extract_evidence(result)

        assert (
            len(evidence_list) > 0
        ), "Should find recent evidence for time-sensitive claim"

        for evidence in evidence_list:
            assert "published_date" in evidence or "date" in evidence

    @pytest.mark.asyncio
    async def test_factcheck_api_integration(self, retriever_env):
        """
        Test: Integration with fact-check evidence
        CRITICAL: Fact-check sources are high-value evidence
        """
        retriever = retriever_env["retriever"]
        mock_extractor = retriever_env["mock_extractor"]

        mock_snippets = [
            EvidenceSnippet(
                text="Fact-check: Vaccines do NOT cause autism",
                source="Snopes",
                url="https://snopes.com/vaccines-autism",
                title="Fact Check: Vaccines Autism",
                published_date="2024-11-01",
                relevance_score=0.95,
            )
        ]
        mock_extractor.extract_evidence_for_claim = AsyncMock(
            return_value=mock_snippets
        )

        claim_dict = {
            "text": "Vaccines cause autism",
            "claim_type": "factual",
            "position": 0,
        }
        result = await retriever.retrieve_evidence_for_claims([claim_dict])
        evidence_list = _extract_evidence(result)

        assert len(evidence_list) > 0, "Should return fact-check evidence"

        for evidence in evidence_list:
            assert "source" in evidence, "Should include source"

    @pytest.mark.asyncio
    async def test_multiple_factcheck_reviewers_consensus(self, retriever_env):
        """
        Test: Handle multiple fact-check reviewers with different ratings
        """
        retriever = retriever_env["retriever"]
        mock_extractor = retriever_env["mock_extractor"]

        mock_snippets = [
            EvidenceSnippet(
                text="Fact-check: COVID-19 vaccines are safe - PolitiFact",
                source="PolitiFact",
                url="https://politifact.com/covid-vaccines",
                title="Fact Check: COVID Vaccines",
                published_date="2024-11-01",
                relevance_score=0.95,
            ),
            EvidenceSnippet(
                text="Fact-check: Vaccines proven safe - Snopes",
                source="Snopes",
                url="https://snopes.com/covid-vaccines",
                title="Fact Check: Vaccine Safety",
                published_date="2024-10-28",
                relevance_score=0.93,
            ),
        ]
        mock_extractor.extract_evidence_for_claim = AsyncMock(
            return_value=mock_snippets
        )

        claim_dict = {
            "text": "COVID-19 vaccines are safe",
            "claim_type": "factual",
            "position": 0,
        }
        result = await retriever.retrieve_evidence_for_claims([claim_dict])
        evidence_list = _extract_evidence(result)

        assert len(evidence_list) >= 2, "Should include multiple fact-check reviewers"

        sources = set(e.get("source") for e in evidence_list)
        assert len(sources) >= 2, "Should have evidence from different reviewers"

    @pytest.mark.asyncio
    async def test_source_diversity_across_domains(self, retriever_env):
        """
        Test: Ensure evidence comes from diverse sources
        """
        retriever = retriever_env["retriever"]
        mock_extractor = retriever_env["mock_extractor"]

        # Create snippets from diverse domains
        mock_snippets = [
            EvidenceSnippet(
                text=f"Evidence from domain {i}",
                source=f"Source {i}",
                url=f"https://domain{i}.org/article",
                title=f"Title {i}",
                published_date="2024-11-01",
                relevance_score=0.9,
            )
            for i in range(6)
        ]
        mock_extractor.extract_evidence_for_claim = AsyncMock(
            return_value=mock_snippets
        )

        claim_dict = {
            "text": "Test claim for diversity",
            "claim_type": "factual",
            "position": 0,
        }
        result = await retriever.retrieve_evidence_for_claims([claim_dict])
        evidence_list = _extract_evidence(result)

        if len(evidence_list) >= 4:
            domains = [e.get("url", "").split("/")[2] for e in evidence_list]
            domain_counts = {}
            for domain in domains:
                domain_counts[domain] = domain_counts.get(domain, 0) + 1

            max_count = max(domain_counts.values()) if domain_counts else 0
            total_count = len(evidence_list)

            assert (
                max_count <= total_count * 0.6
            ), f"Single domain has {max_count}/{total_count} evidence items (>60%)"

    @pytest.mark.asyncio
    async def test_max_evidence_limit(self, retriever_env):
        """
        Test: Enforce maximum evidence items per claim (max_sources_per_claim = 20)
        """
        retriever = retriever_env["retriever"]
        mock_extractor = retriever_env["mock_extractor"]

        # Mock 25 evidence snippets
        mock_snippets = [
            EvidenceSnippet(
                text=f"Evidence text {i}",
                source=f"Source {i}",
                url=f"https://source{i}.org",
                title=f"Title {i}",
                published_date="2024-11-01",
                relevance_score=0.9 - (i * 0.02),
            )
            for i in range(25)
        ]
        mock_extractor.extract_evidence_for_claim = AsyncMock(
            return_value=mock_snippets
        )

        claim_dict = {
            "text": "Test claim",
            "claim_type": "factual",
            "position": 0,
        }
        result = await retriever.retrieve_evidence_for_claims([claim_dict])
        evidence_list = _extract_evidence(result)

        assert (
            len(evidence_list) <= retriever.max_sources_per_claim
        ), f"Should return max {retriever.max_sources_per_claim} evidence items, got {len(evidence_list)}"
        assert len(evidence_list) >= 3, "Should return at least some evidence"

    @pytest.mark.asyncio
    async def test_search_query_optimization(self, retriever_env):
        """
        Test: Evidence retrieval with optimized search from claim context
        """
        retriever = retriever_env["retriever"]
        mock_extractor = retriever_env["mock_extractor"]

        mock_snippets = _make_snippets(
            5, text_prefix="195 countries carbon emissions reduction agreement"
        )
        mock_extractor.extract_evidence_for_claim = AsyncMock(
            return_value=mock_snippets
        )

        claim_dict = {
            "text": "According to recent studies, approximately 195 countries agreed to reduce carbon emissions by 45% by 2030",
            "subject_context": "Climate agreement",
            "key_entities": ["195 countries", "carbon emissions", "45%", "2030"],
            "claim_type": "factual",
            "position": 0,
        }
        result = await retriever.retrieve_evidence_for_claims([claim_dict])
        evidence_list = _extract_evidence(result)

        mock_extractor.extract_evidence_for_claim.assert_called_once()
        call_args = mock_extractor.extract_evidence_for_claim.call_args

        assert claim_dict["text"] in str(
            call_args
        ), "Should pass claim text to extractor"
        assert len(evidence_list) >= 3, "Should retrieve evidence for complex claim"

    @pytest.mark.asyncio
    async def test_api_timeout_handling(self, retriever_env):
        """
        Test: Handle search API timeout gracefully
        CRITICAL: Must not crash on API failures
        """
        retriever = retriever_env["retriever"]
        mock_extractor = retriever_env["mock_extractor"]

        mock_snippets = _make_snippets(5)
        mock_extractor.extract_evidence_for_claim = AsyncMock(
            return_value=mock_snippets
        )

        claim_dict = {
            "text": "Test claim",
            "claim_type": "factual",
            "position": 0,
        }

        result = await retriever.retrieve_evidence_for_claims([claim_dict])
        evidence_list = _extract_evidence(result)

        assert isinstance(evidence_list, list), "Should return list even after timeout"
        assert len(evidence_list) >= 3, "Should return evidence"

    @pytest.mark.asyncio
    async def test_api_error_fallback_to_factcheck_only(self, retriever_env):
        """
        Test: Fall back to fact-check API when search API fails
        """
        retriever = retriever_env["retriever"]
        mock_extractor = retriever_env["mock_extractor"]

        mock_snippets = [
            EvidenceSnippet(
                text="Fallback evidence",
                source="Fallback Source",
                url="https://fallback.org",
                title="Fallback Title",
                published_date="2024-11-01",
                relevance_score=0.9,
            )
        ]
        mock_extractor.extract_evidence_for_claim = AsyncMock(
            return_value=mock_snippets
        )

        claim_dict = {
            "text": "Test claim",
            "claim_type": "factual",
            "position": 0,
        }

        result = await retriever.retrieve_evidence_for_claims([claim_dict])
        evidence_list = _extract_evidence(result)

        assert isinstance(
            evidence_list, list
        ), "Should return list even when search fails"
        assert len(evidence_list) >= 1, "Should have fallback evidence"

    @pytest.mark.asyncio
    async def test_empty_search_results_handling(self, retriever_env):
        """
        Test: Handle case when no evidence found
        """
        retriever = retriever_env["retriever"]
        mock_extractor = retriever_env["mock_extractor"]

        mock_extractor.extract_evidence_for_claim = AsyncMock(return_value=[])

        # Also mock recovery search to return nothing
        retriever._ensure_minimum_evidence = AsyncMock(
            side_effect=lambda evidence_by_claim, claims, excluded_domain=None: (
                evidence_by_claim,
                [],
            )
        )

        claim_dict = {
            "text": "Extremely obscure claim with no evidence",
            "claim_type": "factual",
            "position": 0,
        }

        result = await retriever.retrieve_evidence_for_claims([claim_dict])
        evidence_list = _extract_evidence(result)

        assert isinstance(evidence_list, list), "Should return list (may be empty)"
        assert (
            len(evidence_list) == 0
        ), "Should return empty list when no evidence found"

    @pytest.mark.asyncio
    async def test_relevance_scoring(self, retriever_env):
        """
        Test: Score evidence by relevance to claim
        """
        retriever = retriever_env["retriever"]
        mock_extractor = retriever_env["mock_extractor"]

        mock_snippets = [
            EvidenceSnippet(
                text=f"Paris Agreement global warming 1.5C evidence {i}",
                source=f"Source {i}",
                url=f"https://source{i}.org",
                title=f"Title {i}",
                published_date="2024-11-01",
                relevance_score=0.9 - (i * 0.1),
            )
            for i in range(5)
        ]
        mock_extractor.extract_evidence_for_claim = AsyncMock(
            return_value=mock_snippets
        )

        claim_dict = {
            "text": "Paris Agreement set goal to limit global warming to 1.5C",
            "key_entities": ["Paris Agreement", "1.5C", "global warming"],
            "claim_type": "factual",
            "position": 0,
        }

        result = await retriever.retrieve_evidence_for_claims([claim_dict])
        evidence_list = _extract_evidence(result)

        for evidence in evidence_list:
            assert "relevance_score" in evidence, "Evidence should have relevance score"
            assert (
                0 <= evidence.get("relevance_score", 0) <= 1.0
            ), "Relevance score should be 0-1"

        if len(evidence_list) >= 2:
            top_evidence = evidence_list[0]
            assert (
                top_evidence.get("relevance_score", 0) >= 0.0
            ), "Top evidence should have relevance score"

    @pytest.mark.asyncio
    async def test_publisher_metadata_extraction(self, retriever_env):
        """
        Test: Extract and validate publisher metadata
        """
        retriever = retriever_env["retriever"]
        mock_extractor = retriever_env["mock_extractor"]

        mock_snippets = [
            EvidenceSnippet(
                text=f"Evidence text {i}",
                source=f"Publisher {i}",
                url=f"https://publisher{i}.org/article",
                title=f"Title {i}",
                published_date="2024-11-01",
                relevance_score=0.9,
            )
            for i in range(5)
        ]
        mock_extractor.extract_evidence_for_claim = AsyncMock(
            return_value=mock_snippets
        )

        claim_dict = {
            "text": "Test claim",
            "claim_type": "factual",
            "position": 0,
        }

        result = await retriever.retrieve_evidence_for_claims([claim_dict])
        evidence_list = _extract_evidence(result)

        for evidence in evidence_list:
            assert (
                "source" in evidence
            ), f"Evidence missing source: {evidence.get('url')}"
            assert "url" in evidence, "Evidence missing URL"
            assert (
                evidence["source"] is not None and len(evidence["source"]) > 0
            ), "Source should not be empty"
            assert evidence["url"].startswith("http"), "URL should be valid"

    @pytest.mark.asyncio
    async def test_rate_limiting_respect(self, retriever_env):
        """
        Test: Respect API rate limits (one call per claim)
        """
        retriever = retriever_env["retriever"]
        mock_extractor = retriever_env["mock_extractor"]

        mock_snippets = _make_snippets(1)
        mock_extractor.extract_evidence_for_claim = AsyncMock(
            return_value=mock_snippets
        )

        for i in range(5):
            claim_dict = {
                "text": f"Test claim {i}",
                "claim_type": "factual",
                "position": i,
            }
            await retriever.retrieve_evidence_for_claims([claim_dict])

        assert (
            mock_extractor.extract_evidence_for_claim.call_count == 5
        ), "Should make one call per claim"

    @pytest.mark.asyncio
    async def test_cache_usage_for_duplicate_queries(self, retriever_env):
        """
        Test: Retrieve same claim twice successfully
        """
        retriever = retriever_env["retriever"]
        mock_extractor = retriever_env["mock_extractor"]

        mock_snippets = _make_snippets(
            5, text_prefix="Climate change evidence", url_prefix="https://climate"
        )
        mock_extractor.extract_evidence_for_claim = AsyncMock(
            return_value=mock_snippets
        )

        claim_dict = {
            "text": "Climate change is real",
            "claim_type": "factual",
            "position": 0,
        }

        result_1 = await retriever.retrieve_evidence_for_claims([claim_dict])
        evidence_list_1 = _extract_evidence(result_1)
        result_2 = await retriever.retrieve_evidence_for_claims([claim_dict])
        evidence_list_2 = _extract_evidence(result_2)

        assert len(evidence_list_1) > 0, "First retrieval should return evidence"
        assert len(evidence_list_2) > 0, "Second retrieval should return evidence"

    @pytest.mark.asyncio
    async def test_opinion_claim_handling(self, retriever_env):
        """
        Test: Handle opinion claims appropriately
        """
        retriever = retriever_env["retriever"]
        mock_extractor = retriever_env["mock_extractor"]

        mock_snippets = _make_snippets(3, text_prefix="Mona Lisa painting discussion")
        mock_extractor.extract_evidence_for_claim = AsyncMock(
            return_value=mock_snippets
        )

        claim_dict = {
            "text": "The Mona Lisa is the most beautiful painting",
            "claim_type": "opinion",
            "position": 0,
        }
        result = await retriever.retrieve_evidence_for_claims([claim_dict])
        evidence_list = _extract_evidence(result)

        assert isinstance(
            evidence_list, list
        ), "Should return evidence list for opinion claims"

    @pytest.mark.asyncio
    async def test_prediction_claim_handling(self, retriever_env):
        """
        Test: Handle prediction/future claims
        """
        retriever = retriever_env["retriever"]
        mock_extractor = retriever_env["mock_extractor"]

        mock_snippets = _make_snippets(3, text_prefix="Climate prediction data")
        mock_extractor.extract_evidence_for_claim = AsyncMock(
            return_value=mock_snippets
        )

        claim_dict = {
            "text": "Global temperature will rise by 2C by 2050",
            "claim_type": "prediction",
            "temporal_markers": ["by 2050"],
            "is_time_sensitive": True,
            "position": 0,
        }
        result = await retriever.retrieve_evidence_for_claims([claim_dict])
        evidence_list = _extract_evidence(result)

        assert isinstance(evidence_list, list), "Should return evidence for predictions"

    @pytest.mark.asyncio
    async def test_numerical_claim_entity_extraction(self, retriever_env):
        """
        Test: Extract and search for numerical entities
        """
        retriever = retriever_env["retriever"]
        mock_extractor = retriever_env["mock_extractor"]

        mock_snippets = [
            EvidenceSnippet(
                text=f"Unemployment rate data shows decrease from 8.2% to 5.4% in 2024",
                source=f"Economic Source {i}",
                url=f"https://econ{i}.org",
                title=f"Unemployment Statistics {i}",
                published_date="2024-11-01",
                relevance_score=0.9,
            )
            for i in range(5)
        ]
        mock_extractor.extract_evidence_for_claim = AsyncMock(
            return_value=mock_snippets
        )

        claim_dict = {
            "text": "Unemployment rate decreased from 8.2% to 5.4% in 2024",
            "key_entities": ["8.2%", "5.4%", "2024", "unemployment rate"],
            "claim_type": "factual",
            "position": 0,
        }

        result = await retriever.retrieve_evidence_for_claims([claim_dict])
        evidence_list = _extract_evidence(result)

        assert len(evidence_list) >= 3
        mock_extractor.extract_evidence_for_claim.assert_called_once()

        assert any(
            "8.2%" in e.get("text", "") or "5.4%" in e.get("text", "")
            for e in evidence_list
        ), "Evidence should contain numerical values from claim"

    @pytest.mark.asyncio
    async def test_special_characters_in_claim(self, retriever_env):
        """
        Test: Handle special characters in claim text
        """
        retriever = retriever_env["retriever"]
        mock_extractor = retriever_env["mock_extractor"]

        mock_snippets = _make_snippets(
            5,
            text_prefix="Apple stock price analysis: 25% increase to $175.50",
            source_prefix="Financial Source",
            url_prefix="https://finance",
        )
        mock_extractor.extract_evidence_for_claim = AsyncMock(
            return_value=mock_snippets
        )

        claim_dict = {
            "text": "Apple's stock price increased by 25% to $175.50, making it worth $2.8T",
            "claim_type": "factual",
            "position": 0,
        }

        result = await retriever.retrieve_evidence_for_claims([claim_dict])
        evidence_list = _extract_evidence(result)

        assert isinstance(
            evidence_list, list
        ), "Should handle special characters without errors"
        assert len(evidence_list) >= 3
        mock_extractor.extract_evidence_for_claim.assert_called_once()

    @pytest.mark.asyncio
    async def test_very_long_claim_truncation(self, retriever_env):
        """
        Test: Handle very long claims (>500 characters)
        """
        retriever = retriever_env["retriever"]
        mock_extractor = retriever_env["mock_extractor"]

        mock_snippets = _make_snippets(
            5,
            text_prefix="Climate change evidence",
            source_prefix="Climate Source",
            url_prefix="https://climate",
        )
        mock_extractor.extract_evidence_for_claim = AsyncMock(
            return_value=mock_snippets
        )

        long_text = "Climate change " + "is a significant issue " * 50
        claim_dict = {
            "text": long_text,
            "key_entities": ["climate change"],
            "claim_type": "factual",
            "position": 0,
        }

        result = await retriever.retrieve_evidence_for_claims([claim_dict])
        evidence_list = _extract_evidence(result)

        assert len(evidence_list) >= 3
        assert isinstance(evidence_list, list), "Should handle long claims"
        mock_extractor.extract_evidence_for_claim.assert_called_once()

    @pytest.mark.asyncio
    async def test_unicode_characters_in_claim(self, retriever_env):
        """
        Test: Handle unicode characters in claim
        """
        retriever = retriever_env["retriever"]
        mock_extractor = retriever_env["mock_extractor"]

        mock_snippets = _make_snippets(
            5,
            text_prefix="Sao Paulo temperature data: 35C",
            source_prefix="Weather Source",
            url_prefix="https://weather",
        )
        mock_extractor.extract_evidence_for_claim = AsyncMock(
            return_value=mock_snippets
        )

        claim_dict = {
            "text": "S\u00e3o Paulo's temperature reached 35\u00b0C in \u00e9t\u00e9 2024",
            "claim_type": "factual",
            "position": 0,
        }

        result = await retriever.retrieve_evidence_for_claims([claim_dict])
        evidence_list = _extract_evidence(result)

        assert isinstance(evidence_list, list), "Should handle unicode characters"
        assert len(evidence_list) >= 3
        mock_extractor.extract_evidence_for_claim.assert_called_once()

    @pytest.mark.asyncio
    async def test_evidence_date_parsing(self, retriever_env):
        """
        Test: Parse and validate evidence publication dates
        """
        retriever = retriever_env["retriever"]
        mock_extractor = retriever_env["mock_extractor"]

        mock_snippets = _make_snippets(5)
        mock_extractor.extract_evidence_for_claim = AsyncMock(
            return_value=mock_snippets
        )

        claim_dict = {
            "text": "Test claim",
            "claim_type": "factual",
            "position": 0,
        }

        result = await retriever.retrieve_evidence_for_claims([claim_dict])
        evidence_list = _extract_evidence(result)

        assert len(evidence_list) >= 3
        for evidence in evidence_list:
            if evidence.get("published_date") is not None:
                assert isinstance(
                    evidence.get("published_date"), str
                ), "Published date should be string in YYYY-MM-DD format"
                date_str = evidence.get("published_date")
                assert (
                    len(date_str) == 10 and date_str[4] == "-" and date_str[7] == "-"
                ), "Date should be in YYYY-MM-DD format"

    @pytest.mark.asyncio
    async def test_conflicting_factchecks_handling(self, retriever_env):
        """
        Test: Handle conflicting fact-check ratings
        """
        retriever = retriever_env["retriever"]
        mock_extractor = retriever_env["mock_extractor"]

        mock_snippets = [
            EvidenceSnippet(
                text="Fact-check rating: True",
                source="FactCheck Source A",
                url="https://factchecka.org/check1",
                title="Fact Check A",
                published_date="2024-11-01",
                relevance_score=0.9,
            ),
            EvidenceSnippet(
                text="Fact-check rating: False",
                source="FactCheck Source B",
                url="https://factcheckb.org/check2",
                title="Fact Check B",
                published_date="2024-11-01",
                relevance_score=0.9,
            ),
            EvidenceSnippet(
                text="Fact-check rating: Partly True",
                source="FactCheck Source C",
                url="https://factcheckc.org/check3",
                title="Fact Check C",
                published_date="2024-11-01",
                relevance_score=0.9,
            ),
        ]
        mock_extractor.extract_evidence_for_claim = AsyncMock(
            return_value=mock_snippets
        )

        claim_dict = {
            "text": "Controversial claim",
            "claim_type": "factual",
            "position": 0,
        }

        result = await retriever.retrieve_evidence_for_claims([claim_dict])
        evidence_list = _extract_evidence(result)

        assert (
            len(evidence_list) >= 2
        ), "Should include multiple fact-checks even if conflicting"

        sources = [e.get("source") for e in evidence_list]
        assert len(set(sources)) >= 2, "Should include evidence from multiple sources"

    @pytest.mark.asyncio
    async def test_malformed_api_response_handling(self, retriever_env):
        """
        Test: Handle malformed/empty evidence extractor response gracefully
        """
        retriever = retriever_env["retriever"]
        mock_extractor = retriever_env["mock_extractor"]

        # Simulate extractor raising an exception
        mock_extractor.extract_evidence_for_claim = AsyncMock(
            side_effect=Exception("Malformed API response")
        )

        # Also mock recovery to return empty
        retriever._ensure_minimum_evidence = AsyncMock(
            side_effect=lambda evidence_by_claim, claims, excluded_domain=None: (
                evidence_by_claim,
                [],
            )
        )

        claim_dict = {
            "text": "Test claim",
            "claim_type": "factual",
            "position": 0,
        }
        result = await retriever.retrieve_evidence_for_claims([claim_dict])
        evidence_list = _extract_evidence(result)

        assert isinstance(
            evidence_list, list
        ), "Should return list even with malformed data"

    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_end_to_end_retrieve_pipeline(self, retriever_env):
        """
        Test: Complete end-to-end evidence retrieval pipeline
        CRITICAL: Full pipeline test for MVP
        """
        retriever = retriever_env["retriever"]
        mock_extractor = retriever_env["mock_extractor"]

        mock_snippets = [
            EvidenceSnippet(
                text=f"Paris Agreement evidence {i}: 195 countries signed in 2015",
                source=f"Credible Source {i}",
                url=f"https://crediblesource{i}.org/paris-agreement",
                title=f"Paris Agreement Article {i}",
                published_date="2015-12-12",
                relevance_score=0.95 - (i * 0.05),
            )
            for i in range(12)
        ]
        mock_extractor.extract_evidence_for_claim = AsyncMock(
            return_value=mock_snippets
        )

        claim_dict = {
            "text": "The Paris Agreement was signed by 195 countries in 2015",
            "subject_context": "Climate agreement",
            "key_entities": ["Paris Agreement", "195 countries", "2015"],
            "is_time_sensitive": False,
            "claim_type": "factual",
            "position": 0,
        }

        result = await retriever.retrieve_evidence_for_claims([claim_dict])
        evidence_list = _extract_evidence(result)

        assert isinstance(evidence_list, list), "Should return list of evidence"
        assert len(evidence_list) >= 3, "Should return multiple evidence items"
        assert (
            len(evidence_list) <= retriever.max_sources_per_claim
        ), "Should not exceed max limit"

        for evidence in evidence_list:
            assert "text" in evidence, "Evidence must have text"
            assert "url" in evidence, "Evidence must have URL"
            assert "source" in evidence, "Evidence must have source"


class TestGovernmentApiRoutingRobustness:
    """Regression cover for government-API routing edge cases."""

    @pytest.mark.asyncio
    async def test_routing_handles_none_confidence(self, caplog):
        """Sentry PYTHON-FASTAPI-28: a degraded article_classification can carry
        ``confidence=None`` (the key is present with a None value, so the .get
        default never applies). The ``confidence={confidence:.2f}`` debug log
        then raised ``TypeError: unsupported format string passed to NoneType``,
        which was swallowed by the method's try/except and logged as
        'Government API retrieval error'. The fix coerces None -> 0.0, so routing
        must complete with NO error logged.
        """
        import logging

        registry = MagicMock()
        # Non-empty so the method skips its emergency re-initialisation branch.
        registry.adapters = {"dummy": object()}
        # No adapters for the domain -> the method hits its clean empty return
        # at the "if not relevant_adapters" guard, with no live API calls.
        registry.get_adapters_for_domain.return_value = []

        keyword_router = MagicMock()
        keyword_router.get_additional_adapters.return_value = []

        with (
            patch("app.pipeline.retrieve.SearchService"),
            patch("app.pipeline.retrieve.EvidenceExtractor"),
            patch("app.pipeline.retrieve.get_api_registry", return_value=registry),
            patch("app.core.config.settings.ENABLE_API_RETRIEVAL", True),
            patch(
                "app.utils.claim_keyword_router.get_keyword_router",
                return_value=keyword_router,
            ),
        ):
            retriever = EvidenceRetriever()

            claim = {
                "text": "A UK-based child received vaccinations at age 1",
                "claim_type": None,
                "key_entities": [],
                "article_classification": {
                    "primary_domain": "Health",
                    "jurisdiction": "UK",
                    "confidence": None,  # the value that crashed the format string
                    "secondary_domains": [],
                    "source": "fallback_general",
                    "classification_failed": True,
                },
            }

            with caplog.at_level(logging.ERROR, logger="app.pipeline.retrieve"):
                result = await retriever._retrieve_from_government_apis(
                    claim["text"], claim
                )

        # Clean empty return, and crucially NO swallowed format error.
        assert result == {"evidence": [], "api_stats": {}}
        assert not any(
            "Government API retrieval error" in rec.message
            or "unsupported format string" in rec.message
            for rec in caplog.records
        ), "None confidence must not raise a format error during routing"
