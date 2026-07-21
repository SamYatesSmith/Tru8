"""Deploy-shutdown guard tests (app/core/inflight.py, 2026-07-21).

A deploy SIGTERMs uvicorn and kills in-flight pipeline tasks; the guard
fails + refunds whatever is still registered at shutdown.
"""

from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core import inflight
from app.core.inflight import (
    SHUTDOWN_ERROR_MSG,
    fail_and_refund_inflight,
    inflight_count,
    inflight_register,
    inflight_unregister,
)


@pytest.fixture(autouse=True)
def _clean_registry():
    inflight._INFLIGHT.clear()
    yield
    inflight._INFLIGHT.clear()


class TestRegistry:
    def test_register_unregister(self):
        inflight_register("c1")
        inflight_register("c2")
        assert inflight_count() == 2
        inflight_unregister("c1")
        assert inflight_count() == 1

    def test_unregister_missing_is_noop(self):
        inflight_unregister("never-registered")
        assert inflight_count() == 0

    def test_register_idempotent(self):
        inflight_register("c1")
        inflight_register("c1")
        assert inflight_count() == 1


def _fake_db(checks_by_id, monkeypatch):
    """Patch async_session to serve fakes; return the refund mock."""
    session = MagicMock()

    async def execute(stmt):
        # Extract the check_id the select filtered on via param inspection —
        # simpler: pop ids in registry order using a queue.
        result = MagicMock()
        result.scalar_one_or_none = MagicMock(
            side_effect=lambda: checks_by_id.get(execute.current_id)
        )
        return result

    async def execute_wrapper(stmt):
        # The guard iterates list(_INFLIGHT); track which id is being queried
        # by matching the compiled statement string.
        compiled = str(stmt.compile(compile_kwargs={"literal_binds": True}))
        for cid in checks_by_id:
            if cid in compiled:
                execute.current_id = cid
                break
        else:
            execute.current_id = None
        return await execute(stmt)

    session.execute = execute_wrapper
    session.add = MagicMock()
    session.commit = AsyncMock()

    @asynccontextmanager
    async def fake_session():
        yield session

    import app.core.database as db_mod

    monkeypatch.setattr(db_mod, "async_session", fake_session)

    refund = AsyncMock(return_value=True)
    import app.services.usage_ledger as ledger_mod

    monkeypatch.setattr(ledger_mod, "refund_usage", refund)
    return session, refund


class TestFailAndRefund:
    @pytest.mark.asyncio
    async def test_empty_registry_is_noop(self):
        assert await fail_and_refund_inflight() == 0

    @pytest.mark.asyncio
    async def test_processing_check_failed_and_refunded(self, monkeypatch):
        check = SimpleNamespace(id="c-proc", status="processing", error_message=None)
        session, refund = _fake_db({"c-proc": check}, monkeypatch)
        inflight_register("c-proc")

        n = await fail_and_refund_inflight()

        assert n == 1
        assert check.status == "failed"
        assert check.error_message == SHUTDOWN_ERROR_MSG
        refund.assert_awaited_once()
        session.commit.assert_awaited()

    @pytest.mark.asyncio
    async def test_paused_check_left_alone(self, monkeypatch):
        # waiting_for_selection is durable — phase 2 resumes on a new
        # instance; the guard must not fail it.
        check = SimpleNamespace(
            id="c-wait", status="waiting_for_selection", error_message=None
        )
        _, refund = _fake_db({"c-wait": check}, monkeypatch)
        inflight_register("c-wait")

        n = await fail_and_refund_inflight()

        assert n == 0
        assert check.status == "waiting_for_selection"
        refund.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_missing_check_skipped(self, monkeypatch):
        _, refund = _fake_db({}, monkeypatch)
        inflight_register("c-gone")
        assert await fail_and_refund_inflight() == 0
        refund.assert_not_awaited()
