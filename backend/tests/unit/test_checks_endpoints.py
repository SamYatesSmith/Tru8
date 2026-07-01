"""Tests for checks API HTTP endpoints — full request/response cycle.

Covers the 16 endpoint tests planned in K04 that test routing, auth,
validation, and response shapes via FastAPI dependency overrides.

Endpoints tested:
- GET /               (list checks)
- GET /{id}           (get check detail)
- PATCH /select-claims (claim selection)
- PATCH .../bounty    (bounty text)
- GET /public/{id}    (public report — no auth)
- GET /{id}/sources   (reviewed sources)
"""

import json
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

from app.api.v1.checks import router
from app.core.auth import get_current_user_or_api_key
from app.core.database import get_session


# ---------------------------------------------------------------------------
# Test app + dependency overrides
# ---------------------------------------------------------------------------

MOCK_USER = {"id": "user-001", "email": "test@tru8.app"}


def _create_test_app():
    """Build a minimal FastAPI app with the checks router mounted."""
    app = FastAPI()
    app.include_router(router, prefix="/api/v1/checks")
    return app


def _mock_auth_override():
    """Dependency override that always returns MOCK_USER."""

    async def _override():
        return MOCK_USER

    return _override


# ---------------------------------------------------------------------------
# Mock model factories
# ---------------------------------------------------------------------------


def _make_check(
    check_id=None,
    user_id="user-001",
    status="completed",
    input_type="text",
    **kwargs,
):
    """Build a MagicMock resembling a Check DB row."""
    c = MagicMock()
    c.id = check_id or str(uuid.uuid4())
    c.user_id = user_id
    c.status = status
    c.input_type = input_type
    c.input_url = kwargs.get("input_url")
    c.input_content = kwargs.get("input_content", json.dumps({"content": "test"}))
    c.article_excerpt = kwargs.get("article_excerpt", "Test excerpt")
    c.credits_used = kwargs.get("credits_used", 1)
    c.processing_time_ms = kwargs.get("processing_time_ms", 500)
    c.error_message = kwargs.get("error_message")
    c.entry_mode = kwargs.get("entry_mode", "focused")
    c.selected_claims_count = kwargs.get("selected_claims_count", 1)
    c.article_domain = kwargs.get("article_domain")
    c.article_secondary_domains = kwargs.get("article_secondary_domains")
    c.article_jurisdiction = kwargs.get("article_jurisdiction")
    c.article_classification_source = kwargs.get("article_classification_source")
    c.article_classification_confidence = kwargs.get(
        "article_classification_confidence"
    )
    c.user_query = kwargs.get("user_query")
    c.query_response = kwargs.get("query_response")
    c.query_confidence = kwargs.get("query_confidence")
    c.query_sources = kwargs.get("query_sources")
    c.raw_sources_count = kwargs.get("raw_sources_count", 10)
    c.created_at = kwargs.get("created_at", datetime(2026, 1, 15, 12, 0, 0))
    c.completed_at = kwargs.get("completed_at", datetime(2026, 1, 15, 12, 0, 5))
    return c


def _make_claim(
    claim_id=None,
    check_id="check-001",
    position=0,
    text="The earth is round",
    **kwargs,
):
    """Build a MagicMock resembling a Claim DB row."""
    cl = MagicMock()
    cl.id = claim_id or str(uuid.uuid4())
    cl.check_id = check_id
    cl.text = text
    cl.position = position
    cl.claim_type = kwargs.get("claim_type", "factual")
    cl.is_selected = kwargs.get("is_selected", True)
    cl.significance_rank = kwargs.get("significance_rank", 1)
    cl.subject_context = kwargs.get("subject_context")
    cl.key_entities = kwargs.get("key_entities", [])
    cl.source_title = kwargs.get("source_title")
    cl.source_url = kwargs.get("source_url")
    cl.is_time_sensitive = kwargs.get("is_time_sensitive", False)
    cl.time_reference = kwargs.get("time_reference")
    cl.claim_map = kwargs.get(
        "claim_map",
        {
            "normalised_claim": text,
            "claim_type": "factual",
            "elements": [
                {
                    "element_id": "e1",
                    "description": "Test element",
                    "evidence_refs": [],
                    "state": "supported",
                }
            ],
            "orientation": "Evidence supports this claim.",
        },
    )
    return cl


