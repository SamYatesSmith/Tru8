"""Async /agent/check + replay without a silent wait (2026-10-09).

Why: `tru8_check` held one POST open for the whole pipeline, silent until the
end. Cloudflare closes an origin silent for 125 s, so a slow check lost its
result while the server finished and kept the charge. Design + review:
audit/2026-10-09_agent_check_async_design.md.

Pins:
- `/agent/check?async=true` passes async to the pipeline run (202 + poll);
  without the flag every caller keeps today's synchronous behaviour.
- An idempotent replay in async mode answers at once (202 while running);
  sync mode still waits (old clients).
- The async background task is held in `_background_tasks` (a bare
  create_task can be garbage-collected mid-run).
- `/agent/result` honours `compact`.
- A refunded/failed transaction no longer blocks a retry for ten minutes.
- A failure refunds only a transaction still pending (no double refund
  against the shutdown guard / stale sweep).
"""

from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

import app.api.v1.agent as agent_mod
from app.core.agent_auth import (
    AgentIdentity,
    AgentPaymentContext,
    get_agent_identity,
    get_agent_payment,
    idempotency_disposition,
)
from app.core.database import get_session

USER = "user-async-001"


def _app():
    test_app = FastAPI()
    test_app.include_router(agent_mod.router, prefix="/api/v1/agent")
    return test_app


def _payment_override():
    async def _override():
        ctx = AgentPaymentContext(
            provider="credit", payer_id=USER, user_id=USER, session=AsyncMock()
        )
        return ctx

    return _override


def _miss_session():
    session = AsyncMock()
    result = MagicMock()
    result.first.return_value = None
    session.execute = AsyncMock(return_value=result)
    session.get = AsyncMock(return_value=None)
    return session


# ── /agent/check passes async through ─────────────────────────────────────


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.parametrize("query,expected", [("?async=true", True), ("", False)])
async def test_smart_check_forwards_async_flag_to_pipeline(query, expected):
    app = _app()
    app.dependency_overrides[get_agent_payment] = _payment_override()
    app.dependency_overrides[get_session] = _miss_session
    run = AsyncMock(return_value=agent_mod.JSONResponse({"ok": 1}, status_code=202))
    with patch.object(agent_mod, "_run_agent_pipeline", run), patch.object(
        agent_mod.limiter, "enabled", False
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://t"
        ) as c:
            await c.post(
                f"/api/v1/agent/check{query}",
                json={"claim": "x", "max_tier": "full"},
            )
    assert run.await_args.kwargs["async_mode"] is expected


# ── Replay: async answers at once, sync waits ─────────────────────────────


class _Sessions:
    def __init__(self, checks):
        self.checks, self.calls = list(checks), 0

    def __call__(self):
        outer = self

        class _Ctx:
            async def __aenter__(self_inner):
                s = AsyncMock()
                c = outer.checks[min(outer.calls, len(outer.checks) - 1)]
                outer.calls += 1
                r = MagicMock()
                r.scalar_one_or_none = MagicMock(return_value=c)
                s.execute = AsyncMock(return_value=r)
                return s

            async def __aexit__(self_inner, *a):
                return False

        return _Ctx()


def _check(status):
    return SimpleNamespace(id="chk-1", status=status, executed_tier="full")


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.parametrize("status", ["processing", "waiting_for_selection"])
async def test_async_replay_of_running_check_is_an_immediate_202(status):
    tx = SimpleNamespace(id="tx-1", check_id="chk-1")
    sessions = _Sessions([_check(status)])
    with patch("app.core.database.async_session", sessions), patch.object(
        agent_mod.asyncio, "sleep", AsyncMock()
    ) as sleep:
        resp = await agent_mod._idempotent_replay(
            tx=tx,
            tier="full",
            limitations=[],
            compact=False,
            max_wait_s=180,
            wait=False,
        )
    assert resp.status_code == 202
    sleep.assert_not_awaited()
    import json

    body = json.loads(resp.body)
    assert body["checkId"] == "chk-1"
    assert body["chargedPence"] == 0
    assert body["pollUrl"] == "/api/v1/agent/result/chk-1"
    assert resp.headers["X-Tru8-Idempotent-Replay"] == "1"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_sync_replay_still_waits_by_default():
    tx = SimpleNamespace(id="tx-1", check_id="chk-1")
    sessions = _Sessions([_check("processing"), _check("completed")])
    with patch("app.core.database.async_session", sessions), patch(
        "app.api.v1.response_builder.build_agent_response",
        AsyncMock(return_value={"id": "chk-1"}),
    ):
        resp = await agent_mod._idempotent_replay(
            tx=tx,
            tier="full",
            limitations=[],
            compact=False,
            max_wait_s=5,
            poll_s=0.01,
        )
    assert resp.status_code == 200
    # two polls (processing, completed) + one session to build the response
    assert sessions.calls == 3


