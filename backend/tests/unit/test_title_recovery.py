"""Tests for headline recovery + the outbound headers that prevent the need.

Two related defects, 2026-08-25:
  1. Evidence fetches sent NO headers, so publishers 403'd "python-httpx/x.y"
     (3/82 of the corpus's blocked URLs succeeded; 24/82 with headers).
  2. When a fetch IS blocked, the provider's ~54-char truncated title survives
     to the screen looking like a complete headline.
"""

import asyncio

import pytest

from app.services.title_recovery import (
    _headline_from_html,
    _raw_snapshot_url,
    _stub,
    is_truncated_title,
    recover_truncated_titles,
)


# ── truncation detection ────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "title",
    [
        "Britain braces for unprecedented water restrictions as...",
        "UK planners warn water restrictions could be extended to ...",
        "Seismological observations of the 2011 Nabro eruption…",
        "Trump says he has ended six wars in six months. As a ...",
    ],
)
def test_detects_truncated_titles(title):
    assert is_truncated_title(title) is True


@pytest.mark.parametrize(
    "title",
    [
        "Could England and Wales ever run out of water?",
        "How El Nino could make next summer even hotter than this one",
        "Plate tectonics | Definition, Theory, Facts, & Evidence - Britannica",
        # A single full stop ends a sentence; it is not a truncation marker.
        "The drought is over.",
        "",
        None,
    ],
)
def test_leaves_complete_titles_alone(title):
    assert is_truncated_title(title) is False


def test_stub_removes_only_the_marker():
    assert _stub("Britain braces for water restrictions as...") == (
        "Britain braces for water restrictions as"
    )
    assert _stub("A complete headline") == "A complete headline"


# ── headline extraction ─────────────────────────────────────────────────────


def test_prefers_og_title():
    html = (
        '<html><head><meta property="og:title" content="The full original headline">'
        "<title>The full original headline - Site</title></head></html>"
    )
    assert _headline_from_html(html) == "The full original headline"


def test_rejects_archived_bot_walls():
    """An archived interstitial is still an interstitial."""
    for junk in ("Just a moment...", "Access Denied", "Please enable JavaScript"):
        html = f"<html><head><title>{junk}</title></head></html>"
        assert _headline_from_html(html) is None, junk


def test_raw_snapshot_url_requests_original_bytes():
    """`id_` after the timestamp suppresses Wayback's banner + link rewriting."""
    got = _raw_snapshot_url(
        "http://web.archive.org/web/20260718000000/https://example.com/story"
    )
    assert got == (
        "http://web.archive.org/web/20260718000000id_/https://example.com/story"
    )
    # the scheme's own "//" must not be mangled
    assert got.startswith("http://web.archive.org/web/")


# ── the recovery pass ───────────────────────────────────────────────────────


class _FakeResponse:
    def __init__(self, status_code=200, payload=None, text=""):
        self.status_code = status_code
        self._payload = payload or {}
        self.text = text

    def json(self):
        return self._payload


class _FakeClient:
    """Stands in for httpx.AsyncClient: availability API, then the snapshot."""

    def __init__(self, snapshot_html, available=True):
        self.snapshot_html = snapshot_html
        self.available = available
        self.calls = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def get(self, url, params=None):
        self.calls.append(url)
        if "archive.org/wayback/available" in url:
            if not self.available:
                return _FakeResponse(payload={"archived_snapshots": {}})
            return _FakeResponse(
                payload={
                    "archived_snapshots": {
                        "closest": {
                            "available": True,
                            "timestamp": "20260718000000",
                            "url": "http://web.archive.org/web/20260718000000/https://ex.com/a",
                        }
                    }
                }
            )
        return _FakeResponse(text=self.snapshot_html)


def _run(items, client, **kw):
    import app.services.title_recovery as mod

    orig = mod.httpx.AsyncClient
    mod.httpx.AsyncClient = lambda *a, **k: client
    try:
        return asyncio.run(recover_truncated_titles(items, **kw))
    finally:
        mod.httpx.AsyncClient = orig


