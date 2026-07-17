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
    # Structural re-adds are question-wrapped (baseline is assertion-shaped).
    assert (
        "What does the evidence indicate about whether baseline intent element?"
        in descs
    ), "dropped a structural element"


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
    """Tightened for verify NIT-1: when the candidate falls back to the
    baseline AND coverage is malformed, the structural loop must not re-add
    wrapped duplicates of elements already kept."""
    baseline = _baseline("baseline a", "baseline b")
    handlers = {
        DECOMPOSE: lambda _p: None,
        ON_SUBJECT: lambda _p: None,
        COVERAGE: lambda _p: None,
    }
    cm = await apply_grounds_stage(StubAnalyzer(handlers), "X is evil", baseline)
    descs = [e["description"] for e in cm["elements"]]
    assert descs == ["baseline a", "baseline b"], f"duplicated: {descs}"
    assert cm["metadata"]["grounds"]["applied"] is True


@pytest.mark.asyncio
async def test_lock_collapse_restores_baseline_but_discloses():
    """Verify NIT-2: if the lock/filters empty the set, the baseline is
    restored (never empty) but converged=False so downstream can tell the
    rebuild collapsed — the §20.6(2) disclosure promise."""
    baseline = _baseline("Is X truly a disaster?")  # itself a restatement
    handlers = {
        # Every candidate is a restatement → all dropped by the lock.
        DECOMPOSE: _elements("X is a disaster", "Is X a disaster?"),
        ON_SUBJECT: lambda p: {
            "assessments": [{"on_subject": True}]
            * len([ln for ln in p.splitlines() if ln[:2].rstrip(".").isdigit()])
        },
        COVERAGE: lambda _p: {"covered": []},
    }
    cm = await apply_grounds_stage(StubAnalyzer(handlers), "X is a disaster", baseline)
    assert len(cm["elements"]) >= 1, "must never be empty"
    g = cm["metadata"]["grounds"]
    assert g["applied"] is True
    assert g["converged"] is False, "lock collapse must be disclosed"


def test_wrap_phrase_cannot_launder_the_bare_judgement():
    """Verify NIT-3: the stage's own wrap boilerplate must not be a recipe for
    slipping the value predicate past the lock — 'evidence'/'indicate' are
    stopwords, so the wrap-phrased bare judgement is still a restatement."""
    from app.pipeline.opinion_symmetry import _is_restatement

    assert _is_restatement(
        "The situation in Gaza is a genocide",
        "What does the evidence indicate about whether the situation in Gaza is a genocide?",
    )
    assert _is_restatement(
        CLAIM_DISASTER,
        "What does the evidence indicate about whether the government's "
        "immigration policy is a disaster?",
    )


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


# ── §20.6(1): the decompose prompt asks for open questions, never direction ──


def test_decompose_prompt_is_question_shaped_and_direction_free():
    p = opinion_symmetry.NORMATIVE_DECOMPOSE_PROMPT
    assert "OPEN QUESTIONS" in p
    assert "presuppose" in p
    low = p.lower()
    for forbidden in (
        "assertion",  # the §19 toxin — must not come back
        "direction",
        "symmetric",
        "counter",
        "for and against",
        "both sides",
    ):
        assert forbidden not in low, forbidden


# ── §20.6(2): mechanical value-predicate lock ────────────────────────────────


CLAIM_DISASTER = "The government's immigration policy is a disaster"
CLAIM_GAZA = "The situation in Gaza is a genocide"


def test_restatement_lock_drops_bare_judgement():
    from app.pipeline.opinion_symmetry import _is_restatement

    # Question form and assertion form of the bare judgement both drop.
    assert _is_restatement(
        CLAIM_DISASTER, "Is the government's immigration policy a disaster?"
    )
    assert _is_restatement(
        CLAIM_DISASTER, "The government's immigration policy is a disaster."
    )
    assert _is_restatement(CLAIM_GAZA, "Is the situation in Gaza a genocide?")


