from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Request
from fastapi.responses import StreamingResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func
from pydantic import BaseModel
from xhtml2pdf import pisa
from jinja2 import Environment, FileSystemLoader
from io import BytesIO
from app.core.database import get_session
from app.core.auth import get_current_user, get_current_user_sse
from app.core.config import settings
from app.models import User, Check, Claim, Evidence, RawEvidence, Subscription
from datetime import datetime, timezone
import uuid
import json
import asyncio
import logging
import redis.asyncio as aioredis
import redis
from app.core.config import settings
import os
import aiofiles
from app.api.v1.users import get_or_create_user
from app.services.storage import storage_service
from app.core.rate_limit import limiter
from pathlib import Path

logger = logging.getLogger(__name__)


def _claim_map_to_camel_case(claim_map: dict) -> dict:
    """Convert a ClaimMap dict from snake_case (DB/TypedDict) to camelCase (API).

    The backend stores ClaimMap with snake_case keys (Python TypedDict convention)
    but the frontend expects camelCase (TypeScript interface convention).

    This converts: claim_id → claimId, normalised_claim → normalisedClaim,
    element_id → elementId, evidence_refs → evidenceRefs, etc.
    """
    if not claim_map or not isinstance(claim_map, dict):
        return claim_map

    def _snake_to_camel(name: str) -> str:
        parts = name.split("_")
        return parts[0] + "".join(p.capitalize() for p in parts[1:])

    result = {}
    for key, value in claim_map.items():
        camel_key = _snake_to_camel(key)

        if key == "elements" and isinstance(value, list):
            result[camel_key] = [_convert_element(elem) for elem in value]
        elif key == "metadata" and isinstance(value, dict):
            result[camel_key] = {_snake_to_camel(mk): mv for mk, mv in value.items()}
        else:
            result[camel_key] = value

    return result


def _convert_element(elem: dict) -> dict:
    """Convert a ClaimElement dict from snake_case to camelCase."""
    if not isinstance(elem, dict):
        return elem

    def _snake_to_camel(name: str) -> str:
        parts = name.split("_")
        return parts[0] + "".join(p.capitalize() for p in parts[1:])

    result = {}
    for key, value in elem.items():
        camel_key = _snake_to_camel(key)

        if key == "evidence_refs" and isinstance(value, list):
            result[camel_key] = [
                (
                    {_snake_to_camel(rk): rv for rk, rv in ref.items()}
                    if isinstance(ref, dict)
                    else ref
                )
                for ref in value
            ]
        else:
            result[camel_key] = value

    return result


router = APIRouter()


@router.get("/test/search-diagnostic")
async def test_search_diagnostic():
    """
    DIAGNOSTIC ENDPOINT: Test if Brave Search API is working.
    Visit: http://localhost:8000/api/v1/checks/test/search-diagnostic
    """
    import traceback
    from app.services.search import SearchService, warmup_search_providers

    results = {
        "brave_api_key_configured": bool(settings.BRAVE_API_KEY),
        "brave_api_key_length": (
            len(settings.BRAVE_API_KEY) if settings.BRAVE_API_KEY else 0
        ),
        "serp_api_key_configured": bool(settings.SERP_API_KEY),
        "test_query": "Earth age billion years",
        "search_results": [],
        "error": None,
    }

    try:
        warmup_search_providers()
        results["warmup"] = "completed"

        search_service = SearchService()
        results["providers"] = [p.__class__.__name__ for p in search_service.providers]

        if not search_service.providers:
            results["error"] = "No search providers available"
            return results

        search_results = await search_service.search_for_evidence(
            "Earth age billion years", max_results=3
        )

        results["search_results"] = [
            {
                "title": r.title,
                "url": r.url,
                "snippet": r.snippet[:150],
                "source": r.source,
            }
            for r in search_results
        ]
        results["result_count"] = len(search_results)

    except Exception as e:
        results["error"] = f"{type(e).__name__}: {str(e)}"
        results["traceback"] = traceback.format_exc()

    return results


@router.get("/test/full-diagnostic")
async def test_full_diagnostic():
    """
    COMPREHENSIVE DIAGNOSTIC: Test web search AND API adapters.
    Visit: http://localhost:8000/api/v1/checks/test/full-diagnostic
    """
    import traceback
    from app.services.search import SearchService, warmup_search_providers
    from app.services.government_api_client import get_api_registry
    from app.pipeline.retrieve import EvidenceRetriever

    results = {
        "web_search": {
            "brave_key_configured": bool(settings.BRAVE_API_KEY),
            "serp_key_configured": bool(settings.SERP_API_KEY),
            "providers": [],
            "test_results": 0,
            "error": None,
        },
        "api_adapters": {
            "registered_count": 0,
            "adapter_names": [],
            "test_results": {},
            "error": None,
        },
        "evidence_retriever": {
            "initialized": False,
            "error": None,
        },
    }

    # Test 1: Web Search
    try:
        warmup_search_providers()
        search_service = SearchService()
        results["web_search"]["providers"] = [
            p.__class__.__name__ for p in search_service.providers
        ]

        if search_service.providers:
            search_results = await search_service.search_for_evidence(
                "climate change statistics 2024", max_results=3
            )
            results["web_search"]["test_results"] = len(search_results)
            if search_results:
                results["web_search"]["sample"] = {
                    "title": search_results[0].title,
                    "url": search_results[0].url[:80],
                }
    except Exception as e:
        results["web_search"]["error"] = f"{type(e).__name__}: {str(e)}"

    # Test 2: API Adapters
    try:
        registry = get_api_registry()
        adapters = registry.get_all_adapters()
        results["api_adapters"]["registered_count"] = len(adapters)
        results["api_adapters"]["adapter_names"] = [a.api_name for a in adapters]

        # Test Wikipedia (should always work - no API key needed)
        for adapter in adapters:
            if adapter.api_name == "Wikipedia":
                try:
                    wiki_results = adapter.search("Earth age", "Science", "Global", [])
                    results["api_adapters"]["test_results"]["Wikipedia"] = len(
                        wiki_results
                    )
                    if wiki_results:
                        results["api_adapters"]["test_results"]["Wikipedia_sample"] = {
                            "title": wiki_results[0].get("title", "N/A")[:50],
                            "has_snippet": bool(wiki_results[0].get("snippet")),
                        }
                except Exception as e:
                    results["api_adapters"]["test_results"]["Wikipedia_error"] = str(e)
                break
    except Exception as e:
        results["api_adapters"]["error"] = f"{type(e).__name__}: {str(e)}"

    # Test 3: Evidence Retriever initialization
    try:
        retriever = EvidenceRetriever()
        results["evidence_retriever"]["initialized"] = True
        results["evidence_retriever"]["search_providers"] = [
            p.__class__.__name__ for p in retriever.search_service.providers
        ]
    except Exception as e:
        results["evidence_retriever"]["error"] = f"{type(e).__name__}: {str(e)}"

    # Summary
    results["summary"] = {
        "web_search_working": results["web_search"]["test_results"] > 0,
        "api_adapters_registered": results["api_adapters"]["registered_count"] > 0,
        "evidence_retriever_ready": results["evidence_retriever"]["initialized"],
    }

    if (
        not results["summary"]["web_search_working"]
        and not results["api_adapters"]["test_results"]
    ):
        results["diagnosis"] = (
            "CRITICAL: Neither web search nor API adapters are returning results. Check API keys in .env"
        )
    elif not results["summary"]["web_search_working"]:
        results["diagnosis"] = (
            "WARNING: Web search not working. Set BRAVE_API_KEY or SERP_API_KEY. API adapters may still provide some evidence."
        )
    else:
        results["diagnosis"] = "OK: Evidence retrieval should be working."

    return results


