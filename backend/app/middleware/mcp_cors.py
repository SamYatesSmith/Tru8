"""CORS for the remote MCP endpoint, scoped to that path alone.

WHY THIS EXISTS
---------------
The app-level ``CORSMiddleware`` is deliberately tight: a fixed origin
allowlist and ``allow_credentials=True``, because the dashboard API is called
by our own site with a Clerk session attached. Those settings are correct
there and **wrong** for ``/mcp``, which is a public protocol endpoint that
arbitrary third-party clients are *supposed* to call from other origins.

Measured against production on 2026-08-05, before this existed:

    OPTIONS /mcp/  Origin: https://smithery.ai
    → 400 "Disallowed CORS origin, headers"

    OPTIONS /mcp/  Origin: https://www.trueight.com   (an allowed origin)
    → 400 "Disallowed CORS headers"

The second is the telling one. The MCP streamable-HTTP spec requires the
client to read ``Mcp-Session-Id`` off the initialize response and echo it on
every later request. ``mcp-session-id`` was in neither ``allow_headers`` nor
``expose_headers``, so a browser could not send it *or* read it — meaning **no
browser-based MCP client could hold a session with us from any origin at all**,
including our own. Non-browser clients (Claude Desktop, curl, server-side
agents) were unaffected, which is exactly why this survived the launch checks:
CORS is enforced by browsers and by nothing else.

WHY PERMISSIVE ORIGINS ARE SAFE HERE, AND ONLY HERE
---------------------------------------------------
``allow_credentials`` is **False** on this path. That is the load-bearing
detail, not an oversight:

* With credentials off, a browser attaches no cookies to these requests, so
  there is no ambient authority for a hostile page to borrow. The only way to
  authenticate an MCP tool call is to present an API key explicitly, and a
  hostile page does not have the user's key.
* The MCP path never reads cookies — ``tru8_mcp.server._request_api_key()``
  reads ``X-API-Key``, ``Authorization`` or a query parameter, nothing else.
* Widening the *app-level* policy instead would have loosened CORS on the
  authenticated dashboard API, which is a genuine security regression. Hence
  the path scoping: everything outside ``/mcp`` is passed straight through to
  the existing middleware, untouched.

The transport spec's "servers MUST validate the Origin header" warning is
aimed at DNS-rebinding against servers reachable at a private or loopback
address, where network position implies trust. This endpoint is public and
key-authenticated, so origin is not what protects it — the key is.

ORDERING MATTERS
----------------
Starlette's ``CORSMiddleware`` answers a preflight and returns immediately
without calling downstream. So this must sit **outside** the app-level CORS
middleware or it will never see an ``OPTIONS`` request. ``add_middleware``
inserts at the front of the list and the stack is built in reverse, so the
**last** middleware added is the outermost: register this one *after* the
app-level CORS block. See the wiring comment in ``main.py``.
"""

from starlette.middleware.cors import CORSMiddleware
from starlette.types import ASGIApp, Receive, Scope, Send

# Request headers a spec-compliant MCP client sends. `mcp-session-id` and
# `mcp-protocol-version` are required by the 2025-06-18 streamable-HTTP spec;
# `last-event-id` is the SSE resumption header. Listed explicitly rather than
# "*" so the set stays auditable.
#
# 2026-08-10 — `Mcp-Method` and `Mcp-Name` added. Spec revision 2026-07-28 makes
# them REQUIRED on streamable-HTTP POSTs (SEP-2243, with server-side header↔body
# validation and a new -32020 HeaderMismatch error). Measured against production
# before this change:
#
#     OPTIONS /mcp/  Access-Control-Request-Headers: content-type, mcp-method, mcp-name
#     → 400 Bad Request
#     OPTIONS /mcp/  Access-Control-Request-Headers: content-type, mcp-session-id, mcp-protocol-version
#     → 200 OK                                                          (control)
#
# This is the SAME failure as `mcp-session-id` above, one revision later, and it
# recurs because this list is hand-maintained against a moving spec. We do not
# yet SERVE 2026-07-28 — the SDK pin holds us at 2025-06-18 — but a modern
# client's preflight has to succeed before it can discover that and fall back.
# Being unable to negotiate is worse than being old.
#
# NOT added: the optional `Mcp-Param-{Name}` family from the same SEP. Those are
# driven by `x-mcp-header` in a tool's input schema, none of our three tools
# declare one, and CORS allow-lists cannot express a prefix wildcard.
MCP_ALLOW_HEADERS = [
    "Accept",
    "Authorization",
    "Content-Type",
    "Last-Event-ID",
    "MCP-Method",
    "MCP-Name",
    "MCP-Protocol-Version",
    "Mcp-Session-Id",
    "X-API-Key",
]

# Response headers a browser client must be able to READ. Without this the
# client cannot learn its own session id, and every request after initialize
# is rejected as sessionless.
MCP_EXPOSE_HEADERS = ["Mcp-Session-Id"]

# GET opens the server→client SSE stream; DELETE terminates a session. Both
# are part of the transport, not optional extras.
MCP_ALLOW_METHODS = ["GET", "POST", "DELETE", "OPTIONS"]


class _OriginStripped:
    """Hide the ``Origin`` header from everything downstream.

    Starlette's ``CORSMiddleware`` attaches its ``simple_headers`` to *any*
    response whose request carried an ``Origin`` — the allowlist only decides
    whether the origin is echoed back, not whether headers are added at all.
    So without this, an ``/mcp`` response passed through the app-level policy
    on its way out and picked up ``Access-Control-Allow-Credentials: true``
    to sit beside our ``Access-Control-Allow-Origin: *``. That pair is invalid
    under the CORS spec and a browser rejects it outright for any client that
    sends credentials.

    Removing the header here means the app-level middleware sees no CORS
    request at all and returns early, leaving exactly one policy on this path:
    ours. The ``Origin`` value is still visible to *our* CORS layer, which sits
    outside this wrapper and reads it before delegating.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        scope = dict(scope)
        scope["headers"] = [
            (k, v) for k, v in scope.get("headers", []) if k.lower() != b"origin"
        ]
        await self.app(scope, receive, send)


class MCPCorsMiddleware:
    """Apply an MCP-appropriate CORS policy to ``path_prefix`` only.

    Delegates to Starlette's own ``CORSMiddleware`` for matching paths rather
    than reimplementing preflight handling — the policy is what differs here,
    not the mechanics.
    """

    def __init__(self, app: ASGIApp, path_prefix: str = "/mcp") -> None:
        self.app = app
        self.path_prefix = path_prefix
        self.cors = CORSMiddleware(
            _OriginStripped(app),
            allow_origins=["*"],
            # See module docstring — this is what makes "*" safe here.
            allow_credentials=False,
            allow_methods=MCP_ALLOW_METHODS,
            allow_headers=MCP_ALLOW_HEADERS,
            expose_headers=MCP_EXPOSE_HEADERS,
            max_age=600,
        )

    def _handles(self, scope: Scope) -> bool:
        if scope.get("type") != "http":
            return False
        path = scope.get("path", "")
        # Matches "/mcp" and "/mcp/..." but deliberately not "/mcphooks".
        return path == self.path_prefix or path.startswith(self.path_prefix + "/")

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if not self._handles(scope):
            await self.app(scope, receive, send)
            return
        await self.cors(scope, receive, send)
