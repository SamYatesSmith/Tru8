"""Decomposition specificity (2026-09-10).

The 2026-09-09 blind label reviews (audit/review_sheets/2026-09-09{,-postfix})
put 18 of the last 27 rejected labels on ONE cause: decomposition demanding
figures, absolutes or qualities the claim never stated. In assertion form
("exactly 5g", "consistently consume") the invented-precision strip already
backstops the prompt. In QUESTION form — the grounds path asking "What is the
TOTAL lifecycle emission VOLUME…" for "electric cars are cleaner" — nothing
did, and 11 of 27 rejections sat on that one record.

Three mechanisms are pinned here:
  1. The prompt rule, on both decomposition prompts and on the grounds
     question-builder (first line of defence — NF-11).
  2. The mechanical detector for quantity-demanding questions, narrow by
     design, silent when the claim itself states a quantity.
  3. Repair routing: quantity questions ride the SAME repair call as
     compounds (one call, tagged items), fail-safe, flag-gated, disclosed in
     metadata.grounds.specificity.

Design: audit/2026-09-10_decomposition_specificity.md.
"""

import pytest

import app.pipeline.opinion_symmetry as opinion_symmetry
from app.core.config import settings
from app.pipeline.claim_map_analyzer import (
    BATCH_DECOMPOSITION_PROMPT,
    DECOMPOSITION_PROMPT,
)
from app.pipeline.opinion_symmetry import apply_grounds_stage
from app.utils.unstated_quantity import (
    claim_states_quantity,
    demands_unstated_quantity,
    unstated_quantity_indices,
)

# ── the stub analyzer (same shape as test_element_atomicity) ────────────────


class StubAnalyzer:
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


def _handlers(candidate, repaired=None, subj=None, covered=None):
    h = {
        DECOMPOSE: lambda _p: {"elements": [{"description": d} for d in candidate]},
        ON_SUBJECT: lambda _p: {
            "assessments": [
                {"on_subject": f} for f in (subj or [True] * len(candidate))
            ]
        },
        COVERAGE: lambda _p: {"covered": covered or []},
    }
    if repaired is not None:
        h[REPAIR] = lambda _p: {"repaired": list(repaired)}
    return h


EV_CLAIM = "Electric cars are cleaner than petrol cars."

# Verbatim from the 2026-09-09 post-fix regrade, t08_ev — 8 and 3 rejections.
EV_VOLUME = (
    "What is the total lifecycle greenhouse gas emission volume associated with "
    "the manufacturing and operation of electric cars compared to petrol cars?"
)
EV_PROPORTION = (
    "What proportion of the electricity used to charge electric cars is "
    "generated from fossil fuels across major vehicle markets?"
)
EV_REPAIRED_VOLUME = (
    "How do the lifecycle greenhouse gas emissions of electric cars compare "
    "with petrol cars?"
)
EV_REPAIRED_PROPORTION = (
    "How does the fuel mix of the electricity used to charge electric cars "
    "affect their emissions compared with petrol cars?"
)
CLEAN = "How do the lifecycle emissions of electric cars compare with petrol cars?"


# ── 1. prompt rule ──────────────────────────────────────────────────────────


@pytest.mark.parametrize("prompt", [DECOMPOSITION_PROMPT, BATCH_DECOMPOSITION_PROMPT])
def test_decomposition_prompts_carry_the_specificity_rule(prompt):
    assert "MATCH THE CLAIM'S OWN SPECIFICITY" in prompt
    # the measured words, named
    for word in ("exactly", "consistently", "completely", "quantified"):
        assert word in prompt
    # the two shapes that failed on the regrade, named
    assert "comparative claim with no figure" in prompt
    assert "is not a behaviour of a population" in prompt
    # mechanism is no longer an open invitation
    assert "mechanism (only where the claim asserts one)" in prompt


def test_grounds_prompt_asks_at_the_claims_specificity():
    p = opinion_symmetry.NORMATIVE_DECOMPOSE_PROMPT
    assert "claim's OWN level of specificity" in p
    assert "Ask for a quantity only when the claim itself states one" in p
    # the worked example is the real failure
    assert "total lifecycle emission volume" in p


