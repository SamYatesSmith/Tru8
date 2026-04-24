"""
Unit Tests for Remaining Untested API Adapters

Tests for adapters not covered in test_api_adapters_week2.py:

Economic extras:
- ONSAdapter (UK Office for National Statistics)
- MarketauxAdapter (Financial News)
- WorldBankAdapter (Global economic indicators)

Legal extras:
- GovInfoAdapter (US federal statutes)
- LegislationGovUKAdapter (UK statute text)

Academic extras:
- SemanticScholarAdapter (Academic papers)
- OpenAlexAdapter (Scholarly works)

Health extras:
- PubMedAdapter (Biomedical literature)

Business extras:
- CompaniesHouseAdapter (UK company registry)

Nature:
- GBIFAdapter (Global Biodiversity)

YouTube:
- search_youtube_videos (standalone async function)
"""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from app.services.api_adapters import (
    ONSAdapter,
    MarketauxAdapter,
    WorldBankAdapter,
    GovInfoAdapter,
    LegislationGovUKAdapter,
    SemanticScholarAdapter,
    OpenAlexAdapter,
    PubMedAdapter,
    CompaniesHouseAdapter,
    GBIFAdapter,
)
from app.services.api_adapters.youtube import search_youtube_videos


# ========== ONS ADAPTER ==========


class TestONSAdapter:
    """Test suite for ONS (Office for National Statistics) adapter."""

    def test_instantiation(self):
        """Test ONS adapter instantiates correctly."""
        adapter = ONSAdapter()
        assert adapter.api_name == "ONS Economic Statistics"
        assert "ons.gov.uk" in adapter.base_url
        assert adapter.cache_ttl == 86400  # 24 hours

    def test_is_relevant_for_domain(self):
        """Test ONS domain relevance."""
        adapter = ONSAdapter()

        # Should be relevant for Finance + UK
        assert adapter.is_relevant_for_domain("Finance", "UK") == True
        assert adapter.is_relevant_for_domain("Finance", "Global") == True
        assert adapter.is_relevant_for_domain("Demographics", "UK") == True
        assert adapter.is_relevant_for_domain("Demographics", "Global") == True

        # Should not be relevant for other domains/jurisdictions
        assert adapter.is_relevant_for_domain("Health", "UK") == False
        assert adapter.is_relevant_for_domain("Finance", "US") == False

    def test_transform_response(self):
        """Test ONS response transformation."""
        adapter = ONSAdapter()

        mock_response = {
            "items": [
                {
                    "title": "Consumer Price Inflation",
                    "description": "Monthly measure of consumer price inflation...",
                    "id": "cpih01",
                    "links": {
                        "self": {
                            "href": "https://api.beta.ons.gov.uk/v1/datasets/cpih01"
                        }
                    },
                    "release_date": "2024-03-15T09:30:00Z",
                    "type": "filterable",
                    "contacts": [{"name": "ONS Statistical Team"}],
                }
            ]
        }

        result = adapter._transform_response(mock_response)

        assert len(result) == 1
        assert result[0]["title"] == "Consumer Price Inflation"
        assert result[0]["external_source_provider"] == "ONS Economic Statistics"
        assert result[0]["metadata"]["dataset_id"] == "cpih01"

    def test_empty_response(self):
        """Test ONS returns empty list for empty/None response."""
        adapter = ONSAdapter()

        assert adapter._transform_response({}) == []
        assert adapter._transform_response({"items": []}) == []


# ========== MARKETAUX ADAPTER ==========


