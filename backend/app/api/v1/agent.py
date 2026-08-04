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
from app.core.client_origin import resolve_client
from app.core.config import settings
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
        max_length=10_000,
        description="The claim text to analyse, or a URL to extract claims from",
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
        max_length=10_000,
        description="The claim text to analyse, or a URL to extract claims from",
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


class BatchClaimItem(BaseModel):
    """A single claim within a batch request."""

    claim: str = Field(
        max_length=10_000, description="The claim text to analyse, or a URL"
    )
    input_type: Optional[str] = Field(
        None, description="'text' or 'url'. Auto-detected if omitted."
    )


class BatchRequest(BaseModel):
    """Submit multiple claims for concurrent processing."""

    claims: list[BatchClaimItem] = Field(
        description="List of claims to process (max 10)",
        min_length=1,
        max_length=10,
    )
    tier: str = Field(
        "quick",
        description="Pipeline tier for all claims: 'quick' or 'full'.",
    )
    compact: bool = Field(
        False,
        description="If true, compact responses for all claims.",
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

    Tries cached lookup first (instant, £0.02). On cache miss, escalates through
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
            amount_pence = get_tier_price(tier)
            request_hash = compute_request_hash(tier, claim_hash, body.compact)

            tx = await payment.charge(
                amount_pence=amount_pence,
                tier=tier,
                description=claim_hash,
                idempotency_key=idempotency_key,
                request_hash=request_hash,
                check_id=check_row.id,
            )

            from app.api.v1.response_builder import build_agent_response

            try:
                response_data = await build_agent_response(
                    check_id=check_row.id,
                    session=session,
                    executed_tier="lookup",
                    charged_pence=amount_pence,
                    limitations=[],
                    compact=body.compact,
                    cached_from=(
                        check_row.completed_at.isoformat()
                        if check_row.completed_at
                        else None
                    ),
                )
            except Exception:
                await _refund_and_fail_tx(tx, payment, amount_pence, session)
                raise HTTPException(
                    status_code=502,
                    detail="Response building failed. Credits have been refunded.",
                )

            response_data["hit"] = True
            tx.status = "completed"
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
                "upgradeCostPence": get_tier_price("consensus"),
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
                # Check both server-side max age and caller's freshness constraint (O-02)
                consensus_fresh = age_days <= CONSENSUS_MAX_AGE_DAYS
                if consensus_fresh and body.max_age_hours:
                    age_hours = (
                        datetime.now(timezone.utc)
                        - consensus.computed_at.replace(tzinfo=timezone.utc)
                    ).total_seconds() / 3600
                    if age_hours > body.max_age_hours:
                        consensus_fresh = False
                        logger.debug(
                            "Consensus stale for max_age_hours=%s (age=%.1fh)",
                            body.max_age_hours,
                            age_hours,
                        )

                if consensus_fresh:
                    # Consensus hit — charge consensus tier
                    tier = "consensus"
                    amount_pence = get_tier_price(tier)
                    request_hash = compute_request_hash(tier, claim_hash, body.compact)

                    tx = await payment.charge(
                        amount_pence=amount_pence,
                        tier=tier,
                        description=claim_hash,
                        idempotency_key=idempotency_key,
                        request_hash=request_hash,
                        check_id=None,
                    )

                    response_data = build_consensus_response(consensus)
                    response_data["hit"] = True
                    tx.status = "completed"
                    await session.commit()

                    return JSONResponse(
                        content=response_data,
                        headers={"X-Tru8-Tx-Id": tx.id},
                    )
        except Exception:
            # ROLLBACK IS NOT OPTIONAL HERE.
            #
            # This handler used to swallow the failure at DEBUG and fall
            # through with no rollback. Postgres marks a transaction aborted
            # after any failed statement, so the session was already poisoned:
            # the NEXT write — the credit debit — died with
            # InFailedSQLTransactionError and the caller got a 500 whose Sentry
            # trace pointed squarely at billing code that had done nothing
            # wrong. The real cause (claim_consensus did not exist) was
            # invisible because it was logged at DEBUG.
            #
            # Rolling back returns the session to a usable state so a consensus
            # problem costs the caller a cache miss instead of their request.
            await session.rollback()

            # WARNING, not DEBUG. Consensus is an optimisation; failing it is
            # survivable but never normal, and the whole point of the incident
            # above is that nobody could see it happening.
            logger.warning(
                "Consensus lookup failed, continuing without it", exc_info=True
            )

    # Step 2.6: If max_tier is "consensus" and no hit, return structured miss.
    if max_tier == "consensus":
        return JSONResponse(
            content={
                "hit": False,
                "nextSuggestedTier": "quick",
                "upgradeCostPence": get_tier_price("quick"),
                "claimTextHash": claim_hash,
            }
        )

    # Step 3: Escalate to pipeline at resolved tier
    resolved_tier = "quick" if max_tier in ("quick", "full") else max_tier
    if max_tier == "full":
        resolved_tier = "full"

    amount_pence = get_tier_price(resolved_tier)
    request_hash = compute_request_hash(resolved_tier, claim_hash, body.compact)
    limitations = QUICK_LIMITATIONS if resolved_tier == "quick" else []

    return await _run_agent_pipeline(
        body=AgentClaimRequest(
            claim=body.claim, input_type=body.input_type, compact=body.compact
        ),
        tier=resolved_tier,
        amount_pence=amount_pence,
        claim_hash=claim_hash,
        request_hash=request_hash,
        limitations=limitations,
        payment=payment,
        session=session,
        idempotency_key=idempotency_key,
        client=resolve_client(request),
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
    """Instant cached analysis — £0.02 per hit, no charge on miss.

    Searches for a previous analysis of this claim (scoped to your account).
    Returns 200 in both cases — check the `hit` field to distinguish.

    **Cache hit:** Full evidence landscape with `hit: true`.
    **Cache miss:** `{hit: false, nextSuggestedTier, upgradeCostPence}`.

    **Response headers (hit only):** `X-Check-Id`, `X-Tru8-Tx-Id`

    **Rate limit:** 30/minute
    """
    claim_hash = compute_claim_text_hash(body.claim)
    tier = "lookup"
    amount_pence = get_tier_price(tier)

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
                "upgradeCostPence": get_tier_price("quick"),
                "claimTextHash": claim_hash,
            }
        )

    # HIT — charge and return cached result
    claim, check = row

    tx = await payment.charge(
        amount_pence=amount_pence,
        tier=tier,
        description=claim_hash,
        idempotency_key=idempotency_key,
        request_hash=request_hash,
        check_id=check.id,
    )

    from app.api.v1.response_builder import build_agent_response

    try:
        response_data = await build_agent_response(
            check_id=check.id,
            session=session,
            executed_tier=tier,
            charged_pence=amount_pence,
            limitations=[],
            compact=body.compact or False,
            cached_from=check.completed_at.isoformat() if check.completed_at else None,
        )
    except Exception:
        await _refund_and_fail_tx(tx, payment, amount_pence, session)
        raise HTTPException(
            status_code=502,
            detail="Response building failed. Credits have been refunded.",
        )

    response_data["hit"] = True
    tx.status = "completed"
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
        # Return processing status instead of error — enables async polling (O-06)
        return JSONResponse(
            status_code=200,
            content={
                "checkId": check_id,
                "status": check.status,
                "hit": False,
            },
            headers={"X-Check-Id": check_id},
        )

    from app.api.v1.response_builder import build_agent_response

    response_data = await build_agent_response(
        check_id=check_id,
        session=session,
        executed_tier="full",
        charged_pence=0,
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
    async_mode: bool = Query(False, alias="async"),
    payment: AgentPaymentContext = Depends(get_agent_payment),
    session: AsyncSession = Depends(get_session),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
) -> JSONResponse:
    """Reduced pipeline — fewer sources, heuristic classification. ~15 seconds, £0.07.

    Skips: fact-check lookup, government/academic API adapters, LLM relevance
    scoring, coverage recovery, and query answering. Uses heuristic tier/type
    classification instead of LLM.

    Check `_meta.limitations` in the response for the full list of skipped stages.

    Set `?async=true` to receive a 202 Accepted immediately and poll
    `/agent/result/{checkId}` for the completed result.

    **Response headers:** `X-Check-Id`, `X-Tru8-Tx-Id`

    **Rate limit:** 10/minute
    """
    tier = "quick"
    amount_pence = get_tier_price(tier)
    claim_hash = compute_claim_text_hash(body.claim)
    request_hash = compute_request_hash(tier, claim_hash, body.compact or False)

    return await _run_agent_pipeline(
        body=body,
        tier=tier,
        amount_pence=amount_pence,
        claim_hash=claim_hash,
        request_hash=request_hash,
        limitations=QUICK_LIMITATIONS,
        payment=payment,
        session=session,
        idempotency_key=idempotency_key,
        async_mode=async_mode,
        client=resolve_client(request),
    )


