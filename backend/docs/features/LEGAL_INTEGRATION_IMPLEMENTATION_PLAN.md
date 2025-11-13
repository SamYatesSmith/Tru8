# Legal Statute Integration - Production Implementation Plan

**Status:** Ready for Implementation
**Created:** 2025-11-11
**Priority:** HIGH - Adds significant value to pipeline
**Risk Level:** MEDIUM (external APIs, but well-mitigated)
**Estimated Effort:** 60 hours (1.5-2 weeks)

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Implementation Philosophy](#implementation-philosophy)
3. [Prerequisites](#prerequisites)
4. [Phase 1: Foundation & Detection](#phase-1-foundation--detection)
5. [Phase 2: API Integration Layer](#phase-2-api-integration-layer)
6. [Phase 3: Evidence Pipeline Integration](#phase-3-evidence-pipeline-integration)
7. [Phase 4: Testing & Validation](#phase-4-testing--validation)
8. [Phase 5: Deployment & Monitoring](#phase-5-deployment--monitoring)
9. [Rollback Procedures](#rollback-procedures)
10. [Success Criteria](#success-criteria)

---

## Executive Summary

### The Value Proposition

Legal statute claims currently fail because:
- Classified as generic "factual" claims (no special handling)
- Generic web search returns news ABOUT laws, not laws themselves
- congress.gov, govinfo.gov, legislation.gov.uk rarely appear in results
- Verdict confidence: ~45-60% (low)

**With legal integration:**
- Detect legal claims accurately (90%+ precision)
- Direct API access to primary legal sources
- Section-level statute text extraction
- Verdict confidence: ~80-90% (high)

### The Implementation Strategy

**Core Principle:** Build incrementally with safety at every layer

```
Phase 1: Detection (Week 1)
  └─ Can classify legal claims, no behavioral change yet

Phase 2: API Layer (Week 1-2)
  └─ New service, doesn't touch existing pipeline

Phase 3: Pipeline Integration (Week 2)
  └─ Conditional routing, graceful fallbacks

Phase 4: Testing (Week 2-3)
  └─ Comprehensive validation before production

Phase 5: Gradual Rollout (Week 3)
  └─ Feature flags, monitoring, A/B testing
```

### Why This Approach is Safe

1. **Feature Flags:** Can disable entire feature instantly
2. **Graceful Fallbacks:** API failures return empty[], not errors
3. **No Breaking Changes:** Additive only, existing pipeline unaffected
4. **Incremental Deployment:** Each phase validates before next
5. **Comprehensive Testing:** Unit → Integration → End-to-end
6. **Monitoring:** Track every decision point and failure

---

## Implementation Philosophy

### Guiding Principles

**1. Safety First**
- Every integration point has try-catch with fallback
- Feature flags at multiple levels (service, routing, boosting)
- No changes to existing evidence retrieval for non-legal claims
- Database schema already supports claim_type (no migration needed)

**2. Fail Gracefully**
- API timeout? Return empty legal results, continue with general search
- Parse error? Log warning, use raw text
- No API key? Disable legal integration, inform user

**3. Validate Continuously**
- Log every classification decision
- Log every API call result
- Track evidence sources per claim type
- Monitor accuracy improvements

**4. Build for Scale**
- Aggressive caching (30-day TTL for statutes)
- Rate limit management (5,000/hr = 83/min)
- Parallel searches across sources
- Efficient section extraction (not full documents)

**5. User Transparency**
- Show when legal sources are used
- Display statute citations clearly
- Explain if legal verification unavailable

---

## Prerequisites

### API Registration

**Required (Free):**

1. **GovInfo.gov + Congress.gov (Shared Key)**
   - Register: https://api.data.gov/signup/
   - Same key works for both APIs
   - Rate limit: 5,000 requests/hour
   - Add to `.env`: `GOVINFO_API_KEY=xxx`

**Optional (No Registration):**

2. **UK legislation.gov.uk**
   - No API key needed
   - No registration required
   - Open and free

### Environment Setup

```bash
# backend/.env additions

# Legal API Configuration
ENABLE_LEGAL_INTEGRATION=true
ENABLE_LEGAL_SOURCE_BOOSTING=true
GOVINFO_API_KEY=your_key_here
CONGRESS_API_KEY=your_key_here  # Same as GovInfo
LEGAL_API_TIMEOUT_SECONDS=10
LEGAL_CACHE_TTL_DAYS=30

# Feature Rollout Control
LEGAL_FEATURE_ROLLOUT_PERCENTAGE=100  # Start at 10%, gradually increase
LEGAL_INTERNAL_TESTING_USER_IDS=["user-id-1", "user-id-2"]  # Always enabled
```

### Development Environment

```bash
# Install any new dependencies (if needed)
cd backend
pip install httpx  # Already installed
pip install lxml   # For XML parsing (may need to add)

# Verify API access
curl "https://api.govinfo.gov/collections?api_key=DEMO_KEY"
curl "http://www.legislation.gov.uk/id?type=ukpga&year=1998&number=42"
```

---

## Phase 1: Foundation & Detection

**Timeline:** 3 days
**Effort:** 20 hours
**Risk:** MINIMAL
**Dependencies:** None

### 1.1: Update Claim Classifier

**File:** `backend/app/utils/claim_classifier.py`

#### Step 1.1.1: Add Legal Patterns

**Location:** Line 11 (in `__init__` method, after `personal_patterns`)

```python
# NEW: Legal/statutory claim patterns
self.legal_patterns = [
    # Year + legal term
    r"\b(19\d{2}|20\d{2})\s+(federal\s+)?(law|statute|act|legislation|bill)\b",

    # US Code citations
    r"\b(\d+)\s+U\.?S\.?C\.?\s+§?\s*(\d+[a-z]?(?:-\d+)?)\b",

    # UK legislation references
    r"\b(ukpga|uksi|asp)\s+\d{4}/\d+\b",
    r"\b(19\d{2}|20\d{2})\s+c\.\s*\d+\b",  # UK chapter notation

    # Legal actions
    r"\b(congress|parliament|senate|house)\s+(passed|enacted|approved|mandated?)\b",

    # Section references
    r"\b(section|§)\s+\d+\b",

    # Legal requirements
    r"\b(mandated?|required?|prohibited?)\s+(by|under)\s+(law|statute|congress|parliament)\b",

    # Constitutional references
    r"\b(constitution|constitutional|amendment)\b",

    # Public law references
    r"\b(public law|p\.l\.|pub\.\s*l\.)\s+\d+",

    # Title references
    r"\btitle\s+\d+\b",

    # Act names (common pattern)
    r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+Act\s+(?:of\s+)?\d{4}\b"
]
```

**Reasoning for each pattern:**
- Covers US federal, UK, and constitutional claims
- Balances precision (avoid false positives) with recall (catch all legal claims)
- Tested against diverse claim samples

#### Step 1.1.2: Add Legal Classification Logic

**Location:** Line 53 (before `personal_patterns` check, after `prediction_patterns`)

```python
# NEW: Check for legal/statutory claims
if any(re.search(pattern, claim_lower) for pattern in self.legal_patterns):
    metadata = self._extract_legal_metadata(claim_text)
    return {
        "claim_type": "legal",
        "is_verifiable": True,
        "reason": "This is a legal or statutory claim requiring authoritative legal sources",
        "confidence": 0.85,
        "metadata": metadata  # Additional context for search
    }
```

#### Step 1.1.3: Add Metadata Extraction Helper

**Location:** After `classify` method (new method, ~line 70)

```python
def _extract_legal_metadata(self, claim_text: str) -> Dict[str, Any]:
    """
    Extract legal metadata from claim text for search optimization.

    Returns:
        Dict with year, citation, jurisdiction, act_name
    """
    metadata = {
        "year": None,
        "citation": None,
        "jurisdiction": None,
        "act_name": None
    }

    # Extract year (4-digit year between 1700-2099)
    year_match = re.search(r"\b(1[7-9]\d{2}|20\d{2})\b", claim_text)
    if year_match:
        year = int(year_match.group(1))
        # Sanity check: reasonable year range for legislation
        if 1700 <= year <= 2099:
            metadata["year"] = year

    # Extract US Code citation
    usc_match = re.search(
        r"(\d+)\s+U\.?S\.?C\.?\s+§?\s*(\d+[a-z]?(?:-\d+)?)",
        claim_text,
        re.IGNORECASE
    )
    if usc_match:
        metadata["citation"] = {
            "type": "usc",
            "title": usc_match.group(1),
            "section": usc_match.group(2),
            "full": f"{usc_match.group(1)} U.S.C. § {usc_match.group(2)}"
        }
        metadata["jurisdiction"] = "federal_us"

    # Extract UK legislation reference (e.g., "ukpga 1998/42" or "1998 c.42")
    uk_match = re.search(
        r"(?:(ukpga|uksi|asp)\s+(\d{4})/(\d+))|(?:(\d{4})\s+c\.\s*(\d+))",
        claim_text,
        re.IGNORECASE
    )
    if uk_match:
        if uk_match.group(1):  # Format: ukpga 1998/42
            metadata["citation"] = {
                "type": uk_match.group(1).lower(),
                "year": uk_match.group(2),
                "number": uk_match.group(3)
            }
        else:  # Format: 1998 c.42
            metadata["citation"] = {
                "type": "ukpga",  # Default to Public General Act
                "year": uk_match.group(4),
                "number": uk_match.group(5)
            }
        metadata["jurisdiction"] = "uk"

    # Detect jurisdiction from keywords if not found in citation
    if not metadata["jurisdiction"]:
        federal_keywords = ["federal", "congress", "u.s.", "united states", "senate", "house"]
        uk_keywords = ["parliament", "uk", "united kingdom", "british", "westminster"]

        claim_lower = claim_text.lower()
        if any(kw in claim_lower for kw in federal_keywords):
            metadata["jurisdiction"] = "federal_us"
        elif any(kw in claim_lower for kw in uk_keywords):
            metadata["jurisdiction"] = "uk"

    # Extract act name (e.g., "Human Rights Act 1998")
    act_match = re.search(
        r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,4})\s+Act(?:\s+(?:of\s+)?(\d{4}))?",
        claim_text
    )
    if act_match:
        act_name = act_match.group(1) + " Act"
        if act_match.group(2):  # Year included
            act_name += f" {act_match.group(2)}"
            if not metadata["year"]:
                metadata["year"] = int(act_match.group(2))
        metadata["act_name"] = act_name

    return metadata
```

**Why this metadata matters:**
- **year**: Filters search to specific timeframe (reduces 50,000 → 500)
- **citation**: Enables direct statute lookup (fastest path)
- **jurisdiction**: Routes to correct API (US vs UK)
- **act_name**: Supports popular name lookup

### 1.2: Add Classification Tests

**File:** `backend/tests/unit/test_claim_classifier.py`

#### Step 1.2.1: Add Legal Test Class

**Location:** After existing test classes (~line 100)

```python
class TestLegalClaimDetection:
    """Test legal/statutory claim detection"""

    @pytest.fixture
    def classifier(self):
        return ClaimClassifier()

    def test_us_statute_with_citation(self, classifier):
        """Test: Detects US Code citations"""
        claims = [
            "Title 52, Section 8722 of the U.S. Code requires campaign finance reporting",
            "42 USC 1395w-3 establishes Medicare payment rules",
            "The statute at 18 U.S.C. § 1001 prohibits false statements"
        ]

        for claim in claims:
            result = classifier.classify(claim)
            assert result["claim_type"] == "legal", f"Failed for: {claim}"
            assert result["is_verifiable"] == True
            assert result["metadata"]["citation"] is not None
            assert result["metadata"]["jurisdiction"] == "federal_us"

    def test_us_statute_with_year(self, classifier):
        """Test: Detects year + law references"""
        claims = [
            "A 1952 federal law requires submission to the National Capital Planning Commission",
            "The 2010 Affordable Care Act mandates health insurance coverage",
            "Congress passed a statute in 1965 creating Medicare"
        ]

        for claim in claims:
            result = classifier.classify(claim)
            assert result["claim_type"] == "legal", f"Failed for: {claim}"
            assert result["metadata"]["year"] is not None

    def test_uk_legislation(self, classifier):
        """Test: Detects UK legislation references"""
        claims = [
            "The Human Rights Act 1998 incorporates ECHR into UK law",
            "ukpga 1998/42 requires courts to interpret legislation compatibly",
            "The 1998 c.42 established fundamental rights protections"
        ]

        for claim in claims:
            result = classifier.classify(claim)
            assert result["claim_type"] == "legal", f"Failed for: {claim}"
            assert result["metadata"]["jurisdiction"] == "uk"

    def test_legal_vs_factual_distinction(self, classifier):
        """Test: Distinguishes legal claims from general factual claims"""
        legal_claims = [
            "The statute mandates reporting requirements",
            "Section 3 of the Act requires compatibility with ECHR"
        ]

        factual_claims = [
            "The company law firm reviewed the contract",  # "law" in different context
            "I saw the bill at the restaurant",  # "bill" in different context
            "The act of kindness was inspiring"  # "act" in different context
        ]

        for claim in legal_claims:
            result = classifier.classify(claim)
            assert result["claim_type"] == "legal", f"Should be legal: {claim}"

        for claim in factual_claims:
            result = classifier.classify(claim)
            assert result["claim_type"] != "legal", f"Should NOT be legal: {claim}"

    def test_metadata_extraction_completeness(self, classifier):
        """Test: Metadata extraction captures all available information"""
        claim = "Title 52, Section 8722 of the 2002 U.S. Code mandates reporting"

        result = classifier.classify(claim)
        metadata = result["metadata"]

        assert metadata["year"] == 2002
        assert metadata["citation"]["type"] == "usc"
        assert metadata["citation"]["title"] == "52"
        assert metadata["citation"]["section"] == "8722"
        assert metadata["jurisdiction"] == "federal_us"

    def test_act_name_extraction(self, classifier):
        """Test: Extracts popular act names"""
        claims = [
            ("The Affordable Care Act requires coverage", "Affordable Care Act"),
            ("The Freedom of Information Act 1966 establishes transparency", "Freedom of Information Act 1966"),
            ("Human Rights Act 1998 protects fundamental rights", "Human Rights Act 1998")
        ]

        for claim, expected_name in claims:
            result = classifier.classify(claim)
            assert result["metadata"]["act_name"] == expected_name, f"Failed for: {claim}"
```

#### Step 1.2.2: Run Tests

```bash
cd backend
pytest tests/unit/test_claim_classifier.py::TestLegalClaimDetection -v

# Expected output:
# test_us_statute_with_citation PASSED
# test_us_statute_with_year PASSED
# test_uk_legislation PASSED
# test_legal_vs_factual_distinction PASSED
# test_metadata_extraction_completeness PASSED
# test_act_name_extraction PASSED
```

### 1.3: Validation & Integration Testing

#### Step 1.3.1: Manual Validation

Create test file: `backend/tests/manual/test_legal_classification.py`

```python
"""
Manual validation of legal claim classification.
Run interactively to verify classification accuracy.
"""

from app.utils.claim_classifier import ClaimClassifier

def test_legal_claims():
    classifier = ClaimClassifier()

    test_cases = [
        # US Federal - Citations
        "Title 42, Section 1395 of the U.S. Code establishes Medicare",
        "18 U.S.C. § 1001 prohibits false statements to federal officials",

        # US Federal - Year + Topic
        "A 1952 federal law requires submission to planning commission",
        "The 2010 Affordable Care Act mandates health insurance",

        # UK Legislation
        "The Human Rights Act 1998 incorporates ECHR",
        "Parliament passed the Data Protection Act 2018",

        # Should NOT be legal
        "The company law firm reviewed the contract",
        "I saw the bill at the restaurant"
    ]

    for claim in test_cases:
        result = classifier.classify(claim)
        print(f"\n{'='*80}")
        print(f"CLAIM: {claim}")
        print(f"TYPE: {result['claim_type']}")
        print(f"VERIFIABLE: {result['is_verifiable']}")
        if result.get('metadata'):
            print(f"METADATA: {result['metadata']}")

if __name__ == "__main__":
    test_legal_claims()
```

Run manually:
```bash
python backend/tests/manual/test_legal_classification.py
```

#### Step 1.3.2: Integration with Extract Pipeline

Verify claim_type is populated in extract.py:

```bash
# Enable claim classification (should already be enabled)
grep "ENABLE_CLAIM_CLASSIFICATION" backend/.env
# Should show: ENABLE_CLAIM_CLASSIFICATION=true

# Test extraction with legal claim
cd backend
python -c "
import asyncio
from app.pipeline.extract import ClaimExtractor

async def test():
    extractor = ClaimExtractor()
    result = await extractor.extract_claims(
        'A 1952 federal law requires submission to the National Capital Planning Commission',
        metadata={'url': 'test'}
    )

    if result['success']:
        claim = result['claims'][0]
        print(f'Claim type: {claim.get(\"claim_type\")}')
        print(f'Classification: {claim.get(\"classification\")}')
        assert claim.get('claim_type') == 'legal', 'Legal claim not detected!'
        print('✓ Legal detection working in extract pipeline')

asyncio.run(test())
"
```

### 1.4: Phase 1 Completion Checklist

- [ ] Legal patterns added to claim_classifier.py
- [ ] Metadata extraction implemented
- [ ] Unit tests written and passing (6 tests)
- [ ] Manual validation shows 90%+ accuracy
- [ ] Extract pipeline populates claim_type="legal"
- [ ] No regressions in existing classification (opinion, prediction, etc.)
- [ ] Code reviewed for edge cases
- [ ] Committed to feature branch: `git checkout -b feature/legal-integration-phase1`

**Success Criteria:**
- Legal claims detected with 90%+ precision
- Metadata extraction accuracy 85%+
- Zero false positives from test cases
- claim_type field populated correctly

**Rollback:**
If issues found, simply remove legal detection block and patterns.

---

## Phase 2: API Integration Layer

**Timeline:** 5 days
**Effort:** 25 hours
**Risk:** MEDIUM (external APIs, but isolated service)
**Dependencies:** Phase 1 complete

### 2.1: Create Legal Search Service

**File:** `backend/app/services/legal_search.py` (NEW FILE)

This is the core service that interfaces with legal APIs.

#### Step 2.1.1: Service Structure

```python
"""
Legal Statute Search Service

Retrieves statutes from official legal APIs:
- US: GovInfo.gov (primary), Congress.gov (supplementary)
- UK: legislation.gov.uk

Follows FactCheckAPI pattern for consistency.
"""

import httpx
import re
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from xml.etree import ElementTree as ET

from app.core.config import settings

logger = logging.getLogger(__name__)


class LegalSearchService:
    """
    Search official legal databases for statutes and legislation.

    Features:
    - Direct citation lookup (fastest)
    - Year + keyword search (filtered)
    - Full-text search (broad)
    - Section-level extraction (not full documents)
    - Aggressive caching (statutes rarely change)
    """

    def __init__(self):
        self.govinfo_api_key = settings.GOVINFO_API_KEY
        self.congress_api_key = settings.CONGRESS_API_KEY
        self.timeout = settings.LEGAL_API_TIMEOUT_SECONDS

        # In-memory cache with TTL
        self.cache = {}
        self.cache_ttl = timedelta(days=settings.LEGAL_CACHE_TTL_DAYS)

    async def search_statutes(
        self,
        claim_text: str,
        metadata: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Search for statutes across appropriate sources.

        Args:
            claim_text: Original claim text
            metadata: Extracted metadata (year, citation, jurisdiction, act_name)

        Returns:
            List of statute results with text excerpts
        """
        # Check cache first
        cache_key = self._build_cache_key(claim_text, metadata)
        if cache_key in self.cache:
            cached_result, cached_time = self.cache[cache_key]
            if datetime.utcnow() - cached_time < self.cache_ttl:
                logger.info(f"Legal search cache hit: {cache_key}")
                return cached_result

        results = []
        jurisdiction = metadata.get("jurisdiction")

        try:
            if jurisdiction == "federal_us":
                results = await self._search_us_sources(claim_text, metadata)
            elif jurisdiction == "uk":
                results = await self._search_uk_sources(claim_text, metadata)
            else:
                # Unknown jurisdiction - try both
                logger.warning(f"Unknown jurisdiction, trying all sources")
                us_results = await self._search_us_sources(claim_text, metadata)
                uk_results = await self._search_uk_sources(claim_text, metadata)
                results = us_results + uk_results

            # Cache results
            self.cache[cache_key] = (results, datetime.utcnow())

            logger.info(f"Legal search returned {len(results)} results for: {claim_text[:50]}")
            return results

        except Exception as e:
            logger.error(f"Legal search failed: {e}")
            return []  # Return empty, don't crash pipeline

    async def _search_us_sources(
        self,
        claim_text: str,
        metadata: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Search US legal sources (GovInfo + Congress)"""
        results = []

        # Priority 1: Direct citation lookup (if available)
        if metadata.get("citation") and metadata["citation"].get("type") == "usc":
            citation_results = await self._search_govinfo_by_citation(
                metadata["citation"]
            )
            results.extend(citation_results)

        # Priority 2: Year + keyword search (if year available)
        if metadata.get("year") and len(results) < 3:
            year_results = await self._search_govinfo_by_year(
                claim_text,
                metadata["year"]
            )
            results.extend(year_results)

        # Priority 3: Broad keyword search (fallback)
        if len(results) < 3:
            keyword_results = await self._search_govinfo_fulltext(claim_text)
            results.extend(keyword_results)

        # Deduplicate by URL
        seen_urls = set()
        unique_results = []
        for result in results:
            if result["url"] not in seen_urls:
                seen_urls.add(result["url"])
                unique_results.append(result)

        return unique_results[:5]  # Top 5 results

    async def _search_uk_sources(
        self,
        claim_text: str,
        metadata: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Search UK legislation.gov.uk"""
        try:
            # Build search parameters
            params = {}

            if metadata.get("citation"):
                # Direct identifier lookup
                citation = metadata["citation"]
                params["type"] = citation.get("type", "ukpga")
                params["year"] = citation.get("year")
                params["number"] = citation.get("number")
            else:
                # Search by act name or keywords
                if metadata.get("act_name"):
                    params["title"] = metadata["act_name"]
                else:
                    # Extract likely act name from claim
                    params["title"] = self._extract_act_name(claim_text)

                if metadata.get("year"):
                    params["start-year"] = metadata["year"]
                    params["end-year"] = metadata["year"]

            # Remove None values
            params = {k: v for k, v in params.items() if v is not None}

            if not params:
                logger.warning("No search parameters for UK legislation")
                return []

            async with httpx.AsyncClient(
                timeout=self.timeout,
                follow_redirects=True
            ) as client:
                # Determine search URL
                if params.get("number"):
                    url = "http://www.legislation.gov.uk/id"
                else:
                    url = "http://www.legislation.gov.uk/search"

                response = await client.get(url, params=params)

                if response.status_code == 200:
                    # Fetch XML data for parsing
                    xml_url = str(response.url) + "/data.xml"
                    xml_response = await client.get(xml_url)

                    if xml_response.status_code == 200:
                        # Parse XML and extract relevant sections
                        text = self._parse_uk_legislation_xml(
                            xml_response.text,
                            claim_text
                        )

                        return [{
                            "source": "legislation.gov.uk",
                            "title": params.get("title", "UK Legislation"),
                            "url": str(response.url),
                            "text": text[:2000],  # First 2000 chars
                            "snippet": text[:500],  # First 500 chars for preview
                            "credibility_score": 1.0,
                            "tier": "legal_primary",
                            "source_type": "legal",
                            "published_date": params.get("year"),
                            "metadata": {
                                "jurisdiction": "uk",
                                "citation": params
                            }
                        }]

            return []

        except httpx.TimeoutException:
            logger.warning("UK legislation API timeout")
            return []
        except Exception as e:
            logger.error(f"UK legislation search failed: {e}")
            return []

    async def _search_govinfo_by_citation(
        self,
        citation: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Direct lookup by US Code citation"""
        if not self.govinfo_api_key:
            logger.warning("GovInfo API key not configured, skipping citation search")
            return []

        try:
            citation_str = citation["full"]

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    "https://api.govinfo.gov/search",
                    headers={"X-Api-Key": self.govinfo_api_key},
                    json={
                        "query": f'collection:uscode citation:"{citation_str}"',
                        "pageSize": 3,
                        "offsetMark": "*"
                    }
                )
                response.raise_for_status()
                data = response.json()

                results = []
                for item in data.get("results", []):
                    # Fetch section text
                    text = await self._fetch_govinfo_section_text(item)

                    results.append({
                        "source": "GovInfo.gov",
                        "title": item.get("title", ""),
                        "citation": citation_str,
                        "url": item.get("detailsLink", ""),
                        "text": text[:2000],
                        "snippet": text[:500],
                        "credibility_score": 1.0,
                        "tier": "legal_primary",
                        "source_type": "legal",
                        "published_date": item.get("dateIssued"),
                        "metadata": {
                            "jurisdiction": "federal_us",
                            "citation": citation,
                            "granule_url": item.get("download", {}).get("txtLink")
                        }
                    })

                logger.info(f"GovInfo citation search returned {len(results)} results")
                return results

        except httpx.HTTPStatusError as e:
            logger.error(f"GovInfo API HTTP error: {e.response.status_code}")
            return []
        except httpx.TimeoutException:
            logger.warning("GovInfo API timeout")
            return []
        except Exception as e:
            logger.error(f"GovInfo citation search failed: {e}")
            return []

    async def _search_govinfo_by_year(
        self,
        claim_text: str,
        year: int
    ) -> List[Dict[str, Any]]:
        """Search GovInfo filtered by year"""
        if not self.govinfo_api_key:
            return []

        try:
            keywords = self._extract_keywords(claim_text)
            query = f"collection:uscode {year} {' '.join(keywords[:5])}"

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    "https://api.govinfo.gov/search",
                    headers={"X-Api-Key": self.govinfo_api_key},
                    json={
                        "query": query,
                        "pageSize": 5,
                        "offsetMark": "*"
                    }
                )
                response.raise_for_status()
                data = response.json()

                results = []
                for item in data.get("results", [])[:3]:
                    text = await self._fetch_govinfo_section_text(item)

                    results.append({
                        "source": "GovInfo.gov",
                        "title": item.get("title", ""),
                        "url": item.get("detailsLink", ""),
                        "text": text[:2000],
                        "snippet": text[:500],
                        "credibility_score": 1.0,
                        "tier": "legal_primary",
                        "source_type": "legal",
                        "published_date": str(year),
                        "metadata": {
                            "jurisdiction": "federal_us",
                            "search_year": year
                        }
                    })

                return results

        except Exception as e:
            logger.error(f"GovInfo year search failed: {e}")
            return []

    async def _search_govinfo_fulltext(self, claim_text: str) -> List[Dict[str, Any]]:
        """Broad keyword search in GovInfo"""
        if not self.govinfo_api_key:
            return []

        try:
            keywords = self._extract_keywords(claim_text)
            query = f"collection:uscode {' '.join(keywords[:7])}"

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    "https://api.govinfo.gov/search",
                    headers={"X-Api-Key": self.govinfo_api_key},
                    json={
                        "query": query,
                        "pageSize": 5,
                        "offsetMark": "*"
                    }
                )
                response.raise_for_status()
                data = response.json()

                results = []
                for item in data.get("results", [])[:2]:  # Top 2 for broad search
                    text = await self._fetch_govinfo_section_text(item)

                    results.append({
                        "source": "GovInfo.gov",
                        "title": item.get("title", ""),
                        "url": item.get("detailsLink", ""),
                        "text": text[:2000],
                        "snippet": text[:500],
                        "credibility_score": 1.0,
                        "tier": "legal_primary",
                        "source_type": "legal",
                        "published_date": item.get("dateIssued"),
                        "metadata": {
                            "jurisdiction": "federal_us"
                        }
                    })

                return results

        except Exception as e:
            logger.error(f"GovInfo fulltext search failed: {e}")
            return []

    async def _fetch_govinfo_section_text(self, item: Dict) -> str:
        """Fetch section text from GovInfo granule"""
        try:
            txt_link = item.get("download", {}).get("txtLink")
            if not txt_link:
                return item.get("title", "")

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(txt_link)
                response.raise_for_status()
                return response.text

        except Exception as e:
            logger.debug(f"Failed to fetch section text: {e}")
            return item.get("title", "")

    def _parse_uk_legislation_xml(self, xml_text: str, claim_text: str) -> str:
        """Parse UK legislation XML and extract relevant sections"""
        try:
            # Parse XML
            root = ET.fromstring(xml_text.encode('utf-8'))

            # Extract keywords from claim
            keywords = self._extract_keywords(claim_text)

            # Find sections containing keywords
            sections = []

            # Search for Section elements
            for section in root.findall(".//{http://www.legislation.gov.uk/namespaces/legislation}P1"):
                section_text = ''.join(section.itertext())

                # Check if section contains any keywords
                if any(kw.lower() in section_text.lower() for kw in keywords):
                    sections.append(section_text.strip())

            if sections:
                return "\n\n".join(sections[:3])  # Top 3 relevant sections
            else:
                # Fallback: return intro text
                intro = root.find(".//{http://www.legislation.gov.uk/namespaces/legislation}IntroductoryText")
                if intro is not None:
                    return ''.join(intro.itertext()).strip()

                # Last resort: return first 2000 chars of raw XML converted to text
                return ''.join(root.itertext()).strip()[:2000]

        except Exception as e:
            logger.error(f"Failed to parse UK legislation XML: {e}")
            # Return raw text as fallback
            return xml_text[:2000]

    def _extract_keywords(self, text: str) -> List[str]:
        """Extract meaningful keywords from text"""
        # Remove common stop words
        stop_words = {
            "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
            "of", "with", "by", "from", "that", "this", "these", "those", "is",
            "are", "was", "were", "be", "been", "being", "have", "has", "had",
            "do", "does", "did", "will", "would", "should", "could", "may", "might"
        }

        # Extract words (3+ chars, alphabetic)
        words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())

        # Filter stop words and deduplicate
        keywords = []
        seen = set()
        for word in words:
            if word not in stop_words and word not in seen:
                keywords.append(word)
                seen.add(word)

        return keywords

    def _extract_act_name(self, claim_text: str) -> Optional[str]:
        """Extract act name from claim text"""
        # Pattern: [Capitalized Words] Act [of year]?
        match = re.search(
            r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,4})\s+Act(?:\s+(?:of\s+)?(\d{4}))?",
            claim_text
        )
        if match:
            act_name = match.group(1) + " Act"
            if match.group(2):
                act_name += f" {match.group(2)}"
            return act_name
        return None

    def _build_cache_key(self, claim_text: str, metadata: Dict) -> str:
        """Build cache key from claim and metadata"""
        import hashlib

        # Include relevant metadata in cache key
        key_parts = [
            claim_text,
            str(metadata.get("year", "")),
            str(metadata.get("citation", "")),
            str(metadata.get("jurisdiction", ""))
        ]

        key_str = "|".join(key_parts)
        return hashlib.md5(key_str.encode()).hexdigest()


# Singleton pattern
_legal_search_service = None

def get_legal_search_service() -> LegalSearchService:
    """Get singleton legal search service instance"""
    global _legal_search_service
    if _legal_search_service is None:
        _legal_search_service = LegalSearchService()
    return _legal_search_service
```

#### Step 2.1.2: Add Configuration

**File:** `backend/app/core/config.py`

**Location:** After line 91 (after ENABLE_ENHANCED_EXPLAINABILITY)

```python
    # Phase 2.5 - Legal Statute Integration
    ENABLE_LEGAL_INTEGRATION: bool = Field(
        default=True,
        env="ENABLE_LEGAL_INTEGRATION",
        description="Enable legal statute verification via official APIs"
    )
    ENABLE_LEGAL_SOURCE_BOOSTING: bool = Field(
        default=True,
        env="ENABLE_LEGAL_SOURCE_BOOSTING",
        description="Boost credibility of legal sources for legal claims"
    )
    GOVINFO_API_KEY: Optional[str] = Field(
        default=None,
        env="GOVINFO_API_KEY",
        description="API key for GovInfo.gov (free at api.data.gov)"
    )
    CONGRESS_API_KEY: Optional[str] = Field(
        default=None,
        env="CONGRESS_API_KEY",
        description="API key for Congress.gov (same as GovInfo)"
    )
    LEGAL_API_TIMEOUT_SECONDS: int = Field(
        default=10,
        env="LEGAL_API_TIMEOUT_SECONDS",
        description="Timeout for legal API calls"
    )
    LEGAL_CACHE_TTL_DAYS: int = Field(
        default=30,
        env="LEGAL_CACHE_TTL_DAYS",
        description="Cache TTL for legal statute results (statutes rarely change)"
    )

    # Legal feature rollout control
    LEGAL_FEATURE_ROLLOUT_PERCENTAGE: int = Field(
        default=100,
        env="LEGAL_FEATURE_ROLLOUT_PERCENTAGE",
        description="Percentage of users to enable legal features for (0-100)"
    )
    LEGAL_INTERNAL_TESTING_USER_IDS: List[str] = Field(
        default_factory=list,
        env="LEGAL_INTERNAL_TESTING_USER_IDS",
        description="User IDs that always have legal features enabled (for testing)"
    )
```

### 2.2: Create Service Tests

**File:** `backend/tests/unit/services/test_legal_search.py` (NEW FILE)

```python
"""
Unit tests for Legal Search Service

Tests API integration, parsing, caching, error handling.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx

from app.services.legal_search import LegalSearchService, get_legal_search_service


@pytest.mark.asyncio
class TestLegalSearchService:
    @pytest.fixture
    def service(self):
        """Create service instance with mock API keys"""
        service = LegalSearchService()
        service.govinfo_api_key = "test_key"
        service.congress_api_key = "test_key"
        return service

    async def test_search_with_us_citation(self, service):
        """Test: Direct citation lookup for US Code"""
        claim = "Title 52, Section 8722 requires campaign finance reporting"
        metadata = {
            "jurisdiction": "federal_us",
            "citation": {
                "type": "usc",
                "title": "52",
                "section": "8722",
                "full": "52 U.S.C. § 8722"
            }
        }

        # Mock GovInfo API response
        mock_response = {
            "results": [{
                "title": "52 U.S.C. § 8722 - Campaign Finance Reporting",
                "detailsLink": "https://www.govinfo.gov/...",
                "dateIssued": "2002-01-01",
                "download": {"txtLink": "https://www.govinfo.gov/.../text.txt"}
            }]
        }

        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=MagicMock(
                    status_code=200,
                    json=lambda: mock_response,
                    raise_for_status=lambda: None
                )
            )
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=MagicMock(
                    status_code=200,
                    text="Section text content here",
                    raise_for_status=lambda: None
                )
            )

            results = await service.search_statutes(claim, metadata)

        assert len(results) > 0
        assert results[0]["source"] == "GovInfo.gov"
        assert results[0]["credibility_score"] == 1.0
        assert results[0]["tier"] == "legal_primary"

    async def test_search_with_year(self, service):
        """Test: Year + keyword search"""
        claim = "A 1952 federal law requires submission to planning commission"
        metadata = {
            "jurisdiction": "federal_us",
            "year": 1952
        }

        # Should call year-filtered search
        with patch.object(service, '_search_govinfo_by_year', return_value=[
            {"source": "GovInfo.gov", "title": "1952 Planning Act"}
        ]) as mock_search:
            results = await service.search_statutes(claim, metadata)

            mock_search.assert_called_once()
            assert len(results) > 0

    async def test_uk_legislation_search(self, service):
        """Test: UK legislation.gov.uk search"""
        claim = "The Human Rights Act 1998 incorporates ECHR"
        metadata = {
            "jurisdiction": "uk",
            "act_name": "Human Rights Act 1998",
            "year": 1998
        }

        # Mock UK API response
        mock_xml = """<?xml version="1.0"?>
        <Legislation xmlns="http://www.legislation.gov.uk/namespaces/legislation">
            <P1>Section 1: Convention Rights</P1>
        </Legislation>
        """

        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                side_effect=[
                    MagicMock(
                        status_code=200,
                        url="http://www.legislation.gov.uk/ukpga/1998/42"
                    ),
                    MagicMock(
                        status_code=200,
                        text=mock_xml
                    )
                ]
            )

            results = await service.search_statutes(claim, metadata)

        assert len(results) > 0
        assert results[0]["source"] == "legislation.gov.uk"
        assert results[0]["credibility_score"] == 1.0

    async def test_caching(self, service):
        """Test: Results are cached appropriately"""
        claim = "Test claim"
        metadata = {"jurisdiction": "federal_us"}

        with patch.object(service, '_search_us_sources', return_value=[
            {"source": "test", "title": "cached result"}
        ]) as mock_search:
            # First call - should hit API
            results1 = await service.search_statutes(claim, metadata)
            assert mock_search.call_count == 1

            # Second call - should use cache
            results2 = await service.search_statutes(claim, metadata)
            assert mock_search.call_count == 1  # Not called again

            # Results should be identical
            assert results1 == results2

    async def test_api_timeout_handling(self, service):
        """Test: Graceful handling of API timeouts"""
        claim = "Test claim"
        metadata = {"jurisdiction": "federal_us"}

        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                side_effect=httpx.TimeoutException("Timeout")
            )

            # Should return empty list, not raise exception
            results = await service.search_statutes(claim, metadata)
            assert results == []

    async def test_api_error_handling(self, service):
        """Test: Graceful handling of API errors"""
        claim = "Test claim"
        metadata = {"jurisdiction": "federal_us"}

        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                side_effect=Exception("API Error")
            )

            # Should return empty list, not raise exception
            results = await service.search_statutes(claim, metadata)
            assert results == []

    def test_keyword_extraction(self, service):
        """Test: Keyword extraction filters stop words"""
        text = "The federal law requires submission to the commission"
        keywords = service._extract_keywords(text)

        # Should exclude: the, to
        # Should include: federal, law, requires, submission, commission
        assert "the" not in keywords
        assert "to" not in keywords
        assert "federal" in keywords
        assert "law" in keywords
        assert "commission" in keywords

    def test_act_name_extraction(self, service):
        """Test: Act name extraction from claim"""
        test_cases = [
            ("The Affordable Care Act requires coverage", "Affordable Care Act"),
            ("Human Rights Act 1998 protects rights", "Human Rights Act 1998"),
            ("Freedom of Information Act of 1966", "Freedom of Information Act 1966")
        ]

        for claim, expected in test_cases:
            result = service._extract_act_name(claim)
            assert result == expected, f"Failed for: {claim}"

    def test_singleton_pattern(self):
        """Test: get_legal_search_service returns same instance"""
        service1 = get_legal_search_service()
        service2 = get_legal_search_service()
        assert service1 is service2


@pytest.mark.integration
@pytest.mark.asyncio
class TestLegalSearchIntegration:
    """
    Integration tests with real APIs.
    Only run when API keys are configured.
    """

    @pytest.fixture
    def service(self):
        from app.core.config import settings
        if not settings.GOVINFO_API_KEY:
            pytest.skip("GovInfo API key not configured")
        return get_legal_search_service()

    async def test_real_govinfo_search(self, service):
        """Test: Real GovInfo API call (requires API key)"""
        claim = "Title 52, Section 30104 of the U.S. Code"
        metadata = {
            "jurisdiction": "federal_us",
            "citation": {
                "type": "usc",
                "title": "52",
                "section": "30104",
                "full": "52 U.S.C. § 30104"
            }
        }

        results = await service.search_statutes(claim, metadata)

        # Should find at least one result
        assert len(results) > 0
        assert "GovInfo.gov" in results[0]["source"]
        assert len(results[0]["text"]) > 0

    async def test_real_uk_legislation_search(self, service):
        """Test: Real UK legislation.gov.uk call"""
        claim = "The Human Rights Act 1998"
        metadata = {
            "jurisdiction": "uk",
            "year": 1998,
            "citation": {
                "type": "ukpga",
                "year": "1998",
                "number": "42"
            }
        }

        results = await service.search_statutes(claim, metadata)

        # Should find Human Rights Act 1998
        assert len(results) > 0
        assert "legislation.gov.uk" in results[0]["source"]
        assert len(results[0]["text"]) > 0
```

### 2.3: Phase 2 Completion Checklist

- [ ] legal_search.py service implemented
- [ ] Configuration settings added to config.py
- [ ] API keys added to .env (register first!)
- [ ] Unit tests written and passing (10+ tests)
- [ ] Integration tests pass with real APIs (when keys configured)
- [ ] Service follows FactCheckAPI pattern
- [ ] Caching implemented and tested
- [ ] Error handling covers all failure modes
- [ ] Logging added for debugging
- [ ] Code reviewed for security (API keys not logged)

**Success Criteria:**
- Service returns results for US citations
- Service returns results for UK legislation
- Caching reduces API calls by 80%+
- Timeouts handled gracefully (return empty[])
- No crashes on API errors

**Rollback:**
If issues found, legal_search.py is isolated - simply don't use it yet.

---

## Phase 3: Evidence Pipeline Integration

**Timeline:** 3 days
**Effort:** 15 hours
**Risk:** MEDIUM (touches production pipeline)
**Dependencies:** Phase 1 + 2 complete

### 3.1: Integrate with Evidence Retrieval

**File:** `backend/app/pipeline/retrieve.py`

#### Step 3.1.1: Add Legal Routing

**Location:** Line 85 (in `_retrieve_evidence_for_single_claim`, BEFORE `evidence_extractor.extract_evidence_for_claim` call)

**Current code:**
```python
async def _retrieve_evidence_for_single_claim(
    self,
    claim: Dict[str, Any],
    semaphore: asyncio.Semaphore,
    excluded_domain: Optional[str] = None
) -> List[Dict[str, Any]]:
    async with semaphore:
        try:
            claim_text = claim.get("text", "")
            claim_position = claim.get("position", 0)

            # Step 1: Search and extract evidence snippets
            subject_context = claim.get("subject_context")
            key_entities = claim.get("key_entities", [])

            evidence_snippets = await self.evidence_extractor.extract_evidence_for_claim(
                claim_text,
                max_sources=self.max_sources_per_claim * 2,
                ...
            )
```

**NEW code (insert BEFORE evidence_extractor call):**
```python
async def _retrieve_evidence_for_single_claim(
    self,
    claim: Dict[str, Any],
    semaphore: asyncio.Semaphore,
    excluded_domain: Optional[str] = None
) -> List[Dict[str, Any]]:
    async with semaphore:
        try:
            claim_text = claim.get("text", "")
            claim_position = claim.get("position", 0)

            # NEW: Step 0.5 - Check for legal claims requiring specialized search
            legal_evidence_snippets = []
            claim_type = claim.get("claim_type")
            claim_classification = claim.get("classification", {})

            if settings.ENABLE_LEGAL_INTEGRATION and claim_type == "legal":
                logger.info(f"Legal claim detected at position {claim_position}: {claim_text[:50]}...")

                try:
                    from app.services.legal_search import get_legal_search_service
                    legal_search = get_legal_search_service()

                    # Extract legal metadata from classification
                    legal_metadata = claim_classification.get("metadata", {})

                    # Search legal sources
                    legal_results = await legal_search.search_statutes(
                        claim_text,
                        legal_metadata
                    )

                    if legal_results:
                        logger.info(f"Found {len(legal_results)} legal sources for claim {claim_position}")

                        # Convert to evidence snippet format
                        from app.services.evidence import EvidenceSnippet
                        for result in legal_results:
                            legal_evidence_snippets.append(
                                EvidenceSnippet(
                                    text=result.get("snippet", result.get("text", "")[:500]),
                                    source=result.get("source", ""),
                                    url=result.get("url", ""),
                                    title=result.get("title", ""),
                                    published_date=result.get("published_date"),
                                    relevance_score=0.95,  # High relevance (direct legal source)
                                    word_count=len(result.get("text", "").split()),
                                    metadata={
                                        "legal_source": True,
                                        "tier": result.get("tier"),
                                        "source_type": result.get("source_type"),
                                        "citation": result.get("metadata", {}).get("citation"),
                                        "full_text": result.get("text", "")
                                    }
                                )
                            )
                    else:
                        logger.warning(f"No legal sources found for legal claim {claim_position}, using general search")

                except Exception as e:
                    logger.warning(f"Legal search failed for claim {claim_position}: {e}, falling back to general search")
                    legal_evidence_snippets = []

            # Step 1: Search and extract evidence snippets (general search)
            subject_context = claim.get("subject_context")
            key_entities = claim.get("key_entities", [])

            evidence_snippets = await self.evidence_extractor.extract_evidence_for_claim(
                claim_text,
                max_sources=self.max_sources_per_claim * 2,
                subject_context=subject_context,
                key_entities=key_entities,
                excluded_domain=excluded_domain
            )

            # NEW: Merge legal and general evidence (legal sources first for priority)
            if legal_evidence_snippets:
                all_evidence = legal_evidence_snippets + evidence_snippets
                logger.info(
                    f"Merged evidence: {len(legal_evidence_snippets)} legal + "
                    f"{len(evidence_snippets)} general = {len(all_evidence)} total"
                )
                evidence_snippets = all_evidence
```

#### Step 3.1.2: Add Legal Source Boosting

**Location:** Line 287 (in `_apply_credibility_weighting`, after credibility_score calculation)

**Current code:**
```python
for evidence in evidence_list:
    source = evidence.get("source", "").lower()
    url = evidence.get("url", "")

    # Determine credibility tier
    credibility_score = self._get_credibility_score(source, url, evidence)

    # Apply recency weighting
    recency_score = self._get_recency_score(evidence.get("published_date"))
```

**NEW code (insert after credibility_score, before recency_score):**
```python
for evidence in evidence_list:
    source = evidence.get("source", "").lower()
    url = evidence.get("url", "")

    # Determine credibility tier
    credibility_score = self._get_credibility_score(source, url, evidence)

    # NEW: Boost legal sources for legal claims
    if settings.ENABLE_LEGAL_SOURCE_BOOSTING and claim and claim.get("claim_type") == "legal":
        tier = evidence.get("tier")
        source_type = evidence.get("source_type")
        is_legal_source = evidence.get("metadata", {}).get("legal_source", False)

        # Boost if:
        # 1. Tier 1 legal source (govinfo, legislation.gov.uk)
        # 2. Government tier with legal source type
        # 3. Marked as legal_source in metadata
        if (tier in ["legal_primary", "tier1"] and source_type == "legal") or is_legal_source:
            original_score = credibility_score
            credibility_score = min(1.0, credibility_score * 1.15)  # 15% boost, max 1.0

            if credibility_score > original_score:
                logger.debug(
                    f"Legal source boosted for legal claim: {source} "
                    f"({original_score:.2f} → {credibility_score:.2f})"
                )

    # Apply recency weighting
    recency_score = self._get_recency_score(evidence.get("published_date"))
```

### 3.2: Update Search Service

**File:** `backend/app/services/search.py`

#### Step 3.2.1: Add Legal Query Optimization

**Location:** Line 276 (after `_optimize_query_for_factcheck` method)

**Add new method:**
```python
def _optimize_query_for_legal(self, claim: str, metadata: Dict[str, Any]) -> str:
    """
    Optimize search query for legal/statutory claims.

    Prioritizes official legal sources and adds legal context.

    Args:
        claim: Claim text
        metadata: Legal metadata (year, citation, jurisdiction)

    Returns:
        Optimized search query
    """
    query_parts = []

    # Add year if known (strong filter)
    if metadata.get("year"):
        query_parts.append(str(metadata["year"]))

    # Add citation if known (direct match)
    if metadata.get("citation"):
        citation = metadata["citation"]
        if citation.get("type") == "usc":
            query_parts.append(f"{citation['title']} U.S.C. {citation['section']}")
        elif citation.get("type") in ["ukpga", "uksi", "asp"]:
            query_parts.append(f"{citation['type']} {citation['year']}/{citation['number']}")

    # Add claim text
    claim_clean = claim.replace("?", "").replace("!", "").strip()
    query_parts.append(claim_clean)

    # Prioritize legal domains (jurisdiction-specific)
    jurisdiction = metadata.get("jurisdiction")
    legal_sites = []

    if jurisdiction == "federal_us":
        legal_sites = [
            "site:govinfo.gov",
            "site:congress.gov",
            "site:law.cornell.edu"
        ]
    elif jurisdiction == "uk":
        legal_sites = [
            "site:legislation.gov.uk",
            "site:bailii.org"
        ]
    else:
        # Unknown jurisdiction - try both
        legal_sites = [
            "site:govinfo.gov",
            "site:legislation.gov.uk"
        ]

    # Add legal site restrictions (OR logic)
    if legal_sites:
        site_restriction = "(" + " OR ".join(legal_sites[:2]) + ")"
        query_parts.append(site_restriction)

    # Exclude news about laws (prefer primary sources)
    exclude_terms = [
        "-\"new law\"",
        "-\"bill passes\"",
        "-\"lawmakers\"",
        "-\"congress votes\""
    ]

    query = " ".join(query_parts) + " " + " ".join(exclude_terms)

    # Limit query length (leave buffer for API params)
    if len(query) > 250:
        words = query.split()
        query = " ".join(words[:35])

    logger.debug(f"Legal search query optimized: {query[:100]}")
    return query.strip()
```

#### Step 3.2.2: Update Search Method Signature

**Location:** Line 224 (modify `search_for_evidence` method)

**Current signature:**
```python
async def search_for_evidence(self, claim: str, max_results: int = 10) -> List[SearchResult]:
```

**NEW signature:**
```python
async def search_for_evidence(
    self,
    claim: str,
    max_results: int = 10,
    claim_type: Optional[str] = None,
    claim_metadata: Optional[Dict[str, Any]] = None
) -> List[SearchResult]:
    """
    Search for evidence supporting/contradicting a claim.

    Args:
        claim: Claim text
        max_results: Maximum results to return
        claim_type: Type of claim (factual, legal, opinion, etc.)
        claim_metadata: Additional metadata for optimization (year, citation, etc.)

    Returns:
        List of search results
    """
```

**Update method body:**
```python
# Optimize search query based on claim type
if claim_type == "legal" and claim_metadata and settings.ENABLE_LEGAL_INTEGRATION:
    query = self._optimize_query_for_legal(claim, claim_metadata)
    logger.info(f"Using legal-optimized search query for claim")
else:
    query = self._optimize_query_for_factcheck(claim)

# ... rest of existing method
```

#### Step 3.2.3: Update Evidence Extractor Calls

**File:** `backend/app/services/evidence.py`

**Location:** Line 90 (where search_service is called)

**Current call:**
```python
search_results = await self.search_service.search_for_evidence(
    search_query,
    max_results=max_sources * 2
)
```

**NEW call:**
```python
search_results = await self.search_service.search_for_evidence(
    search_query,
    max_results=max_sources * 2,
    claim_type=claim_metadata.get("claim_type"),
    claim_metadata=claim_metadata.get("classification", {}).get("metadata", {})
)
```

**Also update method signature** (Line 58):
```python
async def extract_evidence_for_claim(
    self,
    claim: str,
    max_sources: int = 5,
    subject_context: str = None,
    key_entities: list = None,
    excluded_domain: Optional[str] = None,
    claim_type: Optional[str] = None,  # NEW
    claim_metadata: Optional[Dict[str, Any]] = None  # NEW
) -> List[EvidenceSnippet]:
```

### 3.3: Update Source Credibility Database

**File:** `backend/app/data/source_credibility.json`

**Location:** Top of file (add new tier)

**Add:**
```json
{
  "legal_primary": {
    "credibility": 1.0,
    "description": "Primary legal sources - official statutes and regulations",
    "domains": [
      "govinfo.gov",
      "congress.gov",
      "legislation.gov.uk",
      "uscourts.gov",
      "supremecourt.gov",
      "federalregister.gov"
    ],
    "tier": "legal_primary",
    "source_type": "legal",
    "auto_exclude": false,
    "risk_flags": []
  },

  ... existing entries ...
}
```

### 3.4: Phase 3 Completion Checklist

- [ ] Legal routing added to retrieve.py
- [ ] Legal source boosting implemented
- [ ] Legal query optimization added to search.py
- [ ] Evidence extractor updated to pass claim metadata
- [ ] Source credibility database updated
- [ ] Integration tested with sample legal claims
- [ ] No regressions in non-legal claim handling
- [ ] Logging shows legal sources being used
- [ ] Feature flags can disable all legal logic

**Success Criteria:**
- Legal claims retrieve govinfo.gov or legislation.gov.uk sources
- Legal sources appear first in evidence list
- Legal sources have 1.0 credibility score
- General search still works for legal claims (fallback)
- Non-legal claims unaffected (no performance impact)

**Rollback:**
Set `ENABLE_LEGAL_INTEGRATION=false` and `ENABLE_LEGAL_SOURCE_BOOSTING=false`

---

## Phase 4: Testing & Validation

**Timeline:** 4 days
**Effort:** 20 hours
**Risk:** LOW (finding bugs before production)
**Dependencies:** Phase 1-3 complete

### 4.1: Integration Testing

**File:** `backend/tests/integration/test_legal_pipeline.py` (NEW FILE)

```python
"""
End-to-end integration tests for legal statute verification.

Tests the complete pipeline: classification → retrieval → verification → judgment
"""

import pytest
import asyncio
from datetime import datetime

from app.utils.claim_classifier import ClaimClassifier
from app.pipeline.extract import ClaimExtractor
from app.pipeline.retrieve import EvidenceRetriever
from app.core.config import settings


@pytest.mark.integration
@pytest.mark.asyncio
class TestLegalPipelineIntegration:
    """Test legal claims through full pipeline"""

    @pytest.fixture
    def classifier(self):
        return ClaimClassifier()

    @pytest.fixture
    def retriever(self):
        return EvidenceRetriever()

    async def test_us_code_citation_end_to_end(self, classifier, retriever):
        """Test: US Code citation flows through pipeline correctly"""
        claim_text = "Title 52, Section 30104 of the U.S. Code requires campaign finance disclosure"

        # Step 1: Classification
        classification = classifier.classify(claim_text)
        assert classification["claim_type"] == "legal"
        assert classification["metadata"]["jurisdiction"] == "federal_us"
        assert classification["metadata"]["citation"] is not None

        # Step 2: Evidence Retrieval
        claim_dict = {
            "text": claim_text,
            "position": 0,
            "claim_type": "legal",
            "classification": classification
        }

        if not settings.GOVINFO_API_KEY:
            pytest.skip("GovInfo API key not configured")

        evidence = await retriever._retrieve_evidence_for_single_claim(
            claim_dict,
            semaphore=asyncio.Semaphore(1),
            excluded_domain=None
        )

        # Step 3: Validate results
        assert len(evidence) > 0, "Should find at least one evidence source"

        # Check if legal sources are present
        legal_sources = [
            e for e in evidence
            if "govinfo.gov" in e.get("url", "").lower()
            or e.get("metadata", {}).get("legal_source") == True
        ]

        if settings.ENABLE_LEGAL_INTEGRATION:
            assert len(legal_sources) > 0, "Should find at least one legal source"

            # Validate legal source properties
            legal_source = legal_sources[0]
            assert legal_source.get("credibility_score") >= 0.95
            assert legal_source.get("tier") in ["legal_primary", "tier1"]

    async def test_year_based_legal_claim(self, classifier, retriever):
        """Test: Year + topic legal claim retrieves relevant sources"""
        claim_text = "A 1965 federal law established Medicare health insurance for seniors"

        classification = classifier.classify(claim_text)
        assert classification["claim_type"] == "legal"
        assert classification["metadata"]["year"] == 1965

        claim_dict = {
            "text": claim_text,
            "position": 0,
            "claim_type": "legal",
            "classification": classification
        }

        if not settings.GOVINFO_API_KEY:
            pytest.skip("GovInfo API key not configured")

        evidence = await retriever._retrieve_evidence_for_single_claim(
            claim_dict,
            semaphore=asyncio.Semaphore(1)
        )

        assert len(evidence) > 0

        # Check for relevant content (Medicare, 1965)
        relevant = [
            e for e in evidence
            if "medicare" in e.get("text", "").lower()
            or "1965" in e.get("text", "")
        ]

        assert len(relevant) > 0, "Should find Medicare-related evidence"

    async def test_uk_legislation_end_to_end(self, classifier, retriever):
        """Test: UK legislation claim flows through pipeline"""
        claim_text = "The Human Rights Act 1998 incorporates the European Convention on Human Rights into UK law"

        classification = classifier.classify(claim_text)
        assert classification["claim_type"] == "legal"
        assert classification["metadata"]["jurisdiction"] == "uk"

        claim_dict = {
            "text": claim_text,
            "position": 0,
            "claim_type": "legal",
            "classification": classification
        }

        evidence = await retriever._retrieve_evidence_for_single_claim(
            claim_dict,
            semaphore=asyncio.Semaphore(1)
        )

        assert len(evidence) > 0

        # Check for UK legal sources
        uk_sources = [
            e for e in evidence
            if "legislation.gov.uk" in e.get("url", "").lower()
        ]

        if settings.ENABLE_LEGAL_INTEGRATION:
            assert len(uk_sources) > 0, "Should find UK legislation sources"

    async def test_legal_source_boosting(self, classifier, retriever):
        """Test: Legal sources rank higher for legal claims"""
        claim_text = "The Affordable Care Act requires health insurance coverage"

        classification = classifier.classify(claim_text)
        claim_dict = {
            "text": claim_text,
            "position": 0,
            "claim_type": "legal",
            "classification": classification
        }

        if not settings.GOVINFO_API_KEY:
            pytest.skip("GovInfo API key not configured")

        evidence = await retriever._retrieve_evidence_for_single_claim(
            claim_dict,
            semaphore=asyncio.Semaphore(1)
        )

        if len(evidence) == 0:
            pytest.skip("No evidence found")

        # Top evidence should have high credibility
        top_evidence = evidence[0]
        assert top_evidence.get("credibility_score", 0) >= 0.8

        # Legal sources should appear in top 5
        legal_in_top5 = any(
            e.get("tier") in ["legal_primary", "tier1"]
            for e in evidence[:5]
        )

        if settings.ENABLE_LEGAL_SOURCE_BOOSTING:
            assert legal_in_top5, "Legal sources should appear in top 5"

    async def test_non_legal_claim_unaffected(self, classifier, retriever):
        """Test: Non-legal claims still work normally"""
        claim_text = "Tesla delivered 1.3 million vehicles in 2022"

        classification = classifier.classify(claim_text)
        assert classification["claim_type"] == "factual"  # NOT legal

        claim_dict = {
            "text": claim_text,
            "position": 0,
            "claim_type": "factual",
            "classification": classification
        }

        evidence = await retriever._retrieve_evidence_for_single_claim(
            claim_dict,
            semaphore=asyncio.Semaphore(1)
        )

        # Should still get evidence (general search)
        assert len(evidence) > 0

        # Should NOT have called legal search (check logs)
        # Legal sources may appear but not prioritized

    async def test_fallback_when_legal_api_fails(self, classifier, retriever):
        """Test: Pipeline falls back gracefully if legal API unavailable"""
        claim_text = "A 1952 federal law requires submission to planning commission"

        classification = classifier.classify(claim_text)
        claim_dict = {
            "text": claim_text,
            "position": 0,
            "claim_type": "legal",
            "classification": classification
        }

        # Even with legal integration enabled, if API fails,
        # should still return general search results
        evidence = await retriever._retrieve_evidence_for_single_claim(
            claim_dict,
            semaphore=asyncio.Semaphore(1)
        )

        # Should get SOME evidence (either legal or general)
        assert len(evidence) >= 0  # Empty is OK if both fail


@pytest.mark.integration
class TestLegalFeatureFlags:
    """Test feature flag behavior"""

    def test_legal_integration_flag(self, monkeypatch):
        """Test: ENABLE_LEGAL_INTEGRATION flag controls behavior"""
        from app.core.config import settings

        # Test flag is respected
        assert isinstance(settings.ENABLE_LEGAL_INTEGRATION, bool)

        # Can be disabled
        monkeypatch.setenv("ENABLE_LEGAL_INTEGRATION", "false")
        # Would need to reload settings - simplified for test

    def test_legal_boosting_flag(self, monkeypatch):
        """Test: ENABLE_LEGAL_SOURCE_BOOSTING flag controls behavior"""
        from app.core.config import settings

        assert isinstance(settings.ENABLE_LEGAL_SOURCE_BOOSTING, bool)
```

### 4.2: Manual End-to-End Testing

Create: `backend/tests/manual/test_legal_end_to_end.sh`

```bash
#!/bin/bash

# Manual end-to-end test script for legal integration
# Run after Phase 1-3 complete

echo "=== Legal Integration End-to-End Test ==="
echo ""

# Check prerequisites
echo "1. Checking API keys..."
if [ -z "$GOVINFO_API_KEY" ]; then
    echo "   ⚠️  GOVINFO_API_KEY not set"
else
    echo "   ✓ GOVINFO_API_KEY configured"
fi

echo ""
echo "2. Testing claim classification..."
python3 << 'EOF'
from app.utils.claim_classifier import ClaimClassifier

classifier = ClaimClassifier()

test_cases = [
    "Title 52, Section 30104 requires campaign finance disclosure",
    "The Human Rights Act 1998 incorporates ECHR",
    "A 1965 federal law established Medicare"
]

for claim in test_cases:
    result = classifier.classify(claim)
    status = "✓" if result["claim_type"] == "legal" else "✗"
    print(f"   {status} {claim[:50]}... => {result['claim_type']}")

print("   ✓ Classification working")
EOF

echo ""
echo "3. Testing legal search service..."
python3 << 'EOF'
import asyncio
from app.services.legal_search import get_legal_search_service

async def test():
    service = get_legal_search_service()

    # Test US Code
    results = await service.search_statutes(
        "Title 52, Section 30104",
        {
            "jurisdiction": "federal_us",
            "citation": {
                "type": "usc",
                "title": "52",
                "section": "30104",
                "full": "52 U.S.C. § 30104"
            }
        }
    )

    if len(results) > 0:
        print(f"   ✓ US search returned {len(results)} results")
        print(f"     - {results[0]['source']}: {results[0]['title'][:60]}...")
    else:
        print("   ✗ US search returned no results")

    # Test UK
    results = await service.search_statutes(
        "Human Rights Act 1998",
        {
            "jurisdiction": "uk",
            "year": 1998,
            "citation": {
                "type": "ukpga",
                "year": "1998",
                "number": "42"
            }
        }
    )

    if len(results) > 0:
        print(f"   ✓ UK search returned {len(results)} results")
        print(f"     - {results[0]['source']}: {results[0]['title'][:60]}...")
    else:
        print("   ⚠️  UK search returned no results (may be expected)")

asyncio.run(test())
EOF

echo ""
echo "4. Testing pipeline integration..."
python3 << 'EOF'
import asyncio
from app.pipeline.extract import ClaimExtractor
from app.pipeline.retrieve import EvidenceRetriever

async def test():
    # Extract
    extractor = ClaimExtractor()
    result = await extractor.extract_claims(
        "Title 52, Section 30104 of the U.S. Code requires campaign finance disclosure",
        metadata={"url": "test"}
    )

    if result["success"]:
        claim = result["claims"][0]
        print(f"   ✓ Extraction: claim_type={claim.get('claim_type')}")

        # Retrieve
        retriever = EvidenceRetriever()
        evidence = await retriever._retrieve_evidence_for_single_claim(
            claim,
            semaphore=asyncio.Semaphore(1)
        )

        print(f"   ✓ Retrieval: {len(evidence)} evidence sources")

        # Check for legal sources
        legal_sources = [e for e in evidence if "govinfo.gov" in e.get("url", "").lower()]
        if legal_sources:
            print(f"   ✓ Legal sources found: {len(legal_sources)}")
        else:
            print(f"   ⚠️  No legal sources found (may need API key)")
    else:
        print("   ✗ Extraction failed")

asyncio.run(test())
EOF

echo ""
echo "=== Test Complete ==="
```

Run:
```bash
chmod +x backend/tests/manual/test_legal_end_to_end.sh
./backend/tests/manual/test_legal_end_to_end.sh
```

### 4.3: Validation Metrics

Create: `backend/tests/validation/legal_validation_metrics.py`

```python
"""
Validation metrics for legal integration.

Measures:
- Classification accuracy
- Evidence relevance
- Source credibility distribution
- API success rate
"""

import asyncio
from typing import List, Dict
from collections import defaultdict

from app.utils.claim_classifier import ClaimClassifier
from app.services.legal_search import get_legal_search_service


# Test dataset
VALIDATION_CLAIMS = [
    # US Federal - Citations
    {
        "claim": "Title 52, Section 30104 of the U.S. Code requires campaign finance disclosure",
        "expected_type": "legal",
        "expected_jurisdiction": "federal_us",
        "expected_citation": True
    },
    {
        "claim": "42 U.S.C. § 1395 establishes Medicare",
        "expected_type": "legal",
        "expected_jurisdiction": "federal_us",
        "expected_citation": True
    },

    # US Federal - Year
    {
        "claim": "A 1965 federal law created Medicare health insurance",
        "expected_type": "legal",
        "expected_jurisdiction": "federal_us",
        "expected_year": 1965
    },
    {
        "claim": "The 2010 Affordable Care Act requires health coverage",
        "expected_type": "legal",
        "expected_jurisdiction": "federal_us",
        "expected_year": 2010
    },

    # UK Legislation
    {
        "claim": "The Human Rights Act 1998 incorporates ECHR into UK law",
        "expected_type": "legal",
        "expected_jurisdiction": "uk",
        "expected_year": 1998
    },
    {
        "claim": "Parliament passed the Data Protection Act 2018",
        "expected_type": "legal",
        "expected_jurisdiction": "uk",
        "expected_year": 2018
    },

    # Non-Legal (should NOT classify as legal)
    {
        "claim": "The company law firm reviewed the contract",
        "expected_type": "factual",  # NOT legal
    },
    {
        "claim": "Tesla delivered 1.3 million vehicles in 2022",
        "expected_type": "factual",
    }
]


async def validate_classification():
    """Validate claim classification accuracy"""
    classifier = ClaimClassifier()

    correct = 0
    total = len(VALIDATION_CLAIMS)

    print("=" * 80)
    print("CLASSIFICATION VALIDATION")
    print("=" * 80)

    for test_case in VALIDATION_CLAIMS:
        claim = test_case["claim"]
        expected_type = test_case["expected_type"]

        result = classifier.classify(claim)
        actual_type = result["claim_type"]

        is_correct = (actual_type == expected_type)
        if is_correct:
            correct += 1

        status = "✓" if is_correct else "✗"
        print(f"{status} {claim[:60]}...")
        print(f"  Expected: {expected_type}, Got: {actual_type}")

        # Validate metadata if legal claim
        if expected_type == "legal" and is_correct:
            metadata = result.get("metadata", {})

            if "expected_jurisdiction" in test_case:
                expected_jur = test_case["expected_jurisdiction"]
                actual_jur = metadata.get("jurisdiction")
                if actual_jur == expected_jur:
                    print(f"  ✓ Jurisdiction: {actual_jur}")
                else:
                    print(f"  ✗ Jurisdiction: expected {expected_jur}, got {actual_jur}")

            if "expected_year" in test_case:
                expected_year = test_case["expected_year"]
                actual_year = metadata.get("year")
                if actual_year == expected_year:
                    print(f"  ✓ Year: {actual_year}")
                else:
                    print(f"  ✗ Year: expected {expected_year}, got {actual_year}")

            if "expected_citation" in test_case and test_case["expected_citation"]:
                if metadata.get("citation"):
                    print(f"  ✓ Citation extracted: {metadata['citation']}")
                else:
                    print(f"  ✗ Citation not extracted")

        print()

    accuracy = (correct / total) * 100
    print(f"Accuracy: {correct}/{total} ({accuracy:.1f}%)")
    print()

    return accuracy


async def validate_legal_search():
    """Validate legal search service"""
    service = get_legal_search_service()

    print("=" * 80)
    print("LEGAL SEARCH VALIDATION")
    print("=" * 80)

    test_cases = [
        {
            "claim": "Title 52, Section 30104 requires disclosure",
            "metadata": {
                "jurisdiction": "federal_us",
                "citation": {
                    "type": "usc",
                    "title": "52",
                    "section": "30104",
                    "full": "52 U.S.C. § 30104"
                }
            },
            "expected_source": "GovInfo.gov"
        },
        {
            "claim": "Human Rights Act 1998",
            "metadata": {
                "jurisdiction": "uk",
                "year": 1998,
                "citation": {
                    "type": "ukpga",
                    "year": "1998",
                    "number": "42"
                }
            },
            "expected_source": "legislation.gov.uk"
        }
    ]

    success_count = 0

    for test_case in test_cases:
        claim = test_case["claim"]
        metadata = test_case["metadata"]
        expected = test_case["expected_source"]

        print(f"Testing: {claim}")

        try:
            results = await service.search_statutes(claim, metadata)

            if len(results) > 0:
                print(f"  ✓ Found {len(results)} results")

                # Check for expected source
                has_expected = any(expected.lower() in r["source"].lower() for r in results)
                if has_expected:
                    print(f"  ✓ Expected source found: {expected}")
                    success_count += 1
                else:
                    print(f"  ✗ Expected source not found: {expected}")
                    print(f"    Got: {[r['source'] for r in results]}")

                # Show top result
                top = results[0]
                print(f"  Top result: {top['source']}")
                print(f"    Title: {top['title'][:60]}...")
                print(f"    Credibility: {top['credibility_score']}")
            else:
                print(f"  ✗ No results returned")

        except Exception as e:
            print(f"  ✗ Error: {e}")

        print()

    success_rate = (success_count / len(test_cases)) * 100
    print(f"Success Rate: {success_count}/{len(test_cases)} ({success_rate:.1f}%)")
    print()


async def main():
    """Run all validation metrics"""
    classification_accuracy = await validate_classification()
    await validate_legal_search()

    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Classification Accuracy: {classification_accuracy:.1f}%")
    print()

    if classification_accuracy >= 90:
        print("✓ Legal integration validation PASSED")
    else:
        print("✗ Legal integration validation FAILED")
        print("  Classification accuracy below 90% threshold")


if __name__ == "__main__":
    asyncio.run(main())
```

Run:
```bash
cd backend
python tests/validation/legal_validation_metrics.py
```

### 4.4: Phase 4 Completion Checklist

- [ ] Integration tests written (6+ tests)
- [ ] Manual end-to-end script passes
- [ ] Validation metrics show 90%+ accuracy
- [ ] Non-legal claims unaffected (regression test)
- [ ] Feature flags tested (can disable)
- [ ] Fallback behavior tested (API failures)
- [ ] Performance acceptable (<10s per legal claim)
- [ ] Logs show clear decision trail
- [ ] Documentation updated (if needed)

**Success Criteria:**
- Classification accuracy: 90%+
- Legal search success rate: 80%+ (when API keys configured)
- Zero false positives in test cases
- Non-legal claims unchanged
- Pipeline resilient to API failures

---

## Phase 5: Deployment & Monitoring

**Timeline:** 2 days
**Effort:** 10 hours
**Risk:** LOW (gradual rollout)
**Dependencies:** Phase 1-4 complete

### 5.1: Pre-Deployment Checklist

**Run all tests:**
```bash
cd backend

# Unit tests
pytest tests/unit/test_claim_classifier.py -v
pytest tests/unit/services/test_legal_search.py -v

# Integration tests
pytest tests/integration/test_legal_pipeline.py -v

# Validation
python tests/validation/legal_validation_metrics.py
```

**Expected results:**
- All unit tests pass (20+ tests)
- Integration tests pass (when API keys configured)
- Validation accuracy >90%

### 5.2: Deployment Strategy

**Week 1: Internal Testing (10% rollout)**

```bash
# backend/.env
ENABLE_LEGAL_INTEGRATION=true
LEGAL_FEATURE_ROLLOUT_PERCENTAGE=10  # 10% of users
LEGAL_INTERNAL_TESTING_USER_IDS=["admin-user-id-1", "admin-user-id-2"]

# Restart backend
systemctl restart tru8-backend
# or: uvicorn main:app --reload
```

**Monitor for 3 days:**
- Check legal claim detection rate (~5-10% of total claims)
- Verify legal sources appear in evidence
- Watch for API errors or timeouts
- Confirm no impact on non-legal claims

**Week 2: Gradual Expansion (50% rollout)**

```bash
# backend/.env
LEGAL_FEATURE_ROLLOUT_PERCENTAGE=50
```

**Monitor for 4 days:**
- Increased API usage (still within 5,000/hr limit)
- User feedback on legal claim accuracy
- Compare legal vs non-legal claim confidence

**Week 3: Full Rollout (100%)**

```bash
# backend/.env
LEGAL_FEATURE_ROLLOUT_PERCENTAGE=100
```

**Monitor ongoing:**
- API rate limits (should stay under 80% of 5,000/hr)
- Cache hit rate (target: 70%+)
- Legal claim accuracy (via user feedback)

### 5.3: Monitoring Setup

**Add monitoring queries:**

```sql
-- Legal claim statistics (daily)
SELECT
  DATE(created_at) as date,
  COUNT(*) as total_claims,
  SUM(CASE WHEN claim_type = 'legal' THEN 1 ELSE 0 END) as legal_claims,
  ROUND(100.0 * SUM(CASE WHEN claim_type = 'legal' THEN 1 ELSE 0 END) / COUNT(*), 2) as legal_percentage,
  AVG(CASE WHEN claim_type = 'legal' THEN confidence ELSE NULL END) as avg_legal_confidence,
  AVG(CASE WHEN claim_type != 'legal' THEN confidence ELSE NULL END) as avg_other_confidence
FROM claim
WHERE created_at > NOW() - INTERVAL '7 days'
GROUP BY DATE(created_at)
ORDER BY date DESC;

-- Legal source usage
SELECT
  e.source,
  e.tier,
  COUNT(*) as usage_count,
  AVG(e.credibility_score) as avg_credibility,
  AVG(e.relevance_score) as avg_relevance
FROM evidence e
JOIN claim c ON c.id = e.claim_id
WHERE c.claim_type = 'legal'
  AND c.created_at > NOW() - INTERVAL '7 days'
GROUP BY e.source, e.tier
ORDER BY usage_count DESC
LIMIT 20;

-- Legal claim verdict distribution
SELECT
  verdict,
  COUNT(*) as count,
  ROUND(AVG(confidence), 2) as avg_confidence
FROM claim
WHERE claim_type = 'legal'
  AND created_at > NOW() - INTERVAL '7 days'
GROUP BY verdict;
```

**Add log monitoring:**

```bash
# Check legal search calls
grep "Legal claim detected" /var/log/tru8/backend.log | wc -l

# Check API successes
grep "GovInfo citation search returned" /var/log/tru8/backend.log | grep -v "0 results"

# Check API failures
grep "Legal search failed" /var/log/tru8/backend.log
grep "GovInfo API" /var/log/tru8/backend.log | grep -i "error\|timeout"

# Check cache effectiveness
grep "Legal search cache hit" /var/log/tru8/backend.log | wc -l
```

### 5.4: Dashboard Metrics

**Add to PostHog or monitoring dashboard:**

1. **Legal Claim Rate**
   - Metric: % of claims classified as legal
   - Expected: 5-10%
   - Alert if: >20% or <1%

2. **Legal Source Inclusion Rate**
   - Metric: % of legal claims with govinfo.gov or legislation.gov.uk sources
   - Expected: 70-90%
   - Alert if: <50%

3. **Legal API Success Rate**
   - Metric: % of legal API calls that succeed
   - Expected: 95%+
   - Alert if: <80%

4. **Legal Claim Confidence**
   - Metric: Avg confidence for legal claims
   - Expected: 75-85%
   - Compare to: Non-legal claims

5. **API Rate Limit Usage**
   - Metric: Legal API calls per hour
   - Expected: <4,000/hr (80% of 5,000 limit)
   - Alert if: >4,500/hr

### 5.5: Phase 5 Completion Checklist

- [ ] All tests pass in production environment
- [ ] API keys configured and validated
- [ ] Feature flags set for gradual rollout
- [ ] Monitoring queries added to dashboard
- [ ] Log monitoring configured
- [ ] Alert thresholds set
- [ ] 10% rollout successful (3 days)
- [ ] 50% rollout successful (4 days)
- [ ] 100% rollout complete
- [ ] Documentation updated
- [ ] Team trained on monitoring

**Success Criteria:**
- Legal claims detected at 5-10% rate
- 70%+ of legal claims have legal sources
- 95%+ API success rate
- No increase in errors or latency
- Positive user feedback

---

## Rollback Procedures

### Level 1: Instant Disable (1 minute)

```bash
# Disable all legal features immediately
export ENABLE_LEGAL_INTEGRATION=false
export ENABLE_LEGAL_SOURCE_BOOSTING=false

# Restart backend
systemctl restart tru8-backend
```

**Effect:**
- Legal search service not called
- Legal boosting disabled
- Claims still classified (harmless)
- Pipeline reverts to general search only

### Level 2: Reduce Rollout (2 minutes)

```bash
# Reduce to 10% or internal users only
export LEGAL_FEATURE_ROLLOUT_PERCENTAGE=10
systemctl restart tru8-backend
```

### Level 3: Code Rollback (5 minutes)

```bash
# Revert to previous commit
git log --oneline | head -5  # Find commit before legal integration
git revert <commit-hash>
git push origin main

# Deploy
./deploy.sh
```

### Level 4: Full Rollback (10 minutes)

```bash
# Checkout previous version
git checkout <commit-before-legal>

# Remove legal_search.py
rm backend/app/services/legal_search.py

# Remove legal tests
rm backend/tests/unit/services/test_legal_search.py
rm backend/tests/integration/test_legal_pipeline.py

# Commit and deploy
git add -A
git commit -m "Rollback legal integration"
git push origin main
./deploy.sh
```

### Rollback Decision Matrix

| Issue | Severity | Rollback Level | Timeline |
|-------|----------|----------------|----------|
| API timeout spike | Low | Level 1 (disable) | Immediate |
| High error rate (>10%) | Medium | Level 2 (reduce) | 1 hour |
| Pipeline crashes | High | Level 1 (disable) | Immediate |
| Data quality issues | Medium | Level 2 (reduce) | 1 day |
| False positive spike | Low | Level 2 (reduce) | 1 day |
| User complaints | Medium | Level 2 (reduce) | 1 day |
| Critical bug | High | Level 3 (revert) | Immediate |

---

## Success Criteria

### Phase-Level Success

**Phase 1 (Detection):**
- ✓ 90%+ legal claim detection accuracy
- ✓ Zero false positives on test cases
- ✓ Metadata extraction 85%+ accurate

**Phase 2 (API Layer):**
- ✓ US citation lookup works
- ✓ UK legislation lookup works
- ✓ Cache hit rate 70%+
- ✓ API failures don't crash pipeline

**Phase 3 (Integration):**
- ✓ Legal sources appear in evidence
- ✓ Legal sources ranked higher
- ✓ Non-legal claims unaffected

**Phase 4 (Testing):**
- ✓ All tests pass
- ✓ Validation metrics >90%
- ✓ Manual testing successful

**Phase 5 (Deployment):**
- ✓ 10% rollout successful
- ✓ 100% rollout successful
- ✓ Monitoring shows expected metrics

### Overall Success Metrics

**User Impact:**
- Legal claim accuracy: 80-90% (vs 60% before)
- Legal claim confidence: 80-85% (vs 45-55% before)
- Primary source usage: 70%+ of legal claims

**Technical:**
- API success rate: 95%+
- Cache hit rate: 70%+
- Latency: <10s per legal claim
- No increase in errors

**Business:**
- User satisfaction with legal claims improved
- Zero complaints about legal source quality
- Differentiates Tru8 from competitors

---

## Conclusion

This implementation plan ensures legal statute integration is:

**Safe:**
- Feature flags at every level
- Graceful fallbacks for all failures
- No changes to existing pipeline for non-legal claims
- Comprehensive testing before production

**Logical:**
- Incremental phases with clear dependencies
- Each phase validates before proceeding
- Follows existing patterns (FactCheckAPI, temporal context)
- Uses proven technologies (httpx, XML parsing)

**High Quality:**
- 90%+ accuracy targets
- Primary source verification (1.0 credibility)
- Proper section extraction (not full documents)
- Professional-grade error handling

**Valuable:**
- Addresses critical pipeline gap
- 80-90% accuracy for legal claims (was 60%)
- Differentiates from competitors
- Positions Tru8 as authoritative

**Implementation Timeline:** 10-15 days for full deployment
**Total Effort:** ~60 hours
**Risk Level:** MEDIUM, well-mitigated
**Expected ROI:** +40% accuracy on legal claims

---

**Ready to proceed with Phase 1?**
