import copy
from unittest.mock import AsyncMock

import pytest


def test_passage_ranking_recovers_distinguishing_exception_over_repeated_background():
    from app.services.passage_mapping import rank_passages
    from app.services.text_provenance import _terms

    passages = [{"text": "Concurrent readers writers database logging."} for _ in range(6)]
    exception = {"text": "The database can still return ERROR_LOCKED."}
    passages.append(exception)
    before = copy.deepcopy(passages)
    ranked = rank_passages(passages, _terms("Concurrent readers writers database logging prevents ERROR_LOCKED"))
    assert exception in ranked[:2]
    assert passages == before


def test_passage_ranking_keeps_stable_ties_and_rejects_no_overlap():
    from app.services.passage_mapping import rank_passages
    first, second = {"text": "alpha"}, {"text": "alpha beta"}
    assert rank_passages([first, second, {"text": "gamma"}], {"alpha"}) == [first, second]


def test_exact_identifier_survives_distracting_rare_operational_words():
    from app.services.passage_mapping import rank_passages
    from app.services.text_provenance import _terms

    relevant = {"text": "Operations can return ERROR_LOCKED."}
    distractor = {"text": "Unusual operational conditions occur during maintenance."}
    passages = [distractor, {"text": "Conditions never change automatically."}, relevant]
    assert rank_passages(passages, _terms("ERROR_LOCKED never occurs under unusual operational conditions"))[0] == relevant


@pytest.mark.asyncio
async def test_pair_review_uses_dedicated_provider_schema(monkeypatch):
    from app.services.passage_mapping import PASSAGE_RESPONSE_SCHEMA
    analyzer = ClaimMapAnalyzer()
    analyzer.google_ai_api_key = "test-only"
    analyzer._call_google = AsyncMock(return_value=({"pairs": []}, {}))
    await analyzer._call_llm(prompt="Pairs", temperature=0, max_tokens=100, label="passage_review")
    assert analyzer._call_google.call_args.kwargs["response_schema"] == PASSAGE_RESPONSE_SCHEMA
    assert analyzer._call_google.call_args.kwargs["model"] == analyzer.google_model
from app.core.config import settings
from app.pipeline.claim_map_analyzer import ClaimMapAnalyzer
from app.services.text_provenance import capture_text_provenance
from app.services.passage_mapping import (
    plan_pairs,
    complete_passage_pairs,
    validate_citations,
    MAX_PAIRS,
)


def fixture():
    cm = {
        "claim_id": "0",
        "normalised_claim": "SQLite concurrency prevents SQLITE_BUSY",
        "claim_type": "empirical",
        "metadata": {},
        "elements": [
            {
                "element_id": "e1",
                "description": "SQLite supports concurrent readers",
                "state": "supported",
                "evidence_refs": [
                    {
                        "evidence_id": "sqlite",
                        "relationship": "supports",
                        "reasoning": "Readers coexist",
                    }
                ],
            },
            {
                "element_id": "e2",
                "description": "SQLite never returns SQLITE_BUSY",
                "state": "unresolved",
                "evidence_refs": [],
            },
        ],
    }
    ev = {
        "evidence_id": "sqlite",
        "url": "https://sqlite.org/wal.html",
        "title": "SQLite WAL",
        "tier": "primary",
        "evidence_type": "technical",
        "snippet": "Concurrent readers",
        "_full_text": ("General overview. " * 900)
        + "SQLite supports concurrent readers. SQLite can still return SQLITE_BUSY during cleanup.",
    }
    capture_text_provenance(ev, cm["normalised_claim"], cm["elements"])
    return cm, [ev]


def response(pairs, quote="SQLite can still return SQLITE_BUSY during cleanup."):
    return {
        "pairs": [
            {
                "pair_id": p["pair_id"],
                "relationship": "supports" if p["element_id"] == "e1" else "challenges",
                "reasoning": "The excerpt describes this behaviour.",
                "citations": [
                    {
                        "passage_id": p["passages"][0]["id"],
                        "quote": (
                            "SQLite supports concurrent readers."
                            if p["element_id"] == "e1"
                            else quote
                        ),
                    }
                ],
            }
            for p in pairs
        ]
    }


