"""
Query Planning Agent for Fact-Checking Pipeline

This module provides LLM-powered query planning to generate targeted search queries
with DYNAMIC context-aware freshness decisions.

Key Features:
- Batch processing: Single LLM call for all claims in an article (~$0.02/article)
- Context-aware: Receives article context to make intelligent freshness decisions
- Dynamic freshness: LLM decides freshness per claim based on article context
- No hardcoded domain logic: Works for any domain (sports, politics, finance, etc.)
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
# FRESHNESS REFERENCE (for LLM guidance and staleness checking)
# ============================================================
# Brave Search freshness values:
#   - pd (past day)     -> 1 day    - Breaking news, live events
#   - pw (past week)    -> 7 days   - Fast-changing data (standings, polls)
#   - pm (past month)   -> 30 days  - Periodic updates (monthly stats)
#   - py (past year)    -> 365 days - Stable facts, annual data
#   - 2y (2 years)      -> 730 days - Historical, scientific
#
# The LLM decides freshness dynamically based on article context.
# These defaults are only used for staleness warnings when LLM
# doesn't provide freshness or for fallback scenarios.
# ============================================================

DEFAULT_FRESHNESS = {
    "max_age_days": 365,
    "brave_freshness": "py",
    "stale_warning_days": 730,
    "description": "Default freshness for claims"
}


class LLMQueryPlanner:
    """
    Plans search queries using LLM for semantic understanding.

    Uses batch processing to minimize API calls and costs.
    """

    SYSTEM_PROMPT = """You are a Tru8 fact-checking specialist specializing in evidence retrieval strategy. Generate search queries and determine evidence requirements for claims.

