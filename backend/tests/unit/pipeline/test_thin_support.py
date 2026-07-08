"""Tests for the thin / top-up element reads (``app.pipeline.support_structure``).

This module is the backend twin of ``web/lib/support-structure.ts``. The first
table locks the two in PARITY: every case here mirrors a case in
``web/lib/__tests__/support-structure.test.ts`` so a drift in one is caught. The
rest exercise element-level "thin" selection used by the claim-level top-up
endpoint (``research-thin``).
"""

from app.pipeline.support_structure import (
    side_has_quality_note,
    side_quality_note,
    element_has_quality_note,
    element_is_thin,
    thin_element_ids,
)


def _side(**p):
    base = {
        "count": 0,
        "distinct_domains": 0,
        "tier_counts": {"primary": 0, "reporting": 0, "commentary": 0},
        "derivation": {"originals": 0, "derivative_count": 0},
    }
    base.update(p)
    return base


# ── PARITY with support-structure.test.ts (evidenceQualityNote) ──────────────
# Each entry: (label, side, expect_note?). expect_note True == the TS test
# returns a non-null QualityNote; False == returns null.

PARITY_CASES = [
    ("empty side → no note", _side(count=0), False),
    (
        "echo (breadth re-reports one original)",
        _side(
            count=3,
            distinct_domains=3,
            tier_counts={"primary": 1, "reporting": 2, "commentary": 0},
            derivation={"originals": 1, "derivative_count": 2},
        ),
        True,
    ),
    (
        "thin — commentary-grade only",
        _side(
            count=4,
            distinct_domains=2,
            tier_counts={"primary": 0, "reporting": 0, "commentary": 4},
        ),
        True,
    ),
    (
        "thin — several items one website",
        _side(
            count=3,
            distinct_domains=1,
            tier_counts={"primary": 0, "reporting": 3, "commentary": 0},
        ),
        True,
    ),
    (
        "healthy — several independent good sources",
        _side(
            count=3,
            distinct_domains=3,
            tier_counts={"primary": 1, "reporting": 2, "commentary": 0},
        ),
        False,
    ),
    (
        "single good source is not thin (singleOutlet needs count>=2)",
        _side(
            count=1,
            distinct_domains=1,
            tier_counts={"primary": 1, "reporting": 0, "commentary": 0},
        ),
        False,
    ),
    (
        "echo takes priority (echo signals fire regardless of tier mix)",
        _side(
            count=3,
            distinct_domains=1,
            tier_counts={"primary": 1, "reporting": 0, "commentary": 2},
            derivation={"originals": 1, "derivative_count": 2},
        ),
        True,
    ),
    (
        "repetition — same wording, ≥3 on side, ≥2 domains, no primary (F4)",
        _side(
            count=3,
            distinct_domains=3,
            tier_counts={"primary": 0, "reporting": 2, "commentary": 1},
            repetition={"max_cluster_on_side": 3, "distinct_domains": 3},
        ),
        True,
    ),
    (
        "repetition suppressed — side has its own primary",
        _side(
            count=4,
            distinct_domains=3,
            tier_counts={"primary": 1, "reporting": 2, "commentary": 1},
            repetition={"max_cluster_on_side": 3, "distinct_domains": 3},
        ),
        False,
    ),
    (
        "repetition below on-side threshold (2 < 3) → no note",
        _side(
            count=3,
            distinct_domains=2,
            tier_counts={"primary": 0, "reporting": 2, "commentary": 1},
            repetition={"max_cluster_on_side": 2, "distinct_domains": 2},
        ),
        False,
    ),
]


def test_side_note_parity_with_frontend():
    for label, side, expect in PARITY_CASES:
        assert side_has_quality_note(side) is expect, f"parity drift: {label}"


