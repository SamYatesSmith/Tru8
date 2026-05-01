"""Tests for URL ledger audit-trail coverage.

Background: the URL ledger emits one log line per evidence URL at the
retrieve stage, tagged kept/dropped/cached/recovery. It must fire for:

  - Fresh retrieval (covered by retrieve.py end-stage emission)
  - Cache-hit retrieval (covered by workers/pipeline.py cache branch)
  - Post-filter recovery (covered separately in retrieve.py recovery path)

Without the cache-hit branch, audit checks on cached runs would have
no per-URL trail at the retrieve stage — exactly the blind spot
that allowed the facebook leak to persist invisibly.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.workers.pipeline import retrieve_evidence_with_cache


@pytest.mark.asyncio
async def test_cache_hit_emits_url_ledger_entries(caplog):
    """Cache-hit retrieval must emit [URL LEDGER] kept(cached) for each item."""
    caplog.set_level("INFO")

    cached_items_claim_0 = [
        {"url": "https://example.com/a", "title": "A", "text": "..."},
        {
            "url": "https://www.ncei.noaa.gov/cdo-web/",
            "title": "NOAA",
            "text": "...",
            "external_source_provider": "NOAA CDO",
        },
    ]
    cached_items_claim_1 = [
        {"url": "https://example.com/b", "title": "B", "text": "..."},
    ]

    cache_service = MagicMock()

    async def get_cached(claim_text):
        # Two claim texts in our test; return cached items for each
        if "claim zero" in claim_text:
            return cached_items_claim_0
        if "claim one" in claim_text:
            return cached_items_claim_1
        return None

    cache_service.get_cached_evidence_extraction = AsyncMock(side_effect=get_cached)
    cache_service.cache_evidence_extraction = AsyncMock()

    claims = [
        {"text": "claim zero text", "position": 0},
        {"text": "claim one text", "position": 1},
    ]

    with patch("app.workers.pipeline.EvidenceRetriever"):
        result = await retrieve_evidence_with_cache(claims, cache_service)

    assert "evidence_by_claim" in result
    assert "0" in result["evidence_by_claim"]
    assert "1" in result["evidence_by_claim"]

    ledger_lines = [
        rec.message for rec in caplog.records if "[URL LEDGER]" in rec.message
    ]

    # 3 cached items total → 3 ledger lines
    assert len(ledger_lines) == 3, (
        f"Expected 3 ledger lines for 3 cached items, got {len(ledger_lines)}: "
        f"{ledger_lines}"
    )

    # Every line must be tagged kept(cached)
    assert all(
        "kept(cached)" in line for line in ledger_lines
    ), f"All cache-hit ledger lines must use kept(cached) tag, got: {ledger_lines}"

    # Each URL must appear exactly once
    for ev in cached_items_claim_0 + cached_items_claim_1:
        url = ev["url"]
        matching = [line for line in ledger_lines if url[:60] in line]
        assert (
            len(matching) == 1
        ), f"Expected exactly one ledger line for {url}, got {len(matching)}"

    # API-typed item carries provider; web-typed shows '-'
    api_lines = [line for line in ledger_lines if "ncei.noaa.gov" in line]
    assert any(
        "type=api" in line and "provider=NOAA CDO" in line for line in api_lines
    ), f"NOAA item should be tagged type=api with provider, got: {api_lines}"

    web_lines = [line for line in ledger_lines if "example.com/a" in line]
    assert any(
        "type=web" in line and "provider=-" in line for line in web_lines
    ), f"Web item should be tagged type=web with provider=-, got: {web_lines}"


@pytest.mark.asyncio
async def test_cache_miss_does_not_emit_cached_ledger(caplog):
    """When all claims miss cache, the cache-hit ledger emission must
    not fire (other ledger emissions may fire elsewhere in the pipeline)."""
    caplog.set_level("INFO")

    cache_service = MagicMock()
    cache_service.get_cached_evidence_extraction = AsyncMock(return_value=None)
    cache_service.cache_evidence_extraction = AsyncMock()

    claims = [{"text": "uncached claim", "position": 0}]

    # Mock EvidenceRetriever to return empty so we don't hit the network
    mock_retriever = MagicMock()
    mock_retriever.retrieve_evidence_for_claims = AsyncMock(
        return_value={
            "evidence_by_claim": {"0": []},
            "raw_evidence": [],
            "raw_sources_count": 0,
        }
    )
    mock_retriever.search_service = MagicMock()
    mock_retriever.search_service.providers = []

    with patch("app.workers.pipeline.EvidenceRetriever", return_value=mock_retriever):
        await retrieve_evidence_with_cache(claims, cache_service)

    cached_lines = [
        rec.message
        for rec in caplog.records
        if "[URL LEDGER]" in rec.message and "kept(cached)" in rec.message
    ]

    assert (
        cached_lines == []
    ), f"Cache miss should not produce cached-ledger lines, got: {cached_lines}"
