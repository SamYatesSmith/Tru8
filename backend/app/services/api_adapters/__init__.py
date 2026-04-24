"""
API Adapters Package

Government and data API adapters organized by domain:
- economic: ONS, FRED, AlphaVantage, Marketaux, WorldBank
- health: PubMed, WHO
- climate: NOAA, WeatherAPI, OpenMeteo
- legal: GovUK, Hansard, GovInfo
- academic: CrossRef, SemanticScholar, OpenAlex
- sports: Transfermarkt, FootballData
- archives: Wikipedia, LibraryOfCongress, InternetArchive
- business: CompaniesHouse, Wikidata
- nature: GBIF

Each adapter extends GovernmentAPIClient and implements:
- search(): Query the API with claim-specific parameters
- _transform_response(): Convert API response to standardized evidence format
- is_relevant_for_domain(): Define which domains/jurisdictions this API covers
"""

import logging

from app.core.config import settings
from app.services.government_api_client import get_api_registry

# Import all adapters from their respective modules
from .economic import (
    ONSAdapter,
    FREDAdapter,
    AlphaVantageAdapter,
    MarketauxAdapter,
    WorldBankAdapter,
)
from .health import PubMedAdapter, WHOAdapter
from .climate import NOAAAdapter, WeatherAPIAdapter, OpenMeteoAdapter
from .legal import (
    GovUKAdapter,
    HansardAdapter,
    GovInfoAdapter,
    LegislationGovUKAdapter,
    UKParliamentBillsAdapter,
)
from .academic import CrossRefAdapter, SemanticScholarAdapter, OpenAlexAdapter
from .sports import TransfermarktAdapter, FootballDataAdapter
from .archives import WikipediaAdapter, LibraryOfCongressAdapter, InternetArchiveAdapter
from .business import CompaniesHouseAdapter, WikidataAdapter
from .nature import GBIFAdapter

logger = logging.getLogger(__name__)

# Export all adapter classes
__all__ = [
    # Economic
    "ONSAdapter",
    "FREDAdapter",
    "AlphaVantageAdapter",
    "MarketauxAdapter",
    "WorldBankAdapter",
    # Health
    "PubMedAdapter",
    "WHOAdapter",
    # Climate
    "NOAAAdapter",
    "WeatherAPIAdapter",
    "OpenMeteoAdapter",
    # Legal
    "GovUKAdapter",
    "HansardAdapter",
    "GovInfoAdapter",
    "LegislationGovUKAdapter",
    "UKParliamentBillsAdapter",
    # Academic
    "CrossRefAdapter",
    "SemanticScholarAdapter",
    "OpenAlexAdapter",
    # Sports
    "TransfermarktAdapter",
    "FootballDataAdapter",
    # Archives
    "WikipediaAdapter",
    "LibraryOfCongressAdapter",
    "InternetArchiveAdapter",
    # Business
    "CompaniesHouseAdapter",
    "WikidataAdapter",
    # Nature
    "GBIFAdapter",
    # Function
    "initialize_adapters",
]


