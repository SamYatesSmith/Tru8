"""Characterisation of the four element-refresh sites (structure plan S0).

The structure plan (audit/2026-10-07_structure_and_recovery_plan.md) replaces
four hand-copied "snapshot receipts -> rebuild basis -> restore/merge ->
derive state" sequences with one function (S1a). The replay bench never reads
`basis`, so it cannot prove that refactor output-identical. This test can:
it records the COMPLETE claim map after each site on scenarios chosen to
reach every branch the review named, and compares against a golden file
captured before the refactor.

Sites: B completion census, C relationship review, D echo restore, E coverage
recovery (target gaining refs, non-target gaining refs, target with no new
refs; with and without the full pool).

Regenerate the golden ONLY for an intended output change, and say so in the
commit:  REFRESH_CHARACTERISATION_UPDATE=1 pytest tests/unit/pipeline/test_refresh_characterisation.py
"""

import copy
import json
import os
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from app.models.claim_map import ElementState
from app.pipeline.claim_map_analyzer import ClaimMapAnalyzer, _restore_orphaned_echoes
from app.services.relationship_scope_review import review_relationship_scope

GOLDEN = Path(__file__).parent / "fixtures" / "refresh_characterisation.json"
UPDATE = os.environ.get("REFRESH_CHARACTERISATION_UPDATE") == "1"


def _normalise(obj):
    """What storage sees: enums by value, keys sorted (JSONB + sort_keys)."""
    return json.loads(
        json.dumps(obj, sort_keys=True, default=lambda o: getattr(o, "value", str(o)))
    )


def _bare_analyzer(llm_response):
    analyzer = ClaimMapAnalyzer.__new__(ClaimMapAnalyzer)
    analyzer.snippet_length = 200
    analyzer.analyzer_temperature = 0.1
    analyzer.analyzer_max_tokens = 2000
    analyzer._call_llm = AsyncMock(return_value=llm_response)
    return analyzer


def _ev(eid, tier="primary", snippet=None, **extra):
    return {
        "evidence_id": eid,
        "title": f"Title {eid}",
        "url": f"https://example.org/{eid}",
        "tier": tier,
        "evidence_type": "data",
        "snippet": snippet or f"Snippet for {eid}.",
        **extra,
    }


def _ref(eid, rel, reasoning="test reasoning"):
    return {"evidence_id": eid, "relationship": rel, "reasoning": reasoning}


def _element(eid, state, refs, *, llm_state="supported", receipt=True):
    basis = {"state_derivation": {"rule_applied": "prior", "llm_state": llm_state}}
    if receipt:
        basis["temporal_scope"] = {
            "scoped_count": 1,
            "scoped": [{"evidence_id": "ev-old", "was": "supports"}],
        }
    return {
        "element_id": eid,
        "description": f"Element {eid} about the figures in 2024.",
        "evidence_refs": list(refs),
        "state": ElementState(state),
        "uncertainty": None,
        "basis": basis,
    }


def _claim_map(elements, claim_id="c1"):
    return {
        "claim_id": claim_id,
        "normalised_claim": "The figures rose in 2024.",
        "claim_type": "empirical",
        "elements": elements,
        "metadata": {
            "decomposition_model": "test",
            "mapping_model": "test",
            "element_count": len(elements),
            "completed_at": None,
        },
    }


# ── Scenarios ───────────────────────────────────────────────────────────────


async def _site_b_completion():
    cm = _claim_map(
        [
            _element(
                "e1",
                "disputed",
                [_ref("ev-a", "supports"), _ref("ev-b", "challenges")],
                llm_state="disputed",
            ),
            _element("e2", "unresolved", [], receipt=False, llm_state=None),
        ]
    )
    pool = [_ev("ev-a"), _ev("ev-b"), _ev("ev-c"), _ev("ev-d", tier="reporting")]
    response = {
        "elements": [
            {
                "element_id": "e1",
                "additional_refs": [
                    _ref("ev-c", "supports"),
                    _ref("ev-d", "supports"),
                ],
            },
            {"element_id": "e2", "additional_refs": [_ref("ev-c", "context")]},
        ]
    }
    await _bare_analyzer(response)._complete_unmapped_evidence(cm, pool)
    return cm


async def _site_c_review():
    cm = {
        "claim_id": "x",
        "normalised_claim": "A reduces new diagnoses in adults.",
        "claim_type": "empirical",
        "metadata": {},
        "elements": [
            {
                "element_id": "e1",
                "description": "A reduces new diagnoses in adults.",
                "state": "supported",
                "uncertainty": "Prior uncertainty.",
                "evidence_refs": [
                    _ref("ev-a", "supports", "No progression benefit."),
                    _ref("ev-b", "supports", "Second support."),
                ],
                "basis": {
                    "state_derivation": {
                        "rule_applied": "prior",
                        "llm_state": "supported",
                    },
                    "recital_scope": {
                        "scoped_count": 1,
                        "scoped": [{"evidence_id": "ev-old", "was": "supports"}],
                    },
                },
            }
        ],
    }
    pool = [
        _ev(
            "ev-a",
            content_basis="snippet",
            snippet="The trial enrolled diagnosed adults and measured symptom progression.",
        ),
        _ev("ev-b", content_basis="snippet", snippet="A cut new diagnoses in adults."),
    ]
    row = {
        "pair_id": "scope-0",
        "decision": "mismatch",
        "dimension": "outcome",
        "claim_scope": "new diagnoses",
        "source_scope": "progression after diagnosis",
        "block_id": "mapping-text",
        "quote": pool[0]["snippet"],
        "reasoning": "The trial measures progression after diagnosis, not incidence.",
    }
    analyzer = ClaimMapAnalyzer()
    analyzer._call_llm = AsyncMock(return_value={"pairs": [row]})
    await review_relationship_scope(analyzer, cm, pool)
    return cm


