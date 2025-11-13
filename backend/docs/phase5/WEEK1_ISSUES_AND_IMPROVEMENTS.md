# Week 1: Issues and Required Improvements
**Phase 5: Government API Integration - Foundation & Classification**

---

## 🚨 Critical Issues

### 1. Database Migration Not Applied
**Status**: Migration file created but not executed
**File**: `backend/alembic/versions/2025012_add_government_api_fields.py`
**Issue**: PostgreSQL database connection refused during migration attempt
**Impact**: Database schema doesn't have new API fields yet

**Required Action**:
```bash
# When database is running:
cd backend
alembic upgrade head
```

**Verification**:
```sql
-- Check Evidence table has new columns
SELECT column_name FROM information_schema.columns
WHERE table_name = 'evidence' AND column_name IN ('metadata', 'external_source_provider');

-- Check Check table has new columns
SELECT column_name FROM information_schema.columns
WHERE table_name = 'check' AND column_name IN ('api_sources_used', 'api_call_count', 'api_coverage_percentage');
```

---

## ⚠️ Major Issues

### 2. Jurisdiction Detection Accuracy (70% vs 82-87% target)
**Status**: Below target by 12-17 percentage points
**File**: `backend/app/utils/claim_classifier.py:318-323`

**Failing Test Cases**:
- "Inflation is at 3.2% according to the ONS" → Detected Global (should be UK)
- "The Federal Reserve raised interest rates" → Detected Global (should be US)
- "GDP growth is 2.1%" → Detected Global (should be UK/US based on context)
- "Met Office forecasts record temperatures" → Detected Global (should be UK)
- "Supreme Court ruled on landmark case" → Detected Global (should be US)

**Root Cause**: `_detect_jurisdiction()` method prioritizes explicit location indicators ("UK", "US") but misses entity-based jurisdiction signals (ONS → UK, Federal Reserve → US, Met Office → UK, Supreme Court → US).

**Required Fix**:
```python
def _detect_jurisdiction(self, claim_text: str, doc) -> str:
    """Enhanced jurisdiction detection"""

    # 1. Check custom entity patterns FIRST (ONS, Federal Reserve, etc.)
    uk_entities = ["ons", "nhs", "companies house", "met office", "uk parliament"]
    us_entities = ["federal reserve", "fed", "cdc", "congress", "supreme court"]

    entities_lower = [ent.text.lower() for ent in doc.ents]

    # Priority 1: Organization entities
    if any(org in entities_lower for org in uk_entities):
        return "UK"
    if any(org in entities_lower for org in us_entities):
        return "US"

    # Priority 2: Explicit location indicators (existing logic)
    # Priority 3: GPE entities
    # Priority 4: Default to Global
```

**Expected Impact**: Accuracy should increase from 70% to 82-87%

---

### 3. Empty Claim Handling
**Status**: Edge case causes unexpected behavior
**File**: `backend/app/utils/claim_classifier.py:235-238`

**Issue**: Empty claims return `domain_confidence: 0.0` but still attempt spaCy processing

**Required Fix**:
```python
def detect_domain(self, claim_text: str) -> Dict[str, Any]:
    """Detect claim domain with entity recognition"""

    # Early return for empty claims
    if not claim_text or not claim_text.strip():
        return {
            "domain": "General",
            "domain_confidence": 0.0,
            "jurisdiction": "Global",
            "key_entities": []
        }

    # Continue with normal processing...
```

---

### 4. PubMed XML Parsing Not Implemented
**Status**: MVP placeholder using only PMIDs
**File**: `backend/app/services/api_adapters.py:217-249`

**Current Behavior**: Returns placeholder evidence with just PMID URLs:
```python
title=f"PubMed Article {pmid}",
snippet="Medical research article from PubMed database. Click to view abstract..."
```

**Issue**: No title, abstract, authors, or publication date extracted

**Required Fix**: Parse XML response using `xml.etree.ElementTree`:
```python
import xml.etree.ElementTree as ET

def _transform_response(self, raw_response: Any) -> List[Dict[str, Any]]:
    """Parse PubMed XML response"""

    root = ET.fromstring(raw_response["xml"])

    for article in root.findall('.//PubmedArticle'):
        title = article.findtext('.//ArticleTitle', 'Untitled')
        abstract = article.findtext('.//AbstractText', '')
        pmid = article.findtext('.//PMID', '')

        # Extract date
        pub_date = article.find('.//PubDate')
        year = pub_date.findtext('Year') if pub_date else None

        # Build evidence dict
        evidence = self._create_evidence_dict(
            title=title,
            snippet=abstract[:300],
            url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
            source_date=datetime(int(year), 1, 1) if year else None,
            metadata={"pmid": pmid, "api_source": "PubMed"}
        )
```

**Dependencies**: None (xml.etree is stdlib)

---

### 5. Companies House API Key Required
**Status**: Adapter registered only if API key present
**File**: `backend/app/services/api_adapters.py:458-465`

**Issue**: Without API key, Companies House adapter is silently skipped

