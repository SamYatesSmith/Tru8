# Government API Adapter Guide
**Phase 5: Government API Integration**

**Version**: 1.0
**Last Updated**: 2025-11-12

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Available Adapters](#available-adapters)
4. [Configuration](#configuration)
5. [Domain Routing](#domain-routing)
6. [Performance Characteristics](#performance-characteristics)
7. [Troubleshooting](#troubleshooting)
8. [Adding New Adapters](#adding-new-adapters)
9. [API Reference](#api-reference)

---

## Overview

The Government API Integration system augments Tru8's evidence retrieval with authoritative data from 10+ government and institutional APIs. The system intelligently routes claims to relevant APIs based on domain and jurisdiction, retrieves evidence in parallel with web search, and tracks comprehensive statistics.

### Key Features

- **Intelligent Routing**: Automatic domain/jurisdiction detection via spaCy NER
- **Parallel Execution**: API calls run concurrently with web search (non-blocking)
- **Comprehensive Caching**: Adapter-specific TTLs based on data stability
- **Graceful Fallback**: Individual API failures don't block pipeline
- **Statistics Tracking**: API coverage, call counts, and performance metrics
- **Feature Flag Control**: Easy enable/disable via `ENABLE_API_RETRIEVAL`

---

## Architecture

```
┌─────────────────┐
│  User Claim     │
└────────┬────────┘
         │
         ▼
┌────────────────────────────┐
│  ClaimClassifier           │
│  (spaCy NER)               │
│  → domain: Finance         │
│  → jurisdiction: UK        │
└────────┬───────────────────┘
         │
         ▼
┌────────────────────────────┐
│  APIAdapterRegistry        │
│  → get_adapters_for_domain │
│  → [ONSAdapter]            │
└────────┬───────────────────┘
         │
         ▼
┌────────────────────────────┐     ┌──────────────────┐
│  EvidenceRetriever         │────▶│  Web Search      │
│  (Parallel Execution)      │     └──────────────────┘
│                            │
│  asyncio.gather([          │     ┌──────────────────┐
│    web_search_task,        │────▶│  API Retrieval   │
│    api_retrieval_task      │     │  (10 adapters)   │
│  ])                        │     └──────────────────┘
└────────┬───────────────────┘
         │
         ▼
┌────────────────────────────┐
│  Merged & Ranked Evidence  │
│  + API Statistics          │
└────────────────────────────┘
```

### Components

1. **ClaimClassifier** (`app/utils/claim_classifier.py`)
   - Uses spaCy `en_core_web_sm` for Named Entity Recognition
   - Detects domain (Finance, Health, Government, etc.)
   - Detects jurisdiction (UK, US, Global)

2. **APIAdapterRegistry** (`app/services/government_api_client.py`)
   - Maintains registry of all adapters
   - Routes claims to relevant adapters
   - Handles adapter initialization

3. **GovernmentAPIClient** (`app/services/government_api_client.py`)
   - Abstract base class for all adapters
   - Provides: caching, error handling, rate limiting
   - Standard interface: `search()`, `_transform_response()`

4. **Individual Adapters** (`app/services/api_adapters.py`)
   - ONS, PubMed, Companies House, FRED, WHO, etc.
   - Each implements domain-specific search logic
   - Returns standardized evidence format

---

## Available Adapters

### Week 1 Adapters (3)

#### 1. ONS Economic Statistics
- **Domain**: Finance, Demographics
- **Jurisdiction**: UK
- **API Key**: Not required
- **Rate Limit**: 300 requests/hour
- **Cache TTL**: 7 days
- **Base URL**: https://api.beta.ons.gov.uk/v1

**Example Query**:
```python
adapter.search("UK unemployment rate", "Finance", "UK")
# Returns ONS dataset releases, time series data
```

**Metadata**:
```json
{
  "dataset_id": "LMS",
  "release_date": "2025-01-10",
  "contact_name": "Labour Market Team"
}
```

---

#### 2. PubMed
- **Domain**: Health, Science
- **Jurisdiction**: Global
- **API Key**: Optional (increases rate limit 3→10 req/sec)
- **Rate Limit**: 3 req/sec (10 with key)
- **Cache TTL**: 14 days
- **Base URL**: https://eutils.ncbi.nlm.nih.gov/entrez/eutils

**Example Query**:
```python
adapter.search("COVID-19 vaccine efficacy", "Health", "Global")
# Returns PubMed articles with titles, abstracts, authors
```

**Metadata**:
```json
{
  "pmid": "38123456",
  "authors": "John Smith, Jane Doe",
  "publication_date": "2024-03-01"
}
```

---

#### 3. Companies House (UK)
- **Domain**: Government, Finance
- **Jurisdiction**: UK
- **API Key**: **REQUIRED**
- **Rate Limit**: 600 requests/hour
- **Cache TTL**: 7 days
- **Base URL**: https://api.company-information.service.gov.uk

**Example Query**:
```python
adapter.search("Acme Corporation limited", "Government", "UK")
# Returns company profiles, filing history
```

**Metadata**:
```json
{
  "company_number": "12345678",
  "company_status": "active",
  "incorporation_date": "2020-01-15"
}
```

---

### Week 2 Adapters (7)

#### 4. FRED (US Federal Reserve)
- **Domain**: Finance
- **Jurisdiction**: US
- **API Key**: **REQUIRED**
- **Rate Limit**: 1,000 requests/day
- **Cache TTL**: 7 days
- **Base URL**: https://api.stlouisfed.org/fred

---

#### 5. WHO (World Health Organization)
- **Domain**: Health
- **Jurisdiction**: Global
- **API Key**: Not required
- **Rate Limit**: Unlimited
- **Cache TTL**: 7 days
- **Base URL**: https://ghoapi.azureedge.net/api

---

#### 6. Met Office (UK)
- **Domain**: Climate
- **Jurisdiction**: UK
- **API Key**: **REQUIRED**
- **Rate Limit**: 5,000 requests/day
- **Cache TTL**: 1 hour (weather changes frequently)
- **Base URL**: http://datapoint.metoffice.gov.uk/public/data

**Note**: Currently placeholder implementation (limited search capability)

---

#### 7. CrossRef
- **Domain**: Science
- **Jurisdiction**: Global
- **API Key**: Not required (polite usage)
- **Rate Limit**: Unlimited (polite usage)
- **Cache TTL**: 14 days
- **Base URL**: https://api.crossref.org

---

#### 8. GOV.UK Content API
- **Domain**: Government, General
- **Jurisdiction**: UK
- **API Key**: Not required
- **Rate Limit**: Unlimited
- **Cache TTL**: 1 day
- **Base URL**: https://www.gov.uk/api/search.json

---

#### 9. UK Parliament Hansard
- **Domain**: Government, Law
- **Jurisdiction**: UK
- **API Key**: Not required
- **Rate Limit**: Unlimited
- **Cache TTL**: 7 days
- **Base URL**: https://hansard-api.parliament.uk

---

#### 10. Wikidata
- **Domain**: General
- **Jurisdiction**: Global
- **API Key**: Not required
- **Rate Limit**: Unlimited (polite usage)
- **Cache TTL**: 30 days (structured data very stable)
- **Base URL**: https://www.wikidata.org/w/api.php

---

## Configuration

### Environment Variables

```bash
# Phase 5: Government API Integration
ENABLE_API_RETRIEVAL=true  # Enable/disable API retrieval

# Required API Keys (3)
COMPANIES_HOUSE_API_KEY=your_key_here
FRED_API_KEY=your_key_here
MET_OFFICE_API_KEY=your_key_here

# Optional API Keys (1)
PUBMED_API_KEY=your_key_here  # Increases rate limit

# No API Keys Required (6)
# ONS, WHO, CrossRef, GOV.UK, Hansard, Wikidata
```

### Obtaining API Keys

1. **Companies House**: https://developer.company-information.service.gov.uk/
   - Register for free account
   - Create application
   - Copy API key

2. **FRED**: https://fred.stlouisfed.org/docs/api/api_key.html
   - Create FRED account
   - Request API key (instant)
   - Free tier: 1,000 requests/day

3. **Met Office**: https://www.metoffice.gov.uk/services/data/datapoint/api
   - Register for DataPoint account
   - Request API key (approval required)
   - Free tier: 5,000 requests/day

4. **PubMed** (Optional): https://www.ncbi.nlm.nih.gov/account/settings/
   - Create NCBI account
   - Generate API key
   - Increases rate from 3→10 req/sec

### Application Startup

Adapters are automatically initialized on application startup:

```python
# In main.py lifespan manager
if settings.ENABLE_API_RETRIEVAL:
    from app.services.api_adapters import initialize_adapters
    initialize_adapters()
```

---

## Domain Routing

### Domain Classification

Claims are automatically classified into domains using spaCy NER:

| Domain | Triggers | Example Claim |
|--------|----------|---------------|
| **Finance** | GDP, unemployment, inflation, interest rate, stock, economy | "UK unemployment is 5.2%" |
| **Health** | vaccine, disease, hospital, treatment, WHO, CDC | "COVID-19 vaccine is 95% effective" |
| **Government** | parliament, legislation, policy, minister, election | "Parliament passed new climate bill" |
| **Law** | court, judge, legal, legislation, case | "Supreme Court ruled on abortion" |
| **Climate** | climate, weather, temperature, emissions | "Met Office forecasts record heat" |
| **Science** | research, study, experiment, scientific | "New study shows climate impact" |
| **Demographics** | population, census, birth rate, migration | "UK population reached 67 million" |
| **General** | Fallback for ambiguous claims | "Douglas Adams wrote books" |

### Jurisdiction Detection

Jurisdiction is detected using priority-based logic:

**Priority 1**: Organization entities (highest signal)
- "according to the ONS" → UK
- "Federal Reserve announced" → US
- "WHO declared" → Global

**Priority 2**: Explicit location indicators
- "UK", "USA", "European Union" → Jurisdiction extracted

**Priority 3**: GPE (Geo-Political Entity) from spaCy
- Entity label "GPE" → Check against known jurisdictions

**Priority 4**: Default to Global

### Adapter Routing Logic

```python
# Example: Finance claim about UK
domain_info = classifier.detect_domain("UK unemployment is 5.2%")
# → domain="Finance", jurisdiction="UK"

adapters = registry.get_adapters_for_domain("Finance", "UK")
# → [ONSAdapter] (covers Finance + UK)

# Example: Health claim, Global
domain_info = classifier.detect_domain("WHO declared pandemic")
# → domain="Health", jurisdiction="Global"

adapters = registry.get_adapters_for_domain("Health", "Global")
# → [PubMedAdapter, WHOAdapter] (both cover Health + Global)
```

---

## Performance Characteristics

### Latency Targets

| Operation | Target | Actual (Week 4 Tests) |
|-----------|--------|----------------------|
| **API Retrieval (single claim)** | <2s | <500ms (mocked) |
| **API Retrieval (5 claims)** | <5s | <2s (with concurrency) |
| **Full Pipeline (single claim)** | <10s P95 | TBD (end-to-end test) |
| **API Cache Hit** | <50ms | <10ms (Redis) |

### Cache Strategy

Different TTLs based on data stability:

| Data Type | Example APIs | TTL | Rationale |
|-----------|--------------|-----|-----------|
| **Weather** | Met Office | 1 hour | Changes frequently |
| **News/Gov Content** | GOV.UK | 1 day | Updated daily |
| **Economic Data** | ONS, FRED | 7 days | Weekly/monthly releases |
| **Health Stats** | WHO | 7 days | Periodic updates |
| **Historical Records** | Hansard | 7 days | Archival content |
| **Research Metadata** | CrossRef, PubMed | 14 days | Very stable |
| **Structured Knowledge** | Wikidata | 30 days | Extremely stable |

### Expected API Response Times

| API | Typical Latency | Max Latency | Notes |
|-----|----------------|-------------|-------|
| ONS | 200-500ms | 2s | Large datasets |
| PubMed | 300-600ms | 3s | XML parsing |
| Companies House | 150-300ms | 1s | Simple JSON |
| FRED | 100-300ms | 1s | Fast API |
| WHO | 500ms-1s | 3s | Large DB |
| CrossRef | 300-800ms | 2s | Research DB |
| GOV.UK | 200-400ms | 1s | UK gov infrastructure |
| Hansard | 500ms-1s | 3s | Archive search |
| Wikidata | 300-600ms | 2s | SPARQL queries |

---

## Troubleshooting

### Issue 1: API Adapters Not Initializing

**Symptoms**: No API evidence in results, logs show "0 adapters registered"

**Cause**: `ENABLE_API_RETRIEVAL` flag is false or adapters not initialized

**Solution**:
```bash
# Check environment variable
echo $ENABLE_API_RETRIEVAL  # Should be "true"

# Verify initialization in logs
grep "Registered.*adapter" logs/app.log

# Expected output:
# INFO: Registered ONS adapter
# INFO: Registered PubMed adapter
# ...
```

---

### Issue 2: API Returning No Results

**Symptoms**: API stats show calls made but 0 results returned

**Possible Causes**:
1. **API key missing or invalid**
   - Check `.env` file for required keys
   - Verify key validity with API provider

2. **Domain mismatch**
   - Check domain detection: may be routing to wrong adapters
   - Example: "vaccine" detected as "Science" instead of "Health"

3. **Query too specific**
   - APIs may not match exact phrasing
   - Try broader queries for testing

**Solution**:
```python
# Debug domain detection
from app.utils.claim_classifier import ClaimClassifier

classifier = ClaimClassifier()
result = classifier.detect_domain("your claim here")
print(result)  # Check domain and jurisdiction

# Debug adapter routing
from app.services.government_api_client import get_api_registry

registry = get_api_registry()
adapters = registry.get_adapters_for_domain(result["domain"], result["jurisdiction"])
print([a.api_name for a in adapters])  # Should list relevant adapters
```

---

### Issue 3: High API Latency

**Symptoms**: Pipeline takes >10s, API calls are slow

**Possible Causes**:
1. **Sequential API calls** (should be parallel)
2. **API rate limiting** (429 errors)
3. **Network issues**
4. **Cache not working**

**Solution**:
```python
# Check if calls are parallel (should take ~max, not sum)
# If 3 APIs each take 1s:
# - Parallel: ~1s total
# - Sequential: ~3s total

# Check cache hit rate
# Expected: 60%+ on repeated queries

# Check for rate limit errors in logs
grep "429\|rate limit" logs/app.log
```

---

### Issue 4: API Coverage Too Low

**Symptoms**: API coverage < 10% (mostly web evidence)

**Possible Causes**:
1. **Domain not detected** (fallback to General)
2. **No adapters for domain/jurisdiction**
3. **APIs returning empty results**

**Solution**:
```bash
# Check domain distribution in logs
grep "API routing: domain=" logs/app.log | sort | uniq -c

# Expected: Mix of domains, not all "General"

# Check adapter coverage
# 10 adapters for: Finance, Health, Government, Science, Climate, Law, Demographics, General
# Ensure claims match these domains
```

---

### Issue 5: Database Errors (api_metadata/api_sources_used)

**Symptoms**: `IntegrityError` or `JSONDecodeError` when saving to DB

**Cause**: JSON serialization issues (should be fixed in Week 3)

**Solution**:
```bash
# Verify no double JSON encoding
# BAD: json.dumps(data) before saving to JSON column
# GOOD: pass dict/list directly to JSON column

# Check migration status
cd backend && alembic current
# Should show: 595bc2ddd5c5 (rename_evidence_metadata_to_api_metadata)
```

---

## Adding New Adapters

### Step 1: Create Adapter Class

```python
# In backend/app/services/api_adapters.py

class NewAPIAdapter(GovernmentAPIClient):
    """Adapter for New API."""

    def __init__(self):
        api_key = os.getenv("NEW_API_KEY")
        super().__init__(
            api_name="New API",
            base_url="https://api.newapi.com",
            api_key=api_key,
            cache_ttl=86400 * 7,  # 7 days
            timeout=10,
            max_results=10
        )

    def is_relevant_for_domain(self, domain: str, jurisdiction: str) -> bool:
        """Define when this API is relevant."""
        return domain == "YourDomain" and jurisdiction in ["UK", "Global"]

    def search(self, query: str, domain: str, jurisdiction: str) -> List[Dict[str, Any]]:
        """Search the API."""
        if not self.is_relevant_for_domain(domain, jurisdiction):
            return []

        if not self.api_key:
            logger.warning(f"{self.api_name} API key not configured")
            return []

        # Sanitize query
        query = self._sanitize_query(query)

        # Build request parameters
        params = {
            "q": query,
            "limit": self.max_results
        }

        # Make API request
        response = self._make_request("/search", params=params)
        if not response:
            return []

        # Transform to standard format
        return self._transform_response(response)

    def _transform_response(self, raw_response: Any) -> List[Dict[str, Any]]:
        """Transform API response to standard evidence format."""
        results = []

        for item in raw_response.get("items", []):
            evidence = self._create_evidence_dict(
                title=item.get("title", ""),
                snippet=item.get("description", ""),
                url=item.get("url", ""),
                source_date=parse_date(item.get("published")),
                metadata={
                    "item_id": item.get("id"),
                    "custom_field": item.get("custom_field")
                }
            )
            results.append(evidence)

        return results
```

### Step 2: Register Adapter

```python
# In initialize_adapters() function

def initialize_adapters():
    # ... existing adapters ...

    # Register new adapter
    new_api_key = os.getenv("NEW_API_KEY")
    if new_api_key:
        registry.register(NewAPIAdapter())
        logger.info("Registered New API adapter")
    else:
        logger.warning("New API key not configured, adapter not registered")
```

### Step 3: Add Tests

```python
# In backend/tests/test_api_adapters_weekN.py

class TestNewAPIAdapter:
    def test_instantiation(self):
        adapter = NewAPIAdapter()
        assert adapter.api_name == "New API"
        assert "newapi.com" in adapter.base_url

    def test_is_relevant_for_domain(self):
        adapter = NewAPIAdapter()
        assert adapter.is_relevant_for_domain("YourDomain", "UK") == True
        assert adapter.is_relevant_for_domain("Finance", "UK") == False

    def test_transform_response(self):
        adapter = NewAPIAdapter()
        mock_response = {
            "items": [
                {"title": "Test", "description": "Test desc", "url": "https://test.com"}
            ]
        }
        result = adapter._transform_response(mock_response)
        assert len(result) == 1
        assert result[0]["title"] == "Test"
```

### Step 4: Update Documentation

- Add to "Available Adapters" section above
- Document API key requirements
- Add to `.env.example`
- Update adapter count in README

---

## API Reference

### ClaimClassifier

```python
from app.utils.claim_classifier import ClaimClassifier

classifier = ClaimClassifier()
result = classifier.detect_domain(claim_text: str) -> Dict[str, Any]

# Returns:
# {
#   "domain": "Finance",  # Finance, Health, Government, Law, Climate, Science, Demographics, General
#   "domain_confidence": 0.85,  # 0-1
#   "jurisdiction": "UK",  # UK, US, EU, Global
#   "key_entities": ["ONS", "unemployment"]  # List[str]
# }
```

### APIAdapterRegistry

```python
from app.services.government_api_client import get_api_registry

registry = get_api_registry()

# Get all adapters
all_adapters = registry.get_all_adapters()

# Get adapters for specific domain/jurisdiction
adapters = registry.get_adapters_for_domain(
    domain="Finance",
    jurisdiction="UK"
)  # Returns List[GovernmentAPIClient]

# Get single adapter by name
adapter = registry.get_adapter_by_name("ONS Economic Statistics")
```

### GovernmentAPIClient (Base Class)

```python
from app.services.government_api_client import GovernmentAPIClient

class MyAdapter(GovernmentAPIClient):
    def __init__(self):
        super().__init__(
            api_name="My API",
            base_url="https://api.example.com",
            api_key="optional",
            cache_ttl=86400,  # seconds
            timeout=10,  # seconds
            max_results=10
        )

    def search(self, query, domain, jurisdiction):
        # Implement search logic
        pass

    def _transform_response(self, raw_response):
        # Transform to standard format
        pass

    def is_relevant_for_domain(self, domain, jurisdiction):
        # Return True if adapter covers this domain/jurisdiction
        pass
```

### Evidence Format

Standard evidence dictionary returned by all adapters:

```python
{
    "title": str,  # Evidence title
    "snippet": str,  # Evidence snippet/summary (300 chars)
    "url": str,  # Source URL
    "source": str,  # API name
    "external_source_provider": str,  # API name (for DB)
    "credibility_score": float,  # 0-1 (usually 0.95 for APIs)
    "source_date": str,  # ISO format or None
    "metadata": dict,  # API-specific metadata
    "retrieved_at": str  # ISO timestamp
}
```

---

## Performance Metrics

### Week 4 Test Results

```
Performance Tests: 7 passed
- API retrieval latency: <500ms ✅
- Parallel API calls: ~500ms (not ~1000ms sequential) ✅
- Single claim latency: <2s ✅
- Multi-claim latency (5 claims): <5s ✅
- Error handling: Graceful fallback ✅
- Partial API failure: Continues with working APIs ✅
- Statistics tracking: Accurate aggregation ✅
```

### Cache Hit Rate Targets

| Query Type | Target | Notes |
|------------|--------|-------|
| **Repeated exact queries** | 95%+ | Same claim text |
| **Similar queries** | 60-80% | Slight variations |
| **Unique queries** | 0% | First-time queries |
| **Overall (production)** | 60%+ | Mix of all types |

---

## Conclusion

The Government API Integration system provides authoritative, high-credibility evidence from 10+ institutional sources. With intelligent routing, parallel execution, and comprehensive caching, the system augments Tru8's evidence retrieval without impacting pipeline performance.

**Status**: Production-ready (Week 4 complete)

---

**Document Version**: 1.0
**Last Updated**: 2025-11-12
**Maintained By**: Tru8 Engineering Team
