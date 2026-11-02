"""Payment hold on an open Stripe dispute (security sweep #1, 2026-11-02).

Design + review: audit/2026-11-02_payment_hold_design.md. Founder: a
DISPUTE pauses spending (checks, re-search, comparisons, agent credits, new
purchases) until it is won or released; a full refund cancels the refunded
subscription instead. Real ORM session (aiosqlite): mocked sessions have hidden
ORM bugs in this codebase before.
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker

from app.models.payment_dispute import PaymentDispute
from app.models.user import Subscription, User
from app.services import payment_hold as ph


@compiles(JSONB, "sqlite")
def _jsonb_as_json_on_sqlite(type_, compiler, **kw):  # test-only DDL shim
    return "JSON"


@pytest.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(lambda c: User.__table__.create(c))
        await conn.run_sync(lambda c: Subscription.__table__.create(c))
        await conn.run_sync(lambda c: PaymentDispute.__table__.create(c))
    maker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as s:
        s.add(User(id="user_alice", email="alice@example.com"))
        s.add(User(id="user_bob", email="bob@example.com"))
        await s.commit()
        yield s
    await engine.dispose()


class _Stripe:
    """Programmable stand-in for the four Stripe reads the hold makes."""

    def __init__(self):
        self.disputes = {}  # id -> status
        self.dispute_charge = {}  # id -> charge id
        self.charges = {}  # id -> charge dict
        self.sessions = {}  # payment_intent -> client_reference_id

    def install(self, monkeypatch):
        s = self
        monkeypatch.setattr(
            ph.stripe.Dispute,
            "retrieve",
            lambda i: {
                "id": i,
                "status": s.disputes[i],
                "charge": s.dispute_charge[i],
                "amount": 300,
                "currency": "gbp",
                "reason": "fraudulent",
            },
        )
        monkeypatch.setattr(ph.stripe.Charge, "retrieve", lambda i: s.charges[i])
        monkeypatch.setattr(
            ph.stripe.checkout.Session,
            "list",
            lambda payment_intent, limit=1: {
                "data": (
                    [{"client_reference_id": s.sessions[payment_intent]}]
                    if payment_intent in s.sessions
                    else []
                )
            },
        )
        monkeypatch.setattr(
            ph.stripe.Invoice, "retrieve", lambda i: {"id": i, "subscription": None}
        )
        monkeypatch.setattr(ph, "_notify_founder", lambda *a: None)


@pytest.fixture
def stripe_fake(monkeypatch):
    f = _Stripe()
    f.install(monkeypatch)
    # A credit-pack charge: paid through Checkout WITHOUT a Stripe Customer.
    f.charges["ch_pack"] = {
        "id": "ch_pack",
        "payment_intent": "pi_pack",
        "customer": None,
    }
    f.sessions["pi_pack"] = "user_alice"
    return f


async def _event(session, f, dispute_id, status, charge="ch_pack"):
    f.disputes[dispute_id] = status
    f.dispute_charge[dispute_id] = charge
    await ph.record_dispute(session, {"id": dispute_id})


# --- setting and lifting ------------------------------------------------------


async def test_credit_pack_dispute_places_a_hold(session, stripe_fake):
    """Review BLOCKER: pack charges have no Customer, so the old
    customer-only lookup never found the user."""
    await _event(session, stripe_fake, "dp_1", "needs_response")
    assert await ph.has_payment_hold(session, "user_alice")
    assert not await ph.has_payment_hold(session, "user_bob")


async def test_won_dispute_lifts_the_hold(session, stripe_fake):
    await _event(session, stripe_fake, "dp_1", "needs_response")
    await _event(session, stripe_fake, "dp_1", "won")
    assert not await ph.has_payment_hold(session, "user_alice")


async def test_lost_dispute_keeps_the_hold(session, stripe_fake):
    await _event(session, stripe_fake, "dp_1", "needs_response")
    await _event(session, stripe_fake, "dp_1", "lost")
    assert await ph.has_payment_hold(session, "user_alice")


async def test_escalated_inquiry_cannot_lift_the_chargeback(session, stripe_fake):
    """Review HIGH: an inquiry that escalates closes as warning_closed and a
    NEW dispute opens on the same charge. The inquiry's close must not lift
    the chargeback's hold, in either arrival order."""
    await _event(session, stripe_fake, "dp_inquiry", "warning_needs_response")
    await _event(session, stripe_fake, "dp_charge", "needs_response")
    await _event(session, stripe_fake, "dp_inquiry", "warning_closed")
    assert await ph.has_payment_hold(session, "user_alice")


