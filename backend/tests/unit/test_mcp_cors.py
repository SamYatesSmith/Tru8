"""CORS on the remote MCP endpoint — the browser-client acceptance gate.

WHY THIS FILE EXISTS
--------------------
The hosted MCP endpoint shipped on 2026-08-04 and was verified end to end with
curl and a live listener. Both are non-browser clients, and CORS is enforced by
browsers and by nothing else — so the verification could not have caught what
was actually broken. Measured against production on 2026-08-05:

    OPTIONS /mcp/  Origin: https://smithery.ai        → 400 "Disallowed CORS origin, headers"
    OPTIONS /mcp/  Origin: https://www.trueight.com   → 400 "Disallowed CORS headers"

The second line is the one that matters: `mcp-session-id` was in neither
`allow_headers` nor `expose_headers`, so a browser could neither send it nor
read it. The streamable-HTTP spec requires the client to echo that header on
every request after initialize, so **no browser-based MCP client could hold a
session with us from any origin** — including our own site. That covers
Smithery's playground and the MCP Inspector, i.e. the two things a stranger
evaluating Tru8 is most likely to point at us.

These tests run against the REAL app object, not a reconstruction, because the
failure mode is an ordering interaction between two middlewares: Starlette
answers a preflight and returns without calling downstream, so the MCP policy
only ever runs if it is registered OUTSIDE the app-level one. A test that
rebuilt its own app would pass while production stayed broken.

The last test is the drift guard, and it is the important one.
"""

import pytest
from fastapi.testclient import TestClient
from starlette.middleware.cors import CORSMiddleware

import main
from app.middleware.mcp_cors import MCPCorsMiddleware

# No `with` — that would run the lifespan (DB, MCP session manager). Every
# request below is either a preflight (short-circuited by the middleware) or
# the bare-/mcp redirect route, so none of them reach the mounted sub-app.
client = TestClient(main.app, follow_redirects=False)

FOREIGN = "https://smithery.ai"


def _preflight(
    path, origin=FOREIGN, headers="content-type, mcp-session-id", method="POST"
):
    return client.options(
        path,
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": method,
            "Access-Control-Request-Headers": headers,
        },
    )


# ---------------------------------------------------------------------------
# The defect, pinned
# ---------------------------------------------------------------------------


class TestBrowserClientsCanConnect:
    def test_preflight_from_a_foreign_origin_is_allowed(self):
        """An MCP client is a third-party app by definition — origin cannot gate it."""
        r = _preflight("/mcp/")
        assert r.status_code == 200, r.text
        assert r.headers["access-control-allow-origin"] == "*"

    def test_session_header_is_accepted_on_the_request(self):
        """Without this the preflight 400s and the client never gets to send anything."""
        r = _preflight("/mcp/")
        allowed = r.headers["access-control-allow-headers"].lower()
        assert "mcp-session-id" in allowed

    def test_protocol_version_header_is_accepted(self):
        """Required on every post-initialize request by the 2025-06-18 spec."""
        r = _preflight("/mcp/", headers="content-type, mcp-protocol-version")
        assert r.status_code == 200
        assert (
            "mcp-protocol-version" in r.headers["access-control-allow-headers"].lower()
        )

    def test_resumption_header_is_accepted(self):
        """Last-Event-ID is how a dropped SSE stream resumes."""
        r = _preflight("/mcp/", headers="last-event-id")
        assert r.status_code == 200
        assert "last-event-id" in r.headers["access-control-allow-headers"].lower()

    def test_2026_mandatory_routing_headers_are_accepted(self):
        """`Mcp-Method`/`Mcp-Name` are REQUIRED on POSTs by spec revision
        2026-07-28 (SEP-2243). Measured against production before the fix, this
        exact preflight returned 400 while the 2025-era header set returned 200.

        We do not serve 2026-07-28 yet — the SDK pin holds us at 2025-06-18 —
        but a modern client has to get through the preflight before it can
        discover that and fall back. Being unable to negotiate is worse than
        being old.
        """
        r = _preflight("/mcp/", headers="content-type, mcp-method, mcp-name")
        assert r.status_code == 200, r.text
        allowed = r.headers["access-control-allow-headers"].lower()
        assert "mcp-method" in allowed
        assert "mcp-name" in allowed

    def test_api_key_header_is_accepted(self):
        """The only way a browser client can authenticate a tool call."""
        r = _preflight("/mcp/", headers="x-api-key")
        assert r.status_code == 200
        assert "x-api-key" in r.headers["access-control-allow-headers"].lower()

    @pytest.mark.parametrize("method", ["GET", "POST", "DELETE"])
    def test_transport_methods_are_allowed(self, method):
        """POST sends messages, GET opens the server stream, DELETE ends a session."""
        r = _preflight("/mcp/", method=method)
        assert r.status_code == 200
        assert method in r.headers["access-control-allow-methods"]

    def test_session_header_is_readable_on_the_response(self):
        """The client must READ Mcp-Session-Id off initialize, not just send it.

        Asserted on the bare-/mcp redirect, which is a real response through the
        real middleware stack and needs no session manager. `expose_headers` is
        absent from preflight responses by design, so it cannot be checked there.
        """
        r = client.post("/mcp", headers={"Origin": FOREIGN}, json={})
        assert r.status_code == 307
        exposed = r.headers.get("access-control-expose-headers", "").lower()
        assert "mcp-session-id" in exposed


