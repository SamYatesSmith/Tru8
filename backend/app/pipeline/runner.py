"""
Inline pipeline runner for SSE streaming.

Reuses the battle-tested async functions from workers/pipeline.py,
running them in a thread pool with asyncio.run() for proper isolation
(same pattern Celery uses).
"""

import asyncio
import json
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from functools import partial
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import async_session
from app.models import Check, Claim, Evidence, RawEvidence, User
from app.pipeline.progress import ProgressReporter
from app.services.push_notifications import push_notification_service
from app.services.email_notifications import email_notification_service
from app.services.cache import get_cache_service
from app.utils.date_utils import parse_date

logger = logging.getLogger(__name__)


async def _log_stage_transition(
    check_id: str,
    from_stage: str,
    to_stage: str,
    progress_reporter: "ProgressReporter",
    reason: str = "normal",
) -> None:
    """
    Log a stage transition with structured fields, then report progress.

    Every stage transition is logged with: check_id, from_stage, to_stage,
    reason, and ISO timestamp — enabling post-hoc debugging of stage ordering.
    """
    ts = datetime.utcnow().isoformat() + "Z"
    logger.info(
        f"[STAGE TRANSITION] check={check_id} from={from_stage} to={to_stage} "
        f"reason={reason} ts={ts}"
    )
    await progress_reporter.report_progress(to_stage)


# Thread pool for running async functions with isolated event loops
# This mimics how Celery runs async code - each call gets its own event loop
_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="pipeline_")


def _run_async_in_thread(async_func, *args, **kwargs):
    """
    Run an async function in the current thread with a fresh event loop.
    This is what asyncio.run() does - creates isolated event loop.
    """
    return asyncio.run(async_func(*args, **kwargs))


def _run_async_in_thread_with_timeout(async_func, timeout, *args, **kwargs):
    """
    Run an async function with a timeout, in the current thread with a fresh event loop.
    The timeout is enforced INSIDE the asyncio.run() call, so it actually works.
    """

    async def with_timeout():
        return await asyncio.wait_for(async_func(*args, **kwargs), timeout=timeout)

    return asyncio.run(with_timeout())


async def run_in_executor(async_func, *args, **kwargs):
    """
    Run an async function in a thread pool with isolated event loop.

    This provides the same isolation that Celery gets by using asyncio.run()
    in its synchronous task context. Each call gets its own event loop,
    avoiding shared state issues with FastAPI's main event loop.
    """
    loop = asyncio.get_event_loop()
    func = partial(_run_async_in_thread, async_func, *args, **kwargs)
    return await loop.run_in_executor(_executor, func)


async def run_in_executor_with_timeout(async_func, timeout: float, *args, **kwargs):
    """
    Run an async function in a thread pool with isolated event loop AND enforced timeout.

    The timeout is enforced INSIDE the asyncio.run() call, so it actually works
    (unlike asyncio.wait_for around run_in_executor, which can't cancel thread work).
    """
    loop = asyncio.get_event_loop()
    func = partial(
        _run_async_in_thread_with_timeout, async_func, timeout, *args, **kwargs
    )
    return await loop.run_in_executor(_executor, func)


# User-friendly error messages
USER_FRIENDLY_ERRORS = {
    "cookie_consent_wall": "This website requires cookie consent which we cannot bypass. Please try pasting the article text directly.",
    "paywall": "This article is behind a paywall. Please try pasting the article text directly.",
    "connection_error": "We couldn't reach this website. Please check the URL and try again.",
    "no_claims": "We couldn't extract any verifiable claims from this content. Please try different content.",
    "timeout": "The request took too long to complete. Please try again.",
}


def get_user_friendly_error(error: Exception) -> str:
    """Convert technical errors to user-friendly messages.

    IMPORTANT: The fallback must never leak raw exception strings (SQL traces,
    stack traces, internal paths) to users.  Anything unrecognised gets a
    generic message; the full error is still logged server-side.
    """
    error_str = str(error).lower()
    for key, message in USER_FRIENDLY_ERRORS.items():
        if key in error_str:
            return message
    # Log the full technical error server-side, return generic message to user
    logger.error(
        f"[PIPELINE ERROR] Unhandled error (user will see generic message): {error}"
    )
    return "Something went wrong while processing your check. Please try again."


class PipelineError(Exception):
    """Custom exception for pipeline failures."""

    def __init__(self, message: str, stage: str = "unknown", recoverable: bool = False):
        self.message = message
        self.stage = stage
        self.recoverable = recoverable
        super().__init__(message)


async def run_pipeline(
    check_id: str,
    user_id: str,
    input_data: Dict[str, Any],
    progress_reporter: ProgressReporter,
) -> Optional[Dict[str, Any]]:
    """
    Run the fact-checking pipeline inline with progress streaming.

    Entry point that delegates to phase1 (which may call phase2 for focused mode).
    For article mode, phase1 pauses after claim extraction/ranking so the user
    can select which claims to investigate. Phase2 is triggered later via the
    PATCH /select-claims endpoint.

    Returns the final result dict for focused mode, or None for article mode
    (which pauses at waiting_for_selection).
    """
    return await run_pipeline_phase1(check_id, user_id, input_data, progress_reporter)


