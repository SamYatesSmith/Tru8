import logging
import json
import asyncio
import re
from collections import defaultdict
from typing import Dict, List, Any, Optional, Set, Tuple

import httpx
from pydantic import BaseModel, Field, ValidationError, field_validator
from app.core.config import settings
from app.services.google_ai import call_google_ai, call_google_ai_with_usage

logger = logging.getLogger(__name__)


# NF-15: typed entity vocabulary. Drives adapter routing (LAW -> Hansard,
# ORG -> Companies House, etc.). See audit/pipeline-issues/2026-04-28_typed_entities_proposal.md.
ALLOWED_ENTITY_TYPES = frozenset(
    {"ORG", "PERSON", "LAW", "EVENT", "PRODUCT", "LOCATION", "AMOUNT", "DATE", "OTHER"}
)


class TypedEntity(BaseModel):
    """A claim entity with its semantic type.

    Emitted by the extract LLM (one per name/concept/amount/date in the
    claim). Consumed by retrieve.py to route adapters: Hansard wants LAW,
    Companies House wants ORG, etc. Unknown types are coerced to OTHER
    so an occasional LLM misfire doesn't crash the extract stage.
    """

    text: str = Field(min_length=1, max_length=200)
    type: str = Field(default="OTHER")

    @field_validator("type", mode="before")
    @classmethod
    def coerce_unknown_to_other(cls, v: Any) -> str:
        if not isinstance(v, str):
            return "OTHER"
        v_upper = v.strip().upper()
        if v_upper not in ALLOWED_ENTITY_TYPES:
            logger.warning(f"[EXTRACT] Unknown entity type {v!r} -> OTHER")
            return "OTHER"
        return v_upper


class ExtractedClaim(BaseModel):
    """Schema for extracted claims"""

    text: str = Field(description="The atomic factual claim", min_length=10)
    confidence: int = Field(
        description="Extraction confidence 0-100", ge=0, le=100, default=80
    )
    category: Optional[str] = Field(description="Category of claim", default=None)

    # Context preservation fields
    subject_context: Optional[str] = Field(
        description="Main subject/topic of the claim", default=None
    )
    key_entities: Optional[List[TypedEntity]] = Field(
        description=(
            "Key entities with semantic type. Type is one of: "
            "ORG, PERSON, LAW, EVENT, PRODUCT, LOCATION, AMOUNT, DATE, OTHER."
        ),
        default=None,
    )

    class Config:
        json_schema_extra = {
            "example": {
                "text": "Tesla delivered 1.3 million Model Y vehicles in 2022",
                "confidence": 95,
                "category": "business",
                "subject_context": "Tesla vehicle deliveries",
                "key_entities": [
                    {"text": "Tesla", "type": "ORG"},
                    {"text": "Model Y", "type": "PRODUCT"},
                    {"text": "1.3 million", "type": "AMOUNT"},
                    {"text": "2022", "type": "DATE"},
                ],
            }
        }


class ClaimExtractionResponse(BaseModel):
    """Schema for LLM response"""

    # max_items=20 is a safety ceiling; actual limit controlled by MAX_CLAIMS_PER_CHECK config
    # Truncation happens before validation (see _extract_with_openai)
    claims: List[ExtractedClaim] = Field(
        max_items=20,
        description="List of atomic claims (config-controlled limit, ceiling=20)",
    )
    source_summary: Optional[str] = Field(
        description="Brief summary of source content", default=None
    )
    extraction_confidence: int = Field(
        description="Overall extraction quality 0-100", default=80
    )


