"""Tests for `scripts/cost_report.py` — the per-check cost reader.

The report's job is to be TRUSTED, so the tests concentrate on the ways a cost
report can lie rather than on its formatting:

  * an un-instrumented check must read as UNKNOWN, never as free — a silent zero
    would say "search is costless", the opposite of true, and it would do so
    while looking like a measurement;
  * a partial figure must never be summed into a total that reads as complete;
  * the margin line must not be moved by one pathological check;
  * per-stage cost must be priced at the model that stage actually used, or the
    F4b question ("are two mapping stages quietly on the cheap model?") gets a
    confidently wrong answer.

Prices come from `app.core.cost_constants` and are UNVERIFIED placeholders, so
nothing here asserts an absolute currency amount that would break the moment the
founder sets real rates from an invoice. The assertions are on RELATIONSHIPS —
this is dearer than that, this is excluded, this is None — which survive a
reprice.
"""

import pytest

from app.core.cost_constants import SEARCH_PRICING_USD_PER_UNIT
from scripts.cost_report import (
    CONSOLE_REVENUE_PENCE_PER_CHECK,
    _margins,
    _percentile,
    _spread,
    _stage_cost_usd,
    build_report,
    render,
    row_costs,
)


def telemetry(
    *,
    input_tokens=1000,
    output_tokens=500,
    by_stage=None,
    units=None,
    queries=None,
    calls=3,
    pricing_version="2026-06-15-UNVERIFIED",
):
    """A cost_telemetry blob shaped like the one build_cost_telemetry writes.

    `units=None` reproduces a pre-2026-08-03 row: the search meter did not exist,
    so `(search_meter or {}).get(...)` wrote None into every measured field.
    """
    return {
        "pricing_version": pricing_version,
        "llm": {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "calls": calls,
            "by_stage": by_stage,
        },
        "search": {
            "queries_by_provider": queries,
            "billable_units_by_provider": units,
            "total_queries": sum((queries or {}).values()) if queries else None,
            "total_billable_units": sum(units.values()) if units else None,
        },
        "timing": {"wall_time_ms": 60000},
    }


def row(*, status="completed", tier="full", client=None, **kw):
    return {
        "status": status,
        "executed_tier": tier,
        "client": client,
        "cost_telemetry": telemetry(**kw),
    }


class TestUnmeteredChecksReadAsUnknown:
    """The single most important property: absence must not print as zero."""

    def test_search_cost_is_none_not_zero_when_the_meter_never_ran(self):
        c = row_costs(telemetry(units=None))
        assert c["search_usd"] is None, "an un-metered check must not read as free"
        assert c["metered"] is False

    def test_total_is_none_when_search_is_unknown(self):
        # A partial sum here would present an LLM-only figure as the cost of a
        # check, which is exactly the misreading the field note warns about.
        c = row_costs(telemetry(units=None))
        assert c["total_usd"] is None

    def test_a_metered_check_that_issued_no_searches_costs_zero_not_unknown(self):
        # Distinct from the case above: the meter RAN and counted nothing, so
        # zero is a measurement, not an absence.
        c = row_costs(telemetry(units={}))
        assert c["metered"] is True
        assert c["search_usd"] == 0.0
        assert c["total_usd"] == c["llm_usd"]

    def test_unmetered_rows_are_counted_but_excluded_from_search_and_total(self):
        rows = [
            row(units={"serper": 10}),
            row(units=None),
            row(units=None),
        ]
        r = build_report(rows, gbp_usd=1.28)
        assert r["counts"]["checks_with_telemetry"] == 3
        assert r["counts"]["metered_for_search"] == 1
        assert r["counts"]["unmetered_for_search"] == 2
        # LLM cost is knowable for all three; search and total only for the one.
        assert r["pence_per_check"]["llm_partial"]["n"] == 3
        assert r["pence_per_check"]["search"]["n"] == 1
        assert r["pence_per_check"]["total_partial"]["n"] == 1

    def test_the_exclusion_is_stated_in_the_output(self):
        out = render(build_report([row(units={"serper": 4}), row(units=None)], 1.28))
        assert "predate" in out and "not counted as zero" in out