async def test_close_arriving_before_create_does_not_strand_a_hold(
    session, stripe_fake
):
    """Review HIGH: every event re-reads the dispute's CURRENT status."""
    stripe_fake.disputes["dp_1"] = "won"
    stripe_fake.dispute_charge["dp_1"] = "ch_pack"
    await ph.record_dispute(session, {"id": "dp_1"})  # the 'closed' event
    await ph.record_dispute(session, {"id": "dp_1"})  # the late 'created'
    assert not await ph.has_payment_hold(session, "user_alice")


async def test_a_second_disputed_charge_holds_independently(session, stripe_fake):
    stripe_fake.charges["ch_two"] = {"id": "ch_two", "payment_intent": "pi_two"}
    stripe_fake.sessions["pi_two"] = "user_alice"
    await _event(session, stripe_fake, "dp_1", "needs_response")
    await _event(session, stripe_fake, "dp_2", "needs_response", charge="ch_two")
    await _event(session, stripe_fake, "dp_1", "won")
    assert await ph.has_payment_hold(session, "user_alice")


async def test_founder_release_survives_later_stripe_events(session, stripe_fake):
    await _event(session, stripe_fake, "dp_1", "needs_response")
    row = await session.get(PaymentDispute, "dp_1")
    row.status = "released"
    await session.commit()
    await _event(session, stripe_fake, "dp_1", "under_review")
    assert not await ph.has_payment_hold(session, "user_alice")


async def test_subscription_charge_maps_through_the_invoice(
    session, stripe_fake, monkeypatch
):
    session.add(
        Subscription(
            id="sub_row",
            user_id="user_bob",
            plan="console",
            credits_per_month=200,
            credits_remaining=200,
            current_period_start=__import__("datetime").datetime(2026, 11, 1),
            current_period_end=__import__("datetime").datetime(2026, 12, 1),
            stripe_subscription_id="sub_123",
        )
    )
    await session.commit()
    monkeypatch.setattr(
        ph.stripe.Invoice, "retrieve", lambda i: {"id": i, "subscription": "sub_123"}
    )
    stripe_fake.charges["ch_sub"] = {
        "id": "ch_sub",
        "payment_intent": "pi_sub",
        "invoice": "in_1",
    }
    await _event(session, stripe_fake, "dp_sub", "needs_response", charge="ch_sub")
    assert await ph.has_payment_hold(session, "user_bob")


async def test_unmapped_dispute_is_reported_not_silently_dropped(
    session, stripe_fake, caplog
):
    stripe_fake.charges["ch_orphan"] = {"id": "ch_orphan"}
    with caplog.at_level("ERROR"):
        await _event(session, stripe_fake, "dp_x", "needs_response", charge="ch_orphan")
    assert any("UNMAPPED" in r.getMessage() for r in caplog.records)


async def test_stripe_failure_raises_so_the_webhook_is_retried(session, monkeypatch):
    def boom(i):
        raise RuntimeError("stripe down")

    monkeypatch.setattr(ph.stripe.Dispute, "retrieve", boom)
    with pytest.raises(RuntimeError):
        await ph.record_dispute(session, {"id": "dp_1"})


# --- enforcement ---------------------------------------------------------------


