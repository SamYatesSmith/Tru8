# 🔍 Government API Integration Plan - Second Audit
## Comprehensive Accuracy Verification

**Date:** 2025-01-11
**Auditor:** Claude (Second Pass)
**Plan Version:** 2.0 (GOVERNMENT_API_INTEGRATION_PLAN.md)

---

## ✅ AUDIT SUMMARY

**Status:** **APPROVED WITH 5 CRITICAL CORRECTIONS REQUIRED**

The plan is fundamentally sound and non-duplicative, but needs 5 specific fixes to ensure full compatibility with existing pipeline features.

---

## 1. ✅ ZERO DUPLICATION VERIFICATION

### 1.1 Classification System

**Existing:** `backend/app/utils/claim_classifier.py` (213 lines)
- ✅ Returns: `claim_type`, `is_verifiable`, `jurisdiction`, `metadata`
- ✅ Already detects: factual, opinion, prediction, legal, personal
- ✅ Already extracts: legal citations, jurisdiction (UK/US), year

**Plan Adds:** `_detect_domain()` method (~50 lines)
- ✅ Returns: `domain` field (Finance, Health, Law, etc.)
- ✅ Uses keyword matching (fast, no GPT-4 cost)
- ✅ Reuses existing legal detection logic

**VERDICT:** ✅ **EXTENDS CORRECTLY** - No duplication

---

### 1.2 Caching System

**Existing:** `backend/app/services/cache.py`
- ⚠️ **Currently DISABLED** in pipeline.py line 227:
  ```python
  # DISABLED: Cache service causing event loop issues in Celery - set to None for now
  cache_service = None
  ```

**Plan Fixes:**
- ✅ Creates `get_sync_cache_service()` for Celery context
- ✅ Adds `get_cached_api_response()` and `cache_api_response()` methods
- ✅ Fixes event loop issue with Redis blocking mode

**VERDICT:** ✅ **EXTENDS & FIXES CORRECTLY** - No duplication

---

### 1.3 Credibility System

**Existing:** `backend/app/services/source_credibility.py` (150 lines)
- ✅ Loads tiers from `backend/app/data/source_credibility.json`
- ✅ Returns: `tier`, `credibility` (0-1), `risk_flags`, `auto_exclude`

**Plan Adds:**
- ✅ Registers 15 new API domains in JSON (or `_check_api_domains()` method)
- ✅ Marks all as Tier 1 (`credibility: 1.0`)

**VERDICT:** ✅ **EXTENDS CORRECTLY** - No duplication

---

### 1.4 Legal API System

**Existing:** `backend/app/services/legal_search.py` (441 lines)
- ✅ Already queries: GovInfo.gov, Congress.gov (US)
- ✅ Already queries: legislation.gov.uk (UK)
- ✅ Returns formatted statute results

**Plan:**
- ✅ Reuses existing `LegalSearchService` (NO new legal APIs)
- ✅ Calls it when `domain == "Law"`

**VERDICT:** ✅ **REUSES CORRECTLY** - No duplication

---

### 1.5 Fact-Check API System

**Existing:** `backend/app/services/factcheck_api.py` (186 lines)
- ✅ Already queries: Google Fact Check Explorer API
- ✅ Already has `convert_to_evidence()` method
- ✅ Currently called in Stage 2.5 (pipeline.py line 286-296)

**Plan:**
- ✅ Moves fact-check API calls into Stage 3 (retrieve.py)
- ✅ Consolidates ALL external APIs in one place
- ✅ Reuses existing `FactCheckAPI` class

**VERDICT:** ✅ **CONSOLIDATES CORRECTLY** - No duplication

---

## 2. ✅ EXISTING PIPELINE FEATURES PRESERVED

### 2.1 Pipeline Stages (Unchanged)

```
Stage 1: Ingest (line 238)           ✅ Not affected
Stage 2: Extract (line 259)           ✅ Not affected
Stage 2.5: Fact-check (line 286)      ⚠️ MOVED to Stage 3
Stage 3: Retrieve (line 298)          ✅ ENHANCED (adds APIs)
Stage 4: Verify (line 319)            ✅ Not affected
Stage 5: Judge (line 350)             ✅ Not affected
Stage 5.5: Query Answer (line 386)    ✅ Not affected
Stage 6: Summary (line 479)           ✅ Not affected
```

