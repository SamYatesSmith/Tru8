"""The cited-source gap note reaches the owner and the public payloads.

Real PostgreSQL rows and the real routes' builders; no model or network call.
Design: audit/2026-10-05_cited_source_lane_design.md §17 (Build B).
"""

import copy
import json

import pytest

from integration.test_research_operations import database  # noqa: F401
from app.models import Check, Claim
from app.api.v1.response_builder import build_check_response
from app.api.v1.checks import get_public_check

MISSING = [
    {
        "name": "Bloomberg",
        "cue": "a new Bloomberg analysis finds Trump made nearly 28,700 trades",
    }
]


@pytest.mark.asyncio
async def test_owner_and_public_payloads_carry_the_note(database):  # noqa: F811
    async with database() as session:
        check = await session.get(Check, "report")
        check.input_content = json.dumps({"text": "Claim"})
        claim = await session.get(Claim, "claim")
        cm = copy.deepcopy(claim.claim_map)
        cm["metadata"] = {
            "cited_sources": {
                "contract": "v1",
                "names": [{**MISSING[0], "kind": "analysis", "status": "accepted"}],
                "queries": [],
                "totals": {"follow": "off"},
                "missing": MISSING,
            }
        }
        claim.claim_map = cm
        session.add(claim)
        await session.flush()
        owner = await build_check_response("report", "owner", session)
        public = await get_public_check("report", detailed=True, session=session)
        for response in (owner, public):
            md = response["claims"][0]["claimMap"]["metadata"]
            assert md["citedSources"]["missing"] == MISSING


@pytest.mark.asyncio
async def test_strengthen_hands_research_every_claims_evidence(
    database, monkeypatch  # noqa: F811
):
    """MEDIUM-2: the gap note's re-search recompute sees the whole record, so
    a body pooled under another claim is never called absent."""
    from app.models import Evidence
    from app.pipeline import re_search
    from app.services import research_operations as operations
    from app.services.report_revisions import capture_report, sign_snapshot
    from integration.test_research_operations import admit

    async with database() as session:
        check = await session.get(Check, "report")
        session.add(Claim(id="other", check_id="report", text="Other", position=1))
        await session.flush()
        session.add(
            Evidence(
                id="ev-other",
                claim_id="other",
                evidence_id="ev-bloomberg",
                title="Bloomberg",
                snippet="Trades",
                relevance_score=0.5,
                url="https://www.bloomberg.com/graphics/x",
                source="bloomberg.com",
            )
        )
        await session.flush()
        check.manifest = sign_snapshot(await capture_report(session, check))
        await session.commit()

    op, _ = await admit(database)
    seen = {}

    async def research(claim, targets, progress):
        seen["own"] = [e["url"] for e in claim["evidence"]]
        seen["record"] = [e["url"] for e in claim["record_evidence"]]
        return claim["claimMap"], []

    monkeypatch.setattr(re_search, "research_claim", research)
    await operations.execute_operation(op.id)
    assert seen["own"] == []
    assert seen["record"] == ["https://www.bloomberg.com/graphics/x"]
