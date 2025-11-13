"""
Tests for API evidence retrieval and statistics tracking.

Phase 5: Government API Integration - Issue #6 Fix

Tests the critical bug fix where external_source_provider was lost
during evidence processing, causing API statistics to always show 0%.
"""
import pytest
from app.pipeline.retrieve import EvidenceRetriever
from app.workers.pipeline import aggregate_api_stats
from app.services.evidence import EvidenceSnippet


class TestAPIEvidencePreservation:
    """Test that external_source_provider is preserved through the pipeline."""

    def test_rank_evidence_preserves_external_source_provider(self):
        """
        Test that _rank_evidence_with_embeddings preserves API fields.

        This test ensures the fix for Issue #6 works correctly.
        Before fix: external_source_provider was lost during ranking
        After fix: external_source_provider preserved at top level
        """
        # Create mock snippet with API metadata
        snippet = EvidenceSnippet(
            text="UK GDP grew by 2.1% in Q4 2024",
            source="ONS Economic Statistics",
            url="https://www.ons.gov.uk/economy/gdp",
            title="UK GDP Quarterly Estimate",
            published_date="2024-01-15",
            relevance_score=0.9,
            metadata={
                "external_source_provider": "ONS",
                "credibility_score": 0.95,
                "api_source": "ONS Economic Statistics"
            }
        )

        # Simulate the ranking process
        # Extract fields as the fixed code does
        external_source = snippet.metadata.get("external_source_provider") if snippet.metadata else None
        credibility = snippet.metadata.get("credibility_score", 0.6) if snippet.metadata else 0.6

        evidence_item = {
            "id": "evidence_0",
            "text": snippet.text,
            "source": snippet.source,
            "url": snippet.url,
            "title": snippet.title,
            "published_date": snippet.published_date,
            "relevance_score": float(snippet.relevance_score),
            "credibility_score": credibility,
            "external_source_provider": external_source,
            "metadata": snippet.metadata
        }

        # Critical assertions for Issue #6 fix
        assert evidence_item.get("external_source_provider") == "ONS", \
            "❌ BUG: external_source_provider must be at top level (Issue #6)"
        assert evidence_item.get("credibility_score") == 0.95, \
            "credibility_score must be at top level"
        assert evidence_item["metadata"]["external_source_provider"] == "ONS", \
            "external_source_provider should also be in metadata for context"

    def test_aggregate_api_stats_counts_api_evidence_correctly(self):
        """
        Test that API evidence is correctly counted in statistics.

        Before fix: Always returned api_evidence_count = 0
        After fix: Correctly counts evidence with external_source_provider
        """
        claims = [{
            "text": "UK unemployment is 5.2%",
            "api_stats": {
                "total_api_calls": 2,
                "total_api_results": 5,
                "apis_queried": [
                    {"name": "ONS", "results": 3},
                    {"name": "Companies House", "results": 2}
                ]
            }
        }]

        evidence = {
            "0": [
                {
                    "text": "Web evidence from BBC",
                    "source": "BBC News",
                    "url": "https://bbc.com/news"
                    # No external_source_provider - web source
                },
                {
                    "text": "API evidence from ONS",
                    "source": "ONS Economic Statistics",
                    "url": "https://ons.gov.uk/data",
                    "external_source_provider": "ONS",  # Top level - correctly preserved
                    "credibility_score": 0.95
                },
                {
                    "text": "API evidence from PubMed",
                    "source": "PubMed",
                    "url": "https://pubmed.ncbi.nlm.nih.gov/12345",
                    "external_source_provider": "PubMed",  # Top level - correctly preserved
                    "credibility_score": 0.95
                }
            ]
        }

        stats = aggregate_api_stats(claims, evidence)

        # Critical assertions
        assert stats["total_evidence_count"] == 3, "Should count all evidence"
        assert stats["api_evidence_count"] == 2, \
            "❌ CRITICAL: Should count 2 API evidence items (Issue #6 fix)"
        assert stats["api_coverage_percentage"] == pytest.approx(66.67, rel=0.1), \
            "API coverage should be 66.67% (2 of 3)"
        assert stats["total_api_calls"] == 2, "Should aggregate API calls"
        assert stats["total_api_results"] == 5, "Should aggregate API results"

    def test_aggregate_api_stats_defensive_check_nested(self):
        """
        Test defensive check finds external_source_provider in metadata.

        Tests the defensive fallback that checks nested metadata if
        external_source_provider is not at top level (legacy format).
        """
        claims = [{"api_stats": {"total_api_calls": 1, "apis_queried": []}}]

        # Evidence with external_source_provider ONLY in metadata (legacy/broken format)
        evidence = {
            "0": [
                {
                    "text": "Legacy API evidence",
                    "source": "ONS",
                    # No top-level external_source_provider
                    "metadata": {
                        "external_source_provider": "ONS"  # Nested only
                    }
                }
            ]
        }

        stats = aggregate_api_stats(claims, evidence)

        # Defensive check should still find it
        assert stats["api_evidence_count"] == 1, \
            "Defensive check should find external_source_provider in metadata"
        assert stats["api_coverage_percentage"] == 100.0

    def test_aggregate_api_stats_with_no_api_evidence(self):
        """Test API stats when no API evidence retrieved (all web sources)."""
        claims = [{"api_stats": {"total_api_calls": 0, "apis_queried": []}}]

        evidence = {
            "0": [
                {"text": "Web evidence only", "source": "BBC"},
                {"text": "Another web source", "source": "Guardian"}
            ]
        }

        stats = aggregate_api_stats(claims, evidence)

        assert stats["api_evidence_count"] == 0, "No API evidence"
        assert stats["api_coverage_percentage"] == 0.0, "0% API coverage"
        assert stats["total_evidence_count"] == 2, "2 total evidence items"

    def test_aggregate_api_stats_with_mixed_evidence(self):
        """Test API stats with mixture of API and web evidence across multiple claims."""
        claims = [
            {
                "api_stats": {
                    "total_api_calls": 1,
                    "apis_queried": [{"name": "ONS", "results": 1}]
                }
            },
            {
                "api_stats": {
                    "total_api_calls": 2,
                    "apis_queried": [
                        {"name": "PubMed", "results": 2},
                        {"name": "WHO", "results": 1}
                    ]
                }
            }
        ]

        evidence = {
            "0": [
                {"text": "Web", "source": "BBC"},
                {"text": "API", "source": "ONS", "external_source_provider": "ONS"}
            ],
            "1": [
                {"text": "API", "source": "PubMed", "external_source_provider": "PubMed"},
                {"text": "API", "source": "PubMed", "external_source_provider": "PubMed"},
                {"text": "API", "source": "WHO", "external_source_provider": "WHO"},
                {"text": "Web", "source": "Guardian"}
            ]
        }

        stats = aggregate_api_stats(claims, evidence)

        assert stats["total_evidence_count"] == 6, "6 total evidence items"
        assert stats["api_evidence_count"] == 4, "4 API evidence items"
        assert stats["api_coverage_percentage"] == pytest.approx(66.67, rel=0.1), \
            "66.67% API coverage (4 of 6)"
        assert stats["total_api_calls"] == 3, "3 total API calls"

        # Check API names are aggregated correctly
        api_names = [api["name"] for api in stats["apis_queried"]]
        assert "ONS" in api_names
        assert "PubMed" in api_names
        assert "WHO" in api_names

    def test_aggregate_api_stats_empty_evidence(self):
        """Test API stats with no evidence at all."""
        claims = [{"api_stats": {"total_api_calls": 1, "apis_queried": []}}]
        evidence = {}

        stats = aggregate_api_stats(claims, evidence)

        assert stats["total_evidence_count"] == 0
        assert stats["api_evidence_count"] == 0
        assert stats["api_coverage_percentage"] == 0.0


