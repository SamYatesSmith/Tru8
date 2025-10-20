import httpx
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from app.core.config import settings

logger = logging.getLogger(__name__)


class FactCheckAPI:
    """Google Fact Check Explorer API integration"""

    def __init__(self):
        self.api_key = settings.GOOGLE_FACTCHECK_API_KEY
        self.base_url = "https://factchecktools.googleapis.com/v1alpha1/claims:search"
        self.cache = {}  # Simple in-memory cache
        self.cache_ttl = timedelta(hours=24)

    async def search_fact_checks(self, claim_text: str, language: str = "en") -> List[Dict[str, Any]]:
        """
        Search for existing fact-checks for a claim.

        Args:
            claim_text: The claim to search for
            language: Language code (default: "en")

        Returns:
            List of fact-check results with normalized verdicts
        """
        if not self.api_key:
            logger.warning("Google Fact Check API key not configured")
            return []

        # Check cache
        cache_key = f"{claim_text}:{language}"
        if cache_key in self.cache:
            cached_result, cached_time = self.cache[cache_key]
            if datetime.utcnow() - cached_time < self.cache_ttl:
                logger.debug(f"Fact-check cache hit for: {claim_text[:50]}")
                return cached_result

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                params = {
                    "key": self.api_key,
                    "query": claim_text,
                    "languageCode": language
                }

                response = await client.get(self.base_url, params=params)
                response.raise_for_status()

                data = response.json()
                claims = data.get("claims", [])

                results = []
                for claim in claims:
                    for review in claim.get("claimReview", []):
                        result = self._parse_fact_check(claim, review)
                        if result:
                            results.append(result)

                # Cache results
                self.cache[cache_key] = (results, datetime.utcnow())

                logger.info(f"Found {len(results)} fact-checks for claim: {claim_text[:50]}")
                return results

        except httpx.HTTPStatusError as e:
            logger.error(f"Fact Check API HTTP error: {e.response.status_code}")
            return []
        except Exception as e:
            logger.error(f"Fact Check API error: {e}")
            return []

    def _parse_fact_check(self, claim: Dict, review: Dict) -> Optional[Dict[str, Any]]:
        """
        Parse and normalize fact-check result.

        Args:
            claim: Original claim data
            review: ClaimReview data

        Returns:
            Normalized fact-check dictionary
        """
        try:
            publisher = review.get("publisher", {})
            rating = review.get("textualRating", "")

            return {
                "claim_text": claim.get("text", ""),
                "claim_date": claim.get("claimDate"),
                "claimant": claim.get("claimant", "Unknown"),
                "publisher": publisher.get("name", "Unknown"),
                "publisher_site": publisher.get("site"),
                "url": review.get("url", ""),
                "title": review.get("title", ""),
                "rating": rating,
                "normalized_verdict": self._normalize_verdict(rating),
                "review_date": review.get("reviewDate"),
                "language": review.get("languageCode", "en")
            }
        except Exception as e:
            logger.warning(f"Failed to parse fact-check result: {e}")
            return None

    def _normalize_verdict(self, rating: str) -> str:
        """
        Normalize different fact-check rating formats to standard verdicts.

        Maps various fact-checker ratings to:
        - SUPPORTED (true, mostly true, correct)
        - CONTRADICTED (false, mostly false, incorrect, pants on fire)
        - UNCERTAIN (mixture, unproven, needs context)

        Args:
            rating: Original textual rating

        Returns:
            Normalized verdict string
        """
        rating_lower = rating.lower()

        # Supported/True
        if any(keyword in rating_lower for keyword in [
            "true", "correct", "accurate", "verified", "confirmed"
        ]):
            return "SUPPORTED"

        # Contradicted/False
        if any(keyword in rating_lower for keyword in [
            "false", "incorrect", "inaccurate", "debunked", "pants on fire",
            "misleading", "wrong"
        ]):
            return "CONTRADICTED"

        # Uncertain/Mixed
        if any(keyword in rating_lower for keyword in [
            "mixture", "mixed", "half true", "mostly", "unproven",
            "needs context", "unclear", "unsubstantiated"
        ]):
            return "UNCERTAIN"

        # Default to uncertain if we can't classify
        logger.debug(f"Unknown rating format: {rating}, defaulting to UNCERTAIN")
        return "UNCERTAIN"

    def convert_to_evidence(self, fact_check: Dict[str, Any], claim_text: str) -> Dict[str, Any]:
        """
        Convert fact-check result to Evidence format for pipeline integration.

        Args:
            fact_check: Parsed fact-check result
            claim_text: Original claim being checked

        Returns:
            Evidence-compatible dictionary
        """
        return {
            "source": fact_check.get("publisher", "Unknown"),
            "url": fact_check.get("url", ""),
            "title": fact_check.get("title", ""),
            "snippet": f"Fact-check verdict: {fact_check.get('rating', 'Unknown')}",
            "published_date": fact_check.get("review_date"),
            "relevance_score": 1.0,  # Fact-checks are highly relevant
            "credibility_score": 0.95,  # Fact-checks from IFCN signatories are high credibility
            "is_factcheck": True,
            "factcheck_publisher": fact_check.get("publisher"),
            "factcheck_rating": fact_check.get("rating"),
            "factcheck_date": fact_check.get("review_date"),
            "source_type": "factcheck"
        }

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics for monitoring"""
        return {
            "cache_size": len(self.cache),
            "cache_ttl_hours": self.cache_ttl.total_seconds() / 3600
        }

    def clear_cache(self):
        """Clear the fact-check cache"""
        self.cache.clear()
        logger.info("Fact-check cache cleared")
