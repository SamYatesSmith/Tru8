"""Tests for video_recommendations service — channel classification heuristic
and the parallel fetch/dedup orchestrator."""

import pytest

from app.services import video_recommendations as vr
from app.services.video_recommendations import classify_channel, CHANNEL_HEURISTICS


def _video(vid: str, channel: str = "Random Channel"):
    return {
        "video_id": vid,
        "title": f"title-{vid}",
        # On-topic for the "... claim about oceans" fixtures, so the relevance
        # floor (A− S5) keeps these and the dedup/parallel tests test that.
        "description": "A claim about oceans",
        "channel_name": channel,
        "channel_id": "c1",
        "publish_date": None,
        "video_url": f"https://youtu.be/{vid}",
        "thumbnail_url": None,
        "duration": None,
    }


class _FakeResult:
    def __init__(self, rows):
        self._rows = rows

    def scalars(self):
        return self

    def all(self):
        return self._rows


class _FakeSession:
    def __init__(self, existing_video_ids=None):
        self.added = []
        self._existing = existing_video_ids or []

    def add(self, obj):
        self.added.append(obj)

    async def execute(self, *a, **k):
        # The only execute() the orchestrator issues is the "already stored"
        # video-id lookup before saving.
        return _FakeResult(self._existing)

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


@pytest.mark.asyncio
async def test_fetch_skips_videos_already_stored(monkeypatch):
    """A video already stored for the check is not re-inserted (guards the
    recover endpoint / a second generation from double-inserting)."""

    async def fake_search(query, max_results):
        return [_video("v1"), _video("v2")]

    monkeypatch.setattr(vr, "search_youtube_videos", fake_search)
    fake = _FakeSession(existing_video_ids=["v1"])  # v1 already in the DB
    monkeypatch.setattr(vr, "async_session", lambda: fake)

    await vr.fetch_video_recommendations("chk", [{"id": "c1", "text": "a claim"}])

    assert [v.video_id for v in fake.added] == ["v2"]


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


# ── Relevance floor (A− S5, 2026-09-24) ──────────────────────────────────────
# Every video stored on the 19 graded records: 2 on-topic, 7 off-topic.
_KENNEDY = (
    "As of 11 September 2026, EU-wide gas storage stocks are 67% full against a "
    "seasonal norm of 83%, pretty much the lowest on record for this time of year."
)
_PANTHAGANI = (
    "A study comparing AI-generated and physician-generated clinical summaries found "
    "physicians preferred the AI summaries in most cases."
)
_BURKE_KENNEDY = "Irish public spending has risen by more than 50 per cent since 2020."
_REFORM = (
    "Reform UK's £72 million came in the space of one weekend — £36 million "
    "from Ben Delo and £36 million from a crypto billionaire."
)


@pytest.mark.parametrize(
    "claim,title,desc",
    [
        (_KENNEDY, "Batomon Showdown - 21 Sep 2026 - Unofficial Northernlion VOD", ""),
        (_PANTHAGANI, "Artificial Intelligence Essay", ""),
        (_PANTHAGANI, "How Successful People Turn Daily Habits Into Extraordinary Results", "a summary of habits"),
        (_PANTHAGANI, "1st yr. Vs Final yr. MBBS student #shorts #neet", "physician study life"),
        (_BURKE_KENNEDY, "can we make more Efficient solar panels ? Elon Musk", ""),
    ],
)
def test_off_topic_videos_are_dropped(claim, title, desc):
    assert vr.video_is_on_topic(claim, title, desc) is False


@pytest.mark.parametrize(
    "title",
    [
        "Richard Tice Defends Reform UK’s £72m Donations from Crypto Billionaires",
        "Government suggests that Reform donations of £36 million from Ben Delo could be breaking new rules",
    ],
)
def test_on_topic_videos_are_kept(title):
    assert vr.video_is_on_topic(_REFORM, title, "") is True


def test_years_alone_never_make_a_video_relevant():
    # "2026" on a gaming stream matched nothing in the claim but the year.
    assert vr.video_is_on_topic("Europe had record heat in 2026", "Speedrun 2026 highlights", "") is False


@pytest.mark.asyncio
async def test_fetch_drops_off_topic_videos(monkeypatch):
    async def fake_search(query, max_results):
        off = _video("off")
        off["description"] = "Unofficial gaming stream"
        return [_video("on"), off]

    monkeypatch.setattr(vr, "search_youtube_videos", fake_search)
    fake = _FakeSession()
    monkeypatch.setattr(vr, "async_session", lambda: fake)
    await vr.fetch_video_recommendations("chk-3", [{"id": "ca", "text": "A claim about oceans"}])
    assert [v.video_id for v in fake.added] == ["on"]

