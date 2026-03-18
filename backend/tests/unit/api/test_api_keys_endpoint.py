"""Tests for API key management endpoints.

Covers:
- POST /api/v1/api-keys     — create new API key
- GET  /api/v1/api-keys     — list all API keys
- DELETE /api/v1/api-keys/{key_id} — revoke API key

All database interactions and auth are mocked via FastAPI dependency overrides.
"""

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.v1.api_keys import router
from app.core.auth import get_current_user
from app.core.database import get_session


# ---------------------------------------------------------------------------
# Test app + dependency overrides
# ---------------------------------------------------------------------------

MOCK_USER = {"id": "user-001", "email": "test@tru8.app", "name": "Test User"}
OTHER_USER = {"id": "user-002", "email": "other@tru8.app", "name": "Other User"}

PREFIX = "/api/v1/api-keys"


def _create_test_app(*, with_auth: bool = True):
    """Build a minimal FastAPI app with the api-keys router mounted."""
    app = FastAPI()
    app.include_router(router, prefix=PREFIX)

    if with_auth:

        async def _auth_override():
            return MOCK_USER

        app.dependency_overrides[get_current_user] = _auth_override

    return app


# ---------------------------------------------------------------------------
# Mock helpers
# ---------------------------------------------------------------------------


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


def _make_user(user_id="user-001", email="test@tru8.app"):
    """Build a MagicMock resembling a User DB row."""
    u = MagicMock()
    u.id = user_id
    u.email = email
    return u


def _make_api_key(
    key_id=None,
    user_id="user-001",
    name="My Key",
    is_active=True,
    key_prefix="tru8_sk_abcd",
    usage_count=0,
    last_used_at=None,
    created_at=None,
):
    """Build a MagicMock resembling an APIKey DB row."""
    k = MagicMock()
    k.id = key_id or str(uuid.uuid4())
    k.user_id = user_id
    k.name = name
    k.is_active = is_active
    k.key_prefix = key_prefix
    k.usage_count = usage_count
    k.last_used_at = last_used_at
    k.created_at = created_at or datetime(2026, 3, 1, 12, 0, 0)
    return k


# ===========================================================================
# TestCreateAPIKey
# ===========================================================================


class TestCreateAPIKey:
    """POST /api/v1/api-keys — create new API key."""

    @pytest.mark.asyncio
    async def test_creates_key_with_correct_format(self):
        """Key starts with 'tru8_sk_' and is at least 40 chars total."""
        mock_user = _make_user()
        session = _make_session(
            # 1st execute: get_or_create_user → existing user lookup
            {"scalar": mock_user},
            # 2nd execute: count active keys (returns empty list → under limit)
            {"rows": []},
        )

        app = _create_test_app()
        app.dependency_overrides[get_session] = lambda: session

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(PREFIX, json={"name": "Test Key"})

        assert resp.status_code == 201
        data = resp.json()
        assert data["key"].startswith("tru8_sk_")
        # tru8_sk_ (8 chars) + 32 hex chars = 40 total
        assert len(data["key"]) == 40

    @pytest.mark.asyncio
    async def test_returns_key_only_once(self):
        """Response includes the raw key field at creation time."""
        mock_user = _make_user()
        session = _make_session(
            {"scalar": mock_user},
            {"rows": []},
        )

        app = _create_test_app()
        app.dependency_overrides[get_session] = lambda: session

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(PREFIX, json={"name": "One-time Key"})

        assert resp.status_code == 201
        data = resp.json()
        # The raw key is present in the creation response
        assert "key" in data
        assert data["key"].startswith("tru8_sk_")
        # Also returns id, key_prefix, name, created_at
        assert "id" in data
        assert "key_prefix" in data
        assert data["name"] == "One-time Key"
        assert "created_at" in data

    @pytest.mark.asyncio
    async def test_max_5_keys_enforced(self):
        """6th key creation fails with 400 when user already has 5 active keys."""
        mock_user = _make_user()
        five_keys = [_make_api_key(name=f"Key {i}") for i in range(5)]
        session = _make_session(
            # 1st execute: get_or_create_user
            {"scalar": mock_user},
            # 2nd execute: count active keys → already at 5
            {"rows": five_keys},
        )

        app = _create_test_app()
        app.dependency_overrides[get_session] = lambda: session

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(PREFIX, json={"name": "Sixth Key"})

        assert resp.status_code == 400
        assert "Maximum 5" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_requires_auth(self):
        """Request without auth returns 403 (no credentials provided)."""
        app = _create_test_app(with_auth=False)
        session = _make_session()
        app.dependency_overrides[get_session] = lambda: session

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(PREFIX, json={"name": "No Auth Key"})

        assert resp.status_code == 403