# ---------------------------------------------------------------------------
# POST /agent/full — complete pipeline (~50-70s) (L-04)
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
@limiter.limit("5/minute")
async def agent_full(
    body: AgentClaimRequest,
    request: Request,
    async_mode: bool = Query(False, alias="async"),
    payment: AgentPaymentContext = Depends(get_agent_payment),
    session: AsyncSession = Depends(get_session),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
) -> JSONResponse:
    """Complete evidence research pipeline — web + specialist APIs, all stages. ~50-70 seconds, £0.15.

    Runs the full pipeline: fact-check lookup, web search and specialist providers (government,
    academic, news, data APIs), LLM classification, coverage recovery, and
    query answering. Set your HTTP client timeout to at least 180 seconds.

    Set `?async=true` to receive a 202 Accepted immediately and poll
    `/agent/result/{checkId}` for the completed result.

    **Response headers:** `X-Check-Id`, `X-Tru8-Tx-Id`

    **Rate limit:** 10/minute
    """
    tier = "full"
    amount_pence = get_tier_price(tier)
    claim_hash = compute_claim_text_hash(body.claim)
    request_hash = compute_request_hash(tier, claim_hash, body.compact or False)

    return await _run_agent_pipeline(
        body=body,
        tier=tier,
        amount_pence=amount_pence,
        claim_hash=claim_hash,
        request_hash=request_hash,
        limitations=[],
        payment=payment,
        session=session,
        idempotency_key=idempotency_key,
        async_mode=async_mode,
        client=resolve_client(request),
    )


