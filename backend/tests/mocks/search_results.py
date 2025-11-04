"""
Mock Search API Responses for Testing

Created: 2025-11-03 15:15:00 UTC
Last Updated: 2025-11-03 15:15:00 UTC
Code Version: commit 388ac66
Purpose: Realistic Brave Search and SERP API responses for evidence retrieval testing
APIs: Brave Search API, SERP API

This module provides mock search results matching actual API response formats
with realistic content, dates, and URLs for comprehensive testing.

Usage:
    from search_results import MOCK_SEARCH_RESULTS
    mock_search_api.search.return_value = MOCK_SEARCH_RESULTS

Phase: Phase 0 (Infrastructure)
Status: Production-ready
"""

from typing import Dict, Any, List
from datetime import datetime, timedelta

# ==================== STANDARD SEARCH RESULTS ====================

MOCK_SEARCH_RESULTS = {
    "results": [
        {
            "title": "Climate Summit 2024: 195 Countries Agree to Historic Emissions Cuts",
            "url": "https://www.bbc.com/news/science-environment-67890123",
            "description": "In a landmark agreement, 195 countries have committed to reducing carbon emissions by 45% by 2030. The deal, reached after two weeks of negotiations, represents the most ambitious climate target to date.",
            "published_date": "2024-11-01",
            "domain": "bbc.com",
            "snippet": "195 countries agreed to reduce emissions by 45% by 2030 at the climate summit..."
        },
        {
            "title": "World Leaders Commit to 45% Carbon Reduction Target",
            "url": "https://www.reuters.com/climate/agreement-2024-11-01",
            "description": "The global climate conference concluded with 195 nations agreeing to cut carbon emissions by 45% within six years. The agreement includes enforcement mechanisms and financial support for developing countries.",
            "published_date": "2024-11-01",
            "domain": "reuters.com",
            "snippet": "Agreement includes binding targets for 45% carbon reduction by 2030..."
        },
        {
            "title": "Climate Agreement Reaches 195 Countries - The Guardian",
            "url": "https://www.theguardian.com/environment/2024/nov/01/climate-summit-agreement",
            "description": "Environmental groups cautiously welcome the new climate agreement covering 195 countries, though some argue the 45% emissions target by 2030 doesn't go far enough.",
            "published_date": "2024-11-01",
            "domain": "theguardian.com",
            "snippet": "195 countries sign agreement with 45% emissions reduction target..."
        },
        {
            "title": "NOAA: Global Temperature Rise Data",
            "url": "https://www.noaa.gov/climate-data/temperature-rise-2024",
            "description": "According to NOAA's latest data, global average temperatures have increased by 1.2°C since pre-industrial times. The data shows consistent warming trends across all major climate indicators.",
            "published_date": "2024-10-15",
            "domain": "noaa.gov",
            "snippet": "Global temperatures up 1.2°C since pre-industrial era..."
        },
        {
            "title": "IEA Renewable Energy Report 2024",
            "url": "https://www.iea.org/reports/renewable-energy-2024",
            "description": "The International Energy Agency reports that renewable energy capacity grew by 9.6% in 2023, with solar and wind leading the expansion. Total global capacity reached 3,870 GW.",
            "published_date": "2024-10-28",
            "domain": "iea.org",
            "snippet": "Renewable energy capacity increased 9.6% in 2023, IEA confirms..."
        }
    ],
    "total_results": 5,
    "query": "195 countries carbon emissions 45% 2030"
}

# ==================== HIGH CREDIBILITY RESULTS ====================

MOCK_HIGH_CREDIBILITY_RESULTS = {
    "results": [
        {
            "title": "NASA Climate Data: Temperature Increase Analysis",
            "url": "https://climate.nasa.gov/vital-signs/global-temperature",
            "description": "NASA's Goddard Institute for Space Studies confirms global temperature rise of 1.2°C since pre-industrial times, with acceleration in recent decades.",
            "published_date": "2024-10-20",
            "domain": "nasa.gov",
            "snippet": "Temperature data confirms 1.2°C warming since 1850-1900 baseline..."
        },
        {
            "title": "IPCC Sixth Assessment Report - Temperature Trends",
            "url": "https://www.ipcc.ch/report/ar6/wg1/chapter/summary",
            "description": "The Intergovernmental Panel on Climate Change confirms 1.1°C of warming since pre-industrial times in its latest assessment.",
            "published_date": "2023-08-15",
            "domain": "ipcc.ch",
            "snippet": "Global surface temperature has increased by 1.1°C..."
        },
        {
            "title": "UK Met Office: State of the Climate 2024",
            "url": "https://www.metoffice.gov.uk/research/climate/maps-and-data/uk-and-regional-series",
            "description": "Met Office analysis shows 1.15°C of global warming since pre-industrial period, consistent with international datasets.",
            "published_date": "2024-09-30",
            "domain": "metoffice.gov.uk",
            "snippet": "Global mean temperature 1.15°C above pre-industrial levels..."
        }
    ],
    "total_results": 3,
    "query": "global temperature rise pre-industrial scientific data"
}

