from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.core.database import get_session
from app.core.auth import get_current_user
from app.models import User, Check
from app.services.push_notifications import push_notification_service

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
    
    # Create user if doesn't exist (first login)
    if not user:
        # Ensure we have required user data
        email = current_user.get("email")
        if not email:
            raise HTTPException(
                status_code=500, 
                detail="Unable to retrieve user email from authentication provider"
            )
        
        user = User(
            id=current_user["id"],
            email=email,
            name=current_user.get("name"),
            credits=3  # Free tier
        )
        session.add(user)
        try:
            await session.commit()
            await session.refresh(user)
        except Exception as e:
            await session.rollback()
            raise HTTPException(status_code=500, detail=f"Failed to create user: {str(e)}")
    
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
            "plan": "free",
            "status": "active", 
            "creditsPerMonth": 3,
            "currentPeriodEnd": None,
        },
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
    
    # Create user if doesn't exist (first login)
    if not user:
        # Ensure we have required user data
        email = current_user.get("email")
        if not email:
            raise HTTPException(
                status_code=500, 
                detail="Unable to retrieve user email from authentication provider"
            )
        
        user = User(
            id=current_user["id"],
            email=email,
            name=current_user.get("name"),
            credits=3  # Free tier
        )
        session.add(user)
        try:
            await session.commit()
            await session.refresh(user)
        except Exception as e:
            await session.rollback()
            raise HTTPException(status_code=500, detail=f"Failed to create user: {str(e)}")
    
    return {
        "creditsRemaining": user.credits,
        "totalCreditsUsed": user.total_credits_used,
        "subscription": {
            "plan": "free",
            "creditsPerMonth": 3,
            "resetDate": None,
        }
    }


# Pydantic models for push notifications
class PushTokenRequest(BaseModel):
    push_token: str
    platform: str  # 'ios' or 'android'
    device_id: str


class NotificationPreferencesRequest(BaseModel):
    notifications: bool


@router.post("/push-token")
async def register_push_token(
    request: PushTokenRequest,
    current_user: dict = Depends(get_current_user),
):
    """Register a push token for the current user"""
    success = await push_notification_service.register_push_token(
        user_id=current_user["id"],
        push_token=request.push_token,
        platform=request.platform,
        device_id=request.device_id
    )
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to register push token")
    
    return {"success": True, "message": "Push token registered successfully"}


@router.delete("/push-token")
async def unregister_push_token(
    current_user: dict = Depends(get_current_user),
):
    """Unregister push token for the current user"""
    success = await push_notification_service.unregister_push_token(
        user_id=current_user["id"]
    )
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to unregister push token")
    
    return {"success": True, "message": "Push token unregistered successfully"}


@router.put("/notification-preferences")
async def update_notification_preferences(
    request: NotificationPreferencesRequest,
    current_user: dict = Depends(get_current_user),
):
    """Update user's push notification preferences"""
    success = await push_notification_service.update_notification_preferences(
        user_id=current_user["id"],
        enabled=request.notifications
    )
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update notification preferences")
    
    return {"success": True, "message": "Notification preferences updated successfully"}


@router.get("/notification-preferences")
async def get_notification_preferences(
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Get user's push notification preferences"""
    stmt = select(User).where(User.id == current_user["id"])
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {
        "notifications": user.push_notifications_enabled,
        "hasPushToken": bool(user.push_token),
        "platform": user.platform
    }