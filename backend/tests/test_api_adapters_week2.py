"""
Unit Tests for Week 2 API Adapters
Phase 5: Government API Integration

Tests for the 7 new adapters implemented in Week 2:
- FRED, WHO, Met Office, CrossRef
- GOV.UK, Hansard, Wikidata
"""

import pytest
from app.services.api_adapters import (
    FREDAdapter,
    WHOAdapter,
    MetOfficeAdapter,
    CrossRefAdapter,
    GovUKAdapter,
    HansardAdapter,
    WikidataAdapter
)


class TestFREDAdapter:
    """Test suite for FRED (Federal Reserve Economic Data) adapter."""

    def test_instantiation(self):
        """Test FRED adapter instantiates correctly."""
        adapter = FREDAdapter()
        assert adapter.api_name == "FRED"
        assert "stlouisfed.org" in adapter.base_url
        assert adapter.cache_ttl == 86400 * 7  # 7 days

    def test_is_relevant_for_domain(self):
        """Test FRED domain relevance."""
        adapter = FREDAdapter()

        # Should be relevant for Finance + US
        assert adapter.is_relevant_for_domain("Finance", "US") == True
        assert adapter.is_relevant_for_domain("Finance", "Global") == True

        # Should not be relevant for other domains
        assert adapter.is_relevant_for_domain("Health", "US") == False
        assert adapter.is_relevant_for_domain("Finance", "UK") == False

    def test_transform_response(self):
        """Test FRED response transformation."""
        adapter = FREDAdapter()

        mock_response = {
            "seriess": [
                {
                    "id": "UNRATE",
                    "title": "Unemployment Rate",
                    "notes": "The unemployment rate represents...",
                    "observation_start": "1948-01-01",
                    "frequency": "Monthly",
                    "units": "Percent",
                    "seasonal_adjustment": "Seasonally Adjusted"
                }
            ]
        }

        result = adapter._transform_response(mock_response)

        assert len(result) == 1
        assert result[0]["title"] == "Unemployment Rate"
        assert result[0]["external_source_provider"] == "FRED"
        assert result[0]["metadata"]["series_id"] == "UNRATE"
        assert "fred.stlouisfed.org" in result[0]["url"]


class TestWHOAdapter:
    """Test suite for WHO (World Health Organization) adapter."""

    def test_instantiation(self):
        """Test WHO adapter instantiates correctly."""
        adapter = WHOAdapter()
        assert adapter.api_name == "WHO"
        assert "ghoapi.azureedge.net" in adapter.base_url
        assert adapter.cache_ttl == 86400 * 7  # 7 days

    def test_is_relevant_for_domain(self):
        """Test WHO domain relevance."""
        adapter = WHOAdapter()

        # Should be relevant for Health globally
        assert adapter.is_relevant_for_domain("Health", "Global") == True
        assert adapter.is_relevant_for_domain("Health", "UK") == True
        assert adapter.is_relevant_for_domain("Health", "US") == True

        # Should not be relevant for other domains
        assert adapter.is_relevant_for_domain("Finance", "Global") == False

    def test_transform_response(self):
        """Test WHO response transformation."""
        adapter = WHOAdapter()

        mock_response = {
            "indicators": [
                {
                    "IndicatorCode": "WHS9_86",
                    "IndicatorName": "Life expectancy at birth (years)",
                    "Definition": "Average number of years...",
                    "Language": "EN"
                }
            ]
        }

        result = adapter._transform_response(mock_response)

        assert len(result) == 1
        assert "Life expectancy" in result[0]["title"]
        assert result[0]["external_source_provider"] == "WHO"
        assert result[0]["metadata"]["indicator_code"] == "WHS9_86"


