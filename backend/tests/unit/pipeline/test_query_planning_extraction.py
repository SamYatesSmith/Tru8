"""
Query Planning Content Extraction Tests

Tests the fix for query planning content extraction bypass.
Ensures that _execute_planned_queries() properly extracts page content
instead of returning raw search snippets.

Created: 2025-11-28
Issue: Query Planning was bypassing content extraction, returning meta-descriptions
Fix: Now calls _extract_from_page() for each search result with nuanced fallback policy
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import asyncio

from app.pipeline.retrieve import EvidenceRetriever
from app.services.search import SearchResult
from app.services.evidence import EvidenceSnippet


@pytest.fixture
def retriever():
    """Create an EvidenceRetriever with mocked dependencies."""
    with patch('app.pipeline.retrieve.SearchService'), \
         patch('app.pipeline.retrieve.EvidenceExtractor'), \
         patch('app.pipeline.retrieve.get_api_registry'):
        retriever = EvidenceRetriever()
        # Set max_concurrent for semaphore
        retriever.evidence_extractor.max_concurrent = 3
        return retriever


@pytest.fixture
def mock_search_result():
    """Create a mock SearchResult."""
    return SearchResult(
        title="Arsenal top Premier League table",
        url="https://example.com/arsenal-top",
        snippet="View the latest Arsenal statistics and standings...",  # Meta description
        published_date="2025-11-28",
        source="example.com"
    )


@pytest.fixture
def mock_extracted_snippet():
    """Create a mock EvidenceSnippet with actual extracted content."""
    return EvidenceSnippet(
        text="Arsenal extended their lead at the top of the Premier League to six points after a 2-0 victory over Manchester United on Sunday.",
        source="example.com",
        url="https://example.com/arsenal-top",
        title="Arsenal top Premier League table",
        published_date="2025-11-28",
        relevance_score=0.85,
        metadata={}
    )


@pytest.mark.unit
@pytest.mark.asyncio
class TestQueryPlanningExtraction:
    """Test that Query Planning path properly extracts page content."""

    async def test_execute_planned_queries_calls_content_extraction(
        self, retriever, mock_search_result, mock_extracted_snippet
    ):
        """
        Test: _execute_planned_queries calls content extraction instead of
        directly wrapping search snippets.

        This is the CRITICAL fix - verifies the bug is resolved.
        """
        # Arrange
        retriever.evidence_extractor.search_service.search_for_evidence = AsyncMock(
            return_value=[mock_search_result]
        )
        retriever.evidence_extractor._extract_from_page = AsyncMock(
            return_value=mock_extracted_snippet
        )

        query_plan = {
            "queries": ["Arsenal Premier League standings November 2025"],
            "claim_type": "league_standing",
            "priority_sources": ["premierleague.com"]
        }

        # Act
        results = await retriever._execute_planned_queries(
            claim_text="Arsenal is top of the Premier League",
            query_plan=query_plan
        )

        # Assert
        # Verify content extraction was called
        retriever.evidence_extractor._extract_from_page.assert_called()

        # Verify we got extracted content, not the search snippet
        assert len(results) == 1
        assert "Arsenal extended their lead" in results[0].text
        assert "View the latest" not in results[0].text  # Not the meta description

    async def test_query_planning_preserves_metadata(
        self, retriever, mock_search_result, mock_extracted_snippet
    ):
        """
        Test: Query planning metadata is preserved through extraction.
        """
        # Arrange
        retriever.evidence_extractor.search_service.search_for_evidence = AsyncMock(
            return_value=[mock_search_result]
        )
        retriever.evidence_extractor._extract_from_page = AsyncMock(
            return_value=mock_extracted_snippet
        )

        query_plan = {
            "queries": ["test query"],
            "claim_type": "player_statistics",
            "priority_sources": []
        }

        # Act
        results = await retriever._execute_planned_queries(
            claim_text="Test claim",
            query_plan=query_plan
        )

        # Assert
        assert len(results) == 1
        metadata = results[0].metadata
        assert metadata.get("source_path") == "query_planning"
        assert metadata.get("claim_type") == "player_statistics"
        assert metadata.get("extraction_status") == "success"
        assert metadata.get("is_snippet_fallback") == False

    async def test_fallback_on_blocked_request(self, retriever, mock_search_result):
        """
        Test: When extraction fails with 403, use snippet as fallback.
        """
        # Arrange
        retriever.evidence_extractor.search_service.search_for_evidence = AsyncMock(
            return_value=[mock_search_result]
        )

        # Simulate 403 error
        async def raise_403(*args, **kwargs):
            raise Exception("403 Forbidden")

        retriever.evidence_extractor._extract_from_page = raise_403

        query_plan = {
            "queries": ["blocked query"],
            "claim_type": "general",
            "priority_sources": []
        }

        # Act
        with patch('app.pipeline.retrieve.settings') as mock_settings:
            mock_settings.ALLOW_SNIPPET_FALLBACK = True
            results = await retriever._execute_planned_queries(
                claim_text="Test claim",
                query_plan=query_plan
            )

        # Assert - should get fallback snippet
        assert len(results) == 1
        assert results[0].metadata.get("is_snippet_fallback") == True
        assert results[0].metadata.get("extraction_status") == "fallback_blocked"
        assert results[0].relevance_score == 0.4  # Lower score for fallback

    async def test_drop_empty_extraction(self, retriever, mock_search_result):
        """
        Test: When extraction succeeds but yields no content, drop the result.
        """
        # Arrange
        retriever.evidence_extractor.search_service.search_for_evidence = AsyncMock(
            return_value=[mock_search_result]
        )
        # Simulate empty extraction (JS-only page)
        retriever.evidence_extractor._extract_from_page = AsyncMock(return_value=None)

        query_plan = {
            "queries": ["empty page query"],
            "claim_type": "general",
            "priority_sources": []
        }

        # Act
        results = await retriever._execute_planned_queries(
            claim_text="Test claim",
            query_plan=query_plan
        )

        # Assert - should be empty (dropped)
        assert len(results) == 0

    async def test_fallback_disabled_drops_blocked(self, retriever, mock_search_result):
        """
        Test: When ALLOW_SNIPPET_FALLBACK=False, blocked requests are dropped.
        """
        # Arrange
        retriever.evidence_extractor.search_service.search_for_evidence = AsyncMock(
            return_value=[mock_search_result]
        )

        async def raise_403(*args, **kwargs):
            raise Exception("403 Forbidden")

        retriever.evidence_extractor._extract_from_page = raise_403

        query_plan = {
            "queries": ["blocked query"],
            "claim_type": "general",
            "priority_sources": []
        }

        # Act
        with patch('app.pipeline.retrieve.settings') as mock_settings:
            mock_settings.ALLOW_SNIPPET_FALLBACK = False
            results = await retriever._execute_planned_queries(
                claim_text="Test claim",
                query_plan=query_plan
            )

        # Assert - should be empty (dropped, no fallback)
        assert len(results) == 0

    async def test_multiple_queries_with_deduplication(self, retriever):
        """
        Test: Multiple queries deduplicate by URL before extraction.
        """
        # Arrange
        result1 = SearchResult(
            title="Article 1",
            url="https://example.com/same-url",
            snippet="Snippet 1",
            source="example.com"
        )
        result2 = SearchResult(
            title="Article 2",
            url="https://example.com/same-url",  # Duplicate URL
            snippet="Snippet 2",
            source="example.com"
        )
        result3 = SearchResult(
            title="Article 3",
            url="https://example.com/different-url",
            snippet="Snippet 3",
            source="example.com"
        )

        # Return different results for each query
        call_count = 0
        async def mock_search(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return [result1, result2]
            return [result3]

        retriever.evidence_extractor.search_service.search_for_evidence = mock_search

        extracted = EvidenceSnippet(
            text="Extracted content",
            source="example.com",
            url="",
            title="",
            relevance_score=0.8,
            metadata={}
        )
        retriever.evidence_extractor._extract_from_page = AsyncMock(return_value=extracted)

        query_plan = {
            "queries": ["query 1", "query 2"],
            "claim_type": "general",
            "priority_sources": []
        }

        # Act
        results = await retriever._execute_planned_queries(
            claim_text="Test claim",
            query_plan=query_plan
        )

        # Assert - should have 2 results (1 duplicate removed)
        # Extraction should be called twice (once per unique URL)
        assert retriever.evidence_extractor._extract_from_page.call_count == 2


@pytest.mark.unit
@pytest.mark.asyncio
class TestExtractWithFallback:
    """Test the _extract_with_fallback helper method."""

    async def test_successful_extraction(self, retriever, mock_search_result, mock_extracted_snippet):
        """Test successful content extraction preserves metadata."""
        # Attach query metadata
        mock_search_result._query_index = 0
        mock_search_result._query_used = "test query"
        mock_search_result._claim_type = "league_standing"

        retriever.evidence_extractor._extract_from_page = AsyncMock(
            return_value=mock_extracted_snippet
        )

        # Act
        semaphore = asyncio.Semaphore(3)
        result = await retriever._extract_with_fallback(
            mock_search_result,
            "Test claim",
            semaphore
        )

        # Assert
        assert result is not None
        assert result.metadata["query_index"] == 0
        assert result.metadata["query_used"] == "test query"
        assert result.metadata["claim_type"] == "league_standing"
        assert result.metadata["extraction_status"] == "success"
        assert result.metadata["is_snippet_fallback"] == False

    async def test_timeout_fallback(self, retriever, mock_search_result):
        """Test timeout triggers snippet fallback."""
        mock_search_result._query_index = 0
        mock_search_result._query_used = "test query"
        mock_search_result._claim_type = "general"

        async def raise_timeout(*args, **kwargs):
            raise Exception("Connection timeout")

        retriever.evidence_extractor._extract_from_page = raise_timeout

        # Act
        with patch('app.pipeline.retrieve.settings') as mock_settings:
            mock_settings.ALLOW_SNIPPET_FALLBACK = True
            semaphore = asyncio.Semaphore(3)
            result = await retriever._extract_with_fallback(
                mock_search_result,
                "Test claim",
                semaphore
            )

        # Assert
        assert result is not None
        assert result.metadata["extraction_status"] == "fallback_timeout"
        assert result.metadata["is_snippet_fallback"] == True
        assert result.relevance_score == 0.4

    async def test_other_error_drops(self, retriever, mock_search_result):
        """Test non-transient errors drop the result."""
        mock_search_result._query_index = 0
        mock_search_result._query_used = "test query"
        mock_search_result._claim_type = "general"

        async def raise_other(*args, **kwargs):
            raise Exception("Some other error")

        retriever.evidence_extractor._extract_from_page = raise_other

        # Act
        with patch('app.pipeline.retrieve.settings') as mock_settings:
            mock_settings.ALLOW_SNIPPET_FALLBACK = True
            semaphore = asyncio.Semaphore(3)
            result = await retriever._extract_with_fallback(
                mock_search_result,
                "Test claim",
                semaphore
            )

        # Assert - non-403/timeout errors should drop
        assert result is None
