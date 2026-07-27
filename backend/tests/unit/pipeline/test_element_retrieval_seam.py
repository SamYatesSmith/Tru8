"""Element-level retrieval seam — Phase 2 pins (2026-07-27).

Design: audit/2026-07-27_phase2_element_retrieval_build_design.md

The query planner has always been written for elements, but the key it read
(``claim["elements"]``) was never written by anything — decompose writes
``claim["claim_map"]["elements"]`` — so every check planned its queries from a
single synthetic element made of the raw claim text. On an opinion claim that
means the pool was constituted by searching the judgement's own valence.

These tests pin the WIRED path (what actually reaches the planner and the
search service), not just the helpers in isolation — the NF-18 lesson, and the
reason this defect survived for months behind green unit tests.
"""

import asyncio
import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.pipeline.retrieve import (
    CLAIM_LANE_ELEMENT_ID,
    ELEMENT_RESULTS_PER_QUERY,
    EvidenceRetriever,
    _allocate_fetch_budget,
    _build_retrieval_lanes,
    _class_augmentation_targets,
    _merge_element_plans,
)
from app.services.search import SearchResult
from app.services.evidence import EvidenceSnippet


CLAIM_TEXT = "The UK COVID vaccine rollout was a triumph."
GROUNDS_ELEMENT = (
    "What does the evidence indicate about the speed of the UK COVID vaccine "
    "rollout relative to comparable countries?"
)


def _claim_with_elements(descriptions, text=CLAIM_TEXT):
    return {
        "text": text,
        "position": 0,
        "claim_map": {
            "elements": [
                {"element_id": f"e{i + 1}", "description": d}
                for i, d in enumerate(descriptions)
            ]
        },
    }


def _plan(element_id, queries, claim_index=0, freshness="py"):
    return {
        "claim_index": claim_index,
        "element_id": element_id,
        "queries": list(queries),
        "freshness": freshness,
        "reasoning": "",
    }


# ── Criterion 1/2/5: lanes built from the key decompose actually writes ──


@pytest.mark.unit
class TestLaneConstruction:
    def test_claim_lane_first_then_element_lanes(self):
        lanes = _build_retrieval_lanes(
            _claim_with_elements([GROUNDS_ELEMENT, "second ground", "third ground"])
        )

        assert [lane["element_id"] for lane in lanes] == [
            CLAIM_LANE_ELEMENT_ID,
            "e1",
            "e2",
            "e3",
        ]
        # The claim lane IS today's synthetic element — same text, new id.
        assert lanes[0]["description"] == CLAIM_TEXT
        # And it is not "e1": that silently attributed the whole claim-level
        # pool to the first real element.
        assert lanes[0]["element_id"] != "e1"

    def test_element_description_reaches_the_planner_verbatim(self):
        """Positive assertion — an emptied fixture fails this loudly."""
        lanes = _build_retrieval_lanes(_claim_with_elements([GROUNDS_ELEMENT]))

        descriptions = [lane["description"] for lane in lanes]
        assert GROUNDS_ELEMENT in descriptions
        assert descriptions[1] == GROUNDS_ELEMENT

    def test_element_lanes_capped_at_five_and_blank_descriptions_skipped(self):
        claim = _claim_with_elements([f"ground {i}" for i in range(7)])
        claim["claim_map"]["elements"][1]["description"] = "   "

        lanes = _build_retrieval_lanes(claim)

        assert len(lanes) == 6  # claim lane + 5 element lanes
        assert "e2" not in [lane["element_id"] for lane in lanes]

    def test_caller_supplied_elements_get_no_claim_lane(self):
        """re_search.py builds a claim carrying ONE target element.

        Its contract is "search this element". Adding a claim lane there would
        spend half the fetch budget re-searching what the user already has —
        and would silently change the Seeker's top-up behaviour.
        """
        lanes = _build_retrieval_lanes(
            {
                "text": CLAIM_TEXT,
                "elements": [{"element_id": "e3", "description": "a target ground"}],
            }
        )

        assert lanes == [{"element_id": "e3", "description": "a target ground"}]
        assert CLAIM_LANE_ELEMENT_ID not in [lane["element_id"] for lane in lanes]

    def test_caller_supplied_elements_win_over_the_claim_map(self):
        """Explicit beats derived — the re-search claim is not re-decomposed."""
        lanes = _build_retrieval_lanes(
            {
                "text": CLAIM_TEXT,
                "elements": [{"element_id": "e3", "description": "target only"}],
                "claim_map": {
                    "elements": [
                        {"element_id": "e1", "description": "one"},
                        {"element_id": "e2", "description": "two"},
                    ]
                },
            }
        )

        assert [lane["element_id"] for lane in lanes] == ["e3"]


