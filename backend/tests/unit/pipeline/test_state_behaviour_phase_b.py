"""Quality-first Phase B state behaviour (2026-08-17) — the tie, the floor,
and the uncertainty channel.

Three changes to `_derive_element_state_with_authority`, shipped together so
the corpus moves ONCE with attribution (design review I-1):

1. Strict `>` on BOTH dominant rules. TRU-018F-44AA's crux element sat at an
   exact 2× tie and `>=` handed it `supported`, overriding the LLM's own
   `disputed`. A tie is not dominance.
2. A factual support floor (`FACTUAL_MIN_WEIGHTED_SUPPORT`, weighted, default
   3): check 83120010 left an element `supported` off a single BBC reporting
   ref. One primary alone still suffices; a lone reporting/commentary ref no
   longer does. ⚠️ The design review's §5 nominal "floor 2" contradicted its
   own approved description — 2 would let a lone reporting ref (weight 2)
   pass. The DESCRIBED behaviour (3) is what shipped.
3. The mapper's element-level `uncertainty` reaches the caveat channel when
   the element reads `supported` — it used to reach only the print surface
   (TRU-018F-44AA e2's own uncertainty undercut its badge, invisibly).
"""

import pytest

from app.core.config import settings
from app.models.claim_map import ElementState
from app.pipeline.claim_map_analyzer import (
    _derive_element_state_with_authority,
    _state_floor_for,
)


def _ref(eid, rel):
    return {"evidence_id": eid, "relationship": rel}


def _evi(eid, tier):
    return {"evidence_id": eid, "tier": tier, "url": f"https://example.org/{eid}"}


# ---------------------------------------------------------------------------
# 1. The tie — strict `>` on both sides
# ---------------------------------------------------------------------------


class TestStrictDominance:
    def test_an_exact_2x_supports_tie_is_close_split_disputed(self):
        # 2 reporting supports (4) vs 1 reporting challenge (2): 4 > 4 false.
        elem = {
            "evidence_refs": [
                _ref("s1", "supports"),
                _ref("s2", "supports"),
                _ref("c1", "challenges"),
            ]
        }
        evi = [
            _evi("s1", "reporting"),
            _evi("s2", "reporting"),
            _evi("c1", "reporting"),
        ]
        state, basis = _derive_element_state_with_authority(elem, evi)
        assert state == ElementState.disputed
        assert basis["rule_applied"] == "close_split"

    def test_an_exact_2x_challenges_tie_is_close_split_not_dominant(self):
        """Symmetric same-commit change (invariant #7): on this side the state
        is `disputed` either way — only the recorded rule honestly changes."""
        elem = {
            "evidence_refs": [
                _ref("s1", "supports"),
                _ref("c1", "challenges"),
                _ref("c2", "challenges"),
            ]
        }
        evi = [
            _evi("s1", "reporting"),
            _evi("c1", "reporting"),
            _evi("c2", "reporting"),
        ]
        state, basis = _derive_element_state_with_authority(elem, evi)
        assert state == ElementState.disputed
        assert basis["rule_applied"] == "close_split"

    def test_strict_dominance_still_fires_past_the_tie(self):
        # 3 reporting supports (6) vs 1 commentary challenge (1): 6 > 2.
        elem = {
            "evidence_refs": [
                _ref("s1", "supports"),
                _ref("s2", "supports"),
                _ref("s3", "supports"),
                _ref("c1", "challenges"),
            ]
        }
        evi = [
            _evi("s1", "reporting"),
            _evi("s2", "reporting"),
            _evi("s3", "reporting"),
            _evi("c1", "commentary"),
        ]
        state, basis = _derive_element_state_with_authority(elem, evi)
        assert state == ElementState.supported
        assert basis["rule_applied"] == "supports_dominant_2x"

    def test_challenges_strictly_dominant_still_fires(self):
        elem = {
            "evidence_refs": [
                _ref("s1", "supports"),
                _ref("c1", "challenges"),
                _ref("c2", "challenges"),
            ]
        }
        evi = [_evi("s1", "commentary"), _evi("c1", "reporting"), _evi("c2", "primary")]
        state, basis = _derive_element_state_with_authority(elem, evi)
        assert state == ElementState.disputed
        assert basis["rule_applied"] == "challenges_dominant_2x"


