"""Tests for V1 Step 5 — V3 bench instrumentation.

Covers three new matchers in capture.py and the matching hard invariants
in comparator.py + defaults seeded by golden_io.derive_default_golden:

  - [B3 QUALITY] per-claim quality signals (runner.py:2442-2451)
  - [DOMAIN CAP] per-claim demote + total summary (runner.py:284-289 / 2428)
  - [COVERAGE RECOVERY] Timed out (runner.py:2337)

Real-line text drawn from runner.py emission format, so the regexes pin
against the exact format the pipeline writes, not against a sanitised
reformatting. Bench instability item TRU-B4A3-C42D is deliberately NOT
exercised here — it's a corpus-level provider-variance issue, not a
matcher correctness issue.
"""

from scripts.replay_bench.capture import (
    PipelineCaptureHandler,
    RE_B3_QUALITY,
    RE_COVERAGE_RECOVERY_TIMEOUT,
    RE_DOMAIN_CAP_DEMOTE,
    RE_DOMAIN_CAP_TOTAL,
)
from scripts.replay_bench.comparator import compare_hard_invariants, Diff
from scripts.replay_bench.golden_io import derive_default_golden


# --------------------------------------------------------------------------- #
# Regex parsing
# --------------------------------------------------------------------------- #


class TestB3QualityRegex:
    """Exact runner.py line shape must parse cleanly."""

    LINE = (
        "[B3 QUALITY] claim=0 mapped=11 unique_domains=8 "
        "top_domain=ons.gov.uk@27% wikipedia=15% "
        "factual_weight=42% element_resolution=66% "
        "tier_mix={'primary': 5, 'reporting': 4, 'commentary': 2} "
        "type_mix={'data': 3, 'official_statement': 2, 'news_reporting': 4, 'analysis': 2}"
    )

    def test_top_level_fields(self):
        m = RE_B3_QUALITY.search(self.LINE)
        assert m is not None
        assert m.group("claim") == "0"
        assert m.group("mapped") == "11"
        assert m.group("unique_domains") == "8"
        assert m.group("top_domain") == "ons.gov.uk"
        assert m.group("top_share") == "27"
        assert m.group("wikipedia") == "15"
        assert m.group("factual_weight") == "42"
        assert m.group("element_resolution") == "66"

    def test_dict_groups_capture_full_braces(self):
        m = RE_B3_QUALITY.search(self.LINE)
        assert m.group("tier_mix").startswith("{")
        assert m.group("tier_mix").endswith("}")
        assert "'primary': 5" in m.group("tier_mix")
        assert m.group("type_mix").startswith("{")
        assert "'data': 3" in m.group("type_mix")

    def test_top_domain_with_dashes_and_subdomains(self):
        line = (
            "[B3 QUALITY] claim=1 mapped=4 unique_domains=4 "
            "top_domain=some-sub.example.co.uk@25% wikipedia=0% "
            "factual_weight=0% element_resolution=50% "
            "tier_mix={} type_mix={}"
        )
        m = RE_B3_QUALITY.search(line)
        assert m is not None
        assert m.group("top_domain") == "some-sub.example.co.uk"


class TestDomainCapRegexes:

    def test_demote_line_parses(self):
        line = "[DOMAIN CAP] claim=2 domain=wikipedia.org pre_pr_share=48% post_pr_share=33% demoted=4"
        m = RE_DOMAIN_CAP_DEMOTE.search(line)
        assert m is not None
        assert m.group("claim") == "2"
        assert m.group("domain") == "wikipedia.org"
        assert m.group("pre") == "48"
        assert m.group("post") == "33"
        assert m.group("demoted") == "4"

    def test_demote_line_does_not_match_total_line(self):
        line = "[DOMAIN CAP] total demoted across all claims: 6"
        assert RE_DOMAIN_CAP_DEMOTE.search(line) is None

    def test_total_line_parses(self):
        line = "[DOMAIN CAP] total demoted across all claims: 6"
        m = RE_DOMAIN_CAP_TOTAL.search(line)
        assert m is not None
        assert m.group("total") == "6"

    def test_total_line_does_not_match_demote_pattern(self):
        line = (
            "[DOMAIN CAP] claim=0 domain=x pre_pr_share=40% post_pr_share=33% demoted=1"
        )
        assert RE_DOMAIN_CAP_TOTAL.search(line) is None


class TestCoverageRecoveryTimeoutRegex:

    def test_typical_line(self):
        m = RE_COVERAGE_RECOVERY_TIMEOUT.search(
            "[COVERAGE RECOVERY] Timed out after 28s"
        )
        assert m is not None
        assert m.group("seconds") == "28"

    def test_does_not_match_completion_line(self):
        line = "[COVERAGE RECOVERY] Complete: 2 claims recovered, 3 elements resolved, 4.5s elapsed"
        assert RE_COVERAGE_RECOVERY_TIMEOUT.search(line) is None


