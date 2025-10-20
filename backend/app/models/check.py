from typing import Optional, List
from datetime import datetime
from sqlmodel import Field, SQLModel, Relationship, JSON, Column
import uuid

def generate_uuid() -> str:
    return str(uuid.uuid4())

class Check(SQLModel, table=True):
    id: str = Field(default_factory=generate_uuid, primary_key=True)
    user_id: str = Field(foreign_key="user.id", index=True)
    input_type: str  # 'url', 'text', 'image', 'video'
    input_content: str = Field(sa_column=Column(JSON))  # Store as JSON
    input_url: Optional[str] = None
    status: str = Field(default="pending")  # 'pending', 'processing', 'completed', 'failed'
    credits_used: int = Field(default=1)
    processing_time_ms: Optional[int] = None
    error_message: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    
    # Relationships
    user: "User" = Relationship(back_populates="checks")
    claims: List["Claim"] = Relationship(back_populates="check")

class Claim(SQLModel, table=True):
    id: str = Field(default_factory=generate_uuid, primary_key=True)
    check_id: str = Field(foreign_key="check.id", index=True)
    text: str
    verdict: str  # 'supported', 'contradicted', 'uncertain'
    confidence: float = Field(ge=0, le=100)  # 0-100
    rationale: str
    position: int  # Order in the check
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    check: Check = Relationship(back_populates="claims")
    evidence: List["Evidence"] = Relationship(back_populates="claim")

class Evidence(SQLModel, table=True):
    id: str = Field(default_factory=generate_uuid, primary_key=True)
    claim_id: str = Field(foreign_key="claim.id", index=True)
    source: str  # Publisher name
    url: str
    title: str
    snippet: str
    published_date: Optional[datetime] = None
    relevance_score: float = Field(ge=0, le=1)  # 0-1
    credibility_score: float = Field(default=0.6, ge=0, le=1)  # 0-1 (source trustworthiness)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Deduplication fields (Phase 1, Week 2)
    content_hash: Optional[str] = None  # MD5 hash of normalized content
    is_syndicated: bool = Field(default=False)  # True if content duplicated elsewhere
    original_source_url: Optional[str] = None  # URL of original source if syndicated

    # Source independence fields (Phase 1, Week 3)
    parent_company: Optional[str] = None  # Media company owner (e.g., "News Corp")
    independence_flag: Optional[str] = None  # 'independent', 'corporate', 'state-funded', 'unknown'
    domain_cluster_id: Optional[int] = None  # Unique ID for ownership group

    # Relationships
    claim: Claim = Relationship(back_populates="evidence")