def test_side_quality_note_kinds_and_labels():
    """The label-returning note is locked to the TS evidenceQualityNote payloads
    (kind + exact label), incl. precedence echo → repetition → thin."""
    echo = side_quality_note(
        _side(
            count=3,
            distinct_domains=3,
            tier_counts={"primary": 1, "reporting": 2, "commentary": 0},
            derivation={"originals": 1, "derivative_count": 2},
        )
    )
    assert echo == {
        "kind": "echo",
        "label": "Mostly one source repeated",
        "detail": "Several of these sources repeat a single original report.",
    }

    rep = side_quality_note(
        _side(
            count=3,
            distinct_domains=3,
            tier_counts={"primary": 0, "reporting": 2, "commentary": 1},
            repetition={"max_cluster_on_side": 3, "distinct_domains": 3},
        )
    )
    assert rep["kind"] == "repetition" and rep["label"] == "Same wording, no primary"

    thin_commentary = side_quality_note(
        _side(
            count=4,
            distinct_domains=2,
            tier_counts={"primary": 0, "reporting": 0, "commentary": 4},
        )
    )
    assert (
        thin_commentary["kind"] == "thin"
        and thin_commentary["label"] == "Thin sourcing"
    )

    thin_single = side_quality_note(
        _side(
            count=3,
            distinct_domains=1,
            tier_counts={"primary": 0, "reporting": 3, "commentary": 0},
        )
    )
    assert thin_single == {
        "kind": "thin",
        "label": "Thin sourcing",
        "detail": "All from a single website.",
    }

    assert side_quality_note(_side(count=0)) is None
    assert side_quality_note(None) is None
    # A returned note must be a copy — mutating it can't poison the next call.
    echo["label"] = "MUTATED"
    again = side_quality_note(
        _side(
            count=3,
            tier_counts={"primary": 1, "reporting": 2},
            derivation={"originals": 1, "derivative_count": 2},
        )
    )
    assert again["label"] == "Mostly one source repeated"


def test_side_note_missing_derivation_does_not_crash():
    # A truncated/legacy payload without `derivation` must still classify thin.
    partial = {
        "count": 4,
        "distinct_domains": 2,
        "tier_counts": {"primary": 0, "reporting": 0, "commentary": 4},
    }
    assert side_has_quality_note(partial) is True


def test_side_note_missing_distinct_domains_is_single_outlet():
    # distinct_domains absent -> defaults to 0 -> single-outlet thin, in parity
    # with the frontend `(s.distinct_domains || 0)`.
    partial = {
        "count": 3,
        "tier_counts": {"primary": 0, "reporting": 3, "commentary": 0},
    }
    assert side_has_quality_note(partial) is True


def test_side_note_handles_none_and_garbage():
    assert side_has_quality_note(None) is False
    assert side_has_quality_note("nonsense") is False
    assert side_has_quality_note({}) is False


# ── element_has_quality_note (either side fires) ─────────────────────────────


def test_element_note_fires_on_challenge_side():
    basis = {
        "support_structure": _side(
            count=3,
            distinct_domains=3,
            tier_counts={"primary": 1, "reporting": 2, "commentary": 0},
        ),
        "challenge_structure": _side(
            count=2,
            distinct_domains=1,
            tier_counts={"primary": 0, "reporting": 2, "commentary": 0},
        ),
    }
    assert element_has_quality_note(basis) is True


def test_element_note_none_when_both_sides_healthy():
    healthy = _side(
        count=3,
        distinct_domains=3,
        tier_counts={"primary": 1, "reporting": 2, "commentary": 0},
    )
    basis = {"support_structure": healthy, "challenge_structure": _side(count=0)}
    assert element_has_quality_note(basis) is False


def test_element_note_missing_basis():
    assert element_has_quality_note(None) is False
    assert element_has_quality_note({}) is False


# ── element_is_thin ──────────────────────────────────────────────────────────


def _elem(refs, state="supported", basis=None, eid="e1"):
    e = {"element_id": eid, "evidence_refs": refs, "state": state}
    if basis is not None:
        e["basis"] = basis
    return e


