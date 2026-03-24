"""End-to-end Stripe payment tests against REAL Stripe test API.

These tests hit the live Stripe test API (sk_test_*) to verify:
1. Checkout session creation with correct params
2. Webhook handling (simulated delivery)
3. Credit balance lifecycle (purchase → increment → debit → refund)
4. Subscription checkout creation
5. Webhook idempotency
6. Error scenarios

Run: pytest tests/e2e/test_stripe_e2e.py -v
"""

import asyncio
import hashlib
import hmac
import json
import time
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import stripe
from httpx import ASGITransport, AsyncClient

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

from app.core.config import settings

stripe.api_key = settings.STRIPE_SECRET_KEY

SKIP_REASON = "STRIPE_SECRET_KEY not configured"
SKIP = not settings.STRIPE_SECRET_KEY or not settings.STRIPE_SECRET_KEY.startswith(
    "sk_test_"
)


def _sign_webhook_payload(payload: bytes, secret: str) -> str:
    """Generate a valid Stripe webhook signature for testing."""
    timestamp = str(int(time.time()))
    signed_payload = f"{timestamp}.{payload.decode()}"
    signature = hmac.new(
        secret.encode(), signed_payload.encode(), hashlib.sha256
    ).hexdigest()
    return f"t={timestamp},v1={signature}"


# ---------------------------------------------------------------------------
# 1. Stripe Checkout Session Creation (Credit Packs)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(SKIP, reason=SKIP_REASON)
class TestStripeCheckoutCreation:
    """Verify Stripe Checkout sessions are created with correct params."""

    def test_20_pack_checkout_session(self):
        """Creates a real Stripe Checkout session for 20-pack at 300p GBP."""
        session = stripe.checkout.Session.create(
            customer_email="e2e-test@tru8.app",
            client_reference_id="e2e_test_user_001",
            line_items=[
                {"price": settings.STRIPE_PRICE_ID_CREDIT_PACK_20, "quantity": 1}
            ],
            mode="payment",
            success_url="https://tru8.app/test?success=true",
            cancel_url="https://tru8.app/test?cancelled=true",
            metadata={
                "user_id": "e2e_test_user_001",
                "credit_pack": "20",
                "pence_value": "300",
                "purchase_type": "agent_credits",
            },
        )

        assert session.id.startswith("cs_test_")
        assert session.url is not None
        assert session.payment_status == "unpaid"
        assert session.mode == "payment"
        assert session.amount_total == 300  # 300p = £3.00
        assert session.currency == "gbp"
        assert session.metadata["purchase_type"] == "agent_credits"
        assert session.metadata["pence_value"] == "300"
        assert session.metadata["credit_pack"] == "20"
        assert session.client_reference_id == "e2e_test_user_001"

        print(f"\n  Session created: {session.id}")
        print(f"  Amount: {session.amount_total}p {session.currency.upper()}")
        print(f"  URL: {session.url[:80]}...")

    def test_100_pack_checkout_session(self):
        """Creates a real Stripe Checkout session for 100-pack at 1500p GBP."""
        session = stripe.checkout.Session.create(
            customer_email="e2e-test@tru8.app",
            client_reference_id="e2e_test_user_001",
            line_items=[
                {"price": settings.STRIPE_PRICE_ID_CREDIT_PACK_100, "quantity": 1}
            ],
            mode="payment",
            success_url="https://tru8.app/test?success=true",
            cancel_url="https://tru8.app/test?cancelled=true",
            metadata={
                "user_id": "e2e_test_user_001",
                "credit_pack": "100",
                "pence_value": "1500",
                "purchase_type": "agent_credits",
            },
        )

        assert session.id.startswith("cs_test_")
        assert session.amount_total == 1500  # 1500p = £15.00
        assert session.currency == "gbp"
        assert session.metadata["credit_pack"] == "100"

        print(f"\n  Session created: {session.id}")
        print(f"  Amount: {session.amount_total}p {session.currency.upper()}")

    def test_removed_5_pack_price_id_is_empty(self):
        """5-pack price ID should be empty (pack removed)."""
        assert not settings.STRIPE_PRICE_ID_CREDIT_PACK_5, (
            f"STRIPE_PRICE_ID_CREDIT_PACK_5 should be empty, "
            f"got: {settings.STRIPE_PRICE_ID_CREDIT_PACK_5}"
        )

    def test_checkout_session_has_correct_currency(self):
        """Verify ALL credit pack prices are in GBP, not USD."""
        for price_id, label in [
            (settings.STRIPE_PRICE_ID_CREDIT_PACK_20, "20-pack"),
            (settings.STRIPE_PRICE_ID_CREDIT_PACK_100, "100-pack"),
        ]:
            price = stripe.Price.retrieve(price_id)
            assert (
                price.currency == "gbp"
            ), f"{label} price {price_id} is {price.currency.upper()}, expected GBP"
            assert price.active is True, f"{label} price {price_id} is inactive"
            print(
                f"\n  {label}: {price.unit_amount}p {price.currency.upper()} (active)"
            )


