"""
Tests for Frozen Evidence Replay feature (v2).

Verifies that when claims have `frozen_evidence` attached, the pipeline:
- Skips ALL network calls (web search, gov APIs, page extraction)
- Reconstructs ranked_evidence from frozen data
- Runs evidence filters on the reconstructed evidence
- Returns correct search_mode and pre_weighting_evidence
- Takes priority over frozen_urls when both are present
- Matches claims by sha1(normalized_text) key
"""

import asyncio
import hashlib
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.pipeline.retrieve import EvidenceRetriever


@pytest.fixture
def retriever():
    """Create an EvidenceRetriever with mocked services."""
    with patch("app.pipeline.retrieve.SearchService"), patch(
        "app.pipeline.retrieve.EvidenceExtractor"
    ) as mock_extractor_cls, patch(
        "app.pipeline.retrieve.get_api_registry"
    ) as mock_registry:
        mock_registry.return_value = MagicMock()
        ret = EvidenceRetriever()
        # Mock the evidence extractor's _extract_from_page
        ret.evidence_extractor._extract_from_page = AsyncMock()
        # Mock evidence filters to pass through
        ret._apply_evidence_filters = MagicMock(
            side_effect=lambda evidence, claim, **kw: (evidence, [])
        )
        # Mock embedding storage
        ret._store_evidence_embeddings = AsyncMock()
        # Mock gov API retrieval
        ret._retrieve_from_government_apis = AsyncMock(
            return_value={"evidence": [], "api_stats": {}}
        )
        # Mock API evidence converter
        ret._convert_api_evidence_to_snippets = MagicMock(return_value=[])
        yield ret


def _make_frozen_evidence(
    url, text="Some evidence text", source="example.com", title="Test Title"
):
    """Create a frozen evidence dict matching pre-weighting format."""
    return {
        "url": url,
        "text": text,
        "source": source,
        "title": title,
        "relevance_score": 0.8,
        "published_date": "2026-01-15",
        "external_source_provider": None,
        "is_factcheck": False,
        "source_type": "news",
        "metadata": {},
    }


def _claim_key(text: str) -> str:
    """Compute stable claim key (same as runner.py)."""
    normalized = " ".join(text.lower().split())
    return hashlib.sha1(normalized.encode()).hexdigest()


@pytest.mark.asyncio
async def test_no_network_calls_when_frozen_evidence(retriever):
    """frozen_evidence on claim -> zero network calls, evidence returned."""
    frozen_items = [
        _make_frozen_evidence(
            "https://reuters.com/article1", "Reuters reports findings"
        ),
        _make_frozen_evidence("https://bbc.com/news/2", "BBC confirms data"),
    ]

    claim = {
        "text": "The speed of light is 299,792,458 m/s",
        "position": 0,
        "frozen_evidence": frozen_items,
    }

    semaphore = asyncio.Semaphore(3)
    result = await retriever._retrieve_evidence_for_single_claim(claim, semaphore)

    # No network calls should have been made
    retriever.evidence_extractor._extract_from_page.assert_not_called()
    retriever._retrieve_from_government_apis.assert_not_called()

    # Verify result structure
    assert result["search_mode"] == "frozen_evidence_replay"
    assert result["claim_position"] == 0
    assert len(result["filtered_evidence"]) == 2
    assert result["filtered_evidence"][0]["url"] == "https://reuters.com/article1"
    assert result["filtered_evidence"][1]["url"] == "https://bbc.com/news/2"


@pytest.mark.asyncio
async def test_evidence_filters_runs(retriever):
    """Frozen evidence goes through _apply_evidence_filters."""
    frozen_items = [
        _make_frozen_evidence("https://reuters.com/article1"),
    ]

    claim = {
        "text": "Test claim",
        "position": 0,
        "frozen_evidence": frozen_items,
    }

    semaphore = asyncio.Semaphore(3)
    await retriever._retrieve_evidence_for_single_claim(claim, semaphore)

    # Evidence filters should have been called
    retriever._apply_evidence_filters.assert_called_once()
    call_args = retriever._apply_evidence_filters.call_args
    ranked_evidence = call_args[0][0]
    assert len(ranked_evidence) == 1
    assert ranked_evidence[0]["url"] == "https://reuters.com/article1"
    assert ranked_evidence[0]["text"] == "Some evidence text"


@pytest.mark.asyncio
async def test_empty_frozen_evidence(retriever):
    """Empty frozen_evidence list -> empty results + correct search_mode."""
    claim = {
        "text": "Some claim",
        "position": 0,
        "frozen_evidence": [],
    }

    semaphore = asyncio.Semaphore(3)
    result = await retriever._retrieve_evidence_for_single_claim(claim, semaphore)

    assert result["filtered_evidence"] == []
    assert result["search_mode"] == "frozen_evidence_replay"
    assert result["pre_weighting_evidence"] == []
    retriever._apply_evidence_filters.assert_not_called()


