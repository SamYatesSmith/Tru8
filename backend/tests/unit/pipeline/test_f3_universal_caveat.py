"""F3 Phase B1 — tier-gated universal caveat (R-U1) tests (2026-07-07).

Design: audit/2026-07-07_f3_design_review.md §7 (B1). A `supported` element whose
own wording asserts a universal ("only"/"first"/"no other", tagged at decompose)
gets a descriptive caveat — UNLESS a primary-tier source backs it (a complete
registry legitimately settles a universal). The state is never changed; the
caveat rides the existing neutral `state_derivation.caveat` channel and describes
the evidential limit, never adjudicates (decision #7).
"""

from app.models.claim_map import ElementState
from app.pipeline.claim_map_analyzer import (
    _UNIVERSAL_CAVEAT,
    _derive_element_state_with_authority,
)


def _ev(eid, tier):
    return {"evidence_id": eid, "tier": tier, "url": f"http://{eid}.example.com"}


def _ref(eid, rel="supports"):
    return {"evidence_id": eid, "relationship": rel}


def _flags(universal=None, geographic=None):
    return {"geographic": geographic or [], "universal": universal or []}


# ── Fires: supported + universal + no primary support ────────────────────────


def test_universal_no_primary_fires_caveat():
    el = {
        "scope_flags": _flags(universal=["no other", "in the world"]),
        "evidence_refs": [_ref("a"), _ref("b")],
    }
    evl = [_ev("a", "reporting"), _ev("b", "commentary")]
    state, basis = _derive_element_state_with_authority(el, evl)
    assert state == ElementState.supported  # state unchanged
    assert basis["caveat"] == _UNIVERSAL_CAVEAT
    assert basis["scope"]["trigger"] == "universal"
    assert basis["scope"]["caveated"] is True
    assert basis["scope"]["primary_support"] is False


# ── Tier gate: a primary supporter suppresses the caveat ─────────────────────


def test_universal_with_primary_support_suppressed():
    el = {
        "scope_flags": _flags(universal=["no other"]),
        "evidence_refs": [_ref("a"), _ref("b")],
    }
    evl = [_ev("a", "primary"), _ev("b", "reporting")]
    state, basis = _derive_element_state_with_authority(el, evl)
    assert state == ElementState.supported
    assert basis["caveat"] is None  # primary registry settles the universal
    assert basis["scope"]["primary_support"] is True
    assert basis["scope"]["caveated"] is False


# ── Does not fire when not scope-sensitive / not supported ───────────────────


def test_no_scope_flags_untouched():
    el = {"evidence_refs": [_ref("a")]}
    _, basis = _derive_element_state_with_authority(el, [_ev("a", "reporting")])
    assert basis["caveat"] is None
    assert "scope" not in basis


def test_geographic_only_flag_does_not_fire_universal():
    el = {
        "scope_flags": _flags(geographic=["britain"]),
        "evidence_refs": [_ref("a")],
    }
    _, basis = _derive_element_state_with_authority(el, [_ev("a", "reporting")])
    assert basis["caveat"] is None
    assert "scope" not in basis  # geographic is R-G2 (Phase B2), not B1


def test_empty_universal_list_does_not_fire():
    el = {"scope_flags": _flags(universal=[]), "evidence_refs": [_ref("a")]}
    _, basis = _derive_element_state_with_authority(el, [_ev("a", "reporting")])
    assert basis["caveat"] is None
    assert "scope" not in basis


def test_contextual_universal_element_gets_no_caveat():
    """Context-only refs → state `contextual`, not `supported`; no universal note."""
    el = {
        "scope_flags": _flags(universal=["no other"]),
        "evidence_refs": [_ref("a", "context"), _ref("b", "context")],
    }
    evl = [_ev("a", "reporting"), _ev("b", "commentary")]
    state, basis = _derive_element_state_with_authority(el, evl)
    assert state == ElementState.contextual
    assert basis["caveat"] is None
    assert "scope" not in basis


def test_dangling_evidence_id_under_universal_flag_fires_no_crash():
    """A ref whose evidence_id isn't in evidence_list → non-primary, no crash;
    the universal caveat still fires (no primary support present)."""
    el = {
        "scope_flags": _flags(universal=["no other"]),
        "evidence_refs": [_ref("ghost")],  # id absent from evidence_list
    }
    state, basis = _derive_element_state_with_authority(el, [])
    assert state == ElementState.supported
    assert basis["caveat"] == _UNIVERSAL_CAVEAT
    assert basis["scope"]["primary_support"] is False


def test_disputed_universal_element_gets_no_universal_caveat():
    """State must be `supported`; an all-challenges universal element is disputed."""
    el = {
        "scope_flags": _flags(universal=["no other"]),
        "evidence_refs": [_ref("a", "challenges"), _ref("b", "challenges")],
    }
    evl = [_ev("a", "reporting"), _ev("b", "reporting")]
    state, basis = _derive_element_state_with_authority(el, evl)
    assert state == ElementState.disputed
    assert basis["caveat"] is None
    assert "scope" not in basis


# ── Existing challenge caveat keeps priority over the universal note ──────────


def test_challenge_caveat_wins_over_universal():
    """A supported-with-challenges universal element keeps the disagreement
    caveat (the more salient signal); the universal note does not overwrite it."""
    el = {
        "scope_flags": _flags(universal=["no other"]),
        "evidence_refs": [
            _ref("a"),
            _ref("b"),
            _ref("c"),
            _ref("d", "challenges"),
        ],
    }
    evl = [
        _ev("a", "primary"),
        _ev("b", "reporting"),
        _ev("c", "reporting"),
        _ev("d", "commentary"),
    ]
    state, basis = _derive_element_state_with_authority(el, evl)
    assert state == ElementState.supported  # supports dominate 2x
    assert "disagree" in basis["caveat"]  # challenge caveat, not the universal one
    assert basis["caveat"] != _UNIVERSAL_CAVEAT
    assert "scope" not in basis
