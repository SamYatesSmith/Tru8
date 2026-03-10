"""Agent transaction model for commerce tracking.

Status taxonomy (5 values only):
  pending    — handler ran, settlement not confirmed
  completed  — settled/charged
  failed     — pipeline error, no charge
  refunded   — credits only
  unsettled  — settlement failed/unknown (reason in metadata.settlement_reason)

Settlement reasons (stored in metadata.settlement_reason):
  "failed" | "unknown" | "missing_header" | "stale_pending" | "facilitator_error"
"""

from typing import Optional
from datetime import datetime, timezone

from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel

from .check import generate_uuid


class AgentTransaction(SQLModel, table=True):
    __tablename__ = "agent_transaction"

    id: str = Field(default_factory=generate_uuid, primary_key=True)
    check_id: Optional[str] = Field(
        default=None, foreign_key="check.id", index=True
    )  # null for lookup misses
    provider: str  # "x402" | "skyfire" | "credit"
    payer_id: str = Field(index=True)  # wallet address / skyfire user / tru8 user ID
    tier: str  # "lookup" | "quick" | "full"
    amount_cents: int  # integer cents — NO floats for money
    transaction_ref: Optional[str] = None  # tx hash — null until settlement completes
    idempotency_key: Optional[str] = Field(
        default=None, sa_column_kwargs={"unique": True, "index": True}
    )  # single-use forever
    request_hash: Optional[str] = (
        None  # SHA256 of (tier + claim_hash + compact) — for 409 conflict detection
    )
    status: str = Field(
        default="pending"
    )  # "pending" | "completed" | "failed" | "refunded" | "unsettled"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    tx_metadata: Optional[dict] = Field(
        default=None, sa_column=Column("metadata", JSONB)
    )  # settlement_reason, claim_text_hash, metrics, etc.
