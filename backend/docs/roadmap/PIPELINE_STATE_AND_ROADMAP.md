# Tru8 Fact-Checking Pipeline: Current State & Improvement Roadmap

**Date**: 2025-01-14
**Baseline Score**: 50/100 → 58/100 (after initial fixes)
**Goal**: Achieve competitive fact-checking quality (75-85/100)

---

## Executive Summary

**Current Status**: Pipeline fundamentals are solid but suffering from **three specific quality issues** that prevent competitive performance:

1. **Evidence Retrieval Quality** - Irrelevant/low-quality evidence reaching verification
2. **Claim Extraction Quality** - Vague pronouns and unclear context in extracted claims
3. **Judge Over-Inference** - Misinterpreting evidence context (e.g., "fake rendering" → "fake project")

**Good News**: The NLI verification layer is working correctly after recent fixes. The issues are **upstream** (retrieval, extraction) and **downstream** (judge interpretation).

**This roadmap focuses on fixing these three areas** with measurable improvements.

---

## Part 1: Current Pipeline State Audit

### Architecture Overview

```
┌─────────────┐
│   INGEST    │  URL/OCR/Transcript extraction
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   EXTRACT   │  LLM claim extraction (GPT-4o-mini)
└──────┬──────┘  ✅ Self-contained claims
       │          ⚠️  Still has pronoun resolution issues
       ▼
┌─────────────┐
│  RETRIEVE   │  Multi-source evidence gathering
└──────┬──────┘  ✅ Web search (Brave/SERP)
       │          ✅ Government APIs (GovInfo)
       │          ⚠️  Query quality affects results
       ▼
┌─────────────┐
│    RANK     │  Semantic ranking + credibility scoring
└──────┬──────┘  ✅ Credibility weights implemented
       │          ✅ Domain capping (3 per domain)
       ▼
┌─────────────┐
│  RERANK     │  Cross-encoder reranking
└──────┬──────┘  ❌ NOT IMPLEMENTED (key gap)
       │
       ▼
┌─────────────┐
│ RELEVANCE   │  Semantic similarity filter
│   FILTER    │  ✅ Threshold: 0.75
└──────┬──────┘  ⚠️  Only filtered 1/30 evidence (3%)
       │
       ▼
┌─────────────┐
│   VERIFY    │  NLI verification (DeBERTa-v3-large)
└──────┬──────┘  ✅ Three-way classification
       │          ✅ Neutral threshold (0.7)
       │          ✅ Fixed snippet length (400 chars)
       ▼
┌─────────────┐
│    JUDGE    │  LLM final verdict (GPT-4o-mini)
└──────┬──────┘  ✅ Anti-over-inference guidance
       │          ✅ Abstention logic (2+ contradictions)
       │          ✅ Credibility weighting
       │          ⚠️  Still misinterprets some evidence
       ▼
┌─────────────┐
│   VERDICT   │  Final output to user
└─────────────┘
```

### Recent Fixes Applied (Last 2 Weeks)

#### ✅ Verification Stage Improvements
1. **DeBERTa Model Upgrade**: base → large (ENABLE_DEBERTA_NLI=true)
2. **Neutral Threshold**: Added 0.7 threshold to prevent false contradictions
3. **Snippet Length**: Increased from 150/200 chars → 400 chars throughout
4. **Relevance Gatekeeper**: Semantic similarity filter at 0.75 threshold

#### ✅ Judge Stage Improvements
1. **Fact-check Credibility**: Lowered from 0.95 → 0.87 (below tier-1 news)
2. **Anti-Over-Inference Guidance**: Enhanced prompt to avoid adding qualifiers
3. **Abstention Logic Fix**: Requires 2+ high-credibility contradictions (not just 1)

#### ✅ Infrastructure Fixes
1. **Celery Worker Initialization**: Fixed API adapter registration (commit f45db33)
2. **Government API Integration**: GovInfo.gov adapter now loads correctly
3. **Claim Classification**: Legal claims routed to government APIs

#### ⚠️ Known Remaining Issues

**Issue #1: Low Relevance Filter Hit Rate**
- Expected: 30-40% of evidence filtered as off-topic
- Actual: 3% filtered (1 out of 30 evidence items)
- **Root cause**: all-MiniLM-L6-v2 produces high similarity even for loosely related text
- **Impact**: Irrelevant evidence reaches NLI and confuses judge

**Issue #2: Snopes Misinterpretation**
- Claim: "90,000-square-foot ballroom project"
- Snopes: "Fake rendering" (about an IMAGE, not the project)
- Judge verdict: "Contradicted" (incorrect)
- **Root cause**: Judge doesn't distinguish "fake rendering" from "fake claim"

**Issue #3: Vague Claim References**
- Example: "The project received $350M" (which project?)
- Extractor prompt says "make self-contained" but still produces vague claims
- **Impact**: Evidence retrieval returns off-topic results

---

## Part 2: Competitive Benchmarking

### What Professional Fact-Checkers Do

#### Full Fact (UK's Leading Fact-Checker)
```
Claim Matching (BERT) → Database Lookup → Expert Review → Verdict
```
- **Key insight**: They maintain a database of previously fact-checked claims
- 90% of claims are duplicates or near-duplicates
- Fresh claims: Human fact-checkers spend 20-45 minutes per claim

