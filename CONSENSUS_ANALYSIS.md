# Tru8 Consensus & Scoring Analysis
## Understanding the Current System Before Improvements

---

## Executive Summary

The pipeline **already has credibility-weighted consensus** at the judge stage, but there are **critical gaps** in the NLI aggregation and overall scoring that create artificial uncertainty.

### Key Findings:

✅ **What's Working:**
- Evidence IS filtered by tier (0.6-1.0 credibility scores)
- Consensus strength IS credibility-weighted in judge.py
- Abstention logic checks for minimum sources and consensus

❌ **What's Creating Uncertainty:**
- **Only 5 sources per claim** (too small for statistical confidence)
- **NLI signals NOT credibility-weighted** (1 blog = 1 Reuters vote)
- **Overall score simple count-based** (ignores claim confidence levels)
- **Consensus threshold too strict** (50% with only 5 sources)

---

## Current Data Flow

```
1. RETRIEVE (retrieve.py)
   └─ Search API → 10 sources
   └─ Filter by credibility (≥70%) → ~5-8 sources
   └─ Return TOP 5 sources

2. VERIFY (verify.py)
   └─ NLI check each: support/contradict/neutral
   └─ Count votes: supporting_count, contradicting_count
   └─ ⚠️ PROBLEM: Simple counts, not weighted

3. JUDGE (judge.py)
   └─ Check abstention thresholds (min 3 sources, 50% consensus)
   └─ Calculate credibility-weighted consensus ✅
   └─ If pass: LLM final verdict
   └─ If fail: Abstain (insufficient_evidence)

4. PIPELINE (pipeline.py)
   └─ Aggregate all claims
   └─ Overall score = (supported×100 + uncertain×50 + contradicted×0) / total
   └─ ⚠️ PROBLEM: Treats all claims equally
```

---

## Current Threshold Values

| Setting | Value | Location | Impact |
|---------|-------|----------|--------|
| `max_sources_per_claim` | **5** | retrieve.py:20 | Only 5 evidence sources per claim |
| `MIN_SOURCES_FOR_VERDICT` | **3** | config.py:106 | Need 3+ sources or abstain |
| `MIN_CONSENSUS_STRENGTH` | **0.50** | config.py:108 | Need 50% consensus or abstain |
| `MIN_CREDIBILITY_THRESHOLD` | **0.60** | config.py:107 | High-cred source threshold |
| `SOURCE_CREDIBILITY_THRESHOLD` | **0.70** | config.py:99 | Filter threshold (was 0.65, we raised to 0.70) |

---

## The Three Critical Gaps

### Gap 1: NLI Aggregation Not Weighted (verify.py:547-556)

**Current Code:**
```python
if supporting_count > contradicting_count and max_entailment > 0.7:
    overall_verdict = "supported"
```

**Problem:**
- 3 Reuters sources (0.9 credibility) + 2 blogs (0.6 credibility) = 3 support votes
- 2 Reuters sources + 3 blogs = 2 support votes
- **Second scenario marked "contradicted" even though Reuters agrees!**

**Fix:** Weight by credibility in NLI signal aggregation

---

### Gap 2: Overall Score Ignores Confidence (pipeline.py:592-596)

**Current Code:**
```python
credibility_score = int(
    (supported * 100 + uncertain * 50 + contradicted * 0) / total
)
```

**Problem:**
- Claim 1: SUPPORTED (95% confidence, 5/5 Tier1 sources)
- Claim 2: UNCERTAIN (40% confidence, 3/5 mixed sources)
- **Both count equally in overall score!**

**Fix:** Weight by claim confidence and evidence quality

---

### Gap 3: Sample Size Too Small (retrieve.py:20)

**Current:**
- 5 sources per claim
- With 50% consensus threshold
- **High false uncertainty rate**

**Statistical Reality:**
- True claim with 90% real-world consensus
- Probability of getting only 3/5 agreement = **8.1%**
- **1 in 12 true claims marked uncertain due to sampling**

**Fix:** Increase to 10-15 sources per claim

---

## Existing Infrastructure We Can Build On

### 1. Credibility Service (ALREADY EXISTS)

**Location:** `source_credibility.py`, `retrieve.py:371-458`

```python
# Returns tier-based scores:
{
  'tier': 'news_tier1',          # BBC, Reuters, AP
  'credibility': 0.9,
  'auto_exclude': False,
  'risk_flags': []
}
```

**Use Case:** Already provides tier weighting, just need to apply it consistently

---

### 2. Consensus Calculation (ALREADY EXISTS)

**Location:** `judge.py:520-565`

```python
def _calculate_consensus_strength(evidence, verification_signals):
    # Already credibility-weighted!
    for ev in evidence:
        cred_score = ev.get('credibility_score', 0.6)
        if stance == 'supporting':
            supporting_weight += cred_score
        elif stance == 'contradicting':
            contradicting_weight += cred_score
```

**Use Case:** Good model to replicate in NLI aggregation

---

### 3. Evidence Enrichment (ALREADY EXISTS)

**Location:** `retrieve.py:397-406`

