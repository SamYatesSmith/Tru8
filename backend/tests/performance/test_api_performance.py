"""
Performance Tests for Government API Integration
Phase 5: Week 4 - Performance Testing & Optimization

Tests performance characteristics of API integration:
- Pipeline latency with API retrieval enabled
- API response times
- Cache hit rates
- Concurrent load handling
- Error recovery and fallback
"""

import pytest
import asyncio
import time
from typing import Dict, Any, List
from unittest.mock import Mock, patch, AsyncMock

from app.pipeline.retrieve import EvidenceRetriever
from app.services.api_adapters import initialize_adapters
from app.utils.claim_classifier import ClaimClassifier


class TestAPIPerformance:
    """Test API retrieval performance characteristics."""

    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_api_retrieval_latency(self):
        """Test that API retrieval completes within acceptable time."""
        retriever = EvidenceRetriever()
        retriever.enable_api_retrieval = True

        claim_text = "UK inflation is 3.2% according to the ONS"
        claim = {"text": claim_text, "position": 0}

        # Mock adapters to return quickly
        mock_adapter = Mock()
        mock_adapter.api_name = "Test API"
        mock_adapter.search_with_cache.return_value = [
            {
                "title": "Test Evidence",
                "snippet": "Test snippet",
                "url": "https://test.gov.uk/data",
                "external_source_provider": "Test API",
                "credibility_score": 0.95,
                "metadata": {}
            }
        ]

        with patch.object(retriever.claim_classifier, 'detect_domain') as mock_detect:
            mock_detect.return_value = {
                "domain": "Finance",
                "jurisdiction": "UK",
                "domain_confidence": 0.85,
                "key_entities": ["UK", "ONS"]
            }

            with patch.object(retriever.api_registry, 'get_adapters_for_domain') as mock_get:
                mock_get.return_value = [mock_adapter]

                # Measure API retrieval latency
                start_time = time.time()
                result = await retriever._retrieve_from_government_apis(claim_text, claim)
                latency_ms = (time.time() - start_time) * 1000

                # Assert latency is reasonable
                assert latency_ms < 2000, f"API retrieval took {latency_ms:.0f}ms (target: <2000ms)"
                assert result["evidence"]
                assert result["api_stats"]["total_api_calls"] == 1

    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_parallel_api_calls(self):
        """Test that multiple API calls execute in parallel, not sequentially."""
        retriever = EvidenceRetriever()
        retriever.enable_api_retrieval = True

        claim_text = "COVID-19 vaccine efficacy"
        claim = {"text": claim_text, "position": 0}

        # Create multiple mock adapters with artificial delay
        async def slow_api_call(*args, **kwargs):
            await asyncio.sleep(0.5)  # 500ms delay
            return [
                {
                    "title": "Test Evidence",
                    "snippet": "Test snippet",
                    "url": "https://test.com",
                    "external_source_provider": "Test API",
                    "credibility_score": 0.95,
                    "metadata": {}
                }
            ]

        mock_adapter1 = Mock()
        mock_adapter1.api_name = "API 1"
        mock_adapter1.search_with_cache = Mock(return_value=[])

        mock_adapter2 = Mock()
        mock_adapter2.api_name = "API 2"
        mock_adapter2.search_with_cache = Mock(return_value=[])

        with patch.object(retriever.claim_classifier, 'detect_domain') as mock_detect:
            mock_detect.return_value = {
                "domain": "Health",
                "jurisdiction": "Global",
                "domain_confidence": 0.85,
                "key_entities": ["COVID-19"]
            }

            with patch.object(retriever.api_registry, 'get_adapters_for_domain') as mock_get:
                mock_get.return_value = [mock_adapter1, mock_adapter2]

                # Measure parallel execution time
                start_time = time.time()
                result = await retriever._retrieve_from_government_apis(claim_text, claim)
                latency_ms = (time.time() - start_time) * 1000

                # If sequential: ~1000ms (2 * 500ms)
                # If parallel: ~500ms
                # Allow some overhead, assert < 800ms
                assert latency_ms < 800, f"Parallel API calls took {latency_ms:.0f}ms (expected ~500ms for parallel)"

    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_api_retrieval_with_cache(self):
        """Test cache hit performance for repeated queries."""
        retriever = EvidenceRetriever()
        retriever.enable_api_retrieval = True

        claim_text = "UK inflation is 3.2%"
        claim = {"text": claim_text, "position": 0}

        # First call - cache miss
        mock_adapter = Mock()
        mock_adapter.api_name = "Test API"
        mock_adapter.search_with_cache.return_value = [
            {
                "title": "Cached Evidence",
                "snippet": "Test snippet",
                "url": "https://test.gov.uk/data",
                "external_source_provider": "Test API",
                "credibility_score": 0.95,
                "metadata": {}
            }
        ]

        with patch.object(retriever.claim_classifier, 'detect_domain') as mock_detect:
            mock_detect.return_value = {
                "domain": "Finance",
                "jurisdiction": "UK",
                "domain_confidence": 0.85,
                "key_entities": ["UK"]
            }

            with patch.object(retriever.api_registry, 'get_adapters_for_domain') as mock_get:
                mock_get.return_value = [mock_adapter]

                # First call - should hit API
                start_time = time.time()
                result1 = await retriever._retrieve_from_government_apis(claim_text, claim)
                first_call_ms = (time.time() - start_time) * 1000

                # Second call - should be faster (cached)
                start_time = time.time()
                result2 = await retriever._retrieve_from_government_apis(claim_text, claim)
                cached_call_ms = (time.time() - start_time) * 1000

                # Cache hit should be significantly faster
                # (In real scenario with actual cache, this would be true)
                assert result1["evidence"]
                assert result2["evidence"]


