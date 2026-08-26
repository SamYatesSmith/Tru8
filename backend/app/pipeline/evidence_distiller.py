"""Evidence Distiller — extract claim-relevant atomic facts from full article text.

Sits between CLASSIFY and MAP. For each evidence item that has full article text,
uses Gemini Flash Lite to extract only the atomic facts relevant to the claim.
The mapper then receives structured facts from across the entire article instead
of one arbitrary snippet window.

Falls back to existing snippets on any failure — no regression risk.

Cost: ~$0.004/claim, ~$0.02/check. Adds ~3-5s latency (parallelisable).
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.services.google_ai import call_google_ai_with_usage

logger = logging.getLogger(__name__)

DISTIL_PROMPT = """\
You are a fact extraction engine. Given a claim and source articles, extract ONLY \
the atomic facts from each article that are relevant to evaluating the claim.

Rules:
- Each fact must be a single, self-contained sentence.
- Include specific figures, dates, names, and quantities wherever present.
- Extract facts from ANYWHERE in the article — beginning, middle, or end.
- Maximum {max_facts} facts per article. Fewer is fine.
- If an article contains NO relevant facts, return an empty list for it.
- Do NOT infer or add information not present in the article text.
- Do NOT include opinions or editorial framing — only factual statements.
- Preserve original attribution (e.g. "according to the ONS").

Claim: {claim}

{articles}

Respond with JSON only:
{{
  "results": [
    {{"index": 0, "facts": ["fact 1", "fact 2"]}},
    ...
  ]
}}

