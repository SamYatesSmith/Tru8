"""Bench instrumentation for the four non-temporal scope gates (2026-08-17).

WHY THE BENCH NEEDED CHANGING AT ALL
------------------------------------
All five scope gates share one driver and emit an identically shaped log line,
but the bench parsed only [TEMPORAL SCOPE] — so jurisdiction, measure,
interested-party and recital had receipts and NO drift signal. A change that
silently stopped one firing would still show green: the exact blindness F1's
matcher exists to prevent (interaction I-6 of the 2026-08-14 design review),
now closed for the other four.

The regexes are pinned against the **exact** lines `claim_map_analyzer.py`
emits (shared driver at `_apply_scope_gates`), em dash and pins text included.
"""

from scripts.replay_bench.capture import (
    RE_SCOPE_GATE,
    RE_TEMPORAL_SCOPE,
    SCOPE_GATE_KEYS,
    PipelineCaptureHandler,
)
from scripts.replay_bench.comparator import (
    compare_hard_invariants,
    compare_tolerant_counters,
)


# The literal emissions from ClaimMapAnalyzer._apply_scope_gates, one per gate,
# pins text as each gate builds it.
JURISDICTION_LINE = (
    "[JURISDICTION SCOPE] elem=e2: 1 ref(s) scoped to context — claim pins GB"
)
MEASURE_LINE = (
    "[MEASURE SCOPE] elem=e1: 2 ref(s) scoped to context — "
    "element measures the interval ending 2024-09"
)
INTERESTED_PARTY_LINE = (
    "[INTERESTED PARTY] elem=e4: 2 ref(s) scoped to context — "
    "claim subjects: donald trump, white house"
)
RECITAL_LINE = (
    "[RECITAL] elem=e4: 4 ref(s) scoped to context — "
    "reference rests on the claim being made, not established"
)
TEMPORAL_LINE = (
    "[TEMPORAL SCOPE] elem=e1: 3 ref(s) scoped to context — element pins 2024-09"
)


class TestRegex:
    def test_all_four_real_lines_parse_to_their_basis_keys(self):
        for line, key, element, scoped in (
            (JURISDICTION_LINE, "jurisdiction_scope", "e2", "1"),
            (MEASURE_LINE, "measure_scope", "e1", "2"),
            (INTERESTED_PARTY_LINE, "interested_party", "e4", "2"),
            (RECITAL_LINE, "recital_scope", "e4", "4"),
        ):
            m = RE_SCOPE_GATE.search(line)

            assert m is not None, line
            assert SCOPE_GATE_KEYS[m.group("label")] == key
            assert m.group("element") == element
            assert m.group("scoped") == scoped

    def test_the_temporal_line_is_not_claimed_by_the_generic_matcher(self):
        """Temporal keeps its own matcher and golden vocabulary — a line that
        matched both would count the same firing twice."""
        assert RE_SCOPE_GATE.search(TEMPORAL_LINE) is None
        assert RE_TEMPORAL_SCOPE.search(JURISDICTION_LINE) is None

    def test_an_unrelated_line_does_not_match(self):
        assert RE_SCOPE_GATE.search("[DOMAIN CAP] claim=0 domain=x") is None


class TestCapture:
    def _handler(self, *lines):
        h = PipelineCaptureHandler()
        for line in lines:
            h._dispatch(line)
        return h.observation().to_dict()

    def test_events_and_summaries_are_recorded_per_gate(self):
        obs = self._handler(
            INTERESTED_PARTY_LINE,
            RECITAL_LINE,
            "[RECITAL] elem=e1: 1 ref(s) scoped to context — "
            "reference rests on the claim being made, not established",
        )

        assert obs["interested_party_events"] == [{"element": "e4", "scoped": 2}]
        assert obs["interested_party_summary"] == {"elements": 1, "scoped_refs": 2}
        assert obs["recital_scope_events"] == [
            {"element": "e4", "scoped": 4},
            {"element": "e1", "scoped": 1},
        ]
        assert obs["recital_scope_summary"] == {"elements": 2, "scoped_refs": 5}

    def test_a_run_where_a_gate_never_fires_is_zero_not_absent(self):
        """The golden needs a readable zero, not a missing key — this is also
        what lets a tolerant counter assert 0 at tolerance 0."""
        obs = self._handler("nothing to do with any gate")

        for key in SCOPE_GATE_KEYS.values():
            assert obs[f"{key}_events"] == []
            assert obs[f"{key}_summary"] == {"elements": 0, "scoped_refs": 0}

    def test_temporal_events_are_untouched_by_the_new_matcher(self):
        obs = self._handler(TEMPORAL_LINE, MEASURE_LINE)

        assert obs["temporal_scope_summary"] == {"elements": 1, "scoped_refs": 3}
        assert obs["measure_scope_summary"] == {"elements": 1, "scoped_refs": 2}


class TestHardInvariant:
    """The point of the whole exercise: this must FAIL when a gate stops."""

    FIRED = {
        "interested_party_events": [{"element": "e4", "scoped": 2}],
        "recital_scope_events": [{"element": "e4", "scoped": 4}],
    }
    SILENT = {"interested_party_events": [], "recital_scope_events": []}

    def test_passes_when_the_named_gates_fire(self):
        diffs = compare_hard_invariants(
            self.FIRED,
            {"scope_gates_must_fire": ["interested_party", "recital_scope"]},
        )

        assert [d.level for d in diffs] == ["ok", "ok"]

    def test_fails_per_gate_when_one_stops_firing(self):
        diffs = compare_hard_invariants(
            {
                "interested_party_events": [{"element": "e4", "scoped": 2}],
                "recital_scope_events": [],
            },
            {"scope_gates_must_fire": ["interested_party", "recital_scope"]},
        )

        assert [d.level for d in diffs] == ["ok", "failure"]
        assert diffs[1].observed == "never fired"
        assert "press recitals" in diffs[1].message

    def test_the_failure_names_the_users_stake_not_just_the_gate(self):
        diffs = compare_hard_invariants(
            self.SILENT, {"scope_gates_must_fire": ["interested_party"]}
        )

        assert diffs[0].is_failure()
        assert "claimant's own organ" in diffs[0].message

    def test_the_check_is_skipped_when_the_golden_does_not_ask_for_it(self):
        """Every existing corpus claim must be unaffected by this addition."""
        assert compare_hard_invariants(self.SILENT, {}) == []


class TestTolerantCounter:
    """The summary keys are addressable as counters, same as temporal."""

    def test_scoped_refs_counter_at_tolerance_zero(self):
        obs = {"recital_scope_summary": {"elements": 2, "scoped_refs": 5}}
        diffs = compare_tolerant_counters(
            obs, {"recital_scoped_refs": {"value": 5, "tolerance": 0}}
        )

        assert [d.level for d in diffs] == ["ok"]

    def test_drift_beyond_tolerance_fails(self):
        obs = {"recital_scope_summary": {"elements": 0, "scoped_refs": 0}}
        diffs = compare_tolerant_counters(
            obs, {"recital_scoped_refs": {"value": 5, "tolerance": 1}}
        )

        assert diffs[0].is_failure()
