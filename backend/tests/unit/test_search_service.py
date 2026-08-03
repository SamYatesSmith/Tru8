"""
Tests for app.services.search — SearchService, providers, circuit breaker, warmup.

Covers:
  - _optimize_query_for_factcheck (10 tests)
  - Brave circuit breaker functions (4 tests)
  - BraveSearchProvider (5 tests)
  - SerpAPIProvider (3 tests)
  - SerperProvider (3 tests)
  - SearchService orchestration (5 tests)
  - warmup_search_providers (2 tests)
"""

import time
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

import httpx

import app.services.search as search_module
from app.services.search import (
    SearchResult,
    SearchService,
    BraveSearchProvider,
    SerpAPIProvider,
    SerperProvider,
    _brave_circuit_is_open,
    _brave_circuit_trip,
    warmup_search_providers,
)


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def reset_circuit_breaker():
    """Reset Brave circuit breaker globals before each test."""
    search_module._brave_circuit_open = False
    search_module._brave_circuit_opened_at = 0.0
    yield


@pytest.fixture(autouse=True)
def reset_rate_limiters():
    """Reset rate-limiter timestamps so warmup / provider tests are isolated."""
    search_module._brave_last_request_time = 0
    search_module._serpapi_last_request_time = 0
    search_module._serper_last_request_time = 0
    yield


def _make_service_no_providers():
    """Create a SearchService with no API keys (no providers)."""
    with patch("app.services.search.settings") as mock_settings:
        mock_settings.SERPER_API_KEY = ""
        mock_settings.BRAVE_API_KEY = ""
        mock_settings.SERP_API_KEY = ""
        return SearchService()


# ===========================================================================
# _optimize_query_for_factcheck  (10 tests)
# ===========================================================================


class TestOptimizeQueryForFactcheck:

    def _optimize(self, claim: str) -> str:
        service = _make_service_no_providers()
        return service._optimize_query_for_factcheck(claim)

    def test_strips_procedural_negatives(self):
        result = self._optimize("The government failed to notify residents")
        assert "failed to" not in result
        assert "The government" in result
        assert "-site:snopes.com" in result

    def test_strips_filler_words(self):
        result = self._optimize("He allegedly claimed the earth is flat")
        assert "allegedly" not in result.lower()
        assert "claimed" not in result.lower()
        assert "earth is flat" in result

    def test_removes_punctuation(self):
        result = self._optimize("Is the earth flat?")
        assert "?" not in result
        result2 = self._optimize("Breaking news!")
        assert "!" not in result2

    def test_normalises_whitespace(self):
        result = self._optimize("too   many    spaces")
        # Core words should be single-spaced
        assert "too many spaces" in result

    def test_adds_exclusions(self):
        result = self._optimize("simple claim")
        assert "-site:snopes.com" in result
        assert "-site:factcheck.org" in result
        assert "-site:politifact.com" in result
        assert "-site:wikipedia.org" in result

    def test_does_not_duplicate_exclusions(self):
        result = self._optimize("some claim -site:snopes.com")
        assert result.count("-site:snopes.com") == 1

    def test_truncates_at_250_chars(self):
        long_claim = "word " * 100  # ~500 chars
        result = self._optimize(long_claim)
        assert len(result) <= 250

    def test_max_3_exclusions_kept(self):
        long_claim = "word " * 80  # will trigger truncation
        result = self._optimize(long_claim)
        exclusion_count = result.count("-site:")
        assert exclusion_count <= 3

    def test_empty_string(self):
        result = self._optimize("")
        # Should still have exclusions appended
        assert "-site:" in result

    def test_passthrough_clean_claim(self):
        result = self._optimize("The earth orbits the sun")
        assert result.startswith("The earth orbits the sun")
        assert "-site:snopes.com" in result


# ===========================================================================
# Brave circuit breaker  (4 tests)
# ===========================================================================


class TestBraveCircuitBreaker:

    def test_circuit_closed_by_default(self):
        assert _brave_circuit_is_open() is False

    def test_trip_opens_circuit(self):
        _brave_circuit_trip()
        assert _brave_circuit_is_open() is True

    @patch("app.services.search.time")
    def test_auto_reset_after_cooldown(self, mock_time):
        # Trip at t=100
        mock_time.time.return_value = 100.0
        _brave_circuit_trip()
        # Check at t=161 (> 60s cooldown)
        mock_time.time.return_value = 161.0
        assert _brave_circuit_is_open() is False

    def test_trip_during_open_resets_timer(self):
        _brave_circuit_trip()
        opened_at_first = search_module._brave_circuit_opened_at
        time.sleep(0.01)
        _brave_circuit_trip()
        opened_at_second = search_module._brave_circuit_opened_at
        assert opened_at_second > opened_at_first