@pytest.mark.unit
@pytest.mark.asyncio
async def test_replay_for_key_passes_wait_false_in_async_mode():
    from app.core.agent_auth import compute_request_hash

    tx = SimpleNamespace(
        id="tx-1",
        check_id="chk-1",
        tier="full",
        payer_id=USER,
        status="pending",
        created_at=datetime.utcnow(),
        request_hash=compute_request_hash("full", "h", False),
    )
    replay = AsyncMock(return_value="R")
    with patch.object(agent_mod, "_idempotent_replay", replay), patch(
        "app.core.agent_auth.find_idempotent_transaction",
        AsyncMock(return_value=tx),
    ):
        await agent_mod._replay_for_key(
            session=AsyncMock(),
            payment=SimpleNamespace(payer_id=USER, user_id=USER),
            idempotency_key="k",
            claim_hash="h",
            compact=False,
            async_mode=True,
        )
    assert replay.await_args.kwargs["wait"] is False


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_path_replay_passes_wait_false_in_async_mode():
    existing = SimpleNamespace(id="tx-1", check_id="chk-1", status="pending")
    payment = SimpleNamespace(
        provider="credit",
        token_exp=None,
        user_id=USER,
        charge=AsyncMock(return_value=existing),
    )
    replay = AsyncMock(return_value="R")
    with patch.object(agent_mod, "_idempotent_replay", replay):
        await agent_mod._run_agent_pipeline(
            body=SimpleNamespace(claim="c", input_type=None, compact=False),
            tier="full",
            amount_pence=15,
            claim_hash="h",
            request_hash="r",
            limitations=[],
            payment=payment,
            session=AsyncMock(),
            idempotency_key="k",
            async_mode=True,
        )
    assert replay.await_args.kwargs["wait"] is False


# ── The async task is held ────────────────────────────────────────────────


@pytest.mark.unit
@pytest.mark.asyncio
async def test_async_background_task_is_held_in_background_tasks():
    fresh = SimpleNamespace(id="tx-new", check_id=None, status="pending")
    payment = SimpleNamespace(
        provider="credit",
        token_exp=None,
        user_id=USER,
        payer_id=USER,
        charge=AsyncMock(return_value=fresh),
    )
    session = AsyncMock()
    session.add = MagicMock()
    task = MagicMock()
    with patch.object(agent_mod, "_run_pipeline_background", MagicMock()), patch.object(
        agent_mod.asyncio, "create_task", MagicMock(return_value=task)
    ):
        agent_mod._background_tasks.clear()
        resp = await agent_mod._run_agent_pipeline(
            body=SimpleNamespace(claim="c", input_type=None, compact=False),
            tier="full",
            amount_pence=15,
            claim_hash="h",
            request_hash="r",
            limitations=[],
            payment=payment,
            session=session,
            idempotency_key=None,
            async_mode=True,
        )
    assert resp.status_code == 202
    assert task in agent_mod._background_tasks
    task.add_done_callback.assert_called_once_with(agent_mod._background_tasks.discard)
    agent_mod._background_tasks.clear()


# ── /agent/result honours compact ─────────────────────────────────────────


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.parametrize("query,expected", [("?compact=true", True), ("", False)])
async def test_result_endpoint_honours_compact(query, expected):
    app = _app()
    check = SimpleNamespace(
        id="chk-1", user_id=USER, status="completed", executed_tier="full"
    )
    session = AsyncMock()
    r = MagicMock()
    r.scalar_one_or_none.return_value = check
    session.execute = AsyncMock(return_value=r)
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[get_agent_identity] = lambda: AgentIdentity(
        provider="credit", payer_id=USER, user_id=USER
    )
    build = AsyncMock(return_value={"id": "chk-1"})
    with patch("app.api.v1.response_builder.build_agent_response", build), patch.object(
        agent_mod.limiter, "enabled", False
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://t"
        ) as c:
            resp = await c.get(f"/api/v1/agent/result/chk-1{query}")
    assert resp.status_code == 200
    assert build.await_args.kwargs["compact"] is expected


