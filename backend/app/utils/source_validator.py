"""
Source Validator - Content-Type Heuristic Filtering
Filters out inappropriate sources before NLI verification
"""
import logging
import re
from typing import List, Dict, Any, Tuple

logger = logging.getLogger(__name__)

class SourceValidator:
    """Validate source appropriateness using heuristic pattern matching"""

    def __init__(self):
        # Educational materials (inappropriate for fact-checking)
        self.educational_patterns = [
            r'\b(revision guide|study guide|exam prep|test prep)\b',
            r'\b(student notes|class notes|lecture notes|course materials)\b',
            r'\b(homework|coursework|assignment|quiz|worksheet)\b',
            r'\b(gcse|a-level|ks[0-9]|year [0-9]{1,2} |y[0-9]{1,2} )\b',
            r'\bpaper [0-9]+ revision\b',
            r'\bexam board\b',
        ]

        # Low-quality or user-generated content
        self.low_quality_patterns = [
            r'\b(forum|discussion board|comment section)\b',
            r'\b(blog post|personal blog|opinion piece|editorial)\b',
            r'\b(promotional|advertisement|marketing|press release)\b',
            r'\buser[ -]?(generated|submitted|uploaded)\b',
            r'\b(wiki\b|reddit|quora|yahoo answers)\b',
        ]

        # URL structure patterns (educational domains)
        self.url_education_patterns = [
            r'/students?/',
            r'/revision/',
            r'/uploads/',
            r'/resources/ks[0-9]',
            r'/exam-?prep/',
            r'/study-?guides?/',
            r'/education/',  # Unless it's .gov or authoritative
        ]

        # Authoritative education domains (ALLOWED despite /education/ in URL)
        self.authoritative_education_domains = [
            'gov.uk', 'gov', 'education.gov.uk',
            'ofsted.gov.uk', 'ofqual.gov.uk',
            'ed.gov', 'department-for-education.gov.uk'
        ]

    def validate_sources(self, evidence_list: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Filter out inappropriate sources using heuristic patterns.

        Args:
            evidence_list: List of evidence dictionaries

        Returns:
            Tuple of (filtered_list, stats_dict)
        """
        validated = []
        filtered_out = []

        for evidence in evidence_list:
            title = evidence.get('title', '').lower()
            url = evidence.get('url', '').lower()
            source = evidence.get('source', '').lower()

            # Combine text for pattern matching
            combined_text = f"{title} {url} {source}"

            # Check if inappropriate
            is_inappropriate, reason = self._is_inappropriate(combined_text, url)

            if is_inappropriate:
                filtered_out.append({
                    'title': evidence.get('title'),
                    'url': evidence.get('url'),
                    'reason': reason
                })
                logger.info(f"Filtered out source: {evidence.get('title')[:50]} - Reason: {reason}")
            else:
                validated.append(evidence)

        stats = {
            'original_count': len(evidence_list),
            'validated_count': len(validated),
            'filtered_count': len(filtered_out),
            'filtered_sources': filtered_out
        }

        return validated, stats

    def _is_inappropriate(self, combined_text: str, url: str) -> Tuple[bool, str]:
        """
        Check if source is inappropriate using pattern matching.

        Returns:
            Tuple of (is_inappropriate: bool, reason: str)
        """
        # Check educational material patterns
        for pattern in self.educational_patterns:
            if re.search(pattern, combined_text, re.IGNORECASE):
                return True, f"Educational material detected (pattern: {pattern[:30]})"

        # Check low-quality patterns
        for pattern in self.low_quality_patterns:
            if re.search(pattern, combined_text, re.IGNORECASE):
                return True, f"Low-quality source detected (pattern: {pattern[:30]})"

        # Check URL structure patterns (unless authoritative domain)
        if not self._is_authoritative_education_domain(url):
            for pattern in self.url_education_patterns:
                if re.search(pattern, url, re.IGNORECASE):
                    return True, f"Educational URL structure (pattern: {pattern})"

        return False, ""

    def _is_authoritative_education_domain(self, url: str) -> bool:
        """Check if domain is an authoritative education source (e.g., gov.uk/education)"""
        for domain in self.authoritative_education_domains:
            if domain in url:
                return True
        return False

# Singleton instance
_validator_instance = None

def get_source_validator() -> SourceValidator:
    """Get singleton SourceValidator instance"""
    global _validator_instance
    if _validator_instance is None:
        _validator_instance = SourceValidator()
    return _validator_instance
