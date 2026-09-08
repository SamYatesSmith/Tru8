"""Real PostgreSQL races and atomicity, in a disposable isolated schema.

No model/network calls. Refuses non-local databases.
"""

import asyncio
import base64
import copy
import uuid
from datetime import timedelta

import pytest
import pytest_asyncio
from fastapi import HTTPException
from sqlalchemy import select, text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel

from app.core.config import settings
from app.models import (
    Check,
    Claim,
    Evidence,
    User,
    UsageEvent,
    ResearchOperation,
    ReportRevision,
)
from app.models.check import _utcnow_naive
from app.services import research_operations as operations
from app.services.report_revisions import capture_report, sign_snapshot, verify_snapshot


@pytest_asyncio.fixture
async def database(monkeypatch):
    url = make_url(settings.DATABASE_URL)
    if url.host not in ("localhost", "127.0.0.1"):
        pytest.skip("Research transaction tests require a local PostgreSQL database")
    schema = "test_research_" + uuid.uuid4().hex
    admin = create_async_engine(url, connect_args={"ssl": False})
    async with admin.begin() as conn:
        await conn.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine = create_async_engine(
        url, connect_args={"ssl": False, "server_settings": {"search_path": schema}}
    )
    factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    monkeypatch.setattr(operations, "async_session", factory)
    monkeypatch.setattr(settings, "MANIFEST_SIGNING_ENABLED", True)
    monkeypatch.setattr(settings, "MANIFEST_KID", "research-test")
    monkeypatch.setattr(
        settings,
        "MANIFEST_SIGNING_KEY",
        base64.b64encode(b"test-only-key" * 3).decode(),
    )
    try:
        async with engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.create_all)
        async with factory() as session:
            session.add(
                User(id="owner", email="research-test@example.invalid", credits=10)
            )
            await session.flush()
            check = Check(
                id="report",
                user_id="owner",
                input_type="text",
                input_content="claim",
                status="completed",
                executed_tier="full",
            )
            session.add(check)
            await session.flush()
            session.add(
                Claim(
                    id="claim",
                    check_id="report",
                    text="Claim",
                    position=0,
                    claim_map={
                        "elements": [
                            {
                                "element_id": "e1",
                                "description": "First",
                                "state": "unresolved",
                                "evidence_refs": [],
                            },
                            {
                                "element_id": "e2",
                                "description": "Second",
                                "state": "unresolved",
                                "evidence_refs": [],
                            },
                        ]
                    },
                )
            )
            await session.flush()
            check.manifest = sign_snapshot(await capture_report(session, check))
            await session.commit()
        yield factory
    finally:
        await engine.dispose()
        async with admin.begin() as conn:
            await conn.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        await admin.dispose()


async def admit(factory, key="request"):
    async with factory() as session:
        user = await session.get(User, "owner")
        op, created = await operations.admit_research(
            session, user, "report", "claim", "gaps", key
        )
        await session.commit()
        return op, created


async def result_rows(factory, model):
    async with factory() as session:
        return (await session.execute(select(model))).scalars().all()


@pytest.mark.asyncio
async def test_concurrent_admission_charges_once(database):
    results = await asyncio.gather(admit(database), admit(database))
    assert sum(created for _, created in results) == 1
    assert len({op.id for op, _ in results}) == 1
    assert results[0][0].element_ids == ["e1", "e2"]
    with pytest.raises(HTTPException) as conflict:
        await admit(database, "different")
    assert conflict.value.status_code == 409
    assert len(await result_rows(database, UsageEvent)) == 1


