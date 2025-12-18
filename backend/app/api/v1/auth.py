from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_session
from app.core.auth import get_current_user
from app.models import User, Subscription
from app.api.v1.users import get_or_create_user

router = APIRouter()

@router.get("/me")
async def get_me(
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Get current user profile with credits"""
    user = await get_or_create_user(session, current_user)
    
    # Check for active subscription
    sub_stmt = select(Subscription).where(
        Subscription.user_id == user.id,
        Subscription.status == "active"
    )
    sub_result = await session.execute(sub_stmt)
    has_subscription = sub_result.scalar_one_or_none() is not None
    
    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "credits": user.credits,
        "totalCreditsUsed": user.total_credits_used,
        "hasSubscription": has_subscription,
        "createdAt": user.created_at.isoformat(),
    }

@router.post("/refresh")
async def refresh_token(current_user: dict = Depends(get_current_user)):
    """Validate and return user info (token refresh)"""
    return {
        "valid": True,
        "userId": current_user["id"],
        "email": current_user["email"]
    }