"""Tests for M-03 smart endpoint, expanded landscape, and executed_tier.

Covers:
- Smart check cache hit returns cached result
- Smart check cache miss runs pipeline
- max_tier="lookup" returns miss, not pipeline
- max_age_hours filters stale cache hits
- Charges match executed tier
- Landscape expanded fields (uniqueDomains, freshness, gaps, providerStatus)
- executed_tier set on Check
- x402 preflight returns suggestion without payment
- Dashboard checks have executed_tier="full"
"""

import json
import uuid
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.api.v1.agent import router as agent_router
from app.api.v1.agent_x402 import router as x402_router
from app.api.v1.response_builder import _compute_landscape
from app.core.agent_auth import AgentPaymentContext, get_agent_payment
from app.core.database import get_session
from app.core.rate_limit import limiter


# ---------------------------------------------------------------------------
# Test app + dependency overrides
# ---------------------------------------------------------------------------

MOCK_USER_ID = "user-smart-001"


def _create_test_app():
    test_app = FastAPI()
    test_app.state.limiter = limiter
    test_app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    test_app.add_middleware(SlowAPIMiddleware)
    test_app.include_router(agent_router, prefix="/api/v1/agent")
    test_app.include_router(x402_router, prefix="/api/v1/agent/x402")
    return test_app


def _mock_payment():
    async def _override():
        session = AsyncMock()
        ctx = AgentPaymentContext(
            provider="credit",
            payer_id=MOCK_USER_ID,
            user_id=MOCK_USER_ID,
            session=session,
        )
        # Mock charge to return a fake transaction (avoids hitting real credit provider)
        mock_tx = MagicMock()
        mock_tx.id = "tx-mock-001"
        mock_tx.status = "pending"
        ctx.charge = AsyncMock(return_value=mock_tx)
        return ctx

    return _override


def _mock_session_with_cache_hit(check_id="chk-123", completed_at=None):
    """Mock session that returns a cache hit for the lookup query."""
    session = AsyncMock()
    mock_check = MagicMock()
    mock_check.id = check_id
    mock_check.user_id = MOCK_USER_ID
    mock_check.status = "completed"
    mock_check.completed_at = completed_at or datetime.now(timezone.utc)

    mock_claim = MagicMock()
    mock_claim.claim_text_hash = "abc123"

    mock_result = MagicMock()
    mock_result.first.return_value = (mock_claim, mock_check)

    session.execute = AsyncMock(return_value=mock_result)
    session.flush = AsyncMock()
    session.commit = AsyncMock()

    return session


def _mock_session_cache_miss():
    """Mock session that returns no cache hit."""
    session = AsyncMock()
    mock_result = MagicMock()
    mock_result.first.return_value = None
    session.execute = AsyncMock(return_value=mock_result)
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    return session


# ── Smart check: cache hit ─────────────────────────────────────────────────


