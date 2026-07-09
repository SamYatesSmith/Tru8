"""F-R2f wired-seam tests: Stage 3.8 post-filter recovery freshness.

The defect (TRU-C051-3024, audit/2026-07-09_retrieval_quality_plan.md): the
recovery backfill re-searched the raw claim text with a hardcoded
``freshness="py"``, so a HISTORICAL claim whose pool the scorer had emptied
was backfilled exclusively with past-year social chatter (reddit/tiktok).

The fix derives recovery freshness mechanically: historical marker in the
claim text → ``"none"`` (unwindowed), otherwise the original ``"py"``.

These tests drive run_pipeline_phase2 with a thin evidence pool so the real
Stage 3.8 block executes, and assert on the freshness that actually reaches
SearchService.search_for_evidence — the wired seam, not a helper in
isolation (NF-18 lesson).
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.pipeline.runner import run_pipeline_phase2


_PATCHES = {
    "retrieve": "app.workers.pipeline.retrieve_evidence_with_cache",
    "analyzer_cls": "app.pipeline.claim_map_analyzer.ClaimMapAnalyzer",
    "log_stage": "app.pipeline.runner._log_stage_transition",
    "settings": "app.pipeline.runner.settings",
    # Stage 3.8 imports these inside the block
    "search_service": "app.services.search.SearchService",
    "blocked_domains": "app.services.evidence.get_runtime_blocked_domains",
}


def _phase1_state(claim_text):
    claim = {
        "text": claim_text,
        "position": 0,
        "is_selected": True,
        "significance_rank": 1,
        "significance_score": 0.9,
        "claim_type": "factual",
        "subject_context": None,
        "key_entities": [],
        "source_title": None,
        "source_url": None,
        "source_date": None,
        "rhetorical_analysis": None,
        "has_rhetorical_context": False,
        "rhetorical_style": None,
    }
    return {
        "claims": [claim],
        "selected_claims": [claim],
        "content": {"content": "test content", "metadata": {"url": None}},
        "article_classification": None,
        "entry_mode": "focused",
        "frozen_evidence": None,
        "frozen_evidence_claim_texts": {},
        "_replay_temp_token": None,
        "_replay_evidence_token": None,
        "cache_service": None,
        "ledger": None,
        "start_time": datetime.now(timezone.utc),
        "stage_timings": {},
    }


def _thin_retrieval_result():
    """One evidence item — below MIN_EVIDENCE_POST_FILTER, so Stage 3.8 fires."""
    return {
        "evidence_by_claim": {
            "0": [
                {
                    "evidence_id": "ev-001",
                    "url": "https://example.com/1",
                    "title": "Source 1",
                    "text": "Evidence text",
                    "snippet": "Evidence text",
                    "source": "Serper",
                    "relevance_score": 0.9,
                }
            ]
        },
        "raw_evidence": [],
        "raw_sources_count": 0,
        "pre_weighting_evidence": {},
    }


def _mock_analyzer():
    analyzer = AsyncMock()
    analyzer.decompose_claims_batch = AsyncMock(
        return_value={
            "0": {
                "normalised_claim": "Test claim",
                "claim_type": "factual",
                "elements": [
                    {
                        "element_id": "e1",
                        "description": "Element 1",
                        "evidence_refs": [],
                        "state": "supported",
                    }
                ],
                "orientation": None,
            }
        }
    )
    analyzer.map_evidence_batch = AsyncMock(return_value=None)
    analyzer.get_token_usage = MagicMock(
        return_value={"input_tokens": 0, "output_tokens": 0}
    )
    return analyzer


def _settings_mock():
    s = MagicMock()
    s.ENABLE_FACTCHECK_API = False
    s.ENABLE_LLM_RELEVANCE_SCORER = False
    s.ENABLE_EVIDENCE_CLASSIFIER = False
    s.ENABLE_SEARCH_CLARITY = False
    s.ENVIRONMENT = "test"
    s.MIN_EVIDENCE_POST_FILTER = 5  # pool of 1 is thin -> Stage 3.8 fires
    s.RECOVERY_MAX_CLAIMS = 3
    s.RECOVERY_MAX_ELEMENTS_PER_CLAIM = 5
    s.RECOVERY_TIMEOUT_SECONDS = 20
    s.ENABLE_RECOVERY_QUERY_PLANNING = True
    s.RECOVERY_PLANNER_TIMEOUT = 10.0
    return s


async def _run_and_capture_freshness(claim_text):
    """Run phase 2 with a thin pool; return the freshness kwarg that reached
    SearchService.search_for_evidence in the Stage 3.8 block."""
    search_instance = MagicMock()
    search_instance.search_for_evidence = AsyncMock(return_value=[])
    progress = AsyncMock()
    progress.report_progress = AsyncMock()

    with patch(
        _PATCHES["analyzer_cls"], MagicMock(return_value=_mock_analyzer())
    ), patch(
        _PATCHES["retrieve"],
        new_callable=AsyncMock,
        return_value=_thin_retrieval_result(),
    ), patch(
        _PATCHES["log_stage"], new_callable=AsyncMock
    ), patch(
        _PATCHES["settings"], _settings_mock()
    ), patch(
        _PATCHES["search_service"], MagicMock(return_value=search_instance)
    ), patch(
        _PATCHES["blocked_domains"], MagicMock(return_value=set())
    ):
        result = await run_pipeline_phase2(
            check_id="check-1",
            user_id="user-1",
            input_data={},
            progress_reporter=progress,
            _phase1_state=_phase1_state(claim_text),
        )

    assert result is not None
    assert search_instance.search_for_evidence.await_count >= 1, (
        "Stage 3.8 recovery search did not fire — the wired seam was not "
        "exercised; check MIN_EVIDENCE_POST_FILTER / thin-pool setup"
    )
    _, kwargs = search_instance.search_for_evidence.await_args
    return kwargs.get("freshness")


class TestRecoveryFreshness:
    @pytest.mark.asyncio
    async def test_historical_claim_recovery_is_unwindowed(self):
        """The TRU-C051-3024 shape: 'historically' with no year → the
        recovery search must run without a recency window."""
        freshness = await _run_and_capture_freshness(
            "Many doctors historically recommended a daily glass of red wine"
        )
        assert freshness == "none"

    @pytest.mark.asyncio
    async def test_non_historical_claim_keeps_py_window(self):
        """Recency behaviour for ordinary claims is unchanged."""
        freshness = await _run_and_capture_freshness(
            "Moderate alcohol consumption protects against heart disease"
        )
        assert freshness == "py"
