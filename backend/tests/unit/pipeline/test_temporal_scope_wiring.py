"""The temporal gate, through the real mapping parser — not the tagger alone.

WHY THIS FILE EXISTS SEPARATELY
------------------------------
`test_temporal_scope.py` proves the tagger reads periods correctly. That is not
the same as proving the pipeline uses it, and "test the wired seam" is a
standing lesson here — NF-18 hid behind tests that only exercised the halves.

This reconstructs production check `618efbc4` through
`_parse_mapping_response`: the element ONS settles at 1.7%, mapped with four
supports for September 2024 and six challenges drawn from other periods. Before
the gate the mechanical state derivation counted all ten and returned
`disputed` with "evidence is mixed".
"""

import pytest

from app.models.claim_map import ElementState, EvidenceRelationship
from app.pipeline.claim_map_analyzer import ClaimMapAnalyzer

ELEMENT_TEXT = (
    "The measured consumer price index inflation rate in the UK in "
    "September 2024 was less than 2 percent."
)

# Titles and snippets close to what the live check actually retrieved.
EVIDENCE = [
    {
        "evidence_id": "ev-ons",
        "title": "Consumer price inflation, UK: September 2024",
        "snippet": "The Consumer Prices Index (CPI) rose by 1.7% in the 12 months to September 2024.",
        "tier": "primary",
        "evidence_type": "official",
    },
    {
        "evidence_id": "ev-news",
        "title": "UK inflation falls unexpectedly",
        "snippet": "Inflation in the UK dropped sharply to 1.7% in September 2024.",
        "tier": "reporting",
        "evidence_type": "news",
    },
    {
        "evidence_id": "ev-june",
        "title": "Inflation holds above target",
        "snippet": "The UK annual inflation rate eased to 2.6% in June 2025.",
        "tier": "reporting",
        "evidence_type": "news",
    },
    {
        "evidence_id": "ev-may",
        "title": "Inflation hits the target",
        "snippet": "The inflation rate dropped to 2.0% in May 2024.",
        "tier": "primary",
        "evidence_type": "data",
    },
    {
        "evidence_id": "ev-annual",
        "title": "Historic inflation rates",
        "snippet": "The inflation rate for 2024 was 3.27%.",
        "tier": "primary",
        "evidence_type": "data",
    },
    {
        "evidence_id": "ev-undated",
        "title": "Bank holds rates",
        "snippet": "Inflation is still well above the Bank of England's 2% target.",
        "tier": "commentary",
        "evidence_type": "analysis",
    },
]


def _claim_map():
    return {
        "claim_id": "0",
        "normalised_claim": "UK CPI inflation was below 2 percent in September 2024.",
        "elements": [
            {
                "element_id": "e1",
                "description": ELEMENT_TEXT,
                "evidence_refs": [],
                "state": None,
            }
        ],
        "metadata": {},
    }


def _mapping_response():
    """What the mapper returned in production: off-period figures as challenges."""
    return {
        "elements": [
            {
                "element_id": "e1",
                "state": "disputed",
                "evidence_refs": [
                    {
                        "evidence_id": "ev-ons",
                        "relationship": "supports",
                        "reasoning": "ONS reports 1.7%.",
                    },
                    {
                        "evidence_id": "ev-news",
                        "relationship": "supports",
                        "reasoning": "Reports 1.7%.",
                    },
                    {
                        "evidence_id": "ev-june",
                        "relationship": "challenges",
                        "reasoning": "2.6% is above 2%.",
                    },
                    {
                        "evidence_id": "ev-may",
                        "relationship": "challenges",
                        "reasoning": "2.0% is not below 2%.",
                    },
                    {
                        "evidence_id": "ev-annual",
                        "relationship": "challenges",
                        "reasoning": "3.27% is above 2%.",
                    },
                    {
                        "evidence_id": "ev-undated",
                        "relationship": "challenges",
                        "reasoning": "Says above target.",
                    },
                ],
            }
        ]
    }


def _parse(monkeypatch=None):
    analyzer = ClaimMapAnalyzer()
    claim_map = _claim_map()
    analyzer._parse_mapping_response(_mapping_response(), claim_map, EVIDENCE)
    return claim_map["elements"][0]


