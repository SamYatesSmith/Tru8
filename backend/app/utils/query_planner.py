"""
Query Planning Agent for Fact-Checking Pipeline

This module provides LLM-powered query planning to generate targeted search queries
based on the semantic type of claims being verified.

Key Features:
- Batch processing: Single LLM call for all claims in an article (~$0.02/article)
- Semantic classification: Identifies claim type (squad, stats, contract, etc.)
- Source prioritization: Routes to authoritative sources per claim type
- **Domain-aware freshness**: Different claim types require different evidence recency
- Graceful fallback: Falls back to standard query formulation on failure
"""

import logging
import json
from datetime import datetime
from typing import Dict, List, Any, Optional
import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)


# ============================================================
# DOMAIN-AWARE EVIDENCE FRESHNESS REQUIREMENTS
# ============================================================
# Different claim types require different evidence recency.
# This mapping defines max_age_days for each claim type.
#
# Brave Search freshness values:
#   - pd (past day)     -> 1 day
#   - pw (past week)    -> 7 days
#   - pm (past month)   -> 30 days
#   - py (past year)    -> 365 days
#   - 2y (2 years)      -> 730 days
#
# CRITICAL: Sports squad/standing claims change DAILY during season!
# ============================================================

CLAIM_TYPE_FRESHNESS = {
    # SPORTS - Time-critical (changes daily/weekly during season)
    "squad_composition": {
        "max_age_days": 14,       # Squad can change in transfer windows
        "brave_freshness": "pw",  # Past week
        "stale_warning_days": 30, # Warn if evidence > 30 days old
        "description": "Current squad membership - changes during transfer windows"
    },
    "league_standing": {
        "max_age_days": 7,        # Table changes after each matchweek
        "brave_freshness": "pw",  # Past week
        "stale_warning_days": 14,
        "description": "League table/standings - changes after each match"
    },
    "match_result": {
        "max_age_days": 7,        # Recent match results
        "brave_freshness": "pw",  # Past week
        "stale_warning_days": 14,
        "description": "Recent match results and scores"
    },
    "player_statistics": {
        "max_age_days": 30,       # Season stats update weekly
        "brave_freshness": "pm",  # Past month
        "stale_warning_days": 60,
        "description": "Player performance statistics for current season"
    },
    "comparison_ranking": {
        "max_age_days": 30,       # Rankings change with new data
        "brave_freshness": "pm",  # Past month
        "stale_warning_days": 60,
        "description": "Comparative rankings and statistics"
    },
    "transfer_rumor": {
        "max_age_days": 14,       # Transfer news moves fast
        "brave_freshness": "pw",  # Past week
        "stale_warning_days": 30,
        "description": "Transfer speculation and rumors"
    },

    # SPORTS - Less time-critical
    "contract_info": {
        "max_age_days": 180,      # Contracts change less frequently
        "brave_freshness": "py",  # Past year (contracts are annual data)
        "stale_warning_days": 365,
        "description": "Contract details and expiry dates"
    },

    # NON-SPORTS DOMAINS
    "political": {
        "max_age_days": 90,       # Policy positions can change
        "brave_freshness": "pm",  # Past month
        "stale_warning_days": 180,
        "description": "Political claims and statements"
    },
    "scientific": {
        "max_age_days": 730,      # Scientific findings are more stable
        "brave_freshness": "2y",  # 2 years
        "stale_warning_days": 365,
        "description": "Scientific research and findings"
    },
    "economic": {
        "max_age_days": 90,       # Economic data updates quarterly
        "brave_freshness": "pm",  # Past month
        "stale_warning_days": 180,
        "description": "Economic statistics and financial data"
    },
    "general": {
        "max_age_days": 365,      # Default for unclassified claims
        "brave_freshness": "py",  # Past year
        "stale_warning_days": 730,
        "description": "General claims without specific time sensitivity"
    }
}


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

SMART QUERY STRATEGIES:

1. COMPARISON/RANKING CLAIMS (e.g., "X is second only to Y", "X is behind Y"):
   - Query the RANKING directly: "Champions League top scorers 2024-25", "most goals in Europe clubs"
   - Query BOTH entities' stats: "Arsenal goals Champions League 2024-25", "Bayern Munich goals Champions League 2024-25"
   - Use official sources: UEFA, Premier League, Bundesliga official sites

2. PLAYER STATISTICS (goals, assists, appearances):
   - Include SEASON: "Adeyemi goals assists 2024-25 season"
   - Include COMPETITION: "Adeyemi Bundesliga statistics", "Adeyemi Champions League stats"
   - Use stats sites: fbref, transfermarkt, whoscored

