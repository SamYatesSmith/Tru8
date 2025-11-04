"""
Mock model classes for testing pipeline stages

These are simple data structures used in tests. The actual pipeline implementations
use dictionaries instead of formal model classes.

Created: 2025-11-03
"""

from dataclasses import dataclass, field
from typing import List, Optional, Any, Dict
from datetime import datetime
from enum import Enum


# ============================================================================
# Enum Types
# ============================================================================

class StanceLabel(str, Enum):
    """NLI stance labels for verification results"""
    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"
    NEUTRAL = "neutral"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    CONFLICTING = "conflicting"
    ERROR = "error"


class VerdictType(str, Enum):
    """Final verdict types from judge stage"""
    SUPPORTED = "SUPPORTED"
    CONTRADICTED = "CONTRADICTED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    CONFLICTING_EVIDENCE = "CONFLICTING_EVIDENCE"
    NOT_VERIFIABLE = "NOT_VERIFIABLE"
    UNCERTAIN = "UNCERTAIN"
    ERROR = "ERROR"


# ============================================================================
# Data Models
# ============================================================================

@dataclass
class Claim:
    """
    Represents a factual claim to be verified

    Used in test_extract.py, test_retrieve.py, test_verify.py, test_judge.py
    """
    text: str
    claim_type: str = "factual"  # factual, opinion, prediction
    confidence: float = 0.0
    subject_context: Optional[str] = None
    key_entities: List[str] = field(default_factory=list)
    temporal_markers: List[str] = field(default_factory=list)
    is_time_sensitive: bool = False
    is_verifiable: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Evidence:
    """
    Represents a piece of evidence from a source

    Used in test_retrieve.py, test_verify.py, test_judge.py
    """
    text: str
    url: str
    credibility_score: float
    publisher: str
    relevance_score: float = 0.0
    published_date: Optional[datetime] = None
    is_factcheck: bool = False
    rating: Optional[str] = None  # For fact-check evidence
    reviewer: Optional[str] = None  # For fact-check evidence
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Query:
    """
    Represents a user query for the Search Clarity feature

    Used in test_query_answer.py
    """
    text: str
    query_type: str = "factual"  # factual, complex, philosophical
    is_time_sensitive: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


# ============================================================================
# Utility functions for tests
# ============================================================================

def create_mock_claim(text: str, **kwargs) -> Claim:
    """Helper function to create mock claims in tests"""
    return Claim(text=text, **kwargs)


def create_mock_evidence(text: str, url: str, credibility: float, publisher: str, **kwargs) -> Evidence:
    """Helper function to create mock evidence in tests"""
    return Evidence(
        text=text,
        url=url,
        credibility_score=credibility,
        publisher=publisher,
        **kwargs
    )


def create_mock_query(text: str, **kwargs) -> Query:
    """Helper function to create mock queries in tests"""
    return Query(text=text, **kwargs)