def test_grounds_prompt_stays_direction_free():
    """§20.6(1) still holds: the new rule must not smuggle the §19 toxins
    back in (test_opinion_symmetry pins the same words; repeated here so a
    future edit to THIS rule trips locally)."""
    low = opinion_symmetry.NORMATIVE_DECOMPOSE_PROMPT.lower()
    for forbidden in ("assertion", "direction", "symmetric", "counter", "both sides"):
        assert forbidden not in low, forbidden


def test_repair_prompt_names_both_defects():
    p = opinion_symmetry.QUESTION_REPAIR_PROMPT
    assert "[two questions]" in p and "[unstated quantity]" in p
    assert "repairing research questions" in p  # the marker the tests key on
    assert opinion_symmetry.COMPOUND_REPAIR_PROMPT is p  # alias kept


# ── 2. detector ─────────────────────────────────────────────────────────────


@pytest.mark.parametrize("question", [EV_VOLUME, EV_PROPORTION])
def test_the_regrade_questions_are_detected(question):
    assert demands_unstated_quantity(question, EV_CLAIM)


@pytest.mark.parametrize(
    "question",
    [
        "What is the exact number of jobs the scheme created?",
        "What percentage of patients reported side effects?",
        "What share of the budget went on consultants?",
        "By what margin did the policy miss its target?",
        "What was the aggregate cost to the Treasury?",
    ],
)
def test_close_kin_of_the_measured_heads_are_detected(question):
    assert demands_unstated_quantity(question, "The scheme was a failure.")


# Exposed by the build-2 measurement (2026-09-10 b2 runs 1-2): the quantity
# noun after an auxiliary or a reporting verb, not at the head. 4 labels.
@pytest.mark.parametrize(
    "question",
    [
        "How does the proportion of renewable energy versus fossil fuels used to "
        "charge electric cars compare across different regions?",
        "What do lifecycle analyses show regarding the total carbon footprint of "
        "electric cars versus petrol cars under current electricity generation mixes?",
        "How did the share of coal in the grid change over the decade?",
        "What does the evidence indicate about the percentage of trips under two miles?",
    ],
)
def test_quantity_nouns_after_an_auxiliary_or_reporting_verb_are_detected(question):
    assert demands_unstated_quantity(question, EV_CLAIM)


@pytest.mark.parametrize(
    "question",
    [
        "How does the fuel mix used to charge electric cars affect their emissions?",
        "What do lifecycle analyses show regarding the emissions of electric cars?",
        "How do the environmental impacts of battery production compare with petrol?",
    ],
)
def test_the_same_heads_without_a_quantity_noun_are_left_alone(question):
    assert not demands_unstated_quantity(question, EV_CLAIM)


@pytest.mark.parametrize(
    "question",
    [
        CLEAN,
        "To what extent did the scheme meet its stated targets?",
        "What did independent reviews conclude about the scheme?",
        "Which countries have adopted the same policy?",
        # left OUT on purpose — legitimate grounds for a money judgement
        "How much did the furlough scheme cost?",
        "How many patients were enrolled?",
        "What is the average temperature of Venus?",
    ],
)
def test_ordinary_questions_are_left_alone(question):
    assert not demands_unstated_quantity(question, "The scheme was a waste of money.")


@pytest.mark.parametrize(
    "claim",
    [
        "The scheme cut emissions by 30%.",
        "Most of the electricity comes from coal.",  # no — 'most' is not listed
        "A majority of patients improved.",
        "The total bill was over a billion pounds.",
        "Half of all trips are under two miles.",
        "The number of cases doubled.",
    ],
)
def test_a_claim_that_states_a_quantity_may_be_asked_for_one(claim):
    if claim.startswith("Most of"):
        # 'most' deliberately not a quantity word: "most people think" is not
        # a figure. The question is still flagged for such a claim.
        assert not claim_states_quantity(claim)
        assert demands_unstated_quantity(EV_PROPORTION, claim)
        return
    assert claim_states_quantity(claim)
    assert not demands_unstated_quantity(EV_PROPORTION, claim)


def test_indices_are_positional_and_ordered():
    descs = [CLEAN, EV_VOLUME, "Why did adoption stall?", EV_PROPORTION]
    assert unstated_quantity_indices(descs, EV_CLAIM) == [1, 3]
    assert unstated_quantity_indices([], EV_CLAIM) == []
    assert demands_unstated_quantity("", EV_CLAIM) is False


