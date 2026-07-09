"""F-R2e: the retrieval query plan must reach the persisted claim_map.

The TRU-C051-3024 investigation had to diagnose the web-retrieval path blind:
only queries that RETURNED evidence left a DB trace (metadata.query_used on
surviving items). Zero-yield queries — the diagnostic case — vanished. The
fix writes the merged per-element query plan (queries / element_ids /
freshness, parallel arrays) onto claim_map.metadata.query_plan at
result-build time.

Wired test: drives run_pipeline_phase2 with the retrieve stage mutating the
claim dicts exactly as the real retriever does (claims[i]["query_plan"] =
merged_plan, retrieve.py:396), then asserts the plan appears inside the
final result's claim_map — the same object save_check_results_async persists
to the Claim.claim_map JSONB column.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.pipeline.runner import run_pipeline_phase2
from tests.unit.pipeline.test_recovery_freshness import (
    _PATCHES,
    _mock_analyzer,
    _phase1_state,
    _settings_mock,
)

_PLAN = {
    "queries": [
        "doctors red wine daily recommendation history",
        "physicians prescribed red wine heart",
    ],
    "query_element_ids": ["e1", "e1"],
    "query_freshness": ["py", "none"],
    "freshness": "py",
    "reasoning": "test",
    "claim_index": 0,
}


def _retrieval_result_with_plan_mutation(claims_seen):
    """Side-effect mimicking retrieve.py:396 — attach query_plan to the
    claim dicts in place, return a healthy (non-thin) pool."""

    async def _side_effect(claims, *args, **kwargs):
        claims_seen.extend(claims)
        for claim in claims:
            claim["query_plan"] = dict(_PLAN)
        return {
            "evidence_by_claim": {
                "0": [
                    {
                        "evidence_id": f"ev-{i:03d}",
                        "url": f"https://example.com/{i}",
                        "title": f"Source {i}",
                        "text": f"Evidence text {i}",
                        "snippet": f"Evidence text {i}",
                        "source": "Serper",
                        "relevance_score": 0.9,
                    }
                    for i in range(5)
                ]
            },
            "raw_evidence": [],
            "raw_sources_count": 0,
            "pre_weighting_evidence": {},
        }

    return _side_effect


class TestQueryPlanPersistence:
    @pytest.mark.asyncio
    async def test_query_plan_lands_in_claim_map_metadata(self):
        claims_seen = []
        progress = AsyncMock()
        progress.report_progress = AsyncMock()

        with patch(
            _PATCHES["analyzer_cls"], MagicMock(return_value=_mock_analyzer())
        ), patch(
            _PATCHES["retrieve"],
            new=AsyncMock(
                side_effect=_retrieval_result_with_plan_mutation(claims_seen)
            ),
        ), patch(
            _PATCHES["log_stage"], new_callable=AsyncMock
        ), patch(
            _PATCHES["settings"], _settings_mock()
        ):
            result = await run_pipeline_phase2(
                check_id="check-1",
                user_id="user-1",
                input_data={},
                progress_reporter=progress,
                _phase1_state=_phase1_state("Test claim about something"),
            )

        assert result is not None
        assert claims_seen, "retrieve mock never received claim dicts"

        claim_result = result["claims"][0]
        cm = claim_result["claim_map"]
        assert isinstance(cm, dict), "claim_map missing from result"
        persisted = cm.get("metadata", {}).get("query_plan")
        assert persisted is not None, "query_plan not written to claim_map metadata"
        assert persisted["queries"] == _PLAN["queries"]
        assert persisted["element_ids"] == _PLAN["query_element_ids"]
        assert persisted["freshness"] == _PLAN["query_freshness"]

    @pytest.mark.asyncio
    async def test_no_plan_leaves_metadata_untouched(self):
        """Claims whose planning fell back (no query_plan key) persist
        without a query_plan entry — absence is meaningful (pre-R2e shape)."""
        progress = AsyncMock()
        progress.report_progress = AsyncMock()

        async def _plain_retrieval(claims, *args, **kwargs):
            return {
                "evidence_by_claim": {
                    "0": [
                        {
                            "evidence_id": f"ev-{i:03d}",
                            "url": f"https://example.com/{i}",
                            "title": f"Source {i}",
                            "text": f"Evidence text {i}",
                            "snippet": f"Evidence text {i}",
                            "source": "Serper",
                            "relevance_score": 0.9,
                        }
                        for i in range(5)
                    ]
                },
                "raw_evidence": [],
                "raw_sources_count": 0,
                "pre_weighting_evidence": {},
            }

        with patch(
            _PATCHES["analyzer_cls"], MagicMock(return_value=_mock_analyzer())
        ), patch(
            _PATCHES["retrieve"], new=AsyncMock(side_effect=_plain_retrieval)
        ), patch(
            _PATCHES["log_stage"], new_callable=AsyncMock
        ), patch(
            _PATCHES["settings"], _settings_mock()
        ):
            result = await run_pipeline_phase2(
                check_id="check-1",
                user_id="user-1",
                input_data={},
                progress_reporter=progress,
                _phase1_state=_phase1_state("Test claim about something"),
            )

        cm = result["claims"][0]["claim_map"]
        assert "query_plan" not in (cm.get("metadata") or {})
