"""Tests for lifecycle (funnel) emails — welcome and trial exhausted.

The email service had NO test coverage of any kind before this file, so
these also stand as the first tests of the render/send path.

What is pinned here, and why each one exists:

- Exactly-once. Both emails claim a marker column; if the guard is removed a
  user gets mailed repeatedly.
- Admin exclusion (R-1). ``_is_admin`` bypasses the limit in the gate but NOT
  in ``get_usage_snapshot``, so without this the founder's own account reads
  as permanently exhausted and is mailed on every check.
- Lapsed-subscriber exclusion (R-3). An inactive subscription falls back to
  limit_type 'trial', which would tell a former paying customer about "your
  3 free checks".
- Marker not burned when email is switched off (R-4). Otherwise running the
  flow in dev suppresses the real email forever.
- The wired seams. Both halves passing with a dead wire is exactly how NF-18
  hid — see feedback_test_wired_prepare_query_path.

Design: audit/2026-08-04_funnel_lifecycle_emails_design.md
"""

from contextlib import asynccontextmanager
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services import lifecycle_emails as lc
from app.services.email_notifications import EmailNotificationService


# ---------------------------------------------------------------------------
# Fixtures / factories
# ---------------------------------------------------------------------------


def _user(
    user_id="usr-1",
    email="reader@example.com",
    name="Ada Lovelace",
    notifications=True,
    lifecycle=True,
    welcome_sent=None,
    exhausted_sent=None,
):
    return SimpleNamespace(
        id=user_id,
        email=email,
        name=name,
        credits=0,
        total_credits_used=3,
        email_notifications_enabled=notifications,
        email_lifecycle=lifecycle,
        welcome_email_sent_at=welcome_sent,
        trial_exhausted_email_sent_at=exhausted_sent,
    )


def _session(user, execute_results):
    """Session returning `execute_results` in order, one per execute() call.

    Each entry is a dict of result-accessor -> value, e.g. {"scalar": 4} or
    {"scalar_one_or_none": "usr-1"}.
    """
    session = AsyncMock()
    session.get = AsyncMock(return_value=user)
    session.commit = AsyncMock()
    seq = list(execute_results)
    calls = {"n": 0}

    async def _exec(stmt):
        idx = calls["n"]
        calls["n"] += 1
        spec = seq[idx] if idx < len(seq) else {}
        result = MagicMock()
        result.scalar_one_or_none.return_value = spec.get("scalar_one_or_none")
        result.scalar.return_value = spec.get("scalar")
        return result

    session.execute = AsyncMock(side_effect=_exec)
    session._execute_calls = calls
    return session


@asynccontextmanager
async def _as_ctx(session):
    yield session


def _patch_db(session):
    """Patch app.core.database.async_session (imported inside the functions)."""
    return patch(
        "app.core.database.async_session", MagicMock(return_value=_as_ctx(session))
    )


def _patch_live(live=True):
    return patch.object(lc, "_emails_live", return_value=live)


# ---------------------------------------------------------------------------
# Welcome email
# ---------------------------------------------------------------------------


