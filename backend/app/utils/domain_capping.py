from typing import List, Dict, Any, Optional
from collections import defaultdict
import logging
from app.utils.url_utils import extract_domain

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
            domain = extract_domain(ev.get('url', ''), fallback="unknown")
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
            domain = extract_domain(ev.get('url', ''), fallback="unknown")
            cap = domain_caps.get(domain, 2)  # Default to 2 if not calculated

            if domain_counts[domain] < cap:
                capped_evidence.append(ev)
                domain_counts[domain] += 1

            if len(capped_evidence) >= target_count:
                break

        logger.info(f"Credibility-aware domain capping: {len(evidence)} → {len(capped_evidence)} sources. "
                   f"Distribution: {dict(domain_counts)}")

        return capped_evidence

    def apply_global_caps(
        self,
        evidence_by_claim: Dict[str, List[Dict[str, Any]]],
        global_max_per_domain: int = 5,
        global_max_ratio: float = 0.25
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Apply global domain capping across ALL claims to ensure source diversity.

        This prevents any single domain from dominating the evidence across the
        entire fact-check, even if each individual claim's capping allows it.

        Args:
            evidence_by_claim: Dict mapping claim position to evidence list
            global_max_per_domain: Absolute max evidence from any domain across all claims
            global_max_ratio: Max ratio of total evidence from any domain (e.g., 0.25 = 25%)

        Returns:
            Modified evidence_by_claim with global diversity enforced
        """
        if not evidence_by_claim:
            return evidence_by_claim

        # Flatten all evidence with claim tracking
        all_evidence = []
        for position, ev_list in evidence_by_claim.items():
            for ev in ev_list:
                ev_copy = dict(ev)
                ev_copy['_claim_position'] = position
                all_evidence.append(ev_copy)

        if not all_evidence:
            return evidence_by_claim

        # Calculate current domain distribution
        domain_counts = defaultdict(int)
        domain_evidence = defaultdict(list)
        for ev in all_evidence:
            domain = extract_domain(ev.get('url', ''), fallback="unknown")
            domain_counts[domain] += 1
            domain_evidence[domain].append(ev)

        total_evidence = len(all_evidence)
        effective_max_count = min(
            global_max_per_domain,
            max(3, int(total_evidence * global_max_ratio))  # At least 3
        )

        # Check if any domain exceeds the cap
        capped_domains = {}
        for domain, count in domain_counts.items():
            if count > effective_max_count:
                capped_domains[domain] = count
                logger.info(
                    f"[GLOBAL CAP] Domain '{domain}' has {count} sources "
                    f"(exceeds cap of {effective_max_count}), will be reduced"
                )

        if not capped_domains:
            logger.info(f"[GLOBAL CAP] All domains within limits (max={effective_max_count})")
            return evidence_by_claim

        # Sort evidence within each domain by score (descending) to keep best ones
        for domain in capped_domains:
            domain_evidence[domain].sort(
                key=lambda x: x.get('final_score', x.get('combined_score', 0)),
                reverse=True
            )

        # Rebuild evidence_by_claim with global caps enforced
        global_domain_counts = defaultdict(int)
        new_evidence_by_claim = {pos: [] for pos in evidence_by_claim.keys()}

        # Process evidence in order of score (best first across all claims)
        all_evidence_sorted = sorted(
            all_evidence,
            key=lambda x: x.get('final_score', x.get('combined_score', 0)),
            reverse=True
        )

        for ev in all_evidence_sorted:
            domain = extract_domain(ev.get('url', ''), fallback="unknown")
            position = ev.get('_claim_position')

            # Check global domain cap
            if global_domain_counts[domain] >= effective_max_count:
                logger.debug(
                    f"[GLOBAL CAP] Skipping {domain} source (already at {effective_max_count})"
                )
                continue

            # Remove tracking field and add to result
            ev_clean = {k: v for k, v in ev.items() if not k.startswith('_')}
            new_evidence_by_claim[position].append(ev_clean)
            global_domain_counts[domain] += 1

        # Log results
        total_before = sum(len(v) for v in evidence_by_claim.values())
        total_after = sum(len(v) for v in new_evidence_by_claim.values())
        logger.info(
            f"[GLOBAL CAP] Applied: {total_before} → {total_after} sources. "
            f"Domains capped: {list(capped_domains.keys())}. "
            f"New distribution: {dict(global_domain_counts)}"
        )

        return new_evidence_by_claim

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

        domains = [extract_domain(ev.get('url', ''), fallback="unknown") for ev in evidence]
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
