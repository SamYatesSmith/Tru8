from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_session
from app.core.auth import get_current_user
from app.core.config import settings
from app.models import User, Subscription
from pydantic import BaseModel
from typing import Optional
import stripe
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

# Configure Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY
STRIPE_WEBHOOK_SECRET = settings.STRIPE_WEBHOOK_SECRET

router = APIRouter()

class CreateCheckoutRequest(BaseModel):
    price_id: str
    plan: str  # 'starter' or 'pro'

class CheckoutResponse(BaseModel):
    session_id: str
    url: str

@router.post("/create-checkout-session")
async def create_checkout_session(
    request: CreateCheckoutRequest,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Create a Stripe Checkout session for subscription upgrade"""
    try:
        # Get user from database
        stmt = select(User).where(User.id == current_user["id"])
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Check for existing active subscription
        existing_sub_stmt = select(Subscription).where(
            Subscription.user_id == user.id,
            Subscription.status == "active"
        )
        existing_sub_result = await session.execute(existing_sub_stmt)
        existing_subscription = existing_sub_result.scalar_one_or_none()
        
        if existing_subscription:
            raise HTTPException(
                status_code=400, 
                detail="User already has an active subscription"
            )

        # Create Stripe checkout session
        checkout_session = stripe.checkout.Session.create(
            customer_email=user.email,
            client_reference_id=user.id,
            line_items=[{
                'price': request.price_id,
                'quantity': 1,
            }],
            mode='subscription',
            success_url=f"{settings.FRONTEND_URL}/dashboard?upgraded=true",
            cancel_url=f"{settings.FRONTEND_URL}/dashboard?cancelled=true",
            metadata={
                'user_id': user.id,
                'plan': request.plan,
            },
            allow_promotion_codes=True,
            billing_address_collection='required',
            tax_id_collection={
                'enabled': True,
            },
        )

        return CheckoutResponse(
            session_id=checkout_session.id,
            url=checkout_session.url
        )

    except stripe.error.StripeError as e:
        logger.error(f"Stripe error creating checkout session: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating checkout session: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    session: AsyncSession = Depends(get_session)
):
    """Handle Stripe webhook events"""
    payload = await request.body()
    sig_header = request.headers.get('stripe-signature')

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        logger.error(f"Invalid payload: {e}")
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError as e:
        logger.error(f"Invalid signature: {e}")
        raise HTTPException(status_code=400, detail="Invalid signature")

    # Handle the event
    if event['type'] == 'checkout.session.completed':
        session_data = event['data']['object']
        await handle_successful_payment(session_data, session)

    elif event['type'] == 'customer.subscription.updated':
        subscription = event['data']['object']
        await handle_subscription_updated(subscription, session)

    elif event['type'] == 'customer.subscription.deleted':
        subscription = event['data']['object']
        await handle_subscription_cancelled(subscription, session)

    elif event['type'] == 'invoice.paid':
        invoice = event['data']['object']
        await handle_invoice_paid(invoice, session)

    else:
        logger.info(f"Unhandled event type: {event['type']}")

    return {"status": "success"}

async def handle_successful_payment(session_data: dict, session: AsyncSession):
    """Handle successful payment from Stripe Checkout"""
    user_id = session_data.get('client_reference_id')
    stripe_subscription_id = session_data.get('subscription')
    
    if not user_id:
        logger.error("No user_id found in session metadata")
        return

    # Get the subscription details from Stripe
    stripe_subscription = stripe.Subscription.retrieve(stripe_subscription_id)
    stripe_customer_id = stripe_subscription.get('customer')

    # Get user from database
    stmt = select(User).where(User.id == user_id)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user:
        logger.error(f"User {user_id} not found")
        return

    # Determine plan details from the subscription
    # Map Stripe price IDs to plan names and credit amounts
    price_id = stripe_subscription['items']['data'][0]['price']['id']

    # For now, we only have Professional plan (£7/month = 40 checks)
    if price_id == settings.STRIPE_PRICE_ID_PRO:
        plan = 'pro'
        credits_per_month = 40  # Professional plan: 40 checks per month
    else:
        # Fallback for unknown price IDs
        logger.warning(f"Unknown price ID: {price_id}, defaulting to free plan")
        plan = 'free'
        credits_per_month = 3
    
    # Get existing subscription
    existing_sub_stmt = select(Subscription).where(Subscription.user_id == user_id)
    existing_sub_result = await session.execute(existing_sub_stmt)
    existing_subscription = existing_sub_result.scalar_one_or_none()
    if existing_subscription:
        # Update existing subscription
        existing_subscription.plan = plan
        existing_subscription.status = "active"
        existing_subscription.credits_per_month = credits_per_month
        existing_subscription.credits_remaining = credits_per_month  # Reset credits
        existing_subscription.current_period_start = datetime.fromtimestamp(
            stripe_subscription['current_period_start']
        )
        existing_subscription.current_period_end = datetime.fromtimestamp(
            stripe_subscription['current_period_end']
        )
        existing_subscription.stripe_subscription_id = stripe_subscription_id
        existing_subscription.stripe_customer_id = stripe_customer_id
        existing_subscription.updated_at = datetime.utcnow()
    else:
        # Create new subscription
        new_subscription = Subscription(
            id=f"sub_{user_id}_{datetime.utcnow().timestamp()}",
            user_id=user_id,
            plan=plan,
            status="active",
            credits_per_month=credits_per_month,
            credits_remaining=credits_per_month,
            current_period_start=datetime.fromtimestamp(
                stripe_subscription['current_period_start']
            ),
            current_period_end=datetime.fromtimestamp(
                stripe_subscription['current_period_end']
            ),
            stripe_subscription_id=stripe_subscription_id,
            stripe_customer_id=stripe_customer_id,
        )
        session.add(new_subscription)

    # Update user credits
    user.credits = credits_per_month
    user.updated_at = datetime.utcnow()
    
    await session.commit()
    logger.info(f"Successfully processed payment for user {user_id}, plan: {plan}")

async def handle_subscription_updated(subscription: dict, session: AsyncSession):
    """Handle subscription updates from Stripe"""
    stripe_subscription_id = subscription['id']
    
    # Find subscription in our database
    stmt = select(Subscription).where(Subscription.stripe_subscription_id == stripe_subscription_id)
    result = await session.execute(stmt)
    db_subscription = result.scalar_one_or_none()
    
    if not db_subscription:
        logger.error(f"Subscription {stripe_subscription_id} not found in database")
        return

    # Update subscription status
    db_subscription.status = subscription['status']
    db_subscription.current_period_start = datetime.fromtimestamp(
        subscription['current_period_start']
    )
    db_subscription.current_period_end = datetime.fromtimestamp(
        subscription['current_period_end']
    )
    db_subscription.updated_at = datetime.utcnow()
    
    # If subscription renewed, reset credits
    if subscription['status'] == 'active':
        db_subscription.credits_remaining = db_subscription.credits_per_month
        # Update user credits too
        user_stmt = select(User).where(User.id == db_subscription.user_id)
        user_result = await session.execute(user_stmt)
        user = user_result.scalar_one_or_none()
        if user:
            user.credits = db_subscription.credits_per_month
            user.updated_at = datetime.utcnow()
    
    await session.commit()
    logger.info(f"Updated subscription {stripe_subscription_id} status to {subscription['status']}")

async def handle_subscription_cancelled(subscription: dict, session: AsyncSession):
    """Handle subscription cancellation from Stripe"""
    stripe_subscription_id = subscription['id']
    
    # Find subscription in our database
    stmt = select(Subscription).where(Subscription.stripe_subscription_id == stripe_subscription_id)
    result = await session.execute(stmt)
    db_subscription = result.scalar_one_or_none()
    
    if not db_subscription:
        logger.error(f"Subscription {stripe_subscription_id} not found in database")
        return

    # Update subscription status
    db_subscription.status = "cancelled"
    db_subscription.updated_at = datetime.utcnow()
    
    # Reset user to free tier (but keep remaining credits until period ends)
    user_stmt = select(User).where(User.id == db_subscription.user_id)
    user_result = await session.execute(user_stmt)
    user = user_result.scalar_one_or_none()
    
    if user:
        user.updated_at = datetime.utcnow()
        # Note: We don't immediately reset credits - they keep what they have until period ends
    
    await session.commit()
    logger.info(f"Cancelled subscription {stripe_subscription_id}")


async def handle_invoice_paid(invoice: dict, session: AsyncSession):
    """
    Handle invoice.paid event from Stripe.

    This fires on every successful payment including renewals.
    Updates subscription period dates and resets monthly credits.
    """
    # Only process subscription invoices
    stripe_subscription_id = invoice.get('subscription')
    if not stripe_subscription_id:
        logger.info("Invoice is not for a subscription, skipping")
        return

    # Find subscription in our database
    stmt = select(Subscription).where(Subscription.stripe_subscription_id == stripe_subscription_id)
    result = await session.execute(stmt)
    db_subscription = result.scalar_one_or_none()

    if not db_subscription:
        logger.warning(f"Subscription {stripe_subscription_id} not found for invoice.paid")
        return

    # Fetch current subscription details from Stripe to get updated period
    try:
        stripe_subscription = stripe.Subscription.retrieve(stripe_subscription_id)
    except stripe.error.StripeError as e:
        logger.error(f"Failed to retrieve subscription from Stripe: {e}")
        return

    # Update subscription period dates
    new_period_start = datetime.fromtimestamp(stripe_subscription['current_period_start'])
    new_period_end = datetime.fromtimestamp(stripe_subscription['current_period_end'])

    logger.info(f"Invoice paid for subscription {stripe_subscription_id}. "
                f"Updating period: {db_subscription.current_period_start} -> {new_period_start}")

    db_subscription.current_period_start = new_period_start
    db_subscription.current_period_end = new_period_end
    db_subscription.status = stripe_subscription['status']
    db_subscription.updated_at = datetime.utcnow()

    # Reset monthly credits
    db_subscription.credits_remaining = db_subscription.credits_per_month

    # Update user credits
    user_stmt = select(User).where(User.id == db_subscription.user_id)
    user_result = await session.execute(user_stmt)
    user = user_result.scalar_one_or_none()

    if user:
        user.credits = db_subscription.credits_per_month
        user.updated_at = datetime.utcnow()
        logger.info(f"Reset credits for user {user.id} to {db_subscription.credits_per_month}")

    await session.commit()
    logger.info(f"Successfully processed invoice.paid for subscription {stripe_subscription_id}")


@router.get("/subscription-status")
async def get_subscription_status(
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Get current user's subscription status"""
    stmt = select(User).where(User.id == current_user["id"])
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Get user's subscription
    sub_stmt = select(Subscription).where(
        Subscription.user_id == user.id,
        Subscription.status == "active"
    )
    sub_result = await session.execute(sub_stmt)
    subscription = sub_result.scalar_one_or_none()
    
    if not subscription:
        return {
            "hasSubscription": False,
            "plan": "free",
            "status": "free",
            "creditsPerMonth": 3,
            "creditsRemaining": user.credits,
        }

    return {
        "hasSubscription": True,
        "plan": subscription.plan,
        "status": subscription.status,
        "creditsPerMonth": subscription.credits_per_month,
        "creditsRemaining": subscription.credits_remaining,
        "currentPeriodStart": subscription.current_period_start.isoformat(),
        "currentPeriodEnd": subscription.current_period_end.isoformat(),
        "stripeSubscriptionId": subscription.stripe_subscription_id,
    }

@router.post("/cancel-subscription")
async def cancel_subscription(
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Cancel user's subscription"""
    stmt = select(User).where(User.id == current_user["id"])
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()
    
    # Get user's active subscription
    sub_stmt = select(Subscription).where(
        Subscription.user_id == user.id,
        Subscription.status == "active"
    )
    sub_result = await session.execute(sub_stmt)
    subscription = sub_result.scalar_one_or_none()
    
    if not user or not subscription:
        raise HTTPException(status_code=404, detail="No active subscription found")

    try:
        # Cancel the subscription in Stripe (at period end)
        stripe.Subscription.modify(
            subscription.stripe_subscription_id,
            cancel_at_period_end=True
        )

        return {"message": "Subscription will be cancelled at the end of the current period"}

    except stripe.error.StripeError as e:
        logger.error(f"Error cancelling subscription: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/create-portal-session")
async def create_billing_portal_session(
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Create a Stripe billing portal session

    Allows users to:
    - View billing history
    - Download invoices
    - Update payment method
    - Cancel subscription
    """
    try:
        # Get user from database
        stmt = select(User).where(User.id == current_user["id"])
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Get user's subscription to find Stripe customer ID
        sub_stmt = select(Subscription).where(
            Subscription.user_id == user.id
        ).order_by(desc(Subscription.created_at)).limit(1)
        sub_result = await session.execute(sub_stmt)
        subscription = sub_result.scalar_one_or_none()

        # If no subscription exists yet, we need to create a customer first
        if not subscription or not subscription.stripe_customer_id:
            # Create a Stripe customer for this user
            customer = stripe.Customer.create(
                email=user.email,
                metadata={
                    'user_id': user.id
                }
            )
            customer_id = customer.id

            # Save customer ID to subscription if it exists
            if subscription:
                subscription.stripe_customer_id = customer_id
                await session.commit()
        else:
            customer_id = subscription.stripe_customer_id

        # Create billing portal session
        portal_session = stripe.billing_portal.Session.create(
            customer=customer_id,
            return_url=f"{settings.FRONTEND_URL}/dashboard/settings?tab=subscription",
        )

        return {"url": portal_session.url}

    except stripe.error.StripeError as e:
        logger.error(f"Stripe error creating portal session: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating portal session: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/reactivate-subscription")
async def reactivate_subscription(
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Reactivate a subscription that was scheduled for cancellation

    Removes the cancel_at_period_end flag from the Stripe subscription,
    allowing it to continue renewing after the current period ends.
    """
    try:
        # Get user from database
        stmt = select(User).where(User.id == current_user["id"])
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Get user's subscription
        sub_stmt = select(Subscription).where(
            Subscription.user_id == user.id,
            Subscription.status == "active"
        )
        sub_result = await session.execute(sub_stmt)
        subscription = sub_result.scalar_one_or_none()

        if not subscription or not subscription.stripe_subscription_id:
            raise HTTPException(
                status_code=404,
                detail="No active subscription found to reactivate"
            )

        # Reactivate the subscription in Stripe
        stripe_subscription = stripe.Subscription.modify(
            subscription.stripe_subscription_id,
            cancel_at_period_end=False
        )

        logger.info(f"Reactivated subscription {subscription.stripe_subscription_id} for user {user.id}")

        return {
            "message": "Subscription reactivated successfully",
            "subscription": {
                "id": subscription.id,
                "status": "active",
                "currentPeriodEnd": stripe_subscription.current_period_end
            }
        }

    except stripe.error.StripeError as e:
        logger.error(f"Stripe error reactivating subscription: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error reactivating subscription: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")