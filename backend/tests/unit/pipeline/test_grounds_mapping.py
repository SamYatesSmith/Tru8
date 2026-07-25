"""§20 slice 3 — grounds-aware mapping semantics (P4 fix), gated and inert.

Pins: (1) the GROUNDS_MAPPING_ADDENDUM reaches the mapping prompt IFF the
claim_map carries metadata.grounds.applied (written only by the grounds
stage, which runs only flag-on + normative-hinted) — every other mapping
prompt is byte-identical to before; (2) the batch path routes grounds
claim_maps through the single-claim mapper (the only one carrying the
addendum); (3) the addendum never leaks direction/balance machinery.
"""

import pytest

from app.models.claim_map import ElementState
from app.pipeline.claim_map_analyzer import (
    GROUNDS_MAPPING_ADDENDUM,
    MAPPING_PROMPT,
    ClaimMapAnalyzer,
    _derive_element_state_with_authority,
    _grounds_applied,
    derive_orientation,
)


def _cm(grounds: bool, claim_id: str = "c1"):
    cm = {
        "claim_id": claim_id,
        "normalised_claim": "The policy is questioned",
        "claim_type": "normative_flagged",
        "elements": [
            {
                "element_id": "e1",
                "description": "What are the documented outcomes?",
                "evidence_refs": [],
                "state": None,
                "uncertainty": None,
            }
        ],
        "orientation": None,
        "orientation_basis": None,
        "metadata": {"element_count": 1},
    }
    if grounds:
        cm["metadata"]["grounds"] = {
            "applied": True,
            "converged": True,
            "element_count": 1,
        }
    return cm


EVIDENCE = [
    {
        "evidence_id": "ev-1",
        "title": "Report",
        "snippet": "Outcomes were documented in detail.",
        "tier": "primary",
        "evidence_type": "report",
    }
]


# ── the gate ─────────────────────────────────────────────────────────────────


def test_grounds_applied_truth_table():
    assert _grounds_applied(_cm(True)) is True
    assert _grounds_applied(_cm(False)) is False
    assert _grounds_applied({"metadata": {"grounds": {"applied": False}}}) is False
    assert _grounds_applied({"metadata": {}}) is False
    assert _grounds_applied({}) is False
    assert _grounds_applied({"metadata": None}) is False


def test_addendum_is_direction_free_and_never_infers_the_claim():
    low = GROUNDS_MAPPING_ADDENDUM.lower()
    for forbidden in ("direction", "symmetric", "counter-", "rebalanc", "balance"):
        assert forbidden not in low, forbidden
    assert "never infer" in low  # the no-verdict guard is stated


# ── prompt identity ──────────────────────────────────────────────────────────


class _CaptureAnalyzer(ClaimMapAnalyzer):
    """Captures the mapping prompt; returns a minimal valid mapping."""

    def __init__(self):
        super().__init__()
        self.captured = []

    async def _call_llm(self, prompt, temperature, max_tokens, label):
        self.captured.append((label, prompt))
        self._last_model_used = "stub"
        elements = [
            {
                "element_id": "e1",
                "evidence_refs": [
                    {
                        "evidence_id": "ev-1",
                        "relationship": "supports",
                        "reasoning": "Documents the outcomes asked about.",
                    }
                ],
                "state": "supported",
                "uncertainty": None,
            }
        ]
        if label == "batch_mapping":
            n = prompt.count("=== CLAIM ")
            return {
                "claims": [
                    {"claim_index": i, "elements": list(elements)} for i in range(n)
                ]
            }
        return {"elements": elements}


@pytest.mark.asyncio
async def test_non_grounds_mapping_prompt_is_byte_identical():
    analyzer = _CaptureAnalyzer()
    await analyzer.map_evidence_to_elements(_cm(False), list(EVIDENCE))
    label, prompt = analyzer.captured[0]
    assert label == "mapping"
    assert GROUNDS_MAPPING_ADDENDUM not in prompt
    # Byte-identity with the pre-slice-3 construction:
    assert prompt.startswith(f"{MAPPING_PROMPT}\n\nClaim: ")


@pytest.mark.asyncio
async def test_grounds_mapping_prompt_carries_the_addendum():
    analyzer = _CaptureAnalyzer()
    await analyzer.map_evidence_to_elements(_cm(True), list(EVIDENCE))
    _, prompt = analyzer.captured[0]
    assert GROUNDS_MAPPING_ADDENDUM in prompt
    assert prompt.startswith(f"{MAPPING_PROMPT}{GROUNDS_MAPPING_ADDENDUM}\n\nClaim: ")


# ── batch partition ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_batch_routes_grounds_claims_individually(monkeypatch):
    analyzer = _CaptureAnalyzer()
    routed = []

    async def fake_single(cm, ev):
        routed.append(cm["claim_id"])

    monkeypatch.setattr(analyzer, "map_evidence_to_elements", fake_single)

    grounds_cm = _cm(True, "g1")
    plain_a = _cm(False, "p1")
    plain_b = _cm(False, "p2")
    await analyzer.map_evidence_batch(
        [
            {"claim_map": grounds_cm, "evidence": list(EVIDENCE)},
            {"claim_map": plain_a, "evidence": list(EVIDENCE)},
            {"claim_map": plain_b, "evidence": list(EVIDENCE)},
        ]
    )
    # The grounds claim went through the single-claim mapper...
    assert routed == ["g1"]
    # ...and the two plain claims went through ONE batch call.
    batch_calls = [c for c in analyzer.captured if c[0] == "batch_mapping"]
    assert len(batch_calls) == 1
    assert GROUNDS_MAPPING_ADDENDUM not in batch_calls[0][1]
    assert "p1" not in routed and "p2" not in routed


