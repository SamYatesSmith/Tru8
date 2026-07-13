from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.core.database import get_session
from app.core.auth import get_current_user
from app.core.config import settings
from app.models import User, Subscription
from pydantic import BaseModel
from typing import Optional
import stripe
from datetime import datetime, timedelta, timezone
import logging

logger = logging.getLogger(__name__)

# Configure Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY
STRIPE_WEBHOOK_SECRET = settings.STRIPE_WEBHOOK_SECRET

router = APIRouter()


async def _get_or_create_stripe_customer(user: User, session: AsyncSession) -> str:
    """Find existing Stripe customer ID or create a new one."""
    sub_stmt = (
        select(Subscription)
        .where(Subscription.user_id == user.id)
        .order_by(desc(Subscription.created_at))
        .limit(1)
    )
    sub_result = await session.execute(sub_stmt)
    subscription = sub_result.scalar_one_or_none()

    if subscription and subscription.stripe_customer_id:
        return subscription.stripe_customer_id

    customer = stripe.Customer.create(email=user.email, metadata={"user_id": user.id})
    if subscription:
        subscription.stripe_customer_id = customer.id
        await session.commit()
    return customer.id


class CreateCheckoutRequest(BaseModel):
    price_id: str
    plan: str  # 'starter' or 'professional'


class CheckoutResponse(BaseModel):
    session_id: str
    url: str