# ---------------------------------------------------------------------------
# Shared pipeline runner for /quick and /full (L-04)
# ---------------------------------------------------------------------------


# Strong refs for fire-and-forget tasks so they aren't garbage-collected
# mid-flight (same pattern as checks.py).
_background_tasks: set = set()


def _launch_archiving(check_id: str) -> None:
    """Fire-and-forget Wayback archiving for a completed agent check.

    F10 parity with the dashboard pipeline path — without this, agent-submitted
    checks never get archived_url populated.
    """
    try:
        from app.services.wayback_archive import archive_evidence_urls

        task = asyncio.create_task(archive_evidence_urls(check_id))
        _background_tasks.add(task)
        task.add_done_callback(_background_tasks.discard)
        logger.info(f"[AGENT] Archive task launched for check {check_id}")
    except Exception as exc:
        logger.debug(f"[AGENT] Archiving skipped for {check_id}: {exc}")


async def _run_agent_pipeline(
    *,
    body: AgentClaimRequest,
    tier: str,
    amount_pence: int,
    claim_hash: str,
    request_hash: str,
    limitations: list,
    payment: AgentPaymentContext,
    session: AsyncSession,
    idempotency_key: Optional[str],
    async_mode: bool = False,
    client: Optional[str] = None,
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
        amount_pence=amount_pence,
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
        client=client,  # first-party client attribution (e.g. "mcp")
        executed_tier=tier,  # M-03: record pipeline tier at creation
    )
    session.add(check)
    await session.commit()
    await session.refresh(check)

    # Link transaction to check
    tx.check_id = check.id
    await session.commit()

    # --- Async mode: launch pipeline in background, return 202 immediately ---
    if async_mode:
        asyncio.create_task(
            _run_pipeline_background(
                check_id=check.id,
                user_id=payment.user_id,
                input_data=input_data,
                config=config,
                tier=tier,
                tx_id=tx.id,
                provider=payment.provider,
                amount_pence=amount_pence,
            )
        )
        estimated = 15 if tier == "quick" else 60
        return JSONResponse(
            status_code=202,
            content={
                "checkId": check.id,
                "status": "processing",
                "tier": tier,
                "chargedPence": amount_pence,
                "txId": tx.id,
                "pollUrl": f"/api/v1/agent/result/{check.id}",
                "estimatedSeconds": estimated,
            },
            headers={
                "X-Check-Id": check.id,
                "X-Tru8-Tx-Id": tx.id,
            },
        )

    # --- Synchronous mode: run pipeline inline, return full result ---
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
                max_selected = settings.MAX_SELECTED_CLAIMS
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

        # Fire-and-forget URL archiving (F10)
        _launch_archiving(check.id)

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
                charged_pence=amount_pence,
                limitations=limitations,
                compact=body.compact or False,
            )

        # Fire webhook: check.completed (O-01)
        try:
            from app.services.webhooks import dispatch_webhook_event

            asyncio.create_task(
                dispatch_webhook_event(
                    payment.user_id,
                    "check.completed",
                    {"checkId": check.id, "status": "completed", "tier": tier},
                )
            )
        except Exception:
            pass  # best-effort

        return JSONResponse(
            content=response_data,
            headers={
                "X-Check-Id": check.id,
                "X-Tru8-Tx-Id": tx.id,
            },
        )

    except asyncio.TimeoutError:
        logger.error(f"[AGENT {tier.upper()}] Pipeline timed out for check {check.id}")
        await _refund_and_fail_tx(tx, payment, amount_pence, session)
        await handle_pipeline_failure(
            check.id, payment.user_id, Exception("Pipeline timed out")
        )
        _fire_agent_webhook_failed(payment.user_id, check.id, "Pipeline timed out")
        raise HTTPException(
            status_code=504,
            detail="Pipeline timed out. Credits have been refunded.",
        )

    except PipelineError as e:
        logger.error(f"[AGENT {tier.upper()}] Pipeline error for check {check.id}: {e}")
        await _refund_and_fail_tx(tx, payment, amount_pence, session)
        await handle_pipeline_failure(check.id, payment.user_id, e)
        _fire_agent_webhook_failed(payment.user_id, check.id, str(e))
        raise HTTPException(status_code=502, detail=f"Pipeline error: {e}")

    except HTTPException:
        raise

    except Exception as e:
        logger.error(
            f"[AGENT {tier.upper()}] Unexpected error for check {check.id}: {e}"
        )
        await _refund_and_fail_tx(tx, payment, amount_pence, session)
        await handle_pipeline_failure(check.id, payment.user_id, e)
        _fire_agent_webhook_failed(payment.user_id, check.id, str(e))
        raise HTTPException(status_code=502, detail=f"Pipeline error: {e}")