class TestMetOfficeAdapter:
    """Test suite for Met Office (UK Weather/Climate) adapter."""

    def test_instantiation(self):
        """Test Met Office adapter instantiates correctly."""
        adapter = MetOfficeAdapter()
        assert adapter.api_name == "Met Office"
        assert "metoffice.gov.uk" in adapter.base_url
        assert adapter.cache_ttl == 3600  # 1 hour (weather changes frequently)

    def test_is_relevant_for_domain(self):
        """Test Met Office domain relevance."""
        adapter = MetOfficeAdapter()

        # Should be relevant for Climate + UK
        assert adapter.is_relevant_for_domain("Climate", "UK") == True
        assert adapter.is_relevant_for_domain("Climate", "Global") == True

        # Should not be relevant for other domains
        assert adapter.is_relevant_for_domain("Health", "UK") == False
        assert adapter.is_relevant_for_domain("Climate", "US") == False

    def test_placeholder_evidence(self):
        """Test Met Office creates placeholder evidence."""
        adapter = MetOfficeAdapter()

        result = adapter._create_placeholder_evidence()

        assert len(result) == 1
        assert "Met Office" in result[0]["title"]
        assert result[0]["external_source_provider"] == "Met Office"


class TestCrossRefAdapter:
    """Test suite for CrossRef (Academic Research) adapter."""

    def test_instantiation(self):
        """Test CrossRef adapter instantiates correctly."""
        adapter = CrossRefAdapter()
        assert adapter.api_name == "CrossRef"
        assert "api.crossref.org" in adapter.base_url
        assert adapter.cache_ttl == 86400 * 14  # 14 days

    def test_is_relevant_for_domain(self):
        """Test CrossRef domain relevance."""
        adapter = CrossRefAdapter()

        # Should be relevant for Science globally
        assert adapter.is_relevant_for_domain("Science", "Global") == True
        assert adapter.is_relevant_for_domain("Science", "UK") == True
        assert adapter.is_relevant_for_domain("Science", "US") == True

        # Should not be relevant for other domains
        assert adapter.is_relevant_for_domain("Finance", "Global") == False

    def test_transform_response(self):
        """Test CrossRef response transformation."""
        adapter = CrossRefAdapter()

        mock_response = {
            "items": [
                {
                    "DOI": "10.1038/nature12345",
                    "title": ["Climate change impacts on global biodiversity"],
                    "abstract": "This study examines the impact...",
                    "published-print": {
                        "date-parts": [[2024, 3, 15]]
                    },
                    "publisher": "Nature Publishing Group",
                    "author": [
                        {"given": "John", "family": "Smith"},
                        {"given": "Jane", "family": "Doe"}
                    ]
                }
            ]
        }

        result = adapter._transform_response(mock_response)

        assert len(result) == 1
        assert "Climate change" in result[0]["title"]
        assert result[0]["external_source_provider"] == "CrossRef"
        assert result[0]["metadata"]["doi"] == "10.1038/nature12345"
        assert "doi.org" in result[0]["url"]


class TestGovUKAdapter:
    """Test suite for GOV.UK Content API adapter."""

    def test_instantiation(self):
        """Test GOV.UK adapter instantiates correctly."""
        adapter = GovUKAdapter()
        assert adapter.api_name == "GOV.UK Content API"
        assert "gov.uk" in adapter.base_url
        assert adapter.cache_ttl == 86400  # 1 day

    def test_is_relevant_for_domain(self):
        """Test GOV.UK domain relevance."""
        adapter = GovUKAdapter()

        # Should be relevant for Government + UK
        assert adapter.is_relevant_for_domain("Government", "UK") == True
        assert adapter.is_relevant_for_domain("Government", "Global") == True
        assert adapter.is_relevant_for_domain("General", "UK") == True

        # Should not be relevant for other jurisdictions
        assert adapter.is_relevant_for_domain("Government", "US") == False

    def test_transform_response(self):
        """Test GOV.UK response transformation."""
        adapter = GovUKAdapter()

        mock_response = {
            "results": [
                {
                    "title": "Government announces new policy",
                    "description": "The government has announced...",
                    "link": "/government/news/policy-announcement",
                    "public_timestamp": "2024-03-15T10:00:00Z",
                    "format": "news_article",
                    "organisations": ["HM Treasury"]
                }
            ]
        }

        result = adapter._transform_response(mock_response)

        assert len(result) == 1
        assert "policy" in result[0]["title"].lower()
        assert result[0]["external_source_provider"] == "GOV.UK Content API"
        assert "gov.uk" in result[0]["url"]