@pytest.mark.asyncio
async def test_already_mapped_source_reaches_other_element_with_exact_quote():
    cm, evidence = fixture()
    pairs, _ = plan_pairs(cm, evidence)
    analyzer = ClaimMapAnalyzer()
    analyzer._call_llm = AsyncMock(return_value=response(pairs))
    await complete_passage_pairs(analyzer, cm, evidence)
    analyzer._call_llm.assert_awaited_once()
    assert "during cleanup" in analyzer._call_llm.call_args.kwargs["prompt"]
    prompt = analyzer._call_llm.call_args.kwargs["prompt"]
    assert '"elements": [' not in prompt
    assert '"pairs":[' in prompt
    assert analyzer._call_llm.call_args.kwargs["label"] == "passage_review"
    assert cm["elements"][0]["evidence_refs"][0]["relationship"] == "supports"
    ref = cm["elements"][1]["evidence_refs"][0]
    assert ref["relationship"] == "challenges"
    citation = ref["citations"][0]
    assert (
        evidence[0]["_full_text"][citation["start"] : citation["end"]]
        == citation["quote"]
    )
    assert cm["metadata"]["passage_review"]["assessed_pairs"] == 2


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "bad",
    [
        "SQLite never returns BUSY.",
        "",
        "SQLite can STILL return SQLITE_BUSY during cleanup.",
    ],
)
async def test_invented_or_normalized_quote_cannot_add_relationship(bad):
    cm, evidence = fixture()
    pairs, _ = plan_pairs(cm, evidence)
    analyzer = ClaimMapAnalyzer()
    analyzer._call_llm = AsyncMock(return_value=response(pairs, bad))
    await complete_passage_pairs(analyzer, cm, evidence)
    assert not cm["elements"][1]["evidence_refs"]
    assert cm["metadata"]["passage_review"]["uninspected_pairs"] == 1


@pytest.mark.asyncio
async def test_conflicting_review_is_recorded_without_overwriting():
    cm, evidence = fixture()
    cm["elements"][1]["evidence_refs"] = [
        {
            "evidence_id": "sqlite",
            "relationship": "supports",
            "reasoning": "Earlier work",
        }
    ]
    pairs, _ = plan_pairs(cm, evidence)
    analyzer = ClaimMapAnalyzer()
    analyzer._call_llm = AsyncMock(return_value=response(pairs))
    await complete_passage_pairs(analyzer, cm, evidence)
    assert cm["elements"][1]["evidence_refs"][0]["relationship"] == "supports"
    assert cm["metadata"]["passage_review"]["pairs"][1]["status"] == "conflict"


def test_pair_budget_rotates_across_elements_and_excludes_no_provenance():
    cm, evidence = fixture()
    pool = [dict(evidence[0], evidence_id=f"source-{i}") for i in range(20)]
    pairs, total = plan_pairs(cm, pool + [{"evidence_id": "legacy"}])
    assert total == 40 and len(pairs) == MAX_PAIRS
    assert [p["element_id"] for p in pairs[:2]] == ["e1", "e2"]
    assert all(len(p["passages"]) <= 2 for p in pairs)
    p = pairs[0]
    assert (
        validate_citations([{"passage_id": "other-source", "quote": "SQLite"}], p)
        is None
    )


@pytest.mark.asyncio
async def test_failure_preserves_map_and_reports_uninspected_pairs():
    cm, evidence = fixture()
    original = copy.deepcopy(cm["elements"])
    analyzer = ClaimMapAnalyzer()
    analyzer._call_llm = AsyncMock(side_effect=RuntimeError("offline failure"))
    await complete_passage_pairs(analyzer, cm, evidence)
    assert cm["elements"] == original
    assert cm["metadata"]["passage_review"]["status"] == "failed"
    assert cm["metadata"]["passage_review"]["uninspected_pairs"] == 2