**Current Behavior**:
```python
companies_house_key = os.getenv("COMPANIES_HOUSE_API_KEY")
if companies_house_key:
    registry.register(CompaniesHouseAdapter())
else:
    logger.warning("Companies House API key not configured, adapter not registered")
```

**Required Action**: Document API key setup in `.env.example`:
```bash
# Government API Keys (Phase 5)
COMPANIES_HOUSE_API_KEY=your_key_here  # Get from: https://developer.company-information.service.gov.uk/
PUBMED_API_KEY=your_key_here           # Optional - increases rate limit from 3/sec to 10/sec
```

---

## 📝 Minor Issues

### 6. Special Characters in Test Output
**Status**: Workaround applied, but not root cause fixed
**File**: Previous session issue with Unicode checkmarks

**Issue**: Windows console encoding doesn't support Unicode characters like ✓, ✗

**Workaround**: Removed special characters from test output

**Better Fix**: Configure pytest to use UTF-8 output:
```ini
# pytest.ini
[pytest]
pythonpath = .
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
asyncio_mode = auto
# Add UTF-8 encoding
env =
    PYTHONIOENCODING=utf-8
```

---

### 7. Domain Classification for Multi-Domain Claims
**Status**: Working as designed, but accuracy is lower
**File**: `backend/app/utils/claim_classifier.py:272-301`

**Expected Behavior**: Multi-domain claims have 13-18% error rate (per plan)

**Examples**:
- "NHS spending on mental health increased" → Health + Finance + Government
- "Government spending on climate research" → Climate + Government + Finance

**Current Logic**: Returns HIGHEST scoring domain (may not always be correct)

**Improvement Opportunity** (Future):
```python
def detect_domain(self, claim_text: str) -> Dict[str, Any]:
    """Detect claim domain with multi-domain support"""

    # ... existing logic ...

    # NEW: Return top 3 domains if scores are close
    sorted_domains = sorted(domain_scores.items(), key=lambda x: x[1], reverse=True)
    top_score = sorted_domains[0][1]

    multi_domains = [
        d for d, score in sorted_domains
        if score >= top_score * 0.8  # Within 20% of top score
    ]

    return {
        "domain": sorted_domains[0][0],  # Primary domain
        "multi_domains": multi_domains if len(multi_domains) > 1 else None,
        # ... rest of response
    }
```

---

### 8. spaCy Model Size
**Status**: Using en_core_web_sm (small model)
**File**: `backend/requirements.txt:22`

**Current Model**: en_core_web_sm (12 MB)
**Accuracy**: Good for MVP, but limited entity coverage

**Improvement Opportunity** (Future):
- Upgrade to `en_core_web_md` (40 MB) for 10-15% better entity recognition
- Or `en_core_web_lg` (560 MB) for production-grade accuracy

**Trade-off**: Larger models = better accuracy but slower loading and higher memory usage

---

### 9. API Request Retry Logic Missing
**Status**: Single request attempt only
**File**: `backend/app/services/government_api_client.py:102-136`

**Current Behavior**:
```python
def _make_request(self, endpoint: str, params: Optional[Dict] = None, method: str = "GET"):
    try:
        response = client.get(url, headers=self.headers, params=params)
        response.raise_for_status()
        return response.json()
    except httpx.TimeoutException:
        logger.warning(f"{self.api_name} request timeout: {url}")
        return None  # Single attempt, no retry
```

**Issue**: Transient network errors or API hiccups cause immediate failure

**Required Fix**: Add exponential backoff retry:
```python
import time

def _make_request(self, endpoint: str, params: Optional[Dict] = None,
                 method: str = "GET", max_retries: int = 3):
    """Make HTTP request with exponential backoff retry"""

    for attempt in range(max_retries):
        try:
            # ... make request ...
            return response.json()

        except (httpx.TimeoutException, httpx.RequestError) as e:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # 1s, 2s, 4s
                logger.warning(f"{self.api_name} attempt {attempt+1} failed, retrying in {wait_time}s")
                time.sleep(wait_time)
            else:
                logger.error(f"{self.api_name} failed after {max_retries} attempts")
                return None
```

---

### 10. Cache TTL Not Configurable Per Domain
**Status**: Hardcoded 24-hour TTL for all API responses
**File**: `backend/app/services/cache.py:266`

**Current Behavior**:
```python
async def cache_api_response(
    self,
    api_name: str,
    query: str,
    response: List[Dict],
    ttl: int = 86400  # Hardcoded 24 hours
):
```

**Issue**: Different APIs have different data freshness requirements:
- Economic data (ONS, FRED): Updates monthly → 7 days TTL optimal
- Company data (Companies House): Updates quarterly → 3 days TTL optimal
- Medical research (PubMed): Updates rarely → 7 days TTL optimal
- Weather (Met Office): Updates hourly → 1 hour TTL optimal

**Improvement**: Make TTL domain-specific in adapter constructors (already done in adapters, but not documented)

---

## ✅ Improvements for Week 2+

