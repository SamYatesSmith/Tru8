"""Server-side funnel events (ACE Stage 4, 2026-10-01).

check_completed (activation, with `first`) from the completion hook;
credits_purchased / subscription_started from the Stripe webhook. All are
no-ops without POSTHOG_API_KEY, never raise into their caller, and carry a
deterministic uuid so retries are ingested once.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.config import settings
from app.services import product_analytics as pa


@pytest.fixture
def key_on(monkeypatch):
    monkeypatch.setattr(settings, "POSTHOG_API_KEY", "phc_test")


class _Resp:
    def __init__(self, status):
        self.status_code = status


def _fake_client(monkeypatch, status=200, raises=None):
    sent = []

    class _Client:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def post(self, url, json):
            if raises:
                raise raises
            sent.append((url, json))
            return _Resp(status)

    monkeypatch.setattr(pa.httpx, "AsyncClient", _Client)
    return sent


class TestSendEvent:
    @pytest.mark.asyncio
    async def test_no_key_sends_nothing(self, monkeypatch):
        monkeypatch.setattr(settings, "POSTHOG_API_KEY", "")
        sent = _fake_client(monkeypatch)
        assert await pa.send_event("x", "user_1") is False
        assert sent == []
        assert pa.schedule_event("x", "user_1") is None

    @pytest.mark.asyncio
    async def test_payload_shape(self, monkeypatch, key_on):
        sent = _fake_client(monkeypatch)
        assert await pa.send_event("paid", "user_1", {"plan": "console"}, "cs_1")
        url, body = sent[0]
        assert url == "https://eu.i.posthog.com/i/v0/e/"
        assert body["api_key"] == "phc_test"
        assert body["distinct_id"] == "user_1"
        assert body["properties"] == {"source": "server", "plan": "console"}
        assert body["uuid"] == pa.event_uuid("paid", "cs_1")

    def test_uuid_is_deterministic_per_event_and_key(self):
        assert pa.event_uuid("a", "k") == pa.event_uuid("a", "k")
        assert pa.event_uuid("a", "k") != pa.event_uuid("b", "k")
        assert pa.event_uuid("a", "k") != pa.event_uuid("a", "j")

    @pytest.mark.asyncio
    async def test_errors_are_swallowed(self, monkeypatch, key_on):
        _fake_client(monkeypatch, raises=RuntimeError("boom"))
        assert await pa.send_event("x", "user_1") is False
        _fake_client(monkeypatch, status=500)
        assert await pa.send_event("x", "user_1") is False


class TestCheckCompleted:
    @pytest.mark.asyncio
    @pytest.mark.parametrize("count,first", [(1, True), (2, False)])
    async def test_first_flag(self, monkeypatch, key_on, count, first):
        sent = _fake_client(monkeypatch)
        monkeypatch.setattr(pa, "_completed_check_count", AsyncMock(return_value=count))
        assert await pa.send_check_completed("user_1", "chk_1")
        body = sent[0][1]
        assert body["event"] == "check_completed"
        assert body["properties"]["first"] is first
        assert body["properties"]["check_id"] == "chk_1"
        assert body["uuid"] == pa.event_uuid("check_completed", "chk_1")

    @pytest.mark.asyncio
    async def test_completion_hook_schedules_it(self, monkeypatch):
        """The wired seam: send_success_notifications queues the event."""
        from app.pipeline import runner

        calls = []
        monkeypatch.setattr(
            pa, "schedule_check_completed", lambda u, c: calls.append((u, c))
        )
        monkeypatch.setattr(
            runner.email_notification_service,
            "send_check_completed_email_sync",
            lambda **k: None,
        )
        monkeypatch.setattr(
            "app.services.lifecycle_emails.schedule_trial_exhausted_email",
            lambda u: None,
        )
        await runner.send_success_notifications("user_1", "chk_1", {}, {}, {})
        assert calls == [("user_1", "chk_1")]


@pytest.fixture
def mock_session():
    session = AsyncMock()
    session.commit = AsyncMock()
    return session


class TestWebhookEvents:
    @pytest.mark.asyncio
    async def test_credit_purchase_emits_after_commit(self, monkeypatch, mock_session):
        from app.api.v1 import payments

        calls = []
        monkeypatch.setattr(
            payments, "schedule_event", lambda *a, **k: calls.append((a, k))
        )
        result = MagicMock()
        result.rowcount = 1
        mock_session.execute = AsyncMock(return_value=result)
        await payments.handle_agent_credit_purchase(
            {
                "id": "cs_9",
                "client_reference_id": "user_1",
                "metadata": {"pence_value": "300", "credit_pack": "3"},
            },
            mock_session,
        )
        assert calls == [
            (
                ("credits_purchased", "user_1", {"pack": "3", "pence": 300}),
                {"dedup_key": "cs_9"},
            )
        ]

    @pytest.mark.asyncio
    async def test_failed_credit_purchase_emits_nothing(
        self, monkeypatch, mock_session
    ):
        from app.api.v1 import payments

        calls = []
        monkeypatch.setattr(payments, "schedule_event", lambda *a, **k: calls.append(a))
        result = MagicMock()
        result.rowcount = 0
        mock_session.execute = AsyncMock(return_value=result)
        await payments.handle_agent_credit_purchase(
            {"client_reference_id": "nobody", "metadata": {"pence_value": "300"}},
            mock_session,
        )
        assert calls == []

    @pytest.mark.asyncio
    async def test_subscription_emits_after_commit(self, monkeypatch, mock_session):
        from app.api.v1 import payments

        monkeypatch.setattr(settings, "STRIPE_PRICE_ID_CONSOLE", "price_console")
        stripe_sub = {
            "customer": "cus_1",
            "items": {
                "data": [
                    {
                        "price": {
                            "id": "price_console",
                            "recurring": {"interval": "month"},
                        }
                    }
                ]
            },
            "current_period_start": 1_700_000_000,
            "current_period_end": 1_702_000_000,
        }
        monkeypatch.setattr(
            payments.stripe.Subscription, "retrieve", lambda _id: stripe_sub
        )
        user = MagicMock()
        user_result = MagicMock()
        user_result.scalar_one_or_none.return_value = user
        sub_result = MagicMock()
        sub_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(side_effect=[user_result, sub_result])
        mock_session.add = MagicMock()
        calls = []
        monkeypatch.setattr(
            payments, "schedule_event", lambda *a, **k: calls.append((a, k))
        )
        await payments.handle_successful_payment(
            {"id": "cs_2", "client_reference_id": "user_1", "subscription": "sub_1"},
            mock_session,
        )
        mock_session.commit.assert_called_once()
        assert calls == [
            (
                (
                    "subscription_started",
                    "user_1",
                    {"plan": "console", "interval": "month", "new_subscription": True},
                ),
                {"dedup_key": "cs_2"},
            )
        ]