async def _refund_and_fail_tx(
    tx: "AgentTransaction",
    payment: AgentPaymentContext,
    amount_pence: int,
    session: AsyncSession,
) -> None:
    """Refund credits and mark transaction as refunded/failed."""
    if payment.provider == "credit":
        from app.services.payments.credit_provider import refund_credits

        await refund_credits(payment.user_id, amount_pence, session)
        tx.status = "refunded"
    else:
        tx.status = "failed"
    await session.commit()


def _fire_agent_webhook_failed(user_id: str, check_id: str, error_msg: str) -> None:
    """Best-effort webhook dispatch for agent check failures (O-01)."""
    try:
        from app.services.webhooks import dispatch_webhook_event

        asyncio.create_task(
            dispatch_webhook_event(
                user_id,
                "check.failed",
                {"checkId": check_id, "status": "failed", "error": error_msg},
            )
        )
    except Exception:
        pass


async def _run_pipeline_background(
    *,
    check_id: str,
    user_id: str,
    input_data: dict,
    config,
    tier: str,
    tx_id: str,
    provider: str,
    amount_pence: int,
) -> None:
    """Background pipeline execution for async mode (O-06).

    Runs the full pipeline, saves results, updates the transaction,
    and fires webhooks. On failure, refunds credits and marks tx failed.
    Uses its own DB sessions since the request session is closed.
    """
    from app.core.database import async_session
    from app.pipeline.progress import ProgressReporter
    from app.pipeline.runner import (
        PipelineError,
        handle_pipeline_failure,
        run_pipeline,
        run_pipeline_phase2,
        save_check_results_async,
    )

    progress_reporter = ProgressReporter(check_id)

    try:
        result = await asyncio.wait_for(
            run_pipeline(
                check_id,
                user_id,
                input_data,
                progress_reporter,
                config=config,
            ),
            timeout=config.max_wall_time_seconds,
        )

        # Article mode auto-select
        if result is None:
            async with async_session() as sel_session:
                claims_stmt = (
                    select(Claim)
                    .where(Claim.check_id == check_id)
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
                max_selected = settings.MAX_SELECTED_CLAIMS
                for i, claim in enumerate(ranked):
                    claim.is_selected = i < max_selected

                sel_check_stmt = select(Check).where(Check.id == check_id)
                sel_check_result = await sel_session.execute(sel_check_stmt)
                sel_check = sel_check_result.scalar_one()
                sel_check.selected_claims_count = min(len(ranked), max_selected)
                await sel_session.commit()

            phase2_reporter = ProgressReporter(check_id)
            result = await asyncio.wait_for(
                run_pipeline_phase2(
                    check_id=check_id,
                    user_id=user_id,
                    input_data=input_data,
                    progress_reporter=phase2_reporter,
                    config=config,
                ),
                timeout=config.max_wall_time_seconds,
            )

        # Save results
        async with async_session() as save_session:
            await save_check_results_async(check_id, result, save_session)
            await save_session.commit()

        # Fire-and-forget URL archiving (F10)
        _launch_archiving(check_id)

        # Mark transaction completed
        async with async_session() as tx_session:
            from app.models.agent_transaction import AgentTransaction

            tx_result = await tx_session.execute(
                select(AgentTransaction).where(AgentTransaction.id == tx_id)
            )
            tx = tx_result.scalar_one()
            tx.status = "completed"
            pipeline_metrics = result.get("pipeline_metrics")
            if pipeline_metrics and tx.tx_metadata:
                tx.tx_metadata["metrics"] = pipeline_metrics
            elif pipeline_metrics:
                tx.tx_metadata = {"metrics": pipeline_metrics}
            await tx_session.commit()

        # Fire webhook: check.completed
        _fire_agent_webhook_completed(user_id, check_id, tier)
        logger.info(f"[AGENT ASYNC] {tier.upper()} completed for check {check_id}")

    except (asyncio.TimeoutError, PipelineError, Exception) as e:
        error_msg = (
            "Pipeline timed out" if isinstance(e, asyncio.TimeoutError) else str(e)
        )
        logger.error(
            f"[AGENT ASYNC] {tier.upper()} failed for check {check_id}: {error_msg}"
        )

        # Refund + mark tx failed
        async with async_session() as fail_session:
            from app.models.agent_transaction import AgentTransaction

            tx_result = await fail_session.execute(
                select(AgentTransaction).where(AgentTransaction.id == tx_id)
            )
            tx = tx_result.scalar_one()
            if provider == "credit":
                from app.services.payments.credit_provider import refund_credits

                await refund_credits(user_id, amount_pence, fail_session)
                tx.status = "refunded"
            else:
                tx.status = "failed"
            await fail_session.commit()

        await handle_pipeline_failure(check_id, user_id, e)
        _fire_agent_webhook_failed(user_id, check_id, error_msg)


def _fire_agent_webhook_completed(user_id: str, check_id: str, tier: str) -> None:
    """Best-effort webhook dispatch for async pipeline completion."""
    try:
        from app.services.webhooks import dispatch_webhook_event

        asyncio.create_task(
            dispatch_webhook_event(
                user_id,
                "check.completed",
                {"checkId": check_id, "status": "completed", "tier": tier},
            )
        )
    except Exception:
        pass


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
    """Return the agent's prepaid credit balance in pence and GBP.

    **Rate limit:** 60/minute
    """
    from app.models.user import User

    result = await session.execute(select(User).where(User.id == identity.user_id))
    user = result.scalar_one_or_none()

    balance = user.credit_balance_pence if user else 0
    return JSONResponse(
        content={
            "balancePence": balance,
            "balanceGbp": f"£{balance / 100:.2f}",
        }
    )


# ---------------------------------------------------------------------------
# POST /agent/credits/purchase — Stripe Checkout for credit packs (L-07)
# ---------------------------------------------------------------------------


class CreditPurchaseRequest(BaseModel):
    """Purchase a prepaid credit pack via Stripe Checkout."""

    pack: str = Field(description="Credit pack size: '20' (£3.00) or '100' (£15.00)")


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

    **Available packs:** 20 or 100 (in GBP).

    **Rate limit:** 10/minute
    """
    import stripe
    from app.core.config import settings
    from app.models.user import User

    pack_map = {
        "20": (settings.STRIPE_PRICE_ID_CREDIT_PACK_20, 300),
        "100": (settings.STRIPE_PRICE_ID_CREDIT_PACK_100, 1500),
    }

    if body.pack not in pack_map:
        raise HTTPException(status_code=400, detail="Invalid pack. Choose 20 or 100.")

    price_id, pence_value = pack_map[body.pack]
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
                "pence_value": str(pence_value),
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
            func.sum(AgentTransaction.amount_pence).label("total_pence"),
        )
        .where(
            AgentTransaction.payer_id == identity.user_id,
            AgentTransaction.status.in_(["completed", "refunded"]),
        )
        .group_by(AgentTransaction.tier)
    )
    tier_rows = tier_stats_result.all()

    by_tier = {}
    for tier, count, total_pence in tier_rows:
        by_tier[tier] = {"count": count, "totalPence": total_pence or 0}

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


# ---------------------------------------------------------------------------
# Operational endpoints (O-04)
# ---------------------------------------------------------------------------


@router.get(
    "/health",
    summary="Agent API health check",
    responses={200: {"description": "API and dependency status"}},
)
@limiter.limit("60/minute")
async def agent_health(request: Request) -> JSONResponse:
    """Check agent API availability and dependency health. No auth required.

    **Rate limit:** 60/minute
    """
    from datetime import datetime, timezone

    import redis as _redis

    from app.core.config import settings
    from app.core.database import engine as async_engine

    services = {}

    # Database
    try:
        async with async_engine.connect() as conn:
            await conn.execute(select(1))
        services["database"] = "ok"
    except Exception:
        services["database"] = "unavailable"

    # Redis
    try:
        r = _redis.from_url(settings.REDIS_URL, decode_responses=True)
        r.ping()
        services["redis"] = "ok"
        r.close()
    except Exception:
        services["redis"] = "unavailable"

    overall = "ok" if all(v == "ok" for v in services.values()) else "degraded"

    return JSONResponse(
        content={
            "status": overall,
            "services": services,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    )


@router.get(
    "/tiers",
    summary="List available agent tiers and pricing",
    responses={200: {"description": "Tier pricing and estimated latency"}},
)
@limiter.limit("60/minute")
async def agent_tiers(request: Request) -> JSONResponse:
    """Return agent tier names, pricing (pence), and estimated latency. No auth required.

    **Rate limit:** 60/minute
    """
    from app.core.agent_pricing import AGENT_PRICING_PENCE, TIER_ORDER

    tier_descriptions = {
        "lookup": ("Cached prior analysis", 0),
        "consensus": ("Cross-user aggregate landscape (k>=3 checks)", 0),
        "quick": ("Web search + heuristic classification", 15),
        "full": ("web + specialist APIs, LLM classification, coverage recovery", 60),
    }

    tiers = []
    for name in TIER_ORDER:
        desc, est_seconds = tier_descriptions.get(name, (name, 0))
        tiers.append(
            {
                "name": name,
                "costPence": AGENT_PRICING_PENCE[name],
                "estimatedSeconds": est_seconds,
                "description": desc,
            }
        )

    return JSONResponse(content={"tiers": tiers})


@router.get(
    "/me",
    summary="Get authenticated agent identity",
    responses={200: {"description": "Agent identity and credit balance"}},
)
@limiter.limit("60/minute")
async def agent_me(
    request: Request,
    identity: AgentIdentity = Depends(get_agent_identity),
    session: AsyncSession = Depends(get_session),
) -> JSONResponse:
    """Return the authenticated agent's identity and credit balance. Requires auth.

    **Rate limit:** 60/minute
    """
    from app.models.user import User

    credit_balance_pence = 0
    user = await session.get(User, identity.user_id)
    if user:
        credit_balance_pence = max((user.credit_balance_pence or 0), 0)

    return JSONResponse(
        content={
            "userId": identity.user_id,
            "provider": identity.provider,
            "creditBalancePence": credit_balance_pence,
        }
    )


# ---------------------------------------------------------------------------
# POST /agent/batch — submit multiple claims concurrently (O-08)
# ---------------------------------------------------------------------------


@router.post(
    "/batch",
    summary="Submit multiple claims for concurrent processing",
    responses={
        202: {"description": "All claims accepted for processing"},
        400: {
            "description": "Invalid tier or empty claims list",
            "model": ErrorResponse,
        },
        402: {"description": "Insufficient credits for batch", "model": ErrorResponse},
    },
)
@limiter.limit("5/minute")
async def agent_batch(
    body: BatchRequest,
    request: Request,
    payment: AgentPaymentContext = Depends(get_agent_payment),
    session: AsyncSession = Depends(get_session),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
) -> JSONResponse:
    """Submit up to 10 claims for concurrent background processing.

    All claims run at the same tier (quick or full). Each claim creates its own
    check and transaction. The total cost is deducted upfront — if the balance
    is insufficient, no claims are submitted.

    Returns 202 with check IDs and poll URLs for each claim.

    **Rate limit:** 5/minute
    """
    tier = body.tier.lower()
    if tier not in ("quick", "full"):
        raise HTTPException(
            status_code=400,
            detail="Batch tier must be 'quick' or 'full'.",
        )

    amount_pence = get_tier_price(tier)
    total_cost = amount_pence * len(body.claims)

    # Verify sufficient balance upfront (credit provider only)
    if payment.provider == "credit":
        from app.models.user import User

        user = await session.get(User, payment.user_id)
        balance = max((user.credit_balance_pence or 0), 0) if user else 0
        if balance < total_cost:
            raise HTTPException(
                status_code=402,
                detail=f"Insufficient credits. Need {total_cost} pence for {len(body.claims)} claims at £{amount_pence/100:.2f}/each. Balance: {balance} pence.",
            )

    from app.core.database import async_session
    from app.pipeline.progress import ProgressReporter
    from app.pipeline.runner import DEFAULT_CONFIG, QUICK_CONFIG

    config = QUICK_CONFIG if tier == "quick" else DEFAULT_CONFIG
    results = []

    for i, item in enumerate(body.claims):
        claim_hash = compute_claim_text_hash(item.claim)
        request_hash = compute_request_hash(tier, claim_hash, body.compact)
        item_idem_key = f"{idempotency_key}_{i}" if idempotency_key else None

        # Charge per claim
        tx = await payment.charge(
            amount_pence=amount_pence,
            tier=tier,
            description=claim_hash,
            idempotency_key=item_idem_key,
            request_hash=request_hash,
        )

        # Resolve input
        resolved_type, input_data = _resolve_input(item.claim, item.input_type)

        # Create check
        check = Check(
            id=str(uuid.uuid4()),
            user_id=payment.user_id,
            input_type=resolved_type,
            input_content=json.dumps(input_data),
            input_url=input_data.get("url"),
            status="processing",
            credits_used=0,
            initiated_via=f"agent_{payment.provider}",
            client=resolve_client(request),
            executed_tier=tier,
        )
        session.add(check)
        await session.commit()
        await session.refresh(check)

        tx.check_id = check.id
        await session.commit()

        # Launch pipeline in background
        asyncio.create_task(
            _run_pipeline_background(
                check_id=check.id,
                user_id=payment.user_id,
                input_data=input_data,
                config=config,
                tier=tier,
                tx_id=tx.id,
                provider=payment.provider,
                amount_pence=amount_pence,
            )
        )

        results.append(
            {
                "index": i,
                "checkId": check.id,
                "txId": tx.id,
                "claim": item.claim[:100],
                "pollUrl": f"/api/v1/agent/result/{check.id}",
            }
        )

    estimated = 15 if tier == "quick" else 60
    return JSONResponse(
        status_code=202,
        content={
            "accepted": len(results),
            "tier": tier,
            "totalChargedPence": total_cost,
            "estimatedSeconds": estimated,
            "checks": results,
        },
    )
