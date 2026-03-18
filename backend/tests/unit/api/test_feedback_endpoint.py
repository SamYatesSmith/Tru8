"""Tests for feedback API endpoints: POST /feedback and POST /waitlist.

Covers:
- Authenticated feedback submission with Resend email sending
- Authentication requirement enforcement
- Feedback type validation (emoji/label helpers)
- Public waitlist signup with email validation
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.v1.feedback import router, _get_type_emoji, _get_type_label
from app.core.auth import get_current_user


# ---------------------------------------------------------------------------
# Test app + dependency overrides
# ---------------------------------------------------------------------------

MOCK_USER = {"id": "user-test-001", "email": "tester@tru8.app"}


def _create_test_app():
    """Build a minimal FastAPI app with the feedback router mounted."""
    app = FastAPI()
    # Feedback router is mounted at /api/v1 (no sub-prefix) in main.py
    app.include_router(router, prefix="/api/v1")
    return app


def _mock_auth_override():
    """Dependency override that always returns MOCK_USER."""

    async def _override():
        return MOCK_USER

    return _override


def _mock_auth_failure():
    """Dependency override that raises 401 to simulate missing auth."""
    from fastapi import HTTPException

    async def _override():
        raise HTTPException(status_code=401, detail="Not authenticated")

    return _override


# ===========================================================================
# POST /feedback
# ===========================================================================


class TestSubmitFeedback:
    """POST /api/v1/feedback -- authenticated feedback submission."""

    @pytest.mark.asyncio
    async def test_submits_feedback_successfully(self):
        """Valid feedback with mocked Resend sends email and returns success."""
        app = _create_test_app()
        app.dependency_overrides[get_current_user] = _mock_auth_override()

        mock_resend = MagicMock()
        mock_resend.Emails.send.return_value = {"id": "email-abc123"}

        with patch.dict("sys.modules", {"resend": mock_resend}), patch(
            "app.api.v1.feedback.settings"
        ) as mock_settings:
            mock_settings.RESEND_API_KEY = "re_test_key"
            mock_settings.EMAIL_FROM_ADDRESS = "hello@trueight.com"
            mock_settings.FEEDBACK_EMAIL = "admin@tru8.com"

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.post(
                    "/api/v1/feedback",
                    json={
                        "type": "bug",
                        "message": "The timeline view crashes on mobile",
                        "pageUrl": "/dashboard/check/abc123",
                        "userEmail": "tester@tru8.app",
                        "checkId": "abc12345-6789-0000-0000-000000000000",
                    },
                )

        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert "thank you" in body["message"].lower()

        # Verify Resend was called with correct params
        mock_resend.Emails.send.assert_called_once()
        call_args = mock_resend.Emails.send.call_args[0][0]
        assert "admin@tru8.com" in call_args["to"]
        assert "Bug Report" in call_args["subject"]
        assert "tester@tru8.app" == call_args["reply_to"]

    @pytest.mark.asyncio
    async def test_requires_auth(self):
        """Without authentication, feedback endpoint returns 401."""
        app = _create_test_app()
        app.dependency_overrides[get_current_user] = _mock_auth_failure()

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/v1/feedback",
                json={
                    "type": "suggestion",
                    "message": "Add dark mode",
                    "pageUrl": "/dashboard",
                },
            )

        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_validates_feedback_type(self):
        """Feedback type field maps to correct emoji and label via helpers."""
        # Valid types get correct labels
        assert _get_type_emoji("bug") == "\U0001f41b"
        assert _get_type_label("bug") == "Bug Report"
        assert _get_type_label("suggestion") == "Feature Suggestion"
        assert _get_type_label("ui") == "UI / Design"
        assert _get_type_label("fact-check") == "Fact-Check Result"

        # Unknown type gets fallback
        assert _get_type_emoji("nonsense") == "\u2753"
        assert _get_type_label("nonsense") == "Other"

    @pytest.mark.asyncio
    async def test_feedback_still_succeeds_without_email_configured(self):
        """Feedback returns success even if email sending fails (logged only)."""
        app = _create_test_app()
        app.dependency_overrides[get_current_user] = _mock_auth_override()

        with patch("app.api.v1.feedback.settings") as mock_settings:
            mock_settings.RESEND_API_KEY = ""  # No key configured

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.post(
                    "/api/v1/feedback",
                    json={
                        "type": "other",
                        "message": "General feedback",
                        "pageUrl": "/",
                    },
                )

        assert resp.status_code == 200
        assert resp.json()["success"] is True

    @pytest.mark.asyncio
    async def test_feedback_includes_check_id_in_subject(self):
        """When checkId is provided, it appears in the email subject."""
        app = _create_test_app()
        app.dependency_overrides[get_current_user] = _mock_auth_override()

        mock_resend = MagicMock()
        mock_resend.Emails.send.return_value = {"id": "email-xyz"}

        with patch.dict("sys.modules", {"resend": mock_resend}), patch(
            "app.api.v1.feedback.settings"
        ) as mock_settings:
            mock_settings.RESEND_API_KEY = "re_test_key"
            mock_settings.EMAIL_FROM_ADDRESS = "hello@trueight.com"
            mock_settings.FEEDBACK_EMAIL = None  # Falls back to EMAIL_FROM_ADDRESS

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.post(
                    "/api/v1/feedback",
                    json={
                        "type": "fact-check",
                        "message": "Evidence seems outdated",
                        "pageUrl": "/dashboard/check/deadbeef-1234",
                        "checkId": "deadbeef-1234-5678-9abc-def012345678",
                    },
                )

        assert resp.status_code == 200
        call_args = mock_resend.Emails.send.call_args[0][0]
        assert "deadbeef" in call_args["subject"]


# ===========================================================================
# POST /waitlist
# ===========================================================================


class TestWaitlist:
    """POST /api/v1/waitlist -- public waitlist signup."""

    @pytest.mark.asyncio
    async def test_adds_valid_email(self):
        """Valid email address returns success message."""
        app = _create_test_app()
        # No auth override needed -- waitlist is public

        with patch("app.api.v1.feedback._send_feedback_email", return_value=True):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.post(
                    "/api/v1/waitlist",
                    json={"email": "interested@example.com", "source": "landing"},
                )

        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert "list" in body["message"].lower()

    @pytest.mark.asyncio
    async def test_rejects_invalid_email(self):
        """Malformed email address returns 400."""
        app = _create_test_app()

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/v1/waitlist",
                json={"email": "not-an-email", "source": "landing"},
            )

        assert resp.status_code == 400
        assert "valid email" in resp.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_rejects_email_missing_tld(self):
        """Email without proper TLD is rejected."""
        app = _create_test_app()

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/v1/waitlist",
                json={"email": "user@localhost"},
            )

        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_is_public(self):
        """Waitlist endpoint does not require authentication."""
        app = _create_test_app()
        # Deliberately override auth to fail -- waitlist should still work
        app.dependency_overrides[get_current_user] = _mock_auth_failure()

        with patch("app.api.v1.feedback._send_feedback_email", return_value=False):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.post(
                    "/api/v1/waitlist",
                    json={"email": "public@user.com"},
                )

        assert resp.status_code == 200
        assert resp.json()["success"] is True

    @pytest.mark.asyncio
    async def test_waitlist_sends_notification_email(self):
        """Waitlist signup calls _send_feedback_email with correct args."""
        app = _create_test_app()

        with patch(
            "app.api.v1.feedback._send_feedback_email", return_value=True
        ) as mock_send:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.post(
                    "/api/v1/waitlist",
                    json={"email": "waitlist@example.org", "source": "pricing"},
                )

        assert resp.status_code == 200
        mock_send.assert_called_once()
        feedback_arg = mock_send.call_args[0][0]
        assert feedback_arg.type == "waitlist"
        assert feedback_arg.userEmail == "waitlist@example.org"
        assert "pricing" in feedback_arg.message
        # User ID should be "anonymous" for public waitlist
        assert mock_send.call_args[0][1] == "anonymous"

    @pytest.mark.asyncio
    async def test_waitlist_default_source(self):
        """Waitlist without explicit source defaults to 'landing'."""
        app = _create_test_app()

        with patch(
            "app.api.v1.feedback._send_feedback_email", return_value=True
        ) as mock_send:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.post(
                    "/api/v1/waitlist",
                    json={"email": "default@test.com"},
                )

        assert resp.status_code == 200
        feedback_arg = mock_send.call_args[0][0]
        assert "landing" in feedback_arg.message
