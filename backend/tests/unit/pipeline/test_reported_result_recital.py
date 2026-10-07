"""A reported trial finding that restates the claim is scoped to context by the
recital gate (default path), plus attribution and plan controls."""

import copy

import pytest

from app.pipeline.claim_map_analyzer import ClaimMapAnalyzer
from app.utils.recital_scope import recital_match

CLAIM = "In the LANE trial, intervention Q reduced hospital admissions in adults compared with placebo."
RESULT = "In the LANE randomized trial, intervention Q significantly reduced hospital admissions in adults compared with placebo."


@pytest.mark.parametrize("relationship", ["supports", "challenges"])
def test_reported_finding_through_real_parser(relationship):
    cm = {
        "claim_id": "x",
        "normalised_claim": CLAIM,
        "claim_type": "empirical",
        "metadata": {},
        "elements": [
            {
                "element_id": "e1",
                "description": CLAIM,
                "evidence_refs": [],
                "state": None,
            }
        ],
    }
    evidence = [
        {
            "evidence_id": "ev-direct",
            "title": "LANE trial results",
            "snippet": RESULT,
            "tier": "primary",
            "evidence_type": "academic",
            "url": "https://example.org/result",
        }
    ]
    before = copy.deepcopy(evidence)
    # Forced directional responses isolate the gate, symmetrically. They do not
    # assert that the positive source semantically challenges the claim.
    parsed = {
        "elements": [
            {
                "element_id": "e1",
                "evidence_refs": [
                    {
                        "evidence_id": "ev-direct",
                        "relationship": relationship,
                        "reasoning": "Reports the trial outcome.",
                    }
                ],
            }
        ]
    }
    ClaimMapAnalyzer()._parse_mapping_response(parsed, cm, evidence)
    assert cm["elements"][0]["evidence_refs"][0]["relationship"] == "context"
    assert evidence == before


@pytest.mark.parametrize(
    "text",
    [
        CLAIM,
        'The company claims: "' + RESULT + '"',
        "Researchers predict that " + RESULT,
        "The protocol asks whether " + RESULT,
        "The study never reported that " + RESULT,
        CLAIM + " A separate study reported a reduction in costs.",
    ],
)
def test_repetition_attribution_and_plans_still_excluded(text):
    assert recital_match(None, text, [], CLAIM)


def test_explicit_attribution_reasoning_still_wins():
    assert recital_match(
        "The company claimed the result.",
        RESULT,
        [("company", "the company")],
        CLAIM,
    )
