"""
API key model for agent/developer authentication.

Keys are issued to existing users (who sign up via Clerk) and provide
a simpler auth path than JWT for programmatic API access.
The raw key is shown once at creation; only the SHA-256 hash is stored.
"""

from typing import Optional
from datetime import datetime, timezone
from sqlmodel import Field, SQLModel, Relationship
import uuid


def _generate_uuid() -> str:
    return str(uuid.uuid4())


class APIKey(SQLModel, table=True):
    __tablename__ = "api_key"

    id: str = Field(default_factory=_generate_uuid, primary_key=True)
    user_id: str = Field(foreign_key="user.id", index=True)
    key_hash: str = Field(index=True)
    key_prefix: str = Field(max_length=16)  # "tru8_sk_xxxx" — visible identifier
    name: str = Field(max_length=100)
    is_active: bool = Field(default=True)
    last_used_at: Optional[datetime] = None
    usage_count: int = Field(default=0)
    expires_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    user: Optional["User"] = Relationship()
