"""Regression tests for blocklist enforcement in the two recovery paths.

Background — TRU-E317-4192 (2026-05-11) surfaced facebook.com and
instagram.com leaking into the evidence pool with `receipt_status='shown'`
despite both being pre-seeded as `bot_blocked` in `domain_status.json`
since 2025-12-01.

The previous facebook-leak fix (commit 330ab44, 2026-05-01) patched the
post-filter recovery loop in `runner.py:1535-1559`. This caught the
runner-level recovery path but left TWO recovery paths inside `retrieve.py`
unguarded:

  1. `_recover_evidence_for_claim` (line 553+) — invoked by
     `_ensure_minimum_evidence` when a claim's initial retrieve yielded
     fewer than `MIN_EVIDENCE_PER_CLAIM` items
  2. `retrieve_for_elements` (line 850+) — invoked by Stage 5.1 coverage
     recovery in `runner.py` for unresolved elements after mapping

Both paths take search results and build EvidenceSnippet / evidence dicts
directly from the search snippets (no URL fetch), so the blocklist check
at fetch time in `EvidenceService._extract_from_page` never fires.

These tests pin the contract: search results whose domain is in the
runtime blocklist MUST be dropped before becoming evidence, AND the drop
must be logged via the URL ledger so the receipt-disclosure stays honest.
"""

from unittest.mock import AsyncMock, patch
import logging

import pytest

from app.pipeline.retrieve import EvidenceRetriever
from app.services.search import SearchResult


def _make_search_result(url: str, title: str = None, snippet: str = None):
    """Build a minimal SearchResult dict-compatible object."""
    return SearchResult(
        title=title or f"Title for {url}",
        url=url,
        snippet=snippet or f"Snippet for {url}",
        source=url.split("//")[1].split("/")[0] if "//" in url else "unknown",
    )


@pytest.fixture
def retriever():
    """A retriever with recovery-trigger floor at 0 so unrelated recovery
    paths don't fire during the tests."""
    r = EvidenceRetriever()
    r.MIN_EVIDENCE_PER_CLAIM = 0
    return r


# --------------------------------------------------------------------------- #
# Path 1: _recover_evidence_for_claim (called by _ensure_minimum_evidence)
# --------------------------------------------------------------------------- #


