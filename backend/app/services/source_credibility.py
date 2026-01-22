"""
Source Credibility Service

Centralized source credibility management system.
Single source of truth for domain reputation assessment.

Phase 3 - Week 9: Domain Credibility Framework
"""

import json
import tldextract
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from functools import lru_cache
from urllib.parse import urlparse
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

# Domain suffix to jurisdiction mapping for geographic boosting
DOMAIN_JURISDICTION_MAP = {
    # Nordic countries
    ".dk": "DK",  # Denmark
    ".gl": "GL",  # Greenland
    ".ag": "GL",  # Greenland media (sermitsiaq.ag, etc.) - uses .ag TLD
    ".no": "NO",  # Norway
    ".se": "SE",  # Sweden
    ".fi": "FI",  # Finland
    ".is": "IS",  # Iceland
    ".fo": "FO",  # Faroe Islands
    # Major European
    ".uk": "UK",
    ".co.uk": "UK",
    ".de": "DE",  # Germany
    ".fr": "FR",  # France
    ".es": "ES",  # Spain
    ".it": "IT",  # Italy
    ".nl": "NL",  # Netherlands
    ".be": "BE",  # Belgium
    ".at": "AT",  # Austria
    ".ch": "CH",  # Switzerland
    ".pl": "PL",  # Poland
    ".ie": "IE",  # Ireland
    ".pt": "PT",  # Portugal
    ".gr": "GR",  # Greece
    ".cz": "CZ",  # Czech Republic
    ".hu": "HU",  # Hungary
    # Americas
    ".us": "US",
    ".com": "US",  # Default .com to US (can be overridden)
    ".ca": "CA",  # Canada
    ".mx": "MX",  # Mexico
    ".br": "BR",  # Brazil
    ".ar": "AR",  # Argentina
    # Asia-Pacific
    ".au": "AU",  # Australia
    ".nz": "NZ",  # New Zealand
    ".jp": "JP",  # Japan
    ".kr": "KR",  # South Korea
    ".cn": "CN",  # China
    ".in": "IN",  # India
    ".sg": "SG",  # Singapore
    # Middle East / Africa
    ".il": "IL",  # Israel
    ".za": "ZA",  # South Africa
    ".ae": "AE",  # UAE
    # International
    ".eu": "EU",
    ".int": "INTL",
    ".org": "INTL",  # Many orgs are international
}

# Jurisdiction groupings for "near match" boosting
JURISDICTION_GROUPS = {
    # Nordic group - stories about one Nordic country benefit from other Nordic sources
    "NORDIC": ["DK", "GL", "NO", "SE", "FI", "IS", "FO"],
    # EU group
    "EU": ["DE", "FR", "ES", "IT", "NL", "BE", "AT", "PL", "IE", "PT", "GR", "CZ", "HU", "DK", "SE", "FI"],
    # Anglosphere
    "ANGLO": ["UK", "US", "CA", "AU", "NZ", "IE"],
}

# Credibility boost amounts
JURISDICTION_BOOST_EXACT = 0.12  # Source country matches story country exactly
JURISDICTION_BOOST_GROUP = 0.06  # Source country is in same regional group


