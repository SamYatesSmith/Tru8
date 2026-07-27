"""Phase 1 mechanical honesty (2026-07-27) — orientation suppression + grounds support floor.

Design: audit/2026-07-27_phase1_mechanical_honesty_design.md

Pins the two mechanical changes and, just as importantly, pins that the FACTUAL
path is byte-identical: the floor defaults to 0 and orientation prose is
untouched for any claim the grounds stage did not rebuild.

Live witnesses this exists to prevent:
  * TRU-4B9D-65EA — "retrieved evidence predominantly supports all 4" on
    "The UK COVID vaccine rollout was a triumph", with two of those four
    questions marked supported off ONE source each.
  * TRU-171A-9EF9 — "evidence is mixed" where 12-13 sources agreed with the claim.
"""

import pytest

from app.core.config import settings
from app.models.claim_map import ElementState
from app.pipeline.claim_map_analyzer import (
    _derive_element_state_with_authority,
    _state_floor_for,
    apply_orientation,
    compute_orientation_basis,
    derive_orientation,
)


def _elem(
    element_id="e1", description="What do the records show?", refs=None, state=None
):
    return {
        "element_id": element_id,
        "description": description,
        "evidence_refs": refs if refs is not None else [],
        "state": state,
        "uncertainty": None,
    }


def _cm(grounds: bool, elements=None):
    cm = {
        "claim_id": "c1",
        "normalised_claim": "The rollout was a triumph",
        "claim_type": "normative_flagged" if grounds else "empirical",
        "elements": elements if elements is not None else [_elem(state="supported")],
        "orientation": "STALE — must be overwritten",
        "orientation_basis": None,
        "metadata": {"element_count": 1},
    }
    if grounds:
        cm["metadata"]["grounds"] = {
            "applied": True,
            "converged": True,
            "element_count": len(cm["elements"]),
        }
    return cm


def _ref(evidence_id, relationship="supports"):
    return {"evidence_id": evidence_id, "relationship": relationship, "reasoning": "r"}


def _ev(evidence_id, tier):
    return {"evidence_id": evidence_id, "tier": tier}


# ── Criterion 1 + 2 + 3: orientation ─────────────────────────────────────────


def test_grounds_claim_orientation_prose_is_none():
    """C1: a grounds-routed claim states no aggregate verdict."""
    cm = _cm(grounds=True)
    apply_orientation(cm)
    assert cm["orientation"] is None


def test_factual_claim_orientation_prose_byte_identical():
    """C2: the factual path is untouched — prose equals the raw derivation."""
    cm = _cm(grounds=False)
    expected = derive_orientation(cm["elements"])
    apply_orientation(cm)
    assert cm["orientation"] == expected
    assert cm["orientation"].startswith("Of 1 element")


def test_orientation_basis_always_computed_both_paths():
    """C3: basis survives suppression — it is in the signed manifest payload."""
    for grounds in (True, False):
        cm = _cm(grounds=grounds)
        expected = compute_orientation_basis(cm["elements"])
        apply_orientation(cm)
        assert cm["orientation_basis"] == expected
        assert cm["orientation_basis"] is not None


def test_apply_orientation_handles_missing_elements():
    """Total over hostile shapes — must not raise on a malformed map."""
    cm = {"claim_id": "c1", "metadata": {}}
    apply_orientation(cm)
    assert cm["orientation_basis"] is not None


# ── Criterion 4 + 5 + 6: the support floor ───────────────────────────────────


def test_grounds_element_below_floor_becomes_unresolved():
    """C4: one commentary source (weight 1) cannot answer a question."""
    elem = _elem(refs=[_ref("ev1")])
    evidence = [_ev("ev1", "commentary")]
    state, basis = _derive_element_state_with_authority(elem, evidence, 3)
    assert state == ElementState.unresolved
    assert basis["rule_applied"] == "grounds_support_floor"


def test_grounds_element_at_floor_stays_supported():
    """C5: one primary source (weight 3) clears the floor."""
    elem = _elem(refs=[_ref("ev1")])
    evidence = [_ev("ev1", "primary")]
    state, basis = _derive_element_state_with_authority(elem, evidence, 3)
    assert state == ElementState.supported
    assert basis["rule_applied"] == "all_supports"


def test_grounds_floor_met_by_three_commentary():
    """C5: weights accumulate — three commentary sources also clear it."""
    elem = _elem(refs=[_ref("ev1"), _ref("ev2"), _ref("ev3")])
    evidence = [
        _ev("ev1", "commentary"),
        _ev("ev2", "commentary"),
        _ev("ev3", "commentary"),
    ]
    state, _ = _derive_element_state_with_authority(elem, evidence, 3)
    assert state == ElementState.supported


def test_factual_element_identical_with_default_floor():
    """C6: the same thin evidence on a FACTUAL claim is untouched."""
    elem = _elem(refs=[_ref("ev1")])
    evidence = [_ev("ev1", "commentary")]
    state, basis = _derive_element_state_with_authority(elem, evidence)
    assert state == ElementState.supported
    assert basis["rule_applied"] == "all_supports"


def test_floor_never_upgrades_or_touches_challenged_states():
    """The floor only ever downgrades `supported` — never invents support."""
    elem = _elem(refs=[_ref("ev1", "challenges")])
    evidence = [_ev("ev1", "commentary")]
    state, basis = _derive_element_state_with_authority(elem, evidence, 3)
    assert state == ElementState.disputed
    assert basis["rule_applied"] == "all_challenges"


def test_floor_does_not_disturb_empty_element():
    """No refs at all stays `unresolved` via the no_evidence rule, not the floor."""
    elem = _elem(refs=[])
    state, basis = _derive_element_state_with_authority(elem, [], 3)
    assert state == ElementState.unresolved
    assert basis["rule_applied"] == "no_evidence"


# ── The floor selector ───────────────────────────────────────────────────────


def test_state_floor_zero_for_factual_claim():
    assert _state_floor_for(_cm(grounds=False)) == 0


def test_state_floor_configured_for_grounds_claim():
    assert _state_floor_for(_cm(grounds=True)) == settings.GROUNDS_MIN_WEIGHTED_SUPPORT


def test_state_floor_zero_disables_the_rule(monkeypatch):
    """Rollback lever: GROUNDS_MIN_WEIGHTED_SUPPORT=0 restores prior behaviour."""
    monkeypatch.setattr(settings, "GROUNDS_MIN_WEIGHTED_SUPPORT", 0)
    assert _state_floor_for(_cm(grounds=True)) == 0
    elem = _elem(refs=[_ref("ev1")])
    state, basis = _derive_element_state_with_authority(
        elem, [_ev("ev1", "commentary")], 0
    )
    assert state == ElementState.supported
    assert basis["rule_applied"] == "all_supports"


# ── Criterion 11: unresolved reaches the Seeker's gap count ──────────────────


def test_floored_element_is_seeker_visible_not_contextual():
    """Deliberate divergence from the 2026-05-12 rule: a question with topical
    material but no answer is an UNKNOWN worth re-searching, so it must land in
    `unresolved` (which SeekerView counts) and never in `contextual` (which it
    explicitly excludes from gaps)."""
    elem = _elem(refs=[_ref("ev1"), _ref("ev2", "context")])
    evidence = [_ev("ev1", "commentary"), _ev("ev2", "commentary")]
    state, _ = _derive_element_state_with_authority(elem, evidence, 3)
    assert state == ElementState.unresolved
    assert state != ElementState.contextual
