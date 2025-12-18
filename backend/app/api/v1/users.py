from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, delete, func, text
from sqlalchemy.dialects.postgresql import insert
from datetime import datetime
from app.core.database import get_session
from app.core.auth import get_current_user
from app.core.config import settings
from app.models import User, Check, Subscription, Claim, Evidence
from app.services.push_notifications import push_notification_service
import stripe
import logging

# Configure Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY
logger = logging.getLogger(__name__)

router = APIRouter()


async def get_or_create_user(session: AsyncSession, current_user: dict) -> User:
    """
    Get existing user or create new one with race-condition protection.
    Uses PostgreSQL INSERT ON CONFLICT to handle concurrent requests safely.
    """
    user_id = current_user["id"]
    email = current_user.get("email")
    name = current_user.get("name")

    # First, try to get existing user by ID
    stmt = select(User).where(User.id == user_id)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if user:
        return user

    # User doesn't exist - need to create
    if not email:
        raise HTTPException(
            status_code=500,
            detail="Unable to retrieve user email from authentication provider"
        )

    # Use INSERT ON CONFLICT to handle race conditions
    # If email already exists (from old Clerk ID), update the ID to new one
    insert_stmt = insert(User).values(
        id=user_id,
        email=email,
        name=name,
        credits=3,  # Free tier
        total_credits_used=0,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    ).on_conflict_do_update(
        index_elements=['email'],  # Conflict on email unique constraint
        set_={
            'id': user_id,  # Update to new Clerk ID
            'name': name,
            'updated_at': datetime.utcnow()
        }
    ).returning(User)

    try:
        result = await session.execute(insert_stmt)
        user = result.scalar_one()
        await session.commit()
        logger.info(f"User created/updated: {email} (ID: {user_id})")
        return user
    except Exception as e:
        await session.rollback()
        logger.error(f"Failed to create/update user: {e}")
        # Try to fetch the user one more time (might have been created by another request)
        stmt = select(User).where(User.email == email)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        if user:
            return user
        raise HTTPException(status_code=500, detail=f"Failed to create user: {str(e)}")

@router.get("/profile")
async def get_profile(
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Get user profile with usage stats"""
    user = await get_or_create_user(session, current_user)
    
    # Get check stats
    checks_stmt = select(Check).where(Check.user_id == user.id)
    checks_result = await session.execute(checks_stmt)
    checks = checks_result.scalars().all()

    # Get subscription data
    sub_stmt = select(Subscription).where(
        Subscription.user_id == user.id,
        Subscription.status.in_(["active", "trialing"])
    )
    sub_result = await session.execute(sub_stmt)
    subscription = sub_result.scalar_one_or_none()

    # Build subscription response
    if subscription:
        subscription_data = {
            "plan": subscription.plan,
            "status": subscription.status,
            "creditsPerMonth": subscription.credits_per_month,
            "currentPeriodEnd": subscription.current_period_end.isoformat() if subscription.current_period_end else None,
        }
    else:
        # No active subscription = free tier
        subscription_data = {
            "plan": "free",
            "status": "active",
            "creditsPerMonth": 3,
            "currentPeriodEnd": None,
        }

    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "credits": user.credits,
        "totalCreditsUsed": user.total_credits_used,
        "subscription": subscription_data,
        "stats": {
            "totalChecks": len(checks),
            "completedChecks": len([c for c in checks if c.status == "completed"]),
            "failedChecks": len([c for c in checks if c.status == "failed"]),
        },
        "createdAt": user.created_at.isoformat(),
    }

class ProfileUpdateRequest(BaseModel):
    name: str | None = None


@router.patch("/profile")
async def update_profile(
    request: ProfileUpdateRequest,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Update user profile (name, etc.)"""
    stmt = select(User).where(User.id == current_user["id"])
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Update fields if provided
    if request.name is not None:
        user.name = request.name.strip() if request.name else None

    try:
        await session.commit()
        await session.refresh(user)
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update profile: {str(e)}")

    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "message": "Profile updated successfully"
    }