# ==================== MIXED CREDIBILITY RESULTS ====================

MOCK_MIXED_CREDIBILITY_RESULTS = {
    "results": [
        {
            "title": "Climate Facts You Need to Know - Blog",
            "url": "https://climateblog.example.com/facts-2024",
            "description": "Learn about climate change facts and how they affect you...",
            "published_date": "2024-10-15",
            "domain": "climateblog.example.com",
            "snippet": "Some interesting climate facts..."
        },
        {
            "title": "BBC: Climate Summit Breakthrough",
            "url": "https://www.bbc.com/news/science-environment-latest",
            "description": "Authoritative coverage of climate summit results...",
            "published_date": "2024-11-01",
            "domain": "bbc.com",
            "snippet": "Major agreement reached at climate summit..."
        },
        {
            "title": "Climate Change Discussion - Reddit",
            "url": "https://www.reddit.com/r/climate/comments/abc123",
            "description": "Users discuss latest climate news...",
            "published_date": "2024-10-28",
            "domain": "reddit.com",
            "snippet": "What do you think about the new agreement..."
        }
    ],
    "total_results": 3,
    "query": "climate change agreement"
}

# ==================== DUPLICATE CONTENT RESULTS ====================

MOCK_DUPLICATE_RESULTS = {
    "results": [
        {
            "title": "Climate Agreement Announced - Original Source",
            "url": "https://www.reuters.com/climate/agreement-original",
            "description": "195 countries have agreed to reduce carbon emissions by 45% by 2030 in a historic climate deal.",
            "published_date": "2024-11-01",
            "domain": "reuters.com",
            "snippet": "195 countries agreed to cut emissions by 45% by 2030..."
        },
        {
            "title": "Climate Agreement Announced - Syndicated",
            "url": "https://www.localnews.com/climate/agreement-2024",
            "description": "195 countries have agreed to reduce carbon emissions by 45% by 2030 in a historic climate deal.",
            "published_date": "2024-11-01",
            "domain": "localnews.com",
            "snippet": "195 countries agreed to cut emissions by 45% by 2030..."
        },
        {
            "title": "Climate Agreement - Repeated",
            "url": "https://news.example.org/climate-2024",
            "description": "In a major development, 195 countries have agreed to reduce carbon emissions by 45% by 2030.",
            "published_date": "2024-11-01",
            "domain": "example.org",
            "snippet": "195 countries agreed to cut emissions by 45% by 2030..."
        }
    ],
    "total_results": 3,
    "query": "climate agreement 2024"
}

# ==================== DOMAIN-DOMINATED RESULTS ====================

MOCK_DOMAIN_DOMINATED_RESULTS = {
    "results": [
        {
            "title": "Climate News Part 1",
            "url": "https://www.example-news.com/climate-1",
            "description": "First article about climate...",
            "published_date": "2024-11-01",
            "domain": "example-news.com",
            "snippet": "Climate data shows..."
        },
        {
            "title": "Climate News Part 2",
            "url": "https://www.example-news.com/climate-2",
            "description": "Second article about climate...",
            "published_date": "2024-11-01",
            "domain": "example-news.com",
            "snippet": "More climate information..."
        },
        {
            "title": "Climate News Part 3",
            "url": "https://www.example-news.com/climate-3",
            "description": "Third article about climate...",
            "published_date": "2024-11-01",
            "domain": "example-news.com",
            "snippet": "Additional climate coverage..."
        },
        {
            "title": "Climate News Part 4",
            "url": "https://www.example-news.com/climate-4",
            "description": "Fourth article about climate...",
            "published_date": "2024-11-01",
            "domain": "example-news.com",
            "snippet": "Even more climate news..."
        },
        {
            "title": "Climate News Part 5",
            "url": "https://www.example-news.com/climate-5",
            "description": "Fifth article about climate...",
            "published_date": "2024-11-01",
            "domain": "example-news.com",
            "snippet": "Yet more climate coverage..."
        }
    ],
    "total_results": 5,
    "query": "climate news"
}

# ==================== OUTDATED RESULTS ====================

