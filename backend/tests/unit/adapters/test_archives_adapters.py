"""
Unit Tests for Archives API Adapters

Tests for the 3 archive adapters:
- Wikipedia (MediaWiki REST API)
- Library of Congress (historical documents + Chronicling America)
- Internet Archive (archive.org collections)
"""

import pytest
from app.services.api_adapters import (
    WikipediaAdapter,
    LibraryOfCongressAdapter,
    InternetArchiveAdapter,
)


class TestWikipediaAdapter:
    """Test suite for Wikipedia (MediaWiki REST API) adapter."""

    def test_instantiation(self):
        """Test Wikipedia adapter instantiates correctly."""
        adapter = WikipediaAdapter()
        assert adapter.api_name == "Wikipedia"
        assert "en.wikipedia.org" in adapter.base_url
        assert adapter.cache_ttl == 86400  # 1 day (default)

    def test_is_relevant_for_domain(self):
        """Test Wikipedia domain relevance."""
        adapter = WikipediaAdapter()

        # Should be relevant for encyclopaedic domains
        assert adapter.is_relevant_for_domain("History", "Global") == True
        assert adapter.is_relevant_for_domain("Politics", "UK") == True
        assert adapter.is_relevant_for_domain("Entertainment", "US") == True
        assert adapter.is_relevant_for_domain("General", "Global") == True
        assert adapter.is_relevant_for_domain("Sports", "Global") == True
        assert adapter.is_relevant_for_domain("Science", "Global") == True
        assert adapter.is_relevant_for_domain("Animals", "Global") == True
        assert adapter.is_relevant_for_domain("Climate", "Global") == True
        assert adapter.is_relevant_for_domain("Health", "Global") == True

        # Should not be relevant for domains not in its list
        assert adapter.is_relevant_for_domain("Finance", "Global") == False
        assert adapter.is_relevant_for_domain("Law", "UK") == False

    def test_transform_response(self):
        """Test Wikipedia _transform_response returns empty (search handles transformation)."""
        adapter = WikipediaAdapter()

        mock_response = {
            "query": {
                "search": [
                    {
                        "title": "Climate change",
                        "snippet": "Climate change includes both human-driven...",
                        "timestamp": "2024-03-15T10:00:00Z",
                    }
                ]
            }
        }

        # Wikipedia's _transform_response is a no-op; transformation happens in search()
        result = adapter._transform_response(mock_response)
        assert result == []

    def test_empty_response(self):
        """Test Wikipedia _transform_response returns [] for empty/None input."""
        adapter = WikipediaAdapter()

        assert adapter._transform_response(None) == []
        assert adapter._transform_response({}) == []
        assert adapter._transform_response([]) == []