```python
# Evidence items already have metadata:
evidence_item['tier'] = cred_info.get('tier')
evidence_item['credibility_score'] = 0.9
evidence_item['risk_flags'] = []
```

**Use Case:** All the data we need is already attached to evidence

---

## Proposed Implementation Plan

### Phase 1: Increase Evidence Pool (IMMEDIATE - 10 min)

**Change 1:** Increase source count
```python
# retrieve.py Line 20
self.max_sources_per_claim = 10  # Was: 5
```

**Change 2:** Increase initial retrieval
```python
# retrieve.py Line 96
max_sources=self.max_sources_per_claim * 2  # Gets 20, filters to 10
```

**Impact:**
- More statistical confidence
- Reduces sampling bias
- Lower false uncertainty rate

---

### Phase 2: Weight NLI Signals by Credibility (30 min)

**Location:** `verify.py:547-556`

**Current:**
```python
supporting_count = sum(1 for v in verifications
                       if v.get("relationship") == "entails")
```

**Enhanced:**
```python
supporting_weight = sum(
    v.get("evidence_credibility", 0.6)
    for v in verifications
    if v.get("relationship") == "entails"
)

if supporting_weight > contradicting_weight:
    overall_verdict = "supported"
```

**Impact:**
- Tier1 sources have more influence
- Prevents low-quality sources canceling out high-quality sources
- Uses existing credibility scores (no new data needed)

---

### Phase 3: Confidence-Weighted Overall Score (1 hour)

**Location:** `pipeline.py:592-596`

**Current:**
```python
credibility_score = (supported * 100 + uncertain * 50) / total
```

**Enhanced:**
```python
weighted_score = 0
total_weight = 0

for claim in claims:
    confidence = claim.get('confidence', 50) / 100  # 0-1
    avg_evidence_cred = claim.get('avg_evidence_credibility', 0.7)

    # High confidence + high evidence quality = more weight
    claim_weight = confidence * avg_evidence_cred

    verdict_value = {
        'supported': 100,
        'contradicted': 0,
        'uncertain': 40,  # Penalize uncertainty more
        'insufficient_evidence': 30
    }.get(claim.get('verdict'), 40)

    weighted_score += verdict_value * claim_weight
    total_weight += claim_weight

credibility_score = int(weighted_score / total_weight) if total_weight > 0 else 50
```

**Impact:**
- High-confidence claims dominate score
- Weak claims have less influence
- More accurate overall assessment

---

### Phase 4: Lower Consensus Threshold (5 min)

**Location:** `config.py:108`

**Current:**
```python
MIN_CONSENSUS_STRENGTH: float = 0.50
```

**Recommended:**
```python
MIN_CONSENSUS_STRENGTH: float = 0.45  # With better weighting + more sources
```

**Impact:**
- With 10 sources + credibility weighting, 45% is statistically sound
- Reduces false abstention rate
- More definitive verdicts

---

## Risk Analysis

| Change | Risk Level | Mitigation |
|--------|-----------|------------|
| Increase sources 5→10 | LOW | More API calls, but within budget |
| Weight NLI signals | MEDIUM | Could over-weight Tier1, need testing |
| Weight overall score | LOW | Makes logical sense, easy to rollback |
| Lower consensus 50%→45% | MEDIUM | Only do with other changes together |

---

## Testing Strategy

Before deploying:

1. **Run evaluation on existing checks**
   - Re-process recent checks with new logic
   - Compare old vs new scores
   - Look for improvements in "uncertain" rate

2. **Edge case testing**
   - All Tier1 support, 1 blog contradicts → Should be SUPPORTED
   - 3 Tier1 support, 2 Tier1 contradict → Should be UNCERTAIN (genuine split)
   - 5 blogs, no Tier1 → Should abstain (insufficient quality)

3. **Statistical validation**
   - Track overall "uncertain" percentage
   - Target: Reduce from ~54% to ~25-30%
   - Should NOT reduce to 0% (some claims genuinely uncertain)

---

## Next Steps

**Recommended Order:**

1. **Start with Phase 1** (increase sources) - Low risk, immediate impact
2. **Test with existing checks** - Does it reduce uncertainty?
3. **If positive, add Phase 2** (weight NLI) - Medium risk, high impact
4. **Test again** - Measure improvement
5. **Add Phase 3** (overall score) - Low risk, better UX
6. **Finally Phase 4** (threshold) - Only with all other changes

---

## Integration Points Summary

| File | Lines | Function | What to Change |
|------|-------|----------|----------------|
| `retrieve.py` | 20 | `__init__` | Increase `max_sources_per_claim` |
| `retrieve.py` | 96 | `_retrieve_evidence_for_single_claim` | Increase pool multiplier |
| `verify.py` | 547-556 | `aggregate_verification_signals` | Add credibility weighting |
| `pipeline.py` | 592-596 | `generate_overall_assessment` | Add confidence weighting |
| `config.py` | 108 | Settings | Lower `MIN_CONSENSUS_STRENGTH` |

---

This analysis provides the roadmap to reduce artificial uncertainty while building on existing, working infrastructure.
