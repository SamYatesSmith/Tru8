import logging
import json
import asyncio
import re
from typing import Dict, List, Any, Optional
import httpx
from pydantic import BaseModel, Field, ValidationError
from app.core.config import settings

logger = logging.getLogger(__name__)

class ExtractedClaim(BaseModel):
    """Schema for extracted claims"""
    text: str = Field(description="The atomic factual claim", min_length=10)
    confidence: float = Field(description="Extraction confidence 0-1", ge=0, le=1, default=0.8)
    category: Optional[str] = Field(description="Category of claim", default=None)

    # Context preservation fields
    subject_context: Optional[str] = Field(description="Main subject/topic of the claim", default=None)
    key_entities: Optional[List[str]] = Field(description="Key entities mentioned (names, organizations, places)", default=None)

    class Config:
        json_schema_extra = {
            "example": {
                "text": "The Earth's average temperature has increased by 1.1°C since pre-industrial times",
                "confidence": 0.95,
                "category": "science",
                "subject_context": "global warming and climate change",
                "key_entities": ["Earth", "1.1°C", "pre-industrial times"]
            }
        }

class ClaimExtractionResponse(BaseModel):
    """Schema for LLM response"""
    claims: List[ExtractedClaim] = Field(max_items=12, description="List of atomic claims, max 12 for Quick mode")
    source_summary: Optional[str] = Field(description="Brief summary of source content", default=None)
    extraction_confidence: float = Field(description="Overall extraction quality", default=0.8)

