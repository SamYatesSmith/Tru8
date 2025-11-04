"""
Database Fixtures and Factories for Testing

Created: 2025-11-03 15:30:00 UTC
Last Updated: 2025-11-03 15:30:00 UTC
Code Version: commit 388ac66
Purpose: Factory functions for creating test database records
Models: Check, Claim, Evidence, User

This module provides factory functions for creating realistic
database records for testing, following the factory pattern.

Usage:
    from database import create_test_check, create_test_claim
    check = create_test_check(db_session, status="completed")

Phase: Phase 0 (Infrastructure)
Status: Production-ready
"""

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import json

# Try to import models
try:
    from app.models.check import Check
    from app.models.claim import Claim
    from app.models.evidence import Evidence
    from app.models.user import User
    MODELS_AVAILABLE = True
except ImportError:
    # Models not available during early testing
    Check = Claim = Evidence = User = None
    MODELS_AVAILABLE = False

# ==================== USER FACTORIES ====================

def create_test_user(
    session,
    clerk_id: str = "test_user_123",
    email: str = "test@example.com",
    credits: int = 10,
    is_pro: bool = False,
    **kwargs
) -> Any:
    """
    Create a test user record

    Args:
        session: Database session
        clerk_id: Clerk user ID
        email: User email
        credits: Available credits
        is_pro: Pro subscription status
        **kwargs: Additional user fields

    Returns:
        User model instance

    Created: 2025-11-03
    """
    if not MODELS_AVAILABLE:
        raise RuntimeError("Database models not available")

    user = User(
        clerk_id=clerk_id,
        email=email,
        credits=credits,
        is_pro=is_pro,
        monthly_checks_used=kwargs.get("monthly_checks_used", 0),
        created_at=kwargs.get("created_at", datetime.utcnow()),
        **{k: v for k, v in kwargs.items() if k not in ["monthly_checks_used", "created_at"]}
    )

    session.add(user)
    session.commit()
    session.refresh(user)

    return user


# ==================== CHECK FACTORIES ====================

def create_test_check(
    session,
    user_id: str = "test_user_123",
    input_type: str = "text",
    input_content: str = "Sample text for testing",
    status: str = "pending",
    **kwargs
) -> Any:
    """
    Create a test check record

    Args:
        session: Database session
        user_id: User Clerk ID
        input_type: One of: text, url, image, video
        input_content: Input content
        status: One of: pending, processing, completed, failed
        **kwargs: Additional check fields

    Returns:
        Check model instance

    Created: 2025-11-03
    """
    if not MODELS_AVAILABLE:
        raise RuntimeError("Database models not available")

    check_data = {
        "user_id": user_id,
        "input_type": input_type,
        "input_content": input_content,
        "status": status,
        "created_at": kwargs.get("created_at", datetime.utcnow()),
        "credits_used": kwargs.get("credits_used", 1)
    }

    # Add optional fields if status is completed
    if status == "completed":
        check_data.update({
            "completed_at": kwargs.get("completed_at", datetime.utcnow()),
            "processing_time_ms": kwargs.get("processing_time_ms", 8500),
            "overall_summary": kwargs.get("overall_summary", "Test summary"),
            "credibility_score": kwargs.get("credibility_score", 0.85),
            "claims_supported": kwargs.get("claims_supported", 2),
            "claims_contradicted": kwargs.get("claims_contradicted", 0),
            "claims_uncertain": kwargs.get("claims_uncertain", 1)
        })

    # Add any additional kwargs
    check_data.update({k: v for k, v in kwargs.items()
                      if k not in check_data})

    check = Check(**check_data)
    session.add(check)
    session.commit()
    session.refresh(check)

    return check


def create_completed_check(
    session,
    user_id: str = "test_user_123",
    num_claims: int = 3,
    **kwargs
) -> Any:
    """
    Create a completed check with realistic data

    Args:
        session: Database session
        user_id: User Clerk ID
        num_claims: Number of claims to create
        **kwargs: Additional check fields

    Returns:
        Check model instance with claims and evidence

    Created: 2025-11-03
    """
    check = create_test_check(
        session,
        user_id=user_id,
        status="completed",
        overall_summary="The content contains multiple verifiable claims about climate change. Most claims are well-supported by authoritative sources.",
        credibility_score=0.82,
        claims_supported=num_claims - 1,
        claims_contradicted=0,
        claims_uncertain=1,
        **kwargs
    )

    # Create claims
    for i in range(num_claims):
        verdict = "supported" if i < num_claims - 1 else "uncertain"
        create_test_claim(
            session,
            check_id=check.id,
            text=f"Test claim {i+1}",
            position=i,
            verdict=verdict,
            confidence=0.85 if verdict == "supported" else 0.45
        )

    return check


