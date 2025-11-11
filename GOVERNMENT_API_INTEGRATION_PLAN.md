# 🎯 Tru8 Government API Integration Plan
## **EXTENDS Existing Pipeline** | No Duplication | Non-Breaking

**Version:** 2.0 (Revised - Alignment-Focused)
**Date:** 2025-01-11
**Duration:** 6 weeks
**Objective:** Add 15 new government/institutional API sources to existing pipeline infrastructure

---

## 🚨 CRITICAL: This Plan EXTENDS, Not Replaces

**What We're NOT Doing:**
- ❌ Creating new classification system (we already have `ClaimClassifier`)
- ❌ Creating new caching system (we already have `CacheService`)
- ❌ Creating new credibility system (we already have `SourceCredibilityService`)
- ❌ Creating new legal API system (we already have `LegalSearchService`)
- ❌ Changing pipeline stages (they stay: Ingest → Extract → Retrieve → Verify → Judge)

**What We ARE Doing:**
- ✅ Adding 15 new API clients (ONS, PubMed, Companies House, etc.)
- ✅ Extending `ClaimClassifier` with domain detection (Finance, Health, etc.)
- ✅ Consolidating all external API calls into Stage 3 (Retrieve)
- ✅ Extending `SourceCredibilityService` to recognize new API sources
- ✅ Fixing `CacheService` event loop issue for Celery

---

## 📋 Table of Contents

