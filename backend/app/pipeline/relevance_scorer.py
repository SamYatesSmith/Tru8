"""
LLM Relevance Scorer Module

Scores evidence relevance using LLM instead of embedding-based similarity.
Understands whether evidence actually addresses claims, not just topical overlap.

Architecture:
- ONE API call for all claims + all evidence (efficient batching)
- Returns evidence items with llm_relevance_score (1-5) annotated
- Score-1 items (off-topic) are excluded with receipt tracking
- Score >= 2 and unevaluated (None) items are kept
- Fair round-robin selection ensures all claims get evidence evaluated under MAX cap
"""

import json
import logging
import hashlib
import httpx
from typing import Dict, List, Any, Optional

from app.core.config import settings
from app.services.google_ai import call_google_ai, call_google_ai_with_usage

logger = logging.getLogger(__name__)

# Cache TTL for relevance scores (1 hour default) - in seconds for Redis setex
RELEVANCE_CACHE_TTL_SECONDS = getattr(settings, "LLM_RELEVANCE_CACHE_TTL", 3600)

# NF-07 history:
#
# - Original NF-07 (commit ec175d1, 2026-04-24): bypassed the score=1
#   exclusion for any item with `external_source_provider` set.
# - NF-07-hardening (commit 910c8e1, 2026-04-27): scoped via a frozen
#   whitelist of 13 canonical-record providers after TRU-A3E8-3199
#   audit showed the unscoped bypass had a 12% real mapping rate
#   (2 of 17 bypassed items actually picked by the mapper).
# - NF-07-v2 (this commit): replaced the frozen whitelist with adapter
#   self-declaration via `emits_structural_metadata: bool = False` on
#   the GovernmentAPIClient base class. Each adapter declares whether
#   its snippet is structured metadata (URL identity is the
#   primary-tier signal) or content text (scorer's judgement is
#   final). New adapters self-classify; no central list to maintain.
#
# Bypass logic (below): look up the adapter in the registry by
# external_source_provider name; if the adapter declares
# emits_structural_metadata=True, bypass score=1 exclusion. Unknown
# provider names default to "no bypass" — defensive for typos and
# legacy data.


def _adapter_emits_structural_metadata(provider: Optional[str]) -> bool:
    """NF-07-v2: check the adapter's self-declared snippet shape.

    Returns True if the adapter named by `provider` declares its snippet
    is structured metadata (e.g. taxonomic hierarchy, bill stage, data
    observation). False for search-shape adapters whose snippets are
    content text — and for unknown / unregistered provider names.

    Lazy import keeps this module's import-time light and avoids
    circular dependencies between pipeline and services.
    """
    if not provider:
        return False
    try:
        from app.services.government_api_client import get_api_registry

        adapter = get_api_registry().get_adapter_by_name(provider)
    except Exception:
        return False
    return bool(getattr(adapter, "emits_structural_metadata", False))


def _is_stub_snippet(snippet: Optional[str], title: Optional[str]) -> bool:
    """F-R1b (2026-07-09, audit/2026-07-09_retrieval_quality_plan.md): true
    when a snippet carries no content beyond the item's own title — e.g. the
    WHO adapter's fallback ``"WHO health indicator: <IndicatorName>"``.

    The NF-07 bypass exists because structured-metadata snippets (a bill
    stage, a data observation) can be substantive even when the scorer rates
    them 1. A snippet that merely restates the title is not metadata — there
    is nothing behind it, so the scorer's judgement should stand. Deliberately
    conservative: only fires when the title is embedded with ≤40 chars of
    boilerplate around it (worst case = a content-less item is excluded, the
    NF-07-hardening preference).
    """
    s = (snippet or "").strip()
    t = (title or "").strip()
    if not s:
        return True
    if not t:
        return False
    if s.lower() == t.lower():
        return True
    return t.lower() in s.lower() and (len(s) - len(t)) <= 40