class TestRecoverEvidenceForClaim:

    @pytest.mark.asyncio
    async def test_facebook_url_dropped(self, retriever, monkeypatch, caplog):
        """A facebook.com result must NOT survive recovery."""
        # Force a non-empty blocklist that includes facebook.com.
        monkeypatch.setattr(
            "app.pipeline.retrieve.get_runtime_blocked_domains",
            lambda: {"facebook.com", "www.facebook.com"},
        )

        # Search returns one allowed + one facebook URL.
        async def _stub_search(*args, **kwargs):
            return [
                _make_search_result("https://reuters.com/article/coral"),
                _make_search_result("https://www.facebook.com/some-group/posts/12345"),
            ]

        monkeypatch.setattr(
            retriever.search_service, "search_for_evidence", _stub_search
        )

        claim = {
            "text": "Coral reefs are bleaching across the GBR",
            "position": 1,
            "article_classification": {"primary_domain": "general"},
        }

        with caplog.at_level(logging.INFO, logger="app.pipeline.retrieve"):
            final_evidence, raw_evidence = await retriever._recover_evidence_for_claim(
                claim=claim,
                claim_position="1",
                existing_urls=set(),
                excluded_domain=None,
            )

        urls = [ev.get("url", "") for ev in final_evidence]
        assert not any(
            "facebook.com" in u for u in urls
        ), f"facebook.com URL leaked through recovery: {urls}"
        assert any(
            "reuters.com" in u for u in urls
        ), f"allowed reuters.com URL was unexpectedly dropped: {urls}"

        # Verify the URL ledger dropped(recovery) line was emitted.
        ledger_drops = [
            r.message
            for r in caplog.records
            if "[URL LEDGER]" in r.message
            and "dropped(recovery)" in r.message
            and "facebook.com" in r.message
        ]
        assert ledger_drops, (
            "Expected [URL LEDGER] dropped(recovery) line for facebook.com; "
            f"got log lines: {[r.message for r in caplog.records]}"
        )
        assert "runtime_blocked_domain" in ledger_drops[0]

    @pytest.mark.asyncio
    async def test_instagram_url_dropped(self, retriever, monkeypatch):
        """instagram.com must also be dropped (user-reported in TRU-E317)."""
        monkeypatch.setattr(
            "app.pipeline.retrieve.get_runtime_blocked_domains",
            lambda: {"instagram.com", "www.instagram.com"},
        )

        async def _stub_search(*args, **kwargs):
            return [
                _make_search_result("https://www.instagram.com/p/abc123/"),
                _make_search_result("https://www.bbc.com/news/article-1"),
            ]

        monkeypatch.setattr(
            retriever.search_service, "search_for_evidence", _stub_search
        )

        claim = {
            "text": "Test claim",
            "position": 0,
            "article_classification": {"primary_domain": "general"},
        }

        final_evidence, _ = await retriever._recover_evidence_for_claim(
            claim=claim,
            claim_position="0",
            existing_urls=set(),
            excluded_domain=None,
        )

        urls = [ev.get("url", "") for ev in final_evidence]
        assert not any("instagram.com" in u for u in urls)
        assert any("bbc.com" in u for u in urls)

    @pytest.mark.asyncio
    async def test_empty_blocklist_keeps_everything(self, retriever, monkeypatch):
        """Sanity: with an empty blocklist, no URLs are dropped on
        runtime_blocked_domain grounds."""
        monkeypatch.setattr(
            "app.pipeline.retrieve.get_runtime_blocked_domains", lambda: set()
        )

        async def _stub_search(*args, **kwargs):
            return [
                _make_search_result("https://www.facebook.com/p/x"),
                _make_search_result("https://reuters.com/x"),
            ]

        monkeypatch.setattr(
            retriever.search_service, "search_for_evidence", _stub_search
        )

        claim = {
            "text": "Test claim",
            "position": 0,
            "article_classification": {"primary_domain": "general"},
        }

        final_evidence, _ = await retriever._recover_evidence_for_claim(
            claim=claim,
            claim_position="0",
            existing_urls=set(),
            excluded_domain=None,
        )
        urls = [ev.get("url", "") for ev in final_evidence]
        # Without a blocklist, BOTH URLs should survive the dedup step
        # (satire-filter etc. is a separate concern not exercised here).
        assert any("facebook.com" in u for u in urls)
        assert any("reuters.com" in u for u in urls)

    @pytest.mark.asyncio
    async def test_existing_url_dedup_still_works(self, retriever, monkeypatch):
        """The new blocklist check must not bypass the existing
        `if url in existing_urls: continue` dedup."""
        monkeypatch.setattr(
            "app.pipeline.retrieve.get_runtime_blocked_domains", lambda: set()
        )

        async def _stub_search(*args, **kwargs):
            return [
                _make_search_result("https://reuters.com/article-A"),
                _make_search_result("https://reuters.com/article-B"),
            ]

        monkeypatch.setattr(
            retriever.search_service, "search_for_evidence", _stub_search
        )

        claim = {
            "text": "Test",
            "position": 0,
            "article_classification": {"primary_domain": "general"},
        }

        # Pre-seed existing_urls with article-A.
        final_evidence, _ = await retriever._recover_evidence_for_claim(
            claim=claim,
            claim_position="0",
            existing_urls={"https://reuters.com/article-A"},
            excluded_domain=None,
        )
        urls = [ev.get("url", "") for ev in final_evidence]
        assert "https://reuters.com/article-A" not in urls
        assert "https://reuters.com/article-B" in urls


# --------------------------------------------------------------------------- #
# Path 2: retrieve_for_elements (called by runner.py Stage 5.1 coverage recovery)
# --------------------------------------------------------------------------- #