3. CONTRACT/TRANSFER INFO:
   - Query player profile pages: "Adeyemi contract expiry transfermarkt"
   - Include exact year if mentioned: "Adeyemi contract 2027"

4. SQUAD COMPOSITION (who plays for whom):
   - Query official squad pages: "Arsenal squad 2024-25"
   - Query player profiles: "Gyokeres Arsenal", "Merino Arsenal current club"

5. CURRENT STANDINGS/TABLES:
   - Include date/matchweek: "Premier League table December 2024"
   - Query league official sites: "Premier League standings"

CLAIM TYPES: league_standing, player_statistics, contract_info, transfer_rumor, squad_composition, match_result, comparison_ranking, political, scientific, economic, general

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
            "player_statistics": ["fbref.com", "transfermarkt.com", "whoscored.com"],
            "contract_info": ["transfermarkt.com"],
            "transfer_rumor": ["skysports.com", "bbc.co.uk/sport"],
            "match_result": ["premierleague.com", "flashscore.com"],
            "league_standing": ["premierleague.com", "uefa.com"],
            "comparison_ranking": ["uefa.com", "fbref.com", "transfermarkt.com"],
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


def get_freshness_for_claim_type(claim_type: str) -> Dict[str, Any]:
    """
    Get freshness requirements for a claim type.

    Args:
        claim_type: The type of claim (e.g., 'squad_composition', 'contract_info')

    Returns:
        Dictionary with:
        - brave_freshness: Brave search freshness parameter (pd/pw/pm/py/2y)
        - max_age_days: Maximum acceptable evidence age in days
        - stale_warning_days: Days after which evidence triggers a warning
        - description: Human-readable description of freshness requirement
    """
    return CLAIM_TYPE_FRESHNESS.get(claim_type, CLAIM_TYPE_FRESHNESS["general"])


def check_evidence_staleness(
    claim_type: str,
    evidence_date: Optional[str],
    reference_date: Optional[datetime] = None
) -> Dict[str, Any]:
    """
    Check if evidence is stale for a given claim type.

    Args:
        claim_type: The type of claim being verified
        evidence_date: The published date of the evidence (ISO format or partial)
        reference_date: The date to compare against (default: today)

    Returns:
        Dictionary with:
        - is_stale: True if evidence exceeds max_age_days
        - is_warning: True if evidence exceeds stale_warning_days
        - age_days: Age of evidence in days (or None if unparseable)
        - max_age_days: Maximum acceptable age for this claim type
        - message: Human-readable staleness description
    """
    if reference_date is None:
        reference_date = datetime.now()

    freshness_req = get_freshness_for_claim_type(claim_type)
    max_age = freshness_req["max_age_days"]
    warning_age = freshness_req["stale_warning_days"]

    # Parse evidence date
    age_days = None
    if evidence_date:
        try:
            # Try various date formats with their expected string lengths
            format_specs = [
                ("%Y-%m-%d", 10),       # 2025-11-28
                ("%Y-%m-%dT%H:%M:%S", 19),  # 2025-11-28T12:30:45
                ("%d/%m/%Y", 10),       # 28/11/2025
                ("%Y", 4),              # 2025
            ]
            for fmt, expected_len in format_specs:
                try:
                    if fmt == "%Y" and len(evidence_date) >= 4:
                        # Year only - assume mid-year
                        parsed = datetime(int(evidence_date[:4]), 6, 15)
                    else:
                        date_str = evidence_date[:expected_len]
                        parsed = datetime.strptime(date_str, fmt)
                    age_days = (reference_date - parsed).days
                    break
                except (ValueError, TypeError):
                    continue
        except Exception:
            pass

    # Determine staleness
    is_stale = age_days is not None and age_days > max_age
    is_warning = age_days is not None and age_days > warning_age

    # Generate message
    if age_days is None:
        message = f"Evidence date unknown - cannot verify recency for {claim_type} claim"
    elif is_stale:
        message = f"STALE: Evidence is {age_days} days old, max allowed for {claim_type} is {max_age} days"
    elif is_warning:
        message = f"WARNING: Evidence is {age_days} days old, consider finding more recent sources for {claim_type}"
    else:
        message = f"Evidence is {age_days} days old (acceptable for {claim_type})"

    return {
        "is_stale": is_stale,
        "is_warning": is_warning,
        "age_days": age_days,
        "max_age_days": max_age,
        "warning_age_days": warning_age,
        "message": message
    }
