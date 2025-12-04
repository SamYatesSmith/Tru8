# Query Planning Content Extraction Fix

## Problem Statement

Query Planning generates intelligent, targeted search queries but bypasses the content extraction pipeline. Instead of fetching and parsing full page content, it returns raw search API meta-descriptions as evidence.

**Impact:** Claims that should be "Supported" return "Uncertain" because the NLI model receives evidence like "View the latest comprehensive Arsenal match stats..." instead of actual content like "Arsenal extended their lead to six points..."

---

## Root Cause

In `backend/app/pipeline/retrieve.py`, the `_execute_planned_queries()` method at lines 318-331 directly converts `SearchResult` objects to `EvidenceSnippet` objects using only the search snippet:

```python
snippet = EvidenceSnippet(
    text=result.snippet or "",  # ← PROBLEM: Just the meta-description
    ...
)
```

This bypasses the content extraction logic in `EvidenceExtractor._extract_from_page()` which:
1. Fetches full HTML from the URL
2. Extracts main content via trafilatura/readability
3. Finds relevant snippets via semantic matching

---

## Implementation Plan

### Phase 1: Fix Content Extraction Bypass

#### Task 1.1: Modify `_execute_planned_queries()` in `retrieve.py`

**File:** `backend/app/pipeline/retrieve.py`
**Location:** Lines 242-343

**Current Flow:**
```
queries → search_for_evidence() → SearchResult → EvidenceSnippet(text=snippet)
```

**Required Flow:**
```
queries → search_for_evidence() → SearchResult → _extract_from_page() → EvidenceSnippet(text=extracted_content)
```

**Changes:**

1. After collecting and deduplicating search results, call content extraction:

```python
async def _execute_planned_queries(
    self,
    claim_text: str,
    query_plan: Dict[str, Any],
    excluded_domain: Optional[str] = None,
    max_sources: int = 20,
    freshness: Optional[str] = None
) -> List[EvidenceSnippet]:
    """
    Execute multiple targeted queries from Query Planning Agent.

    FIXED: Now extracts actual page content instead of returning search snippets.
    """
    try:
        queries = query_plan.get("queries", [])
        priority_sources = query_plan.get("priority_sources", [])
        claim_type = query_plan.get("claim_type", "general")

        if not queries:
            logger.warning(f"No queries in plan for claim: {claim_text[:50]}...")
            return []

        # Get site filter from query planner
        from app.utils.query_planner import get_query_planner
        planner = get_query_planner()
        site_filter = planner.get_site_filter(priority_sources, claim_type)

        logger.debug(f"Executing {len(queries)} planned queries")

        # Execute all queries concurrently
        query_tasks = []
        sources_per_query = max(3, max_sources // len(queries))

        for query in queries:
            if site_filter and "site:" not in query.lower():
                full_query = f"{query} {site_filter}"
            else:
                full_query = query
            task = self.evidence_extractor.search_service.search_for_evidence(
                full_query,
                max_results=sources_per_query,
                freshness=freshness
            )
            query_tasks.append(task)

        # Gather all search results
        all_results = await asyncio.gather(*query_tasks, return_exceptions=True)

        # Merge and deduplicate by URL
        seen_urls = set()
        unique_search_results = []

        for i, results in enumerate(all_results):
            if isinstance(results, Exception):
                logger.warning(f"Query {i+1} failed: {results}")
                continue

            for result in results:
                # Skip excluded domain
                if excluded_domain and extract_domain(result.url) == excluded_domain:
                    continue

                # Deduplicate by URL
                if result.url in seen_urls:
                    continue
                seen_urls.add(result.url)

                # Store query metadata for later
                result._query_index = i
                result._query_used = queries[i]
                result._claim_type = claim_type
                unique_search_results.append(result)

        if not unique_search_results:
            logger.warning(f"No search results for planned queries")
            return []

        # ============================================================
        # CRITICAL FIX: Extract actual page content (like standard path)
        # ============================================================
        semaphore = asyncio.Semaphore(self.evidence_extractor.max_concurrent)
        extraction_tasks = [
            self._extract_from_search_result(result, claim_text, semaphore)
            for result in unique_search_results[:max_sources]
        ]

        extracted_results = await asyncio.gather(*extraction_tasks, return_exceptions=True)

        # Filter successful extractions
        evidence_snippets = []
        for result in extracted_results:
            if isinstance(result, EvidenceSnippet):
                evidence_snippets.append(result)

        logger.info(f"[RETRIEVE] Planned queries: {len(evidence_snippets)}/{len(unique_search_results)} sources extracted")
        return evidence_snippets

    except Exception as e:
        logger.error(f"Planned query execution failed: {e}")
        # Fallback to standard search with claim text
        return await self.evidence_extractor.extract_evidence_for_claim(
            claim_text,
            max_sources=max_sources
        )
```

