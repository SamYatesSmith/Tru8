"""x402 audit middleware — pure ASGI (no BaseHTTPMiddleware).

Intercepts responses from x402 tier endpoints and records settlement status
on the corresponding AgentTransaction.  Uses ``request.state.agent_tx_id``
(set by the handler) for correlation.

Detection logic:

  200 + PAYMENT-RESPONSE header  → ``completed``, extract tx hash
  Non-2xx AND NOT 402            → ``failed``
  402 WITH agent_tx_id           → ``unsettled``, enrich body with recovery
  200 without PAYMENT-RESPONSE   → ``unsettled``, reason ``missing_header``
  402 without agent_tx_id        → initial challenge, pass through

NOT using ``BaseHTTPMiddleware`` because it corrupts contextvar state in
ASGI applications.  The ``send_wrapper`` pattern gives us the same
interception capability with zero contextvar issues.
"""

import json
import logging
from typing import Callable

from starlette.types import ASGIApp, Receive, Scope, Send

logger = logging.getLogger(__name__)


class X402AuditMiddleware:
    """Pure ASGI middleware for x402 settlement audit."""

    def __init__(self, app: ASGIApp, route_prefix: str = "/api/v1/agent/x402"):
        self.app = app
        self.route_prefix = route_prefix

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        if not path.startswith(self.route_prefix):
            await self.app(scope, receive, send)
            return

        # Only audit the tier endpoints (lookup, quick, full)
        # Skip challenge and result retrieval
        tier_paths = (
            f"{self.route_prefix}/lookup",
            f"{self.route_prefix}/quick",
            f"{self.route_prefix}/full",
        )
        if path not in tier_paths:
            await self.app(scope, receive, send)
            return

        # Intercept the response via send_wrapper
        response_started = False
        status_code = 0
        response_headers: dict = {}

        async def send_wrapper(message: dict) -> None:
            nonlocal response_started, status_code, response_headers

            if message["type"] == "http.response.start":
                response_started = True
                status_code = message.get("status", 0)
                response_headers = dict(
                    (
                        k.decode() if isinstance(k, bytes) else k,
                        v.decode() if isinstance(v, bytes) else v,
                    )
                    for k, v in message.get("headers", [])
                )
                await send(message)

            elif message["type"] == "http.response.body":
                # Get agent_tx_id from request state (set by handler)
                request_state = scope.get("state", {})
                agent_tx_id = request_state.get("agent_tx_id")

                if agent_tx_id:
                    await self._audit_settlement(
                        agent_tx_id, status_code, response_headers, message
                    )

                await send(message)
            else:
                await send(message)

        await self.app(scope, receive, send_wrapper)

    async def _audit_settlement(
        self,
        agent_tx_id: str,
        status_code: int,
        headers: dict,
        body_message: dict,
    ) -> None:
        """Record settlement outcome on the AgentTransaction."""
        from app.core.database import async_session
        from app.models.agent_transaction import AgentTransaction
        from sqlalchemy import select

        payment_response = headers.get("payment-response", "")

        try:
            if status_code == 200 and payment_response:
                # Successful settlement
                new_status = "completed"
                tx_ref = payment_response
                reason = None
            elif status_code == 200 and not payment_response:
                # Success but missing settlement header
                new_status = "unsettled"
                tx_ref = None
                reason = "missing_header"
            elif status_code == 402:
                # Settlement required — enrich body with recovery info
                new_status = "unsettled"
                tx_ref = None
                reason = "facilitator_error"
            elif status_code >= 400:
                # Handler error
                new_status = "failed"
                tx_ref = None
                reason = f"http_{status_code}"
            else:
                return  # Unexpected status, don't modify

            async with async_session() as session:
                result = await session.execute(
                    select(AgentTransaction).where(AgentTransaction.id == agent_tx_id)
                )
                tx = result.scalar_one_or_none()
                if tx:
                    tx.status = new_status
                    if tx_ref:
                        tx.transaction_ref = tx_ref
                    if reason:
                        meta = tx.tx_metadata or {}
                        meta["settlement_reason"] = reason
                        tx.tx_metadata = meta
                    await session.commit()
                    logger.info(
                        f"[X402 AUDIT] tx={agent_tx_id} status={new_status} "
                        f"reason={reason} ref={tx_ref}"
                    )
        except Exception as e:
            logger.error(f"[X402 AUDIT] Failed to audit tx {agent_tx_id}: {e}")