# --------------------------------------------------------------------------- #
# Handler dispatch — wired path: log message → matcher → Observation
# --------------------------------------------------------------------------- #


class TestHandlerDispatch:
    """Drive the public handler API the way the runner does: pass message
    strings into _dispatch, then assert against handler.observation()."""

    def test_b3_quality_routes_to_per_claim_dict(self):
        h = PipelineCaptureHandler()
        h._dispatch(
            "[B3 QUALITY] claim=0 mapped=11 unique_domains=8 "
            "top_domain=ons.gov.uk@27% wikipedia=15% "
            "factual_weight=42% element_resolution=66% "
            "tier_mix={'primary': 5} type_mix={'data': 3}"
        )
        obs = h.observation()
        assert 0 in obs.b3_quality_per_claim
        rec = obs.b3_quality_per_claim[0]
        assert rec["mapped"] == 11
        assert rec["unique_domains"] == 8
        assert rec["top_domain"] == "ons.gov.uk"
        assert rec["top_domain_share"] == 0.27
        assert rec["wikipedia_share"] == 0.15
        assert rec["factual_weight_share"] == 0.42
        assert rec["element_resolution"] == 0.66
        assert rec["tier_mix"] == {"primary": 5}
        assert rec["type_mix"] == {"data": 3}

    def test_b3_quality_accumulates_multiple_claims(self):
        h = PipelineCaptureHandler()
        for pos in (0, 1, 2):
            h._dispatch(
                f"[B3 QUALITY] claim={pos} mapped=3 unique_domains=4 "
                f"top_domain=x.com@20% wikipedia=10% "
                f"factual_weight=30% element_resolution=50% "
                f"tier_mix={{}} type_mix={{}}"
            )
        obs = h.observation()
        assert set(obs.b3_quality_per_claim.keys()) == {0, 1, 2}

    def test_domain_cap_demote_appends_event(self):
        h = PipelineCaptureHandler()
        h._dispatch(
            "[DOMAIN CAP] claim=2 domain=wikipedia.org "
            "pre_pr_share=48% post_pr_share=33% demoted=4"
        )
        obs = h.observation()
        assert len(obs.domain_cap_events) == 1
        evt = obs.domain_cap_events[0]
        assert evt["claim"] == 2
        assert evt["domain"] == "wikipedia.org"
        assert evt["pre_pr_share"] == 0.48
        assert evt["post_pr_share"] == 0.33
        assert evt["demoted"] == 4

    def test_domain_cap_total_sets_field(self):
        h = PipelineCaptureHandler()
        h._dispatch("[DOMAIN CAP] total demoted across all claims: 6")
        assert h.observation().domain_cap_total == 6

    def test_domain_cap_total_with_demote_lines_present(self):
        """Both lines should coexist — demote events recorded AND total set."""
        h = PipelineCaptureHandler()
        h._dispatch(
            "[DOMAIN CAP] claim=0 domain=a.com pre_pr_share=40% post_pr_share=33% demoted=1"
        )
        h._dispatch(
            "[DOMAIN CAP] claim=1 domain=b.com pre_pr_share=50% post_pr_share=34% demoted=3"
        )
        h._dispatch("[DOMAIN CAP] total demoted across all claims: 4")
        obs = h.observation()
        assert len(obs.domain_cap_events) == 2
        assert obs.domain_cap_total == 4

    def test_coverage_recovery_timeout_sets_flag_and_seconds(self):
        h = PipelineCaptureHandler()
        h._dispatch("[COVERAGE RECOVERY] Timed out after 28s")
        obs = h.observation()
        assert obs.coverage_recovery_timed_out is True
        assert obs.coverage_recovery_timeout_seconds == 28

    def test_coverage_recovery_timeout_not_set_on_completion(self):
        h = PipelineCaptureHandler()
        h._dispatch(
            "[COVERAGE RECOVERY] Complete: 2 claims recovered, "
            "3 elements resolved, 4.5s elapsed"
        )
        obs = h.observation()
        assert obs.coverage_recovery_timed_out is False
        assert obs.coverage_recovery_timeout_seconds is None

    def test_to_dict_exposes_new_fields(self):
        h = PipelineCaptureHandler()
        h._dispatch(
            "[B3 QUALITY] claim=0 mapped=3 unique_domains=4 "
            "top_domain=x@20% wikipedia=10% factual_weight=30% "
            "element_resolution=50% tier_mix={} type_mix={}"
        )
        h._dispatch(
            "[DOMAIN CAP] claim=0 domain=x pre_pr_share=40% post_pr_share=33% demoted=1"
        )
        h._dispatch("[COVERAGE RECOVERY] Timed out after 28s")
        d = h.observation().to_dict()
        assert "b3_quality_per_claim" in d
        assert "domain_cap_events" in d
        assert "domain_cap_total" in d
        assert "coverage_recovery_timed_out" in d
        assert "coverage_recovery_timeout_seconds" in d
        # Per-claim dict is string-keyed for JSON stability with the existing
        # url_ledger_per_claim shape.
        assert "0" in d["b3_quality_per_claim"]


