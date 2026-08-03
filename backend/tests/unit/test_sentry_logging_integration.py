"""Routine logger.error() must not page anyone; real failures still must.

Background (2026-08-03): ``sentry_sdk.init()`` was called without an
``integrations=`` argument, leaving the SDK's default ``LoggingIntegration`` at
``event_level=ERROR``. All ~280 ``logger.error()`` sites in ``app/`` became
Sentry issues and emails, and the backlog was overwhelmingly routine, handled
evidence-fetch failures. The signal that mattered — a failed write to the
``usage_events`` billing ledger — sat unread among them.

These tests are behavioural rather than configuration assertions: they run a real
Sentry client against a capturing transport and check which log records actually
produce events.
"""

import logging

import pytest
import sentry_sdk

from app.core.observability import EVENT_LEVEL, sentry_integrations


@pytest.fixture
def captured_events():
    """A real Sentry client whose transport collects events instead of sending."""
    events = []

    client = sentry_sdk.Client(
        dsn="https://public@example.ingest.sentry.io/1",
        transport=events.append,
        integrations=sentry_integrations(),
        default_integrations=False,  # isolate: only the integration under test
        auto_enabling_integrations=False,
    )
    # sentry-sdk is pinned at 1.45.1 (CVE-2024-40647), so this is the Hub API,
    # not the 2.x isolation_scope(). Binding a Hub keeps the real global client
    # untouched while these tests run.
    with sentry_sdk.Hub(client):
        yield events


def _flush():
    sentry_sdk.Hub.current.flush(timeout=2)


class TestRoutineLogsDoNotPage:
    def test_error_log_creates_no_issue(self, captured_events):
        """The exact shape that filled the inbox: a handled adapter failure."""
        logging.getLogger("app.services.api_adapters.sports").error(
            "Transfermarkt club search failed for FIFA: Server error '500'"
        )
        _flush()
        assert captured_events == []

    def test_warning_log_creates_no_issue(self, captured_events):
        logging.getLogger("app.pipeline.retrieve").warning("provider degraded")
        _flush()
        assert captured_events == []

    def test_many_error_logs_still_create_nothing(self, captured_events):
        """282 sites firing across a check must not produce 282 emails."""
        log = logging.getLogger("app.services.search")
        for i in range(50):
            log.error("all 2 attempts failed for source %d", i)
        _flush()
        assert captured_events == []


class TestRealFailuresStillReport:
    def test_critical_log_creates_an_issue(self, captured_events):
        """CRITICAL is the deliberate 'wake someone' level."""
        logging.getLogger("app.core.database").critical("connection pool exhausted")
        _flush()
        assert len(captured_events) == 1

    def test_captured_exception_creates_an_issue(self, captured_events):
        """The path the billing-ledger IntegrityError arrived by must survive.

        Unhandled exceptions reach Sentry via SentryAsgiMiddleware and the
        explicit capture_exception calls in app/core/exceptions.py — neither
        depends on the logging integration.
        """
        try:
            raise ValueError("usage_events_check_id_fkey violated")
        except ValueError:
            sentry_sdk.capture_exception()
        _flush()
        assert len(captured_events) == 1
        assert "usage_events_check_id_fkey" in str(captured_events[0])

    def test_error_log_is_retained_as_a_breadcrumb(self, captured_events):
        """Diagnostic value is kept: ERROR logs still attach to a real event."""
        logging.getLogger("app.pipeline.retrieve").error("serper returned 429")
        sentry_sdk.capture_message("something genuinely broke", level="fatal")
        _flush()

        assert len(captured_events) == 1
        crumbs = captured_events[0].get("breadcrumbs") or {}
        messages = [c.get("message") for c in crumbs.get("values", crumbs)]
        assert "serper returned 429" in messages


def test_event_level_is_not_quietly_lowered_back_to_error():
    """Guard the decision itself.

    Restoring event_level=ERROR would silently reinstate the 280-email-a-day
    behaviour, and it would look like a harmless one-word change. If this needs
    to move, read app/core/observability.py first.
    """
    assert EVENT_LEVEL == logging.CRITICAL