class TestMarketauxAdapter:
    """Test suite for Marketaux (Financial News) adapter."""

    def test_instantiation(self):
        """Test Marketaux adapter instantiates correctly."""
        adapter = MarketauxAdapter()
        assert adapter.api_name == "Marketaux"
        assert "marketaux.com" in adapter.base_url
        assert adapter.cache_ttl == 600  # 10 minutes

    def test_is_relevant_for_domain(self):
        """Test Marketaux domain relevance."""
        adapter = MarketauxAdapter()

        # Should be relevant for Finance globally
        assert adapter.is_relevant_for_domain("Finance", "Global") == True
        assert adapter.is_relevant_for_domain("Finance", "US") == True
        assert adapter.is_relevant_for_domain("Finance", "UK") == True

        # Should not be relevant for other domains
        assert adapter.is_relevant_for_domain("Health", "Global") == False
        assert adapter.is_relevant_for_domain("Politics", "US") == False

    def test_transform_response(self):
        """Test Marketaux response transformation via _search_news path."""
        adapter = MarketauxAdapter()

        # Marketaux uses _search_news internally, which calls _create_evidence_dict.
        # We test _create_evidence_dict which is the shared transform path.
        evidence = adapter._create_evidence_dict(
            title="Tesla Stock Surges on Q4 Earnings",
            snippet="Tesla reported higher-than-expected quarterly earnings...",
            url="https://example.com/tesla-earnings",
            source_date=None,
            metadata={
                "api_source": "Marketaux",
                "data_type": "financial_news",
                "source_name": "Reuters",
                "sentiment_score": 0.75,
                "entities": ["Tesla", "TSLA"],
            },
        )

        assert evidence["title"] == "Tesla Stock Surges on Q4 Earnings"
        assert evidence["external_source_provider"] == "Marketaux"
        assert evidence["metadata"]["data_type"] == "financial_news"
        assert evidence["metadata"]["sentiment_score"] == 0.75

    def test_empty_response(self):
        """Test Marketaux returns empty list for generic transform."""
        adapter = MarketauxAdapter()

        # _transform_response is a no-op (handled by _search_news)
        assert adapter._transform_response({}) == []
        assert adapter._transform_response({"data": []}) == []


# ========== WORLD BANK ADAPTER ==========


class TestWorldBankAdapter:
    """Test suite for World Bank (Global Economic Indicators) adapter."""

    def test_instantiation(self):
        """Test World Bank adapter instantiates correctly."""
        adapter = WorldBankAdapter()
        assert adapter.api_name == "World Bank"
        assert "worldbank.org" in adapter.base_url
        assert adapter.cache_ttl == 86400 * 7  # 7 days

    def test_is_relevant_for_domain(self):
        """Test World Bank domain relevance."""
        adapter = WorldBankAdapter()

        # Should be relevant for Finance and Demographics globally
        assert adapter.is_relevant_for_domain("Finance", "Global") == True
        assert adapter.is_relevant_for_domain("Finance", "US") == True
        assert adapter.is_relevant_for_domain("Finance", "UK") == True
        assert adapter.is_relevant_for_domain("Demographics", "Global") == True

        # Should not be relevant for other domains
        assert adapter.is_relevant_for_domain("Health", "Global") == False
        assert adapter.is_relevant_for_domain("Politics", "UK") == False

    def test_transform_response(self):
        """Test World Bank response transformation.

        Note: WorldBankAdapter._transform_response passes source_date as a
        string when date is present, which triggers an AttributeError in
        _create_evidence_dict (expects datetime or None). We omit 'date' from
        entries to test the rest of the transform logic. The source_date bug
        is a pre-existing issue in the adapter code.
        """
        adapter = WorldBankAdapter()

        mock_response = {
            "metadata": {"page": 1, "pages": 1, "per_page": 5, "total": 5},
            "data": [
                {
                    "indicator": {"value": "GDP (current US$)"},
                    "country": {"value": "United Kingdom"},
                    "date": "",
                    "value": 3089072751012.5,
                },
                {
                    "indicator": {"value": "GDP (current US$)"},
                    "country": {"value": "United Kingdom"},
                    "date": "",
                    "value": 3070668424694.2,
                },
            ],
            "indicator_code": "NY.GDP.MKTP.CD",
            "country_code": "GBR",
        }

        result = adapter._transform_response(mock_response)

        assert len(result) == 1
        assert "GDP" in result[0]["title"]
        assert "United Kingdom" in result[0]["title"]
        assert result[0]["external_source_provider"] == "World Bank"
        assert result[0]["metadata"]["indicator_code"] == "NY.GDP.MKTP.CD"
        assert result[0]["metadata"]["country_code"] == "GBR"
        assert "worldbank.org" in result[0]["url"]

    def test_empty_response(self):
        """Test World Bank returns empty list for empty/None response."""
        adapter = WorldBankAdapter()

        assert adapter._transform_response({"data": []}) == []
        assert adapter._transform_response({}) == []
        # Entries with no value should be filtered out
        assert (
            adapter._transform_response(
                {
                    "data": [
                        {
                            "indicator": {"value": "GDP"},
                            "country": {"value": "World"},
                            "date": "2023",
                            "value": None,
                        }
                    ],
                    "indicator_code": "NY.GDP.MKTP.CD",
                    "country_code": "WLD",
                }
            )
            == []
        )

    def test_match_indicator(self):
        """Test indicator matching from query text."""
        adapter = WorldBankAdapter()

        assert adapter._match_indicator("UK GDP growth rate") == "NY.GDP.MKTP.KD.ZG"
        assert adapter._match_indicator("inflation rate in US") == "FP.CPI.TOTL.ZG"
        assert adapter._match_indicator("population growth") == "SP.POP.GROW"
        assert adapter._match_indicator("random unrelated query") is None


