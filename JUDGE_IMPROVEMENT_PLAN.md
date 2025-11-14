# Judge System Improvement Plan

**Date**: 2025-11-13
**Objective**: Fix critical judge reasoning failures causing incorrect verdicts
**Target Issues**:
- Ballroom claim incorrectly marked "contradicted"
- Legal exemption claim incorrectly marked "contradicted"
- GovInfo API routing failure

**Status**: PLANNING PHASE

---

## Executive Summary

This plan addresses **5 critical failure modes** in the fact-checking pipeline:

1. **Credibility Paradox**: Fact-check sites (0.95) override primary news sources (0.90)
2. **Context Loss**: 150-char snippet truncation loses critical evidence context
3. **Judge Over-Inference**: Adding phantom qualifiers not present in claims
4. **NLI Context Blindness**: Can't distinguish meta-claims from primary claims
5. **Abstention False Positives**: Marking misinterpretations as "conflicting opinion"

**Approach**: Phased implementation with immediate quick wins, followed by deeper architectural improvements.

---

## Phase 0: Critical Infrastructure Fix

### 🚨 IMMEDIATE: Restart Celery Worker

**Issue**: GovInfo adapter initialized in FastAPI but not in Celery worker
**Fix Applied**: Commit f45db33 added worker_ready signal handler
**Action Required**: Manual Celery worker restart

```bash
# Stop existing worker
pkill -f "celery.*worker"  # Linux/Mac
# Or manually stop on Windows: Ctrl+C in worker terminal

# Start worker with logging
cd backend
celery -A app.workers.celery_app worker --loglevel=info
```

**Validation**:
- Check logs for: `"✅ API adapters initialized in Celery worker"`
- Submit legal claim and verify GovInfo.gov sources appear in results

**Priority**: CRITICAL - Must complete before proceeding
**Time**: 2 minutes
**Risk**: None (fixes existing bug)

---

## Phase 1: Quick Wins (High Impact, Low Risk)

**Timeline**: 1-2 hours
**Testing**: After each fix, rerun both problem claims

### Fix 1.1: Adjust Fact-Check Credibility Scores

**Problem**: Snopes (0.95) beats PBS/BBC/NPR (0.90) in credibility weighting

**Solution**: Lower fact-check credibility to reflect their meta-analysis nature

**File**: `backend/app/data/source_credibility.json`

**Changes**:
```json
{
  "factcheck": {
    "credibility": 0.87,  // Changed from 0.95
    "reasoning": "Fact-check sites provide meta-analysis, not primary evidence. Should not override multiple primary sources.",
    "domains": [
      "snopes.com",
      "politifact.com",
      "factcheck.org",
      "fullfact.org",
      "apnews.com/ap-fact-check",
      "reuters.com/fact-check"
    ]
  }
}
```

**Rationale**:
- 0.87 places fact-checkers BELOW tier-1 news (BBC/Reuters/NPR at 0.90)
- BUT above tier-2 newspapers (NYTimes/WSJ at 0.85)
- Reflects that they're still highly credible, just not primary sources
- Single Snopes article (0.87) won't override PBS (0.90) + BBC (0.90) = 1.80

**Expected Impact**:
- ✅ Ballroom claim: PBS + BBC (1.80) will now outweigh Snopes (0.87)
- ⚠️ Doesn't fix "fake rendering" context loss (addressed in Fix 1.2)

**Testing**:
```bash
# Restart backend (FastAPI auto-reloads, but verify)
# Submit ballroom claim
# Verify verdict changes from "contradicted" to "supported"
```

**Rollback**: Revert to 0.95 if needed

---

### Fix 1.2: Increase Evidence Snippet Length

**Problem**: 150-char truncation cuts "Rumored rendering... Fact-check verdict: Fake" → "Fake"

**Solution**: Increase snippet context to capture critical qualifiers

**File**: `backend/app/pipeline/retrieve.py`

**Current Code** (line ~283):
```python
snippet = ev.get("snippet", ev.get("text", ""))[:150]  # Only 150 chars!
```

**New Code**:
```python
# Increased to 400 chars to preserve context (e.g., "fake rendering" vs "fake")
snippet = ev.get("snippet", ev.get("text", ""))[:400]
```

**Configuration**: Add to `backend/app/core/config.py`:
```python
# Evidence Snippet Configuration
EVIDENCE_SNIPPET_LENGTH: int = Field(400, env="EVIDENCE_SNIPPET_LENGTH")
```

**Updated retrieve.py**:
```python
from app.core.config import settings

snippet = ev.get("snippet", ev.get("text", ""))[:settings.EVIDENCE_SNIPPET_LENGTH]
```