# ── Criteria 3/4: the two ways today's behaviour must survive ──


@pytest.mark.unit
class TestUnchangedPaths:
    def test_pre_decomposition_claim_is_byte_identical(self):
        assert _build_retrieval_lanes({"text": CLAIM_TEXT}) == [
            {"element_id": "e1", "description": CLAIM_TEXT}
        ]

    def test_empty_claim_map_is_byte_identical(self):
        assert _build_retrieval_lanes({"text": CLAIM_TEXT, "claim_map": {}}) == [
            {"element_id": "e1", "description": CLAIM_TEXT}
        ]

    def test_flag_off_restores_single_lane_on_a_decomposed_claim(self):
        claim = _claim_with_elements([GROUNDS_ELEMENT, "second ground"])

        with patch("app.pipeline.retrieve.settings") as mock_settings:
            mock_settings.ENABLE_ELEMENT_RETRIEVAL = False
            lanes = _build_retrieval_lanes(claim)

        assert lanes == [{"element_id": "e1", "description": CLAIM_TEXT}]

    def test_flag_off_leaves_the_merged_plan_unwired(self):
        """The whole chain keys off element_wired, so prove it stays False."""
        merged = _merge_element_plans([_plan("e1", ["q1", "q2", "q3"])], 3)

        assert merged["element_wired"] is False
        assert merged["queries"] == ["q1", "q2", "q3"]
        assert merged["query_element_ids"] == ["e1", "e1", "e1"]


# ── Criteria 6/7: query counts and attribution after the merge ──


@pytest.mark.unit
class TestMergedPlan:
    def test_claim_lane_keeps_three_queries_element_lanes_take_two(self):
        merged = _merge_element_plans(
            [
                _plan("e1", ["e1 q1", "e1 q2", "e1 q3"]),
                _plan(CLAIM_LANE_ELEMENT_ID, ["c q1", "c q2", "c q3"]),
                _plan("e2", ["e2 q1", "e2 q2", "e2 q3"]),
            ],
            3,
        )

        assert merged["element_wired"] is True
        # Claim lane first, deterministically, whatever order the LLM replied in
        assert merged["queries"][:3] == ["c q1", "c q2", "c q3"]
        assert merged["queries"][3:] == ["e1 q1", "e1 q2", "e2 q1", "e2 q2"]
        assert len(merged["queries"]) == 7

    def test_query_element_ids_stay_index_parallel_with_queries(self):
        merged = _merge_element_plans(
            [
                _plan(CLAIM_LANE_ELEMENT_ID, ["c q1", "c q2"]),
                _plan("e1", ["e1 q1", "e1 q2"]),
                _plan("e2", ["e2 q1"]),
            ],
            3,
        )

        assert len(merged["query_element_ids"]) == len(merged["queries"])
        assert merged["query_element_ids"] == [
            CLAIM_LANE_ELEMENT_ID,
            CLAIM_LANE_ELEMENT_ID,
            "e1",
            "e1",
            "e2",
        ]
        for query, lane in zip(merged["queries"], merged["query_element_ids"]):
            prefix = "c" if lane == CLAIM_LANE_ELEMENT_ID else lane
            assert query.startswith(prefix)

    def test_quick_tier_cap_still_binds_on_every_lane(self):
        """max_queries_per_element=1 (quick tier) must cap the claim lane too."""
        merged = _merge_element_plans(
            [
                _plan(CLAIM_LANE_ELEMENT_ID, ["c q1", "c q2", "c q3"]),
                _plan("e1", ["e1 q1", "e1 q2"]),
            ],
            1,
        )

        assert merged["queries"] == ["c q1", "e1 q1"]

    def test_class_augmentation_targets_the_claim_lane_only(self):
        plans = [
            _plan(CLAIM_LANE_ELEMENT_ID, ["c q1"], claim_index=0),
            _plan("e1", ["e1 q1"], claim_index=0),
            _plan("e2", ["e2 q1"], claim_index=0),
            _plan("e1", ["other claim q1"], claim_index=1),
        ]

        targets = _class_augmentation_targets(plans, {0})

        assert [(p["claim_index"], p["element_id"]) for p in targets] == [
            (0, CLAIM_LANE_ELEMENT_ID),
            (1, "e1"),  # unwired claim keeps the old behaviour
        ]

    def test_hedge_applies_per_lane_not_across_the_merged_list(self):
        """F1-D3: position 1 of EACH lane is the unwindowed one."""
        merged = _merge_element_plans(
            [
                _plan(CLAIM_LANE_ELEMENT_ID, ["c q1", "c q2"], freshness="py"),
                _plan("e1", ["e1 q1", "e1 q2"], freshness="py"),
                _plan("e2", ["e2 q1", "e2 q2"], freshness="pd"),
            ],
            3,
        )

        assert merged["query_freshness"] == [
            "py",
            "none",  # claim lane, position 1
            "py",
            "none",  # e1, position 1
            "pd",
            "pd",  # e2 is breaking-news: every lane stays recent
        ]