def _make_evidence(evidence_id=None, claim_id="claim-001", **kwargs):
    """Build a MagicMock resembling an Evidence DB row."""
    ev = MagicMock()
    ev.id = evidence_id or str(uuid.uuid4())
    ev.claim_id = claim_id
    ev.evidence_id = kwargs.get("evidence_id_field", f"ev-{ev.id[:8]}")
    ev.source = kwargs.get("source", "Reuters")
    ev.url = kwargs.get("url", "https://reuters.com/article")
    ev.title = kwargs.get("title", "Test Article")
    ev.snippet = kwargs.get("snippet", "Evidence snippet text")
    ev.published_date = kwargs.get("published_date")
    ev.relevance_score = kwargs.get("relevance_score", 0.85)
    ev.tier = kwargs.get("tier", "reporting")
    ev.evidence_type = kwargs.get("evidence_type", "news")
    ev.receipt_status = kwargs.get("receipt_status", "shown")
    ev.corroboration_group_id = kwargs.get("corroboration_group_id")
    ev.corroborating_evidence_ids = kwargs.get("corroborating_evidence_ids")
    ev.is_factcheck = kwargs.get("is_factcheck", False)
    ev.external_source_provider = kwargs.get("external_source_provider")
    ev.source_type = kwargs.get("source_type")
    ev.factcheck_publisher = kwargs.get("factcheck_publisher")
    ev.factcheck_rating = kwargs.get("factcheck_rating")
    ev.context_before = kwargs.get("context_before")
    ev.context_after = kwargs.get("context_after")
    ev.archived_url = kwargs.get("archived_url")
    return ev


class _MockExecuteResult:
    """Mock for SQLAlchemy execute() result supporting scalar_one_or_none and scalars."""

    def __init__(self, rows=None, scalar=None):
        self._rows = rows or []
        self._scalar_value = scalar

    def scalar_one_or_none(self):
        return self._scalar_value

    def scalars(self):
        return self

    def all(self):
        return self._rows

    def scalar(self):
        return self._scalar_value


def _make_session(*execute_returns):
    """Build a mock async session with chained execute() return values."""
    session = AsyncMock()
    results = [_MockExecuteResult(**r) for r in execute_returns]
    session.execute = AsyncMock(side_effect=results)
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.add = MagicMock()
    return session


# ===========================================================================
# GET / — List checks
# ===========================================================================


class TestGetChecks:
    """GET /api/v1/checks — list user's checks."""

    @pytest.mark.asyncio
    async def test_get_checks_empty(self):
        """No checks → returns empty list."""
        app = _create_test_app()
        session = _make_session(
            {"rows": []},  # checks query
        )
        app.dependency_overrides[get_current_user_or_api_key] = _mock_auth_override()
        app.dependency_overrides[get_session] = lambda: session

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/v1/checks")

        assert resp.status_code == 200
        data = resp.json()
        assert data["checks"] == []
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_get_checks_with_data(self):
        """Returns checks list with preview claim."""
        check = _make_check(check_id="check-list-1")
        claim = _make_claim(check_id="check-list-1", text="Test claim")

        app = _create_test_app()
        session = _make_session(
            {"rows": [check]},  # checks query
            {"scalar": claim},  # first claim for check
            {"scalar": 1},  # claims count
        )
        app.dependency_overrides[get_current_user_or_api_key] = _mock_auth_override()
        app.dependency_overrides[get_session] = lambda: session

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/v1/checks")

        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert len(data["checks"]) == 1
        assert data["checks"][0]["id"] == "check-list-1"
        assert data["checks"][0]["claimsCount"] == 1


# ===========================================================================
# GET /{id} — Get check detail
# ===========================================================================


class TestGetCheck:
    """GET /api/v1/checks/{id} — check detail with claims and evidence."""

    @pytest.mark.asyncio
    async def test_get_check_not_found(self):
        """Non-existent check → 404."""
        app = _create_test_app()
        session = _make_session(
            {"scalar": None},  # check not found
        )
        app.dependency_overrides[get_current_user_or_api_key] = _mock_auth_override()
        app.dependency_overrides[get_session] = lambda: session

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/v1/checks/nonexistent-id")

        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_get_check_success(self):
        """Valid check → returns full response with claims."""
        check = _make_check(check_id="check-detail-1")
        claim = _make_claim(check_id="check-detail-1", claim_id="claim-d1")
        evidence = _make_evidence(claim_id="claim-d1")

        app = _create_test_app()
        session = _make_session(
            {"scalar": check},  # check lookup
            {"rows": [claim]},  # claims query
            {"rows": []},  # raw evidence counts
            {"rows": [evidence]},  # evidence for claim
        )
        app.dependency_overrides[get_current_user_or_api_key] = _mock_auth_override()
        app.dependency_overrides[get_session] = lambda: session

        with patch("app.api.v1.checks.redis") as mock_redis:
            mock_redis_client = MagicMock()
            mock_redis_client.get.return_value = None
            mock_redis_client.close.return_value = None
            mock_redis.from_url.return_value = mock_redis_client

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.get("/api/v1/checks/check-detail-1")

        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == "check-detail-1"
        assert data["status"] == "completed"
        assert len(data["claims"]) == 1
        assert data["claims"][0]["text"] == "The earth is round"

    @pytest.mark.asyncio
    async def test_get_check_wrong_user(self):
        """Check belonging to different user → 404."""
        app = _create_test_app()
        # Query returns None because WHERE clause includes user_id
        session = _make_session(
            {"scalar": None},
        )
        app.dependency_overrides[get_current_user_or_api_key] = _mock_auth_override()
        app.dependency_overrides[get_session] = lambda: session

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/v1/checks/other-users-check")

        assert resp.status_code == 404