# ── 3. repair routing ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_quantity_questions_are_repaired_on_the_compound_call():
    analyzer = StubAnalyzer(
        _handlers(
            [EV_VOLUME, CLEAN, EV_PROPORTION],
            repaired=[EV_REPAIRED_VOLUME, EV_REPAIRED_PROPORTION],
        )
    )
    cm = await apply_grounds_stage(analyzer, EV_CLAIM, _baseline())
    descs = [e["description"] for e in cm["elements"]]
    assert descs == [EV_REPAIRED_VOLUME, CLEAN, EV_REPAIRED_PROPORTION]
    assert cm["metadata"]["grounds"]["specificity"] == {
        "detected": 2,
        "repaired": 2,
        "surviving": 0,
    }
    # compounds untouched by this: none present
    assert cm["metadata"]["grounds"]["atomicity"] == {
        "detected": 0,
        "repaired": 0,
        "surviving": 0,
    }
    # ONE repair call, items tagged with their defect
    repair_prompts = [p for p in analyzer.prompts if REPAIR in p]
    assert len(repair_prompts) == 1
    assert "1. [unstated quantity] " + EV_VOLUME in repair_prompts[0]
    assert "2. [unstated quantity] " + EV_PROPORTION in repair_prompts[0]
    assert f"Claim: {EV_CLAIM}" in repair_prompts[0]


@pytest.mark.asyncio
async def test_compound_and_quantity_share_one_call_and_both_tags():
    compound = (
        "What were the stated objectives for the scheme, and to what extent "
        "have those objectives been met?"
    )
    both = (
        "What proportion of the budget was spent, and to what extent were the "
        "targets met?"
    )
    analyzer = StubAnalyzer(
        _handlers(
            [compound, EV_VOLUME, both],
            repaired=[
                "To what extent were the scheme's objectives met?",
                EV_REPAIRED_VOLUME,
                "To what extent were the scheme's targets met?",
            ],
        )
    )
    cm = await apply_grounds_stage(analyzer, EV_CLAIM, _baseline())
    g = cm["metadata"]["grounds"]
    assert g["atomicity"] == {"detected": 2, "repaired": 2, "surviving": 0}
    assert g["specificity"] == {"detected": 2, "repaired": 2, "surviving": 0}
    repair_prompts = [p for p in analyzer.prompts if REPAIR in p]
    assert len(repair_prompts) == 1
    assert "3. [two questions; unstated quantity] " + both in repair_prompts[0]


@pytest.mark.asyncio
async def test_no_defects_means_no_repair_call():
    analyzer = StubAnalyzer(_handlers([CLEAN, "Why did adoption stall?"]))
    cm = await apply_grounds_stage(analyzer, EV_CLAIM, _baseline())
    assert not any(REPAIR in p for p in analyzer.prompts)
    assert cm["metadata"]["grounds"]["specificity"] == {
        "detected": 0,
        "repaired": 0,
        "surviving": 0,
    }


@pytest.mark.asyncio
async def test_a_rewrite_that_still_demands_a_quantity_is_rejected():
    """Repair may improve or leave alone, never make worse: a rewrite that
    still asks for the figure has lost the original wording for nothing."""
    analyzer = StubAnalyzer(
        _handlers(
            [EV_VOLUME],
            repaired=["What is the total emission volume of electric cars?"],
        )
    )
    cm = await apply_grounds_stage(analyzer, EV_CLAIM, _baseline())
    assert [e["description"] for e in cm["elements"]] == [EV_VOLUME]
    assert cm["metadata"]["grounds"]["specificity"] == {
        "detected": 1,
        "repaired": 0,
        "surviving": 1,
    }


@pytest.mark.asyncio
async def test_a_rewrite_that_introduces_a_compound_is_rejected():
    analyzer = StubAnalyzer(
        _handlers(
            [EV_VOLUME],
            repaired=[
                "How do lifecycle emissions compare, and what drives the difference?"
            ],
        )
    )
    cm = await apply_grounds_stage(analyzer, EV_CLAIM, _baseline())
    assert [e["description"] for e in cm["elements"]] == [EV_VOLUME]


