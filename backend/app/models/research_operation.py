"""Durable strengthening attempts and immutable report revisions."""

from datetime import datetime
from typing import Optional

from sqlalchemy import Column, ForeignKey, Index, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel

from app.models.check import generate_uuid, _utcnow_naive


class ResearchOperation(SQLModel, table=True):
    __tablename__ = "research_operation"
    __table_args__ = (
        UniqueConstraint("check_id", "request_key", name="uq_research_request"),
        Index(
            "uq_research_active_check",
            "check_id",
            unique=True,
            postgresql_where=text("status IN ('pending', 'running')"),
        ),
    )
    id: str = Field(default_factory=generate_uuid, primary_key=True)
    check_id: str = Field(
        sa_column=Column(
            String,
            ForeignKey("check.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )
    claim_id: str = Field(
        sa_column=Column(
            String,
            ForeignKey("claim.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )
    request_key: str = Field(sa_column=Column(String(128), nullable=False))
    request_scope: str
    element_ids: list = Field(sa_column=Column(JSONB, nullable=False))
    debit_id: Optional[str] = Field(
        default=None,
        sa_column=Column(String, ForeignKey("usage_events.id", ondelete="SET NULL")),
    )
    status: str = Field(default="pending", sa_column=Column(String(16), nullable=False))
    stage: str = Field(default="planning", sa_column=Column(String(32), nullable=False))
    message: str = Field(default="Research queued")
    new_evidence_count: int = Field(default=0)
    baseline: dict = Field(sa_column=Column(JSONB, nullable=False))
    baseline_hash: str = Field(sa_column=Column(String(64), nullable=False))
    result_revision_id: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=_utcnow_naive)
    deadline_at: datetime
    finished_at: Optional[datetime] = Field(default=None)


class ReportRevision(SQLModel, table=True):
    __tablename__ = "report_revision"
    __table_args__ = (
        UniqueConstraint("operation_id", "phase", name="uq_research_revision_phase"),
    )
    id: str = Field(default_factory=generate_uuid, primary_key=True)
    check_id: str = Field(
        sa_column=Column(
            String,
            ForeignKey("check.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )
    operation_id: str = Field(
        sa_column=Column(
            String,
            ForeignKey("research_operation.id", ondelete="CASCADE"),
            nullable=False,
        )
    )
    phase: str = Field(sa_column=Column(String(8), nullable=False))
    snapshot: dict = Field(sa_column=Column(JSONB, nullable=False))
    created_at: datetime = Field(default_factory=_utcnow_naive)
