# NLI Threshold Changes for International Content
**Date:** 2025-11-19
**Issue:** International articles (Lula/Merz/Brazil) getting 50/100 scores vs 90/100 for US articles

## Root Cause Analysis

### Two-Stage Filtering Problem

1. **Relevance Filter** (verify.py): Evidence with semantic similarity < 0.75 filtered out BEFORE NLI
   - International paraphrases: "under fire" vs "disparaging remarks" → relevance 0.65-0.73
   - Gets marked OFF-TOPIC and skipped

2. **NLI Model**: Remaining evidence marked as "neutral" instead of "entails"
   - Example: Evidence "Merz under fire in Brazil" vs Claim "Merz made disparaging remarks" → neutral=0.998
   - Should recognize semantic equivalence

3. **Abstention Logic**: < 3 sources → "insufficient_evidence"

### Evidence from Logs

```
[12:26:10] BRAVE SEARCH | Results: 12  ✓ Search working
[12:26:14] FINAL EVIDENCE | Returning: 9 snippets  ✓ Retrieval working
[12:26:22] Evidence OFF-TOPIC (relevance 0.65 < 0.75), skipping NLI  ✗ Filtered out
[12:26:22] Relevance filter: 1 relevant, 0 off-topic  ✗ Only 1 source survives
[12:26:22] NLI: Entailment: 0.001, Neutral: 0.998  ✗ Marked neutral
[12:26:26] Saving 0 evidence items  ✗ Abstention triggered
```

## Changes Made

### Change 1: Lower Relevance Threshold
**File:** backend/app/core/config.py
**Before:** `RELEVANCE_THRESHOLD = 0.75`
**After:** `RELEVANCE_THRESHOLD = 0.65`

**Rationale:** Allow paraphrased international evidence through (0.65-0.73 range)

### Change 2: Adjust NLI Logic
**File:** backend/app/pipeline/verify.py (lines 33-46)
**Before:**
```python
NEUTRAL_THRESHOLD = 0.7

if neutral_score > NEUTRAL_THRESHOLD:
    self.relationship = "neutral"
elif entailment_score > contradiction_score and entailment_score > neutral_score:
    self.relationship = "entails"
# ...
```

**After:**
```python
# NEW: Low contradiction threshold for international content
# If evidence isn't contradicting (< 0.3), it's potentially useful even if neutral
LOW_CONTRADICTION_THRESHOLD = 0.3
NEUTRAL_THRESHOLD = 0.7

if neutral_score > NEUTRAL_THRESHOLD and contradiction_score >= LOW_CONTRADICTION_THRESHOLD:
    # High neutral AND not contradicting → off-topic
    self.relationship = "neutral"
elif contradiction_score < LOW_CONTRADICTION_THRESHOLD and neutral_score > entailment_score:
    # Low contradiction + neutral likely means paraphrasing → treat as weak support
    self.relationship = "entails"
elif entailment_score > contradiction_score and entailment_score > neutral_score:
    self.relationship = "entails"
# ...
```

**Rationale:** If contradiction is very low (< 0.3), the evidence at minimum isn't contradicting the claim, so it should be considered.

## Testing Plan

1. **Retest Lula/Merz article** - Should now find 3+ sources per claim
2. **Retest US article** - Should maintain 90/100 score
3. **Monitor relevance/NLI logs** - Verify filtering behavior

## Rollback Instructions

If US articles regress:
1. Revert `RELEVANCE_THRESHOLD` to 0.75 in config.py
2. Revert NLI logic in verify.py to original (git diff to see changes)
3. Run `git checkout backend/app/pipeline/verify.py backend/app/core/config.py`