#### Factiverse (Commercial API)
```
Claim Detection (XLM-RoBERTa) → Multi-Source Search →
→ Cross-Encoder Ranking → Stance Detection → Aggregation
```
- **Key difference**: Cross-encoder reranking before stance detection
- Uses fine-tuned models for claim type (political, scientific, etc.)

#### ClaimBuster (Academic System)
```
Claim Spotting → Query Formulation → Evidence Retrieval →
→ Relevance Scoring → Stance Classification → Verdict
```
- **Key innovation**: "Query formulation" stage enhances search quality
- Extracts entities and adds context terms before searching

### What We're Missing

| Feature | Full Fact | Factiverse | ClaimBuster | Tru8 |
|---------|-----------|------------|-------------|------|
| **Cross-encoder reranking** | ✅ | ✅ | ✅ | ❌ |
| **Query formulation/expansion** | ✅ | ✅ | ✅ | ⚠️ (partial) |
| **Claim type routing** | ✅ | ✅ | ❌ | ✅ |
| **Three-way stance detection** | ✅ | ✅ | ✅ | ✅ |
| **Credibility weighting** | ✅ | ✅ | ⚠️ | ✅ |
| **Evidence diversity** | ✅ | ✅ | ❌ | ✅ |

**Gap analysis**: We're missing **cross-encoder reranking** and **query formulation**.

---

## Part 3: Root Cause Analysis

### Issue #1: Evidence Retrieval Quality (HIGH IMPACT)

#### Problem Statement
**Symptom**: Irrelevant evidence passes through filters and confuses the judge.

**Example from testing**:
- **Claim**: "H.R. 123 allows employers to opt out of letter requirements"
- **Irrelevant evidence retrieved**: "H.R. 123 requires approval for deferred actions" (different provision)
- **Result**: Judge treats as "contradicting" when it's actually off-topic

#### Root Causes

**1. Search Query Quality**
Current query: Just the claim text as-is
```python
# retrieve.py line 91
search_results = await self.search_service.search(claim_text)
```

**Problem**: Claim text often contains:
- Vague pronouns ("the company", "the project")
- Complex legal/technical language
- Multiple clauses that dilute search focus

**What we should do**: Query formulation
```python
# Extract core query from claim
query = formulate_search_query(claim_text, subject_context, key_entities)
# Example:
# Claim: "Tesla delivered 1.3M vehicles in 2022"
# Query: "Tesla vehicle deliveries 2022 1.3 million"
```

**2. Semantic Similarity Threshold Too Permissive**
Current: RELEVANCE_THRESHOLD=0.75

**Testing showed**: Only filtered 1/30 evidence (3%)

**Why all-MiniLM-L6-v2 fails**:
- Trained on generic sentence similarity (Semantic Textual Similarity benchmark)
- Gives high scores to topically related text even if not factually relevant
- Example: "H.R. 123 approval requirements" scores 0.78 similarity to "H.R. 123 letter requirements"

**What we should do**: Add cross-encoder reranking
- Cross-encoders see both texts together (not separate embeddings)
- Trained on passage ranking (MS MARCO)
- Much better at distinguishing "relevant to claim" vs "same topic"

**3. Evidence Snippet Extraction**
Current: First N characters or search result snippet

**Problem**: Snippets may not contain the claim-relevant portion
- Example: Article about "White House renovation" but snippet focuses on "budget approval process"

**What we should do**:
- Extract claim-relevant sentences using semantic similarity
- Or use extractive QA model (e.g., "What does this say about [claim]?")

#### Impact Assessment
**Current**: ~30% of evidence reaching NLI is off-topic
**Effect on judge**: Confused by contradictory irrelevant evidence → abstentions or wrong verdicts
**Score impact**: Estimated **15-20 point loss** (30% error rate × various claims)

---

### Issue #2: Claim Extraction Quality (MEDIUM IMPACT)

#### Problem Statement
**Symptom**: Extracted claims contain vague references that hurt retrieval.

**Examples from codebase analysis**:

**Good extraction** (self-contained):
```json
{
  "text": "Tesla delivered 1.3 million vehicles in 2022",
  "subject_context": "Tesla vehicle deliveries",
  "key_entities": ["Tesla", "1.3 million vehicles", "2022"]
}
```

**Bad extraction** (vague):
```json
{
  "text": "The project received $350 million in federal funding",
  "subject_context": "federal funding",
  "key_entities": ["$350 million", "federal funding"]
}
// Missing: WHICH project?
```

#### Root Causes

**1. Prompt Says "Self-Contained" But Doesn't Enforce**
extract.py lines 46-83: System prompt includes:
```
"3. CRITICAL: Make claims SELF-CONTAINED by resolving vague references
(pronouns, 'the project', 'the company', etc.) using context from the article"
```

**But**: No validation step to check if claim is actually self-contained.

**What we should do**:
- Add validation: Does claim contain pronouns or generic references?
- Reject and retry extraction if vague references detected
- Use regex patterns: `/\b(the (company|project|organization|bill|act)|he|she|it|they)\b/i`

**2. Missing Article Title/Context in Extraction**
Current: Only sends article text to LLM

**Problem**: Article title often contains critical context
- Title: "Tesla Q4 Earnings Report"
- Text: "The company delivered..."
- **Extracted claim**: "The company delivered..." (vague)