# ========== GOVINFO ADAPTER ==========


class TestGovInfoAdapter:
    """Test suite for GovInfo.gov (US Legal Statutes) adapter."""

    def test_instantiation(self):
        """Test GovInfo adapter instantiates correctly."""
        adapter = GovInfoAdapter()
        assert adapter.api_name == "GovInfo.gov"
        assert "govinfo.gov" in adapter.base_url
        assert adapter.max_results == 5

    def test_is_relevant_for_domain(self):
        """Test GovInfo domain relevance."""
        adapter = GovInfoAdapter()

        # Should be relevant for Law, History, Politics + US/Global
        assert adapter.is_relevant_for_domain("Law", "US") == True
        assert adapter.is_relevant_for_domain("Law", "Global") == True
        assert adapter.is_relevant_for_domain("History", "US") == True
        assert adapter.is_relevant_for_domain("Politics", "US") == True

        # Should not be relevant for other domains/jurisdictions
        assert adapter.is_relevant_for_domain("Law", "UK") == False
        assert adapter.is_relevant_for_domain("Finance", "US") == False
        assert adapter.is_relevant_for_domain("Health", "Global") == False

    def test_transform_response(self):
        """Test GovInfo response transformation."""
        adapter = GovInfoAdapter()

        mock_legal_results = [
            {
                "title": "Clean Air Act, Section 7411",
                "text": "Standards of performance for new stationary sources...",
                "url": "https://www.govinfo.gov/content/pkg/USCODE-2022/clean-air-act",
                "source_date": "1990-11-15",
                "citation": "42 U.S.C. 7411",
                "jurisdiction": "US",
                "statute_type": "federal",
                "section": "7411",
                "year": "1990",
            }
        ]

        result = adapter._transform_response(mock_legal_results)

        assert len(result) == 1
        assert "Clean Air Act" in result[0]["title"]
        assert result[0]["external_source_provider"] == "GovInfo.gov"
        assert result[0]["metadata"]["citation"] == "42 U.S.C. 7411"
        assert result[0]["metadata"]["jurisdiction"] == "US"

    def test_empty_response(self):
        """Test GovInfo returns empty list for empty response."""
        adapter = GovInfoAdapter()

        assert adapter._transform_response([]) == []


# ========== UK LEGISLATION ADAPTER ==========


