"""Tests for the deterministic HTTP cassette used by the replay bench.

These are LLM-free and network-free: a fake "real" send stands in for the live
network so we can assert record/replay/miss/redaction behaviour without spend.
"""

import json
from pathlib import Path

import httpx
import pytest

from scripts.replay_bench.cassette import (
    CassetteMiss,
    HttpxCassette,
    _canonical_signature,
)


def test_signature_is_secret_independent():
    a = httpx.Request("POST", "https://api/search?key=SECRET1", json={"q": "x"})
    b = httpx.Request("POST", "https://api/search?key=SECRET2", json={"q": "x"})
    assert _canonical_signature(a) == _canonical_signature(b)


def test_signature_is_body_sensitive():
    a = httpx.Request("POST", "https://api/search", json={"q": "hello"})
    b = httpx.Request("POST", "https://api/search", json={"q": "world"})
    assert _canonical_signature(a) != _canonical_signature(b)


def test_signature_ignores_query_order():
    a = httpx.Request("GET", "https://api/x?a=1&b=2")
    b = httpx.Request("GET", "https://api/x?b=2&a=1")
    assert _canonical_signature(a) == _canonical_signature(b)


@pytest.fixture
def fake_network(monkeypatch):
    """Patch AsyncClient.send so 'live' calls echo a deterministic response.

    HttpxCassette captures whatever AsyncClient.send is at enter-time as its
    _orig_send, so this fake becomes the recorded backend.
    """
    counter = {"n": 0}

    async def _fake_send(self, request, **kwargs):
        counter["n"] += 1
        payload = json.loads(request.content) if request.content else {}
        return httpx.Response(
            200, json={"echo": payload.get("q"), "call": counter["n"]}, request=request
        )

    monkeypatch.setattr(httpx.AsyncClient, "send", _fake_send)
    return counter


@pytest.mark.asyncio
async def test_record_writes_scrubbed_cassette(tmp_path: Path, fake_network):
    cassette_path = tmp_path / "cassette.json"
    with HttpxCassette(cassette_path, "record"):
        async with httpx.AsyncClient() as c:
            r = await c.post("https://api/search?key=SECRET1", json={"q": "hello"})
            assert r.json()["echo"] == "hello"

    assert cassette_path.exists()
    raw = cassette_path.read_text(encoding="utf-8")
    assert "SECRET1" not in raw
    assert "__REDACTED__" in raw


@pytest.mark.asyncio
async def test_replay_serves_without_network(tmp_path: Path, fake_network):
    cassette_path = tmp_path / "cassette.json"
    with HttpxCassette(cassette_path, "record"):
        async with httpx.AsyncClient() as c:
            await c.post("https://api/search?key=SECRET1", json={"q": "hello"})

    calls_before = fake_network["n"]
    with HttpxCassette(cassette_path, "replay"):
        async with httpx.AsyncClient() as c:
            # rotated key, still matches; no new network call
            r = await c.post("https://api/search?key=ROTATED", json={"q": "hello"})
            assert r.json()["echo"] == "hello"
    assert fake_network["n"] == calls_before  # replay made no live call


@pytest.mark.asyncio
async def test_replay_miss_is_fatal(tmp_path: Path, fake_network):
    cassette_path = tmp_path / "cassette.json"
    with HttpxCassette(cassette_path, "record"):
        async with httpx.AsyncClient() as c:
            await c.post("https://api/search?key=K", json={"q": "recorded"})

    with HttpxCassette(cassette_path, "replay"):
        async with httpx.AsyncClient() as c:
            with pytest.raises(CassetteMiss):
                await c.post("https://api/search?key=K", json={"q": "UNRECORDED"})


# -- sync httpx.Client interception (2026-07-06) ----------------------------
# GovernmentAPIClient adapters (NOAA, GovInfo, Hansard, ...) ride sync
# httpx.Client; before the sync patch they ran LIVE inside "deterministic"
# replay (masked by the 24h tru8:api_response cache — the Friday-green/
# Monday-red drift). These tests pin the sync path so it can't regress.


@pytest.fixture
def fake_sync_network(monkeypatch):
    """Patch sync Client.send so 'live' sync calls echo deterministically."""
    counter = {"n": 0}

    def _fake_send(self, request, **kwargs):
        counter["n"] += 1
        payload = json.loads(request.content) if request.content else {}
        return httpx.Response(
            200, json={"echo": payload.get("q"), "call": counter["n"]}, request=request
        )

    monkeypatch.setattr(httpx.Client, "send", _fake_send)
    return counter


def test_sync_record_and_replay(tmp_path: Path, fake_sync_network):
    cassette_path = tmp_path / "cassette.json"
    with HttpxCassette(cassette_path, "record"):
        with httpx.Client() as c:
            r = c.post("https://api/adapter?key=SECRET9", json={"q": "noaa"})
            assert r.json()["echo"] == "noaa"

    raw = cassette_path.read_text(encoding="utf-8")
    assert "SECRET9" not in raw
    assert "__REDACTED__" in raw

    calls_before = fake_sync_network["n"]
    with HttpxCassette(cassette_path, "replay"):
        with httpx.Client() as c:
            r = c.post("https://api/adapter?key=ROTATED", json={"q": "noaa"})
            assert r.json()["echo"] == "noaa"
    assert fake_sync_network["n"] == calls_before  # replay made no live sync call


def test_sync_replay_miss_is_fatal(tmp_path: Path, fake_sync_network):
    cassette_path = tmp_path / "cassette.json"
    with HttpxCassette(cassette_path, "record"):
        with httpx.Client() as c:
            c.post("https://api/adapter?key=K", json={"q": "recorded"})

    with HttpxCassette(cassette_path, "replay"):
        with httpx.Client() as c:
            with pytest.raises(CassetteMiss):
                c.post("https://api/adapter?key=K", json={"q": "UNRECORDED"})


def test_sync_send_restored_after_exit(tmp_path: Path, fake_sync_network):
    cassette_path = tmp_path / "cassette.json"
    before = httpx.Client.send
    with HttpxCassette(cassette_path, "record"):
        assert httpx.Client.send is not before
        with httpx.Client() as c:
            c.post("https://api/adapter", json={"q": "x"})
    assert httpx.Client.send is before


@pytest.mark.asyncio
async def test_sync_and_async_share_one_cassette(
    tmp_path: Path, fake_network, fake_sync_network
):
    """One recorded store serves both client classes — a request is a request."""
    cassette_path = tmp_path / "cassette.json"
    with HttpxCassette(cassette_path, "record"):
        async with httpx.AsyncClient() as ac:
            await ac.post("https://api/llm", json={"q": "async-call"})
        with httpx.Client() as sc:
            sc.post("https://api/adapter", json={"q": "sync-call"})

    with HttpxCassette(cassette_path, "replay") as cas:
        async with httpx.AsyncClient() as ac:
            r1 = await ac.post("https://api/llm", json={"q": "async-call"})
        with httpx.Client() as sc:
            r2 = sc.post("https://api/adapter", json={"q": "sync-call"})
        assert r1.json()["echo"] == "async-call"
        assert r2.json()["echo"] == "sync-call"
        assert cas.stats["misses"] == 0
        assert cas.stats["hits"] == 2
