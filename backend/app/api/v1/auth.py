from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_session
from app.core.auth import get_current_user
from app.models import User

router = APIRouter()

@router.get("/me")
async def get_me(
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Get current user profile with credits"""
    # Try to find existing user
    stmt = select(User).where(User.id == current_user["id"])
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()
    
    # Create user if doesn't exist (first login)
    if not user:
        user = User(
            id=current_user["id"],
            email=current_user["email"],
            name=current_user.get("name"),
            credits=3  # Free tier
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
    
    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "credits": user.credits,
        "totalCreditsUsed": user.total_credits_used,
        "hasSubscription": user.subscription is not None,
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