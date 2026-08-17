"""The echo scope gate (2026-08-17, quality-first Phase B) through the real
mapping parser.

Reconstructs the NHS outreach record's failure class: one original wire story
plus its syndicated copies, ALL counted as independent supports — the state
function reads only relationship + tier, so five copies of one story weighed
as five sources. The gate re-labels a directional ref to `context` when its
evidence is a DERIVATIVE (corroboration derivation chain) of an original
ALREADY COUNTED on the same side of the same element, with a receipt naming
the original (invariant #5).

Independence stays meaningful: a derivative whose original is NOT counted on
its side is the only carrier of that content and stays directional.
"""

import pytest

from app.core.config import settings
from app.models.claim_map import ElementState
from app.pipeline.claim_map_analyzer import _SCOPE_RECEIPT_KEYS, ClaimMapAnalyzer

# ev-orig is the primary; ev-d1/ev-d2 are its derivatives per the
# corroboration engine (chains live ON the primary, listing derivatives).
# ev-d4 is a derivative of ev-orig2, which is NOT referenced by the element.
EVIDENCE = [
    {
        "evidence_id": "ev-orig",
        "url": "https://agency.example/wire-story",
        "title": "Original wire story",
        "snippet": "The figures were published this morning.",
        "tier": "primary",
        "derivation_chain": ["ev-d1", "ev-d2"],
    },
    {
        "evidence_id": "ev-d1",
        "url": "https://outlet-one.example/reprint",
        "title": "Outlet one reprint",
        "snippet": "The figures were published this morning.",
        "tier": "reporting",
    },
    {
        "evidence_id": "ev-d2",
        "url": "https://outlet-two.example/reprint",
        "title": "Outlet two reprint",
        "snippet": "The figures were published this morning.",
        "tier": "reporting",
    },
    {
        "evidence_id": "ev-orig2",
        "url": "https://agency-two.example/other-story",
        "title": "Second original, unreferenced",
        "snippet": "A separate account entirely.",
        "tier": "primary",
        "derivation_chain": ["ev-d4"],
    },
    {
        "evidence_id": "ev-d4",
        "url": "https://outlet-three.example/reprint",
        "title": "Only carrier of the second account",
        "snippet": "A separate account entirely.",
        "tier": "reporting",
    },
]


def _claim_map():
    # No subjects, no jurisdiction, no month-pinned wording: ONLY the echo
    # gate can arm, so every scoping observed here is its work.
    return {
        "claim_id": "0",
        "normalised_claim": "The figures rose.",
        "elements": [
            {
                "element_id": "e1",
                "description": "Whether the figures rose.",
                "evidence_refs": [],
                "state": None,
            }
        ],
        "metadata": {},
    }


def _response(rels):
    return {
        "elements": [
            {
                "element_id": "e1",
                "state": "supported",
                "evidence_refs": [
                    {
                        "evidence_id": eid,
                        "relationship": rel,
                        "reasoning": "test",
                    }
                    for eid, rel in rels
                ],
            }
        ]
    }


def _parse(rels):
    analyzer = ClaimMapAnalyzer()
    claim_map = _claim_map()
    analyzer._parse_mapping_response(_response(rels), claim_map, EVIDENCE)
    return claim_map["elements"][0]


def _rel(elem, evidence_id):
    for ref in elem["evidence_refs"]:
        if ref["evidence_id"] == evidence_id:
            return getattr(ref["relationship"], "value", ref["relationship"])
    raise AssertionError(f"{evidence_id} missing from refs")


# ---------------------------------------------------------------------------
# The NHS-class failure, pinned
# ---------------------------------------------------------------------------


def test_copies_of_a_counted_original_stop_counting():
    elem = _parse(
        [
            ("ev-orig", "supports"),
            ("ev-d1", "supports"),
            ("ev-d2", "supports"),
        ]
    )
    assert _rel(elem, "ev-orig") == "supports"
    assert _rel(elem, "ev-d1") == "context"
    assert _rel(elem, "ev-d2") == "context"
    # The state is derived from the ONE real source, not three.
    sd = elem["basis"]["state_derivation"]
    assert sd["supports_count"] == 1
    assert elem["state"] == ElementState.supported  # primary alone clears the floor


def test_the_receipt_names_the_original():
    elem = _parse([("ev-orig", "supports"), ("ev-d1", "supports")])
    receipt = elem["basis"]["echo_scope"]
    entry = next(e for e in receipt["scoped"] if e["evidence_id"] == "ev-d1")
    assert entry["was"] == "supports"
    assert entry["original_id"] == "ev-orig"


def test_nothing_is_deleted():
    elem = _parse(
        [
            ("ev-orig", "supports"),
            ("ev-d1", "supports"),
            ("ev-d2", "supports"),
        ]
    )
    assert len(elem["evidence_refs"]) == 3


# ---------------------------------------------------------------------------
# Independence stays meaningful
# ---------------------------------------------------------------------------


def test_a_derivative_whose_original_is_absent_stays_directional():
    """ev-d4's original (ev-orig2) is not referenced by the element, so ev-d4
    is the only carrier of that content — it must keep its direction."""
    elem = _parse([("ev-orig", "supports"), ("ev-d4", "supports")])
    assert _rel(elem, "ev-d4") == "supports"
    assert "echo_scope" not in elem["basis"]


def test_a_derivative_on_the_OTHER_side_from_its_original_stays():
    """The condition is per-side: an original counted `supports` does not make
    a `challenges` derivative redundant — they say different things."""
    elem = _parse([("ev-orig", "supports"), ("ev-d1", "challenges")])
    assert _rel(elem, "ev-d1") == "challenges"


# ---------------------------------------------------------------------------
# Symmetry — the property that stops this being a sycophancy dial
# ---------------------------------------------------------------------------


def test_a_challenge_side_echo_chain_is_scoped_just_as_readily():
    """Five outlets reciting one critical report is one criticism, not five —
    invariant #7 forbids distortion in either direction."""
    elem = _parse(
        [
            ("ev-orig", "challenges"),
            ("ev-d1", "challenges"),
            ("ev-d2", "challenges"),
        ]
    )
    assert _rel(elem, "ev-orig") == "challenges"
    assert _rel(elem, "ev-d1") == "context"
    assert _rel(elem, "ev-d2") == "context"
    entry = next(
        e for e in elem["basis"]["echo_scope"]["scoped"] if e["evidence_id"] == "ev-d1"
    )
    assert entry["was"] == "challenges"


# ---------------------------------------------------------------------------
# Rollback and merge-path parity
# ---------------------------------------------------------------------------


def test_flag_off_restores_old_behaviour(monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_ECHO_SCOPE_GATE", False)
    elem = _parse([("ev-orig", "supports"), ("ev-d1", "supports")])
    assert _rel(elem, "ev-d1") == "supports"
    assert "echo_scope" not in elem["basis"]


def test_echo_scope_is_a_declared_receipt_key():
    """Omission from _SCOPE_RECEIPT_KEYS silently drops a gate's receipts on
    BOTH merge paths while the main pass looks fine — the exact class of the
    d39b65d bug, one layer up (design review I-5)."""
    assert "echo_scope" in _SCOPE_RECEIPT_KEYS
