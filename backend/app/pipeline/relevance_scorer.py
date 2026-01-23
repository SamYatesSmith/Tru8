"""
LLM Relevance Scorer Module

Scores evidence relevance using GPT-4o-mini instead of embedding-based similarity.
Understands whether evidence actually helps verify claims, not just topical overlap.

Architecture:
- ONE API call for all claims + all evidence (efficient batching)
- Returns evidence items with llm_relevance_score (1-5)
- Filters to score >= 4 (configurable via LLM_RELEVANCE_MIN_SCORE)
"""
import json
import logging
import hashlib
from typing import Dict, List, Any, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

# Cache TTL for relevance scores (1 hour default) - in seconds for Redis setex
RELEVANCE_CACHE_TTL_SECONDS = getattr(settings, 'LLM_RELEVANCE_CACHE_TTL', 3600)


RELEVANCE_SCORING_PROMPT = """You are a fact-checking evidence analyst. Score how well each evidence piece helps VERIFY or REFUTE the specific claims below.

CRITICAL: Score based on EVIDENTIAL VALUE for the SPECIFIC CLAIMS, not topical similarity.

AUTOMATIC SCORE 1 (always irrelevant - these NEVER help verify specific claims):
- Pages ABOUT fact-checking tools, methodology, or how to fact-check (e.g., "Web Sites for Fact Checking", "How to verify claims")
- News aggregator index pages or category listings (e.g., "Fact Check News | Latest Articles")
- Academic papers about misinformation research or fact-checker analysis (e.g., "Fact-checking fact checkers", "Misinformation Review")
- Generic guides, tutorials, or resource lists
- Content about completely different topics/events than the claims

SCORE 4-5 (actually relevant):
- News articles reporting on the SAME EVENT mentioned in the claims
- Official statements, press releases, or documents about the claimed facts
- Statistics, data, or quotes that directly address what the claim asserts

ARTICLE BEING FACT-CHECKED:
{article_context}

CLAIMS TO VERIFY:
{claims_text}

EVIDENCE ITEMS TO SCORE:
{evidence_text}

SCORING RUBRIC:
5 = Direct proof/refutation with specific data, quotes, or official statements about THIS event
4 = Strongly relevant - reports on the same event or provides authoritative context
3 = Moderately relevant - covers the topic/event, may lack some specific details
2 = Weakly relevant - same general subject area but limited direct connection to claims
1 = OFF-TOPIC or META-SOURCE - doesn't contain facts about the claimed events (includes fact-checking guides, methodology pages, aggregator indexes)

RESPONSE FORMAT (JSON array):
[
  {{"evidence_index": 0, "score": 5, "rationale": "Brief explanation", "relevant_claims": [0, 2]}},
  ...
]

Rules:
- evidence_index: 0-based index matching evidence order above
- score: integer 1-5 per rubric (score accurately based on evidential value)
- rationale: 1-2 sentences explaining score
- relevant_claims: claim indices this evidence helps verify (empty [] if score <= 2)

Return ONLY valid JSON array."""


async def _get_cached_relevance_scores(cache_key: str) -> Optional[List[Dict[str, Any]]]:
    """Get cached relevance scores from Redis."""
    try:
        from app.core.redis import get_redis
        redis = await get_redis()
        if redis is None:
            return None

        cached = await redis.get(cache_key)
        if cached:
            logger.debug(f"Relevance score cache hit: {cache_key[:50]}...")
            return json.loads(cached)
        return None
    except Exception as e:
        logger.warning(f"Failed to get cached relevance scores: {e}")
        return None


async def _cache_relevance_scores(cache_key: str, scores: List[Dict[str, Any]]) -> None:
    """Cache relevance scores in Redis."""
    try:
        from app.core.redis import get_redis
        redis = await get_redis()
        if redis is None:
            return

        await redis.setex(cache_key, RELEVANCE_CACHE_TTL_SECONDS, json.dumps(scores))
        logger.debug(f"Cached relevance scores: {cache_key[:50]}...")
    except Exception as e:
        logger.warning(f"Failed to cache relevance scores: {e}")


def _generate_cache_key(claims: List[str], evidence_urls: List[str]) -> str:
    """Generate a cache key from claims and evidence URLs."""
    content = json.dumps({"claims": claims, "urls": sorted(evidence_urls)}, sort_keys=True)
    return f"relevance:{hashlib.md5(content.encode()).hexdigest()}"