class TestSearchPricing:
    def test_billable_units_drive_the_cost_not_query_count(self):
        # Serper bills 2 credits for 11-100 results and the claim lane asks for
        # 13, so pricing off queries would understate spend by nearly half.
        cheap = row_costs(telemetry(units={"serper": 6}, queries={"serper": 6}))
        dear = row_costs(telemetry(units={"serper": 12}, queries={"serper": 6}))
        assert dear["search_usd"] == pytest.approx(2 * cheap["search_usd"])

    def test_providers_are_priced_at_their_own_rate(self):
        serper = row_costs(telemetry(units={"serper": 10}))["search_usd"]
        serpapi = row_costs(telemetry(units={"serpapi": 10}))["search_usd"]
        assert (
            SEARCH_PRICING_USD_PER_UNIT["serpapi"]
            > SEARCH_PRICING_USD_PER_UNIT["serper"]
        )
        assert serpapi > serper

    def test_provider_totals_aggregate_across_metered_rows_only(self):
        rows = [
            row(units={"serper": 10}, queries={"serper": 6}),
            row(units={"serper": 4, "brave": 2}, queries={"serper": 3, "brave": 2}),
            row(units=None, queries=None),
        ]
        r = build_report(rows, 1.28)
        by = {p["provider"]: p for p in r["search_providers"]}
        assert by["serper"]["billable_units"] == 14
        assert by["serper"]["queries"] == 9
        assert by["brave"]["billable_units"] == 2

    def test_the_serper_double_charge_is_explained_when_it_shows(self):
        out = render(
            build_report([row(units={"serper": 12}, queries={"serper": 6})], 1.28)
        )
        assert "2 credits" in out


class TestStageAttribution:
    def test_a_stage_is_priced_at_the_model_it_used(self):
        # The whole point of the F4b question: the same tokens cost different
        # money depending which model ran them, so a stage priced at the default
        # would hide a stage quietly running on something dearer.
        flash = {
            "input_tokens": 100_000,
            "output_tokens": 10_000,
            "models_used": {"a": "gemini-2.5-flash"},
        }
        lite = {
            "input_tokens": 100_000,
            "output_tokens": 10_000,
            "models_used": {"a": "gemini-2.5-flash-lite"},
        }
        assert _stage_cost_usd(flash) > _stage_cost_usd(lite)

    def test_stage_costs_sum_to_the_check_cost(self):
        by_stage = {
            "mapping": {
                "input_tokens": 60_000,
                "output_tokens": 4_000,
                "calls": 2,
                "models_used": {"a": "gemini-2.5-flash"},
            },
            "classify": {
                "input_tokens": 40_000,
                "output_tokens": 2_000,
                "calls": 1,
                "models_used": {"a": "gemini-2.5-flash-lite"},
            },
        }
        c = row_costs(
            telemetry(
                input_tokens=100_000,
                output_tokens=6_000,
                by_stage=by_stage,
                units={"serper": 1},
            )
        )
        assert sum(_stage_cost_usd(s) for s in by_stage.values()) == pytest.approx(
            c["llm_usd"], rel=1e-6
        )

    def test_stages_are_ranked_by_spend_with_models_named(self):
        by_stage = {
            "distil": {
                "input_tokens": 500_000,
                "output_tokens": 20_000,
                "calls": 5,
                "models_used": {"a": "gemini-2.5-flash-lite"},
            },
            "mapping": {
                "input_tokens": 10_000,
                "output_tokens": 1_000,
                "calls": 1,
                "models_used": {"a": "gemini-2.5-flash"},
            },
        }
        r = build_report([row(by_stage=by_stage, units={"serper": 2})], 1.28)
        assert [s["stage"] for s in r["stages"]] == ["distil", "mapping"]
        assert r["stages"][0]["share"] > r["stages"][1]["share"]
        assert r["stages"][0]["models"] == {"gemini-2.5-flash-lite": 1}
        assert sum(s["share"] for s in r["stages"]) == pytest.approx(1.0)

    def test_a_stage_seen_in_several_checks_accumulates(self):
        stage = {
            "input_tokens": 1_000,
            "output_tokens": 100,
            "calls": 1,
            "models_used": {"a": "gemini-2.5-flash"},
        }
        r = build_report(
            [row(by_stage={"mapping": stage}, units={"serper": 1}) for _ in range(3)],
            1.28,
        )
        m = r["stages"][0]
        assert m["checks"] == 3 and m["input_tokens"] == 3_000 and m["calls"] == 3


class TestMargins:
    def test_headroom_is_revenue_minus_cost(self):
        m = _margins(
            {"n": 1, "avg": 4.0, "median": 4.0, "p90": 4.0, "min": 4.0, "max": 4.0}
        )
        console = next(l for l in m["lines"] if l["product"].startswith("Console"))
        assert console["revenue_pence"] == CONSOLE_REVENUE_PENCE_PER_CHECK == 10.0
        assert console["headroom_pence"] == pytest.approx(6.0)
        assert console["margin_pct"] == pytest.approx(60.0)

    def test_a_negative_margin_is_reported_not_clamped(self):
        m = _margins(
            {"n": 1, "avg": 25.0, "median": 25.0, "p90": 25.0, "min": 25.0, "max": 25.0}
        )
        console = next(l for l in m["lines"] if l["product"].startswith("Console"))
        assert console["headroom_pence"] == pytest.approx(-15.0)
        assert console["margin_pct"] < 0

    def test_the_margin_uses_the_median_so_one_outlier_cannot_move_it(self):
        # Nine ordinary checks and one monster. The mean lands where no real
        # check lives; the median answers "what does a typical check do?".
        vals = [4.0] * 9 + [200.0]
        m = _margins(_spread(vals))
        assert m["median_cost_pence"] == pytest.approx(4.0)
        assert sum(vals) / len(vals) > 20  # the mean would have said otherwise

    def test_every_agent_tier_gets_a_line(self):
        m = _margins(_spread([4.0]))
        products = " ".join(l["product"] for l in m["lines"])
        for tier in ("lookup", "consensus", "quick", "full"):
            assert tier in products

    def test_margins_are_none_when_nothing_is_metered(self):
        m = _margins(_spread([]))
        assert m["median_cost_pence"] is None
        assert all(l["headroom_pence"] is None for l in m["lines"])


