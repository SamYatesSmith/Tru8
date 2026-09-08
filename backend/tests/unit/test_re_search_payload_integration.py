"""Exercise the research orchestrator's mapping and persistence boundary offline."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.models import Claim, Evidence
from app.pipeline import re_search


@pytest.mark.asyncio
@pytest.mark.parametrize("distilled", [False, True])
async def test_research_retains_existing_primary_metadata_and_persists_mapped_ids(
    monkeypatch,
    distilled,
):
    claim = Claim(
        id="claim",
        check_id="check",
        text="Claim",
        position=0,
        claim_map={
            "elements": [
                {"element_id": "e1", "description": "Question"},
                {"element_id": "e2", "description": "Second"},
            ]
        },
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
    monkeypatch.setattr(re_search.settings, "ENABLE_EVIDENCE_DISTILLATION", distilled)
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
                            "evidence_id": "old",
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

    async def distil(text, items):
        items[0].update(text="Selected facts", snippet="Stale snippet", _distilled=True)
        return items

    monkeypatch.setitem(
        sys.modules,
        "app.pipeline.evidence_distiller",
        SimpleNamespace(
            EvidenceDistiller=lambda: SimpleNamespace(distil_evidence_for_claim=distil)
        ),
    )

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
    updated, candidates = await re_search.research_claim(
        {
            "text": claim.text,
            "claimMap": claim.claim_map,
            "evidence": [old.model_dump()],
        },
        ["e1", "e2"],
        AsyncMock(),
    )
    analyzer.map_evidence_to_elements.assert_awaited_once()
    retriever.retrieve_evidence_for_claims.assert_awaited_once()
    assert len(planner.plan_queries_batch.call_args.args[0][0]["elements"]) == 2
    assert candidates[0]["evidence_id"] != "old"
    assert captured[0]["tier"] == "primary"
    assert captured[0]["date_basis"] == "api_adapter"
    from app.services.evidence_payload import evidence_from_mapping

    saved = evidence_from_mapping(claim.id, candidates[0])
    assert saved.evidence_id == captured[1]["evidence_id"]
    assert saved.content_basis == "full"
    if distilled:
        assert saved.snippet == captured[1]["snippet"] == "Selected facts"
    assert len(updated["elements"][0]["evidence_refs"]) == 2
