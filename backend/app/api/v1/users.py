from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.core.database import get_session
from app.core.auth import get_current_user
from app.models import User, Check

router = APIRouter()

@router.get("/profile")
async def get_profile(
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Get user profile with usage stats"""
    stmt = select(User).where(User.id == current_user["id"])
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get check stats
    checks_stmt = select(Check).where(Check.user_id == user.id)
    checks_result = await session.execute(checks_stmt)
    checks = checks_result.scalars().all()
    
    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "credits": user.credits,
        "totalCreditsUsed": user.total_credits_used,
        "subscription": {
            "plan": user.subscription.plan if user.subscription else None,
            "status": user.subscription.status if user.subscription else None,
            "creditsPerMonth": user.subscription.credits_per_month if user.subscription else 0,
            "currentPeriodEnd": user.subscription.current_period_end.isoformat() if user.subscription else None,
        } if user.subscription else None,
        "stats": {
            "totalChecks": len(checks),
            "completedChecks": len([c for c in checks if c.status == "completed"]),
            "failedChecks": len([c for c in checks if c.status == "failed"]),
        },
        "createdAt": user.created_at.isoformat(),
    }

@router.get("/usage")
async def get_usage(
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Get detailed usage statistics"""
    stmt = select(User).where(User.id == current_user["id"])
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {
        "creditsRemaining": user.credits,
        "totalCreditsUsed": user.total_credits_used,
        "subscription": {
            "plan": user.subscription.plan if user.subscription else "free",
            "creditsPerMonth": user.subscription.credits_per_month if user.subscription else 3,
            "resetDate": user.subscription.current_period_end.isoformat() if user.subscription else None,
        }
    }