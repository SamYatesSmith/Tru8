"""Usage ledger — the single source of truth for dashboard credit accounting.

Design: audit/2026-07-10_usage_ledger_design.md (founder-approved 2026-07-10).

Every dashboard-side debit (check creation, re-search, top-up) appends one
+1 row; refunds append a compensating -1 row — events are never deleted or
mutated, so any time window sums correctly and the history stays auditable.
Entitlement gates and usage meters sum this table. The legacy counters
(User.credits, User.total_credits_used, Check.credits_used) are still
dual-written for API response back-compat, but no gate reads them.

The /agent prepaid rail (User.credit_balance_pence) is a separate system
and does not touch this ledger.
"""

from typing import Optional
from datetime import datetime

from sqlalchemy import Index
from sqlmodel import Field, SQLModel

from .check import _utcnow_naive

# Event kinds. Debits are always +1 credit; 'refund' is -1; 'adjustment'
# carries the migration-time reconciliation delta (historical re-searches
# that only ever lived in User.total_credits_used).
KIND_CHECK = "check"
KIND_RE_SEARCH = "re_search"
KIND_TOP_UP = "top_up"
KIND_REFUND = "refund"
KIND_ADJUSTMENT = "adjustment"

DEBIT_KINDS = frozenset({KIND_CHECK, KIND_RE_SEARCH, KIND_TOP_UP})


class UsageEvent(SQLModel, table=True):
    __tablename__ = "usage_events"
    __table_args__ = (Index("ix_usage_events_user_created", "user_id", "created_at"),)

    id: str = Field(primary_key=True)
    user_id: str = Field(foreign_key="user.id", nullable=False)
    # The check this event concerns: the new check for 'check' debits, the
    # re-searched check for 're_search'/'top_up', the refunded check for
    # 'refund'. NULL only for 'adjustment'.
    check_id: Optional[str] = Field(default=None, foreign_key="check.id")
    kind: str = Field(max_length=16, nullable=False)
    credits: int = Field(nullable=False)
    # Whether the debit drew from the trial allocation (User.credits > 0 at
    # debit time). Mirrored exactly on refund so a subscriber's refund can
    # never mint a phantom trial credit (design D2).
    drew_trial: bool = Field(default=False, nullable=False)
    created_at: datetime = Field(default_factory=_utcnow_naive, nullable=False)
