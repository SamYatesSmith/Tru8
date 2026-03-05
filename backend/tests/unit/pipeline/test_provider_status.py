"""Tests for M-02 provider status + freshness signal.

Covers:
- _build_provider_status aggregation helper
- Web search timeout recorded
- Provider status persisted to Check
- _build_freshness with various dates
- _count_unique_domains with various URLs and www stripping
- Freshness handles all-undated evidence
"""

import pytest
from datetime import datetime, timedelta

from app.pipeline.runner import _build_provider_status
from app.services.computed_analytics import _build_freshness, _count_unique_domains


# ── _build_provider_status ─────────────────────────────────────────────────


class TestBuildProviderStatus:
    def test_basic_aggregation(self):
        claims = [
            {
                "web_search_status": {"status": "ok", "count": 8},
                "api_stats": {
                    "apis_queried": [
                        {"name": "ONS Economic Statistics", "results": 3},
                        {"name": "FRED", "results": 0},
                    ]
                },
            }
        ]
        result = _build_provider_status(claims)

        assert result["web_search"]["status"] == "ok"
        assert result["web_search"]["count"] == 8
        assert result["ONS Economic Statistics"]["status"] == "ok"
        assert result["ONS Economic Statistics"]["count"] == 3
        assert result["FRED"]["status"] == "0_results"
        assert result["FRED"]["count"] == 0

    def test_web_search_timeout_recorded(self):
        claims = [
            {
                "web_search_status": {"status": "timeout", "count": 0},
                "api_stats": {"apis_queried": []},
            }
        ]
        result = _build_provider_status(claims)
        assert result["web_search"]["status"] == "timeout"
        assert result["web_search"]["count"] == 0

    def test_any_ok_wins_over_errors(self):
        """If any call for a provider succeeded, overall status is ok."""
        claims = [
            {
                "api_stats": {
                    "apis_queried": [
                        {"name": "PubMed", "results": 0, "error": "timeout occurred"},
                    ]
                }
            },
            {
                "api_stats": {
                    "apis_queried": [
                        {"name": "PubMed", "results": 5},
                    ]
                }
            },
        ]
        result = _build_provider_status(claims)
        assert result["PubMed"]["status"] == "ok"
        assert result["PubMed"]["count"] == 5

    def test_all_timeout_yields_timeout(self):
        claims = [
            {
                "api_stats": {
                    "apis_queried": [
                        {"name": "Brave", "results": 0, "error": "Request timeout"},
                    ]
                }
            },
            {
                "api_stats": {
                    "apis_queried": [
                        {"name": "Brave", "results": 0, "error": "timeout exceeded"},
                    ]
                }
            },
        ]
        result = _build_provider_status(claims)
        assert result["Brave"]["status"] == "timeout"

    def test_all_error_yields_error(self):
        claims = [
            {
                "api_stats": {
                    "apis_queried": [
                        {
                            "name": "NOAA",
                            "results": 0,
                            "error": "500 Internal Server Error",
                        },
                    ]
                }
            },
        ]
        result = _build_provider_status(claims)
        assert result["NOAA"]["status"] == "error"

    def test_empty_claims(self):
        result = _build_provider_status([])
        assert result == {}

    def test_no_api_stats(self):
        claims = [{"web_search_status": {"status": "ok", "count": 5}}]
        result = _build_provider_status(claims)
        assert "web_search" in result
        assert len(result) == 1

    def test_provider_status_persisted_to_check(self):
        """Verify the dict shape is valid for JSONB storage."""
        claims = [
            {
                "web_search_status": {"status": "ok", "count": 10},
                "api_stats": {"apis_queried": [{"name": "ONS", "results": 2}]},
            }
        ]
        status = _build_provider_status(claims)
        # Must be JSON-serialisable dict
        import json

        serialised = json.dumps(status)
        assert isinstance(json.loads(serialised), dict)


# ── _build_freshness ───────────────────────────────────────────────────────


class TestBuildFreshness:
    def test_basic_freshness(self):
        now = datetime.utcnow()
        evidence = [
            {"publishedDate": (now - timedelta(days=5)).isoformat()},
            {"publishedDate": (now - timedelta(days=30)).isoformat()},
        ]
        result = _build_freshness(evidence)
        assert result["freshestDaysAgo"] == 5
        assert result["dateSpanDays"] == 25
        assert result["undatedCount"] == 0

    def test_all_undated(self):
        evidence = [
            {"publishedDate": None},
            {"url": "https://example.com"},
        ]
        result = _build_freshness(evidence)
        assert result["freshestDaysAgo"] is None
        assert result["dateSpanDays"] is None
        assert result["undatedCount"] == 2

    def test_mixed_dated_undated(self):
        now = datetime.utcnow()
        evidence = [
            {"publishedDate": (now - timedelta(days=1)).isoformat()},
            {"publishedDate": None},
            {},
        ]
        result = _build_freshness(evidence)
        assert result["freshestDaysAgo"] == 1
        assert result["undatedCount"] == 2

    def test_empty_list(self):
        result = _build_freshness([])
        assert result["freshestDaysAgo"] is None
        assert result["undatedCount"] == 0

    def test_iso_with_timezone(self):
        now = datetime.utcnow()
        evidence = [
            {"publishedDate": (now - timedelta(days=2)).isoformat() + "Z"},
        ]
        result = _build_freshness(evidence)
        assert result["freshestDaysAgo"] == 2

    def test_single_date_zero_span(self):
        now = datetime.utcnow()
        evidence = [{"publishedDate": now.isoformat()}]
        result = _build_freshness(evidence)
        assert result["dateSpanDays"] == 0


# ── _count_unique_domains ──────────────────────────────────────────────────


class TestCountUniqueDomains:
    def test_basic_counting(self):
        evidence = [
            {"url": "https://bbc.co.uk/news/article1"},
            {"url": "https://bbc.co.uk/news/article2"},
            {"url": "https://reuters.com/story"},
        ]
        assert _count_unique_domains(evidence) == 2

    def test_www_stripping(self):
        evidence = [
            {"url": "https://www.bbc.co.uk/news"},
            {"url": "https://bbc.co.uk/sport"},
        ]
        assert _count_unique_domains(evidence) == 1

    def test_case_insensitive(self):
        evidence = [
            {"url": "https://BBC.co.uk/news"},
            {"url": "https://bbc.co.uk/sport"},
        ]
        assert _count_unique_domains(evidence) == 1

    def test_empty_urls(self):
        evidence = [{"url": ""}, {}]
        assert _count_unique_domains(evidence) == 0

    def test_diverse_domains(self):
        evidence = [
            {"url": "https://bbc.co.uk/a"},
            {"url": "https://reuters.com/b"},
            {"url": "https://nytimes.com/c"},
            {"url": "https://who.int/d"},
        ]
        assert _count_unique_domains(evidence) == 4
