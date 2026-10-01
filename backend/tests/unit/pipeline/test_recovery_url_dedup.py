"""Recovery paths dedupe on the canonical URL key (2026-10-01).

A− re-measure 3 (#5, #12, #14): one page entered the pool twice under URLs
differing only by a tracking parameter (`srsltid`, WSJ `eafs_enabled`). The
main lane already collapsed these (Build C); the recovery paths compared raw
strings. Each test here fails if a recovery path goes back to a plain `set`.
"""

import logging

import pytest

from app.pipeline.retrieve import EvidenceRetriever, _already_pooled
from app.services.search import SearchResult
from app.utils.url_identity import UrlKeySet, canonical_url_key

STATISTA = "https://www.statista.com/statistics/1091926/atmospheric-concentration-of-co2-historic/"
STATISTA_TRACKED = STATISTA + "?srsltid=AfmBOoq1"
WSJ = "https://www.wsj.com/finance/commodities-futures/europe-gas-storage-winter-abc123"
WSJ_FLAGGED = WSJ + "?eafs_enabled=false"


def _sr(url):
    return SearchResult(
        title=f"Title for {url}",
        url=url,
        snippet=f"Snippet for {url}",
        source=url.split("//")[1].split("/")[0],
    )


class TestUrlKeySet:
    def test_tracking_variant_is_a_member(self):
        pool = UrlKeySet([STATISTA])
        assert STATISTA_TRACKED in pool
        assert pool.twin(STATISTA_TRACKED) == STATISTA

    def test_wsj_feature_switch_is_not_identity(self):
        assert canonical_url_key(WSJ_FLAGGED) == canonical_url_key(WSJ)

    def test_identity_parameters_still_differ(self):
        pool = UrlKeySet(["https://www.youtube.com/watch?v=aaa"])
        assert "https://www.youtube.com/watch?v=bbb" not in pool

    def test_empty_and_non_string(self):
        pool = UrlKeySet([None, ""])
        assert len(pool) == 0
        assert None not in pool
        assert "" not in pool


class TestAlreadyPooled:
    def test_variant_dropped_with_a_receipt(self, caplog):
        with caplog.at_level(logging.INFO, logger="app.pipeline.retrieve"):
            assert _already_pooled(UrlKeySet([STATISTA]), STATISTA_TRACKED, "claim=0")
        lines = [r.message for r in caplog.records if "[URL LEDGER]" in r.message]
        assert len(lines) == 1
        assert "stage=copy_dedup" in lines[0] and "survivor=" + STATISTA in lines[0]

    def test_exact_repeat_is_silent(self, caplog):
        with caplog.at_level(logging.INFO, logger="app.pipeline.retrieve"):
            assert _already_pooled(UrlKeySet([STATISTA]), STATISTA, "claim=0")
        assert not [r for r in caplog.records if "[URL LEDGER]" in r.message]

    def test_plain_set_still_works(self):
        assert _already_pooled({STATISTA}, STATISTA, "claim=0")
        assert not _already_pooled({STATISTA}, STATISTA_TRACKED, "claim=0")


@pytest.fixture
def retriever(monkeypatch):
    monkeypatch.setattr(
        "app.pipeline.retrieve.get_runtime_blocked_domains", lambda: set()
    )
    r = EvidenceRetriever()
    r.MIN_EVIDENCE_PER_CLAIM = 0
    return r


class TestRecoverEvidenceForClaim:
    @pytest.mark.asyncio
    async def test_variant_of_a_pooled_page_is_skipped(self, retriever, monkeypatch):
        async def _search(*a, **k):
            return [_sr(STATISTA_TRACKED), _sr("https://www.noaa.gov/co2")]

        monkeypatch.setattr(retriever.search_service, "search_for_evidence", _search)
        claim = {"text": "CO2 is above 420 ppm", "position": 0}
        final, _raw = await retriever._recover_evidence_for_claim(
            claim=claim,
            claim_position="0",
            existing_urls=UrlKeySet([STATISTA]),
            excluded_domain=None,
        )
        urls = [ev["url"] for ev in final]
        assert STATISTA_TRACKED not in urls
        assert "https://www.noaa.gov/co2" in urls

    @pytest.mark.asyncio
    async def test_two_queries_returning_one_page_keep_one(
        self, retriever, monkeypatch
    ):
        calls = iter([[_sr(WSJ)], [_sr(WSJ_FLAGGED)]])

        async def _search(*a, **k):
            return next(calls, [])

        monkeypatch.setattr(retriever.search_service, "search_for_evidence", _search)
        monkeypatch.setattr(
            retriever, "_generate_recovery_queries", lambda *a, **k: ["q1", "q2"]
        )
        claim = {"text": "Europe is running low on gas", "position": 0}
        final, _raw = await retriever._recover_evidence_for_claim(
            claim=claim,
            claim_position="0",
            existing_urls=UrlKeySet(),
            excluded_domain=None,
        )
        assert [ev["url"] for ev in final] == [WSJ]


class TestRetrieveForElements:
    @pytest.mark.asyncio
    async def test_variant_of_a_pooled_page_is_skipped(self, retriever, monkeypatch):
        monkeypatch.setattr(
            "app.core.config.settings.ENABLE_RECOVERY_QUERY_PLANNING", False
        )

        async def _search(*a, **k):
            return [_sr(STATISTA_TRACKED), _sr("https://www.noaa.gov/co2")]

        monkeypatch.setattr(retriever.search_service, "search_for_evidence", _search)
        evidence = await retriever.retrieve_for_elements(
            elements=[{"element_id": "e1", "description": "CO2 concentration"}],
            claim_text="CO2 is above 420 ppm",
            existing_urls=UrlKeySet([STATISTA]),
        )
        urls = [ev["url"] for ev in evidence]
        assert STATISTA_TRACKED not in urls
        assert "https://www.noaa.gov/co2" in urls


class TestEnsureMinimumEvidence:
    @pytest.mark.asyncio
    async def test_pool_set_is_canonical(self, retriever, monkeypatch):
        """The caller builds the pool set; a raw `set()` there reopens the hole."""
        retriever.MIN_EVIDENCE_PER_CLAIM = 3

        async def _search(*a, **k):
            return [_sr(STATISTA_TRACKED), _sr("https://www.noaa.gov/co2")]

        monkeypatch.setattr(retriever.search_service, "search_for_evidence", _search)
        evidence = {"0": [{"url": STATISTA, "text": "x"}]}
        claims = [{"text": "CO2 is above 420 ppm", "position": 0}]
        updated, _raw = await retriever._ensure_minimum_evidence(
            evidence, claims, excluded_domain=None
        )
        urls = [ev["url"] for ev in updated["0"]]
        assert urls.count(STATISTA) == 1
        assert STATISTA_TRACKED not in urls
