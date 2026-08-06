"""Bench instrumentation for the F1 temporal scope gate (2026-08-06).

WHY THE BENCH NEEDED CHANGING AT ALL
------------------------------------
F1 shipped, passed the bench at 135/2/1, and had fired **zero times** — the
corpus contained no month-pinned claim, so the drift guard was blind to the only
class the gate acts on. Adding a fixture alone would not have fixed that: with no
matcher, the bench cannot see the gate, so a change that silently stopped it
firing would still report green.

The regex is pinned against the **exact** line `claim_map_analyzer.py` emits,
em dash included, rather than a sanitised reformatting of it.
"""

from scripts.replay_bench.capture import PipelineCaptureHandler, RE_TEMPORAL_SCOPE
from scripts.replay_bench.comparator import compare_hard_invariants


# The literal emission from ClaimMapAnalyzer._apply_temporal_scope.
LINE = "[TEMPORAL SCOPE] elem=e1: 3 ref(s) scoped to context — " "element pins 2024-09"


class TestRegex:
    def test_the_real_line_parses(self):
        m = RE_TEMPORAL_SCOPE.search(LINE)

        assert m is not None
        assert m.group("element") == "e1"
        assert m.group("scoped") == "3"
        assert m.group("period") == "2024-09"

    def test_an_unrelated_line_does_not_match(self):
        assert RE_TEMPORAL_SCOPE.search("[DOMAIN CAP] claim=0 domain=x") is None


class TestCapture:
    def _handler(self, *lines):
        h = PipelineCaptureHandler()
        for line in lines:
            h._dispatch(line)
        return h.observation().to_dict()

    def test_events_and_summary_are_recorded(self):
        obs = self._handler(
            LINE,
            "[TEMPORAL SCOPE] elem=e2: 1 ref(s) scoped to context — "
            "element pins 2024-09",
        )

        assert obs["temporal_scope_events"] == [
            {"element": "e1", "scoped": 3, "period": "2024-09"},
            {"element": "e2", "scoped": 1, "period": "2024-09"},
        ]
        assert obs["temporal_scope_summary"] == {"elements": 2, "scoped_refs": 4}

    def test_a_run_where_the_gate_never_fires_is_empty_not_absent(self):
        """The golden needs a readable zero, not a missing key."""
        obs = self._handler("nothing to do with the gate")

        assert obs["temporal_scope_events"] == []
        assert obs["temporal_scope_summary"] == {"elements": 0, "scoped_refs": 0}


class TestHardInvariant:
    """The point of the whole exercise: this must FAIL when the gate stops."""

    FIRED = {
        "temporal_scope_events": [{"element": "e1", "scoped": 3, "period": "2024-09"}]
    }
    SILENT = {"temporal_scope_events": []}

    def test_passes_when_the_gate_fires_on_the_expected_period(self):
        diffs = compare_hard_invariants(
            self.FIRED, {"temporal_scope_must_fire_on_periods": ["2024-09"]}
        )

        assert [d.level for d in diffs] == ["ok"]

    def test_fails_when_the_gate_never_fires(self):
        diffs = compare_hard_invariants(
            self.SILENT, {"temporal_scope_must_fire_on_periods": ["2024-09"]}
        )

        assert len(diffs) == 1
        assert diffs[0].is_failure()
        assert diffs[0].observed == "never fired"
        assert "settled facts can read as disputed" in diffs[0].message

    def test_fails_when_it_fires_on_a_different_period(self):
        """Firing somewhere else is not evidence it still works here."""
        diffs = compare_hard_invariants(
            {
                "temporal_scope_events": [
                    {"element": "e1", "scoped": 2, "period": "2025-06"}
                ]
            },
            {"temporal_scope_must_fire_on_periods": ["2024-09"]},
        )

        assert diffs[0].is_failure()
        assert "2025-06" in diffs[0].observed

    def test_the_check_is_skipped_when_the_golden_does_not_ask_for_it(self):
        """Every other corpus claim must be unaffected by this addition."""
        assert compare_hard_invariants(self.SILENT, {}) == []