def _site_d_echo_restore(monkeypatch):
    from app.core.config import settings

    from tests.unit.pipeline.test_echo_orphans import (
        ECHO_EVIDENCE,
        RELS,
        _demote,
        _parse,
    )

    monkeypatch.setattr(settings, "ENABLE_ECHO_SCOPE_GATE", True)
    claim_map, elem = _parse(ECHO_EVIDENCE, RELS)
    elem["basis"]["state_derivation"]["llm_state"] = "supported"
    _demote(elem, "ev-orig")
    _restore_orphaned_echoes(claim_map, ECHO_EVIDENCE)
    return claim_map


async def _site_e_recovery(full_pool: bool):
    main = [_ev("ev-main"), _ev("ev-main-2", tier="reporting")]
    new = [
        _ev("ev-rec-e1_0_a", tier="reporting"),
        _ev("ev-rec-e2_0_b"),
        _ev("ev-rec-e2_0_c"),
    ]
    cm = _claim_map(
        [
            _element("e1", "unresolved", [_ref("ev-main-2", "context")]),
            _element("e2", "supported", [_ref("ev-main", "supports")]),
            _element("e3", "unresolved", [], llm_state="unresolved"),
        ]
    )
    response = {
        "elements": [
            {
                "element_id": "e1",
                "evidence_refs": [_ref("ev-rec-e1_0_a", "supports")],
                "state": "supported",
                "uncertainty": "Recovery uncertainty.",
            },
            {
                "element_id": "e2",
                "evidence_refs": [
                    _ref("ev-rec-e2_0_b", "challenges"),
                    _ref("ev-rec-e2_0_c", "challenges"),
                ],
                "state": "disputed",
                "uncertainty": None,
            },
            {
                "element_id": "e3",
                "evidence_refs": [],
                "state": "unresolved",
                "uncertainty": None,
            },
        ]
    }
    await _bare_analyzer(response).map_evidence_to_specific_elements(
        claim_map=cm,
        unresolved_element_ids=["e1", "e3"],
        new_evidence=new,
        full_evidence=(main + new) if full_pool else None,
    )
    return cm


# ── The test ────────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _defaults(monkeypatch):
    from app.core.config import settings

    # Sites B and E call the review only when this flag is on; site C calls it
    # directly. Off keeps each scenario to the one site it characterises.
    monkeypatch.setattr(settings, "ENABLE_RELATIONSHIP_REVIEW", False)


@pytest.mark.asyncio
async def test_refresh_sites_match_the_recorded_output(monkeypatch):
    observed = {
        "B_completion": _normalise(await _site_b_completion()),
        "C_review": _normalise(await _site_c_review()),
        "D_echo_restore": _normalise(_site_d_echo_restore(monkeypatch)),
        "E_recovery_full_pool": _normalise(await _site_e_recovery(True)),
        "E_recovery_no_pool": _normalise(await _site_e_recovery(False)),
    }
    if UPDATE:
        GOLDEN.parent.mkdir(parents=True, exist_ok=True)
        GOLDEN.write_text(
            json.dumps(observed, indent=1, sort_keys=True), encoding="utf-8"
        )
        pytest.skip("golden regenerated")
    golden = json.loads(GOLDEN.read_text(encoding="utf-8"))
    for site in golden:
        assert observed[site] == golden[site], f"{site} output changed"
    assert set(observed) == set(golden)


@pytest.mark.asyncio
async def test_scenarios_reach_the_branches_they_claim(monkeypatch):
    """Guard the characterisation itself: if a scenario stops exercising its
    branch, the golden would silently prove nothing."""
    b = await _site_b_completion()
    assert len(b["elements"][0]["evidence_refs"]) == 4  # completion merged refs
    assert b["elements"][0]["basis"]["state_derivation"]["llm_state"] == "disputed"

    c = await _site_c_review()
    assert "relationship_scope" in c["elements"][0]["basis"]
    assert "recital_scope" in c["elements"][0]["basis"]

    d = _site_d_echo_restore(monkeypatch)
    assert d["elements"][0]["basis"]["echo_scope"].get("restored")

    e = await _site_e_recovery(True)
    by_id = {el["element_id"]: el for el in e["elements"]}
    assert len(by_id["e2"]["evidence_refs"]) == 3  # non-target gained refs
    assert (
        by_id["e2"]["basis"]["state_derivation"]["rule_applied"] == "prior"
    )  # D1 today
    assert by_id["e3"]["evidence_refs"] == []  # target with no new refs
    e_np = await _site_e_recovery(False)
    assert e_np["elements"][1]["basis"].get("evidence_count") is None  # old basis kept
