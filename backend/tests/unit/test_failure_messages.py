"""What a user is told when a check fails (2026-10-12).

Production check b918746c ("Trump will cause world war 3") stopped at
extraction with a specific, user-written reason. The user saw "Something went
wrong ... Please try again.. Your credit has been returned." and an email
blaming "evidence gathering", because:

1. handle_pipeline_failure ran the already-friendly PipelineError message
   through get_user_friendly_error a second time; no key matched, so the
   generic text replaced it.
2. The refund line was appended after a message that already ended in ".".
3. The email template hard-coded "during evidence gathering" and its own
   refund line, while the error text it embedded carried a second one.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.pipeline.runner import (
    PipelineError,
    get_user_friendly_error,
    handle_pipeline_failure,
)
from app.services.email_notifications import EmailNotificationService

NO_CLAIMS = (
    "We couldn't extract any verifiable claims from this content. "
    "Try submitting a specific factual statement, e.g. "
    "'The Eiffel Tower was completed in 1889'. "
    "Questions are accepted if they imply a verifiable claim."
)


def _session_ctx(check):
    session = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = check
    session.execute = AsyncMock(return_value=result)
    session.commit = AsyncMock()
    ctx = AsyncMock()
    ctx.__aenter__ = AsyncMock(return_value=session)
    ctx.__aexit__ = AsyncMock(return_value=False)
    return ctx


class TestUserFacingPipelineError:
    def test_user_facing_message_is_shown_as_is(self):
        err = PipelineError(NO_CLAIMS, stage="extract", user_facing=True)
        assert get_user_friendly_error(err) == NO_CLAIMS

    def test_internal_pipeline_error_still_hidden(self):
        """Messages that embed raw exceptions must never reach the user."""
        err = PipelineError("Evidence mapping failed: KeyError 'x'", stage="analyze")
        msg = get_user_friendly_error(err)
        assert "KeyError" not in msg
        assert "Something went wrong" in msg

    def test_default_is_not_user_facing(self):
        assert PipelineError("boom").user_facing is False


@pytest.mark.asyncio
class TestHandlePipelineFailureMessages:
    @patch("app.pipeline.runner.email_notification_service")
    @patch("app.pipeline.runner.push_notification_service")
    @patch(
        "app.pipeline.runner.refund_check_credit_async",
        new_callable=AsyncMock,
        return_value=True,
    )
    @patch("app.pipeline.runner.async_session")
    async def test_specific_reason_reaches_record_and_email(
        self, mock_session_factory, mock_refund, mock_push, mock_email
    ):
        check = MagicMock()
        mock_session_factory.return_value = _session_ctx(check)

        await handle_pipeline_failure(
            "chk-1",
            "usr-1",
            PipelineError(NO_CLAIMS, stage="extract", user_facing=True),
        )

        assert check.error_message == (NO_CLAIMS + " Your credit has been returned.")
        assert ".." not in check.error_message
        assert "Something went wrong" not in check.error_message

        kwargs = mock_email.send_check_failed_email_sync.call_args.kwargs
        # The email states the refund itself — the reason travels without it,
        # and is not cut mid-sentence.
        assert kwargs["error_message"] == NO_CLAIMS
        assert kwargs["credit_refunded"] is True

    @patch("app.pipeline.runner.email_notification_service")
    @patch("app.pipeline.runner.push_notification_service")
    @patch(
        "app.pipeline.runner.refund_check_credit_async",
        new_callable=AsyncMock,
        return_value=True,
    )
    @patch("app.pipeline.runner.async_session")
    async def test_generic_message_gets_single_full_stop(
        self, mock_session_factory, mock_refund, mock_push, mock_email
    ):
        check = MagicMock()
        mock_session_factory.return_value = _session_ctx(check)

        await handle_pipeline_failure("chk-1", "usr-1", Exception("weird internal"))

        assert check.error_message == (
            "Something went wrong while processing your check. Please try again. "
            "Your credit has been returned."
        )

    @patch("app.pipeline.runner.email_notification_service")
    @patch("app.pipeline.runner.push_notification_service")
    @patch(
        "app.pipeline.runner.refund_check_credit_async",
        new_callable=AsyncMock,
        return_value=False,
    )
    @patch("app.pipeline.runner.async_session")
    async def test_no_refund_no_refund_line(
        self, mock_session_factory, mock_refund, mock_push, mock_email
    ):
        check = MagicMock()
        mock_session_factory.return_value = _session_ctx(check)

        await handle_pipeline_failure("chk-1", "usr-1", Exception("timeout"))

        assert "credit" not in check.error_message.lower()
        kwargs = mock_email.send_check_failed_email_sync.call_args.kwargs
        assert kwargs["credit_refunded"] is False


class TestCheckFailedEmailTemplate:
    def _render(self, **kw):
        svc = EmailNotificationService.__new__(EmailNotificationService)
        return svc._render_check_failed_template(check_id="chk-1", **kw)

    def test_does_not_blame_evidence_gathering(self):
        html = self._render(error_message=NO_CLAIMS, credit_refunded=True)
        assert "evidence gathering" not in html

    def test_refund_stated_exactly_once(self):
        html = self._render(error_message=NO_CLAIMS, credit_refunded=True)
        assert html.count("credit has been returned") == 1

    def test_no_refund_line_when_not_refunded(self):
        html = self._render(error_message=NO_CLAIMS, credit_refunded=False)
        assert "credit has been returned" not in html

    def test_full_reason_is_shown(self):
        html = self._render(error_message=NO_CLAIMS, credit_refunded=True)
        assert "imply a verifiable claim." in html