# ── Criteria 8/9: the fetch budget reaches every lane ──


def _results_for(query_index, count, lane):
    out = []
    for i in range(count):
        result = SearchResult(
            title=f"{lane}-{i}",
            url=f"https://example.com/{lane}/{i}",
            snippet="s",
            source="example.com",
        )
        result._query_index = query_index
        out.append(result)
    return out


def _wired_pool():
    """1 claim lane (3 queries x 13) + 4 element lanes (2 queries x 5)."""
    lane_ids = [CLAIM_LANE_ELEMENT_ID] * 3
    results = []
    for qi in range(3):
        results += _results_for(qi, 13, f"c{qi}")
    qi = 3
    for element in range(1, 5):
        for _ in range(2):
            lane_ids.append(f"e{element}")
            results += _results_for(qi, 5, f"e{element}-{qi}")
            qi += 1
    return results, lane_ids


@pytest.mark.unit
class TestFetchBudgetAllocation:
    def test_every_lane_is_represented_within_the_budget(self):
        results, lane_ids = _wired_pool()
        assert len(results) == 79  # sanity: the budget genuinely has to bite

        allocated = _allocate_fetch_budget(results, lane_ids)[:40]

        lanes_funded = {lane_ids[r._query_index] for r in allocated}
        assert lanes_funded == {CLAIM_LANE_ELEMENT_ID, "e1", "e2", "e3", "e4"}
        # And every individual QUERY, not just every lane
        assert {r._query_index for r in allocated} == set(range(11))

    def test_sequential_order_would_starve_the_element_lanes(self):
        """The defect this allocation exists to prevent, asserted directly."""
        results, lane_ids = _wired_pool()

        sequential = {lane_ids[r._query_index] for r in results[:40]}

        assert sequential == {CLAIM_LANE_ELEMENT_ID, "e1"}
        assert "e4" not in sequential

    def test_claim_lane_is_weighted_two_to_one(self):
        results, lane_ids = _wired_pool()

        allocated = _allocate_fetch_budget(results, lane_ids)[:40]

        per_query = {}
        for r in allocated:
            per_query[r._query_index] = per_query.get(r._query_index, 0) + 1
        claim_queries = [per_query[i] for i in range(3)]
        element_queries = [per_query[i] for i in range(3, 11)]
        assert min(claim_queries) >= 2 * max(element_queries) - 1
        assert sum(claim_queries) > max(element_queries)

    def test_allocation_reorders_and_never_drops(self):
        results, lane_ids = _wired_pool()

        allocated = _allocate_fetch_budget(results, lane_ids)

        assert len(allocated) == len(results)
        assert {id(r) for r in allocated} == {id(r) for r in results}

    def test_within_a_lane_provider_ranking_is_preserved(self):
        results, lane_ids = _wired_pool()

        allocated = _allocate_fetch_budget(results, lane_ids)

        first_query = [r for r in allocated if r._query_index == 0]
        assert [r.title for r in first_query] == [f"c0-{i}" for i in range(13)]