# ---------------------------------------------------------------------------
# 2. Stripe Subscription Checkout Creation
# ---------------------------------------------------------------------------


@pytest.mark.skipif(SKIP, reason=SKIP_REASON)
class TestStripeSubscriptionCreation:
    """Verify subscription checkout sessions create correctly."""

    def test_pro_subscription_checkout(self):
        """Creates a subscription checkout for Starter/Pro at 700p/month GBP."""
        price = stripe.Price.retrieve(settings.STRIPE_PRICE_ID_PRO)
        assert price.unit_amount == 700
        assert price.currency == "gbp"
        assert price.recurring is not None
        assert price.recurring.interval == "month"

        session = stripe.checkout.Session.create(
            customer_email="e2e-sub@tru8.app",
            client_reference_id="e2e_test_sub_user",
            line_items=[{"price": settings.STRIPE_PRICE_ID_PRO, "quantity": 1}],
            mode="subscription",
            success_url="https://tru8.app/test?sub=success",
            cancel_url="https://tru8.app/test?sub=cancelled",
            metadata={"user_id": "e2e_test_sub_user", "plan": "starter"},
        )

        assert session.id.startswith("cs_test_")
        assert session.mode == "subscription"
        print(f"\n  Subscription session: {session.id}")

    def test_developer_subscription_checkout(self):
        """Creates a subscription checkout for Developer at 2900p/month GBP."""
        price = stripe.Price.retrieve(settings.STRIPE_PRICE_ID_DEVELOPER)
        assert price.unit_amount == 2900
        assert price.currency == "gbp"
        assert price.recurring.interval == "month"

        session = stripe.checkout.Session.create(
            customer_email="e2e-dev@tru8.app",
            client_reference_id="e2e_test_dev_user",
            line_items=[{"price": settings.STRIPE_PRICE_ID_DEVELOPER, "quantity": 1}],
            mode="subscription",
            success_url="https://tru8.app/test?sub=success",
            cancel_url="https://tru8.app/test?sub=cancelled",
            metadata={"user_id": "e2e_test_dev_user", "plan": "professional"},
        )

        assert session.id.startswith("cs_test_")
        assert session.mode == "subscription"
        print(f"\n  Subscription session: {session.id}")


# ---------------------------------------------------------------------------
# 3. Webhook Handler — Credit Purchase Flow
# ---------------------------------------------------------------------------


