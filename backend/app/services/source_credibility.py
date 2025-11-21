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

logger = logging.getLogger(__name__)


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

        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
            logger.info(f"Loaded source credibility config from {config_path}")
        except FileNotFoundError:
            logger.error(f"Credibility config not found at {config_path}")
            # Fallback to minimal config
            self.config = {"general": {"credibility": 0.6, "description": "Default", "tier": "general"}}
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in credibility config: {e}")
            self.config = {"general": {"credibility": 0.6, "description": "Default", "tier": "general"}}

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
        general_config = self.config.get('general', {
            'credibility': 0.6,
            'description': 'Default for unmatched sources',
            'tier': 'general'
        })

        return {
            'tier': 'general',
            'credibility': general_config.get('credibility', 0.6),
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
