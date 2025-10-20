from typing import List, Dict, Any, Tuple
import hashlib
from difflib import SequenceMatcher
import logging

logger = logging.getLogger(__name__)


class EvidenceDeduplicator:
    """Detect and remove duplicate/near-duplicate evidence"""

    def __init__(self, text_similarity_threshold: float = 0.85):
        """
        Initialize deduplicator with configurable thresholds.

        Args:
            text_similarity_threshold: Minimum similarity ratio (0-1) to consider text as duplicate
        """
        self.text_similarity_threshold = text_similarity_threshold

    def deduplicate(self, evidence_list: List[Dict[str, Any]]) -> Tuple[List[Dict], Dict[str, Any]]:
        """
        Remove duplicates using three-stage process:
        1. Exact hash deduplication (fastest)
        2. Text similarity deduplication (medium)
        3. Semantic similarity if embeddings available (slowest, most accurate)

        Args:
            evidence_list: List of evidence dictionaries

        Returns:
            Tuple of (deduplicated evidence list, statistics dictionary)
        """
        if len(evidence_list) <= 1:
            return evidence_list, {"duplicates_removed": 0}

        # Stage 1: Exact hash deduplication
        stage1 = self._exact_hash_dedup(evidence_list)

        # Stage 2: Text similarity deduplication
        stage2 = self._text_similarity_dedup(stage1)

        stats = {
            "original_count": len(evidence_list),
            "after_hash_dedup": len(stage1),
            "final_count": len(stage2),
            "duplicates_removed": len(evidence_list) - len(stage2),
            "dedup_ratio": round((len(evidence_list) - len(stage2)) / len(evidence_list), 2) if evidence_list else 0
        }

        logger.info(f"Deduplication: {stats['original_count']} → {stats['final_count']} "
                   f"({stats['duplicates_removed']} duplicates removed)")

        return stage2, stats

    def _exact_hash_dedup(self, evidence: List[Dict]) -> List[Dict]:
        """
        Remove exact duplicates by content hash.

        Args:
            evidence: List of evidence dictionaries

        Returns:
            List with exact duplicates removed
        """
        seen_hashes = set()
        unique = []

        for ev in evidence:
            # Get text content (try snippet first, then text field)
            content = ev.get('snippet', ev.get('text', ''))
            content_hash = self._hash_content(content)

            if content_hash not in seen_hashes:
                seen_hashes.add(content_hash)
                ev['content_hash'] = content_hash  # Store for database
                unique.append(ev)
            else:
                logger.debug(f"Exact duplicate found: {ev.get('url', 'unknown')}")

        return unique

    def _hash_content(self, text: str) -> str:
        """
        Create normalized hash of content.

        Normalization steps:
        1. Convert to lowercase
        2. Remove extra whitespace
        3. Remove punctuation
        4. Hash with MD5

        Args:
            text: Text content to hash

        Returns:
            MD5 hex digest of normalized text
        """
        # Normalize: lowercase, remove extra spaces, remove punctuation
        normalized = text.lower().strip()
        normalized = ''.join(c for c in normalized if c.isalnum() or c.isspace())
        normalized = ' '.join(normalized.split())

        return hashlib.md5(normalized.encode('utf-8')).hexdigest()

    def _text_similarity_dedup(self, evidence: List[Dict]) -> List[Dict]:
        """
        Remove near-duplicates using sequence matching.

        Uses SequenceMatcher to find text with >85% similarity.
        Marks syndicated content (same text, different URL).

        Args:
            evidence: List of evidence dictionaries

        Returns:
            List with near-duplicates removed
        """
        if len(evidence) <= 1:
            return evidence

        unique = [evidence[0]]

        for candidate in evidence[1:]:
            is_duplicate = False
            candidate_text = candidate.get('snippet', candidate.get('text', '')).lower()

            for existing in unique:
                existing_text = existing.get('snippet', existing.get('text', '')).lower()
                similarity = SequenceMatcher(None, candidate_text, existing_text).ratio()

                if similarity >= self.text_similarity_threshold:
                    is_duplicate = True

                    # Mark as syndicated if from different domain
                    candidate_url = candidate.get('url', '')
                    existing_url = existing.get('url', '')
                    if candidate_url != existing_url:
                        logger.debug(f"Syndicated content detected: {candidate_url} (similar to {existing_url})")
                        candidate['is_syndicated'] = True
                        candidate['original_source_url'] = existing_url

                    break

            if not is_duplicate:
                # Initialize syndication flags for non-duplicates
                if 'is_syndicated' not in candidate:
                    candidate['is_syndicated'] = False
                    candidate['original_source_url'] = None
                unique.append(candidate)

        return unique

    def get_dedup_metrics(self, original_count: int, final_count: int) -> Dict[str, Any]:
        """
        Calculate deduplication metrics for monitoring.

        Args:
            original_count: Original evidence count
            final_count: Count after deduplication

        Returns:
            Dictionary with deduplication metrics
        """
        if original_count == 0:
            return {
                "duplicates_found": 0,
                "dedup_percentage": 0,
                "efficiency_gain": 0
            }

        duplicates = original_count - final_count
        dedup_percentage = (duplicates / original_count) * 100

        return {
            "duplicates_found": duplicates,
            "dedup_percentage": round(dedup_percentage, 1),
            "efficiency_gain": round(dedup_percentage / 100, 2)
        }
