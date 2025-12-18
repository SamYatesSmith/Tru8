from celery import Task
from typing import Dict, List, Any, Optional
import asyncio
import logging
import hashlib
import json
import httpx
from datetime import datetime
from app.workers import celery_app
from app.utils.date_utils import parse_date
from app.utils.article_classifier import classify_article
from app.pipeline.ingest import UrlIngester, ImageIngester, VideoIngester
from app.pipeline.extract import ClaimExtractor
from app.pipeline.retrieve import EvidenceRetriever
from app.pipeline.verify import get_claim_verifier
from app.pipeline.judge import get_pipeline_judge
from app.services.cache import get_cache_service
from app.services.push_notifications import push_notification_service
from app.services.email_notifications import email_notification_service
from app.core.config import settings

logger = logging.getLogger(__name__)

class PipelineTask(Task):
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        logger.error(f"Task {task_id} failed: {exc}")
        # Get check_id from kwargs since task is called with keyword arguments
        check_id = kwargs.get("check_id") if kwargs else None
        user_id = kwargs.get("user_id") if kwargs else None

        if check_id:
            # Refund the user's credit for the failed check
            credit_refunded = False
            if user_id:
                credit_refunded = refund_check_credit_sync(check_id, user_id)

            # Build error message with refund status
            error_msg = str(exc)
            if credit_refunded:
                error_msg = f"{error_msg}. Your credit has been returned."

            # Update check status using SYNC version to avoid event loop issues in Celery
            update_check_status_sync(check_id, "failed", error_msg)

            # Send failure notification using SYNC version to avoid event loop issues
            if user_id:
                try:
                    push_notification_service.send_check_failed_notification_sync(
                        user_id=user_id,
                        check_id=check_id,
                        error_message=error_msg[:100]  # Truncate error message
                    )
                except Exception as notif_error:
                    # Push notification failure should not crash the failure handler
                    logger.warning(f"Failed to send push notification: {notif_error}")

                # Email notification
                try:
                    email_notification_service.send_check_failed_email_sync(
                        user_id=user_id,
                        check_id=check_id,
                        error_message=error_msg[:200]
                    )
                except Exception as email_error:
                    # Email notification failure should not crash the failure handler
                    logger.warning(f"Failed to send email notification: {email_error}")

    def on_success(self, retval, task_id, args, kwargs):
        logger.info(f"Task {task_id} completed successfully")
        # Get check_id from kwargs since task is called with keyword arguments
        check_id = kwargs.get("check_id") if kwargs else None
        if check_id and retval.get("status") == "completed":
            # Simply log successful completion - pipeline already completed successfully
            # The main issue was tasks not completing, which is now fixed
            logger.info(f"Task {task_id} for check {check_id} completed successfully with processing time {retval.get('processing_time_ms', 0)}ms")

            # We'll handle database updates through the main process instead of callbacks
            # This avoids all event loop and threading issues completely

async def update_check_status(check_id: str, status: str, error_message: str = None):
    """Update check status in database (async version - DO NOT USE IN CELERY)"""
    try:
        from app.core.database import async_session
        from app.models import Check
        from sqlalchemy import select

        async with async_session() as session:
            stmt = select(Check).where(Check.id == check_id)
            result = await session.execute(stmt)
            check = result.scalar_one_or_none()

            if check:
                check.status = status
                if error_message:
                    check.error_message = error_message
                if status == "completed":
                    check.completed_at = datetime.utcnow()

                await session.commit()
                logger.info(f"Updated check {check_id} status to {status}")

    except Exception as e:
        logger.error(f"Failed to update check status: {e}")

def update_check_status_sync(check_id: str, status: str, error_message: str = None):
    """Update check status in database (synchronous for Celery)"""
    try:
        from app.core.database import sync_session
        from app.models import Check
        from sqlalchemy import select

        with sync_session() as session:
            stmt = select(Check).where(Check.id == check_id)
            result = session.execute(stmt)
            check = result.scalar_one_or_none()

            if check:
                check.status = status
                if error_message:
                    check.error_message = error_message
                if status == "completed":
                    check.completed_at = datetime.utcnow()

                session.commit()
                logger.info(f"Updated check {check_id} status to {status}")

    except Exception as e:
        logger.error(f"Failed to update check status: {e}")

def refund_check_credit_sync(check_id: str, user_id: str) -> bool:
    """
    Refund the credit used for a failed check (synchronous for Celery).

    Returns True if refund was successful, False otherwise.
    """
    try:
        from app.core.database import sync_session
        from app.models import Check, User
        from sqlalchemy import select

        with sync_session() as session:
            # Get the check
            check_stmt = select(Check).where(Check.id == check_id)
            check_result = session.execute(check_stmt)
            check = check_result.scalar_one_or_none()

            if not check:
                logger.error(f"Cannot refund: Check {check_id} not found")
                return False

            # Check if already refunded (credits_used = 0)
            if check.credits_used == 0:
                logger.info(f"Check {check_id} already refunded or no credits used")
                return True

            credits_to_refund = check.credits_used

            # Get the user
            user_stmt = select(User).where(User.id == user_id)
            user_result = session.execute(user_stmt)
            user = user_result.scalar_one_or_none()

            if not user:
                logger.error(f"Cannot refund: User {user_id} not found")
                return False

            # Refund the credit
            user.credits += credits_to_refund
            # Note: We keep total_credits_used as-is to track attempted usage

            # Mark check as refunded
            check.credits_used = 0

            session.commit()
            logger.info(f"Refunded {credits_to_refund} credit(s) to user {user_id} for failed check {check_id}")
            return True

    except Exception as e:
        logger.error(f"Failed to refund credit for check {check_id}: {e}")
        return False

