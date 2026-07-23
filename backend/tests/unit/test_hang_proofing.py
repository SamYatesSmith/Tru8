"""Hang-proofing tests (2026-07-23, audit/2026-07-23_hang_proofing_design.md).

A check must always reach a terminal state — completed, or failed with an
honest message and a refund. These lock the four layers:

  W1 task-level watchdog (app/core/watchdog.py) — the ceiling lives on the
     task itself, survives client disconnects, and routes breaches through
     the existing handle_pipeline_failure (pipeline) / Redis status channel
     (re-search, whose parent check is COMPLETED and must stay so);
  W2 boot-time stale sweep (inflight.sweep_stale_checks) — heals rows
     stranded by kills (OOM/SIGKILL bypass the SIGTERM guard);
  W3 stream hygiene (progress.events) — the stream-duration bound closes the
     CONNECTION only: it never cancels the pipeline and never claims a refund
     it did not make (defect D3).
"""

import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.config import settings
from app.core.inflight import STALE_ERROR_MSG, sweep_stale_checks
from app.core.watchdog import supervise_pipeline_task, supervise_re_search_task


def _naive_now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


# ── W1: pipeline watchdog ────────────────────────────────────────────────────


class TestPipelineWatchdog:
    @pytest.mark.asyncio
    async def test_breach_fails_check_honestly(self, monkeypatch):
        monkeypatch.setattr(settings, "PIPELINE_WATCHDOG_SECONDS", 0.05)
        import app.pipeline.runner as runner_mod

        handler = AsyncMock()
        monkeypatch.setattr(runner_mod, "handle_pipeline_failure", handler)

        cancelled = {"v": False}

        async def slow_pipeline():
            try:
                await asyncio.sleep(5)
            except asyncio.CancelledError:
                cancelled["v"] = True
                raise

        task = supervise_pipeline_task(
            slow_pipeline(), check_id="c1", user_id="u1", label="test"
        )
        # The wrapper re-raises after handling so an attached SSE stream
        # reports an error instead of announcing "completed" for a failed
        # check; detached callers see it via gather(return_exceptions=True).
        (result,) = await asyncio.gather(task, return_exceptions=True)
        assert type(result).__name__ == "PipelineError"

        assert cancelled["v"], "underlying pipeline coroutine was not cancelled"
        handler.assert_awaited_once()
        args = handler.await_args.args
        assert args[0] == "c1" and args[1] == "u1"
        # 'timeout' in the message maps to the honest took-too-long copy via
        # get_user_friendly_error; handle_pipeline_failure appends the refund line.
        assert "timeout" in str(args[2]).lower()

    @pytest.mark.asyncio
    async def test_fast_pipeline_untouched(self, monkeypatch):
        monkeypatch.setattr(settings, "PIPELINE_WATCHDOG_SECONDS", 5)
        import app.pipeline.runner as runner_mod

        handler = AsyncMock()
        monkeypatch.setattr(runner_mod, "handle_pipeline_failure", handler)

        ran = {"v": False}

        async def fast_pipeline():
            ran["v"] = True

        await supervise_pipeline_task(
            fast_pipeline(), check_id="c1", user_id="u1", label="test"
        )
        assert ran["v"]
        handler.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_handler_failure_never_masks_the_breach(self, monkeypatch):
        # A failing failure-handler (db down) must not swallow the breach:
        # the wrapper still raises PipelineError (not the handler's error),
        # so an attached stream still reports honestly.
        monkeypatch.setattr(settings, "PIPELINE_WATCHDOG_SECONDS", 0.05)
        import app.pipeline.runner as runner_mod

        monkeypatch.setattr(
            runner_mod,
            "handle_pipeline_failure",
            AsyncMock(side_effect=RuntimeError("db down")),
        )

        async def slow_pipeline():
            await asyncio.sleep(5)

        task = supervise_pipeline_task(
            slow_pipeline(), check_id="c1", user_id="u1", label="test"
        )
        (result,) = await asyncio.gather(task, return_exceptions=True)
        assert type(result).__name__ == "PipelineError"


# ── W1: re-search watchdog ───────────────────────────────────────────────────


class TestReSearchWatchdog:
    @pytest.mark.asyncio
    async def test_breach_terminates_redis_status_not_check(self, monkeypatch):
        monkeypatch.setattr(settings, "RESEARCH_WATCHDOG_SECONDS", 0.05)
        import app.pipeline.re_search as rs_mod

        status = MagicMock()
        monkeypatch.setattr(rs_mod, "_update_status", status)
        # The check-failure path must NOT be touched: a re-search runs on a
        # COMPLETED check.
        import app.pipeline.runner as runner_mod

        handler = AsyncMock()
        monkeypatch.setattr(runner_mod, "handle_pipeline_failure", handler)

        async def slow_research():
            await asyncio.sleep(5)

        await supervise_re_search_task(
            slow_research(), check_id="c1", claim_id="cl1", element_id="e1"
        )

        status.assert_called_once()
        args = status.call_args.args
        assert args[:3] == ("c1", "cl1", "e1")
        assert args[3] == "error"
        handler.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_fast_research_untouched(self, monkeypatch):
        monkeypatch.setattr(settings, "RESEARCH_WATCHDOG_SECONDS", 5)
        import app.pipeline.re_search as rs_mod

        status = MagicMock()
        monkeypatch.setattr(rs_mod, "_update_status", status)

        async def fast_research():
            pass

        await supervise_re_search_task(
            fast_research(), check_id="c1", claim_id="cl1", element_id="e1"
        )
        status.assert_not_called()


