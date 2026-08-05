"""Stateless transport on the remote MCP endpoint — the capability-scan gate.

WHY THIS FILE EXISTS
--------------------
The hosted endpoint answered `initialize` correctly and then refused everything
else. Measured against production on 2026-08-05, and reproduced locally against
mcp 1.12.4 (the version the deployed image resolved — `requirements.txt` pins a
range, `mcp[cli]>=1.2,<2`):

    initialize                                     -> 200, session id, serverInfo
    tools/list      (no notifications/initialized) -> -32602 Invalid request parameters
    tools/list      (after notifications/initialized) -> all three tools

That A/B is the evidence, and it is the whole diagnosis: one variable changed,
one outcome changed. The SDK holds each session in a NotInitialized state until
the client sends the `notifications/initialized` notification and rejects every
other request until it arrives. Requiring it is spec-correct; assuming every
client sends it is not. Smithery's capability scanner goes straight from
`initialize` to listing, so it concluded:

    No capabilities found. Warning: Failed to list tools ... resources ...
    prompts ... triggers

i.e. we would have been published as an MCP server with no tools.

(An earlier version of this file also read `triggers/list` returning -32602 as
proof the gate sat before method dispatch. It is not proof: an unknown method
returns -32602 anyway, because the SDK validates incoming requests against a
union of known methods and unknown ones simply fail validation. Measured on
both 1.12.4 and 1.29.0 with the gate removed. The A/B above stands alone.)

The fix is one line in main.py: `settings.stateless_http = True`, which starts
each session already initialised.

These tests drive the REAL FastMCP instance that main.py mounts and configures,
so deleting that line fails them. They mount it in a bare Starlette app rather
than using main.app because the only lifespan they need is the MCP session
manager's — the API's own lifespan reaches for the database.
"""

import contextlib
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from starlette.applications import Starlette
from starlette.routing import Mount

import main

MCP_HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
}

EXPECTED_TOOLS = {"tru8_check", "tru8_get_result", "tru8_get_result_raw"}


@pytest.fixture(scope="module")
def client():
    """The mounted MCP app, with only the session manager's lifespan running."""
    server = main._tru8_mcp_server

    @contextlib.asynccontextmanager
    async def lifespan(app):
        async with server.session_manager.run():
            yield

    app = Starlette(
        lifespan=lifespan,
        routes=[Mount("/mcp", app=server.streamable_http_app())],
    )
    with TestClient(app) as test_client:
        yield test_client


def _rpc(client, method, *, id=1, params=None):
    """One JSON-RPC call, returning the decoded payload.

    Responses come back as SSE (`event: message` / `data: {...}`), so the
    payload has to be picked out of the stream rather than json()-decoded.
    """
    response = client.post(
        "/mcp/",
        headers=MCP_HEADERS,
        content=json.dumps(
            {"jsonrpc": "2.0", "id": id, "method": method, "params": params or {}}
        ),
    )
    assert response.status_code == 200, response.text
    for line in response.text.splitlines():
        if line.startswith("data: "):
            return json.loads(line[6:])
    raise AssertionError(f"no data frame in response: {response.text!r}")


# ---------------------------------------------------------------------------
# The defect, pinned
# ---------------------------------------------------------------------------


def test_tools_list_works_as_the_very_first_request(client):
    """No initialize, no initialized notification — exactly what Smithery sends.

    This is the whole bug. Before stateless_http it returned
    -32602 Invalid request parameters and the scan reported no capabilities.
    """
    payload = _rpc(client, "tools/list")

    assert "error" not in payload, payload["error"]
    listed = {tool["name"] for tool in payload["result"]["tools"]}
    assert listed == EXPECTED_TOOLS


# ---------------------------------------------------------------------------
# What must NOT have broken
# ---------------------------------------------------------------------------


def test_compliant_handshake_still_lists_tools(client):
    """Clients that do it properly are unaffected.

    Claude Desktop and the MCP Inspector send initialize, then the notification,
    then list. Stateless mode must not be a trade of one client for another.
    """
    initialised = _rpc(
        client,
        "initialize",
        params={
            "protocolVersion": "2025-06-18",
            "capabilities": {},
            "clientInfo": {"name": "guard-test", "version": "0"},
        },
    )
    assert initialised["result"]["serverInfo"]["name"] == "tru8"

    notification = client.post(
        "/mcp/",
        headers=MCP_HEADERS,
        content=json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}),
    )
    assert notification.status_code == 202

    payload = _rpc(client, "tools/list", id=2)
    assert {tool["name"] for tool in payload["result"]["tools"]} == EXPECTED_TOOLS


def test_tool_descriptions_survive_for_the_scanner(client):
    """A scan that lists tools with empty descriptions is barely better.

    Smithery renders these on the listing page, so they are the shop window.
    """
    payload = _rpc(client, "tools/list")

    for tool in payload["result"]["tools"]:
        assert tool.get("description"), f"{tool['name']} has no description"
        assert tool.get("inputSchema", {}).get("properties"), tool["name"]


# ---------------------------------------------------------------------------
# Drift guards
# ---------------------------------------------------------------------------


def test_public_host_header_is_served(client):
    """The endpoint must answer on its real hostname, on every SDK in the range.

    FastMCP auto-enables DNS rebinding protection with a localhost-only
    allowlist when `host` is the default 127.0.0.1 — ours is. Measured on
    mcp 1.29.0 without the transport_security override:

        Host: api.trueight.com -> 421 Misdirected Request

    Production survives today only because its image resolved mcp 1.12.4,
    which predates that behaviour. requirements.txt allows both. If this test
    fails, /mcp is dead in production for every client.
    """
    public = TestClient(client.app, base_url="http://api.trueight.com")
    response = public.post(
        "/mcp/",
        headers=MCP_HEADERS,
        content=json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/list"}),
    )

    assert response.status_code == 200, f"expected 200, got {response.status_code}"


def test_browser_origin_is_not_rejected_by_transport_security(client):
    """The same protection also validates Origin, which is a CORS-shaped trap.

    On mcp 1.29.0 an Origin of https://smithery.ai returned 403 before the
    override — a rejection that happens INSIDE the MCP app, so no amount of
    CORS middleware in front of it (see test_mcp_cors.py) would help. That
    covers the Smithery playground and the MCP Inspector.
    """
    response = client.post(
        "/mcp/",
        headers={**MCP_HEADERS, "Origin": "https://smithery.ai"},
        content=json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/list"}),
    )

    assert response.status_code == 200, f"expected 200, got {response.status_code}"


def test_hosted_transport_is_configured_stateless():
    """Pins the setting itself, in case the behavioural tests are ever skipped."""
    assert main._tru8_mcp_server.settings.stateless_http is True


def test_transport_security_is_stated_not_inherited():
    """The value must be set deliberately, not left to the SDK's default.

    The default is version-dependent and changed under us mid-range. Asserting
    the object exists is the point: `None` would mean we are inheriting again.
    """
    security = main._tru8_mcp_server.settings.transport_security

    assert security is not None, "transport_security left to the SDK default"
    assert security.enable_dns_rebinding_protection is False


def test_published_stdio_package_does_not_set_stateless():
    """Scope guard: this is a HOSTED-transport decision only.

    tru8_mcp/server.py ships to PyPI and runs over stdio, where one process
    serves one user and the setting is meaningless. It is applied in main.py
    for the same reason streamable_http_path is — so the published package
    keeps stock settings.
    """
    source = Path(main.__file__).parent / "tru8_mcp" / "server.py"
    assert "stateless_http" not in source.read_text(encoding="utf-8")
