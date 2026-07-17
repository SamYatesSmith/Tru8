"""Phase 1b — opinion grounds stage mechanics (decoupling plan §20, slice 1).

Pins the mechanical guarantees with a SCRIPTED stub analyzer (no real LLM):
on-subject / structural-coverage / fail-safe / never-empty /
converge-or-disclose. Route quality (are the grounds good, is the value
predicate absent) is proven by the live eval battery, not here.

The direction-forcing rebalancing apparatus (option C) was REMOVED in slice 1
after the false-balance finding (plan §19/§20); these tests also pin its
absence — the stage must never add, drop, or reorder elements by direction.
"""

import pytest

import app.pipeline.opinion_symmetry as opinion_symmetry
from app.pipeline.opinion_symmetry import apply_grounds_stage


class StubAnalyzer:
    """Scripts _call_llm by inspecting which prompt is being sent.

    Handlers are keyed by a marker substring in the prompt. Each handler gets
    the prompt and returns the parsed dict (or None to simulate failure).
    """

    def __init__(self, handlers):
        self.decomposition_temperature = 0.0
        self._handlers = handlers

    async def _call_llm(self, prompt, temperature, max_tokens, label):
        for marker, fn in self._handlers.items():
            if marker in prompt:
                return fn(prompt)
        return None


DECOMPOSE = "decomposing an EVALUATIVE"
ON_SUBJECT = "auditing a research design"
COVERAGE = "checking coverage"


def _baseline(*descriptions):
    return {
        "elements": [
            {"element_id": f"e{i + 1}", "description": d}
            for i, d in enumerate(descriptions)
        ],
        "metadata": {},
    }


def _elements(*descs):
    return lambda _p: {"elements": [{"description": d} for d in descs]}


def _subj(*flags):
    return lambda _p: {"assessments": [{"on_subject": f} for f in flags]}


# ── the removal is pinned: no direction apparatus survives ───────────────────


def test_direction_apparatus_is_gone():
    """The option-C rebalancing core must not silently return (plan §20.4).
    A balance gate may only ever come back if it fails two-sided."""
    for symbol in ("_claim_dominated", "_rebalance_add", "apply_symmetry_stage"):
        assert not hasattr(opinion_symmetry, symbol), symbol
    for prompt_name in ("REBALANCE_PROMPT", "ASSESS_PROMPT"):
        assert not hasattr(opinion_symmetry, prompt_name), prompt_name
    for prompt in (
        opinion_symmetry.NORMATIVE_DECOMPOSE_PROMPT,
        opinion_symmetry.ON_SUBJECT_PROMPT,
        opinion_symmetry.COVERAGE_PROMPT,
    ):
        low = prompt.lower()
        for forbidden in ("direction", "symmetric", "counter-", "rebalanc"):
            assert forbidden not in low, forbidden


# ── on-subject filtering ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_off_subject_candidate_is_dropped():
    handlers = {
        DECOMPOSE: _elements("on subject ground", "off subject drift"),
        ON_SUBJECT: _subj(True, False),
        COVERAGE: lambda _p: {"covered": []},
    }
    cm = await apply_grounds_stage(StubAnalyzer(handlers), "X is corrupt", _baseline())
    descs = [e["description"] for e in cm["elements"]]
    assert "off subject drift" not in descs
    assert "on subject ground" in descs


@pytest.mark.asyncio
async def test_no_direction_based_selection():
    """Grounds that would build the case FOR the claim are kept exactly like
    any other on-subject ground — the union-guard deletion (opinion_symmetry
    line 250 in the killed design) must not resurface."""
    handlers = {
        DECOMPOSE: _elements(
            "backlog grew under the policy",  # claim-direction ground
            "costs exceeded projections",  # claim-direction ground
            "safeguards exist",  # counter-direction ground
        ),
        ON_SUBJECT: _subj(True, True, True),
        COVERAGE: lambda _p: {"covered": []},
    }
    cm = await apply_grounds_stage(
        StubAnalyzer(handlers), "X is a disaster", _baseline()
    )
    descs = [e["description"] for e in cm["elements"]]
    assert descs == [
        "backlog grew under the policy",
        "costs exceeded projections",
        "safeguards exist",
    ], "selection or order changed — direction-based editing has returned"


# ── fail-safe: garbage assessment preserves elements ─────────────────────────


@pytest.mark.asyncio
async def test_malformed_assessment_preserves_candidates():
    handlers = {
        DECOMPOSE: _elements("ground 0", "ground 1", "ground 2"),
        ON_SUBJECT: lambda _p: {"garbage": "wrong shape"},
        COVERAGE: lambda _p: None,
    }
    cm = await apply_grounds_stage(
        StubAnalyzer(handlers), "X is a triumph", _baseline()
    )
    assert len(cm["elements"]) == 3  # preserved, never condemned


# ── structural coverage: an uncovered baseline element is added back ─────────


@pytest.mark.asyncio
async def test_uncovered_baseline_structural_element_is_added():
    baseline = _baseline("baseline intent element")
    handlers = {
        DECOMPOSE: _elements("candidate ground"),
        ON_SUBJECT: _subj(True),  # applies to both candidate and baseline lists
        COVERAGE: lambda _p: {"covered": [False]},  # baseline NOT covered
    }
    cm = await apply_grounds_stage(
        StubAnalyzer(handlers), "situation is genocide", baseline
    )
    descs = [e["description"] for e in cm["elements"]]
    assert "baseline intent element" in descs, "dropped a structural element"


