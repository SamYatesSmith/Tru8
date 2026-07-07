"""Tests for the per-element support/challenge STRUCTURE summary.

Covers the echo / thin-support detector's mechanical backend (Phase 1):
- `_compute_relationship_structure` — count, domain breadth, tier mix, derivation
- `_compute_element_basis` — attaches support_structure + challenge_structure,
  without regressing the existing basis keys
- `_domain_of` — domain extraction edge cases

The pipeline reports STRUCTURE ONLY (no thin/echo verdict, no score); these
tests assert that contract: deterministic, mechanical, additive.
"""

from app.pipeline.claim_map_analyzer import (
    _compute_element_basis,
    _compute_relationship_structure,
    _domain_of,
)


# ── Helpers ──────────────────────────────────────────────────────────────────


def _ev(eid, url="https://example.com/x", tier="reporting", derivation_chain=None):
    d = {"evidence_id": eid, "url": url, "tier": tier}
    if derivation_chain is not None:
        d["derivation_chain"] = derivation_chain
    return d


def _ref(eid, relationship="supports"):
    return {"evidence_id": eid, "relationship": relationship, "reasoning": "x"}


def _index(evs):
    return {e["evidence_id"]: e for e in evs}


# ── _domain_of ───────────────────────────────────────────────────────────────


def test_domain_of_strips_www_and_lowercases():
    assert _domain_of("https://www.Reuters.com/article") == "reuters.com"


def test_domain_of_handles_empty_and_garbage():
    assert _domain_of("") == ""
    assert _domain_of(None) == ""  # type: ignore[arg-type]
    # Unparseable input must not raise.
    assert isinstance(_domain_of("not a url"), str)


# ── _compute_relationship_structure ──────────────────────────────────────────


def test_structure_broad_primary_backed_support():
    """Case A: 3 independent sources, mixed tier, no derivation → robust."""
    evs = [
        _ev("a", url="https://gov.uk/report", tier="primary"),
        _ev("b", url="https://reuters.com/x", tier="reporting"),
        _ev("c", url="https://bbc.co.uk/y", tier="reporting"),
    ]
    refs = [_ref("a"), _ref("b"), _ref("c")]
    s = _compute_relationship_structure(refs, _index(evs), set())

    assert s["count"] == 3
    assert s["distinct_domains"] == 3
    assert s["tier_counts"] == {"primary": 1, "reporting": 2, "commentary": 0}
    assert s["derivation"] == {"originals": 0, "derivative_count": 0}


def test_structure_thin_commentary_only_narrow():
    """Case B: 4 commentary items from one domain → thin, narrow."""
    evs = [
        _ev("a", url="https://blog.example.com/1", tier="commentary"),
        _ev("b", url="https://blog.example.com/2", tier="commentary"),
        _ev("c", url="https://blog.example.com/3", tier="commentary"),
        _ev("d", url="https://blog.example.com/4", tier="commentary"),
    ]
    refs = [_ref(e["evidence_id"]) for e in evs]
    s = _compute_relationship_structure(refs, _index(evs), set())

    assert s["count"] == 4
    assert s["distinct_domains"] == 1
    assert s["tier_counts"] == {"primary": 0, "reporting": 0, "commentary": 4}
    assert s["derivation"] == {"originals": 0, "derivative_count": 0}


def test_structure_echo_traces_to_single_original():
    """Case C: 1 primary + 2 re-reporters deriving from it → echo."""
    evs = [
        _ev(
            "a",
            url="https://gov.uk/release",
            tier="primary",
            derivation_chain=["b", "c"],
        ),
        _ev("b", url="https://news1.com/x", tier="reporting"),
        _ev("c", url="https://news2.com/y", tier="reporting"),
    ]
    derivative_ids = {"b", "c"}  # union of derivation chains across the pool
    refs = [_ref("a"), _ref("b"), _ref("c")]
    s = _compute_relationship_structure(refs, _index(evs), derivative_ids)

    assert s["count"] == 3
    # 1 original primary with a chain; 2 of the items are derivatives of it.
    assert s["derivation"] == {"originals": 1, "derivative_count": 2}


def test_structure_unresolved_ref_bucketed_commentary():
    """A ref whose evidence_id isn't in the pool still counts (as commentary)."""
    evs = [_ev("a", tier="primary")]
    refs = [_ref("a"), _ref("missing")]
    s = _compute_relationship_structure(refs, _index(evs), set())

    assert s["count"] == 2
    assert s["tier_counts"]["primary"] == 1
    assert s["tier_counts"]["commentary"] == 1  # the unresolved ref


def test_structure_unknown_tier_bucketed_commentary():
    evs = [_ev("a", tier="op-ed"), _ev("b", tier=None)]
    refs = [_ref("a"), _ref("b")]
    s = _compute_relationship_structure(refs, _index(evs), set())
    assert s["tier_counts"]["commentary"] == 2


