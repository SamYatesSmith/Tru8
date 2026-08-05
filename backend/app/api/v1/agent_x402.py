"""x402 USDC payment endpoints — /api/v1/agent/x402/*

These endpoints are identical to /api/v1/agent/{tier} but use the x402
HTTP 402 challenge/response payment flow instead of API key + credits.

The x402 payment middleware handles settlement automatically:
  1. Agent sends POST without payment → 402 with price + payTo
  2. Agent pays via USDC → resends with PAYMENT-SIGNATURE header
  3. Middleware verifies payment → handler runs → 200 with PAYMENT-RESPONSE

SIWE endpoints (challenge + result retrieval) are NOT behind x402 middleware.
"""

import asyncio
import json
import logging
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Header, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.agent import _resolve_input
from app.core.agent_auth import AgentPaymentContext, compute_request_hash
from app.core.agent_pricing import get_tier_price
from app.core.tier_limitations import limitations_for_tier
from app.core.client_origin import resolve_client
from app.core.config import settings
from app.core.database import get_session
from app.core.rate_limit import limiter
from app.models.check import Check, Claim, compute_claim_text_hash
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Request model (same as agent.py)
# ---------------------------------------------------------------------------


class X402ClaimRequest(BaseModel):
    claim: str
    input_type: Optional[str] = None
    compact: Optional[bool] = False


# ---------------------------------------------------------------------------
# x402 auth dependency — wallet identity via PAYMENT-SIGNATURE header
# ---------------------------------------------------------------------------