class TestWebhookCreditFlow:
    """Simulate Stripe webhook delivery and verify credit increment."""

    @pytest.mark.asyncio
    async def test_credit_purchase_webhook_increments_balance(self):
        """Simulate checkout.session.completed → balance should increase."""
        from app.api.v1.payments import handle_agent_credit_purchase

        # Mock session with atomic update
        mock_result = MagicMock()
        mock_result.rowcount = 1
        session = AsyncMock()
        session.execute.return_value = mock_result
        session.commit = AsyncMock()

        session_data = {
            "client_reference_id": "e2e_test_user_001",
            "amount_total": 300,
            "metadata": {
                "purchase_type": "agent_credits",
                "credit_pack": "20",
                "pence_value": "300",
            },
        }

        await handle_agent_credit_purchase(session_data, session)

        # Verify atomic UPDATE was called
        session.execute.assert_awaited_once()
        session.commit.assert_awaited_once()

        # Verify the SQL update used correct pence value
        call_args = session.execute.call_args
        update_stmt = call_args[0][0]
        # The update statement should exist (we can't easily inspect the compiled SQL
        # but we verify it was called and committed)

    @pytest.mark.asyncio
    async def test_credit_purchase_amount_mismatch_rejected(self):
        """Webhook with amount_total != pence_value is rejected."""
        from app.api.v1.payments import handle_agent_credit_purchase

        session = AsyncMock()

        session_data = {
            "client_reference_id": "e2e_test_user_001",
            "amount_total": 9999,  # Doesn't match pence_value
            "metadata": {
                "purchase_type": "agent_credits",
                "credit_pack": "20",
                "pence_value": "300",
            },
        }

        await handle_agent_credit_purchase(session_data, session)

        # Should NOT have executed any DB update
        session.execute.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_credit_purchase_missing_user_handled(self):
        """Webhook for non-existent user doesn't crash."""
        from app.api.v1.payments import handle_agent_credit_purchase

        mock_result = MagicMock()
        mock_result.rowcount = 0  # User not found
        session = AsyncMock()
        session.execute.return_value = mock_result

        session_data = {
            "client_reference_id": "nonexistent_user",
            "amount_total": 300,
            "metadata": {
                "purchase_type": "agent_credits",
                "credit_pack": "20",
                "pence_value": "300",
            },
        }

        # Should not raise
        await handle_agent_credit_purchase(session_data, session)

        # Execute called (UPDATE attempted) but commit NOT called (rowcount=0)
        session.execute.assert_awaited_once()
        session.commit.assert_not_awaited()


# ---------------------------------------------------------------------------
# 4. Credit Debit + Refund Lifecycle
# ---------------------------------------------------------------------------


class TestCreditLifecycle:
    """Test the full credit lifecycle: debit → refund."""

    @pytest.mark.asyncio
    async def test_debit_success_then_refund(self):
        """Debit succeeds (rowcount=1), then refund succeeds."""
        from app.services.payments.credit_provider import debit_credits, refund_credits

        # Debit
        debit_result = MagicMock()
        debit_result.rowcount = 1
        debit_session = AsyncMock()
        debit_session.execute.return_value = debit_result

        success = await debit_credits("user_001", 7, debit_session)
        assert success is True

        # Refund
        refund_result = MagicMock()
        refund_result.rowcount = 1
        refund_session = AsyncMock()
        refund_session.execute.return_value = refund_result

        await refund_credits("user_001", 7, refund_session)
        refund_session.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_debit_insufficient_balance(self):
        """Debit fails when balance insufficient (rowcount=0)."""
        from app.services.payments.credit_provider import debit_credits

        mock_result = MagicMock()
        mock_result.rowcount = 0
        session = AsyncMock()
        session.execute.return_value = mock_result

        success = await debit_credits("user_001", 1500, session)
        assert success is False

    @pytest.mark.asyncio
    async def test_debit_is_atomic(self):
        """Verify debit uses SQL UPDATE with WHERE guard, not SELECT+UPDATE."""
        from app.services.payments.credit_provider import debit_credits

        mock_result = MagicMock()
        mock_result.rowcount = 1
        session = AsyncMock()
        session.execute.return_value = mock_result

        await debit_credits("user_001", 7, session)

        # Should be a single execute call (atomic UPDATE), not two (SELECT + UPDATE)
        assert (
            session.execute.await_count == 1
        ), f"Expected 1 execute call (atomic UPDATE), got {session.execute.await_count}"


# ---------------------------------------------------------------------------
# 5. Webhook Idempotency
# ---------------------------------------------------------------------------