def save_check_results_sync(check_id: str, results: Dict[str, Any]):
    """Save pipeline results to database (synchronous for Celery)"""
    try:
        from app.core.database import sync_session
        from app.models import Check, Claim, Evidence, RawEvidence
        from sqlalchemy import select

        with sync_session() as session:
            # Update check
            stmt = select(Check).where(Check.id == check_id)
            result = session.execute(stmt)
            check = result.scalar_one_or_none()

            if not check:
                logger.error(f"Check {check_id} not found in database")
                return

            check.status = "completed"
            check.completed_at = datetime.utcnow()
            check.processing_time_ms = results.get("processing_time_ms", 0)

            # Save overall summary fields
            check.overall_summary = results.get("overall_summary")
            check.credibility_score = results.get("credibility_score")
            check.claims_supported = results.get("claims_supported", 0)
            check.claims_contradicted = results.get("claims_contradicted", 0)
            check.claims_uncertain = results.get("claims_uncertain", 0)

            # Save article excerpt for context-aware judgments
            check.article_excerpt = results.get("article_excerpt")

            # Phase 5: Save Government API statistics
            api_stats = results.get("api_stats")
            if api_stats:
                check.api_sources_used = api_stats.get("apis_queried", [])
                check.api_call_count = api_stats.get("total_api_calls", 0)
                check.api_coverage_percentage = api_stats.get("api_coverage_percentage", 0.0)
                logger.info(
                    f"API stats: {api_stats['total_api_calls']} calls, "
                    f"{api_stats['api_coverage_percentage']:.1f}% coverage"
                )

            # Save Search Clarity query response fields (if present)
            query_data = results.get("query_response")
            if query_data:
                check.query_response = query_data.get("answer")
                check.query_confidence = query_data.get("confidence")

                # Store source objects and related claims as JSON (SQLAlchemy handles serialization)
                query_metadata = {
                    "sources": query_data.get("source_ids", []),
                    "related_claims": query_data.get("related_claims", [])
                }
                check.query_sources = query_metadata

            # Save article classification (passed directly from pipeline, not from claims)
            article_class = results.get("article_classification")
            if article_class:
                check.article_domain = article_class.get("primary_domain")
                check.article_secondary_domains = article_class.get("secondary_domains", [])
                check.article_jurisdiction = article_class.get("jurisdiction")
                check.article_classification_confidence = int(article_class.get("confidence", 0) * 100) if article_class.get("confidence") else None
                check.article_classification_source = article_class.get("source")
                logger.info(f"Saved article classification: {check.article_domain} (jurisdiction: {check.article_jurisdiction})")
            else:
                logger.warning(f"No article classification available for check {check_id}")

            claims_data = results.get("claims", [])

            # Save claims and evidence
            logger.info(f"Saving {len(claims_data)} claims for check {check_id}")

            for claim_data in claims_data:
                # Create claim with context preservation fields
                claim = Claim(
                    check_id=check_id,
                    text=claim_data.get("text", ""),
                    verdict=claim_data.get("verdict", "uncertain"),
                    confidence=claim_data.get("confidence", 0),
                    rationale=claim_data.get("rationale", ""),
                    position=claim_data.get("position", 0),
                    # Context preservation fields (Context Improvement)
                    subject_context=claim_data.get("subject_context"),
                    key_entities=claim_data.get("key_entities", []) if claim_data.get("key_entities") else None,
                    source_title=claim_data.get("source_title"),
                    source_url=claim_data.get("source_url"),
                    source_date=claim_data.get("source_date"),
                    # Temporal drift comparison (current API data vs claimed values)
                    current_verified_data=claim_data.get("current_verified_data"),
                    # Rhetorical context detection (sarcasm, mockery, satire from source analysis)
                    rhetorical_context=claim_data.get("rhetorical_analysis"),
                    has_rhetorical_context=claim_data.get("has_rhetorical_context", False),
                    rhetorical_style=claim_data.get("rhetorical_style")
                )
                session.add(claim)
                session.flush()  # Get claim ID
                logger.info(f"Saved claim {claim.id}: {claim.text[:50]}...")

                # Create evidence
                evidence_list = claim_data.get("evidence", [])
                logger.info(f"Saving {len(evidence_list)} evidence items for claim {claim.id}")

                for ev_data in evidence_list:
                    # Get metadata dict for API fields
                    metadata_dict = ev_data.get("metadata", {})

                    evidence = Evidence(
                        claim_id=claim.id,
                        source=ev_data.get("source", "Unknown"),
                        url=ev_data.get("url", ""),
                        title=ev_data.get("title", ""),
                        snippet=ev_data.get("snippet", ev_data.get("text", "")),
                        credibility_score=ev_data.get("credibility_score", 0.6),
                        published_date=parse_date(ev_data.get("published_date")),
                        relevance_score=ev_data.get("relevance_score", 0.0),

                        # Citation Precision (Phase 2)
                        page_number=metadata_dict.get("page_number") if metadata_dict else None,
                        context_before=metadata_dict.get("context_before") if metadata_dict else None,
                        context_after=metadata_dict.get("context_after") if metadata_dict else None,

                        # NLI Context (Phase 2 - enriched in judge.py)
                        nli_stance=ev_data.get("nli_stance"),
                        nli_confidence=ev_data.get("nli_confidence"),
                        nli_entailment=ev_data.get("nli_entailment"),
                        nli_contradiction=ev_data.get("nli_contradiction"),

                        # Phase 5: Government API Integration
                        external_source_provider=ev_data.get("external_source_provider"),
                        api_metadata=metadata_dict
                    )
                    session.add(evidence)

            # Save raw evidence for Full Sources List Pro feature
            raw_evidence_data = results.get("raw_evidence", [])
            raw_sources_count = results.get("raw_sources_count", len(raw_evidence_data))

            if raw_evidence_data:
                logger.info(f"Saving {len(raw_evidence_data)} raw evidence items for check {check_id}")
                check.raw_sources_count = raw_sources_count

                for raw_ev in raw_evidence_data:
                    # Safely truncate claim_text to 500 chars
                    claim_text_val = raw_ev.get("claim_text")
                    if claim_text_val:
                        claim_text_val = str(claim_text_val)[:500]

                    raw_evidence = RawEvidence(
                        check_id=check_id,
                        claim_position=raw_ev.get("claim_position", 0),
                        claim_text=claim_text_val,
                        source=raw_ev.get("source", "Unknown") or "Unknown",
                        url=raw_ev.get("url", "") or "",
                        title=raw_ev.get("title", "") or "",
                        snippet=raw_ev.get("snippet", "") or "",
                        published_date=parse_date(raw_ev.get("published_date")),
                        relevance_score=raw_ev.get("relevance_score", 0.0) or 0.0,
                        credibility_score=raw_ev.get("credibility_score", 0.6) or 0.6,
                        is_included=raw_ev.get("is_included", False),
                        filter_stage=raw_ev.get("filter_stage"),
                        filter_reason=raw_ev.get("filter_reason"),
                        tier=raw_ev.get("tier"),
                        is_factcheck=raw_ev.get("is_factcheck", False),
                        external_source_provider=raw_ev.get("external_source_provider")
                    )
                    session.add(raw_evidence)

                logger.info(f"Saved {len(raw_evidence_data)} raw evidence items (Full Sources List)")

            session.commit()
            logger.info(f"Successfully saved results for check {check_id} with {len(claims_data)} claims")

    except Exception as e:
        logger.error(f"Failed to save check results: {e}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")

# Keep async version for compatibility
async def save_check_results(check_id: str, results: Dict[str, Any]):
    """Save pipeline results to database (async version for compatibility)"""
    return save_check_results_sync(check_id, results)

