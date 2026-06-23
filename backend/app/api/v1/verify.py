"""M-04: Public manifest verification endpoint.

GET /verify/{check_id} — unauthenticated, rate-limited.
Verifies both signature authenticity and data integrity.
"""

import logging

from fastapi import APIRouter, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session
from app.core.manifest_signer import (
    build_canonical_data,
    compute_canonical_hash,
    verify_manifest,
)
from app.models.check import Check, Claim, Evidence
from app.api.v1.schemas import VerifySuccessResponse, VerifyFailureResponse

logger = logging.getLogger(__name__)

router = APIRouter()


async def _load_claims_for_verify(check_id: str, session: AsyncSession) -> list[dict]:
    """Load claims with ClaimMaps for canonical hash computation.

    Deliberately separate from response_builder._load_claims_data() because:
    1. /verify is public — must not depend on user-scoped response builder.
    2. Only loads fields required for canonical hashing.
    3. Prevents accidental field leakage through the public verify path.
    """
    stmt = select(Claim).where(Claim.check_id == check_id).order_by(Claim.position)
    result = await session.execute(stmt)
    claims = result.scalars().all()

    claims_data = []
    for claim in claims:
        # Load evidence for this claim
        ev_stmt = select(Evidence).where(Evidence.claim_id == claim.id)
        ev_result = await session.execute(ev_stmt)
        evidence_rows = ev_result.scalars().all()

        evidence_list = []
        for ev in evidence_rows:
            evidence_list.append(
                {
                    "evidence_id": ev.evidence_id,
                    "tier": ev.tier,
                    "evidence_type": ev.evidence_type,
                    "content_basis": ev.content_basis,
                    "classification_method": ev.classification_method,
                    # Required so the recomputed landscape matches signing time:
                    # _compute_landscape derives uniqueDomains from evidence URLs,
                    # and the signing path (runner) passes evidence dicts with url.
                    "url": ev.url,
                }
            )

        claim_dict = {
            "text": claim.text,
            "claim_text_hash": claim.claim_text_hash,
            "claimMap": claim.claim_map,
            "evidence": evidence_list,
        }
        claims_data.append(claim_dict)

    return claims_data


@router.get(
    "/verify/{check_id}",
    summary="Verify check manifest integrity",
    responses={
        200: {
            "description": "Verification result — check `valid` field",
            "model": VerifySuccessResponse,
        },
    },
)
async def verify_check(check_id: str, request: Request):
    """Verify the signed manifest for a completed check.

    Confirms the signed fields haven't changed since signing.

    **Public endpoint** — no authentication required.

    Two-step verification:
    1. **Signature authenticity** — proves the manifest wasn't forged
    2. **Data integrity** — proves the database wasn't mutated since signing

    Returns `{valid: true, ...}` on success, or `{valid: false, reason: "..."}` on failure.

    **Rate limit:** 60/minute per IP
    """
    async with async_session() as session:
        check = await session.get(Check, check_id)
        if not check or not check.manifest:
            return {"valid": False, "reason": "not_found"}

        stored = check.manifest

        # Step 1: Verify signature authenticity
        sig_result = verify_manifest(stored)
        if not sig_result.get("valid"):
            return sig_result

        # Step 2: Verify data integrity — recompute canonical hash from DB
        claims_data = await _load_claims_for_verify(check_id, session)

        # Recompute landscape from response builder
        from app.api.v1.response_builder import _compute_landscape

        landscape = _compute_landscape(claims_data, check)

        # Get orientation_basis from first claim's ClaimMap (if present)
        orientation_basis = None
        for c in claims_data:
            cm = c.get("claimMap") or {}
            ob = cm.get("orientation_basis")
            if ob:
                orientation_basis = ob
                break

        canonical_data = build_canonical_data(
            check_id=check_id,
            claims_data=claims_data,
            executed_tier=check.executed_tier,
            landscape=landscape,
            orientation_basis=orientation_basis,
        )
        current_hash = compute_canonical_hash(canonical_data)

        if current_hash != stored.get("landscape_hash"):
            return {"valid": False, "reason": "data_modified"}

        return {
            "valid": True,
            "checkId": check_id,
            "signedAt": stored.get("signed_at"),
            "kid": stored.get("kid"),
            "executedTier": stored.get("executed_tier"),
            "pipelineFingerprint": stored.get("pipeline_fingerprint"),
        }