# --------------------------------------------------------------------------- #
# V3 hard invariants — Poor floor (FAIL), Mediocre warn-band (WARN)
# --------------------------------------------------------------------------- #


def _obs_with_claim_quality(**signals):
    """Build a minimal observation dict with one claim's B3 QUALITY data."""
    base = {
        "mapped": 5,
        "unique_domains": 10,
        "top_domain": "x.com",
        "top_domain_share": 0.20,
        "wikipedia_share": 0.10,
        "factual_weight_share": 0.40,
        "element_resolution": 0.70,
        "tier_mix": {},
        "type_mix": {},
    }
    base.update(signals)
    return {"b3_quality_per_claim": {"0": base}}


POOR_FLOORS = {
    "unique_domains_min": 5,
    "top_domain_share_max": 0.45,
    "wikipedia_share_max": 0.40,
    "factual_weight_share_min": 0.15,
    "element_resolution_min": 0.30,
}

MEDIOCRE_BAND = {
    "unique_domains_min": 7,
    "top_domain_share_max": 0.30,
    "wikipedia_share_max": 0.25,
    "factual_weight_share_min": 0.25,
    "element_resolution_min": 0.50,
}


def _diffs_for_signal(diffs, signal_substr):
    return [d for d in diffs if signal_substr in d.signal]


class TestV3QualityFloors:

    def test_good_claim_all_ok(self):
        obs = _obs_with_claim_quality()
        diffs = compare_hard_invariants(
            obs,
            {"v3_quality_floors": POOR_FLOORS, "v3_quality_warn_band": MEDIOCRE_BAND},
        )
        v3 = [d for d in diffs if d.signal.startswith("v3:")]
        assert len(v3) >= 5
        assert all(d.level == "ok" for d in v3), [
            (d.signal, d.level, d.message) for d in v3 if d.level != "ok"
        ]

    def test_unique_domains_below_poor_fails(self):
        obs = _obs_with_claim_quality(unique_domains=3)
        diffs = compare_hard_invariants(
            obs,
            {"v3_quality_floors": POOR_FLOORS, "v3_quality_warn_band": MEDIOCRE_BAND},
        )
        ud = _diffs_for_signal(diffs, "v3:unique_domains")
        assert len(ud) == 1
        assert ud[0].level == "failure"
        assert "below Poor floor" in ud[0].message

    def test_unique_domains_mediocre_band_warns(self):
        obs = _obs_with_claim_quality(unique_domains=6)
        diffs = compare_hard_invariants(
            obs,
            {"v3_quality_floors": POOR_FLOORS, "v3_quality_warn_band": MEDIOCRE_BAND},
        )
        ud = _diffs_for_signal(diffs, "v3:unique_domains")
        assert ud[0].level == "warning"
        assert "drifting toward Poor" in ud[0].message

    def test_wikipedia_share_above_poor_fails(self):
        obs = _obs_with_claim_quality(wikipedia_share=0.48)
        diffs = compare_hard_invariants(obs, {"v3_quality_floors": POOR_FLOORS})
        wiki = _diffs_for_signal(diffs, "v3:wikipedia_share")
        assert wiki[0].level == "failure"
        assert "above Poor cap" in wiki[0].message

    def test_wikipedia_share_mediocre_band_warns(self):
        obs = _obs_with_claim_quality(wikipedia_share=0.30)
        diffs = compare_hard_invariants(
            obs,
            {"v3_quality_floors": POOR_FLOORS, "v3_quality_warn_band": MEDIOCRE_BAND},
        )
        wiki = _diffs_for_signal(diffs, "v3:wikipedia_share")
        assert wiki[0].level == "warning"

    def test_top_domain_share_above_poor_fails(self):
        obs = _obs_with_claim_quality(top_domain_share=0.50)
        diffs = compare_hard_invariants(obs, {"v3_quality_floors": POOR_FLOORS})
        td = _diffs_for_signal(diffs, "v3:top_domain_share")
        assert td[0].level == "failure"

    def test_factual_weight_below_poor_fails(self):
        obs = _obs_with_claim_quality(factual_weight_share=0.10)
        diffs = compare_hard_invariants(obs, {"v3_quality_floors": POOR_FLOORS})
        fw = _diffs_for_signal(diffs, "v3:factual_weight_share")
        assert fw[0].level == "failure"

    def test_element_resolution_below_poor_fails(self):
        obs = _obs_with_claim_quality(element_resolution=0.20)
        diffs = compare_hard_invariants(obs, {"v3_quality_floors": POOR_FLOORS})
        er = _diffs_for_signal(diffs, "v3:element_resolution")
        assert er[0].level == "failure"

    def test_no_b3_quality_data_yields_no_v3_diffs(self):
        """If a pipeline run produced no [B3 QUALITY] lines (e.g. no claim
        had any evidence), the V3 check should not invent diffs."""
        diffs = compare_hard_invariants(
            {"b3_quality_per_claim": {}}, {"v3_quality_floors": POOR_FLOORS}
        )
        assert [d for d in diffs if d.signal.startswith("v3:")] == []

    def test_multiple_claims_each_checked(self):
        obs = {
            "b3_quality_per_claim": {
                "0": {**_obs_with_claim_quality()["b3_quality_per_claim"]["0"]},
                "1": {
                    "mapped": 2,
                    "unique_domains": 3,  # FAIL
                    "top_domain": "x.com",
                    "top_domain_share": 0.50,  # FAIL
                    "wikipedia_share": 0.10,
                    "factual_weight_share": 0.40,
                    "element_resolution": 0.70,
                    "tier_mix": {},
                    "type_mix": {},
                },
            }
        }
        diffs = compare_hard_invariants(obs, {"v3_quality_floors": POOR_FLOORS})
        failures = [
            d for d in diffs if d.level == "failure" and d.signal.startswith("v3:")
        ]
        # Claim 0 is Good; Claim 1 should produce two failures.
        assert all("claim=1" in d.signal for d in failures)
        assert len(failures) == 2


