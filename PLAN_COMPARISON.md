# Pipeline Improvement Plan Comparison

## Two Paths Forward

We have two comprehensive improvement plans ready to implement. This comparison will help decide which to pursue first.

---

## Plan A: Accuracy Improvement Plan (DeBERTa NLI Swap)

**Location:** `IMPLEMENTATION_ACCURACY_IMPROVEMENT.md`

### Current Status
- **Phase 1: FULLY IMPLEMENTED** (flags are OFF, ready to enable)
- **Phase 2-3: NOT STARTED** (planning only)

### What Phase 1 Contains (Ready to Enable)

#### 1.1 DeBERTa NLI Model Swap
- **Current:** BART-large-mnli (140M params, 2019 architecture)
- **New:** DeBERTa-v3-base-mnli-fever-anli (184M params, MNLI + FEVER + ANLI trained)
- **Flag:** `ENABLE_DEBERTA_NLI=true`
- **Files:** `backend/app/core/config.py:119`, `backend/app/pipeline/verify.py:77-84`
- **Expected Impact:** +5-8% accuracy on entailment detection

#### 1.2 Judge Few-Shot Prompting
- **Current:** Zero-shot prompt with basic instructions
- **New:** 3 examples showing reasoning patterns for supported/contradicted/uncertain
- **Flag:** `ENABLE_JUDGE_FEW_SHOT=true`
- **Files:** `backend/app/core/config.py:122`, `backend/app/pipeline/judge.py:166-264`
- **Expected Impact:** Better verdict consistency, clearer reasoning

#### 1.3 Cross-Encoder Evidence Reranking
- **Current:** Evidence used in retrieval order (BM25 + embedding hybrid)
- **New:** Rerank by relevance to claim using ms-marco-MiniLM-L-6-v2
- **Flag:** `ENABLE_CROSS_ENCODER_RERANK=true`
- **Files:** `backend/app/core/config.py:125`, `backend/app/pipeline/retrieve.py:129-203`
- **Expected Impact:** Most relevant evidence prioritized, better NLI inputs

### What Phase 2-3 Would Add (Not Yet Implemented)

**Phase 2:** Multi-Model Validation
- Two-pass claim extraction (confidence filtering)
- Ensemble NLI (combine multiple models)
- Implementation: 3-4 weeks

**Phase 3:** Advanced Optimizations
- ONNX quantization, caching, batch processing
- Implementation: 2-3 weeks

### Problems This Plan Solves
- ✅ Better NLI accuracy (fewer false neutrals)
- ✅ More consistent judge verdicts
- ✅ Better evidence quality through reranking
- ✅ Improved model performance

### Problems This Plan Doesn't Solve
- ❌ Small evidence pool (still only 5 sources per claim)
- ❌ Statistical confidence issues
- ❌ Non-weighted NLI aggregation
- ❌ High "uncertain" verdict rate

---

## Plan B: Consensus Improvement Plan

**Location:** `CONSENSUS_ANALYSIS.md`

### Current Status
- **All Phases: NOT IMPLEMENTED** (documented and ready to code)

### What Each Phase Does

#### Phase 1: Increase Evidence Pool (10 min to implement)
```python
# retrieve.py Line 20
self.max_sources_per_claim = 10  # Was: 5

# retrieve.py Line 96
max_sources=self.max_sources_per_claim * 2  # Gets 20, filters to 10
```
- **Impact:** More statistical confidence, reduces sampling bias
- **Risk:** Low (more API calls, but within budget)