async def _score_with_llm(
    claims: List[str],
    evidence_items: List[Dict[str, Any]],
    article_context: str
) -> List[Dict[str, Any]]:
    """
    Score evidence relevance using GPT-4o-mini.

    Args:
        claims: List of claim texts to verify
        evidence_items: Flattened list of all evidence items
        article_context: Original article excerpt for context

    Returns:
        List of score dicts with evidence_index, score, rationale, relevant_claims
    """
    import openai

    client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    # Format claims for prompt
    claims_text = "\n".join([f"[Claim {i}]: {claim}" for i, claim in enumerate(claims)])

    # Format evidence for prompt (limit to prevent token overflow)
    max_evidence = getattr(settings, 'LLM_RELEVANCE_MAX_EVIDENCE', 50)
    evidence_to_score = evidence_items[:max_evidence]

    evidence_text_parts = []
    for i, ev in enumerate(evidence_to_score):
        title = ev.get('title', 'Unknown')[:150]
        # Try 'text' first (standard), then 'snippet' (alias), then 'content' (fallback)
        # Use 500 chars for better context to identify meta-sources
        snippet = ev.get('text', ev.get('snippet', ev.get('content', '')))[:500]
        source = ev.get('source', ev.get('external_source_provider', 'Unknown'))
        url = ev.get('url', '')[:150]
        evidence_text_parts.append(
            f"[Evidence {i}]:\n"
            f"  Source: {source}\n"
            f"  Title: {title}\n"
            f"  URL: {url}\n"
            f"  Content: {snippet}"
        )

    evidence_text = "\n\n".join(evidence_text_parts)

    # Truncate article context
    article_excerpt = (article_context or "")[:2000]

    prompt = RELEVANCE_SCORING_PROMPT.format(
        article_context=article_excerpt,
        claims_text=claims_text,
        evidence_text=evidence_text
    )

    model = getattr(settings, 'LLM_RELEVANCE_MODEL', 'gpt-4o-mini-2024-07-18')

    # Calculate required output tokens: ~100 tokens per evidence item for score object
    # Plus overhead for JSON structure
    required_output_tokens = len(evidence_to_score) * 120 + 200
    max_output_tokens = max(4000, min(required_output_tokens, 16000))  # Between 4K-16K

    logger.debug(f"[LLM SCORER] Scoring {len(evidence_to_score)} items, max_tokens={max_output_tokens}")

    response = await client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": "You are a fact-checking evidence analyst. Return only valid JSON arrays."
            },
            {"role": "user", "content": prompt}
        ],
        temperature=0.1,  # Low temperature for consistency
        max_tokens=max_output_tokens,  # Dynamic based on evidence count
        response_format={"type": "json_object"}
    )

    result_text = response.choices[0].message.content

    # Check for truncation (finish_reason="length" means max_tokens was hit)
    finish_reason = response.choices[0].finish_reason
    if finish_reason == "length":
        logger.error(
            f"[LLM SCORER] Response truncated (max_tokens={max_output_tokens} insufficient). "
            f"Evidence count: {len(evidence_to_score)}. Response length: {len(result_text)} chars"
        )
        # Try to parse anyway - might have partial valid JSON

    # Log token usage for monitoring
    if hasattr(response, 'usage') and response.usage:
        logger.info(
            f"[LLM SCORER] Token usage: input={response.usage.prompt_tokens}, "
            f"output={response.usage.completion_tokens}, total={response.usage.total_tokens}"
        )

    # Parse JSON response - handle both array and object formats
    try:
        result = json.loads(result_text)
        # Handle case where LLM wraps array in an object
        if isinstance(result, dict):
            # Look for array in common keys (order by likelihood)
            for key in ['scores', 'evidence_scores', 'results', 'items', 'evidence', 'data']:
                if key in result and isinstance(result[key], list):
                    return result[key]
            # Check if dict itself contains score entries (numbered keys like "0", "1")
            if any(k.isdigit() for k in result.keys()):
                # Convert dict with numeric keys to list
                scores = []
                for k, v in sorted(result.items(), key=lambda x: int(x[0]) if x[0].isdigit() else 999):
                    if isinstance(v, dict) and 'score' in v:
                        v['evidence_index'] = int(k) if k.isdigit() else len(scores)
                        scores.append(v)
                if scores:
                    return scores
            # If no array found, return empty
            logger.warning(f"LLM returned object without recognizable scores array: {list(result.keys())}")
            return []
        elif isinstance(result, list):
            return result
        else:
            logger.warning(f"Unexpected LLM response type: {type(result)}")
            return []
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM relevance scores: {e}")
        return []


