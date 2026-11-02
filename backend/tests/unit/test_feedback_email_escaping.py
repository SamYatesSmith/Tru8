"""Feedback and waitlist emails must not carry caller-supplied HTML.

Security sweep 2026-11-02, #3: `/waitlist` is public, and every field was
f-stringed into the HTML mailed to the founder from Tru8's own domain, so
anyone could send a convincing phishing email ("your Railway login…") that
passes SPF/DKIM. `reply_to` was also whatever the caller typed.
"""

import sys
import types
from unittest.mock import patch

import pytest

from app.api.v1 import feedback as fb
from app.core.config import settings

EVIL = '<a href="https://evil.example/login">Railway: re-enter password</a><script>x()</script>'


@pytest.fixture
def sent(monkeypatch):
    captured = {}
    fake = types.SimpleNamespace(
        api_key=None,
        Emails=types.SimpleNamespace(
            send=lambda params: captured.update(params) or {"id": "e1"}
        ),
    )
    monkeypatch.setitem(sys.modules, "resend", fake)
    monkeypatch.setattr(settings, "RESEND_API_KEY", "re_test")
    return captured


def _req(**kw):
    base = dict(type="bug", message="hello", pageUrl="/dashboard")
    base.update(kw)
    return fb.FeedbackRequest(**base)


@pytest.mark.parametrize("field", ["message", "pageUrl", "claimText", "userEmail"])
def test_caller_html_is_escaped(sent, field):
    kw = {field: EVIL}
    if field == "claimText":
        kw["claimPosition"] = 1
    assert fb._send_feedback_email(_req(**kw), "user_x")
    html = sent["html"]
    assert "<script>" not in html
    assert '<a href="https://evil.example' not in html
    assert "&lt;script&gt;" in html or "&lt;a href" in html


def test_check_id_cannot_break_out_of_the_link(sent):
    assert fb._send_feedback_email(_req(checkId='abc"><img src=x onerror=1>'), "u")
    html = sent["html"]
    assert "<img" not in html
    assert '"><' not in html


def test_check_link_points_at_our_domain(sent):
    """It pointed at tru8.com, a domain we do not own."""
    assert fb._send_feedback_email(_req(checkId="abc-123"), "u")
    assert "https://www.trueight.com/dashboard/check/abc-123" in sent["html"]
    assert "tru8.com/" not in sent["html"]


def test_subject_carries_no_control_characters(sent):
    assert fb._send_feedback_email(_req(checkId="ab\r\nBcc: x@y.z"), "u")
    assert "\r" not in sent["subject"] and "\n" not in sent["subject"]


def test_invalid_reply_to_is_dropped(sent):
    assert fb._send_feedback_email(_req(userEmail=EVIL), "u")
    assert "reply_to" not in sent


def test_valid_reply_to_is_kept(sent):
    assert fb._send_feedback_email(_req(userEmail="sam@example.com"), "u")
    assert sent["reply_to"] == "sam@example.com"


@pytest.mark.asyncio
async def test_waitlist_source_is_escaped(sent):
    # __wrapped__ skips the rate-limit decorator, which needs a live request.
    await fb.join_waitlist.__wrapped__(
        None, fb.WaitlistRequest(email="a@b.co", source=EVIL[:60])
    )
    assert "<script>" not in sent["html"]
    assert '<a href="https://evil.example' not in sent["html"]


def test_reply_to_with_trailing_newline_is_dropped(sent):
    """`$` matches before a trailing newline; fullmatch does not."""
    assert fb._send_feedback_email(_req(userEmail="a@b.co\n"), "u")
    assert "reply_to" not in sent


@pytest.mark.asyncio
async def test_waitlist_rejects_trailing_newline_email(sent):
    from fastapi import HTTPException

    with pytest.raises(HTTPException):
        await fb.join_waitlist.__wrapped__(None, fb.WaitlistRequest(email="a@b.co\n"))


def test_overlong_fields_are_refused():
    with pytest.raises(Exception):
        fb.FeedbackRequest(type="bug", message="x" * 5001, pageUrl="/")
