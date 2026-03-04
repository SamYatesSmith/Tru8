"""Claim Map Analyzer — decompose claims into elements and map evidence.

Two LLM stages:
  1. Decomposition: claim text → normalised_claim + claim_type + 1-5 elements
  2. Evidence mapping: elements + evidence → evidence_refs + states + uncertainty

Supports both per-claim and batch modes:
  - Per-claim: decompose_claim() / map_evidence_to_elements() — 1 LLM call each
  - Batch: decompose_claims_batch() / map_evidence_batch() — 1 LLM call per stage
    with automatic fallback to per-claim on parse failure

Orientation line is derived mechanically (no LLM).

Canonical contract: audit/track-b/2026-02-12_claim-map-contract.md
"""

import json
import logging
from collections import Counter
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx

from app.core.config import settings
from app.services.google_ai import call_google_ai, call_google_ai_with_usage
from app.models.claim_map import (
    ClaimElement,
    ClaimMap,
    ClaimMapMetadata,
    ClaimType,
    ElementState,
    EvidenceRef,
    EvidenceRelationship,
)

logger = logging.getLogger(__name__)

# ── Valid enum values for validation ────────────────────────────────────────

_VALID_CLAIM_TYPES = {e.value for e in ClaimType}
_VALID_STATES = {e.value for e in ElementState}
_VALID_RELATIONSHIPS = {e.value for e in EvidenceRelationship}


# ── Prompts ─────────────────────────────────────────────────────────────────

DECOMPOSITION_PROMPT = """\
You are an analytical decomposition engine. Given a claim, you must:

1. **Normalise** the claim into a clear, standalone assertion.
2. **Classify** the claim type from exactly one of: empirical, definitional, \
causal_interpretive, predictive, normative_flagged.
3. **Decompose** the claim into 1-5 required elements — the things that must \
hold for the claim to stand. Each element should be a distinct, testable \
sub-assertion. Atomic claims may have just 1 element.

Respond with JSON only:
{
  "normalised_claim": "<string>",
  "claim_type": "<ClaimType>",
  "elements": [
    {"description": "<what must hold>"},
    ...
  ]
}

Rules:
- Minimum 1 element, maximum 5.
- Each element description must be a single clear sentence.
- claim_type must be exactly one of the five listed values.
- Do NOT include evidence_refs, state, or uncertainty — those come later.
"""

MAPPING_PROMPT = """\
You are an evidence mapping engine. You are given:
1. A list of elements (sub-assertions) of a claim.
2. A list of evidence items, each with an evidence_id, title, and snippet.

For each element, map relevant evidence and assign a state. EVERY evidence_ref \
MUST include all three fields: evidence_id, relationship, reasoning.

Respond with JSON only:
{
  "elements": [
    {
      "element_id": "<e1..e5>",
      "evidence_refs": [
        {"evidence_id": "ev-abc", "relationship": "supports", "reasoning": "Reports GDP rose 0.1% in Q3, confirming growth occurred"},
        {"evidence_id": "ev-def", "relationship": "challenges", "reasoning": "States growth was 0.1%, contradicting the claimed 0.6%"}
      ],
      "state": "supported|disputed|unresolved",
      "uncertainty": "<one sentence or null>"
    }
  ]
}

Rules:
- Only use evidence_ids from the provided list. Do NOT invent IDs.
- relationship must be exactly one of: supports, challenges, context.
- reasoning is REQUIRED on every evidence_ref. One sentence: what the evidence \
says and why the relationship applies. Cite specific figures, dates, or entities.
- state must be exactly one of: supported, disputed, unresolved.
- "supported" = predominantly supportive evidence, no significant challenges.
- "disputed" = both supporting and challenging evidence present.
- "unresolved" = no meaningful supporting or challenging evidence.
- uncertainty is optional (null if not applicable), max one sentence.
- Every element_id from the input must appear in the output.
- SCOPE CHECK: Before assigning "supports", verify that the evidence's geographic \
and temporal scope matches the element's scope. Evidence about one country does NOT \
support a claim about "worldwide" or "global" figures. Evidence from one time period \
does NOT support a claim about a different time period.
- STATE RULE: An element can only be "supported" if at least one evidence_ref has \
relationship = "supports". If all refs are "context", the state MUST be "unresolved".
- CROSS-ELEMENT: A single evidence item may be relevant to multiple elements. For each \
evidence item, consider ALL elements it could inform, not just the most obvious one.
- PRECISION: When comparing numbers, treat round figures (e.g. "sixty percent") as \
approximate. A source saying "59%" does not challenge a claim of "approximately 60%". \
But a source saying "25%" DOES challenge a claim of "18%".
"""

