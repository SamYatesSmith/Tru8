"""
Webhook registration model.

Each user can register up to 5 webhook URLs. When a subscribed event fires
(e.g. check.completed), the webhook service POSTs a signed payload.
"""

from typing import Optional, List
from datetime import datetime, timezone
from sqlmodel import Field, SQLModel, Column
from sqlalchemy.dialects.postgresql import JSONB
from .check import _utcnow_naive
import uuid


def _generate_uuid() -> str:
    return str(uuid.uuid4())


class Webhook(SQLModel, table=True):
    __tablename__ = "webhook"

    id: str = Field(default_factory=_generate_uuid, primary_key=True)
    user_id: str = Field(foreign_key="user.id", index=True)
    url: str = Field(max_length=2048)
    # Events to subscribe to (e.g. ["check.completed", "check.failed"])
    events: List[str] = Field(default=[], sa_column=Column(JSONB))
    secret: str = Field(max_length=64)  # HMAC signing secret
    is_active: bool = Field(default=True)
    description: Optional[str] = Field(default=None, max_length=200)
    # Delivery tracking
    last_triggered_at: Optional[datetime] = None
    failure_count: int = Field(default=0)
    created_at: datetime = Field(default_factory=_utcnow_naive)