async def run_pipeline_phase1(
    check_id: str,
    user_id: str,
    input_data: Dict[str, Any],
    progress_reporter: ProgressReporter,
) -> Optional[Dict[str, Any]]:
    """
    Pipeline Phase 1: ingest → extract → classify → rank claims.

    For article mode: saves ranked claims to DB, sets check status to
    'waiting_for_selection', emits SSE event, and returns None.
    For focused mode: calls phase2 directly and returns the final result.
    """
    from app.workers.pipeline import (
        ingest_content_async,
        extract_claims_with_cache,
    )
    from app.utils.article_classifier import classify_article
    from app.services.search import warmup_search_providers

    warmup_search_providers()

    start_time = datetime.utcnow()
    stage_timings = {}

    from app.pipeline.evidence_ledger import get_ledger

    ledger = get_ledger(check_id)

    try:
        cache_service = await get_cache_service()
        logger.info(f"[INLINE PIPELINE] Cache service initialized successfully")
    except Exception as e:
        logger.warning(
            f"[INLINE PIPELINE] Cache service initialization failed, continuing without cache: {e}"
        )
        cache_service = None

    logger.info(f"[INLINE PIPELINE] Starting phase 1 for check {check_id}")

    # =========================================================================
    # Stage 1: Ingest
    # =========================================================================
    current_stage = "starting"
    await _log_stage_transition(check_id, current_stage, "ingest", progress_reporter)
    current_stage = "ingest"
    stage_start = datetime.utcnow()

    try:
        content = await ingest_content_async(input_data)
    except Exception as e:
        logger.error(
            f"[STAGE ERROR] check={check_id} stage=ingest error={type(e).__name__}: {e}"
        )
        import traceback

        logger.error(f"[INLINE PIPELINE] Ingest traceback: {traceback.format_exc()}")
        raise PipelineError(get_user_friendly_error(e), stage="ingest")

    if not content.get("success"):
        error_msg = content.get("message") or content.get("error", "Unknown error")
        raise PipelineError(
            get_user_friendly_error(Exception(error_msg)), stage="ingest"
        )

    stage_timings["ingest"] = (datetime.utcnow() - stage_start).total_seconds()
    logger.info(
        f"[INLINE PIPELINE] Ingested content, length: {len(content.get('content', ''))}"
    )

    # =========================================================================
    # Stage 2: Extract Claims
    # =========================================================================
    await _log_stage_transition(check_id, current_stage, "extract", progress_reporter)
    current_stage = "extract"
    stage_start = datetime.utcnow()

    extract_content = content.get("content", "")
    extract_metadata = content.get("metadata", {})

    # Article classification (optional)
    article_classification = None
    if settings.ENABLE_ARTICLE_CLASSIFICATION:
        try:
            article_classification = await classify_article(
                title=extract_metadata.get("title", "") if extract_metadata else "",
                url=extract_metadata.get("url", "") if extract_metadata else "",
                content=extract_content[:2000],
            )
            logger.info(
                f"[INLINE PIPELINE] Article classified: {article_classification.primary_domain}"
            )
        except Exception as e:
            logger.warning(f"Article classification failed: {e}")

    # Extract claims
    try:
        claims = await extract_claims_with_cache(
            extract_content, extract_metadata, cache_service
        )
    except Exception as e:
        logger.error(
            f"[STAGE ERROR] check={check_id} stage=extract error={type(e).__name__}: {e}"
        )
        raise PipelineError(get_user_friendly_error(e), stage="extract")

    if not claims:
        # Give a specific message if the input looks like a question
        raw_text = (extract_content or "").strip()
        if raw_text.endswith("?") or raw_text.lower().startswith(
            (
                "who ",
                "what ",
                "when ",
                "where ",
                "why ",
                "how ",
                "is ",
                "are ",
                "was ",
                "were ",
                "do ",
                "does ",
                "did ",
                "can ",
                "could ",
                "will ",
                "would ",
                "should ",
                "given ",
            )
        ):
            raise PipelineError(
                "Your input looks like a question. Tru8 researches evidence "
                "for factual claims — try submitting a statement instead, e.g. "
                "'The Eiffel Tower was completed in 1889'.",
                stage="extract",
            )
        raise PipelineError(
            "We couldn't extract any verifiable claims from this content. "
            "Try submitting content that contains specific factual statements.",
            stage="extract",
        )

    # Attach article classification
    if article_classification:
        for claim in claims:
            claim["article_classification"] = article_classification.to_dict()

    # FROZEN EVIDENCE REPLAY: Attach frozen evidence to claims (zero network)
    import hashlib

    def _claim_key(text: str) -> str:
        """Stable claim identifier: sha1 of normalized text."""
        normalized = " ".join(text.lower().split())
        return hashlib.sha1(normalized.encode()).hexdigest()

    frozen_evidence = input_data.get("frozen_evidence")
    frozen_evidence_claim_texts = input_data.get("frozen_claim_texts") or {}
    _replay_temp_token = None
    _replay_evidence_token = None

    if frozen_evidence:
        attached_count = 0
        frozen_replay_mismatches = 0
        for claim in claims:
            pos = str(claim.get("position", 0))
            claim_text = claim.get("text", "")
            key = _claim_key(claim_text)

            evidence_items = frozen_evidence.get(key) or frozen_evidence.get(pos)
            if evidence_items is None:
                logger.warning(
                    f"[FROZEN EVIDENCE REPLAY] No frozen evidence for claim {pos} (key={key[:12]})"
                )
                continue

            expected_text = frozen_evidence_claim_texts.get(
                key, frozen_evidence_claim_texts.get(pos, "")
            )
            if expected_text:
                norm_expected = " ".join(expected_text.lower().split())
                norm_actual = " ".join(claim_text.lower().split())
                if norm_expected != norm_actual:
                    frozen_replay_mismatches += 1
                    logger.warning(
                        f"[FROZEN EVIDENCE REPLAY MISMATCH] Claim {pos}: "
                        f"expected='{expected_text[:80]}...' actual='{claim_text[:80]}...'"
                    )
                    continue

            claim["frozen_evidence"] = evidence_items
            attached_count += 1

        from app.pipeline.replay_context import (
            frozen_replay_temperature,
            frozen_evidence_replay,
        )

        _replay_temp_token = frozen_replay_temperature.set(0.0)
        _replay_evidence_token = frozen_evidence_replay.set(True)

        logger.info(
            f"[FROZEN EVIDENCE REPLAY] Attached to {attached_count}/{len(claims)} claims"
            f"{f', {frozen_replay_mismatches} mismatches' if frozen_replay_mismatches else ''}"
        )

        if ledger:
            ledger.record(
                "frozen_evidence_replay",
                attached=attached_count,
                mismatches=frozen_replay_mismatches,
            )

    stage_timings["extract"] = (datetime.utcnow() - stage_start).total_seconds()
    logger.info(f"[INLINE PIPELINE] Extracted {len(claims)} claims")

    # =========================================================================
    # Determine entry mode
    # =========================================================================
    entry_mode = "focused" if len(claims) == 1 else "article"

    # =========================================================================
    # Stage 2.6: Claim Selection / Ranking (article mode only)
    # =========================================================================
    from app.pipeline.claim_selector import ClaimSelector

    selected_claims = claims

    if entry_mode == "article":
        await _log_stage_transition(
            check_id, current_stage, "select", progress_reporter
        )
        current_stage = "select"
        stage_start = datetime.utcnow()

        try:
            selector = ClaimSelector()
            claims = await selector.rank_claims_by_significance(
                claims,
                article_context={
                    "domain": (
                        article_classification.primary_domain
                        if article_classification
                        else "unknown"
                    ),
                    "classification": (
                        article_classification.to_dict()
                        if article_classification
                        else {}
                    ),
                    "excerpt": extract_content[:500],
                },
            )
            claims = selector.select_claims(claims)
            selected_claims = [c for c in claims if c.get("is_selected")]
            logger.info(
                f"[INLINE PIPELINE] Selected {len(selected_claims)}/{len(claims)} "
                f"claims for analysis"
            )
        except Exception as e:
            logger.warning(f"Claim selection failed (non-critical): {e}")
            for i, c in enumerate(claims):
                c["is_selected"] = i < settings.MAX_SELECTED_CLAIMS
                c["significance_rank"] = i + 1
                c["significance_score"] = 0.5
            selected_claims = [c for c in claims if c.get("is_selected")]

        stage_timings["select"] = (datetime.utcnow() - stage_start).total_seconds()

        if ledger:
            ledger.record(
                "claim_selection",
                total_claims=len(claims),
                selected_claims=len(selected_claims),
            )
    else:
        # Focused mode: single claim, always selected
        claims[0]["is_selected"] = True
        claims[0]["significance_rank"] = 1
        claims[0]["significance_score"] = 1.0
        selected_claims = claims

    # =========================================================================
    # Save Phase 1 state to DB (claims, classification, etc.)
    # =========================================================================
    async with async_session() as session:
        stmt = select(Check).where(Check.id == check_id)
        result = await session.execute(stmt)
        check = result.scalar_one_or_none()

        if check:
            check.entry_mode = entry_mode
            check.article_excerpt = extract_content[:5000]

            # Save article classification
            if article_classification:
                check.article_domain = article_classification.primary_domain
                check.article_secondary_domains = (
                    article_classification.secondary_domains
                    if hasattr(article_classification, "secondary_domains")
                    else []
                )
                check.article_jurisdiction = (
                    article_classification.jurisdiction
                    if hasattr(article_classification, "jurisdiction")
                    else None
                )
                check.article_classification_confidence = (
                    int(article_classification.confidence * 100)
                    if hasattr(article_classification, "confidence")
                    and article_classification.confidence
                    else None
                )
                check.article_classification_source = (
                    article_classification.source
                    if hasattr(article_classification, "source")
                    else None
                )

            # Save all claims to DB
            for claim_data in claims:
                position_val = claim_data.get("position", 0)
                claim_map_data = claim_data.get("claim_map")
                resolved_claim_type = None
                if claim_map_data and isinstance(claim_map_data, dict):
                    ct = claim_map_data.get("claim_type")
                    resolved_claim_type = ct.value if hasattr(ct, "value") else ct

                claim = Claim(
                    check_id=check_id,
                    text=claim_data.get("text", ""),
                    position=int(position_val) if position_val is not None else 0,
                    subject_context=claim_data.get("subject_context"),
                    key_entities=(
                        claim_data.get("key_entities", [])
                        if claim_data.get("key_entities")
                        else None
                    ),
                    source_title=claim_data.get("source_title"),
                    source_url=claim_data.get("source_url"),
                    source_date=claim_data.get("source_date"),
                    rhetorical_context=claim_data.get("rhetorical_analysis"),
                    has_rhetorical_context=claim_data.get(
                        "has_rhetorical_context", False
                    ),
                    rhetorical_style=claim_data.get("rhetorical_style"),
                    claim_type=resolved_claim_type,
                    significance_rank=claim_data.get("significance_rank"),
                    significance_score=claim_data.get("significance_score"),
                    is_selected=claim_data.get("is_selected"),
                )
                session.add(claim)

            # For article mode: set status to waiting_for_selection
            if entry_mode == "article":
                check.status = "waiting_for_selection"
                check.selected_claims_count = len(selected_claims)

            await session.commit()

        logger.info(
            f"[INLINE PIPELINE] Phase 1 complete: saved {len(claims)} claims to DB "
            f"(entry_mode={entry_mode})"
        )

    # =========================================================================
    # For article mode: emit SSE event and RETURN (don't continue)
    # =========================================================================
    if entry_mode == "article":
        # Build claims data for the SSE event
        claims_for_sse = []
        for c in claims:
            claims_for_sse.append(
                {
                    "text": c.get("text", ""),
                    "position": c.get("position", 0),
                    "claimType": c.get("claim_type")
                    or (
                        c.get("article_classification", {}).get("claim_type")
                        if c.get("article_classification")
                        else None
                    ),
                    "significanceRank": c.get("significance_rank"),
                    "significanceScore": c.get("significance_score"),
                    "isSelected": c.get("is_selected", False),
                    "subjectContext": c.get("subject_context"),
                }
            )

        await progress_reporter.report_awaiting_selection(claims_for_sse)

        logger.info(
            f"[INLINE PIPELINE] Phase 1 paused for article mode — "
            f"waiting for user claim selection (check={check_id})"
        )
        return None

    # =========================================================================
    # For focused mode: continue directly to phase2
    # =========================================================================
    return await run_pipeline_phase2(
        check_id=check_id,
        user_id=user_id,
        input_data=input_data,
        progress_reporter=progress_reporter,
        # Pass through phase1 state to avoid re-reading DB
        _phase1_state={
            "claims": claims,
            "selected_claims": selected_claims,
            "content": content,
            "article_classification": article_classification,
            "entry_mode": entry_mode,
            "frozen_evidence": frozen_evidence,
            "frozen_evidence_claim_texts": frozen_evidence_claim_texts,
            "_replay_temp_token": _replay_temp_token,
            "_replay_evidence_token": _replay_evidence_token,
            "cache_service": cache_service,
            "ledger": ledger,
            "start_time": start_time,
            "stage_timings": stage_timings,
        },
    )


