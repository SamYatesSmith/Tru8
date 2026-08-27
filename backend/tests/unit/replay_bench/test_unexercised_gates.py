"""A must-fire gate assertion must distinguish "broken" from "trap absent".

WHY THIS EXISTS (2026-08-27)
---------------------------
The corpus re-record found `TRU-018F-44AA` reporting the interested-party gate
as FAILED. The gate was fine — 64 unit tests pass — but that draw's pool carried
no `whitehouse.gov`, so the gate was never given anything to scope. Live pools
churn ~62% between identical runs, so this is routine, and a check that reports
it as a failure cannot be told apart from a real break. Eleven such lines is how
a red bench stops being read at all.

The rule these tests pin:

    precondition ABSENT   -> "unexercised"  (not a failure)
    precondition PRESENT  -> "failure"      (the trap was there; nothing caught it)
    no precondition       -> "failure"      (old behaviour; silence never softens)

The second case is the one that must never regress: if softening the first case
ever swallows the second, the guard is gone and the bench would look healthier
for it.
"""

from scripts.replay_bench.comparator import (
    _check_scope_gates_fire,
    _check_temporal_scope,
    compare_tolerant_counters,
    unexercised_gate_counters,
)
from scripts.replay_bench.reporter import render_overall


PRECONDITION = {"interested_party": ["whitehouse.gov"]}


def _obs(domains, events=None):
    """`domains` is the FINAL pool — what reached mapping, which is all the gate sees."""
    obs = {"domain_set": list(domains), "url_ledger_flat": []}
    if events is not None:
        obs["interested_party_events"] = events
    return obs


# ---------------------------------------------------------------------------
# The gate boolean
# ---------------------------------------------------------------------------


def test_trap_absent_and_gate_silent_is_unexercised_not_failure():
    obs = _obs(["bbc.co.uk", "apnews.com"])
    (diff,) = _check_scope_gates_fire(obs, ["interested_party"], PRECONDITION)
    assert diff.level == "unexercised"
    assert not diff.is_failure()
    assert "NOT EXERCISED" in diff.message


def test_trap_present_but_gate_silent_is_still_a_hard_failure():
    """The whole point. The claimant's organ WAS in the pool and nothing caught it."""
    obs = _obs(["whitehouse.gov", "bbc.co.uk"])
    (diff,) = _check_scope_gates_fire(obs, ["interested_party"], PRECONDITION)
    assert diff.level == "failure"
    assert diff.is_failure()
    assert "stopped scoping" in diff.message


def test_gate_that_fired_is_ok_regardless_of_precondition():
    obs = _obs(["bbc.co.uk"], events=[{"element": "e1", "scoped": 2}])
    (diff,) = _check_scope_gates_fire(obs, ["interested_party"], PRECONDITION)
    assert diff.level == "ok"


def test_no_declared_precondition_keeps_the_old_hard_failure():
    """Silence must never soften a guard: an undeclared gate still fails."""
    obs = _obs(["bbc.co.uk"])
    (diff,) = _check_scope_gates_fire(obs, ["interested_party"], {})
    assert diff.level == "failure"


def test_empty_precondition_list_is_treated_as_cannot_tell_and_fails():
    obs = _obs(["bbc.co.uk"])
    (diff,) = _check_scope_gates_fire(
        obs, ["interested_party"], {"interested_party": []}
    )
    assert diff.level == "failure"


def test_precondition_matches_case_insensitively_and_inside_a_url():
    obs = _obs(["WWW.WhiteHouse.GOV"])
    (diff,) = _check_scope_gates_fire(obs, ["interested_party"], PRECONDITION)
    assert diff.level == "failure"  # trap present -> guard bites


def test_domain_set_alone_satisfies_the_precondition():
    obs = {
        "url_ledger_flat": [],
        "domain_set": ["whitehouse.gov"],
    }
    (diff,) = _check_scope_gates_fire(obs, ["interested_party"], PRECONDITION)
    assert diff.level == "failure"


# ---------------------------------------------------------------------------
# The temporal gate takes the same treatment
# ---------------------------------------------------------------------------


def test_temporal_gate_unexercised_when_no_off_period_source():
    obs = {"domain_set": ["ons.gov.uk"]}
    (diff,) = _check_temporal_scope(obs, ["2024-09"], ["gianlucabenigno.substack.com"])
    assert diff.level == "unexercised"


def test_temporal_gate_fails_when_the_off_period_source_is_present():
    obs = {"domain_set": ["gianlucabenigno.substack.com"]}
    (diff,) = _check_temporal_scope(obs, ["2024-09"], ["gianlucabenigno.substack.com"])
    assert diff.level == "failure"


# ---------------------------------------------------------------------------
# The counters that belong to an unexercised gate
# ---------------------------------------------------------------------------


def test_counters_follow_their_gate_into_unexercised():
    golden = {"hard_invariants": {"must_fire_preconditions": PRECONDITION}}
    obs = _obs(["bbc.co.uk"])
    names = unexercised_gate_counters(obs, golden)
    assert "interested_party_scoped_refs" in names
    assert "interested_party_scoped_elements" in names


def test_counters_do_not_follow_when_the_trap_was_present():
    golden = {"hard_invariants": {"must_fire_preconditions": PRECONDITION}}
    obs = _obs(["whitehouse.gov"])
    assert unexercised_gate_counters(obs, golden) == []


def test_counters_do_not_follow_when_the_gate_actually_fired():
    golden = {"hard_invariants": {"must_fire_preconditions": PRECONDITION}}
    obs = _obs(["bbc.co.uk"], events=[{"element": "e1", "scoped": 1}])
    assert unexercised_gate_counters(obs, golden) == []


def test_unexercised_counter_is_reported_never_silently_dropped():
    obs = {"interested_party_summary": {"scoped_refs": 0}}
    counters = {"interested_party_scoped_refs": {"value": 1, "tolerance": 0}}
    diffs = compare_tolerant_counters(
        obs, counters, unexercised=["interested_party_scoped_refs"]
    )
    assert len(diffs) == 1
    assert diffs[0].level == "unexercised"
    assert "NOT EXERCISED" in diffs[0].message


# ---------------------------------------------------------------------------
# Reporting — an unexercised guard must never read as a passing one
# ---------------------------------------------------------------------------


def test_unexercised_is_not_counted_as_ok_and_does_not_fail_the_run():
    obs = _obs(["bbc.co.uk"])
    diffs = _check_scope_gates_fire(obs, ["interested_party"], PRECONDITION)
    text, exit_code = render_overall([("TRU-TEST", diffs)])
    assert exit_code == 0  # does not fail the run
    assert "0 ok" in text  # and is NOT counted as a pass
    assert "UNEXERCISED" in text  # named loudly in the verdict
    assert "guard not tested this run" in text


def test_retrieved_but_dropped_before_mapping_does_NOT_count_as_the_trap():
    """The bug this mechanism shipped with, pinned.

    On the 2026-08-27 recording of TRU-018F-44AA, whitehouse.gov was fetched (a
    National Security Strategy PDF) but never reached the final pool. The gate
    therefore saw nothing. Reading `url_ledger_flat` called the trap "present"
    and reported a hard failure for a gate that was never given a chance.
    """
    obs = {
        "url_ledger_flat": ["https://www.whitehouse.gov/wp-content/2025-NSS.pdf"],
        "domain_set": ["bbc.co.uk", "apnews.com"],
    }
    (diff,) = _check_scope_gates_fire(obs, ["interested_party"], PRECONDITION)
    assert diff.level == "unexercised"