def initialize_adapters():
    """
    Initialize all API adapters and register them.

    Call this function at application startup to register all adapters.
    """
    registry = get_api_registry()

    # Register ONS adapter
    registry.register(ONSAdapter())
    logger.info("Registered ONS adapter")

    # Register PubMed adapter
    registry.register(PubMedAdapter())
    logger.info("Registered PubMed adapter")

    # Register Companies House adapter (if API key is configured)
    if settings.COMPANIES_HOUSE_API_KEY:
        registry.register(CompaniesHouseAdapter())
        logger.info("Registered Companies House adapter")
    else:
        logger.warning("Companies House API key not configured, adapter not registered")

    # Register FRED adapter (Week 2)
    if settings.FRED_API_KEY:
        registry.register(FREDAdapter())
        logger.info("Registered FRED adapter")
    else:
        logger.warning("FRED API key not configured, adapter not registered")

    # Register WHO adapter (Week 2)
    registry.register(WHOAdapter())
    logger.info("Registered WHO adapter")

    # Register NOAA CDO adapter (Global Climate Data)
    if settings.NOAA_API_KEY:
        registry.register(NOAAAdapter())
        logger.info(
            f"[ADAPTERS] Registered NOAA CDO adapter for Climate (key: {settings.NOAA_API_KEY[:10]}...)"
        )
    else:
        logger.warning(
            "[ADAPTERS] NOAA_API_KEY not configured, NOAA adapter not registered"
        )

    # CrossRef unregistered (PQ-06): redundant with Semantic Scholar + OpenAlex

    # Register GOV.UK adapter (Week 2)
    registry.register(GovUKAdapter())
    logger.info("Registered GOV.UK adapter")

    # Register Hansard adapter (Week 2)
    registry.register(HansardAdapter())
    logger.info("Registered Hansard adapter")

    # Register UK Legislation adapter (PQ-06: UK statute text, no API key required)
    registry.register(LegislationGovUKAdapter())
    logger.info(
        "[ADAPTERS] Registered UK Legislation adapter for Law/UK (no key required)"
    )

    # Register UK Parliament Bills adapter (SC-15: Law-specialist fallback
    # independent of legislation.gov.uk, which is IP-blocked — see SC-05).
    # No API key required.
    registry.register(UKParliamentBillsAdapter())
    logger.info(
        "[ADAPTERS] Registered UK Parliament Bills adapter for Law+Politics/UK (no key required)"
    )

    # Register Wikidata adapter (Week 2)
    registry.register(WikidataAdapter())
    logger.info("Registered Wikidata adapter")

    # Register GovInfo adapter (Phase 4/5 integration)
    # Use settings instead of os.getenv() because .env is loaded by pydantic-settings
    if settings.GOVINFO_API_KEY:
        adapter = GovInfoAdapter()
        registry.register(adapter)
        logger.info(
            f"[ADAPTERS] Registered GovInfo.gov adapter for US legal statutes (key: {settings.GOVINFO_API_KEY[:10]}...)"
        )
        logger.info(
            f"   Adapter: {adapter.api_name}, relevant for domain=Law, jurisdiction=US"
        )
    else:
        logger.warning(
            "[ADAPTERS] GOVINFO_API_KEY not configured, GovInfo adapter not registered"
        )

    # Register Football-Data.org adapter (Sports Statistics - Real-time)
    # Use settings instead of os.getenv() - .env is loaded by pydantic-settings into settings object
    if settings.FOOTBALL_DATA_API_KEY:
        adapter = FootballDataAdapter()
        registry.register(adapter)
        logger.info(
            f"[ADAPTERS] Registered Football-Data.org adapter for Sports (key: {settings.FOOTBALL_DATA_API_KEY[:10]}...)"
        )
    else:
        logger.warning(
            "[ADAPTERS] FOOTBALL_DATA_API_KEY not configured, Football-Data adapter not registered"
        )

    # Register Transfermarkt adapter (Sports Statistics - Historical)
    # No API key required - uses free community-hosted API
    registry.register(TransfermarktAdapter())
    logger.info(
        "[ADAPTERS] Registered Transfermarkt adapter for historical sports data (transfers, achievements, career stats)"
    )

    # Alpha Vantage unregistered (PQ-06): 25 req/day free tier unusable in production

    # Register Marketaux adapter (Financial News)
    if settings.MARKETAUX_API_KEY:
        registry.register(MarketauxAdapter())
        logger.info(
            f"[ADAPTERS] Registered Marketaux adapter for Financial News (key: {settings.MARKETAUX_API_KEY[:10]}...)"
        )
    else:
        logger.warning(
            "[ADAPTERS] MARKETAUX_API_KEY not configured, Marketaux adapter not registered"
        )

    # Register WeatherAPI adapter (Weather - 1M calls/month free, commercial OK)
    if settings.WEATHER_API_KEY:
        registry.register(WeatherAPIAdapter())
        logger.info(
            f"[ADAPTERS] Registered WeatherAPI adapter for Weather (key: {settings.WEATHER_API_KEY[:10]}...)"
        )
    else:
        logger.warning(
            "[ADAPTERS] WEATHER_API_KEY not configured, WeatherAPI adapter not registered"
        )

    # Register GBIF adapter (Biodiversity/Species - No API key required, fully open)
    registry.register(GBIFAdapter())
    logger.info(
        "[ADAPTERS] Registered GBIF adapter for Animals/Biodiversity (no key required)"
    )

    # Register Wikipedia adapter (History, Politics, Entertainment, General - No API key required)
    registry.register(WikipediaAdapter())
    logger.info(
        "[ADAPTERS] Registered Wikipedia adapter for History/Politics/Entertainment/General (no key required)"
    )

    # ===== NEW HIGH-QUALITY FREE ADAPTERS (No API keys required) =====

    # Register Library of Congress adapter (History, Politics, General - Primary sources, newspapers)
    registry.register(LibraryOfCongressAdapter())
    logger.info(
        "[ADAPTERS] Registered Library of Congress adapter for History/Politics/General (no key required)"
    )

    # Register Semantic Scholar adapter (Science, History, Health, General - 200M+ academic papers)
    registry.register(SemanticScholarAdapter())
    logger.info(
        "[ADAPTERS] Registered Semantic Scholar adapter for Science/History/Health/General (no key required)"
    )

    # Register OpenAlex adapter (Science, History, Health, General - 250M+ scholarly works)
    registry.register(OpenAlexAdapter())
    logger.info(
        "[ADAPTERS] Registered OpenAlex adapter for Science/History/Health/General (no key required)"
    )

    # Register Internet Archive adapter (History, General - Historical documents, Wayback Machine)
    registry.register(InternetArchiveAdapter())
    logger.info(
        "[ADAPTERS] Registered Internet Archive adapter for History/General (no key required)"
    )

    # Register World Bank adapter (Finance, Demographics - Global economic indicators, no API key required)
    registry.register(WorldBankAdapter())
    logger.info(
        "[ADAPTERS] Registered World Bank adapter for Finance/Demographics (no key required)"
    )

    # Register Open-Meteo adapter (Weather, Climate - Global weather data, no API key required)
    registry.register(OpenMeteoAdapter())
    logger.info(
        "[ADAPTERS] Registered Open-Meteo adapter for Weather/Climate (no key required)"
    )

    logger.info(
        f"API adapter initialization complete. {len(registry.get_all_adapters())} adapters registered."
    )
