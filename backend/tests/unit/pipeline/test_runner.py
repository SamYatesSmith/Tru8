"""Tests for pipeline runner: helpers, error paths, and phase1 logic."""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.pipeline.runner import (
    PipelineError,
    _aggregate_api_stats,
    _log_stage_transition,
    _run_async_in_thread,
    _run_async_in_thread_with_timeout,
    get_user_friendly_error,
    handle_pipeline_failure,
    refund_check_credit_async,
    run_pipeline,
    run_pipeline_phase1,
    send_success_notifications,
)


# ── Helpers ─────────────────────────────────────────────────────────────────


def _mock_async_session(check=None, user=None):
    """Build a mock async_session context manager that returns mocked query results."""
    session = AsyncMock()

    call_count = {"n": 0}

    async def _execute_side_effect(stmt):
        call_count["n"] += 1
        result = MagicMock()
        # First call returns check, second returns user
        if call_count["n"] == 1:
            result.scalar_one_or_none.return_value = check
        else:
            result.scalar_one_or_none.return_value = user
        return result

    session.execute = AsyncMock(side_effect=_execute_side_effect)
    session.commit = AsyncMock()
    session.add = MagicMock()

    ctx = AsyncMock()
    ctx.__aenter__ = AsyncMock(return_value=session)
    ctx.__aexit__ = AsyncMock(return_value=False)

    return ctx, session


# ── get_user_friendly_error ─────────────────────────────────────────────────


class TestGetUserFriendlyError:
    def test_cookie_wall(self):
        err = Exception("cookie_consent_wall blocked us")
        msg = get_user_friendly_error(err)
        assert "cookie consent" in msg.lower()

    def test_paywall(self):
        err = Exception("paywall detected on page")
        msg = get_user_friendly_error(err)
        assert "paywall" in msg.lower()

    def test_connection_error(self):
        err = Exception("connection_error occurred")
        msg = get_user_friendly_error(err)
        assert "couldn't reach" in msg.lower()

    def test_no_claims(self):
        err = Exception("no_claims found in text")
        msg = get_user_friendly_error(err)
        assert "claims" in msg.lower()

    def test_timeout(self):
        err = Exception("timeout exceeded waiting for response")
        msg = get_user_friendly_error(err)
        assert "too long" in msg.lower()

    def test_unknown_error_generic(self):
        """Unknown errors return generic message — no raw error text leaked."""
        err = Exception("sql_injection_attack; SELECT * FROM users;")
        msg = get_user_friendly_error(err)
        assert "Something went wrong" in msg
        assert "sql_injection" not in msg
        assert "SELECT" not in msg


# ── PipelineError ───────────────────────────────────────────────────────────


class TestPipelineError:
    def test_constructor_defaults(self):
        err = PipelineError("something broke")
        assert err.message == "something broke"
        assert err.stage == "unknown"
        assert err.recoverable is False
        assert str(err) == "something broke"

    def test_constructor_custom(self):
        err = PipelineError("timeout", stage="ingest", recoverable=True)
        assert err.stage == "ingest"
        assert err.recoverable is True
        assert isinstance(err, Exception)


# ── _aggregate_api_stats ────────────────────────────────────────────────────