class ClaimExtractor:
    """Extract atomic factual claims from content using LLM"""
    
    def __init__(self):
        self.openai_api_key = settings.OPENAI_API_KEY
        self.max_claims = settings.MAX_CLAIMS_PER_CHECK  # 12 for Quick mode
        self.timeout = 30
        
        # System prompt for claim extraction
        self.system_prompt = """You are a fact-checking assistant that extracts atomic, verifiable claims from content.

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
8. Maximum {max_claims} claims for Quick mode
9. Focus on the most important/checkable claims

OUTPUT FORMAT:
For EACH claim, provide:
- text: The self-contained, atomic, verifiable claim
- confidence: 0.8-1.0 (how confident you are this is verifiable)
- subject_context: Main subject/topic (2-5 words)
- key_entities: List of specific entities (names, organizations, places, amounts, dates)

GOOD EXAMPLES:

Article Title: "Tesla Q4 Earnings Report"
Input: "The company delivered 1.3 million vehicles in 2022, exceeding expectations."
Output: {{
  "claims": [{{
    "text": "Tesla delivered 1.3 million vehicles in 2022",
    "confidence": 0.95,
    "subject_context": "Tesla vehicle deliveries",
    "key_entities": ["Tesla", "1.3 million vehicles", "2022"]
  }}]
}}

Article Title: "White House Renovation"
Input: "The Project received $350 million in federal funding."
Output: {{
  "claims": [{{
    "text": "The White House ballroom renovation project received $350 million in federal funding",
    "confidence": 0.95,
    "subject_context": "White House renovation funding",
    "key_entities": ["White House", "ballroom renovation", "$350 million", "federal funding"]
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

    async def extract_claims(self, content: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Extract atomic claims from content"""
        try:
            if not content.strip():
                return {
                    "success": False,
                    "error": "No content provided for claim extraction",
                    "claims": []
                }
            
            # Truncate content if too long (cost optimization)
            max_words = 2500  # Project limit
            words = content.split()
            if len(words) > max_words:
                content = ' '.join(words[:max_words]) + "..."
                logger.info(f"Truncated content to {max_words} words")
            
            # Try OpenAI extraction
            if self.openai_api_key:
                result = await self._extract_with_openai(content, metadata or {})
                if result["success"]:
                    # Add source metadata to each claim
                    for claim in result.get("claims", []):
                        claim["source_title"] = metadata.get("title") if metadata else None
                        claim["source_url"] = metadata.get("url") if metadata else None
                    return result
                else:
                    logger.error(f"OpenAI extraction failed: {result.get('error')}")

            # Fallback to rule-based extraction
            logger.warning("LLM extraction failed, using rule-based fallback")
            return self._extract_rule_based(content)
            
        except Exception as e:
            logger.error(f"Claim extraction error: {e}")
            return {
                "success": False,
                "error": str(e),
                "claims": []
            }
    
    async def _extract_with_openai(self, content: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Extract claims using OpenAI GPT"""
        try:
            # Build context-aware user prompt
            user_prompt = ""
            if metadata and metadata.get("title"):
                user_prompt += f"Article Title: \"{metadata.get('title')}\"\n"
            if metadata and metadata.get("url"):
                user_prompt += f"Source URL: {metadata.get('url')}\n"
            user_prompt += f"\nExtract atomic factual claims from this content:\n\n{content}"

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.openai_api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "gpt-4o-mini-2024-07-18",
                        "messages": [
                            {
                                "role": "system",
                                "content": self.system_prompt.format(max_claims=self.max_claims)
                            },
                            {
                                "role": "user",
                                "content": user_prompt
                            }
                        ],
                        "temperature": 0.1,
                        "max_tokens": 1500,
                        "response_format": {"type": "json_object"}
                    }
                )
                
                if response.status_code != 200:
                    error_msg = f"OpenAI API error: {response.status_code}"
                    logger.error(error_msg)
                    return {"success": False, "error": error_msg}
                
                result = response.json()
                content_text = result["choices"][0]["message"]["content"]
                
                # Parse and validate JSON
                claims_data = json.loads(content_text)
                validated_response = ClaimExtractionResponse(**claims_data)
                
                # Convert to format expected by pipeline with context preservation
                claims = [
                    {
                        "text": claim.text,
                        "position": i,
                        "confidence": claim.confidence,
                        "category": claim.category,
                        # Context preservation fields
                        "subject_context": claim.subject_context,
                        "key_entities": claim.key_entities or []
                    }
                    for i, claim in enumerate(validated_response.claims)
                ]

                # Validate and refine claims (filter unverifiable, strip procedural negatives)
                claims = self._validate_and_refine_claims(claims)

                # Re-number positions after filtering
                for i, claim in enumerate(claims):
                    claim["position"] = i

                # Post-processing: temporal analysis and claim classification
                from app.core.config import settings

                # Temporal analysis if enabled (Phase 1.5, Week 4.5-5.5)
                if settings.ENABLE_TEMPORAL_CONTEXT:
                    from app.utils.temporal import TemporalAnalyzer
                    temporal_analyzer = TemporalAnalyzer()

                    for i, claim in enumerate(claims):
                        temporal_analysis = temporal_analyzer.analyze_claim(claim["text"])
                        claims[i]["temporal_analysis"] = temporal_analysis
                        claims[i]["is_time_sensitive"] = temporal_analysis["is_time_sensitive"]
                        claims[i]["temporal_markers"] = temporal_analysis["temporal_markers"]
                        claims[i]["temporal_window"] = temporal_analysis["temporal_window"]

                        logger.debug(f"Claim temporal analysis: {temporal_analysis}")

                # Claim classification if enabled (Phase 2, Week 5.5-6.5)
                if settings.ENABLE_CLAIM_CLASSIFICATION:
                    from app.utils.claim_classifier import ClaimClassifier
                    classifier = ClaimClassifier()

                    for i, claim in enumerate(claims):
                        classification = classifier.classify(claim["text"])
                        claims[i]["classification"] = classification
                        claims[i]["claim_type"] = classification["claim_type"]
                        claims[i]["is_verifiable"] = classification["is_verifiable"]
                        claims[i]["verifiability_reason"] = classification["reason"]

                        # Store legal metadata if present (for legal claims)
                        if "metadata" in classification:
                            claims[i]["legal_metadata"] = classification["metadata"]

                        logger.debug(f"Claim classification: {classification['claim_type']} (verifiable: {classification['is_verifiable']})")

                return {
                    "success": True,
                    "claims": claims,
                    "metadata": {
                        "extraction_method": "openai_gpt4o_mini",
                        "source_summary": validated_response.source_summary,
                        "extraction_confidence": validated_response.extraction_confidence,
                        "token_usage": result.get("usage", {})
                    }
                }
                
        except httpx.TimeoutException:
            return {"success": False, "error": "OpenAI API timeout"}
        except ValidationError as e:
            logger.error(f"OpenAI response validation error: {e}")
            return {"success": False, "error": "Invalid response format from OpenAI"}
        except Exception as e:
            logger.error(f"OpenAI extraction error: {e}")
            return {"success": False, "error": str(e)}

    def _validate_and_refine_claims(self, claims: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter out unverifiable claims and refine problematic ones"""
        validated_claims = []
        filtered_count = 0

        for claim in claims:
            claim_text = claim.get("text", "")

            # Check 1: Detect procedural negatives (unverifiable)
            procedural_patterns = [
                'without ', 'failed to', 'did not', 'never ', "didn't",
                'refused to', 'neglected to', 'omitted to'
            ]
            has_procedural = any(phrase in claim_text.lower() for phrase in procedural_patterns)

            if has_procedural:
                # Try to extract factual core by removing the procedural part
                factual_core = claim_text
                for pattern in [
                    r'\s+without\s+\w+ing\b.*',
                    r'\s+failed to\s+\w+\b.*',
                    r'\s+did not\s+\w+\b.*',
                    r'\s+didn\'?t\s+\w+\b.*',
                    r'\s+never\s+\w+ed\b.*',
                    r'\s+refused to\s+\w+\b.*',
                ]:
                    factual_core = re.sub(pattern, '', factual_core, flags=re.IGNORECASE)

                factual_core = factual_core.strip().rstrip(',')

                # Only keep if factual core is substantial (>20 chars)
                if len(factual_core) > 20:
                    logger.info(f"🔧 CLAIM REFINEMENT: Stripped procedural negative")
                    logger.info(f"   Original: {claim_text[:80]}...")
                    logger.info(f"   Refined: {factual_core[:80]}...")
                    claim["text"] = factual_core
                    claim["confidence"] *= 0.85  # Lower confidence for modified claim
                    claim["was_refined"] = True
                else:
                    logger.warning(f"⚠️  CLAIM FILTERED: Procedural negative with no factual core")
                    logger.warning(f"   Claim: {claim_text[:80]}...")
                    filtered_count += 1
                    continue

            # Check 2: Ensure entities are resolved (no unresolved pronouns)
            unresolved_pronouns = ['he ', 'she ', 'they ', 'it ', 'this ', 'that ', 'these ', 'those ']
            words_lower = claim_text.lower().split()
            has_pronoun = any(pronoun.strip() in words_lower for pronoun in unresolved_pronouns)

            if has_pronoun:
                logger.warning(f"⚠️  CLAIM FILTERED: Unresolved pronoun/reference")
                logger.warning(f"   Claim: {claim_text[:80]}...")
                filtered_count += 1
                continue

            # Check 3: Minimum specificity (has at least one specific marker)
            has_date = bool(re.search(r'\b(19|20)\d{2}\b|\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)', claim_text))
            has_number = bool(re.search(r'\d+', claim_text))
            has_proper_noun = bool(re.search(r'\b[A-Z][a-z]+\b', claim_text))

            if not (has_date or has_number or has_proper_noun):
                logger.warning(f"⚠️  CLAIM FILTERED: Too vague (no date/number/proper noun)")
                logger.warning(f"   Claim: {claim_text[:80]}...")
                filtered_count += 1
                continue

            # Check 4: Detect subjective/opinion language
            subjective_words = [
                'controversial', 'debatable', 'questionable', 'arguably',
                'seems', 'appears', 'might', 'could', 'possibly',
                'probably', 'likely', 'unlikely'
            ]
            has_subjective = any(word in claim_text.lower() for word in subjective_words)

            if has_subjective:
                # Lower confidence but don't filter (might still be verifiable)
                logger.info(f"⚠️  CLAIM WARNING: Contains subjective language")
                logger.info(f"   Claim: {claim_text[:80]}...")
                claim["confidence"] *= 0.75
                claim["has_subjective_language"] = True

            # Passed all checks
            validated_claims.append(claim)

        if filtered_count > 0:
            logger.info(f"📊 CLAIM VALIDATION: {len(validated_claims)} passed, {filtered_count} filtered")

        return validated_claims

    def _extract_rule_based(self, content: str) -> Dict[str, Any]:
        """Fallback rule-based claim extraction"""
        try:
            # Simple heuristic-based extraction
            sentences = [s.strip() for s in content.split('.') if s.strip()]
            
            claims = []
            for i, sentence in enumerate(sentences[:self.max_claims]):
                # Filter for sentences that might contain factual claims
                if (len(sentence) > 20 and 
                    any(keyword in sentence.lower() for keyword in [
                        'study', 'research', 'data', 'report', 'according to',
                        'percent', '%', 'million', 'billion', 'increase', 'decrease',
                        'announced', 'confirmed', 'revealed', 'found', 'discovered'
                    ])):
                    claims.append({
                        "text": sentence + ".",
                        "position": i,
                        "confidence": 0.6,  # Lower confidence for rule-based
                        "category": "general"
                    })
            
            if not claims:
                # If no heuristic matches, take first few substantial sentences
                for i, sentence in enumerate(sentences[:3]):
                    if len(sentence) > 30:
                        claims.append({
                            "text": sentence + ".",
                            "position": i,
                            "confidence": 0.4,
                            "category": "general"
                        })

            return {
                "success": True,
                "claims": claims,
                "metadata": {
                    "extraction_method": "rule_based_fallback",
                    "extraction_confidence": 0.5
                }
            }
            
        except Exception as e:
            logger.error(f"Rule-based extraction error: {e}")
            return {
                "success": False,
                "error": str(e),
                "claims": []
            }