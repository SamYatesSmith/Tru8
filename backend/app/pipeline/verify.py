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
        
        # Determine relationship
        if entailment_score > contradiction_score and entailment_score > neutral_score:
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
            "evidence_snippet": self.evidence_text[:200] + "..." if len(self.evidence_text) > 200 else self.evidence_text
        }

class NLIVerifier:
    """Natural Language Inference verifier for claim-evidence pairs"""
    
    def __init__(self):
        self.model = None
        self.tokenizer = None
        self.model_name = "facebook/bart-large-mnli"  # Well-tested NLI model that actually exists
        self.max_length = 512
        self.batch_size = 8
        self.confidence_threshold = getattr(settings, 'NLI_CONFIDENCE_THRESHOLD', 0.7)
        self.device = None  # Will be set when model is loaded
        self._lock = asyncio.Lock()
        self.cache_service = None

        logger.info("NLI Verifier initialized (models will be loaded on first use)")

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
                            model = AutoModelForSequenceClassification.from_pretrained(self.model_name)
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

        return {
            "stance": stance,
            "confidence": result.confidence,
            "scores": {
                "entailment": result.entailment_score,
                "neutral": result.neutral_score,
                "contradiction": result.contradiction_score
            }
        }

    def _make_cache_key(self, claim: str, evidence: str) -> str:
        """Create cache key for claim-evidence pair"""
        content = f"{claim}|||{evidence}"
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
                        3600 * 24  # 24 hour cache
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
        """Process a single batch of claim-evidence pairs"""
        try:
            # Prepare inputs
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
            
            # Convert to list of tuples (entailment, contradiction, neutral)
            results = []
            for i in range(len(premises)):
                # DeBERTa-MNLI: [contradiction, neutral, entailment]
                contradiction = probabilities[i][0].item()
                neutral = probabilities[i][1].item()
                entailment = probabilities[i][2].item()
                results.append((entailment, contradiction, neutral))
            
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
        
        supporting_count = sum(1 for v in verifications if v.get("relationship") == "entails")
        contradicting_count = sum(1 for v in verifications if v.get("relationship") == "contradicts")
        neutral_count = len(verifications) - supporting_count - contradicting_count
        
        max_entailment = max([v.get("entailment_score", 0.0) for v in verifications], default=0.0)
        max_contradiction = max([v.get("contradiction_score", 0.0) for v in verifications], default=0.0)
        
        avg_confidence = sum([v.get("confidence", 0.0) for v in verifications]) / len(verifications)
        
        # Determine overall verdict based on evidence strength
        if supporting_count > contradicting_count and max_entailment > 0.7:
            overall_verdict = "supported"
            confidence = min(max_entailment * (supporting_count / len(verifications)), 0.95)
        elif contradicting_count > supporting_count and max_contradiction > 0.7:
            overall_verdict = "contradicted"
            confidence = min(max_contradiction * (contradicting_count / len(verifications)), 0.95)
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

# Singleton instance for reuse
_claim_verifier = None

async def get_claim_verifier() -> ClaimVerifier:
    """Get singleton claim verifier instance"""
    global _claim_verifier
    if _claim_verifier is None:
        _claim_verifier = ClaimVerifier()
    return _claim_verifier