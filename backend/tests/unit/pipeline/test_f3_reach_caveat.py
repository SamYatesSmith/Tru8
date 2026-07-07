"""F3 Phase B2 — R-G2 reach caveat tests (2026-07-07).

Design: audit/2026-07-07_f3_design_review.md §7 (B2). When the mapper judges an
element's supporting evidence NARROWER than the element's own scope (emits
`scope_caveat` → `elem["scope_reach"]`) AND the tagger independently flagged a
composite-geography term (LLM ∧ lexicon agreement), a `supported` element gets a
descriptive reach caveat. State unchanged; describes the evidence's reach, never
re-scopes the claim (decision #7). Reach outranks the universal caveat when both
apply (more specific).
"""

from app.models.claim_map import ElementState
from app.pipeline.claim_map_analyzer import (
    _REACH_CAVEAT,
    _UNIVERSAL_CAVEAT,
    _derive_element_state_with_authority,
)


def _ev(eid, tier):
    return {"evidence_id": eid, "tier": tier, "url": f"http://{eid}.example.com"}


def _ref(eid, rel="supports"):
    return {"evidence_id": eid, "relationship": rel}


def _el(geographic=None, universal=None, reach=None, refs=None):
    return {
        "scope_flags": {"geographic": geographic or [], "universal": universal or []},
        "scope_reach": reach,
        "evidence_refs": refs if refs is not None else [_ref("a")],
    }


# ── Fires: geographic flag + mapper reach ────────────────────────────────────


def test_reach_caveat_fires_with_geographic_flag_and_reach():
    el = _el(geographic=["britain"], reach="England and Wales")
    state, basis = _derive_element_state_with_authority(el, [_ev("a", "reporting")])
    assert state == ElementState.supported  # unchanged
    assert (
        basis["caveat"] == "evidence covers England and Wales, narrower than 'Britain'"
    )
    assert basis["scope"]["trigger"] == "reach"
    assert basis["scope"]["reach"] == "England and Wales"


# ── Cross-gate: reach without a tagger geographic flag does NOT fire ──────────


def test_reach_ignored_without_geographic_flag():
    """LLM ∧ lexicon: a mapper reach with no composite-geography flag is
    distrusted (cuts LLM false positives)."""
    el = _el(geographic=[], universal=[], reach="England and Wales")
    _, basis = _derive_element_state_with_authority(el, [_ev("a", "reporting")])
    assert basis["caveat"] is None
    assert "scope" not in basis


def test_geographic_flag_without_reach_does_not_fire():
    """Tagger flag but the mapper returned no narrower reach (scope null)."""
    el = _el(geographic=["britain"], reach=None)
    _, basis = _derive_element_state_with_authority(el, [_ev("a", "reporting")])
    assert basis["caveat"] is None
    assert "scope" not in basis


# ── Priority: reach outranks universal; challenge outranks both ──────────────


def test_reach_outranks_universal_when_both_apply():
    el = _el(
        geographic=["united kingdom"],
        universal=["the only"],
        reach="England and Wales",
    )
    _, basis = _derive_element_state_with_authority(el, [_ev("a", "reporting")])
    assert basis["scope"]["trigger"] == "reach"
    assert basis["caveat"] != _UNIVERSAL_CAVEAT
    assert "narrower than 'the United Kingdom'" in basis["caveat"]


def test_reach_no_geo_falls_through_to_universal():
    el = _el(geographic=[], universal=["no other"], reach="England and Wales")
    _, basis = _derive_element_state_with_authority(el, [_ev("a", "reporting")])
    assert basis["caveat"] == _UNIVERSAL_CAVEAT
    assert basis["scope"]["trigger"] == "universal"


def test_challenge_caveat_outranks_reach():
    el = _el(
        geographic=["britain"],
        reach="England and Wales",
        refs=[_ref("a"), _ref("b"), _ref("c"), _ref("d", "challenges")],
    )
    evl = [
        _ev("a", "primary"),
        _ev("b", "reporting"),
        _ev("c", "reporting"),
        _ev("d", "commentary"),
    ]
    state, basis = _derive_element_state_with_authority(el, evl)
    assert state == ElementState.supported
    assert "disagree" in basis["caveat"]  # challenge caveat wins
    assert "scope" not in basis