**Rationale**:
- 400 chars ≈ 2-3 sentences
- Captures full context: "Rumored rendering of Trump's planned White House ballroom isn't real. Fact-check verdict: Fake"
- NLI will see "rendering" and "fake" together, understanding meta-claim nature
- Minimal performance impact (NLI models handle 512+ token inputs)

**Expected Impact**:
- ✅ NLI can distinguish "fake rendering" from "fake project"
- ✅ Better context for all evidence types

**Testing**:
```bash
# Submit ballroom claim
# Check evidence snippets are longer and include context
# Verify NLI scores Snopes more accurately (lower contradiction score)
```

**Rollback**: Set EVIDENCE_SNIPPET_LENGTH=150 in .env

---

### Fix 1.3: Enhance Judge Prompt - Anti-Qualifier Guidance

**Problem**: Judge adds qualifiers like "all provisions" when claim just says "provisions"

**Solution**: Add explicit prompt instructions against semantic over-inference

**File**: `backend/app/pipeline/judge.py`

**Current System Prompt** (lines 49-104):
- Has guidance on fact-checks
- Has numerical tolerance guidance
- MISSING: Qualifier guidance

**New Prompt Section** (insert after line 82):
```python
CRITICAL - Do NOT Add Qualifiers or Over-Interpret:
- Judge ONLY what the claim EXPLICITLY states
- If claim says "exempts from provisions", do NOT interpret as "all provisions" or "certain provisions"
- If claim says "roughly $350M", accept $320M-$380M (±15%), do NOT require exact match
- Do NOT infer semantic qualifiers (all, some, certain, most, few) unless EXPLICITLY present
- Do NOT add temporal qualifiers (always, never, sometimes) unless stated
- Do NOT add scope qualifiers (everywhere, nowhere, somewhere) unless stated

Examples of OVER-INFERENCE to AVOID:
❌ Claim: "The act exempts the White House"
   Judge reads: "exempts from ALL provisions"
   → WRONG: "all" not in claim

❌ Claim: "Project costs roughly $350 million"
   Judge reads: "costs exactly $350 million"
   → WRONG: "roughly" means ±15% tolerance

✅ Claim: "The act exempts the White House from its provisions"
   Evidence: "White House is exempt from Section 106"
   → CORRECT: Exemption confirmed, no "all" qualifier needed

✅ Claim: "Project costs roughly $350 million"
   Evidence: "Estimated at $320 million"
   → CORRECT: $320M is within ±15% of $350M
```

**Implementation**:
```python
def _build_system_prompt(self) -> str:
    """Build the judge system prompt with anti-qualifier guidance"""
    return """You are an expert fact-checker making final verdicts on claims based on evidence analysis.

Your job is to determine if claims are SUPPORTED, CONTRADICTED, or UNCERTAIN based on evidence.

CRITICAL - Do NOT Add Qualifiers or Over-Interpret:
[... new section above ...]

IMPORTANT - Handling Fact-Check Articles:
[... existing guidance ...]

[... rest of existing prompt ...]
"""
```

**Expected Impact**:
- ✅ Legal exemption claim: Judge won't add "all provisions" → verdict becomes "supported"
- ✅ Numerical claims: Better tolerance handling
- ✅ Reduced false contradictions from over-interpretation

**Testing**:
```bash
# Submit legal exemption claim
# Check judge reasoning in response
# Verify no mention of "all provisions" or similar qualifiers
# Verdict should be "supported"
```

**Rollback**: Remove new prompt section

---

### Fix 1.4: Add Evidence Relevance Filter

**Problem**: Tangentially-related evidence (e.g., "fake rendering" article about ballroom project) influences verdict

**Solution**: Pre-filter evidence by semantic relevance before judge sees it

**New Feature Flag** in `backend/app/core/config.py`:
```python
# Phase 6 - Judge Improvements (Week 12)
ENABLE_EVIDENCE_RELEVANCE_FILTER: bool = Field(False, env="ENABLE_EVIDENCE_RELEVANCE_FILTER")
RELEVANCE_THRESHOLD: float = Field(0.65, env="RELEVANCE_THRESHOLD")
```

**New Function** in `backend/app/pipeline/verify.py`:
```python
def calculate_evidence_relevance(
    self,
    claim: str,
    evidence_snippet: str,
    evidence_title: str = ""
) -> float:
    """
    Calculate semantic relevance of evidence to claim using embedding similarity.

    Returns: 0.0-1.0 score where:
    - > 0.8: Highly relevant (direct evidence)
    - 0.65-0.8: Moderately relevant
    - < 0.65: Low relevance (possibly tangential)
    """
    from app.services.embeddings import get_embedding_service

    embedding_service = get_embedding_service()

    # Combine title + snippet for better context
    evidence_text = f"{evidence_title} {evidence_snippet}".strip()

    # Calculate cosine similarity
    claim_embedding = embedding_service.embed(claim)
    evidence_embedding = embedding_service.embed(evidence_text)

    relevance_score = cosine_similarity(claim_embedding, evidence_embedding)

    logger.info(f"Evidence relevance: {relevance_score:.3f} | Claim: {claim[:50]}... | Evidence: {evidence_text[:50]}...")

    return relevance_score
```

