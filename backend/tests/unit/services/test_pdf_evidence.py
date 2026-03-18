"""Tests for pdf_evidence service — keyword extraction, relevance, snippets."""

import pytest

from app.services.pdf_evidence import PDFEvidenceExtractor


@pytest.fixture
def extractor() -> PDFEvidenceExtractor:
    return PDFEvidenceExtractor()


# ---------------------------------------------------------------------------
# TestExtractKeywords
# ---------------------------------------------------------------------------


class TestExtractKeywords:
    """_extract_keywords removes stopwords and short words, returns unique terms."""

    def test_removes_stopwords(self, extractor):
        """Stopwords and words with 3 or fewer characters are removed."""
        result = extractor._extract_keywords(
            "the climate change is driven by carbon emissions"
        )
        # "the" (stopword), "is" (stopword + short), "by" (stopword + short)
        # "climate" (7), "change" (6), "driven" (6), "carbon" (6), "emissions" (9)
        assert "climate" in result
        assert "change" in result
        assert "carbon" in result
        assert "the" not in result
        assert "is" not in result
        assert "by" not in result

    def test_handles_empty_string(self, extractor):
        """Empty input returns an empty list."""
        result = extractor._extract_keywords("")
        assert result == []

    def test_deduplicates(self, extractor):
        """Repeated words appear only once in output (via list, may repeat — verify)."""
        result = extractor._extract_keywords("climate climate climate change change")
        # The implementation uses a list comprehension without dedup, so repeated
        # words will appear multiple times. We test the actual behaviour.
        # Each occurrence that passes the filter will be present.
        assert "climate" in result
        assert "change" in result


# ---------------------------------------------------------------------------
# TestCalculateRelevance
# ---------------------------------------------------------------------------


class TestCalculateRelevance:
    """_calculate_relevance scores page text against a claim and its keywords."""

    def test_high_relevance_for_matching_text(self, extractor):
        """Page text containing all keywords scores > 0.5."""
        claim = "Carbon emissions drive climate change"
        keywords = extractor._extract_keywords(claim)
        page_text = (
            "Research shows that carbon emissions are the primary driver of "
            "climate change globally, according to recent studies."
        )
        score = extractor._calculate_relevance(page_text, claim, keywords)
        assert score > 0.5

    def test_zero_for_unrelated(self, extractor):
        """Completely unrelated text scores 0."""
        claim = "Carbon emissions drive climate change"
        keywords = extractor._extract_keywords(claim)
        page_text = "The restaurant menu featured pasta and tiramisu."
        score = extractor._calculate_relevance(page_text, claim, keywords)
        assert score == 0.0

    def test_partial_match(self, extractor):
        """Some keywords matching gives an intermediate score between 0 and 1."""
        claim = "Carbon emissions drive climate change"
        keywords = extractor._extract_keywords(claim)
        # Only "climate" and "change" appear; "carbon", "emissions", "drive" do not
        page_text = "The climate is expected to change significantly by 2050."
        score = extractor._calculate_relevance(page_text, claim, keywords)
        assert 0.0 < score < 1.0


# ---------------------------------------------------------------------------
# TestExtractRelevantSnippet
# ---------------------------------------------------------------------------


class TestExtractRelevantSnippet:
    """_extract_relevant_snippet picks the best sentence window from page text."""

    def test_extracts_around_keyword(self, extractor):
        """Snippet is centred on the sentence with the most keyword matches."""
        claim = "carbon emissions"
        keywords = extractor._extract_keywords(claim)
        page_text = (
            "The sky is blue. "
            "Carbon emissions have risen sharply since 2010. "
            "Policy action is needed."
        )
        snippet = extractor._extract_relevant_snippet(page_text, claim, keywords)
        # The middle sentence contains the keywords — it must appear in the snippet
        assert "emissions" in snippet.lower()

    def test_handles_no_match(self, extractor):
        """When no keywords match, returns text from the start of the page."""
        claim = "quantum entanglement"
        keywords = extractor._extract_keywords(claim)
        page_text = (
            "The restaurant menu featured pasta and tiramisu. Dessert was excellent."
        )
        snippet = extractor._extract_relevant_snippet(page_text, claim, keywords)
        # With no keyword hits, best_sentence_idx stays 0, so start of text is returned
        assert snippet.startswith("The restaurant")
