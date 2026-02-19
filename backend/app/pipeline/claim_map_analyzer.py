"""Claim Map Analyzer — decompose claims into elements and map evidence.

Two LLM calls per claim:
  1. Decomposition: claim text → normalised_claim + claim_type + 1-5 elements
  2. Evidence mapping: elements + evidence → evidence_refs + states + uncertainty

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
from app.services.google_ai import call_google_ai
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

For each element, map relevant evidence and assign a state.

Respond with JSON only:
{
  "elements": [
    {
      "element_id": "<e1..e5>",
      "evidence_refs": [
        {"evidence_id": "<string>", "relationship": "supports|challenges|context"}
      ],
      "state": "supported|disputed|unresolved",
      "uncertainty": "<one sentence or null>"
    }
  ]
}

Rules:
- Only use evidence_ids from the provided list. Do NOT invent IDs.
- relationship must be exactly one of: supports, challenges, context.
- state must be exactly one of: supported, disputed, unresolved.
- "supported" = predominantly supportive evidence, no significant challenges.
- "disputed" = both supporting and challenging evidence present.
- "unresolved" = no meaningful supporting or challenging evidence.
- uncertainty is optional (null if not applicable), max one sentence.
- Every element_id from the input must appear in the output.
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
        self.timeout = 30

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

    # ── LLM call (Google primary, OpenAI fallback) ──────────────────────

    async def _call_llm(
        self,
        prompt: str,
        temperature: float,
        max_tokens: int,
        label: str,
    ) -> Optional[Dict[str, Any]]:
        """Call LLM with Google primary, OpenAI fallback. Returns parsed JSON or None."""
        self._last_model_used = "unknown"

        # Try Google first
        if self.google_ai_api_key:
            try:
                result = await self._call_google(prompt, temperature, max_tokens)
                if result is not None:
                    self._last_model_used = self.google_model
                    logger.info(f"[CLAIM_MAP] {label} completed via Google Gemini")
                    return result
            except Exception as e:
                logger.warning(f"[CLAIM_MAP] Google {label} failed: {e}")

        # Fall back to OpenAI
        if self.openai_api_key:
            try:
                model = (
                    self.decomposition_model
                    if label == "decomposition"
                    else self.analyzer_model
                )
                result = await self._call_openai(prompt, temperature, max_tokens, model)
                if result is not None:
                    self._last_model_used = model
                    logger.info(f"[CLAIM_MAP] {label} completed via OpenAI")
                    return result
            except Exception as e:
                logger.warning(f"[CLAIM_MAP] OpenAI {label} failed: {e}")

        logger.error(f"[CLAIM_MAP] Both LLM providers failed for {label}")
        return None

    async def _call_google(
        self, prompt: str, temperature: float, max_tokens: int
    ) -> Optional[Dict[str, Any]]:
        return await call_google_ai(
            prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=self.timeout,
            model=self.google_model,
        )

    async def _call_openai(
        self, prompt: str, temperature: float, max_tokens: int, model: str
    ) -> Optional[Dict[str, Any]]:
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
            return None
        result = response.json()
        content = result["choices"][0]["message"]["content"]
        return json.loads(content)

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
                EvidenceRef(evidence_id=eid, relationship=EvidenceRelationship(rel))
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

    def _fallback_mapping(self, claim_map: ClaimMap) -> None:
        """Mark all elements as unresolved when mapping fails."""
        for elem in claim_map["elements"]:
            elem["evidence_refs"] = []
            elem["state"] = ElementState.unresolved
            elem["uncertainty"] = None
