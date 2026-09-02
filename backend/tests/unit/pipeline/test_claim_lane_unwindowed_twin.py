"""Build A (2026-09-02): the claim lane's unwindowed twin.

Design: audit/2026-09-02_claim_lane_unwindowed_twin_design.md. Evidence:
audit/2026-09-02_dissent_discovery_probe.md §1 — with the pipeline's exact
parameters the plain claim text finds the TTE and Scotland rebuttals at rank 3
UNWINDOWED; inside the past-month window the claim lane actually ran, Google
returned only blocklisted social links, so the lane contributed nothing and a
critic's presence rode on element-lane churn (11f54993 vs b0398fca).

These tests hit the real seams retrieve.py uses (`_merge_element_plans`,
`_allocate_fetch_budget`, `_execute_planned_queries`) — never a copy of the
logic (NF-18: test the wired path).
"""

from unittest.mock import AsyncMock, patch

import pytest

from app.core.config import settings
from app.pipeline.retrieve import (
    CLAIM_LANE_ELEMENT_ID,
    CLAIM_LANE_TWIN_RESULTS,
    ELEMENT_RESULTS_PER_QUERY,
    EvidenceRetriever,
    _allocate_fetch_budget,
    _merge_element_plans,
    _synthesise_claim_lane_plan,
)
from app.services.evidence import EvidenceSnippet
from app.services.search import SearchResult

CLAIM_TEXT = "AI triage through the NHS App reduced phone queues by 29 per cent"


def _plan(element_id, freshness, queries):
    return {
        "claim_index": 0,
        "element_id": element_id,
        "freshness": freshness,
        "queries": list(queries),
        "reasoning": "r",
    }


def _rows(merged):
    return list(
        zip(
            merged["queries"],
            merged["query_element_ids"],
            merged["query_freshness"],
            merged["query_twin_of"],
        )
    )


# ── the merge seam ───────────────────────────────────────────────────