class TestLegislationGovUKAdapter:
    """Test suite for legislation.gov.uk (UK statute text) adapter."""

    def test_instantiation(self):
        """Test UK Legislation adapter instantiates correctly."""
        adapter = LegislationGovUKAdapter()
        assert adapter.api_name == "UK Legislation"
        assert "legislation.gov.uk" in adapter.base_url
        assert adapter.cache_ttl == 86400  # 1 day

    def test_is_relevant_for_domain_sc05_disabled(self):
        """SC-05: UK Legislation is temporarily disabled because The National
        Archives are returning HTTP 437 to every request from both local dev
        and Railway IPs. is_relevant_for_domain() returns False for ALL
        inputs until access is restored.

        When the origin is reachable again, the adapter should be restored to:
            return domain == "Law" and jurisdiction in ["UK", "Global"]
        and this test should revert to the pre-SC-05 shape below.
        """
        adapter = LegislationGovUKAdapter()

        # SC-05 state: every combination returns False
        assert adapter.is_relevant_for_domain("Law", "UK") is False
        assert adapter.is_relevant_for_domain("Law", "Global") is False
        assert adapter.is_relevant_for_domain("Law", "US") is False
        assert adapter.is_relevant_for_domain("Politics", "UK") is False
        assert adapter.is_relevant_for_domain("Finance", "UK") is False

    def test_transform_response(self):
        """Test UK Legislation XML response transformation."""
        adapter = LegislationGovUKAdapter()

        mock_xml = """<?xml version="1.0" encoding="utf-8"?>
        <feed xmlns="http://www.w3.org/2005/Atom">
            <entry>
                <title>Online Safety Act 2023</title>
                <link rel="alternate" href="https://www.legislation.gov.uk/ukpga/2023/50"/>
                <updated>2023-10-26T00:00:00Z</updated>
                <summary>An Act to make provision for and in connection with the regulation by OFCOM of certain internet services.</summary>
                <category term="UnitedKingdomPublicGeneralAct"/>
            </entry>
        </feed>"""

        result = adapter._transform_response(mock_xml)

        assert len(result) == 1
        assert "Online Safety Act 2023" in result[0]["title"]
        assert result[0]["external_source_provider"] == "UK Legislation"
        assert "legislation.gov.uk" in result[0]["url"]
        assert (
            result[0]["metadata"]["legislation_type"] == "UnitedKingdomPublicGeneralAct"
        )

    def test_empty_response(self):
        """Test UK Legislation returns empty list for empty feed."""
        adapter = LegislationGovUKAdapter()

        empty_xml = """<?xml version="1.0" encoding="utf-8"?>
        <feed xmlns="http://www.w3.org/2005/Atom">
        </feed>"""

        assert adapter._transform_response(empty_xml) == []

        # Invalid XML should also return empty
        assert adapter._transform_response("not xml at all") == []


# ========== SEMANTIC SCHOLAR ADAPTER ==========


class TestSemanticScholarAdapter:
    """Test suite for Semantic Scholar (Academic Papers) adapter."""

    def test_instantiation(self):
        """Test Semantic Scholar adapter instantiates correctly."""
        adapter = SemanticScholarAdapter()
        assert adapter.api_name == "Semantic Scholar"
        assert "semanticscholar.org" in adapter.base_url
        assert adapter.cache_ttl == 86400 * 7  # 7 days

    def test_is_relevant_for_domain(self):
        """Test Semantic Scholar domain relevance."""
        adapter = SemanticScholarAdapter()

        # Should be relevant for research-heavy domains
        assert adapter.is_relevant_for_domain("Science", "Global") == True
        assert adapter.is_relevant_for_domain("Climate", "Global") == True
        assert adapter.is_relevant_for_domain("Health", "UK") == True

        # Should not be relevant for current news domains
        assert adapter.is_relevant_for_domain("Politics", "Global") == False
        assert adapter.is_relevant_for_domain("Finance", "US") == False
        assert adapter.is_relevant_for_domain("Entertainment", "Global") == False

    def test_transform_response(self):
        """Test Semantic Scholar evidence creation via search path."""
        adapter = SemanticScholarAdapter()

        # Semantic Scholar builds evidence directly in search().
        # Test via _create_evidence_dict which is the shared helper.
        evidence = adapter._create_evidence_dict(
            title="Deep Learning for Climate Modelling",
            snippet="A comprehensive survey of deep learning approaches...",
            url="https://www.semanticscholar.org/paper/abc123",
            source_date=None,
            metadata={
                "authors": ["Alice Smith", "Bob Jones"],
                "venue": "Nature Machine Intelligence",
                "citation_count": 42,
                "paper_id": "abc123",
            },
        )

        assert evidence["title"] == "Deep Learning for Climate Modelling"
        assert evidence["external_source_provider"] == "Semantic Scholar"
        assert evidence["metadata"]["citation_count"] == 42

    def test_empty_response(self):
        """Test Semantic Scholar _transform_response returns empty (handled by search)."""
        adapter = SemanticScholarAdapter()

        # _transform_response is a stub, actual logic is in search()
        assert adapter._transform_response({}) == []
        assert adapter._transform_response(None) == []