### 11. Add API Health Check Endpoint
**Status**: Health check method exists but not exposed
**File**: `backend/app/services/government_api_client.py:269-281`

**Suggestion**: Add FastAPI endpoint to monitor API adapter health:
```python
# backend/api/v1/admin.py
@router.get("/api-health")
async def check_api_health():
    """Check health of all registered API adapters"""
    registry = get_api_registry()

    health_status = {}
    for adapter in registry.get_all_adapters():
        health_status[adapter.api_name] = {
            "healthy": adapter.health_check(),
            "info": adapter.get_api_info()
        }

    return health_status
```

---

### 12. Add Telemetry for API Routing Decisions
**Status**: No logging of routing decisions

**Suggestion**: Log domain detection results for monitoring and improvement:
```python
def detect_domain(self, claim_text: str) -> Dict[str, Any]:
    # ... existing logic ...

    result = {
        "domain": best_domain,
        "domain_confidence": confidence,
        "jurisdiction": jurisdiction,
        "key_entities": key_entities
    }

    # NEW: Log for analytics
    logger.info(
        f"Domain detection: {best_domain} ({confidence:.2f}) | "
        f"Jurisdiction: {jurisdiction} | "
        f"Entities: {len(key_entities)} | "
        f"Claim: {claim_text[:50]}"
    )

    return result
```

**Benefit**: Track routing accuracy in production to identify improvement areas

---

### 13. Add Domain Detection Confidence Threshold
**Status**: No threshold for low-confidence routing

**Suggestion**: Fall back to "General" if confidence < 0.5:
```python
def detect_domain(self, claim_text: str) -> Dict[str, Any]:
    # ... existing logic ...

    # If confidence too low, default to General (no API routing)
    if confidence < 0.5:
        logger.info(f"Low confidence ({confidence:.2f}), defaulting to General domain")
        return {
            "domain": "General",
            "domain_confidence": confidence,
            "jurisdiction": "Global",
            "key_entities": key_entities
        }
```

**Benefit**: Prevents incorrect API calls for ambiguous claims

---

### 14. Add API Response Validation
**Status**: No validation of API response format

**Suggestion**: Validate evidence format before returning:
```python
from pydantic import BaseModel, validator

class EvidenceResponse(BaseModel):
    title: str
    snippet: str
    url: str
    source: str
    credibility_score: float

    @validator('credibility_score')
    def validate_credibility(cls, v):
        if not 0.0 <= v <= 1.0:
            raise ValueError('Credibility must be between 0.0 and 1.0')
        return v

def _create_evidence_dict(self, title: str, snippet: str, url: str, ...):
    evidence = {
        "title": title,
        "snippet": snippet,
        # ...
    }

    # Validate before returning
    EvidenceResponse(**evidence)  # Raises ValidationError if invalid
    return evidence
```

---

### 15. Add Rate Limiting Per Adapter
**Status**: No rate limiting implemented

**Suggestion**: Implement rate limiting using Redis:
```python
class GovernmentAPIClient(ABC):
    def __init__(self, ..., rate_limit_per_hour: int = None):
        self.rate_limit = rate_limit_per_hour

    def _check_rate_limit(self) -> bool:
        """Check if we're within rate limit"""
        if not self.rate_limit:
            return True

        # Use Redis to track request count
        key = f"rate_limit:{self.api_name}:{datetime.now().hour}"
        count = self.cache.redis.incr(key)

        if count == 1:
            self.cache.redis.expire(key, 3600)  # Expire after 1 hour

        if count > self.rate_limit:
            logger.warning(f"{self.api_name} rate limit exceeded: {count}/{self.rate_limit}")
            return False

        return True
```

---

## 📋 Summary

### Critical (Must Fix Before Week 2)
1. ✅ Apply database migration when DB is available
2. ⚠️ Improve jurisdiction detection accuracy (70% → 82-87%)
3. ⚠️ Fix empty claim handling
4. ⚠️ Implement PubMed XML parsing
5. ⚠️ Document Companies House API key setup

### Major (Should Fix in Week 2-3)
6. Add retry logic with exponential backoff
7. Add API health check endpoint
8. Add telemetry for routing decisions
9. Add domain detection confidence threshold
10. Add API response validation

### Minor (Nice to Have for Production)
11. Upgrade to larger spaCy model (en_core_web_md or lg)
12. Implement multi-domain detection (return top 3 domains)
13. Add rate limiting per adapter
14. Configure UTF-8 output for pytest

---

## 🎯 Next Steps Priority Order

**Before continuing to Week 2:**
1. Fix jurisdiction detection logic (2-3 hours)
2. Fix empty claim edge case (30 minutes)
3. Apply database migration (when DB available)
4. Implement PubMed XML parsing (2 hours)
5. Run full test suite again (target: 82-87% accuracy)

**Total Estimated Time**: 5-6 hours of fixes before Week 2 implementation

---

**Last Updated**: 2025-01-12
**Phase**: Week 1 Complete, Pre-Week 2 Improvements Identified