# ===========================================================================
# PATCH /{id}/select-claims
# ===========================================================================


class TestSelectClaims:
    """PATCH /api/v1/checks/{id}/select-claims — claim selection gate."""

    @pytest.mark.asyncio
    async def test_select_claims_not_found(self):
        """Non-existent check → 404."""
        app = _create_test_app()
        session = _make_session(
            {"scalar": None},
        )
        app.dependency_overrides[get_current_user_or_api_key] = _mock_auth_override()
        app.dependency_overrides[get_session] = lambda: session

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.patch(
                "/api/v1/checks/missing/select-claims",
                json={"selected_positions": [0]},
            )

        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_select_claims_wrong_status(self):
        """Check not in waiting_for_selection → 409."""
        check = _make_check(check_id="check-sel-1", status="completed")

        app = _create_test_app()
        session = _make_session(
            {"scalar": check},
        )
        app.dependency_overrides[get_current_user_or_api_key] = _mock_auth_override()
        app.dependency_overrides[get_session] = lambda: session

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.patch(
                "/api/v1/checks/check-sel-1/select-claims",
                json={"selected_positions": [0]},
            )

        assert resp.status_code == 409
        assert "not waiting" in resp.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_select_claims_empty_positions(self):
        """Empty positions list → 400."""
        check = _make_check(check_id="check-sel-2", status="waiting_for_selection")

        app = _create_test_app()
        session = _make_session(
            {"scalar": check},
        )
        app.dependency_overrides[get_current_user_or_api_key] = _mock_auth_override()
        app.dependency_overrides[get_session] = lambda: session

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.patch(
                "/api/v1/checks/check-sel-2/select-claims",
                json={"selected_positions": []},
            )

        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_select_claims_invalid_positions(self):
        """Position not in claims → 400."""
        check = _make_check(check_id="check-sel-3", status="waiting_for_selection")
        claim0 = _make_claim(check_id="check-sel-3", position=0)

        app = _create_test_app()
        session = _make_session(
            {"scalar": check},  # check lookup
            {"rows": [claim0]},  # claims query (only position 0)
        )
        app.dependency_overrides[get_current_user_or_api_key] = _mock_auth_override()
        app.dependency_overrides[get_session] = lambda: session

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.patch(
                "/api/v1/checks/check-sel-3/select-claims",
                json={"selected_positions": [0, 99]},
            )

        assert resp.status_code == 400
        assert "99" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_select_claims_success(self):
        """Valid selection → 200, fires Phase 2."""
        check = _make_check(
            check_id="check-sel-ok",
            status="waiting_for_selection",
            input_content=json.dumps({"content": "test", "url": None}),
        )
        claim0 = _make_claim(check_id="check-sel-ok", position=0)
        claim1 = _make_claim(check_id="check-sel-ok", position=1, text="Second claim")

        app = _create_test_app()
        session = _make_session(
            {"scalar": check},  # check lookup
            {"rows": [claim0, claim1]},  # claims query
        )
        app.dependency_overrides[get_current_user_or_api_key] = _mock_auth_override()
        app.dependency_overrides[get_session] = lambda: session

        with patch("app.api.v1.checks.asyncio.create_task") as mock_task:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.patch(
                    "/api/v1/checks/check-sel-ok/select-claims",
                    json={"selected_positions": [0]},
                )

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "processing"
        assert data["selectedCount"] == 1
        # Phase 2 task was created
        mock_task.assert_called_once()


# ===========================================================================
# PATCH .../bounty
# ===========================================================================