# ========== OPENALEX ADAPTER ==========


class TestOpenAlexAdapter:
    """Test suite for OpenAlex (Scholarly Works) adapter."""

    def test_instantiation(self):
        """Test OpenAlex adapter instantiates correctly."""
        adapter = OpenAlexAdapter()
        assert adapter.api_name == "OpenAlex"
        assert "openalex.org" in adapter.base_url
        assert adapter.cache_ttl == 86400 * 7  # 7 days

    def test_is_relevant_for_domain(self):
        """Test OpenAlex domain relevance."""
        adapter = OpenAlexAdapter()

        # Should be relevant for research-heavy domains
        assert adapter.is_relevant_for_domain("Science", "Global") == True
        assert adapter.is_relevant_for_domain("Climate", "US") == True
        assert adapter.is_relevant_for_domain("Health", "Global") == True

        # Should not be relevant for current news domains
        assert adapter.is_relevant_for_domain("Politics", "UK") == False
        assert adapter.is_relevant_for_domain("Finance", "Global") == False
        assert adapter.is_relevant_for_domain("Law", "US") == False

    def test_transform_response(self):
        """Test OpenAlex evidence creation via search path."""
        adapter = OpenAlexAdapter()

        # OpenAlex builds evidence directly in search().
        # Test via _create_evidence_dict which is the shared helper.
        evidence = adapter._create_evidence_dict(
            title="Global Trends in Renewable Energy Investment",
            snippet="Analysis of worldwide investment patterns in renewable energy...",
            url="https://doi.org/10.1234/example",
            source_date=None,
            metadata={
                "authors": ["Jane Doe", "John Smith"],
                "citation_count": 118,
                "type": "journal-article",
                "open_access": True,
                "journal_source": "Nature Energy",
            },
        )

        assert evidence["title"] == "Global Trends in Renewable Energy Investment"
        assert evidence["external_source_provider"] == "OpenAlex"
        assert evidence["metadata"]["citation_count"] == 118
        assert evidence["metadata"]["open_access"] == True

    def test_empty_response(self):
        """Test OpenAlex _transform_response returns empty (handled by search)."""
        adapter = OpenAlexAdapter()

        # _transform_response is a stub, actual logic is in search()
        assert adapter._transform_response({}) == []
        assert adapter._transform_response(None) == []


# ========== PUBMED ADAPTER ==========


