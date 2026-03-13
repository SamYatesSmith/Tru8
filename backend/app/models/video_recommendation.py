"""VideoRecommendation model — standalone video context (E14).

Videos are NOT pipeline evidence. They are a standalone recommendation feature
retrieved via YouTube Data API, classified by lightweight channel heuristics.
"""

from typing import Optional
from datetime import datetime, timezone
from sqlmodel import Field, SQLModel, Relationship
from .check import generate_uuid, _utcnow_naive


class VideoRecommendation(SQLModel, table=True):
    __tablename__ = "video_recommendation"

    id: str = Field(default_factory=generate_uuid, primary_key=True)
    check_id: str = Field(foreign_key="check.id", index=True)
    claim_id: str = Field(foreign_key="claim.id", index=True)

    # YouTube fields
    video_id: str = Field(max_length=20, description="YouTube video ID")
    title: str = Field(max_length=500)
    description: Optional[str] = Field(default=None, max_length=2000)
    channel_name: str = Field(max_length=200)
    channel_id: Optional[str] = Field(default=None, max_length=50)
    publish_date: Optional[datetime] = None
    video_url: str = Field(max_length=500)
    thumbnail_url: Optional[str] = Field(default=None, max_length=500)
    duration: Optional[str] = Field(
        default=None, max_length=20, description="ISO 8601 duration e.g. PT4M32S"
    )

    # Lightweight classification (channel heuristics, NOT LLM)
    tier_label: Optional[str] = Field(
        default=None,
        max_length=20,
        description="Heuristic tier: primary|reporting|commentary",
    )
    type_label: Optional[str] = Field(
        default=None,
        max_length=30,
        description="Heuristic type: data|official_statement|news_reporting|analysis|opinion|academic",
    )

    created_at: datetime = Field(default_factory=_utcnow_naive)
