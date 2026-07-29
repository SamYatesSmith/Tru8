"""Phase 3a — element atomicity (design: audit/2026-07-29_element_atomicity_design.md).

An element is meant to ask ONE question. Measured on the live path, 21.2% ask
two and 13.8% ask two of DIFFERENT shapes — and the mapper is told to pick one
shape per element, so the trivially-satisfiable half badges the whole element
`supported` while the half bearing on the claim is never graded.

Two mechanisms are pinned here:
  1. REPAIR at decompose — rewrite two-in-one questions as one (fail-safe:
     never make an element worse, never fail a live check).
  2. The mapper BACKSTOP — a mechanical [COMPOUND] tag steering survivors to
     the stricter rule. This holds even when repair fails entirely, which is
     why it is the honesty guarantee and repair is only the quality win.

Scripted stub analyzer throughout — no real LLM. Route quality is proven by
scripts/compound_question_battery.py, not here.
"""

import pytest

import app.pipeline.claim_map_analyzer as cma
import app.pipeline.opinion_symmetry as opinion_symmetry
from app.core.config import settings
from app.pipeline.opinion_symmetry import apply_grounds_stage
from app.utils.atomicity import (
    DIRECTIONAL,
    ENUMERATIVE,
    conjuncts,
    is_compound,
    is_mixed_shape,
    shape,
)


class StubAnalyzer:
    """Scripts _call_llm by prompt marker; records every prompt sent."""

    def __init__(self, handlers):
        self.decomposition_temperature = 0.0
        self._handlers = handlers
        self.prompts = []

    async def _call_llm(self, prompt, temperature, max_tokens, label):
        self.prompts.append(prompt)
        for marker, fn in self._handlers.items():
            if marker in prompt:
                return fn(prompt)
        return None


DECOMPOSE = "decomposing an EVALUATIVE"
REPAIR = "repairing research questions"
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


def _handlers(candidate, repaired=None, subj=None, covered=None):
    h = {
        DECOMPOSE: _elements(*candidate),
        ON_SUBJECT: _subj(*(subj or [True] * len(candidate))),
        COVERAGE: lambda _p: {"covered": covered or []},
    }
    if repaired is not None:
        h[REPAIR] = lambda _p: {"repaired": list(repaired)}
    return h


# Real compounds lifted verbatim from the 2026-07-29 battery log.
COMPOUND_REAL = [
    "What were the stated objectives for privatising British Rail, and to what "
    "extent have those objectives been met based on available data?",
    "What are the projected passenger numbers and revenue forecasts for the HS2 "
    "line, and how do these compare to initial estimates?",
    "What has been the total expenditure on the HS2 rail project to date, and "
    "what are the projected final costs?",
    "What was the overall cost of the furlough scheme to the government, and how "
    "did this cost compare to alternative policy responses?",
]

# Must NOT split: conjoined noun phrases are ONE question. This is the
# false-positive the interrogative-head requirement exists to prevent.
NOT_COMPOUND = [
    "What is the clinical efficacy and evidence base of the programme?",
    "What are the documented costs and benefits of the scheme?",
    "To what extent were the stated objectives met?",
    "What were the total casualties reported by official inquiries and coroners?",
    "How has demand for degrees changed over the past two decades?",
]


# ── detector ────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("text", COMPOUND_REAL)
def test_real_compounds_are_detected(text):
    assert is_compound(text)
    assert len(conjuncts(text)) == 2


@pytest.mark.parametrize("text", NOT_COMPOUND)
def test_conjoined_noun_phrases_are_never_split(text):
    """Freeze criterion 4 — 'efficacy and evidence base' is one question."""
    assert not is_compound(text)
    assert conjuncts(text) == [text]


def test_empty_text_is_not_compound():
    assert not is_compound("")
    assert conjuncts("") == []


# ── shape classification ────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "text,expected",
    [
        ("To what extent were the targets met?", DIRECTIONAL),
        ("Whether the programme reduced costs?", DIRECTIONAL),
        ("What were the stated targets?", ENUMERATIVE),
        ("Which regions reported a fall?", ENUMERATIVE),
        ("How many deaths were recorded?", ENUMERATIVE),
    ],
)
def test_shape_classification(text, expected):
    assert shape(text) == expected


def test_unknown_shape_defaults_to_the_stricter_rule():
    """An unclassifiable question must never be graded by the easier rule."""
    assert shape("Consider the programme's outcome.") == DIRECTIONAL


