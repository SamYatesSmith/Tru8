"""Tests for transaction-state recovery in app.services.explore.

Background: PYTHON-FASTAPI-1Z / 1Y in Sentry — InFailedSQLTransactionError
on /api/v1/checks/{check_id}/claims/{claim_id}/explore. The
_find_by_entity_overlap function caught its DB exception and returned
[] for graceful degradation, but did NOT roll back the session. The
asyncpg transaction stayed in aborted state, so the very next
session.execute() in _find_by_subject_context raised
"current transaction is aborted, commands ignored until end of
transaction block" — Python rescued, Postgres didn't.

These tests pin the rollback behaviour so the regression cannot
silently reintroduce: each defensive except block in explore.py
must call session.rollback() before returning.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.explore import (
    _enrich_with_consensus,
    _find_by_entity_overlap,
    _find_by_subject_context,
    find_related_claims,
)


def _build_failing_session(fail_on_call: int = 1):
    """Build a mock session whose Nth execute() raises a DB error.

    fail_on_call=1 means the first execute raises; subsequent calls
    succeed (returning empty results). Tracks rollback() calls.
    """
    session = MagicMock()
    call_count = {"n": 0}

    async def _execute(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == fail_on_call:
            raise RuntimeError(
                "InFailedSQLTransactionError: current transaction is aborted, "
                "commands ignored until end of transaction block"
            )
        # Subsequent calls return an empty result
        result = MagicMock()
        result.fetchall.return_value = []
        result.fetchone.return_value = None
        return result

    session.execute = AsyncMock(side_effect=_execute)
    session.rollback = AsyncMock()
    session._call_count = call_count
    return session


class TestEntityOverlapTransactionRecovery:
    """_find_by_entity_overlap rolls back its aborted transaction
    before returning the empty fallback."""

    @pytest.mark.asyncio
    async def test_query_failure_rolls_back_session(self):
        session = _build_failing_session(fail_on_call=1)

        result = await _find_by_entity_overlap(
            session,
            normalised_entities=["alpha", "beta", "gamma"],
            user_id="user-1",
            target_hash="hash-target",
            limit=5,
        )

        assert result == []
        # Critical: rollback must be awaited so subsequent queries on
        # the same session don't hit InFailedSQLTransactionError
        session.rollback.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_rollback_failure_swallowed(self):
        """If rollback itself fails, we log and proceed — never raise."""
        session = MagicMock()
        session.execute = AsyncMock(side_effect=RuntimeError("query died"))
        session.rollback = AsyncMock(side_effect=RuntimeError("rollback also died"))

        # Must not raise — graceful degradation is the policy
        result = await _find_by_entity_overlap(
            session,
            normalised_entities=["alpha", "beta"],
            user_id="user-1",
            target_hash=None,
            limit=5,
        )

        assert result == []
        session.rollback.assert_awaited_once()


class TestSubjectContextTransactionRecovery:
    """_find_by_subject_context rolls back on query failure."""

    @pytest.mark.asyncio
    async def test_query_failure_rolls_back_session(self):
        session = _build_failing_session(fail_on_call=1)

        result = await _find_by_subject_context(
            session,
            context_tokens=["climate", "december", "2010"],
            user_id="user-1",
            target_hash="hash-target",
            existing_hashes=set(),
            limit=5,
        )

        assert result == []
        session.rollback.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_no_rollback_on_success(self):
        """Happy path must not call rollback."""
        session = MagicMock()
        result_mock = MagicMock()
        result_mock.fetchall.return_value = []
        session.execute = AsyncMock(return_value=result_mock)
        session.rollback = AsyncMock()

        await _find_by_subject_context(
            session,
            context_tokens=["climate", "december"],
            user_id="user-1",
            target_hash=None,
            existing_hashes=set(),
            limit=5,
        )

        session.rollback.assert_not_called()


class TestEnrichConsensusTransactionRecovery:
    """_enrich_with_consensus rolls back on query failure and
    returns claims unenriched rather than 500ing the request."""

    @pytest.mark.asyncio
    async def test_enrichment_failure_rolls_back_and_returns(self):
        session = MagicMock()
        session.execute = AsyncMock(side_effect=RuntimeError("consensus died"))
        session.rollback = AsyncMock()

        claims = [
            {"claimTextHash": "hash-1", "consensus": None},
            {"claimTextHash": "hash-2", "consensus": None},
        ]

        # Must not raise
        await _enrich_with_consensus(session, claims)

        session.rollback.assert_awaited_once()
        # Claims pass through unmodified — consensus stays None
        assert all(c["consensus"] is None for c in claims)

    @pytest.mark.asyncio
    async def test_no_claims_short_circuits(self):
        """Empty claim list — no execute, no rollback."""
        session = MagicMock()
        session.execute = AsyncMock()
        session.rollback = AsyncMock()

        await _enrich_with_consensus(session, [])

        session.execute.assert_not_called()
        session.rollback.assert_not_called()


class TestFullExploreFlowRecovery:
    """End-to-end: target-claim load succeeds, entity-overlap query
    fails, subject-context fallback then runs cleanly. This is the
    exact PYTHON-FASTAPI-1Z scenario."""

    @pytest.mark.asyncio
    async def test_entity_overlap_failure_does_not_break_subject_context(self):
        """The bug pattern: entity-overlap fails, subject-context must
        still execute without InFailedSQLTransactionError."""

        # Three execute() calls expected:
        #   1. target claim lookup (succeeds — returns row with entities + context)
        #   2. entity-overlap query (FAILS)
        #   3. subject-context fallback (succeeds — returns empty)
        #   4. (possibly) consensus enrichment — but with empty results, skipped
        session = MagicMock()

        target_row = MagicMock()
        target_row.__getitem__ = lambda self, idx: [
            [
                {"text": "Manchester", "type": "LOCATION"},
                {"text": "December 2010", "type": "DATE"},
            ],
            "Manchester saw -17C in December 2010",
            "hash-target",
        ][idx]

        target_result = MagicMock()
        target_result.fetchone.return_value = target_row

        empty_result = MagicMock()
        empty_result.fetchall.return_value = []

        call_log: list[str] = []

        async def _execute(query, *args, **kwargs):
            sql = str(query).lower()
            if "from claim cl" in sql and "where cl.id" in sql:
                call_log.append("target")
                return target_result
            if "candidate_claims" in sql:
                call_log.append("entity_overlap")
                raise RuntimeError(
                    "InFailedSQLTransactionError: current transaction is aborted"
                )
            if "subject_context" in sql:
                call_log.append("subject_context")
                return empty_result
            call_log.append("other")
            return empty_result

        session.execute = AsyncMock(side_effect=_execute)
        session.rollback = AsyncMock()

        with patch("app.services.explore.MIN_CONTEXT_TOKENS", 2):
            results = await find_related_claims(
                claim_id="claim-1",
                user_id="user-1",
                session=session,
                limit=5,
            )

        # No exception propagates — endpoint stays healthy
        assert isinstance(results, list)

        # The exact scenario: target loaded, entity-overlap failed,
        # subject-context still ran. Without the rollback fix the
        # subject-context call would have raised
        # InFailedSQLTransactionError.
        assert "target" in call_log
        assert "entity_overlap" in call_log
        assert "subject_context" in call_log

        # Rollback fired after entity-overlap failure
        session.rollback.assert_awaited()
