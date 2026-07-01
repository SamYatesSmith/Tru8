"""Path-separation wall: /checks submission is Console-only (sign-in / JWT).

The two-product boundary — Console = /checks = sign-in; API = /agent = metered —
is enforced by `_require_console_submission`: it rejects API-key auth on the
check-submission endpoints so a programmatic caller cannot ride the human
subscription's fair-use quota. Read-only /checks endpoints and the metered
/agent endpoints are unaffected.

These tests exercise that guard directly (it is the entire behavioural change).
"""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi import Depends, FastAPI, HTTPException, Request
from httpx import ASGITransport, AsyncClient

from app.api.v1.checks import _require_console_submission
from app.core.auth import get_current_user_or_api_key
from app.core.database import get_session


def _make_request(headers: dict, auth_method: str | None = None) -> Request:
    """Build a minimal Starlette Request carrying the given headers.

    `auth_method` simulates the value the dual-auth dependency records on
    request.state after resolving the caller (jwt / api_key / stream_token).
    """
    raw = [(k.lower().encode(), v.encode()) for k, v in headers.items()]
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/api/v1/checks/run",
        "headers": raw,
    }
    request = Request(scope)
    if auth_method is not None:
        request.state.auth_method = auth_method
    return request


class TestRequireConsoleSubmission:
    def test_api_key_submission_is_rejected_403(self):
        """An X-API-Key header on a submit endpoint → 403 pointing to /agent."""
        request = _make_request({"X-API-Key": "tk_live_example"})
        with pytest.raises(HTTPException) as exc:
            _require_console_submission(request)
        assert exc.value.status_code == 403
        assert "/agent" in exc.value.detail

    def test_jwt_submission_is_allowed(self):
        """A Clerk JWT (Authorization: Bearer) is NOT walled — returns dashboard."""
        request = _make_request({"Authorization": "Bearer eyJhbGciOi.fake.jwt"})
        assert _require_console_submission(request) == "dashboard"

    def test_no_auth_header_is_allowed(self):
        """No API key (e.g. SSE stream-token path) is not walled."""
        request = _make_request({})
        assert _require_console_submission(request) == "dashboard"

    def test_stream_token_header_is_allowed(self):
        """A non-API-key auth header (e.g. a stream token) passes through."""
        request = _make_request({"X-Stream-Token": "st_example"})
        assert _require_console_submission(request) == "dashboard"

    def test_api_key_rejected_even_with_jwt_present(self):
        """If an API key is present, it's rejected regardless of other headers."""
        request = _make_request(
            {"X-API-Key": "tk_live_example", "Authorization": "Bearer jwt"}
        )
        with pytest.raises(HTTPException) as exc:
            _require_console_submission(request)
        assert exc.value.status_code == 403

    # --- Stricter version: reject on RESOLVED auth method, not just header ---

    def test_resolved_api_key_method_rejected_without_header(self):
        """A caller resolved as api_key is rejected even with no X-API-Key header.

        Proves the guard keys off the resolved auth method, not header presence.
        """
        request = _make_request({}, auth_method="api_key")
        with pytest.raises(HTTPException) as exc:
            _require_console_submission(request)
        assert exc.value.status_code == 403
        assert "/agent" in exc.value.detail

    def test_resolved_jwt_method_allowed(self):
        """auth_method='jwt' → allowed (returns dashboard)."""
        request = _make_request({}, auth_method="jwt")
        assert _require_console_submission(request) == "dashboard"

    def test_resolved_stream_token_method_allowed(self):
        """auth_method='stream_token' → allowed (returns dashboard)."""
        request = _make_request({}, auth_method="stream_token")
        assert _require_console_submission(request) == "dashboard"


