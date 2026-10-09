"""Stale sweep against a REAL async session (2026-10-09).

Why: the sweep moved to one transaction per check, rolling back a check that
fails. A rollback expires every loaded row — its primary key included, even
with expire_on_commit=False — and an async session cannot lazily refresh, so
touching the next row raised MissingGreenlet and the whole sweep returned 0.
The mocked-session tests could not see it (independent verifier reproduced it
on aiosqlite). This test runs the real ORM.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import select

from app.core.inflight import STALE_ERROR_MSG, sweep_stale_checks
from app.models.check import Check
from app.models.user import User


@compiles(JSONB, "sqlite")
def _jsonb_as_json_on_sqlite(type_, compiler, **kw):  # test-only DDL shim
    return "JSON"


@pytest.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(lambda c: User.__table__.create(c))
        await conn.run_sync(lambda c: Check.__table__.create(c))
    maker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as s:
        yield s
    await engine.dispose()


def _stale_check(check_id: str, user_id: str) -> Check:
    old = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=1)
    return Check(
        id=check_id,
        user_id=user_id,
        input_type="text",
        status="processing",
        created_at=old,
        processing_started_at=old,
    )


@pytest.mark.asyncio
async def test_a_failing_check_does_not_stop_the_next_one(session, monkeypatch):
    session.add(User(id="u-1", email="u1@example.com"))
    session.add(_stale_check("c-bad", "u-1"))  # inserted first → read first
    session.add(_stale_check("c-good", "u-1"))
    await session.commit()

    order = []

    async def _refund(sess, check_id, user_id=None):
        order.append(check_id)
        if check_id == "c-bad":
            raise RuntimeError("refund broke")
        return True

    import app.services.agent_refunds as ar_mod
    import app.services.usage_ledger as ledger_mod

    monkeypatch.setattr(ledger_mod, "refund_usage", _refund)
    monkeypatch.setattr(
        ar_mod, "refund_stranded_agent_transaction", AsyncMock(return_value=0)
    )

    swept = await sweep_stale_checks(session=session)

    assert order == ["c-bad", "c-good"]  # the failing row came first
    assert swept == 1
    rows = {c.id: c for c in (await session.execute(select(Check))).scalars().all()}
    assert rows["c-good"].status == "failed"
    assert rows["c-good"].error_message == STALE_ERROR_MSG
    assert rows["c-bad"].status == "processing"


@pytest.mark.asyncio
async def test_shutdown_guard_survives_a_failing_check(session, monkeypatch):
    from contextlib import asynccontextmanager

    import app.core.database as db_mod
    import app.services.agent_refunds as ar_mod
    import app.services.usage_ledger as ledger_mod
    from app.core.inflight import (
        SHUTDOWN_ERROR_MSG,
        fail_and_refund_inflight,
        inflight_register,
        inflight_unregister,
    )

    session.add(User(id="u-1", email="u1@example.com"))
    session.add(_stale_check("c-bad", "u-1"))
    session.add(_stale_check("c-good", "u-1"))
    await session.commit()

    @asynccontextmanager
    async def _same_session():
        yield session

    async def _refund(sess, check_id, user_id=None):
        if check_id == "c-bad":
            raise RuntimeError("refund broke")
        return True

    monkeypatch.setattr(db_mod, "async_session", _same_session)
    monkeypatch.setattr(ledger_mod, "refund_usage", _refund)
    monkeypatch.setattr(
        ar_mod, "refund_stranded_agent_transaction", AsyncMock(return_value=0)
    )
    inflight_register("c-bad")
    inflight_register("c-good")
    try:
        assert await fail_and_refund_inflight() == 1
    finally:
        inflight_unregister("c-bad")
        inflight_unregister("c-good")

    rows = {c.id: c for c in (await session.execute(select(Check))).scalars().all()}
    assert rows["c-good"].status == "failed"
    assert rows["c-good"].error_message == SHUTDOWN_ERROR_MSG
    assert rows["c-bad"].status == "processing"
