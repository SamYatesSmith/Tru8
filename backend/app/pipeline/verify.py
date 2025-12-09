import logging
import asyncio
from typing import List, Dict, Any, Optional, Tuple
import hashlib
import json
from app.core.config import settings
from app.services.cache import get_cache_service

# Note: transformers and torch imports moved inside functions to prevent
# 400MB+ memory consumption at startup. They will only load when NLI verification is actually used.

logger = logging.getLogger(__name__)

# MODULE LOAD DIAGNOSTIC: This will print when the module is imported
print("=" * 80)
print("VERIFY.PY MODULE LOADED - Checking NLI label mapping configuration")
print(f"   Timestamp: {__import__('datetime').datetime.now()}")
print(f"   Expected label order: {{0: 'entailment', 1: 'neutral', 2: 'contradiction'}}")
print("=" * 80)

class NLIVerificationResult:
    """Result of NLI verification for a claim-evidence pair"""
    
    def __init__(self, claim_text: str, evidence_text: str,
                 entailment_score: float, contradiction_score: float, neutral_score: float):
        self.claim_text = claim_text
        self.evidence_text = evidence_text
        self.entailment_score = entailment_score
        self.contradiction_score = contradiction_score
        self.neutral_score = neutral_score
        self.confidence = max(entailment_score, contradiction_score, neutral_score)

        # INTERNATIONAL CONTENT FIX: Adjust thresholds for paraphrasing tolerance
        # If contradiction is very low (< 0.3), evidence at minimum isn't contradicting
        # This helps with international content where paraphrasing is common
        # Example: "under fire for comments" vs "made disparaging remarks" should match
        LOW_CONTRADICTION_THRESHOLD = 0.3
        NEUTRAL_THRESHOLD = 0.7

        if neutral_score > NEUTRAL_THRESHOLD and contradiction_score >= LOW_CONTRADICTION_THRESHOLD:
            # High neutral AND meaningful contradiction → evidence is off-topic
            self.relationship = "neutral"
        elif contradiction_score < LOW_CONTRADICTION_THRESHOLD and neutral_score > entailment_score:
            # Low contradiction + neutral likely means paraphrasing → treat as weak support
            self.relationship = "entails"
        elif entailment_score > contradiction_score and entailment_score > neutral_score:
            self.relationship = "entails"
        elif contradiction_score > entailment_score and contradiction_score > neutral_score:
            self.relationship = "contradicts"
        else:
            self.relationship = "neutral"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "relationship": self.relationship,
            "confidence": self.confidence,
            "entailment_score": self.entailment_score,
            "contradiction_score": self.contradiction_score,
            "neutral_score": self.neutral_score,
            "evidence_snippet": self.evidence_text[:400] + "..." if len(self.evidence_text) > 400 else self.evidence_text
        }