# ==================== CLAIM FACTORIES ====================

def create_test_claim(
    session,
    check_id: int,
    text: str = "Test claim",
    position: int = 0,
    verdict: str = "supported",
    confidence: float = 0.85,
    **kwargs
) -> Any:
    """
    Create a test claim record

    Args:
        session: Database session
        check_id: Parent check ID
        text: Claim text
        position: Claim position in check
        verdict: One of: supported, contradicted, uncertain,
                 insufficient_evidence, conflicting_expert_opinion, outdated_claim
        confidence: Confidence score (0-1)
        **kwargs: Additional claim fields

    Returns:
        Claim model instance

    Created: 2025-11-03
    """
    if not MODELS_AVAILABLE:
        raise RuntimeError("Database models not available")

    claim_data = {
        "check_id": check_id,
        "text": text,
        "position": position,
        "verdict": verdict,
        "confidence": confidence,
        "rationale": kwargs.get("rationale", f"This claim is {verdict} based on available evidence."),
        "subject_context": kwargs.get("subject_context", "Test subject"),
        "key_entities": kwargs.get("key_entities", json.dumps(["entity1", "entity2"])),
        "claim_type": kwargs.get("claim_type", "factual"),
        "is_verifiable": kwargs.get("is_verifiable", True),
        "is_time_sensitive": kwargs.get("is_time_sensitive", False)
    }

    # Add additional kwargs
    claim_data.update({k: v for k, v in kwargs.items()
                      if k not in claim_data})

    claim = Claim(**claim_data)
    session.add(claim)
    session.commit()
    session.refresh(claim)

    return claim


# ==================== EVIDENCE FACTORIES ====================

def create_test_evidence(
    session,
    claim_id: int,
    source: str = "BBC News",
    url: str = "https://www.bbc.com/news/test-article",
    relevance_score: float = 0.90,
    credibility_score: float = 0.88,
    **kwargs
) -> Any:
    """
    Create a test evidence record

    Args:
        session: Database session
        claim_id: Parent claim ID
        source: Source name
        url: Source URL
        relevance_score: Relevance score (0-1)
        credibility_score: Credibility score (0-1)
        **kwargs: Additional evidence fields

    Returns:
        Evidence model instance

    Created: 2025-11-03
    """
    if not MODELS_AVAILABLE:
        raise RuntimeError("Database models not available")

    evidence_data = {
        "claim_id": claim_id,
        "source": source,
        "url": url,
        "title": kwargs.get("title", f"Article from {source}"),
        "snippet": kwargs.get("snippet", "Relevant text snippet from the source..."),
        "relevance_score": relevance_score,
        "credibility_score": credibility_score,
        "published_date": kwargs.get("published_date", "2024-11-01"),
        "tier": kwargs.get("tier", "tier1_news"),
        "is_factcheck": kwargs.get("is_factcheck", False),
        "nli_stance": kwargs.get("nli_stance", "supporting"),
        "nli_confidence": kwargs.get("nli_confidence", 0.85)
    }

    # Add additional kwargs
    evidence_data.update({k: v for k, v in kwargs.items()
                         if k not in evidence_data})

    evidence = Evidence(**evidence_data)
    session.add(evidence)
    session.commit()
    session.refresh(evidence)

    return evidence


# ==================== BATCH FACTORIES ====================

def create_check_with_full_pipeline_data(
    session,
    user_id: str = "test_user_123",
    num_claims: int = 3,
    num_evidence_per_claim: int = 3
) -> Any:
    """
    Create a complete check with claims and evidence

    Simulates a full pipeline run with realistic data

    Args:
        session: Database session
        user_id: User Clerk ID
        num_claims: Number of claims
        num_evidence_per_claim: Evidence items per claim

    Returns:
        Check model instance with full data

    Created: 2025-11-03
    """
    # Create check
    check = create_completed_check(
        session,
        user_id=user_id,
        num_claims=num_claims,
        decision_trail=json.dumps([
            {"stage": "ingest", "duration_ms": 1200, "status": "success"},
            {"stage": "extract", "duration_ms": 2500, "status": "success", "claims_found": num_claims},
            {"stage": "retrieve", "duration_ms": 3000, "status": "success", "evidence_found": num_claims * num_evidence_per_claim},
            {"stage": "verify", "duration_ms": 1500, "status": "success"},
            {"stage": "judge", "duration_ms": 800, "status": "success"}
        ]),
        transparency_score=0.88
    )

    # Add evidence to each claim
    for claim in check.claims:
        for i in range(num_evidence_per_claim):
            create_test_evidence(
                session,
                claim_id=claim.id,
                source=f"Source {i+1}",
                url=f"https://example{i+1}.com/article",
                relevance_score=0.9 - (i * 0.05),
                credibility_score=0.85 - (i * 0.05)
            )

    return check