class SourceCredibilityService:
    """
    Centralized source credibility management.

    Provides:
    - Tiered credibility scoring (0.0 - 1.0)
    - Risk flag assessment
    - Auto-exclusion for satire/unreliable sources
    - Transparent reasoning for all scores

    Usage:
        service = SourceCredibilityService()
        cred_info = service.get_credibility("BBC News", "https://bbc.co.uk/news/123")
        # Returns: {'tier': 'news_tier1', 'credibility': 0.9, ...}
    """

    def __init__(self):
        """Initialize service and load credibility configuration"""
        config_path = Path(__file__).parent.parent / "data" / "source_credibility.json"

        # Get default credibility from unified config (aligned with CREDIBILITY_MINIMUM)
        default_credibility = getattr(settings, 'UNKNOWN_SOURCE_CREDIBILITY', 0.55)

        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
            logger.info(f"Loaded source credibility config from {config_path}")
        except FileNotFoundError:
            logger.error(f"Credibility config not found at {config_path}")
            # Fallback to minimal config - uses unified UNKNOWN_SOURCE_CREDIBILITY
            self.config = {"general": {"credibility": default_credibility, "description": "Default", "tier": "general"}}
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in credibility config: {e}")
            self.config = {"general": {"credibility": default_credibility, "description": "Default", "tier": "general"}}

        # Cache for performance (stores domain -> credibility info)
        self._domain_cache: Dict[str, Dict[str, Any]] = {}

    def get_credibility(self, source: str, url: str) -> Dict[str, Any]:
        """
        Get credibility score and metadata for a source.

        Args:
            source: Source name (e.g., "BBC News")
            url: Full URL to assess

        Returns:
            Dictionary with:
                - tier: str - Category tier (e.g., 'news_tier1', 'blacklist')
                - credibility: float - Score 0.0-1.0
                - risk_flags: list - Risk indicators (e.g., ['state_sponsored'])
                - auto_exclude: bool - Should be excluded from results
                - reasoning: str - Explanation of score
                - description: str - Tier description

        Example:
            >>> service.get_credibility("BBC", "https://bbc.co.uk/sport/football")
            {
                'tier': 'sports_news',
                'credibility': 0.85,
                'risk_flags': [],
                'auto_exclude': False,
                'reasoning': 'Matched sports_news tier (path: bbc.co.uk/sport)',
                'description': 'Sports journalism and news outlets'
            }
        """
        # Extract domain and path from URL
        try:
            parsed = tldextract.extract(url)
            domain = parsed.registered_domain.lower()
            url_path = urlparse(url).path.lower().rstrip('/')
        except Exception as e:
            logger.warning(f"Failed to extract domain from {url}: {e}")
            return self._get_general_tier("Failed to parse domain")

        # Generate cache key (includes path prefix for path-based matches)
        cache_key = self._get_cache_key(domain, url_path)
        if cache_key in self._domain_cache:
            return self._domain_cache[cache_key]

        # Match against tiers (path patterns first, then domain patterns)
        result = self._match_domain_to_tier(domain, url_path, parsed)

        # Cache the result
        self._domain_cache[cache_key] = result

        return result

    def _get_cache_key(self, domain: str, url_path: str) -> str:
        """
        Generate cache key based on domain and path.

        For path-based matches, includes the first path segment.
        For domain-only matches, uses just the domain.
        """
        if url_path:
            # Extract first path segment for cache key
            path_parts = url_path.strip('/').split('/')
            if path_parts and path_parts[0]:
                return f"{domain}/{path_parts[0]}"
        return domain

    def _match_domain_to_tier(self, domain: str, url_path: str, parsed) -> Dict[str, Any]:
        """
        Match domain and path against all configured tiers.

        Uses two-pass matching:
        1. First pass: Check path patterns (more specific)
        2. Second pass: Check domain-only patterns (fallback)

        Args:
            domain: Registered domain (e.g., 'bbc.co.uk')
            url_path: URL path (e.g., '/sport/football')
            parsed: tldextract result object

        Returns:
            Credibility info dictionary
        """
        # PASS 1: Check path patterns first (more specific)
        for tier_name, tier_config in self.config.items():
            if tier_name == 'general':
                continue

            if 'domains' not in tier_config:
                continue

            for pattern in tier_config['domains']:
                # Only check path patterns in first pass
                if '/' in pattern:
                    if self._matches_path_pattern(domain, url_path, pattern):
                        return {
                            'tier': tier_name,
                            'credibility': tier_config.get('credibility', 0.6),
                            'risk_flags': tier_config.get('risk_flags', []),
                            'auto_exclude': tier_config.get('auto_exclude', False),
                            'reasoning': f"Matched {tier_name} tier (path: {domain}{url_path})",
                            'description': tier_config.get('description', '')
                        }

        # PASS 2: Check domain-only patterns (fallback)
        for tier_name, tier_config in self.config.items():
            if tier_name == 'general':
                continue

            if 'domains' not in tier_config:
                continue

            for pattern in tier_config['domains']:
                # Only check domain patterns in second pass
                if '/' not in pattern:
                    if self._matches_domain_pattern(domain, pattern, parsed):
                        return {
                            'tier': tier_name,
                            'credibility': tier_config.get('credibility', 0.6),
                            'risk_flags': tier_config.get('risk_flags', []),
                            'auto_exclude': tier_config.get('auto_exclude', False),
                            'reasoning': f"Matched {tier_name} tier (domain: {domain})",
                            'description': tier_config.get('description', '')
                        }

        # No match found - default to general tier
        return self._get_general_tier(f"No specific tier matched (domain: {domain})")

    def _matches_path_pattern(self, domain: str, url_path: str, pattern: str) -> bool:
        """
        Check if domain+path matches a path pattern.

        Patterns:
            - 'bbc.co.uk/sport/*' matches 'bbc.co.uk' + '/sport/football'
            - 'theguardian.com/football/*' matches 'theguardian.com' + '/football/article'

        Args:
            domain: Domain to check (e.g., 'bbc.co.uk')
            url_path: URL path (e.g., '/sport/football')
            pattern: Path pattern (e.g., 'bbc.co.uk/sport/*')

        Returns:
            True if domain+path matches pattern
        """
        pattern = pattern.lower().rstrip('/')

        # Split pattern into domain and path parts
        if '/' not in pattern:
            return False

        pattern_parts = pattern.split('/', 1)
        pattern_domain = pattern_parts[0]
        pattern_path = '/' + pattern_parts[1] if len(pattern_parts) > 1 else ''

        # Check domain matches
        if pattern_domain != domain:
            return False

        # Check path matches (with wildcard support)
        if pattern_path.endswith('/*'):
            # Wildcard path - check prefix
            path_prefix = pattern_path[:-2]  # Remove '/*'
            return url_path.startswith(path_prefix)
        else:
            # Exact path match
            return url_path == pattern_path or url_path.startswith(pattern_path + '/')

    def _matches_domain_pattern(self, domain: str, pattern: str, parsed) -> bool:
        """
        Check if domain matches a domain-only pattern (supports wildcards).

        Patterns:
            - Exact match: 'bbc.co.uk' matches 'bbc.co.uk'
            - Wildcard TLD: '*.edu' matches 'mit.edu', 'stanford.edu'
            - Wildcard suffix: '*.ac.uk' matches 'ox.ac.uk', 'cam.ac.uk'

        Args:
            domain: Domain to check (e.g., 'mit.edu')
            pattern: Pattern to match (e.g., '*.edu')
            parsed: tldextract result object

        Returns:
            True if domain matches pattern
        """
        pattern = pattern.lower()

        if pattern.startswith('*.'):
            # Wildcard pattern - match TLD/suffix
            suffix = pattern[2:]  # Remove '*.'
            return domain.endswith(suffix)
        else:
            # Exact match
            return domain == pattern

    def _get_general_tier(self, reasoning: str) -> Dict[str, Any]:
        """Get default 'general' tier with custom reasoning"""
        # Use unified UNKNOWN_SOURCE_CREDIBILITY for default (aligned with CREDIBILITY_MINIMUM)
        default_cred = getattr(settings, 'UNKNOWN_SOURCE_CREDIBILITY', 0.55)
        general_config = self.config.get('general', {
            'credibility': default_cred,
            'description': 'Default for unmatched sources',
            'tier': 'general'
        })

        return {
            'tier': 'general',
            'credibility': general_config.get('credibility', default_cred),
            'risk_flags': [],
            'auto_exclude': False,
            'reasoning': reasoning,
            'description': general_config.get('description', 'Default for unmatched sources')
        }

    def should_exclude(self, url: str) -> bool:
        """
        Check if source should be auto-excluded (e.g., satire).

        Args:
            url: URL to check

        Returns:
            True if source should be excluded from results
        """
        cred_info = self.get_credibility("", url)
        return cred_info.get('auto_exclude', False)

    def get_risk_assessment(self, url: str) -> Dict[str, Any]:
        """
        Get detailed risk assessment for a source.

        Args:
            url: URL to assess

        Returns:
            Dictionary with:
                - risk_level: str - 'high' | 'medium' | 'low' | 'none'
                - risk_flags: list - Risk indicators
                - should_flag_to_user: bool - Display warning to user
                - warning_message: str - User-friendly warning text

        Example:
            >>> service.get_risk_assessment("https://rt.com/news")
            {
                'risk_level': 'medium',
                'risk_flags': ['state_sponsored', 'propaganda_concerns'],
                'should_flag_to_user': True,
                'warning_message': 'Source editorial independence concerns (state_sponsored, propaganda_concerns)'
            }
        """
        cred_info = self.get_credibility("", url)
        risk_flags = cred_info.get('risk_flags', [])

        # Determine risk level based on flags
        if not risk_flags:
            risk_level = 'none'
        elif any(flag in risk_flags for flag in ['conspiracy_theories', 'medical_misinformation', 'multiple_failed_fact_checks']):
            risk_level = 'high'
        elif any(flag in risk_flags for flag in ['state_sponsored', 'propaganda_concerns', 'editorial_independence_questioned']):
            risk_level = 'medium'
        elif any(flag in risk_flags for flag in ['sensationalism', 'entertainment_focus']):
            risk_level = 'low'
        else:
            risk_level = 'low'

        # Generate warning message
        warning = None
        if risk_level == 'high':
            warning = f"Source has history of spreading misinformation ({', '.join(risk_flags)})"
        elif risk_level == 'medium':
            warning = f"Source editorial independence concerns ({', '.join(risk_flags)})"
        elif risk_level == 'low':
            warning = f"Source quality concerns ({', '.join(risk_flags)})"

        return {
            'risk_level': risk_level,
            'risk_flags': risk_flags,
            'should_flag_to_user': risk_level in ['high', 'medium'],
            'warning_message': warning
        }

    def get_tier_summary(self) -> Dict[str, int]:
        """
        Get count of domains in each tier.
        Useful for admin dashboards and monitoring.

        Returns:
            Dictionary mapping tier name to domain count

        Example:
            >>> service.get_tier_summary()
            {'academic': 16, 'government': 18, 'news_tier1': 6, ...}
        """
        summary = {}
        for tier_name, tier_config in self.config.items():
            if 'domains' in tier_config:
                summary[tier_name] = len(tier_config['domains'])
            else:
                summary[tier_name] = 0
        return summary

    def clear_cache(self):
        """Clear the domain cache (useful for testing or config updates)"""
        self._domain_cache.clear()
        logger.info("Domain cache cleared")

    def get_credibility_breakdown(self, url: str) -> Dict[str, Any]:
        """
        Get detailed breakdown of credibility scoring.

        Includes tier info, risk assessment, and reasoning.
        Useful for transparency and debugging.

        Args:
            url: URL to analyze

        Returns:
            Complete credibility breakdown
        """
        cred_info = self.get_credibility("", url)
        risk_info = self.get_risk_assessment(url)

        return {
            'url': url,
            'tier': cred_info['tier'],
            'credibility_score': cred_info['credibility'],
            'description': cred_info['description'],
            'reasoning': cred_info['reasoning'],
            'risk_level': risk_info['risk_level'],
            'risk_flags': risk_info['risk_flags'],
            'should_flag': risk_info['should_flag_to_user'],
            'warning': risk_info['warning_message'],
            'auto_exclude': cred_info['auto_exclude']
        }

    def _get_source_jurisdiction(self, url: str) -> Optional[str]:
        """
        Extract jurisdiction (country code) from URL based on domain suffix.

        Args:
            url: URL to analyze

        Returns:
            Two-letter country code or None if unknown
        """
        try:
            parsed = tldextract.extract(url)
            domain = parsed.registered_domain.lower()
            suffix = parsed.suffix.lower()

            # Check full suffix first (e.g., .co.uk)
            full_suffix = f".{suffix}"
            if full_suffix in DOMAIN_JURISDICTION_MAP:
                return DOMAIN_JURISDICTION_MAP[full_suffix]

            # Check TLD only (e.g., .uk from .co.uk)
            tld = suffix.split('.')[-1] if '.' in suffix else suffix
            tld_key = f".{tld}"
            if tld_key in DOMAIN_JURISDICTION_MAP:
                return DOMAIN_JURISDICTION_MAP[tld_key]

            return None
        except Exception as e:
            logger.debug(f"Failed to extract jurisdiction from {url}: {e}")
            return None

    def _calculate_jurisdiction_boost(
        self,
        source_jurisdiction: Optional[str],
        story_jurisdiction: Optional[str]
    ) -> Tuple[float, str]:
        """
        Calculate credibility boost based on geographic relevance.

        Args:
            source_jurisdiction: Country code of the source (e.g., "DK")
            story_jurisdiction: Country/region of the story (e.g., "DK", "UK", "EU", "Global")

        Returns:
            Tuple of (boost_amount, reasoning)
        """
        if not source_jurisdiction or not story_jurisdiction:
            return 0.0, ""

        story_jurisdiction = story_jurisdiction.upper()

        # Exact match - source is from the same country as the story
        if source_jurisdiction == story_jurisdiction:
            return JURISDICTION_BOOST_EXACT, f"local source (+{JURISDICTION_BOOST_EXACT:.0%})"

        # Special case: Greenland stories - boost Danish sources too
        if story_jurisdiction == "GL" and source_jurisdiction == "DK":
            return JURISDICTION_BOOST_EXACT, f"Danish source for Greenland story (+{JURISDICTION_BOOST_EXACT:.0%})"

        # Check if both are in the same regional group
        for group_name, countries in JURISDICTION_GROUPS.items():
            if source_jurisdiction in countries:
                # Story jurisdiction might be a country code or group name
                if story_jurisdiction in countries:
                    return JURISDICTION_BOOST_GROUP, f"regional source ({group_name}, +{JURISDICTION_BOOST_GROUP:.0%})"
                # Story jurisdiction might be the group itself (e.g., "EU")
                if story_jurisdiction == group_name:
                    return JURISDICTION_BOOST_GROUP, f"regional source ({group_name}, +{JURISDICTION_BOOST_GROUP:.0%})"

        return 0.0, ""

    def get_credibility_with_jurisdiction(
        self,
        source: str,
        url: str,
        story_jurisdiction: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get credibility score with geographic/jurisdictional boosting.

        Local sources get a credibility boost when covering stories in their region.
        This helps ensure diverse, locally-relevant sources are included.

        Args:
            source: Source name (e.g., "BBC News")
            url: Full URL to assess
            story_jurisdiction: Jurisdiction of the story being fact-checked
                               (e.g., "UK", "DK", "US", "EU", "Global")

        Returns:
            Credibility info with jurisdiction boost applied:
                - tier: str - Category tier
                - credibility: float - Base score 0.0-1.0
                - boosted_credibility: float - Score with jurisdiction boost
                - jurisdiction_boost: float - Amount of boost applied
                - jurisdiction_reasoning: str - Why boost was applied
                - source_jurisdiction: str - Detected source country
                - ... (all other standard fields)

        Example:
            >>> service.get_credibility_with_jurisdiction(
            ...     "Politiken", "https://politiken.dk/article", story_jurisdiction="DK"
            ... )
            {
                'tier': 'news_nordic_newspapers',
                'credibility': 0.82,
                'boosted_credibility': 0.94,  # 0.82 + 0.12 boost
                'jurisdiction_boost': 0.12,
                'jurisdiction_reasoning': 'local source (+12%)',
                'source_jurisdiction': 'DK',
                ...
            }
        """
        # Get base credibility
        base_cred = self.get_credibility(source, url)

        # Extract source jurisdiction
        source_jurisdiction = self._get_source_jurisdiction(url)

        # Calculate jurisdiction boost
        boost, boost_reasoning = self._calculate_jurisdiction_boost(
            source_jurisdiction, story_jurisdiction
        )

        # Calculate boosted credibility (capped at 1.0)
        boosted_credibility = min(1.0, base_cred['credibility'] + boost)

        # Log significant boosts for monitoring
        if boost > 0:
            logger.debug(
                f"[JURISDICTION BOOST] {url[:50]}... "
                f"({source_jurisdiction} for {story_jurisdiction} story): "
                f"{base_cred['credibility']:.2f} -> {boosted_credibility:.2f}"
            )

        return {
            **base_cred,
            'boosted_credibility': boosted_credibility,
            'jurisdiction_boost': boost,
            'jurisdiction_reasoning': boost_reasoning,
            'source_jurisdiction': source_jurisdiction
        }


# Singleton instance for reuse
_credibility_service = None

def get_credibility_service() -> SourceCredibilityService:
    """
    Get singleton instance of SourceCredibilityService.

    Returns:
        Singleton SourceCredibilityService instance
    """
    global _credibility_service
    if _credibility_service is None:
        _credibility_service = SourceCredibilityService()
    return _credibility_service