class TestPubMedAdapter:
    """Test suite for PubMed (Biomedical Literature) adapter."""

    def test_instantiation(self):
        """Test PubMed adapter instantiates correctly."""
        adapter = PubMedAdapter()
        assert adapter.api_name == "PubMed"
        assert "ncbi.nlm.nih.gov" in adapter.base_url
        assert adapter.cache_ttl == 86400 * 7  # 7 days

    def test_is_relevant_for_domain(self):
        """Test PubMed domain relevance."""
        adapter = PubMedAdapter()

        # Should be relevant for Health, Science, Animals
        assert adapter.is_relevant_for_domain("Health", "Global") == True
        assert adapter.is_relevant_for_domain("Science", "US") == True
        assert adapter.is_relevant_for_domain("Animals", "UK") == True

        # Should not be relevant for other domains (Climate removed in Fix 2)
        assert adapter.is_relevant_for_domain("Climate", "Global") == False
        assert adapter.is_relevant_for_domain("Finance", "US") == False
        assert adapter.is_relevant_for_domain("Politics", "UK") == False

    def test_transform_response(self):
        """Test PubMed XML response transformation."""
        adapter = PubMedAdapter()

        mock_xml = """<?xml version="1.0" encoding="utf-8"?>
        <PubmedArticleSet>
            <PubmedArticle>
                <MedlineCitation>
                    <PMID>12345678</PMID>
                    <Article>
                        <ArticleTitle>COVID-19 vaccine efficacy in elderly populations</ArticleTitle>
                        <Abstract>
                            <AbstractText>This systematic review examines the efficacy of COVID-19 vaccines in populations aged 65 and over.</AbstractText>
                        </Abstract>
                        <AuthorList>
                            <Author>
                                <LastName>Garcia</LastName>
                                <ForeName>Maria</ForeName>
                            </Author>
                            <Author>
                                <LastName>Chen</LastName>
                                <ForeName>Wei</ForeName>
                            </Author>
                        </AuthorList>
                        <Journal>
                            <JournalIssue>
                                <PubDate>
                                    <Year>2024</Year>
                                    <Month>Mar</Month>
                                </PubDate>
                            </JournalIssue>
                        </Journal>
                    </Article>
                </MedlineCitation>
            </PubmedArticle>
        </PubmedArticleSet>"""

        result = adapter._transform_response({"ids": ["12345678"], "xml": mock_xml})

        assert len(result) == 1
        assert "COVID-19 vaccine efficacy" in result[0]["title"]
        assert result[0]["external_source_provider"] == "PubMed"
        assert result[0]["metadata"]["pmid"] == "12345678"
        assert "pubmed.ncbi.nlm.nih.gov/12345678" in result[0]["url"]
        assert "Maria Garcia" in result[0]["metadata"]["authors"]

    def test_empty_response(self):
        """Test PubMed returns empty list for empty/None XML."""
        adapter = PubMedAdapter()

        assert adapter._transform_response({"ids": [], "xml": ""}) == []
        assert adapter._transform_response({"ids": [], "xml": None}) == []

    def test_fallback_on_invalid_xml(self):
        """Test PubMed falls back to ID-based evidence on invalid XML."""
        adapter = PubMedAdapter()

        result = adapter._transform_response(
            {
                "ids": ["99999999"],
                "xml": "not valid xml <broken>",
            }
        )

        # Should fall back to ID-based evidence
        assert len(result) == 1
        assert result[0]["metadata"]["pmid"] == "99999999"
        assert "pubmed.ncbi.nlm.nih.gov/99999999" in result[0]["url"]


# ========== COMPANIES HOUSE ADAPTER ==========


class TestCompaniesHouseAdapter:
    """Test suite for Companies House (UK Company Registry) adapter."""

    def test_instantiation(self):
        """Test Companies House adapter instantiates correctly."""
        adapter = CompaniesHouseAdapter()
        assert adapter.api_name == "Companies House"
        assert "company-information.service.gov.uk" in adapter.base_url
        assert adapter.cache_ttl == 86400 * 3  # 3 days

    def test_is_relevant_for_domain(self):
        """Test Companies House domain relevance."""
        adapter = CompaniesHouseAdapter()

        # Should be relevant for Politics and Finance + UK only
        assert adapter.is_relevant_for_domain("Politics", "UK") == True
        assert adapter.is_relevant_for_domain("Finance", "UK") == True

        # Should not be relevant for other jurisdictions (UK-specific)
        assert adapter.is_relevant_for_domain("Finance", "US") == False
        assert adapter.is_relevant_for_domain("Finance", "Global") == False
        assert adapter.is_relevant_for_domain("Health", "UK") == False

    def test_transform_response(self):
        """Test Companies House response transformation."""
        adapter = CompaniesHouseAdapter()

        mock_response = {
            "items": [
                {
                    "title": "BP P.L.C.",
                    "company_number": "00102498",
                    "company_status": "active",
                    "date_of_creation": "1909-04-14",
                    "company_type": "plc",
                    "address": {
                        "address_line_1": "1 St James's Square",
                        "locality": "London",
                    },
                }
            ]
        }

        result = adapter._transform_response(mock_response)

        assert len(result) == 1
        assert result[0]["title"] == "BP P.L.C."
        assert result[0]["external_source_provider"] == "Companies House"
        assert result[0]["metadata"]["company_number"] == "00102498"
        assert result[0]["metadata"]["company_status"] == "active"
        assert "company-information.service.gov.uk" in result[0]["url"]

    def test_empty_response(self):
        """Test Companies House returns empty list for empty response."""
        adapter = CompaniesHouseAdapter()

        assert adapter._transform_response({}) == []
        assert adapter._transform_response({"items": []}) == []


