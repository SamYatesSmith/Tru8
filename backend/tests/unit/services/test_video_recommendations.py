"""Tests for video_recommendations service — channel classification heuristic
and the parallel fetch/dedup orchestrator."""

import pytest

from app.services import video_recommendations as vr
from app.services.video_recommendations import classify_channel, CHANNEL_HEURISTICS


def _video(vid: str, channel: str = "Random Channel"):
    return {
        "video_id": vid,
        "title": f"title-{vid}",
        "description": "desc",
        "channel_name": channel,
        "channel_id": "c1",
        "publish_date": None,
        "video_url": f"https://youtu.be/{vid}",
        "thumbnail_url": None,
        "duration": None,
    }


class _FakeSession:
    def __init__(self):
        self.added = []

    def add(self, obj):
        self.added.append(obj)

    async def commit(self):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False


@pytest.mark.asyncio
async def test_fetch_is_parallel_deduped_and_failure_resilient(monkeypatch):
    """All claim searches run; duplicates keep the first claim; a claim whose
    search raises does not sink the others (the parallel-fetch hardening)."""
    calls = []

    async def fake_search(query, max_results):
        calls.append(query)
        if query.startswith("boom"):
            raise RuntimeError("simulated search failure")
        if query.startswith("A"):
            return [_video("v1"), _video("v2")]
        if query.startswith("B"):
            return [_video("v1"), _video("v3")]  # v1 duplicates claim A
        return []

    monkeypatch.setattr(vr, "search_youtube_videos", fake_search)
    fake = _FakeSession()
    monkeypatch.setattr(vr, "async_session", lambda: fake)

    await vr.fetch_video_recommendations(
        "chk-1",
        [
            {"id": "ca", "text": "A claim about oceans"},
            {"id": "cb", "text": "B claim about oceans"},
            {"id": "cc", "text": "boom claim"},  # raises — must not sink the rest
        ],
    )

    # Every claim was searched (issued together via gather).
    assert len(calls) == 3
    # Dedup across claims: v1 saved once, plus v2 and v3.
    assert sorted(v.video_id for v in fake.added) == ["v1", "v2", "v3"]
    # First claim to surface v1 (claim A) keeps it.
    v1 = next(v for v in fake.added if v.video_id == "v1")
    assert v1.claim_id == "ca"


@pytest.mark.asyncio
async def test_fetch_skips_claims_missing_id_or_text(monkeypatch):
    calls = []

    async def fake_search(query, max_results):
        calls.append(query)
        return [_video("v9")]

    monkeypatch.setattr(vr, "search_youtube_videos", fake_search)
    fake = _FakeSession()
    monkeypatch.setattr(vr, "async_session", lambda: fake)

    await vr.fetch_video_recommendations(
        "chk-2",
        [
            {"id": "c1", "text": "real claim"},
            {"id": "", "text": "no id"},
            {"id": "c2", "text": ""},
        ],
    )
    assert len(calls) == 1  # only the valid claim searched


class TestClassifyChannel:
    """classify_channel maps YouTube channel names to (tier, type) tuples."""

    def test_known_channel_exact_match(self):
        """Exact match for a known channel returns its classification."""
        tier, etype = classify_channel("BBC News")
        assert tier == "reporting"
        assert etype == "news_reporting"

    def test_known_channel_case_insensitive(self):
        """Lookup is case-insensitive — lowercased input still matches."""
        tier, etype = classify_channel("bbc news")
        assert tier == "reporting"
        assert etype == "news_reporting"

    def test_unknown_channel_defaults(self):
        """Unknown channels default to (commentary, analysis)."""
        tier, etype = classify_channel("Random Channel XYZ")
        assert tier == "commentary"
        assert etype == "analysis"

    def test_partial_match(self):
        """A channel name containing a known channel as a substring matches."""
        # "reuters" is in CHANNEL_HEURISTICS; a longer name containing it should match
        tier, etype = classify_channel("Reuters UK Edition")
        assert tier == "reporting"
        assert etype == "news_reporting"
