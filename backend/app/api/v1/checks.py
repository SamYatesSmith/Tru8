from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func
from pydantic import BaseModel
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
import redis.asyncio as redis
from app.core.config import settings
import os
import aiofiles
from pathlib import Path

logger = logging.getLogger(__name__)

router = APIRouter()

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

@router.post("/")
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
    
    # Get claims count for each check with explicit async query
    check_data = []
    for check in checks:
        # Count claims for this check
        claims_count_stmt = select(func.count(Claim.id)).where(Claim.check_id == check.id)
        claims_count_result = await session.execute(claims_count_stmt)
        claims_count = claims_count_result.scalar() or 0
        
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
            "evidence": [
                {
                    "id": ev.id,
                    "source": ev.source,
                    "url": ev.url,
                    "title": ev.title,
                    "snippet": ev.snippet,
                    "publishedDate": ev.published_date.isoformat() if ev.published_date else None,
                    "relevanceScore": ev.relevance_score,
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
    
    async def event_stream():
        """Generate SSE events for pipeline progress"""
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
                    # Get task status from Celery
                    task_id = None
                    
                    # Find task ID by scanning Redis keys (fallback method)
                    keys = await redis_client.keys(task_key_pattern)
                    for key in keys:
                        try:
                            task_data = await redis_client.get(key)
                            if task_data:
                                task_info = json.loads(task_data)
                                # Check if this task relates to our check
                                if isinstance(task_info, dict) and 'args' in str(task_info):
                                    if check_id in str(task_info):
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
                                    'judge': 'Generating final verdicts...'
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
                    
                    # Check database for status updates
                    try:
                        from app.core.database import async_session
                        async with async_session() as db_session:
                            stmt = select(Check).where(Check.id == check_id)
                            result = await db_session.execute(stmt)
                            updated_check = result.scalar_one_or_none()
                            
                            if updated_check:
                                if updated_check.status == "completed":
                                    yield f"data: {json.dumps({'type': 'completed', 'checkId': check_id, 'status': 'completed', 'progress': 100, 'message': 'Fact-check completed successfully'})}\n\n"
                                    break
                                elif updated_check.status == "failed":
                                    yield f"data: {json.dumps({'type': 'error', 'checkId': check_id, 'status': 'failed', 'error': updated_check.error_message or 'Processing failed'})}\n\n"
                                    break
                                elif updated_check.status == "processing":
                                    # Update local check status to track progress
                                    check.status = "processing"
                    except Exception as db_error:
                        logger.warning(f"Database check failed in SSE: {db_error}")
                    
                    # Send heartbeat
                    if timeout_counter % 10 == 0:  # Every 10 seconds
                        yield f"data: {safe_json_dumps({'type': 'heartbeat', 'timestamp': datetime.now(timezone.utc).isoformat()})}\n\n"
                    
                    await asyncio.sleep(1)
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
                await redis_client.aclose()
    
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