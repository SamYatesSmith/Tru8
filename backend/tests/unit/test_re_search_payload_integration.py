"""Exercise the research orchestrator's mapping and persistence boundary offline."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models import Claim, Evidence
from app.pipeline import re_search


@pytest.mark.asyncio
async def test_research_retains_existing_primary_metadata_and_persists_mapped_ids(
    monkeypatch,
):
    claim = Claim(
        id="claim",
        check_id="check",
        text="Claim",
        position=0,
        claim_map={"elements": [{"element_id": "e1", "description": "Question"}]},
    )
    old = Evidence(
        claim_id="claim",
        evidence_id="old",
        source="Official",
        url="https://old",
        title="Old",
        snippet="Original",
        relevance_score=1,
        tier="primary",
        evidence_type="data",
        content_basis="api",
        date_basis="api_adapter",
    )
    session = AsyncMock()
    session.add = MagicMock()
    claim_result, evidence_result = MagicMock(), MagicMock()
    claim_result.scalar_one_or_none.return_value = claim
    evidence_result.scalars.return_value.all.return_value = [old]
    session.execute.side_effect = [claim_result, evidence_result]
    context = MagicMock()
    context.__aenter__ = AsyncMock(return_value=session)
    context.__aexit__ = AsyncMock(return_value=False)
    monkeypatch.setattr(re_search, "async_session", lambda: context)
    monkeypatch.setattr(re_search, "_update_status", MagicMock())
    planner = SimpleNamespace(
        plan_queries_batch=AsyncMock(return_value=[{"queries": ["query"]}])
    )
    retriever = SimpleNamespace(
        retrieve_evidence_for_claims=AsyncMock(
            return_value={
                "evidence_by_claim": {
                    "0": [
                        {
                            "url": "https://new",
                            "title": "New",
                            "text": "New facts",
                            "tier": "reporting",
                            "content_basis": "full",
                        }
                    ]
                }
            }
        )
    )
    classifier = SimpleNamespace(
        classify_batch=AsyncMock(side_effect=lambda items: items)
    )
    captured = []

    async def map_evidence(cm, evidence):
        captured.extend(evidence)
        cm["elements"][0]["evidence_refs"] = [
            {"evidence_id": item["evidence_id"], "relationship": "supports"}
            for item in evidence
        ]
        return cm

    analyzer = SimpleNamespace(
        map_evidence_to_elements=AsyncMock(side_effect=map_evidence)
    )
    # Only external stages are replaced; actual payload helpers and ORM rows run.
    import sys

    monkeypatch.setitem(
        sys.modules,
        "app.utils.query_planner",
        SimpleNamespace(get_query_planner=lambda: planner),
    )
    monkeypatch.setitem(
        sys.modules,
        "app.pipeline.retrieve",
        SimpleNamespace(EvidenceRetriever=lambda: retriever),
    )
    monkeypatch.setitem(
        sys.modules,
        "app.pipeline.evidence_classifier",
        SimpleNamespace(EvidenceClassifier=lambda: classifier),
    )
    monkeypatch.setitem(
        sys.modules,
        "app.pipeline.claim_map_analyzer",
        SimpleNamespace(ClaimMapAnalyzer=lambda: analyzer),
    )
    await re_search.run_element_re_search("check", "claim", "e1")
    session.commit.assert_awaited_once()
    assert captured[0]["tier"] == "primary"
    assert captured[0]["date_basis"] == "api_adapter"
    saved = session.add.call_args.args[0]
    assert saved.evidence_id == captured[1]["evidence_id"]
    assert saved.content_basis == "full"
    assert len(claim.claim_map["elements"][0]["evidence_refs"]) == 2