async def score_evidence_batch(
    claims: List[str],
    evidence: Dict[str, List[Dict[str, Any]]],
    article_context: str
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Score all evidence items and filter by relevance threshold.

    Args:
        claims: List of claim texts (ordered by position)
        evidence: Dict mapping claim_position -> list of evidence items
        article_context: Article excerpt for context

    Returns:
        Filtered evidence dict with only high-relevance items (score >= threshold)
    """
    if not getattr(settings, 'ENABLE_LLM_RELEVANCE_SCORER', True):
        logger.info("[LLM SCORER] Disabled via config, passing through unscored")
        return evidence

    if not claims or not evidence:
        return evidence

    # Flatten all evidence items while tracking their original position
    all_evidence = []
    evidence_positions = []  # Track (claim_position, index_in_claim_list)

    for claim_pos, ev_list in evidence.items():
        for idx, ev in enumerate(ev_list):
            all_evidence.append(ev)
            evidence_positions.append((claim_pos, idx))

    if not all_evidence:
        return evidence

    logger.info(f"[LLM SCORER] Scoring {len(all_evidence)} evidence items for {len(claims)} claims")

    # Check cache first
    evidence_urls = [ev.get('url', '') for ev in all_evidence]
    cache_key = _generate_cache_key(claims, evidence_urls)

    cached_scores = await _get_cached_relevance_scores(cache_key)
    if cached_scores:
        logger.info(f"[LLM SCORER] Using cached scores ({len(cached_scores)} items)")
        scores = cached_scores
    else:
        # Call LLM for scoring
        try:
            scores = await _score_with_llm(claims, all_evidence, article_context)
            if scores:
                await _cache_relevance_scores(cache_key, scores)
        except Exception as e:
            logger.warning(f"[LLM SCORER] LLM scoring failed: {e}, passing through unscored")
            return evidence

    if not scores:
        logger.warning("[LLM SCORER] No scores returned, passing through unscored")
        return evidence

    # Create a lookup for scores by evidence index
    score_lookup = {}
    for score_item in scores:
        idx = score_item.get('evidence_index')
        if idx is not None:
            score_lookup[idx] = score_item

    # Apply scores to evidence items and filter
    min_score = getattr(settings, 'LLM_RELEVANCE_MIN_SCORE', 4)

    # Rebuild evidence dict with scored and filtered items
    filtered_evidence = {pos: [] for pos in evidence.keys()}
    kept_count = 0
    filtered_count = 0

    for flat_idx, ev in enumerate(all_evidence):
        score_data = score_lookup.get(flat_idx, {})
        llm_score = score_data.get('score', 0)
        llm_rationale = score_data.get('rationale', '')
        relevant_claims = score_data.get('relevant_claims', [])

        # Add LLM relevance data to evidence item
        ev['llm_relevance_score'] = llm_score
        ev['llm_relevance_rationale'] = llm_rationale
        ev['llm_relevant_claims'] = relevant_claims

        # Get original claim position
        claim_pos, _ = evidence_positions[flat_idx]

        if llm_score >= min_score:
            filtered_evidence[claim_pos].append(ev)
            kept_count += 1
        else:
            filtered_count += 1
            if llm_score > 0:
                logger.debug(
                    f"[LLM SCORER] Filtered evidence (score={llm_score}): "
                    f"{ev.get('title', 'Unknown')[:50]}..."
                )

    logger.info(
        f"[LLM SCORER] Complete: kept {kept_count}, filtered {filtered_count} "
        f"(threshold={min_score})"
    )

    # If filtering removed ALL evidence, keep top items as fallback
    total_kept = sum(len(v) for v in filtered_evidence.values())
    if total_kept == 0 and all_evidence:
        logger.warning("[LLM SCORER] All evidence filtered, keeping top items as fallback")
        # Sort by score and keep best items per claim
        for claim_pos, ev_list in evidence.items():
            sorted_ev = sorted(
                ev_list,
                key=lambda x: x.get('llm_relevance_score', 0),
                reverse=True
            )
            # Keep top 2 as fallback
            filtered_evidence[claim_pos] = sorted_ev[:2]

    return filtered_evidence