Include one entry per article. If an article has no relevant facts, return \
{{"index": N, "facts": []}}.\
"""

MAX_ARTICLE_CHARS = 8000


class EvidenceDistiller:
    """Extract claim-relevant atomic facts from full article text."""

    # D1 (latency): 15-article batches ran ~15.6s — exactly ON the 15s
    # timeout (silent coin-flip failure, measured 2/17 items distilled) and
    # at 3,986/4,000 output tokens (truncation-close). Latency is ~1s/article
    # (output-generation bound), so small batches fired CONCURRENTLY give the
    # same facts for the same tokens in the time of the slowest small batch.
    BATCH_SIZE = 15  # legacy default; instance uses DISTIL_BATCH_SIZE below

    def __init__(self):
        self.google_ai_api_key = getattr(settings, "GOOGLE_AI_API_KEY", "")
        self.model = getattr(settings, "DISTIL_MODEL", "gemini-2.5-flash-lite")
        self.timeout = getattr(settings, "DISTIL_TIMEOUT", 15)
        self.max_facts = getattr(settings, "DISTIL_MAX_FACTS_PER_ITEM", 8)
        self.min_text_length = getattr(settings, "DISTIL_MIN_TEXT_LENGTH", 500)
        self.batch_size = getattr(settings, "DISTIL_BATCH_SIZE", 5)
        self._token_usage: Dict[str, int] = {"input_tokens": 0, "output_tokens": 0}

    def get_token_usage(self) -> Dict[str, int]:
        """Return accumulated token usage across all LLM calls."""
        return self._token_usage

    async def distil_evidence_for_claim(
        self,
        claim_text: str,
        evidence_items: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Distil full article text into atomic facts for each evidence item.

        Modifies evidence_items in-place. Items with successful distillation get:
        - ``text`` replaced with bullet-point facts
        - ``_distilled`` set to ``True``
        - ``content_basis`` set to ``"distilled"``

        Items without full text or where distillation fails keep their original
        snippet. ``_full_text`` is removed from ALL items after processing.

        Returns the same list (for chaining convenience).
        """
        if not evidence_items or not claim_text:
            self._cleanup_full_text(evidence_items)
            return evidence_items

        # Partition into distillable vs skip
        distillable_indices: List[int] = []
        for i, item in enumerate(evidence_items):
            full_text = item.get("_full_text")
            if full_text and len(full_text) >= self.min_text_length:
                distillable_indices.append(i)

        if not distillable_indices:
            self._cleanup_full_text(evidence_items)
            return evidence_items

        # Process in small CONCURRENT batches (D1). Each article's facts
        # depend only on (claim, article) — no cross-article reasoning — so
        # batch composition doesn't change per-article output; concurrency
        # only changes wall time. A failed batch keeps snippets for ITS
        # items only, exactly as the old sequential loop did.
        batch_size = max(1, self.batch_size)
        batches: List[List[int]] = [
            distillable_indices[s : s + batch_size]
            for s in range(0, len(distillable_indices), batch_size)
        ]

        facts_lists = await asyncio.gather(
            *[
                self._distil_batch(
                    claim_text, [evidence_items[i] for i in batch_indices]
                )
                for batch_indices in batches
            ],
            return_exceptions=True,
        )

        for batch_indices, facts_list in zip(batches, facts_lists):
            if facts_list is None or isinstance(facts_list, BaseException):
                # LLM call failed — keep all snippets in this batch
                continue

            # Apply facts to evidence items
            for offset, idx in enumerate(batch_indices):
                if offset >= len(facts_list):
                    continue
                facts = facts_list[offset]
                if facts is None or not facts:
                    # Empty or missing facts — keep original snippet
                    continue

                # Cap facts
                capped = facts[: self.max_facts]
                # Filter non-string items
                capped = [f for f in capped if isinstance(f, str) and f.strip()]
                if not capped:
                    continue

                evidence_items[idx]["text"] = "- " + "\n- ".join(capped)
                evidence_items[idx]["_distilled"] = True
                evidence_items[idx]["content_basis"] = "distilled"

        self._cleanup_full_text(evidence_items)
        return evidence_items

    async def _distil_batch(
        self,
        claim_text: str,
        batch_items: List[Dict[str, Any]],
    ) -> Optional[List[Optional[List[str]]]]:
        """Call LLM to distil a batch of articles. Returns list of fact lists or None on failure."""
        # Build articles section
        article_parts = []
        for i, item in enumerate(batch_items):
            full_text = (item.get("_full_text") or "")[:MAX_ARTICLE_CHARS]
            title = item.get("title", "Untitled")[:200]
            source = item.get("source", item.get("domain", "Unknown"))[:100]
            article_parts.append(
                f"[Article {i}] Title: {title}\nSource: {source}\n\n{full_text}"
            )

        articles_text = "\n\n---\n\n".join(article_parts)
        prompt = DISTIL_PROMPT.format(
            max_facts=self.max_facts,
            claim=claim_text,
            articles=articles_text,
        )

        try:
            parsed, usage = await call_google_ai_with_usage(
                prompt,
                temperature=0.0,
                max_tokens=4000,
                timeout=self.timeout,
                model=self.model,
            )
            self._accumulate(usage)
        except Exception as e:
            logger.warning(f"[DISTIL] LLM call failed: {e}")
            return None

        if parsed is None:
            return None

        return self._parse_response(parsed, len(batch_items))

    def _parse_response(
        self,
        raw: Any,
        expected_count: int,
    ) -> Optional[List[Optional[List[str]]]]:
        """Parse LLM response into list of fact lists."""
        results: List[Optional[List[str]]] = [None] * expected_count

        if not isinstance(raw, dict):
            logger.warning("[DISTIL] LLM response is not a dict")
            return None

        entries = raw.get("results", [])
        if not entries:
            # Try to find any list value
            for key, value in raw.items():
                if isinstance(value, list) and len(value) > 0:
                    if isinstance(value[0], dict) and "facts" in value[0]:
                        entries = value
                        break

        if not entries:
            logger.warning("[DISTIL] No results found in LLM response")
            return None

        for entry in entries:
            if not isinstance(entry, dict):
                continue
            index = entry.get("index")
            if index is None or not isinstance(index, int):
                continue
            if index < 0 or index >= expected_count:
                continue
            facts = entry.get("facts", [])
            if isinstance(facts, list):
                # Filter non-string items
                results[index] = [f for f in facts if isinstance(f, str)]

        return results

    def _accumulate(self, usage: Optional[Dict[str, int]]) -> None:
        """Add usage to running total."""
        if usage:
            self._token_usage["input_tokens"] += usage.get("input_tokens", 0)
            self._token_usage["output_tokens"] += usage.get("output_tokens", 0)
            # Same guarded pattern as ClaimMapAnalyzer._accumulate: present only
            # when a thinking model ran, so the dict shape is otherwise unchanged.
            if usage.get("thinking_tokens"):
                self._token_usage["thinking_tokens"] = self._token_usage.get(
                    "thinking_tokens", 0
                ) + usage.get("thinking_tokens", 0)

    @staticmethod
    def _cleanup_full_text(items: List[Dict[str, Any]]) -> None:
        """Remove _full_text from all items to free memory."""
        for item in items:
            item.pop("_full_text", None)
