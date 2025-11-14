import logging
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import json
import httpx
from app.core.config import settings
from app.services.cache import get_cache_service
from app.pipeline.extract import ClaimExtractor  # Reuse LLM infrastructure

logger = logging.getLogger(__name__)

class JudgmentResult:
    """Result of claim judgment with verdict and rationale"""
    
    def __init__(self, claim_text: str, verdict: str, confidence: float, rationale: str, 
                 supporting_evidence: List[Dict[str, Any]], evidence_summary: Dict[str, Any]):
        self.claim_text = claim_text
        self.verdict = verdict  # 'supported', 'contradicted', 'uncertain'
        self.confidence = confidence  # 0-100
        self.rationale = rationale
        self.supporting_evidence = supporting_evidence
        self.evidence_summary = evidence_summary
        self.created_at = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.claim_text,
            "verdict": self.verdict,
            "confidence": self.confidence,
            "rationale": self.rationale,
            "evidence": self.supporting_evidence,
            "evidence_summary": self.evidence_summary,
            "timestamp": self.created_at.isoformat()
        }

class ClaimJudge:
    """LLM-powered claim judge that makes final verdicts based on verification signals"""
    
    def __init__(self):
        self.openai_api_key = settings.OPENAI_API_KEY
        self.anthropic_api_key = getattr(settings, 'ANTHROPIC_API_KEY', '')
        self.judge_max_tokens = getattr(settings, 'JUDGE_MAX_TOKENS', 1000)
        self.temperature = getattr(settings, 'JUDGE_TEMPERATURE', 0.3)
        self.timeout = 30
        self.cache_service = None
        
        # Judge system prompt optimized for final verdicts
        self.system_prompt = """You are an expert fact-checker making final verdicts on claims based on evidence analysis.

TASK: Analyze verification signals and evidence to determine final verdict and explanation.

VERDICTS:
- "supported": Strong evidence supports the claim
- "contradicted": Strong evidence contradicts the claim
- "uncertain": Insufficient or conflicting evidence

ANALYSIS FRAMEWORK:
1. Evidence Quality: Assess source credibility, recency, relevance
2. Signal Strength: Weight entailment/contradiction scores
3. Consensus: Look for agreement across multiple sources
4. Context & Numerical Precision: Consider nuances, qualifications, temporal factors, and apply appropriate numerical tolerance:

   APPLY TOLERANCE (±15-20%) when the claim text contains approximation language:
   - Approximate words: "roughly", "approximately", "around", "about", "~", "nearly", "close to"
   - Magnitude phrases: "hundreds of", "thousands of", "millions in", "billions of"
   - Ranges: "between X and Y", "X to Y", "X-Y"
   - Estimates: "estimated", "projected", "expected", "forecasted"
   - Comparative: "more than", "over", "under", "at least", "up to"

   REQUIRE EXACT PRECISION when the claim text contains precision indicators:
   - Exactness: "exactly", "precisely", "specifically", "the exact figure"
   - Legal/Official: "allocated", "mandated", "authorized by law", "statute requires", "enacted"
   - Records: "highest ever", "first time", "record-breaking", "maximum", "minimum"
   - Contractual: "agreed to", "signed for", "contract states"

   EXAMPLES:
   ✓ Claim "roughly $350 million" + Evidence "$300M" or "$400M" = SUPPORTING (tolerance applies)
   ✗ Claim "exactly $350 million mandated" + Evidence "$300M" = CONTRADICTING (precision required)
   ✓ Claim "about 85% support" + Evidence "82-87% support" = SUPPORTING (tolerance applies)
   ✗ Claim "over 50 people attended" + Evidence "48 people" = CONTRADICTING (48 is not over 50)

   If no qualifier present, use DEFAULT tolerance (±10%) for minor discrepancies

CRITICAL - Do NOT Add Qualifiers or Over-Interpret:
- Judge ONLY what the claim EXPLICITLY states - do not infer additional meaning
- If claim says "exempts from provisions", do NOT interpret as "all provisions" or "certain provisions"
- If claim says "exempts the White House", do NOT add qualifiers like "completely" or "partially"
- If claim states a fact without qualifiers, do NOT assume universal or limited scope
- Do NOT infer semantic qualifiers (all, some, certain, most, few, many) unless EXPLICITLY present
- Do NOT add temporal qualifiers (always, never, sometimes, often, rarely) unless stated
- Do NOT add scope qualifiers (everywhere, nowhere, somewhere, completely, partially) unless stated

EXAMPLES OF OVER-INFERENCE TO AVOID:
❌ Claim: "The act exempts the White House from its provisions"
   Judge reads: "exempts from ALL provisions"
   Evidence: "White House is exempt from Section 106"
   Wrong conclusion: CONTRADICTED (because "all" ≠ "certain")
   → ERROR: The claim NEVER said "all provisions"!

✓  Claim: "The act exempts the White House from its provisions"
   Evidence: "White House is exempt from Section 106"
   Correct conclusion: SUPPORTED (exemption confirmed, scope not specified in claim)

❌ Claim: "Project costs $350 million"
   Judge reads: "costs exactly $350 million"
   Evidence: "$320 million"
   → ERROR: No exactness qualifier present, should apply default ±10% tolerance

✓  Claim: "Project costs $350 million"
   Evidence: "$320 million"
   Correct conclusion: SUPPORTED ($320M is within ±10% tolerance of $350M)

IMPORTANT - Handling Fact-Check Articles:
- If evidence is from fact-checking sites (Snopes, FactCheck.org, etc.), recognize these are META-CLAIMS
- A fact-check article saying "FALSE - claim X is debunked" means the OPPOSITE claim is supported
- Focus on PRIMARY sources (scientific studies, government data, news reports) over fact-check meta-content
- Do not be confused by double negatives in fact-check headlines

CRITICAL - Detecting Off-Topic/Irrelevant Evidence:
- Before marking evidence as CONTRADICTING, verify it actually ADDRESSES the claim
- Evidence about a DIFFERENT ASPECT of the topic is IRRELEVANT, not contradicting
- Only mark as CONTRADICTING if evidence DIRECTLY DISPROVES the claim's core assertion
- Examples of IRRELEVANT (not contradicting) evidence:
  ❌ Claim: "Person A sent a letter requesting documentation" + Evidence: "The letter doesn't require approval" → DIFFERENT TOPICS (action vs requirements)
  ❌ Claim: "Event costs $500M" + Evidence: "Event is funded by private donations" → DIFFERENT ASPECTS (cost vs funding source)
  ❌ Claim: "Building demolition began in June" + Evidence: "Building is exempt from review" → DIFFERENT TOPICS (timing vs legal status)
  ✓  Claim: "Person A sent a letter" + Evidence: "No letter was ever sent by Person A" → DIRECT CONTRADICTION
  ✓  Claim: "Event costs $500M" + Evidence: "Event actually costs $300M" → DIRECT CONTRADICTION

- When evidence is OFF-TOPIC or discusses unrelated aspects, treat as NEUTRAL/INSUFFICIENT
- Do NOT infer logical connections between unrelated facts
- Absence of requirement ≠ Absence of action
- Legal exemption ≠ Action didn't happen
- Funding source ≠ Cost amount

CRITICAL - Logical Fallacies to Avoid:
- Do NOT infer: "Action X doesn't require approval → Therefore action X didn't happen"
- Do NOT infer: "Project funded privately → Therefore no oversight requests were made"
- Do NOT infer: "Law exempts building → Therefore no agencies were consulted"
- Do NOT infer: "Process doesn't need documentation → Therefore no documentation was requested"

RESPONSE FORMAT: Respond with a valid JSON object containing:
{
  "verdict": "supported|contradicted|uncertain",
  "confidence": 85,
  "rationale": "Clear explanation of reasoning based on evidence analysis",
  "key_evidence_points": ["point 1", "point 2", "point 3"],
  "certainty_factors": {
    "source_quality": "high|medium|low",
    "evidence_consensus": "strong|mixed|weak",
    "temporal_relevance": "current|recent|outdated"
  }
}

Be precise, objective, and transparent about uncertainty. Always return valid JSON."""

    async def initialize(self):
        """Initialize judge service"""
        if self.cache_service is None:
            self.cache_service = await get_cache_service()
    
    async def judge_claim(self, claim: Dict[str, Any], verification_signals: Dict[str, Any],
                         evidence: List[Dict[str, Any]]) -> JudgmentResult:
        """Judge a single claim based on verification signals and evidence"""
        await self.initialize()

        claim_text = claim.get("text", "")

        # Check cache first
        cache_key = self._make_judgment_cache_key(claim_text, verification_signals, evidence)
        if self.cache_service:
            cached_result = await self.cache_service.get("judgment", cache_key)
            if cached_result:
                return self._result_from_dict(cached_result)

        # PHASE 3: Check for abstention BEFORE making a judgment
        if settings.ENABLE_ABSTENTION_LOGIC:
            abstention_check = self._should_abstain(evidence, verification_signals)
            if abstention_check:
                verdict, reason, consensus_strength = abstention_check
                logger.info(f"Abstaining from verdict: {verdict} - {reason}")

                # Return abstention result
                return JudgmentResult(
                    claim_text=claim_text,
                    verdict=verdict,
                    confidence=0.0,  # No confidence when abstaining
                    rationale=reason,
                    supporting_evidence=evidence[:3],
                    evidence_summary={
                        **verification_signals,
                        'abstention_reason': reason,
                        'min_requirements_met': False,
                        'consensus_strength': consensus_strength
                    }
                )

        # Prepare judgment context
        context = self._prepare_judgment_context(claim, verification_signals, evidence)

        # Get LLM judgment
        try:
            if self.openai_api_key:
                judgment_data = await self._judge_with_openai(context)
            elif self.anthropic_api_key:
                judgment_data = await self._judge_with_anthropic(context)
            else:
                # Fallback to rule-based judgment
                judgment_data = self._fallback_judgment(verification_signals)
            
            # Create result
            # Phase 3: Enrich evidence summary with consensus data
            enriched_summary = {
                **verification_signals,
                'min_requirements_met': True,
                'consensus_strength': self._calculate_consensus_strength(evidence, verification_signals) if settings.ENABLE_ABSTENTION_LOGIC else None,
                'abstention_reason': None
            }

            result = JudgmentResult(
                claim_text=claim_text,
                verdict=judgment_data.get("verdict", "uncertain"),
                confidence=min(max(judgment_data.get("confidence", 50), 0), 100),
                rationale=judgment_data.get("rationale", "Assessment based on available evidence"),
                supporting_evidence=evidence[:3],  # Top 3 evidence pieces
                evidence_summary=enriched_summary
            )
            
            # Cache result
            if self.cache_service:
                await self.cache_service.set(
                    "judgment",
                    cache_key,
                    result.to_dict(),
                    3600 * 6  # 6 hours
                )
            
            return result
            
        except Exception as e:
            logger.error(f"LLM judgment failed for claim: {e}")
            # Return fallback judgment
            fallback_data = self._fallback_judgment(verification_signals)
            return JudgmentResult(
                claim_text=claim_text,
                verdict=fallback_data["verdict"],
                confidence=fallback_data["confidence"],
                rationale=fallback_data["rationale"],
                supporting_evidence=evidence[:3],
                evidence_summary=verification_signals
            )

    def _get_few_shot_examples(self) -> str:
        """
        Return few-shot examples for judge prompt (Phase 1.2).
        Covers: clean support, contradiction, abstention (insufficient), numerical tolerance.
        """
        return """
=== EXAMPLE 1: Clean Support Case ===

CLAIM: "NASA's Perseverance rover landed on Mars on February 18, 2021"

EVIDENCE:
[1] "NASA confirmed successful touchdown at 3:55 PM EST on Feb 18, 2021"
    Source: nasa.gov, Credibility: 0.95, Published: 2021-02-18
[2] "Perseverance Mars landing confirmed by mission control"
    Source: Reuters, Credibility: 0.90, Published: 2021-02-18

VERDICT: supported
CONFIDENCE: 95
RATIONALE: Multiple high-credibility sources (NASA official + Reuters) confirm exact date. No contradicting evidence. Clean consensus.

---

=== EXAMPLE 2: Contradiction with Conflicting Snippets ===

CLAIM: "The conference had exactly 500 attendees"

EVIDENCE:
[1] "Conference organizers report 487 registered participants"
    Source: Conference Official Site, Credibility: 0.90, Published: 2024-10-15
[2] "Attendance estimated at 480-490 based on venue capacity"
    Source: Industry Journal, Credibility: 0.75, Published: 2024-10-16

VERDICT: contradicted
CONFIDENCE: 80
RATIONALE: Claim states "exactly 500" requiring precision. High-quality official source reports 487. Second source estimates 480-490. Both contradict the exact figure. Clear mismatch.

---

=== EXAMPLE 3: Abstention - Insufficient Evidence ===

CLAIM: "Startup SecureChain raised $50 million in Series B funding"

EVIDENCE:
[1] "SecureChain rumored to close funding round"
    Source: startup-rumors-blog.com, Credibility: 0.45, Published: 2024-11-01
[2] "Sources suggest blockchain company raising capital"
    Source: crypto-news-aggregator.net, Credibility: 0.50, Published: 2024-11-02

VERDICT: insufficient_evidence
CONFIDENCE: 0
RATIONALE: Only low-credibility sources (blog rumors, aggregator). No authoritative sources (company announcement, financial press, SEC filing). Cannot verify funding claim. Abstaining is appropriate.

---

=== EXAMPLE 4: Numerical Tolerance ===

CLAIM: "The infrastructure project received roughly $350 million in federal funding"

EVIDENCE:
[1] "Department of Transportation allocated $320 million to highway expansion"
    Source: dot.gov, Credibility: 0.95, Published: 2023-06-10
[2] "Federal infrastructure grants totaled $350M for state projects"
    Source: Reuters, Credibility: 0.90, Published: 2023-06-12

VERDICT: supported
CONFIDENCE: 85
RATIONALE: Claim uses "roughly" indicating approximation. Evidence shows $320M (official gov source) and $350M (news source). Within reasonable tolerance for approximate language. High-credibility sources support the claim.

---

NOW JUDGE THE FOLLOWING CLAIM:

"""

    def _prepare_judgment_context(self, claim: Dict[str, Any], verification_signals: Dict[str, Any],
                                 evidence: List[Dict[str, Any]]) -> str:
        """Prepare context for LLM judgment (Phase 1.2: with optional few-shot examples)"""
        claim_text = claim.get("text", "")

        # Evidence summary
        evidence_summary = []
        for i, ev in enumerate(evidence[:5]):  # Top 5 pieces
            source = ev.get("source", "Unknown")
            # Use configurable snippet length (increased from 150 to 400 to preserve context)
            snippet = ev.get("snippet", ev.get("text", ""))[:settings.EVIDENCE_SNIPPET_LENGTH]
            url = ev.get("url", "")
            date = ev.get("published_date", "")

            evidence_summary.append(
                f"Evidence {i+1}:\n"
                f"Source: {source}\n"
                f"Date: {date}\n"
                f"Content: {snippet}...\n"
                f"URL: {url}\n"
            )

        # Verification signals summary
        signals = verification_signals

        base_context = f"""
CLAIM TO JUDGE:
{claim_text}

EVIDENCE ANALYSIS:
Total Evidence Pieces: {signals.get('total_evidence', 0)}
Supporting Evidence: {signals.get('supporting_count', 0)} pieces
Contradicting Evidence: {signals.get('contradicting_count', 0)} pieces
Neutral Evidence: {signals.get('neutral_count', 0)} pieces

VERIFICATION METRICS:
Overall Verdict Signal: {signals.get('overall_verdict', 'uncertain')}
Signal Confidence: {signals.get('confidence', 0.0):.2f}
Max Entailment Score: {signals.get('max_entailment', 0.0):.2f}
Max Contradiction Score: {signals.get('max_contradiction', 0.0):.2f}
Evidence Quality: {signals.get('evidence_quality', 'low')}

EVIDENCE DETAILS:
{chr(10).join(evidence_summary)}

Based on this analysis, provide your final judgment."""

        # Phase 1.2: Prepend few-shot examples if enabled
        if settings.ENABLE_JUDGE_FEW_SHOT:
            few_shot_examples = self._get_few_shot_examples()
            return f"{few_shot_examples}\n{base_context}"

        return base_context
    
    async def _judge_with_openai(self, context: str) -> Dict[str, Any]:
        """Make judgment using OpenAI API"""
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
                            {"role": "system", "content": self.system_prompt},
                            {"role": "user", "content": context}
                        ],
                        "max_tokens": self.judge_max_tokens,
                        "temperature": self.temperature,
                        "response_format": {"type": "json_object"}
                    }
                )
                
                if response.status_code == 200:
                    result = response.json()
                    content = result["choices"][0]["message"]["content"]
                    return json.loads(content)
                else:
                    logger.error(f"OpenAI API error: {response.status_code} - {response.text}")
                    raise Exception(f"OpenAI API error: {response.status_code}")
                    
        except Exception as e:
            logger.error(f"OpenAI judgment error: {e}")
            raise
    
    async def _judge_with_anthropic(self, context: str) -> Dict[str, Any]:
        """Make judgment using Anthropic API"""
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
                        "max_tokens": self.judge_max_tokens,
                        "temperature": self.temperature,
                        "messages": [
                            {
                                "role": "user", 
                                "content": f"{self.system_prompt}\n\n{context}\n\nProvide your judgment as JSON."
                            }
                        ]
                    }
                )
                
                if response.status_code == 200:
                    result = response.json()
                    content = result["content"][0]["text"]
                    # Extract JSON from response
                    json_start = content.find('{')
                    json_end = content.rfind('}') + 1
                    if json_start >= 0 and json_end > json_start:
                        json_content = content[json_start:json_end]
                        return json.loads(json_content)
                    else:
                        raise Exception("No JSON found in Anthropic response")
                else:
                    logger.error(f"Anthropic API error: {response.status_code} - {response.text}")
                    raise Exception(f"Anthropic API error: {response.status_code}")
                    
        except Exception as e:
            logger.error(f"Anthropic judgment error: {e}")
            raise
    
    def _fallback_judgment(self, verification_signals: Dict[str, Any]) -> Dict[str, Any]:
        """Rule-based fallback judgment when LLM is unavailable"""
        signals = verification_signals
        
        supporting = signals.get('supporting_count', 0)
        contradicting = signals.get('contradicting_count', 0)
        total = signals.get('total_evidence', 0)
        max_entailment = signals.get('max_entailment', 0.0)
        max_contradiction = signals.get('max_contradiction', 0.0)
        quality = signals.get('evidence_quality', 'low')
        
        # Rule-based verdict
        if supporting > contradicting and max_entailment > 0.75 and quality in ['high', 'medium']:
            verdict = "supported"
            confidence = min(80, int(max_entailment * 85))
            rationale = f"Evidence analysis shows {supporting} supporting sources with high confidence scores. The strongest supporting evidence has {max_entailment:.2f} entailment score."
        elif contradicting > supporting and max_contradiction > 0.75 and quality in ['high', 'medium']:
            verdict = "contradicted"
            confidence = min(80, int(max_contradiction * 85))
            rationale = f"Evidence analysis shows {contradicting} contradicting sources with high confidence scores. The strongest contradicting evidence has {max_contradiction:.2f} contradiction score."
        else:
            verdict = "uncertain"
            confidence = 40
            rationale = f"Evidence analysis is inconclusive. Found {supporting} supporting and {contradicting} contradicting sources with mixed confidence levels."
        
        return {
            "verdict": verdict,
            "confidence": confidence,
            "rationale": rationale,
            "key_evidence_points": [
                f"Analyzed {total} evidence sources",
                f"Evidence quality rated as {quality}",
                f"Verification confidence: {signals.get('confidence', 0.0):.2f}"
            ],
            "certainty_factors": {
                "source_quality": quality,
                "evidence_consensus": "strong" if abs(supporting - contradicting) >= 2 else "mixed",
                "temporal_relevance": "current"
            }
        }

    def _should_abstain(self, evidence: List[Dict[str, Any]], verification_signals: Dict[str, Any]) -> Optional[tuple]:
        """
        Determine if we should abstain from making a verdict.

        Phase 3 - Week 8: Consensus & Abstention Logic
        Never force a verdict when evidence is weak or conflicting.

        Returns:
            Tuple[verdict, reason, consensus_strength] if should abstain, None otherwise
        """
        # Configuration thresholds
        MIN_SOURCES = settings.MIN_SOURCES_FOR_VERDICT  # Default: 3
        MIN_HIGH_CRED = settings.MIN_CREDIBILITY_THRESHOLD  # Default: 0.75
        MIN_CONSENSUS = settings.MIN_CONSENSUS_STRENGTH  # Default: 0.65

        # Check 1: Too few sources
        if len(evidence) < MIN_SOURCES:
            return (
                "insufficient_evidence",
                f"Only {len(evidence)} source(s) found. Need at least {MIN_SOURCES} for reliable verdict.",
                0.0
            )

        # Check 2: No authoritative sources
        high_cred_sources = [e for e in evidence if e.get('credibility_score', 0.6) >= MIN_HIGH_CRED]
        if len(high_cred_sources) < 1:
            max_cred = max([e.get('credibility_score', 0) for e in evidence]) if evidence else 0
            return (
                "insufficient_evidence",
                f"No high-credibility sources (≥{MIN_HIGH_CRED:.0%}). "
                f"Highest credibility: {max_cred:.0%}. Need authoritative sources for verdict.",
                0.0
            )

        # Check 3: Calculate consensus strength
        consensus_strength = self._calculate_consensus_strength(evidence, verification_signals)
        if consensus_strength < MIN_CONSENSUS:
            return (
                "conflicting_expert_opinion",
                f"Evidence shows weak consensus ({consensus_strength:.0%}). "
                f"High-credibility sources disagree on this claim.",
                consensus_strength
            )

        # Check 4: Conflicting high-credibility sources
        supporting = verification_signals.get('supporting_count', 0)
        contradicting = verification_signals.get('contradicting_count', 0)

        high_cred_supporting = sum(1 for e in high_cred_sources
                                   if verification_signals.get(f"evidence_{e.get('id', '')}_stance") == 'supporting')
        high_cred_contradicting = sum(1 for e in high_cred_sources
                                      if verification_signals.get(f"evidence_{e.get('id', '')}_stance") == 'contradicting')

        # CRITICAL FIX: Only abstain if contradictions are STRONG and NUMEROUS
        # Don't abstain on 1 false contradiction - require at least 2 contradicting sources
        # AND contradictions must be equal to or outnumber supporting sources
        if high_cred_contradicting >= 2 and high_cred_contradicting >= high_cred_supporting:
            return (
                "conflicting_expert_opinion",
                f"High-credibility sources conflict: {high_cred_supporting} support, "
                f"{high_cred_contradicting} contradict. Expert opinion divided.",
                consensus_strength
            )

        # Check 5: Temporal issues (if temporal markers present)
        if verification_signals.get('temporal_flag') == 'outdated':
            return (
                "outdated_claim",
                "Claim may have been accurate historically, but circumstances have changed. "
                "Evidence suggests this is no longer current.",
                consensus_strength
            )

        # No abstention needed - minimum requirements met
        return None

    def _calculate_consensus_strength(self, evidence: List[Dict[str, Any]],
                                     verification_signals: Dict[str, Any]) -> float:
        """
        Calculate consensus strength using credibility-weighted agreement.

        Neutral stances are counted as weak support (40% weight) to avoid
        falsely flagging tangentially-related evidence as "conflicting opinion".

        Returns:
            Float 0-1 representing strength of consensus
        """
        if not evidence:
            return 0.0

        # Weight for neutral evidence (weak support, not disagreement)
        NEUTRAL_SUPPORT_WEIGHT = 0.4

        # Weight votes by credibility score
        supporting_weight = 0.0
        contradicting_weight = 0.0

        for ev in evidence:
            cred_score = ev.get('credibility_score', 0.6)
            ev_id = ev.get('id', '')

            # Get stance from verification signals (None if missing)
            stance = verification_signals.get(f'evidence_{ev_id}_stance')

            if stance == 'supporting':
                supporting_weight += cred_score
            elif stance == 'contradicting':
                contradicting_weight += cred_score
            elif stance == 'neutral':
                # Neutral evidence that discusses topic = weak support
                supporting_weight += cred_score * NEUTRAL_SUPPORT_WEIGHT

        total_weight = supporting_weight + contradicting_weight

        if total_weight == 0:
            return 0.0

        # Consensus = majority weight / total weight
        majority_weight = max(supporting_weight, contradicting_weight)
        consensus = majority_weight / total_weight

        return consensus

    def _make_judgment_cache_key(self, claim: str, signals: Dict[str, Any], evidence: List[Dict[str, Any]]) -> str:
        """Create cache key for judgment result"""
        # Include key signal values and evidence URLs for cache invalidation
        key_data = {
            "claim": claim[:100],  # First 100 chars
            "verdict_signal": signals.get("overall_verdict"),
            "confidence": round(signals.get("confidence", 0.0), 2),
            "evidence_count": len(evidence),
            "evidence_urls": [ev.get("url", "")[:50] for ev in evidence[:3]]
        }
        content = json.dumps(key_data, sort_keys=True)
        import hashlib
        return hashlib.md5(content.encode()).hexdigest()
    
    def _result_from_dict(self, data: Dict[str, Any]) -> JudgmentResult:
        """Create JudgmentResult from cached dictionary"""
        return JudgmentResult(
            claim_text=data["text"],
            verdict=data["verdict"],
            confidence=data["confidence"],
            rationale=data["rationale"],
            supporting_evidence=data.get("evidence", []),
            evidence_summary=data.get("evidence_summary", {})
        )