MOCK_OUTDATED_RESULTS = {
    "results": [
        {
            "title": "Climate Data from 2019",
            "url": "https://www.archive.org/climate-2019",
            "description": "Historical climate data from 2019...",
            "published_date": "2019-06-15",
            "domain": "archive.org",
            "snippet": "Climate statistics from 2019..."
        },
        {
            "title": "Old Climate Report",
            "url": "https://www.oldnews.com/climate-2020",
            "description": "Climate report from 2020...",
            "published_date": "2020-03-20",
            "domain": "oldnews.com",
            "snippet": "2020 climate analysis..."
        }
    ],
    "total_results": 2,
    "query": "climate data"
}

# ==================== NO RESULTS ====================

MOCK_NO_RESULTS = {
    "results": [],
    "total_results": 0,
    "query": "xyz123impossible query"
}

# ==================== FACT-CHECK SOURCES ====================

MOCK_FACTCHECK_SOURCES_RESULTS = {
    "results": [
        {
            "title": "FACT CHECK: Climate Agreement Claims",
            "url": "https://www.politifact.com/climate-agreement-2024",
            "description": "PolitiFact rates claims about the climate agreement as 'Mostly True'. 195 countries did agree to 45% emissions cuts.",
            "published_date": "2024-11-02",
            "domain": "politifact.com",
            "snippet": "FACT CHECK: The claim that 195 countries agreed to 45% emissions cuts is Mostly True..."
        },
        {
            "title": "FactCheck.org: Climate Summit Verification",
            "url": "https://www.factcheck.org/2024/11/climate-summit-claims",
            "description": "We verify claims made about the recent climate summit. The 195 countries figure is accurate.",
            "published_date": "2024-11-02",
            "domain": "factcheck.org",
            "snippet": "Our analysis confirms 195 countries participated..."
        }
    ],
    "total_results": 2,
    "query": "climate agreement fact check"
}

# ==================== TEMPORAL-SENSITIVE RESULTS ====================

MOCK_TEMPORAL_RECENT_RESULTS = {
    "results": [
        {
            "title": "Breaking: Climate Summit Concludes Today",
            "url": "https://www.reuters.com/breaking-climate-2024-11-03",
            "description": "Just hours ago, the climate summit concluded...",
            "published_date": "2024-11-03",
            "domain": "reuters.com",
            "snippet": "Summit concluded today with agreement..."
        },
        {
            "title": "Live: Climate Summit Results",
            "url": "https://www.bbc.com/live-climate-summit",
            "description": "Live updates from the climate summit...",
            "published_date": "2024-11-03",
            "domain": "bbc.com",
            "snippet": "Latest updates from today's summit..."
        }
    ],
    "total_results": 2,
    "query": "climate summit today"
}

# ==================== HELPER FUNCTIONS ====================

def create_search_result(
    title: str,
    url: str,
    domain: str,
    snippet: str,
    published_date: str = None,
    description: str = None
) -> Dict[str, Any]:
    """
    Create a single search result

    Args:
        title: Result title
        url: Result URL
        domain: Domain name
        snippet: Text snippet
        published_date: Publication date (YYYY-MM-DD)
        description: Full description

    Returns:
        Search result dictionary

    Created: 2025-11-03
    """
    if published_date is None:
        published_date = datetime.now().strftime("%Y-%m-%d")

    if description is None:
        description = snippet

    return {
        "title": title,
        "url": url,
        "domain": domain,
        "snippet": snippet,
        "description": description,
        "published_date": published_date
    }


def create_search_response(results: List[Dict[str, Any]], query: str = "") -> Dict[str, Any]:
    """
    Create a complete search API response

    Args:
        results: List of search results
        query: Search query

    Returns:
        Complete API response

    Created: 2025-11-03
    """
    return {
        "results": results,
        "total_results": len(results),
        "query": query
    }


def get_search_results_by_credibility(level: str = "high") -> Dict[str, Any]:
    """
    Get search results filtered by credibility level

    Args:
        level: "high", "medium", "low", or "mixed"

    Returns:
        Search results matching credibility level

    Created: 2025-11-03
    """
    if level == "high":
        return MOCK_HIGH_CREDIBILITY_RESULTS
    elif level == "mixed":
        return MOCK_MIXED_CREDIBILITY_RESULTS
    elif level == "low":
        # Return blog/forum sources
        return {
            "results": [r for r in MOCK_MIXED_CREDIBILITY_RESULTS["results"]
                       if "blog" in r["domain"] or "reddit" in r["domain"]],
            "total_results": 2,
            "query": "low credibility sources"
        }
    else:
        return MOCK_SEARCH_RESULTS


