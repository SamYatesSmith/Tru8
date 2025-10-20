from typing import List, Dict, Any, Tuple
from urllib.parse import urlparse
import json
import os
import logging

logger = logging.getLogger(__name__)


class SourceIndependenceChecker:
    """Check source independence and detect media ownership clustering"""

    def __init__(self):
        self.ownership_db = self._load_ownership_database()
        self.domain_to_parent = self._build_domain_lookup()

    def _load_ownership_database(self) -> Dict[str, Any]:
        """Load ownership database from JSON file"""
        try:
            db_path = os.path.join(
                os.path.dirname(__file__),
                '..', 'data', 'source_ownership.json'
            )
            with open(db_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load ownership database: {e}")
            return {}

    def _build_domain_lookup(self) -> Dict[str, str]:
        """Build reverse lookup: domain → parent company"""
        lookup = {}
        for parent_id, parent_data in self.ownership_db.items():
            parent_name = parent_data.get('name', parent_id)
            for domain in parent_data.get('domains', []):
                lookup[domain.lower()] = parent_name
        return lookup

    def enrich_evidence(self, evidence_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Add ownership metadata to evidence items.

        Args:
            evidence_list: List of evidence dictionaries

        Returns:
            Evidence list with added fields:
            - parent_company: Name of media company owner
            - independence_flag: 'independent', 'corporate', 'state-funded', 'unknown'
            - domain_cluster_id: Unique ID for ownership group
        """
        for ev in evidence_list:
            url = ev.get('url', '')
            domain = self._extract_domain(url)

            parent = self.domain_to_parent.get(domain, 'Unknown')
            ev['parent_company'] = parent

            # Assign independence flag
            if parent == 'Unknown':
                ev['independence_flag'] = 'unknown'
            elif 'state' in parent.lower() or domain in self._get_state_media():
                ev['independence_flag'] = 'state-funded'
            elif any(x in parent.lower() for x in ['nonprofit', 'foundation', 'trust']):
                ev['independence_flag'] = 'independent'
            else:
                ev['independence_flag'] = 'corporate'

            # Assign cluster ID (hash of parent company name)
            ev['domain_cluster_id'] = hash(parent) % 100000

        return evidence_list

    def check_diversity(
        self,
        evidence_list: List[Dict[str, Any]],
        threshold: float = 0.6
    ) -> Tuple[float, bool]:
        """
        Calculate source diversity score and check if it meets threshold.

        Diversity score = 1 - (max_cluster_ratio)
        Higher score = more diverse ownership

        Args:
            evidence_list: List of evidence with parent_company fields
            threshold: Minimum acceptable diversity score (0-1)

        Returns:
            Tuple of (diversity_score, passes_threshold)
        """
        if len(evidence_list) <= 1:
            return 1.0, True

        # Count evidence per parent company
        parent_counts = {}
        for ev in evidence_list:
            parent = ev.get('parent_company', 'Unknown')
            parent_counts[parent] = parent_counts.get(parent, 0) + 1

        # Calculate max cluster ratio
        max_count = max(parent_counts.values())
        max_ratio = max_count / len(evidence_list)

        diversity_score = 1.0 - max_ratio
        passes = diversity_score >= threshold

        logger.info(f"Source diversity: {diversity_score:.2f} (threshold: {threshold}, "
                   f"max cluster: {max_count}/{len(evidence_list)})")

        return round(diversity_score, 2), passes

    def get_diversity_metrics(self, evidence_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Get detailed diversity metrics for transparency.

        Returns:
            Dictionary with:
            - unique_parents: Number of distinct parent companies
            - parent_distribution: Counts per parent company
            - independence_distribution: Counts per independence flag
            - diversity_score: Overall diversity (0-1)
        """
        if not evidence_list:
            return {
                "unique_parents": 0,
                "parent_distribution": {},
                "independence_distribution": {},
                "diversity_score": 0
            }

        parent_counts = {}
        independence_counts = {}

        for ev in evidence_list:
            parent = ev.get('parent_company', 'Unknown')
            independence = ev.get('independence_flag', 'unknown')

            parent_counts[parent] = parent_counts.get(parent, 0) + 1
            independence_counts[independence] = independence_counts.get(independence, 0) + 1

        max_count = max(parent_counts.values()) if parent_counts else 0
        diversity_score = 1.0 - (max_count / len(evidence_list)) if evidence_list else 0

        return {
            "unique_parents": len(parent_counts),
            "parent_distribution": parent_counts,
            "independence_distribution": independence_counts,
            "diversity_score": round(diversity_score, 2)
        }

    def _extract_domain(self, url: str) -> str:
        """Extract clean domain from URL"""
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

    def _get_state_media(self) -> List[str]:
        """List of known state-funded media domains"""
        return [
            'rt.com',
            'sputniknews.com',
            'presstv.ir',
            'cgtn.com',
            'globaltimes.cn'
        ]
