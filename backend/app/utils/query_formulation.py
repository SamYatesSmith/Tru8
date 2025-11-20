"""
Query Formulation Enhancement Module

Transforms vague claims into optimized search queries for better evidence retrieval.

Key Improvements:
1. Entity-focused boosting (extracts key entities from claims)
2. Temporal refinement (adds year for time-sensitive claims)
3. Query term extraction (important nouns/verbs only)
4. Search syntax optimization (site: filters, exclusions)

Author: Tru8 Development Team
Date: 2025-01-17
"""

import re
import spacy
from typing import Dict, List, Optional
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class QueryFormulator:
    """
    Enhanced query formulation for evidence retrieval.
    Transforms claims into optimized search queries.
    """

    def __init__(self):
        """Initialize QueryFormulator with spaCy model."""
        try:
            self.nlp = spacy.load("en_core_web_sm")
            logger.info("QueryFormulator initialized with spaCy model")
        except Exception as e:
            logger.error(f"Failed to load spaCy model: {e}")
            logger.warning("Query formulation will use fallback mode")
            self.nlp = None

    def formulate_query(
        self,
        claim: str,
        subject_context: Optional[str] = None,
        key_entities: Optional[List[str]] = None,
        temporal_analysis: Optional[Dict] = None,
        article_title: Optional[str] = None,
        article_date: Optional[str] = None
    ) -> str:
        """
        Create optimized search query from claim.

        Improvements:
        1. Entity-focused boosting (use key_entities from extraction)
        2. Temporal refinement (add year for time-sensitive claims)
        3. Query term extraction (important nouns/verbs only)
        4. Search syntax optimization (site: filters, exclusions)
        5. Article context grounding (add title entities and date for specificity)

        Args:
            claim: Original claim text
            subject_context: Main subject/topic from extraction
            key_entities: Key entities from extraction (names, orgs, places)
            temporal_analysis: Temporal analysis from claim extraction
            article_title: Title of source article (for context grounding)
            article_date: Publication date of source article (for temporal context)

        Returns:
            Optimized search query string (max 250 chars for API limits)
        """
        if not claim:
            return ""

        try:
            # If spaCy not available, use fallback
            if not self.nlp:
                return self._fallback_query(claim, key_entities, temporal_analysis, article_title, article_date)

            # Parse claim with spaCy
            doc = self.nlp(claim)

            # Extract core query terms (entities + important nouns/verbs)
            query_terms = self._extract_query_terms(doc, key_entities)

            # Apply temporal refinement if claim is time-sensitive
            if temporal_analysis and temporal_analysis.get('is_time_sensitive'):
                temporal_terms = self._add_temporal_refinement(temporal_analysis)
                query_terms.extend(temporal_terms)

            # Apply article context grounding (Phase 2.2 & 2.3)
            if article_title or article_date:
                article_terms = self._add_article_context(
                    claim,
                    article_title,
                    article_date,
                    query_terms
                )
                query_terms.extend(article_terms)

            # Build final query
            query = " ".join(query_terms)

            # Note: Previously filtered to .gov/.edu/.org but this EXCLUDED news sources
            # For news-based claims, we NEED NYT, BBC, Reuters, etc.
            # Credibility filtering happens downstream in retrieve.py

            # Exclude fact-check meta-content (avoid circular fact-checking)
            query += ' -site:snopes.com -site:factcheck.org -"fact check"'

            # Enforce API limit
            final_query = query[:250]

            logger.debug(f"Enhanced query formulation: '{claim[:50]}...' -> '{final_query[:80]}...'")
            return final_query

        except Exception as e:
            logger.error(f"Query formulation failed: {e}, using fallback")
            return self._fallback_query(claim, key_entities, temporal_analysis, article_title, article_date)

    def _extract_query_terms(self, doc, key_entities: Optional[List[str]]) -> List[str]:
        """
        Extract important terms for query.

        Args:
            doc: spaCy Doc object
            key_entities: Pre-extracted entities from claim extraction

        Returns:
            List of important query terms
        """
        terms = []

        # Priority 1: Named entities (from extraction or spaCy)
        if key_entities:
            # Use entities from extraction phase (more accurate)
            terms.extend(key_entities[:3])  # Top 3 entities
        else:
            # Fall back to spaCy entity extraction
            entities = [
                ent.text for ent in doc.ents
                if ent.label_ in ['PERSON', 'ORG', 'GPE', 'DATE', 'MONEY', 'LAW', 'EVENT']
            ]
            terms.extend(entities[:3])

        # Priority 2: Important nouns/verbs (content words)
        content_words = [
            token.text for token in doc
            if token.pos_ in ['NOUN', 'PROPN', 'VERB']
            and not token.is_stop
            and len(token.text) > 3
            and token.text.isalpha()  # Exclude numbers/punctuation
        ]
        terms.extend(content_words[:5])

        # Deduplicate while preserving order
        # Also track individual words to avoid "Biden Biden" + "Biden" duplication
        seen = set()
        seen_words = set()
        unique_terms = []

        for term in terms:
            term_lower = term.lower()
            # Skip if we've seen this exact term
            if term_lower in seen:
                continue

            # For multi-word terms, check if all words have been seen individually
            words = term_lower.split()
            if len(words) > 1:
                # Multi-word entity like "Biden Biden" or "New York"
                # Check if all individual words have been seen
                if all(word in seen_words for word in words):
                    continue  # Skip since all words already represented
                # Add all words to seen_words
                seen_words.update(words)
            else:
                # Single word
                if term_lower in seen_words:
                    continue  # Skip if word already seen
                seen_words.add(term_lower)

            seen.add(term_lower)
            unique_terms.append(term)

        return unique_terms

    def _add_temporal_refinement(self, temporal_analysis: Dict) -> List[str]:
        """
        Add year/date terms for time-sensitive claims.

        Args:
            temporal_analysis: Temporal analysis from claim extraction

        Returns:
            List of temporal terms to add to query
        """
        temporal_terms = []

        try:
            # Extract year markers
            markers = temporal_analysis.get('temporal_markers', [])
            for marker in markers:
                if marker.get('type') == 'YEAR':
                    year = str(marker.get('value'))
                    if year and year.isdigit() and len(year) == 4:
                        temporal_terms.append(year)

            # Add temporal window (e.g., "2024" for recent claims)
            window = temporal_analysis.get('temporal_window')
            if window and isinstance(window, str) and window.startswith('year_'):
                year = window.replace('year_', '')
                if year.isdigit() and year not in temporal_terms:
                    temporal_terms.append(year)

        except Exception as e:
            logger.error(f"Temporal refinement failed: {e}")

        return temporal_terms

    def _add_article_context(
        self,
        claim: str,
        article_title: Optional[str],
        article_date: Optional[str],
        existing_query_terms: List[str]
    ) -> List[str]:
        """
        Extract context from article title and date for query grounding.

        Phase 2.2: Extract entities from article title that aren't in claim
        Phase 2.3: Add article year for recent articles

        Args:
            claim: Original claim text
            article_title: Title of source article
            article_date: Publication date (ISO format string or date object)
            existing_query_terms: Already extracted query terms

        Returns:
            List of additional terms from article context
        """
        article_terms = []

        try:
            # Phase 2.2: Extract entities from article title
            if article_title and self.nlp:
                # Parse article title with spaCy
                title_doc = self.nlp(article_title)

                # Extract named entities from title
                title_entities = [
                    ent.text for ent in title_doc.ents
                    if ent.label_ in ['PERSON', 'ORG', 'GPE', 'EVENT', 'LAW']
                ]

                # Add entities NOT already in claim or existing query terms
                claim_lower = claim.lower()
                existing_lower = [term.lower() for term in existing_query_terms]

                for entity in title_entities[:3]:  # Top 3 entities from title
                    entity_lower = entity.lower()
                    # Check if entity not already in claim or query
                    if entity_lower not in claim_lower and entity_lower not in existing_lower:
                        article_terms.append(entity)
                        logger.debug(f"Added title entity to query: {entity}")

            # Phase 2.3: Add article year for recent articles
            if article_date:
                try:
                    # Parse date (handle ISO string or datetime)
                    if isinstance(article_date, str):
                        # Try parsing ISO format
                        if 'T' in article_date:
                            pub_date = datetime.fromisoformat(article_date.replace('Z', '+00:00'))
                        else:
                            # Try simple YYYY-MM-DD format
                            pub_date = datetime.strptime(article_date[:10], '%Y-%m-%d')
                    else:
                        pub_date = article_date

                    # Add year if article is recent (within last 2 years)
                    days_old = (datetime.now() - pub_date).days
                    if days_old < 730:  # ~2 years
                        year = str(pub_date.year)
                        if year not in existing_query_terms:
                            article_terms.append(year)
                            logger.debug(f"Added article year to query: {year}")

                except Exception as date_error:
                    logger.debug(f"Could not parse article date '{article_date}': {date_error}")

        except Exception as e:
            logger.error(f"Article context extraction failed: {e}")

        return article_terms

    def _fallback_query(
        self,
        claim: str,
        key_entities: Optional[List[str]],
        temporal_analysis: Optional[Dict],
        article_title: Optional[str] = None,
        article_date: Optional[str] = None
    ) -> str:
        """
        Fallback query formulation when spaCy unavailable.

        Args:
            claim: Original claim
            key_entities: Entities from extraction
            temporal_analysis: Temporal context
            article_title: Title of source article
            article_date: Publication date of source article

        Returns:
            Basic optimized query
        """
        query_parts = [claim]

        # Add entities if available
        if key_entities:
            query_parts.extend(key_entities[:2])

        # Add year if time-sensitive
        if temporal_analysis and temporal_analysis.get('is_time_sensitive'):
            markers = temporal_analysis.get('temporal_markers', [])
            for marker in markers:
                if marker.get('type') == 'YEAR':
                    query_parts.append(str(marker.get('value')))
                    break

        # Add article year if available (basic version of Phase 2.3)
        if article_date:
            try:
                # Extract year from date string
                if isinstance(article_date, str):
                    # Try to extract year (first 4 digits)
                    year_match = re.search(r'\d{4}', article_date)
                    if year_match:
                        year = year_match.group()
                        query_parts.append(year)
            except Exception:
                pass

        query = " ".join(query_parts)

        # Add basic filters
        query += ' -site:snopes.com -site:factcheck.org'

        return query[:250]


# Singleton instance for reuse (spaCy model loaded once)
_query_formulator_instance = None


def get_query_formulator() -> QueryFormulator:
    """
    Get singleton QueryFormulator instance.

    Returns:
        QueryFormulator instance
    """
    global _query_formulator_instance
    if _query_formulator_instance is None:
        _query_formulator_instance = QueryFormulator()
    return _query_formulator_instance