class TestUpdateBounty:
    """PATCH .../bounty — element bounty text update."""

    @pytest.mark.asyncio
    async def test_bounty_check_not_found(self):
        """Non-existent check → 404."""
        app = _create_test_app()
        session = _make_session({"scalar": None})
        app.dependency_overrides[get_current_user_or_api_key] = _mock_auth_override()
        app.dependency_overrides[get_session] = lambda: session

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.patch(
                "/api/v1/checks/missing/claims/c1/elements/e1/bounty",
                json={"text": "test"},
            )

        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_bounty_not_completed(self):
        """Check not completed → 409."""
        check = _make_check(check_id="check-b1", status="processing")

        app = _create_test_app()
        session = _make_session({"scalar": check})
        app.dependency_overrides[get_current_user_or_api_key] = _mock_auth_override()
        app.dependency_overrides[get_session] = lambda: session

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.patch(
                "/api/v1/checks/check-b1/claims/c1/elements/e1/bounty",
                json={"text": "test"},
            )

        assert resp.status_code == 409

    @pytest.mark.asyncio
    async def test_bounty_too_long(self):
        """Text >200 chars → 400."""
        check = _make_check(check_id="check-b2", status="completed")

        app = _create_test_app()
        session = _make_session({"scalar": check})
        app.dependency_overrides[get_current_user_or_api_key] = _mock_auth_override()
        app.dependency_overrides[get_session] = lambda: session

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.patch(
                "/api/v1/checks/check-b2/claims/c1/elements/e1/bounty",
                json={"text": "x" * 201},
            )

        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_bounty_success(self):
        """Valid bounty text → updates claim_map element."""
        check = _make_check(check_id="check-b3", status="completed")
        claim = _make_claim(
            claim_id="claim-b3",
            check_id="check-b3",
            claim_map={
                "elements": [
                    {"element_id": "e1", "description": "Test", "state": "unresolved"}
                ]
            },
        )

        app = _create_test_app()
        session = _make_session(
            {"scalar": check},  # check lookup
            {"scalar": claim},  # claim lookup
        )
        app.dependency_overrides[get_current_user_or_api_key] = _mock_auth_override()
        app.dependency_overrides[get_session] = lambda: session

        with patch("sqlalchemy.orm.attributes.flag_modified"):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.patch(
                    "/api/v1/checks/check-b3/claims/claim-b3/elements/e1/bounty",
                    json={"text": "What evidence exists?"},
                )

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert data["bountyText"] == "What evidence exists?"

    @pytest.mark.asyncio
    async def test_bounty_element_not_found(self):
        """Element not in claim_map → 404."""
        check = _make_check(check_id="check-b4", status="completed")
        claim = _make_claim(
            claim_id="claim-b4",
            check_id="check-b4",
            claim_map={
                "elements": [
                    {"element_id": "e1", "description": "Test", "state": "supported"}
                ]
            },
        )

        app = _create_test_app()
        session = _make_session(
            {"scalar": check},
            {"scalar": claim},
        )
        app.dependency_overrides[get_current_user_or_api_key] = _mock_auth_override()
        app.dependency_overrides[get_session] = lambda: session

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.patch(
                "/api/v1/checks/check-b4/claims/claim-b4/elements/nonexistent/bounty",
                json={"text": "test"},
            )

        assert resp.status_code == 404


# ===========================================================================
# GET /public/{id}
# ===========================================================================


class TestPublicCheck:
    """GET /api/v1/checks/public/{id} — public report (no auth)."""

    @pytest.mark.asyncio
    async def test_public_check_not_found(self):
        """Non-existent check → 404."""
        app = _create_test_app()
        session = _make_session({"scalar": None})
        # Public endpoint has no auth override needed, but session is still injected
        app.dependency_overrides[get_session] = lambda: session

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/v1/checks/public/nonexistent")

        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_public_check_not_completed(self):
        """Check not completed → 404."""
        check = _make_check(check_id="check-pub-1", status="processing")

        app = _create_test_app()
        session = _make_session({"scalar": check})
        app.dependency_overrides[get_session] = lambda: session

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/v1/checks/public/check-pub-1")

        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_public_check_success_minimal(self):
        """Completed check → returns OG card data (minimal, no detailed flag)."""
        check = _make_check(
            check_id="check-pub-2",
            input_url="https://example.com/article-about-science",
        )
        claim = _make_claim(check_id="check-pub-2", claim_id="cl-pub")
        evidence = _make_evidence(claim_id="cl-pub")

        app = _create_test_app()
        session = _make_session(
            {"scalar": check},  # check lookup
            {"rows": [claim]},  # claims query
            {"rows": [evidence]},  # evidence for claim
        )
        app.dependency_overrides[get_session] = lambda: session

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/v1/checks/public/check-pub-2")

        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == "check-pub-2"
        assert data["claimsCount"] == 1
        assert data["evidenceCount"] == 1
        # Minimal mode: no "claims" key with full data
        assert "inputType" not in data


