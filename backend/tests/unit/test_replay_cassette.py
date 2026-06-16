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