# ===========================================================================
# BraveSearchProvider  (5 tests)
# ===========================================================================


class TestBraveSearchProvider:

    @patch("app.services.search.settings")
    async def test_no_key_returns_empty(self, mock_settings):
        mock_settings.BRAVE_API_KEY = ""
        provider = BraveSearchProvider()
        assert provider.api_key == ""
        result = await provider.search("anything")
        assert result == []

    @patch("app.services.search.settings")
    async def test_circuit_open_returns_empty(self, mock_settings):
        mock_settings.BRAVE_API_KEY = "test-key"
        provider = BraveSearchProvider()
        _brave_circuit_trip()
        result = await provider.search("anything")
        assert result == []

    @patch("app.services.search.asyncio.sleep", new_callable=AsyncMock)
    @patch("app.services.search.settings")
    async def test_429_trips_circuit(self, mock_settings, mock_sleep):
        mock_settings.BRAVE_API_KEY = "test-key"
        provider = BraveSearchProvider()
        provider.api_key = "test-key"

        # Build a mock 429 response
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "429 Too Many Requests",
            request=MagicMock(),
            response=mock_response,
        )

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        provider._client = mock_client

        result = await provider.search("test query")
        assert result == []
        assert _brave_circuit_is_open() is True

    @patch("app.services.search.asyncio.sleep", new_callable=AsyncMock)
    @patch("app.services.search.settings")
    async def test_timeout_retries_then_empty(self, mock_settings, mock_sleep):
        mock_settings.BRAVE_API_KEY = "test-key"
        provider = BraveSearchProvider()
        provider.api_key = "test-key"

        mock_client = AsyncMock()
        mock_client.get.side_effect = httpx.TimeoutException("timed out")
        provider._client = mock_client

        result = await provider.search("test query")
        assert result == []
        # 3 retries total
        assert mock_client.get.call_count == 3

    @patch("app.services.search.asyncio.sleep", new_callable=AsyncMock)
    @patch("app.services.search.settings")
    async def test_success_returns_results(self, mock_settings, mock_sleep):
        mock_settings.BRAVE_API_KEY = "test-key"
        provider = BraveSearchProvider()
        provider.api_key = "test-key"

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "web": {
                "results": [
                    {
                        "title": "Result 1",
                        "url": "https://example.com/1",
                        "description": "Snippet 1",
                    },
                    {
                        "title": "Result 2",
                        "url": "https://example.com/2",
                        "description": "Snippet 2",
                        "published_date": "2025-01-01",
                    },
                ]
            }
        }

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        provider._client = mock_client

        results = await provider.search("test query")
        assert len(results) == 2
        assert results[0].title == "Result 1"
        assert results[0].url == "https://example.com/1"
        assert results[1].published_date == "2025-01-01"


# ===========================================================================
# SerpAPIProvider  (3 tests)
# ===========================================================================


class TestSerpAPIProvider:

    @patch("app.services.search.asyncio.sleep", new_callable=AsyncMock)
    @patch("app.services.search.settings")
    async def test_success_parses_organic_results(self, mock_settings, mock_sleep):
        mock_settings.SERP_API_KEY = "test-key"
        provider = SerpAPIProvider()
        provider.api_key = "test-key"

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "organic_results": [
                {
                    "title": "SerpAPI Result",
                    "link": "https://serpapi-example.com/page",
                    "snippet": "Some snippet",
                    "date": "2025-06-15",
                    "displayed_link": "https://serpapi-example.com/page",
                },
            ]
        }

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        provider._client = mock_client

        results = await provider.search("test query")
        assert len(results) == 1
        assert results[0].title == "SerpAPI Result"
        assert results[0].url == "https://serpapi-example.com/page"
        assert results[0].published_date == "2025-06-15"

    @patch("app.services.search.asyncio.sleep", new_callable=AsyncMock)
    @patch("app.services.search.settings")
    async def test_freshness_maps_to_tbs(self, mock_settings, mock_sleep):
        mock_settings.SERP_API_KEY = "test-key"
        provider = SerpAPIProvider()
        provider.api_key = "test-key"

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"organic_results": []}

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        provider._client = mock_client

        await provider.search("query", freshness="pd")

        # Verify the tbs param was "qdr:d"
        call_kwargs = mock_client.get.call_args
        params = call_kwargs.kwargs.get("params") or call_kwargs[1].get("params")
        assert params["tbs"] == "qdr:d"

    @patch("app.services.search.asyncio.sleep", new_callable=AsyncMock)
    @patch("app.services.search.settings")
    async def test_timeout_returns_empty(self, mock_settings, mock_sleep):
        mock_settings.SERP_API_KEY = "test-key"
        provider = SerpAPIProvider()
        provider.api_key = "test-key"

        mock_client = AsyncMock()
        mock_client.get.side_effect = httpx.TimeoutException("timed out")
        provider._client = mock_client

        results = await provider.search("test query")
        assert results == []