class TestLibraryOfCongressAdapter:
    """Test suite for Library of Congress adapter."""

    def test_instantiation(self):
        """Test Library of Congress adapter instantiates correctly."""
        adapter = LibraryOfCongressAdapter()
        assert adapter.api_name == "Library of Congress"
        assert "loc.gov" in adapter.base_url
        assert adapter.cache_ttl == 86400 * 7  # 7 days

    def test_is_relevant_for_domain(self):
        """Test Library of Congress domain relevance."""
        adapter = LibraryOfCongressAdapter()

        # Should be relevant for History, Politics, General
        assert adapter.is_relevant_for_domain("History", "US") == True
        assert adapter.is_relevant_for_domain("Politics", "Global") == True
        assert adapter.is_relevant_for_domain("General", "UK") == True

        # Should not be relevant for other domains
        assert adapter.is_relevant_for_domain("Finance", "US") == False
        assert adapter.is_relevant_for_domain("Health", "Global") == False
        assert adapter.is_relevant_for_domain("Science", "US") == False

    def test_transform_response(self):
        """Test Library of Congress _transform_response returns empty (search handles transformation)."""
        adapter = LibraryOfCongressAdapter()

        mock_response = {
            "results": [
                {
                    "title": "Declaration of Independence",
                    "description": ["The Declaration of Independence..."],
                    "url": "/resource/bdsdcc.02101/",
                    "date": "1776-07-04",
                    "partof": ["American Treasures"],
                    "original_format": ["manuscript"],
                    "contributor": ["Thomas Jefferson"],
                    "subject": ["United States -- Politics and government"],
                }
            ]
        }

        # Library of Congress's _transform_response is a no-op; transformation happens in search()
        result = adapter._transform_response(mock_response)
        assert result == []

    def test_empty_response(self):
        """Test Library of Congress _transform_response returns [] for empty/None input."""
        adapter = LibraryOfCongressAdapter()

        assert adapter._transform_response(None) == []
        assert adapter._transform_response({}) == []
        assert adapter._transform_response([]) == []

    def test_sc04_timeout_is_10s(self):
        """SC-04: timeout bumped from 5s to 10s to accommodate Chronicling America's
        legitimate 8s latency under at=results. 5s produced 100% timeout."""
        adapter = LibraryOfCongressAdapter()
        assert adapter.timeout == 10, (
            f"SC-04 regression: timeout is {adapter.timeout}s, expected 10s. "
            f"Lowering this below 10s risks reintroducing 100% Chronicling America timeouts."
        )

    def test_sc04_collections_drops_narrow_format_filter(self):
        """SC-04: _search_loc_collections must NOT pass fa=original-format:book|... .
        That filter returned 0 results for common history queries (e.g. Marshall Plan)
        because it excluded LoC's curated web exhibit pages, which are primary sources.
        """
        import inspect

        source = inspect.getsource(LibraryOfCongressAdapter._search_loc_collections)
        # Match the params-dict entry specifically, not the comment explaining why it was dropped
        assert '"fa": "original-format' not in source, (
            "SC-04 regression: _search_loc_collections reintroduced the narrow "
            "format filter in the params dict. This excluded LoC's best curated "
            "content (web exhibit pages) and returned 0 results for Marshall "
            "Plan and similar claims."
        )

    def test_sc04_both_searches_use_at_results_trim(self):
        """SC-04: both LoC search methods must pass at=results to trim payload.
        Raw response is 1.8MB per 5 results; at=results cuts to ~22KB (99% smaller,
        33% faster). Without this trim Chronicling America exceeds the 10s timeout."""
        import inspect

        collections_source = inspect.getsource(
            LibraryOfCongressAdapter._search_loc_collections
        )
        chronicling_source = inspect.getsource(
            LibraryOfCongressAdapter._search_chronicling_america
        )
        assert '"at": "results"' in collections_source, (
            "SC-04 regression: _search_loc_collections dropped at=results param. "
            "Response payload will balloon to ~1.8MB; pipeline latency increases."
        )
        assert '"at": "results"' in chronicling_source, (
            "SC-04 regression: _search_chronicling_america dropped at=results param. "
            "Chronicling America will exceed the 10s adapter timeout and fail 100%."
        )


class TestInternetArchiveAdapter:
    """Test suite for Internet Archive adapter."""

    def test_instantiation(self):
        """Test Internet Archive adapter instantiates correctly."""
        adapter = InternetArchiveAdapter()
        assert adapter.api_name == "Internet Archive"
        assert "archive.org" in adapter.base_url
        assert adapter.cache_ttl == 86400 * 7  # 7 days

    def test_is_relevant_for_domain(self):
        """Test Internet Archive domain relevance."""
        adapter = InternetArchiveAdapter()

        # Should be relevant for History, General, Politics, Entertainment, Science
        assert adapter.is_relevant_for_domain("History", "Global") == True
        assert adapter.is_relevant_for_domain("General", "US") == True
        assert adapter.is_relevant_for_domain("Politics", "UK") == True
        assert adapter.is_relevant_for_domain("Entertainment", "Global") == True
        assert adapter.is_relevant_for_domain("Science", "Global") == True

        # Should not be relevant for other domains
        assert adapter.is_relevant_for_domain("Finance", "Global") == False
        assert adapter.is_relevant_for_domain("Health", "US") == False
        assert adapter.is_relevant_for_domain("Law", "UK") == False

    def test_transform_response(self):
        """Test Internet Archive _transform_response returns empty (search handles transformation)."""
        adapter = InternetArchiveAdapter()

        mock_response = {
            "response": {
                "docs": [
                    {
                        "identifier": "greatgatsby1925",
                        "title": "The Great Gatsby",
                        "description": "A novel by F. Scott Fitzgerald...",
                        "date": "1925-04-10",
                        "creator": "F. Scott Fitzgerald",
                        "mediatype": "texts",
                        "collection": ["americana"],
                    }
                ]
            }
        }

        # Internet Archive's _transform_response is a no-op; transformation happens in search()
        result = adapter._transform_response(mock_response)
        assert result == []

    def test_empty_response(self):
        """Test Internet Archive _transform_response returns [] for empty/None input."""
        adapter = InternetArchiveAdapter()

        assert adapter._transform_response(None) == []
        assert adapter._transform_response({}) == []
        assert adapter._transform_response([]) == []