async def get_x402_payment(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> AgentPaymentContext:
    """Verify x402 payment and resolve wallet to Tru8 user.

    The x402 facilitator middleware has already verified the payment by this
    point.  We extract the wallet address from the verified payment headers
    and lazy-create a Tru8 user for it.
    """
    # Extract wallet address from x402 payment headers
    # The facilitator sets these after verifying the USDC payment
    payer_address = request.headers.get("x-payer-address", "").lower()

    if not payer_address:
        raise HTTPException(
            status_code=401,
            detail="x402 payment required. Send USDC payment to proceed.",
        )

    # Lazy-create Tru8 user for wallet address (CAIP-10, always lowercase)
    external_id = f"x402:{settings.X402_NETWORK}:{payer_address}"

    result = await session.execute(select(User).where(User.external_id == external_id))
    user = result.scalar_one_or_none()

    if not user:
        try:
            user = User(
                id=f"x402_{payer_address[:16]}",
                email=f"{payer_address[:16]}@x402.agent",
                external_id=external_id,
                credits=0,
            )
            session.add(user)
            await session.flush()
            logger.info(f"Created Tru8 user for x402 wallet: {user.id}")
        except IntegrityError:
            await session.rollback()
            result = await session.execute(
                select(User).where(User.external_id == external_id)
            )
            user = result.scalar_one()

    return AgentPaymentContext(
        provider="x402",
        payer_id=payer_address,
        user_id=user.id,
        session=session,
    )


# ---------------------------------------------------------------------------
# Shared pipeline handler (reuses agent.py pattern)
# ---------------------------------------------------------------------------

# Derived from the pipeline config (2026-08-05). This was a verbatim copy of
# the list in agent.py — two hand-maintained copies of the same truth, either
# of which could be updated without the other. Both now read the same source.
QUICK_LIMITATIONS = limitations_for_tier("quick")


async def _run_x402_pipeline(
    *,
    body: X402ClaimRequest,
    tier: str,
    amount_pence: int,
    limitations: list,
    payment: AgentPaymentContext,
    session: AsyncSession,
    request: Request,
    idempotency_key: Optional[str] = None,
) -> JSONResponse:
    """Create check, run pipeline, return response with _meta.

    Sets ``request.state.agent_tx_id`` for the audit middleware.
    """
    from app.core.database import async_session
    from app.pipeline.progress import ProgressReporter
    from app.pipeline.runner import (
        DEFAULT_CONFIG,
        QUICK_CONFIG,
        PipelineError,
        handle_pipeline_failure,
        run_pipeline,
        run_pipeline_phase2,
        save_check_results_async,
    )

    config = QUICK_CONFIG if tier == "quick" else DEFAULT_CONFIG
    claim_hash = compute_claim_text_hash(body.claim)
    request_hash = compute_request_hash(tier, claim_hash, body.compact or False)

    # Create transaction (x402 payment already verified by middleware)
    tx = await payment.charge(
        amount_pence=amount_pence,
        tier=tier,
        description=claim_hash,
        idempotency_key=idempotency_key,
        request_hash=request_hash,
    )

    # Set tx ID on request state for audit middleware correlation
    request.state.agent_tx_id = tx.id

    # Honour input_type (parity with /agent): auto-detect URL vs text so a URL
    # submitted via x402 is fetched/extracted rather than treated as literal text.
    resolved_type, input_data = _resolve_input(body.claim, body.input_type)

    # Create check record
    check = Check(
        id=str(uuid.uuid4()),
        user_id=payment.user_id,
        input_type=resolved_type,
        input_content=json.dumps(input_data),
        input_url=input_data.get("url"),
        status="processing",
        credits_used=0,
        initiated_via="agent_x402",
        client=resolve_client(request),  # first-party client attribution (e.g. "mcp")
        executed_tier=tier,  # M-03: record pipeline tier at creation
    )
    session.add(check)
    await session.commit()
    await session.refresh(check)

    tx.check_id = check.id
    await session.commit()

    progress_reporter = ProgressReporter(check.id)

    try:
        result = await asyncio.wait_for(
            run_pipeline(
                check.id, payment.user_id, input_data, progress_reporter, config=config
            ),
            timeout=config.max_wall_time_seconds,
        )

        # Article mode auto-select
        if result is None:
            async with async_session() as sel_session:
                claims_stmt = (
                    select(Claim)
                    .where(Claim.check_id == check.id)
                    .order_by(Claim.position)
                )
                claims_result = await sel_session.execute(claims_stmt)
                db_claims = list(claims_result.scalars().all())
                ranked = sorted(
                    db_claims,
                    key=lambda c: (
                        c.significance_rank if c.significance_rank is not None else 999
                    ),
                )
                for i, claim in enumerate(ranked):
                    claim.is_selected = i < 5
                sel_check = (
                    await sel_session.execute(select(Check).where(Check.id == check.id))
                ).scalar_one()
                sel_check.selected_claims_count = min(len(ranked), 5)
                await sel_session.commit()

            result = await asyncio.wait_for(
                run_pipeline_phase2(
                    check_id=check.id,
                    user_id=payment.user_id,
                    input_data=input_data,
                    progress_reporter=ProgressReporter(check.id),
                    config=config,
                ),
                timeout=config.max_wall_time_seconds,
            )

        async with async_session() as save_session:
            await save_check_results_async(check.id, result, save_session)
            await save_session.commit()

        # Mark completed + attach metrics
        tx.status = "completed"
        pipeline_metrics = result.get("pipeline_metrics")
        if pipeline_metrics and tx.tx_metadata:
            tx.tx_metadata["metrics"] = pipeline_metrics
        elif pipeline_metrics:
            tx.tx_metadata = {"metrics": pipeline_metrics}
        await session.commit()

        from app.api.v1.response_builder import build_agent_response

        async with async_session() as resp_session:
            response_data = await build_agent_response(
                check_id=check.id,
                session=resp_session,
                executed_tier=tier,
                charged_pence=amount_pence,
                limitations=limitations,
                compact=body.compact or False,
            )

        return JSONResponse(
            content=response_data,
            headers={
                "X-Check-Id": check.id,
                "X-Tru8-Tx-Id": tx.id,
            },
        )

    except asyncio.TimeoutError:
        logger.error(
            f"[AGENT X402 {tier.upper()}] Pipeline timed out for check {check.id}"
        )
        tx.status = "failed"
        await session.commit()
        await handle_pipeline_failure(
            check.id, payment.user_id, Exception("Pipeline timed out")
        )
        raise HTTPException(status_code=504, detail="Pipeline timed out.")

    except PipelineError as e:
        logger.error(
            f"[AGENT X402 {tier.upper()}] Pipeline error for check {check.id}: {e}"
        )
        tx.status = "failed"
        await session.commit()
        await handle_pipeline_failure(check.id, payment.user_id, e)
        raise HTTPException(status_code=502, detail=f"Pipeline error: {e}")

    except HTTPException:
        raise

    except Exception as e:
        logger.error(
            f"[AGENT X402 {tier.upper()}] Unexpected error for check {check.id}: {e}"
        )
        tx.status = "failed"
        await session.commit()
        await handle_pipeline_failure(check.id, payment.user_id, e)
        raise HTTPException(status_code=502, detail=f"Pipeline error: {e}")


# ---------------------------------------------------------------------------
# POST /agent/x402/preflight — tier suggestion without payment (M-03)
# ---------------------------------------------------------------------------


class PreflightRequest(BaseModel):
    claim: str


@router.post("/preflight")
@limiter.limit("30/minute")
async def x402_preflight(
    body: PreflightRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> JSONResponse:
    """Suggest optimal tier for a claim without requiring payment.

    User-scoped: resolves wallet via SIWE challenge/verify and checks
    for existing completed analysis matching the claim hash.

    NOT behind x402 payment middleware — free endpoint.
    """
    # Resolve wallet identity (same as get_x402_payment but no charge)
    payer_address = request.headers.get("x-payer-address", "").lower()
    if not payer_address:
        # Allow unauthenticated preflight — always suggests "quick"
        claim_hash = compute_claim_text_hash(body.claim)
        return JSONResponse(
            content={
                "suggestedTier": "quick",
                "reason": "no_auth",
                "costPence": get_tier_price("quick"),
                "claimTextHash": claim_hash,
            }
        )

    external_id = f"x402:{settings.X402_NETWORK}:{payer_address}"
    result = await session.execute(select(User).where(User.external_id == external_id))
    user = result.scalar_one_or_none()

    claim_hash = compute_claim_text_hash(body.claim)

    if not user:
        return JSONResponse(
            content={
                "suggestedTier": "quick",
                "reason": "no_prior_analysis",
                "costPence": get_tier_price("quick"),
                "claimTextHash": claim_hash,
            }
        )

    # User-scoped lookup (same scope as /agent/lookup)
    hit_result = await session.execute(
        select(Claim, Check)
        .join(Check, Claim.check_id == Check.id)
        .where(
            Claim.claim_text_hash == claim_hash,
            Check.user_id == user.id,
            Check.status == "completed",
        )
        .order_by(Check.completed_at.desc())
        .limit(1)
    )
    row = hit_result.first()

    if row:
        _, check = row
        return JSONResponse(
            content={
                "suggestedTier": "lookup",
                "reason": "cache_hit",
                "costPence": get_tier_price("lookup"),
                "claimTextHash": claim_hash,
                "cachedCheckId": check.id,
                "cachedAt": (
                    check.completed_at.isoformat() if check.completed_at else None
                ),
            }
        )

    return JSONResponse(
        content={
            "suggestedTier": "quick",
            "reason": "no_prior_analysis",
            "costPence": get_tier_price("quick"),
            "claimTextHash": claim_hash,
        }
    )


# ---------------------------------------------------------------------------
# POST /agent/x402/lookup — cached analysis via x402 payment
# ---------------------------------------------------------------------------


@router.post("/lookup")
@limiter.limit("30/minute")
async def x402_lookup(
    body: X402ClaimRequest,
    request: Request,
    payment: AgentPaymentContext = Depends(get_x402_payment),
    session: AsyncSession = Depends(get_session),
) -> JSONResponse:
    """Instant cached analysis via claim_text_hash, paid via USDC."""
    claim_hash = compute_claim_text_hash(body.claim)
    tier = "lookup"
    amount_pence = get_tier_price(tier)

    result = await session.execute(
        select(Claim, Check)
        .join(Check, Claim.check_id == Check.id)
        .where(
            Claim.claim_text_hash == claim_hash,
            Check.user_id == payment.user_id,
            Check.status == "completed",
        )
        .order_by(Check.completed_at.desc())
        .limit(1)
    )
    row = result.first()

    if not row:
        return JSONResponse(
            content={
                "hit": False,
                "nextSuggestedTier": "quick",
                "upgradeCostPence": get_tier_price("quick"),
                "claimTextHash": claim_hash,
            }
        )

    claim, check = row
    tx = await payment.charge(
        amount_pence=amount_pence,
        tier=tier,
        description=claim_hash,
        check_id=check.id,
    )
    request.state.agent_tx_id = tx.id
    tx.status = "completed"
    await session.flush()

    from app.api.v1.response_builder import build_agent_response

    response_data = await build_agent_response(
        check_id=check.id,
        session=session,
        executed_tier=tier,
        charged_pence=amount_pence,
        limitations=limitations_for_tier(check.executed_tier),
        compact=body.compact or False,
        cached_from=check.completed_at.isoformat() if check.completed_at else None,
        cached_tier=check.executed_tier,
    )
    response_data["hit"] = True
    await session.commit()

    return JSONResponse(
        content=response_data,
        headers={"X-Check-Id": check.id, "X-Tru8-Tx-Id": tx.id},
    )


# ---------------------------------------------------------------------------
# POST /agent/x402/quick
# ---------------------------------------------------------------------------


@router.post("/quick")
@limiter.limit("10/minute")
async def x402_quick(
    body: X402ClaimRequest,
    request: Request,
    payment: AgentPaymentContext = Depends(get_x402_payment),
    session: AsyncSession = Depends(get_session),
) -> JSONResponse:
    """Reduced pipeline via x402 USDC payment."""
    return await _run_x402_pipeline(
        body=body,
        tier="quick",
        amount_pence=get_tier_price("quick"),
        limitations=limitations_for_tier("quick"),
        payment=payment,
        session=session,
        request=request,
        idempotency_key=request.headers.get("Idempotency-Key"),
    )


# ---------------------------------------------------------------------------
# POST /agent/x402/full
# ---------------------------------------------------------------------------


@router.post("/full")
@limiter.limit("10/minute")
async def x402_full(
    body: X402ClaimRequest,
    request: Request,
    payment: AgentPaymentContext = Depends(get_x402_payment),
    session: AsyncSession = Depends(get_session),
) -> JSONResponse:
    """Complete pipeline via x402 USDC payment."""
    return await _run_x402_pipeline(
        body=body,
        tier="full",
        amount_pence=get_tier_price("full"),
        limitations=limitations_for_tier("full"),
        payment=payment,
        session=session,
        request=request,
        idempotency_key=request.headers.get("Idempotency-Key"),
    )


# ---------------------------------------------------------------------------
# GET /agent/x402/challenge — SIWE challenge for result retrieval
# ---------------------------------------------------------------------------


@router.get("/challenge")
@limiter.limit("10/minute")
async def x402_challenge(
    request: Request,
    address: str = Query(..., description="Ethereum wallet address"),
    check_id: str = Query(..., description="Check ID to retrieve"),
) -> JSONResponse:
    """Generate a SIWE challenge for authenticated result retrieval.

    Rate-limited to 10/min per address to prevent nonce flooding.
    """
    from app.core.siwe_verifier import generate_challenge

    try:
        challenge = await generate_challenge(address.lower(), check_id)
        return JSONResponse(content=challenge)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))