@pytest.mark.asyncio
async def test_covered_baseline_element_is_not_duplicated():
    baseline = _baseline("already covered ground")
    handlers = {
        DECOMPOSE: _elements("candidate that covers it"),
        ON_SUBJECT: _subj(True),
        COVERAGE: lambda _p: {"covered": [True]},
    }
    cm = await apply_grounds_stage(StubAnalyzer(handlers), "X is unfair", baseline)
    descs = [e["description"] for e in cm["elements"]]
    assert descs == ["candidate that covers it"]


# ── never empty + total failure discloses ────────────────────────────────────


@pytest.mark.asyncio
async def test_total_decompose_failure_keeps_baseline_and_discloses():
    baseline = _baseline("baseline a", "baseline b")
    handlers = {
        DECOMPOSE: lambda _p: None,
        ON_SUBJECT: lambda _p: None,
        COVERAGE: lambda _p: None,
    }
    cm = await apply_grounds_stage(StubAnalyzer(handlers), "X is evil", baseline)
    assert len(cm["elements"]) >= 1, "must never be empty"
    assert cm["metadata"]["grounds"]["applied"] is True


@pytest.mark.asyncio
async def test_analyzer_exception_keeps_baseline_untouched_and_discloses():
    """NIT-1 (slice-1 verify): failure must preserve baseline elements FIELD-
    FOR-FIELD — scope_flags, evidence_refs, state, element_id all survive."""
    rich_element = {
        "element_id": "elem-abc",
        "description": "baseline a",
        "scope_flags": {"geographic": True, "universal": False},
        "evidence_refs": [{"evidence_id": "ev1", "relationship": "supports"}],
        "state": "supported",
    }
    baseline = {"elements": [dict(rich_element)], "metadata": {}}

    class ExplodingAnalyzer:
        decomposition_temperature = 0.0

        async def _call_llm(self, **_kw):
            raise RuntimeError("LLM down")

    cm = await apply_grounds_stage(ExplodingAnalyzer(), "X is evil", baseline)
    assert cm["elements"] == [rich_element], "baseline element mutated on failure"
    g = cm["metadata"]["grounds"]
    assert g["applied"] is False
    assert g["converged"] is False
    assert g["element_count"] == 1


@pytest.mark.asyncio
async def test_degenerate_all_empty_input_left_untouched():
    """NIT-2: empty baseline + failed decompose → claim_map untouched, disclosed."""
    baseline = {"elements": [], "metadata": {}}
    handlers = {
        DECOMPOSE: lambda _p: None,
        ON_SUBJECT: lambda _p: None,
        COVERAGE: lambda _p: None,
    }
    cm = await apply_grounds_stage(StubAnalyzer(handlers), "X is evil", baseline)
    assert cm["elements"] == []
    g = cm["metadata"]["grounds"]
    assert g["applied"] is False
    assert g["element_count"] == 0


@pytest.mark.asyncio
async def test_metadata_less_claim_map_gets_element_count():
    """NIT-3: a claim_map arriving without a metadata key still gets
    element_count written (setdefault, not conditional)."""
    baseline = {"elements": [{"element_id": "e1", "description": "old"}]}
    handlers = {
        DECOMPOSE: _elements("a ground"),
        ON_SUBJECT: _subj(True),
        COVERAGE: lambda _p: {"covered": [True]},  # baseline covered → not re-added
    }
    cm = await apply_grounds_stage(StubAnalyzer(handlers), "X is bad", baseline)
    assert cm["metadata"]["element_count"] == 1
    assert cm["metadata"]["grounds"]["applied"] is True


# ── converge-or-disclose: thin sets disclose, never fail ─────────────────────


@pytest.mark.asyncio
async def test_thin_set_discloses_not_fails():
    handlers = {
        DECOMPOSE: _elements("only ground"),
        ON_SUBJECT: _subj(True),
        COVERAGE: lambda _p: {"covered": []},
    }
    cm = await apply_grounds_stage(StubAnalyzer(handlers), "X is a mess", _baseline())
    assert len(cm["elements"]) == 1
    g = cm["metadata"]["grounds"]
    assert g["applied"] is True
    assert g["converged"] is False  # below breadth floor 3 → disclosed
    assert g["element_count"] == 1


@pytest.mark.asyncio
async def test_breadth_floor_met_converges():
    handlers = {
        DECOMPOSE: _elements("g1", "g2", "g3"),
        ON_SUBJECT: _subj(True, True, True),
        COVERAGE: lambda _p: {"covered": []},
    }
    cm = await apply_grounds_stage(StubAnalyzer(handlers), "X is great", _baseline())
    assert cm["metadata"]["grounds"]["converged"] is True


# ── element shape is mapper-ready ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_element_shape_is_mapper_ready():
    handlers = {
        DECOMPOSE: _elements("a ground"),
        ON_SUBJECT: _subj(True),
        COVERAGE: lambda _p: {"covered": []},
    }
    cm = await apply_grounds_stage(StubAnalyzer(handlers), "X is unfair", _baseline())
    el = cm["elements"][0]
    assert el["element_id"] == "e1"
    assert el["evidence_refs"] == []
    assert el["state"] is None
    assert "basis" not in el, "basis.direction must not be written (plan §20.4)"
    assert cm["metadata"]["element_count"] == 1


# ── cap ──────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_max_elements_cap_holds():
    handlers = {
        DECOMPOSE: _elements("g1", "g2", "g3", "g4", "g5", "g6", "g7"),
        ON_SUBJECT: _subj(*([True] * 7)),
        COVERAGE: lambda _p: {"covered": []},
    }
    cm = await apply_grounds_stage(StubAnalyzer(handlers), "X is huge", _baseline())
    assert len(cm["elements"]) <= 5