def add_date_to_results(results: Dict[str, Any], days_ago: int = 0) -> Dict[str, Any]:
    """
    Modify result dates to be X days ago

    Args:
        results: Search results dictionary
        days_ago: Number of days in the past

    Returns:
        Modified results

    Created: 2025-11-03
    """
    target_date = (datetime.now() - timedelta(days=days_ago)).strftime("%Y-%m-%d")

    modified_results = results.copy()
    for result in modified_results["results"]:
        result["published_date"] = target_date

    return modified_results


# ==================== REALISTIC TEST SCENARIOS ====================

# Scenario: Same-day news event
MOCK_BREAKING_NEWS_RESULTS = create_search_response([
    create_search_result(
        title="BREAKING: Major Climate Agreement Signed",
        url="https://www.reuters.com/breaking-news-climate",
        domain="reuters.com",
        snippet="Just announced: 195 countries sign climate agreement...",
        published_date=datetime.now().strftime("%Y-%m-%d")
    ),
    create_search_result(
        title="Climate Summit: What Just Happened",
        url="https://www.bbc.com/news/just-now",
        domain="bbc.com",
        snippet="Here's what we know about the agreement reached moments ago...",
        published_date=datetime.now().strftime("%Y-%m-%d")
    )
], query="climate agreement today")

# Scenario: Historical claim verification
MOCK_HISTORICAL_RESULTS = create_search_response([
    create_search_result(
        title="Federal Reserve History",
        url="https://www.federalreserve.gov/aboutthefed/history.htm",
        domain="federalreserve.gov",
        snippet="The Federal Reserve was created on December 23, 1913...",
        published_date="2023-12-23"
    ),
    create_search_result(
        title="Federal Reserve Act of 1913",
        url="https://en.wikipedia.org/wiki/Federal_Reserve_Act",
        domain="wikipedia.org",
        snippet="The Federal Reserve Act was passed by Congress on December 23, 1913...",
        published_date="2024-01-15"
    )
], query="Federal Reserve established 1913")

# ==================== ERROR RESPONSES ====================

MOCK_API_ERROR_RESPONSE = {
    "error": {
        "code": 429,
        "message": "Rate limit exceeded",
        "type": "rate_limit_error"
    }
}

MOCK_API_TIMEOUT_RESPONSE = {
    "error": {
        "code": 504,
        "message": "Gateway timeout",
        "type": "timeout_error"
    }
}

# ==================== DOCUMENTATION ====================

"""
Usage Examples:

1. Standard Testing:
    from search_results import MOCK_SEARCH_RESULTS
    mock_search_api.search.return_value = MOCK_SEARCH_RESULTS

2. Credibility Testing:
    from search_results import get_search_results_by_credibility
    results = get_search_results_by_credibility("high")
    mock_search_api.search.return_value = results

3. Temporal Testing:
    from search_results import add_date_to_results, MOCK_SEARCH_RESULTS
    old_results = add_date_to_results(MOCK_SEARCH_RESULTS, days_ago=365)
    mock_search_api.search.return_value = old_results

4. Custom Results:
    from search_results import create_search_result, create_search_response
    result = create_search_result("Title", "https://...", "domain.com", "snippet")
    response = create_search_response([result], query="test")
    mock_search_api.search.return_value = response

5. Duplicate Testing:
    from search_results import MOCK_DUPLICATE_RESULTS
    mock_search_api.search.return_value = MOCK_DUPLICATE_RESULTS

6. No Results:
    from search_results import MOCK_NO_RESULTS
    mock_search_api.search.return_value = MOCK_NO_RESULTS
"""

# ==================== VERSION HISTORY ====================
# v1.0.0 - 2025-11-03 - Initial mock library
#          - Standard search results (5 results, varied domains)
#          - High credibility results (NASA, IPCC, Met Office)
#          - Mixed credibility results
#          - Duplicate content scenarios
#          - Domain-dominated results
#          - Outdated results
#          - Fact-check sources
#          - Temporal-sensitive results
#          - Helper functions
#          - Realistic test scenarios
#          - Error responses

# Aliases for test compatibility (Phase 1 tests use different naming)
MOCK_SEARCH_RESULTS_STANDARD = MOCK_SEARCH_RESULTS
MOCK_SEARCH_RESULTS_HIGH_CREDIBILITY = MOCK_HIGH_CREDIBILITY_RESULTS
MOCK_SEARCH_RESULTS_MIXED_CREDIBILITY = MOCK_MIXED_CREDIBILITY_RESULTS
MOCK_SEARCH_RESULTS_DUPLICATES = MOCK_DUPLICATE_RESULTS
MOCK_SEARCH_RESULTS_DOMAIN_DOMINATED = MOCK_DOMAIN_DOMINATED_RESULTS
MOCK_SEARCH_RESULTS_TEMPORAL = MOCK_TEMPORAL_RECENT_RESULTS