**VERDICT:** ✅ **PIPELINE STRUCTURE PRESERVED**

---

### 2.2 Feature Flags (All Must Work)

From `backend/app/core/config.py` lines 71-132:

| Feature Flag | Status | Impact from Plan |
|--------------|--------|------------------|
| `ENABLE_DOMAIN_CAPPING` | ✅ True | ✅ Applied AFTER evidence retrieved (line 335-345) |
| `ENABLE_DEDUPLICATION` | ✅ True | ✅ Applied AFTER evidence retrieved (line 320-324) |
| `ENABLE_SOURCE_DIVERSITY` | ✅ True | ✅ Applied AFTER evidence retrieved (line 327-332) |
| `ENABLE_CONTEXT_PRESERVATION` | ✅ True | ⚠️ **NEEDS FIX** - Not passed to APIs |
| `ENABLE_TEMPORAL_CONTEXT` | ✅ True | ✅ Applied AFTER evidence retrieved (line 310-316) |
| `ENABLE_DOMAIN_CREDIBILITY_FRAMEWORK` | ✅ True | ✅ Already extended in plan |
| `ENABLE_SOURCE_VALIDATION` | ✅ True | ✅ Applied AFTER evidence retrieved (line 348-355) |
| `ENABLE_FACTCHECK_API` | ✅ True | ✅ Consolidated into Stage 3 |
| `ENABLE_LEGAL_SEARCH` | ✅ True | ✅ Reused in plan |
| `ENABLE_CROSS_ENCODER_RERANK` | ✅ False | ✅ Applied AFTER evidence retrieved (line 194-259) |

**VERDICT:** ✅ **ALL FEATURES PRESERVED** (1 fix needed - see Section 3)

---

### 2.3 Evidence Processing Chain

Evidence goes through this chain in retrieve.py:

```
1. Retrieved from sources (APIs + web)
2. Ranked by embeddings (line 131-193)        ✅ Works with API evidence
3. Cross-encoder reranked (line 194-259)      ✅ Works with API evidence
4. Credibility weighted (line 261-370)        ✅ Works with API evidence
5. Temporal filtered (line 310-316)           ✅ Works with API evidence
6. Deduplicated (line 320-324)                ✅ Works with API evidence
7. Source diversity checked (line 327-332)    ✅ Works with API evidence
8. Domain capped (line 335-345)               ✅ Works with API evidence
9. Source validated (line 348-355)            ✅ Works with API evidence
```

**Why it works:** API evidence has same fields as web evidence (url, source, credibility_score, etc.)

**VERDICT:** ✅ **FULL COMPATIBILITY**

---

### 2.4 NLI Verification Compatibility

From `backend/app/pipeline/verify.py` line 17-18:

```python
def __init__(self, claim_text: str, evidence_text: str, ...):
```

NLI verifier expects `evidence_text` field.

**Plan's API evidence format** (from government_api_client.py):
```python
{
    "source": ...,
    "url": ...,
    "snippet": ...,  # ⚠️ ISSUE: Should be "text"
    ...
}
```

**Web evidence format** (from retrieve.py line 153-166):
```python
{
    "text": snippet.text,  # ✅ Correct field name
    ...
}
```

**ISSUE FOUND:** API evidence uses "snippet", NLI expects "text"

**VERDICT:** ⚠️ **FIX REQUIRED** - See Section 3.1

---

### 2.5 Judge Compatibility

From `backend/app/pipeline/judge.py` lines 14-35:

Judge expects evidence with:
- `text` or `snippet` (it checks both)
- `source`, `url`, `title`
- `credibility_score`, `relevance_score`

**Pipeline save logic** (pipeline.py line 187):
```python
snippet=ev_data.get("snippet", ev_data.get("text", ""))  # ✅ Accepts either
```

**VERDICT:** ✅ **COMPATIBLE** (but should standardize on "text")

---

## 3. 🚨 CRITICAL CORRECTIONS REQUIRED