class TestHansardAdapter:
    """Test suite for UK Parliament Hansard adapter."""

    def test_instantiation(self):
        """Test Hansard adapter instantiates correctly."""
        adapter = HansardAdapter()
        assert adapter.api_name == "UK Parliament Hansard"
        assert "hansard-api.parliament.uk" in adapter.base_url
        assert adapter.cache_ttl == 86400 * 7  # 7 days

    def test_is_relevant_for_domain(self):
        """Test Hansard domain relevance."""
        adapter = HansardAdapter()

        # Should be relevant for Government and Law + UK
        assert adapter.is_relevant_for_domain("Government", "UK") == True
        assert adapter.is_relevant_for_domain("Law", "UK") == True
        assert adapter.is_relevant_for_domain("Government", "Global") == True

        # Should not be relevant for other domains/jurisdictions
        assert adapter.is_relevant_for_domain("Finance", "UK") == False
        assert adapter.is_relevant_for_domain("Government", "US") == False

    def test_transform_response(self):
        """Test Hansard response transformation."""
        adapter = HansardAdapter()

        mock_response = {
            "Response": {
                "Results": [
                    {
                        "Title": "Immigration Bill: Second Reading",
                        "Excerpt": "The Secretary of State spoke about...",
                        "Url": "https://hansard.parliament.uk/debates/12345",
                        "Date": "2024-03-15T14:30:00Z",
                        "DebateType": "Commons",
                        "Member": "The Prime Minister"
                    }
                ]
            }
        }

        result = adapter._transform_response(mock_response)

        assert len(result) == 1
        assert "Immigration Bill" in result[0]["title"]
        assert result[0]["external_source_provider"] == "UK Parliament Hansard"
        assert "hansard.parliament.uk" in result[0]["url"]


class TestWikidataAdapter:
    """Test suite for Wikidata adapter."""

    def test_instantiation(self):
        """Test Wikidata adapter instantiates correctly."""
        adapter = WikidataAdapter()
        assert adapter.api_name == "Wikidata"
        assert "wikidata.org" in adapter.base_url
        assert adapter.cache_ttl == 86400 * 30  # 30 days

    def test_is_relevant_for_domain(self):
        """Test Wikidata domain relevance."""
        adapter = WikidataAdapter()

        # Should be relevant for General only
        assert adapter.is_relevant_for_domain("General", "Global") == True
        assert adapter.is_relevant_for_domain("General", "UK") == True

        # Should not be relevant for specific domains
        assert adapter.is_relevant_for_domain("Finance", "Global") == False
        assert adapter.is_relevant_for_domain("Health", "Global") == False

    def test_transform_response(self):
        """Test Wikidata response transformation."""
        adapter = WikidataAdapter()

        mock_response = {
            "search": [
                {
                    "id": "Q42",
                    "label": "Douglas Adams",
                    "description": "English author and humorist",
                    "concepturi": "http://www.wikidata.org/entity/Q42"
                }
            ]
        }

        result = adapter._transform_response(mock_response)

        assert len(result) == 1
        assert "Douglas Adams" in result[0]["title"]
        assert result[0]["external_source_provider"] == "Wikidata"
        assert result[0]["metadata"]["entity_id"] == "Q42"
        assert "wikidata.org/wiki/Q42" in result[0]["url"]


