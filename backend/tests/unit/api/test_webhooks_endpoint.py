"""Tests for webhook management endpoints (POST / GET / DELETE).

Covers:
- POST /  — create webhook (HTTPS validation, event validation, max 5 cap, secret returned)
- GET /   — list webhooks (secrets never exposed)
- DELETE /{webhook_id} — delete webhook (ownership check, 404 for missing)
"""

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.v1.webhooks import router
from app.core.auth import get_current_user_or_api_key
from app.core.database import get_session


# ---------------------------------------------------------------------------
# Test app + dependency overrides
# ---------------------------------------------------------------------------

MOCK_USER = {"id": "user-001", "email": "test@tru8.app"}


def _create_test_app():
    """Build a minimal FastAPI app with the webhooks router mounted."""
    app = FastAPI()
    app.include_router(router, prefix="/api/v1/webhooks")
    return app


def _mock_auth_override():
    """Dependency override that always returns MOCK_USER."""

    async def _override():
        return MOCK_USER

    return _override


# ---------------------------------------------------------------------------
# Mock model factories
# ---------------------------------------------------------------------------


def _make_webhook(
    webhook_id=None,
    user_id="user-001",
    url="https://example.com/hook",
    events=None,
    is_active=True,
    description=None,
    failure_count=0,
    last_triggered_at=None,
    created_at=None,
    secret="whsec_abc123",
):
    """Build a MagicMock resembling a Webhook DB row."""
    w = MagicMock()
    w.id = webhook_id or str(uuid.uuid4())
    w.user_id = user_id
    w.url = url
    w.events = events or ["check.completed"]
    w.is_active = is_active
    w.description = description
    w.failure_count = failure_count
    w.last_triggered_at = last_triggered_at
    w.created_at = created_at or datetime(2026, 3, 1, 12, 0, 0)
    w.secret = secret
    return w


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


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def app():
    """FastAPI app with auth override."""
    app = _create_test_app()
    app.dependency_overrides[get_current_user_or_api_key] = _mock_auth_override()
    yield app
    app.dependency_overrides.clear()


@pytest.fixture
def mock_session():
    """Async mock for the database session."""
    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.delete = AsyncMock()
    session.execute = AsyncMock()
    return session


# ---------------------------------------------------------------------------
# TestCreateWebhook
# ---------------------------------------------------------------------------


class TestCreateWebhook:
    """POST /api/v1/webhooks"""

    @pytest.mark.anyio
    async def test_creates_webhook_with_valid_url(self, app, mock_session):
        """HTTPS URL is accepted and webhook is persisted."""
        # No existing active webhooks
        mock_session.execute.return_value = _MockExecuteResult(rows=[])

        # After commit + refresh, the webhook gets an id and created_at
        async def _refresh(obj):
            obj.id = str(uuid.uuid4())
            obj.created_at = datetime(2026, 3, 1, 12, 0, 0)

        mock_session.refresh.side_effect = _refresh

        app.dependency_overrides[get_session] = lambda: mock_session

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/v1/webhooks",
                json={
                    "url": "https://example.com/webhook",
                    "events": ["check.completed"],
                    "description": "My hook",
                },
            )

        assert resp.status_code == 201
        data = resp.json()
        assert data["url"] == "https://example.com/webhook"
        assert data["events"] == ["check.completed"]
        assert data["description"] == "My hook"
        assert "id" in data
        assert "created_at" in data
        # session.add should have been called with the new webhook
        mock_session.add.assert_called_once()
        mock_session.commit.assert_awaited_once()

    @pytest.mark.anyio
    async def test_rejects_http_url(self, app, mock_session):
        """Non-HTTPS URL is rejected with 400."""
        app.dependency_overrides[get_session] = lambda: mock_session

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/v1/webhooks",
                json={
                    "url": "http://example.com/webhook",
                    "events": ["check.completed"],
                },
            )

        assert resp.status_code == 400
        assert "HTTPS" in resp.json()["detail"]
        # No DB writes should have occurred
        mock_session.add.assert_not_called()

    @pytest.mark.anyio
    async def test_rejects_invalid_event_type(self, app, mock_session):
        """Unknown event type is rejected with 400."""
        app.dependency_overrides[get_session] = lambda: mock_session

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/v1/webhooks",
                json={
                    "url": "https://example.com/webhook",
                    "events": ["check.completed", "check.exploded"],
                },
            )

        assert resp.status_code == 400
        detail = resp.json()["detail"]
        assert "check.exploded" in detail
        assert "Invalid events" in detail
        mock_session.add.assert_not_called()

    @pytest.mark.anyio
    async def test_max_5_webhooks_enforced(self, app, mock_session):
        """6th webhook creation is rejected when 5 are already active."""
        existing = [_make_webhook() for _ in range(5)]
        mock_session.execute.return_value = _MockExecuteResult(rows=existing)

        app.dependency_overrides[get_session] = lambda: mock_session

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/v1/webhooks",
                json={
                    "url": "https://example.com/sixth",
                    "events": ["check.completed"],
                },
            )

        assert resp.status_code == 400
        assert "Maximum 5" in resp.json()["detail"]
        mock_session.add.assert_not_called()

    @pytest.mark.anyio
    async def test_returns_secret_once(self, app, mock_session):
        """Response includes the HMAC signing secret (shown only at creation)."""
        mock_session.execute.return_value = _MockExecuteResult(rows=[])

        async def _refresh(obj):
            obj.id = str(uuid.uuid4())
            obj.created_at = datetime(2026, 3, 1, 12, 0, 0)

        mock_session.refresh.side_effect = _refresh

        app.dependency_overrides[get_session] = lambda: mock_session

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/v1/webhooks",
                json={
                    "url": "https://example.com/webhook",
                    "events": ["check.completed"],
                },
            )

        assert resp.status_code == 201
        data = resp.json()
        # Secret must be present and be a 64-char hex string (token_hex(32))
        assert "secret" in data
        assert len(data["secret"]) == 64
        assert all(c in "0123456789abcdef" for c in data["secret"])