BATCH_DECOMPOSITION_PROMPT = """\
You are an analytical decomposition engine. Given multiple claims, for EACH claim:

1. Normalise the claim into a clear, standalone assertion.
2. Classify the claim type from exactly one of: empirical, definitional, \
causal_interpretive, predictive, normative_flagged.
3. Decompose the claim into 1-5 required elements — the things that must \
hold for the claim to stand. Each element should be a distinct, testable \
sub-assertion. Atomic claims may have just 1 element.

Respond with JSON only:
{
  "claims": [
    {
      "claim_index": 0,
      "normalised_claim": "<string>",
      "claim_type": "<ClaimType>",
      "elements": [{"description": "<what must hold>"}, ...]
    }
  ]
}

Rules:
- One entry per claim_index. Do NOT skip any claims.
- Minimum 1 element, maximum 5 per claim.
- Each element description must be a single clear sentence.
- claim_type must be exactly one of the five listed values.
- Do NOT include evidence_refs, state, or uncertainty — those come later.
"""

BATCH_MAPPING_PROMPT = """\
You are an evidence mapping engine. You are given multiple claims, each with:
1. A list of elements (sub-assertions).
2. A list of evidence items with evidence_id, title, and snippet.

For each claim, map relevant evidence to its elements and assign states. \
EVERY evidence_ref MUST include all three fields: evidence_id, relationship, reasoning.

Respond with JSON only:
{
  "claims": [
    {
      "claim_index": 0,
      "elements": [
        {
          "element_id": "<e1..e5>",
          "evidence_refs": [
            {"evidence_id": "ev-abc", "relationship": "supports", "reasoning": "Reports GDP rose 0.1% in Q3, confirming growth occurred"},
            {"evidence_id": "ev-def", "relationship": "challenges", "reasoning": "States growth was 0.1%, contradicting the claimed 0.6%"}
          ],
          "state": "supported|disputed|unresolved",
          "uncertainty": "<one sentence or null>"
        }
      ]
    }
  ]
}

Rules:
- One entry per claim_index. Do NOT skip any claims.
- Only use evidence_ids from the provided evidence for THAT claim. Do NOT mix across claims.
- relationship must be exactly one of: supports, challenges, context.
- reasoning is REQUIRED on every evidence_ref. One sentence: what the evidence \
says and why the relationship applies. Cite specific figures, dates, or entities.
- state must be exactly one of: supported, disputed, unresolved.
- "supported" = predominantly supportive evidence, no significant challenges.
- "disputed" = both supporting and challenging evidence present.
- "unresolved" = no meaningful supporting or challenging evidence.
- uncertainty is optional (null if not applicable), max one sentence.
- Every element_id from the input must appear in the output for that claim.
- SCOPE CHECK: Before assigning "supports", verify that the evidence's geographic \
and temporal scope matches the element's scope. Evidence about one country does NOT \
support a claim about "worldwide" or "global" figures. Evidence from one time period \
does NOT support a claim about a different time period.
- STATE RULE: An element can only be "supported" if at least one evidence_ref has \
relationship = "supports". If all refs are "context", the state MUST be "unresolved".
- CROSS-ELEMENT: A single evidence item may be relevant to multiple elements. For each \
evidence item, consider ALL elements it could inform, not just the most obvious one.
- PRECISION: When comparing numbers, treat round figures (e.g. "sixty percent") as \
approximate. A source saying "59%" does not challenge a claim of "approximately 60%". \
But a source saying "25%" DOES challenge a claim of "18%".
"""


# ── Orientation line derivation (pure function, no LLM) ────────────────────