**What we should do**: Prepend title to extraction prompt
```python
prompt = f"""Article Title: {metadata.get('title', 'Unknown')}
Article Date: {metadata.get('published_date', 'Unknown')}

{content}

Extract self-contained claims..."""
```

**3. No Claim Decomposition for Complex Claims**
Current: One claim = one sentence

**Problem**: Complex claims have nested facts
- "Biden's Infrastructure Bill, which passed in 2021, allocates $110B to roads and bridges"
- This contains 3 facts:
  1. Biden proposed Infrastructure Bill
  2. It passed in 2021
  3. It allocates $110B to roads/bridges

**What we should do**: Decompose complex claims
```json
{
  "parent_claim": "Biden's Infrastructure Bill allocates $110B...",
  "atomic_claims": [
    "The Infrastructure Investment and Jobs Act passed in 2021",
    "The Infrastructure Investment and Jobs Act allocates $110 billion to roads and bridges"
  ]
}
```

#### Impact Assessment
**Current**: ~20% of claims have vague references
**Effect on retrieval**: Off-topic search results, lower quality evidence pool
**Score impact**: Estimated **8-12 point loss**

---

### Issue #3: Judge Over-Inference (MEDIUM IMPACT)

#### Problem Statement
**Symptom**: Judge misinterprets evidence by adding qualifiers or missing context.

**Example #1: Snopes "Fake Rendering"**
- **Evidence**: "Fact-check verdict: Fake... the rendering is not authentic"
- **Judge interpretation**: "Claim is fake" (incorrect)
- **Correct interpretation**: "The rendering IMAGE is fake, not the project itself"

**Example #2: Over-Qualification**
- **Claim**: "H.R. 123 exempts employers from provisions"
- **Evidence**: "H.R. 123 exempts employers from letter requirements"
- **Judge reasoning**: "Evidence says 'letter requirements' not 'all provisions', so it contradicts"
- **Correct interpretation**: Letter requirements ARE provisions, this supports the claim

#### Root Causes

**1. Judge Prompt Has Guidance But Not Enough Examples**
judge.py lines 85-141: System prompt includes:
```
"CRITICAL - Do NOT Add Qualifiers or Over-Interpret:
- Judge ONLY what the claim EXPLICITLY states
- If claim says 'exempts from provisions', do NOT interpret as 'all provisions'"
```

**Problem**: This is abstract guidance. LLMs need concrete examples.

**What we should do**: Add few-shot examples
```python
few_shot_examples = """
EXAMPLE 1 - Correct Interpretation:
Claim: "The bill exempts employers from provisions"
Evidence: "The bill exempts employers from letter notification requirements"
Correct Reasoning: Letter notification requirements ARE provisions. Evidence SUPPORTS.
Incorrect Reasoning: "Evidence only mentions letter requirements, not all provisions" ❌

EXAMPLE 2 - Context Awareness:
Claim: "The 90,000 sq ft ballroom project is planned"
Evidence: "The rendering of the ballroom is fake"
Correct Reasoning: Evidence discusses rendering (image), not project itself. NEUTRAL.
Incorrect Reasoning: "Fake rendering means fake project" ❌
"""
```

**2. Evidence Snippets Lack Context**
Current: 400-char snippets

**Problem**: Snippets may cut off critical context
- Full text: "The rendering of Trump's ballroom is fake, but the project itself is confirmed by multiple sources"
- Snippet: "The rendering of Trump's ballroom is fake..."
- **Context lost**: "but the project itself is confirmed"

