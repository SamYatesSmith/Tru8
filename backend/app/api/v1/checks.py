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
from app.models import User, Check, Claim, Evidence
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

@router.post("", status_code=201)
@router.post("/", status_code=201)
async def create_check(
    request: CreateCheckRequest,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Create a new fact-check request"""
    # Get user and check credits
    stmt = select(User).where(User.id == current_user["id"])
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Skip credit check in development mode
    if not settings.DEBUG and user.credits < 1:
        raise HTTPException(
            status_code=402,
            detail="Insufficient credits. Please upgrade your plan."
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
        credits_used=1
    )
    
    session.add(check)
    
    # Reserve credits
    user.credits -= 1
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
                "file_path": request.file_path
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