def derive_orientation(elements: List[ClaimElement]) -> str:
    """Derive orientation line mechanically from element states.

    Contract Section 5: deterministic, no LLM, fully derivable from states.
    """
    total = len(elements)
    if total == 0:
        return "No elements to assess."

    state_values = [
        e["state"].value if hasattr(e["state"], "value") else e["state"]
        for e in elements
        if e.get("state")
    ]
    if not state_values:
        return "No element states have been assigned."

    counts = Counter(state_values)

    # Single element
    if total == 1:
        state = state_values[0]
        return f"The single required element is evidentially {state}."

    # Unanimous
    if len(counts) == 1:
        state = state_values[0]
        return f"All {total} required elements are evidentially {state}."

    # Find majority (strictly more than any other single state)
    most_common = counts.most_common()
    top_count = most_common[0][1]
    # Check if there's a tie for the top
    tied = [s for s, c in most_common if c == top_count]

    if len(tied) == 1:
        # Majority exists
        majority_state = tied[0]
        majority_count = top_count
        remainder_parts = []
        for state, count in most_common[1:]:
            remainder_parts.append(f"{count} {'is' if count == 1 else 'are'} {state}")
        remainder = " and ".join(remainder_parts)
        return (
            f"{majority_count} of {total} required elements are evidentially "
            f"{majority_state}; {remainder}."
        )

    # No majority (tied or all different)
    parts = [f"{count} {state}" for state, count in most_common]
    joined = ", ".join(parts)
    return f"Evidence is mixed across {total} required elements: {joined}."


# ── ClaimMapAnalyzer ────────────────────────────────────────────────────────