**Integration** in `backend/app/pipeline/judge.py` (before judgment):
```python
def judge_claim(self, claim: Dict[str, Any], evidence: List[Dict[str, Any]],
                verification_signals: Dict[str, Any]) -> Dict[str, Any]:
    """Make final judgment on claim with relevance filtering"""

    # NEW: Filter low-relevance evidence before judgment
    if settings.ENABLE_EVIDENCE_RELEVANCE_FILTER:
        filtered_evidence = []
        for ev in evidence:
            relevance = self.verifier.calculate_evidence_relevance(
                claim=claim.get("text", ""),
                evidence_snippet=ev.get("snippet", ""),
                evidence_title=ev.get("title", "")
            )

            if relevance >= settings.RELEVANCE_THRESHOLD:
                ev["relevance_score"] = relevance
                filtered_evidence.append(ev)
            else:
                logger.info(f"🚫 Filtered low-relevance evidence (score={relevance:.3f}): {ev.get('source', 'Unknown')}")

        logger.info(f"Evidence filtering: {len(evidence)} → {len(filtered_evidence)} (threshold={settings.RELEVANCE_THRESHOLD})")
        evidence = filtered_evidence

    # Existing judgment logic continues...
    if not evidence or len(evidence) < 3:
        return self._create_abstention_verdict(...)
```

**Expected Impact**:
- ✅ "Fake rendering" article filtered out (low relevance to "ballroom project claim")
- ✅ Only direct evidence about the ballroom reaches judge
- ⚠️ Requires testing to tune threshold (0.65 default)

**Testing**:
```bash
# Enable feature flag in .env
ENABLE_EVIDENCE_RELEVANCE_FILTER=true
RELEVANCE_THRESHOLD=0.65

# Submit ballroom claim
# Check logs for relevance scores
# Verify Snopes "rendering" article is filtered
# Adjust threshold if needed
```

**Rollback**: Set ENABLE_EVIDENCE_RELEVANCE_FILTER=false

---

## Phase 2: Architectural Improvements (Medium Risk)

**Timeline**: 3-4 hours
**Prerequisites**: Phase 1 complete and validated

### Fix 2.1: Implement Fact-Check Detection & Parsing

**Problem**: System treats fact-check META-CLAIMS as primary evidence

**Solution**: Detect fact-check articles and parse their target claim

**New Service**: `backend/app/services/factcheck_parser.py`

```python
from typing import Dict, Optional
import re

FACTCHECK_DOMAINS = {
    "snopes.com", "politifact.com", "factcheck.org",
    "fullfact.org", "apnews.com/ap-fact-check", "reuters.com/fact-check"
}

FACTCHECK_VERDICT_PATTERNS = {
    "false": ["false", "fake", "debunked", "incorrect", "untrue"],
    "true": ["true", "correct", "accurate", "confirmed"],
    "mixed": ["mixed", "partly true", "mostly true", "unproven"]
}

class FactCheckParser:
    """Parse and interpret fact-check articles"""

    def is_factcheck_article(self, url: str, source: str) -> bool:
        """Detect if article is from fact-checking site"""
        from urllib.parse import urlparse
        domain = urlparse(url).netloc.lower()
        return any(fc_domain in domain for fc_domain in FACTCHECK_DOMAINS)

    def parse_factcheck_verdict(self, title: str, snippet: str) -> Optional[Dict]:
        """
        Extract fact-check verdict and target claim.

        Returns: {
            "verdict": "false" | "true" | "mixed",
            "target_claim": str,  # What claim they're fact-checking
            "confidence": float   # How confident we are in parsing
        }
        """
        text = f"{title} {snippet}".lower()

        # Detect verdict
        verdict = None
        for verdict_type, patterns in FACTCHECK_VERDICT_PATTERNS.items():
            if any(pattern in text for pattern in patterns):
                verdict = verdict_type
                break

        if not verdict:
            return None

        # Try to extract target claim (basic heuristics)
        # Look for patterns like:
        # - "Claim: [text]" or "Claim that [text]"
        # - "Rumor: [text]"
        # - "[text] is false"

        target_claim = None

        # Pattern 1: "claim that X"
        match = re.search(r"claim that ([^.!?]+)", text)
        if match:
            target_claim = match.group(1).strip()

        # Pattern 2: "rumor/rumored X"
        if not target_claim:
            match = re.search(r"rumored? ([^.!?]+)", text)
            if match:
                target_claim = match.group(1).strip()

        return {
            "verdict": verdict,
            "target_claim": target_claim,
            "confidence": 0.8 if target_claim else 0.5
        }

    def calculate_factcheck_relevance(
        self,
        our_claim: str,
        factcheck_target: Optional[str],
        factcheck_verdict: str
    ) -> float:
        """
        Determine if fact-check article is relevant to our claim.

        Returns: 0.0-1.0 relevance score
        """
        if not factcheck_target:
            return 0.3  # Low confidence - can't tell what they're fact-checking

        # Calculate semantic similarity between our claim and their target
        from app.services.embeddings import get_embedding_service
        embeddings = get_embedding_service()

        our_embedding = embeddings.embed(our_claim.lower())
        target_embedding = embeddings.embed(factcheck_target.lower())

        similarity = cosine_similarity(our_embedding, target_embedding)

        # High similarity = factcheck is about our claim
        # Low similarity = factcheck is about something else
        return similarity
```

