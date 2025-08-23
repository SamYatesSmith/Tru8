from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from pydantic import BaseModel
from app.core.database import get_session
from app.core.auth import get_current_user
from app.models import User, Check, Claim, Evidence
from app.workers.pipeline import process_check
from datetime import datetime
import uuid
import json

router = APIRouter()

class CreateCheckRequest(BaseModel):
    input_type: str  # 'url', 'text', 'image', 'video'
    content: Optional[str] = None
    url: Optional[str] = None

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
    
    if user.credits < 1:
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
    
    # Create check record
    check = Check(
        id=str(uuid.uuid4()),
        user_id=user.id,
        input_type=request.input_type,
        input_content=json.dumps({
            "content": request.content,
            "url": request.url
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
    task = process_check.delay(
        check_id=check.id,
        user_id=user.id,
        input_data={
            "input_type": request.input_type,
            "content": request.content,
            "url": request.url
        }
    )
    
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
    
    return {
        "checks": [
            {
                "id": check.id,
                "inputType": check.input_type,
                "inputUrl": check.input_url,
                "status": check.status,
                "creditsUsed": check.credits_used,
                "processingTimeMs": check.processing_time_ms,
                "createdAt": check.created_at.isoformat(),
                "completedAt": check.completed_at.isoformat() if check.completed_at else None,
                "claimsCount": len(check.claims),
            }
            for check in checks
        ],
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
async def get_check_progress(check_id: str):
    """Get real-time progress of a check (SSE endpoint placeholder)"""
    # TODO: Implement SSE for real-time updates
    return {
        "checkId": check_id,
        "stage": "processing",
        "progress": 50,
        "message": "Extracting claims..."
    }