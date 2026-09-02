"""The MCP client sends an Idempotency-Key on every agent call (2026-09-02).

Why: over the hosted transport the streamable-HTTP stream dies at ~140 s, the
client re-initialises and re-sends the pending tool call, and the server runs
it again — one tru8_check produced two charged checks (dd2ca726 + c8dd4886).
The API already honours the header (agent_auth.py: same key + same request
hash → the first transaction is returned); the client never sent one.

Pins: the key is stable for an identical call inside a ten-minute window,
differs across payloads, endpoints and windows, and actually reaches the
request headers of both agent POSTs.
"""

from types import SimpleNamespace

import pytest

import tru8_mcp.tools as tools
from tru8_mcp.tools import Tru8APIClient, idempotency_key_for


@pytest.mark.unit
class TestKeyDerivation:
    def test_same_call_same_window_same_key(self):
        p = {"claim": "x", "max_tier": "full", "max_age_hours": 0, "compact": False}
        assert idempotency_key_for("agent/check", p, now=10.0) == idempotency_key_for(
            "agent/check", p, now=590.0
        )

    def test_key_changes_with_payload_endpoint_and_window(self):
        p = {"claim": "x", "max_tier": "full"}
        base = idempotency_key_for("agent/check", p, now=10.0)
        assert idempotency_key_for("agent/check", {**p, "claim": "y"}, now=10.0) != base
        assert (
            idempotency_key_for("agent/check", {**p, "max_age_hours": 0}, now=10.0)
            != base
        )
        assert idempotency_key_for("agent/full", p, now=10.0) != base
        assert idempotency_key_for("agent/check", p, now=610.0) != base

    def test_key_shape(self):
        k = idempotency_key_for("agent/check", {"claim": "x"}, now=0.0)
        assert k.startswith("mcp-") and len(k) == 44


class _FakeResponse:
    status_code = 200

    def json(self):
        return {"ok": True}


class _FakeClient:
    """Stands in for httpx.AsyncClient; records the POST it receives."""

    calls = []

    def __init__(self, *a, **kw):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def post(self, url, json=None, headers=None):
        _FakeClient.calls.append(SimpleNamespace(url=url, json=json, headers=headers))
        return _FakeResponse()


@pytest.mark.unit
@pytest.mark.asyncio
class TestHeaderReachesTheRequest:
    async def test_smart_endpoint_carries_the_key(self, monkeypatch):
        _FakeClient.calls.clear()
        monkeypatch.setattr(tools.httpx, "AsyncClient", _FakeClient)
        monkeypatch.setattr(tools.time, "time", lambda: 1000.0)

        await Tru8APIClient(api_key="k").submit_smart(
            "some claim", max_tier="full", max_age_hours=0
        )

        call = _FakeClient.calls[-1]
        assert call.url.endswith("/api/v1/agent/check")
        expected = idempotency_key_for("agent/check", call.json, now=1000.0)
        assert call.headers["Idempotency-Key"] == expected
        assert call.headers["X-API-Key"] == "k"

    async def test_tier_endpoint_carries_the_key(self, monkeypatch):
        _FakeClient.calls.clear()
        monkeypatch.setattr(tools.httpx, "AsyncClient", _FakeClient)
        monkeypatch.setattr(tools.time, "time", lambda: 1000.0)

        await Tru8APIClient(api_key="k").submit_tier("some claim", tier="quick")

        call = _FakeClient.calls[-1]
        assert call.url.endswith("/api/v1/agent/quick")
        assert call.headers["Idempotency-Key"] == idempotency_key_for(
            "agent/quick", call.json, now=1000.0
        )

    async def test_a_retry_inside_the_window_sends_the_same_key(self, monkeypatch):
        _FakeClient.calls.clear()
        monkeypatch.setattr(tools.httpx, "AsyncClient", _FakeClient)
        clock = {"t": 1000.0}
        monkeypatch.setattr(tools.time, "time", lambda: clock["t"])

        c = Tru8APIClient(api_key="k")
        await c.submit_smart("same claim", max_tier="full", max_age_hours=0)
        clock["t"] = 1000.0 + 150.0  # the observed retry gap
        await c.submit_smart("same claim", max_tier="full", max_age_hours=0)

        first, second = _FakeClient.calls[-2:]
        assert first.headers["Idempotency-Key"] == second.headers["Idempotency-Key"]