class TestWelcomeEmail:
    @pytest.mark.asyncio
    async def test_sends_when_never_sent_before(self):
        user = _user()
        session = _session(user, [{"scalar_one_or_none": "usr-1"}])  # claim wins
        sender = MagicMock(return_value=True)

        with _patch_live(), _patch_db(session), patch.object(
            lc.email_notification_service, "send_welcome_email_sync", sender
        ):
            assert await lc.send_welcome_email("usr-1") is True

        sender.assert_called_once_with("reader@example.com", "Ada Lovelace")

    @pytest.mark.asyncio
    async def test_does_not_send_twice(self):
        """The marker is already set — a second arrival must not re-send."""
        user = _user(welcome_sent=datetime(2026, 8, 1))
        # The claim WOULD succeed if we got that far — so this pins the marker
        # check itself, not merely the claim behind it.
        session = _session(user, [{"scalar_one_or_none": "usr-1"}])
        sender = MagicMock(return_value=True)

        with _patch_live(), _patch_db(session), patch.object(
            lc.email_notification_service, "send_welcome_email_sync", sender
        ):
            assert await lc.send_welcome_email("usr-1") is False

        sender.assert_not_called()
        assert session._execute_calls["n"] == 0  # short-circuits before any query

    @pytest.mark.asyncio
    async def test_losing_the_claim_race_does_not_send(self):
        """Two concurrent first requests: only the one that claims may send."""
        user = _user()
        session = _session(user, [{"scalar_one_or_none": None}])  # claim lost
        sender = MagicMock(return_value=True)

        with _patch_live(), _patch_db(session), patch.object(
            lc.email_notification_service, "send_welcome_email_sync", sender
        ):
            assert await lc.send_welcome_email("usr-1") is False

        sender.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "notifications,lifecycle", [(False, True), (True, False), (False, False)]
    )
    async def test_respects_preferences(self, notifications, lifecycle):
        user = _user(notifications=notifications, lifecycle=lifecycle)
        session = _session(user, [{"scalar_one_or_none": "usr-1"}])
        sender = MagicMock(return_value=True)

        with _patch_live(), _patch_db(session), patch.object(
            lc.email_notification_service, "send_welcome_email_sync", sender
        ):
            assert await lc.send_welcome_email("usr-1") is False

        sender.assert_not_called()

    @pytest.mark.asyncio
    async def test_unknown_user_is_a_no_op(self):
        session = _session(None, [])
        with _patch_live(), _patch_db(session):
            assert await lc.send_welcome_email("ghost") is False

    @pytest.mark.asyncio
    async def test_disabled_service_does_not_burn_the_marker(self):
        """R-4: dev runs must not permanently suppress the real email."""
        user = _user()
        session = _session(user, [{"scalar_one_or_none": "usr-1"}])

        with _patch_live(False), _patch_db(session):
            assert await lc.send_welcome_email("usr-1") is False

        # No claim attempted at all.
        assert session._execute_calls["n"] == 0
        session.commit.assert_not_called()


# ---------------------------------------------------------------------------
# Trial exhausted
# ---------------------------------------------------------------------------


def _exhausted_snapshot(usage=3, limit=3, limit_type="trial"):
    return {
        "usage": usage,
        "limit": limit,
        "limit_type": limit_type,
        "period_start": None,
        "subscription": None,
    }