@pytest.mark.asyncio
async def test_rollout_off_does_not_call_passage_model(monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_PASSAGE_MAPPING", False)
    cm, evidence = fixture()
    analyzer = ClaimMapAnalyzer()
    analyzer._call_llm = AsyncMock()
    await analyzer._complete_unmapped_evidence(cm, evidence)
    analyzer._call_llm.assert_not_called()  # old completion excludes an already mapped source
    assert "passage_review" not in cm["metadata"]


@pytest.mark.asyncio
async def test_rollout_on_integrates_completion_and_gate_uses_reviewed_text(
    monkeypatch,
):
    monkeypatch.setattr(settings, "ENABLE_PASSAGE_MAPPING", True)
    cm, evidence = fixture()
    pairs, _ = plan_pairs(cm, evidence)
    analyzer = ClaimMapAnalyzer()
    analyzer._call_llm = AsyncMock(return_value=response(pairs))
    original_gate = analyzer._apply_scope_gates
    seen = []

    def gate(element, index, claim):
        seen.append(index["sqlite"].text)
        return original_gate(element, index, claim)

    monkeypatch.setattr(analyzer, "_apply_scope_gates", gate)
    await analyzer._complete_unmapped_evidence(cm, evidence)
    assert any("SQLITE_BUSY during cleanup" in text for text in seen)
    assert cm["elements"][1]["evidence_refs"][0]["citations"]
    from app.api.v1.response_builder import _claim_map_to_camel_case, _sanitize_strings

    serialized = _sanitize_strings(_claim_map_to_camel_case(cm))
    assert (
        serialized["elements"][1]["evidenceRefs"][0]["citations"]
        == cm["elements"][1]["evidence_refs"][0]["citations"]
    )


@pytest.mark.asyncio
async def test_distiller_input_includes_late_exceptions_and_element_requirements(
    monkeypatch,
):
    from app.pipeline.evidence_distiller import EvidenceDistiller
    from app.pipeline import evidence_distiller

    monkeypatch.setattr(settings, "ENABLE_PASSAGE_MAPPING", True)
    cm, evidence = fixture()
    model = AsyncMock(
        return_value=(
            {"results": [{"index": 0, "facts": ["SQLite can return SQLITE_BUSY."]}]},
            {},
        )
    )
    monkeypatch.setattr(evidence_distiller, "call_google_ai_with_usage", model)
    await EvidenceDistiller().distil_evidence_for_claim(
        cm["normalised_claim"], evidence, elements=cm["elements"]
    )
    prompt = model.call_args.args[0]
    assert "SQLite can still return SQLITE_BUSY during cleanup." in prompt
    assert "Research elements:" in prompt
    assert len(prompt) < 12000


@pytest.mark.asyncio
async def test_duplicate_or_missing_pair_is_not_reported_as_inspected():
    cm, evidence = fixture()
    pairs, _ = plan_pairs(cm, evidence)
    row = response(pairs)["pairs"][0]
    analyzer = ClaimMapAnalyzer()
    analyzer._call_llm = AsyncMock(return_value={"pairs": [row, row]})
    await complete_passage_pairs(analyzer, cm, evidence)
    assert cm["metadata"]["passage_review"]["assessed_pairs"] == 0
    assert cm["metadata"]["passage_review"]["status"] == "partial"


def test_exact_quote_provenance_is_not_mojibake_normalized():
    from app.api.v1.response_builder import _sanitize_strings

    payload = {
        "textProvenance": {"passages": [{"text": "cafÃ©"}]},
        "citations": [{"quote": "cafÃ©"}],
    }
    assert _sanitize_strings(payload) == payload


@pytest.mark.asyncio
async def test_temporal_gate_scopes_the_actual_reviewed_passage():
    cm, _ = fixture()
    cm["normalised_claim"] = "UK CPI was below 2% in September 2024"
    cm["elements"] = [
        {
            "element_id": "e1",
            "description": cm["normalised_claim"],
            "state": "unresolved",
            "evidence_refs": [],
        }
    ]
    ev = {
        "evidence_id": "ons",
        "url": "https://ons.gov.uk/",
        "tier": "primary",
        "evidence_type": "data",
        "snippet": "UK CPI in September 2024",
        "_full_text": "UK CPI was 3.8% in September 2025.",
    }
    capture_text_provenance(ev, cm["normalised_claim"], cm["elements"])
    pairs, _ = plan_pairs(cm, [ev])
    p = pairs[0]
    analyzer = ClaimMapAnalyzer()
    analyzer._call_llm = AsyncMock(
        return_value={
            "pairs": [
                {
                    "pair_id": p["pair_id"],
                    "relationship": "challenges",
                    "reasoning": "Higher rate",
                    "citations": [
                        {
                            "passage_id": p["passages"][0]["id"],
                            "quote": ev["_full_text"],
                        }
                    ],
                }
            ]
        }
    )
    await complete_passage_pairs(analyzer, cm, [ev])
    ref = cm["elements"][0]["evidence_refs"][0]
    assert ref["relationship"] == "context"
    assert ref["citations"][0]["quote"] == ev["_full_text"]
    # A later recovery pass must not revert to the stale September 2024 snippet.
    from app.pipeline.claim_map_analyzer import _index_evidence

    ref["relationship"] = "challenges"
    analyzer._apply_scope_gates(cm["elements"][0], _index_evidence([ev]), cm)
    assert ref["relationship"] == "context"


def test_passage_contract_changes_fingerprint_only_when_enabled(monkeypatch):
    from app.core.manifest_signer import compute_pipeline_fingerprint

    monkeypatch.setattr(settings, "ENABLE_PASSAGE_MAPPING", False)
    original = compute_pipeline_fingerprint()
    monkeypatch.setattr(settings, "ENABLE_PASSAGE_MAPPING", True)
    assert compute_pipeline_fingerprint() != original
