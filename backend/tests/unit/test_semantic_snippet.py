"""
Unit tests for Semantic Snippet Extraction (Tier 1 Improvement)

Tests the semantic similarity-based snippet extraction which improves upon
word overlap matching for handling paraphrasing and synonyms.
"""

import pytest
from app.services.evidence import EvidenceExtractor
from unittest.mock import AsyncMock, Mock, patch


class TestSemanticSnippetExtraction:
    """Test semantic snippet extraction enhancement"""

    @pytest.fixture
    def extractor(self):
        """Create EvidenceExtractor instance"""
        return EvidenceExtractor()

    @pytest.mark.asyncio
    async def test_semantic_similarity_captures_synonyms(self, extractor):
        """Test: Semantic matching finds synonyms that word overlap misses"""
        claim = "Study shows vehicles reduce emissions"
        sentences = [
            "Background information here.",
            "Recent research indicates that electric cars significantly lower carbon output.",
            "The investigation found a 40% reduction.",
            "Other factors were also examined."
        ]

        # Mock embedding service
        mock_service = AsyncMock()
        mock_service.embed_text = AsyncMock(return_value=[0.1, 0.2, 0.3])
        mock_service.embed_batch = AsyncMock(return_value=[
            [0.1, 0.2, 0.3],  # Background
            [0.8, 0.85, 0.9],  # Research (high similarity)
            [0.7, 0.75, 0.8],  # Investigation
            [0.2, 0.25, 0.3]   # Other
        ])
        mock_service.compute_similarity = AsyncMock(side_effect=[0.3, 0.85, 0.75, 0.25])

        with patch('app.services.embeddings.get_embedding_service', new=AsyncMock(return_value=mock_service)):

            snippet = await extractor._extract_semantic_snippet(claim, sentences)

            # Should find "cars" even though claim says "vehicles"
            assert "electric cars" in snippet
            assert "40% reduction" in snippet or "lower carbon output" in snippet

    @pytest.mark.asyncio
    async def test_context_window_preserved(self, extractor):
        """Test: Includes context sentences before/after best match"""
        claim = "Company hired 500 employees"
        sentences = [
            "Background information here.",
            "The company expanded rapidly.",
            "They hired 500 new employees in Q1.",  # Best match
            "This was unprecedented.",
            "Future plans are unclear."
        ]

        mock_service = AsyncMock()
        mock_service.embed_text = AsyncMock(return_value=[0.1, 0.2, 0.3])
        mock_service.embed_batch = AsyncMock(return_value=[
            [0.1, 0.1, 0.1],  # Background
            [0.4, 0.4, 0.4],  # Expanded
            [0.9, 0.9, 0.9],  # Hired (best match)
            [0.3, 0.3, 0.3],  # Unprecedented
            [0.2, 0.2, 0.2]   # Future
        ])
        mock_service.compute_similarity = AsyncMock(side_effect=[0.1, 0.4, 0.9, 0.3, 0.2])

        with patch('app.services.embeddings.get_embedding_service', new=AsyncMock(return_value=mock_service)):
            with patch('app.core.config.settings.SNIPPET_CONTEXT_SENTENCES', 1):
                with patch('app.core.config.settings.SNIPPET_SEMANTIC_THRESHOLD', 0.65):
                    snippet = await extractor._extract_semantic_snippet(claim, sentences)

                    # Should include context sentence before or after
                    assert "500" in snippet
                    assert ("expanded rapidly" in snippet or "unprecedented" in snippet)

    @pytest.mark.asyncio
    async def test_threshold_filtering(self, extractor):
        """Test: Filters sentences below semantic threshold"""
        claim = "Climate change affects weather"
        sentences = [
            "The stock market rose today.",  # Irrelevant
            "Temperature patterns are shifting globally."  # Relevant
        ]

        mock_service = AsyncMock()
        mock_service.embed_text = AsyncMock(return_value=[0.1, 0.2, 0.3])
        mock_service.embed_batch = AsyncMock(return_value=[
            [0.1, 0.1, 0.1],  # Stock market (low similarity)
            [0.9, 0.9, 0.9]   # Temperature (high similarity)
        ])
        mock_service.compute_similarity = AsyncMock(side_effect=[0.2, 0.9])

        with patch('app.services.embeddings.get_embedding_service', new=AsyncMock(return_value=mock_service)):
            with patch('app.core.config.settings.SNIPPET_SEMANTIC_THRESHOLD', 0.65):
                with patch('app.core.config.settings.SNIPPET_CONTEXT_SENTENCES', 0):  # No context to isolate high-similarity sentence
                    snippet = await extractor._extract_semantic_snippet(claim, sentences)

                    # Should only include high-similarity sentence
                    assert "Temperature" in snippet
                    assert "stock market" not in snippet.lower()

    @pytest.mark.asyncio
    async def test_fallback_on_no_threshold_match(self, extractor):
        """Test: Returns best match even if below threshold"""
        claim = "Specific technical claim"
        sentences = [
            "Somewhat related content.",
            "Another marginally related sentence."
        ]

        mock_service = AsyncMock()
        mock_service.embed_text = AsyncMock(return_value=[0.1, 0.2, 0.3])
        mock_service.embed_batch = AsyncMock(return_value=[
            [0.4, 0.4, 0.4],  # Somewhat (0.5 similarity)
            [0.3, 0.3, 0.3]   # Another (0.4 similarity)
        ])
        mock_service.compute_similarity = AsyncMock(side_effect=[0.5, 0.4])

        with patch('app.services.embeddings.get_embedding_service', new=AsyncMock(return_value=mock_service)):
            with patch('app.core.config.settings.SNIPPET_SEMANTIC_THRESHOLD', 0.7):
                with patch('app.core.config.settings.SNIPPET_CONTEXT_SENTENCES', 2):
                    snippet = await extractor._extract_semantic_snippet(claim, sentences)

                    # Should return best match even though below threshold
                    assert snippet is not None
                    assert len(snippet) > 0

    @pytest.mark.asyncio
    async def test_max_length_enforcement(self, extractor):
        """Test: Enforces max snippet length"""
        claim = "Test claim"
        long_sentence = " ".join(["word"] * 300)  # Very long sentence
        sentences = [long_sentence]

        mock_service = AsyncMock()
        mock_service.embed_text = AsyncMock(return_value=[0.1, 0.2, 0.3])
        mock_service.embed_batch = AsyncMock(return_value=[[0.9, 0.9, 0.9]])
        mock_service.compute_similarity = AsyncMock(return_value=0.9)

        with patch('app.services.embeddings.get_embedding_service', new=AsyncMock(return_value=mock_service)):
            snippet = await extractor._extract_semantic_snippet(claim, sentences)

            # Should truncate to max_snippet_words
            word_count = len(snippet.split())
            assert word_count <= extractor.max_snippet_words

    @pytest.mark.asyncio
    async def test_filters_short_sentences(self, extractor):
        """Test: Skips very short sentences (<20 chars)"""
        claim = "Important claim"
        sentences = [
            "Hi.",  # Too short
            "This is a substantial sentence with enough content.",
            "Yes."  # Too short
        ]

        mock_service = AsyncMock()
        mock_service.embed_text = AsyncMock(return_value=[0.1, 0.2, 0.3])
        # Only substantial sentence should be embedded
        mock_service.embed_batch = AsyncMock(return_value=[[0.9, 0.9, 0.9]])
        mock_service.compute_similarity = AsyncMock(return_value=0.9)

        with patch('app.services.embeddings.get_embedding_service', new=AsyncMock(return_value=mock_service)):
            snippet = await extractor._extract_semantic_snippet(claim, sentences)

            # Should only include substantial sentence
            assert "substantial sentence" in snippet
            assert snippet.count("Hi") == 0