RELEVANCE_SCORING_PROMPT = """You are an evidence analyst. Score how well each evidence piece is TOPICALLY RELEVANT to the specific claims below.

CRITICAL: Score based on TOPICAL RELEVANCE ONLY. Do NOT judge source reputation, authority, or trustworthiness. A blog post that directly addresses a claim is more relevant than a prestigious journal article about a different topic.

CLAIM-EVIDENCE MATCHING IS ESSENTIAL:
- Each piece of evidence may only address SOME claims, not all
- An article about "Topic X" only helps examine claims that SPECIFICALLY discuss Topic X
- Generic background information about a topic does NOT address specific factual claims
- The "relevant_claims" field MUST list ONLY the claims that evidence DIRECTLY addresses
- If evidence is about a DIFFERENT aspect of the same topic, it is NOT relevant to that claim

SCORING RUBRIC:
5 = Directly addresses the specific claim with substantive content
4 = Strongly relevant to the claim topic with useful detail
3 = Partially relevant, addresses related but not identical topic
2 = Weakly relevant, same general domain but different specific topic
1 = Off-topic, does not address the claim, or is a meta-source (page about fact-checking tools, news aggregator index)

ARTICLE UNDER EXAMINATION:
{article_context}

CLAIMS TO EXAMINE:
{claims_text}

EVIDENCE ITEMS TO SCORE:
{evidence_text}

RESPONSE FORMAT (JSON array):
[
  {{"evidence_index": 0, "score": 5, "rationale": "Directly provides mortality data cited in claim", "relevant_claims": [0, 2]}},
  {{"evidence_index": 1, "score": 1, "rationale": "Article is about a different policy entirely", "relevant_claims": []}}
]

Rules:
- evidence_index: 0-based index matching evidence order above
- score: integer 1-5 per rubric (score based on TOPICAL RELEVANCE ONLY, not source reputation)
- rationale: 1-2 sentences explaining WHY the evidence is or is not relevant to the specific claim
- relevant_claims: list ONLY the specific claim indices (0, 1, 2...) that this evidence DIRECTLY addresses
  * If evidence discusses "Event A" but claim is about "Event B", relevant_claims should NOT include that claim
  * Only list claims where the evidence provides DIRECT information for THAT SPECIFIC claim
  * Empty [] only if score <= 2 (off-topic evidence)

Return ONLY valid JSON array."""


async def _get_cached_relevance_scores(
    cache_key: str,
) -> Optional[List[Dict[str, Any]]]:
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
    content = json.dumps(
        {"claims": claims, "urls": sorted(evidence_urls)}, sort_keys=True
    )
    # v2 prefix: invalidates pre-2026-05-01 entries written before the
    # evidence_index alignment fix in score_evidence_batch. Old entries
    # were keyed identically but stored scores under index positions
    # that depended on dict insertion order; reading them back into a
    # different ordering corrupted score-to-item mapping.
    return f"relevance:v2:{hashlib.md5(content.encode()).hexdigest()}"


def _claim_pos_sort_key(claim_pos: str):
    """Stable sort key for claim positions.

    Numeric positions sort numerically; non-numeric tail-sort lexically.
    Underscore-prefixed keys (e.g. _excluded) are filtered separately
    by callers and should not be passed here.
    """
    try:
        return (0, int(claim_pos))
    except (ValueError, TypeError):
        return (1, claim_pos)