# ==================== SCENARIO FACTORIES ====================

def create_insufficient_evidence_check(session, user_id: str = "test_user_123") -> Any:
    """
    Create a check that results in insufficient evidence

    Created: 2025-11-03
    """
    check = create_test_check(
        session,
        user_id=user_id,
        status="completed",
        claims_supported=0,
        claims_contradicted=0,
        claims_uncertain=0
    )

    claim = create_test_claim(
        session,
        check_id=check.id,
        verdict="insufficient_evidence",
        confidence=0.20,
        rationale="Only 2 low-quality sources found, below minimum threshold of 3"
    )

    # Add only 2 low-quality evidence items
    for i in range(2):
        create_test_evidence(
            session,
            claim_id=claim.id,
            credibility_score=0.50,
            tier="blog"
        )

    return check


def create_conflicting_evidence_check(session, user_id: str = "test_user_123") -> Any:
    """
    Create a check with conflicting high-credibility sources

    Created: 2025-11-03
    """
    check = create_test_check(
        session,
        user_id=user_id,
        status="completed"
    )

    claim = create_test_claim(
        session,
        check_id=check.id,
        verdict="conflicting_expert_opinion",
        confidence=0.35,
        rationale="High-credibility sources disagree on this claim"
    )

    # Add conflicting evidence
    create_test_evidence(
        session,
        claim_id=claim.id,
        source="NASA",
        credibility_score=0.95,
        nli_stance="supporting"
    )

    create_test_evidence(
        session,
        claim_id=claim.id,
        source="NOAA",
        credibility_score=0.93,
        nli_stance="contradicting"
    )

    return check


# ==================== HELPER FUNCTIONS ====================

def cleanup_test_data(session):
    """
    Clean up all test data from database

    Created: 2025-11-03
    """
    if not MODELS_AVAILABLE:
        return

    session.query(Evidence).delete()
    session.query(Claim).delete()
    session.query(Check).delete()
    session.query(User).delete()
    session.commit()


def create_test_user_with_checks(
    session,
    clerk_id: str = "test_user_123",
    num_checks: int = 5
) -> Any:
    """
    Create a user with multiple checks

    Args:
        session: Database session
        clerk_id: User ID
        num_checks: Number of checks to create

    Returns:
        User model instance

    Created: 2025-11-03
    """
    user = create_test_user(session, clerk_id=clerk_id)

    for i in range(num_checks):
        create_test_check(
            session,
            user_id=clerk_id,
            input_content=f"Test content {i+1}",
            status="completed" if i % 2 == 0 else "processing"
        )

    return user


# ==================== DOCUMENTATION ====================

"""
Usage Examples:

1. Simple Check Creation:
    from database import create_test_check
    check = create_test_check(db_session, status="completed")

2. Full Pipeline Data:
    from database import create_check_with_full_pipeline_data
    check = create_check_with_full_pipeline_data(
        db_session,
        num_claims=4,
        num_evidence_per_claim=5
    )

3. Specific Scenarios:
    from database import create_insufficient_evidence_check
    check = create_insufficient_evidence_check(db_session)

4. User with Checks:
    from database import create_test_user_with_checks
    user = create_test_user_with_checks(db_session, num_checks=10)

5. Cleanup:
    from database import cleanup_test_data
    cleanup_test_data(db_session)

6. Custom Check:
    from database import create_test_check, create_test_claim
    check = create_test_check(
        db_session,
        input_type="url",
        status="completed",
        credibility_score=0.92
    )
    claim = create_test_claim(
        db_session,
        check_id=check.id,
        text="Custom claim text",
        verdict="supported"
    )
"""

# ==================== VERSION HISTORY ====================
# v1.0.0 - 2025-11-03 - Initial database factory library
#          - User factories
#          - Check factories (simple, completed, with claims)
#          - Claim factories
#          - Evidence factories
#          - Batch factories (full pipeline data)
#          - Scenario factories (insufficient evidence, conflicting evidence)
#          - Helper functions (cleanup, user with checks)