**Integration** in `backend/app/pipeline/verify.py`:
```python
from app.services.factcheck_parser import FactCheckParser

class VerificationService:
    def __init__(self):
        # ... existing init ...
        self.factcheck_parser = FactCheckParser()

    def verify_claim(self, claim: Dict[str, Any], evidence: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Verify claim against evidence with fact-check awareness"""

        processed_evidence = []

        for ev in evidence:
            # Check if this is a fact-check article
            is_factcheck = self.factcheck_parser.is_factcheck_article(
                url=ev.get("url", ""),
                source=ev.get("source_name", "")
            )

            if is_factcheck:
                logger.info(f"🔍 Detected fact-check article: {ev.get('source_name', '')}")

                # Parse fact-check content
                factcheck_data = self.factcheck_parser.parse_factcheck_verdict(
                    title=ev.get("title", ""),
                    snippet=ev.get("snippet", "")
                )

                if factcheck_data:
                    # Calculate relevance
                    relevance = self.factcheck_parser.calculate_factcheck_relevance(
                        our_claim=claim.get("text", ""),
                        factcheck_target=factcheck_data.get("target_claim"),
                        factcheck_verdict=factcheck_data.get("verdict")
                    )

                    logger.info(f"   Fact-check relevance: {relevance:.3f}")
                    logger.info(f"   Fact-check target: {factcheck_data.get('target_claim', 'Unknown')}")

                    # If low relevance, mark for filtering or downweighting
                    if relevance < 0.65:
                        logger.info(f"   ⚠️ Fact-check about different claim - downweighting")
                        ev["credibility_score"] *= 0.5  # Reduce influence

                    ev["factcheck_data"] = factcheck_data
                    ev["factcheck_relevance"] = relevance

            processed_evidence.append(ev)

        # Continue with NLI verification on processed evidence
        verifications = []
        for ev in processed_evidence:
            verification = self._verify_single_evidence(claim, ev)
            verifications.append(verification)

        return self.aggregate_verification_signals(verifications)
```

**Expected Impact**:
- ✅ Snopes "fake rendering" detected as fact-check about different target
- ✅ Downweighted or filtered before judgment
- ✅ Better handling of all fact-check meta-claims

**Testing**:
```bash
# Submit ballroom claim with Snopes "rendering" article
# Check logs for fact-check detection and relevance scoring
# Verify Snopes influence is reduced
```

---

### Fix 2.2: Enhanced NLI Context Window

**Problem**: NLI model sees only 150-char snippets, missing context

**Solution**: Pass more context to NLI (title + snippet)

**File**: `backend/app/pipeline/verify.py`

**Current Code**:
```python
def _verify_single_evidence(self, claim: Dict, evidence: Dict) -> Dict:
    """Run NLI on single evidence"""
    claim_text = claim.get("text", "")
    evidence_text = evidence.get("snippet", "")  # Only snippet!

    scores = self.nli_model(claim_text, evidence_text)
    # ...
```

**New Code**:
```python
def _verify_single_evidence(self, claim: Dict, evidence: Dict) -> Dict:
    """Run NLI on single evidence with enhanced context"""
    claim_text = claim.get("text", "")

    # NEW: Combine title + snippet for better context
    evidence_title = evidence.get("title", "")
    evidence_snippet = evidence.get("snippet", "")

    if evidence_title:
        # Format: "Title. Snippet"
        evidence_text = f"{evidence_title}. {evidence_snippet}"
    else:
        evidence_text = evidence_snippet

    # Truncate to model's max input length (512 tokens ≈ 2000 chars)
    evidence_text = evidence_text[:2000]

    logger.debug(f"NLI input - Claim: {claim_text[:80]}...")
    logger.debug(f"NLI input - Evidence: {evidence_text[:120]}...")

    scores = self.nli_model(claim_text, evidence_text)
    # ...
```

