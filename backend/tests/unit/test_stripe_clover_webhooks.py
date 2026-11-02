"""Subscription webhooks work with the endpoint's API version (clover).

The live webhook (`we_1TEtiA`) sends 2025-09-30.clover payloads. Basil
(2025-03-31) removed `invoice.subscription` (now
`invoice.parent.subscription_details.subscription`) and subscription-level
`current_period_start/end` (now on items). So, before 2026-11-02:
- `invoice.paid` and `invoice.payment_failed` skipped every renewal as a
  "non-subscription invoice" — a failed renewal never marked past_due;
- `customer.subscription.updated` raised KeyError on every event — status
  and plan changes never landed.
The SDK pins its own requests to 2024-06-20, which still has the old fields.
Real ORM session (aiosqlite).
"""

from datetime import datetime

import pytest
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker

from app.api.v1 import payments
from app.models.user import Subscription, User


@compiles(JSONB, "sqlite")
def _jsonb_as_json_on_sqlite(type_, compiler, **kw):  # test-only DDL shim
    return "JSON"


@pytest.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(lambda c: User.__table__.create(c))
        await conn.run_sync(lambda c: Subscription.__table__.create(c))
    maker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as s:
        s.add(User(id="user_a", email="a@example.com"))
        s.add(
            Subscription(
                id="row1",
                user_id="user_a",
                plan="console",
                status="active",
                credits_per_month=200,
                credits_remaining=10,
                current_period_start=datetime(2026, 10, 1),
                current_period_end=datetime(2026, 11, 1),
                stripe_subscription_id="sub_1",
                stripe_customer_id="cus_1",
            )
        )
        await s.commit()
        yield s
    await engine.dispose()


# What the SDK (2024-06-20) returns for Subscription.retrieve — the old shape.
SDK_SUBSCRIPTION = {
    "id": "sub_1",
    "status": "active",
    "current_period_start": int(datetime(2026, 11, 1).timestamp()),
    "current_period_end": int(datetime(2026, 12, 1).timestamp()),
    "items": {
        "data": [{"price": {"id": "price_x", "recurring": {"interval": "month"}}}]
    },
}

# What the clover webhook sends: subscription under `parent`, no top-level field.
CLOVER_INVOICE = {
    "id": "in_1",
    "object": "invoice",
    "parent": {
        "type": "subscription_details",
        "subscription_details": {"subscription": "sub_1"},
    },
}


@pytest.fixture
def sdk(monkeypatch):
    calls = []

    def retrieve(sub_id):
        calls.append(sub_id)
        return dict(SDK_SUBSCRIPTION, id=sub_id)

    monkeypatch.setattr(payments.stripe.Subscription, "retrieve", retrieve)
    return calls


async def _sub(session):
    return await session.get(Subscription, "row1")


async def test_renewal_in_clover_format_is_processed(session, sdk):
    await payments.handle_invoice_paid(dict(CLOVER_INVOICE), session)
    sub = await _sub(session)
    assert sub.current_period_start.date() == datetime(2026, 11, 1).date()
    assert sub.credits_remaining == 200
    assert sdk == ["sub_1"]


async def test_failed_renewal_in_clover_format_marks_past_due(session):
    await payments.handle_invoice_payment_failed(dict(CLOVER_INVOICE), session)
    assert (await _sub(session)).status == "past_due"


async def test_status_change_in_clover_format_lands(session, sdk, monkeypatch):
    """The clover payload has no current_period_start; this used to KeyError."""
    monkeypatch.setattr(
        payments.stripe.Subscription,
        "retrieve",
        lambda i: dict(SDK_SUBSCRIPTION, id=i, status="past_due"),
    )
    clover_subscription = {
        "id": "sub_1",
        "object": "subscription",
        "status": "past_due",
    }
    await payments.handle_subscription_updated(clover_subscription, session)
    assert (await _sub(session)).status == "past_due"


def test_old_format_invoice_still_maps():
    assert payments._invoice_subscription_id({"subscription": "sub_9"}) == "sub_9"


def test_expanded_subscription_object_maps():
    inv = {"parent": {"subscription_details": {"subscription": {"id": "sub_7"}}}}
    assert payments._invoice_subscription_id(inv) == "sub_7"


def test_one_off_invoice_maps_to_nothing():
    assert (
        payments._invoice_subscription_id({"parent": {"type": "quote_details"}}) is None
    )
    assert payments._invoice_subscription_id({}) is None


async def test_unknown_subscription_makes_no_stripe_call(session, sdk):
    await payments.handle_subscription_updated({"id": "sub_unknown"}, session)
    assert sdk == []


async def test_stripe_outage_on_renewal_raises_so_stripe_retries(session, monkeypatch):
    """It used to log and return, so the webhook answered 200 and the renewal
    (period roll-forward + allowance reset) was silently lost."""

    def down(sub_id):
        raise payments.stripe.error.APIConnectionError("stripe unreachable")

    monkeypatch.setattr(payments.stripe.Subscription, "retrieve", down)
    with pytest.raises(payments.stripe.error.StripeError):
        await payments.handle_invoice_paid(dict(CLOVER_INVOICE), session)
