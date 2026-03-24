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
    @patch("app.api.v1.payments.handle_agent_credit_purchase", new_callable=AsyncMock)
    @patch("app.api.v1.payments.stripe.Webhook.construct_event")
    async def test_agent_credit_purchase_routing(
        self, mock_construct, mock_handle_agent, mock_session
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
    @patch("app.api.v1.payments.handle_successful_payment", new_callable=AsyncMock)
    @patch("app.api.v1.payments.stripe.Webhook.construct_event")
    async def test_subscription_payment_routing(
        self, mock_construct, mock_handle_payment, mock_session
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
