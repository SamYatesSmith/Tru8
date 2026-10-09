"""Event streams must leave the server as they are written, never gzip-buffered.

WHY THIS FILE EXISTS
--------------------
The app compresses responses with Starlette's ``GZipMiddleware``. On a
streaming response it feeds each chunk to a ``GzipFile`` and sends whatever
the compressor has emitted so far — and for a small write (an SSE heartbeat,
an MCP ``: ping``, a progress event) that is nothing. Measured in production
on 2026-10-09: all 45 ``GET /mcp/`` streams longer than 30 s in the Railway
HTTP log sent exactly 10 bytes (the gzip header) in ~75 s, despite a ping
every 15 s. Cloudflare's 125 s proxy read timeout sees an idle origin; a
browser sees progress arrive in bursts. Record:
audit/2026-10-08_complex_stage_functions_review.md, F11.

These tests take the gzip middleware from the REAL app's stack, so swapping
the class back in ``main.py`` fails them.
"""

import gzip

import pytest

import main


def _gzip_middleware():
    for mw in main.app.user_middleware:
        if "gzip" in mw.cls.__name__.lower():
            return mw.cls, mw.kwargs
    raise AssertionError("no gzip middleware registered on main.app")


def _streaming_app(content_type: str, chunks: list[bytes]):
    async def app(scope, receive, send):
        await send(
            {
                "type": "http.response.start",
                "status": 200,
                "headers": [(b"content-type", content_type.encode())],
            }
        )
        for chunk in chunks:
            await send({"type": "http.response.body", "body": chunk, "more_body": True})
        await send({"type": "http.response.body", "body": b"", "more_body": False})

    return app


async def _run(app, accept_encoding: str = "gzip, deflate, br"):
    cls, kwargs = _gzip_middleware()
    wrapped = cls(app, **kwargs)
    sent = []

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        sent.append(message)

    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": [(b"accept-encoding", accept_encoding.encode())],
    }
    await wrapped(scope, receive, send)
    return sent


def _headers(start_message) -> dict:
    return {k.decode().lower(): v.decode() for k, v in start_message["headers"]}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "content_type", ["text/event-stream", "text/event-stream; charset=utf-8"]
)
async def test_event_stream_chunks_leave_uncompressed_and_unbuffered(content_type):
    chunks = [b": ping\n\n", b'data: {"progress": 35}\n\n', b": ping\n\n"]
    sent = await _run(_streaming_app(content_type, chunks))

    start = sent[0]
    assert start["type"] == "http.response.start"
    assert "content-encoding" not in _headers(start)
    bodies = [m["body"] for m in sent[1:] if m["type"] == "http.response.body"]
    # Every heartbeat goes out the moment it is written, byte for byte.
    assert bodies[: len(chunks)] == chunks


@pytest.mark.asyncio
async def test_large_json_is_still_gzipped():
    body = b'{"x": "' + b"a" * 5000 + b'"}'

    async def app(scope, receive, send):
        await send(
            {
                "type": "http.response.start",
                "status": 200,
                "headers": [(b"content-type", b"application/json")],
            }
        )
        await send({"type": "http.response.body", "body": body, "more_body": False})

    sent = await _run(app)
    assert _headers(sent[0]).get("content-encoding") == "gzip"
    assert gzip.decompress(sent[1]["body"]) == body


@pytest.mark.asyncio
async def test_event_stream_without_gzip_accepted_is_untouched():
    chunks = [b": ping\n\n"]
    sent = await _run(_streaming_app("text/event-stream", chunks), accept_encoding="")
    assert [m["body"] for m in sent[1:]][:1] == chunks


@pytest.mark.asyncio
async def test_single_body_event_stream_passes_through():
    async def app(scope, receive, send):
        await send(
            {
                "type": "http.response.start",
                "status": 200,
                "headers": [(b"content-type", b"text/event-stream")],
            }
        )
        await send({"type": "http.response.body", "body": b": ping\n\n"})

    sent = await _run(app)
    assert "content-encoding" not in _headers(sent[0])
    assert sent[1]["body"] == b": ping\n\n"