class TestAggregateApiStats:
    def test_aggregates_api_names(self):
        """Deduplicates API names across claims, sums results."""
        claims = [
            {
                "api_stats": {
                    "apis_queried": [{"name": "serper", "results": 3}],
                    "total_api_calls": 1,
                    "total_api_results": 3,
                }
            },
            {
                "api_stats": {
                    "apis_queried": [
                        {"name": "serper", "results": 2},
                        {"name": "brave", "results": 1},
                    ],
                    "total_api_calls": 2,
                    "total_api_results": 3,
                }
            },
        ]
        evidence = {"0": [{"external_source_provider": "serper"}]}
        stats = _aggregate_api_stats(claims, evidence)
        api_names = [a["name"] for a in stats["apis_queried"]]
        assert "serper" in api_names
        assert "brave" in api_names
        assert len(stats["apis_queried"]) == 2
        # Serper results merged: 3 + 2 = 5
        serper = next(a for a in stats["apis_queried"] if a["name"] == "serper")
        assert serper["results"] == 5

    def test_sums_totals(self):
        claims = [
            {
                "api_stats": {
                    "apis_queried": [],
                    "total_api_calls": 5,
                    "total_api_results": 10,
                }
            },
            {
                "api_stats": {
                    "apis_queried": [],
                    "total_api_calls": 3,
                    "total_api_results": 7,
                }
            },
        ]
        evidence = {}
        stats = _aggregate_api_stats(claims, evidence)
        assert stats["total_api_calls"] == 8
        assert stats["total_api_results"] == 17

    def test_coverage_percentage(self):
        claims = [
            {
                "api_stats": {
                    "apis_queried": [],
                    "total_api_calls": 0,
                    "total_api_results": 0,
                }
            }
        ]
        evidence = {
            "0": [
                {"external_source_provider": "serper"},
                {"external_source_provider": "brave"},
                {},  # no provider
                {
                    "metadata": {"external_source_provider": "noaa"}
                },  # provider in metadata
            ]
        }
        stats = _aggregate_api_stats(claims, evidence)
        assert stats["total_evidence_count"] == 4
        assert stats["api_evidence_count"] == 3
        assert stats["api_coverage_percentage"] == 75.0

    def test_empty_input(self):
        stats = _aggregate_api_stats([], {})
        assert stats["total_api_calls"] == 0
        assert stats["total_api_results"] == 0
        assert stats["total_evidence_count"] == 0
        assert stats["api_evidence_count"] == 0
        assert stats["api_coverage_percentage"] == 0.0


# ── handle_pipeline_failure ─────────────────────────────────────────────────


@pytest.mark.asyncio
class TestHandlePipelineFailure:
    @patch("app.pipeline.runner.email_notification_service")
    @patch("app.pipeline.runner.push_notification_service")
    @patch(
        "app.pipeline.runner.refund_check_credit_async",
        new_callable=AsyncMock,
        return_value=False,
    )
    @patch("app.pipeline.runner.async_session")
    async def test_sets_failed_status(
        self, mock_session_factory, mock_refund, mock_push, mock_email
    ):
        check = MagicMock()
        check.status = "processing"
        ctx, session = _mock_async_session(check)
        mock_session_factory.return_value = ctx

        await handle_pipeline_failure("chk-1", "usr-1", Exception("boom"))
        assert check.status == "failed"

    @patch("app.pipeline.runner.email_notification_service")
    @patch("app.pipeline.runner.push_notification_service")
    @patch(
        "app.pipeline.runner.refund_check_credit_async",
        new_callable=AsyncMock,
        return_value=False,
    )
    @patch("app.pipeline.runner.async_session")
    async def test_writes_user_friendly_error(
        self, mock_session_factory, mock_refund, mock_push, mock_email
    ):
        check = MagicMock()
        ctx, session = _mock_async_session(check)
        mock_session_factory.return_value = ctx

        await handle_pipeline_failure(
            "chk-1", "usr-1", Exception("timeout in pipeline")
        )
        assert "too long" in check.error_message.lower()

    @patch("app.pipeline.runner.email_notification_service")
    @patch("app.pipeline.runner.push_notification_service")
    @patch(
        "app.pipeline.runner.refund_check_credit_async",
        new_callable=AsyncMock,
        return_value=True,
    )
    @patch("app.pipeline.runner.async_session")
    async def test_refund_appended_to_message(
        self, mock_session_factory, mock_refund, mock_push, mock_email
    ):
        check = MagicMock()
        ctx, session = _mock_async_session(check)
        mock_session_factory.return_value = ctx

        await handle_pipeline_failure("chk-1", "usr-1", Exception("connection_error"))
        assert "credit has been returned" in check.error_message.lower()

    @patch("app.pipeline.runner.email_notification_service")
    @patch("app.pipeline.runner.push_notification_service")
    @patch(
        "app.pipeline.runner.refund_check_credit_async",
        new_callable=AsyncMock,
        return_value=False,
    )
    @patch("app.pipeline.runner.async_session")
    async def test_notification_failure_swallowed(
        self, mock_session_factory, mock_refund, mock_push, mock_email
    ):
        """Push/email errors are swallowed, no crash."""
        check = MagicMock()
        ctx, session = _mock_async_session(check)
        mock_session_factory.return_value = ctx

        mock_push.send_check_failed_notification_sync.side_effect = Exception(
            "push down"
        )
        mock_email.send_check_failed_email_sync.side_effect = Exception("smtp down")

        # Should not raise
        await handle_pipeline_failure("chk-1", "usr-1", Exception("timeout"))
        assert check.status == "failed"

    @patch("app.pipeline.runner.email_notification_service")
    @patch("app.pipeline.runner.push_notification_service")
    @patch(
        "app.pipeline.runner.refund_check_credit_async",
        new_callable=AsyncMock,
        return_value=False,
    )
    @patch("app.pipeline.runner.async_session")
    async def test_missing_check_no_crash(
        self, mock_session_factory, mock_refund, mock_push, mock_email
    ):
        """If check not found in DB, no crash."""
        ctx, session = _mock_async_session(check=None)
        mock_session_factory.return_value = ctx

        # Should not raise
        await handle_pipeline_failure("chk-missing", "usr-1", Exception("boom"))


