"""Tests for pipeline runner — Phase 2, save_check_results_async, and executor helpers.

Covers:
- save_check_results_async: status, claim/evidence persistence, missing-check path
- run_pipeline_phase2 focused mode: state passthrough, decompose, retrieve, mapping, result shape
- run_pipeline_phase2 article mode: DB reload, missing check, selected-only filtering
- Executor helpers: _run_async_in_thread, _run_async_in_thread_with_timeout, run_in_executor
"""

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch, call

import pytest

from app.pipeline.runner import (
    _run_async_in_thread,
    _run_async_in_thread_with_timeout,
    run_in_executor,
    save_check_results_async,
    run_pipeline_phase2,
    PipelineError,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_session(check=None, db_claims=None):
    """Build an AsyncMock session that returns `check` on first execute
    and `db_claims` on claims query.
    """
    session = AsyncMock()

    # For the check query (scalar_one_or_none)
    check_result = MagicMock()
    check_result.scalar_one_or_none.return_value = check

    # For the claims query (scalars().all())
    claims_result = MagicMock()
    claims_scalars = MagicMock()
    claims_scalars.all.return_value = db_claims or []
    claims_result.scalars.return_value = claims_scalars

    # sequence: first execute -> check query; second -> existing claims for deletion; third -> delete evidence; etc.
    session.execute = AsyncMock(side_effect=[check_result, claims_result])
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()

    return session


def _make_phase1_state(**overrides):
    """Minimal _phase1_state dict for focused-mode tests."""
    base = {
        "claims": [
            {
                "text": "Test claim",
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
        ],
        "selected_claims": [
            {
                "text": "Test claim",
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
        ],
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
    base.update(overrides)
    return base


def _make_mock_check(check_id="check-1", status="processing", **kwargs):
    """Build a MagicMock resembling a Check DB row."""
    check = MagicMock()
    check.id = check_id
    check.status = status
    check.entry_mode = kwargs.get("entry_mode", "article")
    check.input_content = kwargs.get("input_content")
    check.article_excerpt = kwargs.get("article_excerpt", "Some excerpt")
    check.input_url = kwargs.get("input_url")
    check.article_domain = kwargs.get("article_domain")
    check.article_secondary_domains = kwargs.get("article_secondary_domains")
    check.article_jurisdiction = kwargs.get("article_jurisdiction")
    check.article_classification_confidence = kwargs.get(
        "article_classification_confidence"
    )
    check.article_classification_source = kwargs.get("article_classification_source")
    return check


# ===========================================================================
# save_check_results_async
# ===========================================================================


class TestSaveCheckResultsAsync:
    """Tests for save_check_results_async — DB persistence of pipeline output."""

    @pytest.mark.asyncio
    async def test_sets_status_completed(self):
        mock_check = _make_mock_check()
        session = _make_mock_session(check=mock_check)

        results = {"claims": [], "processing_time_ms": 1234}
        await save_check_results_async("check-1", results, session)

        assert mock_check.status == "completed"
        assert mock_check.completed_at is not None
        assert mock_check.processing_time_ms == 1234

    @pytest.mark.asyncio
    async def test_deletes_skeleton_claims(self):
        """Existing Phase 1 skeleton claims are deleted before saving new ones."""
        mock_check = _make_mock_check()
        existing_claim = MagicMock()
        existing_claim.id = "old-claim-1"

        session = AsyncMock()

        # Build mock results for execute calls:
        # 1. check lookup
        check_result = MagicMock()
        check_result.scalar_one_or_none.return_value = mock_check

        # 2. existing claims query
        claims_scalars = MagicMock()
        claims_scalars.all.return_value = [existing_claim]
        claims_result = MagicMock()
        claims_result.scalars.return_value = claims_scalars

        # 3+4. delete evidence + delete claims
        delete_result1 = MagicMock()
        delete_result2 = MagicMock()

        session.execute = AsyncMock(
            side_effect=[check_result, claims_result, delete_result1, delete_result2]
        )
        session.add = MagicMock()
        session.flush = AsyncMock()
        session.commit = AsyncMock()

        results = {"claims": [], "processing_time_ms": 100}
        await save_check_results_async("check-1", results, session)

        # At least 4 execute calls: check lookup, claims lookup, delete evidence, delete claims
        assert session.execute.call_count >= 4

    @pytest.mark.asyncio
    async def test_saves_claims_with_claim_maps(self):
        """New Claim objects are created and added to the session."""
        mock_check = _make_mock_check()
        session = AsyncMock()

        check_result = MagicMock()
        check_result.scalar_one_or_none.return_value = mock_check
        claims_scalars = MagicMock()
        claims_scalars.all.return_value = []
        claims_result = MagicMock()
        claims_result.scalars.return_value = claims_scalars

        # execute is called for: check lookup, existing claims lookup
        session.execute = AsyncMock(side_effect=[check_result, claims_result])
        added_objects = []
        session.add = MagicMock(side_effect=lambda obj: added_objects.append(obj))
        session.flush = AsyncMock()
        session.commit = AsyncMock()

        results = {
            "claims": [
                {
                    "text": "Earth is round",
                    "position": 0,
                    "claim_map": {"claim_type": "factual", "elements": []},
                    "evidence": [],
                }
            ],
            "processing_time_ms": 500,
        }

        await save_check_results_async("check-1", results, session)

        # At least one object was added (the Claim)
        assert len(added_objects) >= 1
        claim_obj = added_objects[0]
        assert claim_obj.text == "Earth is round"
        assert claim_obj.check_id == "check-1"
        assert claim_obj.position == 0

    @pytest.mark.asyncio
    async def test_saves_evidence_items(self):
        """Evidence objects are created for each claim's evidence."""
        mock_check = _make_mock_check()
        session = AsyncMock()

        check_result = MagicMock()
        check_result.scalar_one_or_none.return_value = mock_check
        claims_scalars = MagicMock()
        claims_scalars.all.return_value = []
        claims_result = MagicMock()
        claims_result.scalars.return_value = claims_scalars

        session.execute = AsyncMock(side_effect=[check_result, claims_result])
        added_objects = []
        session.add = MagicMock(side_effect=lambda obj: added_objects.append(obj))
        session.flush = AsyncMock()
        session.commit = AsyncMock()

        results = {
            "claims": [
                {
                    "text": "Test claim",
                    "position": 0,
                    "evidence": [
                        {
                            "evidence_id": "ev-abc",
                            "source": "Reuters",
                            "url": "https://reuters.com/article",
                            "title": "Article",
                            "snippet": "Evidence text",
                            "relevance_score": 0.85,
                        },
                        {
                            "evidence_id": "ev-def",
                            "source": "AP",
                            "url": "https://ap.com/article",
                            "title": "AP Article",
                            "snippet": "More evidence",
                            "relevance_score": 0.72,
                        },
                    ],
                }
            ],
            "processing_time_ms": 300,
        }

        await save_check_results_async("check-1", results, session)

        # 1 Claim + 2 Evidence = 3 objects added
        assert len(added_objects) >= 3
        # First added is the Claim, next two are Evidence
        ev_objects = [o for o in added_objects if hasattr(o, "evidence_id")]
        assert len(ev_objects) == 2
        assert ev_objects[0].evidence_id == "ev-abc"
        assert ev_objects[0].source == "Reuters"

    @pytest.mark.asyncio
    async def test_missing_check_logs_warning(self):
        """Check not found in DB logs error and returns without crash."""
        session = _make_mock_session(check=None)

        results = {"claims": [], "processing_time_ms": 0}
        # Should not raise
        await save_check_results_async("nonexistent", results, session)


# ===========================================================================
# run_pipeline_phase2 — focused mode
# ===========================================================================


_PHASE2_PATCHES = {
    "retrieve": "app.workers.pipeline.retrieve_evidence_with_cache",
    "factcheck": "app.workers.pipeline.search_factchecks_for_claims",
    "analyzer_cls": "app.pipeline.claim_map_analyzer.ClaimMapAnalyzer",
    "save": "app.pipeline.runner.save_check_results_async",
    "log_stage": "app.pipeline.runner._log_stage_transition",
    "notify": "app.pipeline.runner.send_success_notifications",
    "settings": "app.pipeline.runner.settings",
}


def _mock_analyzer():
    """Build a mock ClaimMapAnalyzer with decompose + map stubs."""
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


def _mock_retrieval_result():
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
                    "relevance_score": round(0.9 - i * 0.05, 2),
                }
                for i in range(5)
            ]
        },
        "raw_evidence": [],
        "raw_sources_count": 0,
        "pre_weighting_evidence": {},
    }