class TestTrialExhaustedEmail:
    @pytest.mark.asyncio
    async def test_sends_when_trial_is_spent(self):
        user = _user()
        session = _session(
            user,
            [
                {"scalar_one_or_none": None},  # never subscribed
                {"scalar": 3},  # checks run
                {"scalar": 47},  # sources organised
                {"scalar_one_or_none": "usr-1"},  # claim wins
            ],
        )
        sender = MagicMock(return_value=True)

        with _patch_live(), _patch_db(session), patch(
            "app.services.usage_ledger.get_usage_snapshot",
            AsyncMock(return_value=_exhausted_snapshot()),
        ), patch.object(
            lc.email_notification_service, "send_trial_exhausted_email_sync", sender
        ):
            assert await lc.send_trial_exhausted_email("usr-1") is True

        sender.assert_called_once_with("reader@example.com", 3, 47)

    @pytest.mark.asyncio
    async def test_not_sent_while_credits_remain(self):
        user = _user()
        session = _session(user, [{"scalar_one_or_none": None}])
        sender = MagicMock(return_value=True)

        with _patch_live(), _patch_db(session), patch(
            "app.services.usage_ledger.get_usage_snapshot",
            AsyncMock(return_value=_exhausted_snapshot(usage=2, limit=3)),
        ), patch.object(
            lc.email_notification_service, "send_trial_exhausted_email_sync", sender
        ):
            assert await lc.send_trial_exhausted_email("usr-1") is False

        sender.assert_not_called()

    @pytest.mark.asyncio
    async def test_admin_is_never_told_their_trial_ran_out(self):
        """R-1: admins bypass the gate but still read as exhausted."""
        user = _user(email="founder@trueight.com")
        session = _session(user, [])
        sender = MagicMock(return_value=True)
        snapshot = AsyncMock(return_value=_exhausted_snapshot(usage=900, limit=3))

        with _patch_live(), _patch_db(session), patch.object(
            lc.settings, "ADMIN_EMAILS", ["founder@trueight.com"]
        ), patch(
            "app.services.usage_ledger.get_usage_snapshot", snapshot
        ), patch.object(
            lc.email_notification_service, "send_trial_exhausted_email_sync", sender
        ):
            assert await lc.send_trial_exhausted_email("usr-1") is False

        sender.assert_not_called()
        snapshot.assert_not_called()

    @pytest.mark.asyncio
    async def test_admin_match_is_case_insensitive(self):
        user = _user(email="Founder@TruEight.com")
        session = _session(user, [])
        sender = MagicMock(return_value=True)

        with _patch_live(), _patch_db(session), patch.object(
            lc.settings, "ADMIN_EMAILS", ["founder@trueight.com"]
        ), patch.object(
            lc.email_notification_service, "send_trial_exhausted_email_sync", sender
        ):
            assert await lc.send_trial_exhausted_email("usr-1") is False

        sender.assert_not_called()

    @pytest.mark.asyncio
    async def test_lapsed_subscriber_is_not_told_about_free_checks(self):
        """R-3: an inactive subscription falls back to limit_type 'trial'."""
        user = _user()
        session = _session(user, [{"scalar_one_or_none": "sub-9"}])  # has history
        sender = MagicMock(return_value=True)
        snapshot = AsyncMock(return_value=_exhausted_snapshot(usage=200, limit=200))

        with _patch_live(), _patch_db(session), patch(
            "app.services.usage_ledger.get_usage_snapshot", snapshot
        ), patch.object(
            lc.email_notification_service, "send_trial_exhausted_email_sync", sender
        ):
            assert await lc.send_trial_exhausted_email("usr-1") is False

        sender.assert_not_called()
        snapshot.assert_not_called()

    @pytest.mark.asyncio
    async def test_subscriber_on_monthly_limit_is_not_sent_trial_copy(self):
        user = _user()
        session = _session(user, [{"scalar_one_or_none": None}])
        sender = MagicMock(return_value=True)

        with _patch_live(), _patch_db(session), patch(
            "app.services.usage_ledger.get_usage_snapshot",
            AsyncMock(
                return_value=_exhausted_snapshot(
                    usage=200, limit=200, limit_type="monthly"
                )
            ),
        ), patch.object(
            lc.email_notification_service, "send_trial_exhausted_email_sync", sender
        ):
            assert await lc.send_trial_exhausted_email("usr-1") is False

        sender.assert_not_called()

    @pytest.mark.asyncio
    async def test_does_not_send_twice(self):
        user = _user(exhausted_sent=datetime(2026, 8, 1))
        # Everything downstream is primed to succeed, so the ONLY thing that
        # can stop a second send is the marker check.
        session = _session(
            user,
            [
                {"scalar_one_or_none": None},  # never subscribed
                {"scalar": 3},
                {"scalar": 47},
                {"scalar_one_or_none": "usr-1"},  # claim would win
            ],
        )
        sender = MagicMock(return_value=True)

        with _patch_live(), _patch_db(session), patch(
            "app.services.usage_ledger.get_usage_snapshot",
            AsyncMock(return_value=_exhausted_snapshot()),
        ), patch.object(
            lc.email_notification_service, "send_trial_exhausted_email_sync", sender
        ):
            assert await lc.send_trial_exhausted_email("usr-1") is False

        sender.assert_not_called()
        assert session._execute_calls["n"] == 0  # short-circuits before any query

    @pytest.mark.asyncio
    async def test_respects_lifecycle_opt_out(self):
        user = _user(lifecycle=False)
        session = _session(user, [])
        sender = MagicMock(return_value=True)

        with _patch_live(), _patch_db(session), patch.object(
            lc.email_notification_service, "send_trial_exhausted_email_sync", sender
        ):
            assert await lc.send_trial_exhausted_email("usr-1") is False

        sender.assert_not_called()

    @pytest.mark.asyncio
    async def test_tally_failure_still_sends(self):
        """A missing stat block must not cost the email."""
        user = _user()
        session = _session(user, [{"scalar_one_or_none": None}])

        # Call order: 1) subscription history, 2) tally (blows up, taking the
        # whole tally block with it), 3) the marker claim.
        calls = {"n": 0}

        async def _exec(stmt):
            calls["n"] += 1
            if calls["n"] == 2:
                raise RuntimeError("tally query exploded")
            r = MagicMock()
            r.scalar_one_or_none.return_value = None if calls["n"] == 1 else "usr-1"
            return r

        session.execute = AsyncMock(side_effect=_exec)
        sender = MagicMock(return_value=True)

        with _patch_live(), _patch_db(session), patch(
            "app.services.usage_ledger.get_usage_snapshot",
            AsyncMock(return_value=_exhausted_snapshot()),
        ), patch.object(
            lc.email_notification_service, "send_trial_exhausted_email_sync", sender
        ):
            assert await lc.send_trial_exhausted_email("usr-1") is True

        sender.assert_called_once_with("reader@example.com", 0, 0)


