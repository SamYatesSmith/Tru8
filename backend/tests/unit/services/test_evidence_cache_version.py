"""Piece 3 (2026-09-02): the evidence cache must not outlive its retrieval code.

Scope: audit/2026-09-02_pool_quality_gate_scope.md. Why: the key was
md5(claim text) alone with a 24 h TTL, so a retrieval improvement did not reach
a repeated claim for a day and a re-run inside the window replayed the old pool
with zero searches (Build A's TTE control arm came back void that way).

Pins: the retrieval version is in the key; changing it changes the key; a
breaking-news claim (planner freshness pd/pw) is cached for an hour, everything
else keeps the category default.
"""

from unittest.mock import AsyncMock

import pytest

from app.core.config import settings
from app.services.cache import CacheService
from app.workers.pipeline import EVIDENCE_CACHE_TTL_BREAKING_NEWS, _evidence_cache_ttl

CLAIM = "AI triage through the NHS App reduced phone queues by 29 per cent"


def _service(monkeypatch, version):
    monkeypatch.setattr(settings, "RETRIEVAL_CACHE_VERSION", version)
    svc = CacheService()
    svc.redis_client = AsyncMock()
    svc.redis_client.get = AsyncMock(return_value=None)
    svc.redis_client.setex = AsyncMock(return_value=True)
    svc.initialize = AsyncMock()
    return svc


@pytest.mark.unit
@pytest.mark.asyncio
class TestEvidenceCacheKeyCarriesTheRetrievalVersion:
    async def test_key_is_prefixed_with_the_version(self, monkeypatch):
        svc = _service(monkeypatch, "2026-09-02a")
        await svc.cache_evidence_extraction(CLAIM, [{"url": "https://x.test/1"}])
        key = svc.redis_client.setex.call_args.args[0]
        assert key.startswith("tru8:evidence_extract:2026-09-02a:")
        # The rest is still the content hash, so identical text still collides on purpose.
        assert key.endswith(svc._hash_content(CLAIM))

    async def test_bumping_the_version_changes_the_key(self, monkeypatch):
        a = _service(monkeypatch, "2026-09-02a")
        await a.cache_evidence_extraction(CLAIM, [{"url": "https://x.test/1"}])
        key_a = a.redis_client.setex.call_args.args[0]

        b = _service(monkeypatch, "2026-09-03a")
        await b.cache_evidence_extraction(CLAIM, [{"url": "https://x.test/1"}])
        key_b = b.redis_client.setex.call_args.args[0]

        assert key_a != key_b

    async def test_get_reads_the_same_versioned_key(self, monkeypatch):
        svc = _service(monkeypatch, "2026-09-02a")
        await svc.get_cached_evidence_extraction(CLAIM)
        key = svc.redis_client.get.call_args.args[0]
        assert key == f"tru8:evidence_extract:2026-09-02a:{svc._hash_content(CLAIM)}"

    async def test_default_ttl_is_a_day_and_an_override_is_honoured(self, monkeypatch):
        svc = _service(monkeypatch, "2026-09-02a")
        await svc.cache_evidence_extraction(CLAIM, [{"url": "https://x.test/1"}])
        assert svc.redis_client.setex.call_args.args[1] == 3600 * 24

        await svc.cache_evidence_extraction(
            CLAIM, [{"url": "https://x.test/1"}], ttl=3600
        )
        assert svc.redis_client.setex.call_args.args[1] == 3600


@pytest.mark.unit
class TestBreakingNewsClaimsAreCachedForAnHour:
    def test_pd_and_pw_get_the_short_ttl(self):
        for fresh in ("pd", "pw"):
            claim = {"text": CLAIM, "query_plan": {"freshness": fresh}}
            assert (
                _evidence_cache_ttl(claim) == EVIDENCE_CACHE_TTL_BREAKING_NEWS == 3600
            )

    def test_everything_else_keeps_the_category_default(self):
        for fresh in ("pm", "py", "2y", "none", None):
            claim = {"text": CLAIM, "query_plan": {"freshness": fresh}}
            assert _evidence_cache_ttl(claim) is None
        # Legacy paths that leave no plan on the claim: default too.
        assert _evidence_cache_ttl({"text": CLAIM}) is None