class TestSpreadAndPercentile:
    def test_single_value_does_not_crash(self):
        # At current volume a window can legitimately hold one check.
        assert _percentile([7.0], 0.9) == 7.0
        s = _spread([7.0])
        assert s["median"] == s["p90"] == s["min"] == s["max"] == 7.0

    def test_empty_is_none_everywhere_and_n_is_zero(self):
        s = _spread([])
        assert s["n"] == 0
        assert all(s[k] is None for k in ("avg", "median", "p90", "min", "max"))

    def test_percentile_interpolates(self):
        assert _percentile([0.0, 10.0], 0.5) == pytest.approx(5.0)
        assert _percentile([0.0, 10.0], 0.9) == pytest.approx(9.0)

    def test_input_order_does_not_matter(self):
        assert _spread([9.0, 1.0, 5.0])["median"] == pytest.approx(5.0)


class TestCurrency:
    def test_cost_converts_usd_to_pence_at_the_given_rate(self):
        rows = [row(units={"serper": 10})]
        cheap = build_report(rows, gbp_usd=2.0)["pence_per_check"]["total_partial"][
            "median"
        ]
        dear = build_report(rows, gbp_usd=1.0)["pence_per_check"]["total_partial"][
            "median"
        ]
        # A weaker pound makes a dollar-denominated cost dearer in pence.
        assert dear == pytest.approx(2 * cheap)

    def test_the_assumed_rate_is_printed(self):
        out = render(build_report([row(units={"serper": 1})], 1.33))
        assert "1.33" in out and "not a live rate" in out


class TestTierAndStatus:
    def test_cost_is_broken_down_by_executed_tier(self):
        rows = [
            row(tier="quick", input_tokens=10_000, units={"serper": 2}),
            row(tier="full", input_tokens=100_000, units={"serper": 20}),
        ]
        r = build_report(rows, 1.28)
        assert set(r["by_tier"]) == {"quick", "full"}
        assert r["by_tier"]["full"]["median"] > r["by_tier"]["quick"]["median"]

    def test_a_missing_tier_is_labelled_not_dropped(self):
        r = build_report([row(tier=None, units={"serper": 1})], 1.28)
        assert "(unset)" in r["by_tier"]

    def test_failed_checks_are_shown_and_their_cost_called_real(self):
        rows = [
            row(status="completed", units={"serper": 5}),
            row(status="failed", units={"serper": 5}),
        ]
        r = build_report(rows, 1.28)
        assert r["counts"]["by_status"] == {"completed": 1, "failed": 1}
        out = render(r)
        assert "Cost is real, revenue is not" in out


class TestHonestyOfTheOutput:
    def test_the_floor_ceiling_warning_is_present(self):
        # The single most misreadable number in the report is the headroom.
        out = render(build_report([row(units={"serper": 5})], 1.28))
        assert "FLOOR" in out and "CEILING" in out

    def test_prices_are_labelled_unverified(self):
        out = render(build_report([row(units={"serper": 5})], 1.28))
        assert "UNVERIFIED" in out

    def test_a_reprice_is_disclosed_when_rows_were_saved_under_another_version(self):
        out = render(
            build_report(
                [row(units={"serper": 5}, pricing_version="1999-ancient")], 1.28
            )
        )
        assert "recomputed" in out

    def test_it_says_so_rather_than_guessing_when_nothing_is_metered(self):
        out = render(build_report([row(units=None)], 1.28))
        assert "cannot answer yet" in out

    def test_render_survives_a_check_with_almost_no_telemetry(self):
        r = build_report(
            [
                {
                    "status": "failed",
                    "executed_tier": None,
                    "client": None,
                    "cost_telemetry": {},
                }
            ],
            1.28,
        )
        assert isinstance(render(r), str)

    def test_render_survives_junk_in_the_blob(self):
        # Telemetry is JSONB written by a pipeline that has changed shape twice;
        # a report that crashes on an old row is a report nobody runs.
        r = build_report(
            [
                {
                    "status": "completed",
                    "executed_tier": "full",
                    "client": None,
                    "cost_telemetry": {"llm": "not-a-dict", "search": None},
                }
            ],
            1.28,
        )
        assert isinstance(render(r), str)