class PipelineJudge:
    """High-level judge service for the entire pipeline"""
    
    def __init__(self):
        self.claim_judge = ClaimJudge()
        self.max_concurrent_judgments = 3  # Conservative for LLM calls
    
    async def judge_all_claims(self, claims: List[Dict[str, Any]], 
                              verifications_by_claim: Dict[str, List[Dict[str, Any]]], 
                              evidence_by_claim: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        """Judge all claims and return final results"""
        try:
            await self.claim_judge.initialize()
            
            # Import verification aggregation from verify module
            from app.pipeline.verify import get_claim_verifier
            claim_verifier = await get_claim_verifier()
            
            # Create judgment tasks with concurrency control
            semaphore = asyncio.Semaphore(self.max_concurrent_judgments)
            
            async def judge_single_claim(claim: Dict[str, Any]) -> Dict[str, Any]:
                async with semaphore:
                    position = str(claim.get("position", 0))
                    verifications = verifications_by_claim.get(position, [])
                    evidence = evidence_by_claim.get(position, [])

                    # Phase 2: Enrich evidence with NLI verification data (Section 2.6a)
                    enriched_evidence = []
                    for i, ev in enumerate(evidence):
                        ev_copy = ev.copy()  # Don't mutate original

                        # Attach NLI data if verification exists for this evidence
                        if i < len(verifications):
                            verification = verifications[i]
                            relationship = verification.get("relationship", "neutral")

                            # Map NLI relationship to user-friendly stance
                            ev_copy["nli_stance"] = (
                                "supporting" if relationship == "entails" else
                                "contradicting" if relationship == "contradicts" else
                                "neutral"
                            )
                            ev_copy["nli_confidence"] = verification.get("confidence", 0.0)
                            ev_copy["nli_entailment"] = verification.get("entailment_score", 0.0)
                            ev_copy["nli_contradiction"] = verification.get("contradiction_score", 0.0)

                        enriched_evidence.append(ev_copy)

                    # Aggregate verification signals
                    signals = claim_verifier.aggregate_verification_signals(verifications)

                    # Get final judgment with ENRICHED evidence (now has NLI fields)
                    judgment = await self.claim_judge.judge_claim(claim, signals, enriched_evidence)

                    return {
                        **judgment.to_dict(),
                        "position": claim.get("position", 0),
                        "verification_signals": signals
                    }
            
            # Run judgments with controlled concurrency
            tasks = [judge_single_claim(claim) for claim in claims]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Handle any failures
            final_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Judgment failed for claim {i}: {result}")
                    # Create fallback result
                    claim = claims[i]
                    position = str(claim.get("position", i))
                    evidence = evidence_by_claim.get(position, [])
                    
                    fallback_result = {
                        "text": claim.get("text", ""),
                        "verdict": "uncertain",
                        "confidence": 30,
                        "rationale": "Judgment failed due to processing error. Evidence review inconclusive.",
                        "evidence": evidence[:3],
                        "position": claim.get("position", i),
                        "verification_signals": {"error": "judgment_failed"}
                    }
                    final_results.append(fallback_result)
                else:
                    final_results.append(result)
            
            return final_results
            
        except Exception as e:
            logger.error(f"Pipeline judgment error: {e}")
            # Return fallback results for all claims
            fallback_results = []
            for i, claim in enumerate(claims):
                position = str(claim.get("position", i))
                evidence = evidence_by_claim.get(position, [])
                
                fallback_results.append({
                    "text": claim.get("text", ""),
                    "verdict": "uncertain", 
                    "confidence": 25,
                    "rationale": "Pipeline judgment service temporarily unavailable. Manual review recommended.",
                    "evidence": evidence[:3],
                    "position": claim.get("position", i),
                    "verification_signals": {"error": "pipeline_error"}
                })
            
            return fallback_results

# Singleton instance
_pipeline_judge = None

async def get_pipeline_judge() -> PipelineJudge:
    """Get singleton pipeline judge instance"""
    global _pipeline_judge
    if _pipeline_judge is None:
        _pipeline_judge = PipelineJudge()
    return _pipeline_judge