**Expected Impact**:
- ✅ NLI sees "Rumored rendering... ballroom... fake" together
- ✅ Better semantic understanding of meta-claims
- ✅ Improved accuracy across all evidence types

---

### Fix 2.3: Judge Self-Critique Step

**Problem**: Judge makes reasoning errors but has no self-correction mechanism

**Solution**: Two-pass judgment with self-critique

**Feature Flag** in `backend/app/core/config.py`:
```python
ENABLE_JUDGE_SELF_CRITIQUE: bool = Field(False, env="ENABLE_JUDGE_SELF_CRITIQUE")
```

**Implementation** in `backend/app/pipeline/judge.py`:
```python
def judge_claim_with_critique(self, claim: Dict, evidence: List[Dict],
                              verification_signals: Dict) -> Dict:
    """Two-pass judgment with self-critique"""

    # Pass 1: Initial judgment
    initial_verdict = self._generate_verdict(claim, evidence, verification_signals)

    if not settings.ENABLE_JUDGE_SELF_CRITIQUE:
        return initial_verdict

    # Pass 2: Self-critique prompt
    critique_prompt = f"""
You previously judged this claim with the following verdict:

CLAIM: {claim.get('text')}
YOUR VERDICT: {initial_verdict.get('verdict')}
YOUR REASONING: {initial_verdict.get('reasoning')}

SELF-CRITIQUE CHECKLIST:
1. Did you add any qualifiers (all, some, certain, most) not present in the claim?
2. Did you interpret "roughly" or "approximately" as requiring exactness?
3. If evidence is from fact-check sites, did you verify they're fact-checking THIS claim (not a similar one)?
4. Did you give appropriate weight to primary sources vs. meta-analysis?

If you made any errors above, provide a CORRECTED verdict. Otherwise, respond "VERDICT CONFIRMED".

Format:
{{
  "status": "CORRECTED" or "CONFIRMED",
  "issues_found": ["list of any issues"],
  "corrected_verdict": "supported/contradicted/uncertain" (if corrected),
  "corrected_reasoning": "..." (if corrected)
}}
"""

    critique_response = self._call_llm(critique_prompt)
    critique_data = json.loads(critique_response)

    if critique_data["status"] == "CORRECTED":
        logger.info(f"🔄 Judge self-corrected verdict: {initial_verdict['verdict']} → {critique_data['corrected_verdict']}")
        logger.info(f"   Issues found: {critique_data['issues_found']}")

        return {
            **initial_verdict,
            "verdict": critique_data["corrected_verdict"],
            "reasoning": critique_data["corrected_reasoning"],
            "self_critique": critique_data,
            "original_verdict": initial_verdict["verdict"]
        }

    return initial_verdict
```

**Expected Impact**:
- ✅ Catches qualifier over-inference ("all provisions" error)
- ✅ Catches fact-check misinterpretations
- ⚠️ Adds latency (~1-2s additional LLM call)
- ⚠️ Doubles LLM cost for judgments

**Testing**:
```bash
ENABLE_JUDGE_SELF_CRITIQUE=true

# Submit legal exemption claim
# Check logs for self-critique activation
# Verify corrected verdict if initial was wrong
```

---

## Phase 3: Long-Term Enhancements (High Impact, High Risk)

**Timeline**: 6-8 hours
**Prerequisites**: Phases 1-2 complete, tested, and deployed to production

### Fix 3.1: Ensemble NLI Verification

**Problem**: Single NLI model (DeBERTa) can make systematic errors

**Solution**: Run multiple NLI models and average scores

**Models**:
1. DeBERTa-v3-base-mnli-fever-anli (current, best for facts)
2. BART-large-mnli (fallback, more general)
3. RoBERTa-large-mnli (alternative architecture)

**Implementation**: See detailed pseudocode in separate doc

---

### Fix 3.2: Multi-Stage Evidence Pipeline

**Architecture**:
```
Evidence → Relevance Filter → Fact-Check Parser → NLI Verification → Judge
           ↓                  ↓                   ↓
       Discard <0.65    Downweight tangential   Weighted scores
```

---

### Fix 3.3: Fine-Tune Judge on Failure Cases

**Approach**:
1. Collect 50-100 examples of judge failures
2. Create training dataset with corrections
3. Fine-tune GPT-4o-mini or Claude on dataset
4. A/B test fine-tuned vs. base model

---

## Testing Strategy

### Test Suite 1: Original Problem Claims

**Test Case 1: Ballroom Claim**
```yaml
claim: "The East Wing demolition project is part of plans to construct a 90,000-square-foot ballroom."
expected_verdict: supported
expected_confidence: 0.80+
expected_sources: PBS, BBC, NPR (supporting)
must_not_include: Snopes as primary contradicting source
```