@celery_app.task(base=PipelineTask, bind=True, max_retries=2, default_retry_delay=60)
def process_check(self, check_id: str, user_id: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main pipeline task that processes a fact-check request.
    Full pipeline with real LLM, search, embeddings, and caching!
    Enhanced with circuit breakers and retry logic.
    """
    start_time = datetime.utcnow()
    stage_timings = {}
    
    try:
        print(f"[PIPELINE] process_check started for {check_id}", flush=True)
        # Set processing status (using sync version to avoid event loop issues)
        update_check_status_sync(check_id, "processing")
        print(f"[PIPELINE] Status updated to processing", flush=True)

        # DISABLED: Cache service causing event loop issues in Celery - set to None for now
        cache_service = None

        # DISABLED: Checking cached results (cache_service is None)
        # cached_result = asyncio.run(cache_service.get_cached_pipeline_result(check_id))
        # if cached_result:
        #     logger.info(f"Returning cached result for check {check_id}")
        #     return cached_result

        print(f"[PIPELINE DEBUG] About to start Stage 1: Ingest for check {check_id}", flush=True)
        logger.info(f"About to start Stage 1: Ingest for check {check_id}")

        # Stage 1: Ingest (REAL IMPLEMENTATION WITH CIRCUIT BREAKER)
        self.update_state(state="PROGRESS", meta={"stage": "ingest", "progress": 10})
        print(f"[PIPELINE DEBUG] Task state updated to PROGRESS for check {check_id}", flush=True)
        logger.info(f"Task state updated to PROGRESS for check {check_id}")
        stage_start = datetime.utcnow()
        
        try:
            logger.info(f"Ingesting content for check {check_id}, input_type: {input_data.get('input_type')}")
            logger.info(f"Input content length: {len(input_data.get('content') or '')}")
            content = asyncio.run(ingest_content_async(input_data))
            if not content.get("success"):
                raise Exception(f"Ingest failed: {content.get('error', 'Unknown error')}")
            logger.info(f"Ingested content length: {len(content.get('content') or '')}")
        except Exception as e:
            logger.error(f"Ingest stage failed: {e}")
            if self.request.retries < self.max_retries:
                raise self.retry(countdown=60, exc=e)
            raise Exception(f"Ingest stage failed after retries: {e}")
        
        stage_timings["ingest"] = (datetime.utcnow() - stage_start).total_seconds()
            
        # Stage 2: Extract claims (REAL LLM IMPLEMENTATION WITH CACHING)
        self.update_state(state="PROGRESS", meta={"stage": "extract", "progress": 25})
        stage_start = datetime.utcnow()

        extract_content = content.get("content", "")
        extract_metadata = content.get("metadata", {})

        # Run article classification FIRST (at pipeline level) - ensures fallback claims get it too
        article_classification = None
        if settings.ENABLE_ARTICLE_CLASSIFICATION:
            try:
                article_classification = asyncio.run(classify_article(
                    title=extract_metadata.get("title", "") if extract_metadata else "",
                    url=extract_metadata.get("url", "") if extract_metadata else "",
                    content=extract_content[:2000]  # First 2000 chars for classification
                ))
                logger.info(
                    f"[PIPELINE] Article classified: {article_classification.primary_domain} "
                    f"(confidence: {article_classification.confidence:.2f})"
                )
            except Exception as e:
                logger.warning(f"Article classification failed, continuing without: {e}")

        try:
            logger.info(f"Extracting claims from content of length: {len(extract_content)}")
            logger.info(f"First 100 chars of content: {extract_content[:100]}")
            claims = asyncio.run(extract_claims_with_cache(
                extract_content,
                extract_metadata,
                cache_service
            ))
            logger.info(f"Extracted {len(claims)} claims")
            if not claims:
                raise Exception("No claims extracted from content")
        except Exception as e:
            logger.error(f"Extract stage failed: {e}")
            # Try fallback extraction
            claims = extract_claims_fallback(extract_content)
            logger.info(f"Fallback extraction returned {len(claims)} claims")
            if not claims:
                logger.error(f"Both primary and fallback extraction failed for content: {extract_content[:200]}")
                raise Exception(f"Extract stage failed completely: {e}")

        # Attach article classification to ALL claims (main or fallback)
        # This ensures API routing works correctly regardless of extraction method
        if article_classification:
            for claim in claims:
                claim["article_classification"] = article_classification.to_dict()
            logger.info(f"[PIPELINE] Attached {article_classification.primary_domain} classification to {len(claims)} claims")
        
        stage_timings["extract"] = (datetime.utcnow() - stage_start).total_seconds()

        # Stage 2.5: Fact-check lookup (if enabled)
        factcheck_evidence = {}
        if settings.ENABLE_FACTCHECK_API:
            self.update_state(state="PROGRESS", meta={"stage": "factcheck", "progress": 35})
            stage_start = datetime.utcnow()
            try:
                factcheck_evidence = asyncio.run(search_factchecks_for_claims(claims))
                logger.info(f"Found {sum(len(v) for v in factcheck_evidence.values())} fact-checks")
            except Exception as e:
                logger.warning(f"Fact-check lookup failed (non-critical): {e}")
            stage_timings["factcheck"] = (datetime.utcnow() - stage_start).total_seconds()

        # Stage 3: Retrieve evidence (REAL IMPLEMENTATION WITH CACHING)
        self.update_state(state="PROGRESS", meta={"stage": "retrieve", "progress": 40})
        stage_start = datetime.utcnow()

        # Raw evidence for Full Sources List Pro feature
        raw_evidence_data = []
        raw_sources_count = 0

        try:
            # Extract source URL for self-citation filtering
            source_url = content.get("metadata", {}).get("url")
            retrieval_result = asyncio.run(retrieve_evidence_with_cache(claims, cache_service, factcheck_evidence, source_url=source_url))

            # Extract evidence and raw evidence from new structure
            if isinstance(retrieval_result, dict) and "evidence_by_claim" in retrieval_result:
                evidence = retrieval_result["evidence_by_claim"]
                raw_evidence_data = retrieval_result.get("raw_evidence", [])
                raw_sources_count = retrieval_result.get("raw_sources_count", 0)
                logger.info(f"[RAW_EVIDENCE] Captured {raw_sources_count} raw sources for Full Sources List")
            else:
                # Backward compatibility
                evidence = retrieval_result
        except Exception as e:
            logger.error(f"Retrieve stage failed: {e}")
            # Try fallback evidence (development only)
            if settings.ENVIRONMENT == "development":
                logger.warning("Using mock evidence fallback (development only)")
                evidence = retrieve_evidence(claims, factcheck_evidence)
            else:
                # Production: fail the check properly with clear error
                logger.critical(f"Evidence retrieval failed in {settings.ENVIRONMENT} environment, cannot continue")
                raise Exception(f"Evidence retrieval failed: {e}")

        stage_timings["retrieve"] = (datetime.utcnow() - stage_start).total_seconds()

        # Stage 3.5: Parse fact-check evidence (CONDITIONAL IMPLEMENTATION)
        if settings.ENABLE_FACTCHECK_PARSING:
            self.update_state(state="PROGRESS", meta={"stage": "factcheck_parse", "progress": 50})
            stage_start = datetime.utcnow()
            try:
                from app.services.factcheck_parser import get_factcheck_parser
                parser = get_factcheck_parser()
                evidence = asyncio.run(parser.parse_factcheck_evidence(claims, evidence))

                # Count parsed fact-checks
                parsed_count = sum(
                    1 for ev_list in evidence.values()
                    for ev in ev_list
                    if ev.get('factcheck_parse_success')
                )
                logger.info(f"Fact-check parsing: {parsed_count} articles parsed successfully")

            except Exception as e:
                logger.warning(f"Fact-check parsing failed (non-critical): {e}")
                # Continue with unparsed evidence - safe fallback

            stage_timings["factcheck_parse"] = (datetime.utcnow() - stage_start).total_seconds()

        # Stage 3.7: Global Domain Capping (cross-claim diversity enforcement)
        if settings.ENABLE_GLOBAL_DOMAIN_CAPPING and evidence:
            stage_start = datetime.utcnow()
            try:
                from app.utils.domain_capping import DomainCapper
                global_capper = DomainCapper()
                evidence = global_capper.apply_global_caps(
                    evidence,
                    global_max_per_domain=settings.GLOBAL_MAX_PER_DOMAIN,
                    global_max_ratio=settings.GLOBAL_MAX_DOMAIN_RATIO
                )
                logger.info("[GLOBAL CAP] Applied global domain diversity enforcement")
            except Exception as e:
                logger.warning(f"Global domain capping failed (non-critical): {e}")
                # Continue with uncapped evidence - safe fallback

            stage_timings["global_domain_cap"] = (datetime.utcnow() - stage_start).total_seconds()

        # Stage 4: Verify with NLI (REAL IMPLEMENTATION WITH TIMEOUT)
        self.update_state(state="PROGRESS", meta={"stage": "verify", "progress": 60})
        stage_start = datetime.utcnow()

        try:
            # Add timeout for NLI stage
            verifications = asyncio.run(
                asyncio.wait_for(
                    verify_claims_with_nli(claims, evidence, cache_service),
                    timeout=settings.VERIFICATION_TIMEOUT_SECONDS * len(claims)
                )
            )
        except asyncio.TimeoutError:
            logger.warning(f"Verify stage timed out")
            if settings.ENVIRONMENT == "development":
                logger.warning("Using mock verification fallback (development only)")
                verifications = verify_claims(claims, evidence)
            else:
                logger.critical(f"NLI verification timed out in {settings.ENVIRONMENT} environment")
                raise Exception("NLI verification timed out")
        except Exception as e:
            logger.error(f"Verify stage failed: {e}")
            if settings.ENVIRONMENT == "development":
                logger.warning("Using mock verification fallback (development only)")
                verifications = verify_claims(claims, evidence)
            else:
                logger.critical(f"NLI verification failed in {settings.ENVIRONMENT} environment")
                raise Exception(f"NLI verification failed: {e}")
        
        stage_timings["verify"] = (datetime.utcnow() - stage_start).total_seconds()
        
        # Stage 5: Judge and finalize (REAL IMPLEMENTATION WITH TIMEOUT)
        self.update_state(state="PROGRESS", meta={"stage": "judge", "progress": 80})
        stage_start = datetime.utcnow()

        try:
            # Add timeout for judge stage
            # Adjust timeout: 15s per claim with 120s max cap to prevent exceeding pipeline timeout
            judge_timeout = min(15 * len(claims), 120)
            logger.info(f"Judge stage timeout set to {judge_timeout}s for {len(claims)} claims")

            # Extract article excerpt for context-aware judgment
            article_excerpt = content.get("content", "")[:5000]

            results = asyncio.run(
                asyncio.wait_for(
                    judge_claims_with_llm(claims, verifications, evidence, article_context=article_excerpt),
                    timeout=judge_timeout
                )
            )
        except asyncio.TimeoutError:
            logger.warning(f"Judge stage timed out")
            if settings.ENVIRONMENT == "development":
                logger.warning("Using mock judgment fallback (development only)")
                results = judge_claims(claims, verifications, evidence)
            else:
                logger.critical(f"LLM judgment timed out in {settings.ENVIRONMENT} environment")
                raise Exception("LLM judgment timed out")
        except Exception as e:
            logger.error(f"Judge stage failed: {e}")
            if settings.ENVIRONMENT == "development":
                logger.warning("Using mock judgment fallback (development only)")
                results = judge_claims(claims, verifications, evidence)
            else:
                logger.critical(f"LLM judgment failed in {settings.ENVIRONMENT} environment")
                raise Exception(f"LLM judgment failed: {e}")
        
        stage_timings["judge"] = (datetime.utcnow() - stage_start).total_seconds()

        # Stage 5.5: Query Answering (OPTIONAL - if user_query exists)
        query_response_data = None
        if input_data.get("user_query") and settings.ENABLE_SEARCH_CLARITY:
            self.update_state(state="PROGRESS", meta={"stage": "query", "progress": 85})
            stage_start = datetime.utcnow()

            try:
                from app.pipeline.query_answer import get_query_answerer

                user_query = input_data.get("user_query")
                logger.info(f"Answering user query: {user_query}")

                # Call async function using asyncio.run (same pattern as ingest stage)
                async def run_query_answering():
                    query_answerer = await get_query_answerer()
                    return await query_answerer.answer_query(
                        user_query=user_query,
                        claims=claims,
                        evidence_by_claim=evidence,
                        original_text=content.get("content", "")[:1000]  # First 1000 chars for context
                    )

                query_result = asyncio.run(run_query_answering())

                # Store query response
                query_response_data = {
                    "answer": query_result["answer"],
                    "confidence": query_result["confidence"],
                    "source_ids": query_result["source_ids"],  # Already full objects
                    "related_claims": query_result["related_claims"],
                    "found_answer": query_result["found_answer"]
                }

                logger.info(f"Query answered: confidence={query_result['confidence']}%, found_answer={query_result['found_answer']}")

            except Exception as e:
                logger.error(f"Query answering failed (non-critical): {e}", exc_info=True)
                query_response_data = None

            stage_timings["query"] = (datetime.utcnow() - stage_start).total_seconds()

        # Stage 6: Enhanced Explainability (Phase 2, Week 6.5-7.5)
        if settings.ENABLE_ENHANCED_EXPLAINABILITY:
            from app.utils.explainability import ExplainabilityEnhancer
            explainer = ExplainabilityEnhancer()

            # Add explainability to each claim
            for i, result in enumerate(results):
                position = result.get("position", i)
                claim_evidence = evidence.get(position, [])
                claim_verifications = verifications.get(position, [])

                # Create verification signals summary
                verification_signals = {
                    "supporting_count": sum(1 for v in claim_verifications if v.get("label") == "SUPPORTS"),
                    "contradicting_count": sum(1 for v in claim_verifications if v.get("label") == "CONTRADICTS"),
                    "neutral_count": sum(1 for v in claim_verifications if v.get("label") == "NEUTRAL")
                }

                # Add uncertainty explanation if verdict is uncertain or abstention
                abstention_verdicts = ['insufficient_evidence', 'conflicting_expert_opinion',
                                      'outdated_claim', 'needs_primary_source', 'lacks_context']
                if result.get("verdict", "").lower() in ["uncertain", "unclear"] or result.get("verdict") in abstention_verdicts:
                    uncertainty_explanation = explainer.create_uncertainty_explanation(
                        result.get("verdict", ""),
                        verification_signals,
                        claim_evidence
                    )
                    results[i]["uncertainty_explanation"] = uncertainty_explanation

                # Add confidence breakdown
                confidence_breakdown = explainer.create_confidence_breakdown(
                    result,
                    claim_evidence,
                    verification_signals
                )
                results[i]["confidence_breakdown"] = confidence_breakdown

            # Create overall decision trail for the check
            decision_trail = {
                "total_claims": len(claims),
                "claims_processed": len(results),
                "stage_timings": stage_timings,
                "features_enabled": {
                    "domain_capping": settings.ENABLE_DOMAIN_CAPPING,
                    "global_domain_capping": settings.ENABLE_GLOBAL_DOMAIN_CAPPING,
                    "deduplication": settings.ENABLE_DEDUPLICATION,
                    "temporal_context": settings.ENABLE_TEMPORAL_CONTEXT,
                    "factcheck_api": settings.ENABLE_FACTCHECK_API,
                    "claim_classification": settings.ENABLE_CLAIM_CLASSIFICATION
                }
            }

            logger.info(f"Added explainability for {len(results)} claims")

        # Stage 6.5: Generate Overall Assessment (Summary + Credibility Score)
        self.update_state(state="PROGRESS", meta={"stage": "summary", "progress": 90})
        stage_start = datetime.utcnow()

        try:
            logger.info(f"Generating overall assessment for {len(results)} claims")
            assessment = asyncio.run(generate_overall_assessment(
                results,
                input_data.get('url') or input_data.get('content', '')[:100],  # Pass URL or content preview
                evidence_by_claim=evidence  # Pass evidence for confidence weighting
            ))
            logger.info(f"Overall assessment generated: credibility_score={assessment['credibility_score']}")
        except Exception as e:
            logger.error(f"Assessment generation failed, using fallback: {e}")
            # Fallback assessment
            total = len(results)
            supported = sum(1 for c in results if c.get('verdict') == 'supported')
            contradicted = sum(1 for c in results if c.get('verdict') == 'contradicted')
            # Include abstention verdicts in uncertain count
            abstention_verdicts = ['insufficient_evidence', 'conflicting_expert_opinion',
                                  'outdated_claim', 'needs_primary_source', 'lacks_context']
            uncertain = sum(1 for c in results if c.get('verdict') == 'uncertain' or
                           c.get('verdict') in abstention_verdicts)
            assessment = {
                "summary": f"Analysis of {total} claims found {supported} supported, {contradicted} contradicted, and {uncertain} uncertain.",
                "credibility_score": int((supported * 100 + uncertain * 50) / total) if total > 0 else 50,
                "claims_supported": supported,
                "claims_contradicted": contradicted,
                "claims_uncertain": uncertain
            }

        stage_timings["summary"] = (datetime.utcnow() - stage_start).total_seconds()

        # Phase 5: Aggregate API statistics across all claims
        api_stats = aggregate_api_stats(claims, evidence)

        # Calculate processing time
        processing_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

        # Prepare final result with enhanced metrics
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
            "query_response": query_response_data,  # Search Clarity
            "api_stats": api_stats,  # Phase 5: Government API Integration
            "article_excerpt": content.get("content", "")[:5000],  # First 5000 chars for judge context
            # Article classification for domain stats
            "article_classification": article_classification.to_dict() if article_classification else None,
            # Full Sources List Pro feature
            "raw_evidence": raw_evidence_data,
            "raw_sources_count": raw_sources_count,
            "pipeline_stats": {
                "claims_extracted": len(claims),
                "evidence_sources": sum(len(ev) for ev in evidence.values()),
                "raw_sources_reviewed": raw_sources_count,  # NEW: Total sources reviewed
                "cache_hits": getattr(cache_service, '_cache_hits', 0),
                "stage_timings": stage_timings,
                "total_stage_time": sum(stage_timings.values()),
                "pipeline_version": "week4_optimized"
            },
            "performance_metrics": {
                "under_10s_target": processing_time_ms < 10000,
                "avg_time_per_claim": processing_time_ms / max(len(claims), 1),
                "efficiency_score": min(100, (10000 / max(processing_time_ms, 1000)) * 100)
            }
        }

        # DISABLED: Cache the complete pipeline result (cache_service is None)
        # asyncio.run(cache_service.cache_pipeline_result(check_id, final_result))

        # Save all results to database (claims, evidence, and check status)
        try:
            save_check_results_sync(check_id, final_result)

            # Send check completion email notification
            try:
                email_notification_service.send_check_completed_email_sync(
                    user_id=user_id,
                    check_id=check_id,
                    claims_count=len(results),
                    supported=assessment["claims_supported"],
                    contradicted=assessment["claims_contradicted"],
                    uncertain=assessment["claims_uncertain"],
                    credibility_score=assessment["credibility_score"]
                )
            except Exception as email_error:
                # Email notification failure should not crash the pipeline
                logger.warning(f"Failed to send check completion email: {email_error}")

        except Exception as db_error:
            logger.error(f"Failed to save check results to database for check {check_id}: {db_error}")
            import traceback
            logger.error(f"Full database error traceback: {traceback.format_exc()}")

        return final_result

    except Exception as e:
        logger.error(f"Pipeline failed for check {check_id}: {e}")
        raise


def aggregate_api_stats(
    claims: List[Dict[str, Any]],
    evidence: Dict[str, List[Dict[str, Any]]]
) -> Dict[str, Any]:
    """
    Aggregate API statistics across all claims.

    Phase 5: Government API Integration

    Args:
        claims: List of claims (each may have api_stats)
        evidence: Evidence by claim position

    Returns:
        Aggregated API stats dictionary
    """
    # Collect all API calls from claim-level stats
    all_apis_queried = []
    total_api_calls = 0
    total_api_results = 0

    for claim in claims:
        claim_api_stats = claim.get("api_stats", {})
        apis_queried = claim_api_stats.get("apis_queried", [])

        for api_info in apis_queried:
            # Check if this API is already in the aggregate list
            existing_api = next(
                (a for a in all_apis_queried if a["name"] == api_info["name"]),
                None
            )

            if existing_api:
                # Aggregate results for this API
                existing_api["results"] += api_info.get("results", 0)
            else:
                # Add new API to list
                all_apis_queried.append({
                    "name": api_info["name"],
                    "results": api_info.get("results", 0)
                })

        total_api_calls += claim_api_stats.get("total_api_calls", 0)
        total_api_results += claim_api_stats.get("total_api_results", 0)

    # Count evidence from APIs vs web search
    total_evidence_count = sum(len(ev_list) for ev_list in evidence.values())
    api_evidence_count = 0

    for ev_list in evidence.values():
        for ev in ev_list:
            # Issue #6 Fix: Check both top-level (correct) and nested (defensive fallback)
            external_provider = ev.get("external_source_provider")

            # Defensive: also check in metadata if not at top level
            if not external_provider and ev.get("metadata"):
                external_provider = ev.get("metadata", {}).get("external_source_provider")

            if external_provider:
                api_evidence_count += 1

    # Calculate API coverage percentage
    api_coverage_percentage = 0.0
    if total_evidence_count > 0:
        api_coverage_percentage = (api_evidence_count / total_evidence_count) * 100

    return {
        "apis_queried": all_apis_queried,
        "total_api_calls": total_api_calls,
        "total_api_results": total_api_results,
        "api_evidence_count": api_evidence_count,
        "total_evidence_count": total_evidence_count,
        "api_coverage_percentage": round(api_coverage_percentage, 2)
    }

async def generate_overall_assessment(
    claims: List[Dict[str, Any]],
    check_url: Optional[str] = None,
    evidence_by_claim: Optional[Dict[str, List[Dict[str, Any]]]] = None
) -> Dict[str, Any]:
    """
    Generate overall credibility assessment after all claims judged.
    Returns: {
        "summary": str,           # 2-3 sentence executive summary
        "credibility_score": int, # 0-100 overall score
        "claims_supported": int,
        "claims_contradicted": int,
        "claims_uncertain": int
    }
    """
    # Calculate statistics
    total = len(claims)
    supported = sum(1 for c in claims if c.get('verdict') == 'supported')
    contradicted = sum(1 for c in claims if c.get('verdict') == 'contradicted')

    # Phase 3: Abstention verdicts are semantically a type of "uncertain"
    # These verdicts indicate uncertainty with specific, documented reasons:
    # - insufficient_evidence: Too few sources or low credibility
    # - conflicting_expert_opinion: High-credibility sources disagree
    # - outdated_claim: Temporal flag indicates claim is no longer current
    # - needs_primary_source: Requires direct source verification
    # - lacks_context: Missing critical context for verification
    abstention_verdicts = ['insufficient_evidence', 'conflicting_expert_opinion',
                          'outdated_claim', 'needs_primary_source', 'lacks_context']
    uncertain = sum(1 for c in claims if c.get('verdict') == 'uncertain' or
                   c.get('verdict') in abstention_verdicts)

    avg_confidence = sum(c.get('confidence', 0) for c in claims) / total if total > 0 else 0

    # Calculate overall credibility score (Consensus Plan Phase 3: confidence-weighted)
    # Weight each claim by its confidence and average evidence credibility
    if evidence_by_claim and total > 0:
        weighted_score = 0.0
        total_weight = 0.0

        for i, claim in enumerate(claims):
            # Get claim confidence (0-100) and convert to 0-1
            confidence = claim.get('confidence', 50) / 100.0

            # Calculate average evidence credibility for this claim
            position = claim.get('position', i)
            claim_evidence = evidence_by_claim.get(str(position), [])
            if claim_evidence:
                avg_evidence_cred = sum(e.get('credibility_score', 0.6) for e in claim_evidence) / len(claim_evidence)
            else:
                avg_evidence_cred = 0.7  # Default if no evidence

            # Claim weight = confidence × evidence quality
            claim_weight = confidence * avg_evidence_cred

            # Verdict value: supported=100, contradicted=0, uncertain=40, abstention=30
            verdict = claim.get('verdict', '')
            if verdict == 'supported':
                verdict_value = 100
            elif verdict == 'contradicted':
                verdict_value = 0
            elif verdict in abstention_verdicts:
                verdict_value = 30  # Penalize abstention more than uncertain
            else:  # uncertain or other
                verdict_value = 40  # Penalize uncertainty more than old 50

            weighted_score += verdict_value * claim_weight
            total_weight += claim_weight

        credibility_score = int(weighted_score / total_weight) if total_weight > 0 else 50
    else:
        # Fallback: simple count-based (old method)
        credibility_score = int(
            (supported * 100 + uncertain * 50 + contradicted * 0) / total if total > 0 else 50
        )

    # Prepare claims summary for LLM (use 1-indexed numbering for user display)
    claims_summary = []
    for i, claim in enumerate(claims, 1):  # START AT 1 for user-facing numbers
        claims_summary.append({
            "number": i,  # User-facing claim number (1, 2, 3...)
            "text": claim.get('text', '')[:200],  # Truncate long claims
            "verdict": claim.get('verdict'),
            "confidence": claim.get('confidence')
        })

    # LLM prompt
    prompt = f"""You are a fact-checking expert providing an overall assessment.

SOURCE: {check_url or 'User-submitted content'}

CLAIMS ANALYZED: {total}
- Supported: {supported} ({supported/total*100:.1f}%)
- Contradicted: {contradicted} ({contradicted/total*100:.1f}%)
- Uncertain: {uncertain} ({uncertain/total*100:.1f}%)
- Average Confidence: {avg_confidence:.1f}%

CLAIM DETAILS:
{json.dumps(claims_summary, indent=2)}

Generate a concise overall assessment in 2-3 sentences that answers:
1. What is the overall credibility of this content?
2. What can readers trust vs. what needs skepticism?
3. Are there any red flags or patterns?

Be direct and actionable. Focus on practical guidance for the reader.
When referencing specific claims, use the format "Claim X" where X is the claim number.
For example: "However, Claim 3 contradicts multiple fact-checking sources."
"""

    try:
        # Use OpenAI API (same pattern as judge.py)
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "gpt-4o-mini-2024-07-18",
                    "messages": [
                        {"role": "system", "content": "You are a fact-checking expert providing concise overall assessments."},
                        {"role": "user", "content": prompt}
                    ],
                    "max_tokens": 250,
                    "temperature": 0.3
                }
            )

            if response.status_code == 200:
                result = response.json()
                summary = result["choices"][0]["message"]["content"].strip()
            else:
                logger.error(f"OpenAI API error for summary: {response.status_code}")
                # Fallback summary
                summary = f"Analysis of {total} claims found {supported} supported, {contradicted} contradicted, and {uncertain} uncertain. Overall credibility score: {credibility_score}/100."

    except Exception as e:
        logger.error(f"LLM summary generation failed: {e}")
        # Fallback summary
        summary = f"Analysis of {total} claims found {supported} supported, {contradicted} contradicted, and {uncertain} uncertain. Overall credibility score: {credibility_score}/100."

    return {
        "summary": summary,
        "credibility_score": credibility_score,
        "claims_supported": supported,
        "claims_contradicted": contradicted,
        "claims_uncertain": uncertain
    }

async def ingest_content_async(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """Real ingest implementation using pipeline classes"""
    input_type = input_data.get("input_type")
    
    try:
        if input_type == "text":
            return {
                "success": True,
                "content": input_data.get("content", ""),
                "metadata": {
                    "input_type": "text",
                    "word_count": len(input_data.get("content", "").split())
                }
            }
        elif input_type == "url":
            url_ingester = UrlIngester()
            return await url_ingester.process(input_data.get("url", ""))
        elif input_type == "image":
            image_ingester = ImageIngester()
            return await image_ingester.process(input_data.get("file_path", ""))
        elif input_type == "video":
            video_ingester = VideoIngester()
            return await video_ingester.process(input_data.get("url", ""))
        else:
            return {
                "success": False,
                "error": f"Unsupported input type: {input_type}",
                "content": ""
            }
    except Exception as e:
        logger.error(f"Ingest error: {e}")
        return {
            "success": False,
            "error": str(e),
            "content": ""
        }

async def extract_claims_with_cache(content: str, metadata: Dict[str, Any], cache_service) -> List[Dict[str, Any]]:
    """Extract claims using LLM with caching"""
    try:
        # Try cache first using content hash and model name
        model_name = "gpt-4o-mini"  # Default extraction model

        # Check cache if available
        if cache_service:
            cached_claims = await cache_service.get_cached_claim_extraction(content, model_name)
            if cached_claims:
                logger.info("Using cached claim extraction")
                # BUGFIX: Add current metadata to cached claims (may be missing from old cache)
                for claim in cached_claims:
                    claim["source_title"] = metadata.get("title") if metadata else None
                    claim["source_url"] = metadata.get("url") if metadata else None
                    claim["source_date"] = metadata.get("date") if metadata else None
                logger.info(f"Added metadata to {len(cached_claims)} cached claims")
                return cached_claims

        # Extract claims with real LLM
        extractor = ClaimExtractor()
        extraction_result = await extractor.extract_claims(content, metadata)

        if extraction_result.get("success"):
            claims = extraction_result.get("claims", [])
            # Cache the result if cache is available
            if cache_service:
                await cache_service.cache_claim_extraction(content, model_name, claims)
            return claims
        else:
            logger.warning(f"LLM extraction failed: {extraction_result.get('error')}")
            # Fallback to simple extraction
            fallback_claims = extract_claims_fallback(content)
            return fallback_claims
            
    except Exception as e:
        logger.error(f"Claims extraction error: {e}")
        return extract_claims_fallback(content)

async def search_factchecks_for_claims(claims: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """Search for existing fact-checks for claims"""
    from app.services.factcheck_api import FactCheckAPI

    factcheck_api = FactCheckAPI()
    factcheck_evidence = {}

    for claim in claims:
        claim_text = claim.get("text", "")
        position = str(claim.get("position", 0))

        # Search for fact-checks
        fact_checks = await factcheck_api.search_fact_checks(claim_text)

        if fact_checks:
            # Convert to evidence format
            evidence_items = []
            for fc in fact_checks:
                ev = factcheck_api.convert_to_evidence(fc, claim_text)
                evidence_items.append(ev)

            factcheck_evidence[position] = evidence_items
            logger.info(f"Found {len(evidence_items)} fact-checks for claim position {position}")

    return factcheck_evidence

async def retrieve_evidence_with_cache(
    claims: List[Dict[str, Any]],
    cache_service,
    factcheck_evidence: Dict = None,
    source_url: Optional[str] = None
) -> Dict[str, Any]:
    """Retrieve evidence using real search and embeddings with caching.

    Returns:
        Dict with keys:
        - evidence_by_claim: Dict[str, List[Dict]] - Filtered evidence by claim position
        - raw_evidence: List[Dict] - All sources reviewed with filtering metadata
        - raw_sources_count: int - Total count of raw sources
    """
    if factcheck_evidence is None:
        factcheck_evidence = {}

    try:
        retriever = EvidenceRetriever()

        # Check if we have cached evidence for each claim
        cached_evidence = {}
        uncached_claims = []

        for claim in claims:
            claim_text = claim.get("text", "")
            # Check cache if available
            if cache_service:
                cached_result = await cache_service.get_cached_evidence_extraction(claim_text)
                if cached_result:
                    position = str(claim.get("position", 0))
                    cached_evidence[position] = cached_result
                    continue
            # If no cache or no cached result, add to uncached list
            uncached_claims.append(claim)

        # Retrieve evidence for uncached claims
        all_raw_evidence = []
        if uncached_claims:
            logger.info(f"Retrieving evidence for {len(uncached_claims)} uncached claims")
            retrieval_result = await retriever.retrieve_evidence_for_claims(
                uncached_claims,
                exclude_source_url=source_url
            )

            # Extract evidence and raw evidence from new structure
            if isinstance(retrieval_result, dict) and "evidence_by_claim" in retrieval_result:
                new_evidence = retrieval_result["evidence_by_claim"]
                all_raw_evidence = retrieval_result.get("raw_evidence", [])
            else:
                # Backward compatibility: old format returned Dict[str, List]
                new_evidence = retrieval_result if isinstance(retrieval_result, dict) else {}
                all_raw_evidence = []

            # Cache the new evidence if cache is available
            if cache_service:
                for claim in uncached_claims:
                    claim_text = claim.get("text", "")
                    position = str(claim.get("position", 0))
                    if position in new_evidence:
                        await cache_service.cache_evidence_extraction(claim_text, new_evidence[position])

            # Merge cached and new evidence
            cached_evidence.update(new_evidence)

        # Merge fact-check evidence (prepend to give it priority)
        for position, fc_evidence in factcheck_evidence.items():
            if position in cached_evidence:
                cached_evidence[position] = fc_evidence + cached_evidence[position]
            else:
                cached_evidence[position] = fc_evidence

        return {
            "evidence_by_claim": cached_evidence,
            "raw_evidence": all_raw_evidence,
            "raw_sources_count": len(all_raw_evidence)
        }

    except Exception as e:
        logger.error(f"Evidence retrieval error: {e}")
        # Fallback to mock evidence (development only)
        if settings.ENVIRONMENT == "development":
            logger.warning("Using mock evidence fallback (development only)")
            mock_evidence = retrieve_evidence(claims, factcheck_evidence)
            return {
                "evidence_by_claim": mock_evidence,
                "raw_evidence": [],
                "raw_sources_count": 0
            }
        else:
            # Production: return empty evidence dict, let judge handle insufficient evidence
            logger.critical(f"Evidence retrieval failed in {settings.ENVIRONMENT} environment: {e}")
            return {
                "evidence_by_claim": {},
                "raw_evidence": [],
                "raw_sources_count": 0
            }

async def verify_claims_with_nli(claims: List[Dict[str, Any]], evidence_by_claim: Dict[str, List[Dict[str, Any]]], 
                                cache_service) -> Dict[str, List[Dict[str, Any]]]:
    """Verify claims using real NLI with caching"""
    try:
        claim_verifier = await get_claim_verifier()
        
        # Check cache for each claim's verification
        cached_verifications = {}
        uncached_claims = []
        
        for claim in claims:
            claim_text = claim.get("text", "")
            position = str(claim.get("position", 0))
            
            if cache_service:
                cache_key = hashlib.md5(claim_text.encode()).hexdigest()
                cached_result = await cache_service.get("nli_verification", cache_key)
                if cached_result:
                    cached_verifications[position] = cached_result
                    continue
            
            uncached_claims.append(claim)
        
        # Verify uncached claims
        if uncached_claims:
            logger.info(f"Running NLI verification for {len(uncached_claims)} uncached claims")
            
            # Create evidence subset for uncached claims
            uncached_evidence = {}
            for claim in uncached_claims:
                position = str(claim.get("position", 0))
                uncached_evidence[position] = evidence_by_claim.get(position, [])
            
            new_verifications = await claim_verifier.verify_claims_with_evidence(uncached_claims, uncached_evidence)
            
            # Cache new verifications
            if cache_service:
                for claim in uncached_claims:
                    claim_text = claim.get("text", "")
                    position = str(claim.get("position", 0))
                    cache_key = hashlib.md5(claim_text.encode()).hexdigest()
                    
                    if position in new_verifications:
                        await cache_service.set(
                            "nli_verification",
                            cache_key,
                            new_verifications[position],
                            3600 * 12  # 12 hours
                        )
            
            # Merge cached and new verifications
            cached_verifications.update(new_verifications)
        
        return cached_verifications
        
    except Exception as e:
        logger.error(f"NLI verification error: {e}")
        # Fallback to mock verification (development only)
        if settings.ENVIRONMENT == "development":
            logger.warning("Using mock verification fallback (development only)")
            return verify_claims(claims, evidence_by_claim)
        else:
            # Production: return empty verifications, will trigger abstention
            logger.critical(f"NLI verification failed in {settings.ENVIRONMENT} environment: {e}")
            return {}

async def judge_claims_with_llm(claims: List[Dict[str, Any]], verifications_by_claim: Dict[str, List[Dict[str, Any]]],
                               evidence_by_claim: Dict[str, List[Dict[str, Any]]], article_context: Optional[str] = None) -> List[Dict[str, Any]]:
    """Judge claims using real LLM with verification signals and article context"""
    try:
        pipeline_judge = await get_pipeline_judge()

        logger.info(f"Running LLM judgment for {len(claims)} claims with article context: {bool(article_context)}")
        results = await pipeline_judge.judge_all_claims(claims, verifications_by_claim, evidence_by_claim, article_context=article_context)
        
        # Sort results by position to maintain order
        results.sort(key=lambda x: x.get("position", 0))
        
        return results
        
    except Exception as e:
        logger.error(f"LLM judgment error: {e}")
        # Fallback to mock judgment (development only)
        if settings.ENVIRONMENT == "development":
            logger.warning("Using mock judgment fallback (development only)")
            return judge_claims(claims, verifications_by_claim, evidence_by_claim)
        else:
            # Production: fail properly
            logger.critical(f"LLM judgment failed in {settings.ENVIRONMENT} environment: {e}")
            raise

def extract_claims_fallback(content: str) -> List[Dict[str, Any]]:
    """Mock claim extraction - Week 3 will implement real LLM"""
    if not content.strip():
        return [{"text": "No claims found in empty content", "position": 0}]
    
    # Simple sentence splitting as mock
    sentences = [s.strip() for s in content.split('.') if s.strip()]
    claims = []
    
    for i, sentence in enumerate(sentences[:6]):  # Max 6 claims for demo
        if len(sentence) > 20:  # Only substantial sentences
            claims.append({
                "text": sentence + ".",
                "position": i
            })
    
    if not claims:
        claims = [{"text": content[:200] + "...", "position": 0}]
    
    return claims

def retrieve_evidence(claims: List[Dict[str, Any]], factcheck_evidence: Dict = None) -> Dict[str, List[Dict[str, Any]]]:
    """Mock evidence retrieval fallback"""
    if factcheck_evidence is None:
        factcheck_evidence = {}

    evidence = {}

    for i, claim in enumerate(claims):
        # Generate realistic mock evidence
        sources = [
            ("BBC", "2024-01-15", "https://bbc.com/example"),
            ("Reuters", "2024-01-10", "https://reuters.com/example"),
            ("Scientific American", "2023-12-20", "https://sciam.com/example"),
        ]
        
        position = str(claim.get("position", i))
        evidence[position] = []
        for source, date, url in sources:
            evidence[position].append({
                "id": f"evidence_{i}_{source.lower().replace(' ', '_')}",
                "text": f"Supporting evidence snippet for the claim: {claim['text'][:50]}...",
                "source": source,
                "url": url,
                "title": f"Article about: {claim['text'][:50]}...",
                "published_date": date,
                "relevance_score": 0.85 + (i * 0.05),  # Vary scores
                "semantic_similarity": 0.75 + (i * 0.03),
                "combined_score": 0.8 + (i * 0.04),
                "credibility_score": 0.9,
                "recency_score": 1.0,
                "final_score": 0.85 + (i * 0.05),
                "word_count": 150 + (i * 20)
            })
    
    return evidence

def verify_claims(claims: List[Dict[str, Any]], evidence: Dict) -> Dict[str, List[Dict[str, Any]]]:
    """Mock NLI verification - Week 3 implementation"""
    verdicts = ["supported", "contradicted", "uncertain"]
    verifications = {}

    for i, claim in enumerate(claims):
        # Mock realistic confidence based on content
        confidence = 85.0 + (i * 3.0) % 30  # Vary confidence
        verdict = verdicts[i % len(verdicts)]

        position = str(claim.get("position", i))
        verifications[position] = [{
            "verdict": verdict,
            "confidence": confidence,
            "evidence_id": f"mock_evidence_{i}",
            "similarity_score": 0.8 + (i * 0.02) % 0.2
        }]

    return verifications

def judge_claims(claims: List[Dict[str, Any]], verifications: Dict[str, List[Dict[str, Any]]],
                evidence: Dict) -> List[Dict[str, Any]]:
    """Mock judge stage - Week 4 implementation"""
    rationales = {
        "supported": "This claim is well-supported by multiple reliable sources with consistent reporting.",
        "contradicted": "Evidence from credible sources contradicts this claim with factual information.",
        "uncertain": "Available evidence is mixed or insufficient to make a definitive determination.",
    }
    
    results = []
    for claim in claims:
        position = str(claim.get("position", 0))
        claim_verifications = verifications.get(position, [])

        if claim_verifications:
            # Use the first verification result
            verification = claim_verifications[0]
            verdict = verification["verdict"]
            confidence = verification["confidence"]
        else:
            # Fallback for claims without verification
            verdict = "uncertain"
            confidence = 0.0

        results.append({
            "text": claim["text"],
            "verdict": verdict,
            "confidence": confidence,
            "rationale": rationales.get(verdict, "Assessment based on available evidence."),
            "evidence": evidence.get(position, [])[:3],  # Top 3 sources
            "position": claim.get("position", 0),
        })
    
    return results