class NLIVerifier:
    """Natural Language Inference verifier for claim-evidence pairs"""

    # Cache version - increment when NLI or search logic changes to invalidate old cache
    CACHE_VERSION = "v3_rate_limited_search"

    def __init__(self):
        self.model = None
        self.tokenizer = None
        self.model_name = settings.nli_model_name  # Dynamic based on ENABLE_DEBERTA_NLI flag
        self.max_length = 512
        self.batch_size = 8
        self.confidence_threshold = getattr(settings, 'NLI_CONFIDENCE_THRESHOLD', 0.7)
        self.device = None  # Will be set when model is loaded
        self._lock = asyncio.Lock()
        self.cache_service = None

        logger.info(f"NLI Verifier initialized with model: {self.model_name} (will load on first use)")

    @property
    def nli_model(self):
        """Alias for self.model to support test mocking"""
        return self.model

    @nli_model.setter
    def nli_model(self, value):
        """Setter for nli_model alias"""
        self.model = value

    @nli_model.deleter
    def nli_model(self):
        """Deleter for nli_model alias"""
        self.model = None
    
    async def initialize(self):
        """Initialize the NLI model and tokenizer"""
        try:
            if self.model is None:
                async with self._lock:
                    if self.model is None:  # Double-check locking
                        logger.info(f"Loading NLI model: {self.model_name}")
                        
                        # Load in thread pool to avoid blocking
                        loop = asyncio.get_event_loop()
                        
                        def load_model():
                            # Import transformers only when actually needed
                            from transformers import AutoTokenizer, AutoModelForSequenceClassification
                            import torch

                            # Set device here when torch is available
                            device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

                            tokenizer = AutoTokenizer.from_pretrained(self.model_name)
                            # Load with FP16 on GPU for memory efficiency (Phase 1.1)
                            model = AutoModelForSequenceClassification.from_pretrained(
                                self.model_name,
                                dtype=torch.float16 if device.type == 'cuda' else torch.float32
                            )
                            model.to(device)
                            model.eval()
                            return tokenizer, model, device
                        
                        self.tokenizer, self.model, self.device = await loop.run_in_executor(None, load_model)
                        logger.info(f"NLI model loaded successfully on device: {self.device}")
            
            # Initialize cache service
            if self.cache_service is None:
                self.cache_service = await get_cache_service()
                
        except Exception as e:
            logger.error(f"Failed to initialize NLI verifier: {e}")
            raise

    async def verify_single(self, claim, evidence):
        """
        Helper method for testing: Verify a single claim against a single evidence

        Args:
            claim: Claim object with .text attribute
            evidence: Evidence object with .text attribute

        Returns:
            dict with stance, confidence, and scores
        """
        # Skip initialization if model is mocked (for testing)
        if self.model is None and hasattr(self, '_is_mocked'):
            # Use mocked inference directly
            claim_text = getattr(claim, 'text', str(claim))
            evidence_text = getattr(evidence, 'text', str(evidence))

            try:
                # Call mocked _run_inference
                scores = self._run_inference([evidence_text], [claim_text])
                entailment, contradiction, neutral = scores[0]

                # Determine stance
                if entailment > contradiction and entailment > neutral:
                    stance = "supports"
                    confidence = entailment
                elif contradiction > entailment and contradiction > neutral:
                    stance = "contradicts"
                    confidence = contradiction
                else:
                    stance = "neutral"
                    confidence = neutral

                # Mark as uncertain if confidence is low
                is_uncertain = (confidence < 0.60)

                return {
                    "stance": stance,
                    "confidence": confidence,
                    "is_uncertain": is_uncertain,
                    "scores": {
                        "entailment": entailment,
                        "neutral": neutral,
                        "contradiction": contradiction
                    }
                }
            except Exception as e:
                # Handle errors gracefully - return neutral with zero confidence
                logger.error(f"NLI verification error: {e}")
                return {
                    "stance": "neutral",
                    "confidence": 0.0,
                    "is_uncertain": True,
                    "scores": {
                        "entailment": 0.33,
                        "neutral": 0.34,
                        "contradiction": 0.33
                    }
                }

        # Convert claim and evidence objects to required format
        claim_text = getattr(claim, 'text', str(claim))
        evidence_text = getattr(evidence, 'text', str(evidence))

        # Call the main verification method
        evidence_dict = {"text": evidence_text}
        results = await self.verify_claim_against_evidence(claim_text, [evidence_dict])

        if not results:
            return {
                "stance": "NEUTRAL",
                "confidence": 0.0,
                "scores": {
                    "entailment": 0.33,
                    "neutral": 0.34,
                    "contradiction": 0.33
                }
            }

        # Convert result to test-expected format
        result = results[0]

        # Map relationship to stance label (lowercase to match StanceLabel enum)
        stance_map = {
            "entails": "supports",
            "contradicts": "contradicts",
            "neutral": "neutral"
        }
        stance = stance_map.get(result.relationship, "neutral")

        # Mark as uncertain if confidence is low
        is_uncertain = (result.confidence < 0.60)

        return {
            "stance": stance,
            "confidence": result.confidence,
            "is_uncertain": is_uncertain,
            "scores": {
                "entailment": result.entailment_score,
                "neutral": result.neutral_score,
                "contradiction": result.contradiction_score
            }
        }

    async def verify_multiple(self, claim, evidence_list):
        """
        Helper method for testing: Verify a claim against multiple evidence items

        Args:
            claim: Claim object with .text attribute
            evidence_list: List of Evidence objects

        Returns:
            dict with consensus_stance, confidence, and evidence counts
        """
        # Handle empty evidence list
        if not evidence_list:
            return {
                "consensus_stance": "insufficient_evidence",
                "confidence": 0.0,
                "support_count": 0,
                "contradict_count": 0,
                "neutral_count": 0,
                "has_conflicting_evidence": False,
                "weighted_support_score": 0.0,
                "weighted_contradict_score": 0.0,
                "individual_results": []
            }

        # Verify each evidence item
        results = []
        for evidence in evidence_list:
            result = await self.verify_single(claim, evidence)
            results.append(result)

        # Count stances
        support_count = sum(1 for r in results if r['stance'] == 'supports')
        contradict_count = sum(1 for r in results if r['stance'] == 'contradicts')
        neutral_count = sum(1 for r in results if r['stance'] == 'neutral')

        # Determine consensus
        if support_count > contradict_count and support_count > neutral_count:
            consensus_stance = 'supports'
            # Average confidence of supporting evidence
            supporting_confidences = [r['confidence'] for r in results if r['stance'] == 'supports']
            confidence = sum(supporting_confidences) / len(supporting_confidences) if supporting_confidences else 0.0
        elif contradict_count > support_count and contradict_count > neutral_count:
            consensus_stance = 'contradicts'
            contradicting_confidences = [r['confidence'] for r in results if r['stance'] == 'contradicts']
            confidence = sum(contradicting_confidences) / len(contradicting_confidences) if contradicting_confidences else 0.0
        else:
            consensus_stance = 'neutral'
            neutral_confidences = [r['confidence'] for r in results if r['stance'] == 'neutral']
            confidence = sum(neutral_confidences) / len(neutral_confidences) if neutral_confidences else 0.0

        # Detect conflicting evidence
        has_conflicting_evidence = (support_count > 0 and contradict_count > 0)

        # Calculate credibility-weighted scores (for testing)
        weighted_support_score = 0.0
        weighted_contradict_score = 0.0
        total_credibility = 0.0

        for i, result in enumerate(results):
            # Get credibility from original evidence list
            cred = getattr(evidence_list[i], 'credibility_score', 50) / 100.0  # normalize to 0-1
            total_credibility += cred

            if result['stance'] == 'supports':
                weighted_support_score += result['confidence'] * cred
            elif result['stance'] == 'contradicts':
                weighted_contradict_score += result['confidence'] * cred

        return {
            "consensus_stance": consensus_stance,
            "confidence": confidence,
            "support_count": support_count,
            "contradict_count": contradict_count,
            "neutral_count": neutral_count,
            "has_conflicting_evidence": has_conflicting_evidence,
            "weighted_support_score": weighted_support_score,
            "weighted_contradict_score": weighted_contradict_score,
            "individual_results": results
        }

    def _make_cache_key(self, claim: str, evidence: str) -> str:
        """Create cache key for claim-evidence pair with version"""
        # Include version to auto-invalidate cache when logic changes
        content = f"{self.CACHE_VERSION}|||{claim}|||{evidence}"
        return hashlib.md5(content.encode()).hexdigest()
    
    async def verify_claim_against_evidence(self, claim: str, evidence_list: List[Dict[str, Any]]) -> List[NLIVerificationResult]:
        """Verify a single claim against multiple evidence pieces"""
        await self.initialize()
        
        if not evidence_list:
            return []
        
        results = []
        cache_keys = []
        cached_results = []
        uncached_pairs = []
        
        # Check cache for each evidence piece
        for evidence in evidence_list:
            evidence_text = evidence.get("text", evidence.get("snippet", ""))
            cache_key = self._make_cache_key(claim, evidence_text)
            cache_keys.append(cache_key)
            
            if self.cache_service:
                cached = await self.cache_service.get("nli_verification", cache_key)
                if cached:
                    cached_results.append((len(uncached_pairs), cached))
                    continue
            
            uncached_pairs.append((claim, evidence_text, evidence))
        
        # Process uncached pairs in batches
        if uncached_pairs:
            batch_results = await self._batch_verify(uncached_pairs)
            
            # Cache new results
            for i, (claim_text, evidence_text, evidence) in enumerate(uncached_pairs):
                cache_key = self._make_cache_key(claim_text, evidence_text)
                result_dict = batch_results[i].to_dict()
                
                if self.cache_service:
                    await self.cache_service.set(
                        "nli_verification",
                        cache_key,
                        result_dict,
                        3600  # 1 hour cache for testing (was 24 hours)
                    )
                
                results.append(batch_results[i])
        
        # Add cached results back in order
        for original_pos, cached_result in cached_results:
            nli_result = NLIVerificationResult(
                claim_text=claim,
                evidence_text=cached_result["evidence_snippet"],
                entailment_score=cached_result["entailment_score"],
                contradiction_score=cached_result["contradiction_score"],
                neutral_score=cached_result["neutral_score"]
            )
            results.insert(original_pos, nli_result)
        
        return results
    
    async def _batch_verify(self, claim_evidence_pairs: List[Tuple[str, str, Dict]]) -> List[NLIVerificationResult]:
        """Verify multiple claim-evidence pairs in batches"""
        if not claim_evidence_pairs:
            return []
        
        all_results = []
        
        # Process in batches
        for i in range(0, len(claim_evidence_pairs), self.batch_size):
            batch = claim_evidence_pairs[i:i + self.batch_size]
            batch_results = await self._process_batch(batch)
            all_results.extend(batch_results)
        
        return all_results
    
    async def _process_batch(self, batch: List[Tuple[str, str, Dict]]) -> List[NLIVerificationResult]:
        """Process a single batch of claim-evidence pairs with relevance filtering"""
        try:
            from app.core.config import settings

            # NEW: Relevance gatekeeper - check semantic similarity before running NLI
            if settings.ENABLE_EVIDENCE_RELEVANCE_FILTER:
                from app.services.embeddings import get_embedding_service, calculate_semantic_similarity

                embedding_service = await get_embedding_service()
                results = []

                # Split batch into relevant and irrelevant
                relevant_pairs = []
                irrelevant_pairs = []

                for claim_text, evidence_text, evidence in batch:
                    # Calculate semantic similarity
                    relevance_score = await calculate_semantic_similarity(claim_text, evidence_text)

                    # Store relevance score in evidence metadata
                    if isinstance(evidence, dict):
                        evidence['relevance_score'] = relevance_score

                    # If evidence is OFF-TOPIC (low relevance), skip NLI and mark as neutral
                    if relevance_score < settings.RELEVANCE_THRESHOLD:
                        logger.info(f"Evidence OFF-TOPIC (relevance {relevance_score:.2f} < {settings.RELEVANCE_THRESHOLD}), skipping NLI")
                        # Mark as highly neutral (off-topic evidence is not supporting OR contradicting)
                        result = NLIVerificationResult(
                            claim_text=claim_text,
                            evidence_text=evidence_text,
                            entailment_score=0.05,  # Very low
                            contradiction_score=0.05,  # Very low
                            neutral_score=0.90  # High - evidence is irrelevant
                        )
                        irrelevant_pairs.append((claim_text, evidence_text, evidence, result))
                    else:
                        logger.debug(f"Evidence relevant (relevance {relevance_score:.2f}), running NLI")
                        relevant_pairs.append((claim_text, evidence_text, evidence))

                # Run NLI only on relevant evidence
                if relevant_pairs:
                    premises = [evidence_text for claim_text, evidence_text, _ in relevant_pairs]
                    hypotheses = [claim_text for claim_text, evidence_text, _ in relevant_pairs]

                    loop = asyncio.get_event_loop()
                    scores = await loop.run_in_executor(None, self._run_inference, premises, hypotheses)

                    # Convert NLI results
                    for i, (claim_text, evidence_text, evidence) in enumerate(relevant_pairs):
                        entailment, contradiction, neutral = scores[i]
                        result = NLIVerificationResult(
                            claim_text=claim_text,
                            evidence_text=evidence_text,
                            entailment_score=float(entailment),
                            contradiction_score=float(contradiction),
                            neutral_score=float(neutral)
                        )
                        results.append(result)

                # Add irrelevant results (already created above)
                results.extend([result for _, _, _, result in irrelevant_pairs])

                logger.info(f"Relevance filter: {len(relevant_pairs)} relevant, {len(irrelevant_pairs)} off-topic (skipped NLI)")
                return results

            # FALLBACK: If relevance filter disabled, run NLI on all evidence (old behavior)
            # Prepare inputs
            # CORRECT NLI CONVENTION: premise = evidence (the facts), hypothesis = claim (what we're testing)
            # This asks: "Given the EVIDENCE (premise), does the CLAIM (hypothesis) logically follow?"
            premises = [evidence_text for claim_text, evidence_text, _ in batch]
            hypotheses = [claim_text for claim_text, evidence_text, _ in batch]

            # Run inference in thread pool
            loop = asyncio.get_event_loop()
            scores = await loop.run_in_executor(None, self._run_inference, premises, hypotheses)

            # Convert to results
            results = []
            for i, (claim_text, evidence_text, evidence) in enumerate(batch):
                entailment, contradiction, neutral = scores[i]
                result = NLIVerificationResult(
                    claim_text=claim_text,
                    evidence_text=evidence_text,
                    entailment_score=float(entailment),
                    contradiction_score=float(contradiction),
                    neutral_score=float(neutral)
                )
                results.append(result)

            return results
            
        except Exception as e:
            logger.error(f"Batch NLI inference failed: {e}")
            # Return neutral results as fallback
            return [
                NLIVerificationResult(
                    claim_text=claim_text,
                    evidence_text=evidence_text,
                    entailment_score=0.33,
                    contradiction_score=0.33,
                    neutral_score=0.34
                )
                for claim_text, evidence_text, _ in batch
            ]
    
    def _run_inference(self, premises: List[str], hypotheses: List[str]) -> List[Tuple[float, float, float]]:
        """Run NLI inference on CPU/GPU"""
        try:
            # Import torch here to avoid startup overhead
            import torch

            # Tokenize inputs
            inputs = self.tokenizer(
                premises,
                hypotheses,
                truncation=True,
                padding=True,
                max_length=self.max_length,
                return_tensors="pt"
            )

            # Move to device
            inputs = {k: v.to(self.device) for k, v in inputs.items()}

            # Run inference
            with torch.no_grad():
                outputs = self.model(**inputs)
                probabilities = torch.softmax(outputs.logits, dim=-1)

            # DIAGNOSTIC: Print raw probabilities to verify correct loading
            logger.info(f"[NLI] RAW MODEL OUTPUT (first result): {probabilities[0].tolist() if len(probabilities) > 0 else 'empty'}")
            logger.info(f"   Model config: {self.model_name}")

            # Convert to list of tuples (entailment, contradiction, neutral)
            results = []
            for i in range(len(premises)):
                # DeBERTa model outputs: {0: 'entailment', 1: 'neutral', 2: 'contradiction'}
                entailment = probabilities[i][0].item()
                neutral = probabilities[i][1].item()
                contradiction = probabilities[i][2].item()
                results.append((entailment, contradiction, neutral))

                # DEBUG LOGGING: Show NLI scores for each verification
                logger.info(f"[NLI] SCORES - Premise (EVIDENCE): {premises[i][:80]}...")
                logger.info(f"   Hypothesis (CLAIM): {hypotheses[i][:80]}...")
                logger.info(f"   Entailment: {entailment:.3f}, Contradiction: {contradiction:.3f}, Neutral: {neutral:.3f}")
                logger.info(f"   → Relationship: {'ENTAILS' if entailment > max(contradiction, neutral) else 'CONTRADICTS' if contradiction > max(entailment, neutral) else 'NEUTRAL'}")

            return results
            
        except Exception as e:
            logger.error(f"NLI inference error: {e}")
            # Return neutral scores as fallback
            return [(0.33, 0.33, 0.34)] * len(premises)