### **3.1 FIX: Evidence Field Consistency**

**Issue:** API evidence uses different field names than web evidence.

**Current inconsistency:**
| Field | Web Evidence | API Evidence | NLI Expects |
|-------|--------------|--------------|-------------|
| Content | `text` | `snippet` | `text` |
| ID | `id` | Missing | Optional |
| Similarity | `semantic_similarity` | Missing | Optional |
| Combined | `combined_score` | Missing | Optional |
| Word Count | `word_count` | Missing | Optional |

**Required Fix in plan's `government_api_client.py` line 143-158:**

```python
# CURRENT (WRONG):
def _convert_to_evidence(self, api_result: Dict, api_name: str) -> Dict[str, Any]:
    return {
        "source": api_result.get("source", api_name),
        "url": api_result.get("url", ""),
        "title": api_result.get("title", ""),
        "snippet": api_result.get("content", ...),  # ❌ WRONG FIELD NAME
        ...
    }

# CORRECTED (RIGHT):
def _convert_to_evidence(self, api_result: Dict, api_name: str, idx: int = 0) -> Dict[str, Any]:
    text_content = api_result.get("content", api_result.get("snippet", ""))

    return {
        "id": f"evidence_api_{idx}",  # ✅ Add ID
        "text": text_content,  # ✅ Use "text" field
        "snippet": text_content[:300],  # ✅ Add snippet (first 300 chars)
        "source": api_result.get("source", api_name),
        "url": api_result.get("url", ""),
        "title": api_result.get("title", ""),
        "published_date": api_result.get("published_date"),
        "relevance_score": api_result.get("relevance_score", 0.9),
        "credibility_score": api_result.get("credibility_score", 0.95),
        "semantic_similarity": 0.9,  # ✅ Default high for API matches
        "combined_score": 0.925,  # ✅ (relevance + semantic) / 2
        "word_count": len(text_content.split()),  # ✅ Add word count
        "source_type": "api",
        "external_source_provider": api_name,
        "metadata": api_result.get("metadata", {})
    }
```

**Impact:** HIGH - NLI verification will fail without "text" field

---

### **3.2 FIX: Context Not Passed to APIs**

**Issue:** `subject_context` and `key_entities` are not passed to API queries.

From retrieve.py lines 87-99, web search uses context:
```python
subject_context = claim.get("subject_context")
key_entities = claim.get("key_entities", [])

evidence_snippets = await self.evidence_extractor.extract_evidence_for_claim(
    claim_text,
    subject_context=subject_context,  # ✅ Passed to web search
    key_entities=key_entities
)
```

**Plan's API call** (government_api_client.py line 40-46):
```python
async def search_by_domain(
    self,
    claim_text: str,
    domain: str,
    jurisdiction: str = "Global",
    max_results: int = 10  # ❌ Missing context parameters
) -> List[Dict[str, Any]]:
```

**Required Fix:**

```python
# CORRECTED:
async def search_by_domain(
    self,
    claim_text: str,
    domain: str,
    jurisdiction: str = "Global",
    max_results: int = 10,
    subject_context: Optional[str] = None,  # ✅ Add context
    key_entities: Optional[List[str]] = None  # ✅ Add entities
) -> List[Dict[str, Any]]:
    """
    Search APIs for a specific domain.

    Args:
        ...
        subject_context: Main subject/topic for enhanced query building
        key_entities: Key entities to include in search
    """
    # Some adapters can use this context to build better queries
    # e.g., PubMed can add entities as MeSH terms
    # e.g., ONS can filter datasets by topic
```

**Impact:** MEDIUM - Context improves relevance but not critical for v1

---

### **3.3 FIX: Legal Metadata Access Path**

**Issue:** Plan incorrectly accesses legal metadata.

**Plan's code** (retrieve.py modification):
```python
legal_metadata = claim.get("legal_metadata", {})  # ❌ WRONG PATH
```

**Correct path** (from claim_classifier.py line 56-63):
```python
if any(re.search(pattern, claim_lower) for pattern in self.legal_patterns):
    metadata = self._extract_legal_metadata(claim_text, claim_lower)
    return {
        "claim_type": "legal",
        "metadata": metadata  # ✅ It's in "metadata", not "legal_metadata"
    }
```

