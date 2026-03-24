"""Payment provider abstraction for agent commerce.

All payment rails (Skyfire, credits) implement this interface.
x402 is NOT a PaymentProvider — it is ASGI middleware (see L-05).
"""

from abc import ABC, abstractmethod
from typing import Optional

from fastapi import Request
from pydantic import BaseModel


class PaymentVerification(BaseModel):
    """Result of a successful payment verification and charge."""

    provider: str  # "skyfire" | "credit" (x402 handled at middleware layer)
    payer_id: str  # skyfire user ID, or tru8 user ID
    amount_pence: int  # integer pence (GBP) — £0.07 -> 7
    transaction_ref: Optional[str] = None  # populated after charge succeeds
    metadata: dict = {}


class PaymentProvider(ABC):
    """Abstract base class for agent payment providers.

    Providers are tried in order by the agent auth dependency:
    Skyfire header -> API key + credit balance.
    """

    @abstractmethod
    async def can_handle(self, request: Request) -> bool:
        """Return True if this provider recognises headers in the request."""

    @abstractmethod
    async def verify_and_charge(
        self, request: Request, amount_pence: int, description: str
    ) -> PaymentVerification:
        """Verify payment credentials and charge the amount. Raises on failure."""
