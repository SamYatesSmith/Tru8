"""Fetch-phase deadline (2026-09-02): keep what has finished, cancel the stragglers.

Why: the per-claim 45 s wait (RETRIEVE_CLAIM_TIMEOUT_S) is all-or-nothing INSIDE
the web task. On the TTE control arm (dd2ca726) forty pages were fetched, the
critic's page among them, and every one was discarded at the deadline —
`0 web snippets + 1 API snippets` — leaving recovery to rebuild a thin pool.
The fetch phase now has its own, shorter deadline and returns partial results.

These tests drive the real `_extract_all_within_deadline` on the real
EvidenceRetriever with a fake page extractor whose latency is set by the URL.
"""

import asyncio
import time
from unittest.mock import patch

import pytest

from app.core.config import settings
from app.pipeline.retrieve import EvidenceRetriever
from app.services.evidence import EvidenceSnippet
from app.services.search import SearchResult

CLAIM = "AI triage through the NHS App reduced phone queues by 29 per cent"


@pytest.fixture
def retriever():
    with patch("app.pipeline.retrieve.SearchService"), patch(
        "app.pipeline.retrieve.EvidenceExtractor"
    ), patch("app.pipeline.retrieve.get_api_registry"):
        r = EvidenceRetriever()
        r.evidence_extractor.max_concurrent = 10
        return r


def _result(url):
    return SearchResult(title=url, url=url, snippet="s", source="x.test")


def _extractor_by_url():
    """fast-* returns at once; slow-* sleeps 3 s; boom-* raises; empty-* returns None."""

    async def _extract(search_result, claim_text, semaphore):
        url = search_result.url
        if "slow" in url:
            await asyncio.sleep(3)
        if "boom" in url:
            raise RuntimeError("fetch failed")
        if "empty" in url:
            return None
        return EvidenceSnippet(
            text="content",
            source="x.test",
            url=url,
            title="t",
            relevance_score=0.5,
            metadata={},
        )

    return _extract


@pytest.mark.unit
@pytest.mark.asyncio
class TestFetchPhaseDeadline:
    async def test_finished_fetches_are_kept_and_stragglers_cancelled(
        self, retriever, monkeypatch
    ):
        monkeypatch.setattr(settings, "ENABLE_FETCH_PHASE_DEADLINE", True)
        monkeypatch.setattr(settings, "RETRIEVE_FETCH_PHASE_TIMEOUT_S", 0.4)
        retriever.evidence_extractor._extract_from_page = _extractor_by_url()
        fetch_set = [
            _result("https://x.test/fast-1"),
            _result("https://x.test/slow-1"),
            _result("https://x.test/fast-2"),
            _result("https://x.test/slow-2"),
        ]

        started = time.monotonic()
        results = await retriever._extract_all_within_deadline(
            fetch_set, CLAIM, asyncio.Semaphore(10)
        )
        elapsed = time.monotonic() - started

        # Aligned with fetch_set: kept, dropped, kept, dropped.
        assert [r is not None for r in results] == [True, False, True, False]
        assert results[0].url == "https://x.test/fast-1"
        assert results[2].url == "https://x.test/fast-2"
        # We stopped waiting at the deadline, not at the slowest fetch.
        assert elapsed < 2.0

    async def test_exceptions_and_empties_keep_the_old_shape(
        self, retriever, monkeypatch
    ):
        monkeypatch.setattr(settings, "ENABLE_FETCH_PHASE_DEADLINE", True)
        monkeypatch.setattr(settings, "RETRIEVE_FETCH_PHASE_TIMEOUT_S", 5.0)
        retriever.evidence_extractor._extract_from_page = _extractor_by_url()
        fetch_set = [
            _result("https://x.test/fast-1"),
            _result("https://x.test/boom"),
            _result("https://x.test/empty"),
        ]

        results = await retriever._extract_all_within_deadline(
            fetch_set, CLAIM, asyncio.Semaphore(10)
        )

        # gather(return_exceptions=True) contract: snippet, exception, None.
        assert results[0].url == "https://x.test/fast-1"
        assert (
            isinstance(results[1], Exception) or results[1] is None
        )  # wrapper may swallow into None
        assert results[2] is None

    async def test_flag_off_waits_for_everything_as_today(self, retriever, monkeypatch):
        monkeypatch.setattr(settings, "ENABLE_FETCH_PHASE_DEADLINE", False)
        monkeypatch.setattr(settings, "RETRIEVE_FETCH_PHASE_TIMEOUT_S", 0.1)
        retriever.evidence_extractor._extract_from_page = _extractor_by_url()
        fetch_set = [_result("https://x.test/fast-1"), _result("https://x.test/slow-1")]

        started = time.monotonic()
        results = await retriever._extract_all_within_deadline(
            fetch_set, CLAIM, asyncio.Semaphore(10)
        )
        elapsed = time.monotonic() - started

        assert all(r is not None for r in results)
        assert elapsed >= 2.5

    async def test_dropped_pages_get_a_ledger_receipt(
        self, retriever, monkeypatch, caplog
    ):
        import logging

        monkeypatch.setattr(settings, "ENABLE_FETCH_PHASE_DEADLINE", True)
        monkeypatch.setattr(settings, "RETRIEVE_FETCH_PHASE_TIMEOUT_S", 0.3)
        retriever.evidence_extractor._extract_from_page = _extractor_by_url()
        fetch_set = [_result("https://x.test/fast-1"), _result("https://x.test/slow-9")]

        with caplog.at_level(logging.INFO, logger="app.pipeline.retrieve"):
            await retriever._extract_all_within_deadline(
                fetch_set, CLAIM, asyncio.Semaphore(10)
            )

        receipts = [
            r.message for r in caplog.records if "stage=fetch_deadline" in r.message
        ]
        assert len(receipts) == 1
        assert "https://x.test/slow-9" in receipts[0]
        summary = [r.message for r in caplog.records if "Fetch deadline" in r.message]
        assert (
            summary and "kept=1" in summary[0] and "dropped_by_deadline=1" in summary[0]
        )

    async def test_empty_fetch_set(self, retriever, monkeypatch):
        monkeypatch.setattr(settings, "ENABLE_FETCH_PHASE_DEADLINE", True)
        assert (
            await retriever._extract_all_within_deadline(
                [], CLAIM, asyncio.Semaphore(1)
            )
            == []
        )