**Required Fix:**

```python
# CORRECTED:
classification = classifier.classify(claim["text"])

if self.legal_search and classification["claim_type"] == "legal":
    legal_metadata = classification.get("metadata", {})  # ✅ Correct path
    sources.append(
        self.legal_search.search_statutes(claim_text, legal_metadata)
    )
```

**Impact:** MEDIUM - Legal claims won't route to legal APIs without fix

---

### **3.4 FIX: Fact-Check Evidence Parameter Handling**

**Issue:** Plan removes `factcheck_evidence` parameter but function expects it.

**Current function signature** (retrieve.py line 807):
```python
async def retrieve_evidence_with_cache(
    claims: List[Dict[str, Any]],
    cache_service,
    factcheck_evidence: Dict = None,  # ✅ Expected parameter
    source_url: Optional[str] = None
) -> Dict[str, List[Dict[str, Any]]]:
```

**Current merge logic** (retrieve.py lines 855-860):
```python
# Merge with fact-check evidence if provided
if factcheck_evidence and str(i) in factcheck_evidence:
    evidence_list = factcheck_evidence[str(i)] + evidence_list
```

**Plan's modification** (pipeline.py):
```python
# PLAN SAYS:
evidence = asyncio.run(retrieve_evidence_with_cache(
    claims,
    cache_service,
    source_url=source_url  # ❌ Missing factcheck_evidence parameter
))
```

**Required Fix - Option A (Keep parameter, pass empty):**
```python
# In pipeline.py, keep the parameter but pass empty dict:
evidence = asyncio.run(retrieve_evidence_with_cache(
    claims,
    cache_service,
    factcheck_evidence={},  # ✅ Pass empty (fact-check now handled in retrieve.py)
    source_url=source_url
))
```

**Required Fix - Option B (Make parameter truly optional):**
```python
# In retrieve.py, make parameter have default value:
async def retrieve_evidence_with_cache(
    claims: List[Dict[str, Any]],
    cache_service,
    source_url: Optional[str] = None,  # Move source_url up
    factcheck_evidence: Optional[Dict] = None  # ✅ Make optional with default None
) -> Dict[str, List[Dict[str, Any]]]:
```

**Recommendation:** Use Option B (cleaner)

**Impact:** LOW - Easy fix, won't break anything

---

### **3.5 FIX: Evidence Index Tracking**

**Issue:** API evidence conversion needs index for ID generation.

**Current plan** (government_api_client.py line 92-100):
```python
# Query APIs in parallel
results = await asyncio.gather(*tasks, return_exceptions=True)

# Merge results
all_evidence = []
for adapter, result in zip(relevant_adapters[:3], results):
    if result:
        evidence_items = [
            self._convert_to_evidence(item, adapter.name)  # ❌ No index
            for item in result
        ]
```

**Required Fix:**
```python
# CORRECTED:
all_evidence = []
evidence_idx = 0  # ✅ Track index across all APIs

for adapter, result in zip(relevant_adapters[:3], results):
    if isinstance(result, Exception):
        logger.error(f"{adapter.name} failed: {result}")
        continue

    if result:
        evidence_items = [
            self._convert_to_evidence(item, adapter.name, evidence_idx + i)  # ✅ Pass index
            for i, item in enumerate(result)
        ]
        all_evidence.extend(evidence_items)
        evidence_idx += len(evidence_items)
```

**Impact:** LOW - Just for consistent ID generation

---

## 4. ✅ DATABASE SCHEMA VERIFICATION

### 4.1 Evidence Table Changes

**Existing fields** (check.py lines 99-151):
```python
is_factcheck: bool = Field(default=False)              # ✅ Already exists
factcheck_publisher: Optional[str] = None              # ✅ Can reuse for API name
source_type: Optional[str] = None                      # ✅ Already exists
metadata: Optional[Dict] = Field(default={}, sa_column=...)  # ✅ Already exists (JSONB)
```

**Plan proposes** (Option A - Reuse):
- Use `source_type = 'api'`
- Use `factcheck_publisher` for API name
- Use `metadata` JSONB for API details

