"""Offline model stub, real strengthening transaction and revision persistence."""

from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select
from integration.test_research_operations import database, admit
from app.core.config import settings
from app.models import Claim, Evidence, ReportRevision
from app.services import research_operations
from app.services.passage_mapping import complete_passage_pairs, plan_pairs
from app.services.text_provenance import capture_text_provenance
from app.services.report_revisions import verify_snapshot
from app.pipeline.claim_map_analyzer import ClaimMapAnalyzer


@pytest.mark.asyncio
async def test_citations_survive_atomic_strengthening_and_revision_history(
    database, monkeypatch
):
    monkeypatch.setattr(settings, "ENABLE_PASSAGE_MAPPING", True)
    op, _ = await admit(database)
    from app.pipeline import re_search

    async def research(claim, targets, progress):
        cm = claim["claimMap"]
        cm["normalised_claim"] = claim["text"]
        evidence = {
            "evidence_id": "source",
            "url": "https://example.invalid/fixture",
            "title": "Synthetic test source",
            "tier": "primary",
            "evidence_type": "data",
            "text": "First is documented.",
            "_full_text": "First is documented. Second can fail. café 🙂",
        }
        capture_text_provenance(evidence, claim["text"], cm["elements"])
        pairs, _ = plan_pairs(cm, [evidence])
        analyzer = ClaimMapAnalyzer()
        analyzer._call_llm = AsyncMock(
            return_value={
                "pairs": [
                    {
                        "pair_id": p["pair_id"],
                        "relationship": (
                            "supports" if p["element_id"] == "e1" else "challenges"
                        ),
                        "reasoning": "Synthetic fixture interpretation",
                        "citations": [
                            {
                                "passage_id": p["passages"][0]["id"],
                                "quote": (
                                    "First is documented."
                                    if p["element_id"] == "e1"
                                    else "Second can fail."
                                ),
                            }
                        ],
                    }
                    for p in pairs
                ]
            }
        )
        await complete_passage_pairs(analyzer, cm, [evidence])
        return cm, [evidence]

    monkeypatch.setattr(re_search, "research_claim", research)
    await research_operations.execute_operation(op.id)
    async with database() as session:
        claim = await session.get(Claim, "claim")
        evidence = (await session.execute(select(Evidence))).scalar_one()
        revisions = (await session.execute(select(ReportRevision))).scalars().all()
        assert len(revisions) == 2
        assert all(verify_snapshot(r.snapshot)["valid"] for r in revisions)
        citation = claim.claim_map["elements"][1]["evidence_refs"][0]["citations"][0]
        assert citation["quote"] == "Second can fail."
        assert (
            citation["extraction_sha256"]
            == evidence.text_provenance["extraction_sha256"]
        )
        assert claim.claim_map["metadata"]["passage_review"]["assessed_pairs"] == 2
