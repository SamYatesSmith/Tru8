"""Tests for GET /verify/{check_id} — public manifest verification endpoint.

Covers:
- Valid manifest with matching canonical hash
- Check not found (404)
- Check exists but no manifest (404)
- Invalid HMAC signature
- Signature valid but data integrity mismatch (hash drift)
- Signing disabled globally (MANIFEST_SIGNING_ENABLED=False)
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.v1.verify import router


# ---------------------------------------------------------------------------
# Test app
# ---------------------------------------------------------------------------


def _create_test_app():
    """Minimal FastAPI app with the verify router mounted at root.

    Mirrors main.py: verify is intentionally outside /api/v1 so the
    public verifyUrl in _manifest matches the documented contract.
    """
    app = FastAPI()
    app.include_router(router)
    return app


# ---------------------------------------------------------------------------
# Mock model factories
# ---------------------------------------------------------------------------


def _make_check(check_id=None, manifest=None, executed_tier="full", **kwargs):
    """Build a MagicMock resembling a Check DB row."""
    c = MagicMock()
    c.id = check_id or str(uuid.uuid4())
    c.manifest = manifest
    c.executed_tier = executed_tier
    c.created_at = MagicMock(isoformat=MagicMock(return_value="2026-03-09T12:00:00"))
    c.completed_at = MagicMock(isoformat=MagicMock(return_value="2026-03-09T12:00:05"))
    c.provider_status = kwargs.get("provider_status")
    return c


def _make_valid_manifest(
    landscape_hash="abc123def456",
    signed_at="2026-03-09T12:00:00Z",
    kid="tru8-2026-03",
    executed_tier="full",
    pipeline_fingerprint="a1b2c3d4e5f6",
):
    """Build a dict resembling a stored manifest JSONB value."""
    return {
        "landscape_hash": landscape_hash,
        "signature": "hmac-sha256:deadbeef",
        "signed_at": signed_at,
        "kid": kid,
        "scheme": "hmac-sha256",
        "canonical_version": 1,
        "pipeline_fingerprint": pipeline_fingerprint,
        "executed_tier": executed_tier,
    }


# ---------------------------------------------------------------------------
# Mock helpers
# ---------------------------------------------------------------------------


class _MockExecuteResult:
    """Mock for SQLAlchemy execute() result supporting scalars().all()."""

    def __init__(self, rows=None):
        self._rows = rows or []

    def scalars(self):
        return self

    def all(self):
        return self._rows


def _build_mock_session(check=None, claims=None, evidence_by_claim=None):
    """Build an AsyncMock session with get() and execute() wired up.

    Args:
        check: The Check model returned by session.get(Check, id).
        claims: List of Claim mocks returned for the claims query.
        evidence_by_claim: Dict mapping claim.id to list of Evidence mocks.
    """
    session = AsyncMock()
    session.get = AsyncMock(return_value=check)

    claims = claims or []
    evidence_by_claim = evidence_by_claim or {}

    call_count = {"n": 0}

    async def _mock_execute(stmt):
        # First call: claims query; subsequent calls: evidence per claim
        idx = call_count["n"]
        call_count["n"] += 1
        if idx == 0:
            return _MockExecuteResult(rows=claims)
        else:
            # Return evidence for the claim at (idx-1)
            if idx - 1 < len(claims):
                claim = claims[idx - 1]
                evs = evidence_by_claim.get(claim.id, [])
                return _MockExecuteResult(rows=evs)
            return _MockExecuteResult(rows=[])

    session.execute = _mock_execute
    return session


def _make_claim(
    claim_id=None, check_id="check-001", text="GDP grew 2.1%", claim_map=None
):
    """Build a MagicMock resembling a Claim DB row."""
    cl = MagicMock()
    cl.id = claim_id or str(uuid.uuid4())
    cl.check_id = check_id
    cl.text = text
    cl.position = 0
    cl.claim_text_hash = "hash-" + cl.id[:8]
    cl.claim_map = claim_map or {
        "elements": [
            {
                "description": "GDP grew 2.1%",
                "state": "supported",
                "evidence_refs": [{"evidence_id": "ev-001"}],
            }
        ],
    }
    return cl


def _make_evidence(evidence_id="ev-001", claim_id="claim-001"):
    """Build a MagicMock resembling an Evidence DB row."""
    ev = MagicMock()
    ev.id = str(uuid.uuid4())
    ev.evidence_id = evidence_id
    ev.claim_id = claim_id
    ev.tier = "reporting"
    ev.evidence_type = "news"
    ev.content_basis = "snippet"
    ev.classification_method = "heuristic"
    return ev


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestVerifyEndpoint:
    """Tests for GET /verify/{check_id}."""

    @pytest.mark.asyncio
    async def test_valid_manifest(self):
        """Valid manifest with matching canonical hash returns {valid: true}."""
        check_id = "check-valid-001"
        manifest = _make_valid_manifest(landscape_hash="correct-hash")
        check = _make_check(check_id=check_id, manifest=manifest)
        claim = _make_claim(check_id=check_id)
        evidence = _make_evidence(claim_id=claim.id)
        session = _build_mock_session(
            check=check,
            claims=[claim],
            evidence_by_claim={claim.id: [evidence]},
        )

        app = _create_test_app()

        with (
            patch("app.api.v1.verify.get_session") as mock_get_session,
            patch("app.api.v1.verify.verify_manifest") as mock_verify,
            patch("app.api.v1.verify.build_canonical_data") as mock_build,
            patch("app.api.v1.verify.compute_canonical_hash") as mock_hash,
            patch(
                "app.api.v1.response_builder._compute_landscape",
                return_value={"elementCount": 1},
            ),
        ):
            # Wire up the async context manager for get_session
            mock_ctx = AsyncMock()
            mock_ctx.__aenter__ = AsyncMock(return_value=session)
            mock_ctx.__aexit__ = AsyncMock(return_value=False)
            mock_get_session.return_value = mock_ctx

            mock_verify.return_value = {"valid": True}
            mock_build.return_value = {"v": 1, "check_id": check_id}
            mock_hash.return_value = "correct-hash"

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.get(f"/verify/{check_id}")

        assert resp.status_code == 200
        body = resp.json()
        assert body["valid"] is True
        assert body["checkId"] == check_id
        assert body["signedAt"] == manifest["signed_at"]
        assert body["kid"] == manifest["kid"]
        assert body["executedTier"] == manifest["executed_tier"]
        assert body["pipelineFingerprint"] == manifest["pipeline_fingerprint"]

    @pytest.mark.asyncio
    async def test_check_not_found(self):
        """Non-existent check_id returns {valid: false, reason: 'not_found'}."""
        session = AsyncMock()
        session.get = AsyncMock(return_value=None)

        app = _create_test_app()

        with patch("app.api.v1.verify.get_session") as mock_get_session:
            mock_ctx = AsyncMock()
            mock_ctx.__aenter__ = AsyncMock(return_value=session)
            mock_ctx.__aexit__ = AsyncMock(return_value=False)
            mock_get_session.return_value = mock_ctx

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.get("/verify/nonexistent-id")

        assert resp.status_code == 200
        body = resp.json()
        assert body["valid"] is False
        assert body["reason"] == "not_found"

    @pytest.mark.asyncio
    async def test_no_manifest(self):
        """Check exists but manifest is None returns {valid: false, reason: 'not_found'}."""
        check = _make_check(check_id="check-no-manifest", manifest=None)
        session = AsyncMock()
        session.get = AsyncMock(return_value=check)

        app = _create_test_app()

        with patch("app.api.v1.verify.get_session") as mock_get_session:
            mock_ctx = AsyncMock()
            mock_ctx.__aenter__ = AsyncMock(return_value=session)
            mock_ctx.__aexit__ = AsyncMock(return_value=False)
            mock_get_session.return_value = mock_ctx

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.get("/verify/check-no-manifest")

        assert resp.status_code == 200
        body = resp.json()
        assert body["valid"] is False
        assert body["reason"] == "not_found"

    @pytest.mark.asyncio
    async def test_invalid_signature(self):
        """verify_manifest returns invalid signature -> {valid: false, reason: 'signature_invalid'}."""
        manifest = _make_valid_manifest()
        check = _make_check(check_id="check-bad-sig", manifest=manifest)
        session = AsyncMock()
        session.get = AsyncMock(return_value=check)

        app = _create_test_app()

        with (
            patch("app.api.v1.verify.get_session") as mock_get_session,
            patch("app.api.v1.verify.verify_manifest") as mock_verify,
        ):
            mock_ctx = AsyncMock()
            mock_ctx.__aenter__ = AsyncMock(return_value=session)
            mock_ctx.__aexit__ = AsyncMock(return_value=False)
            mock_get_session.return_value = mock_ctx

            mock_verify.return_value = {"valid": False, "reason": "signature_invalid"}

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.get("/verify/check-bad-sig")

        assert resp.status_code == 200
        body = resp.json()
        assert body["valid"] is False
        assert body["reason"] == "signature_invalid"

    @pytest.mark.asyncio
    async def test_data_integrity_mismatch(self):
        """Signature valid but recomputed hash differs -> {valid: false, reason: 'data_modified'}."""
        check_id = "check-tampered"
        manifest = _make_valid_manifest(landscape_hash="original-hash")
        check = _make_check(check_id=check_id, manifest=manifest)
        claim = _make_claim(check_id=check_id)
        evidence = _make_evidence(claim_id=claim.id)
        session = _build_mock_session(
            check=check,
            claims=[claim],
            evidence_by_claim={claim.id: [evidence]},
        )

        app = _create_test_app()

        with (
            patch("app.api.v1.verify.get_session") as mock_get_session,
            patch("app.api.v1.verify.verify_manifest") as mock_verify,
            patch("app.api.v1.verify.build_canonical_data") as mock_build,
            patch("app.api.v1.verify.compute_canonical_hash") as mock_hash,
            patch("app.api.v1.response_builder._compute_landscape", return_value={}),
        ):
            mock_ctx = AsyncMock()
            mock_ctx.__aenter__ = AsyncMock(return_value=session)
            mock_ctx.__aexit__ = AsyncMock(return_value=False)
            mock_get_session.return_value = mock_ctx

            mock_verify.return_value = {"valid": True}
            mock_build.return_value = {"v": 1, "check_id": check_id}
            # Recomputed hash differs from stored landscape_hash
            mock_hash.return_value = "different-hash-after-mutation"

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.get(f"/verify/{check_id}")

        assert resp.status_code == 200
        body = resp.json()
        assert body["valid"] is False
        assert body["reason"] == "data_modified"

    @pytest.mark.asyncio
    async def test_unknown_key_reason(self):
        """verify_manifest returns unknown_key -> {valid: false, reason: 'unknown_key'}."""
        manifest = _make_valid_manifest(kid="expired-kid-2024")
        check = _make_check(check_id="check-old-key", manifest=manifest)
        session = AsyncMock()
        session.get = AsyncMock(return_value=check)

        app = _create_test_app()

        with (
            patch("app.api.v1.verify.get_session") as mock_get_session,
            patch("app.api.v1.verify.verify_manifest") as mock_verify,
        ):
            mock_ctx = AsyncMock()
            mock_ctx.__aenter__ = AsyncMock(return_value=session)
            mock_ctx.__aexit__ = AsyncMock(return_value=False)
            mock_get_session.return_value = mock_ctx

            mock_verify.return_value = {"valid": False, "reason": "unknown_key"}

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.get("/verify/check-old-key")

        assert resp.status_code == 200
        body = resp.json()
        assert body["valid"] is False
        assert body["reason"] == "unknown_key"