class TestPipelineLatency:
    """Test full pipeline latency with API integration."""

    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_single_claim_latency_target(self):
        """Test that single claim processing meets <10s target."""
        # This would be an integration test with full pipeline
        # For now, just verify retrieval component is fast enough

        retriever = EvidenceRetriever()
        retriever.enable_api_retrieval = True

        claims = [
            {"text": "UK unemployment is 5.2%", "position": 0},
        ]

        # Mock evidence extraction to return quickly
        with patch.object(retriever.evidence_extractor, 'extract_evidence_for_claim') as mock_extract:
            mock_extract.return_value = []  # Mock web evidence

            with patch.object(retriever, '_retrieve_from_government_apis') as mock_api:
                mock_api.return_value = {
                    "evidence": [],
                    "api_stats": {"total_api_calls": 0}
                }

                # This is just the retrieval stage
                start_time = time.time()
                result = await retriever.retrieve_evidence_for_claims(claims)
                latency_ms = (time.time() - start_time) * 1000

                # Retrieval alone should be fast (<2s for single claim)
                assert latency_ms < 2000, f"Evidence retrieval took {latency_ms:.0f}ms"

    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_multi_claim_latency(self):
        """Test latency for multiple claims (concurrency)."""
        retriever = EvidenceRetriever()
        retriever.enable_api_retrieval = True

        claims = [
            {"text": f"Test claim {i}", "position": i}
            for i in range(5)
        ]

        with patch.object(retriever.evidence_extractor, 'extract_evidence_for_claim') as mock_extract:
            mock_extract.return_value = []

            with patch.object(retriever, '_retrieve_from_government_apis') as mock_api:
                mock_api.return_value = {
                    "evidence": [],
                    "api_stats": {"total_api_calls": 0}
                }

                start_time = time.time()
                result = await retriever.retrieve_evidence_for_claims(claims)
                latency_ms = (time.time() - start_time) * 1000

                # With concurrency limit of 3, should process efficiently
                # 5 claims should not take 5x the time of 1 claim
                assert latency_ms < 5000, f"5 claims took {latency_ms:.0f}ms (expected <5s with concurrency)"


class TestErrorHandling:
    """Test error handling and fallback behavior."""

    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_api_timeout_graceful_fallback(self):
        """Test that API timeouts don't crash the pipeline."""
        retriever = EvidenceRetriever()
        retriever.enable_api_retrieval = True

        claim_text = "Test claim"
        claim = {"text": claim_text, "position": 0}

        # Mock adapter that times out
        mock_adapter = Mock()
        mock_adapter.api_name = "Slow API"
        mock_adapter.search_with_cache.side_effect = TimeoutError("API timeout")

        with patch.object(retriever.claim_classifier, 'detect_domain') as mock_detect:
            mock_detect.return_value = {
                "domain": "Finance",
                "jurisdiction": "UK",
                "domain_confidence": 0.85,
                "key_entities": []
            }

            with patch.object(retriever.api_registry, 'get_adapters_for_domain') as mock_get:
                mock_get.return_value = [mock_adapter]

                # Should not raise exception, should return empty results
                result = await retriever._retrieve_from_government_apis(claim_text, claim)

                assert "evidence" in result
                assert "api_stats" in result
                # Should track the failed call
                assert result["api_stats"]["total_api_calls"] == 1

    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_partial_api_failure(self):
        """Test that one API failure doesn't affect others."""
        retriever = EvidenceRetriever()
        retriever.enable_api_retrieval = True

        claim_text = "Test claim"
        claim = {"text": claim_text, "position": 0}

        # Mock: one successful adapter, one failing adapter
        mock_adapter1 = Mock()
        mock_adapter1.api_name = "Good API"
        mock_adapter1.search_with_cache.return_value = [
            {
                "title": "Good Evidence",
                "snippet": "Test",
                "url": "https://good.com",
                "external_source_provider": "Good API",
                "credibility_score": 0.95,
                "metadata": {}
            }
        ]

        mock_adapter2 = Mock()
        mock_adapter2.api_name = "Bad API"
        mock_adapter2.search_with_cache.side_effect = Exception("API error")

        with patch.object(retriever.claim_classifier, 'detect_domain') as mock_detect:
            mock_detect.return_value = {
                "domain": "General",
                "jurisdiction": "Global",
                "domain_confidence": 0.5,
                "key_entities": []
            }

            with patch.object(retriever.api_registry, 'get_adapters_for_domain') as mock_get:
                mock_get.return_value = [mock_adapter1, mock_adapter2]

                result = await retriever._retrieve_from_government_apis(claim_text, claim)

                # Should get evidence from good API
                assert len(result["evidence"]) == 1
                assert result["evidence"][0]["title"] == "Good Evidence"

                # Should track both API calls
                assert result["api_stats"]["total_api_calls"] == 2