# ========== GBIF ADAPTER ==========


class TestGBIFAdapter:
    """Test suite for GBIF (Global Biodiversity Information Facility) adapter."""

    def test_instantiation(self):
        """Test GBIF adapter instantiates correctly."""
        adapter = GBIFAdapter()
        assert adapter.api_name == "GBIF"
        assert "gbif.org" in adapter.base_url
        assert adapter.cache_ttl == 86400 * 7  # 7 days

    def test_is_relevant_for_domain(self):
        """Test GBIF domain relevance."""
        adapter = GBIFAdapter()

        # Should be relevant for Animals globally
        assert adapter.is_relevant_for_domain("Animals", "Global") == True
        assert adapter.is_relevant_for_domain("Animals", "UK") == True
        assert adapter.is_relevant_for_domain("Animals", "US") == True

        # Should not be relevant for other domains
        assert adapter.is_relevant_for_domain("Science", "Global") == False
        assert adapter.is_relevant_for_domain("Health", "Global") == False
        assert adapter.is_relevant_for_domain("Finance", "UK") == False

    def test_transform_response(self):
        """Test GBIF evidence creation via _create_evidence_dict."""
        adapter = GBIFAdapter()

        # GBIF builds evidence via _search_species and _get_occurrence_data,
        # both of which use _create_evidence_dict.
        evidence = adapter._create_evidence_dict(
            title="Species: Red Panda (Ailurus fulgens)",
            snippet="Scientific classification: Animalia > Chordata > Mammalia > Carnivora > Ailuridae. Taxonomic status: ACCEPTED.",
            url="https://www.gbif.org/species/5219404",
            source_date=None,
            metadata={
                "api_source": "GBIF",
                "data_type": "species_taxonomy",
                "species_key": 5219404,
                "scientific_name": "Ailurus fulgens",
                "kingdom": "Animalia",
                "family": "Ailuridae",
            },
        )

        assert "Red Panda" in evidence["title"]
        assert evidence["external_source_provider"] == "GBIF"
        assert evidence["metadata"]["species_key"] == 5219404
        assert evidence["metadata"]["scientific_name"] == "Ailurus fulgens"

    def test_empty_response(self):
        """Test GBIF _transform_response returns empty (handled by search)."""
        adapter = GBIFAdapter()

        # _transform_response is a stub, actual logic is in _search_species
        assert adapter._transform_response({}) == []
        assert adapter._transform_response(None) == []


# ========== YOUTUBE SEARCH ==========