@router.post("/create-checkout-session")
async def create_checkout_session(
    request: CreateCheckoutRequest,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Create a Stripe Checkout session for subscription upgrade"""
    try:
        # Get user from database
        stmt = select(User).where(User.id == current_user["id"])
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

        # Create user if doesn't exist (first login)
        if not user:
            email = current_user.get("email")
            if not email:
                raise HTTPException(
                    status_code=500,
                    detail="Unable to retrieve user email from authentication provider",
                )

            user = User(
                id=current_user["id"],
                email=email,
                name=current_user.get("name"),
                credits=3,  # Free tier
            )
            session.add(user)
            try:
                await session.commit()
                await session.refresh(user)
            except Exception as e:
                await session.rollback()
                raise HTTPException(
                    status_code=500, detail=f"Failed to create user: {str(e)}"
                )

        # Check for existing active subscription
        existing_sub_stmt = select(Subscription).where(
            Subscription.user_id == user.id, Subscription.status == "active"
        )
        existing_sub_result = await session.execute(existing_sub_stmt)
        existing_subscription = existing_sub_result.scalar_one_or_none()

        if existing_subscription:
            raise HTTPException(
                status_code=400, detail="User already has an active subscription"
            )

        # Reuse or create Stripe customer
        customer_id = await _get_or_create_stripe_customer(user, session)

        # Create Stripe checkout session
        checkout_session = stripe.checkout.Session.create(
            customer=customer_id,
            client_reference_id=user.id,
            line_items=[
                {
                    "price": request.price_id,
                    "quantity": 1,
                }
            ],
            mode="subscription",
            success_url=f"{settings.FRONTEND_URL}/dashboard?upgraded=true",
            cancel_url=f"{settings.FRONTEND_URL}/dashboard?cancelled=true",
            metadata={
                "user_id": user.id,
                "plan": request.plan,
            },
            allow_promotion_codes=True,
            billing_address_collection="required",
            tax_id_collection={
                "enabled": True,
            },
            customer_update={
                "name": "auto",
                "address": "auto",
            },
        )

        return CheckoutResponse(
            session_id=checkout_session.id, url=checkout_session.url
        )

    except stripe.error.StripeError as e:
        logger.error(f"Stripe error creating checkout session: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating checkout session: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/webhook")
async def stripe_webhook(
    request: Request, session: AsyncSession = Depends(get_session)
):
    """Handle Stripe webhook events"""
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

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

    # Idempotency: skip duplicate event deliveries (72h TTL in Redis,
    # matching Stripe's 72h retry window)
    event_id = event["id"]
    try:
        from app.core.redis import get_redis

        redis_client = await get_redis()
        if redis_client:
            cache_key = f"stripe_event:{event_id}"
            if await redis_client.exists(cache_key):
                logger.info(f"Duplicate Stripe event {event_id}, skipping")
                return {"status": "success"}
            await redis_client.set(cache_key, "1", ex=259200)  # 72h
    except Exception:
        pass  # Degrade gracefully if Redis unavailable

    # Handle the event — wrap each handler so individual failures return 500
    # (Stripe will retry on 5xx, preventing lost events)
    try:
        if event["type"] == "checkout.session.completed":
            session_data = event["data"]["object"]
            # Route to agent credit handler or subscription handler
            if session_data.get("metadata", {}).get("purchase_type") == "agent_credits":
                await handle_agent_credit_purchase(session_data, session)
            else:
                await handle_successful_payment(session_data, session)

        elif event["type"] == "customer.subscription.updated":
            subscription = event["data"]["object"]
            await handle_subscription_updated(subscription, session)

        elif event["type"] == "customer.subscription.deleted":
            subscription = event["data"]["object"]
            await handle_subscription_cancelled(subscription, session)

        elif event["type"] == "invoice.paid":
            invoice = event["data"]["object"]
            await handle_invoice_paid(invoice, session)

        # F-PAY-02 / F-PAY-03: previously missing event handlers
        elif event["type"] == "charge.refunded":
            charge = event["data"]["object"]
            await handle_charge_refunded(charge, session)

        elif event["type"] == "charge.dispute.created":
            dispute = event["data"]["object"]
            await handle_charge_dispute(dispute, session)

        elif event["type"] == "invoice.payment_failed":
            invoice = event["data"]["object"]
            await handle_invoice_payment_failed(invoice, session)

        elif event["type"] == "customer.subscription.trial_will_end":
            subscription = event["data"]["object"]
            await handle_trial_will_end(subscription, session)

        elif event["type"] == "customer.deleted":
            customer = event["data"]["object"]
            await handle_customer_deleted(customer, session)

        else:
            logger.info(f"Unhandled event type: {event['type']}")
    except Exception as e:
        logger.error(
            f"Webhook handler failed for event {event_id} ({event['type']}): {e}"
        )
        raise HTTPException(status_code=500, detail="Webhook handler error")

    return {"status": "success"}


async def handle_agent_credit_purchase(session_data: dict, session: AsyncSession):
    """Handle agent credit pack purchase from Stripe Checkout (L-07)."""
    user_id = session_data.get("client_reference_id")
    metadata = session_data.get("metadata", {})

    try:
        pence_value = int(metadata.get("pence_value", 0))
    except (ValueError, TypeError):
        logger.error(
            f"Agent credit purchase: invalid pence_value in metadata: {metadata}"
        )
        return

    pack = metadata.get("credit_pack", "unknown")

    if not user_id or not pence_value:
        logger.error(
            f"Agent credit purchase missing data: user={user_id}, pence={pence_value}"
        )
        return

    # Cross-check: Stripe amount_total (in pence for GBP) must match metadata
    stripe_amount = session_data.get("amount_total")
    if stripe_amount is not None and stripe_amount != pence_value:
        logger.error(
            f"Agent credit purchase amount mismatch: stripe={stripe_amount}, "
            f"metadata={pence_value}, user={user_id}. Rejecting."
        )
        return

    # Atomic DB-level increment to prevent race conditions on concurrent webhooks
    from sqlalchemy import update as sa_update

    result = await session.execute(
        sa_update(User)
        .where(User.id == user_id)
        .values(
            credit_balance_pence=User.credit_balance_pence + pence_value,
            updated_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )
    )
    if result.rowcount == 0:
        logger.error(f"User {user_id} not found for agent credit purchase")
        return

    await session.commit()

    logger.info(
        f"Agent credit purchase: user={user_id}, pack={pack}, added={pence_value}p"
    )


async def handle_successful_payment(session_data: dict, session: AsyncSession):
    """Handle successful payment from Stripe Checkout"""
    user_id = session_data.get("client_reference_id")
    stripe_subscription_id = session_data.get("subscription")

    if not user_id:
        logger.error("No user_id found in session metadata")
        return

    # Get the subscription details from Stripe
    stripe_subscription = stripe.Subscription.retrieve(stripe_subscription_id)
    stripe_customer_id = stripe_subscription.get("customer")

    # Get user from database
    stmt = select(User).where(User.id == user_id)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        logger.error(f"User {user_id} not found")
        return

    # Determine plan details from the subscription
    # Map Stripe price IDs to plan names and credit amounts
    price_id = stripe_subscription["items"]["data"][0]["price"]["id"]

    PRICE_TO_PLAN = {
        settings.STRIPE_PRICE_ID_PRO: ("starter", 40),
        settings.STRIPE_PRICE_ID_DEVELOPER: ("professional", 200),
        # Console (2026-07): monthly + annual both grant 200 checks/month
        settings.STRIPE_PRICE_ID_CONSOLE: ("console", 200),
        settings.STRIPE_PRICE_ID_CONSOLE_ANNUAL: ("console", 200),
    }
    PRICE_TO_PLAN.pop("", None)  # unset env vars must never match

    if price_id in PRICE_TO_PLAN:
        plan, credits_per_month = PRICE_TO_PLAN[price_id]
    else:
        logger.error(
            f"Unknown Stripe price ID: {price_id}. "
            f"Expected: {list(PRICE_TO_PLAN.keys())}. "
            f"Check STRIPE_PRICE_ID_PRO / _DEVELOPER / _CONSOLE / "
            f"_CONSOLE_ANNUAL env vars."
        )
        return  # Do not create/update subscription with incorrect data

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
        existing_subscription.billing_interval = _interval_from_subscription(
            stripe_subscription
        )
        existing_subscription.current_period_start = datetime.fromtimestamp(
            stripe_subscription["current_period_start"], tz=timezone.utc
        ).replace(tzinfo=None)
        existing_subscription.current_period_end = datetime.fromtimestamp(
            stripe_subscription["current_period_end"], tz=timezone.utc
        ).replace(tzinfo=None)
        existing_subscription.stripe_subscription_id = stripe_subscription_id
        existing_subscription.stripe_customer_id = stripe_customer_id
        existing_subscription.updated_at = datetime.now(timezone.utc).replace(
            tzinfo=None
        )
    else:
        # Create new subscription
        new_subscription = Subscription(
            id=f"sub_{user_id}_{datetime.now(timezone.utc).timestamp()}",
            user_id=user_id,
            plan=plan,
            status="active",
            credits_per_month=credits_per_month,
            credits_remaining=credits_per_month,
            billing_interval=_interval_from_subscription(stripe_subscription),
            current_period_start=datetime.fromtimestamp(
                stripe_subscription["current_period_start"], tz=timezone.utc
            ).replace(tzinfo=None),
            current_period_end=datetime.fromtimestamp(
                stripe_subscription["current_period_end"], tz=timezone.utc
            ).replace(tzinfo=None),
            stripe_subscription_id=stripe_subscription_id,
            stripe_customer_id=stripe_customer_id,
        )
        session.add(new_subscription)

    # Update user credits
    user.credits = credits_per_month
    user.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)

    await session.commit()
    logger.info(f"Successfully processed payment for user {user_id}, plan: {plan}")


def _plan_from_price_id(price_id: str):
    """F-PAY-04 helper: map a Stripe price ID to (plan_name, credits_per_month).

    Returns ``None`` if the price ID is unknown — caller decides whether to
    treat that as a hard error or fall through to status-only updates.

    NB: env vars are named STRIPE_PRICE_ID_PRO / _DEVELOPER for historical
    reasons; user-facing names are 'starter' / 'professional'. M-04 in the
    audit tracks renaming env vars post-launch.
    """
    mapping = {
        settings.STRIPE_PRICE_ID_PRO: ("starter", 40),
        settings.STRIPE_PRICE_ID_DEVELOPER: ("professional", 200),
        # Console (2026-07): monthly + annual both grant 200 checks/month
        settings.STRIPE_PRICE_ID_CONSOLE: ("console", 200),
        settings.STRIPE_PRICE_ID_CONSOLE_ANNUAL: ("console", 200),
    }
    mapping.pop("", None)  # unset env vars must never match
    return mapping.get(price_id)


def _interval_from_subscription(stripe_subscription: dict) -> str:
    """Billing cadence ('month' | 'year') from the active price's recurring
    interval. Defaults to 'month' if the shape is unexpected."""
    try:
        price = stripe_subscription["items"]["data"][0]["price"]
        interval = (price.get("recurring") or {}).get("interval")
    except (KeyError, IndexError, TypeError):
        interval = None
    return "year" if interval == "year" else "month"


async def handle_subscription_updated(subscription: dict, session: AsyncSession):
    """Handle ``customer.subscription.updated`` from Stripe.

    F-PAY-04: re-derive ``plan`` + ``credits_per_month`` from the active
    item's price ID on every update. Without this, Stripe Customer Portal
    upgrades (Starter -> Professional) silently leave the DB at the old
    plan + old credit allocation.
    """
    stripe_subscription_id = subscription["id"]

    stmt = select(Subscription).where(
        Subscription.stripe_subscription_id == stripe_subscription_id
    )
    result = await session.execute(stmt)
    db_subscription = result.scalar_one_or_none()

    if not db_subscription:
        logger.error(f"Subscription {stripe_subscription_id} not found in database")
        return

    db_subscription.status = subscription["status"]
    db_subscription.current_period_start = datetime.fromtimestamp(
        subscription["current_period_start"], tz=timezone.utc
    ).replace(tzinfo=None)
    db_subscription.current_period_end = datetime.fromtimestamp(
        subscription["current_period_end"], tz=timezone.utc
    ).replace(tzinfo=None)
    db_subscription.billing_interval = _interval_from_subscription(subscription)
    db_subscription.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)

    # F-PAY-04: re-derive plan + credit allocation from price ID
    items = subscription.get("items", {}).get("data", [])
    plan_changed = False
    if items:
        price_id = items[0].get("price", {}).get("id")
        mapped = _plan_from_price_id(price_id) if price_id else None
        if mapped:
            new_plan, new_credits = mapped
            if (
                db_subscription.plan != new_plan
                or db_subscription.credits_per_month != new_credits
            ):
                logger.info(
                    f"[F-PAY-04] plan change for {stripe_subscription_id}: "
                    f"{db_subscription.plan}/{db_subscription.credits_per_month} -> "
                    f"{new_plan}/{new_credits} (price_id={price_id})"
                )
                db_subscription.plan = new_plan
                db_subscription.credits_per_month = new_credits
                plan_changed = True
        else:
            logger.warning(
                f"[F-PAY-04] unknown price_id {price_id!r} on {stripe_subscription_id}; "
                f"leaving plan/credits unchanged. Expected one of: "
                f"{[settings.STRIPE_PRICE_ID_PRO, settings.STRIPE_PRICE_ID_DEVELOPER]}"
            )

    # Renewal OR plan change -> reset to new allocation.
    if subscription["status"] == "active" and (
        plan_changed
        or db_subscription.credits_remaining < db_subscription.credits_per_month
    ):
        db_subscription.credits_remaining = db_subscription.credits_per_month
        user_stmt = select(User).where(User.id == db_subscription.user_id)
        user_result = await session.execute(user_stmt)
        user = user_result.scalar_one_or_none()
        if user:
            user.credits = db_subscription.credits_per_month
            user.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)

    await session.commit()
    logger.info(
        f"Updated subscription {stripe_subscription_id} status to {subscription['status']}"
        + (" (plan changed)" if plan_changed else "")
    )


# ---------------------------------------------------------------------------
# F-PAY-02 / F-PAY-03: handlers for refund / dispute / failed renewal /
# trial-ending / deleted customer. Without these, refunded users keep their
# credits, disputed charges leave subscriptions active, failed renewals
# stay "active", and deleted Stripe customers remain billable in our DB.
# ---------------------------------------------------------------------------


async def _revoke_credits_for_charge(
    charge: dict,
    session: AsyncSession,
    reason: str,
) -> None:
    """Best-effort: clear monthly subscription credits + zero user.credits for
    the user associated with a refunded / disputed Stripe charge.

    We deliberately do NOT touch ``credit_balance_pence`` (agent credit
    packs) because refund-vs-purchase reconciliation for those is policy
    not code — flagged for separate post-launch policy work."""
    customer_id = charge.get("customer")
    if not customer_id:
        logger.warning(
            f"[{reason}] charge {charge.get('id')} has no customer; skipping"
        )
        return

    sub_stmt = select(Subscription).where(
        Subscription.stripe_customer_id == customer_id
    )
    result = await session.execute(sub_stmt)
    db_subs = result.scalars().all()

    for sub in db_subs:
        logger.info(
            f"[{reason}] revoking credits on subscription {sub.id} "
            f"(user={sub.user_id}, charge={charge.get('id')})"
        )
        sub.credits_remaining = 0
        sub.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
        user_stmt = select(User).where(User.id == sub.user_id)
        user_result = await session.execute(user_stmt)
        user = user_result.scalar_one_or_none()
        if user:
            user.credits = 0
            user.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)

    if not db_subs:
        logger.info(
            f"[{reason}] no subscription found for stripe_customer_id={customer_id}"
        )


async def handle_charge_refunded(charge: dict, session: AsyncSession) -> None:
    """F-PAY-03: Stripe charge refunded — revoke matching subscription credits."""
    await _revoke_credits_for_charge(charge, session, reason="REFUND")
    await session.commit()


async def handle_charge_dispute(dispute: dict, session: AsyncSession) -> None:
    """F-PAY-02: chargeback / dispute filed — revoke matching subscription credits.

    Stripe will follow up with a ``charge.dispute.closed`` event for the
    outcome; for now we treat the dispute as cash-loss until proven otherwise."""
    # Dispute objects reference a charge id (string).
    charge_id = dispute.get("charge")
    if not charge_id:
        logger.warning("Dispute event with no charge id; skipping")
        return
    try:
        charge = stripe.Charge.retrieve(charge_id)
    except Exception as e:
        logger.error(f"Could not retrieve charge {charge_id} for dispute: {e}")
        return
    await _revoke_credits_for_charge(charge, session, reason="DISPUTE")
    await session.commit()


async def handle_invoice_payment_failed(invoice: dict, session: AsyncSession) -> None:
    """F-PAY-02: renewal payment failed — mark subscription past_due so the
    rest of the app can downgrade access. Credits are NOT reset to zero here;
    Stripe will retry the payment and either succeed (invoice.paid) or move
    to subscription cancellation."""
    sub_id = invoice.get("subscription")
    if not sub_id:
        logger.info(
            f"invoice.payment_failed for non-subscription invoice {invoice.get('id')}; skipping"
        )
        return
    sub_stmt = select(Subscription).where(Subscription.stripe_subscription_id == sub_id)
    result = await session.execute(sub_stmt)
    db_subscription = result.scalar_one_or_none()
    if not db_subscription:
        logger.warning(f"invoice.payment_failed for unknown subscription {sub_id}")
        return

    db_subscription.status = "past_due"
    db_subscription.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    await session.commit()
    logger.info(
        f"[PAYMENT_FAILED] subscription {sub_id} marked past_due "
        f"(user={db_subscription.user_id}, invoice={invoice.get('id')})"
    )


async def handle_trial_will_end(subscription: dict, session: AsyncSession) -> None:
    """F-PAY-02: 3 days before a trial converts. Log only — actual email send
    is handled by Clerk/Resend email templates downstream of this signal."""
    logger.info(
        f"[TRIAL_WILL_END] subscription {subscription.get('id')} "
        f"customer={subscription.get('customer')} trial_end={subscription.get('trial_end')}"
    )


async def handle_customer_deleted(customer: dict, session: AsyncSession) -> None:
    """F-PAY-02: Stripe customer object deleted (rare, usually admin action).
    Null out the stripe_customer_id link on every local Subscription so we
    don't keep trying to bill an orphan."""
    customer_id = customer.get("id")
    if not customer_id:
        return
    sub_stmt = select(Subscription).where(
        Subscription.stripe_customer_id == customer_id
    )
    result = await session.execute(sub_stmt)
    db_subs = result.scalars().all()
    for sub in db_subs:
        sub.stripe_customer_id = None
        sub.status = "cancelled"
        sub.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    if db_subs:
        await session.commit()
        logger.info(
            f"[CUSTOMER_DELETED] cleared stripe_customer_id on {len(db_subs)} subscriptions "
            f"for customer={customer_id}"
        )


async def handle_subscription_cancelled(subscription: dict, session: AsyncSession):
    """Handle subscription cancellation from Stripe"""
    stripe_subscription_id = subscription["id"]

    # Find subscription in our database
    stmt = select(Subscription).where(
        Subscription.stripe_subscription_id == stripe_subscription_id
    )
    result = await session.execute(stmt)
    db_subscription = result.scalar_one_or_none()

    if not db_subscription:
        logger.error(f"Subscription {stripe_subscription_id} not found in database")
        return

    # Update subscription status
    db_subscription.status = "cancelled"
    db_subscription.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)

    # Reset user to free tier (but keep remaining credits until period ends)
    user_stmt = select(User).where(User.id == db_subscription.user_id)
    user_result = await session.execute(user_stmt)
    user = user_result.scalar_one_or_none()

    if user:
        user.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
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
    stripe_subscription_id = invoice.get("subscription")
    if not stripe_subscription_id:
        logger.info("Invoice is not for a subscription, skipping")
        return

    # Find subscription in our database
    stmt = select(Subscription).where(
        Subscription.stripe_subscription_id == stripe_subscription_id
    )
    result = await session.execute(stmt)
    db_subscription = result.scalar_one_or_none()

    if not db_subscription:
        logger.warning(
            f"Subscription {stripe_subscription_id} not found for invoice.paid"
        )
        return

    # Fetch current subscription details from Stripe to get updated period
    try:
        stripe_subscription = stripe.Subscription.retrieve(stripe_subscription_id)
    except stripe.error.StripeError as e:
        logger.error(f"Failed to retrieve subscription from Stripe: {e}")
        return

    # Update subscription period dates
    new_period_start = datetime.fromtimestamp(
        stripe_subscription["current_period_start"], tz=timezone.utc
    ).replace(tzinfo=None)
    new_period_end = datetime.fromtimestamp(
        stripe_subscription["current_period_end"], tz=timezone.utc
    ).replace(tzinfo=None)

    logger.info(
        f"Invoice paid for subscription {stripe_subscription_id}. "
        f"Updating period: {db_subscription.current_period_start} -> {new_period_start}"
    )

    db_subscription.current_period_start = new_period_start
    db_subscription.current_period_end = new_period_end
    db_subscription.billing_interval = _interval_from_subscription(stripe_subscription)
    db_subscription.status = stripe_subscription["status"]
    db_subscription.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)

    # Reset monthly credits
    db_subscription.credits_remaining = db_subscription.credits_per_month

    # Update user credits
    user_stmt = select(User).where(User.id == db_subscription.user_id)
    user_result = await session.execute(user_stmt)
    user = user_result.scalar_one_or_none()

    if user:
        user.credits = db_subscription.credits_per_month
        user.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
        logger.info(
            f"Reset credits for user {user.id} to {db_subscription.credits_per_month}"
        )

    await session.commit()
    logger.info(
        f"Successfully processed invoice.paid for subscription {stripe_subscription_id}"
    )