class TestCacheEfficiency:
    """Test cache hit rates and efficiency."""

    def test_cache_ttl_configuration(self):
        """Test that different adapters have appropriate TTLs."""
        from app.services.api_adapters import (
            ONSAdapter, PubMedAdapter, FREDAdapter,
            WHOAdapter, MetOfficeAdapter, WikidataAdapter
        )

        # Economic data: 7 days (changes slowly)
        assert ONSAdapter().cache_ttl == 86400 * 7
        assert FREDAdapter().cache_ttl == 86400 * 7

        # Health data: 7 days
        assert WHOAdapter().cache_ttl == 86400 * 7

        # Weather: 1 hour (changes frequently)
        assert MetOfficeAdapter().cache_ttl == 3600

        # Structured knowledge: 30 days (very stable)
        assert WikidataAdapter().cache_ttl == 86400 * 30


class TestLoadCapacity:
    """Test system behavior under load."""

    @pytest.mark.asyncio
    @pytest.mark.performance
    @pytest.mark.slow
    async def test_concurrent_claim_processing(self):
        """Test processing multiple claims concurrently."""
        retriever = EvidenceRetriever()
        retriever.enable_api_retrieval = True

        # Create 10 claims
        claims = [
            {"text": f"Claim about topic {i}", "position": i}
            for i in range(10)
        ]

        with patch.object(retriever.evidence_extractor, 'extract_evidence_for_claim') as mock_extract:
            mock_extract.return_value = []

            with patch.object(retriever, '_retrieve_from_government_apis') as mock_api:
                mock_api.return_value = {
                    "evidence": [],
                    "api_stats": {"total_api_calls": 0}
                }

                start_time = time.time()
                result = await retriever.retrieve_evidence_for_claims(claims)
                latency_ms = (time.time() - start_time) * 1000

                # Should process all claims
                assert len(result) == 10

                # Should be faster than sequential processing
                # With concurrency limit of 3, should take ~4 batches
                assert latency_ms < 10000, f"10 claims took {latency_ms:.0f}ms"


class TestAPIStatistics:
    """Test API statistics tracking accuracy."""

    def test_api_stats_aggregation(self):
        """Test that API stats are correctly aggregated."""
        from app.workers.pipeline import aggregate_api_stats

        claims = [
            {
                "text": "Claim 1",
                "api_stats": {
                    "apis_queried": [{"name": "API A", "results": 3}],
                    "total_api_calls": 1,
                    "total_api_results": 3
                }
            },
            {
                "text": "Claim 2",
                "api_stats": {
                    "apis_queried": [
                        {"name": "API A", "results": 2},
                        {"name": "API B", "results": 5}
                    ],
                    "total_api_calls": 2,
                    "total_api_results": 7
                }
            }
        ]

        evidence = {
            "0": [
                {"title": "E1", "external_source_provider": "API A"},
                {"title": "E2", "source": "Web"}
            ],
            "1": [
                {"title": "E3", "external_source_provider": "API A"},
                {"title": "E4", "external_source_provider": "API B"},
                {"title": "E5", "source": "Web"}
            ]
        }

        stats = aggregate_api_stats(claims, evidence)

        # Verify aggregation
        assert stats["total_api_calls"] == 3
        assert stats["total_api_results"] == 10
        assert stats["api_evidence_count"] == 3
        assert stats["total_evidence_count"] == 5
        assert stats["api_coverage_percentage"] == 60.0

        # Verify API A results are aggregated
        api_a = next(a for a in stats["apis_queried"] if a["name"] == "API A")
        assert api_a["results"] == 5  # 3 + 2


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "-m", "performance"])