@pytest.mark.asyncio
async def test_completion_preserves_both_signed_revisions(database, monkeypatch):
    op, _ = await admit(database)
    baseline = copy.deepcopy(op.baseline)

    async def research(claim, targets, progress):
        cm = copy.deepcopy(claim["claimMap"])
        cm["elements"][0]["evidence_refs"] = [
            {"evidence_id": "new", "relationship": "supports"}
        ]
        return cm, [
            {
                "evidence_id": "new",
                "url": "https://example.invalid/new",
                "title": "New",
                "text": "Facts",
                "tier": "primary",
                "evidence_type": "data",
            }
        ]

    from app.pipeline import re_search

    monkeypatch.setattr(re_search, "research_claim", research)
    await asyncio.gather(
        operations.execute_operation(op.id), operations.execute_operation(op.id)
    )
    revisions = await result_rows(database, ReportRevision)
    assert len(revisions) == 2
    before = next(r for r in revisions if r.phase == "before")
    after = next(r for r in revisions if r.phase == "after")
    assert before.snapshot == baseline
    assert verify_snapshot(before.snapshot)["valid"]
    assert verify_snapshot(after.snapshot)["valid"]
    assert before.snapshot["manifest"] != after.snapshot["manifest"]
    assert len(await result_rows(database, Evidence)) == 1
    assert len(await result_rows(database, UsageEvent)) == 1
    completed = (await result_rows(database, ResearchOperation))[0]
    assert completed.status == "completed"
    assert completed.result_revision_id == after.id
    from app.api.v1 import verify

    monkeypatch.setattr(verify, "async_session", database)
    assert (await verify.verify_check("report", None))["valid"]
    public = await verify.verify_report_revision("report", before.id)
    assert public["valid"] and "snapshot" not in public
    tampered = copy.deepcopy(before.snapshot)
    tampered["claims"][0]["claimMap"]["elements"][0]["state"] = "supported"
    assert not verify_snapshot(tampered)["valid"]
    from app.api.v1 import checks

    async with database() as session:
        history = await checks.list_report_revisions("report", {"id": "owner"}, session)
        assert len(history["revisions"]) == 2
        with pytest.raises(HTTPException) as denied:
            await checks.get_report_revision(
                "report", before.id, {"id": "stranger"}, session
            )
        assert denied.value.status_code == 404


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", ["stage", "signing", "changed", "cancel"])
async def test_failure_rolls_back_and_refunds_exactly_once(
    database, monkeypatch, failure
):
    op, _ = await admit(database)
    from app.pipeline import re_search

    async def research(claim, targets, progress):
        if failure == "stage":
            raise RuntimeError("offline stage failure")
        if failure == "cancel":
            raise asyncio.CancelledError()
        return claim["claimMap"], [
            {
                "evidence_id": "new",
                "url": "https://example.invalid/new",
                "title": "New",
                "text": "Facts",
            }
        ]

    monkeypatch.setattr(re_search, "research_claim", research)
    if failure == "signing":
        monkeypatch.setattr(operations, "sign_snapshot", lambda _: None)
    if failure == "changed":
        async with database() as session:
            claim = await session.get(Claim, "claim")
            claim.text = "Edited while research was running"
            await session.commit()
    try:
        await operations.execute_operation(op.id)
    except asyncio.CancelledError:
        assert failure == "cancel"
    await asyncio.gather(
        operations.fail_operation(op.id, "duplicate"),
        operations.fail_operation(op.id, "duplicate"),
    )
    assert (await result_rows(database, ResearchOperation))[0].status == "error"
    assert not await result_rows(database, Evidence)
    assert not await result_rows(database, ReportRevision)
    events = await result_rows(database, UsageEvent)
    assert sorted(e.credits for e in events) == [-1, 1]
    user = (await result_rows(database, User))[0]
    assert (user.credits, user.total_credits_used) == (10, 0)
    check = (await result_rows(database, Check))[0]
    assert check.status == "completed" and check.credits_used == 1
    assert check.manifest == op.baseline["manifest"]


@pytest.mark.asyncio
async def test_expired_operation_refunded_and_cannot_commit(database):
    op, _ = await admit(database)
    async with database() as session:
        row = await session.get(ResearchOperation, op.id)
        row.deadline_at = _utcnow_naive() - timedelta(seconds=1)
        await session.commit()
    await operations.reconcile_expired()
    async with database() as session:
        with pytest.raises(RuntimeError, match="expired"):
            await operations.commit_result(session, op.id, {}, [])
    second, created = await admit(database, "second")
    assert created and second.id != op.id
    assert len(await result_rows(database, UsageEvent)) == 3


@pytest.mark.asyncio
async def test_admission_replaces_expired_work_atomically(database):
    op, _ = await admit(database)
    async with database() as session:
        row = await session.get(ResearchOperation, op.id)
        row.deadline_at = _utcnow_naive() - timedelta(seconds=1)
        await session.commit()
    second, created = await admit(database, "next")
    assert created and second.id != op.id
    rows = await result_rows(database, ResearchOperation)
    assert sorted(r.status for r in rows) == ["error", "pending"]
    assert sorted(e.credits for e in await result_rows(database, UsageEvent)) == [
        -1,
        1,
        1,
    ]


@pytest.mark.asyncio
async def test_watchdog_ends_and_refunds_running_work(database, monkeypatch):
    op, _ = await admit(database)
    async with database() as session:
        row = await session.get(ResearchOperation, op.id)
        row.deadline_at = _utcnow_naive() + timedelta(seconds=0.3)
        await session.commit()
    from app.pipeline import re_search

    monkeypatch.setattr(re_search, "research_claim", lambda *args: asyncio.sleep(20))
    await operations.execute_operation(op.id)
    assert (await result_rows(database, ResearchOperation))[0].status == "error"
    assert sorted(e.credits for e in await result_rows(database, UsageEvent)) == [-1, 1]


@pytest.mark.asyncio
async def test_migration_matches_bootstrap_and_admits(database):
    import importlib.util
    from pathlib import Path
    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    from sqlalchemy import inspect

    path = (
        Path(__file__).resolve().parents[2]
        / "alembic/versions/2026_09_08_research_operations.py"
    )
    spec = importlib.util.spec_from_file_location("research_migration", path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    async with database() as session:
        connection = await session.connection()

        def roundtrip(conn):
            def schema_shape():
                inspector = inspect(conn)
                return {
                    table: {
                        "columns": [
                            (c["name"], str(c["type"]), c["nullable"])
                            for c in inspector.get_columns(table)
                        ],
                        "unique": sorted(
                            c["name"] for c in inspector.get_unique_constraints(table)
                        ),
                        "indexes": sorted(
                            i["name"] for i in inspector.get_indexes(table)
                        ),
                    }
                    for table in ("research_operation", "report_revision")
                }

            baseline = schema_shape()
            with Operations.context(MigrationContext.configure(conn)):
                migration.downgrade()
                migration.upgrade()
            assert schema_shape() == baseline

        await connection.run_sync(roundtrip)
        await session.commit()
    _, created = await admit(database)
    assert created
