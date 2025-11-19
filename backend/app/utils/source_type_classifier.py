"""
Source Type Classifier Module

Classifies evidence sources as primary/secondary/tertiary for credibility weighting.

Source Types:
- PRIMARY: Original research, government data, legal docs, official reports
- SECONDARY: News reporting on primary sources
- TERTIARY: Fact-checks, encyclopedias (meta-content)

Author: Tru8 Development Team
Date: 2025-01-17
"""

import re
from typing import Dict, List
from urllib.parse import urlparse
import logging

logger = logging.getLogger(__name__)


class SourceTypeClassifier:
    """
    Classify evidence sources as primary/secondary/tertiary.

    Primary sources are original materials (research papers, government data, legal docs).
    Secondary sources are news articles reporting on primary sources.
    Tertiary sources are meta-content (fact-checks, encyclopedias).
    """

    def __init__(self):
        """Initialize classifier with pattern dictionaries."""

        # Primary source indicators
        self.primary_patterns = {
            'academic_journal': [
                r'doi\.org',
                r'journal',
                r'\.edu/.*publication',
                r'nature\.com',
                r'science\.org',
                r'cell\.com',
                r'plos\.org',
                r'jama\.',
                r'nejm\.org',
                r'thelancet\.com',
                r'springer\.com',
                r'wiley\.com',
                r'academic\.oup\.com',
                r'sciencedirect\.com'
            ],
            'government_data': [
                r'\.gov/.*data',
                r'\.gov/.*statistics',
                r'census\.gov',
                r'ons\.gov\.uk',
                r'data\.gov',
                r'\.gov/.*report',
                r'bls\.gov',
                r'bea\.gov',
                r'eia\.gov'
            ],
            'research_institution': [
                r'\.edu',
                r'\.ac\.uk',
                r'research\.',
                r'institute\.',
                r'nber\.org',
                r'brookings\.edu',
                r'rand\.org'
            ],
            'official_report': [
                r'whitehouse\.gov',
                r'parliament\.uk',
                r'congress\.gov',
                r'fda\.gov',
                r'cdc\.gov',
                r'who\.int',
                r'un\.org',
                r'europa\.eu',
                r'gov\.uk/government/publications'
            ],
            'legal_source': [
                r'supremecourt\.gov',
                r'govinfo\.gov',
                r'congress\.gov/bill',
                r'law\.cornell\.edu',
                r'justia\.com/cases'
            ]
        }

        # Secondary source indicators (news media)
        self.secondary_patterns = [
            r'bbc\.',
            r'reuters\.',
            r'apnews\.',
            r'guardian\.',
            r'nytimes\.',
            r'telegraph\.',
            r'washingtonpost\.',
            r'ft\.com',
            r'economist\.com',
            r'bloomberg\.com',
            r'/news/',
            r'/article/',
            r'/story/'
        ]

        # Tertiary source indicators (meta-content)
        self.tertiary_patterns = [
            r'wikipedia\.',
            r'snopes\.',
            r'factcheck\.org',
            r'politifact\.',
            r'fullfact\.',
            r'factcheck\.afp\.com',
            r'apnews\.com/APFactCheck'
        ]

        # Peer-review content indicators
        self.peer_review_indicators = [
            'published in',
            'journal of',
            'peer reviewed',
            'peer-reviewed',
            'doi:',
            'vol.',
            'volume',
            'issue',
            'abstract:',
            'methods:',
            'methodology',
            'cited by'
        ]

        # Statistical report indicators
        self.statistical_indicators = [
            'statistics',
            'census',
            'survey data',
            'annual report',
            'official figures',
            'dataset',
            'data release',
            'statistical bulletin',
            'official statistics'
        ]

    def classify_source(self, url: str, title: str = "", snippet: str = "") -> Dict:
        """
        Classify source type and detect primary source indicators.

        Args:
            url: Source URL
            title: Article/document title
            snippet: Text snippet from the source

        Returns:
            {
                'source_type': 'primary|secondary|tertiary|unknown',
                'primary_indicators': ['academic_journal', 'peer_reviewed'],
                'is_original_research': bool,
                'credibility_boost': float
            }
        """
        if not url:
            return self._unknown_source()

        try:
            url_lower = url.lower()
            title_lower = title.lower() if title else ""
            snippet_lower = snippet.lower() if snippet else ""

            # Check primary source patterns
            primary_indicators = []
            for category, patterns in self.primary_patterns.items():
                if any(re.search(pattern, url_lower) for pattern in patterns):
                    primary_indicators.append(category)
                    logger.debug(f"Primary indicator detected: {category} in {url[:50]}")

            # Check content indicators
            if self._is_peer_reviewed(title_lower, snippet_lower):
                primary_indicators.append('peer_reviewed')
            if self._is_statistical_report(title_lower, snippet_lower):
                primary_indicators.append('statistical_report')

            # Determine source type and credibility boost
            if primary_indicators:
                source_type = 'primary'
                credibility_boost = 0.25  # +25% credibility
                logger.info(f"Primary source detected: {primary_indicators} for {url[:60]}")

            elif any(re.search(p, url_lower) for p in self.tertiary_patterns):
                source_type = 'tertiary'
                credibility_boost = -0.15  # -15% (meta-content)
                logger.debug(f"Tertiary source detected: {url[:60]}")

            elif any(re.search(p, url_lower) for p in self.secondary_patterns):
                source_type = 'secondary'
                credibility_boost = 0.0  # Neutral
                logger.debug(f"Secondary source detected: {url[:60]}")

            else:
                source_type = 'unknown'
                credibility_boost = 0.0

            # Determine if original research
            is_original_research = (
                'academic_journal' in primary_indicators or
                'peer_reviewed' in primary_indicators or
                'research_institution' in primary_indicators
            )

            return {
                'source_type': source_type,
                'primary_indicators': primary_indicators,
                'is_original_research': is_original_research,
                'credibility_boost': credibility_boost
            }

        except Exception as e:
            logger.error(f"Source classification failed for {url}: {e}")
            return self._unknown_source()

    def _is_peer_reviewed(self, title: str, snippet: str) -> bool:
        """
        Detect peer-reviewed research from content.

        Args:
            title: Document title
            snippet: Text snippet

        Returns:
            True if content indicates peer-reviewed research
        """
        combined = title + " " + snippet
        matches = sum(1 for ind in self.peer_review_indicators if ind in combined)
        return matches >= 2  # Require at least 2 indicators

    def _is_statistical_report(self, title: str, snippet: str) -> bool:
        """
        Detect statistical/data reports.

        Args:
            title: Document title
            snippet: Text snippet

        Returns:
            True if content indicates statistical report
        """
        combined = title + " " + snippet
        return any(ind in combined for ind in self.statistical_indicators)

    def _unknown_source(self) -> Dict:
        """
        Return default classification for unknown sources.

        Returns:
            Default classification dict
        """
        return {
            'source_type': 'unknown',
            'primary_indicators': [],
            'is_original_research': False,
            'credibility_boost': 0.0
        }

    def get_source_quality_label(self, source_type: str, is_original_research: bool) -> str:
        """
        Get human-readable quality label for source.

        Args:
            source_type: Classification type
            is_original_research: Whether source is original research

        Returns:
            Quality label string
        """
        if is_original_research:
            return "Original Research"
        elif source_type == 'primary':
            return "Primary Source"
        elif source_type == 'secondary':
            return "News Report"
        elif source_type == 'tertiary':
            return "Meta-Analysis"
        else:
            return "General Source"


# Singleton instance for reuse
_classifier_instance = None


def get_source_type_classifier() -> SourceTypeClassifier:
    """
    Get singleton SourceTypeClassifier instance.

    Returns:
        SourceTypeClassifier instance
    """
    global _classifier_instance
    if _classifier_instance is None:
        _classifier_instance = SourceTypeClassifier()
    return _classifier_instance
