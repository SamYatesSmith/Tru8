"""Actual broad-pilot false exclusion plus adjacent recital controls."""

import copy

import pytest

from app.core.config import settings
from app.pipeline.claim_map_analyzer import ClaimMapAnalyzer
from app.utils.recital_scope import recital_match

CLAIM = "In the LANE trial, intervention Q reduced hospital admissions in adults compared with placebo."
RESULT = "In the LANE randomized trial, intervention Q significantly reduced hospital admissions in adults compared with placebo."


@pytest.mark.parametrize("enabled", [False, True])
@pytest.mark.parametrize("relationship", ["supports", "challenges"])
def test_reported_finding_through_real_parser(monkeypatch, enabled, relationship):
    monkeypatch.setattr(settings, "ENABLE_PASSAGE_MAPPING", enabled)
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
    assert cm["elements"][0]["evidence_refs"][0]["relationship"] == (
        relationship if enabled else "context"
    )
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
    assert recital_match(None, text, [], CLAIM, allow_reported_results=True)


def test_explicit_attribution_reasoning_still_wins():
    assert recital_match(
        "The company claimed the result.",
        RESULT,
        [("company", "the company")],
        CLAIM,
        allow_reported_results=True,
    )


def test_unseen_reported_observation_not_discarded_for_wording():
    claim = "Practice N was associated with fewer missed school days among adolescents."
    text = "In the adolescent survey, practice N was associated with fewer missed school days among adolescents; researchers reported the association."
    assert recital_match(None, text, [], claim, allow_reported_results=True) is None