# Setup Jinja2 environment for PDF templates
template_dir = Path(__file__).parent.parent.parent / "templates"
jinja_env = Environment(loader=FileSystemLoader(str(template_dir)))


def safe_json_dumps(data: dict) -> str:
    """Safely serialize JSON for SSE with ASCII encoding"""
    return json.dumps(data, ensure_ascii=True, separators=(",", ":"))


class CreateCheckRequest(BaseModel):
    input_type: str  # 'url', 'text', 'image', 'video'
    content: Optional[str] = None
    url: Optional[str] = None
    file_path: Optional[str] = None  # For uploaded files
    user_query: Optional[str] = None  # Search Clarity feature
    frozen_evidence: Optional[Dict[str, List[Dict[str, Any]]]] = (
        None  # Frozen evidence replay (v2): full pre-weighting evidence dicts
    )


@router.post("/upload")
@limiter.limit("10/minute")  # Rate limit uploads
async def upload_file(
    request: Request,  # Required for rate limiting
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    """Upload a file for fact-checking (images only)"""

    # Validate file type
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image files are supported")

    # Check file size (6MB limit from project requirements)
    max_size = 6 * 1024 * 1024  # 6MB
    content = await file.read()
    if len(content) > max_size:
        raise HTTPException(
            status_code=413, detail="File too large. Maximum size is 6MB."
        )

    # Generate unique filename
    file_id = str(uuid.uuid4())
    file_extension = Path(file.filename).suffix.lower()
    if file_extension not in [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"]:
        raise HTTPException(
            status_code=400,
            detail="Unsupported image format. Supported: jpg, jpeg, png, gif, bmp, webp",
        )

    filename = f"{file_id}{file_extension}"

    try:
        # Use storage service (S3 in production, local in development)
        file_path = await storage_service.upload(
            file_data=content,
            filename=filename,
            content_type=file.content_type,
        )

        return {
            "success": True,
            "filePath": file_path,
            "filename": file.filename,
            "contentType": file.content_type,
            "size": len(content),
        }

    except Exception as e:
        logger.error(f"File upload error: {e}")
        raise HTTPException(status_code=500, detail="Failed to save uploaded file")


@router.get("/test/stream-mock", status_code=200)
async def test_stream_mock():
    """
    Mock streaming endpoint for testing SSE mechanism.
    DEBUG mode only. Returns fake progress events.
    """
    if not settings.DEBUG:
        raise HTTPException(
            status_code=404, detail="Test endpoint only available in DEBUG mode"
        )

    from app.pipeline.progress import ProgressReporter

    check_id = str(uuid.uuid4())
    reporter = ProgressReporter(check_id)

    async def mock_pipeline():
        """Simulate pipeline stages with delays."""
        stages = [
            "ingest",
            "extract",
            "select",
            "decompose",
            "retrieve",
            "analyze",
            "complete",
        ]
        for stage in stages:
            await asyncio.sleep(1)  # Simulate work
            await reporter.report_progress(stage)
        await asyncio.sleep(0.5)
        await reporter.report_completed()

    async def mock_stream():
        task = asyncio.create_task(mock_pipeline())
        async for event in reporter.events(task):
            yield event
        await task

    return StreamingResponse(
        mock_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Check-Id": check_id,
        },
    )


@router.get("/test/{check_id}")
async def get_check_test(check_id: str, session: AsyncSession = Depends(get_session)):
    """TEST-ONLY ENDPOINT: Get check status without authentication (DEBUG mode only)"""
    if not settings.DEBUG:
        raise HTTPException(
            status_code=404, detail="Test endpoint only available in DEBUG mode"
        )

    try:
        # Get check from database
        stmt = select(Check).where(Check.id == check_id)
        result = await session.execute(stmt)
        check = result.scalar_one_or_none()

        if not check:
            raise HTTPException(status_code=404, detail="Check not found")

        # Build basic response
        response = {
            "id": check.id,
            "status": check.status,
            "inputType": check.input_type,
            "inputUrl": check.input_url,
            "createdAt": check.created_at.isoformat() if check.created_at else None,
            "creditsUsed": check.credits_used or 0,
        }

        # If completed, add results
        if check.status == "completed":
            try:
                # Get claims for this check
                claims_stmt = select(Claim).where(Claim.check_id == check_id)
                claims_result = await session.execute(claims_stmt)
                claims = list(claims_result.scalars().all())

                # Calculate statistics
                total_claims = len(claims)
                selected_claims = sum(1 for c in claims if c.is_selected)

                response.update(
                    {
                        "claims_analyzed": total_claims,
                        "selected_claims": selected_claims,
                    }
                )
            except Exception as e:
                logger.error(f"[TEST] Error getting claims for check {check_id}: {e}")
                # Return basic response without claims data
                pass

        # If failed, add error
        if check.status == "failed":
            response["error"] = check.error_message or "Unknown error"

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[TEST] Error in get_check_test for {check_id}: {e}")
        import traceback

        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


class CreateCheckTestStreamRequest(BaseModel):
    """Test-only request for streaming endpoint"""

    input_type: str = "text"
    content: Optional[str] = None
    url: Optional[str] = None


@router.post("/test/stream", status_code=200)
async def create_check_test_streaming(
    body: CreateCheckTestStreamRequest, session: AsyncSession = Depends(get_session)
):
    """
    TEST-ONLY ENDPOINT: Create a streaming fact-check without authentication.
    DEBUG mode only. Uses test user with unlimited credits.

    Example:
        curl -N -X POST http://localhost:8000/api/v1/checks/test/stream \\
          -H "Content-Type: application/json" \\
          -d '{"input_type": "text", "content": "The Earth is flat."}'
    """
    if not settings.DEBUG:
        raise HTTPException(
            status_code=404, detail="Test endpoint only available in DEBUG mode"
        )

    from app.core.database import async_session
    from app.pipeline.progress import ProgressReporter
    from app.pipeline.runner import (
        run_pipeline,
        save_check_results_async,
        handle_pipeline_failure,
        send_success_notifications,
        PipelineError,
    )

    # Create or get test user
    test_user_id = "test-user-streaming"
    stmt = select(User).where(User.id == test_user_id)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        user = User(
            id=test_user_id,
            email="test-stream@consistency.local",
            name="Streaming Test User",
            credits=1000000,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

    # Normalize URL if provided
    if body.input_type == "url" and body.url:
        if not body.url.startswith(("http://", "https://")):
            body.url = f"https://{body.url}"

    # Validate
    if body.input_type == "text" and not body.content:
        raise HTTPException(status_code=400, detail="Content required for text input")
    if body.input_type == "url" and not body.url:
        raise HTTPException(status_code=400, detail="URL required for url input")

    # Create check record
    check = Check(
        id=str(uuid.uuid4()),
        user_id=user.id,
        input_type=body.input_type,
        input_content=json.dumps(
            {"content": body.content, "url": body.url, "file_path": None}
        ),
        input_url=body.url,
        status="processing",
        credits_used=0,  # Don't charge for test
        user_query=None,
    )

    session.add(check)
    await session.commit()
    await session.refresh(check)

    logger.info(f"[TEST STREAM] Created check {check.id}")

    # Prepare input data
    input_data = {
        "input_type": body.input_type,
        "content": body.content,
        "url": body.url,
        "file_path": None,
        "user_query": None,
    }

    progress_reporter = ProgressReporter(check.id)

    async def run_pipeline_and_save():
        """Background task that runs pipeline and saves results independently."""
        try:
            logger.info(f"[TEST STREAM] Starting pipeline for check {check.id}")
            result = await asyncio.wait_for(
                run_pipeline(check.id, user.id, input_data, progress_reporter),
                timeout=300,
            )

            # result is None for article mode (waiting_for_selection)
            if result is not None:
                async with async_session() as save_session:
                    await save_check_results_async(check.id, result, save_session)
                    await save_session.commit()

                await progress_reporter.report_completed()
                logger.info(f"[TEST STREAM] Check {check.id} completed successfully")
            else:
                logger.info(
                    f"[TEST STREAM] Check {check.id} paused — waiting for claim selection"
                )

        except asyncio.TimeoutError:
            logger.error(f"[TEST STREAM] Pipeline timed out for check {check.id}")
            await handle_pipeline_failure(
                check.id, user.id, Exception("Pipeline timed out")
            )
            await progress_reporter.report_error("Pipeline timed out")

        except PipelineError as e:
            logger.error(f"[TEST STREAM] Pipeline error: {e}")
            await handle_pipeline_failure(check.id, user.id, e)
            await progress_reporter.report_error(str(e))

        except Exception as e:
            logger.error(f"[TEST STREAM] Unexpected error: {e}")
            import traceback

            logger.error(traceback.format_exc())
            await handle_pipeline_failure(check.id, user.id, e)
            await progress_reporter.report_error(str(e))

    # Start pipeline as fire-and-forget background task
    pipeline_task = asyncio.create_task(run_pipeline_and_save())

    async def pipeline_stream():
        """Generator that yields SSE events - pipeline runs independently."""
        async for event in progress_reporter.events(
            pipeline_task, max_duration_seconds=300
        ):
            yield event

    return StreamingResponse(
        pipeline_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "X-Check-Id": check.id,
        },
    )


@router.post("/stream", status_code=200)
@limiter.limit("10/minute")
async def create_check_streaming(
    body: CreateCheckRequest,
    request: Request,
    current_user: dict = Depends(get_current_user_sse),
    session: AsyncSession = Depends(get_session),
):
    """
    Create a new fact-check with inline SSE streaming.

    This endpoint runs the pipeline inline (no Celery) and streams progress
    directly to the client. Eliminates worker infrastructure costs.

    Returns: StreamingResponse with SSE events
    """
    from app.core.database import async_session
    from app.pipeline.progress import ProgressReporter
    from app.pipeline.runner import (
        run_pipeline,
        save_check_results_async,
        handle_pipeline_failure,
        send_success_notifications,
        PipelineError,
    )

    # Get or create user (handles race conditions)
    user = await get_or_create_user(session, current_user)

    # BETA TESTER CHECK (skip in DEBUG mode)
    is_beta_tester = user.email.lower() in [
        e.lower() for e in settings.BETA_TESTER_EMAILS
    ]

    if not settings.DEBUG and settings.BETA_TESTER_EMAILS and not is_beta_tester:
        raise HTTPException(
            status_code=403,
            detail={
                "message": "Tru8 is currently in closed beta. Join our waitlist to be notified when we launch!",
                "code": "BETA_ACCESS_REQUIRED",
                "waitlist": True,
            },
        )

    # MONTHLY USAGE LIMIT CHECK
    sub_stmt = select(Subscription).where(
        Subscription.user_id == user.id, Subscription.status.in_(["active", "trialing"])
    )
    sub_result = await session.execute(sub_stmt)
    subscription = sub_result.scalar_one_or_none()

    # Determine usage limit
    if is_beta_tester:
        now = datetime.utcnow()
        period_start = datetime(now.year, now.month, 1)
        credits_limit = 40

        usage_stmt = select(func.coalesce(func.sum(Check.credits_used), 0)).where(
            Check.user_id == user.id, Check.created_at >= period_start
        )
        usage_result = await session.execute(usage_stmt)
        current_usage = usage_result.scalar() or 0
        limit_type = "beta_monthly"
    elif subscription and subscription.current_period_start:
        period_start = subscription.current_period_start
        credits_limit = subscription.credits_per_month

        usage_stmt = select(func.coalesce(func.sum(Check.credits_used), 0)).where(
            Check.user_id == user.id, Check.created_at >= period_start
        )
        usage_result = await session.execute(usage_stmt)
        current_usage = usage_result.scalar() or 0
        limit_type = "monthly"
    else:
        credits_limit = 3
        current_usage = user.total_credits_used
        limit_type = "trial"

    # Admin bypass OR DEBUG mode bypass
    if settings.DEBUG:
        logger.info(f"DEBUG mode: {user.email} - skipping credit limit check")
    elif user.email and user.email.lower() in [
        e.lower() for e in settings.ADMIN_EMAILS
    ]:
        logger.info(f"Admin bypass: {user.email} - skipping credit limit check")
    elif current_usage >= credits_limit:
        if limit_type == "trial":
            raise HTTPException(
                status_code=402,
                detail=f"Free trial exhausted ({current_usage}/{credits_limit} checks used). Please upgrade to Pro for unlimited monthly checks.",
            )
        elif limit_type == "beta_monthly":
            raise HTTPException(
                status_code=402,
                detail=f"Beta monthly limit reached ({current_usage}/{credits_limit} checks used). Your limit resets on the 1st of next month.",
            )
        else:
            raise HTTPException(
                status_code=402,
                detail=f"Monthly limit reached ({current_usage}/{credits_limit} checks used). Please upgrade your plan for more checks.",
            )

    # Validate input
    if body.input_type not in ["url", "text", "image", "video"]:
        raise HTTPException(status_code=400, detail="Invalid input type")

    if body.input_type == "url" and not body.url:
        raise HTTPException(
            status_code=400, detail="URL is required for url input type"
        )

    if body.input_type in ["url", "video"] and body.url:
        if not body.url.startswith(("http://", "https://")):
            body.url = f"https://{body.url}"

    if body.input_type == "text" and not body.content:
        raise HTTPException(
            status_code=400, detail="Content is required for text input type"
        )

    if body.input_type == "image" and not body.file_path:
        raise HTTPException(
            status_code=400, detail="File path is required for image input type"
        )

    if body.input_type == "video" and not body.url:
        raise HTTPException(
            status_code=400, detail="URL is required for video input type"
        )

    # Sanitize inputs
    if body.url:
        body.url = body.url.strip()
    if body.content:
        body.content = body.content.strip()

    # Search Clarity validation
    if body.user_query:
        if not settings.ENABLE_SEARCH_CLARITY:
            raise HTTPException(
                status_code=503, detail="Search Clarity feature is temporarily disabled"
            )
        if len(body.user_query) > 200:
            raise HTTPException(
                status_code=400, detail="Query must be 200 characters or less"
            )
        body.user_query = body.user_query.strip()

    # Create check record
    check = Check(
        id=str(uuid.uuid4()),
        user_id=user.id,
        input_type=body.input_type,
        input_content=json.dumps(
            {"content": body.content, "url": body.url, "file_path": body.file_path}
        ),
        input_url=body.url,
        status="processing",  # Start as processing (no pending state for inline)
        credits_used=1,
        user_query=body.user_query,
    )

    session.add(check)

    # Reserve credits
    user.credits -= 1
    user.total_credits_used += 1
    await session.commit()
    await session.refresh(check)

    # Prepare input data for pipeline
    input_data = {
        "input_type": body.input_type,
        "content": body.content,
        "url": body.url,
        "file_path": body.file_path,
        "user_query": body.user_query,
        "frozen_evidence": body.frozen_evidence,
    }

    # Create progress reporter
    progress_reporter = ProgressReporter(check.id)

    async def run_pipeline_and_save():
        """
        Background task that runs the pipeline and saves results.
        This runs INDEPENDENTLY of the SSE stream - results are saved
        even if the client disconnects.
        """
        try:
            logger.info(f"[PIPELINE TASK] Starting pipeline for check {check.id}")
            result = await asyncio.wait_for(
                run_pipeline(check.id, user.id, input_data, progress_reporter),
                timeout=300,  # 5 minute hard timeout
            )

            # result is None for article mode (waiting_for_selection)
            if result is not None:
                logger.info(f"[PIPELINE TASK] Pipeline completed for check {check.id}")

                # Save results to database
                async with async_session() as save_session:
                    await save_check_results_async(check.id, result, save_session)
                    await save_session.commit()
                logger.info(f"[PIPELINE TASK] Results saved for check {check.id}")

                # Send success notifications
                content_data = {"metadata": result.get("ingest_metadata", {})}
                await send_success_notifications(
                    user.id, check.id, result, input_data, content_data
                )

                # Signal completion
                await progress_reporter.report_completed()
                logger.info(f"[PIPELINE TASK] Check {check.id} fully completed")
            else:
                logger.info(
                    f"[PIPELINE TASK] Check {check.id} phase 1 complete — "
                    f"waiting for claim selection"
                )

        except asyncio.TimeoutError:
            logger.error(f"[PIPELINE TASK] Pipeline timed out for check {check.id}")
            await handle_pipeline_failure(
                check.id, user.id, Exception("Pipeline timed out after 5 minutes")
            )
            await progress_reporter.report_error(
                "Pipeline timed out. Your credit has been returned."
            )

        except PipelineError as e:
            logger.error(f"[PIPELINE TASK] Pipeline error for check {check.id}: {e}")
            await handle_pipeline_failure(check.id, user.id, e)
            await progress_reporter.report_error(str(e))

        except Exception as e:
            logger.error(f"[PIPELINE TASK] Unexpected error for check {check.id}: {e}")
            import traceback

            logger.error(traceback.format_exc())
            await handle_pipeline_failure(check.id, user.id, e)
            await progress_reporter.report_error(str(e))

    # Start pipeline as fire-and-forget background task
    # This ensures results are saved even if client disconnects
    pipeline_task = asyncio.create_task(run_pipeline_and_save())
    logger.info(f"[SSE STREAM] Background pipeline task created for check {check.id}")

    async def pipeline_stream():
        """
        Async generator that yields SSE events.
        The actual pipeline runs independently - this just streams events.
        """
        logger.info(f"[SSE STREAM] Starting event stream for check {check.id}")
        event_count = 0

        try:
            async for event in progress_reporter.events(
                pipeline_task, max_duration_seconds=300
            ):
                event_count += 1
                if (
                    event_count <= 5 or event_count % 10 == 0
                ):  # Log first 5 and every 10th
                    logger.info(
                        f"[SSE STREAM] Event #{event_count} for check {check.id}"
                    )
                yield event
        except Exception as e:
            logger.error(
                f"[SSE STREAM] Error streaming events for check {check.id}: {e}"
            )
        finally:
            logger.info(
                f"[SSE STREAM] Stream ended for check {check.id} after {event_count} events"
            )
            # Note: We do NOT cancel the pipeline task here - it should complete independently

    return StreamingResponse(
        pipeline_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "X-Check-Id": check.id,  # Include check ID in headers for client
        },
    )


