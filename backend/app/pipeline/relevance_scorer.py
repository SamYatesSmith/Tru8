"""
LLM Relevance Scorer Module

Scores evidence relevance using GPT-4o-mini instead of embedding-based similarity.
Understands whether evidence actually helps verify claims, not just topical overlap.

Architecture:
- ONE API call for all claims + all evidence (efficient batching)
- Returns evidence items with llm_relevance_score (1-5)
- Filters to score >= LLM_RELEVANCE_MIN_SCORE (default 3)
- Fair round-robin selection ensures all claims get evidence evaluated under MAX cap
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


def _fair_select_evidence(
    all_evidence: List[Dict[str, Any]],
    evidence_positions: List[tuple],
    max_evidence: int,
    evidence_by_claim: Dict[str, List[Dict[str, Any]]]
) -> tuple:
    """
    Fair round-robin selection of evidence items under the MAX cap.

    Instead of sequential truncation (which starves late-position claims),
    allocates slots evenly across claims, then fills remainder by claim size.

    Args:
        all_evidence: Flattened list of all evidence items
        evidence_positions: List of (claim_pos, index_in_claim) tuples
        max_evidence: Maximum items to send to LLM
        evidence_by_claim: Original evidence dict (claim_pos -> list)

    Returns:
        (selected_evidence, selected_positions, selected_indices_set)
        - selected_evidence: List of evidence items to score
        - selected_positions: Corresponding (claim_pos, idx) tuples
        - selected_indices_set: Set of flat indices that were selected
    """
    if len(all_evidence) <= max_evidence:
        return all_evidence, evidence_positions, set(range(len(all_evidence)))

    # Build per-claim index lists from the flat array
    claim_indices = {}  # claim_pos -> [flat_idx, ...]
    for flat_idx, (claim_pos, _) in enumerate(evidence_positions):
        if claim_pos not in claim_indices:
            claim_indices[claim_pos] = []
        claim_indices[claim_pos].append(flat_idx)

    num_claims = len(claim_indices)

    # Two-pass allocation: first pass distributes evenly, second pass redistributes unused slots
    # Sort claims by evidence count descending — larger claims absorb leftover slots
    sorted_claims = sorted(claim_indices.keys(), key=lambda cp: len(claim_indices[cp]), reverse=True)

    # Pass 1: allocate base slots evenly
    base_per_claim = max_evidence // num_claims
    remainder = max_evidence - (base_per_claim * num_claims)

    claim_slots = {}
    for i, claim_pos in enumerate(sorted_claims):
        claim_slots[claim_pos] = base_per_claim + (1 if i < remainder else 0)

    # Pass 2: redistribute unused slots (when a claim has fewer items than allocated)
    redistributed = True
    while redistributed:
        redistributed = False
        surplus = 0
        for cp in sorted_claims:
            available = len(claim_indices[cp])
            if claim_slots[cp] > available:
                surplus += claim_slots[cp] - available
                claim_slots[cp] = available
                redistributed = True
        if surplus > 0:
            # Give surplus to claims that still have unused evidence
            for cp in sorted_claims:
                if surplus <= 0:
                    break
                available = len(claim_indices[cp])
                can_take = available - claim_slots[cp]
                if can_take > 0:
                    give = min(can_take, surplus)
                    claim_slots[cp] += give
                    surplus -= give

    selected_indices = set()
    for claim_pos in sorted_claims:
        indices = claim_indices[claim_pos]
        for idx in indices[:claim_slots[claim_pos]]:
            selected_indices.add(idx)

    # Build output in original flat order (preserves evidence_index alignment)
    selected_evidence = []
    selected_positions = []
    for flat_idx in sorted(selected_indices):
        selected_evidence.append(all_evidence[flat_idx])
        selected_positions.append(evidence_positions[flat_idx])

    logger.info(
        f"[LLM SCORER] Fair selection: {len(all_evidence)} total → {len(selected_evidence)} selected "
        f"(cap={max_evidence}, {num_claims} claims, ~{base_per_claim}/claim)"
    )

    # Log per-claim selection stats
    for claim_pos in sorted(claim_indices.keys(), key=lambda x: int(x) if x.isdigit() else 999):
        total = len(claim_indices[claim_pos])
        sent = sum(1 for idx in claim_indices[claim_pos] if idx in selected_indices)
        skipped = total - sent
        if skipped > 0:
            logger.info(f"[LLM SCORER] Claim {claim_pos}: {sent}/{total} selected ({skipped} truncated)")

    return selected_evidence, selected_positions, selected_indices


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

    # Fair selection: round-robin across claims instead of sequential truncation
    max_evidence = getattr(settings, 'LLM_RELEVANCE_MAX_EVIDENCE', 50)
    selected_evidence, selected_positions, selected_indices = _fair_select_evidence(
        all_evidence, evidence_positions, max_evidence, evidence
    )

    # Check cache first
    evidence_urls = [ev.get('url', '') for ev in selected_evidence]
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
            scores = await _score_with_google(claims, selected_evidence, article_context)
            if scores:
                logger.info(f"[LLM SCORER] Scored with Google Gemini ({len(scores)} items)")
                await _cache_relevance_scores(cache_key, scores)
        except Exception as e:
            logger.warning(f"[LLM SCORER] Google scoring failed: {e}")

        # Fallback: OpenAI
        if not scores:
            try:
                logger.info("[LLM SCORER] Attempting OpenAI scoring as fallback")
                scores = await _score_with_llm(claims, selected_evidence, article_context)
                if scores:
                    logger.info(f"[LLM SCORER] Scored with OpenAI fallback ({len(scores)} items)")
                    await _cache_relevance_scores(cache_key, scores)
            except Exception as e:
                logger.warning(f"[LLM SCORER] OpenAI scoring failed: {e}, passing through unscored")
                return evidence

    if not scores:
        logger.warning("[LLM SCORER] No scores returned, passing through unscored")
        return evidence

    # Build a mapping from selected_evidence index -> score data
    # LLM returns evidence_index based on the selected_evidence ordering (0..len-1)
    score_lookup = {}
    for score_item in scores:
        idx = score_item.get('evidence_index')
        if idx is not None:
            score_lookup[idx] = score_item

    # Map selected indices back to flat indices for score application
    # selected_evidence[i] corresponds to all_evidence[sorted(selected_indices)[i]]
    selected_flat_indices = sorted(selected_indices)
    selected_to_flat = {sel_idx: flat_idx for sel_idx, flat_idx in enumerate(selected_flat_indices)}

    # Build flat_idx -> score_data lookup
    flat_score_lookup = {}
    for sel_idx, score_data in score_lookup.items():
        if sel_idx in selected_to_flat:
            flat_score_lookup[selected_to_flat[sel_idx]] = score_data

    # Apply scores to evidence items and filter
    min_score = getattr(settings, 'LLM_RELEVANCE_MIN_SCORE', 3)

    # Rebuild evidence dict with scored and filtered items
    filtered_evidence = {pos: [] for pos in evidence.keys()}
    kept_count = 0
    filtered_count = 0
    unscored_count = 0

    # Track how many claims each URL has been assigned to GLOBALLY
    max_claims_per_url = getattr(settings, 'MAX_CLAIMS_PER_URL', 1)
    assigned_url_counts = {}  # url -> int (number of claims assigned to)

    for flat_idx, ev in enumerate(all_evidence):
        score_data = flat_score_lookup.get(flat_idx)

        if score_data is not None:
            # Item was sent to LLM and got a score
            llm_score = score_data.get('score', None)
            llm_rationale = score_data.get('rationale', '')
            relevant_claims = score_data.get('relevant_claims', [])
        elif flat_idx in selected_indices:
            # Item was sent to LLM but LLM didn't return a score for it
            llm_score = None
            llm_rationale = 'LLM did not return score for this item'
            relevant_claims = []
        else:
            # Item was NOT sent to LLM (truncated by fair selection)
            llm_score = None
            llm_rationale = 'Not evaluated (exceeded MAX_EVIDENCE cap)'
            relevant_claims = []

        # Add LLM relevance data to evidence item
        ev['llm_relevance_score'] = llm_score
        ev['llm_relevance_rationale'] = llm_rationale
        ev['llm_relevant_claims'] = relevant_claims

        # Get original claim position
        original_claim_pos, _ = evidence_positions[flat_idx]
        original_claim_idx = int(original_claim_pos) if original_claim_pos.isdigit() else -1
        ev_url = ev.get('url', '')

        if llm_score is not None and llm_score >= min_score:
            # SINGLE-CLAIM ASSIGNMENT: Each evidence goes to ONE claim only (best match)
            target_claim = None

            if len(relevant_claims) > 0:
                if original_claim_idx in relevant_claims:
                    target_claim = original_claim_pos
                else:
                    for claim_idx in relevant_claims:
                        claim_pos_str = str(claim_idx)
                        if claim_pos_str in filtered_evidence:
                            target_claim = claim_pos_str
                            break
            else:
                target_claim = original_claim_pos

            # Assign to target claim ONLY if URL hasn't exceeded MAX_CLAIMS_PER_URL
            if target_claim and assigned_url_counts.get(ev_url, 0) < max_claims_per_url:
                ev_copy = dict(ev) if target_claim != original_claim_pos else ev
                if target_claim != original_claim_pos:
                    ev_copy['reassigned_from_claim'] = original_claim_pos
                    logger.debug(
                        f"[LLM SCORER] Reassigned evidence from claim {original_claim_pos} to claim {target_claim}: "
                        f"{ev.get('title', 'Unknown')[:50]}..."
                    )
                filtered_evidence[target_claim].append(ev_copy)
                assigned_url_counts[ev_url] = assigned_url_counts.get(ev_url, 0) + 1
                kept_count += 1
            elif target_claim and assigned_url_counts.get(ev_url, 0) >= max_claims_per_url:
                logger.debug(
                    f"[LLM SCORER] SKIPPED URL (assigned to {assigned_url_counts.get(ev_url, 0)} claims, max={max_claims_per_url}): {ev.get('title', 'Unknown')[:50]}..."
                )
        elif llm_score is None:
            unscored_count += 1
        else:
            filtered_count += 1
            if llm_score > 0:
                logger.debug(
                    f"[LLM SCORER] Filtered evidence (score={llm_score}): "
                    f"{ev.get('title', 'Unknown')[:50]}..."
                )

    logger.info(
        f"[LLM SCORER] Complete: kept {kept_count}, filtered {filtered_count}, unscored {unscored_count}, "
        f"globally assigned URLs: {len(assigned_url_counts)} (max {max_claims_per_url} claims/URL) "
        f"(threshold={min_score})"
    )

    # Log per-claim summary
    for cp, ev_list in filtered_evidence.items():
        logger.info(f"[LLM SCORER] Claim {cp}: {len(ev_list)} evidence items")

    # Per-claim fallback: rescue claims with 0 evidence
    # Considers both scored-but-reasonable items AND unscored items (which may be relevant
    # but were never evaluated due to MAX_EVIDENCE cap or LLM response gaps)
    FALLBACK_MIN_SCORE = 3  # Must be at least "somewhat relevant" for scored items

    for claim_pos, ev_list in evidence.items():
        if len(filtered_evidence[claim_pos]) == 0 and len(ev_list) > 0:
            # Separate scored and unscored items
            scored_reasonable = []
            unscored_items = []
            for e in ev_list:
                score = e.get('llm_relevance_score')
                url = e.get('url', '')
                url_available = assigned_url_counts.get(url, 0) < max_claims_per_url
                if not url_available:
                    continue
                if score is None:
                    unscored_items.append(e)
                elif score >= FALLBACK_MIN_SCORE:
                    scored_reasonable.append(e)

            # Priority: scored items first (we know they're relevant), then unscored
            # Sort scored by score desc, unscored by final_score desc (best available signal)
            scored_reasonable.sort(key=lambda x: x.get('llm_relevance_score', 0), reverse=True)
            unscored_items.sort(key=lambda x: x.get('final_score', 0), reverse=True)
            rescue_pool = scored_reasonable + unscored_items

            if rescue_pool:
                fallback_to_add = rescue_pool[:2]
                filtered_evidence[claim_pos] = fallback_to_add
                for fb_ev in fallback_to_add:
                    fb_url = fb_ev.get('url', '')
                    assigned_url_counts[fb_url] = assigned_url_counts.get(fb_url, 0) + 1
                score_info = [e.get('llm_relevance_score') for e in fallback_to_add]
                logger.warning(
                    f"[LLM SCORER] Claim {claim_pos} using fallback evidence "
                    f"(scores: {score_info})"
                )
            else:
                scored_items = [e for e in ev_list if e.get('llm_relevance_score') is not None]
                top_scores = sorted(
                    [e.get('llm_relevance_score', 0) for e in scored_items],
                    reverse=True
                )[:3] if scored_items else []
                unscored_n = sum(1 for e in ev_list if e.get('llm_relevance_score') is None)
                logger.warning(
                    f"[LLM SCORER] Claim {claim_pos} has NO relevant evidence - "
                    f"{len(scored_items)} scored (top: {top_scores}), {unscored_n} unscored, "
                    f"all either below {FALLBACK_MIN_SCORE} or URL already assigned"
                )

    # Global fallback: if ALL claims have 0 evidence
    total_kept = sum(len(v) for v in filtered_evidence.values())
    if total_kept == 0 and all_evidence:
        logger.warning("[LLM SCORER] All evidence filtered globally, checking for reasonable fallback")
        any_reasonable = False
        for claim_pos, ev_list in evidence.items():
            # Combine scored-reasonable and unscored items
            rescue_pool = []
            for e in ev_list:
                score = e.get('llm_relevance_score')
                url = e.get('url', '')
                url_available = assigned_url_counts.get(url, 0) < max_claims_per_url
                if not url_available:
                    continue
                if score is None or score >= FALLBACK_MIN_SCORE:
                    rescue_pool.append(e)
            # Sort: scored items by score desc, then unscored by final_score desc
            rescue_pool.sort(
                key=lambda x: (
                    0 if x.get('llm_relevance_score') is None else 1,
                    x.get('llm_relevance_score') or 0,
                    x.get('final_score', 0)
                ),
                reverse=True
            )
            if rescue_pool:
                fallback_to_add = rescue_pool[:2]
                filtered_evidence[claim_pos] = fallback_to_add
                for fb_ev in fallback_to_add:
                    fb_url = fb_ev.get('url', '')
                    assigned_url_counts[fb_url] = assigned_url_counts.get(fb_url, 0) + 1
                any_reasonable = True

        if not any_reasonable:
            logger.error(
                "[LLM SCORER] NO relevant evidence found for ANY claim - "
                "all evidence scored below minimum threshold. This indicates a search quality issue."
            )

    return filtered_evidence
