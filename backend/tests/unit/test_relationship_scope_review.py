import copy
from unittest.mock import AsyncMock

import pytest

from app.pipeline.claim_map_analyzer import ClaimMapAnalyzer
from app.services.relationship_scope_review import (
    plan_review,
    review_relationship_scope,
    MAX_PAIRS,
    RESPONSE_SCHEMA,
)


def fixture(relationship="challenges"):
    cm = {
        "claim_id": "x",
        "normalised_claim": "A reduces new diagnoses in adults.",
        "claim_type": "empirical",
        "metadata": {},
        "elements": [
            {
                "element_id": "e1",
                "description": "A reduces new diagnoses in adults.",
                "state": "disputed",
                "uncertainty": "The evidence disproves prevention.",
                "evidence_refs": [
                    {
                        "evidence_id": "ev-a",
                        "relationship": relationship,
                        "reasoning": "No progression benefit.",
                    }
                ],
            }
        ],
    }
    ev = [
        {
            "evidence_id": "ev-a",
            "title": "Trial",
            "url": "https://example.org/a",
            "tier": "primary",
            "content_basis": "snippet",
            "snippet": "The trial enrolled diagnosed adults and measured symptom progression.",
        }
    ]
    row = {
        "pair_id": "scope-0",
        "decision": "mismatch",
        "dimension": "outcome",
        "claim_scope": "new diagnoses",
        "source_scope": "progression after diagnosis",
        "block_id": "mapping-text",
        "quote": ev[0]["snippet"],
        "reasoning": "The trial measures progression after diagnosis, not incidence in initially unaffected adults.",
    }
    return cm, ev, row


@pytest.mark.asyncio
@pytest.mark.parametrize("relationship", ["supports", "challenges"])
async def test_explicit_mismatch_scopes_without_deleting_source(relationship):
    cm, ev, row = fixture(relationship)
    before = copy.deepcopy(ev)
    a = ClaimMapAnalyzer()
    a._call_llm = AsyncMock(return_value={"pairs": [row]})
    await review_relationship_scope(a, cm, ev)
    e = cm["elements"][0]
    ref = e["evidence_refs"][0]
    assert ref["relationship"] == "context" and e["state"] == "contextual"
    assert ref["reasoning"].startswith("Context after scope review:")
    record = e["basis"]["relationship_scope"]["scoped"][0]
    assert record["original_ref"]["relationship"] == relationship
    assert record["original_uncertainty"] == "The evidence disproves prevention."
    assert record["content_basis"] == "snippet" and "citations" not in ref
    assert ev == before
    await review_relationship_scope(a, cm, ev)
    assert e["basis"]["relationship_scope"]["scoped_count"] == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "fault",
    [
        "quote",
        "dimension",
        "claim_scope",
        "duplicate",
        "missing",
        "unknown",
        "compatible",
        "failure",
    ],
)
async def test_nondecisive_or_invalid_review_preserves_previous_mapping(fault):
    cm, ev, row = fixture()
    before = copy.deepcopy(cm["elements"])
    if fault in ("quote", "dimension", "claim_scope"):
        row[fault] = ""
    if fault in ("unknown", "compatible"):
        row["decision"] = fault
    if fault == "unknown":
        row["quote"] = ""
    rows = [] if fault == "missing" else [row, row] if fault == "duplicate" else [row]
    a = ClaimMapAnalyzer()
    a._call_llm = AsyncMock(return_value={"pairs": rows})
    if fault == "failure":
        a._call_llm.side_effect = RuntimeError("provider unavailable")
    await review_relationship_scope(a, cm, ev)
    assert cm["elements"] == before


@pytest.mark.asyncio
async def test_unestablished_scope_is_context_with_explicit_receipt():
    cm, ev, row = fixture()
    row["decision"] = "unknown"
    a = ClaimMapAnalyzer()
    a._call_llm = AsyncMock(return_value={"pairs": [row]})
    await review_relationship_scope(a, cm, ev)
    ref = cm["elements"][0]["evidence_refs"][0]
    assert ref["relationship"] == "context"
    assert "unestablished" in ref["reasoning"]
    assert cm["metadata"]["scope_review"]["pairs"][0]["decision"] == "unknown"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "source_name,expected",
    [
        ("", "context"),
        ("TRACE trial", "supports"),
        ("trace study", "supports"),
        ("TRACER study", "context"),
    ],
)
async def test_named_study_requires_identifier_in_supplied_material(
    source_name, expected
):
    cm, ev, row = fixture("supports")
    cm["elements"][0]["description"] = "In the TRACE trial, A reduced new diagnoses."
    ev[0]["title"] = source_name
    row["decision"] = "compatible"
    a = ClaimMapAnalyzer()
    a._call_llm = AsyncMock(return_value={"pairs": [row]})
    await review_relationship_scope(a, cm, ev)
    assert cm["elements"][0]["evidence_refs"][0]["relationship"] == expected
    if expected == "context":
        assert (
            cm["metadata"]["scope_review"]["pairs"][0]["model_decision"] == "compatible"
        )


def test_bounded_round_robin_and_no_context_promotion():
    cm, ev, _ = fixture()
    cm["elements"][0]["evidence_refs"] *= MAX_PAIRS + 2
    other = copy.deepcopy(cm["elements"][0])
    other["element_id"] = "e2"
    cm["elements"].append(other)
    pairs, total = plan_review(cm, ev)
    assert len(pairs) == MAX_PAIRS and total == 2 * (MAX_PAIRS + 2)
    assert [p["element_id"] for p in pairs[:2]] == ["e1", "e2"]
    cm, ev, _ = fixture("context")
    assert plan_review(cm, ev) == ([], 0)


@pytest.mark.asyncio
async def test_provider_schema_and_default_no_extra_review(monkeypatch):
    from app.core.config import settings

    a = ClaimMapAnalyzer()
    a.google_ai_api_key = "test-only"
    a._call_google = AsyncMock(return_value=({"pairs": []}, {}))
    await a._call_llm("review", 0, 100, "scope_review")
    assert a._call_google.call_args.kwargs["response_schema"] == RESPONSE_SCHEMA
    monkeypatch.setattr(settings, "ENABLE_PASSAGE_MAPPING", False)
    a._complete_unmapped_sources = AsyncMock()
    a._call_llm = AsyncMock()
    cm, ev, _ = fixture()
    await a._complete_unmapped_evidence(cm, ev)
    a._call_llm.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("enabled", [False, True])
async def test_recovery_also_reviews_the_merged_pool(monkeypatch, enabled):
    from app.core.config import settings
    from app.services import relationship_scope_review

    monkeypatch.setattr(settings, "ENABLE_PASSAGE_MAPPING", enabled)
    review = AsyncMock()
    monkeypatch.setattr(relationship_scope_review, "review_relationship_scope", review)
    cm, ev, _ = fixture()
    a = ClaimMapAnalyzer()
    a._call_llm = AsyncMock(return_value={"elements": []})
    await a.map_evidence_to_specific_elements(cm, ["e1"], ev, full_evidence=ev)
    assert review.await_count == int(enabled)
    if enabled:
        assert review.call_args.args[2] is ev
