"""
Query Planning Agent for Evidence Pipeline

This module provides LLM-powered query planning to generate targeted search queries
for individual ELEMENTS of claims, with DYNAMIC context-aware freshness decisions.

Key Features:
- Element-level: Generates queries per-element (not per-claim) for targeted retrieval
- Batch processing: Single LLM call for all elements across all claims (~$0.02/article)
- Context-aware: Receives article context to make intelligent freshness decisions
- Dynamic freshness: LLM decides freshness per element based on article context
- No hardcoded domain logic: Works for any domain (sports, politics, finance, etc.)
- Graceful fallback: Falls back to standard query formulation on failure
"""

import logging
import json
from datetime import datetime
from typing import Dict, List, Any, Optional
import httpx
from app.core.config import settings
from app.services.google_ai import call_google_ai

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
    "description": "Default freshness for claims",
}


class LLMQueryPlanner:
    """
    Plans search queries using LLM for semantic understanding.

    Uses batch processing to minimize API calls and costs.
    """

    SYSTEM_PROMPT = """You are a Tru8 evidence retrieval specialist. Generate targeted search queries for individual ELEMENTS of factual claims.

WHAT ARE ELEMENTS?
Each claim has been decomposed into 1-5 ELEMENTS — specific conditions that must be evidentially addressed for the claim to be fully examined. Your job is to generate search queries that find evidence addressing each ELEMENT specifically.

CRITICAL - DATE CONTEXT:
You will be given TODAY'S DATE at the start of the user message. This is the ACTUAL current date.
- ALWAYS use this date when generating queries about recent/current events
- NEVER guess or hallucinate dates - use ONLY the date provided
- If a claim mentions "this week" or "yesterday", calculate relative to TODAY'S DATE
- For recent events, include the correct year (from TODAY'S DATE) in your queries

You will receive ARTICLE CONTEXT and CLAIMS WITH ELEMENTS. Use the article context to make intelligent freshness decisions for each element.

FOR EACH ELEMENT, OUTPUT:
1. queries: 2-3 specific search queries targeting THIS element
   - Use EXACT names, numbers, and entities from the element description
   - For RECENT events, include the year from TODAY'S DATE
   - Keep queries concise (5-10 words)
   - DO NOT add site: filters

2. freshness: How recent must evidence be? Choose one:
   - "pd" (past day): Breaking news, live events, real-time data
   - "pw" (past week): Fast-changing data (standings, polls, prices)
   - "pm" (past month): Periodic updates (monthly stats, recent news)
   - "py" (past year): Stable facts, annual data, historical

   IMPORTANT — a year mentioned IN the claim does NOT mean "breaking news":
   - "Did X happen in 2026?" — about a stable past event → use "py"
   - "What's the current state of X right now?" — only then use "pd" or "pw"
   - Default to "py" for scientific, historical, archaeological, medical,
     or established factual claims, even if a recent year appears in the claim.
   - Use "pd"/"pw" only when the element explicitly demands live, unfolding,
     or real-time evidence (e.g. ongoing legal proceedings, today's market data).

3. reasoning: Why this freshness level and these queries are appropriate

QUERY STRATEGIES:
- RANKINGS/COMPARISONS: Query the ranking directly, query both entities being compared
- STATISTICS: Include the relevant time period (season, quarter, year)
- CURRENT STATE: Include recent date context to get fresh results
- HISTORICAL: Can use broader time range

HANDLING UNCERTAINTY:
If an element is too vague to query effectively:
- Generate broader queries covering multiple interpretations
- Set freshness to "py" (past year) for safety
- In reasoning field, note what makes the element ambiguous

RESPOND WITH JSON:
{
  "plans": [
    {
      "claim_index": 0,
      "element_id": "e1",
      "queries": ["query 1", "query 2"],
      "freshness": "pw",
      "reasoning": "Data changes frequently"
    }
  ]
}"""

    def __init__(self):
        self.openai_api_key = settings.OPENAI_API_KEY
        self.google_ai_api_key = getattr(settings, "GOOGLE_AI_API_KEY", "")
        self.timeout = settings.QUERY_PLANNING_TIMEOUT
        self.model = settings.QUERY_PLANNING_MODEL  # OpenAI fallback model
        self.google_model = getattr(
            settings, "GOOGLE_LLM_MODEL", "gemini-2.5-flash-lite"
        )

    async def plan_queries_batch(
        self,
        claims_with_elements: List[Dict[str, Any]],
        article_context: Optional[Dict[str, Any]] = None,
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Plan queries for all elements across all claims in a single LLM call.

        Args:
            claims_with_elements: List of claim dicts, each with:
                - 'text': claim text
                - 'claim_index': position in the check
                - 'elements': list of {"element_id": str, "description": str}
                Optional temporal metadata: is_time_sensitive, temporal_markers, temporal_window
            article_context: Article classification with temporal_context, key_entities, etc.

        Returns:
            List of query plans (one per element) with element_id and freshness, or None on failure
        """
        if not claims_with_elements:
            return []

        if not self.openai_api_key:
            logger.warning("[QUERY_PLANNER] OpenAI API key not configured")
            return None

        # Count total elements for logging and validation
        total_elements = sum(len(c.get("elements", [])) for c in claims_with_elements)
        if total_elements == 0:
            logger.warning("[QUERY_PLANNER] No elements found in claims")
            return []

        try:
            # Current date for context
            now = datetime.now()
            current_date = now.strftime("%Y-%m-%d")
            current_year = now.strftime("%Y")
            logger.info(
                f"[QUERY_PLANNER] Current date: {current_date}, {total_elements} elements across {len(claims_with_elements)} claims"
            )

            # Format claims with elements for the prompt
            claim_element_lines = []
            # Build element-to-claim text mapping for relevance validation
            element_texts = []  # (claim_text, element_description) pairs

            for c in claims_with_elements:
                claim_idx = c.get("claim_index", 0)
                claim_text = c.get("text", "")
                elements = c.get("elements", [])

                # Add temporal context if available
                temporal_info = []
                if c.get("is_time_sensitive"):
                    temporal_info.append("TIME-SENSITIVE")
                if c.get("temporal_markers"):
                    markers = c.get("temporal_markers", [])
                    years = [
                        str(m.get("value")) for m in markers if m.get("type") == "YEAR"
                    ]
                    if years:
                        temporal_info.append(f"Years mentioned: {', '.join(years)}")
                if c.get("temporal_window") and c.get("temporal_window") != "any":
                    temporal_info.append(f"Temporal window: {c.get('temporal_window')}")

                temporal_suffix = (
                    f" [{' | '.join(temporal_info)}]" if temporal_info else ""
                )

                claim_element_lines.append(
                    f'\nCLAIM {claim_idx}: "{claim_text}"{temporal_suffix}'
                )
                for el in elements:
                    eid = el.get("element_id", "?")
                    desc = el.get("description", "")
                    claim_element_lines.append(f"  - {eid}: {desc}")
                    element_texts.append((claim_text, desc))

            claims_elements_text = "\n".join(claim_element_lines)

            # Build article context section
            article_context_section = ""
            if article_context:
                article_context_section = f"""
ARTICLE CONTEXT:
- Domain: {article_context.get('primary_domain', 'General')}
- Jurisdiction: {article_context.get('jurisdiction', 'Global')}
- Temporal Context: {article_context.get('temporal_context', 'Not specified')}
- Key Entities: {', '.join(article_context.get('key_entities', [])) or 'Not specified'}
- Evidence Guidance: {article_context.get('evidence_guidance', 'Use appropriate sources')}
"""
                logger.info(
                    f"[QUERY_PLANNER] Using article context: domain={article_context.get('primary_domain')}, jurisdiction={article_context.get('jurisdiction')}"
                )

            user_prompt = f"""TODAY'S DATE: {current_date} (CURRENT YEAR: {current_year})
Use {current_year} in queries for recent events - NEVER use older years unless the claim explicitly refers to those years.
{article_context_section}
Generate query plans for each ELEMENT below. Each element is a specific condition of a claim that needs evidence.
{claims_elements_text}

For EACH element, provide: claim_index, element_id, queries, freshness (pd/pw/pm/py), and reasoning.
Return a JSON object with "plans" array containing exactly {total_elements} plan objects (one per element)."""

            # Try Google first, then OpenAI as fallback
            parsed = None

            if self.google_ai_api_key:
                try:
                    parsed = await self._plan_with_google(user_prompt)
                    if parsed:
                        logger.info(
                            "[QUERY_PLANNER] Using Google Gemini for query planning"
                        )
                except Exception as e:
                    logger.warning(f"[QUERY_PLANNER] Google planning failed: {e}")

            if parsed is None and self.openai_api_key:
                logger.info(
                    "[QUERY_PLANNER] Attempting OpenAI query planning as fallback"
                )
                try:
                    parsed = await self._plan_with_openai(user_prompt)
                except Exception as e:
                    logger.error(f"[QUERY_PLANNER] OpenAI planning failed: {e}")
                    return None

            if parsed is None:
                logger.error("[QUERY_PLANNER] Both LLM providers failed")
                return None

            logger.debug(
                f"[QUERY_PLANNER] Raw response keys: {list(parsed.keys()) if isinstance(parsed, dict) else 'array'}"
            )

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
                for key, value in parsed.items():
                    if (
                        isinstance(value, list)
                        and len(value) > 0
                        and isinstance(value[0], dict)
                    ):
                        query_plans = value
                        logger.debug(f"[QUERY_PLANNER] Found plans under key: {key}")
                        break
                else:
                    logger.error(
                        f"[QUERY_PLANNER] No plans array found. Keys: {list(parsed.keys())}"
                    )
                    return None

            if not query_plans:
                logger.error("[QUERY_PLANNER] Empty plans array")
                return None

            # Validate structure and filter irrelevant queries
            validated_plans = self._validate_plans(
                query_plans, total_elements, element_texts
            )

            if len(validated_plans) < total_elements:
                logger.warning(
                    f"[QUERY_PLANNER] Only {len(validated_plans)} plans for {total_elements} elements - some elements will use fallback"
                )

            logger.info(
                f"[QUERY_PLANNER] SUCCESS: {len(validated_plans)} plans for {total_elements} elements across {len(claims_with_elements)} claims"
            )
            return validated_plans

        except httpx.TimeoutException:
            logger.warning("[QUERY_PLANNER] TIMEOUT: API call took too long")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"[QUERY_PLANNER] JSON ERROR: {e}")
            return None
        except Exception as e:
            logger.error(
                f"[QUERY_PLANNER] EXCEPTION: {type(e).__name__}: {e}", exc_info=True
            )
            return None

    async def _plan_with_google(self, user_prompt: str) -> Optional[Dict[str, Any]]:
        """Plan queries using Google Gemini (primary provider)"""
        full_prompt = f"{self.SYSTEM_PROMPT}\n\n{user_prompt}\n\nProvide your response as valid JSON."
        return await call_google_ai(
            full_prompt,
            temperature=0.1,
            max_tokens=3000,
            timeout=self.timeout,
            model=self.google_model,
        )

    async def _plan_with_openai(self, user_prompt: str) -> Optional[Dict[str, Any]]:
        """Plan queries using OpenAI (fallback provider)"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.openai_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": self.SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt},
                    ],
                    "temperature": 0.1,
                    "max_tokens": 3000,
                    "response_format": {"type": "json_object"},
                },
            )

            if response.status_code != 200:
                logger.error(f"OpenAI query planning error: {response.status_code}")
                return None

            result = response.json()
            content = result["choices"][0]["message"]["content"]
            return json.loads(content)

    def _validate_plans(
        self,
        plans: List[Any],
        expected_count: int,
        element_texts: Optional[List[tuple]] = None,
    ) -> List[Dict[str, Any]]:
        """Validate and normalize element-level query plans with freshness decisions.

        Args:
            plans: Raw plans from LLM response
            expected_count: Expected number of element plans
            element_texts: List of (claim_text, element_description) tuples for relevance validation
        """
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
                logger.warning(
                    f"[QUERY_PLANNER] Invalid freshness '{freshness}', defaulting to 'py'"
                )
                freshness = "py"

            validated_plan = {
                "claim_index": plan.get("claim_index", 0),
                "element_id": plan.get("element_id", f"e{i + 1}"),
                "queries": plan.get("queries", []),
                "freshness": freshness,
                "reasoning": plan.get("reasoning", ""),
            }

            # Ensure queries is a list
            if isinstance(validated_plan["queries"], str):
                validated_plan["queries"] = [validated_plan["queries"]]

            # POST-PROCESS: Fix hallucinated years in queries for recent elements.
            # Pass the original claim text so years the user typed (e.g. "September
            # 2024" in a historical claim) are preserved rather than rewritten to
            # current year.
            if freshness in {"pd", "pw", "pm"}:
                claim_text_for_years = ""
                if element_texts and i < len(element_texts):
                    claim_text_for_years = element_texts[i][0]
                validated_plan["queries"] = self._fix_hallucinated_years(
                    validated_plan["queries"], current_year, claim_text_for_years
                )

            # Limit queries to 2 per element
            validated_plan["queries"] = validated_plan["queries"][:2]

            # Validate query relevance using both claim text and element description
            if element_texts and i < len(element_texts):
                claim_text, element_desc = element_texts[i]
                # Combine claim + element text for relevance checking
                context_text = f"{claim_text} {element_desc}"
                validated_plan["queries"] = self._validate_query_relevance_sync(
                    validated_plan["queries"], context_text
                )

            validated.append(validated_plan)

        return validated

    def _fix_hallucinated_years(
        self, queries: List[str], current_year: int, claim_text: str = ""
    ) -> List[str]:
        """
        Fix hallucinated years in LLM-generated queries.

        LLMs often generate old years (2023, 2024) due to training data patterns.
        For recent claims, we replace these with the current year — EXCEPT when
        the year appears verbatim in the user's claim text, in which case it is
        an intentional historical reference and must be preserved.

        Args:
            queries: List of search query strings
            current_year: The actual current year (e.g., 2025)
            claim_text: Original claim text; any year appearing here is excluded
                from the hallucinated set and preserved in queries.

        Returns:
            List of queries with corrected years
        """
        import re

        # Years explicitly referenced in the claim are not hallucinations.
        claim_years = set(re.findall(r"\b(?:19|20)\d{2}\b", claim_text))

        # Candidate hallucinated years: 1-3 years before current, minus any
        # year the user typed in the claim.
        hallucinated_years = [
            str(current_year - i)
            for i in range(1, 4)
            if str(current_year - i) not in claim_years
        ]

        fixed_queries = []
        for query in queries:
            original = query
            for old_year in hallucinated_years:
                pattern = rf"\b{old_year}\b"
                if re.search(pattern, query):
                    query = re.sub(pattern, str(current_year), query)

            if query != original:
                logger.info(
                    f"[QUERY_PLANNER] Fixed hallucinated year: '{original}' -> '{query}'"
                )

            fixed_queries.append(query)

        return fixed_queries

    def _validate_query_relevance_sync(
        self, queries: List[str], claim_text: str, min_similarity: float = 0.15
    ) -> List[str]:
        """
        Filter queries with no keyword overlap with claim.

        Uses lightweight keyword overlap (Jaccard similarity) to catch egregiously
        irrelevant queries without requiring embedding computation.

        Args:
            queries: Generated search queries
            claim_text: Original claim text
            min_similarity: Minimum keyword overlap ratio (0-1)

        Returns:
            Filtered list of relevant queries (at least 1 kept)
        """
        import re

        stop_words = {
            "the",
            "and",
            "for",
            "are",
            "was",
            "were",
            "been",
            "have",
            "has",
            "had",
            "will",
            "would",
            "could",
            "should",
            "this",
            "that",
            "with",
            "from",
            "they",
            "their",
            "there",
            "what",
            "when",
            "where",
            "which",
            "about",
            "into",
            "than",
            "then",
        }

        def extract_keywords(text: str) -> set:
            words = re.findall(r"\b[a-zA-Z]{4,}\b", text.lower())
            return {w for w in words if w not in stop_words}

        claim_keywords = extract_keywords(claim_text)
        if not claim_keywords:
            return queries  # Can't validate, pass through

        relevant = []
        for query in queries:
            query_keywords = extract_keywords(query)
            if not query_keywords:
                relevant.append(query)
                continue

            overlap = len(claim_keywords & query_keywords)
            union = len(claim_keywords | query_keywords)
            similarity = overlap / union if union > 0 else 0

            if similarity >= min_similarity:
                relevant.append(query)
            else:
                logger.warning(
                    f"[QUERY_PLANNER] Filtered irrelevant query: '{query}' "
                    f"(similarity={similarity:.2f} < {min_similarity})"
                )

        return relevant if relevant else queries[:1]  # Keep at least 1


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
    claim_type: str = "",  # Deprecated, kept for backward compatibility
) -> Dict[str, Any]:
    """
    Check if evidence is stale based on freshness requirements.

    Freshness is determined dynamically by the LLM query planner. This function
    validates evidence age against the freshness decision for staleness warnings.

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
                ("%Y-%m-%d", 10),  # 2025-11-28
                ("%Y-%m-%dT%H:%M:%S", 19),  # 2025-11-28T12:30:45
                ("%d/%m/%Y", 10),  # 28/11/2025
                ("%Y", 4),  # 2025
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
        "pd": "real-time",
        "pw": "weekly",
        "pm": "monthly",
        "py": "annual",
        "2y": "historical",
    }.get(freshness, "standard")

    # Generate message
    if age_days is None:
        message = f"Evidence date unknown - cannot verify recency"
    elif is_stale:
        message = f"STALE: Evidence is {age_days} days old, max allowed for {freshness_desc} data is {max_age} days"
    elif is_warning:
        message = f"WARNING: Evidence is {age_days} days old, consider finding more recent sources"
    else:
        message = (
            f"Evidence is {age_days} days old (acceptable for {freshness_desc} data)"
        )

    return {
        "is_stale": is_stale,
        "is_warning": is_warning,
        "age_days": age_days,
        "max_age_days": max_age,
        "warning_age_days": warning_age,
        "message": message,
    }
