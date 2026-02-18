"""Evidence Classifier — batched LLM classification of evidence tier and type.

Assigns Tier (proximity to original information) and Type (nature of content)
to each evidence item. Uses a single batched LLM call per batch of up to 30 items,
with a heuristic fallback for failures.

Philosophy (locked 2026-02-16):
  Classify, don't score. Tier + Type, not credibility numbers.
  A Tier 1 government dataset from a questionable government is still "primary".
  A BBC opinion column is still "commentary". The tier describes proximity, not quality.

Canonical doc: audit/pipeline-issues/fireside_discussion.md
"""

import json
import logging
import re
from collections import Counter
from typing import Any, Dict, List, Optional, Tuple

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

# ── Valid classification values ────────────────────────────────────────────

VALID_TIERS = {"primary", "reporting", "commentary"}
VALID_TYPES = {
    "data",
    "official_statement",
    "news_reporting",
    "analysis",
    "opinion",
    "academic",
}

DEFAULT_TIER = "commentary"
DEFAULT_TYPE = "news_reporting"

BATCH_SIZE = 30

# ── Classification prompt ──────────────────────────────────────────────────

CLASSIFICATION_SYSTEM_PROMPT = """\
You are an evidence classification engine. You assign two labels to each evidence item:

**Tier** — proximity to the original information:
- primary: The thing itself. Government data, official statements, court filings, \
original research, raw statistics, primary documents, datasets.
- reporting: Someone investigated, interviewed, verified. News organisations, \
investigative outlets, specialist correspondents, field reporting.
- commentary: Interpretation of primary sources or reporting. Op-eds, analysis, \
editorials, blog posts, think-tank output.

Tier describes proximity, NOT quality. A government dataset from a questionable \
government is still "primary". A BBC opinion column is still "commentary".

**Type** — nature of the content:
- data: Numbers, datasets, measurements
- official_statement: Press releases, government communications
- news_reporting: Event coverage, investigation
- analysis: In-depth contextual pieces, explainers
- opinion: Stated perspective, editorials
- academic: Peer-reviewed, studies

Rules:
- Every item MUST get exactly one tier and one type.
- Use the evidence title, source/domain, URL, and snippet to determine classification.
- If uncertain, prefer the more conservative label (closer to primary, closer to data).
"""

CLASSIFICATION_USER_PROMPT = """\
Classify each evidence item below by tier and type.

{evidence_text}

Respond with JSON only:
{{
  "classifications": [
    {{"index": 0, "tier": "<primary|reporting|commentary>", "type": "<data|official_statement|news_reporting|analysis|opinion|academic>"}},
    ...
  ]
}}

Include one entry per evidence item. The index must match the item number above."""


# ── Heuristic patterns ────────────────────────────────────────────────────

_GOV_PATTERNS = re.compile(
    r"\.(gov|gov\.uk|parliament\.uk|congress\.gov|europa\.eu|govt\.nz|gc\.ca)"
    r"|whitehouse\.gov|govinfo\.gov",
    re.IGNORECASE,
)

_ACADEMIC_PATTERNS = re.compile(
    r"\.(edu|ac\.uk|ac\.jp)"
    r"|pubmed\.ncbi|arxiv\.org|nature\.com|sciencedirect\.com"
    r"|springer\.com|wiley\.com|jstor\.org|ncbi\.nlm\.nih\.gov"
    r"|scholar\.google",
    re.IGNORECASE,
)

_WIRE_SERVICES = re.compile(
    r"reuters\.com|apnews\.com|ap\.org|bbc\.co\.uk|bbc\.com"
    r"|theguardian\.com|nytimes\.com|washingtonpost\.com"
    r"|ft\.com|economist\.com|bloomberg\.com|cnbc\.com",
    re.IGNORECASE,
)

_DATA_PORTALS = re.compile(
    r"ons\.gov\.uk|bls\.gov|worldbank\.org|data\.who\.int"
    r"|fred\.stlouisfed\.org|data\.gov|eurostat\.ec"
    r"|stats\.oecd\.org|imf\.org/en/Data",
    re.IGNORECASE,
)


def _classify_heuristic(evidence: Dict[str, Any]) -> Tuple[str, str]:
    """Classify a single evidence item using URL/source pattern matching.

    Returns (tier, evidence_type) tuple.
    """
    url = evidence.get("url", "")
    source = evidence.get("source", evidence.get("domain", ""))
    title = evidence.get("title", "")
    combined = f"{url} {source} {title}".lower()

    # API adapter results (government/data APIs) → primary/data
    if evidence.get("external_source_provider"):
        return ("primary", "data")

    # Fact-check articles → reporting/news_reporting
    if evidence.get("is_factcheck"):
        return ("reporting", "news_reporting")

    # Data portals → primary/data
    if _DATA_PORTALS.search(url) or _DATA_PORTALS.search(source):
        return ("primary", "data")

    # Government sources → primary/official_statement
    if _GOV_PATTERNS.search(url) or _GOV_PATTERNS.search(source):
        return ("primary", "official_statement")

    # Academic sources → primary/academic
    if _ACADEMIC_PATTERNS.search(url) or _ACADEMIC_PATTERNS.search(source):
        return ("primary", "academic")

    # Major news organisations → reporting/news_reporting
    if _WIRE_SERVICES.search(url) or _WIRE_SERVICES.search(source):
        # Check if it's an opinion/editorial piece
        opinion_markers = [
            "opinion",
            "editorial",
            "op-ed",
            "comment",
            "analysis",
            "column",
        ]
        if any(marker in combined for marker in opinion_markers):
            return ("commentary", "opinion")
        return ("reporting", "news_reporting")

    # Default → commentary/news_reporting
    return (DEFAULT_TIER, DEFAULT_TYPE)


