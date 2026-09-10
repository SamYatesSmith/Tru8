"""Build 2 of 2026-09-10: "finding, not topic" + direction fidelity.

Three blind label reviews (audit/2026-09-10_decomposition_specificity.md §8)
left 45 rejections after the specificity build. 17 were passages that name
the element's SUBJECT and supply a related fact but not the FINDING (a Venus
temperature with no planetary comparison; a trial's design with no result; a
fact-check RATING with no claim; a scheduled launch for "was launched"). Five
of seven reviewer misreads sat on a causal element that had DROPPED the
claim's direction ("primary driver of its mortality outcome" for "caused
LOWER mortality").

Pinned here:
  1. The mapping rule FINDING, NOT TOPIC on both mapping prompts.
  2. The fact-check adapter's fallback snippet carries the claim it rated.
  3. The decomposition rule KEEP THE CLAIM'S DIRECTION on both prompts.
  4. The mechanical detector for a causal element that lost the direction.
  5. The repair call: one call per claim, 1->1, fail-safe, flag-gated, on
     BOTH decomposition paths, recorded in metadata.direction_restored.

Design: audit/2026-09-10_finding_not_topic_direction.md.
"""

import pytest

from app.core.config import settings
from app.pipeline import claim_map_analyzer as cma
from app.pipeline.claim_map_analyzer import (
    BATCH_DECOMPOSITION_PROMPT,
    BATCH_MAPPING_PROMPT,
    DECOMPOSITION_PROMPT,
    DIRECTION_REPAIR_PROMPT,
    MAPPING_PROMPT,
    ClaimMapAnalyzer,
)
from app.services.factcheck_api import FactCheckAPI
from app.utils.direction_fidelity import (
    claim_directions,
    keeps_direction,
    lost_direction,
    lost_direction_indices,
)

SWEDEN = (
    "Sweden's decision not to impose a general lockdown caused it to have lower "
    "excess mortality in 2020-22 than every other European country."
)
# Verbatim from the 2026-09-10 runs — the shape that invited the misreads.
DROPPED = "Sweden's lack of a general lockdown was the primary driver of its mortality outcomes."
DROPPED_2 = (
    "Sweden's absence of a general lockdown was the primary cause of its excess "
    "mortality outcome relative to other European countries in 2020-22."
)
KEPT = (
    "Sweden's decision not to impose a general lockdown was the primary cause of it "
    "having lower excess mortality than every other European country in 2020-22."
)
NOT_CAUSAL = "Sweden did not impose a general lockdown in 2020-22."
REPAIRED = (
    "Sweden's lack of a general lockdown was the primary driver of its lower excess "
    "mortality."
)


# ── 1. mapping rule ─────────────────────────────────────────────────────────


@pytest.mark.parametrize("prompt", [MAPPING_PROMPT, BATCH_MAPPING_PROMPT])
def test_mapping_prompts_carry_finding_not_topic(prompt):
    assert "FINDING, NOT TOPIC" in prompt
    # the four measured shapes, named
    for shape in (
        "no comparison to the other planets",
        "design and endpoints without its result",
        "fact-check RATING with no statement of what was rated",
        "launch is SCHEDULED",
        "a study in one population",
    ):
        assert shape in prompt, shape
    # sits AFTER the rule it generalises
    assert prompt.index("TOPIC vs FIGURE") < prompt.index("FINDING, NOT TOPIC")


# ── 2. fact-check snippet ───────────────────────────────────────────────────


def _fc(**over):
    fc = {
        "publisher": "AFP",
        "url": "https://factcheck.afp.com/x",
        "title": "Report did not find EVs pollute more than gas cars",
        "rating": "False",
        "review_date": "2026-01-01",
    }
    fc.update(over)
    return fc


def test_factcheck_fallback_snippet_names_the_claim_rated():
    api = FactCheckAPI()
    out = api.convert_to_evidence(
        _fc(claim_text="Electric vehicles pollute more than gas cars"),
        "EVs are cleaner",
    )
    assert (
        out["snippet"]
        == 'Fact-check of the claim "Electric vehicles pollute more than gas cars" — rating: False'
    )


def test_factcheck_fallback_without_claim_text_is_unchanged():
    """Legacy shape kept byte-identical (fixtures in test_retrieve /
    test_assertion_evidence_wiring rely on it)."""
    api = FactCheckAPI()
    assert api.convert_to_evidence(_fc(), "x")["snippet"] == "Fact-check rating: False"
    assert (
        api.convert_to_evidence(_fc(claim_text="   "), "x")["snippet"]
        == "Fact-check rating: False"
    )