# ── refund_check_credit_async ───────────────────────────────────────────────


@pytest.mark.asyncio
class TestRefundCheckCreditAsync:
    async def test_idempotent_zero_credits(self):
        """credits_used=0 returns True without modifying anything."""
        check = MagicMock()
        check.credits_used = 0

        session = AsyncMock()
        call_count = {"n": 0}

        async def _exec(stmt):
            call_count["n"] += 1
            result = MagicMock()
            result.scalar_one_or_none.return_value = check
            return result

        session.execute = AsyncMock(side_effect=_exec)

        result = await refund_check_credit_async("chk-1", "usr-1", session)
        assert result is True
        # credits_used was already 0, no user query needed
        assert call_count["n"] == 1

    async def test_increments_user_credits(self):
        check = MagicMock()
        check.credits_used = 2

        user = MagicMock()
        user.credits = 5

        session = AsyncMock()
        call_count = {"n": 0}

        async def _exec(stmt):
            call_count["n"] += 1
            result = MagicMock()
            if call_count["n"] == 1:
                result.scalar_one_or_none.return_value = check
            else:
                result.scalar_one_or_none.return_value = user
            return result

        session.execute = AsyncMock(side_effect=_exec)

        result = await refund_check_credit_async("chk-1", "usr-1", session)
        assert result is True
        assert user.credits == 7  # 5 + 2

    async def test_resets_check_credits(self):
        check = MagicMock()
        check.credits_used = 3

        user = MagicMock()
        user.credits = 10

        session = AsyncMock()
        call_count = {"n": 0}

        async def _exec(stmt):
            call_count["n"] += 1
            result = MagicMock()
            if call_count["n"] == 1:
                result.scalar_one_or_none.return_value = check
            else:
                result.scalar_one_or_none.return_value = user
            return result

        session.execute = AsyncMock(side_effect=_exec)

        await refund_check_credit_async("chk-1", "usr-1", session)
        assert check.credits_used == 0

    async def test_missing_check_returns_false(self):
        session = AsyncMock()

        async def _exec(stmt):
            result = MagicMock()
            result.scalar_one_or_none.return_value = None
            return result

        session.execute = AsyncMock(side_effect=_exec)

        result = await refund_check_credit_async("chk-missing", "usr-1", session)
        assert result is False


# ── send_success_notifications ──────────────────────────────────────────────


