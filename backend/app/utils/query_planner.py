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
from typing import Dict, List, Any, Optional
import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)


class LLMQueryPlanner:
    """
    Plans search queries using LLM for semantic understanding.

    Uses batch processing to minimize API calls and costs.
    """

    SYSTEM_PROMPT = """You are a fact-checking query planner. Given claims from an article, determine what data would verify each claim and generate targeted search queries.

For EACH claim, analyze what TYPE of evidence would verify it and generate appropriate queries.

CLAIM TYPES:
- squad_composition: Claims about which players are in a team's squad
- player_statistics: Claims about goals, assists, appearances, etc.
- contract_info: Claims about player contracts, expiry dates, wages
- transfer_rumor: Claims about potential transfers, interest from clubs
- match_result: Claims about specific match scores or outcomes
- league_standing: Claims about league positions, points, leads
- general: Other factual claims

PRIORITY SOURCES BY TYPE:
- squad_composition: premierleague.com, official club sites, transfermarkt.com
- player_statistics: fbref.com, transfermarkt.com, whoscored.com
- contract_info: transfermarkt.com, capology.com
- transfer_rumor: skysports.com, theathletic.com, bbc.co.uk/sport
- match_result: premierleague.com, uefa.com, flashscore.com
- league_standing: premierleague.com, uefa.com, official league sites

QUERY GENERATION RULES:
1. Generate 2-4 targeted queries per claim
2. Include year/season when relevant (e.g., "2024-25 season", "2025")
3. Use specific entity names from the claim
4. For squad claims, query both official sources AND verify individual players
5. Include site: filters for authoritative sources when helpful

Respond with a JSON array. For each claim:
{
  "claim_index": <index>,
  "claim_type": "<type>",
  "priority_sources": ["<domain1>", "<domain2>"],
  "queries": ["<query1>", "<query2>", "<query3>"]
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
            logger.warning("OpenAI API key not configured, skipping query planning")
            return None

        try:
            # Format claims for the prompt
            claims_text = "\n".join([
                f"{i+1}. {c.get('text', '')}"
                for i, c in enumerate(claims)
            ])

            user_prompt = f"""Plan search queries for these {len(claims)} claims:

{claims_text}

Respond with a JSON array of query plans."""

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
                        "max_tokens": 2000,
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

                # Handle both array and object with 'plans' key
                if isinstance(parsed, list):
                    query_plans = parsed
                elif isinstance(parsed, dict) and "plans" in parsed:
                    query_plans = parsed["plans"]
                elif isinstance(parsed, dict) and "claims" in parsed:
                    query_plans = parsed["claims"]
                else:
                    # Try to extract array from dict values
                    for key, value in parsed.items():
                        if isinstance(value, list):
                            query_plans = value
                            break
                    else:
                        logger.error(f"Unexpected response format: {parsed}")
                        return None

                # Validate structure
                validated_plans = self._validate_plans(query_plans, len(claims))

                logger.info(f"Query planning complete: {len(validated_plans)} plans for {len(claims)} claims")
                return validated_plans

        except httpx.TimeoutException:
            logger.warning("Query planning timed out, using fallback")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Query planning JSON parse error: {e}")
            return None
        except Exception as e:
            logger.error(f"Query planning failed: {e}", exc_info=True)
            return None

    def _validate_plans(self, plans: List[Any], expected_count: int) -> List[Dict[str, Any]]:
        """Validate and normalize query plans."""
        validated = []

        for i, plan in enumerate(plans):
            if not isinstance(plan, dict):
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
