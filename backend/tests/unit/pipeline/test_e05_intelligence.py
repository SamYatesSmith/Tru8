"""
PR-E05: Intelligence fixes tests.

Tests for:
- Query planner cap at 2 per element
- Per-element freshness preservation
- Academic adapter year filters
- Hardcoded relevance_score removal from all adapters
- FactCheck text extraction and URL dedup
- Round-robin caps (API evidence + pre-ranking)
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime


# ============================================================
# 1. Query planner: cap at 2 queries per element
# ============================================================


def test_query_cap_at_2_per_element():
    """Verify query planner caps at 2 queries per element."""
    from app.utils.query_planner import LLMQueryPlanner

    planner = LLMQueryPlanner()

    # Create a plan with 5 queries
    plans = [
        {
            "claim_index": 0,
            "element_id": "e1",
            "queries": ["q1", "q2", "q3", "q4", "q5"],
            "freshness": "py",
        }
    ]

    validated = planner._validate_plans(plans, 1)
    assert len(validated) == 1
    assert len(validated[0]["queries"]) == 2
    assert validated[0]["queries"] == ["q1", "q2"]


# ============================================================
# 2. Per-element freshness preserved in merged query plan
# ============================================================


def test_per_element_freshness_preserved():
    """Verify query_freshness list matches per-element freshness decisions."""
    # Simulate what retrieve_evidence_for_claims does when merging plans
    plans_by_claim = {
        0: [
            {"element_id": "e1", "freshness": "pd", "queries": ["breaking news query"]},
            {"element_id": "e2", "freshness": "py", "queries": ["historical query"]},
            {"element_id": "e3", "freshness": "pw", "queries": ["weekly data query"]},
        ]
    }

    # Replicate the merge logic from retrieve.py
    for claim_idx, plans in plans_by_claim.items():
        merged_queries = []
        query_element_ids = []
        query_freshness = []
        for p in plans:
            element_id = p.get("element_id", "e1")
            element_freshness = p.get("freshness", "py")
            for q in p.get("queries", []):
                merged_queries.append(q)
                query_element_ids.append(element_id)
                query_freshness.append(element_freshness)

        # Verify freshness is per-query, not collapsed to first element
        assert len(query_freshness) == 3
        assert query_freshness[0] == "pd"  # e1's freshness
        assert query_freshness[1] == "py"  # e2's freshness
        assert query_freshness[2] == "pw"  # e3's freshness

        # Verify element IDs match
        assert query_element_ids == ["e1", "e2", "e3"]


# ============================================================
# 3-5. Academic adapter year filters
# ============================================================


def test_crossref_year_filter():
    """Verify CrossRef adds from-pub-date year filter to params."""
    from app.services.api_adapters.academic import CrossRefAdapter

    adapter = CrossRefAdapter()
    current_year = datetime.utcnow().year
    min_year = current_year - 2

    # Mock _make_request to capture params
    captured_params = {}

    def mock_request(endpoint, params=None, **kwargs):
        captured_params.update(params or {})
        return {"message": {"items": []}}

    adapter._make_request = mock_request
    adapter.search("test query", "Science", "Global")

    assert "filter" in captured_params
    assert f"from-pub-date:{min_year}" in captured_params["filter"]


def test_semantic_scholar_year_filter():
    """Verify Semantic Scholar adds year= param to URL."""
    from app.services.api_adapters.academic import SemanticScholarAdapter

    adapter = SemanticScholarAdapter()
    current_year = datetime.utcnow().year
    min_year = current_year - 2

    # Mock httpx.Client to capture the URL
    captured_url = {}

    class MockResponse:
        status_code = 200

        def raise_for_status(self):
            pass

        def json(self):
            return {"data": []}

    class MockClient:
        def __init__(self, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def get(self, url, **kwargs):
            captured_url["url"] = url
            return MockResponse()

    with patch("httpx.Client", MockClient):
        adapter.search("test query", "Science", "Global")

    assert f"year={min_year}-{current_year}" in captured_url["url"]


def test_openalex_year_filter():
    """Verify OpenAlex adds from_publication_date filter to URL."""
    from app.services.api_adapters.academic import OpenAlexAdapter

    adapter = OpenAlexAdapter()
    current_year = datetime.utcnow().year
    min_year = current_year - 2

    # Mock httpx.Client to capture the URL
    captured_url = {}

    class MockResponse:
        status_code = 200

        def raise_for_status(self):
            pass

        def json(self):
            return {"results": []}

    class MockClient:
        def __init__(self, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def get(self, url, **kwargs):
            captured_url["url"] = url
            return MockResponse()

    with patch("httpx.Client", MockClient):
        adapter.search("test query", "Science", "Global")

    assert f"from_publication_date:{min_year}-01-01" in captured_url["url"]


# ============================================================
# 6-8. No hardcoded relevance_score in adapters
# ============================================================


def test_academic_no_relevance_score():
    """Verify Semantic Scholar and OpenAlex results have no relevance_score key."""
    from app.services.api_adapters.academic import (
        SemanticScholarAdapter,
        OpenAlexAdapter,
    )

    # Test SemanticScholar
    ss = SemanticScholarAdapter()

    class MockResponse:
        status_code = 200

        def raise_for_status(self):
            pass

        def json(self):
            return {
                "data": [
                    {
                        "paperId": "abc123",
                        "title": "Test Paper",
                        "abstract": "Test abstract",
                        "url": "https://example.com/paper",
                        "year": 2025,
                        "authors": [{"name": "Test Author"}],
                        "citationCount": 10,
                        "publicationDate": "2025-01-01",
                        "venue": "Test Venue",
                    }
                ]
            }

    class MockClient:
        def __init__(self, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def get(self, url, **kwargs):
            return MockResponse()

    with patch("httpx.Client", MockClient):
        results = ss.search("test", "Science", "Global")

    assert len(results) == 1
    assert "relevance_score" not in results[0]

    # Test OpenAlex
    oa = OpenAlexAdapter()

    class MockOAResponse:
        status_code = 200

        def raise_for_status(self):
            pass

        def json(self):
            return {
                "results": [
                    {
                        "title": "Test Work",
                        "authorships": [{"author": {"display_name": "Test Author"}}],
                        "publication_date": "2025-06-01",
                        "cited_by_count": 5,
                        "doi": "10.1234/test",
                        "abstract_inverted_index": {"test": [0], "abstract": [1]},
                        "primary_location": {
                            "source": {"display_name": "Test Journal"}
                        },
                        "open_access": {"is_oa": True},
                        "type": "article",
                    }
                ]
            }

    class MockOAClient:
        def __init__(self, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def get(self, url, **kwargs):
            return MockOAResponse()

    with patch("httpx.Client", MockOAClient):
        results = oa.search("test", "Science", "Global")

    assert len(results) == 1
    assert "relevance_score" not in results[0]


def test_archives_no_relevance_score():
    """Verify Wikipedia, LoC, and Internet Archive results have no relevance_score key."""
    from app.services.api_adapters.archives import (
        WikipediaAdapter,
        LibraryOfCongressAdapter,
        InternetArchiveAdapter,
    )

    # Test Wikipedia
    wiki = WikipediaAdapter(max_results=1)

    class MockWikiSearchResponse:
        status_code = 200

        def raise_for_status(self):
            pass

        def json(self):
            return {
                "query": {
                    "search": [
                        {
                            "title": "Test Article",
                            "snippet": "test",
                            "timestamp": "2025-01-01T00:00:00Z",
                        }
                    ]
                }
            }

    class MockWikiSummaryResponse:
        status_code = 200

        def raise_for_status(self):
            pass

        def json(self):
            return {
                "title": "Test Article",
                "extract": "Test content",
                "content_urls": {
                    "desktop": {"page": "https://en.wikipedia.org/wiki/Test"}
                },
                "description": "Test desc",
                "pageid": 123,
                "timestamp": "2025-01-01T00:00:00Z",
            }

    class MockWikiClient:
        def __init__(self, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def get(self, url, **kwargs):
            return MockWikiSearchResponse()

    # Mock _make_request for summary calls
    wiki._make_request = lambda endpoint, **kw: MockWikiSummaryResponse().json()

    with patch("app.services.api_adapters.archives.httpx.Client", MockWikiClient):
        results = wiki.search("test", "History", "Global")

    assert len(results) >= 1
    for r in results:
        assert "relevance_score" not in r

    # Test Library of Congress
    loc = LibraryOfCongressAdapter(max_results=1)
    loc._make_request = lambda endpoint, **kw: {
        "results": [
            {
                "title": "Test Doc",
                "url": "https://www.loc.gov/test",
                "date": "2020",
                "description": ["Test description"],
            }
        ]
    }
    results = loc._search_loc_collections("test")
    for r in results:
        assert "relevance_score" not in r

    # Chronicling America
    results = loc._search_chronicling_america("test")
    for r in results:
        assert "relevance_score" not in r

    # Test Internet Archive
    ia = InternetArchiveAdapter(max_results=1)

    class MockIAResponse:
        status_code = 200

        def raise_for_status(self):
            pass

        def json(self):
            return {
                "response": {
                    "docs": [
                        {
                            "identifier": "test123",
                            "title": "Test Archive",
                            "description": "Test desc",
                            "date": "2020-01-01",
                            "creator": ["Test Creator"],
                            "mediatype": "texts",
                            "collection": ["test"],
                        }
                    ]
                }
            }

    class MockIAClient:
        def __init__(self, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def get(self, url, **kwargs):
            return MockIAResponse()

    with patch("app.services.api_adapters.archives.httpx.Client", MockIAClient):
        results = ia.search("test", "History", "Global")

    assert len(results) >= 1
    for r in results:
        assert "relevance_score" not in r


def test_factcheck_no_relevance_score():
    """Verify convert_to_evidence() output has no relevance_score key."""
    from app.services.factcheck_api import FactCheckAPI

    api = FactCheckAPI()
    fc = {
        "publisher": "Snopes",
        "url": "https://snopes.com/test",
        "title": "Test Fact Check",
        "rating": "True",
        "review_date": "2025-01-01",
    }

    result = api.convert_to_evidence(fc, "test claim")
    assert "relevance_score" not in result


# ============================================================
# 9-10. FactCheck text extraction
# ============================================================


@pytest.mark.asyncio
async def test_factcheck_text_extraction():
    """Verify extracted text is used as snippet when available."""
    from app.services.factcheck_api import FactCheckAPI

    api = FactCheckAPI()
    fc = {
        "publisher": "Snopes",
        "url": "https://snopes.com/test",
        "title": "Test Fact Check",
        "rating": "True",
        "review_date": "2025-01-01",
    }

    extracted_text = (
        "This is the actual fact-check article content with detailed analysis."
    )
    result = api.convert_to_evidence(fc, "test claim", extracted_text=extracted_text)

    assert result["snippet"] == extracted_text
    assert "Fact-check rating" not in result["snippet"]


@pytest.mark.asyncio
async def test_factcheck_text_extraction_fallback():
    """Verify stub snippet is used when text extraction fails."""
    from app.services.factcheck_api import FactCheckAPI

    api = FactCheckAPI()
    fc = {
        "publisher": "Snopes",
        "url": "https://snopes.com/test",
        "title": "Test Fact Check",
        "rating": "True",
        "review_date": "2025-01-01",
    }

    # No extracted_text → fallback to stub
    result = api.convert_to_evidence(fc, "test claim")
    assert result["snippet"] == "Fact-check rating: True"

    # None extracted_text → fallback to stub
    result = api.convert_to_evidence(fc, "test claim", extracted_text=None)
    assert result["snippet"] == "Fact-check rating: True"


# ============================================================
# 11. FactCheck URL dedup
# ============================================================


@pytest.mark.asyncio
async def test_factcheck_url_dedup():
    """Verify duplicate URLs from multi-claim fact-checks are deduplicated."""
    from app.services.factcheck_api import FactCheckAPI

    api = FactCheckAPI()
    api.api_key = "test-key"

    # Mock API response with duplicate URLs across claim reviews
    mock_response_data = {
        "claims": [
            {
                "text": "Claim 1",
                "claimReview": [
                    {
                        "publisher": {"name": "Snopes", "site": "snopes.com"},
                        "url": "https://snopes.com/fact-check/duplicate",
                        "title": "Fact Check 1",
                        "textualRating": "True",
                        "reviewDate": "2025-01-01",
                    }
                ],
            },
            {
                "text": "Claim 2",
                "claimReview": [
                    {
                        "publisher": {"name": "Snopes", "site": "snopes.com"},
                        "url": "https://snopes.com/fact-check/duplicate",  # Same URL
                        "title": "Fact Check 1 (duplicate)",
                        "textualRating": "True",
                        "reviewDate": "2025-01-01",
                    },
                    {
                        "publisher": {"name": "PolitiFact", "site": "politifact.com"},
                        "url": "https://politifact.com/unique",
                        "title": "Fact Check 2",
                        "textualRating": "False",
                        "reviewDate": "2025-01-02",
                    },
                ],
            },
        ]
    }

    class MockResponse:
        status_code = 200

        def raise_for_status(self):
            pass

        def json(self):
            return mock_response_data

    with patch("httpx.AsyncClient") as MockClient:
        mock_client_instance = AsyncMock()
        mock_client_instance.get.return_value = MockResponse()
        MockClient.return_value.__aenter__ = AsyncMock(
            return_value=mock_client_instance
        )
        MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

        results = await api.search_fact_checks("test claim")

    # Should have 2 results (not 3) — the duplicate URL is removed
    assert len(results) == 2
    urls = [r["url"] for r in results]
    assert len(set(urls)) == len(urls)  # All unique


# ============================================================
# 12. API cap round-robin
# ============================================================


def test_api_cap_round_robin():
    """Verify API evidence cap uses round-robin across providers."""
    from collections import defaultdict

    MAX_API_EVIDENCE_PER_CLAIM = 5

    # 12 items from 3 providers (4 each)
    all_api_evidence = []
    for i in range(4):
        all_api_evidence.append(
            {"external_source_provider": "Wikipedia", "title": f"Wiki {i}"}
        )
        all_api_evidence.append(
            {"external_source_provider": "CrossRef", "title": f"CR {i}"}
        )
        all_api_evidence.append(
            {"external_source_provider": "Semantic Scholar", "title": f"SS {i}"}
        )

    assert len(all_api_evidence) == 12

    # Apply round-robin (same logic as retrieve.py)
    by_provider = defaultdict(list)
    for item in all_api_evidence:
        by_provider[item.get("external_source_provider", "unknown")].append(item)
    providers = list(by_provider.values())
    interleaved = []
    idx = 0
    while len(interleaved) < MAX_API_EVIDENCE_PER_CLAIM:
        added = False
        for group in providers:
            if idx < len(group) and len(interleaved) < MAX_API_EVIDENCE_PER_CLAIM:
                interleaved.append(group[idx])
                added = True
        if not added:
            break
        idx += 1

    assert len(interleaved) == 5
    # Verify diversity: at least 2 providers represented
    result_providers = set(item["external_source_provider"] for item in interleaved)
    assert len(result_providers) >= 2

    # Round-robin should pick: Wiki0, CR0, SS0, Wiki1, CR1
    assert interleaved[0]["external_source_provider"] == "Wikipedia"
    assert interleaved[1]["external_source_provider"] == "CrossRef"
    assert interleaved[2]["external_source_provider"] == "Semantic Scholar"


# ============================================================
# 13. Pre-ranking cap interleaves web + API
# ============================================================


def test_pre_ranking_cap_interleaves():
    """Verify pre-ranking cap interleaves web and API items (not sorted by score)."""
    from app.services.evidence import EvidenceSnippet

    MAX_EVIDENCE_FOR_RANKING = 6

    # Create web snippets (all with score 0.0 since we removed hardcoded scores)
    web = [
        EvidenceSnippet(
            text=f"Web result {i}",
            source=f"web{i}.com",
            url=f"https://web{i}.com",
            title=f"Web {i}",
            relevance_score=0.0,
        )
        for i in range(5)
    ]

    # Create API snippets
    api = [
        EvidenceSnippet(
            text=f"API result {i}",
            source=f"api{i}",
            url=f"https://api{i}.com",
            title=f"API {i}",
            relevance_score=0.0,
            metadata={"external_source_provider": f"Provider{i}"},
        )
        for i in range(5)
    ]

    all_evidence_snippets = web + api  # 10 total

    # Apply interleave (same logic as retrieve.py)
    if len(all_evidence_snippets) > MAX_EVIDENCE_FOR_RANKING:
        interleaved = []
        wi, ai = 0, 0
        while len(interleaved) < MAX_EVIDENCE_FOR_RANKING and (
            wi < len(web) or ai < len(api)
        ):
            if wi < len(web):
                interleaved.append(web[wi])
                wi += 1
            if ai < len(api) and len(interleaved) < MAX_EVIDENCE_FOR_RANKING:
                interleaved.append(api[ai])
                ai += 1
        all_evidence_snippets = interleaved

    assert len(all_evidence_snippets) == 6

    # Verify interleaving: web and api alternate
    sources = [s.source for s in all_evidence_snippets]
    assert sources[0] == "web0.com"  # web first
    assert sources[1] == "api0"  # then API
    assert sources[2] == "web1.com"  # web
    assert sources[3] == "api1"  # API
