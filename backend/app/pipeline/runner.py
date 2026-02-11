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

import httpx  # For synchronous HTTP calls in threads

logger = logging.getLogger(__name__)

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
        return await asyncio.wait_for(
            async_func(*args, **kwargs),
            timeout=timeout
        )
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
    func = partial(_run_async_in_thread_with_timeout, async_func, timeout, *args, **kwargs)
    return await loop.run_in_executor(_executor, func)


def generate_summary_sync(
    claims: List[Dict[str, Any]],
    check_url: Optional[str] = None,
    evidence_by_claim: Optional[Dict[str, List[Dict[str, Any]]]] = None
) -> Dict[str, Any]:
    """
    Synchronous summary generation using httpx.Client (sync) with strict timeout.
    This is more reliable in thread pool than async version.
    """
    import json as _json  # Local import to avoid issues

    # Calculate statistics
    total = len(claims)
    supported = sum(1 for c in claims if c.get('verdict') == 'supported')
    contradicted = sum(1 for c in claims if c.get('verdict') == 'contradicted')

    abstention_verdicts = ['insufficient_evidence', 'conflicting_expert_opinion',
                          'outdated_claim', 'needs_primary_source', 'lacks_context']
    uncertain = sum(1 for c in claims if c.get('verdict') == 'uncertain' or
                   c.get('verdict') in abstention_verdicts)

    avg_confidence = sum(c.get('confidence', 0) for c in claims) / total if total > 0 else 0

    # Calculate credibility score
    if evidence_by_claim and total > 0:
        weighted_score = 0.0
        total_weight = 0.0

        for i, claim in enumerate(claims):
            confidence = claim.get('confidence', 50) / 100.0
            position = claim.get('position', i)
            claim_evidence = evidence_by_claim.get(str(position), [])

            if claim_evidence:
                avg_evidence_cred = sum(e.get('credibility_score', 0.6) for e in claim_evidence) / len(claim_evidence)
            else:
                avg_evidence_cred = 0.7

            claim_weight = max(0.1, confidence * avg_evidence_cred)
            verdict = claim.get('verdict', '')

            if verdict == 'supported':
                verdict_value = 100
            elif verdict == 'contradicted':
                verdict_value = 0
            elif verdict in abstention_verdicts:
                verdict_value = 30
            else:
                verdict_value = 40

            weighted_score += verdict_value * claim_weight
            total_weight += claim_weight

        credibility_score = int(weighted_score / total_weight) if total_weight > 0 else 50
    else:
        credibility_score = int(
            (supported * 100 + uncertain * 50 + contradicted * 0) / total if total > 0 else 50
        )

    fallback_summary = f"Analysis of {total} claims found {supported} supported, {contradicted} contradicted, and {uncertain} uncertain. Overall credibility score: {credibility_score}/100."

    # Build claims summary for LLM
    claims_summary = []
    for i, claim in enumerate(claims, 1):
        claims_summary.append({
            "number": i,
            "text": claim.get('text', '')[:200],
            "verdict": claim.get('verdict'),
            "confidence": claim.get('confidence')
        })

    system_prompt = "You are a fact-checking expert providing concise overall assessments."
    prompt = f"""SOURCE: {check_url or 'User-submitted content'}

CLAIMS ANALYZED: {total}
- Supported: {supported} ({supported/total*100:.1f}%)
- Contradicted: {contradicted} ({contradicted/total*100:.1f}%)
- Uncertain: {uncertain} ({uncertain/total*100:.1f}%)
- Average Confidence: {avg_confidence:.1f}%

CLAIM DETAILS:
{_json.dumps(claims_summary, indent=2)}

Generate a concise overall assessment in 2-3 sentences."""

    summary = None

    # Use synchronous httpx with strict timeout (20 seconds total)
    timeout_config = httpx.Timeout(20.0, connect=5.0)

    google_ai_key = getattr(settings, 'GOOGLE_AI_API_KEY', '')
    google_model = getattr(settings, 'GOOGLE_LLM_MODEL', 'gemini-2.5-flash-lite')

    # Try Google Gemini first
    if google_ai_key:
        try:
            full_prompt = f"{system_prompt}\n\n{prompt}"
            with httpx.Client(timeout=timeout_config) as client:
                response = client.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/{google_model}:generateContent?key={google_ai_key}",
                    headers={"Content-Type": "application/json"},
                    json={
                        "contents": [{"parts": [{"text": full_prompt}]}],
                        "generationConfig": {
                            "temperature": 0.3,
                            "maxOutputTokens": 250
                        }
                    }
                )

                if response.status_code == 200:
                    result = response.json()
                    summary = result["candidates"][0]["content"]["parts"][0]["text"].strip()
                    logger.info("Generated overall assessment with Google Gemini (sync)")
                else:
                    logger.warning(f"Google AI API error for summary: {response.status_code}")
        except httpx.TimeoutException:
            logger.warning("Google API timed out for summary")
        except Exception as e:
            logger.warning(f"Google summary generation failed: {e}")

    # Fallback: OpenAI
    if summary is None and settings.OPENAI_API_KEY:
        try:
            logger.info("Attempting OpenAI summary generation as fallback (sync)")
            with httpx.Client(timeout=timeout_config) as client:
                response = client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "gpt-4o-mini-2024-07-18",
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": prompt}
                        ],
                        "max_tokens": 250,
                        "temperature": 0.3
                    }
                )

                if response.status_code == 200:
                    result = response.json()
                    summary = result["choices"][0]["message"]["content"].strip()
                    logger.info("Generated overall assessment with OpenAI fallback (sync)")
                else:
                    logger.error(f"OpenAI API error for summary: {response.status_code}")
        except httpx.TimeoutException:
            logger.warning("OpenAI API timed out for summary")
        except Exception as e:
            logger.error(f"OpenAI summary generation failed: {e}")

    # Use fallback if both failed
    if summary is None:
        summary = fallback_summary
        logger.info("Using fallback summary (no LLM response)")

    return {
        "summary": summary,
        "credibility_score": credibility_score,
        "claims_supported": supported,
        "claims_contradicted": contradicted,
        "claims_uncertain": uncertain
    }


# User-friendly error messages
USER_FRIENDLY_ERRORS = {
    "cookie_consent_wall": "This website requires cookie consent which we cannot bypass. Please try pasting the article text directly.",
    "paywall": "This article is behind a paywall. Please try pasting the article text directly.",
    "connection_error": "We couldn't reach this website. Please check the URL and try again.",
    "no_claims": "We couldn't extract any verifiable claims from this content. Please try different content.",
    "timeout": "The request took too long to complete. Please try again.",
}


