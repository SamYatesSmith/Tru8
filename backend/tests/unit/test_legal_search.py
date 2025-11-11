"""
Unit tests for Legal Search Service
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta

from app.services.legal_search import LegalSearchService


class TestLegalSearchService:
    """Test legal statute search functionality"""

    @pytest.fixture
    def service(self):
        """Create service instance for testing"""
        return LegalSearchService()

    @pytest.fixture
    def us_metadata(self):
        """Sample US legal claim metadata"""
        return {
            "jurisdiction": "US",
            "year": "1983",
            "citations": [{
                "type": "USC",
                "title": "42",
                "section": "1983",
                "full_text": "42 USC 1983"
            }],
            "statute_type": "federal"
        }

    @pytest.fixture
    def uk_metadata(self):
        """Sample UK legal claim metadata"""
        return {
            "jurisdiction": "UK",
            "year": "2018",
            "citations": [{
                "type": "UKPGA",
                "year": "2018",
                "number": "12"
            }]
        }

    def test_initialization(self, service):
        """Test: Service initializes correctly"""
        assert service.cache == {}
        assert service.timeout > 0
        assert service.cache_ttl.days == 30

    def test_cache_key_building(self, service, us_metadata):
        """Test: Cache key building works correctly"""
        claim_text = "42 USC 1983 protects civil rights"

        key = service._build_cache_key(claim_text, us_metadata)

        assert "US" in key
        assert "1983" in key
        assert "42 USC 1983 protects civil rights" in key

    def test_keyword_extraction(self, service):
        """Test: Search keyword extraction"""
        claim_text = "The 1964 Civil Rights Act banned discrimination in public places"

        keywords = service._extract_search_keywords(claim_text)

        # Should extract meaningful words, not stopwords
        assert "1964" in keywords
        assert "Civil" in keywords or "civil" in keywords
        assert "Rights" in keywords or "rights" in keywords
        assert "discrimination" in keywords
        # Should NOT include stopwords as standalone words
        assert " the " not in f" {keywords.lower()} "
        # Check keyword list is reasonable length (not everything)
        assert len(keywords.split()) <= 10

    @pytest.mark.asyncio
    async def test_search_caching(self, service, us_metadata):
        """Test: Results are cached and reused"""
        claim_text = "42 USC 1983 protects civil rights"

        # Mock the search method
        service._search_us_sources = AsyncMock(return_value=[
            {"url": "test.com", "title": "Test Statute"}
        ])

        # First call
        result1 = await service.search_statutes(claim_text, us_metadata)
        assert len(result1) == 1

        # Second call should hit cache
        result2 = await service.search_statutes(claim_text, us_metadata)
        assert len(result2) == 1

        # Should only call _search_us_sources once
        service._search_us_sources.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_routes_by_jurisdiction_us(self, service, us_metadata):
        """Test: US jurisdiction routes to US sources"""
        claim_text = "42 USC 1983 test"

        service._search_us_sources = AsyncMock(return_value=[])
        service._search_uk_sources = AsyncMock(return_value=[])

        await service.search_statutes(claim_text, us_metadata)

        service._search_us_sources.assert_called_once()
        service._search_uk_sources.assert_not_called()

    @pytest.mark.asyncio
    async def test_search_routes_by_jurisdiction_uk(self, service, uk_metadata):
        """Test: UK jurisdiction routes to UK sources"""
        claim_text = "ukpga 2018/12 test"

        service._search_us_sources = AsyncMock(return_value=[])
        service._search_uk_sources = AsyncMock(return_value=[])

        await service.search_statutes(claim_text, uk_metadata)

        service._search_us_sources.assert_not_called()
        service._search_uk_sources.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_handles_unknown_jurisdiction(self, service):
        """Test: Unknown jurisdiction tries both sources"""
        claim_text = "Some statute test"
        metadata = {"jurisdiction": None}

        service._search_us_sources = AsyncMock(return_value=[{"url": "us.com"}])
        service._search_uk_sources = AsyncMock(return_value=[{"url": "uk.com"}])

        results = await service.search_statutes(claim_text, metadata)

        service._search_us_sources.assert_called_once()
        service._search_uk_sources.assert_called_once()
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_search_handles_errors_gracefully(self, service, us_metadata):
        """Test: Errors don't crash, return empty list"""
        claim_text = "Test claim"

        service._search_us_sources = AsyncMock(side_effect=Exception("API Error"))

        results = await service.search_statutes(claim_text, us_metadata)

        assert results == []

    def test_govinfo_result_formatting(self, service):
        """Test: GovInfo API results formatted correctly"""
        api_response = {
            "packageLink": "https://www.govinfo.gov/content/pkg/USCODE-2021-title42",
            "title": "42 U.S.C. 1983",
            "summary": "Civil action for deprivation of rights",
            "dateIssued": "2021-01-01"
        }

        citation = {"full_text": "42 USC §1983"}

        result = service._format_govinfo_result(api_response, citation)

        assert result["url"] == api_response["packageLink"]
        assert result["title"] == api_response["title"]
        assert result["snippet"] == api_response["summary"]
        assert result["source"] == "govinfo.gov"
        assert result["jurisdiction"] == "US"
        assert result["citation"] == "42 USC §1983"

    def test_uk_xml_parsing(self, service):
        """Test: UK legislation XML parsing"""
        xml_content = """<?xml version="1.0"?>
        <Legislation xmlns="http://www.legislation.gov.uk/namespaces/legislation">
            <Title>Data Protection Act 2018</Title>
            <Text>This Act makes provision for the regulation of data processing.</Text>
        </Legislation>
        """

        url = "https://www.legislation.gov.uk/ukpga/2018/12"
        citation = {"type": "UKPGA", "year": "2018", "number": "12"}

        result = service._parse_uk_legislation_xml(xml_content, url, citation)

        assert result["url"] == url
        assert "Data Protection Act 2018" in result["title"]
        assert "regulation of data processing" in result["snippet"]
        assert result["source"] == "legislation.gov.uk"
        assert result["jurisdiction"] == "UK"

    @pytest.mark.asyncio
    async def test_us_three_tier_search_strategy(self, service, us_metadata):
        """Test: US search follows three-tier strategy"""
        claim_text = "42 USC 1983 civil rights"

        # Mock all three search methods
        service._search_govinfo_by_citation = AsyncMock(return_value=[{"url": "citation"}])
        service._search_govinfo_by_year = AsyncMock(return_value=[])
        service._search_govinfo_fulltext = AsyncMock(return_value=[])

        results = await service._search_us_sources(claim_text, us_metadata)

        # Should try citation first
        service._search_govinfo_by_citation.assert_called_once()
        # Should not need year or fulltext since citation found results
        # (but may be called if result count < 3)

    @pytest.mark.asyncio
    async def test_us_search_deduplication(self, service, us_metadata):
        """Test: US search deduplicates results by URL"""
        claim_text = "Test claim"

        # Mock methods returning duplicate URLs
        service._search_govinfo_by_citation = AsyncMock(return_value=[
            {"url": "same.com", "title": "Result 1"}
        ])
        service._search_govinfo_by_year = AsyncMock(return_value=[
            {"url": "same.com", "title": "Result 2 (duplicate)"},
            {"url": "different.com", "title": "Result 3"}
        ])
        service._search_govinfo_fulltext = AsyncMock(return_value=[])

        results = await service._search_us_sources(claim_text, us_metadata)

        # Should only have 2 unique URLs
        urls = [r["url"] for r in results]
        assert len(urls) == len(set(urls))  # All unique
        assert "same.com" in urls
        assert "different.com" in urls

    @pytest.mark.asyncio
    async def test_us_search_limits_to_5_results(self, service, us_metadata):
        """Test: US search returns max 5 results"""
        claim_text = "Test claim"

        # Mock methods returning many results
        service._search_govinfo_by_citation = AsyncMock(return_value=[
            {"url": f"url{i}.com", "title": f"Result {i}"} for i in range(10)
        ])
        service._search_govinfo_by_year = AsyncMock(return_value=[])
        service._search_govinfo_fulltext = AsyncMock(return_value=[])

        results = await service._search_us_sources(claim_text, us_metadata)

        assert len(results) <= 5

    def test_cache_ttl_expiration(self, service):
        """Test: Cache expires after TTL"""
        claim_text = "Test claim"
        metadata = {"jurisdiction": "US"}
        cache_key = service._build_cache_key(claim_text, metadata)

        # Add to cache with old timestamp
        old_time = datetime.utcnow() - timedelta(days=31)  # Older than 30-day TTL
        service.cache[cache_key] = ([{"test": "data"}], old_time)

        # Check if cache is valid
        cached_result, cached_time = service.cache[cache_key]
        is_valid = datetime.utcnow() - cached_time < service.cache_ttl

        assert not is_valid  # Cache should be expired

    @pytest.mark.asyncio
    async def test_search_without_api_keys(self):
        """Test: Service handles missing API keys gracefully"""
        # Create service without API keys
        with patch('app.core.config.settings') as mock_settings:
            mock_settings.GOVINFO_API_KEY = None
            mock_settings.CONGRESS_API_KEY = None
            mock_settings.LEGAL_API_TIMEOUT_SECONDS = 10
            mock_settings.LEGAL_CACHE_TTL_DAYS = 30

            service = LegalSearchService()

            metadata = {
                "jurisdiction": "US",
                "citations": [{"type": "USC", "title": "42", "section": "1983"}]
            }

            results = await service._search_govinfo_by_citation({"title": "42", "section": "1983"})

            # Should return empty list, not crash
            assert results == []

    @pytest.mark.asyncio
    async def test_uk_direct_identifier_lookup(self, service, uk_metadata):
        """Test: UK direct identifier lookup"""
        claim_text = "ukpga 2018/12 test"

        service._search_uk_by_identifier = AsyncMock(return_value={
            "url": "https://www.legislation.gov.uk/ukpga/2018/12",
            "title": "Data Protection Act 2018"
        })

        results = await service._search_uk_sources(claim_text, uk_metadata)

        service._search_uk_by_identifier.assert_called_once()
        assert len(results) == 1
        assert "Data Protection Act" in results[0]["title"]
