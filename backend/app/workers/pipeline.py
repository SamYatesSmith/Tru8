from celery import Task
from typing import Dict, List, Any, Optional
import asyncio
import logging
import hashlib
import json
import httpx
from datetime import datetime
from app.workers import celery_app
from app.pipeline.ingest import UrlIngester, ImageIngester, VideoIngester
from app.pipeline.extract import ClaimExtractor
from app.pipeline.retrieve import EvidenceRetriever
from app.pipeline.verify import get_claim_verifier
from app.pipeline.judge import get_pipeline_judge
from app.services.cache import get_cache_service
from app.services.push_notifications import push_notification_service
from app.core.config import settings

logger = logging.getLogger(__name__)

class PipelineTask(Task):
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        logger.error(f"Task {task_id} failed: {exc}")
        # Get check_id from kwargs since task is called with keyword arguments
        check_id = kwargs.get("check_id") if kwargs else None
        user_id = kwargs.get("user_id") if kwargs else None
        
        if check_id:
            # Update check status in database
            asyncio.run(update_check_status(check_id, "failed", str(exc)))
            
            # Send failure notification
            if user_id:
                asyncio.run(
                    push_notification_service.send_check_failed_notification(
                        user_id=user_id,
                        check_id=check_id,
                        error_message=str(exc)[:100]  # Truncate error message
                    )
                )
    
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

def parse_published_date(date_value: Any) -> Optional[datetime]:
    """
    Parse published_date from various formats.

    Args:
        date_value: Can be datetime, ISO string, or other date formats

    Returns:
        datetime object or None if unparseable
    """
    if date_value is None:
        return None

    # Already a datetime
    if isinstance(date_value, datetime):
        return date_value

    # String date
    if isinstance(date_value, str):
        # Try ISO format (most common from APIs)
        try:
            # Handle both "2025-01-28" and "2025-01-28T10:30:00Z"
            return datetime.fromisoformat(date_value.replace('Z', '+00:00'))
        except:
            pass

        # Try common formats
        import re
        formats = [
            "%Y-%m-%d",           # 2025-01-28
            "%Y/%m/%d",           # 2025/01/28
            "%d-%m-%Y",           # 28-01-2025
            "%B %d, %Y",          # January 28, 2025
            "%b %d, %Y",          # Jan 28, 2025
            "%Y-%m-%dT%H:%M:%S"   # 2025-01-28T10:30:00
        ]

        for fmt in formats:
            try:
                return datetime.strptime(date_value, fmt)
            except:
                continue

        # Extract year and assume Jan 1 (fallback for "2025" or "Published in 2025")
        match = re.search(r"20\d{2}", date_value)
        if match:
            year = int(match.group(0))
            return datetime(year, 1, 1)

    # Can't parse
    logger.warning(f"Could not parse published_date: {date_value} (type: {type(date_value)})")
    return None

def save_check_results_sync(check_id: str, results: Dict[str, Any]):
    """Save pipeline results to database (synchronous for Celery)"""
    try:
        from app.core.database import sync_session
        from app.models import Check, Claim, Evidence
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

            # Save claims and evidence
            claims_data = results.get("claims", [])
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
                    key_entities=json.dumps(claim_data.get("key_entities", [])) if claim_data.get("key_entities") else None,
                    source_title=claim_data.get("source_title"),
                    source_url=claim_data.get("source_url")
                )
                session.add(claim)
                session.flush()  # Get claim ID
                logger.info(f"Saved claim {claim.id}: {claim.text[:50]}...")

                # Create evidence
                evidence_list = claim_data.get("evidence", [])
                logger.info(f"Saving {len(evidence_list)} evidence items for claim {claim.id}")

                for ev_data in evidence_list:
                    evidence = Evidence(
                        claim_id=claim.id,
                        source=ev_data.get("source", "Unknown"),
                        url=ev_data.get("url", ""),
                        title=ev_data.get("title", ""),
                        snippet=ev_data.get("snippet", ev_data.get("text", "")),
                        credibility_score=ev_data.get("credibility_score", 0.6),
                        published_date=parse_published_date(ev_data.get("published_date")),
                        relevance_score=ev_data.get("relevance_score", 0.0),

                        # Citation Precision (Phase 2)
                        page_number=ev_data.get("metadata", {}).get("page_number") if ev_data.get("metadata") else None,
                        context_before=ev_data.get("metadata", {}).get("context_before") if ev_data.get("metadata") else None,
                        context_after=ev_data.get("metadata", {}).get("context_after") if ev_data.get("metadata") else None,

                        # NLI Context (Phase 2 - enriched in judge.py)
                        nli_stance=ev_data.get("nli_stance"),
                        nli_confidence=ev_data.get("nli_confidence"),
                        nli_entailment=ev_data.get("nli_entailment"),
                        nli_contradiction=ev_data.get("nli_contradiction")
                    )
                    session.add(evidence)

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
        
        try:
            extract_content = content.get("content", "")
            logger.info(f"Extracting claims from content of length: {len(extract_content)}")
            logger.info(f"First 100 chars of content: {extract_content[:100]}")
            claims = asyncio.run(extract_claims_with_cache(
                extract_content,
                content.get("metadata", {}),
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

        try:
            evidence = asyncio.run(retrieve_evidence_with_cache(claims, cache_service, factcheck_evidence))
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

            results = asyncio.run(
                asyncio.wait_for(
                    judge_claims_with_llm(claims, verifications, evidence),
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
                input_data.get('url') or input_data.get('content', '')[:100]  # Pass URL or content preview
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
            "pipeline_stats": {
                "claims_extracted": len(claims),
                "evidence_sources": sum(len(ev) for ev in evidence.values()),
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
        except Exception as db_error:
            logger.error(f"Failed to save check results to database for check {check_id}: {db_error}")
            import traceback
            logger.error(f"Full database error traceback: {traceback.format_exc()}")

        return final_result

    except Exception as e:
        logger.error(f"Pipeline failed for check {check_id}: {e}")
        raise

async def generate_overall_assessment(
    claims: List[Dict[str, Any]],
    check_url: Optional[str] = None
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

    # Calculate overall credibility score (weighted)
    # Abstention verdicts are treated as uncertain (50% weight)
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

async def retrieve_evidence_with_cache(claims: List[Dict[str, Any]], cache_service, factcheck_evidence: Dict = None) -> Dict[str, List[Dict[str, Any]]]:
    """Retrieve evidence using real search and embeddings with caching"""
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
        if uncached_claims:
            logger.info(f"Retrieving evidence for {len(uncached_claims)} uncached claims")
            new_evidence = await retriever.retrieve_evidence_for_claims(uncached_claims)

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

        return cached_evidence

    except Exception as e:
        logger.error(f"Evidence retrieval error: {e}")
        # Fallback to mock evidence (development only)
        if settings.ENVIRONMENT == "development":
            logger.warning("Using mock evidence fallback (development only)")
            return retrieve_evidence(claims, factcheck_evidence)
        else:
            # Production: return empty evidence dict, let judge handle insufficient evidence
            logger.critical(f"Evidence retrieval failed in {settings.ENVIRONMENT} environment: {e}")
            return {}

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
                               evidence_by_claim: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """Judge claims using real LLM with verification signals"""
    try:
        pipeline_judge = await get_pipeline_judge()
        
        logger.info(f"Running LLM judgment for {len(claims)} claims")
        results = await pipeline_judge.judge_all_claims(claims, verifications_by_claim, evidence_by_claim)
        
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