def get_user_friendly_error(error: Exception) -> str:
    """Convert technical errors to user-friendly messages."""
    error_str = str(error).lower()
    for key, message in USER_FRIENDLY_ERRORS.items():
        if key in error_str:
            return message
    return str(error)


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
    progress_reporter: ProgressReporter
) -> Dict[str, Any]:
    """
    Run the fact-checking pipeline inline with progress streaming.

    Reuses the battle-tested functions from workers/pipeline.py,
    running them in a thread pool with isolated event loops.
    """
    # Import the existing functions from workers/pipeline.py
    from app.workers.pipeline import (
        ingest_content_async,
        extract_claims_with_cache,
        retrieve_evidence_with_cache,
        judge_claims_with_llm,
        generate_overall_assessment,
        search_factchecks_for_claims,
    )
    from app.utils.article_classifier import classify_article
    from app.pipeline.judge import get_pipeline_judge
    from app.services.search import warmup_search_providers

    # Warmup search providers to prevent 10s cold-start delay
    # (Same as Celery worker does at startup - critical for inline execution)
    warmup_search_providers()

    # DIAGNOSTIC: Check if search API keys are configured
    from app.services.search import SearchService
    search_svc = SearchService()
    provider_names = [p.__class__.__name__ for p in search_svc.providers]
    if not search_svc.providers:
        logger.warning(f"[INLINE PIPELINE] WARNING: No search providers configured! Set BRAVE_API_KEY or SERP_API_KEY")
    else:
        logger.info(f"[INLINE PIPELINE] Search providers available: {provider_names}")

    start_time = datetime.utcnow()
    stage_timings = {}

    # Evidence Loss Ledger (PR 0 — observability only, no logic changes)
    from app.pipeline.evidence_ledger import get_ledger
    ledger = get_ledger(check_id)

    # Initialize cache service for evidence caching
    # This reduces non-determinism by reusing good quality evidence for identical claims
    # Quality gates in retrieve_evidence_with_cache ensure only good results are cached
    try:
        cache_service = await get_cache_service()
        logger.info(f"[INLINE PIPELINE] Cache service initialized successfully")
    except Exception as e:
        logger.warning(f"[INLINE PIPELINE] Cache service initialization failed, continuing without cache: {e}")
        cache_service = None

    logger.info(f"[INLINE PIPELINE] Starting for check {check_id}")

    # =========================================================================
    # Stage 1: Ingest
    # =========================================================================
    await progress_reporter.report_progress("ingest")
    stage_start = datetime.utcnow()

    try:
        # Await directly in FastAPI's event loop - simpler and more reliable
        content = await ingest_content_async(input_data)
    except Exception as e:
        logger.error(f"[INLINE PIPELINE] Ingest failed: {e}")
        import traceback
        logger.error(f"[INLINE PIPELINE] Ingest traceback: {traceback.format_exc()}")
        raise PipelineError(get_user_friendly_error(e), stage="ingest")

    if not content.get("success"):
        error_msg = content.get("message") or content.get("error", "Unknown error")
        raise PipelineError(get_user_friendly_error(Exception(error_msg)), stage="ingest")

    stage_timings["ingest"] = (datetime.utcnow() - stage_start).total_seconds()
    logger.info(f"[INLINE PIPELINE] Ingested content, length: {len(content.get('content', ''))}")

    # =========================================================================
    # Stage 2: Extract Claims
    # =========================================================================
    await progress_reporter.report_progress("extract")
    stage_start = datetime.utcnow()

    extract_content = content.get("content", "")
    extract_metadata = content.get("metadata", {})

    # Article classification (optional)
    article_classification = None
    if settings.ENABLE_ARTICLE_CLASSIFICATION:
        try:
            # Direct await - classify_article is async
            article_classification = await classify_article(
                title=extract_metadata.get("title", "") if extract_metadata else "",
                url=extract_metadata.get("url", "") if extract_metadata else "",
                content=extract_content[:2000]
            )
            logger.info(f"[INLINE PIPELINE] Article classified: {article_classification.primary_domain}")
        except Exception as e:
            logger.warning(f"Article classification failed: {e}")

    # Extract claims
    try:
        # Direct await - extract_claims_with_cache is async
        claims = await extract_claims_with_cache(
            extract_content,
            extract_metadata,
            cache_service
        )
    except Exception as e:
        logger.error(f"[INLINE PIPELINE] Claim extraction failed: {e}")
        raise PipelineError(get_user_friendly_error(e), stage="extract")

    if not claims:
        raise PipelineError("No claims extracted from content", stage="extract")

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

    frozen_evidence = input_data.get("frozen_evidence")  # Dict[claim_key_or_pos, List[Dict]]
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

            # Match by claim_key first, position fallback
            evidence_items = frozen_evidence.get(key) or frozen_evidence.get(pos)
            if evidence_items is None:
                logger.warning(f"[FROZEN EVIDENCE REPLAY] No frozen evidence for claim {pos} (key={key[:12]})")
                continue

            # Mismatch guard: verify claim text matches
            expected_text = frozen_evidence_claim_texts.get(key, frozen_evidence_claim_texts.get(pos, ""))
            if expected_text:
                norm_expected = " ".join(expected_text.lower().split())
                norm_actual = " ".join(claim_text.lower().split())
                if norm_expected != norm_actual:
                    frozen_replay_mismatches += 1
                    logger.warning(f"[FROZEN EVIDENCE REPLAY MISMATCH] Claim {pos}: "
                                   f"expected='{expected_text[:80]}...' actual='{claim_text[:80]}...'")
                    continue

            claim["frozen_evidence"] = evidence_items
            attached_count += 1

        # Request-scoped overrides (concurrency-safe)
        from app.pipeline.replay_context import frozen_replay_temperature, frozen_evidence_replay
        _replay_temp_token = frozen_replay_temperature.set(0.0)
        _replay_evidence_token = frozen_evidence_replay.set(True)

        logger.info(f"[FROZEN EVIDENCE REPLAY] Attached to {attached_count}/{len(claims)} claims"
                     f"{f', {frozen_replay_mismatches} mismatches' if frozen_replay_mismatches else ''}")

        if ledger:
            ledger.record("frozen_evidence_replay", attached=attached_count,
                           mismatches=frozen_replay_mismatches)

    # FROZEN REPLAY: Attach frozen URLs to claims for deterministic replay
    frozen_urls = input_data.get("frozen_urls")
    frozen_claim_texts = input_data.get("frozen_claim_texts") or {}
    frozen_replay_mismatches = 0
    _frozen_temp_overrides = {}
    if frozen_urls:
        attached_count = 0
        for claim in claims:
            pos = str(claim.get("position", 0))
            if pos in frozen_urls:
                # Mismatch guard: verify stored claim text matches extracted claim text
                expected_text = frozen_claim_texts.get(pos, "")
                actual_text = claim.get("text", "")
                if expected_text:
                    norm_expected = " ".join(expected_text.lower().split())
                    norm_actual = " ".join(actual_text.lower().split())
                    if norm_expected != norm_actual:
                        frozen_replay_mismatches += 1
                        logger.warning(
                            f"[FROZEN REPLAY MISMATCH] Claim {pos}: "
                            f"expected='{expected_text[:80]}...' "
                            f"actual='{actual_text[:80]}...' — skipping freeze for this claim"
                        )
                        continue  # Skip freeze, run normal search
                claim["frozen_urls"] = frozen_urls[pos]
                attached_count += 1
        logger.info(f"[FROZEN REPLAY] Attached frozen URLs to {attached_count}/{len(claims)} claims"
                     f"{f', {frozen_replay_mismatches} mismatches skipped' if frozen_replay_mismatches else ''}")

        # Force deterministic settings for frozen replay
        import os
        for env_key in ("JUDGE_TEMPERATURE", "LLM_RELEVANCE_TEMPERATURE"):
            _frozen_temp_overrides[env_key] = os.environ.get(env_key)
            os.environ[env_key] = "0"
        # Auto-skip gov APIs to eliminate non-frozen variance
        _frozen_temp_overrides["FROZEN_REPLAY_SKIP_GOV_APIS"] = os.environ.get("FROZEN_REPLAY_SKIP_GOV_APIS")
        os.environ["FROZEN_REPLAY_SKIP_GOV_APIS"] = "1"
        logger.info("[FROZEN REPLAY] Forced temperature=0 + skip gov APIs for determinism")

        if ledger:
            ledger.record("frozen_replay", attached=attached_count,
                          mismatches=frozen_replay_mismatches,
                          total_positions=len(frozen_urls))

    stage_timings["extract"] = (datetime.utcnow() - stage_start).total_seconds()
    logger.info(f"[INLINE PIPELINE] Extracted {len(claims)} claims")

    # =========================================================================
    # Stage 2.5: Fact-check Lookup (optional, skipped for frozen replay)
    # =========================================================================
    factcheck_evidence = {}
    if frozen_urls or frozen_evidence:
        logger.info("[FROZEN REPLAY] Skipping fact-check API for deterministic replay")
    elif settings.ENABLE_FACTCHECK_API:
        await progress_reporter.report_progress("factcheck")
        stage_start = datetime.utcnow()
        try:
            # Direct await - search_factchecks_for_claims is async
            factcheck_evidence = await search_factchecks_for_claims(claims)
            logger.info(f"[INLINE PIPELINE] Found {sum(len(v) for v in factcheck_evidence.values())} fact-checks")
        except Exception as e:
            logger.warning(f"Fact-check lookup failed (non-critical): {e}")
        stage_timings["factcheck"] = (datetime.utcnow() - stage_start).total_seconds()

    # =========================================================================
    # Stage 3: Retrieve Evidence
    # =========================================================================
    await progress_reporter.report_progress("retrieve")
    stage_start = datetime.utcnow()

    source_url = content.get("metadata", {}).get("url")
    retrieve_timeout = 180  # 180 seconds (3 min) for evidence retrieval - increased from 90s

    # V2 FROZEN EVIDENCE REPLAY: Build evidence dict directly from frozen data,
    # bypassing retrieve entirely. The frozen evidence is already post-filtering
    # (captured at judge_input stage), so no further processing is needed.
    _v2_frozen_bypass = frozen_evidence and any(claim.get("frozen_evidence") for claim in claims)

    if _v2_frozen_bypass:
        evidence = {}
        for claim in claims:
            pos = str(claim.get("position", 0))
            frozen_items = claim.get("frozen_evidence", [])
            evidence[pos] = frozen_items  # Already post-filtering, use as-is
        raw_evidence_data = []
        raw_sources_count = 0
        total_frozen = sum(len(ev) for ev in evidence.values())
        logger.info(f"[FROZEN EVIDENCE REPLAY] Built evidence directly: {total_frozen} items for {len(evidence)} claims (retrieve bypassed)")
        print(f"[FROZEN EVIDENCE REPLAY] Direct evidence injection: {total_frozen} items (retrieve bypassed)", flush=True)
        stage_timings["retrieve"] = 0.0
        if ledger:
            ledger.record("retrieve", total=total_frozen,
                           per_claim={pos: len(ev) for pos, ev in evidence.items()},
                           mode="frozen_evidence_direct")
    else:
        # Track when retrieve actually starts
        import time as _time
        _retrieve_start = _time.time()

        # CRITICAL DIAGNOSTIC: Print to stdout to ensure visibility even if logging fails
        print(f"\n{'#'*70}", flush=True)
        print(f"[RETRIEVE STAGE] Starting for check {check_id} at {_retrieve_start:.2f}", flush=True)
        print(f"[RETRIEVE STAGE] Claims to process: {len(claims)}", flush=True)
        print(f"[RETRIEVE STAGE] Timeout set to: {retrieve_timeout}s", flush=True)

        # Check search provider configuration
        from app.services.search import SearchService
        _diag_search = SearchService()
        _diag_providers = [p.__class__.__name__ for p in _diag_search.providers]
        print(f"[RETRIEVE STAGE] WEB SEARCH PROVIDERS: {_diag_providers if _diag_providers else '*** NONE CONFIGURED ***'}", flush=True)
        if not _diag_providers:
            print(f"[RETRIEVE STAGE] WARNING: Set BRAVE_API_KEY or SERP_API_KEY for web search!", flush=True)

        # Check API adapter configuration
        from app.services.government_api_client import get_api_registry
        _diag_registry = get_api_registry()
        _diag_adapters = [a.api_name for a in _diag_registry.get_all_adapters()]
        print(f"[RETRIEVE STAGE] API ADAPTERS: {len(_diag_adapters)} configured - {_diag_adapters[:5]}{'...' if len(_diag_adapters) > 5 else ''}", flush=True)
        print(f"{'#'*70}\n", flush=True)

        logger.critical(f"[RETRIEVE STAGE] Starting for check {check_id} with {len(claims)} claims")

        try:
            logger.info(f"[INLINE PIPELINE] Starting evidence retrieval with {retrieve_timeout}s timeout")
            # Use asyncio.wait_for directly instead of thread pool - simpler and more reliable
            # Thread pool was causing issues with async httpx clients
            retrieval_result = await asyncio.wait_for(
                retrieve_evidence_with_cache(
                    claims,
                    cache_service,
                    factcheck_evidence,
                    source_url=source_url
                ),
                timeout=retrieve_timeout
            )
            _retrieve_elapsed = _time.time() - _retrieve_start
            print(f"\n[RETRIEVE SUCCESS] Completed in {_retrieve_elapsed:.2f}s", flush=True)
            logger.info(f"[INLINE PIPELINE] Evidence retrieval completed in {_retrieve_elapsed:.2f}s")
        except asyncio.TimeoutError:
            _retrieve_elapsed = _time.time() - _retrieve_start
            print(f"\n[RETRIEVE TIMEOUT] Timed out after {_retrieve_elapsed:.2f}s (limit was {retrieve_timeout}s)", flush=True)
            logger.warning(f"[INLINE PIPELINE] Evidence retrieval timed out after {_retrieve_elapsed:.2f}s (limit={retrieve_timeout}s), continuing with empty evidence")
            retrieval_result = {"evidence_by_claim": {}, "raw_evidence": [], "raw_sources_count": 0}
        except Exception as e:
            logger.error(f"[INLINE PIPELINE] Evidence retrieval failed: {e}")
            import traceback
            logger.error(f"[INLINE PIPELINE] Full traceback: {traceback.format_exc()}")
            if settings.ENVIRONMENT == "development":
                retrieval_result = {"evidence_by_claim": {}, "raw_evidence": [], "raw_sources_count": 0}
            else:
                raise PipelineError(f"Evidence retrieval failed: {e}", stage="retrieve")

        # Handle result format
        if isinstance(retrieval_result, dict) and "evidence_by_claim" in retrieval_result:
            evidence = retrieval_result["evidence_by_claim"]
            raw_evidence_data = retrieval_result.get("raw_evidence", [])
            raw_sources_count = retrieval_result.get("raw_sources_count", 0)
        else:
            evidence = retrieval_result if isinstance(retrieval_result, dict) else {}
            raw_evidence_data = []
            raw_sources_count = 0

        stage_timings["retrieve"] = (datetime.utcnow() - stage_start).total_seconds()

        # Save pre-weighting evidence to ledger (for freeze capture)
        pre_weighting_evidence = retrieval_result.get("pre_weighting_evidence", {}) if isinstance(retrieval_result, dict) else {}
        if ledger and pre_weighting_evidence:
            ledger.record("pre_weighting_evidence", evidence=pre_weighting_evidence)

    # DIAGNOSTIC: Log evidence counts per claim to debug filtering
    total_evidence = sum(len(ev) for ev in evidence.values())
    logger.critical(f"[INLINE PIPELINE] *** EVIDENCE SUMMARY: {total_evidence} total items for {len(evidence)} claims ***")
    print(f"[INLINE PIPELINE STDOUT] *** EVIDENCE: {total_evidence} total items for {len(evidence)} claims ***", flush=True)
    for pos, ev_list in evidence.items():
        logger.info(f"[INLINE PIPELINE] Claim {pos}: {len(ev_list)} evidence items")
    if total_evidence == 0:
        logger.critical(f"[INLINE PIPELINE] CRITICAL: No evidence retrieved for any claim! Check search providers.")
        print(f"[INLINE PIPELINE STDOUT] CRITICAL: Zero evidence retrieved!", flush=True)

    if ledger:
        ledger.record("retrieve", total=total_evidence,
                       per_claim={pos: len(ev) for pos, ev in evidence.items()})
        # Aggregate per-claim filter stats from raw evidence tracking
        if raw_evidence_data:
            from collections import Counter
            claim_filter_counts: dict = {}
            for raw_item in raw_evidence_data:
                pos = str(raw_item.get("claim_position", "?"))
                if pos not in claim_filter_counts:
                    claim_filter_counts[pos] = {"total_raw": 0, "included": 0, "excluded_by_stage": Counter()}
                claim_filter_counts[pos]["total_raw"] += 1
                if raw_item.get("is_included"):
                    claim_filter_counts[pos]["included"] += 1
                elif raw_item.get("filter_stage"):
                    claim_filter_counts[pos]["excluded_by_stage"][raw_item["filter_stage"]] += 1
            # Count unknown-domain items filtered at credibility stage
            unknown_domain_filtered = 0
            for raw_item in raw_evidence_data:
                if not raw_item.get("is_included"):
                    cred = raw_item.get("credibility_score")
                    if isinstance(cred, (int, float)) and cred <= 0.40:
                        unknown_domain_filtered += 1
            for pos, stats in claim_filter_counts.items():
                ledger.record_claim(pos, "credibility_weighting",
                                    total_raw=stats["total_raw"],
                                    included=stats["included"],
                                    excluded_by_stage=dict(stats["excluded_by_stage"]))
            ledger.record("credibility_filtering",
                          unknown_domain_filtered=unknown_domain_filtered,
                          total_raw=sum(s["total_raw"] for s in claim_filter_counts.values()),
                          total_included=sum(s["included"] for s in claim_filter_counts.values()))

    # =========================================================================
    # Stage 3.5: Fact-check Parsing (optional)
    # =========================================================================
    if settings.ENABLE_FACTCHECK_PARSING and evidence:
        stage_start = datetime.utcnow()
        try:
            from app.services.factcheck_parser import get_factcheck_parser
            parser = get_factcheck_parser()
            # Direct await - parse_factcheck_evidence is async
            evidence = await parser.parse_factcheck_evidence(claims, evidence)
        except Exception as e:
            logger.warning(f"Fact-check parsing failed (non-critical): {e}")
        stage_timings["factcheck_parse"] = (datetime.utcnow() - stage_start).total_seconds()

    # =========================================================================
    # Stage 3.6: Cross-Claim URL Deduplication
    # =========================================================================
    # IMPORTANT: Same article URL must only appear ONCE across all claims.
    # This prevents the same source being used to "prove" multiple claims,
    # which creates appearance of bias and reduces source diversity.
    # This runs BEFORE global domain capping so the capper works with clean data.
    #
    # V2 frozen evidence replay: skip Stages 3.6, 3.7, 3.8 entirely.
    # Frozen evidence is already post-filtering (captured at judge_input stage).
    from app.pipeline.replay_context import frozen_evidence_replay as _fer_var
    _is_frozen_evidence_replay = _fer_var.get(False)

    if _is_frozen_evidence_replay and evidence:
        logger.info(f"[URL DEDUP] SKIPPED — V2 frozen evidence replay (deterministic bypass)")
    elif evidence:
        stage_start = datetime.utcnow()
        try:
            # Flatten all evidence with claim tracking
            # Allow each URL to appear in up to MAX_CLAIMS_PER_URL claims (default 1 = old behavior)
            max_claims_per_url = getattr(settings, 'MAX_CLAIMS_PER_URL', 1)
            url_claims = {}  # url -> [(claim_pos, evidence_item, score), ...]
            dedup_losers = [] if ledger else None  # Track casualties for ledger

            for claim_pos, ev_list in evidence.items():
                for ev in ev_list:
                    url = ev.get('url', '')
                    if not url:
                        continue

                    score = ev.get('final_score', ev.get('combined_score', ev.get('credibility_score', 0)))

                    if url not in url_claims:
                        url_claims[url] = [(claim_pos, ev, score)]
                    elif len(url_claims[url]) < max_claims_per_url:
                        # Under the limit — keep this copy too
                        url_claims[url].append((claim_pos, ev, score))
                    else:
                        # At the limit — drop the weakest copy (keep-best)
                        # Deterministic tie-break: lower claim_pos wins
                        entries = url_claims[url] + [(claim_pos, ev, score)]
                        entries.sort(key=lambda x: (-x[2], x[0]))  # score DESC, claim_pos ASC
                        url_claims[url] = entries[:max_claims_per_url]
                        loser = entries[max_claims_per_url]
                        winner = entries[0]
                        logger.debug(f"[URL DEDUP] Dropped {url[:60]} from claim {loser[0]} (score {loser[2]:.2f}), kept in {[e[0] for e in entries[:max_claims_per_url]]}")
                        if dedup_losers is not None:
                            dedup_losers.append({"url": url[:120], "loser": loser[0], "winner": winner[0]})

            # Rebuild evidence_by_claim from url_claims
            deduped_evidence = {pos: [] for pos in evidence.keys()}
            for url, entries in url_claims.items():
                for claim_pos, ev, score in entries:
                    deduped_evidence[claim_pos].append(ev)

            # Count what was removed
            before_count = sum(len(ev_list) for ev_list in evidence.values())
            after_count = sum(len(ev_list) for ev_list in deduped_evidence.values())
            removed_count = before_count - after_count

            if removed_count > 0:
                logger.info(f"[URL DEDUP] Removed {removed_count} duplicate URLs across claims: {before_count} → {after_count}")
                print(f"[PIPELINE] Cross-claim URL dedup: removed {removed_count} duplicates", flush=True)
            else:
                logger.info(f"[URL DEDUP] No cross-claim duplicates found ({after_count} unique URLs)")

            evidence = deduped_evidence

            if ledger:
                casualties_per_claim = {}
                if dedup_losers:
                    for entry in dedup_losers:
                        lc = entry["loser"]
                        if lc not in casualties_per_claim:
                            casualties_per_claim[lc] = []
                        casualties_per_claim[lc].append({"url": entry["url"], "won_by": entry["winner"]})
                ledger.record("url_dedup", in_count=before_count, out_count=after_count,
                              removed=removed_count, casualties_per_claim=casualties_per_claim)

        except Exception as e:
            logger.warning(f"Cross-claim URL deduplication failed (non-critical): {e}")
        stage_timings["url_dedup"] = (datetime.utcnow() - stage_start).total_seconds()

    # =========================================================================
    # Stage 3.7: LLM Relevance Scoring with Reassignment
    # =========================================================================
    # IMPORTANT: This stage now REASSIGNS evidence to correct claims based on
    # what the LLM determines each evidence actually helps verify.
    # This runs BEFORE domain capping so capping operates on correctly-assigned evidence.
    #
    # SKIP during V2 frozen evidence replay: frozen evidence is already in
    # correct claim buckets from the baseline run. Re-scoring would introduce
    # LLM nondeterminism and break evidence determinism.
    if _is_frozen_evidence_replay and evidence:
        logger.info(f"[LLM SCORER] SKIPPED — V2 frozen evidence replay (deterministic bypass)")
        if ledger:
            count_frozen = sum(len(ev_list) for ev_list in evidence.values())
            ledger.record("llm_scoring", in_count=count_frozen, out_count=count_frozen,
                          note="skipped_frozen_replay")
    elif settings.ENABLE_LLM_RELEVANCE_SCORER and evidence:
        stage_start = datetime.utcnow()
        count_before_scoring = sum(len(ev_list) for ev_list in evidence.values())
        try:
            from app.pipeline.relevance_scorer import score_evidence_batch
            article_excerpt = content.get("content", "")[:5000]
            claim_texts = [c.get("text", "") for c in claims]
            # Direct await - score_evidence_batch is async
            evidence = await score_evidence_batch(
                claims=claim_texts,
                evidence=evidence,
                article_context=article_excerpt
            )

            count_after_scoring = sum(len(ev_list) for ev_list in evidence.values())
            # Note: Count may increase due to reassignment (evidence can go to multiple claims)
            # Domain capping in the next stage will handle this
            logger.info(f"[LLM SCORER] Evidence after scoring/reassignment: {count_before_scoring} → {count_after_scoring}")

            if ledger:
                ledger.record("llm_scoring", in_count=count_before_scoring, out_count=count_after_scoring)

        except Exception as e:
            logger.warning(f"LLM relevance scoring failed (non-critical): {e}")
        stage_timings["llm_relevance"] = (datetime.utcnow() - stage_start).total_seconds()

    # =========================================================================
    # Stage 3.8: Global Domain Capping
    # =========================================================================
    # IMPORTANT: This limits any single domain to appear at most GLOBAL_MAX_PER_DOMAIN
    # times (default 3) or GLOBAL_MAX_DOMAIN_RATIO of total evidence (default 15%).
    # This prevents bias where one source dominates the fact-check.
    # Runs AFTER LLM scoring so it operates on correctly-assigned evidence.
    #
    # SKIP during V2 frozen evidence replay: frozen evidence is already
    # post-capping (captured at judge_input stage).
    if _is_frozen_evidence_replay and evidence:
        logger.info(f"[GLOBAL CAP] SKIPPED — V2 frozen evidence replay (deterministic bypass)")
    elif settings.ENABLE_GLOBAL_DOMAIN_CAPPING and evidence:
        stage_start = datetime.utcnow()
        try:
            from app.utils.domain_capping import DomainCapper
            from app.utils.url_utils import extract_domain

            # Log domain distribution BEFORE capping
            domain_counts_before = {}
            for ev_list in evidence.values():
                for ev in ev_list:
                    domain = extract_domain(ev.get('url', ''), fallback='unknown')
                    domain_counts_before[domain] = domain_counts_before.get(domain, 0) + 1

            total_before = sum(domain_counts_before.values())
            logger.info(f"[GLOBAL CAP] BEFORE: {total_before} evidence items, domains: {dict(sorted(domain_counts_before.items(), key=lambda x: -x[1])[:5])}")
            print(f"[PIPELINE] Domain cap BEFORE: {total_before} items, top domains: {dict(sorted(domain_counts_before.items(), key=lambda x: -x[1])[:3])}", flush=True)

            global_capper = DomainCapper()
            evidence = global_capper.apply_global_caps(
                evidence,
                global_max_per_domain=settings.GLOBAL_MAX_PER_DOMAIN,
                global_max_ratio=settings.GLOBAL_MAX_DOMAIN_RATIO
            )

            # Log domain distribution AFTER capping
            domain_counts_after = {}
            for ev_list in evidence.values():
                for ev in ev_list:
                    domain = extract_domain(ev.get('url', ''), fallback='unknown')
                    domain_counts_after[domain] = domain_counts_after.get(domain, 0) + 1

            total_after = sum(domain_counts_after.values())
            removed = total_before - total_after
            logger.info(f"[GLOBAL CAP] AFTER: {total_after} evidence items (removed {removed}), domains: {dict(sorted(domain_counts_after.items(), key=lambda x: -x[1])[:5])}")
            print(f"[PIPELINE] Domain cap AFTER: {total_after} items (removed {removed})", flush=True)

            if ledger:
                # Record which domains were capped
                caps_applied = {d: {"before": domain_counts_before.get(d, 0), "after": domain_counts_after.get(d, 0)}
                                for d in domain_counts_before if domain_counts_before[d] != domain_counts_after.get(d, 0)}
                ledger.record("global_domain_cap", in_count=total_before, out_count=total_after,
                               removed=removed, caps_applied=caps_applied)

        except Exception as e:
            logger.warning(f"Global domain capping failed (non-critical): {e}")
            import traceback
            logger.debug(f"Global domain capping traceback: {traceback.format_exc()}")
        stage_timings["global_domain_cap"] = (datetime.utcnow() - stage_start).total_seconds()
    elif not settings.ENABLE_GLOBAL_DOMAIN_CAPPING:
        logger.warning("[GLOBAL CAP] DISABLED via settings - domain diversity not enforced!")
        print("[PIPELINE] WARNING: Global domain capping is DISABLED", flush=True)

    # =========================================================================
    # Stage 5: Judge Claims
    # =========================================================================
    await progress_reporter.report_progress("judge")
    stage_start = datetime.utcnow()

    # FINAL EVIDENCE SUMMARY - Log what the Judge will use
    # This confirms the diversity cascade (URL dedup → domain cap → relevance filter) worked
    from app.utils.url_utils import extract_domain
    final_evidence_count = sum(len(ev_list) for ev_list in evidence.values())
    final_domains = {}
    final_urls = set()
    for ev_list in evidence.values():
        for ev in ev_list:
            domain = extract_domain(ev.get('url', ''), fallback='unknown')
            final_domains[domain] = final_domains.get(domain, 0) + 1
            final_urls.add(ev.get('url', ''))

    logger.info(f"[JUDGE INPUT] Final evidence for judge: {final_evidence_count} items, {len(final_urls)} unique URLs, {len(final_domains)} domains")
    logger.info(f"[JUDGE INPUT] Domain distribution: {dict(sorted(final_domains.items(), key=lambda x: -x[1]))}")
    print(f"[PIPELINE] JUDGE INPUT: {final_evidence_count} evidence items from {len(final_domains)} domains", flush=True)

    # Warn if any domain still appears too many times (indicates capping may have failed)
    max_domain_count = max(final_domains.values()) if final_domains else 0
    if max_domain_count > settings.GLOBAL_MAX_PER_DOMAIN:
        logger.warning(f"[JUDGE INPUT] WARNING: Domain appears {max_domain_count} times, exceeds cap of {settings.GLOBAL_MAX_PER_DOMAIN}")

    if ledger:
        snippet_fallback_count = 0
        snippet_reasons = {"403": 0, "429": 0, "timeout": 0, "js_required": 0, "other": 0}
        title_only_count = 0
        unknown_domain_count = 0
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
                cred = ev.get("credibility_score", 1.0)
                if isinstance(cred, (int, float)) and cred <= 0.40:
                    unknown_domain_count += 1
        ledger.record("judge_input", total=final_evidence_count,
                       unique_urls=len(final_urls),
                       domains=dict(sorted(final_domains.items(), key=lambda x: -x[1])),
                       snippet_fallbacks=snippet_fallback_count,
                       snippet_fallback_reasons=snippet_reasons,
                       title_only_items=title_only_count,
                       unknown_domain_items=unknown_domain_count)
        # Record actual evidence dicts for V2 frozen replay (judge sees these exact items)
        ledger.record("judge_input_evidence", evidence={
            pos: [dict(ev) for ev in ev_list] for pos, ev_list in evidence.items()
        })

    article_excerpt = content.get("content", "")[:5000]
    judge_timeout = min(15 * len(claims), 120)  # Same timeout as Celery

    # PATH_A logging: show what the judge is about to receive
    if getattr(settings, 'ENABLE_PATH_A', False):
        judge_input_count = sum(len(ev_list) for ev_list in evidence.items())
        per_claim = {pos: len(ev_list) for pos, ev_list in evidence.items()}
        logger.info(
            f"[PATH_A] Judge receiving {judge_input_count} evidence items "
            f"(no relevance veto, no pre-judge abstention). Per-claim: {per_claim}"
        )

    try:
        logger.info(f"[INLINE PIPELINE] Starting judge with {judge_timeout}s timeout for {len(claims)} claims")
        # Direct await with asyncio.wait_for for timeout - judge_claims_with_llm is async
        results = await asyncio.wait_for(
            judge_claims_with_llm(
                claims, evidence, article_context=article_excerpt
            ),
            timeout=judge_timeout
        )
        logger.info(f"[INLINE PIPELINE] Judge completed successfully")
    except asyncio.TimeoutError:
        logger.error(f"[INLINE PIPELINE] Judge timed out after {judge_timeout}s")
        raise PipelineError("LLM judgment timed out", stage="judge")
    except Exception as e:
        logger.error(f"[INLINE PIPELINE] Judge failed: {e}")
        raise PipelineError(f"LLM judgment failed: {e}", stage="judge")

    results.sort(key=lambda x: x.get("position", 0))
    stage_timings["judge"] = (datetime.utcnow() - stage_start).total_seconds()
    logger.info(f"[INLINE PIPELINE] Judged {len(results)} claims")

    # =========================================================================
    # Stage 5.5: Query Answering (optional)
    # =========================================================================
    query_response_data = None
    if input_data.get("user_query") and settings.ENABLE_SEARCH_CLARITY:
        await progress_reporter.report_progress("query")
        stage_start = datetime.utcnow()

        try:
            from app.pipeline.query_answer import get_query_answerer

            # Direct await - get_query_answerer and answer_query are async
            query_answerer = await get_query_answerer()
            query_result = await query_answerer.answer_query(
                user_query=input_data.get("user_query"),
                claims=claims,
                evidence_by_claim=evidence,
                original_text=content.get("content", "")[:1000]
            )
            query_response_data = {
                "answer": query_result["answer"],
                "confidence": query_result["confidence"],
                "source_ids": query_result["source_ids"],
                "related_claims": query_result["related_claims"],
                "found_answer": query_result["found_answer"]
            }
        except Exception as e:
            logger.error(f"Query answering failed (non-critical): {e}")

        stage_timings["query"] = (datetime.utcnow() - stage_start).total_seconds()

    # =========================================================================
    # Stage 6: Enhanced Explainability (optional)
    # =========================================================================
    if settings.ENABLE_ENHANCED_EXPLAINABILITY:
        from app.utils.explainability import ExplainabilityEnhancer
        explainer = ExplainabilityEnhancer()
        results = _add_explainability(results, evidence, explainer)

    # =========================================================================
    # Stage 6.5: Overall Assessment
    # =========================================================================
    await progress_reporter.report_progress("summary")
    stage_start = datetime.utcnow()

    # Use fallback summary (LLM summary hangs in thread pool executor)
    # TODO: Fix generate_summary_sync to work with run_in_executor
    total = len(results)
    supported = sum(1 for c in results if c.get("verdict") == "supported")
    contradicted = sum(1 for c in results if c.get("verdict") == "contradicted")
    uncertain = total - supported - contradicted
    assessment = {
        "summary": f"Analysis of {total} claims found {supported} supported, {contradicted} contradicted, and {uncertain} uncertain. Review the individual claims for detailed verdicts and evidence.",
        "credibility_score": int((supported * 100 + uncertain * 50) / total) if total > 0 else 50,
        "claims_supported": supported,
        "claims_contradicted": contradicted,
        "claims_uncertain": uncertain
    }
    logger.info(f"[INLINE PIPELINE] Summary generation completed (fallback)")

    stage_timings["summary"] = (datetime.utcnow() - stage_start).total_seconds()

    # =========================================================================
    # Build Final Result
    # =========================================================================
    api_stats = _aggregate_api_stats(claims, evidence)
    processing_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

    final_result = {
        "check_id": check_id,
        "status": "completed",
        "claims": results,
        "overall_summary": assessment["summary"],
        "credibility_score": assessment["credibility_score"],
        "claims_supported": assessment["claims_supported"],
        "claims_contradicted": assessment["claims_contradicted"],
        "claims_uncertain": assessment["claims_uncertain"],
        "processing_time_ms": processing_time_ms,
        "ingest_metadata": content.get("metadata", {}),
        "query_response": query_response_data,
        "api_stats": api_stats,
        "article_excerpt": article_excerpt,
        "article_classification": article_classification.to_dict() if article_classification else None,
        "raw_evidence": raw_evidence_data,
        "raw_sources_count": raw_sources_count,
        "pipeline_stats": {
            "claims_extracted": len(claims),
            "evidence_sources": sum(len(ev) for ev in evidence.values()),
            "raw_sources_reviewed": raw_sources_count,
            "stage_timings": stage_timings,
            "total_stage_time": sum(stage_timings.values()),
            "pipeline_version": "inline_sse_v2"
        },
    }

    # Evidence Loss Ledger: save artifact and attach to result
    if ledger:
        try:
            ledger.save()
            final_result["evidence_ledger"] = ledger.to_dict()
        except Exception as e:
            logger.warning(f"[LEDGER] Failed to save ledger: {e}")

    # FROZEN REPLAY: Restore original temperature settings
    if frozen_urls and _frozen_temp_overrides:
        import os
        for env_key, original_val in _frozen_temp_overrides.items():
            if original_val is None:
                os.environ.pop(env_key, None)
            else:
                os.environ[env_key] = original_val
        logger.info("[FROZEN REPLAY] Restored original temperature settings")

    # FROZEN EVIDENCE REPLAY: Reset context var overrides
    if frozen_evidence and _replay_temp_token is not None:
        from app.pipeline.replay_context import frozen_replay_temperature, frozen_evidence_replay
        frozen_replay_temperature.reset(_replay_temp_token)
        if _replay_evidence_token is not None:
            frozen_evidence_replay.reset(_replay_evidence_token)
        logger.info("[FROZEN EVIDENCE REPLAY] Reset replay overrides")

    logger.info(f"[INLINE PIPELINE] Completed in {processing_time_ms}ms for check {check_id}")
    return final_result