def test_structure_empty_side():
    s = _compute_relationship_structure([], {}, set())
    assert s == {
        "count": 0,
        "distinct_domains": 0,
        "tier_counts": {"primary": 0, "reporting": 0, "commentary": 0},
        "derivation": {"originals": 0, "derivative_count": 0},
        "repetition": {"max_cluster_on_side": 0, "distinct_domains": 0},
    }


def test_structure_is_deterministic():
    evs = [_ev("a", tier="primary", derivation_chain=["b"]), _ev("b", tier="reporting")]
    refs = [_ref("a"), _ref("b")]
    idx = _index(evs)
    assert _compute_relationship_structure(refs, idx, {"b"}) == (
        _compute_relationship_structure(refs, idx, {"b"})
    )


# ── _compute_element_basis (integration of the structure into basis) ──────────


def test_element_basis_attaches_both_structures_split_by_side():
    evs = [
        _ev("a", url="https://gov.uk/r", tier="primary"),
        _ev("b", url="https://reuters.com/x", tier="reporting"),
        _ev("c", url="https://blog.com/z", tier="commentary"),
    ]
    elem = {
        "element_id": "e1",
        "evidence_refs": [
            _ref("a", "supports"),
            _ref("b", "supports"),
            _ref("c", "challenges"),
        ],
    }
    basis = _compute_element_basis(elem, evs)

    # New keys present and split correctly.
    assert basis["support_structure"]["count"] == 2
    assert basis["challenge_structure"]["count"] == 1
    assert basis["support_structure"]["tier_counts"]["primary"] == 1
    assert basis["challenge_structure"]["tier_counts"]["commentary"] == 1

    # No regression to existing keys.
    assert basis["evidence_count"] == 3
    assert basis["relationship_breakdown"] == {"supports": 2, "challenges": 1}
    assert basis["tier_breakdown"] == {"primary": 1, "reporting": 1, "commentary": 1}


def test_element_basis_empty_refs_still_has_structures():
    basis = _compute_element_basis({"element_id": "e1", "evidence_refs": []}, [])
    assert basis["evidence_count"] == 0
    assert basis["support_structure"]["count"] == 0
    assert basis["challenge_structure"]["count"] == 0


def test_element_basis_derivative_union_across_pool():
    """derivative_count keys off the union of all derivation chains in the
    pool, so a re-reporter is flagged even though the chain lives on the
    primary item."""
    evs = [
        _ev("a", url="https://gov.uk/r", tier="primary", derivation_chain=["b", "c"]),
        _ev("b", url="https://n1.com/x", tier="reporting"),
        _ev("c", url="https://n2.com/y", tier="commentary"),
    ]
    elem = {
        "element_id": "e1",
        "evidence_refs": [_ref("a"), _ref("b"), _ref("c")],
    }
    basis = _compute_element_basis(elem, evs)
    assert basis["support_structure"]["derivation"]["originals"] == 1
    assert basis["support_structure"]["derivation"]["derivative_count"] == 2


# ── Serialization (AC3): support_structure survives to the API response ───────


def test_support_structure_survives_claim_map_serialization():
    """The generic camelCase serializer must pass element basis (incl. the new
    support_structure) through to the API payload unchanged — no allow-list
    drop. Proves the field reaches both /checks and /r endpoints (shared
    serializer)."""
    from app.api.v1.response_builder import _claim_map_to_camel_case

    claim_map = {
        "claim_id": "c1",
        "normalised_claim": "x",
        "orientation": "Of 1 element examined, retrieved evidence predominantly supports it.",
        "elements": [
            {
                "element_id": "e1",
                "description": "d",
                "evidence_refs": [{"evidence_id": "a", "relationship": "supports"}],
                "state": "supported",
                "basis": {
                    "support_structure": {
                        "count": 3,
                        "distinct_domains": 1,
                        "tier_counts": {"primary": 0, "reporting": 0, "commentary": 3},
                        "derivation": {"originals": 1, "derivative_count": 2},
                    },
                    "challenge_structure": {
                        "count": 0,
                        "distinct_domains": 0,
                        "tier_counts": {"primary": 0, "reporting": 0, "commentary": 0},
                        "derivation": {"originals": 0, "derivative_count": 0},
                    },
                },
            }
        ],
    }

    out = _claim_map_to_camel_case(claim_map)
    elem = out["elements"][0]
    # basis is passed through; its inner keys are not recursively camelCased.
    assert "basis" in elem
    ss = elem["basis"]["support_structure"]
    assert ss["count"] == 3
    assert ss["distinct_domains"] == 1
    assert ss["derivation"]["derivative_count"] == 2
    assert elem["basis"]["challenge_structure"]["count"] == 0
