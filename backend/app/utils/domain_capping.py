from typing import List, Dict, Any
from urllib.parse import urlparse
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)

class DomainCapper:
    """Enforce maximum evidence per domain to prevent single-source dominance"""

    def __init__(self, max_per_domain: int = 3, max_domain_ratio: float = 0.4):
        """
        Initialize DomainCapper with configurable limits.

        Args:
            max_per_domain: Maximum number of sources allowed from a single domain
            max_domain_ratio: Maximum ratio of total evidence from a single domain (e.g., 0.4 = 40%)
        """
        self.max_per_domain = max_per_domain
        self.max_domain_ratio = max_domain_ratio

    def apply_caps(self, evidence: List[Dict[str, Any]], target_count: int = 5) -> List[Dict[str, Any]]:
        """
        Apply per-domain caps to evidence list.

        Rules:
        - Max 40% of evidence from single domain (configurable via max_domain_ratio)
        - Prefer highest-scored evidence from each domain
        - Maintain overall target count when possible

        Args:
            evidence: List of evidence dictionaries (must be pre-sorted by score, descending)
            target_count: Target number of evidence items to return

        Returns:
            Capped evidence list with domain diversity enforced
        """
        if not evidence:
            return []

        # Calculate effective cap: min(max_per_domain, 40% of target_count, but at least 2)
        effective_cap = max(2, min(self.max_per_domain, int(target_count * self.max_domain_ratio)))

        domain_counts = defaultdict(int)
        capped_evidence = []

        # Evidence should already be sorted by score (descending)
        for ev in evidence:
            domain = self._extract_domain(ev.get('url', ''))

            if domain_counts[domain] < effective_cap:
                capped_evidence.append(ev)
                domain_counts[domain] += 1

                if len(capped_evidence) >= target_count:
                    break

        logger.info(f"Domain capping: {len(evidence)} → {len(capped_evidence)} sources. "
                   f"Distribution: {dict(domain_counts)}")

        return capped_evidence

    def _extract_domain(self, url: str) -> str:
        """
        Extract clean domain from URL.

        Args:
            url: Full URL string

        Returns:
            Clean domain (e.g., "bbc.co.uk" from "https://www.bbc.co.uk/news/...")
        """
        try:
            parsed = urlparse(url)
            domain = parsed.netloc

            # Remove www. prefix
            if domain.startswith('www.'):
                domain = domain[4:]

            return domain.lower()
        except Exception as e:
            logger.warning(f"Failed to extract domain from URL '{url}': {e}")
            return "unknown"

    def get_diversity_metrics(self, evidence: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculate domain diversity metrics for transparency and monitoring.

        Args:
            evidence: List of evidence dictionaries

        Returns:
            Dictionary containing:
            - unique_domains: Number of unique domains
            - max_domain_ratio: Ratio of most frequent domain
            - diversity_score: 1.0 - max_domain_ratio (higher = more diverse)
            - domain_distribution: Dictionary of domain → count
        """
        if not evidence:
            return {
                "unique_domains": 0,
                "max_domain_ratio": 0,
                "diversity_score": 0,
                "domain_distribution": {}
            }

        domains = [self._extract_domain(ev.get('url', '')) for ev in evidence]
        domain_counts = defaultdict(int)
        for domain in domains:
            domain_counts[domain] += 1

        unique_domains = len(domain_counts)
        max_domain_count = max(domain_counts.values())
        max_domain_ratio = max_domain_count / len(domains)
        diversity_score = 1.0 - max_domain_ratio

        return {
            "unique_domains": unique_domains,
            "max_domain_ratio": round(max_domain_ratio, 2),
            "diversity_score": round(diversity_score, 2),
            "domain_distribution": dict(domain_counts)
        }