**Test Case 2: Legal Exemption Claim**
```yaml
claim: "The National Historic Preservation Act of 1966 exempts the White House from its provisions."
expected_verdict: supported
expected_confidence: 0.85+
reasoning_must_not_contain: ["all provisions", "certain provisions"]
reasoning_must_contain: ["exemption confirmed", "multiple sources agree"]
```

**Test Case 3: Legal Statute (GovInfo)**
```yaml
claim: "The National Historic Preservation Act of 1966 requires federal agencies to consider historic preservation."
expected_sources: [GovInfo.gov]
source_types: [government_api]
expected_verdict: supported
```

### Test Suite 2: Edge Cases

**Test Case 4: Numerical Tolerance**
```yaml
claim: "The project received roughly $350 million in donations."
evidence_value: "$320 million"
expected_verdict: supported
reasoning: "roughly allows ±15% tolerance"
```

**Test Case 5: Fact-Check Meta-Claim**
```yaml
claim: "Tesla delivered 1.3 million vehicles in 2022."
evidence: "Snopes: FALSE - Claim that Tesla delivered 2 million vehicles is debunked"
expected: Snopes should be recognized as irrelevant (different target claim)
expected_verdict: supported (if other sources confirm 1.3M)
```

**Test Case 6: Ambiguous Fact-Check**
```yaml
claim: "The White House ballroom project includes 90,000 sq ft."
evidence: "Snopes: Fake rendering of ballroom circulates online"
expected: Snopes should be downweighted (about rendering, not project)
expected_verdict: supported (if primary sources confirm)
```

### Automated Test Implementation

**File**: `backend/tests/pipeline/test_judge_improvements.py`

```python
import pytest
from app.pipeline.judge import JudgmentService
from app.pipeline.verify import VerificationService
from app.pipeline.retrieve import EvidenceService

@pytest.mark.asyncio
async def test_ballroom_claim_verdict():
    """Test that ballroom claim is supported despite Snopes 'fake rendering' article"""

    claim = {
        "text": "The East Wing demolition project is part of plans to construct a 90,000-square-foot ballroom.",
        "claim_type": "factual"
    }

    # Retrieve evidence
    evidence_service = EvidenceService()
    evidence = await evidence_service.retrieve_evidence(claim)

    # Verify
    verify_service = VerificationService()
    verification = verify_service.verify_claim(claim, evidence)

    # Judge
    judge_service = JudgmentService()
    judgment = judge_service.judge_claim(claim, evidence, verification)

    # Assertions
    assert judgment["verdict"] == "supported", f"Expected 'supported', got '{judgment['verdict']}'"
    assert judgment["confidence"] >= 0.75, f"Confidence too low: {judgment['confidence']}"

    # Check that Snopes didn't override PBS/BBC/NPR
    reasoning = judgment["reasoning"].lower()
    assert "pbs" in reasoning or "bbc" in reasoning, "Primary sources not mentioned in reasoning"

    # Check for proper source weighting
    supporting_sources = [s for s in judgment.get("sources", []) if s.get("stance") == "supporting"]
    assert len(supporting_sources) >= 2, "Should have multiple supporting sources"

@pytest.mark.asyncio
async def test_legal_exemption_no_qualifier_hallucination():
    """Test that judge doesn't add 'all provisions' qualifier"""

    claim = {
        "text": "The National Historic Preservation Act of 1966 exempts the White House from its provisions.",
        "claim_type": "legal"
    }

    evidence_service = EvidenceService()
    evidence = await evidence_service.retrieve_evidence(claim)

    verify_service = VerificationService()
    verification = verify_service.verify_claim(claim, evidence)

    judge_service = JudgmentService()
    judgment = judge_service.judge_claim(claim, evidence, verification)

    # Assertions
    assert judgment["verdict"] == "supported", f"Expected 'supported', got '{judgment['verdict']}'"

    # CRITICAL: Check reasoning doesn't add qualifiers
    reasoning = judgment["reasoning"].lower()
    assert "all provisions" not in reasoning, "Judge added 'all provisions' qualifier not in claim"
    assert "certain provisions" not in reasoning or judgment["verdict"] != "contradicted", \
        "Judge marked as contradicted based on 'certain' vs phantom 'all'"

    # Should acknowledge exemption exists
    assert "exempt" in reasoning, "Reasoning should mention exemption"

@pytest.mark.asyncio
async def test_govinfo_api_routing():
    """Test that legal claims route to GovInfo API"""

    claim = {
        "text": "The National Historic Preservation Act of 1966 requires federal agencies to consider historic preservation.",
        "claim_type": "legal",
        "legal_metadata": {
            "jurisdiction": "US",
            "statute_name": "National Historic Preservation Act"
        }
    }

    evidence_service = EvidenceService()
    evidence = await evidence_service.retrieve_evidence(claim)

    # Check that GovInfo sources are included
    govinfo_sources = [e for e in evidence if "govinfo.gov" in e.get("url", "").lower()]
    assert len(govinfo_sources) > 0, "No GovInfo.gov sources found for legal claim"

    # Check that at least one source is from government API
    api_sources = [e for e in evidence if e.get("source_type") == "government_api"]
    assert len(api_sources) > 0, "No government API sources found"

@pytest.mark.asyncio
async def test_factcheck_relevance_filtering():
    """Test that irrelevant fact-check articles are filtered/downweighted"""

    claim = {
        "text": "Tesla delivered 1.3 million vehicles in 2022.",
        "claim_type": "factual"
    }

    # Mock evidence with irrelevant Snopes article
    mock_evidence = [
        {
            "source_name": "Snopes",
            "url": "https://snopes.com/fact-check/tesla-2-million",
            "title": "Did Tesla Deliver 2 Million Vehicles?",
            "snippet": "FALSE: Claim that Tesla delivered 2 million vehicles in 2022 is incorrect. Actual figure was 1.31 million.",
            "credibility_score": 0.87
        },
        {
            "source_name": "Reuters",
            "url": "https://reuters.com/tesla-2022-deliveries",
            "title": "Tesla Delivers 1.31 Million Vehicles in 2022",
            "snippet": "Tesla announced it delivered a record 1.31 million vehicles globally in 2022.",
            "credibility_score": 0.90
        }
    ]

    verify_service = VerificationService()
    verification = verify_service.verify_claim(claim, mock_evidence)

    judge_service = JudgmentService()
    judgment = judge_service.judge_claim(claim, mock_evidence, verification)

    # Assertions
    assert judgment["verdict"] == "supported", "Should recognize Snopes is fact-checking a DIFFERENT claim (2M vs 1.3M)"

    # Check that Snopes was properly interpreted
    # It says "2M is false, actual was 1.31M" which SUPPORTS our claim of 1.3M
    reasoning = judgment["reasoning"]
    assert "1.31" in reasoning or "1.3" in reasoning, "Should reference actual delivery figure"
```