@pytest.mark.asyncio
class TestSendSuccessNotifications:
    @patch("app.pipeline.runner.email_notification_service")
    async def test_builds_claims_analyzed(self, mock_email):
        results = {
            "claims": [
                {
                    "text": "The earth is round",
                    "is_selected": True,
                    "claim_map": {
                        "elements": [{"id": "e1"}, {"id": "e2"}],
                        "orientation": "Supported by multiple sources",
                    },
                    "evidence": [],
                }
            ],
            "entry_mode": "focused",
            "raw_sources_count": 5,
        }
        input_data = {"url": "https://example.com"}
        content = {"metadata": {"url": "https://example.com", "title": "Test"}}

        await send_success_notifications("usr-1", "chk-1", results, input_data, content)

        mock_email.send_check_completed_email_sync.assert_called_once()
        call_kwargs = mock_email.send_check_completed_email_sync.call_args
        claims_analyzed = call_kwargs.kwargs.get("claims_analyzed") or call_kwargs[
            1
        ].get("claims_analyzed")
        # If called with positional args, extract from args
        if claims_analyzed is None:
            # Try positional
            all_args = call_kwargs[0] if call_kwargs[0] else []
            # Fallback: inspect keyword args
            claims_analyzed = call_kwargs.kwargs.get("claims_analyzed")

        assert claims_analyzed is not None
        assert len(claims_analyzed) == 1
        assert claims_analyzed[0]["text"] == "The earth is round"
        assert claims_analyzed[0]["element_count"] == 2
        assert "Supported" in claims_analyzed[0]["orientation"]

    @patch("app.pipeline.runner.email_notification_service")
    async def test_email_service_called(self, mock_email):
        results = {
            "claims": [
                {
                    "text": "Claim A",
                    "is_selected": True,
                    "claim_map": {"elements": [], "orientation": ""},
                    "evidence": [],
                }
            ],
            "entry_mode": "focused",
            "raw_sources_count": 0,
        }
        input_data = {"url": "https://example.com"}
        content = {"metadata": {"url": "https://example.com", "title": "Title"}}

        await send_success_notifications("usr-1", "chk-1", results, input_data, content)
        mock_email.send_check_completed_email_sync.assert_called_once()
        call_kwargs = mock_email.send_check_completed_email_sync.call_args
        assert call_kwargs.kwargs["user_id"] == "usr-1"
        assert call_kwargs.kwargs["check_id"] == "chk-1"


# ── _log_stage_transition ──────────────────────────────────────────────────


@pytest.mark.asyncio
class TestLogStageTransition:
    async def test_calls_progress_reporter(self):
        reporter = AsyncMock()
        await _log_stage_transition("chk-1", "ingest", "extract", reporter)
        reporter.report_progress.assert_called_once_with("extract")


# ── Error propagation and delegation ────────────────────────────────────────


@pytest.mark.asyncio
class TestErrorPropagationAndDelegation:
    @patch(
        "app.pipeline.runner.run_pipeline_phase1",
        new_callable=AsyncMock,
        return_value={"result": "ok"},
    )
    async def test_run_pipeline_delegates_to_phase1(self, mock_phase1):
        reporter = AsyncMock()
        result = await run_pipeline(
            "chk-1", "usr-1", {"url": "https://example.com"}, reporter
        )
        mock_phase1.assert_called_once_with(
            "chk-1", "usr-1", {"url": "https://example.com"}, reporter
        )
        assert result == {"result": "ok"}

    def test_pipeline_error_preserves_stage(self):
        err = PipelineError("ingest failed", stage="ingest")
        assert err.stage == "ingest"

    def test_run_async_in_thread(self):
        async def _add(a, b):
            return a + b

        result = _run_async_in_thread(_add, 3, 4)
        assert result == 7

    def test_run_async_in_thread_with_timeout(self):
        async def _slow():
            await asyncio.sleep(10)

        with pytest.raises(asyncio.TimeoutError):
            _run_async_in_thread_with_timeout(_slow, 0.05)


