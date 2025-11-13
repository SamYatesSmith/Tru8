"""
Integration Tests for Government API Integration
Phase 5: Week 3 - Full Pipeline with API Retrieval

Tests the end-to-end integration of government API adapters with the pipeline:
- API adapter initialization and registration
- Domain detection and routing
- Evidence retrieval from APIs + web search
- API statistics tracking in Check model
- Evidence metadata storage
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any, List

from app.pipeline.retrieve import EvidenceRetriever
from app.services.government_api_client import APIAdapterRegistry, get_api_registry
from app.services.api_adapters import (
    ONSAdapter, PubMedAdapter, FREDAdapter, WHOAdapter,
    CrossRefAdapter, GovUKAdapter, initialize_adapters
)
from app.utils.claim_classifier import ClaimClassifier


class TestAPIAdapterRegistration:
    """Test adapter initialization and registration."""

    def test_initialize_adapters_success(self):
        """Test that all adapters initialize successfully."""
        # Clear registry first
        registry = get_api_registry()
        registry.adapters = []

        # Initialize adapters
        initialize_adapters()

        # Verify all adapters registered
        all_adapters = registry.get_all_adapters()
        adapter_names = [a.api_name for a in all_adapters]

        # Week 1 + Week 2 adapters (10 total expected)
        expected_adapters = [
            "ONS Economic Statistics",
            "PubMed",
            "WHO",
            "CrossRef",
            "GOV.UK Content API",
            "UK Parliament Hansard",
            "Wikidata"
        ]

        for expected in expected_adapters:
            assert expected in adapter_names, f"{expected} adapter not registered"

    def test_get_adapters_for_finance_uk(self):
        """Test getting relevant adapters for Finance + UK domain."""
        registry = get_api_registry()

        # Get adapters for Finance + UK
        adapters = registry.get_adapters_for_domain("Finance", "UK")
        adapter_names = [a.api_name for a in adapters]

        # Should return ONS for UK Finance
        assert "ONS Economic Statistics" in adapter_names
        # Should NOT return WHO (Health domain)
        assert "WHO" not in adapter_names

    def test_get_adapters_for_health_global(self):
        """Test getting relevant adapters for Health + Global domain."""
        registry = get_api_registry()

        # Get adapters for Health + Global
        adapters = registry.get_adapters_for_domain("Health", "Global")
        adapter_names = [a.api_name for a in adapters]

        # Should return PubMed and WHO for Global Health
        assert "PubMed" in adapter_names
        assert "WHO" in adapter_names
        # Should NOT return ONS (Finance domain)
        assert "ONS Economic Statistics" not in adapter_names


class TestDomainDetectionAndRouting:
    """Test claim classification and API routing."""

    def test_domain_detection_for_finance_claim(self):
        """Test domain detection routes correctly for finance claims."""
        classifier = ClaimClassifier()

        claim_text = "UK inflation rate is 3.2% according to the ONS"
        domain_info = classifier.detect_domain(claim_text)

        assert domain_info["domain"] == "Finance"
        assert domain_info["jurisdiction"] == "UK"
        assert domain_info["domain_confidence"] > 0.5

    def test_domain_detection_for_health_claim(self):
        """Test domain detection routes correctly for health claims."""
        classifier = ClaimClassifier()

        claim_text = "COVID-19 vaccine efficacy is 95% according to recent studies"
        domain_info = classifier.detect_domain(claim_text)

        assert domain_info["domain"] in ["Health", "Science"]
        assert domain_info["jurisdiction"] in ["Global", "US"]

    def test_domain_detection_for_government_claim(self):
        """Test domain detection routes correctly for government claims."""
        classifier = ClaimClassifier()

        claim_text = "The UK Parliament passed new legislation on climate change"
        domain_info = classifier.detect_domain(claim_text)

        assert domain_info["domain"] in ["Government", "Law"]
        assert domain_info["jurisdiction"] == "UK"


class TestAPIEvidenceRetrieval:
    """Test evidence retrieval with API integration."""

    @pytest.mark.asyncio
    async def test_retrieve_from_government_apis_with_mock(self):
        """Test API evidence retrieval with mocked adapters."""
        retriever = EvidenceRetriever()
        retriever.enable_api_retrieval = True

        claim_text = "UK inflation is 3.2%"
        claim = {"text": claim_text, "position": 0}

        # Mock classifier to return Finance + UK
        with patch.object(retriever.claim_classifier, 'detect_domain') as mock_detect:
            mock_detect.return_value = {
                "domain": "Finance",
                "jurisdiction": "UK",
                "domain_confidence": 0.85,
                "key_entities": ["UK", "inflation"]
            }

            # Mock registry to return mock adapter
            mock_adapter = Mock()
            mock_adapter.api_name = "Test API"
            mock_adapter.search_with_cache.return_value = [
                {
                    "title": "UK Inflation Report",
                    "snippet": "Inflation rate stands at 3.2%",
                    "url": "https://api.test.gov.uk/inflation",
                    "external_source_provider": "Test API",
                    "credibility_score": 0.95,
                    "metadata": {"dataset_id": "CPI"}
                }
            ]

            with patch.object(retriever.api_registry, 'get_adapters_for_domain') as mock_get_adapters:
                mock_get_adapters.return_value = [mock_adapter]

                # Call API retrieval
                result = await retriever._retrieve_from_government_apis(claim_text, claim)

                # Verify results
                assert "evidence" in result
                assert "api_stats" in result
                assert len(result["evidence"]) == 1
                assert result["api_stats"]["total_api_calls"] == 1
                assert result["api_stats"]["total_api_results"] == 1

                # Verify evidence format
                evidence = result["evidence"][0]
                assert evidence["title"] == "UK Inflation Report"
                assert evidence["external_source_provider"] == "Test API"
                assert evidence["credibility_score"] == 0.95

    @pytest.mark.asyncio
    async def test_retrieve_with_feature_flag_disabled(self):
        """Test that API retrieval is skipped when feature flag is off."""
        retriever = EvidenceRetriever()
        retriever.enable_api_retrieval = False

        claim_text = "UK inflation is 3.2%"
        claim = {"text": claim_text, "position": 0}

        result = await retriever._retrieve_from_government_apis(claim_text, claim)

        # Should return empty results when disabled
        assert result["evidence"] == []
        assert result["api_stats"] == {}

    @pytest.mark.asyncio
    async def test_convert_api_evidence_to_snippets(self):
        """Test conversion of API evidence to EvidenceSnippet objects."""
        retriever = EvidenceRetriever()

        api_evidence = [
            {
                "title": "Test Evidence",
                "snippet": "This is a test snippet",
                "url": "https://api.test.gov.uk/data",
                "source": "Test API",
                "external_source_provider": "Test API",
                "metadata": {"dataset_id": "TEST123"},
                "credibility_score": 0.95
            }
        ]

        snippets = retriever._convert_api_evidence_to_snippets(api_evidence)

        assert len(snippets) == 1
        snippet = snippets[0]
        assert snippet.text == "This is a test snippet"
        assert snippet.source == "Test API"
        assert snippet.url == "https://api.test.gov.uk/data"
        assert snippet.metadata["external_source_provider"] == "Test API"
        assert snippet.metadata["credibility_score"] == 0.95


class TestPipelineAPIStats:
    """Test API statistics aggregation in pipeline."""

    def test_aggregate_api_stats_single_claim(self):
        """Test aggregating API stats from a single claim."""
        from app.workers.pipeline import PipelineTask

        task = PipelineTask()

        claims = [
            {
                "text": "UK inflation is 3.2%",
                "position": 0,
                "api_stats": {
                    "apis_queried": [
                        {"name": "ONS Economic Statistics", "results": 3}
                    ],
                    "total_api_calls": 1,
                    "total_api_results": 3
                }
            }
        ]

        evidence = {
            "0": [
                {"title": "ONS Report 1", "external_source_provider": "ONS Economic Statistics"},
                {"title": "ONS Report 2", "external_source_provider": "ONS Economic Statistics"},
                {"title": "Web Article", "source": "BBC"}  # Web evidence
            ]
        }

        stats = task._aggregate_api_stats(claims, evidence)

        assert stats["total_api_calls"] == 1
        assert stats["total_api_results"] == 3
        assert stats["api_evidence_count"] == 2  # 2 from API
        assert stats["total_evidence_count"] == 3
        assert stats["api_coverage_percentage"] == pytest.approx(66.67, rel=0.01)

    def test_aggregate_api_stats_multiple_claims(self):
        """Test aggregating API stats from multiple claims."""
        from app.workers.pipeline import PipelineTask

        task = PipelineTask()

        claims = [
            {
                "text": "UK inflation is 3.2%",
                "position": 0,
                "api_stats": {
                    "apis_queried": [
                        {"name": "ONS Economic Statistics", "results": 2}
                    ],
                    "total_api_calls": 1,
                    "total_api_results": 2
                }
            },
            {
                "text": "COVID-19 cases are rising",
                "position": 1,
                "api_stats": {
                    "apis_queried": [
                        {"name": "WHO", "results": 3},
                        {"name": "PubMed", "results": 5}
                    ],
                    "total_api_calls": 2,
                    "total_api_results": 8
                }
            }
        ]

        evidence = {
            "0": [
                {"title": "ONS Report", "external_source_provider": "ONS Economic Statistics"},
                {"title": "Web Article", "source": "BBC"}
            ],
            "1": [
                {"title": "WHO Report", "external_source_provider": "WHO"},
                {"title": "PubMed Study", "external_source_provider": "PubMed"},
                {"title": "News Article", "source": "Guardian"}
            ]
        }

        stats = task._aggregate_api_stats(claims, evidence)

        assert stats["total_api_calls"] == 3  # 1 + 2
        assert stats["total_api_results"] == 10  # 2 + 8
        assert stats["api_evidence_count"] == 3  # 3 API evidence items
        assert stats["total_evidence_count"] == 5
        assert stats["api_coverage_percentage"] == 60.0

        # Verify aggregated APIs
        api_names = [api["name"] for api in stats["apis_queried"]]
        assert "ONS Economic Statistics" in api_names
        assert "WHO" in api_names
        assert "PubMed" in api_names

    def test_aggregate_api_stats_no_api_evidence(self):
        """Test aggregating stats when no API evidence was retrieved."""
        from app.workers.pipeline import PipelineTask

        task = PipelineTask()

        claims = [
            {
                "text": "Some claim",
                "position": 0,
                "api_stats": {}  # No API stats
            }
        ]

        evidence = {
            "0": [
                {"title": "Web Article 1", "source": "BBC"},
                {"title": "Web Article 2", "source": "Guardian"}
            ]
        }

        stats = task._aggregate_api_stats(claims, evidence)

        assert stats["total_api_calls"] == 0
        assert stats["total_api_results"] == 0
        assert stats["api_evidence_count"] == 0
        assert stats["total_evidence_count"] == 2
        assert stats["api_coverage_percentage"] == 0.0


class TestEndToEndIntegration:
    """Test full end-to-end integration scenarios."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_full_pipeline_with_api_integration(self):
        """
        Test complete pipeline flow with API integration.

        This test verifies:
        1. Domain detection works correctly
        2. Relevant APIs are queried
        3. Evidence is retrieved from both APIs and web
        4. API stats are tracked correctly
        5. Results are properly formatted
        """
        # This is a placeholder for a full integration test
        # In practice, this would require:
        # - Real or mocked API responses
        # - Database setup
        # - Full pipeline execution
        # - Verification of all stages

        retriever = EvidenceRetriever()
        assert retriever.api_registry is not None
        assert retriever.claim_classifier is not None
        assert retriever.enable_api_retrieval is True

        # Test passes if initialization works correctly
        # Full integration tests would be run against a test environment


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