class TestAdapterRegistry:
    """Test that all Week 2 adapters integrate with the registry."""

    def test_all_adapters_registered(self):
        """Test that all adapters can be registered."""
        from app.services.government_api_client import APIAdapterRegistry

        registry = APIAdapterRegistry()

        # Register all Week 2 adapters
        adapters = [
            FREDAdapter(),
            WHOAdapter(),
            MetOfficeAdapter(),
            CrossRefAdapter(),
            GovUKAdapter(),
            HansardAdapter(),
            WikidataAdapter()
        ]

        for adapter in adapters:
            registry.register(adapter)

        # Verify all registered
        assert len(registry.get_all_adapters()) == 7

    def test_get_adapters_for_finance_us(self):
        """Test getting relevant adapters for Finance + US domain."""
        from app.services.government_api_client import APIAdapterRegistry

        registry = APIAdapterRegistry()
        registry.register(FREDAdapter())
        registry.register(WHOAdapter())
        registry.register(CrossRefAdapter())

        relevant = registry.get_adapters_for_domain("Finance", "US")

        # Should only return FRED
        assert len(relevant) == 1
        assert relevant[0].api_name == "FRED"

    def test_get_adapters_for_health_global(self):
        """Test getting relevant adapters for Health + Global domain."""
        from app.services.government_api_client import APIAdapterRegistry

        registry = APIAdapterRegistry()
        registry.register(WHOAdapter())
        registry.register(FREDAdapter())
        registry.register(WikidataAdapter())

        relevant = registry.get_adapters_for_domain("Health", "Global")

        # Should only return WHO
        assert len(relevant) == 1
        assert relevant[0].api_name == "WHO"

    def test_get_adapters_for_government_uk(self):
        """Test getting relevant adapters for Government + UK domain."""
        from app.services.government_api_client import APIAdapterRegistry

        registry = APIAdapterRegistry()
        registry.register(GovUKAdapter())
        registry.register(HansardAdapter())
        registry.register(FREDAdapter())

        relevant = registry.get_adapters_for_domain("Government", "UK")

        # Should return GOV.UK and Hansard
        assert len(relevant) == 2
        api_names = {a.api_name for a in relevant}
        assert "GOV.UK Content API" in api_names
        assert "UK Parliament Hansard" in api_names


class TestCommonAdapterFeatures:
    """Test common features across all Week 2 adapters."""

    @pytest.mark.parametrize("adapter_class", [
        FREDAdapter,
        WHOAdapter,
        MetOfficeAdapter,
        CrossRefAdapter,
        GovUKAdapter,
        HansardAdapter,
        WikidataAdapter
    ])
    def test_adapter_has_required_methods(self, adapter_class):
        """Test each adapter implements required methods."""
        adapter = adapter_class()

        assert hasattr(adapter, 'search')
        assert hasattr(adapter, '_transform_response')
        assert hasattr(adapter, 'is_relevant_for_domain')
        assert callable(adapter.search)
        assert callable(adapter._transform_response)
        assert callable(adapter.is_relevant_for_domain)

    @pytest.mark.parametrize("adapter_class", [
        FREDAdapter,
        WHOAdapter,
        MetOfficeAdapter,
        CrossRefAdapter,
        GovUKAdapter,
        HansardAdapter,
        WikidataAdapter
    ])
    def test_adapter_has_correct_attributes(self, adapter_class):
        """Test each adapter has correct attributes."""
        adapter = adapter_class()

        assert hasattr(adapter, 'api_name')
        assert hasattr(adapter, 'base_url')
        assert hasattr(adapter, 'cache_ttl')
        assert hasattr(adapter, 'timeout')
        assert hasattr(adapter, 'max_results')

        assert isinstance(adapter.api_name, str)
        assert isinstance(adapter.base_url, str)
        assert isinstance(adapter.cache_ttl, int)
        assert adapter.cache_ttl > 0

    @pytest.mark.parametrize("adapter_class", [
        FREDAdapter,
        WHOAdapter,
        MetOfficeAdapter,
        CrossRefAdapter,
        GovUKAdapter,
        HansardAdapter,
        WikidataAdapter
    ])
    def test_adapter_creates_valid_evidence_dict(self, adapter_class):
        """Test each adapter creates valid evidence dictionaries."""
        adapter = adapter_class()

        # Create test evidence
        evidence = adapter._create_evidence_dict(
            title="Test Title",
            snippet="Test snippet",
            url="https://example.com",
            source_date=None,
            metadata={"test": "data"}
        )

        # Verify required fields
        assert "title" in evidence
        assert "snippet" in evidence
        assert "url" in evidence
        assert "source" in evidence
        assert "external_source_provider" in evidence
        assert "credibility_score" in evidence
        assert "metadata" in evidence

        # Verify values
        assert evidence["title"] == "Test Title"
        assert evidence["snippet"] == "Test snippet"
        assert evidence["url"] == "https://example.com"
        assert evidence["external_source_provider"] == adapter.api_name
        assert evidence["credibility_score"] == 0.95
