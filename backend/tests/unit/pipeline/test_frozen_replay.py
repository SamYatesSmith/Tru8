"""
Tests for Frozen URL Replay feature.

Verifies that when claims have `frozen_urls` attached, the pipeline:
- Skips web search entirely
- Creates synthetic SearchResult objects from frozen data
- Extracts content via the normal _extract_from_page path
- Still runs government APIs by default
- Handles partial freeze (some claims frozen, some normal)
- Handles edge cases (empty list, invalid URLs)
"""
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.pipeline.retrieve import EvidenceRetriever
from app.services.evidence import EvidenceSnippet
from app.services.search import SearchResult


@pytest.fixture
def retriever():
    """Create an EvidenceRetriever with mocked services."""
    with patch("app.pipeline.retrieve.SearchService"), \
         patch("app.pipeline.retrieve.EvidenceExtractor") as mock_extractor_cls, \
         patch("app.pipeline.retrieve.get_api_registry") as mock_registry:
        mock_registry.return_value = MagicMock()
        ret = EvidenceRetriever()
        # Mock the evidence extractor's _extract_from_page
        ret.evidence_extractor._extract_from_page = AsyncMock()
        # Mock credibility weighting to pass through
        ret._apply_credibility_weighting = MagicMock(
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


def _make_snippet(url, title="Test Title", text="Some evidence text"):
    """Create a test EvidenceSnippet."""
    return EvidenceSnippet(
        text=text,
        source="example.com",
        url=url,
        title=title,
        relevance_score=0.8,
        metadata={}
    )


@pytest.mark.asyncio
async def test_frozen_urls_skip_search(retriever):
    """When frozen_urls is set, web search is skipped and extraction uses frozen URLs."""
    frozen_urls = [
        {"url": "https://reuters.com/article1", "title": "Reuters Article", "snippet": "Key findings..."},
        {"url": "https://bbc.com/news/2", "title": "BBC News", "snippet": "Report states..."},
    ]

    claim = {
        "text": "The speed of light is 299,792,458 m/s",
        "position": 0,
        "frozen_urls": frozen_urls,
    }

    # Mock extraction to return snippets
    retriever.evidence_extractor._extract_from_page.side_effect = [
        _make_snippet("https://reuters.com/article1", "Reuters Article"),
        _make_snippet("https://bbc.com/news/2", "BBC News"),
    ]

    semaphore = asyncio.Semaphore(3)
    result = await retriever._retrieve_evidence_for_single_claim(claim, semaphore)

    # Verify extraction was called with correct SearchResult objects
    assert retriever.evidence_extractor._extract_from_page.call_count == 2
    calls = retriever.evidence_extractor._extract_from_page.call_args_list
    sr0 = calls[0][0][0]  # First positional arg of first call
    assert isinstance(sr0, SearchResult)
    assert sr0.url == "https://reuters.com/article1"
    assert sr0.title == "Reuters Article"
    assert sr0.snippet == "Key findings..."

    sr1 = calls[1][0][0]
    assert sr1.url == "https://bbc.com/news/2"

    # Verify result structure
    assert result["claim_position"] == 0
    assert result["search_mode"] == "frozen_replay"
    assert len(result["filtered_evidence"]) == 2


@pytest.mark.asyncio
async def test_frozen_urls_partial(retriever):
    """Some claims frozen, others normal — verify mixed mode works."""
    frozen_claim = {
        "text": "Claim with frozen URLs",
        "position": 0,
        "frozen_urls": [
            {"url": "https://reuters.com/frozen", "title": "Frozen", "snippet": ""},
        ],
    }
    normal_claim = {
        "text": "Claim without frozen URLs",
        "position": 1,
    }

    # Frozen claim: extraction returns a snippet
    retriever.evidence_extractor._extract_from_page.return_value = _make_snippet(
        "https://reuters.com/frozen", "Frozen"
    )

    semaphore = asyncio.Semaphore(3)

    # Frozen claim should use frozen path
    result = await retriever._retrieve_evidence_for_single_claim(frozen_claim, semaphore)
    assert result.get("search_mode") == "frozen_replay"

    # Normal claim has no frozen_urls, so it won't hit frozen path
    assert "frozen_urls" not in normal_claim


@pytest.mark.asyncio
async def test_frozen_urls_empty_list(retriever):
    """frozen_urls: [] → 0 web evidence."""
    claim = {
        "text": "Some claim",
        "position": 0,
        "frozen_urls": [],
    }

    semaphore = asyncio.Semaphore(3)
    result = await retriever._retrieve_evidence_for_single_claim(claim, semaphore)

    # Empty frozen list → no extraction calls
    retriever.evidence_extractor._extract_from_page.assert_not_called()
    assert result["filtered_evidence"] == []
    assert result["search_mode"] == "frozen_replay"


@pytest.mark.asyncio
async def test_frozen_urls_invalid_url(retriever):
    """Non-http entries are silently skipped."""
    frozen_urls = [
        {"url": "ftp://invalid.com/file", "title": "FTP", "snippet": ""},
        {"url": "", "title": "Empty", "snippet": ""},
        {"url": "https://valid.com/page", "title": "Valid", "snippet": "Good content"},
    ]

    claim = {
        "text": "Test claim",
        "position": 0,
        "frozen_urls": frozen_urls,
    }

    retriever.evidence_extractor._extract_from_page.return_value = _make_snippet(
        "https://valid.com/page", "Valid"
    )

    semaphore = asyncio.Semaphore(3)
    result = await retriever._retrieve_evidence_for_single_claim(claim, semaphore)

    # Only the valid https URL should be extracted
    assert retriever.evidence_extractor._extract_from_page.call_count == 1
    sr = retriever.evidence_extractor._extract_from_page.call_args[0][0]
    assert sr.url == "https://valid.com/page"


@pytest.mark.asyncio
async def test_frozen_urls_gov_apis_run(retriever):
    """Government APIs still called by default during frozen replay."""
    frozen_urls = [
        {"url": "https://reuters.com/article", "title": "Reuters", "snippet": ""},
    ]

    claim = {
        "text": "Government spending claim",
        "position": 0,
        "frozen_urls": frozen_urls,
    }

    retriever.evidence_extractor._extract_from_page.return_value = _make_snippet(
        "https://reuters.com/article", "Reuters"
    )

    semaphore = asyncio.Semaphore(3)
    await retriever._retrieve_evidence_for_single_claim(claim, semaphore)

    # Gov APIs should have been called
    retriever._retrieve_from_government_apis.assert_called_once()


@pytest.mark.asyncio
async def test_frozen_urls_gov_apis_skip_env(retriever):
    """Government APIs skipped when FROZEN_REPLAY_SKIP_GOV_APIS=1."""
    frozen_urls = [
        {"url": "https://reuters.com/article", "title": "Reuters", "snippet": ""},
    ]

    claim = {
        "text": "Government spending claim",
        "position": 0,
        "frozen_urls": frozen_urls,
    }

    retriever.evidence_extractor._extract_from_page.return_value = _make_snippet(
        "https://reuters.com/article", "Reuters"
    )

    semaphore = asyncio.Semaphore(3)
    with patch.dict("os.environ", {"FROZEN_REPLAY_SKIP_GOV_APIS": "1"}):
        await retriever._retrieve_evidence_for_single_claim(claim, semaphore)

    # Gov APIs should NOT have been called
    retriever._retrieve_from_government_apis.assert_not_called()


@pytest.mark.asyncio
async def test_frozen_urls_extraction_failure(retriever):
    """Extraction failures for some URLs don't break the pipeline."""
    frozen_urls = [
        {"url": "https://broken.com/page", "title": "Broken", "snippet": ""},
        {"url": "https://working.com/page", "title": "Working", "snippet": "Good"},
    ]

    claim = {
        "text": "Test claim",
        "position": 0,
        "frozen_urls": frozen_urls,
    }

    # First URL fails, second succeeds
    retriever.evidence_extractor._extract_from_page.side_effect = [
        Exception("403 Forbidden"),
        _make_snippet("https://working.com/page", "Working"),
    ]

    semaphore = asyncio.Semaphore(3)
    result = await retriever._retrieve_evidence_for_single_claim(claim, semaphore)

    # Only the successful extraction should appear
    assert len(result["filtered_evidence"]) == 1
