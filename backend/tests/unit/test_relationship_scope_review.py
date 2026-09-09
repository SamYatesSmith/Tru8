import copy
import json
from pathlib import Path
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
async def test_actual_pdf_fragment_result_unknown_retains_original_and_source():
    frozen = json.loads(
        (
            Path(__file__).parents[1]
            / "evaluation/passage_quality/result_fragment_failure.json"
        ).read_text()
    )
    cm, _, row = fixture("supports")
    cm["elements"][0]["description"] = frozen["claim"]
    ev = [frozen["evidence"]]
    cm["elements"][0]["evidence_refs"][0]["evidence_id"] = ev[0]["evidence_id"]
    before = copy.deepcopy(ev)
    row.update(
        decision="unknown",
        dimension="result",
        claim_scope="20% relative MACE reduction",
        source_scope="methods/background fragment",
        quote=ev[0]["text"],
        reasoning="The supplied fragment describes randomisation but does not report the asserted effect size.",
    )
    a = ClaimMapAnalyzer()
    a._call_llm = AsyncMock(return_value={"pairs": [row]})
    await review_relationship_scope(a, cm, ev)
    assert cm["elements"][0]["evidence_refs"][0]["relationship"] == "context"
    receipt = cm["elements"][0]["basis"]["relationship_scope"]["scoped"][0]
    assert receipt["original_ref"]["relationship"] == "supports"
    assert receipt["dimension"] == "result" and ev == before


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "quote", ["", "A fabricated result not present in the supplied text."]
)
async def test_compatible_without_valid_result_excerpt_is_unassessed(quote):
    cm, ev, row = fixture("supports")
    row.update(decision="compatible", quote=quote)
    a = ClaimMapAnalyzer()
    a._call_llm = AsyncMock(return_value={"pairs": [row]})
    await review_relationship_scope(a, cm, ev)
    assert cm["metadata"]["scope_review"]["status"] == "needs_review"
    assert cm["metadata"]["scope_review"]["assessed_pairs"] == 0


@pytest.mark.asyncio
async def test_compatible_result_retains_auditable_excerpt():
    cm, ev, row = fixture("supports")
    ev[0][
        "snippet"
    ] = "The adult prevention trial reported fewer new diagnoses with A than placebo."
    row.update(
        decision="compatible",
        dimension="result",
        quote=ev[0]["snippet"],
        source_scope="fewer new diagnoses",
        reasoning="Reports the preventive result in adults.",
    )
    a = ClaimMapAnalyzer()
    a._call_llm = AsyncMock(return_value={"pairs": [row]})
    await review_relationship_scope(a, cm, ev)
    record = cm["metadata"]["scope_review"]["pairs"][0]
    assert record["status"] == "compatible" and record["quote"] == row["quote"]
    assert (
        record["input_sha256"]
        and cm["elements"][0]["evidence_refs"][0]["relationship"] == "supports"
    )


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
@pytest.mark.parametrize(
    "excerpt_id,expected", [("line-1", "context"), ("invented", "supports")]
)
async def test_selected_excerpt_is_resolved_from_exact_block(excerpt_id, expected):
    cm, ev, row = fixture("supports")
    ev[0][
        "snippet"
    ] = "Trial background fragment\nPatients were randomly assigned, with the use of\na centralized system."
    row.update(
        decision="unknown",
        dimension="result",
        excerpt_id=excerpt_id,
        quote="Patients were randomly assigned, with the use of a centralized system.",
    )
    a = ClaimMapAnalyzer()
    a._call_llm = AsyncMock(return_value={"pairs": [row]})
    await review_relationship_scope(a, cm, ev)
    assert cm["elements"][0]["evidence_refs"][0]["relationship"] == expected
    if expected == "context":
        record = cm["metadata"]["scope_review"]["pairs"][0]
        assert record["quote"] == "Patients were randomly assigned, with the use of"
        assert record["quote_basis"] == "selected_exact_excerpt"
        assert record["quote"] in ev[0]["snippet"]


