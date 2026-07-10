"""
Tests for the re-search credit seam (checks._reserve_re_search_credit).

B1 regression (design 2026-07-10): subscriber re-searches/top-ups must land
in the usage ledger — the same sum the monthly gate reads — not just the
legacy User counters. B5 regression: the debit is committed by the helper
itself, so endpoints can (and do) call it BEFORE launching background work.

Full debit/refund semantics: tests/unit/services/test_usage_ledger.py.
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.api.v1.checks import _reserve_re_search_credit
from app.models.usage_event import UsageEvent


def _make_user(credits=0, total_used=10):
    user = MagicMock()
    user.id = "usr-1"
    user.email = "subscriber@example.com"
    user.credits = credits
    user.total_credits_used = total_used
    return user


def _subscription(credits_per_month=200):
    sub = MagicMock()
    sub.credits_per_month = credits_per_month
    sub.current_period_start = datetime(2026, 7, 1)
    return sub


def _session(user, subscription, usage):
    """Execute order: 1) locked user, 2) subscription, 3) ledger sum."""
    session = AsyncMock()
    calls = {"n": 0}

    async def _exec(stmt):
        calls["n"] += 1
        result = MagicMock()
        if calls["n"] == 1:
            result.scalar_one.return_value = user
        elif calls["n"] == 2:
            result.scalar_one_or_none.return_value = subscription
        else:
            result.scalar.return_value = usage
        return result

    session.execute = AsyncMock(side_effect=_exec)
    session.add = MagicMock()
    session.commit = AsyncMock()
    return session


@pytest.mark.asyncio
class TestReserveReSearchCredit:
    async def test_subscriber_debit_lands_in_ledger_and_commits(self):
        """B1: the debit is a usage_events row in the period the gate sums."""
        user = _make_user()
        session = _session(user, _subscription(200), usage=42)

        with patch(
            "app.api.v1.checks.get_or_create_user", new_callable=AsyncMock
        ) as mock_get_user:
            mock_get_user.return_value = user
            await _reserve_re_search_credit(
                session, {"sub": "usr-1"}, kind="re_search", check_id="chk-1"
            )

        session.add.assert_called_once()
        event = session.add.call_args[0][0]
        assert isinstance(event, UsageEvent)
        assert event.kind == "re_search"
        assert event.check_id == "chk-1"
        assert event.credits == 1
        # B5: committed by the helper itself, before any background task.
        session.commit.assert_awaited_once()

    async def test_top_up_kind_passes_through(self):
        user = _make_user()
        session = _session(user, _subscription(200), usage=0)

        with patch(
            "app.api.v1.checks.get_or_create_user", new_callable=AsyncMock
        ) as mock_get_user:
            mock_get_user.return_value = user
            await _reserve_re_search_credit(
                session, {"sub": "usr-1"}, kind="top_up", check_id="chk-2"
            )

        assert session.add.call_args[0][0].kind == "top_up"

    async def test_at_limit_raises_402_without_debit_or_commit(self):
        user = _make_user()
        session = _session(user, _subscription(200), usage=200)

        with patch(
            "app.api.v1.checks.get_or_create_user", new_callable=AsyncMock
        ) as mock_get_user:
            mock_get_user.return_value = user
            with pytest.raises(HTTPException) as exc:
                await _reserve_re_search_credit(
                    session, {"sub": "usr-1"}, kind="re_search", check_id="chk-3"
                )

        assert exc.value.status_code == 402
        assert "re-searches" in exc.value.detail
        session.add.assert_not_called()
        session.commit.assert_not_awaited()
