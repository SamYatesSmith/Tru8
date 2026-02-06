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

CRITICAL: Score based on EVIDENTIAL VALUE for the SPECIFIC CLAIMS, considering both content relevance AND source authority.

CLAIM-EVIDENCE MATCHING IS ESSENTIAL:
- Each piece of evidence may only help verify SOME claims, not all
- An article about "Topic X" only helps verify claims that SPECIFICALLY discuss Topic X
- Generic background information about a topic does NOT help verify specific factual claims
- The "relevant_claims" field MUST list ONLY the claims that evidence DIRECTLY addresses
- If evidence is about a DIFFERENT aspect of the same topic, it is NOT relevant to that claim

CLAIM TYPES - Recognize what kind of evidence each claim needs:
1. EVENT CLAIMS (e.g., "5 healthcare workers infected") → Need news reports about that specific incident
2. FACTUAL/REFERENCE CLAIMS (e.g., "virus has 40-75% fatality rate") → Need authoritative reference sources

SOURCE AUTHORITY - Match source type to claim type:
- MEDICAL/HEALTH claims (mortality rates, symptoms, treatments) → Prefer WHO, CDC, NHS, medical journals
  → Sources with "entertainment_focus" or "lifestyle_content" flags should score 1-2
- SCIENTIFIC claims (statistics, research findings) → Prefer peer-reviewed, academic, government data
  → Low-credibility sources (<50%) should score 1-2 for statistical claims
- SPORTS claims → Sports news, league sites, tabloids all acceptable
- ENTERTAINMENT/CELEBRITY claims → Tabloids and lifestyle magazines ARE appropriate

CREDIBILITY SIGNALS IN EVIDENCE:
- "tier: general" with low credibility = unknown/unvetted source, treat with skepticism
- "risk_flags: entertainment_focus" = lifestyle magazine, inappropriate for medical claims
- "risk_flags: sensationalism" = tabloid, deprioritize for scientific claims

AUTOMATIC SCORE 1-2:
- Pages ABOUT fact-checking tools (meta-sources)
- News aggregator index pages
- Sources with entertainment_focus/lifestyle_content flags FOR medical/scientific claims
- Unknown sources (tier: general, <50% credibility) for factual/statistical claims

ARTICLE BEING FACT-CHECKED:
{article_context}

CLAIMS TO VERIFY:
{claims_text}

EVIDENCE ITEMS TO SCORE:
{evidence_text}

SCORING RUBRIC:
5 = Direct proof/refutation from authoritative source for this claim type
4 = Strongly relevant from appropriate source
3 = Relevant content BUT source questionable for this claim type
2 = Weakly relevant OR inappropriate source type
1 = OFF-TOPIC, META-SOURCE, or inappropriate source for claim type

IMPORTANT: WHO, CDC, NIH, medical journals for medical claims should score 4-5. But lifestyle magazines (Cosmopolitan, etc.) for medical claims should score 1-2 regardless of content.

RESPONSE FORMAT (JSON array):
[
  {{"evidence_index": 0, "score": 5, "rationale": "WHO source authoritative for mortality claim", "relevant_claims": [0, 2]}},
  {{"evidence_index": 1, "score": 2, "rationale": "Lifestyle magazine inappropriate for medical statistics", "relevant_claims": []}}
]

EXAMPLE OF CORRECT CLAIM-EVIDENCE MATCHING:
Claims:
[Claim 0]: "The company laid off 500 employees in January 2024"
[Claim 1]: "The CEO announced record profits for Q4 2023"
[Claim 2]: "The company's stock price fell 20% after the announcement"

Evidence about "Company announces layoffs":
- Relevant to Claim 0 (layoffs) = YES, score 4-5, relevant_claims: [0]
- Relevant to Claim 1 (profits) = NO, different topic
- Relevant to Claim 2 (stock price) = MAYBE if it mentions market reaction, otherwise NO

Evidence about "Company Q4 earnings report":
- Relevant to Claim 0 (layoffs) = NO, different topic
- Relevant to Claim 1 (profits) = YES, score 4-5, relevant_claims: [1]
- Relevant to Claim 2 (stock price) = MAYBE if it mentions stock movement

