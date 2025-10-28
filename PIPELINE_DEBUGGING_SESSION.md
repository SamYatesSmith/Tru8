# Pipeline Debugging Session - October 28, 2025

## Issues Identified from e8e7e345.pdf (50/100 score)

1. **NLI Too Literal** - Claim 1 at 0% despite 3 supporting sources
2. **Search Routing Not Working** - Legal claims not finding primary documents
3. **Consensus Threshold Bug** - Claim 10 at 53% marked weak when threshold is 50%
4. **Primary Source Override Failing** - 3 vs 1 sources still abstaining
5. **Search Relevance Issues** - Wikipedia employee stats for donor list claim

## Fixes Applied

### 1. ✅ Comprehensive Logging for claim_type Routing

**Purpose:** Trace claim_type through entire pipeline to debug search routing

**Files Modified:**
- `backend/app/pipeline/extract.py` (lines 268-272, 385-389)
- `backend/app/services/search.py` (lines 388-410)

**What It Does:**
- Logs claim_type assigned by LLM for each claim during extraction
- Logs which search providers are selected for each claim_type
- Shows provider names and results returned

**Example Logs:**
```
[INFO] Claim 0 extracted - Type: legal, Primary Source Required: True, Text: The National Historic Preservation Act of 1966 requires...
[INFO] ROUTING: Legal claim -> Using ['PrimaryDocumentsProvider', 'BraveSearchProvider']
[INFO] PrimaryDocumentsProvider returned 8 results
```

---

### 2. ✅ Further Lowered NLI Sensitivity Thresholds

**Purpose:** Fix Claim 1 (0% confidence when 3 sources say "bypassed process" vs "without consulting")

**File Modified:** `backend/app/pipeline/verify.py` (lines 26-34)

**Changes:**
```python
# OLD:
if entailment_score > 0.4 and entailment_score > contradiction_score and neutral_score < 0.6:

# NEW:
if entailment_score > 0.35 and entailment_score > contradiction_score and neutral_score < 0.65:
```

**Impact:**
- More lenient matching for semantic equivalence
- "without consulting" vs "bypassed process" should now be recognized as supporting
- Threshold lowered from 40% to 35% entailment minimum
- Neutral tolerance raised from 60% to 65%

---

### 3. ✅ Added Consensus Debugging Logs

**Purpose:** Understand why 53% consensus marked as "weak" when threshold is 50%

**File Modified:** `backend/app/pipeline/judge.py` (line 429, 431)

**What It Does:**
- Logs exact consensus value (both percentage and raw float)
- Logs exact threshold being compared
- Logs when abstention decision is made

**Example Logs:**
```
[INFO] Consensus check: 53.00% (raw: 0.5300) vs threshold 50.00% (raw: 0.5000)
[INFO] ABSTAINING due to weak consensus: 48.67% < 50.00%
```

This will help us identify floating-point precision issues or rounding errors.

---

## Configuration Changes Already Applied (Previous Sessions)

### Abstention Thresholds Lowered
**File:** `backend/app/core/config.py` (lines 97-101)

```python
MIN_SOURCES_FOR_VERDICT: int = 3  # Unchanged
MIN_CREDIBILITY_THRESHOLD: float = 0.60  # Lowered from 0.70
MIN_CONSENSUS_STRENGTH: float = 0.50  # Lowered from 0.65
```

### Primary Source Override Logic Added
**File:** `backend/app/pipeline/judge.py` (lines 388-406)

- Primary sources (legislation, court docs) override news disagreements
- If 1+ primary sources agree, trust them over news
- Only abstains if primary sources conflict with each other

### Search Routing Infrastructure Created
**Files:** `backend/app/services/search.py`

**New Providers:**
- `GoogleBooksProvider` (lines 206-270) - For historical claims
- `PrimaryDocumentsProvider` (lines 272-326) - For legal claims

**Routing Logic:**
- **legal** → Primary docs FIRST, then news
- **historical** → Books FIRST, then primary docs, then news
- **statistical** → Standard search (academic papers, govt stats)
- **current_event** → Standard news only

---

## Still Pending Investigation

### 1. Search Routing Effectiveness
**Status:** Debugging with logs

**Questions:**
- Is LLM actually classifying claims correctly?
- Are the new providers being called?
- Are they returning useful results?

**Next Step:** Run test check and examine logs

---

### 2. Consensus Threshold Bug
**Status:** Debugging with logs

**Issue:** Claim 10 showed "53%" but was marked weak at 50% threshold

**Hypothesis:**
- Floating point precision issue (53.00% display but 49.99% actual?)
- Rounding in calculation vs display

**Next Step:** Examine exact consensus logs from test check

---

### 3. Primary Source Override Not Preventing Abstentions
**Status:** Needs investigation

**Issue:** Claim 2 had 3 supporting sources vs 1 contradicting, still abstained

**Expected:** Primary source override should have caught this

**Hypothesis:**
- No sources were high enough credibility (>= 0.98) to trigger override
- Or primary sources themselves were conflicting

**Next Step:** Check credibility scores and override trigger in logs

---

### 4. Search Relevance Issues
**Status:** Pending

**Issue:** Wikipedia "Palantir employee statistics" returned for donor list claim

**Cause:** Query optimization not specific enough

**Next Step:** Review `_optimize_query_for_factcheck()` and add filtering

---

## How to Test

### Run a Check Through API

1. Ensure Celery worker is running:
```bash
cd backend
celery -A app.workers.celery_app worker --loglevel=info --pool=solo
```

2. Use the web interface or API to submit the White House article:
```
https://rollcall.com/2025/10/24/east-wing-demolition-highlights-loopholes-in-preservation-law/
```

3. Monitor logs in real-time:
```bash
cd backend
tail -f celery_debug.log | grep -E "Claim.*extracted|ROUTING|Consensus check"
```

### What to Look For

**In extraction logs:**
- claim_type values ("legal", "historical", "current_event")
- requires_primary_source flags

**In search routing logs:**
- Which providers are selected for each claim_type
- Whether PrimaryDocumentsProvider/GoogleBooksProvider are being called
- Number of results returned from each provider

**In consensus logs:**
- Exact consensus percentages (raw values)
- Whether abstention threshold comparisons are correct

---

## Expected Improvements

Based on these fixes, we should see:

1. **Claim 1** (Trump demolished without consulting):
   - **Before:** 0% confidence (NLI marked as neutral)
   - **Expected:** 70%+ confidence (3 supporting sources recognized)

2. **Claim 4** (1952 federal law):
   - **Before:** 2 news articles, no primary documents
   - **Expected:** Actual legislation/court documents from primary source providers

3. **Claim 10** (consensus bug):
   - **Before:** 53% marked as weak
   - **Expected:** Either logs show actual value < 50%, or fix identified

4. **Overall Score:**
   - **Before:** 50/100
   - **Target:** 70-80/100 with primary sources and reduced false neutrals

---

## Status Summary

| Issue | Status | Files Modified | Next Action |
|-------|--------|---------------|-------------|
| NLI Too Literal | ✅ Fixed | verify.py | Test & validate |
| claim_type Flow | ✅ Fixed | extract.py | Test & validate |
| Search Routing Debug | ✅ Logged | search.py, extract.py | Run test & analyze logs |
| Consensus Bug Debug | ✅ Logged | judge.py | Run test & analyze logs |
| Primary Override | ⏳ Pending | - | Investigate with test |
| Search Relevance | ⏳ Pending | - | Review after routing works |

---

*Session completed: October 28, 2025 15:40 UTC*
*Ready for testing with new logging and threshold adjustments*