@pytest.mark.asyncio
async def test_compatible_cannot_substitute_an_excerpt_for_invalid_result_quote():
    cm, ev, row = fixture("supports")
    row.update(
        decision="compatible", excerpt_id="line-0", quote="Invented full result."
    )
    a = ClaimMapAnalyzer()
    a._call_llm = AsyncMock(return_value={"pairs": [row]})
    await review_relationship_scope(a, cm, ev)
    assert cm["metadata"]["scope_review"]["assessed_pairs"] == 0
    assert cm["metadata"]["scope_review"]["status"] == "needs_review"


def test_excerpt_options_never_truncate_a_long_line():
    cm, ev, _ = fixture()
    ev[0]["snippet"] = "Background " * 70 + "actual outcome at the end."
    pairs, _ = plan_review(cm, ev)
    assert pairs[0]["blocks"][0]["excerpts"] == []
    assert pairs[0]["blocks"][0]["text"] == ev[0]["snippet"]


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


@pytest.mark.asyncio
async def test_frozen_select_pair_quantitative_support_becomes_context():
    """The 2026-09-09 integrated failure: two SELECT sources labelled support
    for 'reduced MACE by 20%' on text that says only 'reduced MACE' or gives
    37.8% for a different endpoint. A model 'compatible' is overridden to
    unknown/result; sources and the model's decision are kept."""
    frozen = json.loads(
        (
            Path(__file__).parents[1]
            / "evaluation/passage_quality/qualitative_effect_failures.json"
        ).read_text(encoding="utf-8")
    )
    cm, _, row = fixture("supports")
    cm["elements"][0]["description"] = frozen["claim"]
    ev = copy.deepcopy(frozen["evidence"])
    cm["elements"][0]["evidence_refs"] = [
        {
            "evidence_id": e["evidence_id"],
            "relationship": "supports",
            "reasoning": "prior",
        }
        for e in ev
    ]
    before = copy.deepcopy(ev)
    quotes = {
        "ev-e034ece5a149": "- Semaglutide reduced MACE incidence in the SELECT trial.",
        "ev-49522d797c58": "- The SELECT trial previously reported that semaglutide reduced major adverse cardiovascular events compared with placebo over a mean follow-up of 39.8 months.",
    }
    pairs, _ = plan_review(cm, ev)
    rows = [
        dict(
            row,
            pair_id=p["pair_id"],
            decision="compatible",
            dimension="result",
            block_id="mapping-text",
            quote=quotes[p["evidence_id"]],
            claim_scope="20% relative MACE reduction",
            source_scope="MACE reduced",
            reasoning="Reports that MACE was reduced in SELECT.",
        )
        for p in pairs
    ]
    a = ClaimMapAnalyzer()
    a._call_llm = AsyncMock(return_value={"pairs": rows})
    await review_relationship_scope(a, cm, ev)
    refs = {
        r["evidence_id"]: r["relationship"] for r in cm["elements"][0]["evidence_refs"]
    }
    assert refs == {"ev-e034ece5a149": "context", "ev-49522d797c58": "context"}
    for record in cm["metadata"]["scope_review"]["pairs"]:
        assert record["decision_basis"] == "quantitative_result_not_quoted"
        assert record["model_decision"] == "compatible"
        assert record["status"] == "scoped" and record["dimension"] == "result"
    assert ev == before
    assert cm["metadata"]["scope_review"]["status"] == "complete"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "description,quote,expected",
    [
        # equivalent measures establish the figure
        (
            "N reduced admissions by 30% relative to placebo.",
            "The FIELD trial reported a hospital admission risk ratio of 0.70 for N versus placebo.",
            "supports",
        ),
        (
            "N reduced admissions by 30% relative to placebo.",
            "The FIELD trial reported a 30 percent relative reduction in admissions.",
            "supports",
        ),
        (
            "N cut admissions with a hazard ratio of 0.80.",
            "Admissions fell by 20% with N in the FIELD trial.",
            "supports",
        ),
        # a different figure for a different endpoint does not
        (
            "N reduced admissions by 30% relative to placebo.",
            "N lowered a biomarker by 37.8% at 104 weeks in the FIELD trial.",
            "context",
        ),
        # a qualitative result does not
        (
            "N reduced admissions by 30% relative to placebo.",
            "N reduced admissions in the FIELD trial.",
            "context",
        ),
        # an element with no figure is untouched by this guard
        (
            "N reduced admissions relative to placebo.",
            "N reduced admissions in the FIELD trial.",
            "supports",
        ),
    ],
)
async def test_quantitative_support_needs_the_stated_figure_in_the_quote(
    description, quote, expected
):
    cm, ev, row = fixture("supports")
    cm["elements"][0]["description"] = description
    ev[0]["snippet"] = quote
    row.update(
        decision="compatible",
        dimension="result",
        quote=quote,
        source_scope="reported result",
        reasoning="Reports the result.",
    )
    a = ClaimMapAnalyzer()
    a._call_llm = AsyncMock(return_value={"pairs": [row]})
    await review_relationship_scope(a, cm, ev)
    assert cm["elements"][0]["evidence_refs"][0]["relationship"] == expected