@pytest.mark.asyncio
async def test_batch_with_no_grounds_claims_is_unchanged(monkeypatch):
    analyzer = _CaptureAnalyzer()
    routed = []

    async def fake_single(cm, ev):
        routed.append(cm["claim_id"])

    monkeypatch.setattr(analyzer, "map_evidence_to_elements", fake_single)
    await analyzer.map_evidence_batch(
        [
            {"claim_map": _cm(False, "p1"), "evidence": list(EVIDENCE)},
            {"claim_map": _cm(False, "p2"), "evidence": list(EVIDENCE)},
        ]
    )
    assert routed == []  # nothing partitioned
    assert len([c for c in analyzer.captured if c[0] == "batch_mapping"]) == 1


# ── P21 Bug A — shape-aware relationship semantics (2026-07-25) ──────────────


def test_addendum_separates_the_two_question_shapes():
    """The original single rule ("supports" = the evidence ANSWERS the
    question) was right for enumerative grounds and wrong for whether/extent
    ones — a study finding no effect "answered" the question and so earned a
    backwards +SUPPORTED badge (live battery T8, e02). Both shapes must now be
    spelled out, because NORMATIVE_DECOMPOSE_PROMPT commissions both.
    """
    low = GROUNDS_MAPPING_ADDENDUM.lower()
    assert "whether / to what extent" in low
    assert "what / how many / which" in low
    # the whether-shape rule that fixes T8
    assert "negative" in low
    assert 'never "supports"' in low
    # the enumerative shape keeps its worked example — it was never broken
    assert "casualty report" in low


def test_addendum_state_gloss_does_not_relicense_the_answered_reading():
    """`"supported" = the ground is well-documented` sat two sentences below
    the relationship rules and re-licensed exactly the reading Bug A removes:
    evidence documenting that a ground is ABSENT also makes it well-documented.
    """
    low = GROUNDS_MAPPING_ADDENDUM.lower()
    assert "well-documented" not in low
    assert "uniformly shows is not the case" in low


def test_t8_shape_all_challenges_gives_the_honest_unanimous_line():
    """The worked trace behind Bug A: once a negative answer maps to
    `challenges` rather than `supports`, the EXISTING mechanical path carries
    it the rest of the way — no state-derivation or orientation change needed.
    Two grounds whose evidence documents the negative must read as challenged,
    never as "mixed" (invariant #7 — no manufactured false balance).
    """
    evidence = [{"evidence_id": f"ev-{i}", "tier": "primary"} for i in (1, 2, 3)]

    elements = []
    for eid in ("e1", "e2"):
        elem = {
            "element_id": eid,
            "description": "What is the clinical effectiveness of X?",
            "evidence_refs": [
                {"evidence_id": ev["evidence_id"], "relationship": "challenges"}
                for ev in evidence
            ],
            "state": None,
        }
        state, basis = _derive_element_state_with_authority(elem, evidence)
        assert state == ElementState.disputed
        assert basis["rule_applied"] == "all_challenges"
        elem["state"] = state
        elements.append(elem)

    line = derive_orientation(elements)
    assert line == (
        "Of 2 elements examined, retrieved evidence challenges all 2, "
        "with none supporting."
    )
    assert "mixed" not in line


def test_addendum_forbids_silence_as_a_challenge():
    """Live witness `TRU-3661-61C7` (MMR): two grounds badged `−CHALLENGED`
    off ONE source whose own reasoning said the evidence "does not provide
    specific rates" — i.e. silence read as contradiction. The likely licence
    was the bare word "absent", which reads as "absent from the evidence" as
    easily as "absent in the world". Both halves are pinned here.
    """
    low = GROUNDS_MAPPING_ADDENDUM.lower()
    assert "silence is not a challenge" in low
    assert "does not provide this" in low
    assert "in the world" in low
    # the ambiguous bare licence is gone
    assert "it is absent" not in low


def test_silence_outcomes_are_honest_states_not_manufactured_challenges():
    """What the SILENCE rule points the mapper at: an unanswered ground lands
    in a no-answer state. Neither path can produce `disputed`, so a challenge
    on an unanswered question can only come from a mislabelled relationship.
    """
    ev = [{"evidence_id": "ev-1", "tier": "primary"}]
    context_only = {
        "element_id": "e1",
        "evidence_refs": [{"evidence_id": "ev-1", "relationship": "context"}],
        "state": None,
    }
    nothing = {"element_id": "e2", "evidence_refs": [], "state": None}

    state_ctx, basis_ctx = _derive_element_state_with_authority(context_only, ev)
    state_none, basis_none = _derive_element_state_with_authority(nothing, ev)

    assert state_ctx == ElementState.contextual
    assert basis_ctx["rule_applied"] == "context_only"
    assert state_none == ElementState.unresolved
    assert basis_none["rule_applied"] == "no_evidence"


def test_orientation_is_untouched_by_bug_a():
    """Bug A is a mapper-semantics fix ONLY. A genuinely split grounded claim
    still reaches the aggregate "mixed" line with its assertion-framed
    vocabulary — that is Bug B's job (deferred fast-follow). This pins that no
    orientation code moved with Bug A, so the deferral stays honest.
    """
    evidence = [{"evidence_id": "ev-1", "tier": "primary"}]
    supported = {
        "element_id": "e1",
        "evidence_refs": [{"evidence_id": "ev-1", "relationship": "supports"}],
        "state": ElementState.supported,
    }
    challenged = {
        "element_id": "e2",
        "evidence_refs": [{"evidence_id": "ev-1", "relationship": "challenges"}],
        "state": ElementState.disputed,
    }
    assert "mixed" in derive_orientation([supported, challenged])