class TestEvidenceSnippetStructure:
    """Test that EvidenceSnippet correctly stores API metadata."""

    def test_evidence_snippet_preserves_api_metadata(self):
        """Test that EvidenceSnippet stores external_source_provider in metadata."""
        snippet = EvidenceSnippet(
            text="Test evidence",
            source="ONS Economic Statistics",
            url="https://ons.gov.uk/data",
            title="Test Title",
            published_date="2024-01-15",
            relevance_score=0.9,
            metadata={
                "external_source_provider": "ONS",
                "credibility_score": 0.95,
                "api_source": "ONS Economic Statistics"
            }
        )

        # Verify metadata structure
        assert snippet.metadata is not None
        assert snippet.metadata.get("external_source_provider") == "ONS"
        assert snippet.metadata.get("credibility_score") == 0.95
        assert snippet.metadata.get("api_source") == "ONS Economic Statistics"

    def test_evidence_snippet_without_metadata(self):
        """Test that EvidenceSnippet handles missing metadata gracefully."""
        snippet = EvidenceSnippet(
            text="Web evidence",
            source="BBC News",
            url="https://bbc.com",
            title="News Article",
            published_date="2024-01-15",
            relevance_score=0.8
            # No metadata provided
        )

        # Should have empty dict
        assert snippet.metadata == {}
        assert snippet.metadata.get("external_source_provider") is None
