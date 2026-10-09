"""Gzip for ordinary responses; event streams pass through untouched.

WHY THIS EXISTS
---------------
Starlette 0.41's ``GZipMiddleware`` compresses streaming responses by writing
each chunk into a ``GzipFile`` and sending whatever the compressor has emitted
so far. It never flushes, so a small write (an SSE heartbeat, an MCP
``: ping``, a progress event) emits **zero bytes** until enough data piles up
or the stream ends. Measured in production on 2026-10-09: every long
``GET /mcp/`` stream sent exactly 10 bytes (the gzip header) in ~75 s despite
a ping every 15 s. Cloudflare drops an origin that is silent for 125 s, and a
browser sees progress arrive in bursts.

Newer Starlette exempts ``text/event-stream`` from compression for this
reason. This class applies the same rule on the version we run: an event
stream is treated exactly like a response that already set its own
``Content-Encoding`` — passed through as written. Everything else is
compressed as before.

Relies on two private Starlette names (``send_with_gzip``,
``content_encoding_set``). When FastAPI is upgraded past the Starlette
version that exempts event streams itself, delete this module and go back
to the stock middleware; the guard tests will fail if the names change.

Record: audit/2026-10-08_complex_stage_functions_review.md, F11.
Guard: tests/unit/test_sse_gzip.py (runs against the real app's stack).
"""

from starlette.datastructures import Headers
from starlette.middleware.gzip import GZipMiddleware, GZipResponder
from starlette.types import Message, Receive, Scope, Send

_PASSTHROUGH_CONTENT_TYPES = ("text/event-stream",)


class _StreamAwareGZipResponder(GZipResponder):
    async def send_with_gzip(self, message: Message) -> None:
        await super().send_with_gzip(message)
        if message["type"] == "http.response.start":
            content_type = Headers(raw=message["headers"]).get("content-type", "")
            if content_type.lower().startswith(_PASSTHROUGH_CONTENT_TYPES):
                # Reuse Starlette's own pass-through branch.
                self.content_encoding_set = True


class StreamAwareGZipMiddleware(GZipMiddleware):
    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http":
            headers = Headers(scope=scope)
            if "gzip" in headers.get("Accept-Encoding", ""):
                responder = _StreamAwareGZipResponder(
                    self.app, self.minimum_size, compresslevel=self.compresslevel
                )
                await responder(scope, receive, send)
                return
        await self.app(scope, receive, send)