class TestLiveEndpointWiring:
    """End-to-end (ASGI) smoke: drive the REAL dual-auth dependency over HTTP and
    confirm auth_method flows dependency → request.state → guard.

    A minimal route mirrors the submit handlers: it depends on
    `get_current_user_or_api_key` (which records request.state.auth_method) and
    then calls the real `_require_console_submission(request)` guard.
    """

    @staticmethod
    def _app():
        app = FastAPI()

        @app.post("/probe")
        async def probe(
            request: Request,
            user: dict = Depends(get_current_user_or_api_key),
        ):
            via = _require_console_submission(request)
            return {"via": via, "user_id": user["id"]}

        app.dependency_overrides[get_session] = lambda: AsyncMock()
        return app

    @pytest.mark.asyncio
    async def test_api_key_request_gets_403_end_to_end(self):
        """A real X-API-Key request resolves as api_key and the guard 403s it."""
        app = self._app()
        with patch(
            "app.core.auth._verify_api_key",
            new=AsyncMock(return_value={"id": "u1", "email": "a@b.c", "name": "A"}),
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.post("/probe", headers={"X-API-Key": "tk_live_x"})
        assert resp.status_code == 403
        assert "/agent" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_jwt_request_passes_end_to_end(self):
        """A real Bearer-JWT request resolves as jwt and the guard allows it."""
        app = self._app()
        with patch(
            "app.core.auth._verify_jwt_token",
            new=AsyncMock(return_value={"sub": "u1"}),
        ), patch(
            "app.core.auth._fetch_user_data_from_clerk",
            new=AsyncMock(return_value={"id": "u1", "email": "a@b.c", "name": "A"}),
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.post(
                    "/probe", headers={"Authorization": "Bearer fake.jwt.token"}
                )
        assert resp.status_code == 200
        assert resp.json()["via"] == "dashboard"


class TestReSearchWall:
    """The Seeker re-search endpoints also bill the subscription, so they must
    reject API-key callers. These call the real handlers directly: the guard is
    the first statement, so it 403s before any DB/credit work (the session mock
    is never touched).
    """

    @pytest.mark.asyncio
    async def test_gap_research_rejects_api_key_before_billing(self):
        from app.api.v1.checks import start_gap_research

        request = _make_request({}, auth_method="api_key")
        session = AsyncMock()
        with pytest.raises(HTTPException) as exc:
            await start_gap_research(
                check_id="c1",
                claim_id="cl1",
                request=request,
                current_user={"id": "u1"},
                session=session,
            )
        assert exc.value.status_code == 403
        assert "/agent" in exc.value.detail
        session.execute.assert_not_called()  # guard short-circuits before any DB

    @pytest.mark.asyncio
    async def test_thin_research_rejects_api_key_before_billing(self):
        from app.api.v1.checks import start_thin_research

        request = _make_request({}, auth_method="api_key")
        session = AsyncMock()
        with pytest.raises(HTTPException) as exc:
            await start_thin_research(
                check_id="c1",
                claim_id="cl1",
                request=request,
                current_user={"id": "u1"},
                session=session,
            )
        assert exc.value.status_code == 403
        assert "/agent" in exc.value.detail
        session.execute.assert_not_called()  # guard short-circuits before any DB

    @pytest.mark.asyncio
    async def test_element_research_rejects_api_key_before_billing(self):
        from app.api.v1.checks import start_element_research

        request = _make_request({}, auth_method="api_key")
        session = AsyncMock()
        with pytest.raises(HTTPException) as exc:
            await start_element_research(
                check_id="c1",
                claim_id="cl1",
                element_id="el1",
                request=request,
                current_user={"id": "u1"},
                session=session,
            )
        assert exc.value.status_code == 403
        session.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_gap_research_allows_console_jwt_past_the_guard(self):
        """A JWT/Console caller passes the guard (then proceeds to real logic).

        We only assert the guard does NOT 403 — the handler then does its own
        validation against the mock session, which is allowed to fail/return
        normally; what matters is no 403 from the wall.
        """
        from app.api.v1.checks import start_gap_research, _require_console_submission

        request = _make_request({}, auth_method="jwt")
        # The guard itself must pass for a jwt caller.
        assert _require_console_submission(request) == "dashboard"
