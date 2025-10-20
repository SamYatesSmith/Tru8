import re
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


class ClaimClassifier:
    """Classify claims by type and verifiability"""

    def __init__(self):
        # Opinion indicators
        self.opinion_patterns = [
            r"\b(i think|i believe|in my opinion|i feel|seems like)\b",
            r"\b(beautiful|ugly|amazing|terrible|best|worst)\b",
            r"\b(should|ought to|must|need to)\b"  # Normative
        ]

        # Prediction indicators
        self.prediction_patterns = [
            r"\b(will|going to|predict|forecast|expect)\b",
            r"\b(in the future|next year|by 20\d{2})\b"
        ]

        # Personal experience indicators
        self.personal_patterns = [
            r"\b(i saw|i heard|i experienced|happened to me)\b"
        ]

    def classify(self, claim_text: str) -> Dict[str, Any]:
        """Classify claim type and assess verifiability"""
        claim_lower = claim_text.lower()

        # Check for opinion
        if any(re.search(pattern, claim_lower) for pattern in self.opinion_patterns):
            return {
                "claim_type": "opinion",
                "is_verifiable": False,
                "reason": "This appears to be a subjective opinion or value judgment",
                "confidence": 0.85
            }

        # Check for prediction
        if any(re.search(pattern, claim_lower) for pattern in self.prediction_patterns):
            return {
                "claim_type": "prediction",
                "is_verifiable": False,  # Can't verify future
                "reason": "This is a prediction about future events",
                "confidence": 0.8,
                "note": "We can assess the basis for the prediction, but cannot verify its truth"
            }

        # Check for personal experience
        if any(re.search(pattern, claim_lower) for pattern in self.personal_patterns):
            return {
                "claim_type": "personal_experience",
                "is_verifiable": False,
                "reason": "This is a personal experience that cannot be externally verified",
                "confidence": 0.75
            }

        # Default: factual claim
        return {
            "claim_type": "factual",
            "is_verifiable": True,
            "reason": "This appears to be a factual claim that can be verified",
            "confidence": 0.7
        }

    def get_classification_summary(self, claims: list[Dict[str, Any]]) -> Dict[str, Any]:
        """Get summary statistics for a batch of classified claims"""
        total = len(claims)
        if total == 0:
            return {
                "total_claims": 0,
                "verifiable": 0,
                "non_verifiable": 0,
                "types": {}
            }

        verifiable_count = sum(1 for c in claims if c.get("is_verifiable", True))
        type_counts = {}

        for claim in claims:
            classification = claim.get("classification", {})
            claim_type = classification.get("claim_type", "factual")
            type_counts[claim_type] = type_counts.get(claim_type, 0) + 1

        return {
            "total_claims": total,
            "verifiable": verifiable_count,
            "non_verifiable": total - verifiable_count,
            "verifiable_percentage": round((verifiable_count / total) * 100, 1),
            "types": type_counts
        }