def test_mixed_shape_detection():
    mixed = (
        "What are the projected passenger numbers for HS2, and how do these "
        "compare to initial estimates?"
    )
    same = (
        "What has been the total expenditure to date, and what are the "
        "projected final costs?"
    )
    assert is_mixed_shape(mixed)
    assert not is_mixed_shape(same)  # compound, but one rule grades both halves
    assert not is_mixed_shape("To what extent were the targets met?")


# ── repair: the happy path ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_compound_candidate_is_repaired():
    repaired = (
        "To what extent were the stated objectives for privatising British Rail met?"
    )
    analyzer = StubAnalyzer(
        _handlers(
            [COMPOUND_REAL[0], "What were the documented fare changes?"],
            repaired=[repaired],
        )
    )
    cm = await apply_grounds_stage(
        analyzer, "Privatising British Rail was a mistake", _baseline()
    )
    descs = [e["description"] for e in cm["elements"]]
    assert repaired in descs
    assert COMPOUND_REAL[0] not in descs
    assert cm["metadata"]["grounds"]["atomicity"] == {
        "detected": 1,
        "repaired": 1,
        "surviving": 0,
    }


@pytest.mark.asyncio
async def test_element_count_is_preserved_by_repair():
    """Freeze criterion 3 — repair rewrites 1->1. It never splits, so the
    element count, the 5-element contract and the retrieval budget are all
    untouched."""
    analyzer = StubAnalyzer(
        _handlers(
            [COMPOUND_REAL[1], COMPOUND_REAL[2], "What were the documented delays?"],
            repaired=[
                "How do passenger forecasts compare to initial estimates?",
                "What are the projected final costs of HS2?",
            ],
        )
    )
    cm = await apply_grounds_stage(
        analyzer, "HS2 was a catastrophic waste", _baseline()
    )
    assert len(cm["elements"]) == 3


@pytest.mark.asyncio
async def test_no_compounds_means_no_repair_call():
    """Cost + byte-identity: a clean decomposition must not trigger the call."""
    analyzer = StubAnalyzer(_handlers(["What were the documented delays?"]))
    await apply_grounds_stage(analyzer, "X was a mistake", _baseline())
    assert not any(REPAIR in p for p in analyzer.prompts)


# ── repair: fail-safe (criterion 5) ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_malformed_repair_keeps_originals():
    analyzer = StubAnalyzer(_handlers([COMPOUND_REAL[0]]))
    analyzer._handlers[REPAIR] = lambda _p: {"repaired": "not a list"}
    cm = await apply_grounds_stage(analyzer, "X was a mistake", _baseline())
    assert [e["description"] for e in cm["elements"]] == [COMPOUND_REAL[0]]


@pytest.mark.asyncio
async def test_wrong_length_repair_keeps_originals():
    analyzer = StubAnalyzer(
        _handlers([COMPOUND_REAL[0], COMPOUND_REAL[1]], repaired=["only one"])
    )
    cm = await apply_grounds_stage(analyzer, "X was a mistake", _baseline())
    descs = [e["description"] for e in cm["elements"]]
    assert descs == [COMPOUND_REAL[0], COMPOUND_REAL[1]]


@pytest.mark.asyncio
async def test_repair_exception_never_fails_the_check():
    def boom(_p):
        raise RuntimeError("provider down")

    analyzer = StubAnalyzer(_handlers([COMPOUND_REAL[0]]))
    analyzer._handlers[REPAIR] = boom
    cm = await apply_grounds_stage(analyzer, "X was a mistake", _baseline())
    assert [e["description"] for e in cm["elements"]] == [COMPOUND_REAL[0]]
    assert cm["metadata"]["grounds"]["applied"] is True


@pytest.mark.asyncio
async def test_still_compound_rewrite_is_rejected():
    """Repair may improve an element or leave it alone. It may never make one
    worse — a rewrite that is STILL compound loses the original's wording for
    nothing, so it is discarded."""
    analyzer = StubAnalyzer(
        _handlers(
            [COMPOUND_REAL[0]],
            repaired=["What were the aims, and how far were they achieved?"],
        )
    )
    cm = await apply_grounds_stage(analyzer, "X was a mistake", _baseline())
    assert [e["description"] for e in cm["elements"]] == [COMPOUND_REAL[0]]
    assert cm["metadata"]["grounds"]["atomicity"]["surviving"] == 1


# ── ordering: repair must precede the value-predicate lock ──────────────────