def _make_settings_mock():
    """Build a MagicMock for app settings with all pipeline flags off."""
    s = MagicMock()
    s.ENABLE_FACTCHECK_API = False
    s.ENABLE_LLM_RELEVANCE_SCORER = False
    s.ENABLE_EVIDENCE_CLASSIFIER = False
    s.ENABLE_SEARCH_CLARITY = False
    s.ENVIRONMENT = "test"
    # Pipeline limits (Track N Phase 2)
    s.MIN_EVIDENCE_POST_FILTER = 5
    s.RECOVERY_MAX_CLAIMS = 3
    s.RECOVERY_MAX_ELEMENTS_PER_CLAIM = 5
    s.RECOVERY_TIMEOUT_SECONDS = 20
    s.ENABLE_RECOVERY_QUERY_PLANNING = True
    s.RECOVERY_PLANNER_TIMEOUT = 10.0
    return s


class TestRunPipelinePhase2Focused:
    """run_pipeline_phase2 with _phase1_state provided (focused mode)."""

    @pytest.mark.asyncio
    async def test_focused_mode_uses_phase1_state(self):
        """No DB reload when _phase1_state is provided."""
        state = _make_phase1_state()
        mock_analyzer = _mock_analyzer()
        mock_analyzer_cls = MagicMock(return_value=mock_analyzer)
        mock_settings = _make_settings_mock()
        progress = AsyncMock()
        progress.report_progress = AsyncMock()

        with patch(_PHASE2_PATCHES["analyzer_cls"], mock_analyzer_cls), patch(
            _PHASE2_PATCHES["retrieve"],
            new_callable=AsyncMock,
            return_value=_mock_retrieval_result(),
        ), patch(
            _PHASE2_PATCHES["factcheck"], new_callable=AsyncMock, return_value={}
        ), patch(
            _PHASE2_PATCHES["log_stage"], new_callable=AsyncMock
        ), patch(
            _PHASE2_PATCHES["settings"], mock_settings
        ):

            result = await run_pipeline_phase2(
                check_id="check-1",
                user_id="user-1",
                input_data={},
                progress_reporter=progress,
                _phase1_state=state,
            )

            assert result is not None
            assert result["entry_mode"] == "focused"

    @pytest.mark.asyncio
    async def test_decompose_called(self):
        """ClaimMapAnalyzer.decompose_claims_batch is invoked."""
        state = _make_phase1_state()
        mock_analyzer = _mock_analyzer()
        mock_analyzer_cls = MagicMock(return_value=mock_analyzer)
        mock_settings = _make_settings_mock()
        progress = AsyncMock()
        progress.report_progress = AsyncMock()

        with patch(_PHASE2_PATCHES["analyzer_cls"], mock_analyzer_cls), patch(
            _PHASE2_PATCHES["retrieve"],
            new_callable=AsyncMock,
            return_value=_mock_retrieval_result(),
        ), patch(
            _PHASE2_PATCHES["factcheck"], new_callable=AsyncMock, return_value={}
        ), patch(
            _PHASE2_PATCHES["log_stage"], new_callable=AsyncMock
        ), patch(
            _PHASE2_PATCHES["settings"], mock_settings
        ):

            await run_pipeline_phase2(
                check_id="check-1",
                user_id="user-1",
                input_data={},
                progress_reporter=progress,
                _phase1_state=state,
            )

            mock_analyzer.decompose_claims_batch.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_retrieve_called(self):
        """retrieve_evidence_with_cache is invoked."""
        state = _make_phase1_state()
        mock_analyzer = _mock_analyzer()
        mock_analyzer_cls = MagicMock(return_value=mock_analyzer)
        mock_settings = _make_settings_mock()
        mock_retrieve = AsyncMock(return_value=_mock_retrieval_result())
        progress = AsyncMock()
        progress.report_progress = AsyncMock()

        with patch(_PHASE2_PATCHES["analyzer_cls"], mock_analyzer_cls), patch(
            _PHASE2_PATCHES["retrieve"], mock_retrieve
        ), patch(
            _PHASE2_PATCHES["factcheck"], new_callable=AsyncMock, return_value={}
        ), patch(
            _PHASE2_PATCHES["log_stage"], new_callable=AsyncMock
        ), patch(
            _PHASE2_PATCHES["settings"], mock_settings
        ):

            await run_pipeline_phase2(
                check_id="check-1",
                user_id="user-1",
                input_data={},
                progress_reporter=progress,
                _phase1_state=state,
            )

            mock_retrieve.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_returns_result_shape(self):
        """Result dict has claims, api_stats, processing_time_ms keys."""
        state = _make_phase1_state()
        mock_analyzer = _mock_analyzer()
        mock_analyzer_cls = MagicMock(return_value=mock_analyzer)
        mock_settings = _make_settings_mock()
        progress = AsyncMock()
        progress.report_progress = AsyncMock()

        with patch(_PHASE2_PATCHES["analyzer_cls"], mock_analyzer_cls), patch(
            _PHASE2_PATCHES["retrieve"],
            new_callable=AsyncMock,
            return_value=_mock_retrieval_result(),
        ), patch(
            _PHASE2_PATCHES["factcheck"], new_callable=AsyncMock, return_value={}
        ), patch(
            _PHASE2_PATCHES["log_stage"], new_callable=AsyncMock
        ), patch(
            _PHASE2_PATCHES["settings"], mock_settings
        ):

            result = await run_pipeline_phase2(
                check_id="check-1",
                user_id="user-1",
                input_data={},
                progress_reporter=progress,
                _phase1_state=state,
            )

            assert "claims" in result
            assert "api_stats" in result
            assert "processing_time_ms" in result
            assert "entry_mode" in result
            assert isinstance(result["claims"], list)
            assert isinstance(result["processing_time_ms"], int)

    @pytest.mark.asyncio
    async def test_evidence_mapping_called(self):
        """map_evidence_batch is invoked after retrieve."""
        state = _make_phase1_state()
        mock_analyzer = _mock_analyzer()
        mock_analyzer_cls = MagicMock(return_value=mock_analyzer)
        mock_settings = _make_settings_mock()
        progress = AsyncMock()
        progress.report_progress = AsyncMock()

        with patch(_PHASE2_PATCHES["analyzer_cls"], mock_analyzer_cls), patch(
            _PHASE2_PATCHES["retrieve"],
            new_callable=AsyncMock,
            return_value=_mock_retrieval_result(),
        ), patch(
            _PHASE2_PATCHES["factcheck"], new_callable=AsyncMock, return_value={}
        ), patch(
            _PHASE2_PATCHES["log_stage"], new_callable=AsyncMock
        ), patch(
            _PHASE2_PATCHES["settings"], mock_settings
        ):

            await run_pipeline_phase2(
                check_id="check-1",
                user_id="user-1",
                input_data={},
                progress_reporter=progress,
                _phase1_state=state,
            )

            mock_analyzer.map_evidence_batch.assert_awaited_once()