# ── Evidence Classifier ───────────────────────────────────────────────────


class EvidenceClassifier:
    """Batched LLM classifier for evidence tier and type."""

    def __init__(self):
        self.openai_api_key = settings.OPENAI_API_KEY
        self.google_ai_api_key = getattr(settings, "GOOGLE_AI_API_KEY", "")
        self.model = getattr(settings, "LLM_MODEL_NAME", "gpt-4o-mini")
        self.google_model = getattr(
            settings, "GOOGLE_LLM_MODEL", "gemini-2.5-flash-lite"
        )
        self.timeout = 45
        self.snippet_length = 300

    async def classify_batch(
        self, evidence_items: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Classify evidence items with tier and evidence_type.

        Returns the same list with 'tier' and 'evidence_type' fields added
        to each item. Items that already have both fields set are skipped.
        Never raises — always returns with at least heuristic classifications.

        Args:
            evidence_items: List of evidence dicts, each with at least
                title, url/source, and snippet/text fields.

        Returns:
            The same list with 'tier' and 'evidence_type' added to each item.
        """
        if not evidence_items:
            return evidence_items

        # Partition: items needing classification vs already classified
        needs_classification: List[int] = []
        for i, item in enumerate(evidence_items):
            if item.get("tier") and item.get("evidence_type"):
                # Already classified — skip
                continue
            needs_classification.append(i)

        if not needs_classification:
            logger.info(
                "[EVIDENCE_CLASSIFIER] All %d items already classified, skipping",
                len(evidence_items),
            )
            return evidence_items

        logger.info(
            "[EVIDENCE_CLASSIFIER] Classifying %d of %d evidence items",
            len(needs_classification),
            len(evidence_items),
        )

        # Process in batches of BATCH_SIZE
        items_to_classify = [evidence_items[i] for i in needs_classification]
        classified_results: List[Optional[Tuple[str, str]]] = [None] * len(
            items_to_classify
        )

        for batch_start in range(0, len(items_to_classify), BATCH_SIZE):
            batch_end = min(batch_start + BATCH_SIZE, len(items_to_classify))
            batch = items_to_classify[batch_start:batch_end]

            llm_results = await self._classify_batch_llm(batch)

            if llm_results:
                for offset, result in enumerate(llm_results):
                    if result is not None:
                        classified_results[batch_start + offset] = result

        # Apply results: LLM where available, heuristic fallback otherwise
        llm_count = 0
        heuristic_count = 0

        for list_offset, original_index in enumerate(needs_classification):
            item = evidence_items[original_index]
            result = classified_results[list_offset]

            if result is not None:
                tier, evidence_type = result
                item["tier"] = tier
                item["evidence_type"] = evidence_type
                item["classification_method"] = "llm"
                llm_count += 1
            else:
                tier, evidence_type = _classify_heuristic(item)
                item["tier"] = tier
                item["evidence_type"] = evidence_type
                item["classification_method"] = "heuristic"
                heuristic_count += 1

        # Log summary
        tier_counts = Counter(item.get("tier", "unknown") for item in evidence_items)
        type_counts = Counter(
            item.get("evidence_type", "unknown") for item in evidence_items
        )

        logger.info(
            "[EVIDENCE_CLASSIFIER] Classification complete: "
            "%d LLM, %d heuristic. "
            "Tiers: %s. Types: %s",
            llm_count,
            heuristic_count,
            dict(tier_counts),
            dict(type_counts),
        )

        return evidence_items

    # ── LLM batch classification ──────────────────────────────────────────

    async def _classify_batch_llm(
        self, batch: List[Dict[str, Any]]
    ) -> List[Optional[Tuple[str, str]]]:
        """Classify a batch of evidence items via LLM.

        Returns a list of (tier, type) tuples, one per item. Items that
        could not be classified are None.
        """
        # Build evidence text for prompt
        evidence_parts = []
        for i, item in enumerate(batch):
            title = item.get("title", "Untitled")[:200]
            source = item.get("source", item.get("domain", "Unknown"))[:100]
            url = item.get("url", "")[:200]
            snippet = (item.get("snippet", item.get("text", item.get("content", ""))))[
                : self.snippet_length
            ]

            evidence_parts.append(
                f"[{i}] Title: {title}\n"
                f"    Source: {source}\n"
                f"    URL: {url}\n"
                f"    Snippet: {snippet}"
            )

        evidence_text = "\n\n".join(evidence_parts)
        user_prompt = CLASSIFICATION_USER_PROMPT.format(evidence_text=evidence_text)

        parsed = await self._call_llm(user_prompt)

        if parsed is None:
            return [None] * len(batch)

        return self._parse_classification_response(parsed, len(batch))

    def _parse_classification_response(
        self,
        raw: Dict[str, Any],
        expected_count: int,
    ) -> List[Optional[Tuple[str, str]]]:
        """Parse LLM classification response into validated (tier, type) tuples."""
        results: List[Optional[Tuple[str, str]]] = [None] * expected_count

        if isinstance(raw, list):
            classifications = raw
        else:
            classifications = raw.get("classifications", [])

        if not classifications:
            # Search for any list value that looks like classifications
            for key, value in raw.items():
                if isinstance(value, list) and len(value) > 0:
                    if isinstance(value[0], dict) and (
                        "tier" in value[0] or "type" in value[0]
                    ):
                        classifications = value
                        break

        if not classifications:
            logger.warning(
                "[EVIDENCE_CLASSIFIER] No classifications found in LLM response"
            )
            return results

        for entry in classifications:
            if not isinstance(entry, dict):
                continue

            index = entry.get("index")
            if index is None or not isinstance(index, int):
                continue
            if index < 0 or index >= expected_count:
                continue

            tier = entry.get("tier", "").lower().strip()
            evidence_type = entry.get("type", "").lower().strip()

            # Validate tier
            if tier not in VALID_TIERS:
                logger.debug(
                    "[EVIDENCE_CLASSIFIER] Invalid tier '%s' at index %d, "
                    "defaulting to '%s'",
                    tier,
                    index,
                    DEFAULT_TIER,
                )
                tier = DEFAULT_TIER

            # Validate type
            if evidence_type not in VALID_TYPES:
                logger.debug(
                    "[EVIDENCE_CLASSIFIER] Invalid type '%s' at index %d, "
                    "defaulting to '%s'",
                    evidence_type,
                    index,
                    DEFAULT_TYPE,
                )
                evidence_type = DEFAULT_TYPE

            results[index] = (tier, evidence_type)

        classified_count = sum(1 for r in results if r is not None)
        logger.debug(
            "[EVIDENCE_CLASSIFIER] Parsed %d/%d classifications from LLM",
            classified_count,
            expected_count,
        )

        return results

    # ── LLM call (Google primary, OpenAI fallback) ────────────────────────

    async def _call_llm(self, user_prompt: str) -> Optional[Dict[str, Any]]:
        """Call LLM with Google primary, OpenAI fallback. Returns parsed JSON or None."""
        # Try Google first
        if self.google_ai_api_key:
            try:
                result = await self._call_google(user_prompt)
                if result is not None:
                    logger.info(
                        "[EVIDENCE_CLASSIFIER] Classification completed via Google Gemini"
                    )
                    return result
            except Exception as e:
                logger.warning(
                    "[EVIDENCE_CLASSIFIER] Google classification failed: %s", e
                )

        # Fall back to OpenAI
        if self.openai_api_key:
            try:
                result = await self._call_openai(user_prompt)
                if result is not None:
                    logger.info(
                        "[EVIDENCE_CLASSIFIER] Classification completed via OpenAI"
                    )
                    return result
            except Exception as e:
                logger.warning(
                    "[EVIDENCE_CLASSIFIER] OpenAI classification failed: %s", e
                )

        logger.error(
            "[EVIDENCE_CLASSIFIER] Both LLM providers failed for classification"
        )
        return None

    async def _call_google(self, user_prompt: str) -> Optional[Dict[str, Any]]:
        """Classify via Google Gemini API."""
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.google_model}:generateContent?key={self.google_ai_api_key}"
        )
        full_prompt = f"{CLASSIFICATION_SYSTEM_PROMPT}\n\n{user_prompt}"

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                url,
                headers={"Content-Type": "application/json"},
                json={
                    "contents": [{"parts": [{"text": full_prompt}]}],
                    "generationConfig": {
                        "temperature": 0.1,
                        "maxOutputTokens": 4000,
                        "responseMimeType": "application/json",
                    },
                },
            )

        if response.status_code != 200:
            logger.error(
                "[EVIDENCE_CLASSIFIER] Google AI error: %d", response.status_code
            )
            return None

        result = response.json()
        content_text = result["candidates"][0]["content"]["parts"][0]["text"]
        return json.loads(content_text)

    async def _call_openai(self, user_prompt: str) -> Optional[Dict[str, Any]]:
        """Classify via OpenAI API."""
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
                        {
                            "role": "system",
                            "content": CLASSIFICATION_SYSTEM_PROMPT,
                        },
                        {
                            "role": "user",
                            "content": user_prompt,
                        },
                    ],
                    "max_tokens": 4000,
                    "temperature": 0.1,
                    "response_format": {"type": "json_object"},
                },
            )

        if response.status_code != 200:
            logger.error(
                "[EVIDENCE_CLASSIFIER] OpenAI API error: %d", response.status_code
            )
            return None

        result = response.json()
        content = result["choices"][0]["message"]["content"]
        return json.loads(content)
