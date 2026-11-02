"""One row per Stripe dispute (chargeback or inquiry) against a Tru8 payment.

An account is on payment hold while it has ANY dispute whose status is not
resolved in our favour (see app/services/payment_hold.py). Keyed by Stripe's
dispute id, not the charge: an inquiry that escalates opens a NEW dispute on
the same charge, and a customer can dispute several charges, so a single
per-user field could be lifted by the wrong close event (review 2026-11-02,
audit/2026-11-02_payment_hold_design.md).
"""

from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel


def _utcnow_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class PaymentDispute(SQLModel, table=True):
    __tablename__ = "payment_dispute"

    id: str = Field(primary_key=True, max_length=64)  # Stripe dispute id (dp_…)
    user_id: str = Field(foreign_key="user.id", index=True)
    charge_id: str = Field(index=True, max_length=64)
    # Stripe dispute status, or "released" when the founder lifts a hold.
    status: str = Field(max_length=32)
    reason: Optional[str] = Field(default=None, max_length=64)
    amount: int = Field(default=0)  # minor units, as Stripe reports it
    currency: Optional[str] = Field(default=None, max_length=8)
    created_at: datetime = Field(default_factory=_utcnow_naive)
    updated_at: datetime = Field(default_factory=_utcnow_naive)