def _add_explainability(
    results: List[Dict[str, Any]],
    evidence: Dict[str, List[Dict[str, Any]]],
    explainer
) -> List[Dict[str, Any]]:
    """Add explainability to claim results."""
    abstention_verdicts = [
        "insufficient_evidence", "conflicting_expert_opinion",
        "outdated_claim", "needs_primary_source", "lacks_context"
    ]

    empty_signals = {"supporting_count": 0, "contradicting_count": 0, "neutral_count": 0}

    for i, result in enumerate(results):
        position = result.get("position", i)
        claim_evidence = evidence.get(str(position), [])

        verdict = result.get("verdict", "").lower()
        if verdict in ["uncertain", "unclear"] or result.get("verdict") in abstention_verdicts:
            results[i]["uncertainty_explanation"] = explainer.create_uncertainty_explanation(
                result.get("verdict", ""), empty_signals, claim_evidence
            )

        results[i]["confidence_breakdown"] = explainer.create_confidence_breakdown(
            result, claim_evidence, empty_signals
        )

    return results


def _aggregate_api_stats(
    claims: List[Dict[str, Any]],
    evidence: Dict[str, List[Dict[str, Any]]]
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
                (a for a in all_apis_queried if a["name"] == api_info["name"]),
                None
            )
            if existing_api:
                existing_api["results"] += api_info.get("results", 0)
            else:
                all_apis_queried.append({
                    "name": api_info["name"],
                    "results": api_info.get("results", 0)
                })

        total_api_calls += claim_api_stats.get("total_api_calls", 0)
        total_api_results += claim_api_stats.get("total_api_results", 0)

    total_evidence_count = sum(len(ev_list) for ev_list in evidence.values())
    api_evidence_count = 0

    for ev_list in evidence.values():
        for ev in ev_list:
            external_provider = ev.get("external_source_provider")
            if not external_provider and ev.get("metadata"):
                external_provider = ev.get("metadata", {}).get("external_source_provider")
            if external_provider:
                api_evidence_count += 1

    api_coverage = (api_evidence_count / total_evidence_count * 100) if total_evidence_count > 0 else 0.0

    return {
        "apis_queried": all_apis_queried,
        "total_api_calls": total_api_calls,
        "total_api_results": total_api_results,
        "api_evidence_count": api_evidence_count,
        "total_evidence_count": total_evidence_count,
        "api_coverage_percentage": round(api_coverage, 2)
    }


