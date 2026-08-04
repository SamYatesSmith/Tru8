"""Lifecycle (funnel) emails — welcome, and trial exhausted.

Design: audit/2026-08-04_funnel_lifecycle_emails_design.md

This module owns *whether* a lifecycle email should go and *that it goes at
most once*. Rendering and sending live in ``email_notifications``; keeping
eligibility in one place is deliberate, because a second copy of these rules
is a second thing to drift.

Three properties this module has to hold:

1. **Exactly once.** Each email claims a marker column with a conditional
   ``UPDATE ... WHERE marker IS NULL``. Whichever caller wins the update
   sends; everyone else is a no-op. This is what makes it safe to wire the
   exhaustion check into more than one trigger point.

2. **Never breaks its caller.** These run on the signup request path and in
   the pipeline's completion path. Every entry point swallows its own
   exceptions — a mail problem must never fail a check or a page load.

3. **Never blocks the event loop.** The Resend SDK is synchronous, so the
   send is pushed to a worker thread. Each function also opens its OWN
   session rather than joining the caller's transaction, so claiming a
   marker can never commit a caller's half-finished work.
"""

import asyncio
import logging
from typing import Optional, Set

from sqlalchemy import func, select, update

from app.core.config import settings
from app.models import Check, Subscription, User
from app.models.check import _utcnow_naive
from app.services.email_notifications import email_notification_service

logger = logging.getLogger(__name__)

# asyncio only holds a weak reference to tasks, so a fire-and-forget task can
# be garbage-collected mid-flight. Hold a strong reference until it finishes.
_background_tasks: Set[asyncio.Task] = set()


def _emails_live() -> bool:
    """True when a send could actually reach Resend.

    Checked BEFORE claiming a marker. Without this, running the flow in a
    dev environment with notifications off would burn the marker and
    permanently suppress the real email for that user.
    """
    return bool(
        email_notification_service.enabled and email_notification_service.api_key
    )


def _wants_lifecycle_email(user: User) -> bool:
    """Lifecycle mail honours the global switch and its own opt-out.

    Deliberately NOT gated on ``email_marketing``, which defaults to False —
    gating on it would ship the feature dark for every user.
    """
    return bool(user.email_notifications_enabled and user.email_lifecycle)


def _is_admin(user: User) -> bool:
    """Mirrors usage_ledger._is_admin."""
    return bool(user.email) and user.email.lower() in [
        e.lower() for e in settings.ADMIN_EMAILS
    ]


async def _claim(session, user_id: str, column) -> bool:
    """Atomically claim a send marker. True means 'you send it'.

    Claimed before sending rather than after: losing one email to a Resend
    outage is strictly better than a retry loop mailing someone repeatedly.
    """
    result = await session.execute(
        update(User)
        .where(User.id == user_id, column.is_(None))
        .values(**{column.key: _utcnow_naive()})
        .returning(User.id)
    )
    claimed = result.scalar_one_or_none() is not None
    await session.commit()
    return claimed


# ---------------------------------------------------------------------------
# Welcome
# ---------------------------------------------------------------------------


async def send_welcome_email(user_id: str) -> bool:
    """Send the welcome email if this user has never had one.

    Returns True only when an email was actually handed to Resend.
    """
    if not _emails_live():
        return False

    from app.core.database import async_session

    async with async_session() as session:
        user = await session.get(User, user_id)
        if user is None or not _wants_lifecycle_email(user):
            return False
        if user.welcome_email_sent_at is not None:
            return False

        if not await _claim(session, user_id, User.welcome_email_sent_at):
            return False

        email, name = user.email, user.name

    return await asyncio.to_thread(
        email_notification_service.send_welcome_email_sync, email, name
    )


# ---------------------------------------------------------------------------
# Trial exhausted
# ---------------------------------------------------------------------------


async def _trial_is_exhausted(session, user: User) -> bool:
    """True when this user is on the trial and has spent all of it.

    Reuses ``get_usage_snapshot`` rather than re-deriving the limit. The trial
    limit is ``max(3, credits + total_credits_used)``, not a literal 3 — a
    second copy of that expression would drift from the paywall, and then the
    email and the gate would tell the user different things.
    """
    from app.services.usage_ledger import get_usage_snapshot

    # Admins bypass the limit in the gate but NOT in the snapshot, so without
    # this they read as permanently exhausted and would be mailed on every
    # single check.
    if _is_admin(user):
        return False

    # A lapsed subscriber also falls back to limit_type 'trial', and the
    # formula makes them look exhausted. Telling a former paying customer
    # about "your 3 free checks" is wrong, so require a clean history.
    ever_subscribed = await session.execute(
        select(Subscription.id).where(Subscription.user_id == user.id).limit(1)
    )
    if ever_subscribed.scalar_one_or_none() is not None:
        return False

    snapshot = await get_usage_snapshot(session, user)
    return snapshot["limit_type"] == "trial" and snapshot["usage"] >= snapshot["limit"]


async def _trial_tally(session, user_id: str) -> tuple:
    """(checks completed, evidence sources organised) for the email body.

    Best-effort: a failure here costs a stat block, not the email.
    """
    try:
        checks = await session.execute(
            select(func.count(Check.id)).where(
                Check.user_id == user_id, Check.status == "completed"
            )
        )
        sources = await session.execute(
            select(func.coalesce(func.sum(Check.raw_sources_count), 0)).where(
                Check.user_id == user_id, Check.status == "completed"
            )
        )
        return int(checks.scalar() or 0), int(sources.scalar() or 0)
    except Exception as e:
        logger.debug(f"[LIFECYCLE] trial tally unavailable: {e}")
        return 0, 0


async def send_trial_exhausted_email(user_id: str) -> bool:
    """Send the trial-exhausted email if the trial is spent and unannounced."""
    if not _emails_live():
        return False

    from app.core.database import async_session

    async with async_session() as session:
        user = await session.get(User, user_id)
        if user is None or not _wants_lifecycle_email(user):
            return False
        if user.trial_exhausted_email_sent_at is not None:
            return False
        if not await _trial_is_exhausted(session, user):
            return False

        checks_run, sources = await _trial_tally(session, user_id)

        if not await _claim(session, user_id, User.trial_exhausted_email_sent_at):
            return False

        email = user.email

    return await asyncio.to_thread(
        email_notification_service.send_trial_exhausted_email_sync,
        email,
        checks_run,
        sources,
    )


# ---------------------------------------------------------------------------
# Fire-and-forget entry points — what callers should use
# ---------------------------------------------------------------------------


def _spawn(coro, label: str) -> Optional[asyncio.Task]:
    """Run a lifecycle send detached, swallowing everything it raises."""

    async def _guarded():
        try:
            sent = await coro
            if sent:
                logger.info(f"[LIFECYCLE] {label} sent")
        except Exception as e:
            logger.warning(f"[LIFECYCLE] {label} failed: {e}")

    try:
        task = asyncio.create_task(_guarded())
    except RuntimeError:
        # No running loop (sync context / some test paths). Nothing to do —
        # a lifecycle email is never worth raising for.
        coro.close()
        return None

    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)
    return task


def schedule_welcome_email(user_id: str) -> Optional[asyncio.Task]:
    """Queue the welcome email without delaying the caller's response."""
    return _spawn(send_welcome_email(user_id), f"welcome user={user_id}")


def schedule_trial_exhausted_email(user_id: str) -> Optional[asyncio.Task]:
    """Queue the trial-exhausted email without delaying the caller."""
    return _spawn(
        send_trial_exhausted_email(user_id), f"trial-exhausted user={user_id}"
    )