@pytest.mark.asyncio
async def test_quantitative_guard_leaves_challenges_alone():
    """A null-result challenge needs no figure. Only a quantitative SUPPORT is
    held to the stated figure."""
    cm, ev, row = fixture("challenges")
    cm["elements"][0][
        "description"
    ] = "N reduced admissions by 30% relative to placebo."
    ev[0][
        "snippet"
    ] = "The FIELD trial found identical admission rates with N and placebo."
    row.update(
        decision="compatible",
        dimension="result",
        quote=ev[0]["snippet"],
        source_scope="null result",
        reasoning="Equal rates on the claimed endpoint.",
    )
    a = ClaimMapAnalyzer()
    a._call_llm = AsyncMock(return_value={"pairs": [row]})
    await review_relationship_scope(a, cm, ev)
    assert cm["elements"][0]["evidence_refs"][0]["relationship"] == "challenges"
    assert cm["metadata"]["scope_review"]["pairs"][0]["status"] == "compatible"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "description,quote",
    [
        (
            "In the LANE trial, intervention Q reduced hospital admissions in adults compared with placebo.",
            "The LANE randomized placebo-controlled trial found identical hospital admission rates in adults receiving Q and placebo, excluding a meaningful reduction.",
        ),
        (
            "Intervention Q reduces deaths in adults compared with placebo.",
            "A randomized adult trial found identical death rates with Q and placebo.",
        ),
    ],
)
async def test_contrary_result_mismatch_keeps_the_challenge(description, quote):
    """2026-09-09 broader controls, 3 of 8 null-result challenges: the model
    returned mismatch/result ("claim says reduced, source says identical") and
    the review demoted the challenge to context. A contrary result on the
    result dimension IS the challenge; the model's decision is kept in the
    receipt and the reference is left as challenges."""
    cm, ev, row = fixture("challenges")
    cm["elements"][0]["description"] = description
    ev[0]["snippet"] = quote
    row.update(
        decision="mismatch",
        dimension="result",
        quote=quote,
        claim_scope="reduced admissions",
        source_scope="identical rates",
        reasoning="The source reports identical rates, conflicting with the claimed reduction.",
    )
    a = ClaimMapAnalyzer()
    a._call_llm = AsyncMock(return_value={"pairs": [row]})
    await review_relationship_scope(a, cm, ev)
    assert cm["elements"][0]["evidence_refs"][0]["relationship"] == "challenges"
    record = cm["metadata"]["scope_review"]["pairs"][0]
    assert record["status"] == "compatible"
    assert record["decision_basis"] == "contrary_result_is_the_challenge"
    assert record["model_decision"] == "mismatch"
    assert "relationship_scope" not in cm["elements"][0].get("basis", {})


@pytest.mark.asyncio
@pytest.mark.parametrize("dimension", ["population", "outcome", "study_identity"])
async def test_challenge_mismatch_on_other_dimensions_still_scopes(dimension):
    """Only the result dimension is exempt: a challenge from the wrong
    population, endpoint or study is still scoped to context."""
    cm, ev, row = fixture("challenges")
    row.update(decision="mismatch", dimension=dimension)
    a = ClaimMapAnalyzer()
    a._call_llm = AsyncMock(return_value={"pairs": [row]})
    await review_relationship_scope(a, cm, ev)
    assert cm["elements"][0]["evidence_refs"][0]["relationship"] == "context"