def _refs(n):
    return [{"evidence_id": f"x{i}", "relationship": "supports"} for i in range(n)]


def test_gap_is_not_thin():
    # 0 sources → the Seeker's territory, never a top-up.
    assert element_is_thin(_elem([], state="unresolved")) is False


def test_disputed_is_not_thin_even_with_few_refs():
    # Disputed = evidence-rich + contested, not thin — excluded even at <=2 refs.
    assert element_is_thin(_elem(_refs(2), state="disputed")) is False


def test_few_refs_is_thin():
    assert element_is_thin(_elem(_refs(2), state="supported")) is True
    assert element_is_thin(_elem(_refs(1), state="supported")) is True


def test_unresolved_state_is_thin():
    assert element_is_thin(_elem(_refs(5), state="unresolved")) is True


def test_null_state_is_thin():
    assert element_is_thin(_elem(_refs(5), state=None)) is True


def test_note_makes_a_well_counted_element_thin():
    # 4 refs, resolved, but the sourcing carries a thin note → thin.
    thin_basis = {
        "support_structure": _side(
            count=4,
            distinct_domains=1,
            tier_counts={"primary": 0, "reporting": 0, "commentary": 4},
        ),
        "challenge_structure": _side(count=0),
    }
    assert element_is_thin(_elem(_refs(4), state="supported", basis=thin_basis)) is True


def test_repetition_only_element_is_toppable():
    # 4 resolved refs, no thin/echo, but the support side is a talking-point
    # repetition cluster → thin (toppable via "Strengthen this claim").
    rep_basis = {
        "support_structure": _side(
            count=4,
            distinct_domains=3,
            tier_counts={"primary": 0, "reporting": 3, "commentary": 1},
            repetition={"max_cluster_on_side": 3, "distinct_domains": 3},
        ),
        "challenge_structure": _side(count=0),
    }
    assert element_is_thin(_elem(_refs(4), state="supported", basis=rep_basis)) is True


def test_well_covered_is_not_thin():
    healthy_basis = {
        "support_structure": _side(
            count=3,
            distinct_domains=3,
            tier_counts={"primary": 1, "reporting": 2, "commentary": 0},
        ),
        "challenge_structure": _side(count=0),
    }
    # 3 refs, resolved (supported), healthy sourcing, no note → NOT thin.
    assert (
        element_is_thin(_elem(_refs(3), state="supported", basis=healthy_basis))
        is False
    )


def test_contextual_well_covered_is_not_thin():
    healthy_basis = {
        "support_structure": _side(
            count=4,
            distinct_domains=4,
            tier_counts={"primary": 2, "reporting": 2, "commentary": 0},
        ),
        "challenge_structure": _side(count=0),
    }
    assert (
        element_is_thin(_elem(_refs(4), state="contextual", basis=healthy_basis))
        is False
    )


# ── thin_element_ids (endpoint selection) ────────────────────────────────────


def test_thin_element_ids_selects_only_thin_and_preserves_order():
    healthy_basis = {
        "support_structure": _side(
            count=3,
            distinct_domains=3,
            tier_counts={"primary": 1, "reporting": 2, "commentary": 0},
        ),
        "challenge_structure": _side(count=0),
    }
    claim_map = {
        "elements": [
            _elem([], state="unresolved", eid="e1"),  # gap → skip
            _elem(_refs(2), state="supported", eid="e2"),  # few refs → thin
            _elem(_refs(2), state="disputed", eid="e3"),  # disputed → skip
            _elem(
                _refs(3), state="supported", basis=healthy_basis, eid="e4"
            ),  # well-covered → skip
            _elem(_refs(5), state="unresolved", eid="e5"),  # unresolved → thin
        ]
    }
    assert thin_element_ids(claim_map) == ["e2", "e5"]


def test_thin_element_ids_empty_and_garbage():
    assert thin_element_ids(None) == []
    assert thin_element_ids({}) == []
    assert thin_element_ids({"elements": []}) == []
