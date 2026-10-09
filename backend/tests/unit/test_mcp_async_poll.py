"""tru8_check submits async and polls (2026-10-09).

Why: one silent POST for the whole pipeline is cut by Cloudflare after 125 s
of origin silence, losing a result the caller paid for. The client now asks
`/agent/check?async=true` and polls `/agent/result/{id}` with short requests.
Design + review: audit/2026-10-09_agent_check_async_design.md.

Also pins the review's blocker 1: a failure while polling must never be
mistaken for "old server, fall back" — that path re-submits under different
idempotency keys, i.e. a second charged run.
"""

import json

import httpx
import pytest

import tru8_mcp.tools as tools
from tru8_mcp.tools import CheckFailedError, Tru8APIClient

CHECK_ID = "5e4c404a-0000-4000-8000-000000000404"  # contains "404" on purpose


def _install(monkeypatch, handler):
    """Route every httpx.AsyncClient the tools module opens through handler,
    and make polling sleeps instant (recording them)."""
    real = httpx.AsyncClient
    calls = []

    def _recording(request):
        calls.append(request)
        return handler(request, len(calls))

    class _Client(real):
        def __init__(self, *a, **kw):
            kw["transport"] = httpx.MockTransport(_recording)
            super().__init__(*a, **kw)

    sleeps = []

    async def _sleep(s):
        sleeps.append(s)

    clock = {"t": 0.0}

    def _time():
        clock["t"] += 1.0
        return clock["t"]

    monkeypatch.setattr(tools.httpx, "AsyncClient", _Client)
    monkeypatch.setattr(tools.asyncio, "sleep", _sleep)
    monkeypatch.setattr(tools, "_now", _time)
    return calls, sleeps, clock


def _accepted(tier="full", charged=15):
    return httpx.Response(
        202,
        json={
            "checkId": CHECK_ID,
            "status": "processing",
            "tier": tier,
            "chargedPence": charged,
            "txId": "tx-1",
            "pollUrl": f"/api/v1/agent/result/{CHECK_ID}",
        },
    )


def _done():
    return httpx.Response(
        200,
        json={
            "id": CHECK_ID,
            "status": "completed",
            "claims": [],
            "_meta": {"executedTier": "full", "chargedPence": 0},
        },
    )


def _client():
    return Tru8APIClient(api_url="https://api.test", api_key="sk-test")


@pytest.mark.asyncio
async def test_full_tier_submits_async_and_polls_to_completion(monkeypatch):
    def handler(req, n):
        if req.method == "POST":
            return _accepted()
        if n == 2:
            return httpx.Response(
                200, json={"checkId": CHECK_ID, "status": "processing", "hit": False}
            )
        if n == 3:
            return httpx.Response(
                200,
                json={
                    "checkId": CHECK_ID,
                    "status": "waiting_for_selection",
                    "hit": False,
                },
            )
        return _done()

    calls, sleeps, _ = _install(monkeypatch, handler)
    out = await _client().submit_with_fallback("claim", max_tier="full")

    post = calls[0]
    assert post.url.path == "/api/v1/agent/check"
    assert post.url.params.get("async") == "true"
    assert "Idempotency-Key" in post.headers
    assert [c.url.path for c in calls[1:]] == [f"/api/v1/agent/result/{CHECK_ID}"] * 3
    # The result endpoint always reports 0; the caller paid on the submit.
    assert out["_meta"]["chargedPence"] == 15
    assert all(s >= tools.POLL_INTERVAL_S for s in sleeps)


@pytest.mark.asyncio
async def test_compact_is_carried_to_the_poll(monkeypatch):
    def handler(req, n):
        return _accepted() if req.method == "POST" else _done()

    calls, _, _ = _install(monkeypatch, handler)
    await _client().submit_with_fallback("claim", max_tier="full", compact=True)
    assert calls[1].url.params.get("compact") == "true"


@pytest.mark.asyncio
async def test_failed_check_raises_and_never_falls_back(monkeypatch):
    def handler(req, n):
        if req.method == "POST":
            return _accepted()
        return httpx.Response(
            200, json={"checkId": CHECK_ID, "status": "failed", "hit": False}
        )

    calls, _, _ = _install(monkeypatch, handler)
    with pytest.raises(CheckFailedError):
        await _client().submit_with_fallback("claim", max_tier="full")
    # Exactly one submit: no client-side escalation to /agent/quick|full.
    assert [c.method for c in calls].count("POST") == 1


@pytest.mark.asyncio
async def test_404_while_polling_is_not_taken_for_an_old_server(monkeypatch):
    def handler(req, n):
        if req.method == "POST":
            return _accepted()
        return httpx.Response(404, json={"detail": "Check not found"})

    calls, _, _ = _install(monkeypatch, handler)
    with pytest.raises(CheckFailedError):
        await _client().submit_with_fallback("claim", max_tier="full")
    assert [c.method for c in calls].count("POST") == 1