class ClaimExtractor:
    """Extract atomic factual claims from content using LLM"""

    def __init__(self):
        self.openai_api_key = settings.OPENAI_API_KEY
        self.google_ai_api_key = getattr(settings, "GOOGLE_AI_API_KEY", "")
        self.max_claims = settings.MAX_CLAIMS_PER_CHECK
        self.timeout = 30

        # System prompt for claim extraction
        self.system_prompt = """You are a Tru8 fact-checking specialist specializing in identifying verifiable claims.

RULES FOR EXTRACTING VERIFIABLE CLAIMS:

1. FACTUAL ONLY - Extract claims about actions/events/states that DID happen:
   ✓ GOOD: "Trump demolished the East Wing colonnade in March 2020"
   ✗ BAD: "Trump demolished... without consulting preservationists" (can't verify negative action)

2. AVOID PROCEDURAL NEGATIVES - Do NOT extract claims about actions NOT taken:
   ✗ BAD: "without consulting", "failed to notify", "did not consider", "never consulted"
   ✓ GOOD: Focus on positive actions that actually occurred

3. ATOMIC CLAIMS - One verifiable fact per claim (no conjunctions):
   ✗ BAD: "Trump demolished the colonnade and received criticism" (two claims)
   ✓ GOOD: "Trump demolished the East Wing colonnade" (one claim)

4. SELF-CONTAINED - Resolve ALL vague references using article context:
   ✗ BAD: "The administration proposed changes" (which admin? when?)
   ✓ GOOD: "The Biden administration proposed changes to Title IX in June 2022"
   ✗ BAD: "He announced a new policy" (who is "he"?)
   ✓ GOOD: "Boris Johnson announced a new housing policy"

5. CONCRETE & SPECIFIC - Include entities, dates, numbers:
   ✗ BAD: "Unemployment decreased significantly" (vague)
   ✓ GOOD: "UK unemployment decreased from 5.1% to 3.7% between 2020-2023"

6. OBJECTIVE ONLY - Avoid subjective language or opinions:
   ✗ BAD: "The policy is controversial" (opinion/subjective)
   ✓ GOOD: "The policy was opposed by 67% of surveyed voters" (measurable fact)

7. PRESENT IN SOURCE - Extract only explicitly stated or directly implied claims
8. Maximum {max_claims} claims per check
9. QUESTIONS AS CLAIMS - If the input is a question, extract the implicit factual claim:
   ✓ "Is sea level rising 3mm per year?" → "Sea level is rising 3mm per year"
   ✓ "Did the UK leave the EU?" → "The UK left the EU"
   ✓ "Has UK inflation fallen below 3%?" → "UK inflation has fallen below 3%"
   ✗ "What should I invest in?" → No verifiable claim (skip — subjective/advisory)
   ✗ "Who is the best footballer?" → No verifiable claim (skip — subjective)
   Only extract claims where the question implies a specific, verifiable factual statement.
   IMPORTANT: Always extract the AFFIRMATIVE implied claim. Do NOT insert your own judgement.
   ✓ "Is vaping safe?" → "Vaping is safe" (affirmative — evidence will show both sides)
   ✗ "Is vaping safe?" → "Vaping is not safe" (editorialised — do NOT do this)
   ✓ "Does sugar cause diabetes?" → "Sugar causes diabetes"
   ✗ "Does sugar cause diabetes?" → "Sugar does not cause diabetes"
10. AVOID OVERLAPPING CLAIMS - Do NOT extract multiple variations of the same allegation:
   ✗ BAD: Three claims about EU censorship from different angles
     - "EU Commission conducted censorship campaign"
     - "EU pressured platforms to censor content"
     - "EU targeted US political content"
   ✓ GOOD: ONE comprehensive claim covering the allegation:
     - "The EU Commission has pressured social media platforms to censor content, including targeting US political speech"

   If an article makes the SAME core allegation multiple ways, merge them into ONE claim.
   Different aspects of the SAME event/allegation = ONE claim.
   TRULY DIFFERENT allegations (different events, different subjects) = separate claims.

11. EXTRACT COMPREHENSIVELY - Extract ALL distinct verifiable facts, not just the main headline.
   Each of these deserves a separate claim:
   - Dates/timelines ("completed in 2019", "happened last week")
   - Costs/figures (monetary amounts, statistics, quantities)
   - Named individuals and their roles/titles
   - Organizations and their actions
   - Specific events with details
   - Historical context facts
   - Attributions ("X said", "Y denied", "Z confirmed")

   If an article contains 10 facts, extract 10 claims. Never summarize multiple facts into one.

HANDLING UNCERTAINTY:
If you cannot confidently extract a claim:
- Set confidence below 50
- Include the claim with a caveat in subject_context
- Do NOT fabricate or infer information not present in the source

OUTPUT FORMAT:
For EACH claim, provide:
- text: The self-contained, atomic, verifiable claim
- confidence: Integer 0-100 (how confident you are this is verifiable)
  - 90-100: Very high confidence (clear, specific, verifiable)
  - 75-89: High confidence (mostly clear, minor ambiguity)
  - 50-74: Moderate confidence (some ambiguity or missing context)
  - Below 50: Low confidence (significant uncertainty)
- subject_context: Main subject/topic (2-5 words)
- key_entities: List of {{"text": "...", "type": "..."}} objects, where type is one of:
    ORG       — companies, institutions, government bodies, NGOs
                (e.g. "BP plc", "ExxonMobil", "European Central Bank", "UK Treasury")
    PERSON    — named individuals
                (e.g. "Joe Biden", "Keir Starmer", "Karim Adeyemi")
    LAW       — Acts, Bills, Regulations, Codes, named statutes or treaties
                (e.g. "Climate Change Act 2008", "CHIPS and Science Act",
                "GDPR", "Inflation Reduction Act of 2022")
    EVENT     — named events
                (e.g. "2024 Paris Olympics", "COP28", "Brexit")
    PRODUCT   — specific products, instruments, vehicles, named software
                (e.g. "Model Y", "JWST", "iPhone 15", "Falcon 9")
    LOCATION  — places, regions, countries, buildings used as places
                (e.g. "UK", "Paris", "White House", "Mediterranean")
    AMOUNT    — money, percentages, quantities with units
                (e.g. "$40 billion", "GBP 28 billion", "4.5%", "1.3 million")
    DATE      — years, months, full dates, time spans
                (e.g. "2022", "September 2024", "1990-2023")
    OTHER     — domain concepts that don't fit above
                (e.g. "sulfur dioxide", "net zero", "Hycean planet")

  Type rules:
  - LAW takes precedence over DATE for "X Act 2008" — the whole phrase is one LAW entity, not two.
  - "BP plc" is ORG even though "plc" is lowercase.
  - "White House" is LOCATION when it refers to the building, ORG when it refers to the administration.
    Default to LOCATION unless the claim clearly attributes an action to the administration.
  - "Tesla", "ExxonMobil", "JWST" are ORG/PRODUCT respectively even when single-word.
  - Currency-prefixed numbers ("$40 billion", "GBP 28 billion") are AMOUNT regardless of currency.
  - Pure years ("2022") are DATE; numbered events ("2024 Paris Olympics") are EVENT.

GOOD EXAMPLES:

Article Title: "Tesla Q4 Earnings Report"
Input: "The company delivered 1.3 million Model Y vehicles in 2022, exceeding expectations."
Output: {{
  "claims": [{{
    "text": "Tesla delivered 1.3 million Model Y vehicles in 2022",
    "confidence": 95,
    "subject_context": "Tesla vehicle deliveries",
    "key_entities": [
      {{"text": "Tesla", "type": "ORG"}},
      {{"text": "Model Y", "type": "PRODUCT"}},
      {{"text": "1.3 million", "type": "AMOUNT"}},
      {{"text": "2022", "type": "DATE"}}
    ]
  }}]
}}

Article Title: "UK Climate Policy"
Input: "The Climate Change Act 2008 set the UK's target of net zero emissions by 2050."
Output: {{
  "claims": [{{
    "text": "The Climate Change Act 2008 set the UK target of net zero emissions by 2050",
    "confidence": 95,
    "subject_context": "UK climate legislation",
    "key_entities": [
      {{"text": "Climate Change Act 2008", "type": "LAW"}},
      {{"text": "UK", "type": "LOCATION"}},
      {{"text": "net zero", "type": "OTHER"}},
      {{"text": "2050", "type": "DATE"}}
    ]
  }}]
}}

Article Title: "Oil Major Earnings"
Input: "BP plc reported record profits of GBP 28 billion in 2022."
Output: {{
  "claims": [{{
    "text": "BP plc reported record profits of GBP 28 billion in 2022",
    "confidence": 95,
    "subject_context": "BP profits",
    "key_entities": [
      {{"text": "BP plc", "type": "ORG"}},
      {{"text": "GBP 28 billion", "type": "AMOUNT"}},
      {{"text": "2022", "type": "DATE"}}
    ]
  }}]
}}

Article Title: "White House Ceremony"
Input: "Joe Biden signed the CHIPS and Science Act at a White House ceremony in August 2022."
Output: {{
  "claims": [{{
    "text": "Joe Biden signed the CHIPS and Science Act at a White House ceremony in August 2022",
    "confidence": 95,
    "subject_context": "CHIPS Act signing",
    "key_entities": [
      {{"text": "Joe Biden", "type": "PERSON"}},
      {{"text": "CHIPS and Science Act", "type": "LAW"}},
      {{"text": "White House", "type": "LOCATION"}},
      {{"text": "August 2022", "type": "DATE"}}
    ]
  }}]
}}

BAD EXAMPLES TO AVOID:

Input: "Trump demolished the colonnade without consulting preservationists."
✗ BAD: "Trump demolished the colonnade without consulting preservationists" (includes unverifiable negative)
✓ GOOD: "Trump demolished the East Wing colonnade" (factual action only)

Input: "The controversial policy was implemented hastily."
✗ BAD: "The controversial policy was implemented hastily" (subjective words)
✓ GOOD: "The policy was implemented" (if date available, add it)

Always return valid JSON matching the required format."""

    async def extract_claims(
        self, content: str, metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Extract atomic claims from content"""
        try:
            if not content.strip():
                return {
                    "success": False,
                    "error": "No content provided for claim extraction",
                    "claims": [],
                }

            # Truncate content if too long (cost optimization)
            max_words = 2500  # Project limit
            words = content.split()
            if len(words) > max_words:
                content = " ".join(words[:max_words]) + "..."
                logger.info(f"Truncated content to {max_words} words")

            # Try Google AI extraction (primary)
            if self.google_ai_api_key:
                result = await self._extract_with_google(content, metadata or {})
                if result["success"] and result.get("claims"):
                    # Add source metadata to each claim
                    for claim in result.get("claims", []):
                        claim["source_title"] = (
                            metadata.get("title") if metadata else None
                        )
                        claim["source_url"] = metadata.get("url") if metadata else None
                        claim["source_date"] = (
                            metadata.get("date") if metadata else None
                        )
                    return result
                elif result["success"]:
                    logger.warning(
                        "Google AI returned success but 0 claims, trying next extractor"
                    )
                else:
                    logger.error(f"Google AI extraction failed: {result.get('error')}")

            # Try OpenAI extraction (fallback)
            if self.openai_api_key:
                logger.info("Attempting OpenAI extraction as fallback")
                result = await self._extract_with_openai(content, metadata or {})
                if result["success"] and result.get("claims"):
                    # Add source metadata to each claim
                    for claim in result.get("claims", []):
                        claim["source_title"] = (
                            metadata.get("title") if metadata else None
                        )
                        claim["source_url"] = metadata.get("url") if metadata else None
                        claim["source_date"] = (
                            metadata.get("date") if metadata else None
                        )
                    return result
                elif result["success"]:
                    logger.warning(
                        "OpenAI returned success but 0 claims, trying rule-based fallback"
                    )
                else:
                    logger.error(f"OpenAI extraction failed: {result.get('error')}")

            # Fallback to rule-based extraction
            logger.warning("All LLM extractions failed, using rule-based fallback")
            return self._extract_rule_based(content)

        except Exception as e:
            logger.error(f"Claim extraction error: {e}")
            return {"success": False, "error": str(e), "claims": []}

    async def _extract_with_openai(
        self, content: str, metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Extract claims using OpenAI GPT"""
        try:
            from datetime import datetime

            now = datetime.now()
            current_date = now.strftime("%Y-%m-%d")
            current_year = now.strftime("%Y")

            # Build context-aware user prompt with date context
            user_prompt = f"""CURRENT DATE CONTEXT:
Today's date is {current_date} (Year: {current_year}).
Use this to resolve relative time references ("yesterday", "this week", "recently").

"""
            if metadata and metadata.get("title"):
                user_prompt += f"Article Title: \"{metadata.get('title')}\"\n"
            if metadata and metadata.get("url"):
                user_prompt += f"Source URL: {metadata.get('url')}\n"
            user_prompt += (
                f"\nExtract atomic factual claims from this content:\n\n{content}"
            )

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.openai_api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": "gpt-4o-mini-2024-07-18",
                        "messages": [
                            {
                                "role": "system",
                                "content": self.system_prompt.format(
                                    max_claims=self.max_claims
                                ),
                            },
                            {"role": "user", "content": user_prompt},
                        ],
                        "temperature": 0.1,
                        "max_tokens": 1500,
                        "response_format": {"type": "json_object"},
                    },
                )

                if response.status_code != 200:
                    error_msg = f"OpenAI API error: {response.status_code}"
                    logger.error(error_msg)
                    return {"success": False, "error": error_msg}

                result = response.json()
                content_text = result["choices"][0]["message"]["content"]

                # Parse and validate JSON
                claims_data = json.loads(content_text)

                # Truncate claims if LLM exceeded the max (common issue)
                if (
                    "claims" in claims_data
                    and len(claims_data["claims"]) > self.max_claims
                ):
                    logger.warning(
                        f"LLM returned {len(claims_data['claims'])} claims (max={self.max_claims}), "
                        f"truncating to first {self.max_claims}"
                    )
                    claims_data["claims"] = claims_data["claims"][: self.max_claims]

                validated_response = ClaimExtractionResponse(**claims_data)

                # Convert to format expected by pipeline with context preservation.
                # NF-15: serialise TypedEntity -> {text, type} dicts at the boundary
                # so downstream (runner persistence, JSONB column) sees plain dicts.
                claims = [
                    {
                        "text": claim.text,
                        "position": i,
                        "confidence": claim.confidence,
                        "category": claim.category,
                        "subject_context": claim.subject_context,
                        "key_entities": [
                            {"text": e.text, "type": e.type}
                            for e in (claim.key_entities or [])
                        ],
                    }
                    for i, claim in enumerate(validated_response.claims)
                ]

                # Validate and refine claims (filter unverifiable, strip procedural negatives)
                claims = await self._validate_and_refine_claims(claims)

                # Re-number positions after filtering
                for i, claim in enumerate(claims):
                    claim["position"] = i

                # Post-processing: temporal analysis and claim classification
                # Note: settings already imported at module level

                # Temporal analysis if enabled (Phase 1.5, Week 4.5-5.5)
                if settings.ENABLE_TEMPORAL_CONTEXT:
                    from app.utils.temporal import TemporalAnalyzer

                    temporal_analyzer = TemporalAnalyzer()

                    for i, claim in enumerate(claims):
                        temporal_analysis = temporal_analyzer.analyze_claim(
                            claim["text"]
                        )
                        claims[i]["temporal_analysis"] = temporal_analysis
                        claims[i]["is_time_sensitive"] = temporal_analysis[
                            "is_time_sensitive"
                        ]
                        claims[i]["temporal_markers"] = temporal_analysis[
                            "temporal_markers"
                        ]
                        claims[i]["temporal_window"] = temporal_analysis[
                            "temporal_window"
                        ]

                        logger.debug(f"Claim temporal analysis: {temporal_analysis}")

                # Legal claim detection for API routing (simplified from full classification)
                if settings.ENABLE_CLAIM_CLASSIFICATION:
                    from app.utils.legal_claim_detector import LegalClaimDetector

                    detector = LegalClaimDetector()

                    for i, claim in enumerate(claims):
                        result = detector.classify(claim["text"])
                        if result.get("is_legal"):
                            claims[i]["claim_type"] = "legal"
                            claims[i]["legal_metadata"] = result.get("metadata", {})
                            logger.debug(
                                f"Legal claim detected: {claim['text'][:50]}..."
                            )

                # Article classification is handled by runner.py (attached to claims
                # after extraction) — no need to duplicate here.

                return {
                    "success": True,
                    "claims": claims,
                    "metadata": {
                        "extraction_method": "openai_gpt4o_mini",
                        "source_summary": validated_response.source_summary,
                        "extraction_confidence": validated_response.extraction_confidence,
                        "token_usage": result.get("usage", {}),
                    },
                }

        except httpx.TimeoutException:
            return {"success": False, "error": "OpenAI API timeout"}
        except ValidationError as e:
            logger.error(f"OpenAI response validation error: {e}")
            return {"success": False, "error": "Invalid response format from OpenAI"}
        except Exception as e:
            logger.error(f"OpenAI extraction error: {e}")
            return {"success": False, "error": str(e)}

    async def _extract_with_google(
        self, content: str, metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Extract claims using Google AI (Gemini) API as backup provider"""
        try:
            from datetime import datetime

            now = datetime.now()
            current_date = now.strftime("%Y-%m-%d")
            current_year = now.strftime("%Y")

            # Build context-aware user prompt with date context
            user_prompt = f"""CURRENT DATE CONTEXT:
Today's date is {current_date} (Year: {current_year}).
Use this to resolve relative time references ("yesterday", "this week", "recently").

"""
            if metadata and metadata.get("title"):
                user_prompt += f"Article Title: \"{metadata.get('title')}\"\n"
            if metadata and metadata.get("url"):
                user_prompt += f"Source URL: {metadata.get('url')}\n"
            user_prompt += (
                f"\nExtract atomic factual claims from this content:\n\n{content}"
            )

            # Combine system prompt and user prompt for Gemini
            full_prompt = f"{self.system_prompt.format(max_claims=self.max_claims)}\n\n{user_prompt}\n\nProvide your response as valid JSON."

            claims_data, token_usage = await call_google_ai_with_usage(
                full_prompt,
                temperature=0.1,
                max_tokens=1500,
                timeout=self.timeout,
            )
            if claims_data is None:
                return {"success": False, "error": "Google AI returned no response"}

            # Truncate claims if LLM exceeded the max
            if "claims" in claims_data and len(claims_data["claims"]) > self.max_claims:
                logger.warning(
                    f"Google AI returned {len(claims_data['claims'])} claims (max={self.max_claims}), "
                    f"truncating to first {self.max_claims}"
                )
                claims_data["claims"] = claims_data["claims"][: self.max_claims]

            validated_response = ClaimExtractionResponse(**claims_data)

            # NF-15: serialise TypedEntity -> {text, type} dicts at the boundary
            # so downstream (runner persistence, JSONB column) sees plain dicts.
            claims = [
                {
                    "text": claim.text,
                    "position": i,
                    "confidence": claim.confidence,
                    "category": claim.category,
                    "subject_context": claim.subject_context,
                    "key_entities": [
                        {"text": e.text, "type": e.type}
                        for e in (claim.key_entities or [])
                    ],
                }
                for i, claim in enumerate(validated_response.claims)
            ]

            # Validate and refine claims
            claims = await self._validate_and_refine_claims(claims)

            # Re-number positions after filtering
            for i, claim in enumerate(claims):
                claim["position"] = i

            # Post-processing: temporal analysis and claim classification
            if settings.ENABLE_TEMPORAL_CONTEXT:
                from app.utils.temporal import TemporalAnalyzer

                temporal_analyzer = TemporalAnalyzer()

                for i, claim in enumerate(claims):
                    temporal_analysis = temporal_analyzer.analyze_claim(claim["text"])
                    claims[i]["temporal_analysis"] = temporal_analysis
                    claims[i]["is_time_sensitive"] = temporal_analysis[
                        "is_time_sensitive"
                    ]
                    claims[i]["temporal_markers"] = temporal_analysis[
                        "temporal_markers"
                    ]
                    claims[i]["temporal_window"] = temporal_analysis["temporal_window"]

            # Legal claim detection
            if settings.ENABLE_CLAIM_CLASSIFICATION:
                from app.utils.legal_claim_detector import LegalClaimDetector

                detector = LegalClaimDetector()

                for i, claim in enumerate(claims):
                    result = detector.classify(claim["text"])
                    if result.get("is_legal"):
                        claims[i]["claim_type"] = "legal"
                        claims[i]["legal_metadata"] = result.get("metadata", {})

            # Article classification is handled by runner.py (attached to claims
            # after extraction) — no need to duplicate here.

            google_model = getattr(
                settings, "GOOGLE_LLM_MODEL", "gemini-2.5-flash-lite"
            )
            return {
                "success": True,
                "claims": claims,
                "metadata": {
                    "extraction_method": f"google_{google_model}",
                    "source_summary": validated_response.source_summary,
                    "extraction_confidence": validated_response.extraction_confidence,
                    "token_usage": token_usage,
                },
            }

        except ValidationError as e:
            logger.error(f"Google AI response validation error: {e}")
            return {"success": False, "error": "Invalid response format from Google AI"}
        except json.JSONDecodeError as e:
            logger.error(f"Google AI JSON parse error: {e}")
            return {
                "success": False,
                "error": "Failed to parse JSON from Google AI response",
            }
        except Exception as e:
            logger.error(f"Google AI extraction error: {e}")
            return {"success": False, "error": str(e)}

    async def _validate_and_refine_claims(
        self, claims: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Filter unverifiable claims, dedupe near-duplicates, merge over-decompositions."""
        validated = self._validate_individual_claims(claims)
        deduped = await self._deduplicate_similar_claims(validated)
        merged = await self._merge_redecomposed_claims(deduped)
        return merged

    @staticmethod
    def _normalise_subject_context(ctx: Any) -> Optional[str]:
        """Normalise a subject_context for grouping. None / empty → None (never groups).

        Strips case, surrounding whitespace, and surrounding punctuation
        (real LLM output sometimes has trailing punctuation or stray spaces).
        """
        if not isinstance(ctx, str):
            return None
        normalised = ctx.lower().strip().strip(".,;:").strip()
        return normalised or None

    @staticmethod
    def _entity_set(claim: Dict[str, Any]) -> Set[Tuple[str, str]]:
        """Convert key_entities to a set of (text_lower, type_upper) tuples."""
        out: Set[Tuple[str, str]] = set()
        for e in claim.get("key_entities") or []:
            if not isinstance(e, dict):
                continue
            text = e.get("text")
            typ = e.get("type")
            if isinstance(text, str) and isinstance(typ, str):
                t = text.lower().strip()
                if t:
                    out.add((t, typ.upper().strip()))
        return out

    @staticmethod
    def _has_org_date_backbone(entities: Set[Tuple[str, str]]) -> bool:
        """True if the entity set contains an ORG/PRODUCT and a DATE.

        Both anchors required: bare DATE overlap is too weak (every news claim
        shares a year), bare ORG overlap is too weak (companies appear in many
        unrelated claims). Together they identify a same-event/same-finding
        anchor that's unlikely to be coincidental.
        """
        has_org = any(typ in ("ORG", "PRODUCT") for _, typ in entities)
        has_date = any(typ == "DATE" for _, typ in entities)
        return has_org and has_date

    async def _synthesise_merged_claim_text(
        self, group_texts: List[str], required_entities: List[str]
    ) -> Optional[str]:
        """LLM rewrite N short factual sentences into one fluent sentence.

        Returns the synthesised text on success. Returns ``None`` on any
        failure — LLM call returned ``None``, malformed JSON shape, empty
        output, or an entity from ``required_entities`` was dropped from
        the rewrite. Caller falls back to the period-joined concat.

        The entity-preservation check is case-insensitive substring. False
        negatives (e.g. LLM rewrites "$149 billion" as "$149bn") fail the
        check and fall back — strictly safe: worst case is the original
        concat, never worse than today's behaviour.
        """
        if len(group_texts) < 2:
            return None

        numbered = "\n".join(f"{i + 1}. {t}" for i, t in enumerate(group_texts))
        entity_list = ", ".join(required_entities) if required_entities else "(none)"
        prompt = (
            "You are merging short factual sentences about the same topic "
            "into ONE fluent, readable sentence. Every named entity, "
            "figure, percentage, and date from the inputs MUST appear in "
            "your output. Do not add new claims, interpretations, or "
            "facts. Do not omit any fact.\n\n"
            f"Inputs:\n{numbered}\n\n"
            f"Required entities to preserve verbatim or as close-equivalent: {entity_list}\n\n"
            'Output JSON: {"text": "<one fluent sentence containing every input fact>"}'
        )

        try:
            result = await call_google_ai(
                prompt,
                temperature=0.1,
                max_tokens=400,
                timeout=15,
            )
        except Exception as exc:
            logger.warning(f"[EXTRACT] CLAIM SYNTHESIS error: {exc}")
            return None

        if not isinstance(result, dict):
            return None

        synthesised = result.get("text")
        if not isinstance(synthesised, str) or not synthesised.strip():
            return None

        synthesised = synthesised.strip()
        lowered = synthesised.lower()
        for ent in required_entities:
            if not ent:
                continue
            if ent.lower() not in lowered:
                logger.info(
                    f"[EXTRACT] CLAIM SYNTHESIS: dropped entity {ent!r}, falling back to concat"
                )
                return None

        return synthesised

    async def _merge_claim_group(self, group: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Combine a list of claims into one. Concat text, union entities,
        max confidence. Caller renumbers position.

        Attempts an LLM synthesis pass (Flash Lite) to produce a single
        fluent sentence preserving every entity. Falls back to naive
        period-joined concat if the LLM call fails, returns malformed
        JSON, drops an entity, or for any other reason. Original
        sentences are preserved on the merged claim as
        ``merged_source_texts`` regardless of which path is taken, so
        downstream debugging never loses provenance.
        """
        # Original texts: input to synthesis + provenance storage
        original_texts = [c.get("text", "") for c in group if c.get("text")]

        # Naive concat — always computed; used as fallback when synthesis fails
        stripped = [t.rstrip(".") for t in original_texts]
        fallback_text = ". ".join(t for t in stripped if t)
        if fallback_text:
            fallback_text = fallback_text + "."

        confidence = max((c.get("confidence", 0) or 0 for c in group), default=0)
        category = next(
            (c.get("category") for c in group if c.get("category") is not None),
            None,
        )
        subject_context = next(
            (c.get("subject_context") for c in group if c.get("subject_context")),
            None,
        )

        seen: Set[Tuple[str, str]] = set()
        entities: List[Dict[str, str]] = []
        for c in group:
            for e in c.get("key_entities") or []:
                if not isinstance(e, dict):
                    continue
                t_raw = e.get("text") or ""
                ty_raw = e.get("type") or ""
                key = (t_raw.lower().strip(), ty_raw.upper().strip())
                if not key[0]:
                    continue
                if key in seen:
                    continue
                seen.add(key)
                entities.append({"text": t_raw, "type": ty_raw})

        # LLM synthesis: best-effort, falls back to concat on any failure
        entity_strings = [e["text"] for e in entities if e.get("text")]
        synthesised = await self._synthesise_merged_claim_text(
            original_texts, entity_strings
        )
        final_text = synthesised if synthesised else fallback_text

        if synthesised:
            logger.info(
                f"[EXTRACT] CLAIM SYNTHESIS: rewrote {len(group)}-claim merge "
                f"({len(fallback_text)}→{len(synthesised)} chars)"
            )

        # Inherit other fields from the first claim (source_*, confidence-derived flags
        # from validation, etc.). Position renumbering happens in the caller.
        merged = dict(group[0])
        merged.update(
            {
                "text": final_text,
                "confidence": confidence,
                "category": category,
                "subject_context": subject_context,
                "key_entities": entities,
                "was_merged": True,
                "merged_from": [c.get("position") for c in group],
                "merged_source_texts": original_texts,
                "merge_text_source": "synthesised" if synthesised else "concat",
            }
        )
        return merged

    async def _merge_redecomposed_claims(
        self, claims: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Merge claims the LLM over-decomposed from a single substantive claim.

        Two passes operating on the LLM's own structured output (no LLM call,
        no prompt change). Complements the cosine-0.85 dedup that runs before
        it (which catches semantic-near-duplicates, not parent-child
        redecomposition).

        Pass 1 — claims sharing a normalised subject_context get merged.
                 Strongest signal: the LLM's own labelling tells us these
                 claims are about the same thing.
        Pass 2 — remaining singletons that share ≥3 key_entities including
                 an ORG/PRODUCT anchor and a DATE anchor get merged.
                 Catches paired findings of one event when subject_context
                 happens to differ on a modifier word (e.g. "false positives"
                 vs "false negatives" of the same study).

        See V1 quality plan 2026-05-06 for diagnostic data and design rationale.
        """
        if len(claims) <= 1:
            return claims

        # Pass 1: group by normalised subject_context
        by_ctx: Dict[str, List[int]] = defaultdict(list)
        no_ctx_idxs: List[int] = []
        for i, c in enumerate(claims):
            ctx = self._normalise_subject_context(c.get("subject_context"))
            if ctx:
                by_ctx[ctx].append(i)
            else:
                no_ctx_idxs.append(i)

        consumed: Set[int] = set()
        results: List[Tuple[int, Dict[str, Any]]] = []  # (anchor_position, claim)

        for ctx, idxs in by_ctx.items():
            if len(idxs) >= 2:
                group = [claims[i] for i in idxs]
                merged = await self._merge_claim_group(group)
                anchor = min(claims[i].get("position", i) for i in idxs)
                results.append((anchor, merged))
                consumed.update(idxs)
                logger.info(
                    f"[EXTRACT] CLAIM MERGE (subject_context): "
                    f"{len(idxs)} → 1 context='{ctx}' "
                    f"positions={sorted(claims[i].get('position', i) for i in idxs)}"
                )

        # Pass 2: greedy entity-overlap merge on whatever remains as singletons
        remaining: List[Tuple[int, Dict[str, Any]]] = [
            (i, claims[i]) for i in range(len(claims)) if i not in consumed
        ]

        while remaining:
            head_idx, head_claim = remaining.pop(0)
            merge_group: List[Tuple[int, Dict[str, Any]]] = [(head_idx, head_claim)]
            head_ents = self._entity_set(head_claim)

            j = 0
            while j < len(remaining):
                cand_idx, cand_claim = remaining[j]
                cand_ents = self._entity_set(cand_claim)
                overlap = head_ents & cand_ents
                if len(overlap) >= 3 and self._has_org_date_backbone(overlap):
                    merge_group.append((cand_idx, cand_claim))
                    head_ents = head_ents | cand_ents  # greedy union
                    remaining.pop(j)
                else:
                    j += 1

            if len(merge_group) >= 2:
                group_claims = [c for _, c in merge_group]
                merged = await self._merge_claim_group(group_claims)
                anchor = min(c.get("position", idx) for idx, c in merge_group)
                results.append((anchor, merged))
                logger.info(
                    f"[EXTRACT] CLAIM MERGE (entity-overlap): "
                    f"{len(merge_group)} → 1 "
                    f"positions={sorted(c.get('position', idx) for idx, c in merge_group)}"
                )
            else:
                anchor = head_claim.get("position", head_idx)
                results.append((anchor, head_claim))

        # Stable order by original anchor position
        results.sort(key=lambda x: x[0])
        return [c for _, c in results]

    async def _deduplicate_similar_claims(
        self, claims: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Remove semantically similar claims using embedding similarity"""
        if len(claims) <= 1:
            return claims

        try:
            from app.services.embeddings import get_embedding_service
            import numpy as np

            # Get embeddings for all claims
            claim_texts = [c["text"] for c in claims]
            service = await get_embedding_service()
            embeddings = await service.embed_batch(claim_texts)

            if embeddings is None or len(embeddings) == 0:
                logger.warning(
                    "[EXTRACT] Embedding service unavailable, skipping deduplication"
                )
                return claims

            # Find similar pairs (cosine similarity > 0.85)
            SIMILARITY_THRESHOLD = 0.85
            to_remove = set()

            for i in range(len(embeddings)):
                if i in to_remove:
                    continue
                for j in range(i + 1, len(embeddings)):
                    if j in to_remove:
                        continue

                    # Cosine similarity
                    sim = np.dot(embeddings[i], embeddings[j]) / (
                        np.linalg.norm(embeddings[i]) * np.linalg.norm(embeddings[j])
                    )

                    if sim > SIMILARITY_THRESHOLD:
                        # Keep the longer/more detailed claim, remove the shorter one
                        if len(claims[i]["text"]) >= len(claims[j]["text"]):
                            to_remove.add(j)
                            logger.info(
                                f"[EXTRACT] CLAIM DEDUP: Removed similar claim (sim={sim:.2f})"
                            )
                            logger.info(f"   Kept: {claims[i]['text'][:60]}...")
                            logger.info(f"   Removed: {claims[j]['text'][:60]}...")
                        else:
                            to_remove.add(i)
                            logger.info(
                                f"[EXTRACT] CLAIM DEDUP: Removed similar claim (sim={sim:.2f})"
                            )
                            logger.info(f"   Kept: {claims[j]['text'][:60]}...")
                            logger.info(f"   Removed: {claims[i]['text'][:60]}...")
                            break  # i was removed, move to next i

            # Build deduplicated list
            deduped = [c for idx, c in enumerate(claims) if idx not in to_remove]

            if len(to_remove) > 0:
                logger.info(
                    f"[EXTRACT] CLAIM DEDUP: {len(claims)} → {len(deduped)} claims ({len(to_remove)} duplicates removed)"
                )

            return deduped

        except ImportError:
            logger.warning(
                "[EXTRACT] Embeddings module not available, skipping deduplication"
            )
            return claims
        except Exception as e:
            logger.warning(
                f"[EXTRACT] Claim deduplication failed: {e}, continuing without"
            )
            return claims

    def _validate_individual_claims(
        self, claims: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Filter out unverifiable claims and refine problematic ones"""
        validated_claims = []
        filtered_count = 0

        for claim in claims:
            claim_text = claim.get("text", "")

            # Check 1: Detect procedural negatives (unverifiable)
            procedural_patterns = [
                "without ",
                "failed to",
                "did not",
                "never ",
                "didn't",
                "refused to",
                "neglected to",
                "omitted to",
            ]
            has_procedural = any(
                phrase in claim_text.lower() for phrase in procedural_patterns
            )

            if has_procedural:
                # Try to extract factual core by removing the procedural part
                factual_core = claim_text
                for pattern in [
                    r"\s+without\s+\w+ing\b.*",
                    r"\s+failed to\s+\w+\b.*",
                    r"\s+did not\s+\w+\b.*",
                    r"\s+didn\'?t\s+\w+\b.*",
                    r"\s+never\s+\w+ed\b.*",
                    r"\s+refused to\s+\w+\b.*",
                ]:
                    factual_core = re.sub(
                        pattern, "", factual_core, flags=re.IGNORECASE
                    )

                factual_core = factual_core.strip().rstrip(",")

                # Only keep if factual core is substantial (>20 chars)
                if len(factual_core) > 20:
                    logger.info(
                        f"[EXTRACT] CLAIM REFINEMENT: Stripped procedural negative"
                    )
                    logger.info(f"   Original: {claim_text[:80]}...")
                    logger.info(f"   Refined: {factual_core[:80]}...")
                    claim["text"] = factual_core
                    claim["confidence"] = int(
                        claim["confidence"] * 0.85
                    )  # Lower confidence for modified claim
                    claim["was_refined"] = True
                else:
                    logger.warning(
                        f"[EXTRACT] CLAIM FILTERED: Procedural negative with no factual core"
                    )
                    logger.warning(f"   Claim: {claim_text[:80]}...")
                    filtered_count += 1
                    continue

            # Check 2: Ensure entities are resolved (no unresolved pronouns at start)
            first_word = claim_text.lower().split()[0] if claim_text.strip() else ""
            has_pronoun = first_word in (
                "he",
                "she",
                "they",
                "it",
                "this",
                "that",
                "these",
                "those",
            )

            if has_pronoun:
                logger.warning(
                    f"[EXTRACT] CLAIM FILTERED: Unresolved pronoun/reference"
                )
                logger.warning(f"   Claim: {claim_text[:80]}...")
                filtered_count += 1
                continue

            # Check 3: Minimum specificity (has at least one specific marker)
            has_date = bool(
                re.search(
                    r"\b(19|20)\d{2}\b|\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)",
                    claim_text,
                )
            )
            has_number = bool(re.search(r"\d+", claim_text))
            has_proper_noun = bool(
                re.search(r"\b[A-Z][a-z]+\b|\b[A-Z]{2,}\b", claim_text)
            )

            if not (has_date or has_number or has_proper_noun):
                logger.warning(
                    f"[EXTRACT] CLAIM FILTERED: Too vague (no date/number/proper noun)"
                )
                logger.warning(f"   Claim: {claim_text[:80]}...")
                filtered_count += 1
                continue

            # Check 4: Detect subjective/opinion language
            subjective_words = [
                "controversial",
                "debatable",
                "questionable",
                "arguably",
                "seems",
                "appears",
                "might",
                "could",
                "possibly",
                "probably",
                "likely",
                "unlikely",
            ]
            has_subjective = any(
                word in claim_text.lower() for word in subjective_words
            )

            if has_subjective:
                # Lower confidence but don't filter (might still be verifiable)
                logger.info(f"[EXTRACT] CLAIM WARNING: Contains subjective language")
                logger.info(f"   Claim: {claim_text[:80]}...")
                claim["confidence"] = int(claim["confidence"] * 0.75)
                claim["has_subjective_language"] = True

            # Passed all checks
            validated_claims.append(claim)

        if filtered_count > 0:
            logger.info(
                f"[EXTRACT] CLAIM VALIDATION: {len(validated_claims)} passed, {filtered_count} filtered"
            )

        return validated_claims

    def _extract_rule_based(self, content: str) -> Dict[str, Any]:
        """Fallback rule-based claim extraction"""
        try:
            # Simple heuristic-based extraction
            sentences = [s.strip() for s in content.split(".") if s.strip()]

            claims = []
            for i, sentence in enumerate(sentences[: self.max_claims]):
                # Filter for sentences that might contain factual claims
                if len(sentence) > 20 and any(
                    keyword in sentence.lower()
                    for keyword in [
                        "study",
                        "research",
                        "data",
                        "report",
                        "according to",
                        "percent",
                        "%",
                        "million",
                        "billion",
                        "increase",
                        "decrease",
                        "announced",
                        "confirmed",
                        "revealed",
                        "found",
                        "discovered",
                    ]
                ):
                    claims.append(
                        {
                            "text": sentence + ".",
                            "position": i,
                            "confidence": 0.6,  # Lower confidence for rule-based
                            "category": "general",
                        }
                    )

            if not claims:
                # If no heuristic matches, take first few substantial sentences
                for i, sentence in enumerate(sentences[:3]):
                    if len(sentence) > 30:
                        claims.append(
                            {
                                "text": sentence + ".",
                                "position": i,
                                "confidence": 0.4,
                                "category": "general",
                            }
                        )

            return {
                "success": True,
                "claims": claims,
                "metadata": {
                    "extraction_method": "rule_based_fallback",
                    "extraction_confidence": 0.5,
                },
            }

        except Exception as e:
            logger.error(f"Rule-based extraction error: {e}")
            return {"success": False, "error": str(e), "claims": []}
