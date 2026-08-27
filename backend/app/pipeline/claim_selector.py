"""Claim Selector — article-mode claim ranking and selection.

In article mode the extraction stage may produce up to 12 claims.
The selector ranks them by significance and selects the top N for
full Claim Map analysis.

Not wired into the pipeline yet — standalone module for PR-B02.
"""

import json
import logging
from typing import Any, Dict, List, Optional

import httpx

from app.core.config import settings
from app.services.google_ai import call_google_ai

logger = logging.getLogger(__name__)

RANKING_PROMPT = """\
You are a claim significance ranker. Given a list of claims extracted from an \
article and the article context, rank each claim by analytical significance.

Criteria (in order of importance):
1. **Centrality to thesis** — how core is this claim to the article's argument?
2. **Consequence if accepted** — what are the real-world implications?
3. **Epistemic load** — how much does this claim assert that can be tested?

Respond with JSON only:
{
  "ranked_claims": [
    {
      "claim_index": <int, 0-based index from input>,
      "significance_score": <float, 0.0 to 1.0>,
      "significance_rank": <int, 1-based, 1 = most significant>
    }
  ]
}

Rules:
- Include ALL claims from the input. Do not drop any.
- Scores should be meaningfully spread (avoid giving everything 0.5).
- Rank 1 = most significant.
- Every claim must have a unique rank.
"""


class ClaimSelector:
    """Ranks extracted claims by significance and selects top N."""

    def __init__(self):
        self.openai_api_key = settings.OPENAI_API_KEY
        self.google_ai_api_key = getattr(settings, "GOOGLE_AI_API_KEY", "")
        self.max_selected = settings.MAX_SELECTED_CLAIMS
        self.google_model = getattr(
            settings, "GOOGLE_LLM_MODEL", "gemini-3.5-flash-lite"
        )
        self.timeout = 30

    async def rank_claims_by_significance(
        self,
        claims: List[Dict[str, Any]],
        article_context: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Rank claims by significance using LLM.

        Args:
            claims: Extracted claims (up to 12), each with at least a "text" field.
            article_context: Dict with domain, excerpt, classification.

        Returns:
            All claims with significance_score and significance_rank added.
            On failure: claims ordered by position with uniform scores.
        """
        if len(claims) <= 1:
            # Single claim: trivially ranked
            for claim in claims:
                claim["significance_score"] = 1.0
                claim["significance_rank"] = 1
            return claims

        # Build prompt context
        claims_text = "\n".join(
            f"{i}. {c.get('text', c.get('claim_text', ''))}"
            for i, c in enumerate(claims)
        )
        context_text = (
            f"Domain: {article_context.get('domain', 'unknown')}\n"
            f"Classification: {article_context.get('classification', 'unknown')}\n"
            f"Excerpt: {article_context.get('excerpt', '')[:500]}"
        )
        prompt = (
            f"{RANKING_PROMPT}\n\n"
            f"Article context:\n{context_text}\n\n"
            f"Claims:\n{claims_text}"
        )

        parsed = await self._call_llm(prompt)

        if parsed is not None:
            try:
                return self._apply_rankings(claims, parsed)
            except Exception as e:
                logger.warning(f"Ranking parse failed: {e}")

        # Fallback: position order, uniform scores
        return self._fallback_ranking(claims)

    def select_claims(
        self,
        ranked_claims: List[Dict[str, Any]],
        max_selected: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Select top N claims by significance rank.

        Pure function, no LLM. Adds is_selected field to each claim.
        """
        cap = max_selected if max_selected is not None else self.max_selected

        # Sort by rank (ascending = most significant first)
        sorted_claims = sorted(
            ranked_claims,
            key=lambda c: c.get("significance_rank", 999),
        )

        for i, claim in enumerate(sorted_claims):
            claim["is_selected"] = i < cap

        return sorted_claims

    # ── LLM call (Google primary, OpenAI fallback) ──────────────────────

    async def _call_llm(self, prompt: str) -> Optional[Dict[str, Any]]:
        # Try Google first
        if self.google_ai_api_key:
            try:
                result = await self._call_google(prompt)
                if result is not None:
                    logger.info("[CLAIM_SELECTOR] Ranking completed via Google Gemini")
                    return result
            except Exception as e:
                logger.warning(f"[CLAIM_SELECTOR] Google ranking failed: {e}")

        # Fall back to OpenAI
        if self.openai_api_key:
            try:
                result = await self._call_openai(prompt)
                if result is not None:
                    logger.info("[CLAIM_SELECTOR] Ranking completed via OpenAI")
                    return result
            except Exception as e:
                logger.warning(f"[CLAIM_SELECTOR] OpenAI ranking failed: {e}")

        logger.error("[CLAIM_SELECTOR] Both LLM providers failed for ranking")
        return None

    async def _call_google(self, prompt: str) -> Optional[Dict[str, Any]]:
        return await call_google_ai(
            prompt,
            temperature=0.1,
            max_tokens=1500,
            timeout=self.timeout,
            model=self.google_model,
        )

    async def _call_openai(self, prompt: str) -> Optional[Dict[str, Any]]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.openai_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "gpt-4o-mini-2024-07-18",
                    "messages": [{"role": "system", "content": prompt}],
                    "max_tokens": 1500,
                    "temperature": 0.1,
                    "response_format": {"type": "json_object"},
                },
            )
        if response.status_code != 200:
            logger.error(f"OpenAI ranking error: {response.status_code}")
            return None
        result = response.json()
        content = result["choices"][0]["message"]["content"]
        return json.loads(content)

    # ── Helpers ─────────────────────────────────────────────────────────

    def _apply_rankings(
        self,
        claims: List[Dict[str, Any]],
        parsed: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Merge LLM rankings into claims list."""
        ranked = parsed.get("ranked_claims", [])
        if not ranked:
            raise ValueError("No ranked_claims in response")

        # Index by claim_index
        by_index = {r["claim_index"]: r for r in ranked}

        for i, claim in enumerate(claims):
            entry = by_index.get(i)
            if entry:
                claim["significance_score"] = float(
                    entry.get("significance_score", 0.5)
                )
                claim["significance_rank"] = int(entry.get("significance_rank", i + 1))
            else:
                # LLM omitted this claim — assign low score
                claim["significance_score"] = 0.0
                claim["significance_rank"] = len(claims)

        return claims

    def _fallback_ranking(self, claims: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Position-order fallback with uniform scores."""
        logger.warning("[CLAIM_SELECTOR] Using fallback position-order ranking")
        for i, claim in enumerate(claims):
            claim["significance_score"] = round(1.0 - (i / max(len(claims), 1)), 2)
            claim["significance_rank"] = i + 1
        return claims