@pytest.mark.asyncio
async def test_repair_failure_never_fails_the_check():
    def boom(_p):
        raise RuntimeError("provider down")

    analyzer = StubAnalyzer(_handlers([EV_VOLUME]))
    analyzer._handlers[REPAIR] = boom
    cm = await apply_grounds_stage(analyzer, EV_CLAIM, _baseline())
    assert [e["description"] for e in cm["elements"]] == [EV_VOLUME]
    assert cm["metadata"]["grounds"]["applied"] is True
    assert cm["metadata"]["grounds"]["specificity"]["repaired"] == 0


@pytest.mark.asyncio
async def test_a_claim_stating_a_quantity_is_not_repaired():
    """'30%' in the claim licenses 'what proportion' in the question."""
    analyzer = StubAnalyzer(_handlers([EV_PROPORTION], repaired=["ignored"]))
    cm = await apply_grounds_stage(
        analyzer, "Electric cars cut emissions by 30% over petrol cars.", _baseline()
    )
    assert not any(REPAIR in p for p in analyzer.prompts)
    assert [e["description"] for e in cm["elements"]] == [EV_PROPORTION]
    assert cm["metadata"]["grounds"]["specificity"]["detected"] == 0


@pytest.mark.asyncio
async def test_quantity_flag_off_restores_compound_only_behaviour(monkeypatch):
    """ROLLBACK: with the quantity flag off, a quantity question makes no call,
    carries no tag, and the metadata key does not exist."""
    monkeypatch.setattr(settings, "ENABLE_UNSTATED_QUANTITY_REPAIR", False)
    analyzer = StubAnalyzer(_handlers([EV_VOLUME], repaired=["ignored"]))
    cm = await apply_grounds_stage(analyzer, EV_CLAIM, _baseline())
    assert not any(REPAIR in p for p in analyzer.prompts)
    assert [e["description"] for e in cm["elements"]] == [EV_VOLUME]
    assert "specificity" not in cm["metadata"]["grounds"]
    assert cm["metadata"]["grounds"]["atomicity"]["detected"] == 0


@pytest.mark.asyncio
async def test_quantity_flag_off_still_repairs_compounds(monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_UNSTATED_QUANTITY_REPAIR", False)
    compound = "What were the targets, and to what extent were they met?"
    analyzer = StubAnalyzer(
        _handlers([compound], repaired=["To what extent were the targets met?"])
    )
    cm = await apply_grounds_stage(analyzer, EV_CLAIM, _baseline())
    assert [e["description"] for e in cm["elements"]] == [
        "To what extent were the targets met?"
    ]
    prompt = next(p for p in analyzer.prompts if REPAIR in p)
    assert "[two questions] " + compound in prompt
    # the prompt TEXT names both defects; the ITEMS must carry only one
    assert "[two questions; unstated quantity]" not in prompt
    assert "[unstated quantity] " not in prompt.split("Items:")[1]


@pytest.mark.asyncio
async def test_atomicity_flag_off_disables_both(monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_ELEMENT_ATOMICITY", False)
    analyzer = StubAnalyzer(_handlers([EV_VOLUME], repaired=["ignored"]))
    cm = await apply_grounds_stage(analyzer, EV_CLAIM, _baseline())
    assert not any(REPAIR in p for p in analyzer.prompts)
    assert "specificity" not in cm["metadata"]["grounds"]
    assert "atomicity" not in cm["metadata"]["grounds"]


@pytest.mark.asyncio
async def test_repair_runs_before_the_value_predicate_lock():
    """Same load-bearing order as compounds: a rewrite that collapses into the
    judgement must still be caught by _is_restatement."""
    claim = "HS2 was a disaster"
    analyzer = StubAnalyzer(
        _handlers(
            ["What proportion of HS2 was a disaster?", "What were the delays to HS2?"],
            repaired=["To what extent was HS2 a disaster?"],
        )
    )
    cm = await apply_grounds_stage(analyzer, claim, _baseline())
    descs = [e["description"] for e in cm["elements"]]
    assert "To what extent was HS2 a disaster?" not in descs
    assert "What were the delays to HS2?" in descs