Rules:
- evidence_index: 0-based index matching evidence order above
- score: integer 1-5 per rubric (score accurately based on evidential value AND source authority)
- rationale: 1-2 sentences explaining score, mention source appropriateness if relevant
- relevant_claims: CRITICAL - list ONLY the specific claim indices (0, 1, 2...) that this evidence DIRECTLY helps verify or refute
  * If evidence discusses "Event A" but claim is about "Event B", relevant_claims should NOT include that claim
  * Only list claims where the evidence provides DIRECT proof, refutation, or context for THAT SPECIFIC claim
  * An article about the same general topic is NOT automatically relevant to all claims about that topic
  * Empty [] only if score <= 2 (off-topic evidence)

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


async def _score_with_google(
    claims: List[str],
    evidence_items: List[Dict[str, Any]],
    article_context: str
) -> Optional[List[Dict[str, Any]]]:
    """
    Score evidence relevance using Google Gemini (primary provider).

    Args:
        claims: List of claim texts to verify
        evidence_items: Flattened list of all evidence items
        article_context: Original article excerpt for context

    Returns:
        List of score dicts with evidence_index, score, rationale, relevant_claims, or None on failure
    """
    import httpx

    google_ai_key = getattr(settings, 'GOOGLE_AI_API_KEY', '')
    if not google_ai_key:
        return None

    google_model = getattr(settings, 'GOOGLE_LLM_MODEL', 'gemini-2.5-flash-lite')

    # Format claims for prompt
    claims_text = "\n".join([f"[Claim {i}]: {claim}" for i, claim in enumerate(claims)])

    # Format evidence for prompt (limit to prevent token overflow)
    max_evidence = getattr(settings, 'LLM_RELEVANCE_MAX_EVIDENCE', 50)
    evidence_to_score = evidence_items[:max_evidence]

    evidence_text_parts = []
    for i, ev in enumerate(evidence_to_score):
        title = ev.get('title', 'Unknown')[:150]
        snippet = ev.get('text', ev.get('snippet', ev.get('content', '')))[:500]
        source = ev.get('source', ev.get('external_source_provider', 'Unknown'))
        url = ev.get('url', '')[:150]

        # Add credibility context for LLM decision-making
        tier = ev.get('tier', 'general')
        cred_score = ev.get('credibility_score', 0.4)
        risk_flags = ev.get('risk_flags', [])
        if isinstance(risk_flags, str):
            risk_flags = [risk_flags] if risk_flags else []
        risk_str = ', '.join(risk_flags) if risk_flags else 'None'

        evidence_text_parts.append(
            f"[Evidence {i}]:\n"
            f"  Source: {source}\n"
            f"  Credibility: {tier} ({cred_score:.0%})\n"
            f"  Risk Flags: {risk_str}\n"
            f"  Title: {title}\n"
            f"  URL: {url}\n"
            f"  Content: {snippet}"
        )

    evidence_text = "\n\n".join(evidence_text_parts)
    article_excerpt = (article_context or "")[:2000]

    prompt = RELEVANCE_SCORING_PROMPT.format(
        article_context=article_excerpt,
        claims_text=claims_text,
        evidence_text=evidence_text
    )

    # Calculate required output tokens
    required_output_tokens = len(evidence_to_score) * 120 + 200
    max_output_tokens = max(4000, min(required_output_tokens, 16000))

    full_prompt = f"You are a fact-checking evidence analyst. Return only valid JSON arrays.\n\n{prompt}"

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{google_model}:generateContent?key={google_ai_key}",
                headers={"Content-Type": "application/json"},
                json={
                    "contents": [{"parts": [{"text": full_prompt}]}],
                    "generationConfig": {
                        "temperature": 0.1,
                        "maxOutputTokens": max_output_tokens,
                        "responseMimeType": "application/json"
                    }
                }
            )

            if response.status_code != 200:
                logger.error(f"Google AI relevance scoring error: {response.status_code}")
                return None

            result = response.json()
            content_text = result["candidates"][0]["content"]["parts"][0]["text"]

            # Parse JSON response
            parsed = json.loads(content_text)
            if isinstance(parsed, dict):
                for key in ['scores', 'evidence_scores', 'results', 'items', 'evidence', 'data']:
                    if key in parsed and isinstance(parsed[key], list):
                        return parsed[key]
                return []
            elif isinstance(parsed, list):
                return parsed
            return []

    except Exception as e:
        logger.error(f"Google AI relevance scoring failed: {e}")
        return None