**Plan proposes** (Option B - New fields):
```sql
ALTER TABLE evidence
ADD COLUMN external_source_type VARCHAR(50),
ADD COLUMN external_source_provider VARCHAR(200);
```

**VERDICT:** ✅ **BOTH OPTIONS VALID**
- Option A: Zero migration needed (use existing fields)
- Option B: Clearer semantics (small migration)

**Recommendation:** Use Option A for MVP (zero downtime)

---

### 4.2 Check Table Changes

**Plan adds** (optional):
```sql
ALTER TABLE "check"
ADD COLUMN api_sources_used JSONB,
ADD COLUMN api_call_count INTEGER DEFAULT 0,
ADD COLUMN api_coverage_percentage DECIMAL(5,2);
```

**VERDICT:** ✅ **OPTIONAL BUT USEFUL**
- Good for analytics dashboards
- Not required for core functionality

---

## 5. ✅ INTEGRATION POINT VERIFICATION

### 5.1 Stage 3: Retrieve Evidence

**Current code** (pipeline.py lines 298-317):
```python
# Stage 3: Retrieve evidence (REAL IMPLEMENTATION WITH CACHING)
self.update_state(state="PROGRESS", meta={"stage": "retrieve", "progress": 40})

try:
    source_url = content.get("metadata", {}).get("url")

    evidence = asyncio.run(retrieve_evidence_with_cache(
        claims,
        cache_service,
        factcheck_evidence,  # From Stage 2.5
        source_url=source_url
    ))
```

**Plan's change:** Consolidate Stage 2.5 into Stage 3

**Modified code:**
```python
# Stage 3: Retrieve evidence (ALL SOURCES CONSOLIDATED)
self.update_state(state="PROGRESS", meta={"stage": "retrieve", "progress": 40})

try:
    source_url = content.get("metadata", {}).get("url")

    # Fact-check API now handled inside retrieve_evidence_with_cache
    evidence = asyncio.run(retrieve_evidence_with_cache(
        claims,
        cache_service,
        source_url=source_url  # factcheck_evidence removed
    ))
```

**VERDICT:** ✅ **CLEAN CONSOLIDATION**

---

### 5.2 Retrieve.py Refactoring

**Current flow:**
```
_retrieve_evidence_for_single_claim()
    → extract_evidence_for_claim() [web search]
    → _rank_evidence_with_embeddings()
    → _apply_credibility_weighting()
```

**Plan's enhanced flow:**
```
_retrieve_evidence_for_single_claim()
    → Query sources in parallel:
        - government_api.search_by_domain() [NEW]
        - legal_search.search_statutes() [EXISTING]
        - factcheck_api.search_fact_checks() [EXISTING]
        - extract_evidence_for_claim() [EXISTING web search]
    → Merge all sources
    → _rank_evidence_with_embeddings() [EXISTING]
    → _apply_credibility_weighting() [EXISTING]
```

**VERDICT:** ✅ **LOGICAL ENHANCEMENT**
- All existing methods preserved
- Just adds parallel API queries before ranking

---

## 6. ✅ PERFORMANCE VERIFICATION

### 6.1 Latency Budget

**Target:** <10s P95 latency (existing requirement)

**Breakdown:**
- Claim extraction: ~2s (existing)
- Evidence retrieval: ~5s (current web search)
- NLI verification: ~2s (existing)
- Judge: ~3s (existing)
- **Total:** ~12s (current baseline)

**With APIs added:**
- Claim extraction: ~2s (unchanged)
- Classification: +0.1s (keyword matching, not GPT-4)
- Evidence retrieval: ~5s (3 APIs in parallel + web = same time)
- Cache hit: ~0.1s (API responses cached)
- NLI verification: ~2s (unchanged)
- Judge: ~3s (unchanged)
- **Total:** ~12.1s (minimal increase)

**With caching (60% hit rate):**
- 60% of claims: ~7s (cache hits)
- 40% of claims: ~12s (fresh queries)
- **Average:** ~9s ✅

**VERDICT:** ✅ **WITHIN BUDGET** (with caching)

---