async def _hold(session, user_id="user_alice"):
    session.add(
        PaymentDispute(
            id="dp_h", user_id=user_id, charge_id="ch", status="needs_response"
        )
    )
    await session.commit()


async def test_dashboard_gate_refuses_a_held_admin_too(session, monkeypatch):
    from app.core.config import settings
    from app.services import usage_ledger

    await _hold(session)
    monkeypatch.setattr(settings, "ADMIN_EMAILS", ["alice@example.com"])
    user = await session.get(User, "user_alice")
    with pytest.raises(HTTPException) as exc:
        await usage_ledger.enforce_usage_limit(session, user)
    assert exc.value.status_code == 403
    assert exc.value.detail == ph.HOLD_MESSAGE


async def test_unheld_user_passes_the_gate(session, monkeypatch):
    from app.core.config import settings
    from app.services import usage_ledger

    monkeypatch.setattr(settings, "ADMIN_EMAILS", ["alice@example.com"])
    user = await session.get(User, "user_alice")
    assert (await usage_ledger.enforce_usage_limit(session, user)).id == "user_alice"


async def test_agent_prepaid_credits_are_frozen_before_any_debit(session):
    from app.core.agent_auth import AgentPaymentContext

    await _hold(session)
    ctx = AgentPaymentContext(
        provider="credit", payer_id="user_alice", user_id="user_alice", session=session
    )
    with patch(
        "app.services.payments.credit_provider.debit_credits", new=AsyncMock()
    ) as debit:
        with pytest.raises(HTTPException) as exc:
            await ctx.charge(7, "quick", "test")
    assert exc.value.status_code == 403
    debit.assert_not_called()


def test_hold_message_is_shown_verbatim_by_the_web_client():
    """web/app/dashboard/new-check/page.tsx routes errors containing '403',
    'closed beta' or 'limit' to the beta-waitlist / upgrade prompts."""
    m = ph.HOLD_MESSAGE.lower()
    assert "403" not in m and "closed beta" not in m and "limit" not in m
    assert "upgrade" not in m and "credit" not in m


# --- webhook plumbing ----------------------------------------------------------


async def test_full_refund_of_a_subscription_payment_cancels_it(monkeypatch):
    """The webhook payload (clover) has NO `invoice`: the handler must read
    the charge back through the SDK (verifier HIGH, 2026-11-02)."""
    from app.api.v1 import payments

    monkeypatch.setattr(payments, "_revoke_credits_for_charge", AsyncMock())
    monkeypatch.setattr(
        payments.stripe.Charge, "retrieve", lambda i: {"id": i, "invoice": "in_9"}
    )
    monkeypatch.setattr(
        payments.stripe.Invoice, "retrieve", lambda i: {"subscription": "sub_9"}
    )
    monkeypatch.setattr(
        payments.stripe.Subscription, "retrieve", lambda i: {"status": "active"}
    )
    cancel = MagicMock()
    monkeypatch.setattr(payments.stripe.Subscription, "cancel", cancel)
    s = SimpleNamespace(commit=AsyncMock())
    clover_payload = {"id": "ch", "refunded": True}  # no `invoice` key
    await payments.handle_charge_refunded(clover_payload, s)
    cancel.assert_called_once_with("sub_9")


async def test_already_cancelled_subscription_is_left_alone(monkeypatch):
    from app.api.v1 import payments

    monkeypatch.setattr(payments, "_revoke_credits_for_charge", AsyncMock())
    monkeypatch.setattr(
        payments.stripe.Charge, "retrieve", lambda i: {"invoice": "in_9"}
    )
    monkeypatch.setattr(
        payments.stripe.Invoice, "retrieve", lambda i: {"subscription": "sub_9"}
    )
    monkeypatch.setattr(
        payments.stripe.Subscription, "retrieve", lambda i: {"status": "canceled"}
    )
    cancel = MagicMock()
    monkeypatch.setattr(payments.stripe.Subscription, "cancel", cancel)
    await payments.handle_charge_refunded(
        {"id": "ch", "refunded": True}, SimpleNamespace(commit=AsyncMock())
    )
    cancel.assert_not_called()