class TestRetrieveForElements:

    @pytest.mark.asyncio
    async def test_facebook_url_dropped(self, retriever, monkeypatch, caplog):
        """retrieve_for_elements is the SECOND recovery path. Same leak
        class as _recover_evidence_for_claim; same fix required."""
        monkeypatch.setattr(
            "app.pipeline.retrieve.get_runtime_blocked_domains",
            lambda: {"facebook.com", "www.facebook.com"},
        )
        # Disable the LLM recovery query planner so we don't depend on
        # google_ai credentials for this test.
        monkeypatch.setattr(
            "app.core.config.settings.ENABLE_RECOVERY_QUERY_PLANNING", False
        )

        async def _stub_search(*args, **kwargs):
            return [
                _make_search_result("https://www.facebook.com/marinescience/videos/1"),
                _make_search_result("https://aims.gov.au/science/coral"),
            ]

        monkeypatch.setattr(
            retriever.search_service, "search_for_evidence", _stub_search
        )

        elements = [{"element_id": "e1", "description": "Coral bleaching"}]

        with caplog.at_level(logging.INFO, logger="app.pipeline.retrieve"):
            evidence = await retriever.retrieve_for_elements(
                elements=elements,
                claim_text="Coral bleaching event",
                existing_urls=set(),
                article_context=None,
            )

        urls = [ev.get("url", "") for ev in evidence]
        assert not any(
            "facebook.com" in u for u in urls
        ), f"facebook.com URL leaked through retrieve_for_elements: {urls}"
        assert any(
            "aims.gov.au" in u for u in urls
        ), f"allowed aims.gov.au URL was unexpectedly dropped: {urls}"

        # URL ledger drop line emitted, scoped to the element.
        ledger_drops = [
            r.message
            for r in caplog.records
            if "[URL LEDGER]" in r.message
            and "dropped(recovery)" in r.message
            and "facebook.com" in r.message
        ]
        assert ledger_drops
        assert "element=e1" in ledger_drops[0]

    @pytest.mark.asyncio
    async def test_instagram_url_dropped(self, retriever, monkeypatch):
        monkeypatch.setattr(
            "app.pipeline.retrieve.get_runtime_blocked_domains",
            lambda: {"instagram.com", "www.instagram.com"},
        )
        monkeypatch.setattr(
            "app.core.config.settings.ENABLE_RECOVERY_QUERY_PLANNING", False
        )

        async def _stub_search(*args, **kwargs):
            return [
                _make_search_result("https://www.instagram.com/p/xyz"),
                _make_search_result("https://nature.com/articles/abc"),
            ]

        monkeypatch.setattr(
            retriever.search_service, "search_for_evidence", _stub_search
        )

        elements = [{"element_id": "e2", "description": "Some element"}]
        evidence = await retriever.retrieve_for_elements(
            elements=elements,
            claim_text="Test claim",
            existing_urls=set(),
            article_context=None,
        )

        urls = [ev.get("url", "") for ev in evidence]
        assert not any("instagram.com" in u for u in urls)
        assert any("nature.com" in u for u in urls)

    @pytest.mark.asyncio
    async def test_mixed_blocked_and_allowed(self, retriever, monkeypatch):
        """Several blocked + several allowed URLs in one response — only
        allowed survive."""
        monkeypatch.setattr(
            "app.pipeline.retrieve.get_runtime_blocked_domains",
            lambda: {
                "facebook.com",
                "instagram.com",
                "tiktok.com",
                "www.facebook.com",
                "www.instagram.com",
                "www.tiktok.com",
            },
        )
        monkeypatch.setattr(
            "app.core.config.settings.ENABLE_RECOVERY_QUERY_PLANNING", False
        )

        async def _stub_search(*args, **kwargs):
            return [
                _make_search_result("https://www.facebook.com/x"),
                _make_search_result("https://reuters.com/article-1"),
                _make_search_result("https://www.instagram.com/p/y"),
                _make_search_result("https://www.bbc.com/news/article-2"),
                _make_search_result("https://www.tiktok.com/@x/video/z"),
                _make_search_result("https://aims.gov.au/research/r-3"),
            ]

        monkeypatch.setattr(
            retriever.search_service, "search_for_evidence", _stub_search
        )

        elements = [{"element_id": "e1", "description": "Test"}]
        evidence = await retriever.retrieve_for_elements(
            elements=elements,
            claim_text="Test claim",
            existing_urls=set(),
            article_context=None,
        )

        urls = [ev.get("url", "") for ev in evidence]
        # All three social domains dropped.
        assert not any(
            d in u for u in urls for d in ("facebook", "instagram", "tiktok")
        )
        # All three allowed domains kept.
        kept_domains = {"reuters.com", "bbc.com", "aims.gov.au"}
        for d in kept_domains:
            assert any(d in u for u in urls), f"{d} unexpectedly dropped"


# --------------------------------------------------------------------------- #
# Negative regression: helpers themselves should NOT misbehave on edge cases
# --------------------------------------------------------------------------- #


class TestBlocklistHelperEdgeCases:

    def test_is_domain_blocked_handles_empty_url(self):
        from app.services.evidence import is_domain_blocked

        assert is_domain_blocked("", {"facebook.com"}) is False

    def test_is_domain_blocked_handles_empty_blocklist(self):
        from app.services.evidence import is_domain_blocked

        assert is_domain_blocked("https://facebook.com/x", set()) is False

    def test_is_domain_blocked_substring_match_on_subdomain(self):
        """www.facebook.com / m.facebook.com / business.facebook.com etc.
        must all match against the 'facebook.com' blocklist entry."""
        from app.services.evidence import is_domain_blocked

        block = {"facebook.com"}
        assert is_domain_blocked("https://www.facebook.com/x", block) is True
        assert is_domain_blocked("https://m.facebook.com/x", block) is True
        assert is_domain_blocked("https://business.facebook.com/x", block) is True