def test_recovers_a_truncated_title_and_writes_a_receipt():
    items = [
        {
            "url": "https://ex.com/a",
            "title": "Britain braces for unprecedented water restrictions as...",
            "metadata": {},
        }
    ]
    html = (
        '<html><head><meta property="og:title" '
        'content="Britain braces for unprecedented water restrictions as reservoirs fall"'
        "></head></html>"
    )
    fixed = _run(items, _FakeClient(html))

    assert fixed == 1
    assert items[0]["title"].endswith("as reservoirs fall")
    # invariant #5 — never swap text under a source's name without a receipt
    assert items[0]["metadata"]["title_basis"] == "wayback_snapshot"
    assert items[0]["metadata"]["title_original"].endswith("as...")
    assert items[0]["metadata"]["title_snapshot_timestamp"] == "20260718000000"


def test_never_touches_a_complete_title():
    """A publisher's real headline must never be 'improved' by the archive."""
    items = [{"url": "https://ex.com/a", "title": "A complete headline"}]
    client = _FakeClient('<meta property="og:title" content="Something else entirely">')
    assert _run(items, client) == 0
    assert items[0]["title"] == "A complete headline"
    assert client.calls == []  # no archive call spent at all


def test_only_ever_lengthens():
    """A shorter snapshot title is a different title, not a recovery."""
    items = [
        {
            "url": "https://ex.com/a",
            "title": "Britain braces for unprecedented water restrictions as...",
        }
    ]
    html = '<html><head><meta property="og:title" content="Water latest"></head></html>'
    assert _run(items, _FakeClient(html)) == 0
    assert items[0]["title"].endswith("as...")


def test_no_snapshot_leaves_original_untouched():
    items = [{"url": "https://ex.com/a", "title": "Cut headline as..."}]
    assert _run(items, _FakeClient("", available=False)) == 0
    assert items[0]["title"] == "Cut headline as..."


def test_respects_the_per_claim_limit():
    items = [
        {"url": f"https://ex.com/{i}", "title": f"Headline number {i} as..."}
        for i in range(20)
    ]
    html = (
        '<html><head><meta property="og:title" '
        'content="Headline number N recovered in full from the archive"></head></html>'
    )
    fixed = _run(items, _FakeClient(html), limit=5)
    assert fixed == 5
    assert sum(1 for i in items if i["title"].endswith("as...")) == 15


def test_a_failing_archive_is_never_fatal():
    class Boom(_FakeClient):
        async def get(self, url, params=None):
            raise RuntimeError("archive down")

    items = [{"url": "https://ex.com/a", "title": "Cut headline as..."}]
    assert _run(items, Boom("")) == 0
    assert items[0]["title"] == "Cut headline as..."


def test_sits_out_a_replay_bench_run(monkeypatch):
    """A cassette miss is a hard bench error. These archive calls are cosmetic,
    not part of the behaviour the bench measures, so they must not fire under
    replay — otherwise every corpus claim goes red on unrecorded requests."""
    monkeypatch.setenv("TRU8_CASSETTE_ACTIVE", "1")
    items = [{"url": "https://ex.com/a", "title": "Cut headline as...", "metadata": {}}]
    client = _FakeClient(
        '<meta property="og:title" content="A much longer recovered headline">'
    )

    assert _run(items, client) == 0
    assert client.calls == []  # no network touched at all
    assert items[0]["title"] == "Cut headline as..."


def test_runs_normally_when_no_cassette_is_active(monkeypatch):
    monkeypatch.delenv("TRU8_CASSETTE_ACTIVE", raising=False)
    items = [{"url": "https://ex.com/a", "title": "Cut headline as...", "metadata": {}}]
    client = _FakeClient(
        '<meta property="og:title" content="A much longer recovered headline">'
    )

    assert _run(items, client) == 1
    assert items[0]["title"] == "A much longer recovered headline"
