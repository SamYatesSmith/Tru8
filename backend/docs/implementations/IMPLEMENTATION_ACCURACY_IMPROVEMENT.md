# Tru8 Accuracy Improvement Implementation Plan

**Document Status:** Draft
**Last Updated:** 2024-11-07
**Owners:** Tru8 Engineering Team (implementation) + Claude Code (planning)

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Current State Analysis](#current-state-analysis)
3. [Phase 0: Evaluation Infrastructure](#phase-0-evaluation-infrastructure)
4. [Phase 1: Validated Quick Wins](#phase-1-validated-quick-wins)
5. [Phase 2: Targeted Enhancements](#phase-2-targeted-enhancements)
6. [Phase 3: Advanced Optimizations](#phase-3-advanced-optimizations)
7. [Monitoring & Metrics](#monitoring--metrics)
8. [Risk Mitigation](#risk-mitigation)
9. [Rollout Strategy](#rollout-strategy)
10. [Appendices](#appendices)

---

## Executive Summary

### Problem Statement
Current Tru8 fact-checking accuracy is approximately **30%** (user-reported estimate). This accuracy level is insufficient for user trust and product-market fit.

### Goal
Achieve **70-80% accuracy** through systematic, evidence-based pipeline improvements over 6-8 weeks.

### Approach
- **Validation-first:** All changes gated by +10 percentage point improvement on evaluation dataset
- **Feature-flagged rollout:** Every change default-off, promoted only after validation
- **Incremental deployment:** Three phases with clear success criteria

### Expected Outcomes

| Phase | Timeline | Expected Accuracy Gain | Cumulative Accuracy |
|-------|----------|------------------------|---------------------|
| **Phase 0** | Week 1 | Baseline measurement | ~30% (current) |
| **Phase 1** | Week 2-4 | +20-35 pp | ~50-65% |
| **Phase 2** | Week 5-7 | +15-25 pp | ~65-80% |
| **Phase 3** | Week 8+ | +10-20 pp | ~75-90% |

### Cost Impact
- **Phase 1:** <$10/month incremental
- **Phase 2:** ~$50-100/month (multi-model validation on hard claims)
- **Phase 3:** ~$200-300/month (NewsGuard API + advanced features)

### Resource Requirements
- **Engineering:** 1-2 FTE for 6-8 weeks
- **GPU worker:** Required for NLI model benchmarking
- **Evaluation curation:** ~40 hours for manual claim verification

---

## Current State Analysis

### Pipeline Architecture

```
URL/Image/Video Input
    ↓
┌─────────────────────────────────────────────────┐
│ INGEST (ingest.py)                              │
│ - URL: trafilatura + readability                │
│ - Image: Tesseract OCR                          │
│ - Video: YouTube transcript API                 │
└─────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────┐
│ EXTRACT (extract.py)                            │
│ - LLM: GPT-4o-mini                              │
│ - Context window: 2,500 words                   │
│ - Max claims: 12 (Quick mode)                   │
└─────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────┐
│ RETRIEVE (retrieve.py + search.py + evidence.py)│
│ - Search: Brave API or SerpAPI                  │
│ - Pool: 10 candidates per claim                 │
│ - Ranking: Bi-encoder (all-MiniLM-L6-v2)        │
│ - Final sources: 5 per claim                    │
└─────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────┐
│ VERIFY (verify.py)                              │
│ - NLI Model: facebook/bart-large-mnli           │
│ - Batch size: 8                                 │
│ - Outputs: entailment/contradiction/neutral     │
└─────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────┐
│ JUDGE (judge.py)                                │
│ - LLM: GPT-4o-mini                              │
│ - Abstention logic: 3+ sources, 0.60 consensus  │
│ - Output: supported/contradicted/uncertain      │
└─────────────────────────────────────────────────┘
    ↓
Final Verdict + Evidence + Confidence
```

### Identified Weaknesses

| Component | Current State | Impact on Accuracy |
|-----------|---------------|-------------------|
| **NLI Verifier** | BART-MNLI (general-purpose, not fact-tuned) | **HIGH** - Misses numerical/temporal nuances |
| **Evidence Ranking** | Bi-encoder only (no precision reranking) | **MEDIUM-HIGH** - Lower-quality evidence reaches judge |
| **Judge Prompt** | Zero-shot (no examples) | **MEDIUM** - Inconsistent edge case handling |
| **Evidence Pool** | 5 sources (thin consensus) | **MEDIUM** - Insufficient for confidence calibration |
| **Context Window** | 2,500 words (may truncate) | **LOW-MEDIUM** - Loses context in long articles |

### Root Cause Analysis

Based on code review and research:

1. **NLI model not optimized for fact-checking:**
   - BART-MNLI trained on academic entailment (MNLI dataset)
   - Not exposed to real-world claims, numerical precision, temporal alignment
   - DeBERTa-v3-FEVER models exist specifically for fact verification

2. **Evidence ranking lacks precision:**
   - Bi-encoders (MiniLM) encode claim and evidence separately
   - No joint attention over claim+evidence pairs
   - Cross-encoders provide 10-15% better precision but are 50x slower
   - Current flow: fetch 10 → rank with bi-encoder → filter to 5
   - Missing: cross-encoder reranking between bi-encoder and final selection

3. **Judge prompt has no few-shot grounding:**
   - LLMs perform significantly better with examples
   - Current prompt is instruction-only
   - Edge cases (numerical tolerance, conflicting sources) lack examples

4. **Abstention logic is sound but evidence pool is thin:**
   - Good: abstention when <3 sources or <60% consensus
   - Problem: Only 5 sources reduces statistical confidence
   - Cross-encoder reranking can help select better 5 from larger pool

---

## Phase 0: Evaluation Infrastructure

**Timeline:** Week 1 (5 business days)
**Owner:** Tru8 Engineering Team
**Objective:** Establish baseline accuracy and regression testing framework

### 0.1 Evaluation Dataset Assembly

**Deliverable:** 100 claims across difficulty spectrum

**Composition:**
- **40 claims from FEVER dataset** (pre-labeled, fact-verification focused)
  - Easy: 15 claims (unambiguous, well-documented facts)
  - Medium: 15 claims (require multiple sources, nuanced)
  - Hard: 10 claims (conflicting sources, expert disagreement)

- **40 claims from recent news** (manually curated and verified)
  - Short news blurbs: 20 claims (test extraction + verification)
  - Long-form policy articles: 20 claims (test context handling)

- **20 edge cases** (targeted stress tests)
  - Numerical precision: 5 claims (test tolerance logic)
  - Temporal sensitivity: 5 claims (test date handling)
  - Conflicting high-quality sources: 5 claims (test abstention)
  - Ambiguous/prediction claims: 5 claims (test uncertainty)

**Dataset Schema:**

```json
{
  "id": "easy_001",
  "claim_text": "Tesla delivered 1.31 million vehicles in 2022",
  "source_url": "https://example.com/article",
  "source_content": "[Full article text stored for replay]",

  "ground_truth": {
    "verdict": "supported",
    "confidence": 95,
    "rationale": "Official Tesla investor relations press release confirms exact figure",
    "authoritative_sources": [
      "https://ir.tesla.com/press-release/...",
      "https://www.reuters.com/business/autos/..."
    ]
  },

  "metadata": {
    "difficulty": "easy",
    "claim_type": "numerical_exact",
    "temporal_sensitivity": false,
    "domain": "business",
    "requires_context": false
  }
}
```

**Curation Process:**
1. Select FEVER claims (1 day - existing labels)
2. Research and verify 40 news claims (3 days - fact-checking)
3. Create 20 edge cases (1 day - targeted construction)
4. Store full article content for each claim (for pipeline replay)

**Success Criteria:**
- [ ] 100 claims in JSON format
- [ ] All claims have stored source content
- [ ] Ground truth verified by 2+ authoritative sources
- [ ] Balanced distribution across difficulty tiers

---

### 0.2 Evaluation Harness Implementation

**Deliverable:** Automated pipeline testing framework

**Implementation:** `backend/tests/evaluation/`

**Structure:**
```
backend/tests/evaluation/
├── __init__.py
├── datasets/
│   ├── fever_claims.json          # 40 FEVER claims
│   ├── news_claims.json           # 40 news claims
│   ├── edge_cases.json            # 20 edge cases
│   ├── all_claims.json            # Combined 100 claims
│   └── schema.json                # JSON schema definition
├── harness.py                     # Main evaluation runner
├── metrics.py                     # Accuracy, calibration calculations
├── reports/                       # Generated reports
│   └── .gitkeep
└── README.md                      # Usage instructions
```

**Core Functionality:**

**harness.py:**
- Replay stored articles through full pipeline
- Capture per-claim outputs (verdict, confidence, evidence, latency)
- Compare predictions against ground truth
- Generate detailed reports

**metrics.py:**
- Verdict accuracy (exact match %)
- Confidence calibration (Expected Calibration Error)
- Precision@K for evidence quality
- By-difficulty breakdown (easy/medium/hard)
- By-claim-type breakdown (numerical/temporal/etc.)

**Usage:**
```bash
cd backend/tests/evaluation
python harness.py --dataset all_claims.json --config baseline
```

**Success Criteria:**
- [ ] Harness runs full pipeline on 100 claims
- [ ] Generates JSON report with all metrics
- [ ] Runtime <10 minutes for full evaluation
- [ ] Per-claim outputs stored for regression testing

---

### 0.3 Baseline Measurement

**Deliverable:** Baseline accuracy report

**Metrics to Capture:**

```
OVERALL METRICS:
- Overall accuracy: [TO BE MEASURED]%
- Average confidence: [TO BE MEASURED]
- Expected Calibration Error: [TO BE MEASURED]

BY DIFFICULTY:
- Easy claims accuracy: [TO BE MEASURED]%
- Medium claims accuracy: [TO BE MEASURED]%
- Hard claims accuracy: [TO BE MEASURED]%

BY CLAIM TYPE:
- Numerical claims accuracy: [TO BE MEASURED]%
- Temporal claims accuracy: [TO BE MEASURED]%
- Scientific claims accuracy: [TO BE MEASURED]%

PIPELINE PERFORMANCE:
- Average latency per claim: [TO BE MEASURED]ms
- P95 latency: [TO BE MEASURED]ms
- Average cost per claim: [TO BE MEASURED]

ABSTENTION ANALYSIS:
- Abstention rate: [TO BE MEASURED]%
- Abstention precision (were they correct to abstain?): [TO BE MEASURED]%
```

**Report Format:** JSON + Markdown summary

**Success Criteria:**
- [ ] Baseline report published
- [ ] All 100 claims have recorded outputs
- [ ] Metrics validated by engineering team
- [ ] Baseline serves as regression benchmark

---

## Phase 1: Validated Quick Wins

**Timeline:** Week 2-4 (3 weeks)
**Owner:** Tru8 Engineering Team
**Objective:** Implement and validate 3 high-impact improvements

**Gate Criteria:** Each improvement must show:
- **+10 pp accuracy on medium claims** OR **clear wins on hard claims**
- **<10% latency increase**
- **No regressions on easy claims**

---

### 1.1 DeBERTa NLI Model Swap

**Expected Impact:** +8-15% accuracy on medium/hard claims

**Hypothesis:** BART-MNLI lacks fact-verification training. DeBERTa-v3-FEVER trained on 885k NLI pairs including FEVER dataset (fact-verification specific) will reduce borderline misclassifications.

#### Technical Implementation

**Files Modified:**
- `backend/app/core/config.py`
- `backend/app/pipeline/verify.py`

**Configuration Changes:**

```python
# config.py additions:

class Settings(BaseSettings):
    # ... existing settings ...

    # Phase 1.1: DeBERTa NLI Model Swap
    ENABLE_DEBERTA_NLI: bool = Field(
        False,  # Default OFF until validated
        env="ENABLE_DEBERTA_NLI",
        description="Use DeBERTa-v3-FEVER instead of BART-MNLI for NLI verification"
    )

    NLI_MODEL_NAME: str = Field(
        "facebook/bart-large-mnli",
        env="NLI_MODEL_NAME",
        description="NLI model identifier (legacy override)"
    )

    @property
    def nli_model_name(self) -> str:
        """Dynamic NLI model selection based on feature flag"""
        if self.ENABLE_DEBERTA_NLI:
            return "MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli"
        return self.NLI_MODEL_NAME
```

**Model Selection Rationale:**

Using **DeBERTa-v3-base** instead of DeBERTa-v3-large:
- **Parameters:** 184M (vs 434M for large)
- **Memory:** ~900MB FP16 (vs ~1.8GB for large)
- **Performance:** +5-10% over BART (vs +15% for large)
- **Rationale:** Constrained by GPU memory; base model provides most of the gain with half the footprint

**Code Changes in verify.py:**

```python
# Line 50, change from:
self.model_name = "facebook/bart-large-mnli"

# To:
self.model_name = settings.nli_model_name  # Dynamic based on flag
```

**Memory Optimization:**

Enable FP16 precision to reduce memory footprint:

```python
# verify.py load_model() function, modify:

def load_model():
    from transformers import AutoTokenizer, AutoModelForSequenceClassification
    import torch

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    tokenizer = AutoTokenizer.from_pretrained(self.model_name)
    model = AutoModelForSequenceClassification.from_pretrained(
        self.model_name,
        torch_dtype=torch.float16 if device.type == 'cuda' else torch.float32
    )
    model.to(device)
    model.eval()
    return tokenizer, model, device
```

#### Validation Plan

**Step 1: Prototype on GPU worker**
- Deploy DeBERTa model to GPU-enabled worker
- Measure memory usage (target: <1.2GB)
- Benchmark inference speed vs BART

**Step 2: Run evaluation harness**
```bash
ENABLE_DEBERTA_NLI=true python tests/evaluation/harness.py --dataset all_claims.json --config phase1_deberta
```

**Step 3: Compare metrics**
- Verdict accuracy delta (by difficulty)
- Latency delta (target: <10% increase)
- Memory footprint

**Step 4: Analyze per-claim differences**
- Identify which claims improved
- Identify any regressions
- Validate improvement patterns (numerical? temporal?)

**Success Criteria:**
- [ ] +10 pp on medium claims OR +5pp on hard claims
- [ ] <10% latency increase (target: <200ms slower)
- [ ] No regressions on easy claims (±2pp acceptable variance)
- [ ] Memory usage <1.5GB on GPU worker

**Rollback Plan:**
If validation fails:
- Set `ENABLE_DEBERTA_NLI=false`
- Model weights cached separately (no collision)
- Instant revert to BART

---

### 1.2 Judge Few-Shot Prompt Enhancement

**Expected Impact:** +5-10% accuracy on edge cases

**Hypothesis:** Judge prompt lacks grounding examples. Few-shot learning improves LLM consistency on edge cases (numerical tolerance, conflicting evidence, abstention decisions).

#### Technical Implementation

**Files Modified:**
- `backend/app/core/config.py`
- `backend/app/pipeline/judge.py`

**Configuration Changes:**

```python
# config.py additions:

class Settings(BaseSettings):
    # ... existing settings ...

    # Phase 1.2: Judge Few-Shot Prompt
    ENABLE_JUDGE_FEW_SHOT: bool = Field(
        False,  # Default OFF until validated
        env="ENABLE_JUDGE_FEW_SHOT",
        description="Include few-shot examples in judge prompt"
    )
```

**Few-Shot Examples:**

Based on team feedback, cover:
- (a) Clean support case
- (b) Contradiction with conflicting snippets
- (c) Abstention where evidence is thin
- (d) Numerical tolerance edge case

**Code Changes in judge.py:**

Add new method:

```python
def _get_few_shot_examples(self) -> str:
    """
    Return 4 few-shot examples for judge prompt.
    Covers: support, contradict, abstain (insufficient), numerical tolerance.
    """
    return """
=== EXAMPLE 1: Clean Support Case ===

CLAIM: "NASA's Perseverance rover landed on Mars on February 18, 2021"

EVIDENCE:
[1] "NASA confirmed successful touchdown at 3:55 PM EST on Feb 18, 2021"
    Source: nasa.gov, Credibility: 0.95, Published: 2021-02-18
[2] "Perseverance Mars landing confirmed by mission control"
    Source: Reuters, Credibility: 0.90, Published: 2021-02-18

VERDICT: SUPPORTED
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

VERDICT: CONTRADICTED
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

VERDICT: INSUFFICIENT_EVIDENCE
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

VERDICT: SUPPORTED
CONFIDENCE: 85
RATIONALE: Claim uses "roughly" indicating approximation. Evidence shows $320M (official gov source) and $350M (news source). Within reasonable tolerance for approximate language. High-credibility sources support the claim.

---

NOW JUDGE THE FOLLOWING CLAIM:
"""
```

**Modify `_prepare_judgment_context`:**

```python
def _prepare_judgment_context(self, claim: Dict[str, Any],
                              verification_signals: Dict[str, Any],
                              evidence: List[Dict[str, Any]]) -> str:
    """Prepare context for LLM judgment"""

    # Base context (existing implementation)
    base_context = f"""
CLAIM TO JUDGE:
{claim.get("text")}

EVIDENCE ANALYSIS:
Total Evidence Pieces: {verification_signals.get('total_evidence', 0)}
Supporting Evidence: {verification_signals.get('supporting_count', 0)} pieces
Contradicting Evidence: {verification_signals.get('contradicting_count', 0)} pieces
...
"""

    # Prepend few-shot examples if enabled
    if settings.ENABLE_JUDGE_FEW_SHOT:
        few_shot_examples = self._get_few_shot_examples()
        return f"{few_shot_examples}\n\n{base_context}"

    return base_context
```

#### Validation Plan

**Step 1: Run evaluation harness**
```bash
ENABLE_JUDGE_FEW_SHOT=true python tests/evaluation/harness.py --dataset all_claims.json --config phase1_fewshot
```

**Step 2: Compare metrics**
- Overall accuracy delta
- Edge case accuracy (filter for numerical_tolerance, conflicting_sources claim types)
- Verdict consistency (run same claim 3x, measure variance)

**Step 3: Qualitative analysis**
- Review rationale quality on edge cases
- Check if examples biased the model incorrectly
- Validate abstention precision improved

**Success Criteria:**
- [ ] +10 pp on edge cases (numerical/conflicting subset)
- [ ] Improved verdict consistency (lower variance on re-runs)
- [ ] No accuracy regression on standard claims
- [ ] Abstention precision >80% (when abstaining, was it correct?)

---

### 1.3 Cross-Encoder Reranking

**Expected Impact:** +8-12% from better evidence precision

**Hypothesis:** Bi-encoder ranking (separate embeddings) lacks precision. Cross-encoder (joint attention over claim+evidence) better identifies truly relevant passages, leading to higher-quality evidence reaching the judge.

#### Technical Implementation

**Files Modified:**
- `backend/app/core/config.py`
- `backend/app/pipeline/retrieve.py`

**Configuration Changes:**

```python
# config.py additions:

class Settings(BaseSettings):
    # ... existing settings ...

    # Phase 1.3: Cross-Encoder Reranking
    ENABLE_CROSS_ENCODER_RERANK: bool = Field(
        False,  # Default OFF until validated
        env="ENABLE_CROSS_ENCODER_RERANK",
        description="Use cross-encoder for evidence reranking after bi-encoder"
    )
```

**Code Changes in retrieve.py:**

Add new method after `_rank_evidence_with_embeddings`:

```python
async def _rerank_with_cross_encoder(
    self,
    claim_text: str,
    evidence_list: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Rerank evidence using cross-encoder for precision.

    Flow:
    1. Bi-encoder has already ranked 10 candidates
    2. Cross-encoder scores all 10 with full attention
    3. Sort by cross-encoder score
    4. Persist both scores for downstream analysis

    Latency: ~50ms for 10 pairs on CPU
    """
    import time
    from sentence_transformers import CrossEncoder

    if not settings.ENABLE_CROSS_ENCODER_RERANK:
        return evidence_list

    start_time = time.time()

    try:
        # Lazy load cross-encoder (same pattern as NLI model)
        if not hasattr(self, '_cross_encoder'):
            self._cross_encoder = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
            logger.info("Cross-encoder loaded: ms-marco-MiniLM-L-6-v2")

        # Prepare claim-evidence pairs
        pairs = [(claim_text, ev.get('text', '')) for ev in evidence_list]

        # Score all pairs (synchronous but fast)
        scores = self._cross_encoder.predict(pairs)

        # Attach scores and preserve bi-encoder ranking
        for i, ev in enumerate(evidence_list):
            ev['cross_encoder_score'] = float(scores[i])
            ev['bi_encoder_score'] = ev.get('combined_score', 0.0)

        # Sort by cross-encoder score
        reranked = sorted(evidence_list, key=lambda x: x['cross_encoder_score'], reverse=True)

        # Log latency and ranking changes
        latency_ms = (time.time() - start_time) * 1000
        ranking_changes = sum(1 for i, ev in enumerate(reranked) if i != evidence_list.index(ev))

        logger.info(
            f"Cross-encoder reranking: {len(pairs)} pairs in {latency_ms:.1f}ms "
            f"({latency_ms/len(pairs):.1f}ms per pair), "
            f"{ranking_changes} position changes"
        )

        return reranked

    except Exception as e:
        logger.error(f"Cross-encoder reranking failed: {e}, falling back to bi-encoder ranking")
        return evidence_list
```

**Integrate into retrieval flow:**

```python
# In _retrieve_evidence_for_single_claim, modify line 119:

# Step 3: Apply credibility and recency weighting
final_evidence = self._apply_credibility_weighting(ranked_evidence, claim)

# NEW: Step 3.5: Cross-encoder reranking if enabled
if settings.ENABLE_CROSS_ENCODER_RERANK:
    final_evidence = await self._rerank_with_cross_encoder(claim_text, final_evidence)

# Step 4: Store in vector database
await self._store_evidence_embeddings(claim, final_evidence)

# Return top evidence
return final_evidence[:self.max_sources_per_claim]
```

**Model Choice:**
- `cross-encoder/ms-marco-MiniLM-L-6-v2`
- Size: ~80MB
- Speed: ~50 pairs/sec on CPU
- Trained on MS MARCO passage ranking dataset

#### Validation Plan

**Step 1: Run evaluation harness**
```bash
ENABLE_CROSS_ENCODER_RERANK=true python tests/evaluation/harness.py --dataset all_claims.json --config phase1_crossenc
```

**Step 2: Measure evidence quality improvement**
- Calculate Precision@5 (are top 5 sources actually relevant to claim?)
- Compare bi-encoder vs cross-encoder rankings
- Measure verdict accuracy delta (better evidence → better verdicts)

**Step 3: Latency analysis**
- Log per-claim latency
- Confirm <60ms cross-encoder overhead per claim
- Ensure async semaphore doesn't starve tasks

**Step 4: Score persistence verification**
- Confirm both scores saved in evidence items
- Verify judge can see ranking provenance

**Success Criteria:**
- [ ] +10 pp accuracy OR measurable evidence quality improvement (Precision@5)
- [ ] <60ms latency increase per claim
- [ ] Cross-encoder scores persisted correctly
- [ ] No async/concurrency issues

---

### Phase 1 Integration Testing

**Deliverable:** Combined validation of all three improvements

**Test Configuration:**
```bash
ENABLE_DEBERTA_NLI=true \
ENABLE_JUDGE_FEW_SHOT=true \
ENABLE_CROSS_ENCODER_RERANK=true \
python tests/evaluation/harness.py --dataset all_claims.json --config phase1_all
```

**Expected Cumulative Impact:** +20-35 pp accuracy

**Success Criteria:**
- [ ] Overall accuracy: 50-65% (baseline ~30%)
- [ ] Medium claims: >60% accuracy
- [ ] Hard claims: >40% accuracy
- [ ] <15% cumulative latency increase
- [ ] <$10/month cost increase

**Gate Decision:**
If Phase 1 achieves +20pp gain → Proceed to Phase 2
If Phase 1 achieves <15pp gain → Investigate and iterate before Phase 2

---

## Phase 2: Targeted Enhancements

**Timeline:** Week 5-7 (3 weeks)
**Owner:** Tru8 Engineering Team
**Objective:** Implement context and multi-model improvements

**Prerequisites:** Phase 1 must achieve +20pp minimum

---

### 2.1 Two-Pass Context Expansion

**Expected Impact:** +3-5% on long-form articles

**Hypothesis:** 2,500-word truncation loses context. Targeted retry for truncated claims with summarization preserves key information without diluting focus.

#### Implementation Strategy

**Approach:** Conditional expansion rather than blanket increase

**Files Modified:**
- `backend/app/core/config.py`
- `backend/app/pipeline/extract.py`

**Logic:**

```python
async def extract_claims(self, content: str, metadata: Dict):
    """
    Extract claims with optional two-pass context expansion.

    Pass 1: Standard 2,500-word extraction
    Pass 2 (conditional): If truncation detected, summarize overflow + re-extract
    """

    # Pass 1: Standard extraction
    truncated_content = content[:2500] if len(content) > 2500 else content
    initial_claims = await self._extract_with_openai(truncated_content, metadata)

    # Check if expansion needed
    if not settings.ENABLE_TWO_PASS_EXTRACTION:
        return initial_claims

    if self._claims_appear_truncated(initial_claims, content):
        logger.info("Truncation detected, initiating two-pass extraction")

        # Summarize overflow section (words 2500-5000)
        overflow = content[2500:5000]
        summary = await self._summarize_overflow(overflow)

        # Combine: original 2500 words + summary
        enhanced_context = truncated_content + "\n\n[CONTINUED SUMMARY]\n" + summary

        # Re-extract with enhanced context
        enhanced_claims = await self._extract_with_openai(enhanced_context, metadata)
        return enhanced_claims

    return initial_claims
```

**Truncation Detection Heuristics:**

```python
def _claims_appear_truncated(self, claims: List[Dict], full_content: str) -> bool:
    """Detect if claims were cut off due to truncation"""
    if not claims:
        return False

    # Heuristic 1: Last claim ends with dangling reference
    last_claim = claims[-1]['text']
    dangling_indicators = ['this', 'which', 'who', 'that was', 'according to', 'the']
    if any(last_claim.strip().endswith(ind) for ind in dangling_indicators):
        return True

    # Heuristic 2: Content significantly longer than processed
    word_count = len(full_content.split())
    if word_count > 2800:  # Close to 2500 limit
        return True

    # Heuristic 3: Claim extraction confidence low
    avg_confidence = sum(c.get('confidence', 0.8) for c in claims) / len(claims)
    if avg_confidence < 0.7:
        return True

    return False
```

**Validation Plan:** [TBD based on Phase 1 results]

---

### 2.2 Multi-Model Validation for Uncertain Verdicts

**Expected Impact:** +8-12% on uncertain verdicts

**Hypothesis:** Single LLM errors compound. Second-pass review with Claude when confidence <60% catches GPT-4o-mini errors and improves verdict reliability.

#### Implementation Strategy

**Approach:** Conditional second-pass only on hard claims

**Files Modified:**
- `backend/app/pipeline/judge.py`

**Logic:**

```python
async def judge_claim(self, claim: Dict[str, Any], verification_signals: Dict[str, Any],
                     evidence: List[Dict[str, Any]]) -> JudgmentResult:
    """Judge with optional multi-model validation"""

    # Primary judgment (GPT-4o-mini)
    gpt_judgment = await self._judge_with_openai(context)

    # If high confidence, return immediately
    if not settings.ENABLE_MULTI_MODEL_VALIDATION:
        return gpt_judgment

    if gpt_judgment['confidence'] >= 60:
        return gpt_judgment

    # Low confidence → validate with Claude
    logger.info(f"Low confidence ({gpt_judgment['confidence']}), requesting Claude validation")

    claude_judgment = await self._judge_with_anthropic(context)

    # Compare verdicts
    if gpt_judgment['verdict'] == claude_judgment['verdict']:
        # Models agree → average confidence
        merged = self._merge_judgments(gpt_judgment, claude_judgment)
        merged['multi_model_agreement'] = True
        return merged
    else:
        # Models disagree → flag as conflicting
        logger.warning(f"Model disagreement: GPT={gpt_judgment['verdict']}, Claude={claude_judgment['verdict']}")
        return {
            'verdict': 'conflicting_analysis',
            'confidence': 40,
            'rationale': f"Multiple AI models disagree: GPT-4o ({gpt_judgment['verdict']}, {gpt_judgment['confidence']}%) vs Claude ({claude_judgment['verdict']}, {claude_judgment['confidence']}%)",
            'multi_model_agreement': False,
            'gpt_verdict': gpt_judgment,
            'claude_verdict': claude_judgment
        }
```

**Validation Plan:** [TBD]

---

### 2.3 Ensemble NLI Verification

**Expected Impact:** +5-8% on numerical/temporal claims

**Hypothesis:** Single NLI model errors on edge cases. Ensemble voting with two DeBERTa models reduces false positives/negatives.

#### Implementation Strategy

**Approach:** Parallel verification with weighted voting

**Models:**
- DeBERTa-v3-base-FEVER (primary, weight 0.6)
- microsoft/deberta-v3-base (secondary, weight 0.4)

**Validation Plan:** [TBD based on Phase 1 results]

---

## Phase 3: Advanced Optimizations

**Timeline:** Week 8+ (ongoing)
**Owner:** TBD
**Objective:** Incremental improvements based on Phase 1-2 learnings

**Potential Areas:**
- NewsGuard credibility integration
- Semantic snippet extraction with sentence-transformers
- Fact-check validation layer (separate from primary retrieval)
- Advanced prompt engineering (chain-of-thought reasoning)

**Approach:** Data-driven prioritization based on remaining error patterns after Phase 2

---

## Monitoring & Metrics

### Continuous Monitoring

**Per-Claim Logging:**
```json
{
  "claim_id": "abc123",
  "timestamp": "2024-11-07T10:30:00Z",
  "pipeline_version": "phase1_all",
  "feature_flags": {
    "ENABLE_DEBERTA_NLI": true,
    "ENABLE_JUDGE_FEW_SHOT": true,
    "ENABLE_CROSS_ENCODER_RERANK": true
  },
  "latency_ms": {
    "extract": 1200,
    "retrieve": 3400,
    "verify": 850,
    "judge": 950,
    "total": 6400
  },
  "cost": {
    "openai_tokens": 2500,
    "openai_cost": 0.00375,
    "search_api_calls": 1,
    "search_api_cost": 0.001,
    "total_cost": 0.00475
  },
  "verdict": "supported",
  "confidence": 85,
  "evidence_count": 5,
  "nli_model": "DeBERTa-v3-base-FEVER",
  "cross_encoder_used": true
}
```

**Aggregated Metrics Dashboard:**
- Accuracy by week (rolling 7-day window)
- Latency P50/P95/P99
- Cost per claim (daily average)
- Abstention rate
- Error rate by pipeline stage

### Regression Testing

**Automated Checks:**
- Run evaluation harness nightly
- Alert on >5pp accuracy drop
- Alert on >20% latency increase
- Flag individual claims that regress >10pp

**Regression Suite:**
- Store baseline outputs for all 100 eval claims
- Compare new outputs against baseline
- Investigate any significant deviations

### A/B Testing Framework

**Production Validation:**

```python
# Route 10% of production traffic to experimental pipeline

@app.post("/api/v1/check")
async def create_check(check_data):
    # A/B split
    user_hash = hash(check_data.user_id)
    in_experiment = (user_hash % 10) == 0  # 10% traffic

    if in_experiment and settings.ENABLE_AB_TESTING:
        result = await pipeline_experimental.run(check_data)
        result['pipeline_variant'] = 'experimental'
    else:
        result = await pipeline_baseline.run(check_data)
        result['pipeline_variant'] = 'control'

    # Log for analysis
    await log_check_result(result)

    return result
```

**Metrics Comparison:**
- User satisfaction (thumbs up/down on verdicts)
- Re-check rate (users re-running same claim)
- Latency distribution
- Cost distribution

---

## Risk Mitigation

### Technical Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| DeBERTa memory overflow | Medium | High | Use base model + FP16, monitor GPU memory |
| Cross-encoder latency spike | Low | Medium | Gate at <60ms, fallback to bi-encoder |
| LLM API rate limits | Low | High | Implement exponential backoff, queue management |
| Evaluation dataset bias | Medium | High | Include diverse claim types, external validation |
| Cost explosion | Low | Medium | Set per-claim cost caps, alert on anomalies |

### Process Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Overfitting to eval set | High | High | Hold out 20% test set, validate on live traffic |
| False confidence from A/B | Medium | Medium | Require 1-week A/B period, statistical significance |
| Team capacity constraints | Medium | Medium | Prioritize Phase 1, defer Phase 2/3 if needed |
| Model weights unavailable | Low | High | Cache models locally, verify download pre-deployment |

### Rollback Strategy

**Immediate Rollback:**
- All feature flags default to `false`
- Can disable via environment variable (no code deploy)
- Model weights cached separately (no collision on rollback)

**Staged Rollback:**
1. Disable failing flag (1 minute)
2. Verify metrics return to baseline (5 minutes)
3. Investigate root cause offline
4. Fix and re-deploy behind flag

---

## Rollout Strategy

### Feature Flag Progression

**Phase 1 Rollout:**

```
Week 2: Development
├─ Enable all flags in dev environment
├─ Iterate on evaluation harness
└─ Achieve +20pp on eval set

Week 3: Staging
├─ Enable DeBERTa flag in staging
├─ Validate latency, cost, accuracy
├─ Enable few-shot flag in staging
├─ Validate edge case improvements
├─ Enable cross-encoder flag in staging
└─ Validate evidence quality

Week 4: Production A/B
├─ 10% traffic with Phase 1 flags enabled
├─ Monitor for 1 week (7 days)
├─ Compare control vs experiment metrics
└─ Decision: promote or rollback

Week 5: Production Full
├─ Promote flags to 100% traffic
└─ Monitor for regressions
```

**Decision Tree:**

```
A/B Test Results (Week 4):
├─ +15pp accuracy & <10% latency → Promote to 100%
├─ +10pp accuracy & <15% latency → Promote with monitoring
├─ +5pp accuracy → Investigate, extend A/B
└─ <5pp accuracy → Rollback, iterate offline
```

### Success Criteria Checklist

**Phase 0:**
- [ ] 100-claim dataset assembled and verified
- [ ] Evaluation harness implemented and tested
- [ ] Baseline report generated and reviewed
- [ ] All per-claim outputs stored for regression

**Phase 1:**
- [ ] DeBERTa model validated (+10pp on medium claims)
- [ ] Few-shot prompt validated (+5pp on edge cases)
- [ ] Cross-encoder validated (evidence quality improvement)
- [ ] Combined Phase 1: +20pp overall accuracy
- [ ] <15% cumulative latency increase
- [ ] <$10/month cost increase
- [ ] No regressions on easy claims

**Phase 2:**
- [ ] Two-pass extraction validated
- [ ] Multi-model validation implemented
- [ ] Ensemble NLI tested
- [ ] Combined Phase 2: +15pp additional accuracy
- [ ] Cumulative accuracy: 65-80%

**Production:**
- [ ] A/B test shows statistical significance
- [ ] User satisfaction metrics improved
- [ ] No increase in error rate
- [ ] Cost per claim within budget
- [ ] Latency P95 acceptable (<10s for Quick mode)

---

## Appendices

### Appendix A: Evaluation Dataset Schema

**Full JSON Schema:**

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Tru8 Evaluation Claim",
  "type": "object",
  "required": ["id", "claim_text", "source_url", "source_content", "ground_truth", "metadata"],
  "properties": {
    "id": {
      "type": "string",
      "pattern": "^(easy|medium|hard|edge)_[0-9]{3}$",
      "description": "Unique claim identifier"
    },
    "claim_text": {
      "type": "string",
      "minLength": 10,
      "description": "The factual claim to verify"
    },
    "source_url": {
      "type": "string",
      "format": "uri",
      "description": "Original article URL"
    },
    "source_content": {
      "type": "string",
      "minLength": 100,
      "description": "Full article text for pipeline replay"
    },
    "ground_truth": {
      "type": "object",
      "required": ["verdict", "confidence", "rationale"],
      "properties": {
        "verdict": {
          "type": "string",
          "enum": ["supported", "contradicted", "uncertain", "insufficient_evidence"],
          "description": "Human-verified ground truth verdict"
        },
        "confidence": {
          "type": "number",
          "minimum": 0,
          "maximum": 100,
          "description": "Human expert confidence rating"
        },
        "rationale": {
          "type": "string",
          "description": "Explanation for ground truth verdict"
        },
        "authoritative_sources": {
          "type": "array",
          "items": {"type": "string", "format": "uri"},
          "description": "URLs of authoritative sources supporting ground truth"
        }
      }
    },
    "metadata": {
      "type": "object",
      "required": ["difficulty", "claim_type"],
      "properties": {
        "difficulty": {
          "type": "string",
          "enum": ["easy", "medium", "hard"],
          "description": "Claim difficulty tier"
        },
        "claim_type": {
          "type": "string",
          "enum": [
            "numerical_exact",
            "numerical_approximate",
            "temporal_historical",
            "temporal_current",
            "scientific_consensus",
            "scientific_emerging",
            "political_factual",
            "prediction",
            "opinion_labeled_as_fact",
            "conflicting_sources",
            "ambiguous"
          ],
          "description": "Claim classification"
        },
        "temporal_sensitivity": {
          "type": "boolean",
          "description": "Does claim accuracy depend on timing?"
        },
        "domain": {
          "type": "string",
          "enum": ["science", "politics", "business", "health", "technology", "sports", "other"],
          "description": "Subject domain"
        },
        "requires_context": {
          "type": "boolean",
          "description": "Does claim require surrounding article context to verify?"
        },
        "notes": {
          "type": "string",
          "description": "Additional notes for evaluators"
        }
      }
    }
  }
}
```

### Appendix B: Feature Flag Reference

| Flag | Default | Config Variable | Purpose | Phase |
|------|---------|-----------------|---------|-------|
| `ENABLE_DEBERTA_NLI` | `false` | `settings.ENABLE_DEBERTA_NLI` | Swap NLI model to DeBERTa-v3-FEVER | 1.1 |
| `ENABLE_JUDGE_FEW_SHOT` | `false` | `settings.ENABLE_JUDGE_FEW_SHOT` | Add few-shot examples to judge prompt | 1.2 |
| `ENABLE_CROSS_ENCODER_RERANK` | `false` | `settings.ENABLE_CROSS_ENCODER_RERANK` | Precision reranking with cross-encoder | 1.3 |
| `ENABLE_TWO_PASS_EXTRACTION` | `false` | `settings.ENABLE_TWO_PASS_EXTRACTION` | Conditional context expansion | 2.1 |
| `ENABLE_MULTI_MODEL_VALIDATION` | `false` | `settings.ENABLE_MULTI_MODEL_VALIDATION` | Claude validation for low-confidence | 2.2 |
| `ENABLE_ENSEMBLE_NLI` | `false` | `settings.ENABLE_ENSEMBLE_NLI` | Two-model NLI voting | 2.3 |

**Environment Variable Override:**

```bash
# Enable Phase 1 flags
export ENABLE_DEBERTA_NLI=true
export ENABLE_JUDGE_FEW_SHOT=true
export ENABLE_CROSS_ENCODER_RERANK=true

# Run server
uvicorn main:app --reload
```

### Appendix C: Model Specifications

| Model | Purpose | Parameters | Memory (FP16) | Latency | Cost |
|-------|---------|------------|---------------|---------|------|
| **GPT-4o-mini** | Extract + Judge | N/A (API) | N/A | ~1s | $0.15/1M in, $0.60/1M out |
| **BART-large-MNLI** | NLI (baseline) | 406M | ~800MB | ~100ms/batch | Free (local) |
| **DeBERTa-v3-base-FEVER** | NLI (Phase 1) | 184M | ~900MB | ~120ms/batch | Free (local) |
| **all-MiniLM-L6-v2** | Bi-encoder | 23M | ~100MB | ~20ms/batch | Free (local) |
| **ms-marco-MiniLM-L-6-v2** | Cross-encoder | 23M | ~80MB | ~5ms/pair | Free (local) |
| **Claude Haiku** | Multi-model (Phase 2) | N/A (API) | N/A | ~1s | $0.25/1M in, $1.25/1M out |

### Appendix D: Cost Estimation

**Current Cost Per Claim (Baseline):**
```
Extraction (GPT-4o-mini): ~3,000 tokens = $0.0018
Judge (GPT-4o-mini): ~1,500 tokens = $0.0009
Search API (Brave): 1 call = $0.001
NLI (local): $0.00
Embeddings (local): $0.00
──────────────────────────────────────────
Total per claim: ~$0.0037
```

**Phase 1 Cost Per Claim:**
```
Extraction: $0.0018 (unchanged)
Judge (with few-shot): ~2,000 tokens = $0.0012 (+$0.0003)
Search API: $0.001 (unchanged)
NLI (DeBERTa local): $0.00
Cross-encoder (local): $0.00
──────────────────────────────────────────
Total per claim: ~$0.0040 (+$0.0003)

Monthly increase (1000 claims): +$0.30
```

**Phase 2 Cost Per Claim (with multi-model on 30% of claims):**
```
Base (70% of claims): $0.0040
With Claude validation (30% of claims):
  - Base: $0.0040
  - Claude Haiku: ~1,500 tokens = $0.0019
  - Subtotal: $0.0059

Weighted average: 0.7 * $0.0040 + 0.3 * $0.0059 = $0.0046

Monthly increase (1000 claims): +$0.90
```

### Appendix E: Latency Targets

| Pipeline Stage | Baseline (ms) | Phase 1 Target (ms) | Phase 2 Target (ms) |
|----------------|---------------|---------------------|---------------------|
| Ingest | 500-2000 | 500-2000 | 500-2000 |
| Extract | 1200-1500 | 1200-1500 | 1500-2000 (two-pass) |
| Retrieve | 3000-4000 | 3200-4400 (+200) | 3200-4400 |
| Verify (NLI) | 800-1000 | 900-1200 (+200) | 1000-1500 (ensemble) |
| Judge | 900-1200 | 900-1200 | 1200-2400 (multi-model) |
| **Total** | **6400-9700** | **6700-10300** | **7400-12300** |

**P95 Latency Target:** <10s for Quick mode (current: ~9.7s baseline)

### Appendix F: References

**Research Papers:**
- DeBERTa: Decoding-enhanced BERT with Disentangled Attention (He et al., 2021)
- FEVER: Fact Extraction and VERification (Thorne et al., 2018)
- MS MARCO: A Human Generated MAchine Reading COmprehension Dataset (Nguyen et al., 2016)

**Model Documentation:**
- [DeBERTa-v3-FEVER Model Card](https://huggingface.co/MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli)
- [MS MARCO Cross-Encoders](https://www.sbert.net/docs/pretrained-models/ce-msmarco.html)
- [GPT-4o-mini Pricing](https://openai.com/pricing)

**Internal Documentation:**
- Pipeline Architecture: `backend/app/pipeline/README.md`
- Configuration Reference: `backend/app/core/config.py`
- Design System: `DESIGN_SYSTEM.md`

---

## Change Log

| Date | Version | Changes | Author |
|------|---------|---------|--------|
| 2024-11-07 | 0.1 | Initial draft | Claude Code |
| [TBD] | 1.0 | Baseline metrics added | Tru8 Engineering |
| [TBD] | 1.1 | Phase 1 results added | Tru8 Engineering |

---

**Document Status:** Draft - Awaiting evaluation dataset and baseline metrics
**Next Update:** After Phase 0 completion (Week 1)
**Contact:** Tru8 Engineering Team

---

*This document serves as the canonical reference for Tru8 accuracy improvement efforts. All implementation work should reference this plan and update metrics as they become available.*