# ── run_pipeline_phase1 ────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestRunPipelinePhase1:

    @patch(
        "app.pipeline.runner.get_cache_service",
        new_callable=AsyncMock,
        return_value=None,
    )
    @patch("app.pipeline.runner.async_session")
    @patch("app.workers.pipeline.extract_claims_with_cache", new_callable=AsyncMock)
    @patch("app.workers.pipeline.ingest_content_async", new_callable=AsyncMock)
    @patch(
        "app.utils.article_classifier.classify_article",
        new_callable=AsyncMock,
        return_value=None,
    )
    @patch("app.services.search.warmup_search_providers")
    @patch("app.pipeline.evidence_ledger.get_ledger", return_value=None)
    async def test_ingest_failure_raises(
        self,
        mock_ledger,
        mock_warmup,
        mock_classify,
        mock_ingest,
        mock_extract,
        mock_session_factory,
        mock_cache,
    ):
        """Ingest returning success=False raises PipelineError with stage=ingest."""
        mock_ingest.return_value = {"success": False, "error": "connection_error"}
        reporter = AsyncMock()

        with pytest.raises(PipelineError) as exc_info:
            await run_pipeline_phase1("chk-1", "usr-1", {}, reporter)
        assert exc_info.value.stage == "ingest"

    @patch(
        "app.pipeline.runner.get_cache_service",
        new_callable=AsyncMock,
        return_value=None,
    )
    @patch("app.pipeline.runner.async_session")
    @patch(
        "app.workers.pipeline.extract_claims_with_cache",
        new_callable=AsyncMock,
        return_value=[],
    )
    @patch("app.workers.pipeline.ingest_content_async", new_callable=AsyncMock)
    @patch(
        "app.utils.article_classifier.classify_article",
        new_callable=AsyncMock,
        return_value=None,
    )
    @patch("app.services.search.warmup_search_providers")
    @patch("app.pipeline.evidence_ledger.get_ledger", return_value=None)
    @patch("app.core.config.settings")
    async def test_extract_empty_claims(
        self,
        mock_settings,
        mock_ledger,
        mock_warmup,
        mock_classify,
        mock_ingest,
        mock_extract,
        mock_session_factory,
        mock_cache,
    ):
        """0 claims extracted raises PipelineError with stage=extract."""
        mock_settings.ENABLE_ARTICLE_CLASSIFICATION = False
        mock_ingest.return_value = {
            "success": True,
            "content": "Some article text",
            "metadata": {},
        }
        reporter = AsyncMock()

        with pytest.raises(PipelineError) as exc_info:
            await run_pipeline_phase1("chk-1", "usr-1", {}, reporter)
        assert exc_info.value.stage == "extract"

    @patch(
        "app.pipeline.runner.get_cache_service",
        new_callable=AsyncMock,
        return_value=None,
    )
    @patch("app.pipeline.runner.async_session")
    @patch(
        "app.pipeline.runner.run_pipeline_phase2",
        new_callable=AsyncMock,
        return_value={"done": True},
    )
    @patch("app.workers.pipeline.extract_claims_with_cache", new_callable=AsyncMock)
    @patch("app.workers.pipeline.ingest_content_async", new_callable=AsyncMock)
    @patch(
        "app.utils.article_classifier.classify_article",
        new_callable=AsyncMock,
        return_value=None,
    )
    @patch("app.services.search.warmup_search_providers")
    @patch("app.pipeline.evidence_ledger.get_ledger", return_value=None)
    @patch("app.core.config.settings")
    async def test_focused_mode_calls_phase2(
        self,
        mock_settings,
        mock_ledger,
        mock_warmup,
        mock_classify,
        mock_ingest,
        mock_extract,
        mock_phase2,
        mock_session_factory,
        mock_cache,
    ):
        """Single claim (focused mode) calls run_pipeline_phase2 directly."""
        mock_settings.ENABLE_ARTICLE_CLASSIFICATION = False
        mock_ingest.return_value = {
            "success": True,
            "content": "Claim text",
            "metadata": {},
        }
        mock_extract.return_value = [{"text": "Earth is round", "position": 1}]

        check = MagicMock()
        ctx, session = _mock_async_session(check)
        mock_session_factory.return_value = ctx

        reporter = AsyncMock()
        result = await run_pipeline_phase1("chk-1", "usr-1", {}, reporter)

        mock_phase2.assert_called_once()
        assert result == {"done": True}

    @patch(
        "app.pipeline.runner.get_cache_service",
        new_callable=AsyncMock,
        return_value=None,
    )
    @patch("app.pipeline.runner.async_session")
    @patch("app.pipeline.claim_selector.ClaimSelector")
    @patch("app.workers.pipeline.extract_claims_with_cache", new_callable=AsyncMock)
    @patch("app.workers.pipeline.ingest_content_async", new_callable=AsyncMock)
    @patch(
        "app.utils.article_classifier.classify_article",
        new_callable=AsyncMock,
        return_value=None,
    )
    @patch("app.services.search.warmup_search_providers")
    @patch("app.pipeline.evidence_ledger.get_ledger", return_value=None)
    @patch("app.core.config.settings")
    async def test_article_mode_returns_none(
        self,
        mock_settings,
        mock_ledger,
        mock_warmup,
        mock_classify,
        mock_ingest,
        mock_extract,
        mock_selector_cls,
        mock_session_factory,
        mock_cache,
    ):
        """Multiple claims (article mode) returns None after waiting_for_selection."""
        mock_settings.ENABLE_ARTICLE_CLASSIFICATION = False
        mock_settings.MAX_SELECTED_CLAIMS = 5
        mock_ingest.return_value = {
            "success": True,
            "content": "Long article",
            "metadata": {},
        }
        claims = [{"text": f"Claim {i}", "position": i} for i in range(4)]
        mock_extract.return_value = claims

        # Mock selector
        selector_instance = MagicMock()
        selector_instance.rank_claims_by_significance = AsyncMock(return_value=claims)
        for c in claims:
            c["is_selected"] = True
            c["significance_rank"] = c["position"] + 1
            c["significance_score"] = 0.8
        selector_instance.select_claims.return_value = claims
        mock_selector_cls.return_value = selector_instance

        check = MagicMock()
        ctx, session = _mock_async_session(check)
        mock_session_factory.return_value = ctx

        reporter = AsyncMock()
        result = await run_pipeline_phase1("chk-1", "usr-1", {}, reporter)

        assert result is None
        assert check.status == "waiting_for_selection"
        reporter.report_awaiting_selection.assert_called_once()

    @patch(
        "app.pipeline.runner.get_cache_service",
        new_callable=AsyncMock,
        return_value=None,
    )
    @patch("app.pipeline.runner.async_session")
    @patch("app.workers.pipeline.extract_claims_with_cache", new_callable=AsyncMock)
    @patch("app.workers.pipeline.ingest_content_async", new_callable=AsyncMock)
    @patch(
        "app.utils.article_classifier.classify_article",
        new_callable=AsyncMock,
        return_value=None,
    )
    @patch("app.services.search.warmup_search_providers")
    @patch("app.pipeline.evidence_ledger.get_ledger", return_value=None)
    @patch("app.core.config.settings")
    async def test_ingest_exception_wraps_in_pipeline_error(
        self,
        mock_settings,
        mock_ledger,
        mock_warmup,
        mock_classify,
        mock_ingest,
        mock_extract,
        mock_session_factory,
        mock_cache,
    ):
        """Ingest raising an exception is wrapped in PipelineError."""
        mock_settings.ENABLE_ARTICLE_CLASSIFICATION = False
        mock_ingest.side_effect = ConnectionError("connection_error to server")
        reporter = AsyncMock()

        with pytest.raises(PipelineError) as exc_info:
            await run_pipeline_phase1("chk-1", "usr-1", {}, reporter)
        assert exc_info.value.stage == "ingest"
        assert "couldn't reach" in exc_info.value.message.lower()
