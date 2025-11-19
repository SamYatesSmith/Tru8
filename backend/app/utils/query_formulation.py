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
        temporal_analysis: Optional[Dict] = None
    ) -> str:
        """
        Create optimized search query from claim.

        Improvements:
        1. Entity-focused boosting (use key_entities from extraction)
        2. Temporal refinement (add year for time-sensitive claims)
        3. Query term extraction (important nouns/verbs only)
        4. Search syntax optimization (site: filters, exclusions)

        Args:
            claim: Original claim text
            subject_context: Main subject/topic from extraction
            key_entities: Key entities from extraction (names, orgs, places)
            temporal_analysis: Temporal analysis from claim extraction

        Returns:
            Optimized search query string (max 250 chars for API limits)
        """
        if not claim:
            return ""

        try:
            # If spaCy not available, use fallback
            if not self.nlp:
                return self._fallback_query(claim, key_entities, temporal_analysis)

            # Parse claim with spaCy
            doc = self.nlp(claim)

            # Extract core query terms (entities + important nouns/verbs)
            query_terms = self._extract_query_terms(doc, key_entities)

            # Apply temporal refinement if claim is time-sensitive
            if temporal_analysis and temporal_analysis.get('is_time_sensitive'):
                temporal_terms = self._add_temporal_refinement(temporal_analysis)
                query_terms.extend(temporal_terms)

            # Build final query
            query = " ".join(query_terms)

            # Add source type filters (prefer primary sources)
            query += ' (site:.gov OR site:.edu OR site:.org OR "study" OR "research")'

            # Exclude fact-check meta-content
            query += ' -site:snopes.com -site:factcheck.org -"fact check"'

            # Enforce API limit
            final_query = query[:250]

            logger.debug(f"Enhanced query formulation: '{claim[:50]}...' -> '{final_query[:80]}...'")
            return final_query

        except Exception as e:
            logger.error(f"Query formulation failed: {e}, using fallback")
            return self._fallback_query(claim, key_entities, temporal_analysis)

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

    def _fallback_query(
        self,
        claim: str,
        key_entities: Optional[List[str]],
        temporal_analysis: Optional[Dict]
    ) -> str:
        """
        Fallback query formulation when spaCy unavailable.

        Args:
            claim: Original claim
            key_entities: Entities from extraction
            temporal_analysis: Temporal context

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
