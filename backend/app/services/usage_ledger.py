"""Usage ledger service — gate, debit, and refund dashboard credits.

Design: audit/2026-07-10_usage_ledger_design.md (founder-approved 2026-07-10).

The ledger (``usage_events``) is the single source of truth for dashboard
entitlement. The rules:

- ``enforce_usage_limit`` locks the user row (SELECT ... FOR UPDATE) before
  computing usage, so two concurrent requests at limit-1 serialise and
  exactly one passes. The lock is held until the caller commits, which
  makes gate + debit atomic when both run in one transaction.
- ``record_usage`` appends the +1 debit event and dual-writes the legacy
  counters (User.credits / User.total_credits_used) for API back-compat.
  No gate reads the legacy counters any more.
- ``refund_usage`` appends a compensating -1 event. It re-credits the trial
  field only when the original debit actually drew from it (the event's
  ``drew_trial`` flag), so a subscriber's refund can never mint a phantom
  trial credit. Idempotent via the Check.credits_used == 0 marker (and a
  partial unique index at the DB level).
- Nothing here commits — the caller owns the transaction.

The /agent prepaid rail (User.credit_balance_pence) is a separate system.
"""

import calendar
import logging
import uuid
from datetime import datetime
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import Check, Subscription, User
from app.models.check import _utcnow_naive
from app.models.usage_event import (
    DEBIT_KINDS,
    KIND_CHECK,
    KIND_REFUND,
    UsageEvent,
)

logger = logging.getLogger(__name__)


def _is_admin(user: User) -> bool:
    return bool(user.email) and user.email.lower() in [
        e.lower() for e in settings.ADMIN_EMAILS
    ]