@router.get("")
@router.get("/")
async def get_checks(
    skip: int = 0,
    limit: int = 20,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Get user's check history"""
    stmt = (
        select(Check)
        .where(Check.user_id == current_user["id"])
        .order_by(desc(Check.created_at))
        .offset(skip)
        .limit(limit)
    )
    result = await session.execute(stmt)
    checks = result.scalars().all()

    # Get claims for each check (including first claim for preview)
    check_data = []
    for check in checks:
        # Get first claim for preview (ordered by position)
        first_claim_stmt = (
            select(Claim)
            .where(Claim.check_id == check.id)
            .order_by(Claim.position)
            .limit(1)
        )
        first_claim_result = await session.execute(first_claim_stmt)
        first_claim = first_claim_result.scalar_one_or_none()

        # Count total claims
        claims_count_stmt = select(func.count(Claim.id)).where(
            Claim.check_id == check.id
        )
        claims_count_result = await session.execute(claims_count_stmt)
        claims_count = claims_count_result.scalar() or 0

        # Build claims array with first claim details
        claims_array = []
        if first_claim:
            claim_map_raw = first_claim.claim_map
            if isinstance(claim_map_raw, str):
                claim_map_raw = json.loads(claim_map_raw)
            claim_map = claim_map_raw if claim_map_raw else None
            claims_array.append(
                {
                    "id": first_claim.id,
                    "text": first_claim.text,
                    "position": first_claim.position,
                    "claimType": first_claim.claim_type,
                    "elementCount": (
                        len(claim_map.get("elements", [])) if claim_map else 0
                    ),
                    "orientation": claim_map.get("orientation") if claim_map else None,
                }
            )

        check_data.append(
            {
                "id": check.id,
                "inputType": check.input_type,
                "inputUrl": check.input_url,
                "status": check.status,
                "creditsUsed": check.credits_used,
                "processingTimeMs": check.processing_time_ms,
                "createdAt": check.created_at.isoformat(),
                "completedAt": (
                    check.completed_at.isoformat() if check.completed_at else None
                ),
                "claimsCount": claims_count,
                "claims": claims_array,  # First claim for preview
                "entryMode": check.entry_mode,
                "selectedClaimsCount": check.selected_claims_count,
                "articleDomain": check.article_domain,
            }
        )

    return {"checks": check_data, "total": len(checks)}


@router.get("/{check_id}")
async def get_check(
    check_id: str,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Get a specific check with all claims and evidence"""
    stmt = select(Check).where(
        Check.id == check_id, Check.user_id == current_user["id"]
    )
    result = await session.execute(stmt)
    check = result.scalar_one_or_none()

    if not check:
        raise HTTPException(status_code=404, detail="Check not found")

    # Get real-time progress from Redis when processing (inline SSE pipeline)
    current_stage = None
    progress_percent = None
    progress_message = None

    if check.status in ("processing", "waiting_for_selection"):
        try:
            redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
            progress_data = redis_client.get(f"inline-progress:{check_id}")

            if progress_data:
                data = json.loads(progress_data)
                current_stage = data.get("stage", "processing")
                progress_percent = data.get("progress", 0)
                progress_message = data.get("message", "Processing...")

            redis_client.close()
        except Exception as e:
            logger.warning(
                f"Failed to get progress from Redis for check {check_id}: {e}"
            )

    # Get claims with evidence
    claims_stmt = (
        select(Claim).where(Claim.check_id == check.id).order_by(Claim.position)
    )
    claims_result = await session.execute(claims_stmt)
    claims = claims_result.scalars().all()

    # Get per-claim raw source counts for "View sources" link
    from app.models.check import RawEvidence

    raw_counts_stmt = (
        select(RawEvidence.claim_position, func.count(RawEvidence.id))
        .where(RawEvidence.check_id == check.id)
        .group_by(RawEvidence.claim_position)
    )
    raw_counts_result = await session.execute(raw_counts_stmt)
    raw_counts_by_position = dict(raw_counts_result.all())

    claims_data = []
    for claim in claims:
        evidence_stmt = select(Evidence).where(Evidence.claim_id == claim.id)
        evidence_result = await session.execute(evidence_stmt)
        evidence = evidence_result.scalars().all()

        claims_data.append(
            {
                "id": claim.id,
                "text": claim.text,
                "position": claim.position,
                # ClaimMap fields
                "claimMap": (
                    _claim_map_to_camel_case(claim.claim_map)
                    if claim.claim_map
                    else None
                ),
                "claimType": claim.claim_type,
                "isSelected": claim.is_selected,
                "significanceRank": claim.significance_rank,
                # Context preservation fields (Context Improvement - Phase 5)
                "subjectContext": claim.subject_context,
                "keyEntities": (claim.key_entities if claim.key_entities else []),
                "sourceTitle": claim.source_title,
                "sourceUrl": claim.source_url,
                # Sources reviewed count (for "View X sources" link when no evidence displayed)
                "sourcesReviewedCount": raw_counts_by_position.get(claim.position, 0),
                "evidence": [
                    {
                        "id": ev.id,
                        "evidenceId": ev.evidence_id,
                        "source": ev.source,
                        "url": ev.url,
                        "title": ev.title,
                        "snippet": ev.snippet,
                        "publishedDate": (
                            ev.published_date.isoformat() if ev.published_date else None
                        ),
                        "relevanceScore": ev.relevance_score,
                        # Source type fields
                        "isFactcheck": ev.is_factcheck,
                        "externalSourceProvider": ev.external_source_provider,
                        "sourceType": ev.source_type,
                    }
                    for ev in evidence
                ],
            }
        )

    return {
        "id": check.id,
        "inputType": check.input_type,
        "inputContent": json.loads(check.input_content),
        "inputUrl": check.input_url,
        "status": check.status,
        "creditsUsed": check.credits_used,
        "processingTimeMs": check.processing_time_ms,
        "errorMessage": check.error_message,
        "entryMode": check.entry_mode,
        "selectedClaimsCount": check.selected_claims_count,
        # Article classification (domain detection)
        "articleDomain": check.article_domain,
        "articleSecondaryDomains": check.article_secondary_domains,
        "articleJurisdiction": check.article_jurisdiction,
        "articleClassificationSource": check.article_classification_source,  # 'cache_pattern', 'llm_primary', 'fallback_general', etc.
        # Search Clarity fields
        "userQuery": check.user_query,
        "queryResponse": check.query_response,
        "queryConfidence": check.query_confidence,
        "querySources": (
            check.query_sources.get("sources", []) if check.query_sources else None
        ),
        "queryRelatedClaims": (
            check.query_sources.get("related_claims", [])
            if check.query_sources
            else None
        ),
        "claims": claims_data,
        "createdAt": check.created_at.isoformat(),
        "completedAt": check.completed_at.isoformat() if check.completed_at else None,
        # Real-time progress fields (for polling fallback when SSE unavailable)
        "currentStage": current_stage,
        "progress": progress_percent,
        "progressMessage": progress_message,
    }


# ============================================================================
# CLAIM SELECTION ENDPOINT (Phase 1 → Phase 2 gate)
# ============================================================================


class SelectClaimsRequest(BaseModel):
    """Request body for claim selection endpoint."""

    selected_positions: List[int]


@router.patch("/{check_id}/select-claims")
async def select_claims(
    check_id: str,
    body: SelectClaimsRequest,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Select claims for Phase 2 analysis (article mode only).

    After Phase 1 extracts and ranks claims, the frontend presents them
    to the user. The user selects which claims to investigate, and this
    endpoint triggers Phase 2 of the pipeline.

    Request body: {"selected_positions": [0, 2, 4]}
    """
    from app.core.database import async_session as async_session_factory
    from app.pipeline.progress import ProgressReporter
    from app.pipeline.runner import (
        run_pipeline_phase2,
        save_check_results_async,
        handle_pipeline_failure,
        send_success_notifications,
        PipelineError,
    )

    # 1. Validate check exists and belongs to user
    stmt = select(Check).where(
        Check.id == check_id, Check.user_id == current_user["id"]
    )
    result = await session.execute(stmt)
    check = result.scalar_one_or_none()

    if not check:
        raise HTTPException(status_code=404, detail="Check not found")

    # 2. Validate check is in waiting_for_selection status
    if check.status != "waiting_for_selection":
        raise HTTPException(
            status_code=409,
            detail=f"Check is not waiting for claim selection (current status: {check.status})",
        )

    # 3. Validate selected_positions
    if not body.selected_positions:
        raise HTTPException(
            status_code=400, detail="At least one claim must be selected"
        )

    # Load claims to validate positions
    claims_stmt = (
        select(Claim).where(Claim.check_id == check_id).order_by(Claim.position)
    )
    claims_result = await session.execute(claims_stmt)
    db_claims = list(claims_result.scalars().all())

    valid_positions = {c.position for c in db_claims}
    invalid_positions = [p for p in body.selected_positions if p not in valid_positions]

    if invalid_positions:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid claim positions: {invalid_positions}. Valid: {sorted(valid_positions)}",
        )

    # 4. Update claim selection in DB
    selected_set = set(body.selected_positions)
    for claim in db_claims:
        claim.is_selected = claim.position in selected_set

    check.selected_claims_count = len(selected_set)

    await session.commit()

    logger.info(
        f"[SELECT CLAIMS] Check {check_id}: user selected positions {body.selected_positions} "
        f"({len(selected_set)} of {len(db_claims)} claims)"
    )

    # 5. Trigger Phase 2 as a background task
    input_content = json.loads(check.input_content) if check.input_content else {}
    input_data = {
        "input_type": check.input_type,
        "content": input_content.get("content"),
        "url": input_content.get("url") or check.input_url,
        "file_path": input_content.get("file_path"),
        "user_query": check.user_query,
    }

    progress_reporter = ProgressReporter(check_id)

    async def run_phase2_and_save():
        try:
            logger.info(f"[PHASE 2 TASK] Starting phase 2 for check {check_id}")
            phase2_result = await asyncio.wait_for(
                run_pipeline_phase2(
                    check_id=check_id,
                    user_id=current_user["id"],
                    input_data=input_data,
                    progress_reporter=progress_reporter,
                ),
                timeout=300,
            )

            # Save results
            async with async_session_factory() as save_session:
                await save_check_results_async(check_id, phase2_result, save_session)
                await save_session.commit()

            logger.info(f"[PHASE 2 TASK] Results saved for check {check_id}")

            # Send notifications
            content_data = {"metadata": phase2_result.get("ingest_metadata", {})}
            await send_success_notifications(
                current_user["id"], check_id, phase2_result, input_data, content_data
            )

            await progress_reporter.report_completed()
            logger.info(f"[PHASE 2 TASK] Check {check_id} fully completed")

        except asyncio.TimeoutError:
            logger.error(f"[PHASE 2 TASK] Phase 2 timed out for check {check_id}")
            await handle_pipeline_failure(
                check_id,
                current_user["id"],
                Exception("Analysis timed out after 5 minutes"),
            )
            await progress_reporter.report_error(
                "Analysis timed out. Your credit has been returned."
            )

        except PipelineError as e:
            logger.error(f"[PHASE 2 TASK] Pipeline error for check {check_id}: {e}")
            await handle_pipeline_failure(check_id, current_user["id"], e)
            await progress_reporter.report_error(str(e))

        except Exception as e:
            logger.error(f"[PHASE 2 TASK] Unexpected error for check {check_id}: {e}")
            import traceback

            logger.error(traceback.format_exc())
            await handle_pipeline_failure(check_id, current_user["id"], e)
            await progress_reporter.report_error(str(e))

    asyncio.create_task(run_phase2_and_save())

    return {
        "status": "processing",
        "checkId": check_id,
        "selectedPositions": body.selected_positions,
        "selectedCount": len(selected_set),
        "message": "Analysis started for selected claims",
    }


@router.get("/{check_id}/progress")
async def stream_check_progress(
    check_id: str,
    current_user: dict = Depends(get_current_user_sse),
    session: AsyncSession = Depends(get_session),
):
    """Stream real-time progress updates via SSE"""

    # Verify check belongs to user
    stmt = select(Check).where(
        Check.id == check_id, Check.user_id == current_user["id"]
    )
    result = await session.execute(stmt)
    check = result.scalar_one_or_none()

    if not check:
        raise HTTPException(status_code=404, detail="Check not found")

    def event_stream():
        """Generate SSE events for pipeline progress - reads from Redis"""
        import time

        redis_client = None
        try:
            redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
            progress_key = f"inline-progress:{check_id}"

            # Initial connection event
            yield f"data: {safe_json_dumps({'type': 'connected', 'checkId': check_id, 'timestamp': datetime.now(timezone.utc).isoformat()})}\n\n"

            # Check if already completed/failed in database
            if check.status == "completed":
                yield f"data: {json.dumps({'type': 'completed', 'checkId': check_id, 'status': 'completed', 'progress': 100})}\n\n"
                return
            elif check.status == "failed":
                yield f"data: {safe_json_dumps({'type': 'error', 'checkId': check_id, 'status': 'failed', 'error': check.error_message})}\n\n"
                return

            # Poll Redis for inline pipeline progress
            last_progress = -1
            last_stage = ""
            timeout_counter = 0
            max_timeout = 300  # 5 minutes
            # Current state (persists between iterations for heartbeats)
            current_stage = "starting"
            current_progress = 0
            current_message = "Initializing..."
            current_time_estimate = "within 2 minutes"

            while timeout_counter < max_timeout:
                try:
                    # Read progress from Redis (written by ProgressReporter)
                    progress_data = redis_client.get(progress_key)

                    if progress_data:
                        data = json.loads(progress_data)
                        status = data.get("status", "processing")
                        current_progress = data.get("progress", 0)
                        current_stage = data.get("stage", "processing")
                        current_message = data.get("message", "Processing...")
                        current_time_estimate = data.get(
                            "timeEstimate", "within 2 minutes"
                        )

                        if status == "completed":
                            yield f"data: {json.dumps({'type': 'completed', 'checkId': check_id, 'status': 'completed', 'progress': 100, 'message': 'Analysis completed successfully'})}\n\n"
                            break
                        elif status == "failed":
                            error = data.get("error", "Processing failed")
                            yield f"data: {safe_json_dumps({'type': 'error', 'checkId': check_id, 'status': 'failed', 'error': error})}\n\n"
                            break
                        elif (
                            current_progress > last_progress
                            or current_stage != last_stage
                        ):
                            # Send progress update when progress OR stage changes
                            yield f"data: {json.dumps({'type': 'progress', 'checkId': check_id, 'stage': current_stage, 'progress': current_progress, 'message': current_message, 'timeEstimate': current_time_estimate})}\n\n"
                            last_progress = current_progress
                            last_stage = current_stage

                    # Send progress-heartbeat every 5 seconds to keep frontend in sync
                    # Include current progress so frontend always has latest state
                    if timeout_counter > 0 and timeout_counter % 5 == 0:
                        yield f"data: {json.dumps({'type': 'progress', 'checkId': check_id, 'stage': current_stage, 'progress': current_progress, 'message': current_message, 'timeEstimate': current_time_estimate})}\n\n"

                    time.sleep(1)
                    timeout_counter += 1

                except Exception as e:
                    logger.error(f"SSE error for check {check_id}: {e}")
                    yield f"data: {json.dumps({'type': 'error', 'error': 'Connection error occurred'})}\n\n"
                    break

            # Timeout reached
            if timeout_counter >= max_timeout:
                yield f"data: {json.dumps({'type': 'timeout', 'checkId': check_id, 'message': 'Connection timeout - please refresh'})}\n\n"

        except Exception as e:
            logger.error(f"SSE stream error: {e}")
            yield f"data: {json.dumps({'type': 'error', 'error': 'Stream connection failed'})}\n\n"
        finally:
            if redis_client:
                redis_client.close()

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering for SSE
        },
    )


