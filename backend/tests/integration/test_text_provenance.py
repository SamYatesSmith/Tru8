"""Actual initial-pipeline persistence and additive migration on local PostgreSQL."""

import importlib.util
from pathlib import Path

import pytest
from sqlalchemy import inspect, select
from alembic.migration import MigrationContext
from alembic.operations import Operations

from integration.test_research_operations import database
from app.models import Evidence
from app.services.text_provenance import capture_text_provenance


@pytest.mark.asyncio
async def test_initial_save_retains_exact_extraction(database):
    from app.pipeline.runner import save_check_results_async
    from app.api.v1.response_builder import _serialize_evidence

    item = {
        "evidence_id": "captured",
        "url": "https://example.invalid",
        "text": "Stored snippet",
        "_full_text": "Exact source text including late exceptions. " * 30,
    }
    capture_text_provenance(item, "exceptions")
    async with database() as session:
        await save_check_results_async(
            "report",
            {
                "claims": [
                    {
                        "text": "Claim",
                        "position": 0,
                        "claim_map": {"elements": []},
                        "evidence": [item],
                    }
                ]
            },
            session,
        )
        await session.commit()
    async with database() as session:
        row = (await session.execute(select(Evidence))).scalar_one()
        assert row.text_provenance == item["text_provenance"]
        assert (
            _serialize_evidence(row)["textProvenance"]["original_snippet"]
            == "Stored snippet"
        )


@pytest.mark.asyncio
async def test_provenance_migration_matches_bootstrap_without_backfill(database):
    path = (
        Path(__file__).resolve().parents[2]
        / "alembic/versions/2026_09_08_text_provenance.py"
    )
    spec = importlib.util.spec_from_file_location("text_migration", path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    async with database() as session:
        session.add(
            Evidence(
                claim_id="claim",
                evidence_id="legacy",
                url="https://example.invalid",
                title="Old",
                source="Source",
                snippet="Old text",
                relevance_score=1,
            )
        )
        await session.flush()
        conn = await session.connection()

        def roundtrip(connection):
            with Operations.context(MigrationContext.configure(connection)):
                migration.downgrade()
                migration.upgrade()
            column = next(
                c
                for c in inspect(connection).get_columns("evidence")
                if c["name"] == "text_provenance"
            )
            assert str(column["type"]) == "JSONB" and column["nullable"]

        await conn.run_sync(roundtrip)
        await session.commit()
    async with database() as session:
        row = (await session.execute(select(Evidence))).scalar_one()
        assert row.text_provenance is None and row.snippet == "Old text"