@router.get("/subscription-status")
async def get_subscription_status(
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Get current user's subscription status"""
    stmt = select(User).where(User.id == current_user["id"])
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    # Create user if doesn't exist (first login)
    if not user:
        email = current_user.get("email")
        if not email:
            raise HTTPException(
                status_code=500,
                detail="Unable to retrieve user email from authentication provider",
            )

        user = User(
            id=current_user["id"],
            email=email,
            name=current_user.get("name"),
            credits=3,  # Free tier
        )
        session.add(user)
        try:
            await session.commit()
            await session.refresh(user)
        except Exception as e:
            await session.rollback()
            raise HTTPException(
                status_code=500, detail=f"Failed to create user: {str(e)}"
            )

    # Get user's subscription
    sub_stmt = select(Subscription).where(
        Subscription.user_id == user.id, Subscription.status == "active"
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
            "subscriptionsEnabled": settings.SUBSCRIPTIONS_ENABLED,
        }

    # Check Stripe for cancellation status
    cancel_at_period_end = False
    if subscription.stripe_subscription_id:
        try:
            stripe_sub = stripe.Subscription.retrieve(
                subscription.stripe_subscription_id
            )
            cancel_at_period_end = stripe_sub.cancel_at_period_end
        except Exception:
            pass  # Graceful degradation — show as active

    return {
        "hasSubscription": True,
        "plan": subscription.plan,
        "status": subscription.status,
        "billingInterval": subscription.billing_interval,
        "creditsPerMonth": subscription.credits_per_month,
        "creditsRemaining": subscription.credits_remaining,
        "currentPeriodStart": subscription.current_period_start.isoformat(),
        "currentPeriodEnd": subscription.current_period_end.isoformat(),
        "stripeSubscriptionId": subscription.stripe_subscription_id,
        "cancelAtPeriodEnd": cancel_at_period_end,
        "subscriptionsEnabled": settings.SUBSCRIPTIONS_ENABLED,
    }


@router.post("/cancel-subscription")
async def cancel_subscription(
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Cancel user's subscription"""
    stmt = select(User).where(User.id == current_user["id"])
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    # Get user's active subscription
    sub_stmt = select(Subscription).where(
        Subscription.user_id == user.id, Subscription.status == "active"
    )
    sub_result = await session.execute(sub_stmt)
    subscription = sub_result.scalar_one_or_none()

    if not user or not subscription:
        raise HTTPException(status_code=404, detail="No active subscription found")

    try:
        # Cancel the subscription in Stripe (at period end)
        stripe.Subscription.modify(
            subscription.stripe_subscription_id, cancel_at_period_end=True
        )

        return {
            "message": "Subscription will be cancelled at the end of the current period"
        }

    except stripe.error.StripeError as e:
        logger.error(f"Error cancelling subscription: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/create-portal-session")
async def create_billing_portal_session(
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
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

        customer_id = await _get_or_create_stripe_customer(user, session)

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
    session: AsyncSession = Depends(get_session),
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
            Subscription.user_id == user.id, Subscription.status == "active"
        )
        sub_result = await session.execute(sub_stmt)
        subscription = sub_result.scalar_one_or_none()

        if not subscription or not subscription.stripe_subscription_id:
            raise HTTPException(
                status_code=404, detail="No active subscription found to reactivate"
            )

        # Reactivate the subscription in Stripe
        stripe_subscription = stripe.Subscription.modify(
            subscription.stripe_subscription_id, cancel_at_period_end=False
        )

        logger.info(
            f"Reactivated subscription {subscription.stripe_subscription_id} for user {user.id}"
        )

        return {
            "message": "Subscription reactivated successfully",
            "subscription": {
                "id": subscription.id,
                "status": "active",
                "currentPeriodEnd": stripe_subscription.current_period_end,
            },
        }

    except stripe.error.StripeError as e:
        logger.error(f"Stripe error reactivating subscription: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error reactivating subscription: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
