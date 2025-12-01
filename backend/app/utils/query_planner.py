"""
Query Planning Agent for Fact-Checking Pipeline

This module provides LLM-powered query planning to generate targeted search queries
based on the semantic type of claims being verified.

Key Features:
- Batch processing: Single LLM call for all claims in an article (~$0.02/article)
- Semantic classification: Identifies claim type (squad, stats, contract, etc.)
- Source prioritization: Routes to authoritative sources per claim type
- Graceful fallback: Falls back to standard query formulation on failure
"""

import logging
import json
from datetime import datetime
from typing import Dict, List, Any, Optional
import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)


class LLMQueryPlanner:
    """
    Plans search queries using LLM for semantic understanding.

    Uses batch processing to minimize API calls and costs.
    """

    SYSTEM_PROMPT = """You are a fact-checking query planner. Generate targeted search queries to find evidence for claims.

QUERY RULES:
1. Generate 2-3 SPECIFIC queries per claim
2. For claims about CURRENT events, include the current year/month in queries to get recent results
3. Use exact names and numbers from the claim
4. Keep queries concise (5-10 words)

CLAIM TYPES: league_standing, player_statistics, contract_info, transfer_rumor, squad_composition, match_result, political, scientific, economic, general

RESPOND WITH JSON:
{
  "plans": [
    {"claim_index": 0, "claim_type": "...", "queries": ["query1", "query2"]},
    ...
  ]
}"""

    def __init__(self):
        self.openai_api_key = settings.OPENAI_API_KEY
        self.timeout = settings.QUERY_PLANNING_TIMEOUT
        self.model = settings.QUERY_PLANNING_MODEL

    async def plan_queries_batch(self, claims: List[Dict[str, Any]]) -> Optional[List[Dict[str, Any]]]:
        """
        Plan queries for all claims in a single LLM call.

        Args:
            claims: List of claim dictionaries with 'text' and optional metadata

        Returns:
            List of query plans, one per claim, or None on failure
        """
        if not claims:
            return []

        if not self.openai_api_key:
            logger.warning("[QUERY_PLANNER] OpenAI API key not configured")
            return None

        try:
            # Current date for context
            now = datetime.now()
            current_date = now.strftime("%Y-%m-%d")
            logger.info(f"[QUERY_PLANNER] Current date: {current_date}")

            # Format claims for the prompt
            claims_text = "\n".join([
                f"{i+1}. {c.get('text', '')}"
                for i, c in enumerate(claims)
            ])

            user_prompt = f"""TODAY'S DATE: {current_date}

Generate search queries for each of these {len(claims)} claims:

{claims_text}

Return a JSON object with "plans" array containing exactly {len(claims)} plan objects, one for each claim."""

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.openai_api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.model,
                        "messages": [
                            {"role": "system", "content": self.SYSTEM_PROMPT},
                            {"role": "user", "content": user_prompt}
                        ],
                        "temperature": 0.1,
                        "max_tokens": 3000,
                        "response_format": {"type": "json_object"}
                    }
                )

                if response.status_code != 200:
                    logger.error(f"Query planning API error: {response.status_code} - {response.text}")
                    return None

                result = response.json()
                content = result["choices"][0]["message"]["content"]

                # Parse response
                parsed = json.loads(content)
                logger.debug(f"[QUERY_PLANNER] Raw response keys: {list(parsed.keys()) if isinstance(parsed, dict) else 'array'}")

                # Extract plans array from response
                query_plans = None
                if isinstance(parsed, dict) and "plans" in parsed:
                    query_plans = parsed["plans"]
                elif isinstance(parsed, dict) and "claims" in parsed:
                    query_plans = parsed["claims"]
                elif isinstance(parsed, dict) and "query_plans" in parsed:
                    query_plans = parsed["query_plans"]
                elif isinstance(parsed, list):
                    query_plans = parsed
                else:
                    # Try to find any array of dicts in the response
                    for key, value in parsed.items():
                        if isinstance(value, list) and len(value) > 0 and isinstance(value[0], dict):
                            query_plans = value
                            logger.debug(f"[QUERY_PLANNER] Found plans under key: {key}")
                            break
                    else:
                        logger.error(f"[QUERY_PLANNER] No plans array found. Keys: {list(parsed.keys())}")
                        return None

                if not query_plans:
                    logger.error(f"[QUERY_PLANNER] Empty plans array")
                    return None

                # Validate structure
                validated_plans = self._validate_plans(query_plans, len(claims))

                # Check if we got enough plans
                if len(validated_plans) < len(claims):
                    logger.warning(f"[QUERY_PLANNER] Only {len(validated_plans)} plans for {len(claims)} claims - some claims will use fallback")

                logger.info(f"[QUERY_PLANNER] SUCCESS: {len(validated_plans)} plans for {len(claims)} claims")
                return validated_plans

        except httpx.TimeoutException:
            logger.warning("[QUERY_PLANNER] TIMEOUT: API call took too long")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"[QUERY_PLANNER] JSON ERROR: {e}")
            return None
        except Exception as e:
            logger.error(f"[QUERY_PLANNER] EXCEPTION: {type(e).__name__}: {e}", exc_info=True)
            return None

    def _validate_plans(self, plans: List[Any], expected_count: int) -> List[Dict[str, Any]]:
        """Validate and normalize query plans."""
        validated = []

        for i, plan in enumerate(plans):
            if not isinstance(plan, dict):
                logger.warning(f"[QUERY_PLANNER] Plan {i} is not a dict, skipping")
                continue

            validated_plan = {
                "claim_index": plan.get("claim_index", i),
                "claim_type": plan.get("claim_type", "general"),
                "priority_sources": plan.get("priority_sources", []),
                "queries": plan.get("queries", [])
            }

            # Ensure queries is a list
            if isinstance(validated_plan["queries"], str):
                validated_plan["queries"] = [validated_plan["queries"]]

            # Ensure priority_sources is a list
            if isinstance(validated_plan["priority_sources"], str):
                validated_plan["priority_sources"] = [validated_plan["priority_sources"]]

            # Limit queries to 4 per claim
            validated_plan["queries"] = validated_plan["queries"][:4]

            validated.append(validated_plan)

        return validated

    def get_site_filter(self, priority_sources: List[str], claim_type: str) -> str:
        """
        Generate a site filter string for search queries.

        Args:
            priority_sources: List of priority domains
            claim_type: Type of claim for fallback sources

        Returns:
            Site filter string (e.g., "site:premierleague.com OR site:arsenal.com")
        """
        # Default sources by claim type
        default_sources = {
            "squad_composition": ["premierleague.com", "transfermarkt.com"],
            "player_statistics": ["fbref.com", "transfermarkt.com"],
            "contract_info": ["transfermarkt.com"],
            "transfer_rumor": ["skysports.com", "bbc.co.uk"],
            "match_result": ["premierleague.com", "flashscore.com"],
            "league_standing": ["premierleague.com", "uefa.com"],
            "general": []
        }

        sources = priority_sources or default_sources.get(claim_type, [])

        if not sources:
            return ""

        # Use first 2 sources to keep query short
        site_filters = [f"site:{s}" for s in sources[:2]]
        return " OR ".join(site_filters)


# Singleton instance
_query_planner: Optional[LLMQueryPlanner] = None


def get_query_planner() -> LLMQueryPlanner:
    """Get or create the query planner singleton."""
    global _query_planner
    if _query_planner is None:
        _query_planner = LLMQueryPlanner()
    return _query_planner