# ---------------------------------------------------------------------------
# What must NOT have been loosened
# ---------------------------------------------------------------------------


class TestApiPolicyUnchanged:
    def test_foreign_origin_still_rejected_on_the_dashboard_api(self):
        """The whole point of scoping. A blanket widening would be a real regression."""
        r = _preflight("/api/v1/checks", headers="content-type")
        assert r.status_code == 400
        assert "Disallowed CORS origin" in r.text

    def test_root_path_is_not_covered(self):
        r = _preflight("/", headers="content-type")
        assert r.status_code == 400

    def test_mcp_policy_does_not_allow_credentials(self):
        """Load-bearing: it is what makes allow_origins=* safe on this path.

        Credentials off means no cookies ride along, so a hostile page has no
        ambient authority to borrow — a tool call requires an API key it does
        not have.

        Asserted on the wire rather than on middleware internals: Starlette
        keeps no `allow_credentials` attribute, and the header a browser acts
        on is the only thing that actually decides this.
        """
        pre = _preflight("/mcp/")
        assert "access-control-allow-credentials" not in {
            k.lower() for k in pre.headers
        }

        real = client.post("/mcp", headers={"Origin": FOREIGN}, json={})
        assert "access-control-allow-credentials" not in {
            k.lower() for k in real.headers
        }
        # Wildcard origin and credentials are mutually exclusive in the CORS
        # spec; a browser rejects the pair outright. Pin that we send the safe
        # combination and not the one that silently breaks every client.
        assert real.headers["access-control-allow-origin"] == "*"

    def test_prefix_match_is_not_a_bare_startswith(self):
        """'/mcp' must not swallow a future '/mcpsomething' route."""
        mw = MCPCorsMiddleware(app=lambda *a: None)
        assert mw._handles({"type": "http", "path": "/mcp"})
        assert mw._handles({"type": "http", "path": "/mcp/"})
        assert not mw._handles({"type": "http", "path": "/mcphooks"})
        assert not mw._handles({"type": "websocket", "path": "/mcp"})


# ---------------------------------------------------------------------------
# The drift guard
# ---------------------------------------------------------------------------


def test_mcp_cors_is_registered_outside_the_app_level_cors():
    """Ordering IS the feature.

    Starlette's CORSMiddleware answers a preflight and returns without calling
    downstream. If MCPCorsMiddleware were registered before it (i.e. ended up
    inside it), every MCP preflight would be answered by the restrictive policy
    and this file's tests above would be the only thing to notice. Registration
    order is not obvious from reading main.py top to bottom, so pin it.

    `user_middleware` is outermost-first.
    """
    order = [m.cls for m in main.app.user_middleware]
    assert MCPCorsMiddleware in order, "MCP CORS middleware is not registered at all"
    assert CORSMiddleware in order
    assert order.index(MCPCorsMiddleware) < order.index(CORSMiddleware), (
        "MCPCorsMiddleware must be added AFTER the app-level CORSMiddleware so it "
        "sits outside it. Registered inside, it never sees an OPTIONS request."
    )