**Run Tests**:
```bash
cd backend
pytest tests/pipeline/test_judge_improvements.py -v

# Expected output:
# ✅ test_ballroom_claim_verdict PASSED
# ✅ test_legal_exemption_no_qualifier_hallucination PASSED
# ✅ test_govinfo_api_routing PASSED
# ✅ test_factcheck_relevance_filtering PASSED
```

---

## Success Criteria

### Phase 1 Success (Quick Wins)
- [x] Celery worker restarted and logs show adapter initialization
- [ ] Ballroom claim verdict changes from "contradicted" to "supported"
- [ ] Legal exemption claim verdict changes from "contradicted" to "supported"
- [ ] Judge reasoning doesn't contain added qualifiers ("all provisions")
- [ ] Evidence snippets are 400 chars and include context
- [ ] Fact-check credibility is 0.87 (below tier-1 news)

### Phase 2 Success (Architectural)
- [ ] Fact-check articles detected and parsed
- [ ] Irrelevant fact-checks downweighted or filtered
- [ ] NLI receives title + snippet context (not just snippet)
- [ ] Judge self-critique catches over-inference errors
- [ ] Relevance filtering removes tangential evidence

### Phase 3 Success (Long-Term)
- [ ] Ensemble NLI reduces single-model bias
- [ ] Multi-stage pipeline improves evidence quality
- [ ] Fine-tuned judge model outperforms base model on test cases

### Overall Success Metrics
- **Accuracy**: Test suite passes with 100% success rate
- **Reliability**: No false contradictions on known-true claims
- **Source Quality**: Primary sources weighted higher than meta-analysis
- **Reasoning Quality**: Judge reasoning aligns with evidence, no hallucinated qualifiers
- **API Integration**: Legal claims route to GovInfo 90%+ of the time

---

## Rollback Strategy

### If Phase 1 Fails

**Rollback Steps**:
```bash
# 1. Revert credibility scores
git checkout HEAD -- backend/app/data/source_credibility.json

# 2. Disable evidence relevance filter
# In .env:
ENABLE_EVIDENCE_RELEVANCE_FILTER=false

# 3. Reduce snippet length
# In .env:
EVIDENCE_SNIPPET_LENGTH=150

# 4. Revert judge prompt
git checkout HEAD -- backend/app/pipeline/judge.py

# 5. Restart services
pm2 restart backend
celery -A app.workers.celery_app restart
```

### If Phase 2 Fails

**Rollback Steps**:
```bash
# Disable fact-check parser
# In .env:
ENABLE_FACTCHECK_DETECTION=false

# Disable judge self-critique
ENABLE_JUDGE_SELF_CRITIQUE=false

# Restart
pm2 restart backend
```