# ---------------------------------------------------------------------------
# Fire-and-forget wrappers
# ---------------------------------------------------------------------------


class TestScheduling:
    @pytest.mark.asyncio
    async def test_send_failure_never_reaches_the_caller(self):
        with patch.object(
            lc, "send_welcome_email", AsyncMock(side_effect=RuntimeError("resend down"))
        ):
            task = lc.schedule_welcome_email("usr-1")
            await task  # must not raise

    @pytest.mark.asyncio
    async def test_task_reference_is_held_then_released(self):
        """Detached tasks are weakly referenced by asyncio and can vanish."""
        with patch.object(lc, "send_welcome_email", AsyncMock(return_value=True)):
            task = lc.schedule_welcome_email("usr-1")
            assert task in lc._background_tasks
            await task
        assert task not in lc._background_tasks

    def test_no_event_loop_is_survivable(self):
        """Sync contexts must not raise (and must not leak the coroutine)."""
        with patch.object(lc, "send_welcome_email", AsyncMock(return_value=True)):
            assert lc.schedule_welcome_email("usr-1") is None


# ---------------------------------------------------------------------------
# Wired seams
#
# Everything above tests the sender in isolation. These test that something
# actually CALLS it. Both halves green with a dead wire in between is exactly
# how NF-18 hid for months.
# ---------------------------------------------------------------------------


class TestWiredSeams:
    @pytest.mark.asyncio
    async def test_user_creation_triggers_the_welcome_email(self):
        from app.api.v1.users import get_or_create_user

        created = _user()
        session = AsyncMock()
        session.commit = AsyncMock()
        calls = {"n": 0}

        async def _exec(stmt):
            calls["n"] += 1
            r = MagicMock()
            r.scalar_one_or_none.return_value = None  # not found by id
            r.scalar_one.return_value = created  # INSERT ... RETURNING
            return r

        session.execute = AsyncMock(side_effect=_exec)
        scheduled = MagicMock()

        with patch.object(lc, "schedule_welcome_email", scheduled):
            await get_or_create_user(
                session, {"id": "usr-1", "email": "reader@example.com", "name": "Ada"}
            )

        scheduled.assert_called_once_with("usr-1")

    @pytest.mark.asyncio
    async def test_existing_user_does_not_re_trigger_the_welcome(self):
        """The early return for a known user must not reach the scheduler."""
        from app.api.v1.users import get_or_create_user

        session = AsyncMock()

        async def _exec(stmt):
            r = MagicMock()
            r.scalar_one_or_none.return_value = _user()
            return r

        session.execute = AsyncMock(side_effect=_exec)
        scheduled = MagicMock()

        with patch.object(lc, "schedule_welcome_email", scheduled):
            await get_or_create_user(
                session, {"id": "usr-1", "email": "reader@example.com", "name": "Ada"}
            )

        scheduled.assert_not_called()

    @pytest.mark.asyncio
    async def test_check_completion_triggers_the_exhaustion_check(self):
        from app.pipeline.runner import send_success_notifications

        scheduled = MagicMock()
        with patch.object(
            lc, "schedule_trial_exhausted_email", scheduled
        ), patch.object(
            lc.email_notification_service,
            "send_check_completed_email_sync",
            MagicMock(),
        ):
            await send_success_notifications(
                "usr-1", "chk-1", {"claims": []}, {}, {"metadata": {}}
            )

        scheduled.assert_called_once_with("usr-1")

    @pytest.mark.asyncio
    async def test_completion_email_failure_still_runs_the_exhaustion_check(self):
        """The two sends are independent — one dying must not mute the other."""
        from app.pipeline.runner import send_success_notifications

        scheduled = MagicMock()
        with patch.object(
            lc, "schedule_trial_exhausted_email", scheduled
        ), patch.object(
            lc.email_notification_service,
            "send_check_completed_email_sync",
            MagicMock(side_effect=RuntimeError("resend down")),
        ):
            await send_success_notifications(
                "usr-1", "chk-1", {"claims": []}, {}, {"metadata": {}}
            )

        scheduled.assert_called_once_with("usr-1")

    @pytest.mark.asyncio
    async def test_re_search_debit_triggers_the_exhaustion_check(self):
        """R-2: re-searches spend credits but never reach the pipeline hook."""
        import app.api.v1.checks as checks_mod

        session = AsyncMock()
        session.commit = AsyncMock()
        scheduled = MagicMock()

        with patch.object(
            lc, "schedule_trial_exhausted_email", scheduled
        ), patch.object(
            checks_mod, "get_or_create_user", AsyncMock(return_value=_user())
        ), patch.object(
            checks_mod, "reserve_usage", AsyncMock(return_value=_user())
        ):
            await checks_mod._reserve_re_search_credit(
                session, {"id": "usr-1"}, kind="re_search", check_id="chk-1"
            )

        scheduled.assert_called_once_with("usr-1")


# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------


class TestTemplates:
    @pytest.fixture
    def service(self):
        return EmailNotificationService()

    def test_welcome_renders_key_content(self, service):
        html = service._render_welcome_template(name="Ada Lovelace")
        assert "Welcome, Ada." in html
        assert "/dashboard/new-check" in html
        assert "/r/2484b9da-4c94-4042-9fac-61919b93e008" in html
        assert "We organise" in html

    def test_welcome_without_a_name(self, service):
        html = service._render_welcome_template(name=None)
        assert "Welcome." in html
        assert "Welcome, ." not in html

    def test_welcome_escapes_the_name(self, service):
        """Names come from the auth provider — never trust them."""
        html = service._render_welcome_template(name="<script>alert(1)</script>")
        assert "<script>alert(1)</script>" not in html
        assert "&lt;script&gt;" in html

    def test_trial_exhausted_carries_console_pricing(self, service):
        html = service._render_trial_exhausted_template(
            checks_run=3, sources_organised=47
        )
        assert "&pound;20" in html
        assert "&pound;200/year" in html
        assert "200 checks per month" in html
        assert "/pricing" in html

    def test_trial_exhausted_shows_the_tally(self, service):
        html = service._render_trial_exhausted_template(
            checks_run=3, sources_organised=47
        )
        assert "Sources Organised" in html
        assert ">47<" in html

    def test_trial_exhausted_hides_an_empty_tally(self, service):
        """A proud '0 sources organised' is worse than saying nothing."""
        html = service._render_trial_exhausted_template(
            checks_run=0, sources_organised=0
        )
        assert "Sources Organised" not in html

    def test_no_verdict_language(self, service):
        """Tru8 organises evidence; it does not adjudicate."""
        for html in (
            service._render_welcome_template(name="Sam"),
            service._render_trial_exhausted_template(checks_run=3, sources_organised=9),
        ):
            lowered = html.lower()
            for banned in ("fact-check", "verdict", "debunk", "true or false"):
                assert banned not in lowered

    def test_uk_spelling(self, service):
        html = service._render_welcome_template(name="Sam")
        assert "organise" in html.lower()
        assert "organize" not in html.lower()


# ---------------------------------------------------------------------------
# Sending — headers and preference-independent behaviour
# ---------------------------------------------------------------------------


class TestSending:
    def test_lifecycle_mail_carries_an_unsubscribe_header(self):
        service = EmailNotificationService()
        service.enabled = True
        service.api_key = "re_test"
        captured = {}

        fake_resend = MagicMock()
        fake_resend.Emails.send.side_effect = lambda params: captured.update(
            params
        ) or {"id": "e1"}

        with patch.object(service, "_get_resend", return_value=fake_resend):
            assert service.send_welcome_email_sync("a@b.com", "Ada") is True

        assert "List-Unsubscribe" in captured["headers"]
        assert "mailto:" in captured["headers"]["List-Unsubscribe"]

    def test_disabled_service_sends_nothing(self):
        service = EmailNotificationService()
        service.enabled = False
        assert service.send_welcome_email_sync("a@b.com", "Ada") is False
        assert service.send_trial_exhausted_email_sync("a@b.com", 3, 9) is False

    def test_send_failure_is_swallowed(self):
        service = EmailNotificationService()
        service.enabled = True
        service.api_key = "re_test"
        fake_resend = MagicMock()
        fake_resend.Emails.send.side_effect = RuntimeError("resend 500")

        with patch.object(service, "_get_resend", return_value=fake_resend):
            assert service.send_welcome_email_sync("a@b.com", "Ada") is False