#### Task 1.2: Add Helper Method for Extraction with Metadata

**File:** `backend/app/pipeline/retrieve.py`
**Location:** After `_execute_planned_queries()` method

Add a new helper method that wraps the evidence extractor's `_extract_from_page()` and preserves query planning metadata:

```python
async def _extract_from_search_result(
    self,
    search_result: SearchResult,
    claim_text: str,
    semaphore: asyncio.Semaphore
) -> Optional[EvidenceSnippet]:
    """
    Extract content from a search result, preserving query planning metadata.

    Wraps EvidenceExtractor._extract_from_page() and adds query plan context.
    """
    try:
        # Use the evidence extractor's content extraction
        snippet = await self.evidence_extractor._extract_from_page(
            search_result,
            claim_text,
            semaphore
        )

        if snippet is not None:
            # Preserve query planning metadata
            snippet.metadata = snippet.metadata or {}
            snippet.metadata["query_index"] = getattr(search_result, '_query_index', None)
            snippet.metadata["query_used"] = getattr(search_result, '_query_used', None)
            snippet.metadata["claim_type"] = getattr(search_result, '_claim_type', None)
            snippet.metadata["source_path"] = "query_planning"

        return snippet

    except Exception as e:
        logger.warning(f"Content extraction failed for {search_result.url}: {e}")
        return None
```

#### Task 1.3: Add Import Statement

**File:** `backend/app/pipeline/retrieve.py`
**Location:** Top of file (imports section)

Ensure `EvidenceSnippet` is imported (it should already be via `EvidenceExtractor`):

```python
from app.services.evidence import EvidenceExtractor, EvidenceSnippet
```

---

### Phase 2: Testing

#### Task 2.1: Create Unit Test for Query Planning Content Extraction

**File:** `backend/tests/test_query_planning_extraction.py` (new file)

