"""The search meter must count what the provider actually bills for.

Context: `estimated_cost_usd.search` was None since inception because the
pipeline only ever recorded RESULT counts, not QUERY counts. Console sells 200
checks for GBP20 — 10p of revenue per check — and element-level retrieval
(2026-07-27) multiplied the query count per claim, so the largest variable cost
was both bigger than the April model assumed and entirely unmeasured.

The subtle part is billable UNITS, not queries: Serper bills 2 credits when
11-100 results are requested, and the claim lane asks for 13. Counting requests
would understate Serper spend by nearly half.
"""

import asyncio

import pytest

from app.core.cost_constants import (
    SEARCH_PRICING_USD_PER_UNIT,
    build_cost_telemetry,
    estimate_search_cost_usd,
)
from app.core.search_meter import meter_searches, metered, record_search, snapshot


class TestCounting:
    def test_counts_queries_and_units(self):
        with meter_searches():
            record_search("serper", 5)
            record_search("serper", 5)
            snap = snapshot()
        assert snap["queries_by_provider"] == {"serper": 2}
        assert snap["billable_units_by_provider"] == {"serper": 2}

    def test_serper_bills_two_credits_above_ten_results(self):
        """The claim lane asks for 13 — CLAIM_LANE_MAX_RESULTS_PER_QUERY."""
        with meter_searches():
            record_search("serper", 13)
            snap = snapshot()
        assert snap["total_queries"] == 1
        assert snap["total_billable_units"] == 2, "13 results is 2 Serper credits"

    def test_serper_boundary_at_ten(self):
        with meter_searches():
            record_search("serper", 10)  # 1 credit
            record_search("serper", 11)  # 2 credits
            snap = snapshot()
        assert snap["total_billable_units"] == 3

    def test_other_providers_bill_per_request(self):
        with meter_searches():
            record_search("brave", 20)
            record_search("serpapi", 20)
            snap = snapshot()
        assert snap["billable_units_by_provider"] == {"brave": 1, "serpapi": 1}

    def test_a_full_check_shape(self):
        """The designed full-mode shape: 5 claims x (3 claim-lane + 10 element)."""
        with meter_searches():
            for _ in range(5):
                for _ in range(3):
                    record_search("serper", 13)  # claim lane, 2 credits each
                for _ in range(10):
                    record_search("serper", 5)  # element lanes, 1 credit each
            snap = snapshot()
        assert snap["total_queries"] == 65
        assert snap["total_billable_units"] == 80  # 5 * (3*2 + 10*1)


class TestIsolation:
    def test_no_op_outside_a_metered_context(self):
        """Scripts, tests and re-search run unmetered; that must not explode."""
        record_search("serper", 13)  # no context active
        assert snapshot() is None

    def test_context_is_reset_on_exit(self):
        with meter_searches():
            record_search("serper", 1)
        assert snapshot() is None

    def test_counts_survive_asyncio_fan_out(self):
        """Retrieval fans out across tasks; a contextvar must propagate into them."""

        async def scenario():
            with meter_searches():
                await asyncio.gather(
                    *(asyncio.to_thread(record_search, "serper", 13) for _ in range(4))
                )
                return snapshot()

        snap = asyncio.run(scenario())
        assert snap["total_queries"] == 4
        assert snap["total_billable_units"] == 8

    def test_concurrent_checks_do_not_contaminate_each_other(self):
        """A module-level counter would fail this; a contextvar must not."""

        async def one_check(n_queries):
            with meter_searches():
                for _ in range(n_queries):
                    record_search("serper", 5)
                await asyncio.sleep(0)  # yield, letting the other check interleave
                return snapshot()["total_queries"]

        async def scenario():
            return await asyncio.gather(one_check(3), one_check(7))

        assert asyncio.run(scenario()) == [3, 7]


class TestMeteredDecorator:
    def test_attaches_the_tally_to_the_returned_dict(self):
        @metered
        async def fake_phase2():
            record_search("serper", 13)
            return {"claims": []}

        result = asyncio.run(fake_phase2())
        assert result["search_meter"]["total_billable_units"] == 2

    def test_tolerates_a_non_dict_return(self):
        @metered
        async def returns_none():
            record_search("serper", 1)
            return None

        assert asyncio.run(returns_none()) is None


class TestCosting:
    def test_prices_measured_units(self):
        meter = {"billable_units_by_provider": {"serper": 80}}
        expected = 80 * SEARCH_PRICING_USD_PER_UNIT["serper"]
        assert estimate_search_cost_usd(meter) == pytest.approx(expected)

    def test_unmetered_check_is_unknown_not_free(self):
        """A silent zero would read as 'search is costless' — the opposite of true."""
        assert estimate_search_cost_usd(None) is None
        assert estimate_search_cost_usd({}) is None

    def test_telemetry_carries_measured_search_cost(self):
        results = {
            "llm_token_usage": {"input_tokens": 1000, "output_tokens": 100},
            "search_meter": {
                "queries_by_provider": {"serper": 65},
                "billable_units_by_provider": {"serper": 80},
                "total_queries": 65,
                "total_billable_units": 80,
            },
        }
        out = build_cost_telemetry(results)
        assert out["search"]["total_queries"] == 65
        assert out["search"]["total_billable_units"] == 80
        assert out["estimated_cost_usd"]["search"] == pytest.approx(0.08)
        assert out["estimated_cost_usd"]["total_partial"] is not None

    def test_legacy_check_reports_unknown_rather_than_zero(self):
        out = build_cost_telemetry({"llm_token_usage": {"input_tokens": 10}})
        assert out["estimated_cost_usd"]["search"] is None
        assert out["estimated_cost_usd"]["total_partial"] is None

    def test_a_full_check_is_priced_against_console_revenue(self):
        """The decision-relevant number, stated as a test so it cannot drift.

        Console: GBP20 / 200 checks = 10p ~= $0.128 revenue per check. A full
        5-claim check issues 80 Serper credits, which at the entry rate is $0.08
        of SEARCH ALONE — before any LLM cost. This test does not assert that is
        acceptable; it asserts the number is visible.
        """
        cost = estimate_search_cost_usd({"billable_units_by_provider": {"serper": 80}})
        assert cost == pytest.approx(0.08)
        assert cost > 0.5 * 0.128, "search alone exceeds half of per-check revenue"