# ===========================================================================
# run_pipeline_phase2 — article mode (DB reload)
# ===========================================================================


class TestRunPipelinePhase2ArticleMode:
    """run_pipeline_phase2 without _phase1_state — reloads from DB."""

    @pytest.mark.asyncio
    async def test_reloads_from_db_when_no_state(self):
        """_phase1_state=None triggers DB reload for check + claims."""
        mock_check = _make_mock_check(check_id="check-art")
        mock_check.input_content = None

        db_claim = MagicMock()
        db_claim.text = "DB claim"
        db_claim.position = 0
        db_claim.is_selected = True
        db_claim.significance_rank = 1
        db_claim.significance_score = 0.8
        db_claim.claim_type = "factual"
        db_claim.subject_context = None
        db_claim.key_entities = []
        db_claim.source_title = None
        db_claim.source_url = None
        db_claim.source_date = None
        db_claim.rhetorical_context = None
        db_claim.has_rhetorical_context = False
        db_claim.rhetorical_style = None

        # Build mock session returned by async_session context manager
        mock_session = AsyncMock()

        check_result = MagicMock()
        check_result.scalar_one_or_none.return_value = mock_check
        claims_scalars = MagicMock()
        claims_scalars.all.return_value = [db_claim]
        claims_result = MagicMock()
        claims_result.scalars.return_value = claims_scalars

        mock_session.execute = AsyncMock(side_effect=[check_result, claims_result])
        mock_session.commit = AsyncMock()

        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)

        mock_analyzer = _mock_analyzer()
        mock_analyzer_cls = MagicMock(return_value=mock_analyzer)

        progress = AsyncMock()
        progress.report_progress = AsyncMock()

        mock_settings = _make_settings_mock()

        with patch("app.pipeline.runner.async_session", return_value=mock_ctx), patch(
            _PHASE2_PATCHES["analyzer_cls"], mock_analyzer_cls
        ), patch(
            _PHASE2_PATCHES["retrieve"],
            new_callable=AsyncMock,
            return_value=_mock_retrieval_result(),
        ), patch(
            _PHASE2_PATCHES["factcheck"], new_callable=AsyncMock, return_value={}
        ), patch(
            _PHASE2_PATCHES["log_stage"], new_callable=AsyncMock
        ), patch(
            _PHASE2_PATCHES["settings"], mock_settings
        ), patch(
            "app.pipeline.runner.get_cache_service",
            new_callable=AsyncMock,
            return_value=None,
        ), patch(
            "app.pipeline.evidence_ledger.get_ledger", return_value=None
        ):

            result = await run_pipeline_phase2(
                check_id="check-art",
                user_id="user-1",
                input_data={},
                progress_reporter=progress,
                _phase1_state=None,
            )

            # DB was queried
            assert mock_session.execute.call_count == 2
            assert result["entry_mode"] == "article"

    @pytest.mark.asyncio
    async def test_missing_check_raises(self):
        """Check not found in DB raises PipelineError."""
        mock_session = AsyncMock()

        check_result = MagicMock()
        check_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=check_result)

        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)

        progress = AsyncMock()
        progress.report_progress = AsyncMock()

        with patch("app.pipeline.runner.async_session", return_value=mock_ctx), patch(
            "app.pipeline.runner.get_cache_service",
            new_callable=AsyncMock,
            return_value=None,
        ), patch("app.pipeline.evidence_ledger.get_ledger", return_value=None):
            with pytest.raises(PipelineError, match="not found"):
                await run_pipeline_phase2(
                    check_id="missing-id",
                    user_id="user-1",
                    input_data={},
                    progress_reporter=progress,
                    _phase1_state=None,
                )

    @pytest.mark.asyncio
    async def test_loads_only_selected_claims(self):
        """Only is_selected=True claims appear in selected_claims."""
        mock_check = _make_mock_check()
        mock_check.input_content = None

        selected_claim = MagicMock()
        selected_claim.text = "Selected"
        selected_claim.position = 0
        selected_claim.is_selected = True
        selected_claim.significance_rank = 1
        selected_claim.significance_score = 0.9
        selected_claim.claim_type = "factual"
        selected_claim.subject_context = None
        selected_claim.key_entities = []
        selected_claim.source_title = None
        selected_claim.source_url = None
        selected_claim.source_date = None
        selected_claim.rhetorical_context = None
        selected_claim.has_rhetorical_context = False
        selected_claim.rhetorical_style = None

        unselected_claim = MagicMock()
        unselected_claim.text = "Unselected"
        unselected_claim.position = 1
        unselected_claim.is_selected = False
        unselected_claim.significance_rank = 2
        unselected_claim.significance_score = 0.3
        unselected_claim.claim_type = "opinion"
        unselected_claim.subject_context = None
        unselected_claim.key_entities = []
        unselected_claim.source_title = None
        unselected_claim.source_url = None
        unselected_claim.source_date = None
        unselected_claim.rhetorical_context = None
        unselected_claim.has_rhetorical_context = False
        unselected_claim.rhetorical_style = None

        mock_session = AsyncMock()
        check_result = MagicMock()
        check_result.scalar_one_or_none.return_value = mock_check
        claims_scalars = MagicMock()
        claims_scalars.all.return_value = [selected_claim, unselected_claim]
        claims_result = MagicMock()
        claims_result.scalars.return_value = claims_scalars

        mock_session.execute = AsyncMock(side_effect=[check_result, claims_result])
        mock_session.commit = AsyncMock()

        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)

        mock_analyzer = _mock_analyzer()
        mock_analyzer_cls = MagicMock(return_value=mock_analyzer)

        progress = AsyncMock()
        progress.report_progress = AsyncMock()

        mock_settings = _make_settings_mock()

        with patch("app.pipeline.runner.async_session", return_value=mock_ctx), patch(
            _PHASE2_PATCHES["analyzer_cls"], mock_analyzer_cls
        ), patch(
            _PHASE2_PATCHES["retrieve"],
            new_callable=AsyncMock,
            return_value=_mock_retrieval_result(),
        ), patch(
            _PHASE2_PATCHES["factcheck"], new_callable=AsyncMock, return_value={}
        ), patch(
            _PHASE2_PATCHES["log_stage"], new_callable=AsyncMock
        ), patch(
            _PHASE2_PATCHES["settings"], mock_settings
        ), patch(
            "app.pipeline.runner.get_cache_service",
            new_callable=AsyncMock,
            return_value=None,
        ), patch(
            "app.pipeline.evidence_ledger.get_ledger", return_value=None
        ):

            result = await run_pipeline_phase2(
                check_id="check-1",
                user_id="user-1",
                input_data={},
                progress_reporter=progress,
                _phase1_state=None,
            )

            # Result should contain both claims (all) but only 1 selected
            assert result["selected_claims_count"] == 1
            assert len(result["claims"]) == 2