def _rel(elem, evidence_id):
    for ref in elem["evidence_refs"]:
        if ref["evidence_id"] == evidence_id:
            return getattr(ref["relationship"], "value", ref["relationship"])
    raise AssertionError(f"{evidence_id} missing from refs")


# ---------------------------------------------------------------------------
# The production failure, pinned
# ---------------------------------------------------------------------------


def test_off_period_challenges_are_scoped_to_context():
    elem = _parse()

    assert _rel(elem, "ev-june") == "context"
    assert _rel(elem, "ev-may") == "context"
    assert _rel(elem, "ev-annual") == "context"


def test_on_period_evidence_keeps_its_relationship():
    """The gate must not touch evidence that is actually about September 2024."""
    elem = _parse()

    assert _rel(elem, "ev-ons") == "supports"
    assert _rel(elem, "ev-news") == "supports"


def test_undated_evidence_keeps_its_challenge():
    """The deliberate limit — silence is not a period, and guessing over-fires."""
    elem = _parse()

    assert _rel(elem, "ev-undated") == "challenges"


def test_the_element_no_longer_reads_disputed():
    """The user-visible point of the whole fix.

    Two on-period supports against one undated challenge is no longer the
    close split that produced "evidence is mixed" on a settled fact.
    """
    elem = _parse()

    assert elem["state"] != ElementState.disputed


def test_nothing_is_deleted():
    """Scoping is a re-label, not a removal — the evidence stays visible."""
    elem = _parse()

    assert len(elem["evidence_refs"]) == len(EVIDENCE)


# ---------------------------------------------------------------------------
# The receipt
# ---------------------------------------------------------------------------


def test_scoping_is_recorded_in_the_basis():
    """Invariant #5 — every exclusion has a receipt.

    Scoping removes an item from the state count, so it must be visible where
    the rest of the derivation is.
    """
    elem = _parse()
    receipt = elem["basis"]["temporal_scope"]

    assert receipt["element_period"] == "2024-09"
    assert receipt["scoped_count"] == 3
    assert {s["evidence_id"] for s in receipt["scoped"]} == {
        "ev-june",
        "ev-may",
        "ev-annual",
    }
    assert all(s["was"] == "challenges" for s in receipt["scoped"])


def test_no_receipt_when_nothing_was_scoped():
    """Elements with no pinned period must not carry an empty receipt."""
    analyzer = ClaimMapAnalyzer()
    claim_map = _claim_map()
    claim_map["elements"][0]["description"] = "The UK Online Safety Act exists."
    analyzer._parse_mapping_response(_mapping_response(), claim_map, EVIDENCE)

    assert "temporal_scope" not in claim_map["elements"][0]["basis"]


# ---------------------------------------------------------------------------
# Symmetry — the property that stops this being a sycophancy dial
# ---------------------------------------------------------------------------


def test_off_period_supports_are_scoped_too():
    """A source about another period bears on the element in NEITHER direction.

    If this test is ever relaxed so only challenges are scoped, the gate
    becomes a mechanism that can only ever make claims look better supported —
    exactly what invariant #7 forbids.
    """
    analyzer = ClaimMapAnalyzer()
    claim_map = _claim_map()
    response = _mapping_response()
    for ref in response["elements"][0]["evidence_refs"]:
        if ref["evidence_id"] == "ev-may":
            ref["relationship"] = "supports"

    analyzer._parse_mapping_response(response, claim_map, EVIDENCE)
    elem = claim_map["elements"][0]

    assert _rel(elem, "ev-may") == "context"
    assert elem["basis"]["temporal_scope"]["scoped_count"] == 3
    was = {
        s["evidence_id"]: s["was"] for s in elem["basis"]["temporal_scope"]["scoped"]
    }
    assert was["ev-may"] == "supports"


# ---------------------------------------------------------------------------
# Rollback
# ---------------------------------------------------------------------------


def test_flag_off_restores_the_old_behaviour(monkeypatch):
    """ENABLE_TEMPORAL_SCOPE_GATE=False must be a true rollback."""
    from app.core import config

    monkeypatch.setattr(config.settings, "ENABLE_TEMPORAL_SCOPE_GATE", False)
    elem = _parse()

    assert _rel(elem, "ev-june") == "challenges"
    assert _rel(elem, "ev-may") == "challenges"
    assert "temporal_scope" not in elem["basis"]