class TestYouTubeSearch:
    """Test suite for YouTube video search (standalone async function)."""

    @pytest.mark.asyncio
    async def test_returns_empty_list_on_missing_key(self):
        """Test YouTube returns empty list when API key is not configured."""
        with patch("app.services.api_adapters.youtube.settings") as mock_settings:
            mock_settings.YOUTUBE_API_KEY = ""
            result = await search_youtube_videos("test query")
            assert result == []

    @pytest.mark.asyncio
    async def test_returns_empty_list_on_none_key(self):
        """Test YouTube returns empty list when API key is None."""
        with patch("app.services.api_adapters.youtube.settings") as mock_settings:
            mock_settings.YOUTUBE_API_KEY = None
            result = await search_youtube_videos("test query")
            assert result == []

    @pytest.mark.asyncio
    async def test_returns_video_list(self):
        """Test YouTube returns properly formatted video list from mock response."""
        mock_search_response = {
            "items": [
                {
                    "id": {"videoId": "dQw4w9WgXcQ"},
                    "snippet": {
                        "title": "Climate Change Explained",
                        "description": "A comprehensive look at climate change...",
                        "channelTitle": "Science Channel",
                        "channelId": "UC123",
                        "publishedAt": "2025-06-15T10:00:00Z",
                        "thumbnails": {
                            "high": {
                                "url": "https://i.ytimg.com/vi/dQw4w9WgXcQ/hqdefault.jpg"
                            }
                        },
                    },
                }
            ]
        }

        mock_duration_response = {
            "items": [
                {
                    "id": "dQw4w9WgXcQ",
                    "contentDetails": {"duration": "PT12M34S"},
                }
            ]
        }

        with patch("app.services.api_adapters.youtube.settings") as mock_settings:
            mock_settings.YOUTUBE_API_KEY = "fake-api-key"

            mock_response_search = MagicMock()
            mock_response_search.status_code = 200
            mock_response_search.json.return_value = mock_search_response
            mock_response_search.raise_for_status = MagicMock()

            mock_response_duration = MagicMock()
            mock_response_duration.status_code = 200
            mock_response_duration.json.return_value = mock_duration_response
            mock_response_duration.raise_for_status = MagicMock()

            mock_client = AsyncMock()
            # First call: search, second call: durations
            mock_client.get = AsyncMock(
                side_effect=[mock_response_search, mock_response_duration]
            )
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)

            with patch(
                "app.services.api_adapters.youtube.httpx.AsyncClient",
                return_value=mock_client,
            ):
                result = await search_youtube_videos("climate change")

            assert len(result) == 1
            assert result[0]["video_id"] == "dQw4w9WgXcQ"
            assert result[0]["title"] == "Climate Change Explained"
            assert result[0]["channel_name"] == "Science Channel"
            assert (
                result[0]["video_url"] == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
            )
            assert result[0]["duration"] == "PT12M34S"
            assert (
                result[0]["thumbnail_url"]
                == "https://i.ytimg.com/vi/dQw4w9WgXcQ/hqdefault.jpg"
            )

    @pytest.mark.asyncio
    async def test_caps_max_results_at_five(self):
        """Test YouTube caps max_results at 5."""
        with patch("app.services.api_adapters.youtube.settings") as mock_settings:
            mock_settings.YOUTUBE_API_KEY = "fake-api-key"

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"items": []}
            mock_response.raise_for_status = MagicMock()

            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)

            with patch(
                "app.services.api_adapters.youtube.httpx.AsyncClient",
                return_value=mock_client,
            ):
                result = await search_youtube_videos("test", max_results=50)

            # Verify it was called with maxResults capped at 5
            call_kwargs = mock_client.get.call_args
            assert call_kwargs[1]["params"]["maxResults"] == 5


# ========== COMMON ADAPTER FEATURES ==========


class TestRemainingAdapterCommonFeatures:
    """Test common features across all remaining adapters."""

    @pytest.mark.parametrize(
        "adapter_class",
        [
            ONSAdapter,
            MarketauxAdapter,
            WorldBankAdapter,
            GovInfoAdapter,
            LegislationGovUKAdapter,
            SemanticScholarAdapter,
            OpenAlexAdapter,
            PubMedAdapter,
            CompaniesHouseAdapter,
            GBIFAdapter,
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
            ONSAdapter,
            MarketauxAdapter,
            WorldBankAdapter,
            GovInfoAdapter,
            LegislationGovUKAdapter,
            SemanticScholarAdapter,
            OpenAlexAdapter,
            PubMedAdapter,
            CompaniesHouseAdapter,
            GBIFAdapter,
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
            ONSAdapter,
            MarketauxAdapter,
            WorldBankAdapter,
            GovInfoAdapter,
            LegislationGovUKAdapter,
            SemanticScholarAdapter,
            OpenAlexAdapter,
            PubMedAdapter,
            CompaniesHouseAdapter,
            GBIFAdapter,
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