# ── W2: boot-time stale sweep ────────────────────────────────────────────────


def _fake_sweep_session(rows, monkeypatch):
    """Session whose one select returns `rows`; refund mocked at the ledger."""
    session = MagicMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = rows
    session.execute = AsyncMock(return_value=result)
    session.add = MagicMock()
    session.commit = AsyncMock()

    refund = AsyncMock(return_value=True)
    import app.services.usage_ledger as ledger_mod

    monkeypatch.setattr(ledger_mod, "refund_usage", refund)
    return session, refund


def _check(status, *, started_min_ago=None, created_min_ago=10):
    now = _naive_now()
    return SimpleNamespace(
        id=f"c-{status}-{started_min_ago}",
        status=status,
        error_message=None,
        created_at=now - timedelta(minutes=created_min_ago),
        processing_started_at=(
            now - timedelta(minutes=started_min_ago)
            if started_min_ago is not None
            else None
        ),
    )


class TestStaleSweep:
    @pytest.mark.asyncio
    async def test_stale_processing_swept(self, monkeypatch):
        stale = _check("processing", started_min_ago=30)
        session, refund = _fake_sweep_session([stale], monkeypatch)

        n = await sweep_stale_checks(session=session)

        assert n == 1
        assert stale.status == "failed"
        assert stale.error_message == STALE_ERROR_MSG
        refund.assert_awaited_once()
        session.commit.assert_awaited()

    @pytest.mark.asyncio
    async def test_fresh_processing_kept(self, monkeypatch):
        # Younger than ceiling+grace — could be another instance mid-run
        # during a deploy overlap. Must never be swept.
        fresh = _check("processing", started_min_ago=1)
        session, refund = _fake_sweep_session([fresh], monkeypatch)

        n = await sweep_stale_checks(session=session)

        assert n == 0
        assert fresh.status == "processing"
        refund.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_paused_then_resumed_ages_from_processing_started(self, monkeypatch):
        # Article check created hours ago, paused at selection, phase 2 just
        # started: created_at is old but processing_started_at is fresh —
        # ageing from created_at would kill a legitimate run.
        resumed = _check("processing", started_min_ago=1, created_min_ago=600)
        session, refund = _fake_sweep_session([resumed], monkeypatch)

        assert await sweep_stale_checks(session=session) == 0
        assert resumed.status == "processing"
        refund.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_premigration_null_started_coalesces_to_created(self, monkeypatch):
        # Pre-migration stranding (e.g. check 46406547): NULL
        # processing_started_at, old created_at → swept.
        stranded = _check("processing", started_min_ago=None, created_min_ago=120)
        session, refund = _fake_sweep_session([stranded], monkeypatch)

        assert await sweep_stale_checks(session=session) == 1
        assert stranded.status == "failed"
        refund.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_stale_pending_swept_by_created_at(self, monkeypatch):
        # 'pending' rows (task never started) age from created_at even when
        # the insert default populated processing_started_at.
        pending = _check("pending", started_min_ago=1, created_min_ago=120)
        session, refund = _fake_sweep_session([pending], monkeypatch)

        assert await sweep_stale_checks(session=session) == 1
        assert pending.status == "failed"

    @pytest.mark.asyncio
    async def test_one_bad_row_never_aborts_the_sweep(self, monkeypatch):
        stale_a = _check("processing", started_min_ago=30)
        stale_b = _check("processing", started_min_ago=40)
        session, _ = _fake_sweep_session([stale_a, stale_b], monkeypatch)

        refund = AsyncMock(side_effect=[RuntimeError("row a broke"), True])
        import app.services.usage_ledger as ledger_mod

        monkeypatch.setattr(ledger_mod, "refund_usage", refund)

        assert await sweep_stale_checks(session=session) == 1
        assert stale_a.status == "processing"  # failed row left as-was
        assert stale_b.status == "failed"


# ── W3: stream-duration bound is connection-only ─────────────────────────────


class TestStreamHygiene:
    @pytest.mark.asyncio
    async def test_expiry_closes_stream_without_cancel_or_refund_claim(self):
        from app.pipeline.progress import ProgressReporter

        reporter = ProgressReporter("c-stream")

        async def never_ending():
            await asyncio.sleep(60)

        pipeline_task = asyncio.create_task(never_ending())
        try:
            events = []
            async for e in reporter.events(pipeline_task, max_duration_seconds=0):
                events.append(e)

            joined = "".join(events)
            assert "stream_timeout" in joined
            # D3 lock: the stream must never assert a refund it didn't make,
            # and must not emit a failed status on expiry.
            assert "credit has been returned" not in joined.lower()
            assert '"status": "failed"' not in joined
            # The pipeline task is NOT cancelled by the stream.
            assert not pipeline_task.cancelled()
            assert not pipeline_task.done()
        finally:
            pipeline_task.cancel()