# ── Criterion 10/14: what the search service is actually asked for ──


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
        calls.append({"query": query, "max_results": max_results})
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
class TestPerLaneRequestSizes:
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

    async def test_claim_lane_keeps_depth_element_lanes_take_the_floor(self, retriever):
        calls = []
        plan = {
            "queries": ["c1", "c2", "c3", "e1a", "e1b", "e2a", "e2b"],
            "query_element_ids": [
                CLAIM_LANE_ELEMENT_ID,
                CLAIM_LANE_ELEMENT_ID,
                CLAIM_LANE_ELEMENT_ID,
                "e1",
                "e1",
                "e2",
                "e2",
            ],
            "element_wired": True,
        }

        await self._run(retriever, plan, calls)

        by_query = {c["query"]: c["max_results"] for c in calls}
        # Literals, not the constants they came from: an assertion written
        # against the constant it is meant to pin passes under any mutation
        # of that constant.
        assert by_query["c1"] == by_query["c2"] == by_query["c3"] == 13
        assert by_query["e1a"] == 5
        assert by_query["e2b"] == 5
        assert by_query["e1a"] == ELEMENT_RESULTS_PER_QUERY
        assert by_query["e1a"] < by_query["c1"]

    async def test_wired_path_actually_fetches_from_every_lane(self, retriever):
        """The behavioural pin for the allocation — not the helper in isolation.

        _allocate_fetch_budget can be perfect and still never be called. This
        drives the real _execute_planned_queries with a candidate pool that
        overflows the budget and asserts on the URLs that reach the fetcher.
        """
        calls = []
        queries = ["c1", "c2", "c3"] + [f"e{e}{q}" for e in range(1, 5) for q in "ab"]
        lanes = [CLAIM_LANE_ELEMENT_ID] * 3 + [
            f"e{e}" for e in range(1, 5) for _ in "ab"
        ]
        plan = {
            "queries": queries,
            "query_element_ids": lanes,
            "element_wired": True,
        }

        fetched = []

        async def _capture_fetch(search_result, claim_text, semaphore):
            fetched.append(search_result.url)
            return EvidenceSnippet(
                text="content",
                source="example.com",
                url=search_result.url,
                title="t",
                relevance_score=0.5,
                metadata={},
            )

        retriever.evidence_extractor.search_service.search_for_evidence = (
            _capturing_search(calls)
        )
        retriever.evidence_extractor._extract_from_page = _capture_fetch

        await retriever._execute_planned_queries(
            claim_text=CLAIM_TEXT, query_plan=plan, max_sources=40
        )

        # The pool genuinely overflows: 3x13 + 8x5 = 79 candidates for 40 slots
        assert sum(c["max_results"] for c in calls) == 79
        assert len(fetched) == 40

        # _capturing_search stamps each URL with the 1-based call ordinal, so
        # the lane a fetched URL came from is recoverable.
        fetched_lanes = {lanes[int(url.split("/")[3]) - 1] for url in fetched}
        assert fetched_lanes == {CLAIM_LANE_ELEMENT_ID, "e1", "e2", "e3", "e4"}, (
            "a lane was starved of the fetch budget — sequential slicing funds "
            "the first queries and drops the last elements entirely"
        )

    async def test_unwired_plan_keeps_the_uniform_share(self, retriever):
        calls = []
        plan = {
            "queries": ["q1", "q2", "q3"],
            "query_element_ids": ["e1", "e1", "e1"],
        }

        await self._run(retriever, plan, calls)

        assert [c["max_results"] for c in calls] == [13, 13, 13]

    async def test_fetch_budget_telemetry_names_every_lane(self, retriever, caplog):
        calls = []
        plan = {
            "queries": ["c1", "e1a", "e2a"],
            "query_element_ids": [CLAIM_LANE_ELEMENT_ID, "e1", "e2"],
            "element_wired": True,
        }

        with caplog.at_level(logging.INFO, logger="app.pipeline.retrieve"):
            await self._run(retriever, plan, calls)

        budget_lines = [
            r.message for r in caplog.records if "[RETRIEVE] Fetch budget" in r.message
        ]
        assert budget_lines, "fetch-budget telemetry did not fire"
        assert CLAIM_LANE_ELEMENT_ID in budget_lines[0]
        assert "'e1'" in budget_lines[0] and "'e2'" in budget_lines[0]


