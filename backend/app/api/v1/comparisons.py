"""COMPARE tab endpoints.

Design: audit/2026-08-26_compare_tab_design.md §10.3, §7.7.

Surface wall:
- CREATE is Clerk-session ONLY (`get_current_user`, the JWT-only dependency)
  — API keys structurally cannot reach it, so the Agent API and MCP never
  can. Ownership is enforced on the check row.
- READ has an authenticated variant (dashboard) and a public variant under
  /public/ (the /r/ page, completed checks only, read-only) — same split as
  every other public surface in checks.py.

Budget refusal is 409; an invalid pair is 422; a run that produced nothing
is 502 and does not count. Collisions in every response are computed from
the LIVE claim map at read time — never stored (§7.4).
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.database import get_session
from app.models import Check, Claim, ClaimComparison, Evidence
from app.services.comparison import (
    ComparisonError,
    get_comparison_budget,
    run_comparison,
    serialise_comparison,
)

logger = logging.getLogger(__name__)

router = APIRouter()


class CreateComparisonRequest(BaseModel):
    evidenceA: str = Field(min_length=1, max_length=64)
    evidenceB: str = Field(min_length=1, max_length=64)


async def _load_claim(session: AsyncSession, check_id: str, claim_id: str) -> Claim:
    claim = (
        await session.execute(
            select(Claim).where(Claim.id == claim_id, Claim.check_id == check_id)
        )
    ).scalar_one_or_none()
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    return claim


async def _load_shown_evidence(
    session: AsyncSession, claim_id: str, evidence_ref: str
) -> Optional[Evidence]:
    """Resolve an evidence ref (stable evidence_id or row id) within the
    claim's SHOWN set. Excluded/unmapped items are not comparable —
    comparing a source the pipeline excluded with a receipt would
    re-platform it (§7.6)."""
    rows = (
        (await session.execute(select(Evidence).where(Evidence.claim_id == claim_id)))
        .scalars()
        .all()
    )
    for ev in rows:
        if (ev.evidence_id or ev.id) == evidence_ref or ev.id == evidence_ref:
            if (ev.receipt_status or "shown") != "shown":
                return None
            return ev
    return None


@router.post(
    "/{check_id}/claims/{claim_id}/comparisons",
    summary="Compare two sources on this claim (dashboard only)",
    responses={
        200: {"description": "Comparison (fresh or cached)"},
        404: {"description": "Check or claim not found"},
        409: {"description": "Comparison budget exhausted"},
        422: {"description": "Invalid pair"},
        502: {"description": "Fetch or model failure — not charged"},
    },
)
async def create_comparison(
    check_id: str,
    claim_id: str,
    request: CreateComparisonRequest,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    # Ownership — Clerk session only; API keys cannot reach this dependency.
    check = (
        await session.execute(
            select(Check).where(
                Check.id == check_id, Check.user_id == current_user["id"]
            )
        )
    ).scalar_one_or_none()
    if not check:
        raise HTTPException(status_code=404, detail="Check not found")
    if check.status != "completed":
        raise HTTPException(
            status_code=409,
            detail="Comparisons are only available on completed checks",
        )

    if request.evidenceA == request.evidenceB:
        raise HTTPException(status_code=422, detail="invalid_pair")

    claim = await _load_claim(session, check_id, claim_id)
    evidence_a = await _load_shown_evidence(session, claim_id, request.evidenceA)
    evidence_b = await _load_shown_evidence(session, claim_id, request.evidenceB)
    if not evidence_a or not evidence_b:
        raise HTTPException(status_code=422, detail="invalid_pair")

    try:
        row, cached = await run_comparison(
            session, check_id, claim, evidence_a, evidence_b
        )
    except ComparisonError as e:
        # Plain string codes throughout: the web client surfaces error.detail
        # as Error.message, so an object here would reach the UI as
        # "[object Object]". The budget itself comes from the GET.
        if e.code == "budget_exhausted":
            raise HTTPException(status_code=409, detail="budget_exhausted")
        raise HTTPException(status_code=502, detail=e.code)

    budget = await get_comparison_budget(session, check_id)
    return {
        **serialise_comparison(row, claim),
        "cached": cached,
        "budget": budget,
    }


@router.get(
    "/{check_id}/claims/{claim_id}/comparisons",
    summary="List comparisons for a claim (dashboard)",
)
async def list_comparisons(
    check_id: str,
    claim_id: str,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    check = (
        await session.execute(
            select(Check).where(
                Check.id == check_id, Check.user_id == current_user["id"]
            )
        )
    ).scalar_one_or_none()
    if not check:
        raise HTTPException(status_code=404, detail="Check not found")

    claim = await _load_claim(session, check_id, claim_id)
    rows = (
        (
            await session.execute(
                select(ClaimComparison)
                .where(ClaimComparison.claim_id == claim_id)
                .order_by(ClaimComparison.created_at)
            )
        )
        .scalars()
        .all()
    )
    budget = await get_comparison_budget(session, check_id)
    return {
        "comparisons": [serialise_comparison(r, claim) for r in rows],
        "budget": budget,
    }


@router.get(
    "/public/{check_id}/claims/{claim_id}/comparisons",
    summary="List comparisons for a claim (public report, read-only)",
)
async def list_comparisons_public(
    check_id: str,
    claim_id: str,
    session: AsyncSession = Depends(get_session),
):
    """The /r/ page: stored comparisons only, completed checks only, no
    auth, no budget, no create."""
    check = (
        await session.execute(select(Check).where(Check.id == check_id))
    ).scalar_one_or_none()
    if not check or check.status != "completed":
        raise HTTPException(status_code=404, detail="Check not found")

    claim = await _load_claim(session, check_id, claim_id)
    rows = (
        (
            await session.execute(
                select(ClaimComparison)
                .where(ClaimComparison.claim_id == claim_id)
                .order_by(ClaimComparison.created_at)
            )
        )
        .scalars()
        .all()
    )
    return {"comparisons": [serialise_comparison(r, claim) for r in rows]}
