"""YouTube returns HTML-escaped snippet text (A− S6, 2026-10-06: the VIDEO lens
showed "Europe&#39;s …" on #13, #14, #16, #17). Decoded at ingest, and
by migration `video_text_unescape` for rows stored before the fix. Decoded
exactly once, so literal entity text in a title survives."""

from types import SimpleNamespace

import httpx
import pytest

from app.api.v1.checks import _video_to_dict
from app.services.api_adapters import youtube


def _row(**kw):
    base = dict(
        id="v1",
        claim_id="c1",
        video_id="abc",
        title="t",
        description="d",
        channel_name="ch",
        channel_id="cid",
        publish_date=None,
        video_url="https://www.youtube.com/watch?v=abc",
        thumbnail_url=None,
        duration=None,
        tier_label=None,
        type_label=None,
    )
    base.update(kw)
    return SimpleNamespace(**base)


@pytest.mark.unit
def test_served_video_text_is_passed_through_once_decoded():
    # Decoded ONCE at ingest (and by migration video_text_unescape for older
    # rows). Serving must not decode again, or a literal "&lt;" becomes "<".
    d = _video_to_dict(_row(title="a &lt; b", description=None))
    assert d["title"] == "a &lt; b"
    assert d["description"] is None


@pytest.mark.unit
def test_every_video_serializer_uses_the_shared_helper():
    import inspect
    from app.api.v1 import checks

    src = inspect.getsource(checks)
    assert src.count('"channelName": v.channel_name') == 1  # the helper only
    assert src.count("_video_to_dict(v)") >= 4


@pytest.mark.unit
def test_adapter_decodes_snippet_text_at_ingest(monkeypatch):
    import asyncio

    def handler(request):
        if "search" in str(request.url):
            return httpx.Response(
                200,
                json={
                    "items": [
                        {
                            "id": {"videoId": "abc"},
                            "snippet": {
                                "title": "Why Europe&#39;s Wildfires Keep Getting Worse",
                                "description": "Fire &amp; smoke",
                                "channelTitle": "DW &amp; News",
                            },
                        }
                    ]
                },
            )
        return httpx.Response(200, json={"items": []})

    real = httpx.AsyncClient
    monkeypatch.setattr(youtube.settings, "YOUTUBE_API_KEY", "k", raising=False)
    monkeypatch.setattr(
        youtube.httpx,
        "AsyncClient",
        lambda **kw: real(transport=httpx.MockTransport(handler), **kw),
    )
    videos = asyncio.run(youtube.search_youtube_videos("wildfires"))
    assert videos[0]["title"] == "Why Europe's Wildfires Keep Getting Worse"
    assert videos[0]["description"] == "Fire & smoke"
    assert videos[0]["channel_name"] == "DW & News"