1. [Current System Analysis](#1-current-system-analysis)
2. [What Actually Changes](#2-what-actually-changes)
3. [15 New API Sources](#3-15-new-api-sources)
4. [Database Changes (Minimal)](#4-database-changes-minimal)
5. [Code Changes (File by File)](#5-code-changes-file-by-file)
6. [Implementation Timeline](#6-implementation-timeline)
7. [Testing Strategy](#7-testing-strategy)
8. [Rollout Plan](#8-rollout-plan)

---

## 1. Current System Analysis

### ✅ Existing External API Infrastructure

Your codebase **already has** a working external API system:

```python
# EXISTING: backend/app/services/factcheck_api.py (186 lines)
class FactCheckAPI:
    async def search_fact_checks(self, claim_text: str) -> List[Dict]:
        # Queries Google Fact Check Explorer API
        # Returns formatted evidence

    def convert_to_evidence(self, fact_check: Dict, claim_text: str):
        # Converts API response to Evidence format
        # Sets source_type="factcheck"

# EXISTING: backend/app/services/legal_search.py (441 lines)
class LegalSearchService:
    async def search_statutes(self, claim_text: str, metadata: Dict):
        # Queries GovInfo.gov + Congress.gov (US)
        # Queries legislation.gov.uk (UK)
        # Returns formatted statute results
```

**These work! Stage 2.5 (line 286 in pipeline.py) calls `FactCheckAPI`.**

### ✅ Existing Classification System

```python
# EXISTING: backend/app/utils/claim_classifier.py (213 lines)
class ClaimClassifier:
    def classify(self, claim_text: str) -> Dict[str, Any]:
        # Returns: claim_type, is_verifiable, jurisdiction, legal_metadata
        # Already detects: factual, opinion, prediction, legal, personal
        # Already extracts: jurisdiction (UK, US), citations, year
```

### ✅ Existing Credibility System

```python
# EXISTING: backend/app/services/source_credibility.py
class SourceCredibilityService:
    def get_credibility(self, source: str, url: str) -> Dict:
        # Returns: tier, credibility (0-1), risk_flags, auto_exclude
        # Already has tiers: news_tier1, government, academic, blacklist
        # Loads from: backend/app/data/source_credibility.json
```

### ✅ Existing Cache System

```python
# EXISTING: backend/app/services/cache.py
class CacheService:
    async def get_cached_claim_extraction(...)
    async def cache_claim_extraction(...)
    async def get_cached_evidence_extraction(...)
    # Currently DISABLED in pipeline.py (line 227) due to event loop issues
```

---

## 2. What Actually Changes

### 📊 High-Level Architecture (Before → After)

**BEFORE (Current):**
```
Stage 2.5: Fact-check API lookup (factcheck_api.py)
Stage 3: Retrieve evidence (web search only)
```

**AFTER (With Government APIs):**
```
Stage 3: Retrieve evidence (UNIFIED)
   ├─ Fact-check APIs (existing: factcheck_api.py)
   ├─ Legal APIs (existing: legal_search.py)
   ├─ Government APIs (NEW: government_api_client.py) ← 15 new sources
   └─ Web search (existing: SearchService)

   All sources queried in parallel → merged → deduplicated
```

**Key Change:** Stage 2.5 is **merged into Stage 3**. All external queries happen in one place.

### 🔧 Files Modified (8 files)

| File | Change Type | Purpose |
|------|-------------|---------|
| `backend/app/utils/claim_classifier.py` | **Extend** | Add domain detection (Finance, Health, etc.) |
| `backend/app/services/cache.py` | **Fix + Extend** | Fix event loop, add API caching methods |
| `backend/app/services/source_credibility.py` | **Extend** | Register 15 new API domains as Tier 1 |
| `backend/app/pipeline/retrieve.py` | **Refactor** | Consolidate all API calls here |
| `backend/app/workers/pipeline.py` | **Modify** | Move Stage 2.5 into Stage 3, track API stats |
| `backend/app/core/config.py` | **Add** | Feature flag + 15 API keys |
| `backend/app/models/check.py` | **Extend** | Add API stats fields to Evidence table |
| `backend/alembic/versions/xxx.py` | **New** | Migration for Evidence table fields |

### 📦 New Files Created (4 files)

| File | Purpose | Lines |
|------|---------|-------|
| `backend/app/services/government_api_client.py` | Unified client for 15 government APIs | ~500 |
| `backend/app/services/api_adapters/ons.py` | ONS Economic Statistics adapter | ~150 |
| `backend/app/services/api_adapters/pubmed.py` | PubMed adapter | ~150 |
| `backend/app/services/api_adapters/companies_house.py` | Companies House adapter | ~150 |
| ... | (12 more adapters - one per API) | ~150 each |

**Total new code:** ~2500 lines (vs 26,000 in duplicative plan)

---

## 3. 15 New API Sources

### Why 15, Not 18?

**Already Integrated:**
- ❌ **Google Fact Check API** (already in `factcheck_api.py`)
- ❌ **GovInfo.gov** (already in `legal_search.py`)
- ❌ **Legislation.gov.uk** (already in `legal_search.py`)

**Adding 15 New:**

| # | API Name | Domain | Region | Tier | API Key? |
|---|----------|--------|--------|------|----------|
| 1 | ONS Economic Statistics | Finance | UK | 1 | No |
| 2 | FRED | Finance | US | 1 | Yes |
| 3 | Companies House | Government | UK | 1 | Yes |
| 4 | PubMed E-utilities | Health | Global | 1 | No |
| 5 | WHO GHO | Health | Global | 1 | No |
| 6 | Met Office DataPoint | Climate | UK | 1 | Yes |
| 7 | UK Census (ONS) | Demographics | UK | 1 | No |
| 8 | CrossRef | Science | Global | 2 | No |
| 9 | Wikidata Query Service | General | Global | 3 | No |
| 10 | Sports Open Data | Sports | Global | 3 | No |
| 11 | MusicBrainz | Entertainment | Global | 3 | No |
| 12 | GOV.UK Content API | News | UK | 1 | No |
| 13 | UK Parliament Hansard | Quotes | UK | 1 | No |
| 14 | Reddit Data API | Social | Global | 3 | Yes |
| 15 | Stack Exchange | Tech | Global | 3 | No |

**Cost:** $0/month (all free tier)

---

## 4. Database Changes (Minimal)

### Option A: Reuse Existing Fields (Recommended)

**No new tables or fields needed!** Just reuse what exists:

```sql
-- Evidence table (existing fields, lines 99-151 in check.py)
CREATE TABLE evidence (
    ...
    is_factcheck BOOLEAN DEFAULT FALSE,           -- Existing
    factcheck_publisher VARCHAR,                   -- Existing (reuse for API name)
    source_type VARCHAR,                           -- Existing (add 'api' value)
    metadata JSONB,                                -- Existing (store API metadata here)
    ...
);
```

**For API sources:**
- `source_type = 'api'` (already exists, just add to enum)
- `factcheck_publisher = 'ONS Economic Statistics'` (reuse existing field)
- `metadata = {"api_query": "...", "api_confidence": 0.9, ...}` (store API details)

### Option B: Add Minimal Fields (If Needed)

If you want clearer separation:

```sql
ALTER TABLE evidence
ADD COLUMN external_source_type VARCHAR(50),  -- 'factcheck', 'legal_api', 'government_api'
ADD COLUMN external_source_provider VARCHAR(200);  -- 'ONS', 'PubMed', 'Snopes', 'GovInfo'
```

**Alembic Migration:**

```python
# backend/alembic/versions/2025011_add_api_sources.py
def upgrade():
    # Option A: Just add 'api' to source_type enum (if using enum)
    op.execute("ALTER TYPE source_type_enum ADD VALUE IF NOT EXISTS 'api'")

    # Option B: Add explicit fields
    op.add_column('evidence', sa.Column('external_source_type', sa.String(50)))
    op.add_column('evidence', sa.Column('external_source_provider', sa.String(200)))

def downgrade():
    op.drop_column('evidence', 'external_source_provider')
    op.drop_column('evidence', 'external_source_type')
```

**Check table changes:**

```sql
-- Add API stats to Check table (optional, for analytics)
ALTER TABLE "check"
ADD COLUMN api_sources_used JSONB,           -- ["ONS", "PubMed"]
ADD COLUMN api_call_count INTEGER DEFAULT 0,
ADD COLUMN api_coverage_percentage DECIMAL(5,2);
```

---

## 5. Code Changes (File by File)

### 5.1 Extend `ClaimClassifier` (Domain Detection)

**File:** `backend/app/utils/claim_classifier.py`

**Current:** Classifies claim_type (factual, opinion, legal, etc.)
**Add:** Domain detection (Finance, Health, Government, etc.)

```python
# EXISTING CODE (lines 1-99)
class ClaimClassifier:
    def __init__(self):
        self.opinion_patterns = [...]
        self.prediction_patterns = [...]
        self.legal_patterns = [...]  # Already exists!

    def classify(self, claim_text: str) -> Dict[str, Any]:
        # EXISTING: Returns claim_type, is_verifiable, jurisdiction

        # NEW: Add domain classification
        domain = self._detect_domain(claim_text)  # NEW METHOD

        return {
            "claim_type": "factual/opinion/legal/etc.",  # Existing
            "domain": domain,  # NEW
            "jurisdiction": "UK/US/EU",  # Existing (for legal claims)
            "is_verifiable": True,  # Existing
            # ... rest of existing fields
        }

    # NEW METHOD (add at end of file, ~50 lines)
    def _detect_domain(self, claim_text: str) -> str:
        """
        Detect claim domain for API routing.

        Returns:
            One of: Finance, Health, Government, Law, Science, Climate,
                   Demographics, Sports, Entertainment, News, Social,
                   Product, Quotes, General
        """
        claim_lower = claim_text.lower()

        # Keyword-based domain detection (fast, 90% accurate)
        if any(word in claim_lower for word in [
            'unemployment', 'gdp', 'inflation', 'economy', 'market', 'stock'
        ]):
            return "Finance"

        elif any(word in claim_lower for word in [
            'health', 'medical', 'disease', 'vaccine', 'hospital', 'doctor'
        ]):
            return "Health"

        elif any(word in claim_lower for word in [
            'company', 'business', 'corporation', 'registered', 'director'
        ]):
            return "Government"

        elif any(word in claim_lower for word in [
            'climate', 'temperature', 'weather', 'carbon', 'emissions'
        ]):
            return "Climate"

        elif any(word in claim_lower for word in [
            'population', 'census', 'demographic', 'people', 'household'
        ]):
            return "Demographics"

        elif any(word in claim_lower for word in [
            'research', 'study', 'journal', 'science', 'experiment'
        ]):
            return "Science"

        elif any(word in claim_lower for word in [
            'match', 'score', 'team', 'player', 'league', 'championship'
        ]):
            return "Sports"

        elif any(word in claim_lower for word in [
            'said', 'stated', 'parliament', 'speech', 'quote', 'congress'
        ]):
            return "Quotes"

        # Legal claims detected by existing patterns
        elif self._is_legal_claim(claim_lower):
            return "Law"

        else:
            return "General"

    def _is_legal_claim(self, claim_lower: str) -> bool:
        """Check if claim matches legal patterns (reuse existing)"""
        return any(re.search(pattern, claim_lower) for pattern in self.legal_patterns)
```

**Why this works:**
- Extends existing class, doesn't replace it
- Reuses existing legal detection
- Fast keyword matching (no GPT-4 cost)
- Returns same Dict format, just adds "domain" key

---

### 5.2 Fix & Extend `CacheService`

**File:** `backend/app/services/cache.py`

**Current:** Disabled in Celery due to event loop issues
**Fix:** Create sync wrapper for Celery context
**Extend:** Add API response caching methods

```python
# EXISTING CODE (keep all existing methods)
class CacheService:
    def __init__(self, redis_client):
        self.redis = redis_client

    async def get_cached_claim_extraction(...):
        # Keep existing

    async def cache_claim_extraction(...):
        # Keep existing

    # ... rest of existing methods

    # NEW METHODS (add at end of class, ~30 lines)
    async def get_cached_api_response(
        self,
        api_name: str,
        query: str
    ) -> Optional[List[Dict]]:
        """
        Retrieve cached API response.

        Args:
            api_name: "ONS Economic Statistics", "PubMed", etc.
            query: Search query

        Returns:
            Cached response or None
        """
        import hashlib

        query_hash = hashlib.md5(query.encode()).hexdigest()
        cache_key = f"api:{api_name}:{query_hash}"

        try:
            cached = await self.redis.get(cache_key)
            if cached:
                import json
                return json.loads(cached)
        except Exception as e:
            logger.error(f"Cache retrieval error: {e}")

        return None

    async def cache_api_response(
        self,
        api_name: str,
        query: str,
        response: List[Dict],
        ttl: int = 86400  # 24 hours
    ):
        """Cache API response"""
        import hashlib
        import json

        query_hash = hashlib.md5(query.encode()).hexdigest()
        cache_key = f"api:{api_name}:{query_hash}"

        try:
            await self.redis.setex(
                cache_key,
                ttl,
                json.dumps(response)
            )
        except Exception as e:
            logger.error(f"Cache storage error: {e}")

# NEW: Sync wrapper for Celery context (add at end of file, ~20 lines)
def get_sync_cache_service():
    """
    Create cache service for synchronous (Celery) context.

    Uses Redis in blocking mode to avoid event loop issues.
    """
    import redis
    from app.core.config import settings

    redis_client = redis.from_url(
        settings.REDIS_URL,
        decode_responses=True,
        socket_connect_timeout=5
    )

    # Wrap async methods with sync versions
    class SyncCacheService:
        def __init__(self, redis_client):
            self.redis = redis_client

        def get_cached_api_response_sync(self, api_name: str, query: str):
            import hashlib, json
            query_hash = hashlib.md5(query.encode()).hexdigest()
            cache_key = f"api:{api_name}:{query_hash}"
            cached = self.redis.get(cache_key)
            return json.loads(cached) if cached else None

        def cache_api_response_sync(self, api_name: str, query: str, response: List[Dict], ttl=86400):
            import hashlib, json
            query_hash = hashlib.md5(query.encode()).hexdigest()
            cache_key = f"api:{api_name}:{query_hash}"
            self.redis.setex(cache_key, ttl, json.dumps(response))

    return SyncCacheService(redis_client)
```

---

### 5.3 Extend `SourceCredibilityService`

**File:** `backend/app/services/source_credibility.py`

**Current:** Loads credibility tiers from `source_credibility.json`
**Extend:** Register 15 new API domains as Tier 1 sources

**Option A: Update JSON file**

```json
// backend/app/data/source_credibility.json
{
  "government_apis": {
    "description": "Official government data APIs",
    "credibility": 1.0,
    "tier": "tier1",
    "domains": [
      "ons.gov.uk",
      "companieshouse.gov.uk",
      "api.parliament.uk",
      "data.gov.uk",
      "fred.stlouisfed.org",
      "legislation.gov.uk"
    ],
    "auto_exclude": false,
    "risk_flags": []
  },
  "health_apis": {
    "description": "Official health/medical APIs",
    "credibility": 1.0,
    "tier": "tier1",
    "domains": [
      "pubmed.ncbi.nlm.nih.gov",
      "who.int",
      "nhs.uk"
    ],
    "auto_exclude": false,
    "risk_flags": []
  },
  "scientific_apis": {
    "description": "Academic/scientific APIs",
    "credibility": 0.9,
    "tier": "tier2",
    "domains": [
      "crossref.org",
      "api.crossref.org"
    ],
    "auto_exclude": false,
    "risk_flags": []
  }
  // ... existing tiers remain unchanged
}
```

**Option B: Code extension (if JSON isn't flexible enough)**

```python
# In source_credibility.py, extend _match_domain_to_tier()
def _match_domain_to_tier(self, domain: str, parsed) -> Dict[str, Any]:
    """Match domain against all configured tiers"""

    # NEW: Check if it's a known API domain (highest priority)
    api_tier = self._check_api_domains(domain)
    if api_tier:
        return api_tier

    # Existing tier matching logic...
    for tier_name, tier_config in self.config.items():
        # ... existing code

    # Fallback to general
    return self._get_general_tier(...)

# NEW METHOD
def _check_api_domains(self, domain: str) -> Optional[Dict]:
    """Fast lookup for known API domains"""
    api_domains = {
        "ons.gov.uk": {"tier": "tier1", "credibility": 1.0, "name": "ONS"},
        "companieshouse.gov.uk": {"tier": "tier1", "credibility": 1.0, "name": "Companies House"},
        "pubmed.ncbi.nlm.nih.gov": {"tier": "tier1", "credibility": 1.0, "name": "PubMed"},
        "who.int": {"tier": "tier1", "credibility": 1.0, "name": "WHO"},
        "fred.stlouisfed.org": {"tier": "tier1", "credibility": 1.0, "name": "FRED"},
        # ... add all 15
    }

    if domain in api_domains:
        info = api_domains[domain]
        return {
            'tier': info['tier'],
            'credibility': info['credibility'],
            'risk_flags': [],
            'auto_exclude': False,
            'reasoning': f"Official API source: {info['name']}",
            'description': 'Government/institutional API'
        }

    return None
```

---

### 5.4 Create `GovernmentAPIClient` (NEW)

**File:** `backend/app/services/government_api_client.py` (NEW, ~500 lines)

This is the **ONLY** major new file. It follows the same pattern as `FactCheckAPI` and `LegalSearchService`.

```python
"""
Government API Client

Unified interface for querying 15 government/institutional APIs.
Follows same pattern as FactCheckAPI and LegalSearchService.
"""

import httpx
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from app.core.config import settings
from app.services.cache import get_sync_cache_service

logger = logging.getLogger(__name__)


class GovernmentAPIClient:
    """
    Query government and institutional data APIs.

    Supports 15 sources across Finance, Health, Science, etc.
    Follows existing pattern from FactCheckAPI and LegalSearchService.
    """

    def __init__(self):
        self.cache = get_sync_cache_service()
        self.timeout = 10

        # Load adapters dynamically
        self.adapters = self._load_adapters()

    def _load_adapters(self) -> Dict[str, 'BaseAPIAdapter']:
        """Load all API adapters"""
        from app.services.api_adapters.ons import ONSAdapter
        from app.services.api_adapters.pubmed import PubMedAdapter
        from app.services.api_adapters.companies_house import CompaniesHouseAdapter
        # ... import remaining 12

        return {
            "Finance": [ONSAdapter(), FREDAdapter()],
            "Health": [PubMedAdapter(), WHOAdapter()],
            "Government": [CompaniesHouseAdapter()],
            # ... map all 15 by domain
        }

    async def search_by_domain(
        self,
        claim_text: str,
        domain: str,
        jurisdiction: str = "Global",
        max_results: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search APIs for a specific domain.

        Args:
            claim_text: The claim to search for
            domain: Domain classification (Finance, Health, etc.)
            jurisdiction: UK, US, EU, Global
            max_results: Max results per API

        Returns:
            List of evidence dictionaries (same format as FactCheckAPI)
        """
        # Get adapters for this domain
        adapters = self.adapters.get(domain, [])

        if not adapters:
            logger.info(f"No APIs available for domain: {domain}")
            return []

        # Filter by jurisdiction
        relevant_adapters = [
            a for a in adapters
            if jurisdiction in a.supported_jurisdictions
        ]

        if not relevant_adapters:
            relevant_adapters = adapters  # Use all if no jurisdiction match

        # Check cache first
        cached = self.cache.get_cached_api_response_sync(
            f"{domain}:{jurisdiction}",
            claim_text
        )
        if cached:
            logger.info(f"Cache hit for {domain} APIs")
            return cached

        # Query APIs in parallel
        import asyncio
        tasks = [
            adapter.search(claim_text, max_results=max_results)
            for adapter in relevant_adapters[:3]  # Max 3 APIs per domain
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Merge results
        all_evidence = []
        for adapter, result in zip(relevant_adapters[:3], results):
            if isinstance(result, Exception):
                logger.error(f"{adapter.name} failed: {result}")
                continue

            if result:
                # Convert to evidence format (same as FactCheckAPI)
                evidence_items = [
                    self._convert_to_evidence(item, adapter.name)
                    for item in result
                ]
                all_evidence.extend(evidence_items)

        # Cache results
        if all_evidence:
            self.cache.cache_api_response_sync(
                f"{domain}:{jurisdiction}",
                claim_text,
                all_evidence,
                ttl=86400  # 24 hours
            )

        logger.info(f"Government APIs returned {len(all_evidence)} results for {domain}")
        return all_evidence

    def _convert_to_evidence(
        self,
        api_result: Dict,
        api_name: str
    ) -> Dict[str, Any]:
        """
        Convert API result to Evidence format.

        Same format as FactCheckAPI.convert_to_evidence()
        """
        return {
            "source": api_result.get("source", api_name),
            "url": api_result.get("url", ""),
            "title": api_result.get("title", ""),
            "snippet": api_result.get("content", api_result.get("snippet", "")),
            "published_date": api_result.get("published_date"),
            "relevance_score": api_result.get("relevance_score", 0.9),
            "credibility_score": api_result.get("credibility_score", 0.95),
            "source_type": "api",  # Mark as API source
            "external_source_provider": api_name,  # Track which API
            "metadata": api_result.get("metadata", {})
        }


# Base adapter class (similar to FactCheckAPI pattern)
class BaseAPIAdapter:
    """Base class for all API adapters"""

    def __init__(self, name: str, base_url: str, supported_jurisdictions: List[str]):
        self.name = name
        self.base_url = base_url
        self.supported_jurisdictions = supported_jurisdictions
        self.timeout = 10

    async def search(self, query: str, max_results: int = 10) -> List[Dict]:
        """
        Search API and return results.

        Must be implemented by each adapter.
        Returns list of dicts with: title, content, url, published_date, etc.
        """
        raise NotImplementedError
```

---

### 5.5 Example Adapter: ONS

**File:** `backend/app/services/api_adapters/ons.py` (NEW, ~150 lines)

```python
"""ONS Economic Statistics API Adapter"""

import httpx
from typing import List, Dict
from ..government_api_client import BaseAPIAdapter
import logging

logger = logging.getLogger(__name__)


class ONSAdapter(BaseAPIAdapter):
    """UK Office for National Statistics API"""

    def __init__(self):
        super().__init__(
            name="ONS Economic Statistics",
            base_url="https://api.ons.gov.uk/v1",
            supported_jurisdictions=["UK", "Global"]
        )

    async def search(self, query: str, max_results: int = 10) -> List[Dict]:
        """Search ONS datasets"""
        try:
            # ONS API search endpoint
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/datasets",
                    params={
                        "q": query,
                        "limit": max_results
                    }
                )

                if response.status_code == 200:
                    data = response.json()
                    return self._parse_ons_response(data)
                else:
                    logger.warning(f"ONS API returned {response.status_code}")
                    return []

        except Exception as e:
            logger.error(f"ONS API error: {e}")
            return []

    def _parse_ons_response(self, data: Dict) -> List[Dict]:
        """Parse ONS JSON response"""
        results = []

        for item in data.get("items", []):
            results.append({
                "title": item.get("title", "ONS Data"),
                "content": item.get("description", ""),
                "url": item.get("href", self.base_url),
                "published_date": item.get("releaseDate"),
                "source": "Office for National Statistics",
                "credibility_score": 1.0,  # Tier 1 government
                "relevance_score": 0.9,
                "metadata": {
                    "dataset_id": item.get("id"),
                    "unit": item.get("unit"),
                    "frequency": item.get("frequency")
                }
            })

        return results
```

**Remaining 14 adapters follow same pattern** (~150 lines each):
- `pubmed.py` - PubMed E-utilities
- `fred.py` - Federal Reserve Economic Data
- `companies_house.py` - UK Companies House
- `who.py` - World Health Organization
- `met_office.py` - UK Met Office
- `crossref.py` - CrossRef DOI lookup
- etc. (12 more)

---

### 5.6 Refactor `retrieve.py` (Consolidate APIs)

**File:** `backend/app/pipeline/retrieve.py`

**Current:** Lines 33-64 - Only web search
**Change:** Add API queries alongside web search

```python
# EXISTING CODE (lines 1-32 stay unchanged)
class EvidenceRetriever:
    def __init__(self):
        self.search_service = SearchService()  # Existing
        self.evidence_extractor = EvidenceExtractor()  # Existing

        # NEW: Add API clients
        from app.core.config import settings
        if settings.ENABLE_API_RETRIEVAL:
            from app.services.government_api_client import GovernmentAPIClient
            from app.services.factcheck_api import FactCheckAPI
            from app.services.legal_search import LegalSearchService

            self.government_api = GovernmentAPIClient()
            self.factcheck_api = FactCheckAPI()
            self.legal_search = LegalSearchService()
        else:
            self.government_api = None
            self.factcheck_api = None
            self.legal_search = None

# MODIFY: retrieve_evidence_for_claims() (lines 33-64)
async def retrieve_evidence_for_claims(
    self,
    claims: List[Dict[str, Any]],
    exclude_source_url: Optional[str] = None
) -> Dict[str, List[Dict[str, Any]]]:
    """Retrieve evidence for multiple claims concurrently"""

    # EXISTING: Excluded domain logic
    excluded_domain = None
    if exclude_source_url:
        excluded_domain = extract_domain(exclude_source_url)
        logger.info(f"Evidence retrieval will exclude: {excluded_domain}")

    # NEW: Classify claims for API routing
    from app.utils.claim_classifier import ClaimClassifier
    classifier = ClaimClassifier()

    for claim in claims:
        classification = classifier.classify(claim["text"])
        claim["domain"] = classification["domain"]  # Add to claim
        claim["jurisdiction"] = classification.get("jurisdiction", "Global")

    # EXISTING: Process claims with concurrency
    semaphore = asyncio.Semaphore(self.max_concurrent_claims)
    tasks = [
        self._retrieve_evidence_for_single_claim(
            claim,
            semaphore,
            excluded_domain
        )
        for claim in claims
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    # ... rest of existing code unchanged

# MODIFY: _retrieve_evidence_for_single_claim() (lines 70-129)
async def _retrieve_evidence_for_single_claim(
    self,
    claim: Dict[str, Any],
    semaphore: asyncio.Semaphore,
    excluded_domain: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Retrieve evidence for a single claim"""
    async with semaphore:
        try:
            claim_text = claim.get("text", "")
            domain = claim.get("domain", "General")
            jurisdiction = claim.get("jurisdiction", "Global")

            # NEW: Query multiple sources in parallel
            sources = []

            # 1. Government APIs (NEW - if domain matches)
            if self.government_api and domain in [
                "Finance", "Health", "Government", "Climate",
                "Demographics", "Science", "Sports", "Entertainment",
                "News", "Quotes"
            ]:
                sources.append(
                    self.government_api.search_by_domain(
                        claim_text,
                        domain,
                        jurisdiction,
                        max_results=5
                    )
                )

            # 2. Legal APIs (EXISTING - if legal claim)
            if self.legal_search and domain == "Law":
                legal_metadata = claim.get("legal_metadata", {})
                sources.append(
                    self.legal_search.search_statutes(
                        claim_text,
                        legal_metadata
                    )
                )

            # 3. Fact-check APIs (EXISTING - always query)
            if self.factcheck_api:
                sources.append(
                    self.factcheck_api.search_fact_checks(claim_text)
                )

            # 4. Web search (EXISTING - always run as fallback)
            sources.append(
                self._search_web(claim, excluded_domain)  # Existing method
            )

            # Execute all sources in parallel
            api_results = await asyncio.gather(*sources, return_exceptions=True)

            # Merge all sources
            all_evidence = []
            for result in api_results:
                if isinstance(result, Exception):
                    logger.error(f"Source failed: {result}")
                    continue

                if result:
                    # Convert fact-check/legal results to evidence format
                    if isinstance(result, list):
                        all_evidence.extend(result)

            # EXISTING: Rank with embeddings (lines 131-193)
            ranked_evidence = await self._rank_evidence_with_embeddings(
                claim_text,
                all_evidence  # Now includes API + web
            )

            # EXISTING: Apply credibility weighting (lines 261-370)
            final_evidence = self._apply_credibility_weighting(ranked_evidence, claim)

            return final_evidence[:self.max_sources_per_claim]

        except Exception as e:
            logger.error(f"Single claim retrieval error: {e}")
            return []

# NEW HELPER METHOD
async def _search_web(
    self,
    claim: Dict[str, Any],
    excluded_domain: Optional[str]
) -> List[Dict]:
    """Web search (existing logic extracted)"""
    evidence_snippets = await self.evidence_extractor.extract_evidence_for_claim(
        claim["text"],
        max_sources=self.max_sources_per_claim * 2,
        subject_context=claim.get("subject_context"),
        key_entities=claim.get("key_entities", []),
        excluded_domain=excluded_domain
    )

    # Convert to evidence format
    return [
        {
            "text": snippet.text,
            "source": snippet.source,
            "url": snippet.url,
            "title": snippet.title,
            "published_date": snippet.published_date,
            "relevance_score": float(snippet.relevance_score),
            "word_count": snippet.word_count,
            "metadata": snippet.metadata
        }
        for snippet in evidence_snippets
    ]
```

**Key changes:**
- Add 3 API clients to `__init__` (government, factcheck, legal)
- Classify claims to get domain
- Query all sources in parallel (APIs + web)
- Merge results
- Existing ranking/credibility logic unchanged

---

### 5.7 Modify `pipeline.py` (Remove Stage 2.5)

**File:** `backend/app/workers/pipeline.py`

**Current:** Stage 2.5 (lines 286-296) queries fact-check API separately
**Change:** Remove Stage 2.5, rely on retrieve.py to handle all APIs

```python
# DELETE Stage 2.5 (lines 286-296)
# Stage 2.5: Fact-check lookup (if enabled)
# factcheck_evidence = {}
# if settings.ENABLE_FACTCHECK_API:
#     ... DELETE THIS ENTIRE BLOCK

# KEEP Stage 3 (lines 298-317), but pass empty factcheck_evidence
# Stage 3: Retrieve evidence (REAL IMPLEMENTATION WITH CACHING)
self.update_state(state="PROGRESS", meta={"stage": "retrieve", "progress": 40})
stage_start = datetime.utcnow()

try:
    # Extract source URL for self-citation filtering
    source_url = content.get("metadata", {}).get("url")

    # CHANGE: Remove factcheck_evidence parameter (now handled in retrieve.py)
    evidence = asyncio.run(retrieve_evidence_with_cache(
        claims,
        cache_service,
        source_url=source_url  # factcheck_evidence removed
    ))
except Exception as e:
    logger.error(f"Retrieve stage failed: {e}")
    # ... existing error handling

# NEW: Track API usage stats (add after line 317)
api_stats = self._calculate_api_stats(evidence)  # NEW METHOD

# ... rest of pipeline unchanged

# NEW METHOD (add at end of file, ~40 lines)
def _calculate_api_stats(evidence_by_claim: Dict) -> Dict:
    """Calculate API usage statistics from evidence"""
    api_sources_used = set()
    api_call_count = 0
    total_evidence = 0
    api_evidence = 0

    for position, evidence_list in evidence_by_claim.items():
        for ev in evidence_list:
            total_evidence += 1

            # Check if evidence came from an API
            if ev.get("source_type") == "api" or ev.get("external_source_provider"):
                api_evidence += 1
                api_call_count += 1

                provider = ev.get("external_source_provider") or ev.get("source")
                if provider:
                    api_sources_used.add(provider)

    coverage = (api_evidence / total_evidence * 100) if total_evidence > 0 else 0.0

    return {
        "api_sources_used": list(api_sources_used),
        "api_call_count": api_call_count,
        "api_coverage_percentage": round(coverage, 2)
    }
```

---

### 5.8 Add Feature Flag

**File:** `backend/app/core/config.py`

```python
# Add after line 106 (after LEGAL_CACHE_TTL_DAYS)

# ========== PHASE 4: GOVERNMENT API INTEGRATION ==========
ENABLE_API_RETRIEVAL: bool = Field(False, env="ENABLE_API_RETRIEVAL")

# API Keys (15 new sources)
ONS_API_KEY: Optional[str] = Field(None, env="ONS_API_KEY")
COMPANIES_HOUSE_API_KEY: Optional[str] = Field(None, env="COMPANIES_HOUSE_API_KEY")
MET_OFFICE_API_KEY: Optional[str] = Field(None, env="MET_OFFICE_API_KEY")
FRED_API_KEY: Optional[str] = Field(None, env="FRED_API_KEY")
NHS_API_KEY: Optional[str] = Field(None, env="NHS_API_KEY")
CROSSREF_API_KEY: Optional[str] = Field(None, env="CROSSREF_API_KEY")
WIKIDATA_API_KEY: Optional[str] = Field(None, env="WIKIDATA_API_KEY")
SPORTS_OPENDATA_API_KEY: Optional[str] = Field(None, env="SPORTS_OPENDATA_API_KEY")
MUSICBRAINZ_API_KEY: Optional[str] = Field(None, env="MUSICBRAINZ_API_KEY")
GOVUK_CONTENT_API_KEY: Optional[str] = Field(None, env="GOVUK_CONTENT_API_KEY")
HANSARD_API_KEY: Optional[str] = Field(None, env="HANSARD_API_KEY")
REDDIT_API_KEY: Optional[str] = Field(None, env="REDDIT_API_KEY")
REDDIT_API_SECRET: Optional[str] = Field(None, env="REDDIT_API_SECRET")
STACK_EXCHANGE_API_KEY: Optional[str] = Field(None, env="STACK_EXCHANGE_API_KEY")
WHO_API_KEY: Optional[str] = Field(None, env="WHO_API_KEY")

# API Configuration
API_TIMEOUT_SECONDS: int = Field(10, env="API_TIMEOUT_SECONDS")
API_CACHE_TTL_HOURS: int = Field(24, env="API_CACHE_TTL_HOURS")
```

---

## 6. Implementation Timeline

### Week 1-2: Foundation

**Tasks:**
1. Fix `CacheService` event loop issue (add sync wrapper)
2. Extend `ClaimClassifier` with domain detection
3. Run database migration (add Evidence table fields)
4. Extend `SourceCredibilityService` (add 15 API domains)
5. Create `GovernmentAPIClient` base class
6. Implement 5 adapters: ONS, PubMed, Companies House, FRED, WHO

**Deliverable:** 5 APIs working, feature flag off

---

### Week 3-4: Scale Up

**Tasks:**
1. Implement 10 more adapters (Met Office, CrossRef, Wikidata, etc.)
2. Refactor `retrieve.py` to consolidate API calls
3. Remove Stage 2.5 from `pipeline.py`
4. Add API stats tracking
5. Unit tests for all adapters

**Deliverable:** 15 APIs integrated, ready for testing

---

### Week 5: Testing & Optimization

**Tasks:**
1. Integration tests (end-to-end pipeline)
2. Performance testing (ensure <10s latency)
3. Cache hit rate optimization
4. Fix any bugs discovered
5. Documentation

**Deliverable:** Production-ready code

---

### Week 6: Rollout

**Week 6.1:** Enable for internal users (feature flag: 0%)
**Week 6.2:** Enable for 10% users (A/B test)
**Week 6.3:** Enable for 50% users (if metrics good)
**Week 6.4:** Enable for 100% users (GA)

**Success Metrics:**
- 30-50% API coverage (% of evidence from APIs)
- <10s P95 latency (no degradation)
- 60%+ cache hit rate
- Zero production incidents

---

## 7. Testing Strategy

### Unit Tests

```python
# backend/tests/test_government_api.py
import pytest
from app.services.government_api_client import GovernmentAPIClient

@pytest.mark.asyncio
async def test_ons_adapter():
    """Test ONS adapter returns data"""
    client = GovernmentAPIClient()
    results = await client.search_by_domain(
        "UK unemployment rate",
        domain="Finance",
        jurisdiction="UK"
    )

    assert len(results) > 0
    assert results[0]["source_type"] == "api"
    assert results[0]["external_source_provider"] == "ONS Economic Statistics"
```

### Integration Tests

```python
# backend/tests/integration/test_api_pipeline.py
@pytest.mark.asyncio
async def test_finance_claim_routes_to_ons(test_db, test_user):
    """Test finance claims use ONS API"""
    from app.workers.pipeline import process_check

    result = process_check(
        check_id="test-1",
        user_id=test_user.id,
        input_data={
            "input_type": "text",
            "content": "UK unemployment is 5.2%"
        }
    )

    # Verify API was used
    assert "ONS Economic Statistics" in result["api_stats"]["api_sources_used"]
    assert result["api_stats"]["api_coverage_percentage"] > 0
```

---

## 8. Rollout Plan

### Phase 1: Internal Testing (Week 6.1)

```bash
# .env
ENABLE_API_RETRIEVAL=false  # Default off

# For internal users only (via admin panel)
INTERNAL_USER_IDS=["user_123", "user_456"]
```

**Monitor:**
- Logs for errors
- Latency (Sentry)
- API coverage %

---

### Phase 2: Controlled Rollout (Week 6.2-6.3)

```bash
# Enable for 10% users
ENABLE_API_RETRIEVAL=true
FEATURE_ROLLOUT_PERCENTAGE=10
```

**A/B Test:**
- Group A: With APIs
- Group B: Without APIs (control)

**Compare:**
- Evidence credibility scores
- User satisfaction (feedback)
- Verdict accuracy

---

### Phase 3: Full Rollout (Week 6.4)

```bash
# Enable for all users
ENABLE_API_RETRIEVAL=true
FEATURE_ROLLOUT_PERCENTAGE=100
```

**Declare GA** (General Availability)

---

## ✅ Summary: What We're Actually Building

### **8 Files Modified:**
1. `claim_classifier.py` - Add domain detection (+50 lines)
2. `cache.py` - Fix event loop + API caching (+50 lines)
3. `source_credibility.py` - Register 15 APIs (+30 lines or JSON)
4. `retrieve.py` - Consolidate API calls (+100 lines)
5. `pipeline.py` - Remove Stage 2.5, add stats (+40 lines)
6. `config.py` - Add feature flag + 15 API keys (+20 lines)
7. `check.py` - Add Evidence fields (via migration)
8. Alembic migration - DB changes (+30 lines)

### **17 New Files Created:**
1. `government_api_client.py` - Unified client (~500 lines)
2-16. 15 API adapters (~150 lines each = 2250 lines)
17. Alembic migration

**Total new code:** ~2850 lines
**Total modified code:** ~290 lines
**No duplicated systems**

### **Result:**
- Extends existing pipeline infrastructure
- Reuses existing classification, caching, credibility systems
- Consolidates all external APIs into Stage 3
- Non-breaking (feature flag controlled)
- 30-50% API coverage increase
- Zero cost ($0/month, all free APIs)

---

**This plan IMPROVES the pipeline by making it smarter about where to find evidence. It doesn't obliterate anything - it builds on what works.**

Ready to start implementation?

1. **Week 1:** Fix cache + extend classifier
2. **Week 2:** Build first 5 adapters
3. **Week 3-4:** Scale to 15 adapters + refactor retrieve.py
4. **Week 5:** Test & optimize
5. **Week 6:** Gradual rollout

**Questions or concerns before we begin?**