# ============================================================================
# Database Helpers (Async)
# ============================================================================

async def save_check_results_async(
    check_id: str,
    results: Dict[str, Any],
    session: AsyncSession
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
        check.overall_summary = results.get("overall_summary")
        check.credibility_score = results.get("credibility_score")
        check.claims_supported = results.get("claims_supported", 0)
        check.claims_contradicted = results.get("claims_contradicted", 0)
        check.claims_uncertain = results.get("claims_uncertain", 0)
        check.article_excerpt = results.get("article_excerpt")

        # API stats
        api_stats = results.get("api_stats")
        if api_stats:
            check.api_sources_used = api_stats.get("apis_queried", [])
            check.api_call_count = api_stats.get("total_api_calls", 0)
            check.api_coverage_percentage = api_stats.get("api_coverage_percentage", 0.0)

        # Query response
        query_data = results.get("query_response")
        if query_data:
            check.query_response = query_data.get("answer")
            check.query_confidence = query_data.get("confidence")
            check.query_sources = {
                "sources": query_data.get("source_ids", []),
                "related_claims": query_data.get("related_claims", [])
            }

        # Article classification
        article_class = results.get("article_classification")
        if article_class:
            check.article_domain = article_class.get("primary_domain")
            check.article_secondary_domains = article_class.get("secondary_domains", [])
            check.article_jurisdiction = article_class.get("jurisdiction")
            check.article_classification_confidence = int(article_class.get("confidence", 0) * 100) if article_class.get("confidence") else None
            check.article_classification_source = article_class.get("source")

        # Save claims and evidence
        claims_data = results.get("claims", [])
        logger.info(f"Saving {len(claims_data)} claims for check {check_id}")

        for claim_data in claims_data:
            # Ensure numeric fields are properly typed (avoid string '0' issues)
            confidence_val = claim_data.get("confidence", 0)
            position_val = claim_data.get("position", 0)
            claim = Claim(
                check_id=check_id,
                text=claim_data.get("text", ""),
                verdict=claim_data.get("verdict", "uncertain"),
                confidence=float(confidence_val) if confidence_val is not None else 0.0,
                rationale=claim_data.get("rationale", ""),
                position=int(position_val) if position_val is not None else 0,
                subject_context=claim_data.get("subject_context"),
                key_entities=claim_data.get("key_entities", []) if claim_data.get("key_entities") else None,
                source_title=claim_data.get("source_title"),
                source_url=claim_data.get("source_url"),
                source_date=claim_data.get("source_date"),
                current_verified_data=claim_data.get("current_verified_data"),
                rhetorical_context=claim_data.get("rhetorical_analysis"),
                has_rhetorical_context=claim_data.get("has_rhetorical_context", False),
                rhetorical_style=claim_data.get("rhetorical_style"),
                judge_input_hash=claim_data.get("judge_input_hash")
            )
            session.add(claim)
            await session.flush()

            # Save evidence
            for ev_data in claim_data.get("evidence", []):
                metadata_dict = ev_data.get("metadata", {})
                # Ensure numeric fields are properly typed
                cred_score = ev_data.get("credibility_score", 0.6)
                rel_score = ev_data.get("relevance_score", 0.0)
                evidence = Evidence(
                    claim_id=claim.id,
                    source=ev_data.get("source", "Unknown"),
                    url=ev_data.get("url", ""),
                    title=ev_data.get("title", ""),
                    snippet=ev_data.get("snippet", ev_data.get("text", "")),
                    credibility_score=float(cred_score) if cred_score is not None else 0.6,
                    published_date=parse_date(ev_data.get("published_date")),
                    relevance_score=float(rel_score) if rel_score is not None else 0.0,
                    page_number=metadata_dict.get("page_number") if metadata_dict else None,
                    context_before=metadata_dict.get("context_before") if metadata_dict else None,
                    context_after=metadata_dict.get("context_after") if metadata_dict else None,
                    tier=ev_data.get("tier"),
                    risk_flags=ev_data.get("risk_flags"),
                    credibility_reasoning=ev_data.get("credibility_reasoning"),
                    risk_level=ev_data.get("risk_level"),
                    risk_warning=ev_data.get("risk_warning"),
                    external_source_provider=ev_data.get("external_source_provider"),
                    api_metadata=metadata_dict
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
                cred_score = raw_ev.get("credibility_score", 0.6)

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
                    credibility_score=float(cred_score) if cred_score is not None else 0.6,
                    is_included=bool(raw_ev.get("is_included", False)),
                    filter_stage=raw_ev.get("filter_stage"),
                    filter_reason=raw_ev.get("filter_reason"),
                    tier=raw_ev.get("tier"),
                    is_factcheck=bool(raw_ev.get("is_factcheck", False)),
                    external_source_provider=raw_ev.get("external_source_provider")
                )
                session.add(raw_evidence)

        logger.info(f"Successfully saved results for check {check_id}")

    except Exception as e:
        logger.error(f"Failed to save check results: {e}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")
        raise


async def handle_pipeline_failure(
    check_id: str,
    user_id: str,
    error: Exception
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
                user_id=user_id,
                check_id=check_id,
                error_message=error_msg[:100]
            )
        except Exception as e:
            logger.warning(f"Push notification failed: {e}")

        try:
            email_notification_service.send_check_failed_email_sync(
                user_id=user_id,
                check_id=check_id,
                error_message=error_msg[:200]
            )
        except Exception as e:
            logger.warning(f"Email notification failed: {e}")


async def refund_check_credit_async(
    check_id: str,
    user_id: str,
    session: AsyncSession
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
    content: Dict[str, Any]
) -> None:
    """Send notifications on successful completion."""
    try:
        input_url = input_data.get("url") or content.get("metadata", {}).get("url")
        input_title = content.get("metadata", {}).get("title")
        raw_sources_count = results.get("raw_sources_count", 0)
        claims = results.get("claims", [])
        total_sources = raw_sources_count if raw_sources_count > 0 else sum(
            len(c.get("evidence", [])) for c in claims
        )

        # Top claims (max 2)
        sorted_claims = sorted(
            claims,
            key=lambda c: (
                0 if c.get("verdict") == "contradicted" else
                1 if c.get("verdict") == "supported" else 2
            )
        )
        top_claims = [
            {"text": c.get("claim_text", c.get("text", "")), "verdict": c.get("verdict", "uncertain")}
            for c in sorted_claims[:2]
        ]

        # Average confidence
        confidences = [c.get("confidence", 50) for c in claims]
        avg_confidence = int(sum(confidences) / len(confidences)) if confidences else 50

        email_notification_service.send_check_completed_email_sync(
            user_id=user_id,
            check_id=check_id,
            claims_count=len(claims),
            supported=results.get("claims_supported", 0),
            contradicted=results.get("claims_contradicted", 0),
            uncertain=results.get("claims_uncertain", 0),
            credibility_score=results.get("credibility_score", 50),
            input_url=input_url,
            input_title=input_title,
            total_sources=total_sources,
            top_claims=top_claims,
            avg_confidence=avg_confidence
        )
    except Exception as e:
        logger.warning(f"Failed to send completion email: {e}")
# reload trigger