@pytest.mark.unit
class TestTwinAtTheMergeSeam:
    def test_synthesised_claim_lane_gets_its_twin_at_position_one(self):
        # The TTE shape: planner omitted c0, one element lane with pm.
        plans = _synthesise_claim_lane_plan(
            [_plan("e1", "pm", ["e1 q1", "e1 q2"])], 0, CLAIM_TEXT
        )
        merged = _merge_element_plans(
            plans, max_queries_per_element=3, element_wired=True
        )

        assert _rows(merged)[:2] == [
            (CLAIM_TEXT, CLAIM_LANE_ELEMENT_ID, "pm", None),
            (CLAIM_TEXT, CLAIM_LANE_ELEMENT_ID, "none", 0),
        ]
        # Element lanes exactly as before: lead windowed, hedge on position 1.
        assert _rows(merged)[2:] == [
            ("e1 q1", "e1", "pm", None),
            ("e1 q2", "e1", "none", None),
        ]

    def test_planner_emitted_lane_with_site_variants_keeps_lead_depth_order(self):
        plans = [
            _plan(
                CLAIM_LANE_ELEMENT_ID,
                "py",
                ["c lead", "c lead site:a", "c lead site:b"],
            ),
            _plan("e1", "py", ["e1 q1"]),
        ]
        merged = _merge_element_plans(
            plans, max_queries_per_element=3, element_wired=True
        )

        rows = _rows(merged)
        assert rows[0] == ("c lead", CLAIM_LANE_ELEMENT_ID, "py", None)
        assert rows[1] == ("c lead", CLAIM_LANE_ELEMENT_ID, "none", 0)
        # The variants shift down one; the F1-D3 hedge still lands on the
        # planner's position 1 (the first variant), computed BEFORE insertion.
        assert rows[2] == ("c lead site:a", CLAIM_LANE_ELEMENT_ID, "none", None)
        assert rows[3] == ("c lead site:b", CLAIM_LANE_ELEMENT_ID, "py", None)
        assert rows[4] == ("e1 q1", "e1", "py", None)

    def test_breaking_news_lane_is_exempt_like_the_hedge(self):
        for fresh in ("pd", "pw"):
            plans = _synthesise_claim_lane_plan(
                [_plan("e1", fresh, ["e1 q1"])], 0, CLAIM_TEXT
            )
            merged = _merge_element_plans(
                plans, max_queries_per_element=3, element_wired=True
            )
            assert merged["queries"].count(CLAIM_TEXT) == 1
            assert all(t is None for t in merged["query_twin_of"])

    def test_already_unwindowed_lead_gets_no_twin(self):
        # B4 historical claims arrive with freshness "none" already.
        plans = _synthesise_claim_lane_plan(
            [_plan("e1", "none", ["e1 q1"])], 0, CLAIM_TEXT
        )
        merged = _merge_element_plans(
            plans, max_queries_per_element=3, element_wired=True
        )
        assert merged["queries"].count(CLAIM_TEXT) == 1
        assert merged["query_freshness"][0] == "none"
        assert all(t is None for t in merged["query_twin_of"])

    def test_unwired_plans_are_byte_identical_to_today(self):
        # Pre-decomposition / flag-off shape: a single "e1" lane, no claim lane.
        plans = [_plan("e1", "pm", [CLAIM_TEXT, "q2"])]
        merged = _merge_element_plans(
            plans, max_queries_per_element=3, element_wired=False
        )
        assert merged["queries"] == [CLAIM_TEXT, "q2"]
        assert merged["query_twin_of"] == [None, None]

    def test_flag_off_restores_today(self, monkeypatch):
        monkeypatch.setattr(settings, "ENABLE_CLAIM_LANE_UNWINDOWED_TWIN", False)
        plans = _synthesise_claim_lane_plan(
            [_plan("e1", "pm", ["e1 q1"])], 0, CLAIM_TEXT
        )
        merged = _merge_element_plans(
            plans, max_queries_per_element=3, element_wired=True
        )
        assert merged["queries"] == [CLAIM_TEXT, "e1 q1"]
        assert merged["query_freshness"] == ["pm", "pm"]
        assert merged["query_twin_of"] == [None, None]

    def test_four_arrays_stay_index_parallel(self):
        plans = [
            _plan(CLAIM_LANE_ELEMENT_ID, "pm", ["c lead", "c v1"]),
            _plan("e1", "pm", ["e1 q1", "e1 q2"]),
            _plan("e2", "py", ["e2 q1"]),
        ]
        merged = _merge_element_plans(
            plans, max_queries_per_element=3, element_wired=True
        )
        n = len(merged["queries"])
        assert n == 6
        assert len(merged["query_element_ids"]) == n
        assert len(merged["query_freshness"]) == n
        assert len(merged["query_twin_of"]) == n
        twins = [i for i, t in enumerate(merged["query_twin_of"]) if t is not None]
        assert twins == [1]
        assert merged["queries"][1] == merged["queries"][merged["query_twin_of"][1]]

    def test_quick_tier_cap_of_one_still_gets_the_twin(self):
        # QUICK_CONFIG caps the planner's queries at 1 per lane; the twin is a
        # guarantee added after the cap, so the quick claim lane runs 2.
        plans = _synthesise_claim_lane_plan(
            [_plan("e1", "pm", ["e1 q1", "e1 q2"])], 0, CLAIM_TEXT
        )
        merged = _merge_element_plans(
            plans, max_queries_per_element=1, element_wired=True
        )
        assert merged["queries"] == [CLAIM_TEXT, CLAIM_TEXT, "e1 q1"]
        assert merged["query_freshness"] == ["pm", "none", "pm"]


# ── the allocator ────────────────────────────────────────────────────


def _result(title, query_index):
    r = SearchResult(
        title=title, url=f"https://x.test/{title}", snippet="s", source="x.test"
    )
    r._query_index = query_index
    return r