```python
"""
Test that Query Planning path extracts actual page content.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.pipeline.retrieve import EvidenceRetriever
from app.services.search import SearchResult
from app.services.evidence import EvidenceSnippet


@pytest.mark.asyncio
async def test_execute_planned_queries_extracts_content():
    """
    Verify that _execute_planned_queries calls content extraction,
    not just wrapping search snippets.
    """
    retriever = EvidenceRetriever()

    # Mock search result
    mock_search_result = SearchResult(
        title="Arsenal top Premier League",
        url="https://example.com/arsenal",
        snippet="View the latest Arsenal stats...",  # Meta description
        published_date="2025-11-28",
        source="example.com"
    )

    # Mock extracted snippet with ACTUAL content
    mock_extracted = EvidenceSnippet(
        text="Arsenal extended their lead to six points with a 2-0 win.",
        source="example.com",
        url="https://example.com/arsenal",
        title="Arsenal top Premier League",
        relevance_score=0.85
    )

    # Mock the search service
    retriever.evidence_extractor.search_service.search_for_evidence = AsyncMock(
        return_value=[mock_search_result]
    )

    # Mock content extraction
    retriever.evidence_extractor._extract_from_page = AsyncMock(
        return_value=mock_extracted
    )

    query_plan = {
        "queries": ["Arsenal Premier League standings November 2025"],
        "claim_type": "league_standing",
        "priority_sources": ["premierleague.com"]
    }

    results = await retriever._execute_planned_queries(
        claim_text="Arsenal is top of the Premier League",
        query_plan=query_plan
    )

    # Verify content extraction was called
    retriever.evidence_extractor._extract_from_page.assert_called_once()

    # Verify we got the extracted content, not the search snippet
    assert len(results) == 1
    assert "Arsenal extended their lead" in results[0].text
    assert "View the latest" not in results[0].text


@pytest.mark.asyncio
async def test_query_planning_preserves_metadata():
    """
    Verify that query planning metadata is preserved through extraction.
    """
    retriever = EvidenceRetriever()

    mock_search_result = SearchResult(
        title="Test",
        url="https://example.com/test",
        snippet="Test snippet",
        source="example.com"
    )

    mock_extracted = EvidenceSnippet(
        text="Extracted content here",
        source="example.com",
        url="https://example.com/test",
        title="Test",
        relevance_score=0.8,
        metadata={}
    )

    retriever.evidence_extractor.search_service.search_for_evidence = AsyncMock(
        return_value=[mock_search_result]
    )
    retriever.evidence_extractor._extract_from_page = AsyncMock(
        return_value=mock_extracted
    )

    query_plan = {
        "queries": ["test query"],
        "claim_type": "player_statistics",
        "priority_sources": []
    }

    results = await retriever._execute_planned_queries(
        claim_text="Test claim",
        query_plan=query_plan
    )

    assert len(results) == 1
    assert results[0].metadata.get("source_path") == "query_planning"
    assert results[0].metadata.get("claim_type") == "player_statistics"
```

#### Task 2.2: Integration Test with Real Pipeline

**Command:**
```bash
cd backend
pytest tests/test_query_planning_extraction.py -v
```

#### Task 2.3: End-to-End Validation

Re-run the original test article:
```
https://football-talk.co.uk/224843/karim-adeyemi-prefers-to-join-arsenal-over-man-utd/
```

**Expected Improvements:**
- Claim 1 (Arsenal top of league): Should show actual standings content in evidence
- Claim 5 (Adeyemi 4 goals, 3 assists): Should show actual stats if available in article text
- Overall "Supported" count should increase from 4/10

---

### Phase 3: Logging Enhancements

#### Task 3.1: Add Extraction Path Logging

**File:** `backend/app/pipeline/retrieve.py`

In `_retrieve_evidence_for_single_claim()`, add logging to distinguish extraction paths:

```python
if query_plan and query_plan.get("queries"):
    web_search_task = self._execute_planned_queries(...)
    logger.info(f"[RETRIEVE] Claim {claim_position} | Path: QUERY_PLANNING | Queries: {len(query_plan['queries'])}")
else:
    web_search_task = self.evidence_extractor.extract_evidence_for_claim(...)
    logger.info(f"[RETRIEVE] Claim {claim_position} | Path: STANDARD")
```

#### Task 3.2: Log Extraction Success Rate

In `_execute_planned_queries()`, log the extraction success rate:

```python
success_count = len(evidence_snippets)
total_count = len(unique_search_results)
success_rate = (success_count / total_count * 100) if total_count > 0 else 0

logger.info(
    f"[RETRIEVE] Query Planning extraction: {success_count}/{total_count} "
    f"({success_rate:.0f}%) sources yielded content"
)
```

---

## Verification Checklist

- [ ] `_execute_planned_queries()` calls `_extract_from_page()` for each search result
- [ ] Query planning metadata (query_index, claim_type) is preserved in evidence
- [ ] Fallback to search snippet occurs gracefully on extraction failure
- [ ] Unit tests pass
- [ ] Integration test with football article shows improved evidence quality
- [ ] Logs clearly indicate which extraction path was used

---

## Rollback Plan

If issues arise, disable Query Planning temporarily:

**File:** `backend/app/core/config.py`

```python
ENABLE_QUERY_PLANNING: bool = False  # Revert to standard path
```

This will cause the pipeline to use the original `extract_evidence_for_claim()` path which is known to work.

---

## Estimated Impact