# ---------------------------------------------------------------------------
# 2. The factual support floor
# ---------------------------------------------------------------------------


class TestFactualSupportFloor:
    def test_a_lone_reporting_support_no_longer_reads_supported(self):
        elem = {"evidence_refs": [_ref("s1", "supports")]}
        evi = [_evi("s1", "reporting")]
        state, basis = _derive_element_state_with_authority(
            elem, evi, 3, "support_floor"
        )
        assert state == ElementState.unresolved
        assert basis["rule_applied"] == "support_floor"

    def test_a_lone_primary_support_still_suffices(self):
        """A single primary source IS the record for many true claims."""
        elem = {"evidence_refs": [_ref("s1", "supports")]}
        evi = [_evi("s1", "primary")]
        state, basis = _derive_element_state_with_authority(
            elem, evi, 3, "support_floor"
        )
        assert state == ElementState.supported
        assert basis["rule_applied"] == "all_supports"

    def test_the_floor_never_touches_disputed(self):
        """Flooring a dispute away would HIDE disagreement — the sycophancy
        direction. The floor only guards the `supported` badge."""
        elem = {"evidence_refs": [_ref("c1", "challenges")]}
        evi = [_evi("c1", "commentary")]
        state, basis = _derive_element_state_with_authority(
            elem, evi, 3, "support_floor"
        )
        assert state == ElementState.disputed
        assert basis["rule_applied"] == "all_challenges"

    def test_state_floor_for_returns_the_factual_floor_and_rule(self):
        floor, rule = _state_floor_for({"metadata": {}})
        assert floor == int(getattr(settings, "FACTUAL_MIN_WEIGHTED_SUPPORT", 3))
        assert rule == "support_floor"

    def test_setting_zero_disables_the_floor(self, monkeypatch):
        monkeypatch.setattr(settings, "FACTUAL_MIN_WEIGHTED_SUPPORT", 0)
        floor, rule = _state_floor_for({"metadata": {}})
        assert floor == 0
        # And with floor 0 a lone reporting ref reads supported again.
        elem = {"evidence_refs": [_ref("s1", "supports")]}
        evi = [_evi("s1", "reporting")]
        state, _ = _derive_element_state_with_authority(elem, evi, floor, rule)
        assert state == ElementState.supported


# ---------------------------------------------------------------------------
# 3. Uncertainty reaches the caveat channel
# ---------------------------------------------------------------------------


class TestUncertaintyCaveat:
    def test_uncertainty_rides_the_caveat_channel_on_supported(self):
        elem = {
            "evidence_refs": [_ref("s1", "supports")],
            "uncertainty": (
                "evidence indicates at least 4 wars, but the claim specifies "
                "at least six"
            ),
        }
        evi = [_evi("s1", "primary")]
        state, basis = _derive_element_state_with_authority(elem, evi)
        assert state == ElementState.supported
        assert "at least six" in basis["caveat"]

    def test_uncertainty_appends_behind_a_disagreement_caveat(self):
        """Appended, never replacing — a disagreement caveat keeps priority."""
        elem = {
            "evidence_refs": [
                _ref("s1", "supports"),
                _ref("s2", "supports"),
                _ref("s3", "supports"),
                _ref("c1", "challenges"),
            ],
            "uncertainty": "coverage is thinner than the badge suggests",
        }
        evi = [
            _evi("s1", "primary"),
            _evi("s2", "primary"),
            _evi("s3", "primary"),
            _evi("c1", "commentary"),
        ]
        state, basis = _derive_element_state_with_authority(elem, evi)
        assert state == ElementState.supported
        assert "disagree" in basis["caveat"] or "example.org" in basis["caveat"]
        assert "thinner than the badge" in basis["caveat"]
        assert basis["caveat"].index("thinner") > 0  # rides behind, not instead

    def test_uncertainty_does_not_touch_disputed(self):
        """A disputed element already says what needs saying — the channel is
        for a `supported` badge the mapper itself hedged."""
        elem = {
            "evidence_refs": [_ref("c1", "challenges")],
            "uncertainty": "methodology contested",
        }
        evi = [_evi("c1", "primary")]
        state, basis = _derive_element_state_with_authority(elem, evi)
        assert state == ElementState.disputed
        assert basis["caveat"] is None