async def test_credit_pack_refund_cancels_nothing(monkeypatch):
    from app.api.v1 import payments

    monkeypatch.setattr(payments, "_revoke_credits_for_charge", AsyncMock())
    monkeypatch.setattr(payments.stripe.Charge, "retrieve", lambda i: {"invoice": None})
    cancel = MagicMock()
    monkeypatch.setattr(payments.stripe.Subscription, "cancel", cancel)
    await payments.handle_charge_refunded(
        {"id": "ch", "refunded": True}, SimpleNamespace(commit=AsyncMock())
    )
    cancel.assert_not_called()


async def test_partial_refund_does_not_cancel(monkeypatch):
    from app.api.v1 import payments

    monkeypatch.setattr(payments, "_revoke_credits_for_charge", AsyncMock())
    cancel = MagicMock()
    monkeypatch.setattr(payments.stripe.Subscription, "cancel", cancel)
    s = SimpleNamespace(commit=AsyncMock())
    await payments.handle_charge_refunded({"id": "ch", "refunded": False}, s)
    cancel.assert_not_called()


async def test_prevented_dispute_does_not_hold(session, stripe_fake):
    await _event(session, stripe_fake, "dp_p", "prevented")
    assert not await ph.has_payment_hold(session, "user_alice")


async def test_held_user_sees_the_hold_message_at_checkout_not_a_500(monkeypatch):
    """Verifier MEDIUM: the 403 used to be caught by `except Exception` and
    returned as a 500 "Internal server error"."""
    from app.api.v1 import payments

    answers = iter(
        [
            SimpleNamespace(
                scalar_one_or_none=lambda: SimpleNamespace(
                    id="user_alice", email="a@b.co"
                )
            ),  # the user row
            SimpleNamespace(scalar_one_or_none=lambda: None),  # no active sub
        ]
    )

    class _S:
        async def execute(self, *a, **k):
            return next(answers)

    async def _held(session, user_id):
        raise HTTPException(status_code=403, detail=ph.HOLD_MESSAGE)

    monkeypatch.setattr(ph, "assert_no_payment_hold", _held)
    req = SimpleNamespace(price_id="price_console", plan="console")
    with pytest.raises(HTTPException) as exc:
        await payments.create_checkout_session(req, {"id": "user_alice"}, _S())
    assert exc.value.status_code == 403
    assert exc.value.detail == ph.HOLD_MESSAGE


async def test_failed_handler_releases_the_dedupe_claim(monkeypatch):
    """Review HIGH: the key was written before the handler ran, so Stripe's
    retry of a failed event was skipped as a duplicate — the event was lost."""
    from app.api.v1 import payments

    store = {}

    class _R:
        async def exists(self, k):
            return k in store

        async def set(self, k, v, ex=None):
            store[k] = v

        async def delete(self, k):
            store.pop(k, None)

    async def _get_redis():
        return _R()

    monkeypatch.setattr("app.core.redis.get_redis", _get_redis)
    monkeypatch.setattr(
        payments.stripe.Webhook,
        "construct_event",
        lambda p, s, k: {
            "id": "evt_1",
            "type": "charge.dispute.created",
            "data": {"object": {"id": "dp_1"}},
        },
    )

    async def _fail(*a, **k):
        raise RuntimeError("transient")

    monkeypatch.setattr(payments, "handle_charge_dispute", _fail)
    req = SimpleNamespace(
        body=AsyncMock(return_value=b"{}"), headers={"stripe-signature": "t"}
    )
    with pytest.raises(HTTPException) as exc:
        await payments.stripe_webhook(req, session=None)
    assert exc.value.status_code == 500
    assert "stripe_event:evt_1" not in store  # the retry will be processed