@pytest.mark.asyncio
async def test_rate_limit_and_transient_errors_back_off_and_continue(monkeypatch):
    def handler(req, n):
        if req.method == "POST":
            return _accepted()
        if n == 2:
            return httpx.Response(429, json={"error": "rate limited"})
        if n == 3:
            return httpx.Response(502, text="bad gateway")
        return _done()

    calls, sleeps, _ = _install(monkeypatch, handler)
    out = await _client().submit_with_fallback("claim", max_tier="full")
    assert out["id"] == CHECK_ID
    assert tools.RATE_LIMIT_BACKOFF_S in sleeps


@pytest.mark.asyncio
async def test_deadline_returns_a_still_running_answer_not_an_error(monkeypatch):
    def handler(req, n):
        if req.method == "POST":
            return _accepted(tier="quick", charged=7)
        return httpx.Response(
            200, json={"checkId": CHECK_ID, "status": "processing", "hit": False}
        )

    _, _, clock = _install(monkeypatch, handler)
    monkeypatch.setattr(tools, "POLL_DEADLINE_S", {"quick": 3.0, "full": 3.0})
    out = await _client().submit_with_fallback("claim", max_tier="full")
    assert out["checkId"] == CHECK_ID
    assert out["status"] == "processing"
    assert out["chargedPence"] == 7
    assert "tru8_get_result" in out["message"]


@pytest.mark.asyncio
async def test_old_server_answering_synchronously_still_works(monkeypatch):
    def handler(req, n):
        return _done()

    calls, _, _ = _install(monkeypatch, handler)
    out = await _client().submit_with_fallback("claim", max_tier="full")
    assert out["id"] == CHECK_ID
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_lookup_ceiling_does_not_ask_for_async(monkeypatch):
    def handler(req, n):
        return httpx.Response(200, json={"hit": False, "claimTextHash": "h"})

    calls, _, _ = _install(monkeypatch, handler)
    await _client().submit_with_fallback("claim", max_tier="lookup")
    assert "async" not in calls[0].url.params


@pytest.mark.asyncio
async def test_real_404_on_submit_still_falls_back(monkeypatch):
    """Backward compat kept: a server without /agent/check (404 on the
    submit itself) still gets the client-side tier escalation."""

    def handler(req, n):
        if req.url.path == "/api/v1/agent/check":
            return httpx.Response(404, json={"detail": "Not Found"})
        return httpx.Response(200, json={"hit": True, "id": "cached"})

    calls, _, _ = _install(monkeypatch, handler)
    out = await _client().submit_with_fallback("claim", max_tier="full")
    assert out["id"] == "cached"
    assert calls[1].url.path == "/api/v1/agent/lookup"


def test_hosted_mcp_answers_as_an_event_stream():
    """The outer hosted /mcp POST stays alive only because the SDK answers a
    tool call as an SSE stream with a ping every 15 s (passed through gzip
    since 2026-10-09). json_response=True would make it one silent body."""
    import main  # noqa: F401 — applies the hosted settings

    from tru8_mcp.server import mcp

    assert mcp.settings.json_response is False


@pytest.mark.asyncio
async def test_server_error_whose_text_contains_404_does_not_fall_back(monkeypatch):
    """Fallback is decided on the status code: a 502 whose body happens to
    contain "404" (a check id) must surface, not re-submit elsewhere."""

    def handler(req, n):
        return httpx.Response(502, text=f"upstream failed for check {CHECK_ID}")

    calls, _, _ = _install(monkeypatch, handler)
    with pytest.raises(tools.Tru8APIError) as e:
        await _client().submit_with_fallback("claim", max_tier="full")
    assert e.value.status_code == 502
    assert len(calls) == 1


def test_check_failed_is_not_a_runtime_error():
    """Callers (and the old-server fallback) catch RuntimeError for API
    errors; a failed check must never be swallowed into a re-submit there."""
    assert not issubclass(CheckFailedError, RuntimeError)


@pytest.mark.asyncio
async def test_non_json_poll_answer_is_retried(monkeypatch):
    def handler(req, n):
        if req.method == "POST":
            return _accepted()
        if n == 2:
            return httpx.Response(200, text="<html>edge error</html>")
        return _done()

    _, _, _ = _install(monkeypatch, handler)
    out = await _client().submit_with_fallback("claim", max_tier="full")
    assert out["id"] == CHECK_ID


@pytest.mark.asyncio
async def test_202_without_check_id_is_an_api_error(monkeypatch):
    def handler(req, n):
        return httpx.Response(202, json={"status": "processing"})

    _install(monkeypatch, handler)
    with pytest.raises(tools.Tru8APIError):
        await _client().submit_with_fallback("claim", max_tier="full")


@pytest.mark.asyncio
async def test_deadline_follows_the_accepted_tier(monkeypatch):
    seen = {}

    def handler(req, n):
        if req.method == "POST":
            return _accepted(tier="quick")
        return httpx.Response(200, json={"checkId": CHECK_ID, "status": "processing"})

    _, _, clock = _install(monkeypatch, handler)
    monkeypatch.setattr(tools, "POLL_DEADLINE_S", {"quick": 5.0, "full": 1000.0})
    out = await _client().submit_with_fallback("claim", max_tier="full")
    assert out["status"] == "processing"
    # Ended on the quick deadline (5 ticks), nowhere near the full one.
    assert clock["t"] < 50