# ===========================================================================
# SerperProvider  (3 tests)
# ===========================================================================


class TestSerperProvider:

    @patch("app.services.search.asyncio.sleep", new_callable=AsyncMock)
    @patch("app.services.search.settings")
    async def test_success_parses_organic(self, mock_settings, mock_sleep):
        mock_settings.SERPER_API_KEY = "test-key"
        provider = SerperProvider()
        provider.api_key = "test-key"

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "organic": [
                {
                    "title": "Serper Result",
                    "link": "https://serper-example.com/page",
                    "snippet": "Serper snippet",
                    "date": "2025-03-10",
                },
            ]
        }

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        provider._client = mock_client

        results = await provider.search("test query")
        assert len(results) == 1
        assert results[0].title == "Serper Result"
        assert results[0].url == "https://serper-example.com/page"

    @patch("app.services.search.asyncio.sleep", new_callable=AsyncMock)
    @patch("app.services.search.settings")
    async def test_post_body_shape(self, mock_settings, mock_sleep):
        mock_settings.SERPER_API_KEY = "test-key"
        provider = SerperProvider()
        provider.api_key = "test-key"

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"organic": []}

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        provider._client = mock_client

        await provider.search("my query", freshness="pw")

        call_args = mock_client.post.call_args
        # Verify POST body
        json_body = call_args.kwargs.get("json") or call_args[1].get("json")
        assert json_body["q"] == "my query"
        assert json_body["tbs"] == "qdr:w"
        # Verify X-API-KEY header
        headers = call_args.kwargs.get("headers") or call_args[1].get("headers")
        assert headers["X-API-KEY"] == "test-key"

    @patch("app.services.search.asyncio.sleep", new_callable=AsyncMock)
    @patch("app.services.search.settings")
    async def test_error_returns_empty(self, mock_settings, mock_sleep):
        mock_settings.SERPER_API_KEY = "test-key"
        provider = SerperProvider()
        provider.api_key = "test-key"

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "500 Server Error",
            request=MagicMock(),
            response=mock_response,
        )

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        provider._client = mock_client

        results = await provider.search("test query")
        assert results == []


# ===========================================================================
# SearchService orchestration  (5 tests)
# ===========================================================================


class TestSearchServiceOrchestration:

    def _make_result(self, title="r", url="https://example.com"):
        return SearchResult(
            title=title,
            url=url,
            snippet="s",
        )

    async def test_first_provider_succeeds(self):
        service = _make_service_no_providers()
        mock_p1 = AsyncMock()
        mock_p1.search = AsyncMock(return_value=[self._make_result()])
        mock_p1.__class__.__name__ = "Provider1"
        mock_p2 = AsyncMock()
        mock_p2.search = AsyncMock(return_value=[])
        mock_p2.__class__.__name__ = "Provider2"
        service.providers = [mock_p1, mock_p2]

        results = await service.search_for_evidence("test claim")
        assert len(results) == 1
        mock_p2.search.assert_not_called()

    async def test_first_empty_falls_to_second(self):
        service = _make_service_no_providers()
        mock_p1 = AsyncMock()
        mock_p1.search = AsyncMock(return_value=[])
        mock_p1.__class__.__name__ = "Provider1"
        mock_p2 = AsyncMock()
        mock_p2.search = AsyncMock(return_value=[self._make_result()])
        mock_p2.__class__.__name__ = "Provider2"
        service.providers = [mock_p1, mock_p2]

        results = await service.search_for_evidence("test claim")
        assert len(results) == 1
        mock_p2.search.assert_called()

    async def test_all_empty_returns_empty(self):
        service = _make_service_no_providers()
        mock_p1 = AsyncMock()
        mock_p1.search = AsyncMock(return_value=[])
        mock_p1.__class__.__name__ = "Provider1"
        service.providers = [mock_p1]

        results = await service.search_for_evidence("clean claim no negatives")
        assert results == []

    async def test_exclusion_retry(self):
        """When first pass with exclusions returns 0, retries without exclusions."""
        service = _make_service_no_providers()
        call_count = 0

        async def side_effect(query, **kwargs):
            nonlocal call_count
            call_count += 1
            if "-site:" in query:
                return []
            return [self._make_result()]

        mock_p = MagicMock()
        mock_p.__class__.__name__ = "Provider1"
        mock_p.search = AsyncMock(side_effect=side_effect)
        service.providers = [mock_p]

        results = await service.search_for_evidence("some claim")
        assert len(results) == 1
        # Called at least twice — once with exclusions, once without
        assert call_count >= 2

    def test_get_query_without_exclusions(self):
        service = _make_service_no_providers()
        q = "earth is flat -site:snopes.com -site:factcheck.org"
        result = service._get_query_without_exclusions(q)
        assert result == "earth is flat"
        assert "-site:" not in result