@pytest.mark.asyncio
async def test_support_mismatch_on_result_is_still_scoped_never_flipped():
    """A support whose quoted result contradicts the element becomes context;
    the review never flips a relationship."""
    cm, ev, row = fixture("supports")
    ev[0][
        "snippet"
    ] = "The trial found identical rates of new diagnoses with A and placebo."
    row.update(decision="mismatch", dimension="result", quote=ev[0]["snippet"])
    a = ClaimMapAnalyzer()
    a._call_llm = AsyncMock(return_value={"pairs": [row]})
    await review_relationship_scope(a, cm, ev)
    assert cm["elements"][0]["evidence_refs"][0]["relationship"] == "context"


def _many_pairs(n):
    """One element with n distinct directional references."""
    cm, ev, row = fixture("supports")
    cm["elements"][0]["evidence_refs"] = [
        {"evidence_id": f"ev-{i}", "relationship": "supports", "reasoning": "prior"}
        for i in range(n)
    ]
    ev = [
        dict(ev[0], evidence_id=f"ev-{i}", url=f"https://example.org/{i}")
        for i in range(n)
    ]
    return cm, ev, row


@pytest.mark.asyncio
async def test_review_splits_into_bounded_concurrent_calls():
    """Eight pairs -> two calls of at most CALL_PAIRS each; every returned
    decision is applied; the receipt lists both calls."""
    from app.services.relationship_scope_review import CALL_PAIRS

    cm, ev, row = _many_pairs(8)
    seen = []

    async def call(prompt, temperature, max_tokens, label):
        chunk = json.loads(prompt.split("Pairs:\n", 1)[1])
        seen.append(len(chunk))
        return {
            "pairs": [
                dict(row, pair_id=p["pair_id"], decision="unknown") for p in chunk
            ]
        }

    a = ClaimMapAnalyzer()
    a._call_llm = call
    await review_relationship_scope(a, cm, ev)
    assert sorted(seen) == [2, 6] and max(seen) <= CALL_PAIRS
    receipt = cm["metadata"]["scope_review"]
    assert [c["status"] for c in receipt["calls"]] == ["ok", "ok"]
    assert receipt["assessed_pairs"] == 8 and receipt["uninspected_pairs"] == 0
    assert all(
        r["relationship"] == "context" for r in cm["elements"][0]["evidence_refs"]
    )


@pytest.mark.asyncio
async def test_one_slow_call_loses_only_its_own_pairs():
    """The motivating failure: one call times out. The other call's decisions
    still apply; the lost pairs are disclosed as uninspected, not silently
    dropped, and the receipt shows which call failed."""
    cm, ev, row = _many_pairs(8)
    calls = 0

    async def call(prompt, temperature, max_tokens, label):
        nonlocal calls
        calls += 1
        chunk = json.loads(prompt.split("Pairs:\n", 1)[1])
        if len(chunk) == 6:
            raise asyncio.TimeoutError()
        return {
            "pairs": [
                dict(row, pair_id=p["pair_id"], decision="unknown") for p in chunk
            ]
        }

    a = ClaimMapAnalyzer()
    a._call_llm = call
    await review_relationship_scope(a, cm, ev)
    receipt = cm["metadata"]["scope_review"]
    assert calls == 2
    assert sorted(c["status"] for c in receipt["calls"]) == ["failed", "ok"]
    assert receipt["status"] == "needs_review"
    assert receipt["assessed_pairs"] == 2 and receipt["uninspected_pairs"] == 6
    refs = cm["elements"][0]["evidence_refs"]
    assert sum(r["relationship"] == "context" for r in refs) == 2
    assert sum(r["relationship"] == "supports" for r in refs) == 6


@pytest.mark.asyncio
async def test_all_calls_failing_keeps_the_old_failure_status():
    cm, ev, row = _many_pairs(8)
    a = ClaimMapAnalyzer()
    a._call_llm = AsyncMock(side_effect=RuntimeError("provider unavailable"))
    before = copy.deepcopy(cm["elements"])
    await review_relationship_scope(a, cm, ev)
    assert cm["metadata"]["scope_review"]["status"] == "failed"
    assert cm["elements"] == before