def _fair_select_evidence(
    all_evidence: List[Dict[str, Any]],
    evidence_positions: List[tuple],
    max_evidence: int,
    evidence_by_claim: Dict[str, List[Dict[str, Any]]],
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
    sorted_claims = sorted(
        claim_indices.keys(), key=lambda cp: len(claim_indices[cp]), reverse=True
    )

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
        for idx in indices[: claim_slots[claim_pos]]:
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
    for claim_pos in sorted(
        claim_indices.keys(), key=lambda x: int(x) if x.isdigit() else 999
    ):
        total = len(claim_indices[claim_pos])
        sent = sum(1 for idx in claim_indices[claim_pos] if idx in selected_indices)
        skipped = total - sent
        if skipped > 0:
            logger.info(
                f"[LLM SCORER] Claim {claim_pos}: {sent}/{total} selected ({skipped} truncated)"
            )

    return selected_evidence, selected_positions, selected_indices


async def _score_with_google(
    claims: List[str], evidence_items: List[Dict[str, Any]], article_context: str
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
    # Format claims for prompt
    claims_text = "\n".join([f"[Claim {i}]: {claim}" for i, claim in enumerate(claims)])

    # Format evidence for prompt (limit to prevent token overflow)
    max_evidence = getattr(settings, "LLM_RELEVANCE_MAX_EVIDENCE", 50)
    evidence_to_score = evidence_items[:max_evidence]

    evidence_text_parts = []
    for i, ev in enumerate(evidence_to_score):
        title = ev.get("title", "Unknown")[:150]
        snippet = ev.get("text", ev.get("snippet", ev.get("content", "")))[:500]
        source = ev.get("source", ev.get("external_source_provider", "Unknown"))
        url = ev.get("url", "")[:150]

        evidence_text_parts.append(
            f"[Evidence {i}]:\n"
            f"  Source: {source}\n"
            f"  Title: {title}\n"
            f"  URL: {url}\n"
            f"  Content: {snippet}"
        )

    evidence_text = "\n\n".join(evidence_text_parts)
    article_excerpt = (article_context or "")[:2000]

    prompt = RELEVANCE_SCORING_PROMPT.format(
        article_context=article_excerpt,
        claims_text=claims_text,
        evidence_text=evidence_text,
    )

    # Calculate required output tokens
    required_output_tokens = len(evidence_to_score) * 120 + 200
    max_output_tokens = max(4000, min(required_output_tokens, 16000))

    full_prompt = f"You are an evidence relevance analyst. Return only valid JSON arrays.\n\n{prompt}"

    try:
        parsed, _usage = await call_google_ai_with_usage(
            full_prompt,
            temperature=0.1,
            max_tokens=max_output_tokens,
            timeout=60,
        )
        if parsed is None:
            return None

        if isinstance(parsed, dict):
            # Try known wrapper keys first (fast path)
            for key in [
                "scores",
                "evidence_scores",
                "results",
                "items",
                "evidence",
                "data",
            ]:
                if key in parsed and isinstance(parsed[key], list):
                    return parsed[key]

            # Generic fallback: find any value that looks like a scores array
            for key, value in parsed.items():
                if isinstance(value, list) and len(value) > 0:
                    if isinstance(value[0], dict) and (
                        "score" in value[0] or "evidence_index" in value[0]
                    ):
                        logger.info(
                            f"[LLM SCORER] Found scores under unexpected key: '{key}'"
                        )
                        return value

            # Numeric-key fallback
            if any(k.isdigit() for k in parsed.keys()):
                scores = []
                for k, v in sorted(
                    parsed.items(),
                    key=lambda x: int(x[0]) if x[0].isdigit() else 999,
                ):
                    if isinstance(v, dict) and "score" in v:
                        v["evidence_index"] = int(k) if k.isdigit() else len(scores)
                        scores.append(v)
                if scores:
                    return scores

            logger.warning(
                f"[LLM SCORER] Google returned object without recognizable scores array: {list(parsed.keys())}"
            )
            return []
        elif isinstance(parsed, list):
            return parsed
        return []

    except Exception as e:
        logger.error(f"Google AI relevance scoring failed: {e}")
        return None


async def _score_with_llm(
    claims: List[str], evidence_items: List[Dict[str, Any]], article_context: str
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
    # Format claims for prompt
    claims_text = "\n".join([f"[Claim {i}]: {claim}" for i, claim in enumerate(claims)])

    # Format evidence for prompt (limit to prevent token overflow)
    max_evidence = getattr(settings, "LLM_RELEVANCE_MAX_EVIDENCE", 50)
    evidence_to_score = evidence_items[:max_evidence]

    evidence_text_parts = []
    for i, ev in enumerate(evidence_to_score):
        title = ev.get("title", "Unknown")[:150]
        # Try 'text' first (standard), then 'snippet' (alias), then 'content' (fallback)
        # Use 500 chars for better context to identify meta-sources
        snippet = ev.get("text", ev.get("snippet", ev.get("content", "")))[:500]
        source = ev.get("source", ev.get("external_source_provider", "Unknown"))
        url = ev.get("url", "")[:150]

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
        evidence_text=evidence_text,
    )

    model = getattr(settings, "LLM_RELEVANCE_MODEL", "gpt-4o-mini-2024-07-18")

    # Calculate required output tokens: ~100 tokens per evidence item for score object
    # Plus overhead for JSON structure
    required_output_tokens = len(evidence_to_score) * 120 + 200
    max_output_tokens = max(4000, min(required_output_tokens, 16000))  # Between 4K-16K

    logger.debug(
        f"[LLM SCORER] Scoring {len(evidence_to_score)} items, max_tokens={max_output_tokens}"
    )

    timeout = getattr(settings, "LLM_RELEVANCE_TIMEOUT", 90)
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are an evidence relevance analyst. Return only valid JSON arrays.",
                    },
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.1,  # Low temperature for consistency
                "max_tokens": max_output_tokens,  # Dynamic based on evidence count
                "response_format": {"type": "json_object"},
            },
        )

    if response.status_code != 200:
        logger.error(
            f"[LLM SCORER] OpenAI relevance scoring error: {response.status_code}"
        )
        return []

    response_data = response.json()
    choice = response_data["choices"][0]
    result_text = choice["message"]["content"]

    # Check for truncation (finish_reason="length" means max_tokens was hit)
    finish_reason = choice.get("finish_reason")
    if finish_reason == "length":
        logger.error(
            f"[LLM SCORER] Response truncated (max_tokens={max_output_tokens} insufficient). "
            f"Evidence count: {len(evidence_to_score)}. Response length: {len(result_text)} chars"
        )
        # Try to parse anyway - might have partial valid JSON

    # Log token usage for monitoring
    usage = response_data.get("usage")
    if usage:
        logger.info(
            f"[LLM SCORER] Token usage: input={usage.get('prompt_tokens')}, "
            f"output={usage.get('completion_tokens')}, total={usage.get('total_tokens')}"
        )

    # Parse JSON response - handle both array and object formats
    try:
        result = json.loads(result_text)
        # Handle case where LLM wraps array in an object
        if isinstance(result, dict):
            # Try known wrapper keys first (fast path)
            for key in [
                "scores",
                "evidence_scores",
                "results",
                "items",
                "evidence",
                "data",
            ]:
                if key in result and isinstance(result[key], list):
                    return result[key]

            # Generic fallback: find any value that looks like a scores array
            for key, value in result.items():
                if isinstance(value, list) and len(value) > 0:
                    if isinstance(value[0], dict) and (
                        "score" in value[0] or "evidence_index" in value[0]
                    ):
                        logger.info(
                            f"[LLM SCORER] Found scores under unexpected key: '{key}'"
                        )
                        return value

            # Numeric-key fallback
            if any(k.isdigit() for k in result.keys()):
                scores = []
                for k, v in sorted(
                    result.items(),
                    key=lambda x: int(x[0]) if x[0].isdigit() else 999,
                ):
                    if isinstance(v, dict) and "score" in v:
                        v["evidence_index"] = int(k) if k.isdigit() else len(scores)
                        scores.append(v)
                if scores:
                    return scores

            logger.warning(
                f"[LLM SCORER] OpenAI returned object without recognizable scores array: {list(result.keys())}"
            )
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
    claims: List[str], evidence: Dict[str, List[Dict[str, Any]]], article_context: str
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Score all evidence items for topical relevance and exclude irrelevant ones.

    Evidence scoring 1 (off-topic) is excluded with receipt tracking.
    Evidence scoring >= 2 or unevaluated (None) is kept.

    Args:
        claims: List of claim texts (ordered by position)
        evidence: Dict mapping claim_position -> list of evidence items
        article_context: Article excerpt for context

    Returns:
        Evidence dict with llm_relevance_score annotations.
        Score-1 items moved to evidence["_excluded"] with receipt metadata.
    """
    if not getattr(settings, "ENABLE_LLM_RELEVANCE_SCORER", True):
        logger.info("[LLM SCORER] Disabled via config, passing through unscored")
        return evidence

    if not claims or not evidence:
        return evidence

    # Flatten all evidence items while tracking their original position.
    # Sort claim_pos deterministically: scoring uses positional
    # evidence_index, so insertion-order variance between fresh and
    # cached retrievals would otherwise misalign cached scores to items.
    all_evidence = []
    evidence_positions = []  # Track (claim_position, index_in_claim_list)

    for claim_pos in sorted(evidence.keys(), key=_claim_pos_sort_key):
        if claim_pos.startswith("_"):
            continue
        ev_list = evidence[claim_pos]
        for idx, ev in enumerate(ev_list):
            all_evidence.append(ev)
            evidence_positions.append((claim_pos, idx))

    if not all_evidence:
        return evidence

    logger.info(
        f"[LLM SCORER] Scoring {len(all_evidence)} evidence items for {len(claims)} claims"
    )

    # Fair selection: round-robin across claims instead of sequential truncation
    max_evidence = getattr(settings, "LLM_RELEVANCE_MAX_EVIDENCE", 50)
    selected_evidence, selected_positions, selected_indices = _fair_select_evidence(
        all_evidence, evidence_positions, max_evidence, evidence
    )

    # Check cache first
    evidence_urls = [ev.get("url", "") for ev in selected_evidence]
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
            scores = await _score_with_google(
                claims, selected_evidence, article_context
            )
            if scores:
                logger.info(
                    f"[LLM SCORER] Scored with Google Gemini ({len(scores)} items)"
                )
                await _cache_relevance_scores(cache_key, scores)
        except Exception as e:
            logger.warning(f"[LLM SCORER] Google scoring failed: {e}")

        # Fallback: OpenAI
        if not scores:
            try:
                logger.info("[LLM SCORER] Attempting OpenAI scoring as fallback")
                scores = await _score_with_llm(
                    claims, selected_evidence, article_context
                )
                if scores:
                    logger.info(
                        f"[LLM SCORER] Scored with OpenAI fallback ({len(scores)} items)"
                    )
                    await _cache_relevance_scores(cache_key, scores)
            except Exception as e:
                logger.warning(
                    f"[LLM SCORER] OpenAI scoring failed: {e}, passing through unscored"
                )
                return evidence

    if not scores:
        logger.warning("[LLM SCORER] No scores returned, passing through unscored")
        return evidence

    # Build a mapping from selected_evidence index -> score data
    # LLM returns evidence_index based on the selected_evidence ordering (0..len-1)
    score_lookup = {}
    for score_item in scores:
        idx = score_item.get("evidence_index")
        if idx is not None:
            score_lookup[idx] = score_item

    # Map selected indices back to flat indices for score application
    # selected_evidence[i] corresponds to all_evidence[sorted(selected_indices)[i]]
    selected_flat_indices = sorted(selected_indices)
    selected_to_flat = {
        sel_idx: flat_idx for sel_idx, flat_idx in enumerate(selected_flat_indices)
    }

    # Build flat_idx -> score_data lookup
    flat_score_lookup = {}
    for sel_idx, score_data in score_lookup.items():
        if sel_idx in selected_to_flat:
            flat_score_lookup[selected_to_flat[sel_idx]] = score_data

    # Annotate all items with scores
    for flat_idx, ev in enumerate(all_evidence):
        score_data = flat_score_lookup.get(flat_idx)
        if score_data is not None:
            ev["llm_relevance_score"] = score_data.get("score")
            ev["llm_relevance_rationale"] = score_data.get("rationale", "")
            ev["llm_relevant_claims"] = score_data.get("relevant_claims", [])
        elif flat_idx not in selected_indices:
            ev["llm_relevance_score"] = None
            ev["llm_relevance_rationale"] = "Not evaluated (exceeded MAX_EVIDENCE cap)"
            ev["llm_relevant_claims"] = []
        else:
            ev["llm_relevance_score"] = None
            ev["llm_relevance_rationale"] = "LLM did not return score for this item"
            ev["llm_relevant_claims"] = []

    scored_n = sum(
        1 for ev in all_evidence if ev.get("llm_relevance_score") is not None
    )
    total_n = len(all_evidence)

    # Exclude score-1 items (off-topic) with receipt tracking.
    #
    # NF-07-v2 bypass: items from an adapter that self-declares
    # `emits_structural_metadata=True` skip the score=1 exclusion
    # because their URL identity is the primary-tier signal — the
    # snippet is structured metadata, not content text. Items from
    # search-shape adapters (declaring False, the default) get the
    # scorer's judgement applied normally.
    excluded_total = 0
    bypassed_total = 0
    excluded_items = []
    for claim_pos in list(evidence.keys()):
        if claim_pos.startswith("_"):
            continue
        ev_list = evidence[claim_pos]
        kept = []
        for ev in ev_list:
            score = ev.get("llm_relevance_score")
            url = (ev.get("url") or "")[:120]
            rationale = (ev.get("llm_relevance_rationale") or "")[:120]
            if score == 1:
                provider = ev.get("external_source_provider")
                # F-R1b: a stub snippet (title restated, nothing behind it)
                # is not structural metadata — the bypass does not apply.
                if _adapter_emits_structural_metadata(
                    provider
                ) and not _is_stub_snippet(
                    ev.get("snippet", ev.get("text")), ev.get("title")
                ):
                    ev["relevance_scorer_bypass"] = "api_adapter_canonical_source"
                    bypassed_total += 1
                    kept.append(ev)
                    logger.info(
                        f"[SCORER AUDIT] claim={claim_pos} kept(bypass) score=1 "
                        f"provider={provider} url={url}"
                    )
                else:
                    ev["receipt_status"] = "excluded"
                    ev["exclusion_reason"] = "irrelevant"
                    ev["_claim_position"] = int(claim_pos)
                    excluded_items.append(ev)
                    excluded_total += 1
                    logger.warning(
                        f"[SCORER AUDIT] claim={claim_pos} excluded score=1 "
                        f"url={url} rationale='{rationale}'"
                    )
            else:
                kept.append(ev)
                if score is not None:
                    logger.info(
                        f"[SCORER AUDIT] claim={claim_pos} kept score={score} "
                        f"url={url} rationale='{rationale}'"
                    )
        evidence[claim_pos] = kept
    if excluded_items:
        evidence["_excluded"] = excluded_items

    kept_n = total_n - excluded_total
    logger.info(
        f"[LLM SCORER] Scored {scored_n}/{total_n} items, "
        f"excluded {excluded_total} irrelevant (score=1), "
        f"bypassed {bypassed_total} API-adapter primary (NF-07), "
        f"keeping {kept_n}"
    )
    return evidence