@pytest.mark.unit
class TestTwinFetchWeight:
    def test_twin_takes_an_element_lanes_weight_not_the_claim_lanes(self):
        # Buckets: q0 lead (c0), q1 twin (c0), q2 element.
        results = (
            [_result(f"lead-{i}", 0) for i in range(6)]
            + [_result(f"twin-{i}", 1) for i in range(6)]
            + [_result(f"e1-{i}", 2) for i in range(6)]
        )
        lanes = [CLAIM_LANE_ELEMENT_ID, CLAIM_LANE_ELEMENT_ID, "e1"]
        twin_of = [None, 0, None]

        ordered = _allocate_fetch_budget(results, lanes, twin_of)

        # First round: lead takes 2, twin 1, element 1.
        assert [r.title for r in ordered[:4]] == ["lead-0", "lead-1", "twin-0", "e1-0"]
        # The twin's rank-3 result is fetched within the first ~12 slots.
        assert "twin-2" in [r.title for r in ordered[:12]]

    def test_without_twin_marks_the_allocator_is_unchanged(self):
        results = [_result(f"lead-{i}", 0) for i in range(4)] + [
            _result(f"e1-{i}", 1) for i in range(4)
        ]
        lanes = [CLAIM_LANE_ELEMENT_ID, "e1"]
        assert [r.title for r in _allocate_fetch_budget(results, lanes)] == [
            r.title for r in _allocate_fetch_budget(results, lanes, None)
        ]
        assert [r.title for r in _allocate_fetch_budget(results, lanes)[:3]] == [
            "lead-0",
            "lead-1",
            "e1-0",
        ]


# ── what the search service is asked for ─────────────────────────────


@pytest.fixture
def retriever():
    with patch("app.pipeline.retrieve.SearchService"), patch(
        "app.pipeline.retrieve.EvidenceExtractor"
    ), patch("app.pipeline.retrieve.get_api_registry"):
        r = EvidenceRetriever()
        r.evidence_extractor.max_concurrent = 3
        return r


def _capturing_search(calls):
    async def _search(query, max_results=10, freshness=None, country=None):
        calls.append(
            {"query": query, "max_results": max_results, "freshness": freshness}
        )
        return [
            SearchResult(
                title=query,
                url=f"https://example.com/{len(calls)}/{i}",
                snippet="s",
                source="example.com",
            )
            for i in range(max_results)
        ]

    return _search


@pytest.mark.unit
@pytest.mark.asyncio
class TestTwinRequestDepth:
    async def _run(self, retriever, query_plan, calls):
        retriever.evidence_extractor.search_service.search_for_evidence = (
            _capturing_search(calls)
        )
        retriever.evidence_extractor._extract_from_page = AsyncMock(
            return_value=EvidenceSnippet(
                text="content",
                source="example.com",
                url="https://example.com/x",
                title="t",
                relevance_score=0.5,
                metadata={},
            )
        )
        return await retriever._execute_planned_queries(
            claim_text=CLAIM_TEXT, query_plan=query_plan, max_sources=40
        )

    async def test_lead_keeps_todays_depth_twin_asks_for_its_fixed_slice(
        self, retriever
    ):
        calls = []
        plan = {
            "queries": ["lead", "lead", "e1a", "e1b"],
            "query_element_ids": [
                CLAIM_LANE_ELEMENT_ID,
                CLAIM_LANE_ELEMENT_ID,
                "e1",
                "e1",
            ],
            "query_freshness": ["pm", "none", "pm", "none"],
            "query_twin_of": [None, 0, None, None],
            "element_wired": True,
        }
        await self._run(retriever, plan, calls)

        # Literals, not constants: a pin written against the constant it
        # guards passes under any mutation of that constant.
        by_index = {i: c for i, c in enumerate(calls)}
        assert by_index[0]["max_results"] == 13  # the lead, exactly as today
        assert by_index[1]["max_results"] == 10  # the twin
        assert by_index[1]["max_results"] == CLAIM_LANE_TWIN_RESULTS
        assert by_index[1]["freshness"] == "none"
        assert by_index[2]["max_results"] == 5 == ELEMENT_RESULTS_PER_QUERY

    async def test_self_supplied_plan_without_the_key_is_unchanged(self, retriever):
        # re_search.py builds its own plan and never sets query_twin_of.
        calls = []
        plan = {
            "queries": ["c1", "c2", "e1a"],
            "query_element_ids": [CLAIM_LANE_ELEMENT_ID, CLAIM_LANE_ELEMENT_ID, "e1"],
            "element_wired": True,
        }
        await self._run(retriever, plan, calls)
        # Two claim-lane queries, budget 40: min(13, 40 // 2) = 13 each, as today.
        assert calls[0]["max_results"] == calls[1]["max_results"] == 13
        assert calls[2]["max_results"] == 5