# ===========================================================================
# warmup_search_providers  (2 tests)
# ===========================================================================


class TestWarmupSearchProviders:

    def test_sets_timestamps_when_zero(self):
        # Precondition: all are 0 (reset by autouse fixture)
        assert search_module._brave_last_request_time == 0
        assert search_module._serpapi_last_request_time == 0
        assert search_module._serper_last_request_time == 0

        warmup_search_providers()

        assert search_module._brave_last_request_time > 0
        assert search_module._serpapi_last_request_time > 0
        assert search_module._serper_last_request_time > 0

    def test_idempotent_when_already_set(self):
        # Pre-set to a known value
        search_module._brave_last_request_time = 42.0
        search_module._serpapi_last_request_time = 42.0
        search_module._serper_last_request_time = 42.0

        warmup_search_providers()

        # Should remain unchanged
        assert search_module._brave_last_request_time == 42.0
        assert search_module._serpapi_last_request_time == 42.0
        assert search_module._serper_last_request_time == 42.0


class TestSearchMeterIsActuallyWired:
    """The seam, not the halves.

    The meter and the providers were each unit-tested in isolation. That is
    exactly how NF-18 hid — both halves green, the wire between them dead. These
    tests drive the REAL provider request path and assert the tally moved.
    """

    @patch("app.services.search.asyncio.sleep", new_callable=AsyncMock)
    @patch("app.services.search.settings")
    async def test_serper_records_two_credits_for_a_claim_lane_query(
        self, mock_settings, mock_sleep
    ):
        from app.core.search_meter import meter_searches, snapshot

        mock_settings.SERPER_API_KEY = "test-key"
        provider = SerperProvider()
        provider.api_key = "test-key"

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"organic": []}
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        provider._client = mock_client

        with meter_searches():
            # 13 = retrieve.CLAIM_LANE_MAX_RESULTS_PER_QUERY
            await provider.search("test query", max_results=13)
            snap = snapshot()

        assert snap["queries_by_provider"] == {"serper": 1}
        assert snap["billable_units_by_provider"] == {"serper": 2}

    @patch("app.services.search.asyncio.sleep", new_callable=AsyncMock)
    @patch("app.services.search.settings")
    async def test_serper_records_one_credit_for_an_element_lane_query(
        self, mock_settings, mock_sleep
    ):
        from app.core.search_meter import meter_searches, snapshot

        mock_settings.SERPER_API_KEY = "test-key"
        provider = SerperProvider()
        provider.api_key = "test-key"

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"organic": []}
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        provider._client = mock_client

        with meter_searches():
            # 5 = retrieve.ELEMENT_RESULTS_PER_QUERY
            await provider.search("test query", max_results=5)
            snap = snapshot()

        assert snap["billable_units_by_provider"] == {"serper": 1}

    @patch("app.services.search.asyncio.sleep", new_callable=AsyncMock)
    @patch("app.services.search.settings")
    async def test_a_query_returning_nothing_is_still_billed(
        self, mock_settings, mock_sleep
    ):
        """The provider charges for the request, not for useful results."""
        from app.core.search_meter import meter_searches, snapshot

        mock_settings.SERPER_API_KEY = "test-key"
        provider = SerperProvider()
        provider.api_key = "test-key"

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"organic": []}
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        provider._client = mock_client

        with meter_searches():
            results = await provider.search("test query", max_results=5)
            snap = snapshot()

        assert results == []
        assert snap["total_billable_units"] == 1
