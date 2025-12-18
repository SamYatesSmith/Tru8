from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
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
from app.workers.pipeline import process_check
from app.workers import celery_app
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
from pathlib import Path

logger = logging.getLogger(__name__)

router = APIRouter()

# Setup Jinja2 environment for PDF templates
template_dir = Path(__file__).parent.parent.parent / "templates"
jinja_env = Environment(loader=FileSystemLoader(str(template_dir)))

def safe_json_dumps(data: dict) -> str:
    """Safely serialize JSON for SSE with ASCII encoding"""
    return json.dumps(data, ensure_ascii=True, separators=(',', ':'))

class CreateCheckRequest(BaseModel):
    input_type: str  # 'url', 'text', 'image', 'video'
    content: Optional[str] = None
    url: Optional[str] = None
    file_path: Optional[str] = None  # For uploaded files
    user_query: Optional[str] = None  # Search Clarity feature

@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """Upload a file for fact-checking (images only)"""
    
    # Validate file type
    if not file.content_type or not file.content_type.startswith('image/'):
        raise HTTPException(
            status_code=400, 
            detail="Only image files are supported"
        )
    
    # Check file size (6MB limit from project requirements)
    max_size = 6 * 1024 * 1024  # 6MB
    content = await file.read()
    if len(content) > max_size:
        raise HTTPException(
            status_code=413,
            detail="File too large. Maximum size is 6MB."
        )
    
    # Generate unique filename
    file_id = str(uuid.uuid4())
    file_extension = Path(file.filename).suffix.lower()
    if file_extension not in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']:
        raise HTTPException(
            status_code=400,
            detail="Unsupported image format. Supported: jpg, jpeg, png, gif, bmp, webp"
        )
    
    filename = f"{file_id}{file_extension}"
    
    # For now, store locally (TODO: implement S3 storage)
    upload_dir = Path("uploads")
    upload_dir.mkdir(exist_ok=True)
    file_path = upload_dir / filename
    
    try:
        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(content)
        
        return {
            "success": True,
            "filePath": str(file_path),
            "filename": file.filename,
            "contentType": file.content_type,
            "size": len(content)
        }
        
    except Exception as e:
        logger.error(f"File upload error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to save uploaded file"
        )

class CreateCheckTestRequest(BaseModel):
    """Test-only request model that accepts a URL without authentication"""
    url: str
    mode: str = "quick"  # quick or deep