CRITICAL - DATE CONTEXT:
You will be given TODAY'S DATE at the start of the user message. This is the ACTUAL current date.
- ALWAYS use this date when generating queries about recent/current events
- NEVER guess or hallucinate dates - use ONLY the date provided
- If the article mentions "this week" or "yesterday", calculate relative to TODAY'S DATE
- For recent events, include the correct year (from TODAY'S DATE) in your queries

You will receive ARTICLE CONTEXT that tells you:
- The domain (Sports, Politics, Finance, etc.)
- Temporal context (what time period the article covers)
- Key entities mentioned
- Evidence guidance (how fresh evidence needs to be)

USE THIS CONTEXT to make intelligent decisions about each claim.

FOR EACH CLAIM, OUTPUT:
1. queries: 2-3 specific search queries
   - Use EXACT names, numbers, and entities from the claim
   - For RECENT events, include the year from TODAY'S DATE (e.g., if today is 2025-12-03, use "2025" not "2023" or "2024")
   - Keep queries concise (5-10 words)
   - DO NOT add site: filters

2. freshness: How recent must evidence be? Choose one:
   - "pd" (past day): Breaking news, live events, real-time data
   - "pw" (past week): Fast-changing data (standings, polls, prices)
   - "pm" (past month): Periodic updates (monthly stats, recent news)
   - "py" (past year): Stable facts, annual data, historical

3. source_hints: Brief description of authoritative source types

4. reasoning: Why this freshness level is appropriate

QUERY STRATEGIES:
- RANKINGS/COMPARISONS: Query the ranking directly, query both entities being compared
- STATISTICS: Include the relevant time period (season, quarter, year)
- CURRENT STATE: Include recent date context to get fresh results
- HISTORICAL: Can use broader time range

AUTHORITATIVE SOURCES BY DOMAIN (use in source_hints and priority_sources):
- SPORTS STATISTICS: transfermarkt.com, fbref.com, whoscored.com, official league sites
- TRANSFER NEWS: transfermarkt.com, fabrizio romano, official club announcements
- POLITICAL: Official government sites (.gov), established news (Reuters, AP, BBC)
- FINANCIAL: Company filings (SEC, Companies House), Bloomberg, Reuters
- SCIENTIFIC: Peer-reviewed journals, academic institutions (.edu), official health organizations
- GENERAL: Primary sources, official statements, established news organizations

CRITICAL - OFFICIAL SOURCE PRIORITY:
When a claim attributes a statement/action to a NAMED ORGANIZATION (e.g., "X released a statement", "Y announced", "Z confirmed", "W explained"):
1. IDENTIFY the organization's official website domain (use your knowledge)
2. ADD that domain to priority_sources
3. INCLUDE one query with site:[official-domain] filter
The official source is DEFINITIVE - it can verify the claim alone without needing other sources.

For PLAYER STATISTICS claims (goals, assists, appearances, market value):
- Always include priority_sources: ["transfermarkt.com", "fbref.com"]
- Query format: "[Player Name] [season] statistics" or "[Player Name] goals assists [year]"

HANDLING UNCERTAINTY:
If a claim is too vague to query effectively:
- Generate broader queries covering multiple interpretations
- Set freshness to "py" (past year) for safety
- In reasoning field, note what makes the claim ambiguous
- Do NOT guess or fabricate specific details not in the claim

RESPOND WITH JSON:
{
  "plans": [
    {
      "claim_index": 0,
      "queries": ["query 1", "query 2"],
      "freshness": "pw",
      "source_hints": "Official data sources",
      "reasoning": "Data changes frequently"
    }
  ]
}"""

    def __init__(self):
        self.openai_api_key = settings.OPENAI_API_KEY
        self.timeout = settings.QUERY_PLANNING_TIMEOUT
        self.model = settings.QUERY_PLANNING_MODEL

    async def plan_queries_batch(
        self,
        claims: List[Dict[str, Any]],
        article_context: Optional[Dict[str, Any]] = None
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Plan queries for all claims in a single LLM call with article context.

        Args:
            claims: List of claim dictionaries with 'text' and optional metadata
            article_context: Article classification with temporal_context, key_entities, evidence_guidance

        Returns:
            List of query plans with freshness decisions, or None on failure
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

            # Build article context section
            article_context_section = ""
            if article_context:
                article_context_section = f"""
ARTICLE CONTEXT:
- Domain: {article_context.get('primary_domain', 'General')}
- Temporal Context: {article_context.get('temporal_context', 'Not specified')}
- Key Entities: {', '.join(article_context.get('key_entities', [])) or 'Not specified'}
- Evidence Guidance: {article_context.get('evidence_guidance', 'Use appropriate sources')}
"""
                logger.info(f"[QUERY_PLANNER] Using article context: domain={article_context.get('primary_domain')}")

            current_year = now.strftime("%Y")
            user_prompt = f"""TODAY'S DATE: {current_date} (CURRENT YEAR: {current_year})
Use {current_year} in queries for recent events - NEVER use older years like 2023 or 2024 unless the claim explicitly refers to those years.
{article_context_section}
Generate query plans for each of these {len(claims)} claims:

{claims_text}

For EACH claim, provide: queries, freshness (pd/pw/pm/py), source_hints, and reasoning.
Return a JSON object with "plans" array containing exactly {len(claims)} plan objects."""

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
        """Validate and normalize query plans with freshness decisions."""
        validated = []
        valid_freshness = {"pd", "pw", "pm", "py", "2y"}
        current_year = datetime.now().year

        for i, plan in enumerate(plans):
            if not isinstance(plan, dict):
                logger.warning(f"[QUERY_PLANNER] Plan {i} is not a dict, skipping")
                continue

            # Extract and validate freshness
            freshness = plan.get("freshness", "py")
            if freshness not in valid_freshness:
                logger.warning(f"[QUERY_PLANNER] Invalid freshness '{freshness}', defaulting to 'py'")
                freshness = "py"

            validated_plan = {
                "claim_index": i,  # Always use enumeration index, never trust LLM's claim_index
                "queries": plan.get("queries", []),
                "freshness": freshness,
                "source_hints": plan.get("source_hints", ""),
                "reasoning": plan.get("reasoning", ""),
                # Keep for backward compatibility but no longer used for routing
                "claim_type": plan.get("claim_type", "general"),
                "priority_sources": plan.get("priority_sources", []),
            }

            # Ensure queries is a list
            if isinstance(validated_plan["queries"], str):
                validated_plan["queries"] = [validated_plan["queries"]]

            # Ensure priority_sources is a list
            if isinstance(validated_plan["priority_sources"], str):
                validated_plan["priority_sources"] = [validated_plan["priority_sources"]]

            # POST-PROCESS: Fix hallucinated years in queries for recent claims
            # For claims requiring recent evidence (pd/pw/pm), replace old years with current year
            if freshness in {"pd", "pw", "pm"}:
                validated_plan["queries"] = self._fix_hallucinated_years(
                    validated_plan["queries"], current_year
                )

            # Limit queries to 4 per claim
            validated_plan["queries"] = validated_plan["queries"][:4]

            validated.append(validated_plan)

        return validated

    def _fix_hallucinated_years(self, queries: List[str], current_year: int) -> List[str]:
        """
        Fix hallucinated years in LLM-generated queries.

        LLMs often generate old years (2023, 2024) due to training data patterns.
        For recent claims, we replace these with the current year.

        Args:
            queries: List of search query strings
            current_year: The actual current year (e.g., 2025)

        Returns:
            List of queries with corrected years
        """
        import re

        fixed_queries = []
        # Years that are likely hallucinated (1-3 years before current)
        hallucinated_years = [str(current_year - i) for i in range(1, 4)]

        for query in queries:
            original = query
            # Replace hallucinated years with current year
            for old_year in hallucinated_years:
                # Match year as whole word (not part of larger number)
                pattern = rf'\b{old_year}\b'
                if re.search(pattern, query):
                    query = re.sub(pattern, str(current_year), query)

            if query != original:
                logger.info(f"[QUERY_PLANNER] Fixed hallucinated year: '{original}' -> '{query}'")

            fixed_queries.append(query)

        return fixed_queries

    def get_site_filter(self, priority_sources: List[str], claim_type: str = "") -> str:
        """
        Generate a site filter string for search queries.

        Only uses LLM-suggested sources - no hardcoded domain defaults.
        Let the search engine find the best sources dynamically.

        Args:
            priority_sources: List of priority domains from LLM
            claim_type: Unused, kept for backward compatibility

        Returns:
            Site filter string (e.g., "site:example.com OR site:other.com")
        """
        if not priority_sources:
            return ""

        # Use first 2 sources to keep query short
        site_filters = [f"site:{s}" for s in priority_sources[:2]]
        return " OR ".join(site_filters)


# Singleton instance
_query_planner: Optional[LLMQueryPlanner] = None


def get_query_planner() -> LLMQueryPlanner:
    """Get or create the query planner singleton."""
    global _query_planner
    if _query_planner is None:
        _query_planner = LLMQueryPlanner()
    return _query_planner


def get_freshness_for_claim_type(claim_type: str = "") -> Dict[str, Any]:
    """
    Get default freshness requirements.

    NOTE: This function is deprecated. Freshness is now determined dynamically
    by the LLM query planner based on article context. This function returns
    default values for backward compatibility and fallback scenarios.

    Args:
        claim_type: Unused, kept for backward compatibility

    Returns:
        Dictionary with default freshness values
    """
    return DEFAULT_FRESHNESS


def check_evidence_staleness(
    evidence_date: Optional[str],
    freshness: Optional[str] = None,
    reference_date: Optional[datetime] = None,
    claim_type: str = ""  # Deprecated, kept for backward compatibility
) -> Dict[str, Any]:
    """
    Check if evidence is stale based on freshness requirements.

    Freshness is determined dynamically by the LLM query planner. This function
    validates evidence age against the freshness decision for judge warnings.

    Args:
        evidence_date: The published date of the evidence (ISO format or partial)
        freshness: LLM-decided freshness (pd/pw/pm/py/2y) - determines max_age
        reference_date: The date to compare against (default: today)
        claim_type: Deprecated, unused

    Returns:
        Dictionary with:
        - is_stale: True if evidence exceeds max_age_days
        - is_warning: True if evidence exceeds stale_warning_days
        - age_days: Age of evidence in days (or None if unparseable)
        - max_age_days: Maximum acceptable age based on freshness
        - message: Human-readable staleness description
    """
    if reference_date is None:
        reference_date = datetime.now()

    # Map freshness codes to max age days
    freshness_to_days = {
        "pd": {"max_age_days": 1, "stale_warning_days": 3},
        "pw": {"max_age_days": 7, "stale_warning_days": 14},
        "pm": {"max_age_days": 30, "stale_warning_days": 60},
        "py": {"max_age_days": 365, "stale_warning_days": 730},
        "2y": {"max_age_days": 730, "stale_warning_days": 1095},
    }

    # Get freshness config based on LLM decision
    config = freshness_to_days.get(freshness, freshness_to_days["py"])
    max_age = config["max_age_days"]
    warning_age = config["stale_warning_days"]

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

    # Human-readable freshness description
    freshness_desc = {
        "pd": "real-time", "pw": "weekly", "pm": "monthly",
        "py": "annual", "2y": "historical"
    }.get(freshness, "standard")

    # Generate message
    if age_days is None:
        message = f"Evidence date unknown - cannot verify recency"
    elif is_stale:
        message = f"STALE: Evidence is {age_days} days old, max allowed for {freshness_desc} data is {max_age} days"
    elif is_warning:
        message = f"WARNING: Evidence is {age_days} days old, consider finding more recent sources"
    else:
        message = f"Evidence is {age_days} days old (acceptable for {freshness_desc} data)"

    return {
        "is_stale": is_stale,
        "is_warning": is_warning,
        "age_days": age_days,
        "max_age_days": max_age,
        "warning_age_days": warning_age,
        "message": message
    }