# ===========================================================================
# GET /{id}/sources
# ===========================================================================


class TestGetSources:
    """GET /api/v1/checks/{id}/sources — reviewed sources list."""

    @pytest.mark.asyncio
    async def test_sources_check_not_found(self):
        """Non-existent check → 404."""
        app = _create_test_app()
        session = _make_session({"scalar": None})
        app.dependency_overrides[get_current_user_or_api_key] = _mock_auth_override()
        app.dependency_overrides[get_session] = lambda: session

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/v1/checks/missing/sources")

        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_sources_free_user_upgrade_prompt(self):
        """Free user (no subscription) → returns upgrade prompt."""
        check = _make_check(check_id="check-src-1")

        app = _create_test_app()
        session = _make_session(
            {"scalar": check},  # check lookup
            {"scalar": None},  # subscription lookup (none)
        )
        app.dependency_overrides[get_current_user_or_api_key] = _mock_auth_override()
        app.dependency_overrides[get_session] = lambda: session

        with patch("app.api.v1.checks.settings") as mock_settings:
            mock_settings.BETA_TESTER_EMAILS = []

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.get("/api/v1/checks/check-src-1/sources")

        assert resp.status_code == 200
        data = resp.json()
        assert data["requiresUpgrade"] is True


# ===========================================================================
# POST /{id}/videos/recover — on-demand durable video recovery
# ===========================================================================


def _make_video(vid="v1", claim_id="claim-1"):
    v = MagicMock()
    v.id = f"vr-{vid}"
    v.claim_id = claim_id
    v.video_id = vid
    v.title = "T"
    v.description = "D"
    v.channel_name = "BBC News"
    v.channel_id = "c1"
    v.publish_date = None
    v.video_url = f"https://youtu.be/{vid}"
    v.thumbnail_url = None
    v.duration = None
    v.tier_label = "reporting"
    v.type_label = "news_reporting"
    return v


class TestRecoverVideos:
    """POST /api/v1/checks/{id}/videos/recover — durable on-demand recovery."""

    @pytest.mark.asyncio
    async def test_recover_returns_existing_without_regenerating(self):
        from unittest.mock import patch, AsyncMock

        check = _make_check(check_id="chk-r1")
        app = _create_test_app()
        session = _make_session(
            {"scalar": check},  # ownership
            {"rows": [_make_video("v1"), _make_video("v2")]},  # existing videos
        )
        app.dependency_overrides[get_current_user_or_api_key] = _mock_auth_override()
        app.dependency_overrides[get_session] = lambda: session

        with patch(
            "app.services.video_recommendations.fetch_video_recommendations",
            new=AsyncMock(),
        ) as gen:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.post("/api/v1/checks/chk-r1/videos/recover")

        assert resp.status_code == 200
        assert len(resp.json()["videos"]) == 2
        gen.assert_not_awaited()  # idempotent — never regenerate over a set

    @pytest.mark.asyncio
    async def test_recover_generates_when_missing(self):
        from unittest.mock import patch, AsyncMock

        check = _make_check(check_id="chk-r4", status="completed")
        claim = _make_claim(claim_id="cl1", check_id="chk-r4", text="ocean claim")
        app = _create_test_app()
        session = _make_session(
            {"scalar": check},  # ownership
            {"rows": []},  # no existing videos
            {"rows": [claim]},  # is_selected claims
            {"rows": [_make_video("v9")]},  # after generation
        )
        app.dependency_overrides[get_current_user_or_api_key] = _mock_auth_override()
        app.dependency_overrides[get_session] = lambda: session

        with patch(
            "app.services.video_recommendations.fetch_video_recommendations",
            new=AsyncMock(),
        ) as gen:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.post("/api/v1/checks/chk-r4/videos/recover")

        assert resp.status_code == 200
        assert len(resp.json()["videos"]) == 1
        gen.assert_awaited_once()  # durable, awaited generation

    @pytest.mark.asyncio
    async def test_recover_wrong_user_403(self):
        check = _make_check(check_id="chk-r2", user_id="someone-else")
        app = _create_test_app()
        session = _make_session({"scalar": check})
        app.dependency_overrides[get_current_user_or_api_key] = _mock_auth_override()
        app.dependency_overrides[get_session] = lambda: session

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post("/api/v1/checks/chk-r2/videos/recover")

        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_recover_not_found_404(self):
        app = _create_test_app()
        session = _make_session({"scalar": None})
        app.dependency_overrides[get_current_user_or_api_key] = _mock_auth_override()
        app.dependency_overrides[get_session] = lambda: session

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post("/api/v1/checks/chk-r404/videos/recover")

        assert resp.status_code == 404