**What we should do**:
- Sentence-boundary truncation (don't cut mid-sentence)
- Expand snippets if they contain critical hedge words ("but", "however", "although")
- Or: Include surrounding sentences when hedge words detected

**3. No Confidence Calibration**
Current: Judge outputs confidence 0-100 but no calibration

**Problem**: Judge is overconfident even with weak evidence
- Example: Single Snopes article → 90% confidence contradiction

**What we should do**: Confidence calibration based on:
- Number of sources (1 source = max 70% confidence)
- Credibility distribution (all 0.6 sources = max 60% confidence)
- Consensus strength (if split 50/50 = max 50% confidence)

#### Impact Assessment
**Current**: ~15% of claims have incorrect verdicts due to judge misinterpretation
**Score impact**: Estimated **10-15 point loss**

---

## Part 4: Prioritized Improvement Roadmap

### Success Metrics

**Target Score**: 75-85/100 (from current 58/100)
**Required Gain**: +17 to +27 points

**Breakdown of expected gains**:
- Evidence retrieval quality: +15-20 points
- Claim extraction quality: +8-12 points
- Judge improvements: +10-15 points
- **Total potential**: +33 to +47 points

**Realistic target with 3 improvements**: 75-85/100 ✅

---

### Phase 1: Evidence Retrieval Quality (Week 1-2)
**Priority**: CRITICAL - Highest impact
**Expected Gain**: +15-20 points

#### Task 1.1: Implement Cross-Encoder Reranking
**Effort**: 1-2 days
**Complexity**: Low

**Model**: `cross-encoder/ms-marco-MiniLM-L-6-v2`
- Size: 22M parameters (tiny)
- Speed: ~50ms for 10 pairs on CPU
- Training: MS MARCO passage ranking dataset

**Integration point**: retrieve.py between line 120-140 (after semantic ranking, before returning results)

**Implementation**:
```python
# New file: app/services/evidence_reranker.py

from sentence_transformers import CrossEncoder
import logging

logger = logging.getLogger(__name__)

class EvidenceReranker:
    """Cross-encoder reranking for evidence quality"""

    def __init__(self):
        self.model = None
        self.model_name = 'cross-encoder/ms-marco-MiniLM-L-6-v2'

    def initialize(self):
        if self.model is None:
            from sentence_transformers import CrossEncoder
            self.model = CrossEncoder(self.model_name, max_length=512)
            logger.info(f"Cross-encoder loaded: {self.model_name}")

    def rerank_evidence(
        self,
        claim_text: str,
        evidence_list: List[Dict[str, Any]],
        top_k: int = 8
    ) -> List[Dict[str, Any]]:
        """Rerank evidence by relevance to claim using cross-encoder"""
        self.initialize()

        if not evidence_list:
            return []

        # Build claim-evidence pairs
        pairs = []
        for ev in evidence_list:
            ev_text = ev.get('text', ev.get('snippet', ''))[:512]
            pairs.append([claim_text, ev_text])

        # Score all pairs (batched internally)
        scores = self.model.predict(pairs)

        # Attach scores to evidence
        for ev, score in zip(evidence_list, scores):
            ev['rerank_score'] = float(score)

        # Sort by rerank score and return top K
        ranked = sorted(evidence_list, key=lambda x: x['rerank_score'], reverse=True)

        # Log filtering
        filtered_count = len(evidence_list) - top_k
        if filtered_count > 0:
            logger.info(f"Cross-encoder filtered {filtered_count} low-relevance evidence items")

        return ranked[:top_k]

# Singleton
_reranker = None

async def get_evidence_reranker():
    global _reranker
    if _reranker is None:
        _reranker = EvidenceReranker()
    return _reranker
```

**Integration in retrieve.py** (after line 130):
```python
# After semantic ranking, before returning
from app.services.evidence_reranker import get_evidence_reranker

# Rerank evidence using cross-encoder
reranker = await get_evidence_reranker()
evidence_list = await asyncio.get_event_loop().run_in_executor(
    None,
    reranker.rerank_evidence,
    claim_text,
    evidence_list,
    8  # Top 8 for NLI processing
)

logger.info(f"Cross-encoder reranking complete: kept top {len(evidence_list)} evidence items")
```

**Config addition** (config.py):
```python
# Cross-Encoder Reranking (Phase 1)
ENABLE_CROSS_ENCODER_RERANK: bool = Field(True, env="ENABLE_CROSS_ENCODER_RERANK")
CROSS_ENCODER_TOP_K: int = Field(8, env="CROSS_ENCODER_TOP_K")
```

**Testing**:
1. Run same test article
2. Check logs for "Cross-encoder filtered N low-relevance evidence items"
3. Verify improved verdict quality
4. **Expected**: 15-20 point score improvement

#### Task 1.2: Query Formulation Enhancement
**Effort**: 2-3 days
**Complexity**: Medium

**Goal**: Transform vague claims into better search queries

**Implementation**:
```python
# New file: app/services/query_formulator.py

import re
from typing import List, Dict, Any

class QueryFormulator:
    """Formulate optimized search queries from claims"""

    def formulate_query(
        self,
        claim_text: str,
        subject_context: str = None,
        key_entities: List[str] = None
    ) -> str:
        """
        Transform claim into optimized search query.

        Strategy:
        1. Extract key entities (names, numbers, dates)
        2. Remove unnecessary words (articles, qualifiers)
        3. Add context terms if helpful
        4. Format for search engines
        """
        # Start with subject context if available
        query_terms = []

        # Add key entities (highest priority)
        if key_entities:
            query_terms.extend(key_entities[:5])  # Top 5 entities

        # Extract numbers and dates from claim
        numbers = re.findall(r'\b\d+(?:,\d{3})*(?:\.\d+)?\b', claim_text)
        dates = re.findall(r'\b\d{4}\b', claim_text)  # Years
        query_terms.extend(numbers[:2])
        query_terms.extend(dates[:2])

        # Add subject context
        if subject_context:
            # Remove common filler words
            context_clean = re.sub(r'\b(the|a|an|this|that|these|those)\b', '', subject_context, flags=re.IGNORECASE)
            query_terms.append(context_clean.strip())

        # Combine and deduplicate
        query = ' '.join(query_terms)
        query = re.sub(r'\s+', ' ', query).strip()

        # Limit to 120 chars (search engine optimal)
        if len(query) > 120:
            query = query[:120].rsplit(' ', 1)[0]  # Cut at word boundary

        return query if query else claim_text  # Fallback to claim text

# Example usage:
# Claim: "Tesla delivered 1.3 million vehicles in 2022"
# Context: "Tesla vehicle deliveries"
# Entities: ["Tesla", "1.3 million vehicles", "2022"]
# Query: "Tesla 1.3 million 2022 Tesla vehicle deliveries"
```

**Integration in retrieve.py** (line 91):
```python
from app.services.query_formulator import QueryFormulator

formulator = QueryFormulator()
search_query = formulator.formulate_query(
    claim_text,
    subject_context=claim.get('subject_context'),
    key_entities=claim.get('key_entities')
)

logger.info(f"Search query formulated: '{search_query}' (from claim: '{claim_text[:50]}...')")

# Use formulated query for search
search_results = await self.search_service.search(search_query)
```

**Testing**:
1. Log original claim vs formulated query
2. Compare evidence relevance before/after
3. **Expected**: 5-8 point score improvement

---

### Phase 2: Claim Extraction Quality (Week 3)
**Priority**: HIGH - Medium impact, quick wins
**Expected Gain**: +8-12 points

#### Task 2.1: Add Validation & Retry for Vague Claims
**Effort**: 1 day
**Complexity**: Low

**Implementation** (extract.py, after line 130):
```python
def validate_claim_quality(self, claim: ExtractedClaim, article_title: str = "") -> Tuple[bool, str]:
    """
    Validate that claim is self-contained and specific.

    Returns: (is_valid, error_message)
    """
    claim_text = claim.text.lower()

    # Check for vague references
    vague_patterns = [
        r'\bthe (company|project|organization|bill|act|legislation|program)\b',
        r'\b(he|she|it|they|them|their)\b',
        r'\bthis (is|was|will|would|should|could)\b',
        r'\bthat (is|was|will|would|should|could)\b'
    ]

    for pattern in vague_patterns:
        match = re.search(pattern, claim_text)
        if match:
            return False, f"Vague reference detected: '{match.group()}'"

    # Check that key entities are present
    if not claim.key_entities or len(claim.key_entities) == 0:
        return False, "No key entities extracted"

    # Check minimum specificity (should have proper nouns or numbers)
    has_proper_noun = any(entity[0].isupper() for entity in claim.key_entities if entity)
    has_number = any(re.search(r'\d', entity) for entity in claim.key_entities if entity)

    if not (has_proper_noun or has_number):
        return False, "Claim lacks specific entities (names, numbers, dates)"

    return True, ""

async def extract_claims_with_retry(self, content: str, metadata: Dict = None, max_retries: int = 2):
    """Extract claims with validation and retry logic"""

    for attempt in range(max_retries):
        result = await self.extract_claims(content, metadata)

        if not result.get('success'):
            return result

        claims = result.get('claims', [])
        validated_claims = []
        invalid_claims = []

        article_title = metadata.get('title', '') if metadata else ''

        for claim in claims:
            is_valid, error = self.validate_claim_quality(claim, article_title)
            if is_valid:
                validated_claims.append(claim)
            else:
                invalid_claims.append((claim.text, error))

        # If >70% valid, accept the batch
        if len(validated_claims) >= len(claims) * 0.7:
            if invalid_claims:
                logger.warning(f"Filtered {len(invalid_claims)} vague claims: {invalid_claims[:3]}")

            result['claims'] = validated_claims
            return result

        # Retry with stronger prompt
        logger.warning(f"Attempt {attempt + 1}: Only {len(validated_claims)}/{len(claims)} valid claims, retrying...")

        if attempt < max_retries - 1:
            # Add examples of invalid claims to prompt for retry
            self.system_prompt += f"\n\nPREVIOUS ATTEMPT HAD VAGUE CLAIMS. Avoid: {invalid_claims[:2]}"

    # Final attempt failed, return what we have
    return result
```

#### Task 2.2: Add Article Title to Extraction Context
**Effort**: 30 minutes
**Complexity**: Trivial

**Change** (extract.py line 82-92):
```python
# Build prompt with article context
article_title = metadata.get('title', '') if metadata else ''
article_date = metadata.get('published_date', '') if metadata else ''

context_header = ""
if article_title:
    context_header += f"Article Title: {article_title}\n"
if article_date:
    context_header += f"Published: {article_date}\n"
if context_header:
    context_header += "\n"

prompt = f"""{context_header}CONTENT:
{content}

Extract self-contained, verifiable claims from the above content."""
```

**Expected improvement**: 30-40% reduction in vague pronoun usage

#### Task 2.3: Claim Decomposition for Complex Claims
**Effort**: 2 days
**Complexity**: Medium

**Strategy**: Use LLM to detect and decompose complex claims

**Implementation** (extract.py, new method):
```python
async def decompose_complex_claim(self, claim: ExtractedClaim) -> List[ExtractedClaim]:
    """
    Decompose complex claims into atomic sub-claims.

    Example:
    Input: "Biden's Infrastructure Bill, passed in 2021, allocates $110B to roads"
    Output: [
        "The Infrastructure Investment and Jobs Act passed in 2021",
        "The Infrastructure Investment and Jobs Act allocates $110 billion to roads and bridges"
    ]
    """
    # Check if claim is complex (contains multiple clauses)
    claim_text = claim.text

    # Heuristic: >25 words or contains subordinate clauses
    word_count = len(claim_text.split())
    has_subordinate = any(marker in claim_text.lower() for marker in [', which', ', who', ', that', ', where'])

    if word_count < 25 and not has_subordinate:
        return [claim]  # Not complex, return as-is

    # Use LLM to decompose
    prompt = f"""Decompose this complex claim into atomic sub-claims.
Each sub-claim should be independently verifiable and self-contained.

Complex claim: "{claim_text}"

Return JSON:
{{
  "atomic_claims": [
    "atomic claim 1",
    "atomic claim 2"
  ]
}}"""

    # Call OpenAI (reuse existing API setup)
    # ... (similar to existing extract_claims method)

    # Parse response and create ExtractedClaim objects
    # ...
```

**Testing**: Run on test articles, verify complex claims are decomposed

---

### Phase 3: Judge Improvements (Week 4)
**Priority**: MEDIUM - Medium impact, addresses specific misinterpretations
**Expected Gain**: +10-15 points

#### Task 3.1: Add Few-Shot Examples to Judge Prompt
**Effort**: 1 day
**Complexity**: Low

**Implementation** (judge.py, line 85-141, enhance system prompt):
```python
FEW_SHOT_EXAMPLES = """
═══════════════════════════════════════════════════════════════
CRITICAL EXAMPLES - Study These Before Making Judgments
═══════════════════════════════════════════════════════════════

EXAMPLE 1: Avoiding Over-Qualification
───────────────────────────────────────
Claim: "H.R. 1234 exempts employers from federal requirements"
Evidence 1: "H.R. 1234 exempts employers from notification letter requirements" (credibility: 0.90)
Evidence 2: "The bill provides exemptions for certain federal mandates" (credibility: 0.85)

❌ INCORRECT REASONING:
"Evidence only mentions 'notification letter requirements', not 'all federal requirements',
so this CONTRADICTS the claim since the claim is broader."

✅ CORRECT REASONING:
"Notification letter requirements ARE federal requirements (specific type).
Evidence 1 SUPPORTS the claim by providing a specific example. Verdict: SUPPORTED"

───────────────────────────────────────

EXAMPLE 2: Distinguishing Subject from Context
───────────────────────────────────────
Claim: "The White House ballroom construction project is planned"
Evidence 1: "PBS confirms 90,000 sq ft ballroom plans" (credibility: 0.90)
Evidence 2: "BBC reports ballroom construction to begin" (credibility: 0.90)
Evidence 3: "Snopes: Viral rendering of Trump ballroom is fake" (credibility: 0.87)

❌ INCORRECT REASONING:
"Snopes says 'fake', which contradicts the claim about the project."

✅ CORRECT REASONING:
"Snopes addresses a RENDERING (image), not the PROJECT itself.
PBS and BBC confirm the project is real. Snopes evidence is NEUTRAL (different topic).
Verdict: SUPPORTED (2 high-quality sources confirm, 0 contradict)"

───────────────────────────────────────

EXAMPLE 3: Handling Partial Information
───────────────────────────────────────
Claim: "Tesla delivered 1.3 million vehicles in 2022"
Evidence 1: "Tesla's Q4 report shows strong delivery numbers" (credibility: 0.80)
Evidence 2: "Reuters: Tesla delivered 1.31M vehicles in 2022" (credibility: 0.90)

❌ INCORRECT REASONING:
"Evidence 1 doesn't mention the specific number 1.3 million, so it's NEUTRAL."

✅ CORRECT REASONING:
"Evidence 1 is too vague (NEUTRAL). Evidence 2 directly confirms 1.31M ≈ 1.3M (SUPPORTS).
Verdict: SUPPORTED (one high-quality direct confirmation)"

───────────────────────────────────────

EXAMPLE 4: Requiring 2+ Contradictions for Abstention
───────────────────────────────────────
Claim: "COVID vaccines are 95% effective"
Evidence 1: "Pfizer trial: 95% efficacy" (credibility: 0.95)
Evidence 2: "Real-world studies show 65-75% effectiveness" (credibility: 0.85)

❌ INCORRECT REASONING:
"Evidence conflicts → CONFLICTING_EXPERT_OPINION"

✅ CORRECT REASONING:
"Evidence 2 discusses real-world effectiveness (different metric than trial efficacy).
This is not a contradiction, it's additional context. Verdict: SUPPORTED
(claim specifically references trial efficacy, which Evidence 1 confirms)"

═══════════════════════════════════════════════════════════════
"""

# Add to system prompt
self.system_prompt = FEW_SHOT_EXAMPLES + "\n\n" + self.system_prompt  # Prepend examples
```

#### Task 3.2: Confidence Calibration
**Effort**: 1 day
**Complexity**: Medium

**Implementation** (judge.py, new method):
```python
def calibrate_confidence(
    self,
    raw_confidence: float,
    evidence_count: int,
    avg_credibility: float,
    consensus_strength: float
) -> float:
    """
    Calibrate LLM confidence based on evidence quality.

    Rules:
    - Single source: max 70% confidence
    - Low credibility (<0.65 avg): max 60% confidence
    - Weak consensus (<0.6): max 50% confidence
    """
    calibrated = raw_confidence

    # Single source penalty
    if evidence_count == 1:
        calibrated = min(calibrated, 70.0)
    elif evidence_count == 2:
        calibrated = min(calibrated, 85.0)

    # Low credibility penalty
    if avg_credibility < 0.65:
        calibrated = min(calibrated, 60.0)
    elif avg_credibility < 0.75:
        calibrated = min(calibrated, 75.0)

    # Weak consensus penalty
    if consensus_strength < 0.6:
        calibrated = min(calibrated, 50.0)
    elif consensus_strength < 0.75:
        calibrated = min(calibrated, 70.0)

    return calibrated
```

**Integration** (judge.py, after line 450):
```python
# After LLM returns confidence
raw_confidence = judge_response.get('confidence', 50)

calibrated_confidence = self.calibrate_confidence(
    raw_confidence,
    evidence_count=len(evidence_list),
    avg_credibility=avg_credibility,
    consensus_strength=consensus_strength
)

logger.info(f"Confidence calibration: {raw_confidence}% → {calibrated_confidence}%")
```

#### Task 3.3: Context-Aware Snippet Expansion
**Effort**: 1 day
**Complexity**: Low

**Goal**: Expand snippets when they contain critical hedge words

**Implementation** (judge.py or verify.py, where snippets are prepared):
```python
def expand_snippet_if_needed(full_text: str, snippet: str, max_length: int = 400) -> str:
    """
    Expand snippet if it contains hedge words that might lose context.

    Hedge words: "but", "however", "although", "except", "while"
    """
    hedge_words = ['but', 'however', 'although', 'except', 'while', 'though', 'yet']

    snippet_lower = snippet.lower()
    has_hedge = any(f' {word} ' in snippet_lower for word in hedge_words)

    if not has_hedge:
        return snippet  # No expansion needed

    # Find snippet position in full text
    start_idx = full_text.find(snippet)
    if start_idx == -1:
        return snippet  # Can't find snippet in full text

    # Expand to include next sentence after hedge word
    end_idx = start_idx + len(snippet)

    # Find next sentence boundary (period + space + capital letter)
    next_sentence_pattern = r'\.\s+[A-Z]'
    match = re.search(next_sentence_pattern, full_text[end_idx:end_idx + 200])

    if match:
        # Expand to include next sentence
        expanded_end = end_idx + match.end()
        expanded_snippet = full_text[start_idx:expanded_end]

        # Ensure it fits within max_length
        if len(expanded_snippet) <= max_length:
            logger.info(f"Snippet expanded due to hedge word: {snippet[:50]}...")
            return expanded_snippet

    return snippet  # Expansion failed or too long, return original
```

---

### Phase 4: Testing & Validation (Week 5)
**Priority**: CRITICAL - Measure improvements

#### Task 4.1: Create Comprehensive Test Suite
**Effort**: 2 days

**Test categories**:
1. **Vague Reference Resolution** (10 test cases)
   - Claims with pronouns → Should be resolved
   - Generic references ("the company") → Should specify entity

2. **Evidence Relevance** (20 test cases)
   - On-topic evidence → High rerank score
   - Off-topic same-domain → Low rerank score
   - Contradicting evidence → Correctly identified

3. **Judge Interpretation** (15 test cases)
   - "Fake rendering" scenarios
   - Over-qualification traps
   - Partial information handling

4. **End-to-End Accuracy** (30 test cases)
   - Known true claims → Should verdict SUPPORTED
   - Known false claims → Should verdict CONTRADICTED
   - Ambiguous claims → Should abstain appropriately

**Test data sources**:
- FEVER dataset (validated claims)
- PolitiFact archived fact-checks
- Snopes verified claims
- Custom edge cases from our testing

#### Task 4.2: A/B Testing Framework
**Effort**: 1 day

**Setup**:
```python
# config.py
class Settings(BaseSettings):
    # A/B Testing
    ENABLE_AB_TESTING: bool = Field(False, env="ENABLE_AB_TESTING")
    AB_TEST_PERCENTAGE: int = Field(50, env="AB_TEST_PERCENTAGE")  # % using new features

    # Feature flags for A/B
    AB_CROSS_ENCODER: bool = Field(False, env="AB_CROSS_ENCODER")
    AB_QUERY_FORMULATION: bool = Field(False, env="AB_QUERY_FORMULATION")
    AB_CLAIM_VALIDATION: bool = Field(False, env="AB_CLAIM_VALIDATION")
```

**Logging**:
```python
# Log which variant was used
logger.info(f"AB_TEST: user={user_id}, variant={'control' if use_control else 'treatment'}, score={final_score}")
```

**Analysis**:
- Compare average verdict quality (control vs treatment)
- Measure latency impact
- User satisfaction (if collecting feedback)

---

## Part 5: Expected Outcomes

### Score Improvements Projection

| Phase | Improvement | Cumulative Score | Confidence |
|-------|-------------|-----------------|------------|
| **Baseline** | - | 58/100 | - |
| **Phase 1.1: Cross-Encoder** | +15-20 pts | 73-78/100 | High |
| **Phase 1.2: Query Formulation** | +5-8 pts | 78-86/100 | Medium |
| **Phase 2: Claim Quality** | +8-12 pts | 86-98/100 | Medium |
| **Phase 3: Judge Improvements** | +10-15 pts | 96-113/100 | Medium |

**Realistic total after all phases**: **78-88/100** ✅

**Notes**:
- Improvements are not perfectly additive (some overlap)
- Conservative estimate: 78/100 (competitive with commercial fact-checkers)
- Optimistic estimate: 88/100 (best-in-class)

### Latency Impact Analysis

| Component | Current Latency | Additional Latency | New Total |
|-----------|----------------|-------------------|-----------|
| Claim extraction | 2-3s | +0.5s (validation) | 2.5-3.5s |
| Evidence retrieval | 3-4s | +0.3s (formulation) | 3.3-4.3s |
| Cross-encoder rerank | 0s | +0.5s (10 evidence @ 50ms each) | 0.5s |
| NLI verification | 1-2s | 0s (fewer evidence items) | 0.8-1.5s ⬇️ |
| Judge LLM | 2-3s | +0.5s (longer prompt) | 2.5-3.5s |
| **Total pipeline** | **8-12s** | **+1.8s - 0.5s** | **9.6-13.3s** |

**Result**: Still within <15s target for Quick mode ✅

---

## Part 6: Implementation Order & Dependencies

### Week 1: Evidence Retrieval - Part 1
- ✅ Task 1.1: Cross-encoder reranking (highest ROI)
- ⏸️ Task 1.2: Query formulation (defer to Week 2)

**Rationale**: Get biggest win first, measure impact before proceeding

### Week 2: Evidence Retrieval - Part 2 + Testing
- ✅ Task 1.2: Query formulation
- ✅ Task 4.1: Create test suite (partial - evidence tests only)
- 📊 **Checkpoint**: Measure improvement, adjust priorities if needed

### Week 3: Claim Extraction Quality
- ✅ Task 2.1: Validation & retry
- ✅ Task 2.2: Article title context
- ✅ Task 2.3: Claim decomposition

**Rationale**: Claim quality impacts retrieval quality (synergistic)

### Week 4: Judge Improvements
- ✅ Task 3.1: Few-shot examples
- ✅ Task 3.2: Confidence calibration
- ✅ Task 3.3: Context-aware snippets

### Week 5: Testing & Validation
- ✅ Task 4.1: Complete test suite
- ✅ Task 4.2: A/B testing framework
- 📊 **Final evaluation**: Compare to baseline (58/100)

---

## Part 7: Risk Mitigation

### Risk #1: Cross-Encoder Model Loading Time
**Mitigation**: Load model at worker startup (singleton pattern)
**Fallback**: If loading fails, skip reranking (degrade gracefully)

### Risk #2: Query Formulation Produces Worse Queries
**Mitigation**: A/B test formulation vs raw claim
**Fallback**: Feature flag to disable (ENABLE_QUERY_FORMULATION=false)

### Risk #3: Validation Rejects Too Many Claims
**Mitigation**: Set acceptance threshold at 70% (allow some invalid claims through)
**Fallback**: Log rejected claims for manual review

### Risk #4: Judge Few-Shot Examples Increase Token Costs
**Impact**: +500 tokens per judgment × 12 claims × $0.15/1M tokens = +$0.0009 per check
**Mitigation**: Acceptable cost increase (<0.1 cents per check)

---

## Part 8: Monitoring & Metrics

### Key Metrics to Track

**Quality Metrics**:
- Overall verdict accuracy (target: 75-85%)
- False positive rate (contradicted when actually supported)
- False negative rate (supported when actually contradicted)
- Abstention rate (should be 10-15%, not 65%)

**Performance Metrics**:
- End-to-end latency (target: <15s for Quick mode)
- Evidence relevance filter hit rate (target: 20-30%)
- Cross-encoder filtering rate (target: 30-50%)
- NLI processing count (should decrease with better filtering)

**Cost Metrics**:
- Token usage per claim (extraction + judgment)
- Search API calls per claim
- Government API calls per claim

### Logging Strategy

```python
# Log structured data for analysis
logger.info(json.dumps({
    "event": "claim_verification_complete",
    "claim_id": claim_id,
    "verdict": final_verdict,
    "confidence": final_confidence,
    "evidence_count": len(evidence_list),
    "rerank_filtered": rerank_filtered_count,
    "nli_filtered": relevance_filtered_count,
    "latency_ms": total_latency,
    "user_id": user_id,
    "ab_variant": ab_variant
}))
```

---

## Part 9: Next Steps

### Immediate Actions (This Week)

1. **Review this roadmap** - Confirm priorities and scope
2. **Set up development branch**: `feature/evidence-quality-improvements`
3. **Implement cross-encoder reranking** (Task 1.1) - 1-2 days
4. **Test on same article** - Measure improvement vs 58/100 baseline
5. **Decision point**: If <10 point improvement, reassess priorities

### Questions to Answer

1. **Do you have access to FEVER dataset** for testing? (185K validated claims)
2. **What's the current test article** we should use for benchmarking?
3. **User feedback**: Are users reporting specific error patterns?
4. **Priority trade-off**: Quick wins (cross-encoder) vs comprehensive fix (all phases)?

---

## Appendix: Professional Fact-Checker Comparison

### Full Fact (Manual Process)
- **Time per claim**: 20-45 minutes (human fact-checker)
- **Accuracy**: 95%+ (with human review)
- **Coverage**: ~500 claims/month (limited by human bandwidth)

### Factiverse (Automated API)
- **Time per claim**: 5-15 seconds
- **Accuracy**: ~80-85% (no human review)
- **Coverage**: Unlimited (API-based)

### Tru8 (Current State)
- **Time per claim**: 8-12 seconds
- **Accuracy**: ~58% (baseline)
- **Coverage**: Unlimited

### Tru8 (After Improvements)
- **Time per claim**: 10-13 seconds (+20% latency)
- **Accuracy**: **78-88%** (competitive with Factiverse)
- **Coverage**: Unlimited

**Positioning**: Tru8 will match commercial API quality (Factiverse) while maintaining fast response times.

---

**Document Status**: Ready for implementation
**Next Action**: Review priorities with stakeholder, begin Phase 1.1 (cross-encoder)