| Metric | Before | After (Expected) |
|--------|--------|------------------|
| Evidence contains actual content | ~10% | ~70% |
| Claims correctly "Supported" | 4/10 (40%) | 6-7/10 (60-70%) |
| NLI Entailment scores | Near 0 | 0.3-0.8 for factual claims |

---

## Further Recommendations (Next Issues to Resolve)

### Priority 1: Configure Structured Data APIs

#### 1.1 Football-Data.org API
**Issue:** `FOOTBALL_DATA_API_KEY not configured`
**Impact:** League standings claims (e.g., "Arsenal is top with 6 points") would be verified against structured JSON data
**Action:**
- Register for API key at https://www.football-data.org/
- Add to `.env`: `FOOTBALL_DATA_API_KEY=your_key`
- Verify adapter registration in logs

#### 1.2 Transfermarkt API Access
**Issue:** `Transfermarkt client error 403` - all requests blocked
**Impact:** Player statistics, contract info, transfer values unavailable
**Action:**
- Investigate if the `transfermarkt-api.fly.dev` endpoint requires authentication
- Check if there's rate limiting or IP blocking
- Consider alternative: direct Transfermarkt scraping or different API provider

### Priority 2: Content Extraction Resilience

#### 2.1 JavaScript-Rendered Content
**Issue:** Modern sports sites render stats tables via JavaScript; trafilatura only sees static HTML
**Impact:** Claims about specific statistics (goals, assists, points) may still fail
**Action:**
- Evaluate adding Playwright/Puppeteer for JS rendering
- Or: prioritize structured APIs over web scraping for stats

#### 2.2 Bot Detection / 403 Handling
**Issue:** Some sites block scraping, falling back to search snippets
**Action:**
- Add rotating user agents
- Implement exponential backoff
- Consider proxy rotation for high-value sources
- Log which domains consistently fail (for source prioritization)

### Priority 3: Evidence Quality Metrics

#### 3.1 Add Evidence Source Tracking
**Action:** Track in each check result:
- How many sources returned actual content vs. search snippets
- Which domains succeeded vs. failed extraction
- Extraction success rate by claim type

#### 3.2 A/B Testing Infrastructure
**Action:** Compare verdict accuracy between:
- Query Planning + Content Extraction (new)
- Standard path (baseline)
- Structured APIs only (future)

### Priority 4: Claim Type-Specific Handling

#### 4.1 Statistics Claims Special Handling
**Issue:** "4 goals and 3 assists" requires precise numbers often found in tables
**Action:**
- Add table extraction capability (HTML `<table>` parsing)
- For stats claims, prioritize API sources over web scraping
- Consider structured data extraction (schema.org, JSON-LD)

#### 4.2 Time-Sensitive Claims
**Issue:** "Currently top of the league" changes weekly
**Action:**
- Ensure freshness filters are aggressive for `current_week` temporal window
- Add staleness detection: warn if best evidence is >7 days old for current claims
- Consider real-time API calls for live standings/stats

### Priority 5: Source Credibility for Sports

#### 5.1 Add Sports-Specific Tier 1 Sources
**Action:** Update `source_credibility.py` to include:
- `premierleague.com` → 0.95 (official)
- `uefa.com` → 0.95 (official)
- `transfermarkt.com` → 0.90 (authoritative for transfers)
- `fbref.com` → 0.90 (authoritative for stats)

#### 5.2 Deprioritize Aggregator/Gossip Sites
**Action:** Lower credibility for:
- `football-talk.co.uk` → 0.5 (aggregator)
- `90min.com` → 0.5 (aggregator)
- Sites with "gossip" or "rumour" in title

---

## Summary

This fix addresses a critical architectural bug where Query Planning bypasses content extraction entirely. The fix is surgical (modify one method, add one helper) and preserves backward compatibility via the existing fallback mechanism.

After this fix, further improvements should focus on:
1. **Structured APIs** - for precise statistics
2. **Extraction resilience** - for blocked/JS-heavy sites
3. **Quality metrics** - to measure improvement

The expected outcome is a significant improvement in evidence quality, particularly for narrative claims that appear in article prose. Statistical claims will require the structured API work to reach similar quality levels.
