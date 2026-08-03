"""Sentry integration configuration.

Lives here rather than inline in ``main.py`` so it can be tested without
importing the whole FastAPI application graph.

**Sentry carries exceptions. Logs go to the log stream.**

Until 2026-08-03 ``sentry_sdk.init()`` was called with no ``integrations=``
argument, which left the SDK's default ``LoggingIntegration`` enabled at
``event_level=ERROR``. Every one of the ~280 ``logger.error()`` calls in ``app/``
therefore became a Sentry issue and an email.

The resulting backlog was almost entirely routine, *handled* evidence-fetch
failures — "Library of Congress all 2 attempts failed", "Transfermarkt club
search failed", "empty HTML tree for URL …", "Companies House client error 401".
A source going down is not an incident in a pipeline deliberately built to route
around thirty of them. But it paged the founder every time, and the one thing
that genuinely mattered — a failed write to the ``usage_events`` billing ledger —
sat unread among seventeen untriaged issues.

Noise is not a cosmetic problem. An inbox that cries wolf 280 different ways is
an inbox where the real alert is missed.
"""

import logging
from typing import List

from sentry_sdk.integrations.logging import LoggingIntegration

# Records ERROR-level logs as breadcrumbs (context attached to any exception that
# does fire), while only CRITICAL creates an issue in its own right.
BREADCRUMB_LEVEL = logging.INFO
EVENT_LEVEL = logging.CRITICAL


def sentry_integrations() -> List[LoggingIntegration]:
    """Integrations for ``sentry_sdk.init()``.

    Genuine failures still reach Sentry by three routes, none of which depend on
    the logging integration:

    * ``SentryAsgiMiddleware`` — unhandled exceptions on any request
    * ``app.core.exceptions`` — explicit ``capture_exception`` for 5xx
    * ``app.pipeline.claim_map_analyzer`` — deliberate ``capture_message`` calls

    If something warrants waking a human, capture it explicitly or log it at
    CRITICAL. Do not raise ``EVENT_LEVEL`` back to ``ERROR``.
    """
    return [
        LoggingIntegration(
            level=BREADCRUMB_LEVEL,
            event_level=EVENT_LEVEL,
        )
    ]
