"""Idempotent replay on the agent run path (2026-09-02).

Why: charge() honoured a reused Idempotency-Key by returning the existing
transaction, but _run_agent_pipeline then created a second Check, ran the
pipeline again and re-pointed the transaction at the new check. A transport
retry of one tru8_check therefore ran — and, without the header, charged —
twice (dd2ca726 + c8dd4886, 2026-09-02).

Pins, at the wired seam: a transaction that already owns a check is returned
as-is (no new Check, no pipeline run, no re-link); a still-running original is
waited for; a failed original is a 502; the replay reports chargedPence 0.
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

import app.api.v1.agent as agent_mod


def _check(status="completed", check_id="chk-first", executed_tier="full"):
    c = MagicMock()
    c.id = check_id
    c.status = status
    c.executed_tier = executed_tier
    return c


class _Sessions:
    """async_session() factory yielding sessions whose execute() returns the
    given checks in order (the last one repeats)."""

    def __init__(self, checks):
        self.checks = list(checks)
        self.calls = 0

    def __call__(self):
        outer = self

        class _Ctx:
            async def __aenter__(self_inner):
                s = AsyncMock()
                idx = min(outer.calls, len(outer.checks) - 1)
                outer.calls += 1
                result = MagicMock()
                result.scalar_one_or_none = MagicMock(return_value=outer.checks[idx])
                s.execute = AsyncMock(return_value=result)
                return s

            async def __aexit__(self_inner, *a):
                return False

        return _Ctx()


@pytest.mark.unit
@pytest.mark.asyncio
class TestIdempotentReplayHelper:
    async def test_completed_original_is_returned_with_zero_charge(self):
        tx = SimpleNamespace(id="tx-1", check_id="chk-first")
        sessions = _Sessions([_check("completed")])
        with patch("app.core.database.async_session", sessions), patch(
            "app.api.v1.response_builder.build_agent_response",
            AsyncMock(return_value={"id": "chk-first", "_meta": {"chargedPence": 0}}),
        ) as build:
            resp = await agent_mod._idempotent_replay(
                tx=tx, tier="full", limitations=[], compact=False, max_wait_s=5
            )
        assert resp.status_code == 200
        assert resp.headers["X-Check-Id"] == "chk-first"
        assert resp.headers["X-Tru8-Idempotent-Replay"] == "1"
        kwargs = build.call_args.kwargs
        assert kwargs["check_id"] == "chk-first"
        assert kwargs["charged_pence"] == 0
        assert kwargs["executed_tier"] == "full"

    async def test_in_flight_original_is_waited_for(self):
        tx = SimpleNamespace(id="tx-1", check_id="chk-first")
        sessions = _Sessions(
            [_check("processing"), _check("processing"), _check("completed")]
        )
        with patch("app.core.database.async_session", sessions), patch(
            "app.api.v1.response_builder.build_agent_response",
            AsyncMock(return_value={"id": "chk-first"}),
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
        assert sessions.calls >= 3

    async def test_failed_original_is_a_502_not_a_new_run(self):
        tx = SimpleNamespace(id="tx-1", check_id="chk-first")
        with patch("app.core.database.async_session", _Sessions([_check("failed")])):
            with pytest.raises(HTTPException) as e:
                await agent_mod._idempotent_replay(
                    tx=tx, tier="full", limitations=[], compact=False, max_wait_s=5
                )
        assert e.value.status_code == 502

    async def test_original_still_running_past_the_budget_is_a_504(self):
        tx = SimpleNamespace(id="tx-1", check_id="chk-first")
        with patch(
            "app.core.database.async_session", _Sessions([_check("processing")])
        ):
            with pytest.raises(HTTPException) as e:
                await agent_mod._idempotent_replay(
                    tx=tx,
                    tier="full",
                    limitations=[],
                    compact=False,
                    max_wait_s=0,
                    poll_s=0.01,
                )
        assert e.value.status_code == 504


@pytest.mark.unit
@pytest.mark.asyncio
class TestRunPathShortCircuits:
    async def test_replayed_transaction_never_creates_a_check_or_runs_the_pipeline(
        self,
    ):
        """The wired seam: _run_agent_pipeline with a charge() that returns a
        transaction already owning a check must return before touching the
        session or the pipeline."""
        existing_tx = SimpleNamespace(
            id="tx-1", check_id="chk-first", status="completed"
        )
        payment = SimpleNamespace(
            provider="credit",
            token_exp=None,
            user_id="user-1",
            charge=AsyncMock(return_value=existing_tx),
        )
        session = AsyncMock()
        session.add = MagicMock()
        body = SimpleNamespace(claim="some claim", input_type=None, compact=False)

        with patch.object(
            agent_mod, "_idempotent_replay", AsyncMock(return_value="REPLAYED")
        ) as replay, patch(
            "app.pipeline.runner.run_pipeline", AsyncMock()
        ) as run_pipeline:
            out = await agent_mod._run_agent_pipeline(
                body=body,
                tier="full",
                amount_pence=15,
                claim_hash="h",
                request_hash="r",
                limitations=[],
                payment=payment,
                session=session,
                idempotency_key="mcp-abc",
            )

        assert out == "REPLAYED"
        replay.assert_awaited_once()
        assert replay.call_args.kwargs["tx"] is existing_tx
        session.add.assert_not_called()
        run_pipeline.assert_not_awaited()