async def _score_with_llm(
    claims: List[str],
    evidence_items: List[Dict[str, Any]],
    article_context: str
) -> List[Dict[str, Any]]:
    """
    Score evidence relevance using OpenAI GPT-4o-mini (fallback provider).

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

        # Add credibility context for LLM decision-making
        tier = ev.get('tier', 'general')
        cred_score = ev.get('credibility_score', 0.4)
        risk_flags = ev.get('risk_flags', [])
        if isinstance(risk_flags, str):
            risk_flags = [risk_flags] if risk_flags else []
        risk_str = ', '.join(risk_flags) if risk_flags else 'None'

        evidence_text_parts.append(
            f"[Evidence {i}]:\n"
            f"  Source: {source}\n"
            f"  Credibility: {tier} ({cred_score:.0%})\n"
            f"  Risk Flags: {risk_str}\n"
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
        # Try Google first, then OpenAI as fallback
        scores = None

        # Primary: Google Gemini
        try:
            scores = await _score_with_google(claims, all_evidence, article_context)
            if scores:
                logger.info(f"[LLM SCORER] Scored with Google Gemini ({len(scores)} items)")
                await _cache_relevance_scores(cache_key, scores)
        except Exception as e:
            logger.warning(f"[LLM SCORER] Google scoring failed: {e}")

        # Fallback: OpenAI
        if not scores:
            try:
                logger.info("[LLM SCORER] Attempting OpenAI scoring as fallback")
                scores = await _score_with_llm(claims, all_evidence, article_context)
                if scores:
                    logger.info(f"[LLM SCORER] Scored with OpenAI fallback ({len(scores)} items)")
                    await _cache_relevance_scores(cache_key, scores)
            except Exception as e:
                logger.warning(f"[LLM SCORER] OpenAI scoring failed: {e}, passing through unscored")
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

    # Track which evidence URLs have been assigned GLOBALLY (across ALL claims)
    # This is CRITICAL: once a URL is assigned to ANY claim, it cannot be assigned to others
    # This prevents the same article appearing for multiple claims
    assigned_urls_globally = set()

    for flat_idx, ev in enumerate(all_evidence):
        score_data = score_lookup.get(flat_idx, {})
        llm_score = score_data.get('score', 0)
        llm_rationale = score_data.get('rationale', '')
        relevant_claims = score_data.get('relevant_claims', [])

        # Add LLM relevance data to evidence item
        ev['llm_relevance_score'] = llm_score
        ev['llm_relevance_rationale'] = llm_rationale
        ev['llm_relevant_claims'] = relevant_claims

        # Get original claim position (as integer for comparison with relevant_claims)
        original_claim_pos, _ = evidence_positions[flat_idx]
        original_claim_idx = int(original_claim_pos) if original_claim_pos.isdigit() else -1
        ev_url = ev.get('url', '')

        if llm_score >= min_score:
            # SINGLE-CLAIM ASSIGNMENT: Each evidence goes to ONE claim only (best match)
            # This prevents the same article appearing for multiple claims.
            # Priority: original claim if it's in relevant_claims, else first relevant claim

            target_claim = None

            if len(relevant_claims) > 0:
                # Check if original claim is in the relevant list - prefer it for stability
                if original_claim_idx in relevant_claims:
                    target_claim = original_claim_pos
                else:
                    # Use the first claim in relevant_claims that exists
                    for claim_idx in relevant_claims:
                        claim_pos_str = str(claim_idx)
                        if claim_pos_str in filtered_evidence:
                            target_claim = claim_pos_str
                            break
            else:
                # LLM didn't specify - keep in original claim
                target_claim = original_claim_pos

            # Assign to target claim ONLY if URL not already assigned to ANY claim
            # This is the critical single-assignment enforcement
            if target_claim and ev_url not in assigned_urls_globally:
                ev_copy = dict(ev) if target_claim != original_claim_pos else ev
                if target_claim != original_claim_pos:
                    ev_copy['reassigned_from_claim'] = original_claim_pos
                    logger.debug(
                        f"[LLM SCORER] Reassigned evidence from claim {original_claim_pos} to claim {target_claim}: "
                        f"{ev.get('title', 'Unknown')[:50]}..."
                    )
                filtered_evidence[target_claim].append(ev_copy)
                assigned_urls_globally.add(ev_url)  # Mark as used GLOBALLY
                kept_count += 1
            elif target_claim and ev_url in assigned_urls_globally:
                # URL already assigned to another claim - skip this duplicate
                logger.debug(
                    f"[LLM SCORER] SKIPPED duplicate URL (already assigned): {ev.get('title', 'Unknown')[:50]}..."
                )
        else:
            filtered_count += 1
            if llm_score > 0:
                logger.debug(
                    f"[LLM SCORER] Filtered evidence (score={llm_score}): "
                    f"{ev.get('title', 'Unknown')[:50]}..."
                )

    logger.info(
        f"[LLM SCORER] Complete: kept {kept_count}, filtered {filtered_count}, "
        f"globally unique URLs: {len(assigned_urls_globally)} "
        f"(threshold={min_score})"
    )

    # Log per-claim summary to verify diversity
    for cp, ev_list in filtered_evidence.items():
        urls = [e.get('url', '')[:60] for e in ev_list]
        logger.info(f"[LLM SCORER] Claim {cp}: {len(ev_list)} evidence items")

    # Per-claim fallback: ensure no claim ends up with 0 evidence if we had REASONABLE evidence
    # CRITICAL: Only use fallback if evidence scored at least 3 (somewhat relevant)
    # Scores 1-2 = off-topic garbage (e.g., "CIA PROPAGANDA GUIDELINES" for EU censorship claim)
    # It's better to show "insufficient evidence" than completely irrelevant garbage
    FALLBACK_MIN_SCORE = 3  # Must be at least "somewhat relevant"

    for claim_pos, ev_list in evidence.items():
        if len(filtered_evidence[claim_pos]) == 0 and len(ev_list) > 0:
            # Sort by score
            sorted_ev = sorted(
                ev_list,
                key=lambda x: x.get('llm_relevance_score', 0),
                reverse=True
            )
            # Only keep fallback evidence that:
            # 1. Scored >= 3 (somewhat relevant)
            # 2. NOT already assigned to another claim (respect global uniqueness)
            reasonable_fallback = [
                e for e in sorted_ev
                if e.get('llm_relevance_score', 0) >= FALLBACK_MIN_SCORE
                and e.get('url', '') not in assigned_urls_globally
            ]

            if reasonable_fallback:
                fallback_to_add = reasonable_fallback[:2]
                filtered_evidence[claim_pos] = fallback_to_add
                # Track these URLs globally
                for fb_ev in fallback_to_add:
                    assigned_urls_globally.add(fb_ev.get('url', ''))
                logger.warning(
                    f"[LLM SCORER] Claim {claim_pos} using fallback evidence "
                    f"(scores: {[e.get('llm_relevance_score', 0) for e in fallback_to_add]})"
                )
            else:
                # ALL evidence either scored < 3 OR already used by another claim
                logger.warning(
                    f"[LLM SCORER] Claim {claim_pos} has NO relevant evidence - "
                    f"all {len(ev_list)} items either scored below {FALLBACK_MIN_SCORE} or already assigned "
                    f"(top scores: {[e.get('llm_relevance_score', 0) for e in sorted_ev[:3]]})"
                )

    # Global fallback: if ALL claims have 0 evidence, only keep items that scored >= 3
    # and haven't been used elsewhere
    total_kept = sum(len(v) for v in filtered_evidence.values())
    if total_kept == 0 and all_evidence:
        logger.warning("[LLM SCORER] All evidence filtered globally, checking for reasonable fallback")
        any_reasonable = False
        for claim_pos, ev_list in evidence.items():
            sorted_ev = sorted(
                ev_list,
                key=lambda x: x.get('llm_relevance_score', 0),
                reverse=True
            )
            # Only keep if scored >= 3 AND not already assigned
            reasonable = [
                e for e in sorted_ev
                if e.get('llm_relevance_score', 0) >= FALLBACK_MIN_SCORE
                and e.get('url', '') not in assigned_urls_globally
            ]
            if reasonable:
                fallback_to_add = reasonable[:2]
                filtered_evidence[claim_pos] = fallback_to_add
                # Track globally
                for fb_ev in fallback_to_add:
                    assigned_urls_globally.add(fb_ev.get('url', ''))
                any_reasonable = True

        if not any_reasonable:
            logger.error(
                "[LLM SCORER] NO relevant evidence found for ANY claim - "
                "all evidence scored below minimum threshold. This indicates a search quality issue."
            )

    return filtered_evidence
