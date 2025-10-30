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

    def apply_caps(
        self,
        evidence: List[Dict[str, Any]],
        target_count: int = 5,
        outstanding_threshold: float = 0.95
    ) -> List[Dict[str, Any]]:
        """
        Apply per-domain caps to evidence list with credibility awareness.

        Rules:
        - Outstanding sources (credibility >= 0.95): Allow up to target_count from same domain
        - Good sources (credibility >= 0.8): Standard cap (3 per domain)
        - Mediocre sources (credibility < 0.8): Strict cap (2 per domain)
        - Maintain overall target count when possible

        Args:
            evidence: List of evidence dictionaries (must be pre-sorted by score, descending)
            target_count: Target number of evidence items to return
            outstanding_threshold: Credibility threshold for "outstanding" sources (default 0.95)

        Returns:
            Capped evidence list with credibility-aware domain diversity enforced
        """
        if not evidence:
            return []

        # Group evidence by domain with credibility tracking
        domain_evidence = defaultdict(list)
        for ev in evidence:
            domain = self._extract_domain(ev.get('url', ''))
            domain_evidence[domain].append(ev)

        # Calculate domain caps based on credibility
        domain_caps = {}
        for domain, ev_list in domain_evidence.items():
            # Use max credibility from domain (best source determines cap)
            max_credibility = max(ev.get('credibility_score', 0.6) for ev in ev_list)

            if max_credibility >= outstanding_threshold:
                # Outstanding: allow up to target_count (e.g., all 5)
                domain_caps[domain] = target_count
                logger.info(f"Domain '{domain}' is OUTSTANDING (credibility {max_credibility:.2f}), cap: {target_count}")
            elif max_credibility >= 0.8:
                # Good: standard cap (3)
                domain_caps[domain] = min(self.max_per_domain, int(target_count * self.max_domain_ratio))
                logger.info(f"Domain '{domain}' is GOOD (credibility {max_credibility:.2f}), cap: {domain_caps[domain]}")
            else:
                # Mediocre: strict cap (2)
                domain_caps[domain] = max(2, min(self.max_per_domain - 1, int(target_count * 0.4)))
                logger.info(f"Domain '{domain}' is MEDIOCRE (credibility {max_credibility:.2f}), cap: {domain_caps[domain]}")

        # Apply caps
        domain_counts = defaultdict(int)
        capped_evidence = []

        # Evidence should already be sorted by score (descending)
        for ev in evidence:
            domain = self._extract_domain(ev.get('url', ''))
            cap = domain_caps.get(domain, 2)  # Default to 2 if not calculated

            if domain_counts[domain] < cap:
                capped_evidence.append(ev)
                domain_counts[domain] += 1

            if len(capped_evidence) >= target_count:
                break

        logger.info(f"Credibility-aware domain capping: {len(evidence)} → {len(capped_evidence)} sources. "
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