# ---------------------------------------------------------------------------
# POST /agent/x402/result/{check_id} — SIWE-authenticated retrieval
# ---------------------------------------------------------------------------


class SIWEResultRequest(BaseModel):
    message: str
    signature: str


@router.post("/result/{check_id}")
@limiter.limit("30/minute")
async def x402_result(
    check_id: str,
    body: SIWEResultRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> JSONResponse:
    """Retrieve a completed check result via SIWE-authenticated wallet.

    NOT behind x402 payment middleware — retrieval is free after payment.
    """
    from app.core.siwe_verifier import verify_signature

    try:
        wallet_address = await verify_signature(body.message, body.signature, check_id)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))

    # Resolve wallet to Tru8 user
    external_id = f"x402:{settings.X402_NETWORK}:{wallet_address}"
    result = await session.execute(select(User).where(User.external_id == external_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=403, detail="No account found for this wallet")

    # Verify check ownership
    check_result = await session.execute(
        select(Check).where(Check.id == check_id, Check.user_id == user.id)
    )
    check = check_result.scalar_one_or_none()

    if not check:
        raise HTTPException(status_code=404, detail="Check not found")

    if check.status != "completed":
        raise HTTPException(
            status_code=409,
            detail=f"Check is not completed (status: {check.status})",
        )

    from app.api.v1.response_builder import build_agent_response

    # Producing tier, not a hardcoded "full" — see agent.get_agent_result.
    response_data = await build_agent_response(
        check_id=check_id,
        session=session,
        executed_tier=check.executed_tier or "full",
        charged_pence=0,
        limitations=limitations_for_tier(check.executed_tier),
    )

    return JSONResponse(
        content=response_data,
        headers={"X-Check-Id": check_id},
    )