# ── A failed/refunded transaction does not block a retry ──────────────────


@pytest.mark.unit
@pytest.mark.parametrize("status", ["refunded", "failed"])
def test_refunded_or_failed_transaction_is_expired_at_once(status):
    tx = SimpleNamespace(
        payer_id=USER,
        request_hash="r",
        status=status,
        created_at=datetime.utcnow(),
    )
    assert idempotency_disposition(tx, payer_id=USER, request_hash="r") == "expired"


@pytest.mark.unit
@pytest.mark.parametrize("status", ["completed", "unsettled"])
def test_completed_transaction_inside_window_still_replays(status):
    tx = SimpleNamespace(
        payer_id=USER, request_hash="r", status=status, created_at=datetime.utcnow()
    )
    assert idempotency_disposition(tx, payer_id=USER, request_hash="r") == "replay"


# ── Refund only while pending ─────────────────────────────────────────────


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.parametrize("prior,refunds", [("pending", 1), ("refunded", 0)])
async def test_background_failure_refunds_only_a_pending_transaction(prior, refunds):
    tx = SimpleNamespace(id="tx-1", status=prior)
    session = AsyncMock()
    r = MagicMock()
    r.scalar_one.return_value = tx
    session.execute = AsyncMock(return_value=r)

    class _Ctx:
        async def __aenter__(self):
            return session

        async def __aexit__(self, *a):
            return False

    refund = AsyncMock()
    with patch("app.core.database.async_session", lambda: _Ctx()), patch(
        "app.services.payments.credit_provider.refund_credits", refund
    ), patch(
        "app.pipeline.runner.run_pipeline", AsyncMock(side_effect=RuntimeError("boom"))
    ), patch(
        "app.pipeline.runner.handle_pipeline_failure", AsyncMock()
    ), patch.object(
        agent_mod, "_fire_agent_webhook_failed", MagicMock()
    ), patch.object(
        agent_mod, "inflight_register", MagicMock()
    ), patch.object(
        agent_mod, "inflight_unregister", MagicMock()
    ), patch(
        "app.pipeline.progress.ProgressReporter", MagicMock()
    ):
        await agent_mod._run_pipeline_background(
            check_id="chk-1",
            user_id=USER,
            input_data={},
            config=SimpleNamespace(max_wall_time_seconds=5),
            tier="full",
            tx_id="tx-1",
            provider="credit",
            amount_pence=15,
        )
    assert refund.await_count == refunds
    # The read that decides the refund takes a row lock.
    stmt = session.execute.await_args.args[0]
    assert stmt._for_update_arg is not None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_background_failure_refunds_an_unsettled_credit_transaction():
    """The stale-pending sweeper marks a long-running credit tx `unsettled`
    after ten minutes without refunding it; the run's own failure branch must
    still pay it back (verifier, 2026-10-09)."""
    await test_background_failure_refunds_only_a_pending_transaction("unsettled", 1)


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "prior,refunds",
    [
        ("pending", 1),
        ("unsettled", 1),
        ("completed", 1),
        ("refunded", 0),
        ("failed", 0),
    ],
)
async def test_sync_refund_locks_and_refunds_only_unsettled_money(prior, refunds):
    """The synchronous path refunds under the same rule as the async one:
    lock the transaction first (order tx → balance, as everywhere), and pay
    back only money not already returned by the guard or the sweep."""
    tx = SimpleNamespace(id="tx-1", status=prior)
    session = AsyncMock()
    payment = SimpleNamespace(provider="credit", user_id=USER)
    refund = AsyncMock()
    with patch("app.services.payments.credit_provider.refund_credits", refund):
        await agent_mod._refund_and_fail_tx(tx, payment, 15, session)
    session.refresh.assert_awaited_once_with(tx, with_for_update=True)
    assert refund.await_count == refunds
    session.commit.assert_awaited()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_sync_refund_never_masks_the_callers_error():
    """A refund that itself fails is logged and rolled back; the caller still
    raises its own HTTP error, marks the check failed and fires the webhook."""
    tx = SimpleNamespace(id="tx-1", status="pending")
    session = AsyncMock()
    session.refresh = AsyncMock(side_effect=RuntimeError("session broken"))
    payment = SimpleNamespace(provider="credit", user_id=USER)
    await agent_mod._refund_and_fail_tx(tx, payment, 15, session)  # no raise
    session.rollback.assert_awaited_once()