@router.post("/test", status_code=201)
async def create_check_test(
    request: CreateCheckTestRequest,
    session: AsyncSession = Depends(get_session)
):
    """TEST-ONLY ENDPOINT: Create a fact-check without authentication (DEBUG mode only)"""
    if not settings.DEBUG:
        raise HTTPException(
            status_code=404,
            detail="Test endpoint only available in DEBUG mode"
        )

    # Create or get test user
    test_user_id = "test-user-consistency"
    stmt = select(User).where(User.id == test_user_id)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        user = User(
            id=test_user_id,
            email="test@consistency.local",
            name="Consistency Test User",
            credits=1000000  # Unlimited credits for testing
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

    # Create check request in the same format as the main endpoint
    check_request = CreateCheckRequest(
        input_type="url",
        url=request.url,
        content=None,
        file_path=None,
        user_query=None
    )

    # Validate and normalize URL
    if not check_request.url:
        raise HTTPException(status_code=400, detail="URL is required")

    if not check_request.url.startswith(("http://", "https://")):
        check_request.url = f"https://{check_request.url}"
        logger.info(f"Normalized URL to: {check_request.url}")

    check_request.url = check_request.url.strip()

    # Create check record
    check = Check(
        id=str(uuid.uuid4()),
        user_id=user.id,
        input_type="url",
        input_content=json.dumps({
            "content": None,
            "url": check_request.url,
            "file_path": None
        }),
        input_url=check_request.url,
        status="pending",
        credits_used=0,  # Don't charge for test checks
        user_query=None
    )

    session.add(check)
    await session.commit()
    await session.refresh(check)

    # Start pipeline processing
    try:
        logger.info(f"[TEST] Dispatching task for check {check.id}")

        task = process_check.delay(
            check_id=check.id,
            user_id=user.id,
            input_data={
                "input_type": "url",
                "content": None,
                "url": check_request.url,
                "file_path": None,
                "user_query": None
            }
        )
        logger.info(f"[TEST] Task dispatched: {task.id}")

        # Store task ID mapping
        r = redis.Redis.from_url(settings.REDIS_URL)
        r.set(f"check-task:{check.id}", task.id, ex=300)

    except Exception as e:
        logger.error(f"[TEST] Failed to dispatch task: {e}")
        check.status = "failed"
        check.error_message = f"Task dispatch failed: {str(e)}"
        session.add(check)
        await session.commit()
        raise HTTPException(status_code=500, detail="Failed to start fact-checking pipeline")

    return {
        "check_id": check.id,
        "status": check.status,
        "task_id": task.id
    }

@router.get("/test/{check_id}")
async def get_check_test(
    check_id: str,
    session: AsyncSession = Depends(get_session)
):
    """TEST-ONLY ENDPOINT: Get check status without authentication (DEBUG mode only)"""
    if not settings.DEBUG:
        raise HTTPException(
            status_code=404,
            detail="Test endpoint only available in DEBUG mode"
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
                supported = sum(1 for c in claims if c.verdict == "supported")
                contradicted = sum(1 for c in claims if c.verdict == "contradicted")
                uncertain = sum(1 for c in claims if c.verdict == "uncertain")
                insufficient = sum(1 for c in claims if c.verdict == "insufficient_evidence")

                # Calculate overall score
                if total_claims > 0:
                    overall_score = int((supported / total_claims) * 100)
                else:
                    overall_score = 0

                response.update({
                    "overall_score": overall_score,
                    "claims_analyzed": total_claims,
                    "claims_supported": supported,
                    "claims_contradicted": contradicted,
                    "claims_uncertain": uncertain,
                    "claims_insufficient": insufficient,
                })
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

@router.post("", status_code=201)
@router.post("/", status_code=201)
async def create_check(
    request: CreateCheckRequest,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Create a new fact-check request"""
    # Get or create user (handles race conditions)
    user = await get_or_create_user(session, current_user)

    # MONTHLY USAGE LIMIT CHECK (applies in all modes, including DEBUG)
    # Get subscription to determine monthly limit (Subscription already imported at top)
    sub_stmt = select(Subscription).where(
        Subscription.user_id == user.id,
        Subscription.status.in_(["active", "trialing"])
    )
    sub_result = await session.execute(sub_stmt)
    subscription = sub_result.scalar_one_or_none()

    # Determine billing period and monthly limit
    if subscription and subscription.current_period_start:
        period_start = subscription.current_period_start
        credits_per_month = subscription.credits_per_month
    else:
        # Free user: use start of current calendar month
        from datetime import datetime
        now = datetime.utcnow()
        period_start = datetime(now.year, now.month, 1)
        credits_per_month = 3  # Free tier limit

    # Calculate monthly usage
    from sqlalchemy import func
    usage_stmt = select(func.coalesce(func.sum(Check.credits_used), 0)).where(
        Check.user_id == user.id,
        Check.created_at >= period_start
    )
    usage_result = await session.execute(usage_stmt)
    monthly_usage = usage_result.scalar() or 0

    # Check if user has exceeded their monthly limit
    if monthly_usage >= credits_per_month:
        raise HTTPException(
            status_code=402,
            detail=f"Monthly limit reached ({monthly_usage}/{credits_per_month} checks used). Please upgrade your plan for more checks."
        )
    
    # Validate input
    if request.input_type not in ["url", "text", "image", "video"]:
        raise HTTPException(status_code=400, detail="Invalid input type")

    if request.input_type == "url" and not request.url:
        raise HTTPException(status_code=400, detail="URL is required for url input type")

    # Normalize URL (add https:// if missing protocol)
    if request.input_type in ["url", "video"] and request.url:
        if not request.url.startswith(("http://", "https://")):
            request.url = f"https://{request.url}"
            logger.info(f"Normalized URL to: {request.url}")

    if request.input_type == "text" and not request.content:
        raise HTTPException(status_code=400, detail="Content is required for text input type")

    if request.input_type == "image" and not request.file_path:
        raise HTTPException(status_code=400, detail="File path is required for image input type")

    if request.input_type == "video" and not request.url:
        raise HTTPException(status_code=400, detail="URL is required for video input type")

    # Sanitize inputs (trim whitespace)
    if request.url:
        request.url = request.url.strip()
    if request.content:
        request.content = request.content.strip()

    # Search Clarity validation
    if request.user_query:
        # Check feature flag
        if not settings.ENABLE_SEARCH_CLARITY:
            raise HTTPException(
                status_code=503,
                detail="Search Clarity feature is temporarily disabled"
            )

        # Validate query length
        if len(request.user_query) > 200:
            raise HTTPException(
                status_code=400,
                detail="Query must be 200 characters or less"
            )

        # Sanitize query (prevent prompt injection)
        request.user_query = request.user_query.strip()

    # Create check record
    check = Check(
        id=str(uuid.uuid4()),
        user_id=user.id,
        input_type=request.input_type,
        input_content=json.dumps({
            "content": request.content,
            "url": request.url,
            "file_path": request.file_path
        }),
        input_url=request.url,
        status="pending",
        credits_used=1,
        user_query=request.user_query  # Search Clarity feature
    )
    
    session.add(check)

    # Reserve credits and track usage
    user.credits -= 1
    user.total_credits_used += 1
    await session.commit()
    await session.refresh(check)
    
    # Start pipeline processing
    try:
        logger.info(f"Attempting to dispatch task for check {check.id}")
        logger.info(f"Redis URL: {settings.REDIS_URL}")

        # Test Redis connection first
        import redis
        try:
            r = redis.Redis.from_url(settings.REDIS_URL)
            r.ping()
            logger.info("Redis connection successful")
        except Exception as redis_error:
            logger.error(f"Redis connection failed: {redis_error}")
            raise redis_error

        task = process_check.delay(
            check_id=check.id,
            user_id=user.id,
            input_data={
                "input_type": request.input_type,
                "content": request.content,
                "url": request.url,
                "file_path": request.file_path,
                "user_query": request.user_query  # Search Clarity feature
            }
        )
        logger.info(f"Task dispatched successfully: {task.id} for check {check.id}")
        logger.info(f"Task state immediately after dispatch: {task.state}")

        # Store task ID mapping in Redis for progress tracking
        r.set(f"check-task:{check.id}", task.id, ex=300)  # Expire after 5 minutes
        logger.info(f"Stored task mapping check-task:{check.id} -> {task.id}")

        # Verify task is in Redis queue
        queue_length = r.llen("celery")
        logger.info(f"Queue length after dispatch: {queue_length}")

    except Exception as e:
        import traceback
        logger.error(f"Failed to dispatch task for check {check.id}: {e}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
        # Update check status to failed
        check.status = "failed"
        check.error_message = f"Task dispatch failed: {str(e)}"
        session.add(check)
        await session.commit()
        raise HTTPException(status_code=500, detail="Failed to start fact-checking pipeline")
    
    return {
        "check": {
            "id": check.id,
            "status": check.status,
            "inputType": check.input_type,
            "createdAt": check.created_at.isoformat(),
            "creditsUsed": check.credits_used,
        },
        "remainingCredits": user.credits,
        "taskId": task.id
    }

@router.get("")
@router.get("/")
async def get_checks(
    skip: int = 0,
    limit: int = 20,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
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
        claims_count_stmt = select(func.count(Claim.id)).where(Claim.check_id == check.id)
        claims_count_result = await session.execute(claims_count_stmt)
        claims_count = claims_count_result.scalar() or 0

        # Build claims array with first claim details
        claims_array = []
        if first_claim:
            claims_array.append({
                "id": first_claim.id,
                "text": first_claim.text,
                "verdict": first_claim.verdict,
                "confidence": first_claim.confidence,
                "position": first_claim.position,
            })

        check_data.append({
            "id": check.id,
            "inputType": check.input_type,
            "inputUrl": check.input_url,
            "status": check.status,
            "creditsUsed": check.credits_used,
            "processingTimeMs": check.processing_time_ms,
            "createdAt": check.created_at.isoformat(),
            "completedAt": check.completed_at.isoformat() if check.completed_at else None,
            "claimsCount": claims_count,
            "claims": claims_array,  # First claim for preview
            # Synopsis fields for dashboard cards
            "overallSummary": check.overall_summary,
            "credibilityScore": check.credibility_score,
            "claimsSupported": check.claims_supported or 0,
            "claimsContradicted": check.claims_contradicted or 0,
            "claimsUncertain": check.claims_uncertain or 0,
            "articleDomain": check.article_domain,
        })

    return {
        "checks": check_data,
        "total": len(checks)
    }

@router.get("/{check_id}")
async def get_check(
    check_id: str,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Get a specific check with all claims and evidence"""
    stmt = select(Check).where(
        Check.id == check_id,
        Check.user_id == current_user["id"]
    )
    result = await session.execute(stmt)
    check = result.scalar_one_or_none()
    
    if not check:
        raise HTTPException(status_code=404, detail="Check not found")
    
    # Get claims with evidence
    claims_stmt = (
        select(Claim)
        .where(Claim.check_id == check.id)
        .order_by(Claim.position)
    )
    claims_result = await session.execute(claims_stmt)
    claims = claims_result.scalars().all()
    
    claims_data = []
    for claim in claims:
        evidence_stmt = select(Evidence).where(Evidence.claim_id == claim.id)
        evidence_result = await session.execute(evidence_stmt)
        evidence = evidence_result.scalars().all()
        
        claims_data.append({
            "id": claim.id,
            "text": claim.text,
            "verdict": claim.verdict,
            "confidence": claim.confidence,
            "rationale": claim.rationale,
            "position": claim.position,
            # Context preservation fields (Context Improvement - Phase 5)
            "subjectContext": claim.subject_context,
            "keyEntities": json.loads(claim.key_entities) if claim.key_entities else [],
            "sourceTitle": claim.source_title,
            "sourceUrl": claim.source_url,
            "evidence": [
                {
                    "id": ev.id,
                    "source": ev.source,
                    "url": ev.url,
                    "title": ev.title,
                    "snippet": ev.snippet,
                    "publishedDate": ev.published_date.isoformat() if ev.published_date else None,
                    "relevanceScore": ev.relevance_score,
                    "credibilityScore": ev.credibility_score,
                    # Source type fields
                    "isFactcheck": ev.is_factcheck,
                    "externalSourceProvider": ev.external_source_provider,
                    "sourceType": ev.source_type,
                }
                for ev in evidence
            ]
        })
    
    return {
        "id": check.id,
        "inputType": check.input_type,
        "inputContent": json.loads(check.input_content),
        "inputUrl": check.input_url,
        "status": check.status,
        "creditsUsed": check.credits_used,
        "processingTimeMs": check.processing_time_ms,
        "errorMessage": check.error_message,
        "overallSummary": check.overall_summary,
        "credibilityScore": check.credibility_score,
        "claimsSupported": check.claims_supported,
        "claimsContradicted": check.claims_contradicted,
        "claimsUncertain": check.claims_uncertain,
        # Search Clarity fields
        "userQuery": check.user_query,
        "queryResponse": check.query_response,
        "queryConfidence": check.query_confidence,
        "querySources": check.query_sources.get("sources", []) if check.query_sources else None,
        "queryRelatedClaims": check.query_sources.get("related_claims", []) if check.query_sources else None,
        "claims": claims_data,
        "createdAt": check.created_at.isoformat(),
        "completedAt": check.completed_at.isoformat() if check.completed_at else None,
    }

@router.get("/{check_id}/progress")
async def stream_check_progress(
    check_id: str,
    current_user: dict = Depends(get_current_user_sse),
    session: AsyncSession = Depends(get_session)
):
    """Stream real-time progress updates via SSE"""
    
    # Verify check belongs to user
    stmt = select(Check).where(
        Check.id == check_id,
        Check.user_id == current_user["id"]
    )
    result = await session.execute(stmt)
    check = result.scalar_one_or_none()
    
    if not check:
        raise HTTPException(status_code=404, detail="Check not found")
    
    def event_stream():
        """Generate SSE events for pipeline progress"""
        import time
        redis_client = None
        try:
            # Connect to Redis for Celery task updates
            redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
            
            # Initial connection event
            yield f"data: {safe_json_dumps({'type': 'connected', 'checkId': check_id, 'timestamp': datetime.now(timezone.utc).isoformat()})}\n\n"
            
            # Check if task is already completed
            if check.status == "completed":
                yield f"data: {json.dumps({'type': 'completed', 'checkId': check_id, 'status': 'completed', 'progress': 100})}\n\n"
                return
            elif check.status == "failed":
                yield f"data: {safe_json_dumps({'type': 'error', 'checkId': check_id, 'status': 'failed', 'error': check.error_message})}\n\n"
                return
            
            # Monitor task progress
            task_key_pattern = f"celery-task-meta-*"
            last_progress = 0
            timeout_counter = 0
            max_timeout = 200  # 3+ minutes timeout (longer than task timeout)
            
            while timeout_counter < max_timeout:
                try:
                    # Get task ID from Redis mapping
                    task_id = redis_client.get(f"check-task:{check_id}")

                    if not task_id:
                        # Fallback: Find task ID by scanning Redis keys
                        keys = redis_client.keys(task_key_pattern)
                        for key in keys:
                            try:
                                task_data = redis_client.get(key)
                                if task_data:
                                    task_info = json.loads(task_data)
                                    # Check if this task relates to our check
                                    if isinstance(task_info, dict) and 'kwargs' in task_info:
                                        kwargs = task_info.get('kwargs', {})
                                        if kwargs.get('check_id') == check_id:
                                            task_id = key.replace("celery-task-meta-", "")
                                            break
                            except (json.JSONDecodeError, Exception):
                                continue
                    
                    if task_id:
                        # Get task result
                        task = celery_app.AsyncResult(task_id)
                        
                        if task.state == "PENDING":
                            if last_progress == 0:
                                yield f"data: {json.dumps({'type': 'progress', 'checkId': check_id, 'stage': 'queued', 'progress': 0, 'message': 'Check queued for processing'})}\n\n"
                                last_progress = 0
                        
                        elif task.state == "PROGRESS":
                            info = task.info or {}
                            stage = info.get('stage', 'processing')
                            progress = info.get('progress', 0)
                            
                            if progress > last_progress:
                                stage_messages = {
                                    'ingest': 'Processing input content...',
                                    'extract': 'Extracting factual claims...',
                                    'retrieve': 'Gathering evidence from sources...',
                                    'verify': 'Verifying claims against evidence...',
                                    'judge': 'Generating final verdicts...',
                                    'summary': 'Creating overall credibility assessment...'
                                }
                                
                                message = stage_messages.get(stage, f'Processing {stage}...')
                                
                                yield f"data: {json.dumps({'type': 'progress', 'checkId': check_id, 'stage': stage, 'progress': progress, 'message': message})}\n\n"
                                last_progress = progress
                        
                        elif task.state == "SUCCESS":
                            yield f"data: {json.dumps({'type': 'completed', 'checkId': check_id, 'status': 'completed', 'progress': 100, 'message': 'Fact-check completed successfully'})}\n\n"
                            break
                        
                        elif task.state == "FAILURE":
                            error_message = str(task.info) if task.info else "Processing failed"
                            yield f"data: {safe_json_dumps({'type': 'error', 'checkId': check_id, 'status': 'failed', 'error': error_message})}\n\n"
                            break
                    
                    # Skip database status check - rely on Celery task status
                    # Database updates are handled by the pipeline itself
                    
                    # Send heartbeat
                    if timeout_counter % 10 == 0:  # Every 10 seconds
                        yield f"data: {safe_json_dumps({'type': 'heartbeat', 'timestamp': datetime.now(timezone.utc).isoformat()})}\n\n"
                    
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
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Cache-Control"
        }
    )

@router.get("/{check_id}/export/pdf")
async def export_check_pdf(
    check_id: str,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Export fact-check as PDF report"""

    # Fetch check with user verification
    stmt = select(Check).where(
        Check.id == check_id,
        Check.user_id == current_user["id"]
    )
    result = await session.execute(stmt)
    check = result.scalar_one_or_none()

    if not check:
        raise HTTPException(status_code=404, detail="Check not found")

    if check.status != "completed":
        raise HTTPException(
            status_code=400,
            detail="PDF export only available for completed checks"
        )

    # Fetch claims ordered by position
    claims_stmt = (
        select(Claim)
        .where(Claim.check_id == check_id)
        .order_by(Claim.position)
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

        claims_with_evidence.append({
            "text": claim.text,
            "verdict": claim.verdict,
            "confidence": claim.confidence,
            "rationale": claim.rationale,
            "evidence": evidence_list
        })

    # Render HTML template
    try:
        template = jinja_env.get_template("pdf/fact_check_report.html")
        html_content = template.render(
            check=check,
            claims=claims_with_evidence,
            now=datetime.utcnow()
        )
    except Exception as e:
        logger.error(f"Template rendering failed: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to generate PDF template"
        )

    # Generate PDF with xhtml2pdf
    try:
        pdf_buffer = BytesIO()
        pisa_status = pisa.CreatePDF(
            html_content,
            dest=pdf_buffer,
            encoding='utf-8'
        )

        if pisa_status.err:
            raise Exception(f"PDF generation error: {pisa_status.err}")

        pdf_bytes = pdf_buffer.getvalue()
        pdf_buffer.close()
    except Exception as e:
        logger.error(f"PDF generation failed: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to generate PDF. Please try again."
        )

    # Return PDF as downloadable file
    filename = f"tru8-factcheck-{check_id[:8]}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
            "Cache-Control": "no-cache"
        }
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
    sort_by: str = "relevance",  # relevance, credibility, date
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Get all sources reviewed for a check (Pro feature).

    This endpoint returns all sources that were reviewed during fact-checking,
    including those that were filtered out. It shows which filtering stage
    excluded each source and why.

    Query params:
    - include_filtered: Include filtered sources (default: true)
    - sort_by: Sort order - relevance, credibility, or date
    """

    # 1. Verify check belongs to user
    stmt = select(Check).where(
        Check.id == check_id,
        Check.user_id == current_user["id"]
    )
    result = await session.execute(stmt)
    check = result.scalar_one_or_none()

    if not check:
        raise HTTPException(status_code=404, detail="Check not found")

    # 2. Check Pro subscription (include trialing users per project pattern)
    sub_stmt = select(Subscription).where(
        Subscription.user_id == current_user["id"],
        Subscription.status.in_(["active", "trialing"])
    )
    sub_result = await session.execute(sub_stmt)
    subscription = sub_result.scalar_one_or_none()

    is_pro = subscription and subscription.plan == "pro"

    if not is_pro:
        # Return limited response for non-Pro users
        return {
            "checkId": check_id,
            "totalSources": check.raw_sources_count or 0,
            "includedCount": 0,
            "filteredCount": 0,
            "legacyCheck": check.raw_sources_count is None or check.raw_sources_count == 0,
            "message": "Upgrade to Pro to see all sources reviewed during fact-checking",
            "claims": None,
            "filterBreakdown": None,
            "requiresUpgrade": True
        }

    # 3. Query RawEvidence for this check
    raw_stmt = select(RawEvidence).where(RawEvidence.check_id == check_id)

    if not include_filtered:
        raw_stmt = raw_stmt.where(RawEvidence.is_included == True)

    # Apply sorting
    if sort_by == "credibility":
        raw_stmt = raw_stmt.order_by(desc(RawEvidence.credibility_score))
    elif sort_by == "date":
        raw_stmt = raw_stmt.order_by(desc(RawEvidence.published_date))
    else:  # relevance (default)
        raw_stmt = raw_stmt.order_by(desc(RawEvidence.relevance_score))

    raw_result = await session.execute(raw_stmt)
    raw_evidence = raw_result.scalars().all()

    # Check for legacy check (no raw evidence stored)
    if not raw_evidence and (check.raw_sources_count is None or check.raw_sources_count == 0):
        return {
            "checkId": check_id,
            "totalSources": 0,
            "includedCount": 0,
            "filteredCount": 0,
            "legacyCheck": True,
            "message": "Source data not available for checks created before this feature.",
            "claims": None,
            "filterBreakdown": None
        }

    # 4. Group sources by claim
    claims_dict = {}
    filter_breakdown = {
        "credibility": 0,
        "temporal": 0,
        "dedup": 0,
        "diversity": 0,
        "domain_cap": 0,
        "validation": 0,
        "extraction_failed": 0
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
                "sources": []
            }

        source_data = {
            "id": raw_ev.id,
            "source": raw_ev.source,
            "title": raw_ev.title,
            "url": raw_ev.url,
            "publishedDate": raw_ev.published_date.isoformat() if raw_ev.published_date else None,
            "credibilityScore": raw_ev.credibility_score,
            "relevanceScore": raw_ev.relevance_score,
            "isIncluded": raw_ev.is_included,
            "filterStage": raw_ev.filter_stage,
            "filterReason": raw_ev.filter_reason,
            "tier": raw_ev.tier,
            "isFactcheck": raw_ev.is_factcheck,
            "externalSourceProvider": raw_ev.external_source_provider
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
        "filterBreakdown": filter_breakdown
    }


@router.get("/{check_id}/sources/export")
async def export_check_sources(
    check_id: str,
    format: str = "csv",  # csv, bibtex, apa
    include_filtered: bool = False,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
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
        Check.id == check_id,
        Check.user_id == current_user["id"]
    )
    result = await session.execute(stmt)
    check = result.scalar_one_or_none()

    if not check:
        raise HTTPException(status_code=404, detail="Check not found")

    # 2. Check Pro subscription (include trialing users per project pattern)
    sub_stmt = select(Subscription).where(
        Subscription.user_id == current_user["id"],
        Subscription.status.in_(["active", "trialing"])
    )
    sub_result = await session.execute(sub_stmt)
    subscription = sub_result.scalar_one_or_none()

    is_pro = subscription and subscription.plan == "pro"

    if not is_pro:
        raise HTTPException(
            status_code=403,
            detail="Source export is a Pro feature. Upgrade to access."
        )

    # 3. Query RawEvidence
    raw_stmt = select(RawEvidence).where(RawEvidence.check_id == check_id)

    if not include_filtered:
        raw_stmt = raw_stmt.where(RawEvidence.is_included == True)

    raw_stmt = raw_stmt.order_by(RawEvidence.claim_position, desc(RawEvidence.relevance_score))

    raw_result = await session.execute(raw_stmt)
    raw_evidence = raw_result.scalars().all()

    if not raw_evidence:
        raise HTTPException(
            status_code=404,
            detail="No sources available for export"
        )

    # 4. Generate export based on format
    # NOTE: We intentionally exclude internal scoring metrics (credibility_score,
    # relevance_score, filter_stage, filter_reason, tier) from exports to avoid
    # potential legal issues with publicly rating news sources.
    if format == "csv":
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "Claim", "Source", "Title", "URL", "Published Date", "Used in Analysis"
        ])

        for ev in raw_evidence:
            writer.writerow([
                ev.claim_text or "",
                ev.source,
                ev.title,
                ev.url,
                ev.published_date.strftime("%Y-%m-%d") if ev.published_date else "",
                "Yes" if ev.is_included else "No"
            ])

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
            pub_date = ev.published_date.strftime("%Y, %B %d") if ev.published_date else "n.d."
            entry = f"{ev.source}. ({pub_date}). {ev.title}. Retrieved from {ev.url}"
            lines.append(entry)

        content = "\n\n".join(lines)
        media_type = "text/plain"
        filename = f"tru8-sources-{check_id[:8]}-apa.txt"

    else:
        raise HTTPException(
            status_code=400,
            detail="Invalid format. Supported: csv, bibtex, apa"
        )

    return Response(
        content=content,
        media_type=media_type,
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
            "Cache-Control": "no-cache"
        }
    )