@pytest.mark.asyncio
async def test_search_mode_tag(retriever):
    """Return dict has search_mode='frozen_evidence_replay'."""
    frozen_items = [
        _make_frozen_evidence("https://example.com/page"),
    ]

    claim = {
        "text": "Test claim",
        "position": 0,
        "frozen_evidence": frozen_items,
    }

    semaphore = asyncio.Semaphore(3)
    result = await retriever._retrieve_evidence_for_single_claim(claim, semaphore)

    assert result["search_mode"] == "frozen_evidence_replay"


@pytest.mark.asyncio
async def test_pre_weighting_evidence_in_return(retriever):
    """Return dict includes pre_weighting_evidence with full evidence dicts."""
    frozen_items = [
        _make_frozen_evidence("https://reuters.com/article1", "Evidence text 1"),
        _make_frozen_evidence("https://bbc.com/news/2", "Evidence text 2"),
    ]

    claim = {
        "text": "Test claim for pre-weighting",
        "position": 0,
        "frozen_evidence": frozen_items,
    }

    semaphore = asyncio.Semaphore(3)
    result = await retriever._retrieve_evidence_for_single_claim(claim, semaphore)

    pre_weighting = result["pre_weighting_evidence"]
    assert len(pre_weighting) == 2
    assert pre_weighting[0]["url"] == "https://reuters.com/article1"
    assert pre_weighting[0]["text"] == "Evidence text 1"
    assert pre_weighting[1]["url"] == "https://bbc.com/news/2"
    # Pre-weighting should have the reconstructed fields
    assert "relevance_score" in pre_weighting[0]
    assert "word_count" in pre_weighting[0]


@pytest.mark.asyncio
async def test_frozen_evidence_takes_priority_over_frozen_urls(retriever):
    """If both frozen_evidence and frozen_urls on claim, frozen_evidence wins."""
    frozen_evidence = [
        _make_frozen_evidence(
            "https://reuters.com/frozen-evidence", "Frozen evidence text"
        ),
    ]
    frozen_urls = [
        {
            "url": "https://bbc.com/frozen-url",
            "title": "Frozen URL",
            "snippet": "URL text",
        },
    ]

    claim = {
        "text": "Test claim with both",
        "position": 0,
        "frozen_evidence": frozen_evidence,
        "frozen_urls": frozen_urls,
    }

    semaphore = asyncio.Semaphore(3)
    result = await retriever._retrieve_evidence_for_single_claim(claim, semaphore)

    # Should use frozen_evidence path, not frozen_urls
    assert result["search_mode"] == "frozen_evidence_replay"
    assert len(result["filtered_evidence"]) == 1
    assert (
        result["filtered_evidence"][0]["url"] == "https://reuters.com/frozen-evidence"
    )
    # No page extraction should have happened (frozen_urls would trigger extraction)
    retriever.evidence_extractor._extract_from_page.assert_not_called()


@pytest.mark.asyncio
async def test_frozen_evidence_reconstructs_fields(retriever):
    """Frozen evidence items are reconstructed with all expected fields."""
    frozen_items = [
        {
            "url": "https://example.com/page",
            "text": "Full evidence text here",
            "source": "example.com",
            "title": "Example Page",
            "relevance_score": 0.75,
            "published_date": "2026-01-10",
            "is_factcheck": True,
            "source_type": "factcheck",
            "external_source_provider": "google_factcheck",
            "metadata": {"claim_reviewed": "test"},
        }
    ]

    claim = {
        "text": "Test reconstruction",
        "position": 0,
        "frozen_evidence": frozen_items,
    }

    semaphore = asyncio.Semaphore(3)
    result = await retriever._retrieve_evidence_for_single_claim(claim, semaphore)

    ev = result["filtered_evidence"][0]
    assert ev["url"] == "https://example.com/page"
    assert ev["text"] == "Full evidence text here"
    assert ev["is_factcheck"] is True
    assert ev["source_type"] == "factcheck"
    assert ev["external_source_provider"] == "google_factcheck"
    assert ev["word_count"] == 4  # "Full evidence text here"


class TestClaimKeyMatching:
    """Test that runner matches frozen evidence by sha1(normalized_claim_text)."""

    def test_claim_key_deterministic(self):
        """Same text produces same key."""
        key1 = _claim_key("The speed of light is constant")
        key2 = _claim_key("The speed of light is constant")
        assert key1 == key2

    def test_claim_key_normalization(self):
        """Extra whitespace and casing are normalized."""
        key1 = _claim_key("The  speed   of light")
        key2 = _claim_key("the speed of light")
        assert key1 == key2

    def test_claim_key_different_text(self):
        """Different text produces different key."""
        key1 = _claim_key("Claim A")
        key2 = _claim_key("Claim B")
        assert key1 != key2