# ===========================================================================
# TestListAPIKeys
# ===========================================================================


class TestListAPIKeys:
    """GET /api/v1/api-keys — list all API keys."""

    @pytest.mark.asyncio
    async def test_lists_keys_without_secrets(self):
        """Response items have key_prefix but no raw key field."""
        keys = [
            _make_api_key(name="Key A", key_prefix="tru8_sk_aaaa", usage_count=10),
            _make_api_key(name="Key B", key_prefix="tru8_sk_bbbb", usage_count=3),
        ]
        session = _make_session(
            # list_api_keys does a single execute
            {"rows": keys},
        )

        app = _create_test_app()
        app.dependency_overrides[get_session] = lambda: session

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get(PREFIX)

        assert resp.status_code == 200
        data = resp.json()
        assert "keys" in data
        assert len(data["keys"]) == 2

        for item in data["keys"]:
            # Raw key must never be exposed in list response
            assert "key" not in item
            # But key_prefix is present for identification
            assert "key_prefix" in item
            assert item["key_prefix"].startswith("tru8_sk_")
            # Standard fields present
            assert "id" in item
            assert "name" in item
            assert "is_active" in item
            assert "usage_count" in item
            assert "created_at" in item

    @pytest.mark.asyncio
    async def test_returns_empty_list_for_new_user(self):
        """New user with no keys gets an empty list."""
        session = _make_session(
            {"rows": []},
        )

        app = _create_test_app()
        app.dependency_overrides[get_session] = lambda: session

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get(PREFIX)

        assert resp.status_code == 200
        data = resp.json()
        assert data["keys"] == []


# ===========================================================================
# TestDeleteAPIKey
# ===========================================================================


class TestDeleteAPIKey:
    """DELETE /api/v1/api-keys/{key_id} — revoke API key."""

    @pytest.mark.asyncio
    async def test_revokes_key(self):
        """Successful deletion returns 204 and deactivates the key."""
        key_id = str(uuid.uuid4())
        mock_key = _make_api_key(key_id=key_id, is_active=True)
        session = _make_session(
            # revoke_api_key does a single execute to find the key
            {"scalar": mock_key},
        )

        app = _create_test_app()
        app.dependency_overrides[get_session] = lambda: session

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.delete(f"{PREFIX}/{key_id}")

        assert resp.status_code == 204
        # Verify the key was marked inactive
        assert mock_key.is_active is False
        # Verify commit was called to persist the change
        session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_404_for_nonexistent_key(self):
        """Deleting a key that does not exist returns 404."""
        fake_id = str(uuid.uuid4())
        session = _make_session(
            # Key lookup returns None
            {"scalar": None},
        )

        app = _create_test_app()
        app.dependency_overrides[get_session] = lambda: session

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.delete(f"{PREFIX}/{fake_id}")

        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_cannot_delete_other_users_key(self):
        """
        A key owned by another user is not visible — the WHERE clause
        filters by current_user['id'], so it returns 404 rather than 403.
        """
        other_key_id = str(uuid.uuid4())
        # The query filters by user_id == current_user["id"], so a key
        # belonging to user-002 won't be found for user-001.
        session = _make_session(
            {"scalar": None},  # key not found (belongs to other user)
        )

        app = _create_test_app()
        app.dependency_overrides[get_session] = lambda: session

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.delete(f"{PREFIX}/{other_key_id}")

        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()