class ClaimVerifier:
    """High-level claim verification service"""
    
    def __init__(self):
        self.nli_verifier = NLIVerifier()
        self.max_concurrent_claims = getattr(settings, 'MAX_CONCURRENT_VERIFICATIONS', 5)
    
    async def verify_claims_with_evidence(self, claims: List[Dict[str, Any]], 
                                        evidence_by_claim: Dict[str, List[Dict[str, Any]]]) -> Dict[str, List[Dict[str, Any]]]:
        """Verify multiple claims against their evidence concurrently"""
        try:
            await self.nli_verifier.initialize()
            
            # Create verification tasks with semaphore for concurrency control
            semaphore = asyncio.Semaphore(self.max_concurrent_claims)
            
            async def verify_single_claim(claim: Dict[str, Any]) -> Tuple[str, List[Dict[str, Any]]]:
                async with semaphore:
                    claim_text = claim.get("text", "")
                    position = str(claim.get("position", 0))
                    evidence_list = evidence_by_claim.get(position, [])
                    
                    if not evidence_list:
                        return position, []
                    
                    # Run NLI verification
                    nli_results = await self.nli_verifier.verify_claim_against_evidence(claim_text, evidence_list)
                    
                    # Convert to verification format
                    verifications = []
                    for i, nli_result in enumerate(nli_results):
                        if i < len(evidence_list):
                            evidence = evidence_list[i]
                            verification = {
                                "evidence_id": evidence.get("id", f"evidence_{i}"),
                                "relationship": nli_result.relationship,
                                "confidence": nli_result.confidence,
                                "entailment_score": nli_result.entailment_score,
                                "contradiction_score": nli_result.contradiction_score,
                                "neutral_score": nli_result.neutral_score,
                                "evidence": evidence
                            }
                            verifications.append(verification)
                    
                    return position, verifications
            
            # Run verifications concurrently
            tasks = [verify_single_claim(claim) for claim in claims]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Organize results
            verifications_by_claim = {}
            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"Claim verification failed: {result}")
                    continue
                
                position, verifications = result
                verifications_by_claim[position] = verifications
            
            return verifications_by_claim
            
        except Exception as e:
            logger.error(f"Claims verification error: {e}")
            return {}
    
    def aggregate_verification_signals(self, verifications: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Aggregate multiple NLI verification results into overall verdict signals"""
        if not verifications:
            return {
                "overall_verdict": "uncertain",
                "confidence": 0.0,
                "supporting_count": 0,
                "contradicting_count": 0,
                "neutral_count": 0,
                "max_entailment": 0.0,
                "max_contradiction": 0.0,
                "evidence_quality": "low"
            }
        
        # Calculate both simple counts (for metadata) and credibility-weighted scores (for verdict)
        supporting_count = sum(1 for v in verifications if v.get("relationship") == "entails")
        contradicting_count = sum(1 for v in verifications if v.get("relationship") == "contradicts")
        neutral_count = len(verifications) - supporting_count - contradicting_count

        # Weight by evidence credibility (Consensus Plan Phase 2)
        supporting_weight = sum(
            v.get("evidence", {}).get("credibility_score", 0.6)
            for v in verifications
            if v.get("relationship") == "entails"
        )
        contradicting_weight = sum(
            v.get("evidence", {}).get("credibility_score", 0.6)
            for v in verifications
            if v.get("relationship") == "contradicts"
        )

        max_entailment = max([v.get("entailment_score", 0.0) for v in verifications], default=0.0)
        max_contradiction = max([v.get("contradiction_score", 0.0) for v in verifications], default=0.0)

        avg_confidence = sum([v.get("confidence", 0.0) for v in verifications]) / len(verifications)

        # Determine overall verdict using credibility-weighted scores
        total_weight = supporting_weight + contradicting_weight
        if supporting_weight > contradicting_weight and max_entailment > 0.7:
            overall_verdict = "supported"
            confidence = min(max_entailment * (supporting_weight / total_weight if total_weight > 0 else 0), 0.95)
        elif contradicting_weight > supporting_weight and max_contradiction > 0.7:
            overall_verdict = "contradicted"
            confidence = min(max_contradiction * (contradicting_weight / total_weight if total_weight > 0 else 0), 0.95)
        else:
            overall_verdict = "uncertain"
            confidence = max(0.1, min(avg_confidence, 0.6))
        
        # Assess evidence quality
        high_conf_count = sum(1 for v in verifications if v.get("confidence", 0.0) > 0.8)
        if high_conf_count >= 2:
            evidence_quality = "high"
        elif high_conf_count >= 1:
            evidence_quality = "medium"
        else:
            evidence_quality = "low"
        
        signals = {
            "overall_verdict": overall_verdict,
            "confidence": confidence,
            "supporting_count": supporting_count,
            "contradicting_count": contradicting_count,
            "neutral_count": neutral_count,
            "supporting_weight": supporting_weight,
            "contradicting_weight": contradicting_weight,
            "max_entailment": max_entailment,
            "max_contradiction": max_contradiction,
            "evidence_quality": evidence_quality,
            "total_evidence": len(verifications),
            "avg_confidence": avg_confidence
        }

        # Phase 3: Add per-evidence stance data for abstention logic consensus calculation
        for v in verifications:
            evidence_id = v.get('evidence_id', '')
            if evidence_id:
                relationship = v.get('relationship', 'neutral')
                # Map relationship to stance terminology
                stance = 'supporting' if relationship == 'entails' else \
                         'contradicting' if relationship == 'contradicts' else \
                         'neutral'
                signals[f'evidence_{evidence_id}_stance'] = stance

        return signals

    def adjust_confidence_for_claim_complexity(self, claim_text: str, base_confidence: float,
                                               verifications: List[Dict[str, Any]]) -> float:
        """
        Adjust confidence based on claim complexity and evidence coverage

        Complex multi-part claims (with conjunctions like "and", "but", "without")
        may only have partial evidence coverage, so confidence should be reduced.
        """
        # Detect multi-part claims (conjunction indicators)
        complexity_indicators = [
            ' and ', ' but ', ' while ', ' without ', ' despite ',
            ' although ', ' however ', ' yet ', ' whereas '
        ]

        has_multiple_parts = any(conj in claim_text.lower() for conj in complexity_indicators)

        if not has_multiple_parts:
            # Simple atomic claim - no adjustment needed
            return base_confidence

        # Multi-part claim detected - check evidence coverage
        # If evidence only addresses one part, reduce confidence significantly
        logger.info(f"[VERIFY] COMPLEXITY ADJUSTMENT: Multi-part claim detected")
        logger.info(f"   Claim: {claim_text[:80]}...")

        # Check if we have strong evidence (high entailment/contradiction scores)
        has_strong_evidence = any(
            v.get("entailment_score", 0.0) > 0.8 or v.get("contradiction_score", 0.0) > 0.8
            for v in verifications
        )

        if has_strong_evidence:
            # Strong evidence for multi-part claim likely means partial coverage
            # (e.g., evidence confirms "demolished" but not "without consulting")
            adjusted_confidence = base_confidence * 0.65
            logger.info(f"   Adjustment: {base_confidence:.2f} → {adjusted_confidence:.2f} (partial evidence coverage)")
            return adjusted_confidence
        else:
            # Weak evidence for multi-part claim - moderate reduction
            adjusted_confidence = base_confidence * 0.80
            logger.info(f"   Adjustment: {base_confidence:.2f} → {adjusted_confidence:.2f} (weak coverage)")
            return adjusted_confidence

# Singleton instance for reuse
_claim_verifier = None

async def get_claim_verifier() -> ClaimVerifier:
    """Get singleton claim verifier instance"""
    global _claim_verifier
    if _claim_verifier is None:
        _claim_verifier = ClaimVerifier()
    return _claim_verifier