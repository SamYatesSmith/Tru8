"""F2 precedence flip: the page's own declared date beats the engine's guess.

Design: audit/2026-07-03_f1f2_design_review.md — AC2/AC3/AC4 at the
_extract_from_page seam (services/evidence.py). The engine's date is kept
only as a fallback, and an engine date that merely echoes a /YYYY/MM/ URL
segment is labelled url_inferred_suspect — retained, never dropped.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.evidence import EvidenceExtractor
from app.services.search import SearchResult

HTML_WITH_DATE = """
<html><head>
<meta property="article:published_time" content="2020-01-15T09:00:00Z" />
<title>A properly dated article</title>
</head><body><p>Article body long enough to be treated as content.</p></body></html>
"""

HTML_WITHOUT_DATE = """
<html><head><title>An undated article</title></head>
<body><p>Article body long enough to be treated as content.</p></body></html>
"""


def _mock_http_client(html: str):
    """A patched httpx.AsyncClient async-context-manager returning stub HTML."""
    response = MagicMock()
    response.status_code = 200
    response.text = html
    response.raise_for_status = MagicMock()

    client = MagicMock()
    client.get = AsyncMock(return_value=response)

    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=client)
    cm.__aexit__ = AsyncMock(return_value=False)
    return cm


def _extractor_with_stubs() -> EvidenceExtractor:
    extractor = EvidenceExtractor()
    # Focus the test on the date seam — content/relevance machinery stubbed.
    extractor._extract_main_content = MagicMock(return_value="extracted body text")
    extractor._find_relevant_snippet = AsyncMock(return_value="relevant snippet")
    extractor._calculate_relevance = MagicMock(return_value=0.8)
    return extractor


def _run_extract(extractor, search_result):
    semaphore = asyncio.Semaphore(1)
    return asyncio.get_event_loop().run_until_complete(
        extractor._extract_from_page(search_result, "test claim", semaphore)
    )


class TestDatePrecedenceFlip:
    def test_page_date_beats_engine_guess(self):
        """AC2: page-declared date wins; basis=page_metadata."""
        extractor = _extractor_with_stubs()
        sr = SearchResult(
            title="t",
            url="https://example.com/article",
            snippet="s",
            published_date="2026-04-04",  # engine guess — must lose
            source="example.com",
        )
        with patch(
            "app.services.evidence.httpx.AsyncClient",
            return_value=_mock_http_client(HTML_WITH_DATE),
        ):
            snippet = _run_extract(extractor, sr)

        assert snippet is not None
        assert snippet.published_date == "2020-01-15"
        assert snippet.date_basis == "page_metadata"

    def test_engine_date_kept_when_page_undated(self):
        """AC3: no page date => engine date kept; basis=engine."""
        extractor = _extractor_with_stubs()
        sr = SearchResult(
            title="t",
            url="https://example.com/article",
            snippet="s",
            published_date="2026-04-04",
            source="example.com",
        )
        with patch(
            "app.services.evidence.httpx.AsyncClient",
            return_value=_mock_http_client(HTML_WITHOUT_DATE),
        ):
            snippet = _run_extract(extractor, sr)

        assert snippet is not None
        assert snippet.published_date == "2026-04-04"
        assert snippet.date_basis == "engine"

    def test_url_echo_without_page_date_is_suspect_and_retained(self):
        """AC4: engine date echoing /YYYY/MM/ URL path, page undated =>
        labelled url_inferred_suspect; the date itself is RETAINED."""
        extractor = _extractor_with_stubs()
        sr = SearchResult(
            title="t",
            url="https://example.com/wp-content/uploads/2026/04/old-paper.html",
            snippet="s",
            published_date="2026-04-04",
            source="example.com",
        )
        with patch(
            "app.services.evidence.httpx.AsyncClient",
            return_value=_mock_http_client(HTML_WITHOUT_DATE),
        ):
            snippet = _run_extract(extractor, sr)

        assert snippet is not None
        assert snippet.published_date == "2026-04-04"  # kept, not dropped
        assert snippet.date_basis == "url_inferred_suspect"

    def test_no_dates_anywhere_is_none(self):
        """AC6: nothing from engine, nothing on page => null date, null basis."""
        extractor = _extractor_with_stubs()
        sr = SearchResult(
            title="t",
            url="https://example.com/article",
            snippet="s",
            published_date=None,
            source="example.com",
        )
        with patch(
            "app.services.evidence.httpx.AsyncClient",
            return_value=_mock_http_client(HTML_WITHOUT_DATE),
        ):
            snippet = _run_extract(extractor, sr)

        assert snippet is not None
        assert snippet.published_date is None
        assert snippet.date_basis is None

    def test_to_dict_carries_date_basis(self):
        """date_basis survives EvidenceSnippet.to_dict (pipeline carrier)."""
        extractor = _extractor_with_stubs()
        sr = SearchResult(
            title="t",
            url="https://example.com/article",
            snippet="s",
            published_date="2026-04-04",
            source="example.com",
        )
        with patch(
            "app.services.evidence.httpx.AsyncClient",
            return_value=_mock_http_client(HTML_WITH_DATE),
        ):
            snippet = _run_extract(extractor, sr)

        d = snippet.to_dict()
        assert d["date_basis"] == "page_metadata"
        assert d["published_date"] == "2020-01-15"
