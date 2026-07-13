"""Track L hardening: tests for stripe_webhook() in payments.py.

Verifies routing to handle_agent_credit_purchase vs handle_successful_payment,
and error handling for invalid payload/signature.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import HTTPException


@pytest.fixture
def mock_session():
    return AsyncMock()


def _make_request(body: bytes, sig: str = "sig_valid") -> MagicMock:
    """Build a minimal mock Request."""
    req = MagicMock()
    req.body = AsyncMock(return_value=body)
    req.headers = {"stripe-signature": sig}
    return req


class TestStripeWebhook:
    """Tests for stripe_webhook() endpoint."""

    @pytest.mark.asyncio
    @patch("app.core.redis.get_redis", new_callable=AsyncMock, return_value=None)
    @patch("app.api.v1.payments.handle_agent_credit_purchase", new_callable=AsyncMock)
    @patch("app.api.v1.payments.stripe.Webhook.construct_event")
    async def test_agent_credit_purchase_routing(
        self, mock_construct, mock_handle_agent, mock_get_redis, mock_session
    ):
        """checkout.session.completed with purchase_type=agent_credits routes to agent handler."""
        from app.api.v1.payments import stripe_webhook

        mock_construct.return_value = {
            "id": "evt_test_agent_credit",
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "client_reference_id": "user_1",
                    "metadata": {
                        "purchase_type": "agent_credits",
                        "pence_value": "300",
                        "credit_pack": "20",
                    },
                }
            },
        }

        request = _make_request(b'{"test": true}')
        result = await stripe_webhook(request, mock_session)

        assert result == {"status": "success"}
        mock_handle_agent.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.core.redis.get_redis", new_callable=AsyncMock, return_value=None)
    @patch("app.api.v1.payments.handle_successful_payment", new_callable=AsyncMock)
    @patch("app.api.v1.payments.stripe.Webhook.construct_event")
    async def test_subscription_payment_routing(
        self, mock_construct, mock_handle_payment, mock_get_redis, mock_session
    ):
        """checkout.session.completed without agent meta routes to subscription handler."""
        from app.api.v1.payments import stripe_webhook

        mock_construct.return_value = {
            "id": "evt_test_subscription",
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "client_reference_id": "user_1",
                    "subscription": "sub_abc",
                    "metadata": {"user_id": "user_1", "plan": "starter"},
                }
            },
        }

        request = _make_request(b'{"test": true}')
        result = await stripe_webhook(request, mock_session)

        assert result == {"status": "success"}
        mock_handle_payment.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.api.v1.payments.stripe.Webhook.construct_event")
    async def test_invalid_signature_returns_400(self, mock_construct, mock_session):
        """Invalid Stripe signature raises HTTPException 400."""
        import stripe

        from app.api.v1.payments import stripe_webhook

        mock_construct.side_effect = stripe.error.SignatureVerificationError(
            "bad sig", "sig_header"
        )

        request = _make_request(b'{"test": true}', sig="sig_invalid")

        with pytest.raises(HTTPException) as exc_info:
            await stripe_webhook(request, mock_session)

        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    @patch("app.api.v1.payments.stripe.Webhook.construct_event")
    async def test_invalid_payload_returns_400(self, mock_construct, mock_session):
        """Invalid payload raises HTTPException 400."""
        from app.api.v1.payments import stripe_webhook

        mock_construct.side_effect = ValueError("bad payload")

        request = _make_request(b"not json")

        with pytest.raises(HTTPException) as exc_info:
            await stripe_webhook(request, mock_session)

        assert exc_info.value.status_code == 400


class TestConsolePriceMapping:
    """Console tier (2026-07): both price IDs map to ("console", 200);
    unknown / unset price IDs must fail closed."""

    def test_plan_from_console_monthly(self):
        from app.api.v1.payments import _plan_from_price_id
        from app.core.config import settings

        with patch.object(settings, "STRIPE_PRICE_ID_CONSOLE", "price_console_m"):
            assert _plan_from_price_id("price_console_m") == ("console", 200)

    def test_plan_from_console_annual(self):
        from app.api.v1.payments import _plan_from_price_id
        from app.core.config import settings

        with patch.object(
            settings, "STRIPE_PRICE_ID_CONSOLE_ANNUAL", "price_console_y"
        ):
            assert _plan_from_price_id("price_console_y") == ("console", 200)

    def test_unknown_price_returns_none(self):
        from app.api.v1.payments import _plan_from_price_id

        assert _plan_from_price_id("price_attacker_supplied") is None

    def test_unset_env_vars_never_match(self):
        """With console env vars unset (empty string), an empty price_id must
        NOT resolve to a plan — the empty-key entry is popped from the map."""
        from app.api.v1.payments import _plan_from_price_id
        from app.core.config import settings

        with (
            patch.object(settings, "STRIPE_PRICE_ID_CONSOLE", ""),
            patch.object(settings, "STRIPE_PRICE_ID_CONSOLE_ANNUAL", ""),
        ):
            assert _plan_from_price_id("") is None

    @pytest.mark.asyncio
    async def test_console_checkout_creates_console_subscription(self):
        """handle_successful_payment on a Console price creates plan=console
        with 200 credits/month."""
        from app.api.v1.payments import handle_successful_payment
        from app.core.config import settings

        user = MagicMock()
        no_sub = MagicMock()
        no_sub.scalar_one_or_none.return_value = None
        user_result = MagicMock()
        user_result.scalar_one_or_none.return_value = user

        session = AsyncMock()
        session.execute = AsyncMock(side_effect=[user_result, no_sub])
        session.add = MagicMock()

        stripe_sub = {
            "items": {"data": [{"price": {"id": "price_console_m"}}]},
            "customer": "cus_1",
            "current_period_start": 1750000000,
            "current_period_end": 1752600000,
        }
        with (
            patch.object(settings, "STRIPE_PRICE_ID_CONSOLE", "price_console_m"),
            patch(
                "app.api.v1.payments.stripe.Subscription.retrieve",
                return_value=stripe_sub,
            ),
        ):
            await handle_successful_payment(
                {"client_reference_id": "user_1", "subscription": "sub_1"},
                session,
            )

        session.add.assert_called_once()
        new_sub = session.add.call_args[0][0]
        assert new_sub.plan == "console"
        assert new_sub.credits_per_month == 200
        assert new_sub.credits_remaining == 200
        session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_unmapped_price_fails_closed(self):
        """A checkout on an unmapped price must NOT create a subscription
        (money taken + no plan is the trap; the handler must return early)."""
        from app.api.v1.payments import handle_successful_payment

        user_result = MagicMock()
        user_result.scalar_one_or_none.return_value = MagicMock()

        session = AsyncMock()
        session.execute = AsyncMock(return_value=user_result)
        session.add = MagicMock()

        stripe_sub = {
            "items": {"data": [{"price": {"id": "price_not_in_any_map"}}]},
            "customer": "cus_1",
            "current_period_start": 1750000000,
            "current_period_end": 1752600000,
        }
        with patch(
            "app.api.v1.payments.stripe.Subscription.retrieve",
            return_value=stripe_sub,
        ):
            await handle_successful_payment(
                {"client_reference_id": "user_1", "subscription": "sub_1"},
                session,
            )

        session.add.assert_not_called()
        session.commit.assert_not_awaited()