@router.get("/stats")
async def get_user_stats(
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Get aggregated user statistics for dashboard insights"""
    user = await get_or_create_user(session, current_user)
    user_id = user.id

    # Total completed checks
    total_checks_stmt = select(func.count(Check.id)).where(
        Check.user_id == user_id,
        Check.status == "completed"
    )
    total_checks_result = await session.execute(total_checks_stmt)
    total_checks = total_checks_result.scalar() or 0

    # Checks this month
    now = datetime.utcnow()
    start_of_month = datetime(now.year, now.month, 1)
    checks_this_month_stmt = select(func.count(Check.id)).where(
        Check.user_id == user_id,
        Check.status == "completed",
        Check.created_at >= start_of_month
    )
    checks_this_month_result = await session.execute(checks_this_month_stmt)
    checks_this_month = checks_this_month_result.scalar() or 0

    # Total sources analyzed (sum of raw_sources_count)
    sources_stmt = select(func.coalesce(func.sum(Check.raw_sources_count), 0)).where(
        Check.user_id == user_id,
        Check.status == "completed"
    )
    sources_result = await session.execute(sources_stmt)
    total_sources_analyzed = sources_result.scalar() or 0

    # Average confidence across all claims
    avg_confidence_stmt = select(func.avg(Claim.confidence)).join(Check).where(
        Check.user_id == user_id,
        Check.status == "completed"
    )
    avg_confidence_result = await session.execute(avg_confidence_stmt)
    avg_confidence = avg_confidence_result.scalar()
    average_confidence = round(float(avg_confidence), 1) if avg_confidence else 0.0

    # Verdict breakdown (count by verdict type)
    verdict_stmt = select(Claim.verdict, func.count(Claim.id)).join(Check).where(
        Check.user_id == user_id,
        Check.status == "completed"
    ).group_by(Claim.verdict)
    verdict_result = await session.execute(verdict_stmt)
    verdict_rows = verdict_result.all()

    verdict_breakdown = {"supported": 0, "contradicted": 0, "uncertain": 0}
    for verdict, count in verdict_rows:
        if verdict in verdict_breakdown:
            verdict_breakdown[verdict] = count
        elif verdict in ["insufficient_evidence", "conflicting_expert_opinion", "needs_primary_source", "outdated_claim", "lacks_context"]:
            # Group other verdicts under uncertain
            verdict_breakdown["uncertain"] += count

    # Domain breakdown (count by article_domain)
    domain_stmt = select(Check.article_domain, func.count(Check.id)).where(
        Check.user_id == user_id,
        Check.status == "completed",
        Check.article_domain.isnot(None)
    ).group_by(Check.article_domain)
    domain_result = await session.execute(domain_stmt)
    domain_rows = domain_result.all()

    domain_breakdown = {}
    for domain, count in domain_rows:
        if domain:  # Skip None values
            domain_breakdown[domain] = count

    # Calculate top domain
    top_domain = None
    if domain_breakdown:
        top_domain = max(domain_breakdown, key=domain_breakdown.get)

    # Calculate misinformation rate (% of claims that were contradicted)
    total_claims = sum(verdict_breakdown.values())
    misinformation_rate = 0.0
    if total_claims > 0:
        misinformation_rate = round((verdict_breakdown["contradicted"] / total_claims) * 100, 1)

    return {
        "totalChecks": total_checks,
        "checksThisMonth": checks_this_month,
        "totalSourcesAnalyzed": total_sources_analyzed,
        "averageConfidence": average_confidence,
        "verdictBreakdown": verdict_breakdown,
        "domainBreakdown": domain_breakdown,
        "topDomain": top_domain,
        "misinformationRate": misinformation_rate,
        "memberSince": user.created_at.isoformat() if user.created_at else None
    }


@router.get("/usage")
async def get_usage(
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Get detailed usage statistics"""
    user = await get_or_create_user(session, current_user)

    # Get subscription data
    sub_stmt = select(Subscription).where(
        Subscription.user_id == user.id,
        Subscription.status.in_(["active", "trialing"])
    )
    sub_result = await session.execute(sub_stmt)
    subscription = sub_result.scalar_one_or_none()

    # Determine billing period start for monthly usage calculation
    if subscription and subscription.current_period_start:
        # Subscriber: use subscription billing period
        period_start = subscription.current_period_start
        credits_per_month = subscription.credits_per_month
    else:
        # Free user: use start of current calendar month
        now = datetime.utcnow()
        period_start = datetime(now.year, now.month, 1)
        credits_per_month = 3

    # Calculate monthly usage by summing credits_used from checks in current period
    usage_stmt = select(func.coalesce(func.sum(Check.credits_used), 0)).where(
        Check.user_id == user.id,
        Check.created_at >= period_start
    )
    usage_result = await session.execute(usage_stmt)
    monthly_credits_used = usage_result.scalar() or 0

    # Build subscription response
    if subscription:
        subscription_data = {
            "plan": subscription.plan,
            "creditsPerMonth": subscription.credits_per_month,
            "resetDate": subscription.current_period_end.isoformat() if subscription.current_period_end else None,
            "periodStart": subscription.current_period_start.isoformat() if subscription.current_period_start else None,
        }
    else:
        # No active subscription = free tier
        subscription_data = {
            "plan": "free",
            "creditsPerMonth": 3,
            "resetDate": None,
            "periodStart": period_start.isoformat(),
        }

    return {
        "creditsRemaining": user.credits,
        "totalCreditsUsed": user.total_credits_used,
        "monthlyCreditsUsed": monthly_credits_used,
        "creditsPerMonth": credits_per_month,
        "subscription": subscription_data
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


@router.delete("/me")
async def delete_user_account(
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Delete user account and all associated data

    This endpoint:
    - Deletes all checks, claims, and evidence (via CASCADE)
    - Cancels active Stripe subscriptions
    - Deletes all subscription records
    - Deletes the user record

    This action is permanent and cannot be undone.
    Frontend must also delete the Clerk user separately.
    """
    user_id = current_user["id"]

    try:
        # 1. Get user record
        stmt = select(User).where(User.id == user_id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # 2. Cancel active Stripe subscriptions
        subscription_stmt = select(Subscription).where(
            Subscription.user_id == user_id,
            Subscription.status.in_(["active", "trialing", "past_due"])
        )
        subscription_result = await session.execute(subscription_stmt)
        active_subscriptions = subscription_result.scalars().all()

        for sub in active_subscriptions:
            if sub.stripe_subscription_id:
                try:
                    # Cancel immediately (not at period end)
                    stripe.Subscription.delete(sub.stripe_subscription_id)
                    logger.info(f"Cancelled Stripe subscription {sub.stripe_subscription_id} for user {user_id}")
                except stripe.error.StripeError as e:
                    # Log but don't block deletion if Stripe cancellation fails
                    logger.error(f"Failed to cancel Stripe subscription {sub.stripe_subscription_id}: {e}")
                except Exception as e:
                    logger.error(f"Unexpected error cancelling subscription {sub.stripe_subscription_id}: {e}")

        # 3. Delete all evidence records (must be done first due to foreign keys)
        # Get all claim IDs for this user's checks
        check_ids_stmt = select(Check.id).where(Check.user_id == user_id)
        check_ids_result = await session.execute(check_ids_stmt)
        check_ids = [row[0] for row in check_ids_result.all()]

        if check_ids:
            # Get all claim IDs for these checks
            claim_ids_stmt = select(Claim.id).where(Claim.check_id.in_(check_ids))
            claim_ids_result = await session.execute(claim_ids_stmt)
            claim_ids = [row[0] for row in claim_ids_result.all()]

            if claim_ids:
                # Delete all evidence for these claims
                await session.execute(
                    delete(Evidence).where(Evidence.claim_id.in_(claim_ids))
                )
                logger.info(f"Deleted evidence for {len(claim_ids)} claims")

            # Delete all claims for these checks
            await session.execute(
                delete(Claim).where(Claim.check_id.in_(check_ids))
            )
            logger.info(f"Deleted {len(claim_ids)} claims")

        # 4. Delete all checks
        checks_deleted = await session.execute(
            delete(Check).where(Check.user_id == user_id)
        )
        logger.info(f"Deleted {checks_deleted.rowcount} checks for user {user_id}")

        # 5. Delete all subscriptions
        subs_deleted = await session.execute(
            delete(Subscription).where(Subscription.user_id == user_id)
        )
        logger.info(f"Deleted {subs_deleted.rowcount} subscriptions for user {user_id}")

        # 6. Delete user record
        await session.delete(user)
        await session.commit()

        logger.info(f"Successfully deleted user account {user_id}")

        return {
            "message": "Account successfully deleted",
            "userId": user_id
        }

    except HTTPException:
        await session.rollback()
        raise
    except Exception as e:
        await session.rollback()
        logger.error(f"Failed to delete user {user_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete account. Please contact support at support@tru8.com"
        )

# ========== EMAIL NOTIFICATION PREFERENCES ==========

class EmailPreferencesRequest(BaseModel):
    email_notifications_enabled: bool | None = None
    email_check_completion: bool | None = None
    email_check_failure: bool | None = None
    email_weekly_digest: bool | None = None
    email_marketing: bool | None = None


@router.get("/email-preferences")
async def get_email_preferences(
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Get user's email notification preferences"""
    stmt = select(User).where(User.id == current_user["id"])
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "emailNotificationsEnabled": user.email_notifications_enabled,
        "checkCompletion": user.email_check_completion,
        "checkFailure": user.email_check_failure,
        "weeklyDigest": user.email_weekly_digest,
        "marketing": user.email_marketing
    }


@router.put("/email-preferences")
async def update_email_preferences(
    request: EmailPreferencesRequest,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Update user's email notification preferences"""
    stmt = select(User).where(User.id == current_user["id"])
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Update only provided fields
    if request.email_notifications_enabled is not None:
        user.email_notifications_enabled = request.email_notifications_enabled
        # If master toggle is disabled, disable all sub-preferences
        if not request.email_notifications_enabled:
            user.email_check_completion = False
            user.email_check_failure = False
            user.email_weekly_digest = False
            user.email_marketing = False

    if request.email_check_completion is not None:
        user.email_check_completion = request.email_check_completion
    if request.email_check_failure is not None:
        user.email_check_failure = request.email_check_failure
    if request.email_weekly_digest is not None:
        user.email_weekly_digest = request.email_weekly_digest
    if request.email_marketing is not None:
        user.email_marketing = request.email_marketing

    try:
        await session.commit()
        logger.info(f"Email preferences updated for user {user.id}")
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update preferences: {str(e)}")

    return {
        "success": True,
        "message": "Email preferences updated successfully",
        "preferences": {
            "emailNotificationsEnabled": user.email_notifications_enabled,
            "checkCompletion": user.email_check_completion,
            "checkFailure": user.email_check_failure,
            "weeklyDigest": user.email_weekly_digest,
            "marketing": user.email_marketing
        }
    }