# ── Criterion 1 (wired) + 14: what actually reaches the planner ──


@pytest.mark.unit
@pytest.mark.asyncio
class TestWiredPlannerInput:
    async def test_planner_receives_element_lanes_for_a_decomposed_claim(
        self, retriever, caplog
    ):
        captured = {}

        class _StubPlanner:
            async def plan_queries_batch(
                self, claims_with_elements, article_context=None
            ):
                captured["claims"] = claims_with_elements
                return [
                    _plan(CLAIM_LANE_ELEMENT_ID, ["c q1"]),
                    _plan("e1", ["e1 q1"]),
                    _plan("e2", ["e2 q1"]),
                ]

        claim = _claim_with_elements([GROUNDS_ELEMENT, "second ground"])
        retriever._retrieve_evidence_for_single_claim = AsyncMock(
            return_value={
                "filtered_evidence": [],
                "raw_evidence": [],
                "pre_weighting_evidence": [],
                "claim_position": 0,
                "claim_text": CLAIM_TEXT,
            }
        )
        retriever._ensure_minimum_evidence = AsyncMock(return_value=({"0": []}, []))

        with patch(
            "app.utils.query_planner.get_query_planner", return_value=_StubPlanner()
        ), caplog.at_level(logging.INFO, logger="app.pipeline.retrieve"):
            await retriever.retrieve_evidence_for_claims([claim])

        lanes = captured["claims"][0]["elements"]
        assert [lane["element_id"] for lane in lanes] == [
            CLAIM_LANE_ELEMENT_ID,
            "e1",
            "e2",
        ]
        assert lanes[1]["description"] == GROUNDS_ELEMENT

        # The merged plan lands on the claim, wired, with per-lane attribution
        plan = claim["query_plan"]
        assert plan["element_wired"] is True
        assert plan["query_element_ids"] == [CLAIM_LANE_ELEMENT_ID, "e1", "e2"]

        # And the telemetry says so — this is how "the seam is live" stops
        # being an inference from architecture docs.
        wiring_lines = [
            r.message
            for r in caplog.records
            if "[RETRIEVE] Element lanes wired" in r.message
        ]
        assert wiring_lines, "element-wiring telemetry did not fire"
        assert "element_lanes=2" in wiring_lines[0]

    async def test_lane_shortfall_is_named_not_just_counted(self, retriever, caplog):
        """A lane the planner skipped is an element that never gets searched."""

        class _ForgetfulPlanner:
            async def plan_queries_batch(
                self, claims_with_elements, article_context=None
            ):
                return [
                    _plan(CLAIM_LANE_ELEMENT_ID, ["c q1"]),
                    _plan("e1", ["e1 q1"]),
                ]  # e2 planned for, never returned

        claim = _claim_with_elements([GROUNDS_ELEMENT, "second ground"])
        retriever._retrieve_evidence_for_single_claim = AsyncMock(
            return_value={
                "filtered_evidence": [],
                "raw_evidence": [],
                "pre_weighting_evidence": [],
                "claim_position": 0,
                "claim_text": CLAIM_TEXT,
            }
        )
        retriever._ensure_minimum_evidence = AsyncMock(return_value=({"0": []}, []))

        with patch(
            "app.utils.query_planner.get_query_planner",
            return_value=_ForgetfulPlanner(),
        ), caplog.at_level(logging.WARNING, logger="app.pipeline.retrieve"):
            await retriever.retrieve_evidence_for_claims([claim])

        shortfall = [r.message for r in caplog.records if "Lane shortfall" in r.message]
        assert shortfall, "a silently unsearched element produced no warning"
        assert "'e2'" in shortfall[0]