#### Phase 2: Weight NLI Signals by Credibility (30 min)
```python
# verify.py:547-556
# Current: simple counts (1 blog = 1 Reuters vote)
supporting_count = sum(1 for v in verifications if v["relationship"] == "entails")

# New: credibility-weighted
supporting_weight = sum(v.get("evidence_credibility", 0.6)
                       for v in verifications if v["relationship"] == "entails")
```
- **Impact:** Tier1 sources have more influence, prevents low-quality canceling high-quality
- **Risk:** Medium (need to test weighting doesn't over-favor Tier1)

#### Phase 3: Confidence-Weighted Overall Score (1 hour)
```python
# pipeline.py:592-596
# Current: all claims weighted equally
credibility_score = (supported * 100 + uncertain * 50) / total

# New: high-confidence claims dominate
for claim in claims:
    confidence = claim.get('confidence', 50) / 100
    avg_evidence_cred = claim.get('avg_evidence_credibility', 0.7)
    claim_weight = confidence * avg_evidence_cred
    weighted_score += verdict_value * claim_weight
```
- **Impact:** More accurate overall assessment, weak claims less influential
- **Risk:** Low (logical improvement, easy to rollback)

#### Phase 4: Lower Consensus Threshold (5 min)
```python
# config.py:108
MIN_CONSENSUS_STRENGTH: float = 0.45  # Was: 0.50
```
- **Impact:** With 10 sources + weighting, 45% is statistically sound
- **Risk:** Medium (only do with other changes together)

### Problems This Plan Solves
- ✅ Reduces "uncertain" verdicts (target: 54% → 25-30%)
- ✅ Better statistical confidence
- ✅ Prevents low-quality sources canceling high-quality
- ✅ More definitive verdicts (addresses user's "fence sitting" concern)

### Problems This Plan Doesn't Solve
- ❌ NLI model quality (still using BART)
- ❌ Judge prompt consistency
- ❌ Evidence ranking quality

---

## Comparison Matrix

| Dimension | Accuracy Plan (Phase 1) | Consensus Plan (Full) |
|-----------|------------------------|----------------------|
| **Implementation Time** | 0 min (just enable flags) | 1.5 hours total |
| **Code Status** | Already coded & tested locally | Needs to be written |
| **Risk Level** | LOW (already tested) | LOW-MEDIUM (needs testing) |
| **Addresses "Uncertainty Problem"** | No | **Yes** ✅ |
| **Improves Model Quality** | **Yes** ✅ | No |
| **Statistical Confidence** | No change | **Significantly improves** ✅ |
| **Credibility Weighting** | No change | **Adds to NLI & overall** ✅ |
| **Requires New Infrastructure** | No | No (uses existing credibility data) |
| **Can Be Rolled Back** | Yes (flip flags) | Yes (commit-based) |

---

## Recommendation: Do Both, in Sequence

### Step 1: Enable Accuracy Plan Phase 1 (Immediate - 5 min)

**Why First:**
- Already implemented and tested
- Zero implementation time
- Improves fundamental model quality
- Low risk (feature flags make rollback instant)
- Benefits compound with Consensus Plan improvements

**How:**
```bash
# backend/.env
ENABLE_DEBERTA_NLI=true
ENABLE_JUDGE_FEW_SHOT=true
ENABLE_CROSS_ENCODER_RERANK=true
```

**Monitor:** Run 10-20 checks, compare verdicts to previous system

---

### Step 2: Implement Consensus Plan (1-2 days)

**Why Second:**
- Directly addresses the "fence sitting" problem
- Builds on existing credibility infrastructure
- Complements better NLI models (better models + more evidence = best results)
- Statistical improvement is independent of model quality

**Implementation Order:**
1. **Day 1 Morning:** Phase 1 (increase sources to 10)
   - Test with existing checks
   - Measure if uncertainty rate improves
2. **Day 1 Afternoon:** Phase 2 (weight NLI signals)
   - Test edge cases (mixed credibility scenarios)
3. **Day 2 Morning:** Phase 3 (weight overall score)
   - Test overall score accuracy
4. **Day 2 Afternoon:** Phase 4 (lower threshold to 45%)
   - Only if phases 1-3 show positive results

---

### Step 3: Monitor Combined Impact (Week 1)

**Success Metrics:**
- "Uncertain" verdict rate: Target 54% → 25-30%
- User satisfaction: Fewer complaints about indecisive results
- Evidence quality: No social media, no duplicates (already fixed)
- Overall scores: More polarized (higher confidence in verdicts)

**Red Flags:**
- False positives increase (marking false claims as supported)
- Abstention rate increases (system refuses to judge)
- Tier1-only bias (ignoring Tier2/3 consensus)

---

## Why Not Just One Plan?

**If Only Accuracy Plan:**
- ✅ Better model quality
- ❌ Still only 5 sources (weak statistical confidence)
- ❌ Still simple count-based aggregation
- ❌ Doesn't address user's "uncertainty" concern

**If Only Consensus Plan:**
- ✅ Reduces uncertainty through statistical confidence
- ✅ Better credibility weighting
- ❌ Misses opportunity to use better NLI model (already coded!)
- ❌ Leaves model quality improvements on the table

**Both Together:**
- ✅ Better models (DeBERTa, few-shot, reranking)
- ✅ More evidence (10 vs 5 sources)
- ✅ Better weighting (credibility-based aggregation)
- ✅ Statistical confidence + model quality = optimal results

---

## Implementation Checklist

### Phase 1: Enable Accuracy Improvements (Today - 5 min)
- [ ] Add to `backend/.env`: `ENABLE_DEBERTA_NLI=true`
- [ ] Add to `backend/.env`: `ENABLE_JUDGE_FEW_SHOT=true`
- [ ] Add to `backend/.env`: `ENABLE_CROSS_ENCODER_RERANK=true`
- [ ] Restart backend service
- [ ] Run 5 test checks
- [ ] Compare verdicts to previous runs (if available)

### Phase 2: Implement Consensus Plan Phase 1 (Day 1 - 10 min)
- [ ] Edit `retrieve.py:20`: Change `max_sources_per_claim` to 10
- [ ] Edit `retrieve.py:96`: Change multiplier to `* 2`
- [ ] Commit: "Increase evidence pool from 5 to 10 sources per claim"
- [ ] Run test checks, measure uncertainty rate

### Phase 3: Implement Consensus Plan Phase 2 (Day 1 - 30 min)
- [ ] Edit `verify.py:547-556`: Add credibility weighting to NLI aggregation
- [ ] Update tests in `test_verify.py`
- [ ] Commit: "Add credibility weighting to NLI signal aggregation"
- [ ] Test edge cases (Tier1 vs Tier3 conflicts)

### Phase 4: Implement Consensus Plan Phase 3 (Day 2 - 1 hour)
- [ ] Edit `pipeline.py:592-596`: Add confidence-weighted overall score
- [ ] Update claims to include `avg_evidence_credibility` field
- [ ] Commit: "Implement confidence-weighted overall scoring"
- [ ] Test with recent checks

### Phase 5: Implement Consensus Plan Phase 4 (Day 2 - 5 min)
- [ ] Edit `config.py:108`: Lower `MIN_CONSENSUS_STRENGTH` to 0.45
- [ ] Commit: "Lower consensus threshold with improved weighting"
- [ ] Monitor abstention rate

---

## Next Action

**Recommend:** Enable Accuracy Plan Phase 1 immediately, then implement Consensus Plan over next 2 days.

This gives us:
1. Immediate improvement from better models (0 implementation time)
2. Statistical confidence from more evidence + weighting (1.5 hours implementation)
3. Addresses user's "fence sitting" concern directly
4. Compounds benefits (better models + more evidence = best outcomes)
