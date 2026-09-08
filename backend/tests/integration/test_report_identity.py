import copy
import json
import sys
from types import SimpleNamespace

import pytest
from integration.test_research_operations import database, admit
from app.models import Check, Claim, Evidence, ReportRevision
from app.services.report_revisions import capture_report, identify_snapshot
from app.api.v1.response_builder import build_check_response
from app.api.v1.checks import get_public_check, _build_check_pdf_bytes


@pytest.mark.asyncio
async def test_identity_matches_content_not_latest_revision(database):
    op, _ = await admit(database)
    async with database() as session:
        check = await session.get(Check, "report")
        original = await capture_report(session, check)
        session.add(
            ReportRevision(
                id="old",
                check_id="report",
                operation_id=op.id,
                phase="before",
                snapshot=original,
            )
        )
        changed = copy.deepcopy(original)
        changed["claims"][0]["text"] = "Different content"
        session.add(
            ReportRevision(
                id="new",
                check_id="report",
                operation_id=op.id,
                phase="after",
                snapshot=changed,
            )
        )
        await session.flush()
        identity = await identify_snapshot(session, original)
        assert identity["revisionId"] == "old"
        assert (await identify_snapshot(session, changed))["revisionId"] == "new"
        changed["claims"][0]["text"] = "Not retained"
        unmatched = await identify_snapshot(session, changed)
        assert unmatched["revisionId"] is None
        assert unmatched["contentHash"] != identity["contentHash"]


@pytest.mark.asyncio
async def test_owner_public_and_pdf_identify_same_read_content(database, monkeypatch):
    op, _ = await admit(database)
    async with database() as session:
        check = await session.get(Check, "report")
        check.input_content = json.dumps({"text": "Claim"})
        session.add(
            Evidence(
                id="ev",
                claim_id="claim",
                evidence_id="source",
                title="Source",
                snippet="Saved source text",
                relevance_score=0.8,
                url="https://example.invalid",
                source="example.invalid",
            )
        )
        await session.flush()
        snapshot = await capture_report(session, check)
        session.add(
            ReportRevision(
                id="retained",
                check_id="report",
                operation_id=op.id,
                phase="after",
                snapshot=snapshot,
            )
        )
        await session.flush()
        owner = await build_check_response("report", "owner", session)
        public = await get_public_check("report", detailed=True, session=session)
        assert owner["reportIdentity"] == public["reportIdentity"]
        assert owner["reportIdentity"]["revisionId"] == "retained"
        assert "operationId" not in public["reportIdentity"]
        html = []

        class Renderer:
            def __init__(self, *, string, **kwargs):
                html.append(string)

            def write_pdf(self):
                return b"%PDF-test"

        monkeypatch.setitem(sys.modules, "weasyprint", SimpleNamespace(HTML=Renderer))
        assert await _build_check_pdf_bytes(check, session) == b"%PDF-test"
        assert owner["reportIdentity"]["contentHash"] in html[0]
        assert "Retained revision: retained" in html[0]
        assert "?revision=retained" in html[0]
        # PDF presentation notes must not mutate ORM claim maps or their identity.
        assert await capture_report(session, check) == snapshot