### 6.2 Concurrency Handling

**Existing:** `max_concurrent_claims = 3` (retrieve.py line 21)

**Plan:** Query 3-5 APIs per claim in parallel

**Max API calls per check:**
- 3 claims concurrent × 5 APIs each = 15 parallel API calls
- Each API times out after 5s
- Total: Still ~5s (parallel execution)

**VERDICT:** ✅ **NO BOTTLENECK**

---

## 7. ✅ ROLLBACK SAFETY

### 7.1 Feature Flag Control

```python
# .env
ENABLE_API_RETRIEVAL=false  # ✅ Default OFF
```

**Rollback:** Set to `false` → instant disable, zero code deployment needed

**VERDICT:** ✅ **SAFE ROLLBACK**

---

### 7.2 Database Rollback

**If using Option A (reuse fields):** No migration needed, zero rollback risk

**If using Option B (new fields):**
```python
def downgrade():
    op.drop_column('evidence', 'external_source_provider')
    op.drop_column('evidence', 'external_source_type')
```

**VERDICT:** ✅ **CLEAN ROLLBACK**

---

## 8. 📊 FINAL AUDIT SCORE

| Category | Score | Notes |
|----------|-------|-------|
| **Zero Duplication** | ✅ 100% | No parallel systems, extends existing |
| **Feature Preservation** | ✅ 95% | All features work (1 context fix needed) |
| **Database Safety** | ✅ 100% | Minimal changes, reuses fields |
| **Performance** | ✅ 95% | <10s with caching |
| **Integration Quality** | ✅ 90% | Clean consolidation (5 fixes needed) |
| **Rollback Safety** | ✅ 100% | Feature flag + simple migration |
| **Code Quality** | ✅ 85% | Good patterns, needs field consistency |

**Overall Grade:** ✅ **A- (90%)**

---

## 9. ✅ REQUIRED CHANGES BEFORE IMPLEMENTATION

### **Must Fix (High Priority):**
1. ✅ **3.1** - Evidence field consistency (use "text" not "snippet")
2. ✅ **3.3** - Legal metadata access path correction

### **Should Fix (Medium Priority):**
3. ✅ **3.2** - Pass context to API queries (improves relevance)
4. ✅ **3.4** - Handle factcheck_evidence parameter correctly

### **Nice to Fix (Low Priority):**
5. ✅ **3.5** - Evidence index tracking (for consistent IDs)

---

## 10. ✅ FINAL RECOMMENDATION

**APPROVE WITH CORRECTIONS**

The plan is **architecturally sound** and **non-duplicative**. It successfully:

✅ Extends existing systems (classifier, cache, credibility)
✅ Reuses existing APIs (legal_search, factcheck_api)
✅ Preserves all pipeline features (domain capping, deduplication, etc.)
✅ Maintains performance (<10s with caching)
✅ Provides safe rollback (feature flag)

**Before starting implementation:**
1. Apply the 5 corrections in Section 3
2. Update plan document with corrections
3. Review corrected plan one more time

**Then proceed with Week 1: Foundation**

---

## 🎯 CORRECTED IMPLEMENTATION CHECKLIST

### Week 1:
- [ ] Fix cache event loop issue
- [ ] Extend ClaimClassifier with domain detection
- [ ] Update SourceCredibilityService (register 15 APIs)
- [ ] Create GovernmentAPIClient with **corrected evidence format** ✅
- [ ] Implement 5 adapters (ONS, PubMed, Companies House, FRED, WHO)

### Week 2:
- [ ] Add context parameters to API queries ✅
- [ ] Fix legal metadata access path ✅
- [ ] Implement 10 more adapters
- [ ] Refactor retrieve.py (consolidate APIs)
- [ ] Handle factcheck_evidence parameter ✅

### Week 3-4:
- [ ] Unit tests for all adapters
- [ ] Integration tests (end-to-end)
- [ ] Performance testing (<10s verified)

### Week 5-6:
- [ ] Gradual rollout (0% → 10% → 50% → 100%)
- [ ] Monitor metrics (API coverage, latency, errors)

---

**Audit Complete.** Plan is **APPROVED WITH CORRECTIONS**.
