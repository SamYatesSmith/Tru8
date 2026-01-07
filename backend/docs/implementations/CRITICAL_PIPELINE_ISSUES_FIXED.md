# Critical Pipeline Issues - Diagnosis & Fixes

**Report ID**: 4bf1314d
**Date**: 2025-11-13
**Status**: 1 FIXED, 1 REQUIRES FURTHER INVESTIGATION

---

## Issue #1: Legal Claims Not Using GovInfo.gov API ✅ FIXED

### Symptoms
- Claim 4: "The National Historic Preservation Act of 1966 exempts the White House from its provisions."
- Evidence sources: PolitiFact, BBC, Snopes (all web search)
- NO GovInfo.gov sources despite having valid GOVINFO_API_KEY

### Root Cause
**Celery workers run in SEPARATE processes from FastAPI server.**

The API adapters were initialized in `main.py` (FastAPI lifespan), but Celery workers never initialized them. Each worker process had an empty adapter registry.

### Evidence of Root Cause
```bash
# Test showed:
- Adapter registered at startup: ✅ 8 adapters in FastAPI process
- Adapter registry in worker: ❌ 0 adapters
- GovInfo adapter created successfully
- But searches returned 0 results because registry was empty
```

### Fix Applied
**Commit**: f45db33 - "CRITICAL: Initialize API adapters in Celery worker"

Added `worker_ready` signal handler in `app/workers/__init__.py`:
```python
@worker_ready.connect
def initialize_worker(**kwargs):
    """Initialize API adapters when Celery worker starts."""
    if settings.ENABLE_API_RETRIEVAL:
        from app.services.api_adapters import initialize_adapters
        initialize_adapters()
        logger.info("✅ API adapters initialized in Celery worker")
```

### Testing Required
1. **Restart Celery worker** (critical!)
2. Run fact-check on legal claim
3. Verify logs show:
   ```
   "✅ API adapters initialized in Celery worker"
   "🔎 API routing START - claim_type: legal"
   "📊 Found N adapters for domain=Law, jurisdiction=US"
   "🔍 GovInfoAdapter.search() CALLED"
   ```
4. Check PDF results for GovInfo.gov sources

---

## Issue #2: Ballroom Claim Incorrectly Marked as "Contradicted" ⚠️ NEEDS INVESTIGATION

### Symptoms
- **Claim 2**: "The East Wing demolition project is part of plans to construct a 90,000-square-foot ballroom."
- **Current Verdict**: contradicted (90% confidence)
- **Expected Verdict**: supported (claim is TRUE per PBS, BBC, NPR)

### Evidence Analysis
**Supporting Sources (all confirm the claim)**:
- PBS: "Trump insists... adding the massive 90,000-square-foot, glass-walled space"
- BBC: "critics fear the new 90,000-sq-ft building"
- NPR: Multiple confirmations

**The Snopes "Fake" Verdict**:
- Snopes.com: "Rumored rendering of Trump's planned White House ballroom isn't ... Fact-check verdict: Fake..."

### The Problem
The judge is interpreting Snopes' "fake" verdict as contradicting the **entire project**, when Snopes is actually saying a **rendering IMAGE** is fake, NOT the project itself.

### Judge's Reasoning (Incorrect)
> "high-quality evidence from Snopes indicates that this claim is fake, which directly contradicts the assertion"

This is a **misinterpretation** of the Snopes article context.

### Possible Causes
1. **NLI Model Issue**: The DeBERTa NLI model incorrectly scores Snopes evidence as "contradict"
2. **Judge Prompt Issue**: The judge doesn't understand that "fake rendering" ≠ "fake project"
3. **Snopes Snippet Extraction**: Only the "Fact-check verdict: Fake" text is extracted, missing context
4. **Evidence Weighting**: Snopes (0.85 credibility) is given too much weight vs PBS/BBC/NPR

### Classification Check
```python
classifier.classify(claim2)
# Result: claim_type='factual', verifiable=True ✅
```
Classification is correct, so the issue is in **verify.py** or **judge.py**.

### Next Steps to Diagnose
1. **Check NLI scores** for this claim:
   - What is the entailment score for Snopes evidence?
   - Are PBS/BBC/NPR scored as "entailment" or "neutral"?

2. **Check Snopes content extraction**:
   - What text snippet was extracted from Snopes article?
   - Does it include the word "rendering" or just "fake"?

3. **Check judge reasoning**:
   - What was the full judge prompt input?
   - How did the judge weigh the 1 Snopes "contradict" vs 2+ PBS/BBC "support"?

4. **Test Snopes article directly**:
   ```python
   # Fetch and parse Snopes article
   # Check what text is actually being passed to NLI model
   ```

### Recommended Fixes (After Diagnosis)
- **Option A**: Improve evidence snippet extraction to include more context
- **Option B**: Add special handling for "rendering" / "image" mentions in fact-check articles
- **Option C**: Adjust Snopes credibility score for image-related fact-checks
- **Option D**: Improve judge prompt to distinguish "fake rendering" from "fake claim"

---

## Environment Configuration

**CRITICAL**: Ensure these are set in `backend/.env`:
```bash
# Government API Integration
ENABLE_API_RETRIEVAL=true
GOVINFO_API_KEY=RCQ5FLZQLHjT2VVnll00IWnFG9QLZr33nquGJA29

# Claim Classification
ENABLE_CLAIM_CLASSIFICATION=true
```

---

## Restart Instructions

### 1. Restart Celery Worker (REQUIRED for Issue #1 fix)
```bash
# Stop existing worker (if running)
pkill -f "celery.*worker"  # Linux/Mac
# Or manually stop on Windows

# Start worker with logging
cd backend
celery -A app.workers.celery_app worker --loglevel=info
```

**Verify adapter initialization in logs**:
```
"Celery worker starting - initializing API adapters..."
"✅ Registered GovInfo.gov adapter for US legal statutes"
"✅ API adapters initialized in Celery worker"
```

### 2. FastAPI Server (Already Running)
The FastAPI server auto-reloaded with the previous fix and is working correctly.

---

## Testing Checklist

### Test Case 1: Legal Statute Claim
- [ ] Restart Celery worker
- [ ] Submit claim: "The National Historic Preservation Act of 1966 exempts the White House."
- [ ] Check evidence sources include "GovInfo.gov"
- [ ] Verify verdict is based on authoritative legal sources

### Test Case 2: Ballroom Project Claim
- [ ] Submit claim: "The East Wing demolition project is part of plans to construct a 90,000-square-foot ballroom."
- [ ] Verify verdict is "supported" (not "contradicted")
- [ ] Check Snopes evidence is correctly interpreted

---

## Summary

| Issue | Status | Commit | Action Required |
|-------|--------|--------|----------------|
| Legal API routing | ✅ FIXED | f45db33 | Restart Celery worker |
| Ballroom contradiction | ⚠️ INVESTIGATING | - | Further diagnosis needed |

**Priority**: Restart Celery worker IMMEDIATELY to apply Issue #1 fix.