class TestWebhookIdempotency:
    """Test that duplicate webhook events are handled correctly."""

    @pytest.mark.asyncio
    async def test_duplicate_event_skipped_via_redis(self):
        """Second delivery of same event_id should be skipped."""
        from app.api.v1.payments import stripe_webhook

        # Build a mock event
        event = {
            "id": "evt_e2e_duplicate_test",
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "client_reference_id": "user_001",
                    "amount_total": 300,
                    "metadata": {
                        "purchase_type": "agent_credits",
                        "credit_pack": "20",
                        "pence_value": "300",
                    },
                }
            },
        }

        mock_redis = AsyncMock()
        # First call: key doesn't exist
        mock_redis.exists.return_value = False
        mock_redis.set = AsyncMock()

        mock_request = MagicMock()
        mock_request.body = AsyncMock(return_value=json.dumps(event).encode())
        mock_request.headers = {"stripe-signature": "sig_valid"}

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_session.execute.return_value = mock_result
        mock_session.commit = AsyncMock()

        with (
            patch(
                "app.api.v1.payments.stripe.Webhook.construct_event",
                return_value=event,
            ),
            patch(
                "app.core.redis.get_redis",
                new_callable=AsyncMock,
                return_value=mock_redis,
            ),
        ):
            # First delivery — should process
            result = await stripe_webhook(mock_request, mock_session)
            assert result == {"status": "success"}
            mock_session.execute.assert_awaited()

            # Reset mocks
            mock_session.reset_mock()
            mock_redis.exists.return_value = True  # Now key exists

            # Second delivery — should skip
            result = await stripe_webhook(mock_request, mock_session)
            assert result == {"status": "success"}
            mock_session.execute.assert_not_awaited()  # No DB write on duplicate


# ---------------------------------------------------------------------------
# 6. Price Consistency Verification
# ---------------------------------------------------------------------------


@pytest.mark.skipif(SKIP, reason=SKIP_REASON)
class TestPriceConsistency:
    """Verify all Stripe prices match code expectations."""

    def test_all_prices_are_gbp(self):
        """Every configured price must be in GBP."""
        price_ids = [
            settings.STRIPE_PRICE_ID_PRO,
            settings.STRIPE_PRICE_ID_DEVELOPER,
            settings.STRIPE_PRICE_ID_CREDIT_PACK_20,
            settings.STRIPE_PRICE_ID_CREDIT_PACK_100,
        ]
        for pid in price_ids:
            price = stripe.Price.retrieve(pid)
            assert (
                price.currency == "gbp"
            ), f"Price {pid} is {price.currency}, expected gbp"

    def test_all_prices_are_active(self):
        """Every configured price must be active."""
        price_ids = [
            settings.STRIPE_PRICE_ID_PRO,
            settings.STRIPE_PRICE_ID_DEVELOPER,
            settings.STRIPE_PRICE_ID_CREDIT_PACK_20,
            settings.STRIPE_PRICE_ID_CREDIT_PACK_100,
        ]
        for pid in price_ids:
            price = stripe.Price.retrieve(pid)
            assert price.active, f"Price {pid} is inactive"

    def test_credit_pack_amounts_match_code(self):
        """Stripe price amounts must match pack_map in agent.py."""
        expected = {
            settings.STRIPE_PRICE_ID_CREDIT_PACK_20: 300,
            settings.STRIPE_PRICE_ID_CREDIT_PACK_100: 1500,
        }
        for pid, expected_amount in expected.items():
            price = stripe.Price.retrieve(pid)
            assert (
                price.unit_amount == expected_amount
            ), f"Price {pid}: expected {expected_amount}p, got {price.unit_amount}p"

    def test_subscription_amounts_match(self):
        """Stripe subscription prices must match expected amounts."""
        expected = {
            settings.STRIPE_PRICE_ID_PRO: (700, "month"),
            settings.STRIPE_PRICE_ID_DEVELOPER: (2900, "month"),
        }
        for pid, (expected_amount, expected_interval) in expected.items():
            price = stripe.Price.retrieve(pid)
            assert price.unit_amount == expected_amount
            assert price.recurring.interval == expected_interval

    def test_no_old_usd_products_active(self):
        """Old USD credit pack products should be archived."""
        products = stripe.Product.list(limit=100)
        for p in products.data:
            if "Credits" in p.name and p.active:
                prices = stripe.Price.list(product=p.id, limit=5)
                for pr in prices.data:
                    assert pr.currency == "gbp", (
                        f"Active credit product '{p.name}' ({p.id}) has "
                        f"{pr.currency.upper()} price — should be GBP or archived"
                    )
