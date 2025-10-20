import logging
import json
import asyncio
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
    
    class Config:
        json_schema_extra = {
            "example": {
                "text": "The Earth's average temperature has increased by 1.1°C since pre-industrial times",
                "confidence": 0.95,
                "category": "science"
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
        self.anthropic_api_key = getattr(settings, 'ANTHROPIC_API_KEY', '')
        self.max_claims = settings.MAX_CLAIMS_PER_CHECK  # 12 for Quick mode
        self.timeout = 30
        
        # System prompt for claim extraction
        self.system_prompt = """You are a fact-checking assistant that extracts atomic, verifiable claims from content.

RULES:
1. Extract ONLY factual claims that can be verified against external sources
2. Make claims atomic (one fact per claim) and specific
3. Avoid opinions, speculation, or subjective statements
4. Include numbers, dates, names when present
5. Maximum {max_claims} claims for Quick mode
6. Focus on the most important/checkable claims
7. Always return a valid JSON response with the required format

EXAMPLES:
Input: "Tesla delivered 1.3 million vehicles in 2022, exceeding Wall Street expectations."
Output: {{"claims": [{{"text": "Tesla delivered 1.3 million vehicles in 2022", "confidence": 0.95}}]}}

Input: "Climate change is a hoax promoted by scientists for funding."
Output: {{"claims": [{{"text": "Some individuals claim climate change is promoted for funding", "confidence": 0.6}}]}}"""

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
            
            # Try OpenAI first, then Anthropic fallback
            if self.openai_api_key:
                result = await self._extract_with_openai(content)
                if result["success"]:
                    return result
            
            if self.anthropic_api_key:
                result = await self._extract_with_anthropic(content)
                if result["success"]:
                    return result
            
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
    
    async def _extract_with_openai(self, content: str) -> Dict[str, Any]:
        """Extract claims using OpenAI GPT"""
        try:
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
                                "content": f"Extract atomic factual claims from this content:\n\n{content}"
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
                
                # Convert to format expected by pipeline
                claims = [
                    {
                        "text": claim.text,
                        "position": i,
                        "confidence": claim.confidence,
                        "category": claim.category
                    }
                    for i, claim in enumerate(validated_response.claims)
                ]

                # Post-processing: temporal analysis and classification (Phase 1.5+2)
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
    
    async def _extract_with_anthropic(self, content: str) -> Dict[str, Any]:
        """Extract claims using Anthropic Claude"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": self.anthropic_api_key,
                        "Content-Type": "application/json",
                        "anthropic-version": "2023-06-01"
                    },
                    json={
                        "model": "claude-3-haiku-20240307",
                        "max_tokens": 1500,
                        "system": self.system_prompt.format(max_claims=self.max_claims),
                        "messages": [
                            {
                                "role": "user",
                                "content": f"Extract atomic factual claims from this content and return valid JSON:\n\n{content}"
                            }
                        ]
                    }
                )
                
                if response.status_code != 200:
                    error_msg = f"Anthropic API error: {response.status_code}"
                    logger.error(error_msg)
                    return {"success": False, "error": error_msg}
                
                result = response.json()
                content_text = result["content"][0]["text"]
                
                # Extract JSON from response (Claude sometimes wraps in markdown)
                json_start = content_text.find('{')
                json_end = content_text.rfind('}') + 1
                if json_start >= 0 and json_end > json_start:
                    json_content = content_text[json_start:json_end]
                else:
                    json_content = content_text
                
                claims_data = json.loads(json_content)
                validated_response = ClaimExtractionResponse(**claims_data)
                
                claims = [
                    {
                        "text": claim.text,
                        "position": i,
                        "confidence": claim.confidence,
                        "category": claim.category
                    }
                    for i, claim in enumerate(validated_response.claims)
                ]
                
                return {
                    "success": True,
                    "claims": claims,
                    "metadata": {
                        "extraction_method": "anthropic_claude3_haiku",
                        "source_summary": validated_response.source_summary,
                        "extraction_confidence": validated_response.extraction_confidence,
                        "token_usage": result.get("usage", {})
                    }
                }
                
        except httpx.TimeoutException:
            return {"success": False, "error": "Anthropic API timeout"}
        except ValidationError as e:
            logger.error(f"Anthropic response validation error: {e}")
            return {"success": False, "error": "Invalid response format from Anthropic"}
        except Exception as e:
            logger.error(f"Anthropic extraction error: {e}")
            return {"success": False, "error": str(e)}
    
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