def test_factcheck_extracted_text_still_wins():
    api = FactCheckAPI()
    out = api.convert_to_evidence(
        _fc(claim_text="whatever"), "x", extracted_text="Full article body here."
    )
    assert out["snippet"] == "Full article body here."


# ── 3. decomposition rule ───────────────────────────────────────────────────


@pytest.mark.parametrize("prompt", [DECOMPOSITION_PROMPT, BATCH_DECOMPOSITION_PROMPT])
def test_decomposition_prompts_carry_keep_the_direction(prompt):
    assert "KEEP THE CLAIM'S DIRECTION" in prompt
    assert "loses the direction and can be read either way" in prompt
    # placed with the other specificity rule
    assert prompt.index("MATCH THE CLAIM'S OWN SPECIFICITY") < prompt.index(
        "KEEP THE CLAIM'S DIRECTION"
    )


# ── 4. detector ─────────────────────────────────────────────────────────────


def test_claim_directions_are_stems():
    assert claim_directions(SWEDEN) == {"lowe"}
    assert claim_directions("Prices rose and unemployment fell.") == {"rose", "fell"}
    assert claim_directions("The policy reduced emissions by a third.") == {"redu"}
    assert claim_directions("The telescope was launched in 2021.") == set()


@pytest.mark.parametrize("element", [DROPPED, DROPPED_2])
def test_the_measured_shape_is_detected(element):
    assert lost_direction(element, SWEDEN)


def test_an_element_that_keeps_the_direction_is_not_flagged():
    assert not lost_direction(KEPT, SWEDEN)
    assert keeps_direction(KEPT, SWEDEN)


def test_a_non_causal_element_is_never_flagged():
    assert not lost_direction(NOT_CAUSAL, SWEDEN)


def test_a_claim_with_no_direction_never_flags():
    claim = "The mini-budget caused the Bank of England to intervene."
    assert not lost_direction("The mini-budget caused the intervention.", claim)
    assert keeps_direction("anything", claim)


def test_stem_matching_accepts_inflections():
    claim = "The scheme reduced waiting times."
    assert not lost_direction(
        "The scheme was responsible for the reduction in waiting times.", claim
    )
    assert lost_direction(
        "The scheme was responsible for waiting-time outcomes.", claim
    )


def test_indices_are_positional():
    assert lost_direction_indices([NOT_CAUSAL, DROPPED, KEPT, DROPPED_2], SWEDEN) == [
        1,
        3,
    ]


# ── 5. repair routing ───────────────────────────────────────────────────────


REPAIR = "LOST the claim's direction"
DECOMPOSE = "analytical decomposition engine"


class Stub(ClaimMapAnalyzer):
    """Scripts _call_llm by prompt marker; records prompts."""

    def __init__(self, handlers):
        super().__init__()
        self._handlers = handlers
        self.prompts = []
        self._last_model_used = "stub"

    async def _call_llm(self, prompt, temperature, max_tokens, label):
        self.prompts.append((label, prompt))
        for marker, fn in self._handlers.items():
            if marker in prompt:
                return fn(prompt)
        return None


def _decomp(*descs):
    return lambda _p: {
        "normalised_claim": SWEDEN,
        "claim_type": "causal_interpretive",
        "elements": [{"description": d} for d in descs],
    }


@pytest.mark.asyncio
async def test_dropped_direction_is_repaired_on_the_single_path():
    a = Stub(
        {
            DECOMPOSE: _decomp(NOT_CAUSAL, DROPPED),
            REPAIR: lambda _p: {"repaired": [REPAIRED]},
        }
    )
    cm = await a.decompose_claim(SWEDEN, "c1")
    assert [e["description"] for e in cm["elements"]] == [NOT_CAUSAL, REPAIRED]
    assert cm["metadata"]["direction_restored"] == [
        {"element_id": "e2", "was": DROPPED, "now": REPAIRED}
    ]
    repair_prompts = [p for lbl, p in a.prompts if REPAIR in p]
    assert len(repair_prompts) == 1
    assert f"Claim: {SWEDEN}" in repair_prompts[0]
    assert "1. " + DROPPED in repair_prompts[0]
    assert KEPT not in repair_prompts[0] and NOT_CAUSAL not in repair_prompts[0]


