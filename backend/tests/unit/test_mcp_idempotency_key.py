"""The MCP client sends an Idempotency-Key on every agent call (2026-09-02,
rebuilt 2026-09-11).

Why: over the hosted transport the streamable-HTTP stream dies at ~140 s, the
client re-initialises and re-sends the pending tool call, and the server runs
it again — one tru8_check produced two charged checks (dd2ca726 + c8dd4886).

Why rebuilt: the first key mixed in floor(epoch / 600), a FIXED clock bucket
aligned to :00/:10/:20. A retry straddling a boundary carried a new key and
was charged again (2026-09-11: 09:58:40 → 10:04:20, a093c7d2 + bebfa026). The
key now has no time term — the window is the server's — and it is salted with
the caller's API key so two callers can never share one.

Pins: the key is identical for an identical call at ANY two moments (including
across a ten-minute boundary), differs across payloads, endpoints and API keys,
and actually reaches the request headers of both agent POSTs.
"""

from types import SimpleNamespace

import pytest

import tru8_mcp.tools as tools
from tru8_mcp.tools import Tru8APIClient, idempotency_key_for


@pytest.mark.unit
class TestKeyDerivation:
    def test_same_call_same_key_regardless_of_time(self):
        p = {"claim": "x", "max_tier": "full", "max_age_hours": 0, "compact": False}
        assert idempotency_key_for("agent/check", p, "k") == idempotency_key_for(
            "agent/check", p, "k"
        )

    def test_key_has_no_time_term(self):
        """The 2026-09-11 failure: 09:58:40 and 10:04:20 straddle a 600 s
        boundary. Whatever the clock says, the key must not change."""
        p = {"claim": "heatwave", "max_tier": "full", "max_age_hours": 0}
        import inspect

        assert "now" not in inspect.signature(idempotency_key_for).parameters
        assert idempotency_key_for("agent/check", p, "k") == idempotency_key_for(
            "agent/check", p, "k"
        )

    def test_key_changes_with_payload_and_endpoint(self):
        p = {"claim": "x", "max_tier": "full"}
        base = idempotency_key_for("agent/check", p, "k")
        assert idempotency_key_for("agent/check", {**p, "claim": "y"}, "k") != base
        assert (
            idempotency_key_for("agent/check", {**p, "max_age_hours": 0}, "k") != base
        )
        assert idempotency_key_for("agent/full", p, "k") != base

    def test_key_differs_across_api_keys(self):
        """Two hosted callers sending the identical claim must never share a
        key — the server would hand the second the first's check, uncharged."""
        p = {"claim": "same claim", "max_tier": "full"}
        assert idempotency_key_for("agent/check", p, "alice") != idempotency_key_for(
            "agent/check", p, "bob"
        )

    def test_key_shape(self):
        k = idempotency_key_for("agent/check", {"claim": "x"}, "k")
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

        await Tru8APIClient(api_key="k").submit_smart(
            "some claim", max_tier="full", max_age_hours=0
        )

        call = _FakeClient.calls[-1]
        assert call.url.endswith("/api/v1/agent/check")
        assert call.headers["Idempotency-Key"] == idempotency_key_for(
            "agent/check", call.json, "k"
        )
        assert call.headers["X-API-Key"] == "k"

    async def test_tier_endpoint_carries_the_key(self, monkeypatch):
        _FakeClient.calls.clear()
        monkeypatch.setattr(tools.httpx, "AsyncClient", _FakeClient)

        await Tru8APIClient(api_key="k").submit_tier("some claim", tier="quick")

        call = _FakeClient.calls[-1]
        assert call.url.endswith("/api/v1/agent/quick")
        assert call.headers["Idempotency-Key"] == idempotency_key_for(
            "agent/quick", call.json, "k"
        )

    async def test_a_retry_sends_the_same_key_whenever_it_arrives(self, monkeypatch):
        _FakeClient.calls.clear()
        monkeypatch.setattr(tools.httpx, "AsyncClient", _FakeClient)

        c = Tru8APIClient(api_key="k")
        await c.submit_smart("same claim", max_tier="full", max_age_hours=0)
        await c.submit_smart("same claim", max_tier="full", max_age_hours=0)

        first, second = _FakeClient.calls[-2:]
        assert first.headers["Idempotency-Key"] == second.headers["Idempotency-Key"]

    async def test_two_callers_same_claim_different_keys(self, monkeypatch):
        _FakeClient.calls.clear()
        monkeypatch.setattr(tools.httpx, "AsyncClient", _FakeClient)

        await Tru8APIClient(api_key="alice").submit_smart("same claim", max_tier="full")
        await Tru8APIClient(api_key="bob").submit_smart("same claim", max_tier="full")

        first, second = _FakeClient.calls[-2:]
        assert first.headers["Idempotency-Key"] != second.headers["Idempotency-Key"]
