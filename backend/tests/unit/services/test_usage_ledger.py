"""
Tests for the usage ledger service (app/services/usage_ledger.py).

Covers:
- get_usage_snapshot -- subscriber period window vs trial lifetime window
- enforce_usage_limit -- 402 at the boundary, admin bypass, FOR UPDATE lock
- record_usage -- event shape, drew_trial capture, legacy dual-write,
  non-debit kind rejection
- reserve_usage -- gate + debit composition
- refund_usage -- idempotency, drew_trial mirroring (B3 regression: a
  subscriber refund must NOT mint a trial credit), pre-ledger fallback

Design: audit/2026-07-10_usage_ledger_design.md.
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.models.usage_event import (
    DEBIT_KINDS,
    KIND_CHECK,
    KIND_RE_SEARCH,
    KIND_REFUND,
    KIND_TOP_UP,
    UsageEvent,
)
from app.services.usage_ledger import (
    _monthly_window_start,
    enforce_usage_limit,
    get_usage_snapshot,
    record_usage,
    refund_usage,
    reserve_usage,
)


# ---------------------------------------------------------------------------
# Mock factories
# ---------------------------------------------------------------------------


def _user(credits=3, total_used=0, email="user@example.com", user_id="usr-1"):
    user = MagicMock()
    user.id = user_id
    user.email = email
    user.credits = credits
    user.total_credits_used = total_used
    return user


def _subscription(credits_per_month=200, period_start=datetime(2026, 7, 1)):
    sub = MagicMock()
    sub.credits_per_month = credits_per_month
    sub.current_period_start = period_start
    return sub


def _snapshot_session(subscription, usage_sum):
    """Session whose executes return: 1) subscription, 2) ledger sum."""
    session = AsyncMock()
    calls = {"n": 0}

    async def _exec(stmt):
        calls["n"] += 1
        result = MagicMock()
        if calls["n"] == 1:
            result.scalar_one_or_none.return_value = subscription
        else:
            result.scalar.return_value = usage_sum
        return result

    session.execute = AsyncMock(side_effect=_exec)
    return session


def _gate_session(locked_user, subscription, usage_sum):
    """Session for enforce_usage_limit: 1) locked user, 2) sub, 3) sum."""
    session = AsyncMock()
    calls = {"n": 0}
    seen_stmts = []

    async def _exec(stmt):
        calls["n"] += 1
        seen_stmts.append(stmt)
        result = MagicMock()
        if calls["n"] == 1:
            result.scalar_one.return_value = locked_user
        elif calls["n"] == 2:
            result.scalar_one_or_none.return_value = subscription
        else:
            result.scalar.return_value = usage_sum
        return result

    session.execute = AsyncMock(side_effect=_exec)
    session.add = MagicMock()
    return session, seen_stmts


# ---------------------------------------------------------------------------
# get_usage_snapshot
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestGetUsageSnapshot:
    async def test_subscriber_uses_period_window_and_plan_limit(self):
        sub = _subscription(credits_per_month=200)  # period_start 2026-07-01
        session = _snapshot_session(sub, usage_sum=42)

        # now within the first month -> the monthly window == period_start
        snap = await get_usage_snapshot(session, _user(), now=datetime(2026, 7, 20))

        assert snap["usage"] == 42
        assert snap["limit"] == 200
        assert snap["limit_type"] == "monthly"
        assert snap["period_start"] == sub.current_period_start
        assert snap["subscription"] is sub

    async def test_annual_snapshot_counts_from_current_monthly_window(self):
        # Annual sub started 2026-01-15; "now" is 3 months in. The allowance
        # must refresh monthly, so usage is summed from 2026-03-15 (the most
        # recent monthly anniversary), NOT from the annual period start.
        sub = _subscription(credits_per_month=200, period_start=datetime(2026, 1, 15))
        session = _snapshot_session(sub, usage_sum=0)

        with patch(
            "app.services.usage_ledger._ledger_usage",
            new=AsyncMock(return_value=17),
        ) as mock_usage:
            snap = await get_usage_snapshot(session, _user(), now=datetime(2026, 4, 3))

        assert snap["usage"] == 17
        assert snap["period_start"] == datetime(2026, 3, 15)
        # The ledger sum is taken FROM the monthly window start (3rd positional
        # arg `since`), proving only the current month's checks count.
        assert mock_usage.call_args.args[2] == datetime(2026, 3, 15)

    async def test_trial_uses_lifetime_window_and_allocation_limit(self):
        session = _snapshot_session(None, usage_sum=2)

        snap = await get_usage_snapshot(session, _user(credits=1, total_used=2))

        assert snap["usage"] == 2
        assert snap["limit"] == 3  # max(3, 1 + 2)
        assert snap["limit_type"] == "trial"
        assert snap["period_start"] is None

    async def test_trial_gifted_allocation_raises_limit(self):
        session = _snapshot_session(None, usage_sum=4)
        snap = await get_usage_snapshot(session, _user(credits=6, total_used=4))
        assert snap["limit"] == 10


# ---------------------------------------------------------------------------
# _monthly_window_start (annual allowance refresh)
# ---------------------------------------------------------------------------


class TestMonthlyWindowStart:
    def test_monthly_plan_returns_period_start(self):
        start = datetime(2026, 7, 1)
        now = datetime(2026, 7, 20)
        assert _monthly_window_start(start, now) == start

    def test_annual_advances_to_current_month_anniversary(self):
        start = datetime(2026, 1, 15)
        now = datetime(2026, 4, 3)  # most recent anniversary <= now is 15 Mar
        assert _monthly_window_start(start, now) == datetime(2026, 3, 15)

    def test_annual_on_the_anniversary_day(self):
        start = datetime(2026, 1, 15)
        now = datetime(2026, 4, 15)
        assert _monthly_window_start(start, now) == datetime(2026, 4, 15)

    def test_day_clamped_for_short_month(self):
        # 31 Jan anchor: the Feb anniversary clamps to 28; on 10 Mar the
        # current window still started at the clamped 28 Feb.
        start = datetime(2026, 1, 31)
        now = datetime(2026, 3, 10)
        assert _monthly_window_start(start, now) == datetime(2026, 2, 28)

    def test_now_before_start_returns_start(self):
        start = datetime(2026, 7, 1)
        now = datetime(2026, 6, 30)
        assert _monthly_window_start(start, now) == start

    def test_crosses_year_boundary(self):
        # anniversaries: 20 Dec, 20 Jan, 20 Feb (> now) -> window is 20 Jan
        start = datetime(2025, 11, 20)
        now = datetime(2026, 2, 5)
        assert _monthly_window_start(start, now) == datetime(2026, 1, 20)


# ---------------------------------------------------------------------------
# enforce_usage_limit
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestEnforceUsageLimit:
    async def test_locks_the_user_row(self):
        user = _user()
        session, seen = _gate_session(user, _subscription(), usage_sum=0)

        await enforce_usage_limit(session, user)

        # First statement is the user select and must carry FOR UPDATE.
        first = seen[0]
        assert first._for_update_arg is not None

    async def test_allows_below_limit(self):
        user = _user()
        session, _ = _gate_session(user, _subscription(200), usage_sum=199)
        result = await enforce_usage_limit(session, user)
        assert result is user

    async def test_402_at_limit(self):
        user = _user()
        session, _ = _gate_session(user, _subscription(200), usage_sum=200)
        with pytest.raises(HTTPException) as exc:
            await enforce_usage_limit(session, user)
        assert exc.value.status_code == 402
        assert "Monthly limit reached (200/200" in exc.value.detail

    async def test_402_trial_message(self):
        user = _user(credits=0, total_used=3)
        session, _ = _gate_session(user, None, usage_sum=3)
        with pytest.raises(HTTPException) as exc:
            await enforce_usage_limit(session, user)
        assert exc.value.status_code == 402
        assert "Free trial exhausted (3/3" in exc.value.detail

    async def test_402_re_search_message(self):
        user = _user(credits=0, total_used=3)
        session, _ = _gate_session(user, None, usage_sum=3)
        with pytest.raises(HTTPException) as exc:
            await enforce_usage_limit(session, user, context="re_search")
        assert "more re-searches" in exc.value.detail

    async def test_admin_bypasses_limit(self):
        user = _user(credits=0, total_used=500, email="admin@tru8.app")
        session, seen = _gate_session(user, None, usage_sum=500)
        with patch("app.services.usage_ledger.settings") as mock_settings:
            mock_settings.ADMIN_EMAILS = ["admin@tru8.app"]
            result = await enforce_usage_limit(session, user)
        assert result is user
        # Admin path returns straight after the lock — no usage queries.
        assert len(seen) == 1


# ---------------------------------------------------------------------------
# record_usage
# ---------------------------------------------------------------------------


class TestRecordUsage:
    def test_event_shape_and_trial_dual_write(self):
        user = _user(credits=2, total_used=1)
        session = MagicMock()

        event = record_usage(session, user, kind=KIND_CHECK, check_id="chk-1")

        session.add.assert_called_once_with(event)
        assert event.kind == KIND_CHECK
        assert event.credits == 1
        assert event.check_id == "chk-1"
        assert event.drew_trial is True
        assert user.credits == 1  # legacy decrement
        assert user.total_credits_used == 2  # legacy increment

    def test_subscriber_debit_does_not_touch_trial_field(self):
        user = _user(credits=0, total_used=10)
        session = MagicMock()

        event = record_usage(session, user, kind=KIND_RE_SEARCH, check_id="c")

        assert event.drew_trial is False
        assert user.credits == 0
        assert user.total_credits_used == 11

    def test_all_debit_kinds_accepted(self):
        for kind in DEBIT_KINDS:
            record_usage(MagicMock(), _user(), kind=kind)

    def test_non_debit_kind_rejected(self):
        with pytest.raises(ValueError):
            record_usage(MagicMock(), _user(), kind=KIND_REFUND)
        with pytest.raises(ValueError):
            record_usage(MagicMock(), _user(), kind="adjustment")


# ---------------------------------------------------------------------------
# reserve_usage (composition)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestReserveUsage:
    async def test_gate_then_debit(self):
        user = _user(credits=3, total_used=0)
        session, _ = _gate_session(user, _subscription(200), usage_sum=5)

        result = await reserve_usage(session, user, kind=KIND_TOP_UP, check_id="chk-9")

        assert result is user
        session.add.assert_called_once()
        event = session.add.call_args[0][0]
        assert isinstance(event, UsageEvent)
        assert event.kind == KIND_TOP_UP
        assert event.check_id == "chk-9"

    async def test_no_debit_when_gate_raises(self):
        user = _user(credits=0, total_used=3)
        session, _ = _gate_session(user, _subscription(200), usage_sum=200)

        with pytest.raises(HTTPException):
            await reserve_usage(session, user, kind=KIND_RE_SEARCH)

        session.add.assert_not_called()


# ---------------------------------------------------------------------------
# refund_usage
# ---------------------------------------------------------------------------


def _refund_session(check, user, debit_event):
    """Execute order in refund_usage: 1) Check, 2) User, 3) debit event."""
    session = AsyncMock()
    calls = {"n": 0}

    async def _exec(stmt):
        calls["n"] += 1
        result = MagicMock()
        if calls["n"] == 1:
            result.scalar_one_or_none.return_value = check
        elif calls["n"] == 2:
            result.scalar_one_or_none.return_value = user
        else:
            result.scalars.return_value.first.return_value = debit_event
        return result

    session.execute = AsyncMock(side_effect=_exec)
    session.add = MagicMock()
    return session, calls


def _check(credits_used=1, user_id="usr-1"):
    check = MagicMock()
    check.credits_used = credits_used
    check.user_id = user_id
    return check


def _debit(drew_trial):
    debit = MagicMock()
    debit.drew_trial = drew_trial
    return debit


@pytest.mark.asyncio
class TestRefundUsage:
    async def test_idempotent_already_refunded(self):
        check = _check(credits_used=0)
        session, calls = _refund_session(check, _user(), _debit(True))

        assert await refund_usage(session, "chk-1", "usr-1") is True
        assert calls["n"] == 1  # stops at the marker, adds nothing
        session.add.assert_not_called()

    async def test_trial_refund_restores_trial_field(self):
        check = _check(credits_used=1)
        user = _user(credits=2, total_used=1)
        session, _ = _refund_session(check, user, _debit(drew_trial=True))

        assert await refund_usage(session, "chk-1", "usr-1") is True
        assert user.credits == 3
        assert user.total_credits_used == 0
        assert check.credits_used == 0
        event = session.add.call_args[0][0]
        assert event.kind == KIND_REFUND
        assert event.credits == -1
        assert event.drew_trial is True

    async def test_subscriber_refund_does_not_mint_trial_credit(self):
        """B3 regression: drew_trial=False refund must not touch credits."""
        check = _check(credits_used=1)
        user = _user(credits=0, total_used=10)
        session, _ = _refund_session(check, user, _debit(drew_trial=False))

        assert await refund_usage(session, "chk-1", "usr-1") is True
        assert user.credits == 0  # NOT incremented
        assert user.total_credits_used == 9
        event = session.add.call_args[0][0]
        assert event.credits == -1
        assert event.drew_trial is False

    async def test_pre_ledger_check_treated_as_non_trial(self):
        check = _check(credits_used=1)
        user = _user(credits=5, total_used=3)
        session, _ = _refund_session(check, user, debit_event=None)

        assert await refund_usage(session, "chk-1", "usr-1") is True
        assert user.credits == 5  # no debit event -> drew_trial False
        assert user.total_credits_used == 2

    async def test_total_used_floors_at_zero(self):
        check = _check(credits_used=3)
        user = _user(credits=0, total_used=1)
        session, _ = _refund_session(check, user, _debit(drew_trial=False))

        assert await refund_usage(session, "chk-1", "usr-1") is True
        assert user.total_credits_used == 0

    async def test_missing_check_returns_false(self):
        session, _ = _refund_session(None, _user(), None)
        assert await refund_usage(session, "chk-x", "usr-1") is False

    async def test_missing_user_returns_false(self):
        check = _check(credits_used=1)
        session, _ = _refund_session(check, None, None)
        assert await refund_usage(session, "chk-1", "usr-1") is False

    async def test_falls_back_to_check_user_id(self):
        check = _check(credits_used=1, user_id="usr-9")
        user = _user(user_id="usr-9")
        session, _ = _refund_session(check, user, _debit(drew_trial=False))

        assert await refund_usage(session, "chk-1", None) is True
