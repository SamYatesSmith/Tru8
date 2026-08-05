"""A served result must declare the tier that produced it, and what that tier withheld.

WHY THIS FILE EXISTS
--------------------
Found by auditing the paid agent path against production, 2026-08-05.

The cache lookup matches on `claim_text_hash` + `user_id` + completed — **tier
is not part of the match**. So a caller requesting `full` can be served an
analysis produced by `quick`, charged the 2p lookup rate, and told:

    "_meta": {"executedTier": "lookup", "limitations": []}

`executedTier: lookup` describes what THIS request did; it says nothing about
how the underlying analysis was produced. With `limitations: []` beside it, a
caller has no way to discover they received the reduced pipeline — no API
sources, heuristic classification, 8 sources instead of 20. `Check.executed_tier`
recorded the answer the whole time and was not read.

Five call sites served stored checks this way: the smart-check cache hit,
`agent_lookup`, `get_agent_result`, `x402_lookup` and `x402_result`. Two of
them went further and hardcoded `executed_tier="full"`, stating something
untrue rather than merely omitting it.

Also covered: `max_age_hours=0` was falsy, so the freshness filter was skipped
entirely and 0 meant "any age is fine" rather than "never serve cache". Until
this fix a caller could not force a fresh run at all.

Invariant #5: no hidden curation — every exclusion has a receipt.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.api.v1.agent import router as agent_router
from app.core.agent_auth import AgentPaymentContext, get_agent_payment
from app.core.database import get_session
from app.core.rate_limit import limiter
from app.core.tier_limitations import limitations_for_tier

MOCK_USER_ID = "user-receipts-001"


def _create_test_app():
    app = FastAPI()
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)
    app.include_router(agent_router, prefix="/api/v1/agent")
    return app


def _mock_payment():
    async def _override():
        ctx = AgentPaymentContext(
            provider="credit",
            payer_id=MOCK_USER_ID,
            user_id=MOCK_USER_ID,
            session=AsyncMock(),
        )
        tx = MagicMock()
        tx.id = "tx-receipts-001"
        tx.status = "pending"
        ctx.charge = AsyncMock(return_value=tx)
        return ctx

    return _override


def _session_with_cached_check(executed_tier, completed_at=None):
    """Cache hit for a check produced by `executed_tier`.

    `scalar_one_or_none` returns None so the consensus step finds nothing and
    the request continues, rather than short-circuiting on a MagicMock.
    """
    session = AsyncMock()
    check = MagicMock()
    check.id = "chk-receipts"
    check.user_id = MOCK_USER_ID
    check.status = "completed"
    check.executed_tier = executed_tier
    check.completed_at = completed_at or datetime.now(timezone.utc)

    claim = MagicMock()
    claim.claim_text_hash = "hash-receipts"

    result = MagicMock()
    result.first.return_value = (claim, check)
    result.scalar_one_or_none.return_value = None

    session.execute = AsyncMock(return_value=result)
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    return session


async def _post(app, payload):
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        return await client.post("/api/v1/agent/check", json=payload)


# ---------------------------------------------------------------------------
# The defect, pinned
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cached_quick_result_declares_quick_limitations():
    """Ask for full, get served a cached quick analysis — the receipt must say so.

    This is the defect exactly: before the fix this call returned
    `limitations: []` for a result produced without API sources, without LLM
    classification, and capped at 8 sources.
    """
    app = _create_test_app()
    session = _session_with_cached_check(executed_tier="quick")
    app.dependency_overrides[get_agent_payment] = _mock_payment()
    app.dependency_overrides[get_session] = lambda: session

    with patch(
        "app.api.v1.response_builder.build_agent_response",
        new_callable=AsyncMock,
        return_value={"id": "chk-receipts", "status": "completed", "_meta": {}},
    ) as builder:
        resp = await _post(app, {"claim": "a claim", "max_tier": "full"})

    assert resp.status_code == 200
    kwargs = builder.await_args.kwargs
    assert kwargs["limitations"] == limitations_for_tier("quick")
    assert kwargs["limitations"], "a quick-produced result must declare omissions"
    assert kwargs["cached_tier"] == "quick"


@pytest.mark.asyncio
async def test_cached_full_result_declares_nothing():
    """The complement: a full-produced cached result withheld nothing."""
    app = _create_test_app()
    session = _session_with_cached_check(executed_tier="full")
    app.dependency_overrides[get_agent_payment] = _mock_payment()
    app.dependency_overrides[get_session] = lambda: session

    with patch(
        "app.api.v1.response_builder.build_agent_response",
        new_callable=AsyncMock,
        return_value={"id": "chk-receipts", "status": "completed", "_meta": {}},
    ) as builder:
        resp = await _post(app, {"claim": "a claim", "max_tier": "full"})

    assert resp.status_code == 200
    kwargs = builder.await_args.kwargs
    assert kwargs["limitations"] == []
    assert kwargs["cached_tier"] == "full"


@pytest.mark.asyncio
async def test_pre_column_rows_claim_nothing_rather_than_guessing():
    """Checks written before `executed_tier` existed have None.

    Inventing a receipt for them would be worse than omitting one.
    """
    app = _create_test_app()
    session = _session_with_cached_check(executed_tier=None)
    app.dependency_overrides[get_agent_payment] = _mock_payment()
    app.dependency_overrides[get_session] = lambda: session

    with patch(
        "app.api.v1.response_builder.build_agent_response",
        new_callable=AsyncMock,
        return_value={"id": "chk-receipts", "status": "completed", "_meta": {}},
    ) as builder:
        resp = await _post(app, {"claim": "a claim", "max_tier": "full"})

    assert resp.status_code == 200
    assert builder.await_args.kwargs["limitations"] == []


# ---------------------------------------------------------------------------
# max_age_hours=0 must mean "never serve cache"
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_max_age_hours_zero_forces_a_fresh_run():
    """0 is falsy — the old `if body.max_age_hours` skipped the filter entirely.

    The documented meaning is "skip cache hits older than this many hours", so 0
    must reject every cached result. Before this fix there was no way for any
    caller to demand a fresh analysis.
    """
    app = _create_test_app()
    session = _session_with_cached_check(executed_tier="full")
    app.dependency_overrides[get_agent_payment] = _mock_payment()
    app.dependency_overrides[get_session] = lambda: session

    with patch(
        "app.api.v1.agent._run_agent_pipeline",
        new_callable=AsyncMock,
        return_value=MagicMock(status_code=200),
    ) as run_pipeline:
        await _post(app, {"claim": "a claim", "max_tier": "full", "max_age_hours": 0})

    assert run_pipeline.await_count == 1, "cache was served despite max_age_hours=0"
    assert run_pipeline.await_args.kwargs["tier"] == "full"


@pytest.mark.asyncio
async def test_omitted_max_age_hours_still_serves_cache():
    """The default path must not change — absent means no freshness constraint."""
    app = _create_test_app()
    session = _session_with_cached_check(executed_tier="full")
    app.dependency_overrides[get_agent_payment] = _mock_payment()
    app.dependency_overrides[get_session] = lambda: session

    with patch(
        "app.api.v1.response_builder.build_agent_response",
        new_callable=AsyncMock,
        return_value={"id": "chk-receipts", "status": "completed", "_meta": {}},
    ) as builder:
        resp = await _post(app, {"claim": "a claim", "max_tier": "full"})

    assert resp.status_code == 200
    assert builder.await_count == 1
    assert builder.await_args.kwargs["executed_tier"] == "lookup"