class TestCoverageRecoveryMustNotTimeout:

    def test_timeout_observed_fails(self):
        diffs = compare_hard_invariants(
            {
                "coverage_recovery_timed_out": True,
                "coverage_recovery_timeout_seconds": 28,
            },
            {"coverage_recovery_must_not_timeout": True},
        )
        relevant = [d for d in diffs if d.signal == "coverage_recovery_timed_out"]
        assert len(relevant) == 1
        assert relevant[0].level == "failure"
        assert "Bug B regression" in relevant[0].message

    def test_no_timeout_passes(self):
        diffs = compare_hard_invariants(
            {"coverage_recovery_timed_out": False},
            {"coverage_recovery_must_not_timeout": True},
        )
        relevant = [d for d in diffs if d.signal == "coverage_recovery_timed_out"]
        assert relevant[0].level == "ok"

    def test_invariant_off_means_no_diff_emitted(self):
        diffs = compare_hard_invariants(
            {"coverage_recovery_timed_out": True},
            {"coverage_recovery_must_not_timeout": False},
        )
        assert [d for d in diffs if d.signal == "coverage_recovery_timed_out"] == []


# --------------------------------------------------------------------------- #
# derive_default_golden — V3 defaults seeded with V1 plan thresholds
# --------------------------------------------------------------------------- #


class TestDeriveDefaultGoldenV3:

    def test_includes_v3_quality_floors_from_v1_plan(self):
        golden = derive_default_golden("TRU-TEST", {})
        floors = golden["hard_invariants"]["v3_quality_floors"]
        assert floors == {
            "unique_domains_min": 5,
            "top_domain_share_max": 0.45,
            "wikipedia_share_max": 0.40,
            "factual_weight_share_min": 0.15,
            "element_resolution_min": 0.30,
        }

    def test_includes_v3_warn_band(self):
        golden = derive_default_golden("TRU-TEST", {})
        band = golden["hard_invariants"]["v3_quality_warn_band"]
        assert band == {
            "unique_domains_min": 7,
            "top_domain_share_max": 0.30,
            "wikipedia_share_max": 0.25,
            "factual_weight_share_min": 0.25,
            "element_resolution_min": 0.50,
        }

    def test_sets_coverage_recovery_must_not_timeout(self):
        golden = derive_default_golden("TRU-TEST", {})
        assert golden["hard_invariants"]["coverage_recovery_must_not_timeout"] is True

    def test_v3_defaults_do_not_depend_on_observation_values(self):
        """The Poor floor must be universal, not snapshotted from today's run."""
        obs_a = {"b3_quality_per_claim": {"0": {"unique_domains": 100}}}
        obs_b = {"b3_quality_per_claim": {"0": {"unique_domains": 3}}}
        ga = derive_default_golden("A", obs_a)
        gb = derive_default_golden("B", obs_b)
        assert (
            ga["hard_invariants"]["v3_quality_floors"]
            == gb["hard_invariants"]["v3_quality_floors"]
        )