# ---------------------------------------------------------------------------
# TestListWebhooks
# ---------------------------------------------------------------------------


class TestListWebhooks:
    """GET /api/v1/webhooks"""

    @pytest.mark.anyio
    async def test_lists_webhooks_without_secrets(self, app, mock_session):
        """Listed webhooks never expose the signing secret."""
        w1 = _make_webhook(
            webhook_id="wh-001",
            url="https://a.com/hook",
            events=["check.completed"],
            description="First",
            failure_count=2,
        )
        w2 = _make_webhook(
            webhook_id="wh-002",
            url="https://b.com/hook",
            events=["check.completed", "check.failed"],
            is_active=False,
            failure_count=10,
        )
        mock_session.execute.return_value = _MockExecuteResult(rows=[w1, w2])

        app.dependency_overrides[get_session] = lambda: mock_session

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/v1/webhooks")

        assert resp.status_code == 200
        data = resp.json()
        assert len(data["webhooks"]) == 2

        # First webhook
        hook1 = data["webhooks"][0]
        assert hook1["id"] == "wh-001"
        assert hook1["url"] == "https://a.com/hook"
        assert hook1["events"] == ["check.completed"]
        assert hook1["is_active"] is True
        assert hook1["description"] == "First"
        assert hook1["failure_count"] == 2
        assert "secret" not in hook1

        # Second webhook
        hook2 = data["webhooks"][1]
        assert hook2["id"] == "wh-002"
        assert hook2["is_active"] is False
        assert "secret" not in hook2

    @pytest.mark.anyio
    async def test_returns_empty_list(self, app, mock_session):
        """No webhooks returns an empty list."""
        mock_session.execute.return_value = _MockExecuteResult(rows=[])

        app.dependency_overrides[get_session] = lambda: mock_session

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/v1/webhooks")

        assert resp.status_code == 200
        data = resp.json()
        assert data["webhooks"] == []


# ---------------------------------------------------------------------------
# TestDeleteWebhook
# ---------------------------------------------------------------------------


class TestDeleteWebhook:
    """DELETE /api/v1/webhooks/{webhook_id}"""

    @pytest.mark.anyio
    async def test_deletes_webhook(self, app, mock_session):
        """Existing webhook is deleted and returns 204."""
        existing = _make_webhook(webhook_id="wh-to-delete")
        mock_session.execute.return_value = _MockExecuteResult(scalar=existing)

        app.dependency_overrides[get_session] = lambda: mock_session

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.delete("/api/v1/webhooks/wh-to-delete")

        assert resp.status_code == 204
        mock_session.delete.assert_awaited_once_with(existing)
        mock_session.commit.assert_awaited_once()

    @pytest.mark.anyio
    async def test_404_for_nonexistent_webhook(self, app, mock_session):
        """Deleting a non-existent webhook returns 404."""
        mock_session.execute.return_value = _MockExecuteResult(scalar=None)

        app.dependency_overrides[get_session] = lambda: mock_session

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.delete(f"/api/v1/webhooks/{str(uuid.uuid4())}")

        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()
        mock_session.delete.assert_not_awaited()