@pytest.mark.asyncio
async def test_repair_runs_before_the_lock():
    """Load-bearing ordering. A rewrite can collapse into the judgement
    itself; _is_restatement must see the FINAL text or repair becomes a
    laundering route through the door slice 2 shut."""
    claim = "HS2 was a disaster"
    analyzer = StubAnalyzer(
        _handlers(
            [
                "What were the stated aims of HS2, and to what extent was HS2 a disaster?",
                "What were the documented delays to HS2?",
            ],
            # The repair collapses into a bare restatement of the judgement.
            repaired=["To what extent was HS2 a disaster?"],
        )
    )
    cm = await apply_grounds_stage(analyzer, claim, _baseline())
    descs = [e["description"] for e in cm["elements"]]
    assert "To what extent was HS2 a disaster?" not in descs
    assert "What were the documented delays to HS2?" in descs


@pytest.mark.asyncio
async def test_repair_prompt_precedes_on_subject_prompt():
    analyzer = StubAnalyzer(
        _handlers(
            [COMPOUND_REAL[0]], repaired=["To what extent were the objectives met?"]
        )
    )
    await apply_grounds_stage(analyzer, "X was a mistake", _baseline())
    order = [
        next(m for m in (DECOMPOSE, REPAIR, ON_SUBJECT, COVERAGE) if m in p)
        for p in analyzer.prompts
        if any(m in p for m in (DECOMPOSE, REPAIR, ON_SUBJECT, COVERAGE))
    ]
    assert order.index(REPAIR) < order.index(ON_SUBJECT)


# ── flag off: byte-identity (criterion 1) ───────────────────────────────────


@pytest.mark.asyncio
async def test_flag_off_makes_no_repair_call(monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_ELEMENT_ATOMICITY", False)
    analyzer = StubAnalyzer(_handlers([COMPOUND_REAL[0]], repaired=["ignored"]))
    cm = await apply_grounds_stage(analyzer, "X was a mistake", _baseline())
    assert not any(REPAIR in p for p in analyzer.prompts)
    assert [e["description"] for e in cm["elements"]] == [COMPOUND_REAL[0]]
    assert "atomicity" not in cm["metadata"]["grounds"]


def test_flag_off_emits_no_compound_tag(monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_ELEMENT_ATOMICITY", False)
    els = [{"element_id": "e1", "description": COMPOUND_REAL[1]}]
    assert "[COMPOUND]" not in cma._element_lines(els, grounds=True)


# ── mapper backstop (criterion: the honesty guarantee) ──────────────────────


def test_mixed_shape_element_is_tagged():
    els = [{"element_id": "e1", "description": COMPOUND_REAL[1]}]
    assert "[COMPOUND]" in cma._element_lines(els, grounds=True)


def test_atomic_element_is_not_tagged():
    els = [{"element_id": "e1", "description": "To what extent were the targets met?"}]
    assert "[COMPOUND]" not in cma._element_lines(els, grounds=True)


def test_conjoined_noun_phrase_is_not_tagged():
    els = [{"element_id": "e1", "description": NOT_COMPOUND[0]}]
    assert "[COMPOUND]" not in cma._element_lines(els, grounds=True)


def test_tag_never_fires_on_the_factual_path():
    """The tag steers a rule that lives in GROUNDS_MAPPING_ADDENDUM, which
    only grounds prompts carry. An untagged surface must never emit a token
    nothing in its prompt explains."""
    els = [{"element_id": "e1", "description": COMPOUND_REAL[1]}]
    assert "[COMPOUND]" not in cma._element_lines(els, grounds=False)


def test_causal_tag_still_renders():
    """The shared renderer must not have dropped the tag it replaced."""
    els = [{"element_id": "e1", "description": "Smoking causes lung cancer"}]
    assert "[CAUSAL LINK]" in cma._element_lines(els, grounds=False)


def test_addendum_explains_the_tag():
    """A tag with no explanation in the prompt is noise the LLM may follow
    arbitrarily."""
    assert "[COMPOUND]" in cma.GROUNDS_MAPPING_ADDENDUM
    assert "WHETHER / TO WHAT EXTENT" in cma.GROUNDS_MAPPING_ADDENDUM


def test_all_three_mapping_surfaces_use_the_shared_renderer():
    """Phase 2 lesson: don't generalise one probe to N surfaces. If a call
    site rebuilds element lines by hand, its tag is silently dead."""
    import inspect

    src = inspect.getsource(cma)
    # map / completion / recovery / batch — the batch site found by this very
    # test on first run, having been missed by hand.
    assert src.count("_element_lines(") == 5  # 4 call sites + the definition
    # No hand-rolled renderer may survive anywhere, at any indent.
    assert "_is_causal_link(e['description'])" not in src


# ── prompt rule (first line of defence) ─────────────────────────────────────


def test_decompose_prompt_forbids_compound_questions():
    prompt = opinion_symmetry.NORMATIVE_DECOMPOSE_PROMPT
    assert "EXACTLY ONE thing" in prompt