# ===========================================================================
# Executor helpers
# ===========================================================================


class TestExecutorHelpers:
    """Tests for _run_async_in_thread, _run_async_in_thread_with_timeout, run_in_executor."""

    def test_run_async_in_thread(self):
        """Runs an async function and returns the result."""

        async def simple_coro():
            return 42

        result = _run_async_in_thread(simple_coro)
        assert result == 42

    def test_run_async_in_thread_with_args(self):
        """Passes args through correctly."""

        async def add(a, b):
            return a + b

        result = _run_async_in_thread(add, 3, 7)
        assert result == 10

    def test_run_async_in_thread_with_timeout_success(self):
        """Completes before timeout — returns result normally."""

        async def fast_coro():
            return "fast"

        result = _run_async_in_thread_with_timeout(fast_coro, 5.0)
        assert result == "fast"

    def test_run_async_in_thread_with_timeout_fires(self):
        """Exceeds timeout — raises TimeoutError (or asyncio.TimeoutError)."""

        async def slow_coro():
            await asyncio.sleep(10)
            return "never"

        with pytest.raises((asyncio.TimeoutError, TimeoutError)):
            _run_async_in_thread_with_timeout(slow_coro, 0.1)

    @pytest.mark.asyncio
    async def test_run_in_executor(self):
        """Submits async function to thread pool and returns result."""

        async def coro_for_executor():
            return "from_executor"

        result = await run_in_executor(coro_for_executor)
        assert result == "from_executor"
