"""F1-D3 recency hedge tests (2026-07-06).

Design: audit/2026-07-03_f1f2_design_review.md §3 Option D3 + founder
decision #2. Of each element's planned queries, the SECOND runs with
freshness="none" so historical/contemporaneous material always has a
retrieval lane — claims about the past with no explicit year token were
structurally windowed to the last 12 months (report-quality review F1,
the all-2026 LHC evidence set). Breaking-news elements (planner freshness
pd/pw) are exempt: every lane stays recent.

These tests hit the real merge seam (`_merge_element_plans`) that
retrieve.py uses to build the claim-level query_plan — not a copy of its
logic (NF-18 lesson: test the wired path).
"""

from app.pipeline.retrieve import _hedged_query_freshness, _merge_element_plans


def _plan(element_id, freshness, queries):
    return {
        "claim_index": 0,
        "element_id": element_id,
        "freshness": freshness,
        "queries": list(queries),
        "reasoning": "r",
    }


# ── _hedged_query_freshness (pure rule) ──────────────────────────────


class TestHedgeRule:
    def test_second_query_unwindowed_for_py(self):
        assert _hedged_query_freshness("py", 0) == "py"
        assert _hedged_query_freshness("py", 1) == "none"

    def test_second_query_unwindowed_for_pm_and_2y(self):
        assert _hedged_query_freshness("pm", 1) == "none"
        assert _hedged_query_freshness("2y", 1) == "none"

    def test_breaking_news_exempt(self):
        # Founder decision #2: pd/pw elements keep every lane recent.
        assert _hedged_query_freshness("pd", 1) == "pd"
        assert _hedged_query_freshness("pw", 1) == "pw"

    def test_b4_none_stays_none(self):
        # Historical claims already unwindowed by B4 — hedge is a no-op.
        assert _hedged_query_freshness("none", 0) == "none"
        assert _hedged_query_freshness("none", 1) == "none"

    def test_third_query_keeps_element_freshness(self):
        # Only position 1 is the hedge lane; class-augmented extras keep
        # the element's freshness.
        assert _hedged_query_freshness("py", 2) == "py"


# ── _merge_element_plans (the wired seam) ────────────────────────────


class TestMergeWithHedge:
    def test_two_query_element_gets_hedged_second_lane(self):
        plan = _merge_element_plans(
            [_plan("e1", "py", ["q1", "q2"])], max_queries_per_element=3
        )
        assert plan["queries"] == ["q1", "q2"]
        assert plan["query_element_ids"] == ["e1", "e1"]
        assert plan["query_freshness"] == ["py", "none"]

    def test_single_query_element_untouched(self):
        # Quick mode (max 1 query/element): the only recency-guaranteed
        # lane is never hedged away.
        plan = _merge_element_plans(
            [_plan("e1", "py", ["q1", "q2"])], max_queries_per_element=1
        )
        assert plan["queries"] == ["q1"]
        assert plan["query_freshness"] == ["py"]

    def test_breaking_news_element_all_lanes_recent(self):
        plan = _merge_element_plans(
            [_plan("e1", "pw", ["q1", "q2"])], max_queries_per_element=3
        )
        assert plan["query_freshness"] == ["pw", "pw"]

    def test_hedge_is_per_element_not_per_claim(self):
        plan = _merge_element_plans(
            [
                _plan("e1", "py", ["a1", "a2"]),
                _plan("e2", "pd", ["b1", "b2"]),
                _plan("e3", "pm", ["c1"]),
            ],
            max_queries_per_element=3,
        )
        assert plan["queries"] == ["a1", "a2", "b1", "b2", "c1"]
        assert plan["query_element_ids"] == ["e1", "e1", "e2", "e2", "e3"]
        assert plan["query_freshness"] == ["py", "none", "pd", "pd", "pm"]

    def test_third_class_query_keeps_element_freshness(self):
        plan = _merge_element_plans(
            [_plan("e1", "py", ["q1", "q2", "site:gov.uk q"])],
            max_queries_per_element=3,
        )
        assert plan["query_freshness"] == ["py", "none", "py"]

    def test_b4_historical_element_stays_fully_unwindowed(self):
        plan = _merge_element_plans(
            [_plan("e1", "none", ["q1", "q2"])], max_queries_per_element=3
        )
        assert plan["query_freshness"] == ["none", "none"]

    def test_plan_level_fallback_fields_preserved(self):
        plan = _merge_element_plans(
            [_plan("e1", "pm", ["q1"])], max_queries_per_element=3
        )
        assert plan["freshness"] == "pm"
        assert plan["reasoning"] == "r"

    def test_query_cap_applies_before_hedge_position(self):
        # Cap slices first; position is within the CAPPED list.
        plan = _merge_element_plans(
            [_plan("e1", "py", ["q1", "q2", "q3", "q4"])],
            max_queries_per_element=2,
        )
        assert plan["queries"] == ["q1", "q2"]
        assert plan["query_freshness"] == ["py", "none"]