def test_restatement_lock_legal_label_exemption_is_emergent():
    from app.pipeline.opinion_symmetry import _is_restatement

    # D2: the legal label stays researchable by name — real routes that NAME
    # the label but add empirical substance must pass (the 07-17 question-arm
    # run false-flagged Gaza's two best routes; this pins the fix).
    assert not _is_restatement(
        CLAIM_GAZA,
        "What is the status of ICJ proceedings on genocide concerning the situation in Gaza?",
    )
    assert not _is_restatement(
        CLAIM_GAZA,
        "What are the documented instances of international legal bodies formally "
        "accusing Israel of committing genocide in Gaza, and what evidence did they cite?",
    )
    assert not _is_restatement(
        CLAIM_DISASTER,
        "What are the measured outcomes of the government's immigration policy "
        "against its stated targets?",
    )


@pytest.mark.asyncio
async def test_restatement_dropped_from_candidates_and_structural():
    """The lock guards BOTH doors: candidate grounds AND baseline structural
    re-adds (P3 — the baseline can carry the value predicate as an element)."""
    baseline = _baseline(
        "Is the government's immigration policy a disaster?",  # P3-style predicate element
        "The policy's asylum backlog has grown",
    )

    def on_subject(prompt):
        # Answer on_subject True for however many numbered items were sent
        # (the handler serves both the candidate and the baseline list).
        import re as _re

        n = len(_re.findall(r"^\d+\. ", prompt, flags=_re.M))
        return {"assessments": [{"on_subject": True}] * n}

    handlers = {
        DECOMPOSE: _elements(
            "The government's immigration policy is a disaster",  # restatement
            "What are the policy's measured processing costs?",
        ),
        ON_SUBJECT: on_subject,
        COVERAGE: lambda _p: {"covered": [False]},  # the one surviving structural
    }

    cm = await apply_grounds_stage(StubAnalyzer(handlers), CLAIM_DISASTER, baseline)
    descs = [e["description"] for e in cm["elements"]]
    assert "What are the policy's measured processing costs?" in descs
    assert (
        "What does the evidence indicate about whether the policy's asylum backlog has grown?"
        in descs
    ), "structural re-add lost"
    for d in descs:
        assert "disaster" not in d.lower(), f"value predicate leaked: {d}"


def test_question_wrap_is_mechanical_and_idempotent():
    from app.pipeline.opinion_symmetry import _as_question

    assert (
        _as_question("The merger will be approved.")
        == "What does the evidence indicate about whether the merger will be approved?"
    )
    # Already question-shaped → untouched.
    assert _as_question("What are the outcomes?") == "What are the outcomes?"
    assert _as_question(_as_question("X grew.")) == _as_question("X grew.")


# ── §20.6(4): rebuilt elements carry scope_flags (F3 re-tag) ─────────────────


@pytest.mark.asyncio
async def test_rebuilt_elements_are_scope_tagged():
    handlers = {
        # "only" is a universal scope-sensitive marker (F3 tagger)
        DECOMPOSE: _elements(
            "Is this the only policy of its kind in the UK?",
            "What are the policy's measured outcomes?",
            "How do outcomes compare to previous policies?",
        ),
        ON_SUBJECT: _subj(True, True, True),
        COVERAGE: lambda _p: {"covered": []},
    }
    cm = await apply_grounds_stage(StubAnalyzer(handlers), "X is unique", _baseline())
    flagged = [e for e in cm["elements"] if e.get("scope_flags")]
    assert flagged, "apply_scope_flags did not run on rebuilt elements"


def test_content_words_possessive_strip_is_suffix_not_charset():
    """rstrip(\"'s\") strips a character SET — 'mess' would become 'me' and
    corrupt restatement matching. Pin the suffix semantics."""
    from app.pipeline.opinion_symmetry import _content_words

    words = _content_words("The government's policy is a mess")
    assert "mess" in words
    assert "government" in words  # possessive stripped as a suffix
    assert "me" not in words