@router.get("/{check_id}/export/pdf")
async def export_check_pdf(
    check_id: str,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Export fact-check as PDF report"""

    # Fetch check with user verification
    stmt = select(Check).where(
        Check.id == check_id, Check.user_id == current_user["id"]
    )
    result = await session.execute(stmt)
    check = result.scalar_one_or_none()

    if not check:
        raise HTTPException(status_code=404, detail="Check not found")

    if check.status != "completed":
        raise HTTPException(
            status_code=400, detail="PDF export only available for completed checks"
        )

    # Fetch claims ordered by position
    claims_stmt = (
        select(Claim).where(Claim.check_id == check_id).order_by(Claim.position)
    )
    claims_result = await session.execute(claims_stmt)
    claims = claims_result.scalars().all()

    # Fetch evidence for each claim (top 3 by relevance)
    claims_with_evidence = []
    for claim in claims:
        evidence_stmt = (
            select(Evidence)
            .where(Evidence.claim_id == claim.id)
            .order_by(desc(Evidence.relevance_score))
            .limit(3)
        )
        evidence_result = await session.execute(evidence_stmt)
        evidence_list = evidence_result.scalars().all()

        claim_map = claim.claim_map if claim.claim_map else None
        claims_with_evidence.append(
            {
                "text": claim.text,
                "claim_type": claim.claim_type,
                "claim_map": claim_map,
                "orientation": claim_map.get("orientation") if claim_map else None,
                "elements": claim_map.get("elements", []) if claim_map else [],
                "evidence": evidence_list,
            }
        )

    # Pre-compute totals for template (avoids broken Jinja2 sum filter on nested lists)
    total_evidence = sum(len(c.get("evidence", [])) for c in claims_with_evidence)
    total_elements = sum(len(c.get("elements", [])) for c in claims_with_evidence)

    # Render HTML template
    try:
        template = jinja_env.get_template("pdf/fact_check_report.html")
        html_content = template.render(
            check=check,
            claims=claims_with_evidence,
            total_evidence=total_evidence,
            total_elements=total_elements,
            now=datetime.utcnow(),
        )
    except Exception as e:
        logger.error(f"Template rendering failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate PDF template")

    # Generate PDF with xhtml2pdf
    try:
        pdf_buffer = BytesIO()
        pisa_status = pisa.CreatePDF(html_content, dest=pdf_buffer, encoding="utf-8")

        if pisa_status.err:
            raise Exception(f"PDF generation error: {pisa_status.err}")

        pdf_bytes = pdf_buffer.getvalue()
        pdf_buffer.close()
    except Exception as e:
        logger.error(f"PDF generation failed: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to generate PDF. Please try again."
        )

    # Return PDF as downloadable file
    filename = f"tru8-report-{check_id[:8]}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
            "Cache-Control": "no-cache",
        },
    )


# ============================================================================
# FULL SOURCES LIST - Pro Feature
# ============================================================================


class SourcesResponse(BaseModel):
    """Response model for check sources endpoint"""

    checkId: str
    totalSources: int
    includedCount: int
    filteredCount: int
    legacyCheck: bool
    message: Optional[str] = None
    claims: Optional[List[dict]] = None
    filterBreakdown: Optional[dict] = None


@router.get("/{check_id}/sources")
async def get_check_sources(
    check_id: str,
    include_filtered: bool = True,
    sort_by: str = "relevance",  # relevance, date
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Get all sources reviewed for a check (Pro feature).

    This endpoint returns all sources that were reviewed during fact-checking,
    including those that were filtered out. It shows which filtering stage
    excluded each source and why.

    Query params:
    - include_filtered: Include filtered sources (default: true)
    - sort_by: Sort order - relevance or date
    """

    # 1. Verify check belongs to user
    stmt = select(Check).where(
        Check.id == check_id, Check.user_id == current_user["id"]
    )
    result = await session.execute(stmt)
    check = result.scalar_one_or_none()

    if not check:
        raise HTTPException(status_code=404, detail="Check not found")

    # 2. Check Pro subscription OR beta tester status
    sub_stmt = select(Subscription).where(
        Subscription.user_id == current_user["id"],
        Subscription.status.in_(["active", "trialing"]),
    )
    sub_result = await session.execute(sub_stmt)
    subscription = sub_result.scalar_one_or_none()

    # Beta testers get full Pro access
    is_beta_tester = current_user.get("email", "").lower() in [
        e.lower() for e in settings.BETA_TESTER_EMAILS
    ]
    is_pro = (subscription and subscription.plan == "pro") or is_beta_tester

    if not is_pro:
        # Return limited response for non-Pro users
        return {
            "checkId": check_id,
            "totalSources": check.raw_sources_count or 0,
            "includedCount": 0,
            "filteredCount": 0,
            "legacyCheck": check.raw_sources_count is None
            or check.raw_sources_count == 0,
            "message": "Upgrade to Pro to see all sources reviewed during fact-checking",
            "claims": None,
            "filterBreakdown": None,
            "requiresUpgrade": True,
        }

    # 3. Query RawEvidence for this check
    raw_stmt = select(RawEvidence).where(RawEvidence.check_id == check_id)

    if not include_filtered:
        raw_stmt = raw_stmt.where(RawEvidence.is_included == True)

    # Apply sorting
    if sort_by == "date":
        raw_stmt = raw_stmt.order_by(desc(RawEvidence.published_date))
    else:  # relevance (default)
        raw_stmt = raw_stmt.order_by(desc(RawEvidence.relevance_score))

    raw_result = await session.execute(raw_stmt)
    raw_evidence = raw_result.scalars().all()

    # Check for legacy check (no raw evidence stored)
    if not raw_evidence and (
        check.raw_sources_count is None or check.raw_sources_count == 0
    ):
        return {
            "checkId": check_id,
            "totalSources": 0,
            "includedCount": 0,
            "filteredCount": 0,
            "legacyCheck": True,
            "message": "Source data not available for checks created before this feature.",
            "claims": None,
            "filterBreakdown": None,
        }

    # 4. Group sources by claim
    claims_dict = {}
    filter_breakdown = {
        "temporal": 0,
        "dedup": 0,
        "diversity": 0,
        "domain_cap": 0,
        "validation": 0,
        "extraction_failed": 0,
    }

    included_count = 0
    filtered_count = 0

    for raw_ev in raw_evidence:
        claim_pos = raw_ev.claim_position
        if claim_pos not in claims_dict:
            claims_dict[claim_pos] = {
                "claimPosition": claim_pos,
                "claimText": raw_ev.claim_text,
                "sourcesCount": 0,
                "sources": [],
            }

        source_data = {
            "id": raw_ev.id,
            "source": raw_ev.source,
            "title": raw_ev.title,
            "url": raw_ev.url,
            "publishedDate": (
                raw_ev.published_date.isoformat() if raw_ev.published_date else None
            ),
            "relevanceScore": raw_ev.relevance_score,
            "isIncluded": raw_ev.is_included,
            "filterStage": raw_ev.filter_stage,
            "filterReason": raw_ev.filter_reason,
            "isFactcheck": raw_ev.is_factcheck,
            "externalSourceProvider": raw_ev.external_source_provider,
        }

        claims_dict[claim_pos]["sources"].append(source_data)
        claims_dict[claim_pos]["sourcesCount"] += 1

        if raw_ev.is_included:
            included_count += 1
        else:
            filtered_count += 1
            # Count by filter stage
            stage = raw_ev.filter_stage or "unknown"
            if stage in filter_breakdown:
                filter_breakdown[stage] += 1

    # Convert to sorted list
    claims_list = sorted(claims_dict.values(), key=lambda c: c["claimPosition"])

    return {
        "checkId": check_id,
        "totalSources": len(raw_evidence),
        "includedCount": included_count,
        "filteredCount": filtered_count,
        "legacyCheck": False,
        "claims": claims_list,
        "filterBreakdown": filter_breakdown,
    }


# ============================================================================
# PUBLIC ENDPOINT - For OG Image Generation (no auth required)
# ============================================================================


@router.get("/public/{check_id}")
async def get_public_check(
    check_id: str, detailed: bool = False, session: AsyncSession = Depends(get_session)
):
    """Get public check data. No auth required.

    Query params:
    - detailed: If true, returns full check data for public report page.
                If false (default), returns minimal data for OG card generation.

    Only returns completed checks.
    """
    # Get check from database (no user verification - public endpoint)
    stmt = select(Check).where(Check.id == check_id)
    result = await session.execute(stmt)
    check = result.scalar_one_or_none()

    if not check:
        raise HTTPException(status_code=404, detail="Check not found")

    if check.status != "completed":
        raise HTTPException(status_code=404, detail="Check not found or not completed")

    # Get claims for this check
    claims_stmt = (
        select(Claim).where(Claim.check_id == check_id).order_by(Claim.position)
    )
    claims_result = await session.execute(claims_stmt)
    claims = claims_result.scalars().all()

    # Get all evidence for this check to calculate stats
    all_evidence = []
    top_sources_set = set()

    for claim in claims:
        evidence_stmt = (
            select(Evidence)
            .where(Evidence.claim_id == claim.id)
            .order_by(desc(Evidence.relevance_score))
        )
        evidence_result = await session.execute(evidence_stmt)
        evidence_list = evidence_result.scalars().all()
        all_evidence.extend(evidence_list)

        # Collect unique sources
        for ev in evidence_list:
            if ev.source:
                top_sources_set.add(ev.source)

    # Extract source domain and title from URL
    source_domain = None
    title = None

    if check.input_url:
        try:
            from urllib.parse import urlparse
            import re

            parsed = urlparse(check.input_url)
            source_domain = parsed.netloc.replace("www.", "")

            # Extract title from URL slug (last path segment)
            path_parts = [p for p in parsed.path.split("/") if p and len(p) > 3]
            if path_parts:
                slug = path_parts[-1]
                # Remove file extensions
                slug = re.sub(r"\.\w+$", "", slug)
                # Remove trailing IDs (various patterns: -b2895946, -12345678, _abc123)
                slug = re.sub(r"[-_][a-zA-Z]?\d{5,}$", "", slug)  # -b2895946, -12345678
                slug = re.sub(r"[-_]\d+$", "", slug)  # Trailing numbers
                slug = re.sub(
                    r"[-_][a-f0-9]{8,}$", "", slug, flags=re.IGNORECASE
                )  # UUIDs/hashes
                # Convert slug to title case
                title = slug.replace("-", " ").replace("_", " ").title()
        except Exception:
            pass

    # Fallback title options
    if not title or len(title) < 10:
        if check.article_excerpt:
            # Use first sentence of article excerpt
            first_sentence = check.article_excerpt.split(".")[0]
            title = (
                first_sentence[:70] + "..."
                if len(first_sentence) > 70
                else first_sentence
            )
        elif source_domain:
            title = f"Report from {source_domain}"

    # Minimal response for OG card generation
    base_response = {
        "id": check.id,
        "title": title,
        "sourceUrl": check.input_url,
        "sourceDomain": source_domain,
        "claimsCount": len(claims),
        "sourcesCount": check.raw_sources_count or len(top_sources_set),
        "evidenceCount": len(all_evidence),
        "entryMode": check.entry_mode,
        "selectedClaimsCount": check.selected_claims_count,
        "topSources": list(top_sources_set)[:5],
    }

    # If not detailed, return minimal response for OG card
    if not detailed:
        return base_response

    # Build detailed response for public report page
    # Build claims with evidence
    claims_data = []
    for claim in claims:
        # Get evidence for this claim
        evidence_stmt = (
            select(Evidence)
            .where(Evidence.claim_id == claim.id)
            .order_by(desc(Evidence.relevance_score))
        )
        evidence_result = await session.execute(evidence_stmt)
        evidence_list = evidence_result.scalars().all()

        evidence_data = []
        for ev in evidence_list:
            evidence_data.append(
                {
                    "id": ev.id,
                    "evidenceId": ev.evidence_id,
                    "source": ev.source,
                    "url": ev.url,
                    "title": ev.title,
                    "snippet": ev.snippet,
                    "publishedDate": (
                        ev.published_date.isoformat() if ev.published_date else None
                    ),
                    "relevanceScore": ev.relevance_score,
                    "isFactcheck": ev.is_factcheck,
                    "factcheckPublisher": ev.factcheck_publisher,
                    "factcheckRating": ev.factcheck_rating,
                    "contextBefore": ev.context_before,
                    "contextAfter": ev.context_after,
                }
            )

        claim_map = (
            _claim_map_to_camel_case(claim.claim_map) if claim.claim_map else None
        )
        claims_data.append(
            {
                "id": claim.id,
                "text": claim.text,
                "position": claim.position,
                "claimMap": claim_map,
                "claimType": claim.claim_type,
                "isSelected": claim.is_selected,
                "isTimeSensitive": claim.is_time_sensitive,
                "timeReference": claim.time_reference,
                "evidence": evidence_data,
            }
        )

    return {
        **base_response,
        # Full check metadata
        "inputType": check.input_type,
        "inputUrl": check.input_url,
        "inputContent": check.input_content,
        "articleExcerpt": check.article_excerpt,
        "articleDomain": check.article_domain,
        "articleJurisdiction": check.article_jurisdiction,
        "createdAt": check.created_at.isoformat() if check.created_at else None,
        "completedAt": check.completed_at.isoformat() if check.completed_at else None,
        # Full claims with evidence
        "claims": claims_data,
    }


@router.get("/{check_id}/sources/export")
async def export_check_sources(
    check_id: str,
    format: str = "csv",  # csv, bibtex, apa
    include_filtered: bool = False,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Export sources as CSV, BibTeX, or APA format (Pro feature).

    Query params:
    - format: Export format - csv, bibtex, or apa
    - include_filtered: Include filtered sources (default: false)
    """
    import csv
    from io import StringIO

    # 1. Verify check belongs to user
    stmt = select(Check).where(
        Check.id == check_id, Check.user_id == current_user["id"]
    )
    result = await session.execute(stmt)
    check = result.scalar_one_or_none()

    if not check:
        raise HTTPException(status_code=404, detail="Check not found")

    # 2. Check Pro subscription OR beta tester status
    sub_stmt = select(Subscription).where(
        Subscription.user_id == current_user["id"],
        Subscription.status.in_(["active", "trialing"]),
    )
    sub_result = await session.execute(sub_stmt)
    subscription = sub_result.scalar_one_or_none()

    # Beta testers get full Pro access
    is_beta_tester = current_user.get("email", "").lower() in [
        e.lower() for e in settings.BETA_TESTER_EMAILS
    ]
    is_pro = (subscription and subscription.plan == "pro") or is_beta_tester

    if not is_pro:
        raise HTTPException(
            status_code=403, detail="Source export is a Pro feature. Upgrade to access."
        )

    # 3. Query RawEvidence
    raw_stmt = select(RawEvidence).where(RawEvidence.check_id == check_id)

    if not include_filtered:
        raw_stmt = raw_stmt.where(RawEvidence.is_included == True)

    raw_stmt = raw_stmt.order_by(
        RawEvidence.claim_position, desc(RawEvidence.relevance_score)
    )

    raw_result = await session.execute(raw_stmt)
    raw_evidence = raw_result.scalars().all()

    if not raw_evidence:
        raise HTTPException(status_code=404, detail="No sources available for export")

    # 4. Generate export based on format
    # NOTE: We intentionally exclude internal scoring metrics (relevance_score,
    # filter_stage, filter_reason) from exports.
    if format == "csv":
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(
            ["Claim", "Source", "Title", "URL", "Published Date", "Used in Analysis"]
        )

        for ev in raw_evidence:
            writer.writerow(
                [
                    ev.claim_text or "",
                    ev.source,
                    ev.title,
                    ev.url,
                    ev.published_date.strftime("%Y-%m-%d") if ev.published_date else "",
                    "Yes" if ev.is_included else "No",
                ]
            )

        content = output.getvalue()
        media_type = "text/csv"
        filename = f"tru8-sources-{check_id[:8]}.csv"

    elif format == "bibtex":
        lines = []
        for i, ev in enumerate(raw_evidence):
            # Generate a unique key for each entry
            key = f"tru8_{check_id[:8]}_{i+1}"
            pub_year = ev.published_date.year if ev.published_date else "n.d."
            pub_month = ev.published_date.strftime("%B") if ev.published_date else ""
            pub_day = ev.published_date.day if ev.published_date else ""

            # Standard BibTeX @online entry (no internal scoring)
            entry = f"""@online{{{key},
    title = {{{ev.title}}},
    author = {{{{{ev.source}}}}},
    year = {{{pub_year}}},
    month = {{{pub_month.lower()}}},
    url = {{{ev.url}}},
    urldate = {{{datetime.now().strftime("%Y-%m-%d")}}}
}}"""
            lines.append(entry)

        content = "\n\n".join(lines)
        media_type = "application/x-bibtex"
        filename = f"tru8-sources-{check_id[:8]}.bib"

    elif format == "apa":
        lines = []
        for ev in raw_evidence:
            # APA 7th edition format for web pages
            pub_date = (
                ev.published_date.strftime("%Y, %B %d") if ev.published_date else "n.d."
            )
            entry = f"{ev.source}. ({pub_date}). {ev.title}. Retrieved from {ev.url}"
            lines.append(entry)

        content = "\n\n".join(lines)
        media_type = "text/plain"
        filename = f"tru8-sources-{check_id[:8]}-apa.txt"

    else:
        raise HTTPException(
            status_code=400, detail="Invalid format. Supported: csv, bibtex, apa"
        )

    return Response(
        content=content,
        media_type=media_type,
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
            "Cache-Control": "no-cache",
        },
    )