class ClaimMapAnalyzer:
    """Decomposes claims into elements and maps evidence to them."""

    def __init__(self):
        self.openai_api_key = settings.OPENAI_API_KEY
        self.google_ai_api_key = getattr(settings, "GOOGLE_AI_API_KEY", "")
        self.decomposition_model = settings.DECOMPOSITION_MODEL
        self.decomposition_temperature = settings.DECOMPOSITION_TEMPERATURE
        self.analyzer_model = settings.ANALYZER_MODEL
        self.analyzer_temperature = settings.ANALYZER_TEMPERATURE
        self.analyzer_max_tokens = settings.ANALYZER_MAX_TOKENS
        self.max_elements = settings.MAX_ELEMENTS_PER_CLAIM
        self.snippet_length = settings.EVIDENCE_SNIPPET_LENGTH
        self.google_model = getattr(
            settings, "GOOGLE_LLM_MODEL", "gemini-2.5-flash-lite"
        )
        self.mapping_google_model = getattr(
            settings, "MAPPING_GOOGLE_MODEL", self.google_model
        )
        self.timeout = 30
        self._token_usage = {"input_tokens": 0, "output_tokens": 0}

    def get_token_usage(self) -> Dict[str, int]:
        """Return accumulated token usage across all LLM calls."""
        return self._token_usage

    # ── Public: Phase 1 — Decomposition ─────────────────────────────────

    async def decompose_claim(self, claim_text: str, claim_id: str) -> ClaimMap:
        """Decompose a claim into elements and classify its type.

        Returns a partial ClaimMap (evidence_refs empty, states null, no orientation).
        On parse failure: single-element fallback with raw claim text, type=empirical.
        """
        prompt = f"{DECOMPOSITION_PROMPT}\n\nClaim: {claim_text}"
        parsed = await self._call_llm(
            prompt=prompt,
            temperature=self.decomposition_temperature,
            max_tokens=2000,
            label="decomposition",
        )

        if parsed is not None:
            try:
                return self._parse_decomposition_response(parsed, claim_id)
            except Exception as e:
                logger.warning(f"Decomposition parse failed for claim {claim_id}: {e}")

        # Fallback: single element with raw claim text
        logger.warning(f"Using fallback decomposition for claim {claim_id}")
        return self._fallback_decomposition(claim_text, claim_id)

    # ── Public: Phase 2 — Evidence Mapping ──────────────────────────────

    async def map_evidence_to_elements(
        self, claim_map: ClaimMap, evidence_list: List[Dict[str, Any]]
    ) -> ClaimMap:
        """Map evidence to elements, assign states and uncertainty.

        Completes the ClaimMap: fills evidence_refs, state, uncertainty,
        orientation, and mapping metadata.
        """
        if not evidence_list:
            # No evidence: mark all elements as unresolved
            for elem in claim_map["elements"]:
                elem["evidence_refs"] = []
                elem["state"] = ElementState.unresolved
                elem["uncertainty"] = "No evidence was retrieved for this element."
            claim_map["orientation"] = derive_orientation(claim_map["elements"])
            claim_map["metadata"]["mapping_model"] = "none"
            claim_map["metadata"]["element_count"] = len(claim_map["elements"])
            claim_map["metadata"]["completed_at"] = datetime.now(
                timezone.utc
            ).isoformat()
            return claim_map

        # Build context for LLM
        elements_desc = "\n".join(
            f"- {e['element_id']}: {e['description']}" for e in claim_map["elements"]
        )
        evidence_desc = "\n".join(
            f"- {ev.get('evidence_id', 'unknown')}: "
            f"[{ev.get('title', 'Untitled')}] "
            f"[Tier: {ev.get('tier') or 'unclassified'}] "
            f"[Type: {ev.get('evidence_type') or 'unclassified'}] "
            f"{(ev.get('snippet') or ev.get('text') or '')[:self.snippet_length]}"
            for ev in evidence_list
        )

        prompt = (
            f"{MAPPING_PROMPT}\n\n"
            f"Claim: {claim_map['normalised_claim']}\n\n"
            f"Elements:\n{elements_desc}\n\n"
            f"Evidence:\n{evidence_desc}"
        )

        parsed = await self._call_llm(
            prompt=prompt,
            temperature=self.analyzer_temperature,
            max_tokens=self.analyzer_max_tokens,
            label="mapping",
        )

        if parsed is not None:
            try:
                self._parse_mapping_response(parsed, claim_map, evidence_list)
                # Retry once if reasoning is null (output budget issue)
                if self._has_null_reasoning(claim_map):
                    logger.warning(
                        f"[CLAIM_MAP] Null reasoning detected for "
                        f"{claim_map['claim_id']}, retrying"
                    )
                    retry_parsed = await self._call_llm(
                        prompt=prompt,
                        temperature=self.analyzer_temperature,
                        max_tokens=self.analyzer_max_tokens,
                        label="mapping",
                    )
                    if retry_parsed is not None:
                        try:
                            self._parse_mapping_response(
                                retry_parsed, claim_map, evidence_list
                            )
                        except Exception:
                            pass  # Keep original result if retry also fails
            except Exception as e:
                logger.warning(
                    f"Mapping parse failed for claim {claim_map['claim_id']}: {e}"
                )
                self._fallback_mapping(claim_map)
        else:
            self._fallback_mapping(claim_map)

        # Derive orientation mechanically
        claim_map["orientation"] = derive_orientation(claim_map["elements"])

        # Set mapping metadata
        model_used = "fallback" if parsed is None else self._last_model_used
        claim_map["metadata"]["mapping_model"] = model_used
        claim_map["metadata"]["element_count"] = len(claim_map["elements"])
        claim_map["metadata"]["completed_at"] = datetime.now(timezone.utc).isoformat()

        return claim_map

    # ── Public: Batch Decomposition ─────────────────────────────────

    async def decompose_claims_batch(
        self, claims: List[Dict[str, str]]
    ) -> Dict[str, ClaimMap]:
        """Decompose multiple claims in a single LLM call.

        Parameters:
            claims: list of {"text": str, "claim_id": str}

        Returns:
            Dict mapping claim_id to ClaimMap.

        Falls back to per-claim calls on batch parse failure.
        """
        if len(claims) == 1:
            cm = await self.decompose_claim(claims[0]["text"], claims[0]["claim_id"])
            return {claims[0]["claim_id"]: cm}

        # Build numbered claim list
        claim_lines = "\n".join(f"[{i}] {c['text']}" for i, c in enumerate(claims))
        prompt = f"{BATCH_DECOMPOSITION_PROMPT}\n\nClaims:\n{claim_lines}"

        parsed = await self._call_llm(
            prompt=prompt,
            temperature=self.decomposition_temperature,
            max_tokens=2500,
            label="batch_decomposition",
        )

        results: Dict[str, ClaimMap] = {}
        failed_claims: List[Dict[str, str]] = []

        if parsed is not None and isinstance(parsed.get("claims"), list):
            # Index batch response by claim_index
            batch_by_idx = {
                item.get("claim_index"): item
                for item in parsed["claims"]
                if isinstance(item, dict) and item.get("claim_index") is not None
            }

            for i, c in enumerate(claims):
                item = batch_by_idx.get(i)
                if item is not None:
                    try:
                        results[c["claim_id"]] = self._parse_decomposition_response(
                            item, c["claim_id"]
                        )
                        continue
                    except Exception as e:
                        logger.warning(
                            f"Batch decomposition parse failed for claim {c['claim_id']}: {e}"
                        )
                failed_claims.append(c)
        else:
            logger.warning(
                "[CLAIM_MAP] Batch decomposition returned invalid shape, "
                "falling back to per-claim calls"
            )
            failed_claims = list(claims)

        # Retry failed claims individually
        if failed_claims:
            logger.info(
                f"[CLAIM_MAP] Retrying {len(failed_claims)} claims via per-claim decomposition"
            )
            import asyncio

            async def _retry_one(c: Dict[str, str]) -> None:
                results[c["claim_id"]] = await self.decompose_claim(
                    c["text"], c["claim_id"]
                )

            await asyncio.gather(*[_retry_one(c) for c in failed_claims])

        return results

    # ── Public: Batch Evidence Mapping ────────────────────────────────

    async def map_evidence_batch(self, claim_data: List[Dict[str, Any]]) -> None:
        """Map evidence to elements for multiple claims in a single LLM call.

        Parameters:
            claim_data: list of {"claim_map": ClaimMap, "evidence": List[Dict]}

        Mutates each claim_map in place (same as map_evidence_to_elements).
        Falls back to per-claim calls on batch parse failure.
        """
        # Separate claims with and without evidence
        with_evidence = []
        for item in claim_data:
            cm = item["claim_map"]
            ev = item["evidence"]
            if not ev:
                # No evidence: mark all elements as unresolved immediately
                for elem in cm["elements"]:
                    elem["evidence_refs"] = []
                    elem["state"] = ElementState.unresolved
                    elem["uncertainty"] = "No evidence was retrieved for this element."
                cm["orientation"] = derive_orientation(cm["elements"])
                cm["metadata"]["mapping_model"] = "none"
                cm["metadata"]["element_count"] = len(cm["elements"])
                cm["metadata"]["completed_at"] = datetime.now(timezone.utc).isoformat()
            else:
                with_evidence.append(item)

        if not with_evidence:
            return

        if len(with_evidence) == 1:
            item = with_evidence[0]
            await self.map_evidence_to_elements(item["claim_map"], item["evidence"])
            return

        # Build batch prompt with per-claim sections
        sections = []
        for i, item in enumerate(with_evidence):
            cm = item["claim_map"]
            ev = item["evidence"]

            elements_desc = "\n".join(
                f"  - {e['element_id']}: {e['description']}" for e in cm["elements"]
            )
            evidence_desc = "\n".join(
                f"  - {ev_item.get('evidence_id', 'unknown')}: "
                f"[{ev_item.get('title', 'Untitled')}] "
                f"[Tier: {ev_item.get('tier', 'unknown')}] "
                f"[Type: {ev_item.get('evidence_type', 'unknown')}] "
                f"{(ev_item.get('snippet') or ev_item.get('text') or '')[:self.snippet_length]}"
                for ev_item in ev
            )

            sections.append(
                f"=== CLAIM {i} ===\n"
                f"Claim: \"{cm['normalised_claim']}\"\n"
                f"Elements:\n{elements_desc}\n"
                f"Evidence:\n{evidence_desc}"
            )

        prompt = BATCH_MAPPING_PROMPT + "\n\n" + "\n\n".join(sections)

        parsed = await self._call_llm(
            prompt=prompt,
            temperature=self.analyzer_temperature,
            max_tokens=8000,
            label="batch_mapping",
        )

        failed_indices: List[int] = []

        if parsed is not None and isinstance(parsed.get("claims"), list):
            batch_by_idx = {
                item.get("claim_index"): item
                for item in parsed["claims"]
                if isinstance(item, dict) and item.get("claim_index") is not None
            }

            for i, item in enumerate(with_evidence):
                mapped = batch_by_idx.get(i)
                if mapped is not None and isinstance(mapped.get("elements"), list):
                    try:
                        self._parse_mapping_response(
                            mapped, item["claim_map"], item["evidence"]
                        )
                        continue
                    except Exception as e:
                        logger.warning(
                            f"Batch mapping parse failed for claim "
                            f"{item['claim_map']['claim_id']}: {e}"
                        )
                failed_indices.append(i)
        else:
            logger.warning(
                "[CLAIM_MAP] Batch mapping returned invalid shape, "
                "falling back to per-claim calls"
            )
            failed_indices = list(range(len(with_evidence)))

        # Derive orientation + set metadata for successfully batch-mapped claims
        # (failed claims get this via per-claim map_evidence_to_elements)
        failed_set = set(failed_indices)
        model_used = self._last_model_used
        for i, item in enumerate(with_evidence):
            if i not in failed_set:
                cm = item["claim_map"]
                cm["orientation"] = derive_orientation(cm["elements"])
                cm["metadata"]["mapping_model"] = model_used
                cm["metadata"]["element_count"] = len(cm["elements"])
                cm["metadata"]["completed_at"] = datetime.now(timezone.utc).isoformat()

        # Retry failed claims individually
        if failed_indices:
            logger.info(
                f"[CLAIM_MAP] Retrying {len(failed_indices)} claims via per-claim mapping"
            )
            import asyncio

            async def _retry_map(idx: int) -> None:
                item = with_evidence[idx]
                await self.map_evidence_to_elements(item["claim_map"], item["evidence"])

            await asyncio.gather(*[_retry_map(i) for i in failed_indices])

    # ── LLM call (Google primary, OpenAI fallback) ──────────────────────

    async def _call_llm(
        self,
        prompt: str,
        temperature: float,
        max_tokens: int,
        label: str,
    ) -> Optional[Dict[str, Any]]:
        """Call LLM with Google primary, OpenAI fallback.

        Returns parsed JSON or None.  Token usage is accumulated internally
        on ``self._token_usage`` — read via ``get_token_usage()`` after all
        stages complete.
        """
        self._last_model_used = "unknown"

        # Try Google first
        if self.google_ai_api_key:
            try:
                # Use mapping-specific model for mapping/batch_mapping labels
                model_to_use = (
                    self.mapping_google_model
                    if label in ("mapping", "batch_mapping")
                    else self.google_model
                )
                parsed, usage = await self._call_google(
                    prompt, temperature, max_tokens, model=model_to_use
                )
                if parsed is not None:
                    self._last_model_used = model_to_use
                    self._accumulate(usage)
                    logger.info(f"[CLAIM_MAP] {label} completed via Google Gemini")
                    return parsed
            except Exception as e:
                logger.warning(f"[CLAIM_MAP] Google {label} failed: {e}")

        # Fall back to OpenAI
        if self.openai_api_key:
            try:
                model = (
                    self.decomposition_model
                    if label in ("decomposition", "batch_decomposition")
                    else self.analyzer_model
                )
                parsed, usage = await self._call_openai(
                    prompt, temperature, max_tokens, model
                )
                if parsed is not None:
                    self._last_model_used = model
                    self._accumulate(usage)
                    logger.info(f"[CLAIM_MAP] {label} completed via OpenAI")
                    return parsed
            except Exception as e:
                logger.warning(f"[CLAIM_MAP] OpenAI {label} failed: {e}")

        logger.error(f"[CLAIM_MAP] Both LLM providers failed for {label}")
        return None

    def _accumulate(self, usage: Optional[Dict[str, int]]) -> None:
        """Add usage to running total."""
        if usage:
            self._token_usage["input_tokens"] += usage.get("input_tokens", 0)
            self._token_usage["output_tokens"] += usage.get("output_tokens", 0)

    async def _call_google(
        self,
        prompt: str,
        temperature: float,
        max_tokens: int,
        model: Optional[str] = None,
    ) -> tuple:
        return await call_google_ai_with_usage(
            prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=self.timeout,
            model=model or self.google_model,
        )

    async def _call_openai(
        self, prompt: str, temperature: float, max_tokens: int, model: str
    ) -> tuple:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.openai_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": prompt},
                    ],
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                    "response_format": {"type": "json_object"},
                },
            )
        if response.status_code != 200:
            logger.error(f"OpenAI API error: {response.status_code}")
            return None, None
        result = response.json()
        content = result["choices"][0]["message"]["content"]
        usage_raw = result.get("usage", {})
        usage = {
            "input_tokens": usage_raw.get("prompt_tokens", 0),
            "output_tokens": usage_raw.get("completion_tokens", 0),
        }
        return json.loads(content), usage

    # ── Parse helpers ───────────────────────────────────────────────────

    def _parse_decomposition_response(
        self, raw: Dict[str, Any], claim_id: str
    ) -> ClaimMap:
        """Validate decomposition response and build partial ClaimMap."""
        normalised = raw.get("normalised_claim", "")
        if not normalised:
            raise ValueError("Missing normalised_claim")

        # Validate claim_type
        raw_type = raw.get("claim_type", "empirical")
        if raw_type not in _VALID_CLAIM_TYPES:
            logger.warning(f"Invalid claim_type '{raw_type}', defaulting to empirical")
            raw_type = "empirical"

        # Parse elements (enforce 1-5 cap)
        raw_elements = raw.get("elements", [])
        if not raw_elements:
            raise ValueError("No elements in decomposition response")

        raw_elements = raw_elements[: self.max_elements]

        elements: List[ClaimElement] = []
        for i, elem in enumerate(raw_elements, start=1):
            desc = elem.get("description", "")
            if not desc:
                continue
            elements.append(
                ClaimElement(
                    element_id=f"e{i}",
                    description=desc,
                    evidence_refs=[],
                    state=None,
                    uncertainty=None,
                )
            )

        if not elements:
            raise ValueError("All elements had empty descriptions")

        return ClaimMap(
            claim_id=claim_id,
            normalised_claim=normalised,
            claim_type=ClaimType(raw_type),
            elements=elements,
            orientation=None,
            metadata=ClaimMapMetadata(
                decomposition_model=self._last_model_used,
                mapping_model=None,
                element_count=len(elements),
                completed_at=None,
            ),
        )

    def _parse_mapping_response(
        self,
        raw: Dict[str, Any],
        claim_map: ClaimMap,
        evidence_list: List[Dict[str, Any]],
    ) -> None:
        """Parse mapping response and merge into existing ClaimMap (mutates in place)."""
        raw_elements = raw.get("elements", [])
        if not raw_elements:
            raise ValueError("No elements in mapping response")

        # Index by element_id for lookup
        raw_by_id = {e.get("element_id"): e for e in raw_elements}

        for elem in claim_map["elements"]:
            eid = elem["element_id"]
            mapped = raw_by_id.get(eid)
            if not mapped:
                # LLM omitted this element — mark unresolved
                elem["evidence_refs"] = []
                elem["state"] = ElementState.unresolved
                elem["uncertainty"] = None
                continue

            # Validate and filter evidence_refs
            raw_refs = mapped.get("evidence_refs", [])
            elem["evidence_refs"] = self._validate_evidence_refs(
                raw_refs, evidence_list
            )

            # Validate state
            raw_state = mapped.get("state", "unresolved")
            if raw_state not in _VALID_STATES:
                raw_state = "unresolved"
            elem["state"] = ElementState(raw_state)

            # Uncertainty (optional)
            elem["uncertainty"] = mapped.get("uncertainty") or None

    def _validate_evidence_refs(
        self,
        refs: List[Dict[str, str]],
        evidence_list: List[Dict[str, Any]],
    ) -> List[EvidenceRef]:
        """Filter out hallucinated evidence_ids and invalid relationships."""
        valid_ids = {
            ev.get("evidence_id") for ev in evidence_list if ev.get("evidence_id")
        }
        validated = []
        for ref in refs:
            eid = ref.get("evidence_id", "")
            rel = ref.get("relationship", "")
            if eid not in valid_ids:
                logger.debug(f"Stripping hallucinated evidence_id: {eid}")
                continue
            if rel not in _VALID_RELATIONSHIPS:
                logger.debug(f"Stripping invalid relationship: {rel}")
                continue
            validated.append(
                EvidenceRef(
                    evidence_id=eid,
                    relationship=EvidenceRelationship(rel),
                    reasoning=ref.get("reasoning") or None,
                )
            )
        return validated

    # ── Fallbacks ───────────────────────────────────────────────────────

    def _fallback_decomposition(self, claim_text: str, claim_id: str) -> ClaimMap:
        """Return single-element ClaimMap when decomposition fails."""
        return ClaimMap(
            claim_id=claim_id,
            normalised_claim=claim_text,
            claim_type=ClaimType.empirical,
            elements=[
                ClaimElement(
                    element_id="e1",
                    description=claim_text,
                    evidence_refs=[],
                    state=None,
                    uncertainty=None,
                )
            ],
            orientation=None,
            metadata=ClaimMapMetadata(
                decomposition_model="fallback",
                mapping_model=None,
                element_count=1,
                completed_at=None,
            ),
        )

    async def map_evidence_to_specific_elements(
        self,
        claim_map: ClaimMap,
        unresolved_element_ids: List[str],
        new_evidence: List[Dict[str, Any]],
    ) -> None:
        """Map new evidence to elements, with full cross-element visibility.

        Used by coverage recovery. Shows ALL elements in the LLM prompt so
        evidence can be mapped across element boundaries. Only updates state
        for unresolved (target) elements; resolved elements get new refs
        merged but keep their existing state.

        Mutates claim_map in place.
        """
        if not new_evidence or not unresolved_element_ids:
            return

        target_set = set(unresolved_element_ids)
        all_elements = claim_map["elements"]

        # Build context for LLM -- include ALL elements for cross-element mapping
        elements_desc = "\n".join(
            f"- {e['element_id']}: {e['description']}" for e in all_elements
        )
        evidence_desc = "\n".join(
            f"- {ev.get('evidence_id', 'unknown')}: "
            f"[{ev.get('title', 'Untitled')}] "
            f"[Tier: {ev.get('tier') or 'unclassified'}] "
            f"[Type: {ev.get('evidence_type') or 'unclassified'}] "
            f"{(ev.get('snippet') or ev.get('text') or '')[:self.snippet_length]}"
            for ev in new_evidence
        )

        prompt = (
            f"{MAPPING_PROMPT}\n\n"
            f"Claim: {claim_map['normalised_claim']}\n\n"
            f"Elements:\n{elements_desc}\n\n"
            f"Evidence:\n{evidence_desc}"
        )

        parsed = await self._call_llm(
            prompt=prompt,
            temperature=self.analyzer_temperature,
            max_tokens=self.analyzer_max_tokens,
            label="recovery_mapping",
        )

        if parsed is not None:
            try:
                raw_elements = parsed.get("elements", [])
                raw_by_id = {e.get("element_id"): e for e in raw_elements}

                for elem in all_elements:
                    eid = elem["element_id"]
                    mapped = raw_by_id.get(eid)
                    if not mapped:
                        continue

                    # Merge new evidence_refs with existing ones
                    new_refs = self._validate_evidence_refs(
                        mapped.get("evidence_refs", []), new_evidence
                    )
                    existing_refs = elem.get("evidence_refs", [])
                    elem["evidence_refs"] = existing_refs + new_refs

                    # Only update state for unresolved (target) elements
                    if eid in target_set:
                        raw_state = mapped.get("state", "unresolved")
                        if raw_state not in _VALID_STATES:
                            raw_state = "unresolved"
                        elem["state"] = ElementState(raw_state)
                        elem["uncertainty"] = mapped.get("uncertainty") or None

            except Exception as e:
                logger.warning(
                    f"Recovery mapping parse failed for claim {claim_map['claim_id']}: {e}"
                )

        # Re-derive orientation from all element states
        claim_map["orientation"] = derive_orientation(claim_map["elements"])

    def _has_null_reasoning(self, claim_map: ClaimMap) -> bool:
        """Check if any evidence_ref has null reasoning."""
        for elem in claim_map["elements"]:
            for ref in elem.get("evidence_refs", []):
                if ref.get("reasoning") is None:
                    return True
        return False

    def _fallback_mapping(self, claim_map: ClaimMap) -> None:
        """Mark all elements as unresolved when mapping fails."""
        for elem in claim_map["elements"]:
            elem["evidence_refs"] = []
            elem["state"] = ElementState.unresolved
            elem["uncertainty"] = None
