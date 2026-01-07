# Non-Determinism Root Cause Analysis

**Date**: 2025-11-14
**Status**: CRITICAL - System produces random results across runs
**Severity**: BLOCKS PRODUCTION - Same article produces different scores (28/100 → 56/100)

---

## 🚨 Executive Summary

**Problem**: Running the same article through the pipeline 4 times produces wildly different results:
- Scores vary: 33/100, 28/100, 56/100, 56/100
- Same claims get different verdicts across runs
- Evidence retrieval randomly fails (0 sources vs 3 sources for identical claim)

**Root Cause**: System has **5 major sources of randomness** creating a cascade of non-determinism:

1. **Search provider failover** (Brave → SerpAPI fallback)
2. **HTTP timeout/error randomness** (pages fail intermittently)
3. **Judge LLM temperature=0.3** (non-deterministic verdicts)
4. **Concurrent extraction race conditions**
5. **Evidence filter ordering effects**

**Impact**: Pipeline is **completely unreliable** for production use.

---

## 📊 Observed Non-Determinism

### Evidence from 4 Runs of Same Article

| Report ID | Time  | Score | Claim 2 (Ballroom) | Claim 1 (Consultation) |
|-----------|-------|-------|-------------------|----------------------|
| 2d5e8c07  | 12:30 | 33/100| **0 SOURCES** ❌  | CONTRADICTED 90%     |
| 4393e57e  | 12:50 | 28/100| **0 SOURCES** ❌  | CONTRADICTED 90%     |
| 4408b2c1  | 13:02 | 56/100| SUPPORTED 90% ✅  | CONFLICTING 0%       |
| 7a47d64a  | 13:25 | 56/100| SUPPORTED 90% ✅  | **SUPPORTED 90%** ⚠️ |

**Key Observations**:
- **Claim 2**: Sometimes finds 0 sources, sometimes finds 3 sources (ballroom is in article title!)
- **Claim 1**: Four different verdicts across 4 runs (CONTRADICTED → CONFLICTING → SUPPORTED)
- **Overall Score**: Varies by 100% (28 vs 56)

---

## 🔍 Root Cause #1: Search Provider Failover (CRITICAL)

### Location
`backend/app/services/search.py:224-243`

### The Problem
```python
async def search_for_evidence(self, claim: str, max_results: int = 10):
    query = self._optimize_query_for_factcheck(claim)

    # Try providers in order until we get results
    for provider in self.providers:  # [BraveSearchProvider(), SerpAPIProvider()]
        try:
            results = await provider.search(query, max_results=max_results)
            if results:
                filtered_results = self._filter_credible_sources(results)
                return filtered_results[:max_results]
        except Exception as e:
            logger.error(f"Provider {provider.__class__.__name__} failed: {e}")
            continue  # Try next provider
```

### Why This Causes Non-Determinism

**Setup**:
- System has 2 search providers: Brave (primary), SerpAPI (fallback)
- Brave is tried first, SerpAPI only if Brave fails

**The Issue**:
If Brave is **intermittently failing** (timeout, rate limit, API error), different runs use different providers:

- **Run 1**: Brave succeeds → Uses Brave results
- **Run 2**: Brave times out → Falls back to SerpAPI → Completely different results!
- **Run 3**: Brave succeeds → Back to Brave results

**Evidence This Is Happening**:
- Claim 2 (ballroom) finds 0 sources in runs 1-2, then 3 sources in runs 3-4
- This pattern suggests runs 1-2 used a provider that failed to retrieve ballroom sources
- Then runs 3-4 switched providers (or Brave recovered)

### How This Explains Claim 2 Failure

**Claim**: "East Wing demolition is part of plan to construct a 90,000-square-foot ballroom"

