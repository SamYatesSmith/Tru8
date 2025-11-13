"""
Unknown Source Tracking Model

Progressive Curation System - Phase 1
Tracks unknown domains encountered during evidence retrieval for manual review and curation.
"""

from typing import Optional
from datetime import datetime
from sqlmodel import Field, SQLModel, Column, JSON
from sqlalchemy.dialects.postgresql import JSONB
import uuid

def generate_uuid() -> str:
    return str(uuid.uuid4())

class UnknownSource(SQLModel, table=True):
    """
    Track unknown sources for progressive credibility database curation.

    When evidence retrieval encounters a domain not in source_credibility.json,
    log it here with context for weekly manual review.
    """
    __tablename__ = "unknown_source"

    id: str = Field(default_factory=generate_uuid, primary_key=True)
    domain: str = Field(index=True, description="Registered domain (e.g., 'substack.com')")
    full_url: str = Field(description="Full URL where domain was first encountered")

    # Context for curation decisions
    claim_topic: Optional[str] = Field(default=None, description="Topic/subject of claim using this source")
    evidence_title: Optional[str] = Field(default=None, description="Title of the evidence article")
    evidence_snippet: Optional[str] = Field(default=None, description="Snippet for context")

    # Tracking metrics
    frequency: int = Field(default=1, description="Number of times this domain has appeared")
    first_seen: datetime = Field(default_factory=datetime.utcnow, description="First encounter timestamp")
    last_seen: datetime = Field(default_factory=datetime.utcnow, description="Most recent encounter")

    # Curation status
    reviewed: bool = Field(default=False, description="Has been manually reviewed by admin")
    added_to_credibility_list: bool = Field(default=False, description="Added to source_credibility.json")
    review_notes: Optional[str] = Field(default=None, sa_column=Column(JSONB), description="Admin notes from review")
    assigned_tier: Optional[str] = Field(default=None, description="Tier assigned after review (e.g., 'news_tier2')")
    assigned_credibility: Optional[float] = Field(default=None, description="Credibility score assigned (0.0-1.0)")

    # Quality signals (for future multi-signal algorithm)
    has_https: bool = Field(default=False, description="Domain uses HTTPS")
    has_author_byline: Optional[bool] = Field(default=None, description="Article had author attribution")
    has_primary_sources: Optional[bool] = Field(default=None, description="Article cited primary sources")
    domain_age_years: Optional[int] = Field(default=None, description="Domain registration age in years")

    class Config:
        schema_extra = {
            "example": {
                "domain": "theintercept.com",
                "full_url": "https://theintercept.com/2025/article",
                "claim_topic": "government surveillance",
                "evidence_title": "NSA Program Revealed",
                "frequency": 5,
                "reviewed": True,
                "assigned_tier": "investigative_nonprofits",
                "assigned_credibility": 0.85
            }
        }
