"""Tests for the consensus background-loop session acquisition.

Background: PYTHON-FASTAPI-20 in Sentry —
  TypeError: 'async_generator' object does not support the
  asynchronous context manager protocol
in app.services.consensus._consensus_loop. The loop did
`async with get_session() as session:` but get_session() is an
async *generator* (yields) intended for FastAPI dependency
injection — async generators do not support `async with`. The
fix uses async_session() directly, which IS an async context
manager.

These tests pin the corrected import + usage so the regression
cannot reintroduce silently.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services import consensus


def test_consensus_imports_async_session_not_get_session():
    """Module import-level guard: consensus must use async_session
    (the context manager) rather than get_session (the generator)."""
    assert hasattr(consensus, "async_session"), (
        "app.services.consensus must import async_session from "
        "app.core.database — get_session() is an async generator "
        "and cannot be used with `async with` (caused PYTHON-FASTAPI-20)."
    )


@pytest.mark.asyncio
async def test_consensus_loop_acquires_session_via_context_manager():
    """The loop body must enter a real async context manager — no
    TypeError on `async with`. The loop sleeps until 02:00 UTC, then
    runs the session block, then sleeps again. We let the first sleep
    return immediately so the body runs, then raise on the second
    sleep to break the loop after exactly one iteration."""

    sentinel = RuntimeError("break-loop")
    sleep_calls = {"n": 0}

    async def _fake_sleep(_seconds):
        sleep_calls["n"] += 1
        if sleep_calls["n"] >= 2:
            raise sentinel
        # First sleep returns immediately so the body executes

    # Stub the sessionmaker so we don't touch a real DB
    fake_session = MagicMock()
    fake_session.__aenter__ = AsyncMock(return_value=fake_session)
    fake_session.__aexit__ = AsyncMock(return_value=False)

    fake_session_factory = MagicMock(return_value=fake_session)

    fake_compute = AsyncMock(return_value=7)

    with patch("app.services.consensus.async_session", fake_session_factory), patch(
        "app.services.consensus.compute_consensus", fake_compute
    ), patch("app.services.consensus.asyncio.sleep", side_effect=_fake_sleep):

        with pytest.raises(RuntimeError, match="break-loop"):
            await consensus._consensus_loop()

    # Session factory was called exactly once during the iteration
    fake_session_factory.assert_called_once()

    # Context manager protocol was exercised
    fake_session.__aenter__.assert_awaited_once()
    fake_session.__aexit__.assert_awaited_once()

    # compute_consensus ran with the session
    fake_compute.assert_awaited_once_with(fake_session)


@pytest.mark.asyncio
async def test_consensus_loop_does_not_raise_async_generator_typeerror():
    """Direct regression for PYTHON-FASTAPI-20.

    If anyone reintroduces `async with get_session() as session:`,
    `__aenter__` would raise TypeError because async generators do
    not implement the asynchronous context manager protocol. The
    loop catches Exception via its own try/except and logs, so we
    assert the TypeError didn't fire by checking compute_consensus
    was actually awaited with a session — which only happens if the
    `async with` body succeeded.
    """

    sleep_calls = {"n": 0}

    async def _fake_sleep(_seconds):
        sleep_calls["n"] += 1
        if sleep_calls["n"] >= 2:
            raise RuntimeError("break-loop")

    fake_session = MagicMock()
    fake_session.__aenter__ = AsyncMock(return_value=fake_session)
    fake_session.__aexit__ = AsyncMock(return_value=False)
    fake_session_factory = MagicMock(return_value=fake_session)

    fake_compute = AsyncMock(return_value=0)

    with patch("app.services.consensus.async_session", fake_session_factory), patch(
        "app.services.consensus.compute_consensus", fake_compute
    ), patch("app.services.consensus.asyncio.sleep", side_effect=_fake_sleep):

        with pytest.raises(RuntimeError, match="break-loop"):
            await consensus._consensus_loop()

    # If the bug was reintroduced, async_session() would still be
    # called (because we patched it), but the TypeError on `async with`
    # would land in the broad `except Exception` and compute_consensus
    # would never run. The fact that compute_consensus was awaited
    # proves the context-manager entry succeeded.
    fake_compute.assert_awaited_once_with(fake_session)
