# Claim Type Routing Fix - FAILED IMPLEMENTATION

**Date:** October 28, 2025
**Status:** ❌ REVERTED - Implementation caused catastrophic failure (0/100 score)
**Issue:** System only searches news sources, doesn't find primary documents (legislation, books)
**Root Cause:** No claim type detection was happening, all claims defaulting to "current_event"

---

## ⚠️ FAILURE SUMMARY

**What Happened:**
- Implementation completed at 16:10 UTC
- Testing at 16:20 UTC resulted in 0/100 score (down from 50/100 baseline)
- ALL 12 claims showed "Only 0 source(s) found"
- Complete evidence retrieval failure

**Why It Failed:**
1. **Function Signature Mismatch** - evidence.py called search_for_evidence() with `context` and `claim_type` parameters, but search.py didn't accept them → TypeError → 0 results
2. **Incomplete Architecture** - claim_type detection was added but search routing logic was never implemented in search.py
3. **Detector Logic Bug** - Pattern matching required 2+ matches in ONE category, causing legal+historical claims (e.g., "Act of 1966") to fall through to "current_event"

**Changes Reverted:**
- Removed claim_type_detector imports from extract.py (3 locations)
- Reverted evidence.py function signature
- Deleted backend/app/utils/claim_type_detector.py
- Restored 50/100 baseline

**Lessons Learned:**
- ❌ Added downstream functionality WITHOUT verifying upstream infrastructure exists
- ❌ Didn't test signature compatibility before deploying
- ❌ Pattern-matching threshold too strict (2+ required)
- ✅ Need to implement full search routing before adding claim type detection

---

## What Was Broken

### The 33/100 Regression
1. **OpenAI timed out** after 30 seconds
2. **Rule-based fallback** extracted only 3 non-atomic claims
3. **No claim_type fields** were set
4. All claims routed to news search (no books, no legislation found)

### The Baseline (50/100) Problem
1. **ENABLE_CLAIM_CLASSIFICATION = False** (disabled in config)
2. **ClaimClassifier** only detects: opinion, prediction, personal_experience, factual
3. **Search routing needs**: legal, historical, statistical, current_event
4. **All claims defaulted** to "current_event" → only news sources searched

---

## The Minimal Fix

### Created: `backend/app/utils/claim_type_detector.py`

**Purpose:** Simple rule-based detector that classifies claims for search routing

**Detection Logic:**

```python
# Legal claims → Primary documents (legislation, court docs)
legal_patterns = [
    "act", "law", "legislation", "statute", "regulation",
    "court", "judge", "ruling", "supreme court", etc.
]

# Historical claims → Books, archives
historical_patterns = [
    Years 1900-2022, "century", "founded in 1966",
    "during 2020", "historical", etc.
]

# Statistical claims → Academic papers, research
statistical_patterns = [
    "X percent", "X million", "study showed",
    "research found", "increased by X", etc.
]

# Default → Current event (news sources)
```

**Output:**
- `claim_type`: "legal", "historical", "statistical", or "current_event"
- `requires_primary_source`: True for legal/historical, False otherwise
- `confidence`: 0.7-0.9 depending on match strength
- `reasoning`: Explains detection

---

### Modified: `backend/app/pipeline/extract.py`

**What Changed:**

Added **post-processing step** to ALL extraction methods:
1. **OpenAI** (lines 151-158)
2. **Anthropic** (lines 261-265)
3. **Rule-based fallback** (lines 320-324)

```python
# Post-processing: claim type detection
from app.utils.claim_type_detector import get_claim_type_detector
claim_type_detector = get_claim_type_detector()
for claim in claims:
    claim_type_detector.enrich_claim(claim)
```

**Why This Works:**
- ✅ Runs consistently for ALL extraction methods
- ✅ Doesn't modify Pydantic models (no validation errors)
- ✅ Doesn't change LLM prompts (no extraction failures)
- ✅ Even if OpenAI times out → rule-based fallback → still gets claim_type
- ✅ Minimal code change (3 insertions, ~10 lines each)

---

## Expected Improvements

### White House Article Test Case

**Before (baseline 50/100):**
- Claim: "The National Historic Preservation Act of 1966 requires..."
- `claim_type`: "current_event" (default)
- **Search**: News sources only
- **Evidence**: BBC, Roll Call articles
- **Result**: No primary legislation found

**After (with fix):**
- Claim: "The National Historic Preservation Act of 1966 requires..."
- `claim_type`: "legal" (detected via "Act", "1966", "requires")
- `requires_primary_source`: True
- **Search**: Primary documents FIRST (govinfo.gov, legislation.gov.uk) + news
- **Evidence**: Actual legislation text, court documents
- **Result**: Primary sources found!

**Other Claims:**
- "Trump demolished..." → "current_event" (news sources)
- "Sara Bronin chaired..." → "current_event" (bio sources)
- "90,000-square-foot ballroom" → "statistical" if includes numbers

---

## What This Doesn't Fix

**Still Need To Address** (separate sessions):
1. **NLI too literal** - "without consulting" vs "bypassed process" not recognized as equivalent
2. **Consensus threshold bugs** - 53% marked weak at 50% threshold
3. **Search relevance** - Irrelevant Wikipedia results
4. **OpenAI timeouts** - Need better timeout handling or retry logic

---

## Testing Recommendations

### Test 1: Legal Claim
**Input:** Article mentioning "National Historic Preservation Act of 1966"
**Expected:**
- Claim classified as "legal"
- Search hits govinfo.gov, legislation.gov.uk
- Primary legislation text in evidence

### Test 2: Historical Claim
**Input:** Article about "Founded in 1952" or "During the 1990s"
**Expected:**
- Claim classified as "historical"
- Search hits Google Books, academic sources
- Book references in evidence

### Test 3: Statistical Claim
**Input:** "40% of voters support..." or "Increased by 12 million"
**Expected:**
- Claim classified as "statistical"
- Search finds research papers, polls
- Data sources in evidence

### Test 4: Current Event (default)
**Input:** "Trump announced today..."
**Expected:**
- Claim classified as "current_event"
- Standard news search
- Recent news sources

---

## Rollback Plan

If this causes issues:

```bash
cd backend
git restore app/pipeline/extract.py
rm app/utils/claim_type_detector.py
```

Then restart Celery worker.

---

## Success Criteria

**Minimum Success (better than 50/100):**
- ✅ Legal claims find at least 1 primary document
- ✅ OpenAI timeout doesn't crash (rule-based fallback still works)
- ✅ Claims still extract correctly (no validation errors)

**Target Success (70-80/100):**
- ✅ Legal claims find 2-3 primary documents
- ✅ Historical claims find book references
- ✅ Reduced abstentions (better sources = more confidence)
- ✅ Overall score improves by 20+ points

---

*Implementation completed: October 28, 2025 16:10 UTC*
*Ready for testing with White House demolition article*