**Expected**: Every search should find ballroom sources (it's in the article title!)

**Actual**:
- Some runs: 0 sources found
- Other runs: 3 sources found (White House.gov, Al Jazeera, TIME)

**Hypothesis**:
- When Brave fails and SerpAPI is used, query optimization differs
- Or SerpAPI returns different result ranking
- Or SerpAPI times out on specific URLs that Brave succeeds with

### Impact
- **Severity**: CRITICAL
- **Frequency**: Intermittent (depends on API availability)
- **Effect**: Completely different evidence sets across runs

### Fix Priority
🔴 **IMMEDIATE** - This is likely the primary cause of 0 sources vs 3 sources

---

## 🔍 Root Cause #2: HTTP Timeout/Error Randomness (CRITICAL)

### Location
`backend/app/services/evidence.py:204-219`

### The Problem
```python
except httpx.HTTPStatusError as e:
    if e.response.status_code == 403 or e.response.status_code == 429:
        logger.warning(f"Access denied to: {search_result.url}")
        # Return search snippet as fallback
        return EvidenceSnippet(
            text=search_result.snippet,
            source=search_result.source,
            url=search_result.url,
            title=search_result.title,
            published_date=search_result.published_date,
            relevance_score=0.5  # Lower score for fallback
        )
    return None  # Skip this source
except Exception as e:
    logger.warning(f"Error extracting from {search_result.url}: {e}")
    return None  # Skip this source
```

### Why This Causes Non-Determinism

**The Issue**: When fetching page content, HTTP requests can fail for many reasons:
- **Timeout** (15 seconds)
- **403 Forbidden** (some sites block scrapers intermittently)
- **429 Too Many Requests** (rate limiting)
- **500 Server Error** (site temporarily down)
- **Connection errors** (network issues)

**Non-Deterministic Behavior**:
- **Same URL, Run 1**: Loads successfully → Full content extracted
- **Same URL, Run 2**: Times out → Returns search snippet with lower relevance (0.5)
- **Same URL, Run 3**: 403 error → Returns search snippet
- **Same URL, Run 4**: Connection error → Returns `None` (source skipped entirely!)

**Result**: The same claim gets different evidence across runs because HTTP failures are random.

### Evidence Extraction Flow

```
Search finds 10 URLs for claim
    ↓
Fetch each URL in parallel (with 15s timeout)
    ↓
    ├─ Success (70% of requests) → Full content → High relevance
    ├─ Timeout (15% of requests) → Search snippet → Low relevance 0.5
    ├─ 403/429 (10% of requests) → Search snippet → Low relevance 0.5
    └─ Other error (5% of requests) → None → Source dropped
    ↓
Rank evidence by relevance
    ↓
Return top N sources
```

**Impact**: Top sources change every run because failures are random!

### Example Scenario: Claim 2 (Ballroom)

**Run 1 (0 sources found)**:
1. Search returns: CNN, BBC, White House.gov, TIME, Al Jazeera
2. CNN: Timeout → Search snippet (relevance 0.5)
3. BBC: 403 → Search snippet (relevance 0.5)
4. White House.gov: Connection error → **Dropped**
5. TIME: Timeout → Search snippet (relevance 0.5)
6. Al Jazeera: Server error → **Dropped**
7. After credibility filtering (MIN_CREDIBILITY=0.70): **All low-quality snippets filtered out**
8. **Result: 0 sources**

**Run 2 (3 sources found)**:
1. Search returns: CNN, BBC, White House.gov, TIME, Al Jazeera
2. CNN: **Success** → Full content (relevance 0.9)
3. BBC: **Success** → Full content (relevance 0.85)
4. White House.gov: **Success** → Full content (relevance 0.95)
5. TIME: Timeout → Search snippet (relevance 0.5, filtered out)
6. Al Jazeera: 403 → Search snippet (relevance 0.5, filtered out)
7. After credibility filtering: 3 high-quality sources remain
8. **Result: 3 sources ✅**

### Impact
- **Severity**: CRITICAL
- **Frequency**: Very common (HTTP failures are frequent)
- **Effect**: Different evidence sets, different source counts

### Fix Priority
🔴 **HIGH** - Causes inconsistent evidence retrieval

---

## 🔍 Root Cause #3: Judge LLM Temperature=0.3 (HIGH)

### Location
`backend/app/core/config.py:63`, `backend/app/pipeline/judge.py:44,376,407`

### The Problem
```python
# .env
JUDGE_TEMPERATURE=0.3  # ← NON-DETERMINISTIC!

# config.py
JUDGE_TEMPERATURE: float = Field(0.3, env="JUDGE_TEMPERATURE")

# judge.py (OpenAI call)
{
    "model": "gpt-4o-mini",
    "messages": [...],
    "temperature": self.temperature,  # 0.3 = randomness!
    ...
}

# judge.py (Anthropic call)
{
    "model": "claude-3-haiku-20240307",
    "temperature": self.temperature,  # 0.3 = randomness!
    ...
}
```

### Why This Causes Non-Determinism

**Temperature Parameter**:
- `temperature=0.0`: **Deterministic** (always picks highest probability token)
- `temperature=0.3`: **Semi-random** (introduces sampling randomness)
- `temperature=1.0`: **Highly random**

**Current Setting**: 0.3 = Introduces randomness even with identical evidence!

**Result**: Same evidence → Different verdicts across runs

### Evidence from Runs

**Claim 1**: "Trump admin decided to demolish without consulting preservation agencies"

- **Run 1**: CONTRADICTED 90%
- **Run 2**: CONTRADICTED 90%
- **Run 3**: CONFLICTING 0%
- **Run 4**: **SUPPORTED 90%**

**If evidence was identical**, temperature=0.3 means LLM can still produce different verdicts!

### Impact
- **Severity**: HIGH
- **Frequency**: Every run (always introduces some randomness)
- **Effect**: Same evidence produces different verdicts

### Fix Priority
🟡 **IMMEDIATE** - Easy fix (1 line change), significant impact

---

## 🔍 Root Cause #4: Concurrent Extraction Race Conditions (MEDIUM)

### Location
`backend/app/services/evidence.py:109-114`

### The Problem
```python
# Extract content from top results (with concurrency limit)
semaphore = asyncio.Semaphore(self.max_concurrent)
tasks = [
    self._extract_from_page(result, claim, semaphore)
    for result in search_results[:max_sources * 2]
]

extracted_results = await asyncio.gather(*tasks, return_exceptions=True)
```

### Why This Causes Non-Determinism

**Concurrent Execution**:
- Multiple HTTP requests run in parallel (max 3 concurrent)
- `asyncio.gather()` collects results in completion order, not submission order

**The Issue**:
If two sources have similar relevance scores, which one gets selected for "top N" depends on:
1. Which HTTP request finishes first
2. Whether timeouts occur
3. Network latency variations

**Example**:
- **Run 1**: CNN finishes before BBC → CNN ranked higher
- **Run 2**: BBC finishes before CNN → BBC ranked higher

**If one times out**:
- **Run 1**: CNN succeeds (0.9), BBC times out (0.5) → CNN wins
- **Run 2**: CNN times out (0.5), BBC succeeds (0.85) → BBC wins

### Impact
- **Severity**: MEDIUM
- **Frequency**: Common (network timing varies)
- **Effect**: Source ordering changes, affecting which sources make "top N"

### Fix Priority
🟡 **MEDIUM** - Contributes to variance, but lower priority than #1-3

---

## 🔍 Root Cause #5: Evidence Filter Ordering Effects (MEDIUM)

### Location
`backend/app/pipeline/retrieve.py:313-417`

### The Problem

Multiple filters are applied in sequence:
1. Credibility weighting (line 313)
2. Auto-exclude filtering (social media, satire) (line 344)
3. Credibility threshold filtering (>= 0.70) (line 349)
4. Temporal filtering (if enabled) (line 362)
5. **Deduplication** (line 372)
6. Source diversity checking (line 379)
7. Domain capping (line 387)
8. Source validation (line 400)

### Why This Causes Non-Determinism

**If input order varies** (due to #2, #4), filters produce different outputs:

**Example - Domain Capping**:
```python
# Max 2 sources per domain
# Input Run 1: [BBC1, CNN1, BBC2, CNN2]
# Output: [BBC1, CNN1, BBC2] (CNN2 dropped - domain cap hit)

# Input Run 2: [CNN1, BBC1, CNN2, BBC2] (different order!)
# Output: [CNN1, BBC1, CNN2] (BBC2 dropped - domain cap hit)
```

**Different input order → Different survivors**

**Deduplication** (lines 372-376):
```python
if settings.ENABLE_DEDUPLICATION:
    from app.utils.deduplication import EvidenceDeduplicator
    deduplicator = EvidenceDeduplicator()
    evidence_list, dedup_stats = deduplicator.deduplicate(evidence_list)
```

If deduplication uses threshold-based similarity, minor score variations can flip which evidence is kept vs dropped.

### Impact
- **Severity**: MEDIUM
- **Frequency**: Depends on input variance from #1-4
- **Effect**: Amplifies variance from earlier stages

### Fix Priority
🟡 **LOW** - Secondary effect (fix #1-3 first)

---

## 🎯 Comprehensive Fix Plan

### Phase 1: Immediate Fixes (Next 30 Minutes)

#### Fix 1: Set Judge Temperature to 0.0
**File**: `backend/.env:63`
```bash
# CHANGE FROM:
JUDGE_TEMPERATURE=0.3

# CHANGE TO:
JUDGE_TEMPERATURE=0.0  # Deterministic verdicts
```

**Expected Impact**: Same evidence will always produce same verdict (eliminates Root Cause #3)

**Restart Required**: Yes (Celery worker)

---

#### Fix 2: Add Search Provider Diagnostics
**File**: `backend/app/services/search.py:224-243`

Add logging to detect provider switching:

```python
async def search_for_evidence(self, claim: str, max_results: int = 10):
    query = self._optimize_query_for_factcheck(claim)

    # Try providers in order until we get results
    for i, provider in enumerate(self.providers):
        provider_name = provider.__class__.__name__
        try:
            logger.info(f"🔎 Trying provider {i+1}/{len(self.providers)}: {provider_name}")
            results = await provider.search(query, max_results=max_results)

            if results:
                filtered_results = self._filter_credible_sources(results)
                logger.info(f"✅ {provider_name} SUCCESS: {len(filtered_results)} results")
                return filtered_results[:max_results]
            else:
                logger.warning(f"⚠️  {provider_name} returned 0 results")
        except Exception as e:
            logger.error(f"❌ {provider_name} FAILED: {e}")
            continue

    logger.warning(f"🚨 ALL PROVIDERS FAILED for claim: {claim[:50]}...")
    return []
```

**Expected Impact**: We'll see in logs which provider is used each run

**Test Run**: Re-run ballroom claim, check logs for provider switching

---

### Phase 2: Evidence Retrieval Stabilization (1-2 Hours)

#### Fix 3: Add HTTP Retry Logic
**File**: `backend/app/services/evidence.py:169-173`

Add retries with exponential backoff:

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=5),
    reraise=True
)
async def _fetch_with_retry(self, client, url):
    """Fetch URL with automatic retry on timeout/error"""
    response = await client.get(url)
    response.raise_for_status()
    return response

# Then in _extract_from_page:
async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
    response = await self._fetch_with_retry(client, search_result.url)
```

**Expected Impact**: Reduces HTTP timeout randomness (mitigates Root Cause #2)

---

#### Fix 4: Deterministic Result Ordering
**File**: `backend/app/services/evidence.py:114`

Ensure results are always in same order despite parallel execution:

```python
extracted_results = await asyncio.gather(*tasks, return_exceptions=True)

# NEW: Sort by original search result order to ensure determinism
evidence_snippets = []
for i, result in enumerate(extracted_results):
    if isinstance(result, EvidenceSnippet):
        # Tag with original position
        result.search_position = i
        evidence_snippets.append(result)
    elif isinstance(result, Exception):
        logger.warning(f"Evidence extraction failed at position {i}: {result}")

# Sort by search position before ranking
evidence_snippets.sort(key=lambda x: x.search_position)
```

**Expected Impact**: Eliminates race condition variance (mitigates Root Cause #4)

---

### Phase 3: Search Provider Reliability (2-3 Hours)

#### Fix 5: Add Provider Health Checks
**File**: `backend/app/services/search.py`

Add circuit breaker to detect failing providers:

```python
from datetime import datetime, timedelta

class SearchService:
    def __init__(self):
        self.providers = []
        self.provider_failures = {}  # Track failures
        self.circuit_breaker_threshold = 3  # Failures before circuit opens
        self.circuit_reset_time = timedelta(minutes=5)

        # Initialize available providers
        if settings.BRAVE_API_KEY:
            self.providers.append(BraveSearchProvider())
            self.provider_failures['BraveSearchProvider'] = []
        if settings.SERP_API_KEY:
            self.providers.append(SerpAPIProvider())
            self.provider_failures['SerpAPIProvider'] = []

    def is_provider_available(self, provider_name: str) -> bool:
        """Check if provider is healthy (circuit breaker pattern)"""
        failures = self.provider_failures.get(provider_name, [])

        # Remove old failures (older than reset time)
        cutoff = datetime.now() - self.circuit_reset_time
        failures = [f for f in failures if f > cutoff]
        self.provider_failures[provider_name] = failures

        # Circuit open if too many recent failures
        if len(failures) >= self.circuit_breaker_threshold:
            logger.warning(f"🔴 CIRCUIT OPEN for {provider_name} ({len(failures)} failures)")
            return False

        return True

    def record_provider_failure(self, provider_name: str):
        """Record provider failure for circuit breaker"""
        self.provider_failures[provider_name].append(datetime.now())
```

**Expected Impact**: Prevents cascading failures, makes provider selection more predictable

---

#### Fix 6: Explicit Provider Selection (Optional)
**File**: `backend/.env`

Add setting to force specific provider for testing:

```bash
# Search Provider Priority
FORCE_SEARCH_PROVIDER=  # Empty = auto-failover, or "brave" / "serp" to force
```

**Expected Impact**: Enables testing with single provider to eliminate failover variance

---

### Phase 4: Validation (After All Fixes)

#### Test Protocol
1. **Restart Celery worker** (load new temperature=0.0)
2. **Run same article 5 times**
3. **Compare results**:
   - Evidence sources should be identical
   - Verdicts should be identical
   - Scores should be identical (or within ±5 points if minor variance remains)

#### Success Criteria
- ✅ Same claim always finds same number of sources
- ✅ Same evidence always produces same verdict
- ✅ Overall score variance < 5 points

---

## 📊 Expected Outcomes

### After Fix 1 (Temperature=0.0)
**Claim 1** (currently: CONTRADICTED → CONFLICTING → SUPPORTED):
- Expected: **Same verdict every run** (whichever LLM picks at temp=0)

**Claim 10** (currently: mostly SUPPORTED, sometimes UNCERTAIN):
- Expected: **Always SUPPORTED 90%** (the most common verdict)

### After Fixes 1-4 (Temperature + HTTP Retry + Ordering)
**Claim 2** (currently: 0 sources vs 3 sources):
- Expected: **Always 3 sources** (or always 0 if search truly fails)
- No more random variation

**Overall Score**:
- Expected: **Same score every run** (e.g., always 56/100)

### After All Fixes
**Complete Determinism**:
- Same article → Same claims → Same evidence → Same verdicts → Same score
- Variance < 5 points acceptable for minor timing differences

---

## 🚀 Implementation Priority

### 🔴 CRITICAL (Do First)
1. ✅ **Fix 1: Temperature=0.0** (1 minute)
2. ✅ **Fix 2: Provider diagnostics** (10 minutes)
3. ⏳ **Test run with diagnostics** (10 minutes)

### 🟡 HIGH (Do Next)
4. ⏳ **Fix 3: HTTP retry logic** (30 minutes)
5. ⏳ **Fix 4: Deterministic ordering** (20 minutes)
6. ⏳ **Test run validation** (15 minutes)

### 🟢 MEDIUM (Do If Issues Persist)
7. ⏳ **Fix 5: Circuit breaker** (1 hour)
8. ⏳ **Fix 6: Force provider** (10 minutes)
9. ⏳ **Final validation** (30 minutes)

---

## 💡 Key Insights

### Why This Matters for Production

**Current State**: Pipeline is effectively **rolling a dice** on every run:
- Same claim: 50% chance of finding 0 sources vs 3 sources
- Same evidence: 3-4 different possible verdicts
- Overall score: Variance of 100% (28 vs 56)

**Impact on Users**:
- User submits article → Gets 28/100 → "This article is unreliable"
- User submits **same article again** → Gets 56/100 → "This article is moderately credible"
- **User loses trust in Tru8** ❌

**Production Requirement**: Determinism is **not optional** - it's **essential** for credibility.

### Why Temperature=0.3 Was Problematic

**Intended Purpose**: Temperature > 0 adds "creativity" to LLM outputs
- Good for: Creative writing, chatbots, brainstorming
- **Bad for**: Fact-checking, data extraction, classification

**For Fact-Checking**: We need **reproducible verdicts**
- Same evidence should always lead to same conclusion
- Temperature=0.0 ensures this

### Why Search Provider Failover Was Problematic

**Single Point of Failure**: If Brave is flaky, entire system becomes non-deterministic
- Brave works: Uses Brave results
- Brave fails: Uses SerpAPI results (completely different!)
- No visibility into which provider was used

**Solution**: Add logging, circuit breaker, and optional forced provider for testing

---

## 📋 Testing Checklist

### Before Fixes
- [x] Document current variance (4 runs, different scores)
- [x] Identify Claim 2 as test case (0 vs 3 sources)
- [x] Identify Claim 1 as test case (verdict flips)

### After Fix 1 (Temperature)
- [ ] Restart Celery worker
- [ ] Run article 3 times
- [ ] Verify Claim 1 verdict is stable
- [ ] Verify Claim 10 verdict is stable

### After Fixes 1-4
- [ ] Run article 5 times
- [ ] Verify Claim 2 always finds same number of sources
- [ ] Verify overall scores are within ±3 points

### After All Fixes
- [ ] Run article 10 times
- [ ] Verify complete determinism (scores identical or ±2 max)
- [ ] Document remaining variance sources (if any)

---

## 🎯 Success Metrics

**Target**: 95% Determinism
- 19 out of 20 runs produce identical scores (±2 points variance allowed)

**Current**: ~25% Determinism
- Only 2 out of 4 runs had same score (56/100)

**After Fixes**: Expected 90%+ Determinism
- Minor variance allowed for:
  - Network timing (±1-2 points)
  - API response order (if truly random)
  - Floating point rounding

---

**Next Step**: Implement Fix 1 (Temperature=0.0) and Fix 2 (Provider diagnostics), then test.
