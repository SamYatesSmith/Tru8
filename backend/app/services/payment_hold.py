"""Payment hold: an account with an open Stripe dispute cannot spend.

Founder decision 2026-11-02 (option A, then A again on the review): a
DISPUTE pauses new checks, re-searches, comparisons, agent prepaid-credit
spending and new purchases until Stripe resolves it in our favour or the
founder releases it. A full refund does not hold the account; it cancels the
refunded subscription instead (payments.handle_charge_refunded).

Design + review: audit/2026-11-02_payment_hold_design.md.

- State: one ``PaymentDispute`` row per Stripe dispute id. Held while ANY row
  for the user has a status outside ``RESOLVED_STATUSES``. Each dispute is
  tracked on its own, so an escalated inquiry (a NEW dispute on the same
  charge) or a second disputed charge can never be lifted by another
  dispute's close event, and arrival order does not matter: every event
  re-reads the dispute's CURRENT status from Stripe and upserts it.
- Reading existing checks and reports is never blocked: a hold stops
  spending, not access to what was already paid for.
- The refusal is a 403 with plain text that the web client shows verbatim
  (it contains none of the words its error branches match on: "403",
  "limit", "closed beta"), so a held user is never told to buy more.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Optional

import stripe
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.payment_dispute import PaymentDispute
from app.models.user import Subscription

logger = logging.getLogger(__name__)

# Statuses that end a hold. "won": Stripe found for us. "warning_closed": an
# inquiry closed with no funds moved (if it escalated, the chargeback is a
# separate dispute that holds on its own). "released": the founder lifted it.
# "prevented": refunded before it became a chargeback — a refund, which by the
# founder's rule (2026-11-02) cancels rather than holds.
RESOLVED_STATUSES = frozenset({"won", "warning_closed", "prevented", "released"})

HOLD_MESSAGE = (
    "This account is paused while a payment dispute is reviewed. "
    "Please contact support@trueight.com."
)


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _get(obj: Any, key: str, default=None):
    """Stripe objects and plain dicts (tests, webhook payloads) alike."""
    if obj is None:
        return default
    try:
        value = obj.get(key, default)
    except AttributeError:
        value = getattr(obj, key, default)
    return default if value is None else value


async def has_payment_hold(session: AsyncSession, user_id: str) -> bool:
    result = await session.execute(
        select(PaymentDispute.id)
        .where(
            PaymentDispute.user_id == user_id,
            PaymentDispute.status.notin_(RESOLVED_STATUSES),
        )
        .limit(1)
    )
    return result.first() is not None


async def assert_no_payment_hold(session: AsyncSession, user_id: str) -> None:
    """Raise 403 (plain text) when the account is on payment hold."""
    if user_id and await has_payment_hold(session, user_id):
        logger.info(f"[PAYMENT HOLD] refused spend for user={user_id}")
        raise HTTPException(status_code=403, detail=HOLD_MESSAGE)


async def resolve_user_for_charge(session: AsyncSession, charge: Any) -> Optional[str]:
    """Which Tru8 user paid this charge.

    1. The Checkout Session that took the payment: ``client_reference_id``
       (set to the user id on every checkout we create) or
       ``metadata.user_id``. Covers credit packs, which are paid WITHOUT a
       Stripe Customer — the old customer-only lookup never found them.
    2. The invoice's subscription, matched to our Subscription row.
    3. The charge's customer, matched to a Subscription row.
    """
    payment_intent = _get(charge, "payment_intent")
    if payment_intent:
        sessions = stripe.checkout.Session.list(payment_intent=payment_intent, limit=1)
        for cs in _get(sessions, "data", []) or []:
            user_id = _get(cs, "client_reference_id") or _get(
                _get(cs, "metadata", {}), "user_id"
            )
            if user_id:
                return user_id

    invoice_id = _get(charge, "invoice")
    if invoice_id:
        invoice = stripe.Invoice.retrieve(invoice_id)
        sub_id = _get(invoice, "subscription")
        if sub_id:
            row = (
                await session.execute(
                    select(Subscription.user_id).where(
                        Subscription.stripe_subscription_id == sub_id
                    )
                )
            ).first()
            if row:
                return row[0]

    customer_id = _get(charge, "customer")
    if customer_id:
        row = (
            await session.execute(
                select(Subscription.user_id).where(
                    Subscription.stripe_customer_id == customer_id
                )
            )
        ).first()
        if row:
            return row[0]
    return None


async def record_dispute(session: AsyncSession, dispute_event_obj: Any) -> None:
    """Upsert one dispute from any charge.dispute.* event.

    Re-reads the dispute from Stripe so the stored status is the CURRENT one
    whatever order events arrive in. Raises on any failure so the webhook
    returns 500 and Stripe retries (a lost dispute event is a lost hold).
    """
    dispute_id = _get(dispute_event_obj, "id")
    if not dispute_id:
        raise ValueError("dispute event without an id")
    dispute = stripe.Dispute.retrieve(dispute_id)
    status = _get(dispute, "status", "unknown")
    charge_id = _get(dispute, "charge")
    if not isinstance(charge_id, str):
        charge_id = _get(charge_id, "id")

    row = await session.get(PaymentDispute, dispute_id)
    if row is None:
        charge = stripe.Charge.retrieve(charge_id)
        user_id = await resolve_user_for_charge(session, charge)
        if not user_id:
            # The one failure that must be SEEN: a dispute we cannot place.
            logger.error(
                f"[PAYMENT HOLD] UNMAPPED dispute {dispute_id} on charge "
                f"{charge_id} — no Tru8 user found; hold NOT placed"
            )
            try:
                import sentry_sdk

                sentry_sdk.capture_message(
                    f"Unmapped Stripe dispute {dispute_id}", level="error"
                )
            except Exception:
                pass
            return
        row = PaymentDispute(
            id=dispute_id,
            user_id=user_id,
            charge_id=charge_id,
            status=status,
            reason=_get(dispute, "reason"),
            amount=int(_get(dispute, "amount", 0) or 0),
            currency=_get(dispute, "currency"),
        )
        session.add(row)
        action = (
            "set" if status not in RESOLVED_STATUSES else "noted (already resolved)"
        )
        logger.warning(
            f"[PAYMENT HOLD] {action} user={user_id} dispute={dispute_id} "
            f"charge={charge_id} status={status}"
        )
        if status not in RESOLVED_STATUSES:
            _notify_founder(user_id, dispute_id, charge_id, status)
    else:
        if row.status == "released":
            return  # the founder's decision stands over later Stripe noise
        if row.status != status:
            logger.warning(
                f"[PAYMENT HOLD] dispute {dispute_id} user={row.user_id} "
                f"{row.status} -> {status}"
            )
        row.status = status
        row.updated_at = _now()
    await session.commit()


def _notify_founder(user_id: str, dispute_id: str, charge_id: str, status: str) -> None:
    """Best-effort email to the founder; never blocks the hold."""
    try:
        import html

        import resend

        from app.core.config import settings

        if not settings.RESEND_API_KEY:
            return
        resend.api_key = settings.RESEND_API_KEY
        to = getattr(settings, "FEEDBACK_EMAIL", None) or settings.EMAIL_FROM_ADDRESS
        e = html.escape
        resend.Emails.send(
            {
                "from": f"Tru8 Payments <{settings.EMAIL_FROM_ADDRESS}>",
                "to": [to],
                "subject": "[Tru8] Payment dispute: account paused",
                "html": (
                    f"<p>A Stripe dispute paused account <code>{e(user_id)}</code>.</p>"
                    f"<p>Dispute <code>{e(dispute_id)}</code> on charge "
                    f"<code>{e(charge_id)}</code>, status <b>{e(status)}</b>.</p>"
                    "<p>It lifts automatically if the dispute is won. To lift it "
                    "yourself: <code>python -m scripts.payment_hold release "
                    f"{e(dispute_id)}</code></p>"
                ),
            }
        )
    except Exception as exc:
        logger.warning(f"[PAYMENT HOLD] founder email failed: {type(exc).__name__}")