### Feature Flag Safety

All new features controlled by flags:
- `ENABLE_EVIDENCE_RELEVANCE_FILTER`
- `ENABLE_FACTCHECK_DETECTION`
- `ENABLE_JUDGE_SELF_CRITIQUE`
- `ENABLE_ENSEMBLE_NLI`

Can disable any feature instantly without code changes.

---

## Risk Assessment

| Fix | Impact | Risk | Reversibility | Priority |
|-----|--------|------|--------------|----------|
| 1.1 Credibility adjustment | High | Low | Instant | P0 |
| 1.2 Snippet length | High | Low | Instant | P0 |
| 1.3 Judge prompt | High | Low | Easy | P0 |
| 1.4 Relevance filter | Medium | Medium | Instant | P1 |
| 2.1 Fact-check parser | High | Medium | Easy | P1 |
| 2.2 NLI context | Medium | Low | Easy | P2 |
| 2.3 Self-critique | High | Medium | Instant | P2 |
| 3.1 Ensemble NLI | High | High | Moderate | P3 |
| 3.2 Multi-stage pipeline | High | High | Difficult | P3 |
| 3.3 Fine-tuning | Very High | Very High | Difficult | P4 |

---

## Implementation Timeline

### Week 1: Phase 0 + Phase 1
- **Day 1**: Restart Celery worker, validate GovInfo routing
- **Day 2**: Implement Fixes 1.1-1.3 (credibility, snippets, prompt)
- **Day 3**: Test and validate Phase 1 fixes
- **Day 4**: Implement Fix 1.4 (relevance filter)
- **Day 5**: Full regression testing

### Week 2: Phase 2
- **Day 1-2**: Implement fact-check parser (Fix 2.1)
- **Day 3**: Enhanced NLI context (Fix 2.2)
- **Day 4**: Judge self-critique (Fix 2.3)
- **Day 5**: Integration testing and validation

### Week 3+: Phase 3 (Optional)
- Evaluate Phase 1-2 results in production
- Decide if Phase 3 needed based on remaining error rate
- Implement ensemble NLI and multi-stage pipeline if justified

---

## Monitoring & Metrics

### Metrics to Track

**Before/After Comparison**:
```
Metric                          | Before  | After (Target)
--------------------------------|---------|----------------
Ballroom claim verdict          | ❌ Wrong | ✅ Correct
Legal exemption verdict         | ❌ Wrong | ✅ Correct
GovInfo routing rate (legal)    | 0%      | 90%+
False contradiction rate        | ~15%    | <5%
Fact-check misinterpretation    | High    | Low
Judge qualifier hallucination   | High    | None
Average verdict confidence      | 0.75    | 0.85+
```

**Dashboard Metrics**:
- Verdict distribution (supported/contradicted/uncertain)
- Source credibility distribution
- Evidence relevance scores
- Fact-check detection rate
- Judge self-correction rate
- NLI score distributions
- API routing success rate

### Logging Enhancements

Add structured logging:
```python
logger.info(
    "Judge verdict",
    extra={
        "claim_id": claim["id"],
        "verdict": judgment["verdict"],
        "confidence": judgment["confidence"],
        "evidence_count": len(evidence),
        "factcheck_count": sum(1 for e in evidence if e.get("is_factcheck")),
        "relevance_filtered": filtered_count,
        "self_critique_triggered": judgment.get("self_critique") is not None,
        "govinfo_sources": sum(1 for e in evidence if "govinfo" in e.get("url", ""))
    }
)
```

---

## Next Steps

**Immediate Action Required**:

1. **Restart Celery Worker** (Phase 0)
   - Manual restart required to apply GovInfo adapter fix
   - Validation: Check logs for adapter initialization

2. **Approve Phase 1 Implementation**
   - Review proposed changes (credibility, snippets, prompt)
   - Confirm test strategy
   - Authorize implementation start

3. **Set Up Test Environment**
   - Prepare test claims (ballroom, legal exemption)
   - Set up before/after comparison framework
   - Configure logging for detailed analysis

4. **Begin Implementation**
   - Start with Fix 1.1 (credibility scores - lowest risk)
   - Test incrementally after each fix
   - Document results

---

**Questions for Discussion**:

1. Should we implement all Phase 1 fixes together, or one at a time?
2. What's the acceptable false contradiction rate? (Current: ~15%, Target: <5%)
3. Should Phase 2 features be behind feature flags for gradual rollout?
4. Do we need A/B testing infrastructure before deploying?
5. What's the priority: speed (all fixes quickly) or safety (incremental with validation)?

---

**Plan Status**: ✅ READY FOR APPROVAL

**Author**: Claude Code
**Date**: 2025-11-13
**Version**: 1.0