@pytest.mark.asyncio
async def test_dropped_direction_is_repaired_on_the_batch_path():
    def batch(_p):
        return {
            "claims": [
                {
                    "claim_index": 0,
                    "normalised_claim": SWEDEN,
                    "claim_type": "causal_interpretive",
                    "elements": [{"description": DROPPED}],
                },
                {
                    "claim_index": 1,
                    "normalised_claim": "x",
                    "claim_type": "empirical",
                    "elements": [{"description": "The UK left the EU in 2020."}],
                },
            ]
        }

    a = Stub(
        {
            "Given multiple claims": batch,
            REPAIR: lambda _p: {"repaired": [REPAIRED]},
        }
    )
    out = await a.decompose_claims_batch(
        [
            {"text": SWEDEN, "claim_id": "a"},
            {"text": "The UK left the EU in 2020.", "claim_id": "b"},
        ]
    )
    assert out["a"]["elements"][0]["description"] == REPAIRED
    assert "direction_restored" in out["a"]["metadata"]
    assert "direction_restored" not in out["b"]["metadata"]
    assert sum(1 for lbl, p in a.prompts if REPAIR in p) == 1


@pytest.mark.asyncio
async def test_nothing_dropped_means_no_repair_call():
    a = Stub({DECOMPOSE: _decomp(NOT_CAUSAL, KEPT)})
    cm = await a.decompose_claim(SWEDEN, "c1")
    assert not any(REPAIR in p for _, p in a.prompts)
    assert "direction_restored" not in cm["metadata"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "bad",
    [
        "Sweden's lack of a lockdown was the primary driver of its mortality.",  # still no direction
        "Sweden had lower excess mortality.",  # direction back but no longer causal
        "",
    ],
)
async def test_a_rewrite_that_does_not_fix_the_defect_is_rejected(bad):
    a = Stub({DECOMPOSE: _decomp(DROPPED), REPAIR: lambda _p: {"repaired": [bad]}})
    cm = await a.decompose_claim(SWEDEN, "c1")
    assert cm["elements"][0]["description"] == DROPPED
    assert "direction_restored" not in cm["metadata"]


@pytest.mark.asyncio
async def test_a_rewrite_may_not_smuggle_invented_precision():
    a = Stub(
        {
            DECOMPOSE: _decomp(DROPPED),
            REPAIR: lambda _p: {
                "repaired": [
                    "Sweden's lack of a lockdown was the primary driver of its "
                    "consistently lower excess mortality."
                ]
            },
        }
    )
    cm = await a.decompose_claim(SWEDEN, "c1")
    assert (
        cm["elements"][0]["description"]
        == "Sweden's lack of a lockdown was the primary driver of its lower excess mortality."
    )


@pytest.mark.asyncio
async def test_malformed_or_failing_repair_keeps_originals():
    a = Stub({DECOMPOSE: _decomp(DROPPED), REPAIR: lambda _p: {"repaired": "nope"}})
    cm = await a.decompose_claim(SWEDEN, "c1")
    assert cm["elements"][0]["description"] == DROPPED

    def boom(_p):
        raise RuntimeError("provider down")

    a = Stub({DECOMPOSE: _decomp(DROPPED), REPAIR: boom})
    cm = await a.decompose_claim(SWEDEN, "c1")
    assert cm["elements"][0]["description"] == DROPPED
    assert cm["claim_type"] == "causal_interpretive"  # the check did not fail


@pytest.mark.asyncio
async def test_flag_off_makes_no_call_and_no_key(monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_DIRECTION_REPAIR", False)
    a = Stub({DECOMPOSE: _decomp(DROPPED), REPAIR: lambda _p: {"repaired": [REPAIRED]}})
    cm = await a.decompose_claim(SWEDEN, "c1")
    assert cm["elements"][0]["description"] == DROPPED
    assert not any(REPAIR in p for _, p in a.prompts)
    assert "direction_restored" not in cm["metadata"]


def test_repair_prompt_is_one_to_one_and_conservative():
    assert "SAME ORDER" in DIRECTION_REPAIR_PROMPT
    assert "Change nothing else" in DIRECTION_REPAIR_PROMPT
    assert "do not weaken\nor strengthen the causal verb" in DIRECTION_REPAIR_PROMPT


def test_repaired_elements_are_retagged_for_scope():
    """apply_scope_flags runs on the rewritten text (F3 tagging is lexical)."""
    src = open(cma.__file__, encoding="utf-8").read()
    body = src[src.index("async def _repair_lost_direction") :]
    body = body[: body.index("def _parse_decomposition_response")]
    assert "apply_scope_flags(elements)" in body