class TestArchiveAdapterRegistry:
    """Test that all archive adapters integrate with the registry."""

    def test_all_adapters_registered(self):
        """Test that all archive adapters can be registered."""
        from app.services.government_api_client import APIAdapterRegistry

        registry = APIAdapterRegistry()

        adapters = [
            WikipediaAdapter(),
            LibraryOfCongressAdapter(),
            InternetArchiveAdapter(),
        ]

        for adapter in adapters:
            registry.register(adapter)

        assert len(registry.get_all_adapters()) == 3

    def test_get_adapters_for_history_global(self):
        """Test getting relevant adapters for History + Global domain."""
        from app.services.government_api_client import APIAdapterRegistry

        registry = APIAdapterRegistry()
        registry.register(WikipediaAdapter())
        registry.register(LibraryOfCongressAdapter())
        registry.register(InternetArchiveAdapter())

        relevant = registry.get_adapters_for_domain("History", "Global")

        # All three should be relevant for History
        assert len(relevant) == 3
        api_names = {a.api_name for a in relevant}
        assert "Wikipedia" in api_names
        assert "Library of Congress" in api_names
        assert "Internet Archive" in api_names

    def test_get_adapters_for_finance_global(self):
        """Test getting relevant adapters for Finance + Global (none relevant)."""
        from app.services.government_api_client import APIAdapterRegistry

        registry = APIAdapterRegistry()
        registry.register(WikipediaAdapter())
        registry.register(LibraryOfCongressAdapter())
        registry.register(InternetArchiveAdapter())

        relevant = registry.get_adapters_for_domain("Finance", "Global")

        # None of the archive adapters cover Finance
        assert len(relevant) == 0


class TestCommonArchiveAdapterFeatures:
    """Test common features across all archive adapters."""

    @pytest.mark.parametrize(
        "adapter_class",
        [
            WikipediaAdapter,
            LibraryOfCongressAdapter,
            InternetArchiveAdapter,
        ],
    )
    def test_adapter_has_required_methods(self, adapter_class):
        """Test each adapter implements required methods."""
        adapter = adapter_class()

        assert hasattr(adapter, "search")
        assert hasattr(adapter, "_transform_response")
        assert hasattr(adapter, "is_relevant_for_domain")
        assert callable(adapter.search)
        assert callable(adapter._transform_response)
        assert callable(adapter.is_relevant_for_domain)

    @pytest.mark.parametrize(
        "adapter_class",
        [
            WikipediaAdapter,
            LibraryOfCongressAdapter,
            InternetArchiveAdapter,
        ],
    )
    def test_adapter_has_correct_attributes(self, adapter_class):
        """Test each adapter has correct attributes."""
        adapter = adapter_class()

        assert hasattr(adapter, "api_name")
        assert hasattr(adapter, "base_url")
        assert hasattr(adapter, "cache_ttl")
        assert hasattr(adapter, "timeout")
        assert hasattr(adapter, "max_results")

        assert isinstance(adapter.api_name, str)
        assert isinstance(adapter.base_url, str)
        assert isinstance(adapter.cache_ttl, int)
        assert adapter.cache_ttl > 0

    @pytest.mark.parametrize(
        "adapter_class",
        [
            WikipediaAdapter,
            LibraryOfCongressAdapter,
            InternetArchiveAdapter,
        ],
    )
    def test_adapter_creates_valid_evidence_dict(self, adapter_class):
        """Test each adapter creates valid evidence dictionaries."""
        adapter = adapter_class()

        evidence = adapter._create_evidence_dict(
            title="Test Title",
            snippet="Test snippet",
            url="https://example.com",
            source_date=None,
            metadata={"test": "data"},
        )

        # Verify required fields
        assert "title" in evidence
        assert "snippet" in evidence
        assert "url" in evidence
        assert "source" in evidence
        assert "external_source_provider" in evidence
        assert "metadata" in evidence

        # Verify values
        assert evidence["title"] == "Test Title"
        assert evidence["snippet"] == "Test snippet"
        assert evidence["url"] == "https://example.com"
        assert evidence["external_source_provider"] == adapter.api_name