# ── Only on supported ────────────────────────────────────────────────────────


def test_reach_does_not_fire_when_disputed():
    el = _el(
        geographic=["britain"],
        reach="England and Wales",
        refs=[_ref("a", "challenges"), _ref("b", "challenges")],
    )
    state, basis = _derive_element_state_with_authority(
        el, [_ev("a", "reporting"), _ev("b", "reporting")]
    )
    assert state == ElementState.disputed
    assert basis["caveat"] is None
    assert "scope" not in basis


# ── Display-term formatting (acronyms must not title-case to 'Uk'/'Usa') ─────


def test_display_term_acronyms():
    for term, disp in [
        ("usa", "the USA"),
        ("uk", "the UK"),
        ("eu", "the EU"),
        ("britain", "Britain"),
        ("europe", "Europe"),
        ("european union", "the European Union"),
    ]:
        el = _el(geographic=[term], reach="a region")
        _, basis = _derive_element_state_with_authority(el, [_ev("a", "reporting")])
        assert basis["caveat"] == f"evidence covers a region, narrower than '{disp}'"


def test_reach_template_constant_shape():
    assert (
        _REACH_CAVEAT.format(reach="X", term="Y")
        == "evidence covers X, narrower than 'Y'"
    )


# ── N2: echo guard — reach that just restates the scope term must not fire ────


def test_reach_echoing_scope_term_does_not_fire():
    for echo in ["Britain", "britain", "  BRITAIN "]:
        el = _el(geographic=["britain"], reach=echo)
        _, basis = _derive_element_state_with_authority(el, [_ev("a", "reporting")])
        assert basis["caveat"] is None, f"echo {echo!r} should be suppressed"
        assert "scope" not in basis


def test_reach_echoing_display_form_does_not_fire():
    # tagger term "uk" → display "the UK"; a mapper echoing "the UK"/"UK"/"uk".
    for echo in ["the UK", "UK", "uk"]:
        el = _el(geographic=["uk"], reach=echo)
        _, basis = _derive_element_state_with_authority(el, [_ev("a", "reporting")])
        assert basis["caveat"] is None, f"echo {echo!r} should be suppressed"


# ── N1: parse-path sentinel normalisation ("null"/"none" → None) ─────────────


def test_parse_normalises_scope_caveat_sentinels():
    from app.pipeline.claim_map_analyzer import ClaimMapAnalyzer
    from app.models.claim_map import ClaimElement

    analyzer = ClaimMapAnalyzer()
    claim_map = {
        "claim_id": "TRU-TEST",
        "elements": [
            ClaimElement(
                element_id="e1",
                description="d1",
                evidence_refs=[],
                state=None,
                uncertainty=None,
            ),
            ClaimElement(
                element_id="e2",
                description="d2",
                evidence_refs=[],
                state=None,
                uncertainty=None,
            ),
        ],
    }
    evidence = [{"evidence_id": "x1", "tier": "reporting", "url": "http://x.com"}]
    raw = {
        "elements": [
            {
                "element_id": "e1",
                "state": "supported",
                "scope_caveat": "null",
                "evidence_refs": [
                    {"evidence_id": "x1", "relationship": "supports", "reasoning": "r"}
                ],
            },
            {
                "element_id": "e2",
                "state": "supported",
                "scope_caveat": "England and Wales",
                "evidence_refs": [
                    {"evidence_id": "x1", "relationship": "supports", "reasoning": "r"}
                ],
            },
        ]
    }
    analyzer._parse_mapping_response(raw, claim_map, evidence)
    els = {e["element_id"]: e for e in claim_map["elements"]}
    assert els["e1"]["scope_reach"] is None  # "null" sentinel normalised
    assert els["e2"]["scope_reach"] == "England and Wales"
