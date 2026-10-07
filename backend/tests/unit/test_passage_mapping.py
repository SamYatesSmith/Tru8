import copy
from unittest.mock import AsyncMock

import pytest


def test_passage_ranking_recovers_distinguishing_exception_over_repeated_background():
    from app.services.passage_mapping import rank_passages
    from app.services.text_provenance import _terms

    passages = [
        {"text": "Concurrent readers writers database logging."} for _ in range(6)
    ]
    exception = {"text": "The database can still return ERROR_LOCKED."}
    passages.append(exception)
    before = copy.deepcopy(passages)
    ranked = rank_passages(
        passages,
        _terms("Concurrent readers writers database logging prevents ERROR_LOCKED"),
    )
    assert exception in ranked[:2]
    assert passages == before


def test_passage_ranking_keeps_stable_ties_and_rejects_no_overlap():
    from app.services.passage_mapping import rank_passages

    first, second = {"text": "alpha"}, {"text": "alpha beta"}
    assert rank_passages([first, second, {"text": "gamma"}], {"alpha"}) == [
        first,
        second,
    ]


def test_exact_identifier_survives_distracting_rare_operational_words():
    from app.services.passage_mapping import rank_passages
    from app.services.text_provenance import _terms

    relevant = {"text": "Operations can return ERROR_LOCKED."}
    distractor = {"text": "Unusual operational conditions occur during maintenance."}
    passages = [
        distractor,
        {"text": "Conditions never change automatically."},
        relevant,
    ]
    assert (
        rank_passages(
            passages,
            _terms("ERROR_LOCKED never occurs under unusual operational conditions"),
        )[0]
        == relevant
    )


from app.pipeline.claim_map_analyzer import ClaimMapAnalyzer
from app.services.text_provenance import capture_text_provenance


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


@pytest.mark.asyncio
async def test_completion_makes_no_passage_model_call():
    cm, evidence = fixture()
    analyzer = ClaimMapAnalyzer()
    analyzer._call_llm = AsyncMock()
    await analyzer._complete_unmapped_evidence(cm, evidence)
    # No PASSAGE model call. The default-path relationship review (on since
    # 2026-09-29) is a separate call, pinned in test_relationship_scope_review.
    labels = [c.kwargs.get("label") for c in analyzer._call_llm.call_args_list]
    assert "passage_review" not in labels
    assert set(labels) <= {
        "scope_review"
    }  # old completion excludes an already mapped source
    assert "passage_review" not in cm["metadata"]


def test_exact_quote_provenance_is_not_mojibake_normalized():
    from app.api.v1.response_builder import _sanitize_strings

    payload = {"textProvenance": {"passages": [{"text": "cafÃ©"}]}}
    assert _sanitize_strings(payload) == payload