async def run_pipeline_phase2(
    check_id: str,
    user_id: str,
    input_data: Dict[str, Any],
    progress_reporter: ProgressReporter,
    _phase1_state: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Pipeline Phase 2: factcheck → decompose → retrieve → filter cascade → evidence mapping → build result.

    If _phase1_state is provided (focused mode), uses it directly.
    Otherwise (article mode, called from PATCH endpoint), reloads state from DB.
    """
    from app.workers.pipeline import (
        retrieve_evidence_with_cache,
        search_factchecks_for_claims,
    )
    from app.pipeline.claim_map_analyzer import ClaimMapAnalyzer

    start_time = datetime.utcnow()
    stage_timings = {}

    # =========================================================================
    # Load state — either from phase1 passthrough or from DB
    # =========================================================================
    if _phase1_state:
        # Focused mode: phase1 passed state directly
        claims = _phase1_state["claims"]
        selected_claims = _phase1_state["selected_claims"]
        content = _phase1_state["content"]
        article_classification = _phase1_state["article_classification"]
        entry_mode = _phase1_state["entry_mode"]
        frozen_evidence = _phase1_state["frozen_evidence"]
        frozen_evidence_claim_texts = _phase1_state["frozen_evidence_claim_texts"]
        _replay_temp_token = _phase1_state["_replay_temp_token"]
        _replay_evidence_token = _phase1_state["_replay_evidence_token"]
        cache_service = _phase1_state["cache_service"]
        ledger = _phase1_state["ledger"]
        start_time = _phase1_state["start_time"]
        stage_timings = _phase1_state["stage_timings"]
    else:
        # Article mode: reload from DB after user selected claims
        from app.pipeline.evidence_ledger import get_ledger

        ledger = get_ledger(check_id)

        try:
            cache_service = await get_cache_service()
        except Exception as e:
            logger.warning(f"[PHASE 2] Cache service init failed: {e}")
            cache_service = None

        async with async_session() as session:
            # Load check
            stmt = select(Check).where(Check.id == check_id)
            result = await session.execute(stmt)
            check = result.scalar_one_or_none()

            if not check:
                raise PipelineError(f"Check {check_id} not found", stage="phase2_init")

            entry_mode = check.entry_mode or "article"

            # Load content from input_content
            input_content = (
                json.loads(check.input_content) if check.input_content else {}
            )
            content = {
                "content": check.article_excerpt or "",
                "metadata": {
                    "url": check.input_url,
                    "title": None,
                },
            }

            # Reconstruct article_classification from check fields
            article_classification = None
            if check.article_domain:
                article_classification = type(
                    "ArticleClassification",
                    (),
                    {
                        "primary_domain": check.article_domain,
                        "secondary_domains": check.article_secondary_domains or [],
                        "jurisdiction": check.article_jurisdiction,
                        "confidence": (
                            check.article_classification_confidence / 100.0
                            if check.article_classification_confidence
                            else None
                        ),
                        "source": check.article_classification_source,
                        "to_dict": lambda self: {
                            "primary_domain": self.primary_domain,
                            "secondary_domains": self.secondary_domains,
                            "jurisdiction": self.jurisdiction,
                            "confidence": self.confidence,
                            "source": self.source,
                        },
                    },
                )()

            # Load claims from DB
            claims_stmt = (
                select(Claim).where(Claim.check_id == check_id).order_by(Claim.position)
            )
            claims_result = await session.execute(claims_stmt)
            db_claims = claims_result.scalars().all()

            claims = []
            for db_claim in db_claims:
                claim_dict = {
                    "text": db_claim.text,
                    "position": db_claim.position,
                    "is_selected": db_claim.is_selected,
                    "significance_rank": db_claim.significance_rank,
                    "significance_score": db_claim.significance_score,
                    "claim_type": db_claim.claim_type,
                    "subject_context": db_claim.subject_context,
                    "key_entities": db_claim.key_entities,
                    "source_title": db_claim.source_title,
                    "source_url": db_claim.source_url,
                    "source_date": db_claim.source_date,
                    "rhetorical_analysis": db_claim.rhetorical_context,
                    "has_rhetorical_context": db_claim.has_rhetorical_context,
                    "rhetorical_style": db_claim.rhetorical_style,
                }
                if article_classification:
                    claim_dict["article_classification"] = (
                        article_classification.to_dict()
                    )
                claims.append(claim_dict)

            selected_claims = [c for c in claims if c.get("is_selected")]

            # Update check status to processing
            check.status = "processing"
            await session.commit()

        # No frozen evidence in article mode phase2
        frozen_evidence = None
        frozen_evidence_claim_texts = {}
        _replay_temp_token = None
        _replay_evidence_token = None

        logger.info(
            f"[INLINE PIPELINE] Phase 2 starting for check {check_id}: "
            f"{len(selected_claims)} selected claims of {len(claims)} total"
        )

    # =========================================================================
    # Stage 2.5: Fact-check Lookup (optional, skipped for frozen replay)
    # =========================================================================
    current_stage = "select"
    factcheck_evidence = {}
    if frozen_evidence:
        logger.info(
            "[FROZEN EVIDENCE REPLAY] Skipping fact-check API for deterministic replay"
        )
    elif settings.ENABLE_FACTCHECK_API:
        await _log_stage_transition(
            check_id, current_stage, "factcheck", progress_reporter
        )
        current_stage = "factcheck"
        stage_start = datetime.utcnow()
        try:
            factcheck_evidence = await search_factchecks_for_claims(claims)
            logger.info(
                f"[INLINE PIPELINE] Found {sum(len(v) for v in factcheck_evidence.values())} fact-checks"
            )
        except Exception as e:
            logger.warning(f"Fact-check lookup failed (non-critical): {e}")
        stage_timings["factcheck"] = (datetime.utcnow() - stage_start).total_seconds()

    # =========================================================================
    # Stage 3: Decompose Claims into Elements
    # =========================================================================
    await _log_stage_transition(check_id, current_stage, "decompose", progress_reporter)
    current_stage = "decompose"
    stage_start = datetime.utcnow()

    analyzer = ClaimMapAnalyzer()
    max_concurrent = settings.MAX_CONCURRENT_ANALYSES
    _decompose_sem = asyncio.Semaphore(max_concurrent)

    async def _decompose_one(claim):
        async with _decompose_sem:
            claim_id = str(claim.get("position", 0))
            claim_map = await analyzer.decompose_claim(claim["text"], claim_id)
            claim["claim_map"] = claim_map

    try:
        await asyncio.gather(*[_decompose_one(c) for c in selected_claims])
        logger.info(
            f"[INLINE PIPELINE] Decomposed {len(selected_claims)} claims into elements"
        )
    except Exception as e:
        logger.error(
            f"[STAGE ERROR] check={check_id} stage=decompose error={type(e).__name__}: {e}"
        )
        raise PipelineError(f"Claim decomposition failed: {e}", stage="decompose")

    stage_timings["decompose"] = (datetime.utcnow() - stage_start).total_seconds()

    if ledger:
        ledger.record(
            "decomposition",
            claims_decomposed=len(selected_claims),
            elements_per_claim={
                str(c.get("position", 0)): len(
                    c.get("claim_map", {}).get("elements", [])
                )
                for c in selected_claims
            },
        )

    # =========================================================================
    # Stage 4: Retrieve Evidence
    # =========================================================================
    await _log_stage_transition(check_id, current_stage, "retrieve", progress_reporter)
    current_stage = "retrieve"
    stage_start = datetime.utcnow()

    source_url = content.get("metadata", {}).get("url")
    retrieve_timeout = 180

    _v2_frozen_bypass = frozen_evidence and any(
        claim.get("frozen_evidence") for claim in claims
    )

    if _v2_frozen_bypass:
        evidence = {}
        for claim in claims:
            pos = str(claim.get("position", 0))
            frozen_items = claim.get("frozen_evidence", [])
            evidence[pos] = frozen_items
        raw_evidence_data = []
        raw_sources_count = 0
        total_frozen = sum(len(ev) for ev in evidence.values())
        logger.info(
            f"[FROZEN EVIDENCE REPLAY] Built evidence directly: {total_frozen} items for {len(evidence)} claims (retrieve bypassed)"
        )
        stage_timings["retrieve"] = 0.0
        if ledger:
            ledger.record(
                "retrieve",
                total=total_frozen,
                per_claim={pos: len(ev) for pos, ev in evidence.items()},
                mode="frozen_evidence_direct",
            )
    else:
        import time as _time

        _retrieve_start = _time.time()

        retrieve_claims = selected_claims if selected_claims else claims

        logger.info(
            f"[RETRIEVE STAGE] Starting for check {check_id} with {len(retrieve_claims)} claims "
            f"(of {len(claims)} total), timeout={retrieve_timeout}s"
        )

        _progressive_results = {}

        try:
            logger.info(
                f"[INLINE PIPELINE] Starting evidence retrieval with {retrieve_timeout}s timeout"
            )
            retrieval_result = await asyncio.wait_for(
                retrieve_evidence_with_cache(
                    retrieve_claims,
                    cache_service,
                    factcheck_evidence,
                    source_url=source_url,
                    progressive_results=_progressive_results,
                ),
                timeout=retrieve_timeout,
            )
            _retrieve_elapsed = _time.time() - _retrieve_start
            logger.info(
                f"[INLINE PIPELINE] Evidence retrieval completed in {_retrieve_elapsed:.2f}s"
            )
        except asyncio.TimeoutError:
            _retrieve_elapsed = _time.time() - _retrieve_start

            partial_evidence = _progressive_results.get("evidence_by_claim", {})
            partial_count = sum(len(ev) for ev in partial_evidence.values())

            if partial_count > 0:
                partial_raw = _progressive_results.get("raw_evidence", [])
                partial_pre_weight = _progressive_results.get(
                    "pre_weighting_evidence", {}
                )
                logger.warning(
                    f"[STAGE ERROR] check={check_id} stage=retrieve error=TimeoutError: "
                    f"timed out after {_retrieve_elapsed:.2f}s (limit={retrieve_timeout}s) — "
                    f"PRESERVING {partial_count} evidence items from "
                    f"{len(partial_evidence)} completed claims"
                )
                retrieval_result = {
                    "evidence_by_claim": partial_evidence,
                    "raw_evidence": partial_raw,
                    "raw_sources_count": len(partial_raw),
                    "pre_weighting_evidence": partial_pre_weight,
                }
            else:
                logger.warning(
                    f"[STAGE ERROR] check={check_id} stage=retrieve error=TimeoutError: "
                    f"timed out after {_retrieve_elapsed:.2f}s (limit={retrieve_timeout}s), "
                    f"no evidence completed before timeout"
                )
                retrieval_result = {
                    "evidence_by_claim": {},
                    "raw_evidence": [],
                    "raw_sources_count": 0,
                }
        except Exception as e:
            logger.error(
                f"[STAGE ERROR] check={check_id} stage=retrieve error={type(e).__name__}: {e}"
            )
            import traceback

            logger.error(f"[INLINE PIPELINE] Full traceback: {traceback.format_exc()}")
            if settings.ENVIRONMENT == "development":
                retrieval_result = {
                    "evidence_by_claim": {},
                    "raw_evidence": [],
                    "raw_sources_count": 0,
                }
            else:
                raise PipelineError(f"Evidence retrieval failed: {e}", stage="retrieve")

        if (
            isinstance(retrieval_result, dict)
            and "evidence_by_claim" in retrieval_result
        ):
            evidence = retrieval_result["evidence_by_claim"]
            raw_evidence_data = retrieval_result.get("raw_evidence", [])
            raw_sources_count = retrieval_result.get("raw_sources_count", 0)
        else:
            evidence = retrieval_result if isinstance(retrieval_result, dict) else {}
            raw_evidence_data = []
            raw_sources_count = 0

        stage_timings["retrieve"] = (datetime.utcnow() - stage_start).total_seconds()

        pre_weighting_evidence = (
            retrieval_result.get("pre_weighting_evidence", {})
            if isinstance(retrieval_result, dict)
            else {}
        )
        if ledger and pre_weighting_evidence:
            ledger.record("pre_weighting_evidence", evidence=pre_weighting_evidence)

    # DIAGNOSTIC: Log evidence counts per claim to debug filtering
    total_evidence = sum(len(ev) for ev in evidence.values())
    logger.info(
        f"[INLINE PIPELINE] Evidence summary: {total_evidence} total items for {len(evidence)} claims"
    )
    for pos, ev_list in evidence.items():
        logger.info(f"[INLINE PIPELINE] Claim {pos}: {len(ev_list)} evidence items")
    if total_evidence == 0:
        logger.critical(
            f"[INLINE PIPELINE] CRITICAL: No evidence retrieved for any claim! Check search providers."
        )

    if ledger:
        ledger.record(
            "retrieve",
            total=total_evidence,
            per_claim={pos: len(ev) for pos, ev in evidence.items()},
        )
        if raw_evidence_data:
            from collections import Counter

            claim_filter_counts: dict = {}
            for raw_item in raw_evidence_data:
                pos = str(raw_item.get("claim_position", "?"))
                if pos not in claim_filter_counts:
                    claim_filter_counts[pos] = {
                        "total_raw": 0,
                        "included": 0,
                        "excluded_by_stage": Counter(),
                    }
                claim_filter_counts[pos]["total_raw"] += 1
                if raw_item.get("is_included"):
                    claim_filter_counts[pos]["included"] += 1
                elif raw_item.get("filter_stage"):
                    claim_filter_counts[pos]["excluded_by_stage"][
                        raw_item["filter_stage"]
                    ] += 1
            for pos, stats in claim_filter_counts.items():
                ledger.record_claim(
                    pos,
                    "evidence_filtering",
                    total_raw=stats["total_raw"],
                    included=stats["included"],
                    excluded_by_stage=dict(stats["excluded_by_stage"]),
                )
            ledger.record(
                "evidence_filtering",
                total_raw=sum(s["total_raw"] for s in claim_filter_counts.values()),
                total_included=sum(s["included"] for s in claim_filter_counts.values()),
            )

    # =========================================================================
    # Stage 3.6: Cross-Claim URL Deduplication
    # =========================================================================
    from app.pipeline.replay_context import frozen_evidence_replay as _fer_var

    _is_frozen_evidence_replay = _fer_var.get(False)

    if _is_frozen_evidence_replay and evidence:
        logger.info(
            f"[URL DEDUP] SKIPPED — V2 frozen evidence replay (deterministic bypass)"
        )
    elif evidence:
        stage_start = datetime.utcnow()
        try:
            max_claims_per_url = getattr(settings, "MAX_CLAIMS_PER_URL", 1)
            url_claims = {}
            dedup_losers = [] if ledger else None

            for claim_pos, ev_list in evidence.items():
                for ev in ev_list:
                    url = ev.get("url", "")
                    if not url:
                        continue

                    score = ev.get("combined_score", 0)

                    if url not in url_claims:
                        url_claims[url] = [(claim_pos, ev, score)]
                    elif claim_pos in {entry[0] for entry in url_claims[url]}:
                        url_claims[url].append((claim_pos, ev, score))
                    elif (
                        len({entry[0] for entry in url_claims[url]})
                        < max_claims_per_url
                    ):
                        url_claims[url].append((claim_pos, ev, score))
                    else:
                        entries = url_claims[url] + [(claim_pos, ev, score)]
                        entries.sort(key=lambda x: (-x[2], x[0]))
                        kept = []
                        seen_claims = set()
                        for entry in entries:
                            if (
                                entry[0] in seen_claims
                                or len(seen_claims) < max_claims_per_url
                            ):
                                kept.append(entry)
                                seen_claims.add(entry[0])
                            else:
                                loser = entry
                                winner = entries[0]
                                logger.debug(
                                    f"[URL DEDUP] Dropped {url[:60]} from claim {loser[0]} (score {loser[2]:.2f}), kept in {list(seen_claims)}"
                                )
                                if dedup_losers is not None:
                                    dedup_losers.append(
                                        {
                                            "url": url[:120],
                                            "loser": loser[0],
                                            "winner": winner[0],
                                        }
                                    )
                        url_claims[url] = kept

            deduped_evidence = {pos: [] for pos in evidence.keys()}
            for url, entries in url_claims.items():
                for claim_pos, ev, score in entries:
                    deduped_evidence[claim_pos].append(ev)

            before_count = sum(len(ev_list) for ev_list in evidence.values())
            after_count = sum(len(ev_list) for ev_list in deduped_evidence.values())
            removed_count = before_count - after_count

            if removed_count > 0:
                logger.info(
                    f"[URL DEDUP] Removed {removed_count} duplicate URLs across claims: {before_count} → {after_count}"
                )
            else:
                logger.info(
                    f"[URL DEDUP] No cross-claim duplicates found ({after_count} unique URLs)"
                )

            evidence = deduped_evidence

            if ledger:
                casualties_per_claim = {}
                if dedup_losers:
                    for entry in dedup_losers:
                        lc = entry["loser"]
                        if lc not in casualties_per_claim:
                            casualties_per_claim[lc] = []
                        casualties_per_claim[lc].append(
                            {"url": entry["url"], "won_by": entry["winner"]}
                        )
                ledger.record(
                    "url_dedup",
                    in_count=before_count,
                    out_count=after_count,
                    removed=removed_count,
                    casualties_per_claim=casualties_per_claim,
                )

        except Exception as e:
            logger.warning(f"Cross-claim URL deduplication failed (non-critical): {e}")
        stage_timings["url_dedup"] = (datetime.utcnow() - stage_start).total_seconds()

    # =========================================================================
    # Stage 3.7: LLM Relevance Scoring with Reassignment
    # =========================================================================
    if _is_frozen_evidence_replay and evidence:
        logger.info(
            f"[LLM SCORER] SKIPPED — V2 frozen evidence replay (deterministic bypass)"
        )
        if ledger:
            count_frozen = sum(len(ev_list) for ev_list in evidence.values())
            ledger.record(
                "llm_scoring",
                in_count=count_frozen,
                out_count=count_frozen,
                note="skipped_frozen_replay",
            )
    elif settings.ENABLE_LLM_RELEVANCE_SCORER and evidence:
        stage_start = datetime.utcnow()
        count_before_scoring = sum(len(ev_list) for ev_list in evidence.values())
        try:
            from app.pipeline.relevance_scorer import score_evidence_batch

            article_excerpt = content.get("content", "")[:5000]
            claim_texts = [c.get("text", "") for c in claims]
            evidence = await score_evidence_batch(
                claims=claim_texts, evidence=evidence, article_context=article_excerpt
            )

            # Extract excluded items (score-1 irrelevant evidence)
            excluded_by_scorer = evidence.pop("_excluded", [])
            if excluded_by_scorer:
                logger.info(
                    f"[LLM SCORER] Excluded {len(excluded_by_scorer)} irrelevant items"
                )

            count_after_scoring = sum(len(ev_list) for ev_list in evidence.values())
            logger.info(
                f"[LLM SCORER] Evidence after scoring: {count_before_scoring} → {count_after_scoring}"
            )

            if ledger:
                ledger.record(
                    "llm_scoring",
                    in_count=count_before_scoring,
                    out_count=count_after_scoring,
                    excluded=len(excluded_by_scorer),
                )

        except Exception as e:
            logger.warning(f"LLM relevance scoring failed (non-critical): {e}")
        stage_timings["llm_relevance"] = (
            datetime.utcnow() - stage_start
        ).total_seconds()

    # =========================================================================
    # Stage 4.5: Evidence Classification (Tier + Type)
    # =========================================================================
    if _is_frozen_evidence_replay and evidence:
        logger.info(
            "[CLASSIFY] SKIPPED — V2 frozen evidence replay (deterministic bypass)"
        )
    elif evidence:
        await _log_stage_transition(
            check_id, current_stage, "classify", progress_reporter
        )
        current_stage = "classify"
        stage_start = datetime.utcnow()

        try:
            from app.pipeline.evidence_classifier import EvidenceClassifier

            classifier = EvidenceClassifier()
            for claim_pos, ev_list in evidence.items():
                if ev_list:
                    evidence[claim_pos] = await classifier.classify_batch(ev_list)
                    # Update receipt_status to "classified" for all items
                    for ev in evidence[claim_pos]:
                        ev["receipt_status"] = "classified"
                    logger.info(
                        f"[CLASSIFY] Claim {claim_pos}: classified {len(ev_list)} evidence items"
                    )
        except Exception as e:
            logger.warning(f"Evidence classification failed (non-critical): {e}")

        stage_timings["classify"] = (datetime.utcnow() - stage_start).total_seconds()

        if ledger:
            from collections import Counter

            tier_counts = Counter()
            type_counts = Counter()
            for ev_list in evidence.values():
                for ev in ev_list:
                    tier_counts[ev.get("tier", "unknown")] += 1
                    type_counts[ev.get("evidence_type", "unknown")] += 1
            ledger.record(
                "classify",
                tier_distribution=dict(tier_counts),
                type_distribution=dict(type_counts),
            )

    # =========================================================================
    # Stage 5: Evidence Mapping (replaces Judge)
    # =========================================================================
    await _log_stage_transition(check_id, current_stage, "analyze", progress_reporter)
    current_stage = "analyze"
    stage_start = datetime.utcnow()

    from app.utils.url_utils import extract_domain

    final_evidence_count = sum(len(ev_list) for ev_list in evidence.values())
    final_domains = {}
    final_urls = set()
    for ev_list in evidence.values():
        for ev in ev_list:
            domain = extract_domain(ev.get("url", ""), fallback="unknown")
            final_domains[domain] = final_domains.get(domain, 0) + 1
            final_urls.add(ev.get("url", ""))

    logger.info(
        f"[ANALYZER INPUT] Final evidence: {final_evidence_count} items, "
        f"{len(final_urls)} unique URLs, {len(final_domains)} domains"
    )
    logger.info(
        f"[ANALYZER INPUT] Domain distribution: {dict(sorted(final_domains.items(), key=lambda x: -x[1]))}"
    )

    if ledger:
        snippet_fallback_count = 0
        snippet_reasons = {
            "403": 0,
            "429": 0,
            "timeout": 0,
            "js_required": 0,
            "other": 0,
        }
        title_only_count = 0
        for ev_list in evidence.values():
            for ev in ev_list:
                meta = ev.get("metadata") or {}
                if meta.get("is_snippet_fallback"):
                    snippet_fallback_count += 1
                    reason = (meta.get("fallback_reason") or "").lower()
                    if "403" in reason or "forbidden" in reason:
                        snippet_reasons["403"] += 1
                    elif "429" in reason:
                        snippet_reasons["429"] += 1
                    elif "timeout" in reason:
                        snippet_reasons["timeout"] += 1
                    elif "js" in reason or "javascript" in reason:
                        snippet_reasons["js_required"] += 1
                    else:
                        snippet_reasons["other"] += 1
                if not ev.get("text") and ev.get("title"):
                    title_only_count += 1
        ledger.record(
            "analyzer_input",
            total=final_evidence_count,
            unique_urls=len(final_urls),
            domains=dict(sorted(final_domains.items(), key=lambda x: -x[1])),
            snippet_fallbacks=snippet_fallback_count,
            snippet_fallback_reasons=snippet_reasons,
            title_only_items=title_only_count,
        )
        ledger.record(
            "analyzer_input_evidence",
            evidence={
                pos: [dict(ev) for ev in ev_list] for pos, ev_list in evidence.items()
            },
        )

    # Compute claim_map_input_hash BEFORE evidence mapping (determinism tracking)
    import hashlib as _hashlib

    def _compute_claim_map_input_hash(
        claim_map_scaffold: dict, evidence_list: list
    ) -> str:
        """Canonicalize scaffold + evidence, return SHA256[:16] hex."""
        elements_canon = sorted(
            [
                {"element_id": e["element_id"], "description": e["description"]}
                for e in claim_map_scaffold.get("elements", [])
            ],
            key=lambda x: x["element_id"],
        )
        evidence_canon = sorted(
            [
                {"evidence_id": e.get("evidence_id", ""), "url": e.get("url", "")}
                for e in evidence_list
            ],
            key=lambda x: x["evidence_id"],
        )
        blob = json.dumps(
            {"elements": elements_canon, "evidence": evidence_canon},
            sort_keys=True,
            ensure_ascii=True,
        )
        return _hashlib.sha256(blob.encode()).hexdigest()[:16]

    for claim in selected_claims:
        pos = str(claim.get("position", 0))
        scaffold = claim.get("claim_map")
        ev_list = evidence.get(pos, [])
        if scaffold:
            claim["claim_map_input_hash"] = _compute_claim_map_input_hash(
                scaffold, ev_list
            )

    article_excerpt = content.get("content", "")[:5000]
    analyze_timeout = min(15 * len(selected_claims), 120)

    _analyze_sem = asyncio.Semaphore(max_concurrent)

    async def _map_evidence_for_claim(claim):
        async with _analyze_sem:
            pos = str(claim.get("position", 0))
            claim_evidence = evidence.get(pos, [])
            if claim.get("claim_map"):
                completed = await analyzer.map_evidence_to_elements(
                    claim["claim_map"], claim_evidence
                )
                claim["claim_map"] = completed
                claim["evidence"] = claim_evidence

    try:
        logger.info(
            f"[INLINE PIPELINE] Starting evidence mapping for {len(selected_claims)} claims "
            f"with {analyze_timeout}s timeout"
        )
        await asyncio.wait_for(
            asyncio.gather(*[_map_evidence_for_claim(c) for c in selected_claims]),
            timeout=analyze_timeout,
        )
        logger.info(f"[INLINE PIPELINE] Evidence mapping completed successfully")
    except asyncio.TimeoutError:
        logger.error(
            f"[STAGE ERROR] check={check_id} stage=analyze error=TimeoutError: "
            f"Evidence mapping timed out after {analyze_timeout}s"
        )
        raise PipelineError("Evidence mapping timed out", stage="analyze")
    except Exception as e:
        logger.error(
            f"[STAGE ERROR] check={check_id} stage=analyze error={type(e).__name__}: {e}"
        )
        raise PipelineError(f"Evidence mapping failed: {e}", stage="analyze")

    if ledger:
        ledger.record(
            "evidence_mapping",
            claims_mapped=len(selected_claims),
            evidence_per_claim={
                str(c.get("position", 0)): len(
                    evidence.get(str(c.get("position", 0)), [])
                )
                for c in selected_claims
            },
        )

    stage_timings["analyze"] = (datetime.utcnow() - stage_start).total_seconds()

    # =========================================================================
    # Stage 5.5: Query Answering (optional)
    # =========================================================================
    query_response_data = None
    if input_data.get("user_query") and settings.ENABLE_SEARCH_CLARITY:
        await _log_stage_transition(check_id, current_stage, "query", progress_reporter)
        current_stage = "query"
        stage_start = datetime.utcnow()

        try:
            from app.pipeline.query_answer import get_query_answerer

            query_answerer = await get_query_answerer()
            query_result = await query_answerer.answer_query(
                user_query=input_data.get("user_query"),
                claims=claims,
                evidence_by_claim=evidence,
                original_text=content.get("content", "")[:1000],
            )
            query_response_data = {
                "answer": query_result["answer"],
                "confidence": query_result["confidence"],
                "source_ids": query_result["source_ids"],
                "related_claims": query_result["related_claims"],
                "found_answer": query_result["found_answer"],
            }
        except Exception as e:
            logger.error(f"Query answering failed (non-critical): {e}")

        stage_timings["query"] = (datetime.utcnow() - stage_start).total_seconds()

    # =========================================================================
    # Build Final Result
    # =========================================================================
    # Mark surviving evidence as "shown" (final receipt status)
    for ev_list in evidence.values():
        for ev in ev_list:
            ev["receipt_status"] = "shown"

    results = []
    for claim in claims:
        pos = str(claim.get("position", 0))
        result = {
            "text": claim.get("text", ""),
            "position": claim.get("position", 0),
            "is_selected": claim.get("is_selected", False),
            "significance_rank": claim.get("significance_rank"),
            "significance_score": claim.get("significance_score"),
            "claim_map": claim.get("claim_map"),
            "evidence": evidence.get(pos, []),
            "subject_context": claim.get("subject_context"),
            "key_entities": claim.get("key_entities"),
            "source_title": claim.get("source_title"),
            "source_url": claim.get("source_url"),
            "source_date": claim.get("source_date"),
            "rhetorical_analysis": claim.get("rhetorical_analysis"),
            "has_rhetorical_context": claim.get("has_rhetorical_context", False),
            "rhetorical_style": claim.get("rhetorical_style"),
            "article_classification": claim.get("article_classification"),
            "claim_map_input_hash": claim.get("claim_map_input_hash"),
        }
        results.append(result)

    results.sort(key=lambda x: x.get("position", 0))

    api_stats = _aggregate_api_stats(claims, evidence)
    processing_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

    final_result = {
        "check_id": check_id,
        "status": "completed",
        "claims": results,
        "entry_mode": entry_mode,
        "selected_claims_count": len(selected_claims),
        "processing_time_ms": processing_time_ms,
        "ingest_metadata": content.get("metadata", {}),
        "query_response": query_response_data,
        "api_stats": api_stats,
        "article_excerpt": article_excerpt,
        "article_classification": (
            article_classification.to_dict() if article_classification else None
        ),
        "raw_evidence": raw_evidence_data,
        "raw_sources_count": raw_sources_count,
        "pipeline_stats": {
            "claims_extracted": len(claims),
            "claims_selected": len(selected_claims),
            "evidence_sources": sum(len(ev) for ev in evidence.values()),
            "raw_sources_reviewed": raw_sources_count,
            "stage_timings": stage_timings,
            "total_stage_time": sum(stage_timings.values()),
            "pipeline_version": "inline_sse_v4",
        },
    }

    # Evidence Loss Ledger: save artifact and attach to result
    if ledger:
        try:
            ledger.save()
            final_result["evidence_ledger"] = ledger.to_dict()
        except Exception as e:
            logger.warning(f"[LEDGER] Failed to save ledger: {e}")

    # FROZEN EVIDENCE REPLAY: Reset context var overrides
    if frozen_evidence and _replay_temp_token is not None:
        from app.pipeline.replay_context import (
            frozen_replay_temperature,
            frozen_evidence_replay,
        )

        frozen_replay_temperature.reset(_replay_temp_token)
        if _replay_evidence_token is not None:
            frozen_evidence_replay.reset(_replay_evidence_token)
        logger.info("[FROZEN EVIDENCE REPLAY] Reset replay overrides")

    logger.info(
        f"[INLINE PIPELINE] Completed in {processing_time_ms}ms for check {check_id}"
    )
    return final_result


def _aggregate_api_stats(
    claims: List[Dict[str, Any]], evidence: Dict[str, List[Dict[str, Any]]]
) -> Dict[str, Any]:
    """Aggregate API statistics across all claims."""
    all_apis_queried = []
    total_api_calls = 0
    total_api_results = 0

    for claim in claims:
        claim_api_stats = claim.get("api_stats", {})
        apis_queried = claim_api_stats.get("apis_queried", [])

        for api_info in apis_queried:
            existing_api = next(
                (a for a in all_apis_queried if a["name"] == api_info["name"]), None
            )
            if existing_api:
                existing_api["results"] += api_info.get("results", 0)
            else:
                all_apis_queried.append(
                    {"name": api_info["name"], "results": api_info.get("results", 0)}
                )

        total_api_calls += claim_api_stats.get("total_api_calls", 0)
        total_api_results += claim_api_stats.get("total_api_results", 0)

    total_evidence_count = sum(len(ev_list) for ev_list in evidence.values())
    api_evidence_count = 0

    for ev_list in evidence.values():
        for ev in ev_list:
            external_provider = ev.get("external_source_provider")
            if not external_provider and ev.get("metadata"):
                external_provider = ev.get("metadata", {}).get(
                    "external_source_provider"
                )
            if external_provider:
                api_evidence_count += 1

    api_coverage = (
        (api_evidence_count / total_evidence_count * 100)
        if total_evidence_count > 0
        else 0.0
    )

    return {
        "apis_queried": all_apis_queried,
        "total_api_calls": total_api_calls,
        "total_api_results": total_api_results,
        "api_evidence_count": api_evidence_count,
        "total_evidence_count": total_evidence_count,
        "api_coverage_percentage": round(api_coverage, 2),
    }


# ============================================================================
# Database Helpers (Async)
# ============================================================================


async def save_check_results_async(
    check_id: str, results: Dict[str, Any], session: AsyncSession
) -> None:
    """Save pipeline results to database."""
    try:
        stmt = select(Check).where(Check.id == check_id)
        result = await session.execute(stmt)
        check = result.scalar_one_or_none()

        if not check:
            logger.error(f"Check {check_id} not found in database")
            return

        check.status = "completed"
        check.completed_at = datetime.utcnow()
        check.processing_time_ms = results.get("processing_time_ms", 0)
        check.article_excerpt = results.get("article_excerpt")
        check.entry_mode = results.get("entry_mode")
        check.selected_claims_count = results.get("selected_claims_count")

        # API stats
        api_stats = results.get("api_stats")
        if api_stats:
            check.api_sources_used = api_stats.get("apis_queried", [])
            check.api_call_count = api_stats.get("total_api_calls", 0)
            check.api_coverage_percentage = api_stats.get(
                "api_coverage_percentage", 0.0
            )

        # Query response
        query_data = results.get("query_response")
        if query_data:
            check.query_response = query_data.get("answer")
            check.query_confidence = query_data.get("confidence")
            check.query_sources = {
                "sources": query_data.get("source_ids", []),
                "related_claims": query_data.get("related_claims", []),
            }

        # Article classification
        article_class = results.get("article_classification")
        if article_class:
            check.article_domain = article_class.get("primary_domain")
            check.article_secondary_domains = article_class.get("secondary_domains", [])
            check.article_jurisdiction = article_class.get("jurisdiction")
            check.article_classification_confidence = (
                int(article_class.get("confidence", 0) * 100)
                if article_class.get("confidence")
                else None
            )
            check.article_classification_source = article_class.get("source")

        # Save claims and evidence
        claims_data = results.get("claims", [])
        logger.info(f"Saving {len(claims_data)} claims for check {check_id}")

        for claim_data in claims_data:
            # Ensure numeric fields are properly typed (avoid string '0' issues)
            position_val = claim_data.get("position", 0)

            # Extract claim_type from ClaimMap if available
            claim_map_data = claim_data.get("claim_map")
            resolved_claim_type = None
            if claim_map_data and isinstance(claim_map_data, dict):
                ct = claim_map_data.get("claim_type")
                resolved_claim_type = ct.value if hasattr(ct, "value") else ct

            claim = Claim(
                check_id=check_id,
                text=claim_data.get("text", ""),
                position=int(position_val) if position_val is not None else 0,
                subject_context=claim_data.get("subject_context"),
                key_entities=(
                    claim_data.get("key_entities", [])
                    if claim_data.get("key_entities")
                    else None
                ),
                source_title=claim_data.get("source_title"),
                source_url=claim_data.get("source_url"),
                source_date=claim_data.get("source_date"),
                current_verified_data=claim_data.get("current_verified_data"),
                rhetorical_context=claim_data.get("rhetorical_analysis"),
                has_rhetorical_context=claim_data.get("has_rhetorical_context", False),
                rhetorical_style=claim_data.get("rhetorical_style"),
                claim_map_input_hash=claim_data.get("claim_map_input_hash"),
                # Claim Map system fields
                claim_map=claim_map_data,
                claim_type=resolved_claim_type,
                significance_rank=claim_data.get("significance_rank"),
                significance_score=claim_data.get("significance_score"),
                is_selected=claim_data.get("is_selected"),
            )
            session.add(claim)
            await session.flush()

            # Save evidence
            for ev_data in claim_data.get("evidence", []):
                metadata_dict = ev_data.get("metadata", {})
                # Ensure numeric fields are properly typed
                rel_score = ev_data.get("relevance_score", 0.0)
                evidence = Evidence(
                    claim_id=claim.id,
                    evidence_id=ev_data.get("evidence_id"),
                    source=ev_data.get("source", "Unknown"),
                    url=ev_data.get("url", ""),
                    title=ev_data.get("title", ""),
                    snippet=ev_data.get("snippet", ev_data.get("text", "")),
                    published_date=parse_date(ev_data.get("published_date")),
                    relevance_score=float(rel_score) if rel_score is not None else 0.0,
                    page_number=(
                        metadata_dict.get("page_number") if metadata_dict else None
                    ),
                    context_before=(
                        metadata_dict.get("context_before") if metadata_dict else None
                    ),
                    context_after=(
                        metadata_dict.get("context_after") if metadata_dict else None
                    ),
                    tier=ev_data.get("tier"),
                    evidence_type=ev_data.get("evidence_type"),
                    receipt_status=ev_data.get("receipt_status", "shown"),
                    exclusion_reason=ev_data.get("exclusion_reason"),
                    corroboration_group_id=ev_data.get("corroboration_group_id"),
                    corroborating_evidence_ids=ev_data.get(
                        "corroborating_evidence_ids"
                    ),
                    external_source_provider=ev_data.get("external_source_provider"),
                    api_metadata=metadata_dict,
                )
                session.add(evidence)

        # Save raw evidence
        raw_evidence_data = results.get("raw_evidence", [])
        raw_sources_count = results.get("raw_sources_count", len(raw_evidence_data))

        if raw_evidence_data:
            check.raw_sources_count = raw_sources_count
            for raw_ev in raw_evidence_data:
                claim_text_val = raw_ev.get("claim_text")
                if claim_text_val:
                    claim_text_val = str(claim_text_val)[:500]

                # Ensure numeric fields are properly typed
                claim_pos = raw_ev.get("claim_position", 0)
                rel_score = raw_ev.get("relevance_score", 0.0)

                raw_evidence = RawEvidence(
                    check_id=check_id,
                    claim_position=int(claim_pos) if claim_pos is not None else 0,
                    claim_text=claim_text_val,
                    source=raw_ev.get("source", "Unknown") or "Unknown",
                    url=raw_ev.get("url", "") or "",
                    title=raw_ev.get("title", "") or "",
                    snippet=raw_ev.get("snippet", "") or "",
                    published_date=parse_date(raw_ev.get("published_date")),
                    relevance_score=float(rel_score) if rel_score is not None else 0.0,
                    is_included=bool(raw_ev.get("is_included", False)),
                    filter_stage=raw_ev.get("filter_stage"),
                    filter_reason=raw_ev.get("filter_reason"),
                    tier=raw_ev.get("tier"),
                    is_factcheck=bool(raw_ev.get("is_factcheck", False)),
                    external_source_provider=raw_ev.get("external_source_provider"),
                )
                session.add(raw_evidence)

        logger.info(f"Successfully saved results for check {check_id}")

    except Exception as e:
        logger.error(f"Failed to save check results: {e}")
        import traceback

        logger.error(f"Full traceback: {traceback.format_exc()}")
        raise


async def handle_pipeline_failure(
    check_id: str, user_id: str, error: Exception
) -> None:
    """
    Handle pipeline failure - refund credit, update status, send notifications.
    """
    async with async_session() as session:
        # Refund credit
        credit_refunded = await refund_check_credit_async(check_id, user_id, session)

        # Build error message
        error_msg = get_user_friendly_error(error)
        if credit_refunded:
            error_msg = f"{error_msg}. Your credit has been returned."

        # Update status
        stmt = select(Check).where(Check.id == check_id)
        result = await session.execute(stmt)
        check = result.scalar_one_or_none()
        if check:
            check.status = "failed"
            check.error_message = error_msg

        await session.commit()

    # Send notifications (outside transaction)
    if user_id:
        try:
            push_notification_service.send_check_failed_notification_sync(
                user_id=user_id, check_id=check_id, error_message=error_msg[:100]
            )
        except Exception as e:
            logger.warning(f"Push notification failed: {e}")

        try:
            email_notification_service.send_check_failed_email_sync(
                user_id=user_id, check_id=check_id, error_message=error_msg[:200]
            )
        except Exception as e:
            logger.warning(f"Email notification failed: {e}")


async def refund_check_credit_async(
    check_id: str, user_id: str, session: AsyncSession
) -> bool:
    """Refund credit for failed check. IDEMPOTENT."""
    try:
        check_stmt = select(Check).where(Check.id == check_id)
        check_result = await session.execute(check_stmt)
        check = check_result.scalar_one_or_none()

        if not check:
            logger.error(f"Cannot refund: Check {check_id} not found")
            return False

        # Already refunded
        if check.credits_used == 0:
            logger.info(f"Check {check_id} already refunded")
            return True

        credits_to_refund = check.credits_used

        user_stmt = select(User).where(User.id == user_id)
        user_result = await session.execute(user_stmt)
        user = user_result.scalar_one_or_none()

        if not user:
            logger.error(f"Cannot refund: User {user_id} not found")
            return False

        user.credits += credits_to_refund
        check.credits_used = 0

        logger.info(f"Refunded {credits_to_refund} credit(s) for check {check_id}")
        return True

    except Exception as e:
        logger.error(f"Failed to refund credit: {e}")
        return False


async def send_success_notifications(
    user_id: str,
    check_id: str,
    results: Dict[str, Any],
    input_data: Dict[str, Any],
    content: Dict[str, Any],
) -> None:
    """Send notifications on successful completion."""
    try:
        input_url = input_data.get("url") or content.get("metadata", {}).get("url")
        input_title = content.get("metadata", {}).get("title")
        raw_sources_count = results.get("raw_sources_count", 0)
        claims = results.get("claims", [])
        selected = [c for c in claims if c.get("is_selected")]
        total_sources = (
            raw_sources_count
            if raw_sources_count > 0
            else sum(len(c.get("evidence", [])) for c in claims)
        )

        # Build claims summary from ClaimMap data
        claims_analyzed = []
        for c in selected:
            cm = c.get("claim_map") or {}
            claims_analyzed.append(
                {
                    "text": c.get("text", ""),
                    "element_count": len(cm.get("elements", [])),
                    "orientation": cm.get("orientation", ""),
                }
            )

        email_notification_service.send_check_completed_email_sync(
            user_id=user_id,
            check_id=check_id,
            claims_count=len(claims),
            entry_mode=results.get("entry_mode", "focused"),
            selected_claims_count=results.get("selected_claims_count", len(selected)),
            input_url=input_url,
            input_title=input_title,
            total_sources=total_sources,
            claims_analyzed=claims_analyzed,
        )
    except Exception as e:
        logger.warning(f"Failed to send completion email: {e}")


# reload trigger
