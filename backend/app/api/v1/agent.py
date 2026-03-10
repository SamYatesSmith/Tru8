"""Agent commerce endpoints — /api/v1/agent/*

Skyfire + credit auth (PaymentProvider ABC chain).
x402 routes live at /api/v1/agent/x402/* (L-05).

All agent endpoints accept optional Idempotency-Key header.
Response headers: X-Check-Id, X-Tru8-Tx-Id.
"""

import asyncio
import json
import logging
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Header, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.agent_auth import (
    AgentIdentity,
    AgentPaymentContext,
    compute_request_hash,
    get_agent_identity,
    get_agent_payment,
)
from app.core.agent_pricing import get_tier_price
from app.core.database import get_session
from app.core.rate_limit import limiter
from app.models.check import Check, Claim, compute_claim_text_hash
from app.api.v1.schemas import (
    AgentCheckResponse,
    AgentCacheMiss,
    CreditBalanceResponse,
    CheckoutSessionResponse,
    AgentStatsResponse,
    ErrorResponse,
    PipelineErrorResponse,
    TimeoutErrorResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------


class AgentClaimRequest(BaseModel):
    """Submit a claim or URL for evidence research."""

    claim: str = Field(
        description="The claim text to analyse, or a URL to extract claims from"
    )
    input_type: Optional[str] = Field(
        None,
        description="Input type: 'text' or 'url'. Auto-detected from the claim field if omitted.",
    )
    compact: Optional[bool] = Field(
        False,
        description="If true, returns claims and claim maps only — no evidence arrays. Reduces payload size for agents that only need orientation.",
    )


class SmartCheckRequest(BaseModel):
    """Request for the smart /agent/check endpoint with automatic tier fallback."""

    claim: str = Field(
        description="The claim text to analyse, or a URL to extract claims from"
    )
    input_type: Optional[str] = Field(
        None,
        description="Input type: 'text' or 'url'. Auto-detected from the claim field if omitted.",
    )
    max_tier: str = Field(
        "full",
        description="Maximum pipeline tier to execute. The endpoint tries lookup first, then escalates up to this tier. Options: lookup, consensus, quick, full.",
    )
    max_age_hours: Optional[int] = Field(
        None,
        description="Maximum cache age in hours for lookup hits. If the cached result is older than this, it's treated as a miss and the endpoint escalates.",
    )
    compact: bool = Field(
        False,
        description="If true, returns claims and claim maps only — no evidence arrays.",
    )


def _resolve_input(claim: str, explicit_type: Optional[str] = None) -> tuple:
    """Resolve input_type and build input_data dict from agent claim field.

    Auto-detects URLs when explicit_type is omitted.
    Returns (input_type, input_data) where input_data has the keys
    expected by ingest_content_async.
    """
    if explicit_type == "url" or (
        explicit_type is None and claim.strip().startswith(("http://", "https://"))
    ):
        return "url", {"input_type": "url", "url": claim.strip()}
    return "text", {"input_type": "text", "content": claim}


# ---------------------------------------------------------------------------
# POST /agent/check — smart endpoint with server-side fallback (M-03)
# ---------------------------------------------------------------------------


@router.post(
    "/check",
    summary="Smart evidence research with automatic tier fallback",
    responses={
        200: {
            "description": "Evidence landscape returned (check `_meta.executedTier` for which tier was used, `hit` for cache status)",
            "model": AgentCheckResponse,
        },
        402: {
            "description": "Insufficient credits or payment required",
            "model": ErrorResponse,
        },
        504: {
            "description": "Pipeline timed out — no charge applied",
            "model": TimeoutErrorResponse,
        },
        502: {
            "description": "Pipeline error — charge refunded if applicable",
            "model": PipelineErrorResponse,
        },
    },
)
@limiter.limit("10/minute")
async def agent_smart_check(
    body: SmartCheckRequest,
    request: Request,
    payment: AgentPaymentContext = Depends(get_agent_payment),
    session: AsyncSession = Depends(get_session),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
) -> JSONResponse:
    """Smart endpoint with automatic tier fallback — recommended for most agent use cases.

    Tries cached lookup first (instant, $0.02). On cache miss, escalates through
    consensus → quick → full up to the tier specified by `max_tier`.
    You're only charged for the tier actually executed.

    **Fallback chain:** lookup → consensus → quick → full

    **Response headers:** `X-Check-Id`, `X-Tru8-Tx-Id`

    **Rate limit:** 10/minute
    """
    from datetime import datetime, timezone

    claim_hash = compute_claim_text_hash(body.claim)
    valid_tiers = ("lookup", "consensus", "quick", "full")
    max_tier = body.max_tier if body.max_tier in valid_tiers else "full"

    # Step 1: Try lookup (same query as /agent/lookup)
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

    if row:
        claim_row, check_row = row

        # Check max_age_hours freshness filter
        cache_valid = True
        if body.max_age_hours and check_row.completed_at:
            age_hours = (
                datetime.now(timezone.utc)
                - check_row.completed_at.replace(tzinfo=timezone.utc)
            ).total_seconds() / 3600
            if age_hours > body.max_age_hours:
                cache_valid = False

        if cache_valid:
            # Cache hit — charge lookup rate and return
            tier = "lookup"
            amount_cents = get_tier_price(tier)
            request_hash = compute_request_hash(tier, claim_hash, body.compact)

            tx = await payment.charge(
                amount_cents=amount_cents,
                tier=tier,
                description=claim_hash,
                idempotency_key=idempotency_key,
                request_hash=request_hash,
                check_id=check_row.id,
            )
            tx.status = "completed"
            await session.flush()

            from app.api.v1.response_builder import build_agent_response

            response_data = await build_agent_response(
                check_id=check_row.id,
                session=session,
                executed_tier="lookup",
                charged_cents=amount_cents,
                limitations=[],
                compact=body.compact,
                cached_from=(
                    check_row.completed_at.isoformat()
                    if check_row.completed_at
                    else None
                ),
            )
            response_data["hit"] = True
            await session.commit()

            return JSONResponse(
                content=response_data,
                headers={
                    "X-Check-Id": check_row.id,
                    "X-Tru8-Tx-Id": tx.id,
                },
            )

    # Step 2: Cache miss (or stale). If max_tier is "lookup", return structured miss.
    if max_tier == "lookup":
        return JSONResponse(
            content={
                "hit": False,
                "nextSuggestedTier": "consensus",
                "upgradeCostCents": get_tier_price("consensus"),
                "claimTextHash": claim_hash,
            }
        )

    # Step 2.5 (M-06): Try consensus if max_tier allows
    from app.core.agent_pricing import tier_rank, TIER_ORDER

    if tier_rank(max_tier) >= tier_rank("consensus"):
        try:
            from app.models.claim_consensus import ClaimConsensus
            from app.services.consensus import (
                build_consensus_response,
                CONSENSUS_MAX_AGE_DAYS,
            )

            consensus = await session.get(ClaimConsensus, claim_hash)
            if consensus and consensus.computed_at:
                age_days = (
                    datetime.now(timezone.utc)
                    - consensus.computed_at.replace(tzinfo=timezone.utc)
                ).days
                if age_days <= CONSENSUS_MAX_AGE_DAYS:
                    # Consensus hit — charge consensus tier
                    tier = "consensus"
                    amount_cents = get_tier_price(tier)
                    request_hash = compute_request_hash(tier, claim_hash, body.compact)

                    tx = await payment.charge(
                        amount_cents=amount_cents,
                        tier=tier,
                        description=claim_hash,
                        idempotency_key=idempotency_key,
                        request_hash=request_hash,
                        check_id=None,
                    )
                    tx.status = "completed"
                    await session.flush()

                    response_data = build_consensus_response(consensus)
                    response_data["hit"] = True
                    await session.commit()

                    return JSONResponse(
                        content=response_data,
                        headers={"X-Tru8-Tx-Id": tx.id},
                    )
        except Exception:
            import logging as _log

            _log.getLogger(__name__).debug(
                "Consensus lookup failed, continuing fallback"
            )

    # Step 2.6: If max_tier is "consensus" and no hit, return structured miss.
    if max_tier == "consensus":
        return JSONResponse(
            content={
                "hit": False,
                "nextSuggestedTier": "quick",
                "upgradeCostCents": get_tier_price("quick"),
                "claimTextHash": claim_hash,
            }
        )

    # Step 3: Escalate to pipeline at resolved tier
    resolved_tier = "quick" if max_tier in ("quick", "full") else max_tier
    if max_tier == "full":
        resolved_tier = "full"

    amount_cents = get_tier_price(resolved_tier)
    request_hash = compute_request_hash(resolved_tier, claim_hash, body.compact)
    limitations = QUICK_LIMITATIONS if resolved_tier == "quick" else []

    return await _run_agent_pipeline(
        body=AgentClaimRequest(
            claim=body.claim, input_type=body.input_type, compact=body.compact
        ),
        tier=resolved_tier,
        amount_cents=amount_cents,
        claim_hash=claim_hash,
        request_hash=request_hash,
        limitations=limitations,
        payment=payment,
        session=session,
        idempotency_key=idempotency_key,
    )


# ---------------------------------------------------------------------------
# POST /agent/lookup — user-scoped claim hash query (L-03)
# ---------------------------------------------------------------------------


@router.post(
    "/lookup",
    summary="Instant cached lookup",
    responses={
        200: {
            "description": "Cache hit (full response with `hit: true`) or cache miss (structured miss with `hit: false`). Both return 200.",
            "model": AgentCheckResponse,
        },
    },
)
@limiter.limit("30/minute")
async def agent_lookup(
    body: AgentClaimRequest,
    request: Request,
    payment: AgentPaymentContext = Depends(get_agent_payment),
    session: AsyncSession = Depends(get_session),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
) -> JSONResponse:
    """Instant cached analysis — $0.02 per hit, no charge on miss.

    Searches for a previous analysis of this claim (scoped to your account).
    Returns 200 in both cases — check the `hit` field to distinguish.

    **Cache hit:** Full evidence landscape with `hit: true`.
    **Cache miss:** `{hit: false, nextSuggestedTier, upgradeCostCents}`.

    **Response headers (hit only):** `X-Check-Id`, `X-Tru8-Tx-Id`

    **Rate limit:** 30/minute
    """
    claim_hash = compute_claim_text_hash(body.claim)
    tier = "lookup"
    amount_cents = get_tier_price(tier)

    # Check idempotency
    request_hash = compute_request_hash(tier, claim_hash, body.compact or False)

    # User-scoped lookup — CRITICAL: only return this user's analyses
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
        # MISS — return 200 structured body, not 404
        return JSONResponse(
            content={
                "hit": False,
                "nextSuggestedTier": "quick",
                "upgradeCostCents": get_tier_price("quick"),
                "claimTextHash": claim_hash,
            }
        )

    # HIT — charge and return cached result
    claim, check = row

    tx = await payment.charge(
        amount_cents=amount_cents,
        tier=tier,
        description=claim_hash,
        idempotency_key=idempotency_key,
        request_hash=request_hash,
        check_id=check.id,
    )

    # Mark transaction completed (lookup is synchronous, no settlement needed)
    tx.status = "completed"
    await session.flush()

    from app.api.v1.response_builder import build_agent_response

    response_data = await build_agent_response(
        check_id=check.id,
        session=session,
        executed_tier=tier,
        charged_cents=amount_cents,
        limitations=[],
        compact=body.compact or False,
        cached_from=check.completed_at.isoformat() if check.completed_at else None,
    )
    response_data["hit"] = True

    await session.commit()

    return JSONResponse(
        content=response_data,
        headers={
            "X-Check-Id": check.id,
            "X-Tru8-Tx-Id": tx.id,
        },
    )


# ---------------------------------------------------------------------------
# Unpaid retrieval — GET /agent/result/{check_id}
# Identity only, no balance check, no charge.
# ---------------------------------------------------------------------------


@router.get(
    "/result/{check_id}",
    summary="Retrieve a completed check result (no charge)",
    responses={
        200: {"description": "Full evidence landscape", "model": AgentCheckResponse},
        404: {
            "description": "Check not found or not owned by this agent",
            "model": ErrorResponse,
        },
        409: {"description": "Check is not yet completed", "model": ErrorResponse},
    },
)
@limiter.limit("30/minute")
async def get_agent_result(
    check_id: str,
    request: Request,
    identity: AgentIdentity = Depends(get_agent_identity),
    session: AsyncSession = Depends(get_session),
) -> JSONResponse:
    """Retrieve a completed check result without re-paying.

    Use this for lost responses, retries, and client reconnection.
    Only returns checks that belong to the authenticated agent.

    **Rate limit:** 30/minute
    """
    result = await session.execute(select(Check).where(Check.id == check_id))
    check = result.scalar_one_or_none()

    if not check or check.user_id != identity.user_id:
        raise HTTPException(status_code=404, detail="Check not found")

    if check.status != "completed":
        raise HTTPException(
            status_code=409,
            detail=f"Check is not completed (status: {check.status})",
        )

    from app.api.v1.response_builder import build_agent_response

    response_data = await build_agent_response(
        check_id=check_id,
        session=session,
        executed_tier="full",
        charged_cents=0,
        limitations=[],
    )

    return JSONResponse(
        content=response_data,
        headers={"X-Check-Id": check_id},
    )


# ---------------------------------------------------------------------------
# Quick mode limitations (L-04) — reported in _meta.limitations
# ---------------------------------------------------------------------------

QUICK_LIMITATIONS = [
    "heuristic_classification",
    "no_factcheck_lookup",
    "no_api_sources",
    "no_llm_relevance_scoring",
    "no_coverage_recovery",
    "no_query_answering",
]


# ---------------------------------------------------------------------------
# POST /agent/quick — reduced pipeline (~15s) (L-04)
# ---------------------------------------------------------------------------


@router.post(
    "/quick",
    summary="Quick evidence research (~15s)",
    responses={
        200: {
            "description": "Evidence landscape (quick tier)",
            "model": AgentCheckResponse,
        },
        402: {
            "description": "Insufficient credits or payment required",
            "model": ErrorResponse,
        },
        504: {
            "description": "Pipeline timed out — no charge applied",
            "model": TimeoutErrorResponse,
        },
        502: {
            "description": "Pipeline error — charge refunded",
            "model": PipelineErrorResponse,
        },
    },
)
@limiter.limit("10/minute")
async def agent_quick(
    body: AgentClaimRequest,
    request: Request,
    payment: AgentPaymentContext = Depends(get_agent_payment),
    session: AsyncSession = Depends(get_session),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
) -> JSONResponse:
    """Reduced pipeline — fewer sources, heuristic classification. ~15 seconds, $0.07.

    Skips: fact-check lookup, government/academic API adapters, LLM relevance
    scoring, coverage recovery, and query answering. Uses heuristic tier/type
    classification instead of LLM.

    Check `_meta.limitations` in the response for the full list of skipped stages.

    **Response headers:** `X-Check-Id`, `X-Tru8-Tx-Id`

    **Rate limit:** 10/minute
    """
    tier = "quick"
    amount_cents = get_tier_price(tier)
    claim_hash = compute_claim_text_hash(body.claim)
    request_hash = compute_request_hash(tier, claim_hash, body.compact or False)

    return await _run_agent_pipeline(
        body=body,
        tier=tier,
        amount_cents=amount_cents,
        claim_hash=claim_hash,
        request_hash=request_hash,
        limitations=QUICK_LIMITATIONS,
        payment=payment,
        session=session,
        idempotency_key=idempotency_key,
    )


# ---------------------------------------------------------------------------
# POST /agent/full — complete pipeline (~60-90s) (L-04)
# ---------------------------------------------------------------------------


@router.post(
    "/full",
    summary="Full evidence research (~60-90s)",
    responses={
        200: {
            "description": "Complete evidence landscape (full tier)",
            "model": AgentCheckResponse,
        },
        402: {
            "description": "Insufficient credits or payment required",
            "model": ErrorResponse,
        },
        504: {
            "description": "Pipeline timed out — no charge applied",
            "model": TimeoutErrorResponse,
        },
        502: {
            "description": "Pipeline error — charge refunded",
            "model": PipelineErrorResponse,
        },
    },
)
@limiter.limit("10/minute")
async def agent_full(
    body: AgentClaimRequest,
    request: Request,
    payment: AgentPaymentContext = Depends(get_agent_payment),
    session: AsyncSession = Depends(get_session),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
) -> JSONResponse:
    """Complete evidence research pipeline — 30+ sources, all stages. ~60-90 seconds, $0.15.

    Runs the full pipeline: fact-check lookup, 30+ source providers (government,
    academic, news, data APIs), LLM classification, coverage recovery, and
    query answering. Set your HTTP client timeout to at least 180 seconds.

    **Response headers:** `X-Check-Id`, `X-Tru8-Tx-Id`

    **Rate limit:** 10/minute
    """
    tier = "full"
    amount_cents = get_tier_price(tier)
    claim_hash = compute_claim_text_hash(body.claim)
    request_hash = compute_request_hash(tier, claim_hash, body.compact or False)

    return await _run_agent_pipeline(
        body=body,
        tier=tier,
        amount_cents=amount_cents,
        claim_hash=claim_hash,
        request_hash=request_hash,
        limitations=[],
        payment=payment,
        session=session,
        idempotency_key=idempotency_key,
    )


# ---------------------------------------------------------------------------
# Shared pipeline runner for /quick and /full (L-04)
# ---------------------------------------------------------------------------


async def _run_agent_pipeline(
    *,
    body: AgentClaimRequest,
    tier: str,
    amount_cents: int,
    claim_hash: str,
    request_hash: str,
    limitations: list,
    payment: AgentPaymentContext,
    session: AsyncSession,
    idempotency_key: Optional[str],
) -> JSONResponse:
    """Create check, charge, run pipeline, return response with _meta."""
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

    # Fail fast if Skyfire token won't live long enough for this tier
    if payment.provider == "skyfire" and payment.token_exp:
        from app.services.payments.skyfire_provider import SkyfirePaymentProvider

        try:
            SkyfirePaymentProvider().validate_expiry_headroom(
                {"exp": payment.token_exp}, tier
            )
        except ValueError as e:
            raise HTTPException(status_code=402, detail=str(e))

    # Charge upfront — transaction starts as "pending"
    tx = await payment.charge(
        amount_cents=amount_cents,
        tier=tier,
        description=claim_hash,
        idempotency_key=idempotency_key,
        request_hash=request_hash,
    )

    # Resolve input type (auto-detect URL from claim text)
    resolved_type, input_data = _resolve_input(body.claim, body.input_type)

    # Create check record
    check = Check(
        id=str(uuid.uuid4()),
        user_id=payment.user_id,
        input_type=resolved_type,
        input_content=json.dumps(input_data),
        input_url=input_data.get("url"),
        status="processing",
        credits_used=0,  # Agent checks don't use dashboard credits
        initiated_via=f"agent_{payment.provider}",
        executed_tier=tier,  # M-03: record pipeline tier at creation
    )
    session.add(check)
    await session.commit()
    await session.refresh(check)

    # Link transaction to check
    tx.check_id = check.id
    await session.commit()

    progress_reporter = ProgressReporter(check.id)

    try:
        result = await asyncio.wait_for(
            run_pipeline(
                check.id,
                payment.user_id,
                input_data,
                progress_reporter,
                config=config,
            ),
            timeout=config.max_wall_time_seconds,
        )

        # Article mode auto-select (URL inputs trigger this; text inputs shouldn't)
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
                max_selected = 5
                for i, claim in enumerate(ranked):
                    claim.is_selected = i < max_selected

                sel_check_stmt = select(Check).where(Check.id == check.id)
                sel_check_result = await sel_session.execute(sel_check_stmt)
                sel_check = sel_check_result.scalar_one()
                sel_check.selected_claims_count = min(len(ranked), max_selected)
                await sel_session.commit()

            phase2_input = input_data
            phase2_reporter = ProgressReporter(check.id)
            result = await asyncio.wait_for(
                run_pipeline_phase2(
                    check_id=check.id,
                    user_id=payment.user_id,
                    input_data=phase2_input,
                    progress_reporter=phase2_reporter,
                    config=config,
                ),
                timeout=config.max_wall_time_seconds,
            )

        # Save results
        async with async_session() as save_session:
            await save_check_results_async(check.id, result, save_session)
            await save_session.commit()

        # Mark transaction completed + attach pipeline metrics (L-12)
        tx.status = "completed"
        pipeline_metrics = result.get("pipeline_metrics")
        if pipeline_metrics and tx.tx_metadata:
            tx.tx_metadata["metrics"] = pipeline_metrics
        elif pipeline_metrics:
            tx.tx_metadata = {"metrics": pipeline_metrics}
        await session.commit()

        # Build response (fresh session for committed data)
        from app.api.v1.response_builder import build_agent_response

        async with async_session() as resp_session:
            response_data = await build_agent_response(
                check_id=check.id,
                session=resp_session,
                executed_tier=tier,
                charged_cents=amount_cents,
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
        logger.error(f"[AGENT {tier.upper()}] Pipeline timed out for check {check.id}")
        await _refund_and_fail_tx(tx, payment, amount_cents, session)
        await handle_pipeline_failure(
            check.id, payment.user_id, Exception("Pipeline timed out")
        )
        raise HTTPException(
            status_code=504,
            detail="Pipeline timed out. No charge applied.",
        )

    except PipelineError as e:
        logger.error(f"[AGENT {tier.upper()}] Pipeline error for check {check.id}: {e}")
        await _refund_and_fail_tx(tx, payment, amount_cents, session)
        await handle_pipeline_failure(check.id, payment.user_id, e)
        raise HTTPException(status_code=502, detail=f"Pipeline error: {e}")

    except HTTPException:
        raise

    except Exception as e:
        logger.error(
            f"[AGENT {tier.upper()}] Unexpected error for check {check.id}: {e}"
        )
        await _refund_and_fail_tx(tx, payment, amount_cents, session)
        await handle_pipeline_failure(check.id, payment.user_id, e)
        raise HTTPException(status_code=502, detail=f"Pipeline error: {e}")


async def _refund_and_fail_tx(
    tx: "AgentTransaction",
    payment: AgentPaymentContext,
    amount_cents: int,
    session: AsyncSession,
) -> None:
    """Refund credits and mark transaction as refunded/failed."""
    if payment.provider == "credit":
        from app.services.payments.credit_provider import refund_credits

        await refund_credits(payment.user_id, amount_cents, session)
        tx.status = "refunded"
    else:
        tx.status = "failed"
    await session.commit()


# ---------------------------------------------------------------------------
# GET /agent/credits/balance — check prepaid balance (L-07)
# ---------------------------------------------------------------------------


@router.get(
    "/credits/balance",
    summary="Check prepaid credit balance",
    responses={
        200: {"description": "Current credit balance", "model": CreditBalanceResponse},
    },
)
@limiter.limit("60/minute")
async def get_credit_balance(
    request: Request,
    identity: AgentIdentity = Depends(get_agent_identity),
    session: AsyncSession = Depends(get_session),
) -> JSONResponse:
    """Return the agent's prepaid credit balance in cents and USD.

    **Rate limit:** 60/minute
    """
    from app.models.user import User

    result = await session.execute(select(User).where(User.id == identity.user_id))
    user = result.scalar_one_or_none()

    balance = user.credit_balance_cents if user else 0
    return JSONResponse(
        content={
            "balanceCents": balance,
            "balanceUsd": f"{balance / 100:.2f}",
        }
    )


# ---------------------------------------------------------------------------
# POST /agent/credits/purchase — Stripe Checkout for credit packs (L-07)
# ---------------------------------------------------------------------------


class CreditPurchaseRequest(BaseModel):
    """Purchase a prepaid credit pack via Stripe Checkout."""

    pack: str = Field(
        description="Credit pack size: '5' ($5.00), '20' ($20.00), or '100' ($100.00)"
    )


@router.post(
    "/credits/purchase",
    summary="Purchase credit pack via Stripe",
    responses={
        200: {
            "description": "Stripe Checkout session URL",
            "model": CheckoutSessionResponse,
        },
        400: {"description": "Invalid pack size", "model": ErrorResponse},
        503: {"description": "Credit packs not yet configured", "model": ErrorResponse},
    },
)
@limiter.limit("10/minute")
async def purchase_credits(
    body: CreditPurchaseRequest,
    request: Request,
    identity: AgentIdentity = Depends(get_agent_identity),
    session: AsyncSession = Depends(get_session),
) -> JSONResponse:
    """Create a Stripe Checkout session for a one-time credit pack purchase.

    Returns a redirect URL — send the user or agent operator to this URL
    to complete payment. Credits are added to the account automatically
    after successful payment.

    **Available packs:** 5, 20, or 100 (in USD).

    **Rate limit:** 10/minute
    """
    import stripe
    from app.core.config import settings
    from app.models.user import User

    pack_map = {
        "5": (settings.STRIPE_PRICE_ID_CREDIT_PACK_5, 500),
        "20": (settings.STRIPE_PRICE_ID_CREDIT_PACK_20, 2000),
        "100": (settings.STRIPE_PRICE_ID_CREDIT_PACK_100, 10000),
    }

    if body.pack not in pack_map:
        raise HTTPException(
            status_code=400, detail="Invalid pack. Choose 5, 20, or 100."
        )

    price_id, cents_value = pack_map[body.pack]
    if not price_id:
        raise HTTPException(
            status_code=503,
            detail="Credit packs not yet configured. Contact support.",
        )

    # Get user email for Stripe
    result = await session.execute(select(User).where(User.id == identity.user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    stripe.api_key = settings.STRIPE_SECRET_KEY

    try:
        checkout_session = stripe.checkout.Session.create(
            customer_email=user.email,
            client_reference_id=user.id,
            line_items=[{"price": price_id, "quantity": 1}],
            mode="payment",
            success_url=f"{settings.FRONTEND_URL}/developers?credits=purchased",
            cancel_url=f"{settings.FRONTEND_URL}/developers?credits=cancelled",
            metadata={
                "user_id": user.id,
                "credit_pack": body.pack,
                "cents_value": str(cents_value),
                "purchase_type": "agent_credits",
            },
        )
        return JSONResponse(
            content={
                "sessionId": checkout_session.id,
                "url": checkout_session.url,
            }
        )
    except Exception as e:
        logger.error(f"Stripe error creating credit checkout: {e}")
        raise HTTPException(status_code=500, detail="Failed to create checkout session")


# ---------------------------------------------------------------------------
# GET /agent/stats — aggregated usage by tier, provider, time period (L-10)
# ---------------------------------------------------------------------------


@router.get(
    "/stats",
    summary="Get agent usage statistics",
    responses={
        200: {
            "description": "Aggregated usage statistics",
            "model": AgentStatsResponse,
        },
    },
)
@limiter.limit("30/minute")
async def get_agent_stats(
    request: Request,
    identity: AgentIdentity = Depends(get_agent_identity),
    session: AsyncSession = Depends(get_session),
) -> JSONResponse:
    """Aggregated usage statistics — broken down by pipeline tier and payment provider.

    **Rate limit:** 30/minute
    """
    from sqlalchemy import func, case
    from app.models.agent_transaction import AgentTransaction

    # Aggregate by tier
    tier_stats_result = await session.execute(
        select(
            AgentTransaction.tier,
            func.count(AgentTransaction.id).label("count"),
            func.sum(AgentTransaction.amount_cents).label("total_cents"),
        )
        .where(
            AgentTransaction.payer_id == identity.user_id,
            AgentTransaction.status.in_(["completed", "refunded"]),
        )
        .group_by(AgentTransaction.tier)
    )
    tier_rows = tier_stats_result.all()

    by_tier = {}
    for tier, count, total_cents in tier_rows:
        by_tier[tier] = {"count": count, "totalCents": total_cents or 0}

    # Aggregate by provider
    provider_stats_result = await session.execute(
        select(
            AgentTransaction.provider,
            func.count(AgentTransaction.id).label("count"),
        )
        .where(
            AgentTransaction.payer_id == identity.user_id,
            AgentTransaction.status.in_(["completed", "refunded"]),
        )
        .group_by(AgentTransaction.provider)
    )
    provider_rows = provider_stats_result.all()

    by_provider = {}
    for provider, count in provider_rows:
        by_provider[provider] = {"count": count}

    # Total checks initiated via agent
    total_checks_result = await session.execute(
        select(func.count(Check.id)).where(
            Check.user_id == identity.user_id,
            Check.initiated_via.like("agent_%"),
        )
    )
    total_agent_checks = total_checks_result.scalar() or 0

    return JSONResponse(
        content={
            "byTier": by_tier,
            "byProvider": by_provider,
            "totalAgentChecks": total_agent_checks,
        }
    )