async def _active_subscription(
    session: AsyncSession, user_id: str
) -> Optional[Subscription]:
    stmt = select(Subscription).where(
        Subscription.user_id == user_id,
        Subscription.status.in_(["active", "trialing"]),
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


def _add_months(dt: datetime, months: int) -> datetime:
    """Add whole months to ``dt``, clamping the day to the target month length.

    A 31st anchor added into a 30-day month lands on the 30th (or 28th/29th in
    February) rather than overflowing.
    """
    total = dt.month - 1 + months
    year = dt.year + total // 12
    month = total % 12 + 1
    day = min(dt.day, calendar.monthrange(year, month)[1])
    return dt.replace(year=year, month=month, day=day)


def _monthly_window_start(period_start: datetime, now: datetime) -> datetime:
    """Start of the current one-month allowance window within a billing period.

    The dashboard allowance (``credits_per_month``) refreshes every month. For a
    monthly plan the Stripe billing period IS a month, so this returns
    ``period_start`` unchanged. For an ANNUAL plan the billing period is a year;
    without this the allowance would only reset once a year (the bug this fixes).
    We therefore count from the most recent monthly anniversary of
    ``period_start``: started 15 Jan, today 3 Apr -> window starts 15 Mar.
    Day-of-month is clamped for short months.
    """
    if now <= period_start:
        return period_start
    months = (now.year - period_start.year) * 12 + (now.month - period_start.month)
    candidate = _add_months(period_start, months)
    if candidate > now:
        candidate = _add_months(period_start, months - 1)
    return candidate


async def _ledger_usage(
    session: AsyncSession, user_id: str, since: Optional[datetime] = None
) -> int:
    stmt = select(func.coalesce(func.sum(UsageEvent.credits), 0)).where(
        UsageEvent.user_id == user_id
    )
    if since is not None:
        stmt = stmt.where(UsageEvent.created_at >= since)
    result = await session.execute(stmt)
    return result.scalar() or 0


async def get_usage_snapshot(
    session: AsyncSession, user: User, *, now: Optional[datetime] = None
) -> dict:
    """Usage/limit picture for gates and the /users/usage endpoint.

    Subscriber: usage = ledger sum within the current MONTHLY allowance window.
    The allowance refreshes every month; for a monthly plan that window is the
    Stripe billing period, for an annual plan it is the current monthly
    anniversary of the period start (see ``_monthly_window_start``) — so an
    annual subscriber gets 200/month across all 12 months, not 200/year.
    Trial: lifetime ledger sum; the limit formula max(3, credits +
    total_credits_used) is the legacy allocation invariant, preserved
    (equivalence proven in the design doc).

    ``now`` is injectable for deterministic tests; production passes None.
    """
    if now is None:
        now = _utcnow_naive()
    subscription = await _active_subscription(session, user.id)
    if subscription and subscription.current_period_start:
        period_start = _monthly_window_start(subscription.current_period_start, now)
        limit = subscription.credits_per_month
        limit_type = "monthly"
    else:
        period_start = None
        limit = max(3, user.credits + user.total_credits_used)
        limit_type = "trial"

    usage = await _ledger_usage(session, user.id, period_start)
    return {
        "usage": usage,
        "limit": limit,
        "limit_type": limit_type,
        "period_start": period_start,
        "subscription": subscription,
    }


def _limit_message(context: str, limit_type: str, usage: int, limit: int) -> str:
    if context == "re_search":
        return "Credit limit reached. Please upgrade your plan for more re-searches."
    if limit_type == "trial":
        return (
            f"Free trial exhausted ({usage}/{limit} checks used). "
            "Please upgrade your plan for more checks."
        )
    return (
        f"Monthly limit reached ({usage}/{limit} checks used). "
        "Please upgrade your plan for more checks."
    )


async def enforce_usage_limit(
    session: AsyncSession, user: User, *, context: str = "checks"
) -> User:
    """Lock the user row and enforce the usage limit (402 on exhaustion).

    Returns the locked User instance. Admins bypass the limit (but are
    still locked and subsequently debited, matching prior behaviour).
    """
    locked_result = await session.execute(
        select(User).where(User.id == user.id).with_for_update()
    )
    locked_user = locked_result.scalar_one()

    if _is_admin(locked_user):
        logger.info(f"Admin bypass: {locked_user.email} - skipping credit limit check")
        return locked_user

    snapshot = await get_usage_snapshot(session, locked_user)
    if snapshot["usage"] >= snapshot["limit"]:
        raise HTTPException(
            status_code=402,
            detail=_limit_message(
                context,
                snapshot["limit_type"],
                snapshot["usage"],
                snapshot["limit"],
            ),
        )
    return locked_user


def record_usage(
    session: AsyncSession,
    user: User,
    *,
    kind: str,
    check_id: Optional[str] = None,
) -> UsageEvent:
    """Append a 1-credit debit event and dual-write the legacy counters.

    Does NOT commit — call inside the same transaction as the gate so the
    row lock from ``enforce_usage_limit`` covers the debit.
    """
    if kind not in DEBIT_KINDS:
        raise ValueError(f"record_usage called with non-debit kind: {kind}")

    drew_trial = user.credits > 0
    event = UsageEvent(
        id=str(uuid.uuid4()),
        user_id=user.id,
        check_id=check_id,
        kind=kind,
        credits=1,
        drew_trial=drew_trial,
    )
    session.add(event)

    # Legacy dual-write (display/back-compat only — no gate reads these).
    if drew_trial:
        user.credits -= 1
    user.total_credits_used += 1
    return event


async def reserve_usage(
    session: AsyncSession,
    user: User,
    *,
    kind: str,
    check_id: Optional[str] = None,
    context: str = "checks",
) -> User:
    """Gate + debit in one locked transaction. Caller commits."""
    locked_user = await enforce_usage_limit(session, user, context=context)
    record_usage(session, locked_user, kind=kind, check_id=check_id)
    return locked_user


async def refund_usage(
    session: AsyncSession, check_id: str, user_id: Optional[str] = None
) -> bool:
    """Refund a check's debit. IDEMPOTENT. Caller commits.

    Mirrors the original debit exactly: the trial field is only re-credited
    when the debit drew from it (design D2 — closes the phantom-trial-credit
    bug for subscribers). total_credits_used is decremented to keep the
    trial allocation invariant constant under the ledger read path.
    """
    try:
        check_result = await session.execute(select(Check).where(Check.id == check_id))
        check = check_result.scalar_one_or_none()

        if not check:
            logger.error(f"Cannot refund: Check {check_id} not found")
            return False

        # Already refunded (marker doubles as ledger idempotency guard).
        if check.credits_used == 0:
            logger.info(f"Check {check_id} already refunded")
            return True

        credits_to_refund = check.credits_used

        user_result = await session.execute(
            select(User).where(User.id == (user_id or check.user_id))
        )
        user = user_result.scalar_one_or_none()
        if not user:
            logger.error(f"Cannot refund: User {user_id or check.user_id} not found")
            return False

        debit_result = await session.execute(
            select(UsageEvent).where(
                UsageEvent.check_id == check_id, UsageEvent.kind == KIND_CHECK
            )
        )
        debit = debit_result.scalars().first()
        drew_trial = bool(debit.drew_trial) if debit is not None else False

        session.add(
            UsageEvent(
                id=str(uuid.uuid4()),
                user_id=user.id,
                check_id=check_id,
                kind=KIND_REFUND,
                credits=-credits_to_refund,
                drew_trial=drew_trial,
            )
        )

        if drew_trial:
            user.credits += credits_to_refund
        user.total_credits_used = max(0, user.total_credits_used - credits_to_refund)
        check.credits_used = 0

        logger.info(f"Refunded {credits_to_refund} credit(s) for check {check_id}")
        return True

    except Exception as e:
        logger.error(f"Failed to refund credit: {e}")
        return False
