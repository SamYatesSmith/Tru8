"""The absence-of-evidence scope gate (2026-09-09, Track Q — Astra finding 3)
through the real mapping parser.

The three real creatine challenges from the regrade: "there isn't enough
evidence to support…", "no strong evidence linking…", "no large, long-duration
randomized controlled trials have demonstrated…". Each was mapped `challenges`
and the prevention element read `disputed / all_challenges`. A statement that
evidence is LACKING bears on the element in neither direction. A MEASURED null
result is a finding and must keep its direction.
"""

import pytest

from app.core.config import settings
from app.models.claim_map import ElementState
from app.pipeline.claim_map_analyzer import _SCOPE_RECEIPT_KEYS, ClaimMapAnalyzer
from app.utils.absence_of_evidence import absence_of_evidence_match

VERYWELL = (
    "While it might seem like high doses of creatine (20 g/day or more) could improve "
    "brain health or cognitive functioning, there isn't enough evidence to support that."
)
TONIC = (
    "Effects on overall and executive function have been harder to demonstrate, and "
    "there is currently no strong evidence linking creatine to long-term brain health "
    "outcomes such as dementia risk."
)
FACTUALLY = (
    "Small, short-term human trials show biological plausibility and modest cognitive "
    "gains, yet no large, long-duration randomized controlled trials have demonstrated "
    "prevention of dementia or durable long-term cognitive protection."
)
NULL_RESULT = (
    "The randomised placebo-controlled trial found identical rates of new dementia "
    "diagnoses in adults receiving creatine and placebo over five years."
)
EVIDENCE = [
    {
        "evidence_id": "ev-verywell",
        "url": "https://verywellhealth.example/a",
        "title": "Creatine and the brain",
        "snippet": VERYWELL,
        "tier": "reporting",
    },
    {
        "evidence_id": "ev-tonic",
        "url": "https://tonichealth.example/b",
        "title": "Creatine review",
        "snippet": TONIC,
        "tier": "commentary",
    },
    {
        "evidence_id": "ev-factually",
        "url": "https://factually.example/c",
        "title": "How strong is the evidence",
        "snippet": FACTUALLY,
        "tier": "reporting",
    },
    {
        "evidence_id": "ev-null",
        "url": "https://journal.example/d",
        "title": "Creatine prevention trial",
        "snippet": NULL_RESULT,
        "tier": "primary",
    },
    {
        "evidence_id": "ev-safe",
        "url": "https://blog.example/e",
        "title": "Is creatine safe",
        "snippet": "There is no evidence that creatine causes kidney damage in healthy adults.",
        "tier": "commentary",
    },
]


def _claim_map():
    return {
        "claim_id": "0",
        "normalised_claim": "Taking creatine prevents dementia in healthy adults.",
        "elements": [
            {
                "element_id": "e1",
                "description": "Daily creatine intake prevents the onset of dementia in healthy adults.",
                "evidence_refs": [],
                "state": None,
            }
        ],
        "metadata": {},
    }


def _parse(rels, reasoning=None):
    analyzer = ClaimMapAnalyzer()
    claim_map = _claim_map()
    analyzer._parse_mapping_response(
        {
            "elements": [
                {
                    "element_id": "e1",
                    "state": "disputed",
                    "evidence_refs": [
                        {
                            "evidence_id": eid,
                            "relationship": rel,
                            "reasoning": (reasoning or {}).get(eid, "test"),
                        }
                        for eid, rel in rels
                    ],
                }
            ]
        },
        claim_map,
        EVIDENCE,
    )
    return claim_map["elements"][0]


def _rel(elem, evidence_id):
    for ref in elem["evidence_refs"]:
        if ref["evidence_id"] == evidence_id:
            return getattr(ref["relationship"], "value", ref["relationship"])
    raise AssertionError(f"{evidence_id} missing")


# ---------------------------------------------------------------------------
# Detector
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        VERYWELL,
        TONIC,
        FACTUALLY,
        "The benefit has not been established in humans.",
        "Evidence remains inconclusive on long-term outcomes.",
        "This remains unproven.",
    ],
)
def test_absence_wording_matches(text):
    assert absence_of_evidence_match(None, text) is not None


@pytest.mark.parametrize(
    "text",
    [
        NULL_RESULT,
        "The trial showed no significant difference in admissions between arms.",
        "Participants on the drug had similar mortality rates to placebo.",
        "The study found no reduction in events.",
        "Creatine improved memory scores in the trial.",
    ],
)
def test_measured_results_and_positive_findings_do_not_match(text):
    assert absence_of_evidence_match(None, text) is None


def test_reasoning_alone_is_enough_and_is_named_in_the_receipt():
    entry = absence_of_evidence_match(
        "States that there is not enough evidence to support the idea.",
        "Unrelated body text.",
    )
    assert entry and entry["basis"] == "reasoning"


# ---------------------------------------------------------------------------
# Through the parser
# ---------------------------------------------------------------------------


def test_the_creatine_element_no_longer_reads_disputed_on_absence_statements():
    elem = _parse(
        [
            ("ev-verywell", "challenges"),
            ("ev-tonic", "challenges"),
            ("ev-factually", "challenges"),
        ]
    )
    for eid in ("ev-verywell", "ev-tonic", "ev-factually"):
        assert _rel(elem, eid) == "context"
    assert elem["state"] == ElementState.contextual
    receipt = elem["basis"]["absence_of_evidence"]
    assert receipt["scoped_count"] == 3
    assert all(e["was"] == "challenges" and e["excerpt"] for e in receipt["scoped"])
    assert len(elem["evidence_refs"]) == 3  # nothing deleted


def test_a_measured_null_result_keeps_its_challenge():
    elem = _parse([("ev-null", "challenges"), ("ev-tonic", "challenges")])
    assert _rel(elem, "ev-null") == "challenges"
    assert _rel(elem, "ev-tonic") == "context"
    assert elem["state"] == ElementState.disputed


def test_symmetric_for_supports():
    """'No evidence that creatine causes harm' used as SUPPORT for a safety
    element is the same non-finding, scoped the same way."""
    elem = _parse([("ev-safe", "supports")])
    assert _rel(elem, "ev-safe") == "context"
    assert elem["basis"]["absence_of_evidence"]["scoped"][0]["was"] == "supports"


def test_flag_off_leaves_challenges(monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_ABSENCE_OF_EVIDENCE_GATE", False)
    elem = _parse([("ev-tonic", "challenges")])
    assert _rel(elem, "ev-tonic") == "challenges"
    assert "absence_of_evidence" not in elem["basis"]


def test_key_registered_and_order_before_redundancy_gates_echo_last():
    assert "absence_of_evidence" in _SCOPE_RECEIPT_KEYS
    assert _SCOPE_RECEIPT_KEYS[-1] == "echo_scope"
    from app.pipeline.claim_map_analyzer import _index_evidence

    gates = ClaimMapAnalyzer()._armed_scope_gates(
        _claim_map()["elements"][0], _claim_map(), _index_evidence(EVIDENCE)
    )
    keys = [g.key for g in gates]
    assert keys[-1] == "echo_scope"
    assert keys.index("absence_of_evidence") < keys.index("same_study_scope")
