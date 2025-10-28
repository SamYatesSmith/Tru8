"""
Source Monitoring Service

Progressive Curation System - Phase 1
Logs unknown sources for weekly manual review and database expansion.
"""

import logging
import tldextract
from datetime import datetime
from typing import Dict, Any, Optional
from sqlmodel import Session, select
from app.models.unknown_source import UnknownSource

logger = logging.getLogger(__name__)


class SourceMonitor:
    """
    Monitor and track unknown sources for progressive curation.

    Usage:
        monitor = SourceMonitor(db_session)
        monitor.log_unknown_source(
            url="https://newsite.com/article",
            claim_topic="Climate change",
            evidence_title="Study shows warming",
            evidence_snippet="New research..."
        )
    """

    def __init__(self, session: Session):
        """
        Initialize source monitor with database session.

        Args:
            session: SQLModel database session (sync)
        """
        self.session = session

    def log_unknown_source(
        self,
        url: str,
        claim_topic: Optional[str] = None,
        evidence_title: Optional[str] = None,
        evidence_snippet: Optional[str] = None,
        has_https: bool = False,
        has_author_byline: Optional[bool] = None,
        has_primary_sources: Optional[bool] = None
    ) -> None:
        """
        Log an unknown source for later review.

        If domain already logged, increments frequency and updates last_seen.
        If new domain, creates new tracking record.

        Args:
            url: Full URL of the evidence source
            claim_topic: Topic/subject of the claim (for context)
            evidence_title: Title of the evidence article
            evidence_snippet: Snippet for context (truncated to 500 chars)
            has_https: Whether URL uses HTTPS
            has_author_byline: Whether article has author attribution
            has_primary_sources: Whether article cites primary sources
        """
        try:
            # Extract domain from URL
            parsed = tldextract.extract(url)
            domain = parsed.registered_domain.lower()

            if not domain:
                logger.warning(f"Could not extract domain from URL: {url}")
                return

            # Check if domain already tracked
            stmt = select(UnknownSource).where(UnknownSource.domain == domain)
            existing = self.session.exec(stmt).first()

            if existing:
                # Update existing record
                existing.frequency += 1
                existing.last_seen = datetime.utcnow()
                # Update context if not already set
                if not existing.claim_topic and claim_topic:
                    existing.claim_topic = claim_topic
                if not existing.evidence_title and evidence_title:
                    existing.evidence_title = evidence_title
                logger.info(f"Updated unknown source: {domain} (frequency: {existing.frequency})")
            else:
                # Create new tracking record
                unknown_source = UnknownSource(
                    domain=domain,
                    full_url=url,
                    claim_topic=claim_topic,
                    evidence_title=evidence_title,
                    evidence_snippet=evidence_snippet[:500] if evidence_snippet else None,
                    has_https=has_https,
                    has_author_byline=has_author_byline,
                    has_primary_sources=has_primary_sources,
                    frequency=1,
                    first_seen=datetime.utcnow(),
                    last_seen=datetime.utcnow()
                )
                self.session.add(unknown_source)
                logger.info(f"Logged new unknown source: {domain}")

            self.session.commit()

        except Exception as e:
            logger.error(f"Failed to log unknown source {url}: {e}")
            self.session.rollback()

    def get_trending_unknowns(self, min_frequency: int = 3, limit: int = 50) -> list[UnknownSource]:
        """
        Get unknown sources that appear frequently (for weekly review).

        Args:
            min_frequency: Minimum number of appearances to include
            limit: Maximum number of results to return

        Returns:
            List of UnknownSource records sorted by frequency (descending)
        """
        stmt = (
            select(UnknownSource)
            .where(UnknownSource.frequency >= min_frequency)
            .where(UnknownSource.reviewed == False)
            .order_by(UnknownSource.frequency.desc())
            .limit(limit)
        )
        results = self.session.exec(stmt).all()
        return list(results)

    def get_unreviewed_count(self) -> int:
        """
        Get count of unreviewed unknown sources.

        Returns:
            Count of unreviewed sources
        """
        from sqlalchemy import func
        stmt = select(func.count(UnknownSource.id)).where(UnknownSource.reviewed == False)
        count = self.session.exec(stmt).one()
        return count

    def mark_as_reviewed(
        self,
        domain: str,
        assigned_tier: Optional[str] = None,
        assigned_credibility: Optional[float] = None,
        notes: Optional[Dict[str, Any]] = None,
        added_to_list: bool = False
    ) -> None:
        """
        Mark unknown source as reviewed after manual curation.

        Args:
            domain: Domain that was reviewed
            assigned_tier: Tier assigned (e.g., 'news_tier2')
            assigned_credibility: Credibility score assigned (0.0-1.0)
            notes: Admin notes about the decision
            added_to_list: Whether source was added to source_credibility.json
        """
        stmt = select(UnknownSource).where(UnknownSource.domain == domain)
        source = self.session.exec(stmt).first()

        if source:
            source.reviewed = True
            source.assigned_tier = assigned_tier
            source.assigned_credibility = assigned_credibility
            source.review_notes = notes
            source.added_to_credibility_list = added_to_list
            self.session.commit()
            logger.info(f"Marked {domain} as reviewed (tier: {assigned_tier}, added: {added_to_list})")
        else:
            logger.warning(f"Unknown source not found for review: {domain}")

    def get_sources_by_topic(self, topic: str) -> list[UnknownSource]:
        """
        Get unknown sources related to a specific topic.

        Useful for topic-based expansion (e.g., "climate" claims increasing,
        review climate-related unknown sources).

        Args:
            topic: Topic keyword to search for

        Returns:
            List of UnknownSource records matching topic
        """
        stmt = (
            select(UnknownSource)
            .where(UnknownSource.claim_topic.contains(topic))
            .where(UnknownSource.reviewed == False)
            .order_by(UnknownSource.frequency.desc())
        )
        results = self.session.exec(stmt).all()
        return list(results)


# Singleton instance for reuse
_source_monitor = None

def get_source_monitor(session: Session) -> SourceMonitor:
    """
    Get SourceMonitor instance for session.

    Note: Not a true singleton since each session is different,
    but pattern allows for future caching if needed.

    Args:
        session: Database session

    Returns:
        SourceMonitor instance
    """
    return SourceMonitor(session)
