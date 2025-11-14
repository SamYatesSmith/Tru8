# Cross-Run Consistency Analysis
**Same Article, 4 Different Runs - MAJOR INSTABILITY DETECTED**

| Report ID | Time | Score | Claim 1 | Claim 2 (Ballroom) | Claim 9 (Huffman) | Claim 10 (Trust) |
|-----------|------|-------|---------|-------------------|-------------------|------------------|
| **2d5e8c07** | 12:30 | 33/100 | CONTRADICTED 90% | **0 SOURCES** ❌ | SUPPORTED 90% | SUPPORTED 90% |
| **4393e57e** | 12:50 | 28/100 | CONTRADICTED 90% | **0 SOURCES** ❌ | UNCERTAIN 60% | UNCERTAIN 60% |
| **4408b2c1** | 13:02 | 56/100 | CONFLICTING 0% | SUPPORTED 90% ✅ | CONTRADICTED 90% | SUPPORTED 90% |
| **7a47d64a** | 13:25 | 56/100 | **SUPPORTED 90%** ⚠️ | SUPPORTED 90% ✅ | CONTRADICTED 90% | SUPPORTED 90% |

## 🚨 Critical Issues Identified

### Issue 1: Claim 2 (Ballroom) - Evidence Retrieval Failure
**Claim**: "The East Wing demolition is part of a plan to construct a 90,000-square-foot ballroom."

- **Runs 1-2**: Found **0 sources** despite EVERY article mentioning the ballroom
- **Runs 3-4**: Found 3 sources (White House.gov, Al Jazeera, TIME)

**This is impossible** - the ballroom is mentioned in the article title and throughout. Why does evidence retrieval randomly fail?

### Issue 2: Claim 1 - Complete Verdict Flip
**Claim**: "Trump admin decided to demolish without consulting preservation agencies"

- **Runs 1-2**: CONTRADICTED 90%
- **Run 3**: **SUPPORTED 90%** (complete reversal!)
- **Run 4**: CONFLICTING 0%

**Same claim, same article, 3 different verdicts across 4 runs.**

### Issue 3: Claim 9 (Huffman Letter) - Unstable Verdict
**Claim**: "Jared Huffman sent a letter requesting documentation"

- **Run 1**: SUPPORTED 90%
- **Run 2**: UNCERTAIN 60%
- **Runs 3-4**: CONTRADICTED 90%

**The verdict flips from supported → uncertain → contradicted.**

### Issue 4: Claim 10 - Mostly Stable (Good)
**Claim**: "National Trust requested pause"

- **Runs 1, 3-4**: SUPPORTED 90% ✅
- **Run 2**: UNCERTAIN 60%

**This is the ONLY claim showing relative stability.**

## 🔍 Root Cause Hypotheses

### 1. Evidence Retrieval Non-Determinism
- Search queries returning different results each run
- Possible causes:
  - Brave/SERP API randomness
  - No result deduplication across search engines
  - Race conditions in parallel searches
  - Cache invalidation issues

### 2. Judge Prompt Instability
- Same evidence → different verdicts
- Possible causes:
  - Temperature > 0 in judge LLM calls
  - Insufficient grounding in prompt
  - Evidence order affecting judgment
  - Token limit truncation randomness

### 3. NLI Model Issues (Already Fixed)
- We corrected premise/hypothesis order
- But if evidence retrieval is random, NLI scores vary

## 📊 Expected vs Actual Behavior

### Expected: Deterministic System
```
Same Article → Same Claims → Same Evidence → Same Verdicts
```

### Actual: Random System
```
Same Article → Same Claims → RANDOM Evidence → RANDOM Verdicts
```

## 🎯 Investigation Priorities

1. **Immediate**: Check evidence retrieval logic for randomness
2. **Immediate**: Verify judge LLM temperature = 0
3. **High**: Investigate why Claim 2 finds 0 sources (critical bug)
4. **High**: Check if evidence order affects verdict
5. **Medium**: Analyze search query consistency

## 💡 User's Insight

> "Various results that were supported by reasonable evidence and sources, are no longer collecting sufficient sources, or using different sources that report different evidence."

**The user is correct** - this is evidence of:
- Non-deterministic evidence retrieval
- Unstable verdict generation
- Pipeline components working against each other
- Fundamental reliability issue for production

---

**Status**: CRITICAL - System cannot be trusted for production use until consistency is restored.