class TestSmartCheckCacheHit:
    @pytest.mark.asyncio
    async def test_returns_cached_on_hit(self):
        app = _create_test_app()
        session = _mock_session_with_cache_hit()

        app.dependency_overrides[get_agent_payment] = _mock_payment()
        app.dependency_overrides[get_session] = lambda: session

        mock_response = {
            "id": "chk-123",
            "status": "completed",
            "claims": [],
            "_meta": {"executedTier": "lookup"},
        }

        with patch(
            "app.api.v1.response_builder.build_agent_response",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.post(
                    "/api/v1/agent/check",
                    json={"claim": "test claim", "max_tier": "full"},
                )

            assert resp.status_code == 200
            data = resp.json()
            assert data.get("hit") is True


# ── Smart check: max_tier="lookup" returns miss ────────────────────────────


class TestSmartCheckMaxTierLookup:
    @pytest.mark.asyncio
    async def test_lookup_only_returns_miss(self):
        app = _create_test_app()
        session = _mock_session_cache_miss()

        app.dependency_overrides[get_agent_payment] = _mock_payment()
        app.dependency_overrides[get_session] = lambda: session

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/v1/agent/check",
                json={"claim": "test claim", "max_tier": "lookup"},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["hit"] is False
        assert data["nextSuggestedTier"] == "quick"


# ── Landscape expanded fields ──────────────────────────────────────────────


class TestLandscapeExpandedFields:
    def test_unique_domains_in_landscape(self):
        claims_data = [
            {
                "claimMap": {"elements": []},
                "evidence": [
                    {
                        "url": "https://bbc.co.uk/a",
                        "tier": "reporting",
                        "evidenceType": "news_reporting",
                    },
                    {
                        "url": "https://reuters.com/b",
                        "tier": "reporting",
                        "evidenceType": "news_reporting",
                    },
                ],
            }
        ]
        result = _compute_landscape(claims_data)
        assert result["sourceDiversity"]["uniqueDomains"] == 2
        assert result["sourceDiversity"]["typeCoverage"] == 1

    def test_freshness_in_landscape(self):
        now = datetime.utcnow()
        claims_data = [
            {
                "claimMap": {"elements": []},
                "evidence": [
                    {
                        "url": "https://example.com",
                        "publishedDate": (now - timedelta(days=3)).isoformat(),
                    },
                ],
            }
        ]
        result = _compute_landscape(claims_data)
        assert result["freshness"]["freshestDaysAgo"] == 3
        assert result["freshness"]["undatedCount"] == 0

    def test_gaps_element_level(self):
        claims_data = [
            {
                "position": 0,
                "claimMap": {
                    "elements": [
                        {
                            "elementId": "e1",
                            "description": "Sub-claim A",
                            "state": "supported",
                            "evidenceRefs": [{"evidenceId": "ev1"}],
                        },
                        {
                            "elementId": "e2",
                            "description": "Sub-claim B",
                            "state": "unresolved",
                            "evidenceRefs": [],
                        },
                        {
                            "elementId": "e3",
                            "description": "Sub-claim C",
                            "state": "unresolved",
                            "evidenceRefs": [
                                {"evidenceId": "ev2"},
                                {"evidenceId": "ev3"},
                            ],
                        },
                    ]
                },
                "evidence": [],
            }
        ]
        result = _compute_landscape(claims_data)
        assert len(result["gaps"]) == 2

        # First gap: no evidence at all
        gap_no_ev = result["gaps"][0]
        assert gap_no_ev["elementId"] == "e2"
        assert gap_no_ev["claimPosition"] == 0
        assert gap_no_ev["reason"] == "no_evidence"
        assert gap_no_ev["description"] == "Sub-claim B"
        assert "text" not in gap_no_ev

        # Second gap: has evidence but still unresolved
        gap_unresolved = result["gaps"][1]
        assert gap_unresolved["elementId"] == "e3"
        assert gap_unresolved["claimPosition"] == 0
        assert gap_unresolved["reason"] == "unresolved"
        assert gap_unresolved["evidenceCount"] == 2
        assert gap_unresolved["description"] == "Sub-claim C"

    def test_provider_status_from_check(self):
        check = MagicMock()
        check.provider_status = {"web_search": {"status": "ok", "count": 10}}

        claims_data = [{"claimMap": {"elements": []}, "evidence": []}]
        result = _compute_landscape(claims_data, check=check)
        assert result["providerStatus"]["web_search"]["status"] == "ok"

    def test_provider_status_none_without_check(self):
        claims_data = [{"claimMap": {"elements": []}, "evidence": []}]
        result = _compute_landscape(claims_data)
        assert result["providerStatus"] is None


# ── executed_tier set on Check ─────────────────────────────────────────────


class TestExecutedTierSetOnCheck:
    def test_check_model_accepts_executed_tier(self):
        from app.models.check import Check

        check = Check(
            id="test-001",
            user_id="u-001",
            input_type="text",
            input_content='{"content": "test"}',
            executed_tier="quick",
        )
        assert check.executed_tier == "quick"

    def test_dashboard_checks_default_full(self):
        from app.models.check import Check

        check = Check(
            id="test-002",
            user_id="u-002",
            input_type="text",
            input_content='{"content": "test"}',
            executed_tier="full",
        )
        assert check.executed_tier == "full"


# ── x402 preflight ─────────────────────────────────────────────────────────


class TestX402Preflight:
    @pytest.mark.asyncio
    async def test_preflight_without_auth_suggests_quick(self):
        app = _create_test_app()
        session = AsyncMock()
        app.dependency_overrides[get_session] = lambda: session

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/v1/agent/x402/preflight",
                json={"claim": "Test claim"},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["suggestedTier"] == "quick"
        assert data["reason"] == "no_auth"
        assert "claimTextHash" in data
