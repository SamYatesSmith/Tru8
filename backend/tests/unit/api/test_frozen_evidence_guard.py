"""`frozen_evidence` is refused on a deployed backend unless the caller is an admin.

The field replaces retrieval with the caller's own evidence items (tier
included) and the pipeline then skips dedup, scoring and classification, so on
a deployed backend it let any signed-in user produce a normal, publicly
readable record from evidence they wrote
(audit/2026-10-08_complex_stage_functions_review.md F1). Both submission
routes (/checks/stream and /checks/run) go through _validate_and_create_check.
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.api.v1 import checks
from app.api.v1.checks import CreateCheckRequest, _validate_and_create_check

FROZEN = {"0": [{"url": "https://example.com", "text": "x", "tier": "primary"}]}
ADMIN = "founder@example.com"


@pytest.fixture
def env(monkeypatch):
    def _set(environment: str):
        monkeypatch.setattr(checks.settings, "ENVIRONMENT", environment)
        monkeypatch.setattr(checks.settings, "ADMIN_EMAILS", [ADMIN])

    return _set


async def _submit(body, email):
    """Run the shared submission path with the DB and ledger mocked out.

    Returns the usage-gate mock so a test can see whether billing work began.
    """
    user = SimpleNamespace(id="u1", email=email)
    gate = AsyncMock(side_effect=RuntimeError("past the guard"))
    with patch.object(
        checks, "get_or_create_user", new=AsyncMock(return_value=user)
    ), patch.object(checks, "enforce_usage_limit", new=gate):
        try:
            await _validate_and_create_check(body, {"id": "u1"}, MagicMock())
        except RuntimeError:
            pass  # reached the usage gate: the guard let it through
    return gate


def _body(frozen=FROZEN):
    return CreateCheckRequest(
        input_type="text", content="A claim.", frozen_evidence=frozen
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("environment", ["production", "staging", "Production"])
async def test_non_admin_is_refused_on_a_deployed_backend_before_billing(
    env, environment
):
    env(environment)
    with pytest.raises(HTTPException) as exc:
        await _submit(_body(), "someone@example.com")
    assert exc.value.status_code == 403
    assert "frozen_evidence" in exc.value.detail


@pytest.mark.asyncio
async def test_refusal_happens_before_the_usage_gate(env):
    env("production")
    user = SimpleNamespace(id="u1", email="someone@example.com")
    gate = AsyncMock()
    with patch.object(
        checks, "get_or_create_user", new=AsyncMock(return_value=user)
    ), patch.object(checks, "enforce_usage_limit", new=gate):
        with pytest.raises(HTTPException):
            await _validate_and_create_check(_body(), {"id": "u1"}, MagicMock())
    gate.assert_not_awaited()


@pytest.mark.asyncio
async def test_an_empty_dict_is_refused_too(env):
    """Any value is refused, not only a truthy one: the field has no other use."""
    env("production")
    with pytest.raises(HTTPException):
        await _submit(_body(frozen={}), "someone@example.com")


@pytest.mark.asyncio
async def test_admin_may_send_it_on_a_deployed_backend(env):
    env("production")
    gate = await _submit(_body(), ADMIN.upper())
    gate.assert_awaited_once()


@pytest.mark.asyncio
async def test_anyone_may_send_it_on_a_development_backend(env):
    """The golden-dataset harness runs against a local backend."""
    env("development")
    gate = await _submit(_body(), "someone@example.com")
    gate.assert_awaited_once()


@pytest.mark.asyncio
async def test_ordinary_submissions_are_unaffected(env):
    env("production")
    gate = await _submit(_body(frozen=None), "someone@example.com")
    gate.assert_awaited_once()


@pytest.mark.asyncio
async def test_a_user_without_an_email_is_refused(env):
    env("production")
    with pytest.raises(HTTPException):
        await _submit(_body(), None)


def test_both_submission_routes_use_the_guarded_path():
    """The guard lives in the shared helper; both routes must call it."""
    import inspect

    for handler in (checks.create_check_streaming, checks.create_check_sync):
        assert "_validate_and_create_check(" in inspect.getsource(handler), handler
