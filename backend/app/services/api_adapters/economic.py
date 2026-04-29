"""
Economic API Adapters

Adapters for financial and economic data:
- ONS (UK Office for National Statistics)
- FRED (US Federal Reserve Economic Data)
- Alpha Vantage (Stocks, Forex, Crypto)
- Marketaux (Financial News)
- World Bank (Global economic indicators, no API key required)
"""

import logging
import re
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

from app.services.government_api_client import GovernmentAPIClient
from app.core.config import settings
from app.utils.adapter_query_helpers import extract_concept_keyword, extract_entity_name

logger = logging.getLogger(__name__)


# B3.1: ONS recognises UK economic concepts in its dataset titles. Generic
# claim text (e.g. "BP reported record profits") fuzzy-matches dozens of
# unrelated UK statistics datasets — TRU-87D3-6415 surfaced 10 of 19 final
# items as ONS dump from this exact failure mode. The mapping below acts
# as both a relevance gate (claim must mention a known concept to fire ONS
# at all) and a query shaper (the value is what ONS's `q` parameter
# searches well against).
#
# Order matters: more-specific keywords first, so longer phrases win when
# both a specific and a general key would match the same claim. Mapping
# values are canonical phrasing ONS uses in its dataset titles — picked
# from the live catalogue at https://www.ons.gov.uk/economy and
# /labour-market.
#
# Expand iteratively when live verification surfaces a real claim that
# should have routed to ONS but didn't. Don't pre-emptively bloat the
# mapping; ONS skip-aggressively beats ONS dump.
ONS_DATASET_MAPPING: Dict[str, str] = {
    # Inflation
    "consumer price index": "consumer price inflation",
    "retail price index": "retail price index",
    "cpi inflation": "consumer price inflation",
    "rpi": "retail price index",
    "inflation": "consumer price inflation",
    # GDP
    "gdp growth": "GDP growth",
    "gross domestic product": "gross domestic product",
    "gdp": "gross domestic product",
    # Labour market
    "unemployment rate": "unemployment rate",
    "employment rate": "employment rate",
    "unemployment": "unemployment",
    "average weekly earnings": "average weekly earnings",
    "wage growth": "wage growth",
    # Trade & government finance
    "trade balance": "balance of trade",
    "public sector debt": "public sector net debt",
    "public sector borrowing": "public sector net borrowing",
    # Retail
    "retail sales": "retail sales",
    # Population
    "population": "UK population",
}


# ========== ONS ECONOMIC STATISTICS ADAPTER ==========


class ONSAdapter(GovernmentAPIClient):
    """
    Office for National Statistics (UK) API Adapter.

    Covers: Finance, Demographics
    Jurisdiction: UK
    Free tier: No API key required, rate limit ~300 requests/hour
    """

    def __init__(self):
        super().__init__(
            api_name="ONS Economic Statistics",
            base_url="https://api.beta.ons.gov.uk/v1",
            api_key=None,  # No API key required
            cache_ttl=86400,  # 24 hours
            timeout=15,
            max_results=10,
            emits_structural_metadata=True,  # NF-07-v2: economic series, structural
        )

        # ONS-specific headers
        self.headers.update({"Accept": "application/json"})

    def is_relevant_for_domain(self, domain: str, jurisdiction: str) -> bool:
        """ONS covers Finance and Demographics for UK only."""
        return domain in ["Finance", "Demographics"] and jurisdiction in [
            "UK",
            "Global",
        ]  # Global allows UK data

    def prepare_query(
        self,
        claim_text: str,
        entities: Optional[List[Dict[str, str]]] = None,
    ) -> str:
        """B3.1: skip ONS unless the claim mentions a known UK economic concept.

        Returns the canonical search term from ONS_DATASET_MAPPING when
        the claim or its OTHER-typed entities mention a mapped concept
        (e.g. "GDP", "inflation", "unemployment rate"). Returns "" to
        skip the call when no concept matches — generic claims about
        companies, people, laws, or other domains should not fire ONS.

        This is the structural fix for the dump pattern observed in
        TRU-87D3-6415: better to return 0 ONS items than 5 irrelevant
        ones picked up by ONS's loose `q` fuzzy match.
        """
        matched = extract_concept_keyword(claim_text, ONS_DATASET_MAPPING, entities)
        return matched or ""

    def search(
        self,
        query: str,
        domain: str,
        jurisdiction: str,
        entities: Optional[List[Dict[str, str]]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search ONS datasets and fetch latest observation values.

        Strategy:
        1. Search /datasets for relevant datasets
        2. For top results, fetch latest observation via edition/version endpoints
        3. Return evidence with actual data values
        """
        if not self.is_relevant_for_domain(domain, jurisdiction):
            return []

        # B3.1: query has already been shaped by prepare_query when called via
        # search_with_cache. Direct callers (scorecard scripts, integration
        # tests) may still pass raw claim text; defensively re-shape so direct
        # calls also benefit from the concept-keyword gate. extract_concept_
        # keyword is pure and cheap, so the double call is harmless.
        shaped = extract_concept_keyword(query, ONS_DATASET_MAPPING, entities)
        targeted_query = shaped or query

        params = {
            "q": targeted_query,
            "limit": self.max_results,
        }

        try:
            response = self._make_request("datasets", params=params)

            if not response or "items" not in response:
                logger.warning(f"ONS API returned empty response for: {targeted_query}")
                return []

            return self._transform_response_with_observations(response)

        except Exception as e:
            logger.error(f"ONS search failed for '{query}': {e}")
            return []

    def _fetch_latest_observation(self, dataset_id: str) -> Optional[Dict[str, Any]]:
        """Fetch the latest observation value for an ONS dataset."""
        try:
            # Get editions for this dataset
            editions_resp = self._make_request(f"datasets/{dataset_id}/editions")
            if not editions_resp or "items" not in editions_resp:
                return None

            items = editions_resp.get("items", [])
            if not items:
                return None

            # Use the first (latest) edition
            edition = items[0]
            edition_id = edition.get("edition", "time-series")

            # Get latest version
            versions_resp = self._make_request(
                f"datasets/{dataset_id}/editions/{edition_id}/versions"
            )
            if not versions_resp or "items" not in versions_resp:
                return None

            versions = versions_resp.get("items", [])
            if not versions:
                return None

            latest_version = versions[0]
            return {
                "release_date": latest_version.get("release_date"),
                "version": latest_version.get("version"),
                "edition": edition_id,
                "temporal": latest_version.get("temporal"),
                "downloads": latest_version.get("downloads", {}),
            }

        except Exception as e:
            logger.debug(f"ONS observation fetch failed for {dataset_id}: {e}")
            return None

    def _transform_response_with_observations(
        self, raw_response: Any
    ) -> List[Dict[str, Any]]:
        """Transform ONS datasets with latest observation values."""
        evidence_list = []

        for item in raw_response.get("items", [])[:5]:  # Cap at 5 to limit API calls
            try:
                title = item.get("title", "ONS Dataset")
                description = item.get("description", "")
                dataset_id = item.get("id", "")

                links = item.get("links", {})
                url = links.get("self", {}).get("href", "https://www.ons.gov.uk")

                release_date_str = item.get("release_date")
                source_date = None
                if release_date_str:
                    try:
                        source_date = datetime.fromisoformat(
                            release_date_str.replace("Z", "+00:00")
                        )
                    except Exception:
                        pass

                # PQ-06: Fetch latest observation to include actual values
                snippet = description[:300] if description else title
                obs = self._fetch_latest_observation(dataset_id) if dataset_id else None
                if obs:
                    obs_date = obs.get("release_date", "")
                    if obs_date:
                        try:
                            source_date = datetime.fromisoformat(
                                obs_date.replace("Z", "+00:00")
                            )
                        except Exception:
                            pass
                    snippet = f"{title} — ONS dataset updated {obs_date[:10] if obs_date else 'recently'}. {description[:200]}"

                metadata = {
                    "api_source": "ONS",
                    "dataset_id": dataset_id,
                    "dataset_type": item.get("type"),
                    "contact_name": (
                        item.get("contacts", [{}])[0].get("name")
                        if item.get("contacts")
                        else None
                    ),
                }

                evidence = self._create_evidence_dict(
                    title=title,
                    snippet=snippet,
                    url=url,
                    source_date=source_date,
                    metadata=metadata,
                )

                evidence_list.append(evidence)

            except Exception as e:
                logger.warning(f"Failed to parse ONS item: {e}")
                continue

        logger.info(f"ONS returned {len(evidence_list)} evidence items")
        return evidence_list

    def _transform_response(self, raw_response: Any) -> List[Dict[str, Any]]:
        """Transform ONS API response (fallback without observations)."""
        return self._transform_response_with_observations(raw_response)


# ========== FRED ADAPTER (US Federal Reserve Economic Data) ==========


class FREDAdapter(GovernmentAPIClient):
    """
    FRED (Federal Reserve Economic Data) API Adapter.

    Covers: Finance
    Jurisdiction: US
    Free tier: 1,000 requests/day
    API key: Required
    """

    # SC-09: Common economic indicators → FRED series ID mapping.
    # FRED's /series/search?search_text= returns 0 on long claim
    # sentences (verified live 2026-04-23 — UNRATE 0-yield on every
    # Finance/US claim despite the adapter firing). A direct
    # series-ID search reliably hits the right series at the top of
    # results because FRED indexes series IDs as searchable text.
    # Keys are matched as case-insensitive substrings; longest match
    # wins (sorted at use-site) so "consumer price index" beats "cpi".
    _FRED_SERIES_KEYWORDS: Dict[str, str] = {
        # Employment
        "nonfarm payroll": "PAYEMS",
        "labor force participation": "CIVPART",
        "unemployment rate": "UNRATE",
        "unemployment": "UNRATE",
        "jobless": "UNRATE",
        # Inflation / prices
        "consumer price index": "CPIAUCSL",
        "producer price index": "PPIACO",
        "inflation": "CPIAUCSL",
        "cpi": "CPIAUCSL",
        "ppi": "PPIACO",
        # Output
        "gross domestic product": "GDP",
        "real gdp": "GDPC1",
        "gdp": "GDP",
        "industrial production": "INDPRO",
        # Interest rates
        "10-year treasury": "DGS10",
        "10 year treasury": "DGS10",
        "30-year mortgage": "MORTGAGE30US",
        "fed funds rate": "FEDFUNDS",
        "federal funds rate": "FEDFUNDS",
        "federal funds": "FEDFUNDS",
        # Markets / sentiment
        "consumer sentiment": "UMCSENT",
        "personal income": "PI",
        "retail sales": "RSAFS",
        "housing starts": "HOUST",
        "s&p 500": "SP500",
        "sp500": "SP500",
    }

    def __init__(self):
        from app.core.config import settings

        super().__init__(
            api_name="FRED",
            base_url="https://api.stlouisfed.org/fred",
            api_key=settings.FRED_API_KEY or None,
            cache_ttl=86400 * 7,  # 7 days (economic data changes slowly)
            timeout=10,
            max_results=10,
            emits_structural_metadata=True,  # NF-07-v2: series IDs, structural (post-SC-09)
        )

        # FRED uses API key as query parameter
        if self.api_key:
            del self.headers["Authorization"]

    def is_relevant_for_domain(self, domain: str, jurisdiction: str) -> bool:
        """FRED covers Finance for US."""
        return domain == "Finance" and jurisdiction in ["US", "Global"]

    def prepare_query(
        self,
        claim_text: str,
        entities: Optional[List[Dict[str, str]]] = None,
    ) -> str:
        """B2.2: expose SC-09 FRED series mapping via prepare_query.

        Returns the FRED series ID (e.g. "UNRATE", "CPIAUCSL") when the
        claim mentions a mapped concept; falls back to the claim text
        when no concept keyword matches. The fallback preserves the
        existing search() cascade behaviour: ID search first, then
        natural-language search if the ID returns empty.

        Entities unused for now — _FRED_SERIES_KEYWORDS uses
        word-boundary regex on the claim text which is what SC-09 was
        tuned against. Promoting to extract_concept_keyword (which adds
        OTHER-entity matching) is a future option but unnecessary
        without evidence the regex misses real-world cases.
        """
        del entities
        series_id = self._extract_fred_series_query(claim_text)
        return series_id or claim_text

    def _extract_fred_series_query(self, query: str) -> Optional[str]:
        """SC-09: map common economic concepts in a claim to a FRED series ID.

        Returns the matching FRED series ID for the longest matching
        keyword in the claim, or None if no concept keyword matches
        (caller falls back to the original targeted query).

        Uses word-boundary matching so short keys like "gdp", "cpi",
        "ppi" don't false-positive inside unrelated tokens (e.g. "GDPR
        fines exceeded $1B" must not map to GDP).
        """
        if not query:
            return None
        q_low = query.lower()
        for keyword in sorted(self._FRED_SERIES_KEYWORDS, key=len, reverse=True):
            pattern = r"\b" + re.escape(keyword) + r"\b"
            if re.search(pattern, q_low):
                return self._FRED_SERIES_KEYWORDS[keyword]
        return None

    def search(
        self,
        query: str,
        domain: str,
        jurisdiction: str,
        entities: Optional[List[Dict[str, str]]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search FRED for US economic data series and fetch latest observations.

        Strategy:
        1. Search /series/search for relevant series
        2. For top results, fetch latest observations via /series/observations
        3. Return evidence with actual data values
        """
        if not self.is_relevant_for_domain(domain, jurisdiction):
            return []

        if not self.api_key:
            logger.warning("FRED API key not configured, skipping")
            return []

        # B5: query is already shaped by prepare_query (B2.2 returns the
        # FRED series ID on concept match, or claim_text as fallback).
        # The defensive re-extract here keeps the cascade behaviour for
        # direct callers (scorecard scripts) that bypass search_with_cache.
        # SC-09: prefer a known FRED series ID when the claim mentions a
        # mapped concept (UNRATE for unemployment, CPIAUCSL for inflation,
        # etc.). FRED's /series/search hits the right series reliably on
        # an ID and returns 0 on long claim sentences. Cascade fallback
        # below restores the original query if the ID search comes back empty.
        fred_series = self._extract_fred_series_query(query)
        search_text = fred_series or query

        params = {
            "search_text": search_text,
            "api_key": self.api_key,
            "file_type": "json",
            "limit": self.max_results,
        }

        try:
            response = self._make_request("/series/search", params=params)

            # SC-09 cascade: series-ID search hit nothing — retry with the
            # original targeted query before giving up. Uses a fresh params
            # dict so the retry doesn't mutate the original (avoids subtle
            # shared-state hazards if more logic is added between calls).
            if fred_series and (not response or not response.get("seriess")):
                logger.debug(
                    f"FRED series-ID '{fred_series}' returned empty; "
                    f"retrying with raw targeted query"
                )
                retry_params = dict(params, search_text=targeted_query)
                response = self._make_request("/series/search", params=retry_params)

            if not response or "seriess" not in response:
                logger.warning(f"FRED returned empty response for: {query}")
                return []

            return self._transform_response(response)

        except Exception as e:
            logger.error(f"FRED search failed for '{query}': {e}")
            return []

    def _fetch_latest_observations(self, series_id: str) -> Optional[Dict[str, Any]]:
        """Fetch the latest observation values for a FRED series."""
        try:
            params = {
                "series_id": series_id,
                "api_key": self.api_key,
                "file_type": "json",
                "sort_order": "desc",
                "limit": 5,
            }
            response = self._make_request("/series/observations", params=params)
            if not response or "observations" not in response:
                return None

            observations = response.get("observations", [])
            # Filter out entries with "." value (FRED uses "." for missing data)
            valid_obs = [
                o for o in observations if o.get("value") and o["value"] != "."
            ]
            if not valid_obs:
                return None

            latest = valid_obs[0]
            return {
                "value": latest.get("value"),
                "date": latest.get("date"),
            }

        except Exception as e:
            logger.debug(f"FRED observation fetch failed for {series_id}: {e}")
            return None

    def _transform_response(self, raw_response: Any) -> List[Dict[str, Any]]:
        """Transform FRED API response with latest observation values."""
        evidence_list = []

        for series in raw_response.get("seriess", [])[:5]:  # Cap to limit API calls
            try:
                series_id = series.get("id")
                title = series.get("title", f"FRED Series {series_id}")
                notes = series.get("notes", "")
                units = series.get("units", "")
                frequency = series.get("frequency", "")
                seasonal_adj = series.get("seasonal_adjustment", "")

                url = f"https://fred.stlouisfed.org/series/{series_id}"

                # PQ-06: Fetch latest observation to include actual values
                obs = self._fetch_latest_observations(series_id) if series_id else None
                if obs and obs.get("value"):
                    snippet = (
                        f"{title} ({obs['date']}): {obs['value']}"
                        f"{' ' + units if units else ''}"
                        f" — FRED series {series_id}"
                        f"{', ' + frequency if frequency else ''}"
                        f"{', ' + seasonal_adj if seasonal_adj else ''}"
                    )
                    # Use observation date as source_date
                    source_date = None
                    try:
                        source_date = datetime.fromisoformat(obs["date"])
                    except Exception:
                        pass
                else:
                    snippet = notes[:300] if notes else f"Economic data series: {title}"
                    observation_start = series.get("observation_start")
                    source_date = None
                    if observation_start:
                        try:
                            source_date = datetime.fromisoformat(observation_start)
                        except Exception:
                            pass

                metadata = {
                    "api_source": "FRED",
                    "series_id": series_id,
                    "frequency": frequency,
                    "units": units,
                    "seasonal_adjustment": seasonal_adj,
                }
                if obs and obs.get("value"):
                    metadata["latest_value"] = obs["value"]
                    metadata["latest_date"] = obs["date"]

                evidence = self._create_evidence_dict(
                    title=title,
                    snippet=snippet,
                    url=url,
                    source_date=source_date,
                    metadata=metadata,
                )

                evidence_list.append(evidence)

            except Exception as e:
                logger.warning(f"Failed to parse FRED series: {e}")
                continue

        logger.info(f"FRED returned {len(evidence_list)} evidence items")
        return evidence_list


# ========== ALPHA VANTAGE ADAPTER (Stocks, Forex, Crypto, News) ==========


class AlphaVantageAdapter(GovernmentAPIClient):
    """
    Alpha Vantage API Adapter.

    Covers: Finance (stocks, forex, crypto, news sentiment)
    Jurisdiction: Global (primarily US stocks)
    Rate limits: 25 requests/day (free tier)
    API key: Required

    Key endpoints:
    - GLOBAL_QUOTE: Latest stock price
    - TIME_SERIES_DAILY: Historical daily prices
    - NEWS_SENTIMENT: News with AI sentiment
    - CURRENCY_EXCHANGE_RATE: Forex rates
    """

    def __init__(self):
        super().__init__(
            api_name="Alpha Vantage",
            base_url="https://www.alphavantage.co/query",
            api_key=settings.ALPHA_VANTAGE_API_KEY,
            cache_ttl=300,  # 5 minutes (stock data changes frequently)
            timeout=15,
            max_results=10,
        )

        # Alpha Vantage uses apikey as query parameter, not header
        if "Authorization" in self.headers:
            del self.headers["Authorization"]

    def is_relevant_for_domain(self, domain: str, jurisdiction: str) -> bool:
        """Alpha Vantage covers Finance globally."""
        return domain == "Finance"

    def search(
        self,
        query: str,
        domain: str,
        jurisdiction: str,
        entities: Optional[List[Dict[str, str]]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search Alpha Vantage for financial data.

        Args:
            query: Search query (e.g., "Apple stock price", "Bitcoin price")
            domain: Finance
            jurisdiction: Any
            entities: Optional NER entities for ticker extraction

        Returns:
            List of evidence dictionaries
        """
        # Domain check removed - adapter selection already filters by relevance
        # This was blocking calls from secondary domain routing and keyword routing

        if not self.api_key:
            logger.warning("Alpha Vantage API key not configured, skipping")
            return []

        query_lower = query.lower()
        evidence = []

        try:
            # Extract ticker symbol from entities or query
            ticker = self._extract_ticker(query, entities)

            # Determine what type of financial data to fetch
            # NOTE: Order matters! Check specific commodities/crypto BEFORE generic terms like "price"
            # because "oil price" should match commodity, not stock
            if any(
                term in query_lower
                for term in [
                    "oil",
                    "crude",
                    "brent",
                    "wti",
                    "petroleum",
                    "natural gas",
                    "commodity",
                    "barrel",
                ]
            ):
                evidence.extend(self._get_commodity_price(query))
            elif any(
                term in query_lower
                for term in ["bitcoin", "crypto", "ethereum", "btc", "eth"]
            ):
                evidence.extend(self._get_crypto_rate(query))
            elif any(
                term in query_lower
                for term in ["exchange rate", "forex", "currency", "usd", "eur", "gbp"]
            ):
                evidence.extend(self._get_forex_rate(query))
            elif any(
                term in query_lower for term in ["stock", "share", "price", "trading"]
            ):
                if ticker:
                    evidence.extend(self._get_stock_quote(ticker))
                else:
                    evidence.extend(self._search_symbol(query))
            elif any(term in query_lower for term in ["news", "sentiment", "market"]):
                evidence.extend(self._get_news_sentiment(ticker or query))
            else:
                # Default: try stock quote if ticker found, else search
                if ticker:
                    evidence.extend(self._get_stock_quote(ticker))
                else:
                    evidence.extend(self._search_symbol(query))

            return evidence

        except Exception as e:
            logger.error(f"Alpha Vantage search failed for '{query}': {e}")
            return []

    def _extract_ticker(
        self, query: str, entities: Optional[List[Dict[str, str]]] = None
    ) -> Optional[str]:
        """Extract stock ticker from query or entities."""
        # Common company to ticker mapping
        company_tickers = {
            "apple": "AAPL",
            "microsoft": "MSFT",
            "google": "GOOGL",
            "alphabet": "GOOGL",
            "amazon": "AMZN",
            "tesla": "TSLA",
            "meta": "META",
            "facebook": "META",
            "nvidia": "NVDA",
            "netflix": "NFLX",
            "intel": "INTC",
            "amd": "AMD",
            "ibm": "IBM",
            "oracle": "ORCL",
            "salesforce": "CRM",
            "adobe": "ADBE",
            "paypal": "PYPL",
            "uber": "UBER",
            "airbnb": "ABNB",
            "spotify": "SPOT",
            "twitter": "X",
            "snap": "SNAP",
            "pinterest": "PINS",
            "zoom": "ZM",
            "shopify": "SHOP",
            "square": "SQ",
            "block": "SQ",
            "coinbase": "COIN",
            "disney": "DIS",
            "warner": "WBD",
            "comcast": "CMCSA",
            "verizon": "VZ",
            "at&t": "T",
            "boeing": "BA",
            "lockheed": "LMT",
            "raytheon": "RTX",
            "jpmorgan": "JPM",
            "goldman": "GS",
            "morgan stanley": "MS",
            "citi": "C",
            "bank of america": "BAC",
            "wells fargo": "WFC",
            "visa": "V",
            "mastercard": "MA",
            "walmart": "WMT",
            "target": "TGT",
            "costco": "COST",
            "home depot": "HD",
            "nike": "NKE",
            "starbucks": "SBUX",
            "mcdonald": "MCD",
            "coca-cola": "KO",
            "pepsi": "PEP",
            "procter": "PG",
            "johnson": "JNJ",
            "pfizer": "PFE",
            "moderna": "MRNA",
            "exxon": "XOM",
            "chevron": "CVX",
            "shell": "SHEL",
        }

        query_lower = query.lower()

        # Check for company name matches
        for company, ticker in company_tickers.items():
            if company in query_lower:
                return ticker

        # Check for direct ticker symbols (uppercase, 1-5 chars)
        ticker_match = re.search(r"\b([A-Z]{1,5})\b", query)
        if ticker_match:
            potential_ticker = ticker_match.group(1)
            # Verify it's likely a ticker (not a common word)
            common_words = {
                "A",
                "I",
                "THE",
                "AND",
                "OR",
                "FOR",
                "TO",
                "IN",
                "ON",
                "AT",
                "IS",
                "IT",
                "BE",
                "AS",
                "BY",
            }
            if potential_ticker not in common_words:
                return potential_ticker

        # Check entities for ORG type
        if entities:
            for entity in entities:
                if entity.get("type") == "ORG":
                    org_name = entity.get("text", "").lower()
                    for company, ticker in company_tickers.items():
                        if company in org_name:
                            return ticker

        return None

    def _get_stock_quote(self, ticker: str) -> List[Dict[str, Any]]:
        """Get latest stock quote for a ticker."""
        params = {"function": "GLOBAL_QUOTE", "symbol": ticker, "apikey": self.api_key}

        try:
            response = self._make_request("", params=params)

            if not response or "Global Quote" not in response:
                logger.warning(f"Alpha Vantage returned no quote for {ticker}")
                return []

            quote = response["Global Quote"]
            if not quote:
                return []

            price = quote.get("05. price", "N/A")
            change = quote.get("09. change", "N/A")
            change_pct = quote.get("10. change percent", "N/A")
            volume = quote.get("06. volume", "N/A")
            latest_day = quote.get("07. latest trading day", "N/A")

            snippet = (
                f"{ticker} stock price: ${price} (Change: {change} / {change_pct}). "
                f"Volume: {volume}. Latest trading day: {latest_day}."
            )

            evidence = self._create_evidence_dict(
                title=f"{ticker} Stock Quote - Alpha Vantage",
                snippet=snippet,
                url=f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={ticker}",
                source_date=datetime.now(timezone.utc),
                metadata={
                    "api_source": "Alpha Vantage",
                    "data_type": "stock_quote",
                    "ticker": ticker,
                    "price": price,
                    "change": change,
                    "change_percent": change_pct,
                    "volume": volume,
                },
            )
            return [evidence]

        except Exception as e:
            logger.error(f"Alpha Vantage stock quote failed for {ticker}: {e}")
            return []

    def _search_symbol(self, query: str) -> List[Dict[str, Any]]:
        """Search for stock symbols matching a query."""
        params = {
            "function": "SYMBOL_SEARCH",
            "keywords": query[:50],  # Limit query length
            "apikey": self.api_key,
        }

        try:
            response = self._make_request("", params=params)

            if not response or "bestMatches" not in response:
                return []

            evidence_list = []
            for match in response["bestMatches"][:5]:
                symbol = match.get("1. symbol", "")
                name = match.get("2. name", "")
                match_type = match.get("3. type", "")
                region = match.get("4. region", "")

                evidence = self._create_evidence_dict(
                    title=f"{symbol} - {name}",
                    snippet=f"{name} ({symbol}): {match_type} listed in {region}.",
                    url=f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={symbol}",
                    source_date=datetime.now(timezone.utc),
                    metadata={
                        "api_source": "Alpha Vantage",
                        "data_type": "symbol_search",
                        "ticker": symbol,
                        "company_name": name,
                        "type": match_type,
                        "region": region,
                    },
                )
                evidence_list.append(evidence)

            return evidence_list

        except Exception as e:
            logger.error(f"Alpha Vantage symbol search failed: {e}")
            return []

    def _get_crypto_rate(self, query: str) -> List[Dict[str, Any]]:
        """Get cryptocurrency exchange rate."""
        # Determine crypto symbol
        crypto_map = {
            "bitcoin": "BTC",
            "btc": "BTC",
            "ethereum": "ETH",
            "eth": "ETH",
            "litecoin": "LTC",
            "ltc": "LTC",
            "ripple": "XRP",
            "xrp": "XRP",
            "dogecoin": "DOGE",
            "doge": "DOGE",
            "cardano": "ADA",
            "ada": "ADA",
            "solana": "SOL",
            "sol": "SOL",
        }

        query_lower = query.lower()
        crypto = "BTC"  # Default to Bitcoin
        for name, symbol in crypto_map.items():
            if name in query_lower:
                crypto = symbol
                break

        params = {
            "function": "CURRENCY_EXCHANGE_RATE",
            "from_currency": crypto,
            "to_currency": "USD",
            "apikey": self.api_key,
        }

        try:
            response = self._make_request("", params=params)

            if not response or "Realtime Currency Exchange Rate" not in response:
                return []

            rate_data = response["Realtime Currency Exchange Rate"]
            rate = rate_data.get("5. Exchange Rate", "N/A")
            from_name = rate_data.get("2. From_Currency Name", crypto)
            last_refresh = rate_data.get("6. Last Refreshed", "N/A")

            snippet = f"{from_name} ({crypto}) price: ${rate} USD. Last updated: {last_refresh}."

            evidence = self._create_evidence_dict(
                title=f"{crypto}/USD Exchange Rate - Alpha Vantage",
                snippet=snippet,
                url=f"https://www.alphavantage.co/query?function=CURRENCY_EXCHANGE_RATE&from_currency={crypto}&to_currency=USD",
                source_date=datetime.now(timezone.utc),
                metadata={
                    "api_source": "Alpha Vantage",
                    "data_type": "crypto_rate",
                    "crypto": crypto,
                    "rate_usd": rate,
                },
            )
            return [evidence]

        except Exception as e:
            logger.error(f"Alpha Vantage crypto rate failed: {e}")
            return []

    def _get_forex_rate(self, query: str) -> List[Dict[str, Any]]:
        """Get forex exchange rate."""
        # Extract currency pair from query
        currencies = {
            "usd": "USD",
            "dollar": "USD",
            "eur": "EUR",
            "euro": "EUR",
            "gbp": "GBP",
            "pound": "GBP",
            "sterling": "GBP",
            "jpy": "JPY",
            "yen": "JPY",
            "cad": "CAD",
            "canadian": "CAD",
            "aud": "AUD",
            "australian": "AUD",
            "chf": "CHF",
            "swiss": "CHF",
        }

        query_lower = query.lower()
        from_curr = "USD"
        to_curr = "EUR"

        found = []
        for name, code in currencies.items():
            if name in query_lower and code not in found:
                found.append(code)
                if len(found) >= 2:
                    break

        if len(found) >= 2:
            from_curr, to_curr = found[0], found[1]
        elif len(found) == 1:
            from_curr = found[0]
            to_curr = "USD" if from_curr != "USD" else "EUR"

        params = {
            "function": "CURRENCY_EXCHANGE_RATE",
            "from_currency": from_curr,
            "to_currency": to_curr,
            "apikey": self.api_key,
        }

        try:
            response = self._make_request("", params=params)

            if not response or "Realtime Currency Exchange Rate" not in response:
                return []

            rate_data = response["Realtime Currency Exchange Rate"]
            rate = rate_data.get("5. Exchange Rate", "N/A")
            last_refresh = rate_data.get("6. Last Refreshed", "N/A")

            snippet = f"{from_curr}/{to_curr} exchange rate: {rate}. Last updated: {last_refresh}."

            evidence = self._create_evidence_dict(
                title=f"{from_curr}/{to_curr} Exchange Rate - Alpha Vantage",
                snippet=snippet,
                url=f"https://www.alphavantage.co/query?function=CURRENCY_EXCHANGE_RATE&from_currency={from_curr}&to_currency={to_curr}",
                source_date=datetime.now(timezone.utc),
                metadata={
                    "api_source": "Alpha Vantage",
                    "data_type": "forex_rate",
                    "from_currency": from_curr,
                    "to_currency": to_curr,
                    "rate": rate,
                },
            )
            return [evidence]

        except Exception as e:
            logger.error(f"Alpha Vantage forex rate failed: {e}")
            return []

    def _get_commodity_price(self, query: str) -> List[Dict[str, Any]]:
        """
        Get commodity prices from Alpha Vantage.

        Supports: Brent Crude, WTI Crude, Natural Gas, and other commodities.

        Args:
            query: Search query containing commodity keywords

        Returns:
            List of evidence dictionaries with commodity price data
        """
        # Map query terms to Alpha Vantage commodity functions
        commodity_map = {
            "brent": ("BRENT", "Brent Crude Oil"),
            "wti": ("WTI", "WTI Crude Oil"),
            "crude": ("BRENT", "Brent Crude Oil"),  # Default crude to Brent
            "oil": ("BRENT", "Brent Crude Oil"),  # Default oil to Brent
            "petroleum": ("BRENT", "Brent Crude Oil"),
            "natural gas": ("NATURAL_GAS", "Natural Gas"),
            "gas": ("NATURAL_GAS", "Natural Gas"),
            "copper": ("COPPER", "Copper"),
            "aluminum": ("ALUMINUM", "Aluminum"),
            "wheat": ("WHEAT", "Wheat"),
            "corn": ("CORN", "Corn"),
            "cotton": ("COTTON", "Cotton"),
            "sugar": ("SUGAR", "Sugar"),
            "coffee": ("COFFEE", "Coffee"),
        }

        query_lower = query.lower()

        # Find matching commodity
        function_name = "BRENT"  # Default
        commodity_name = "Brent Crude Oil"

        for term, (func, name) in commodity_map.items():
            if term in query_lower:
                function_name = func
                commodity_name = name
                break

        params = {
            "function": function_name,
            "interval": "daily",
            "apikey": self.api_key,
        }

        try:
            response = self._make_request("", params=params)

            if not response or "data" not in response:
                logger.warning(
                    f"Alpha Vantage returned no data for commodity {function_name}"
                )
                return []

            # Get the most recent data point
            data = response.get("data", [])
            if not data:
                return []

            # Get latest price
            latest = data[0]
            current_value = latest.get("value", "N/A")
            current_date = latest.get("date", "N/A")

            # Calculate percentage change if we have historical data
            pct_change = None
            prev_value = None
            if len(data) >= 2:
                try:
                    current = float(current_value)
                    previous = float(data[1].get("value", 0))
                    if previous > 0:
                        pct_change = ((current - previous) / previous) * 100
                        prev_value = previous
                except (ValueError, TypeError):
                    pass

            # Build detailed snippet
            if pct_change is not None:
                change_direction = "up" if pct_change > 0 else "down"
                snippet = (
                    f"{commodity_name} price: ${current_value}/barrel as of {current_date}. "
                    f"Price {change_direction} {abs(pct_change):.2f}% from previous close (${prev_value:.2f})."
                )
            else:
                snippet = f"{commodity_name} price: ${current_value}/barrel as of {current_date}."

            # Parse date
            source_date = datetime.now(timezone.utc)
            if current_date and current_date != "N/A":
                try:
                    source_date = datetime.strptime(current_date, "%Y-%m-%d")
                except:
                    pass

            evidence = self._create_evidence_dict(
                title=f"{commodity_name} Price - Alpha Vantage",
                snippet=snippet,
                url=f"https://www.alphavantage.co/query?function={function_name}&interval=daily",
                source_date=source_date,
                metadata={
                    "api_source": "Alpha Vantage",
                    "data_type": "commodity_price",
                    "commodity": function_name,
                    "commodity_name": commodity_name,
                    "price": current_value,
                    "date": current_date,
                    "pct_change": round(pct_change, 2) if pct_change else None,
                    "unit": "USD/barrel" if "Oil" in commodity_name else "USD",
                },
            )

            logger.info(
                f"Alpha Vantage commodity price: {commodity_name} = ${current_value}"
            )
            return [evidence]

        except Exception as e:
            logger.error(
                f"Alpha Vantage commodity price failed for {function_name}: {e}"
            )
            return []

    def _get_news_sentiment(self, query: str) -> List[Dict[str, Any]]:
        """Get news with sentiment analysis."""
        params = {
            "function": "NEWS_SENTIMENT",
            "tickers": query if query.isupper() and len(query) <= 5 else "",
            "topics": "" if query.isupper() else query[:50],
            "limit": 5,
            "apikey": self.api_key,
        }

        # Remove empty params
        params = {k: v for k, v in params.items() if v}
        params["apikey"] = self.api_key
        params["function"] = "NEWS_SENTIMENT"
        params["limit"] = 5

        try:
            response = self._make_request("", params=params)

            if not response or "feed" not in response:
                return []

            evidence_list = []
            for article in response["feed"][:5]:
                title = article.get("title", "Financial News")
                summary = article.get("summary", "")[:300]
                url = article.get("url", "")
                sentiment = article.get("overall_sentiment_label", "Neutral")
                sentiment_score = article.get("overall_sentiment_score", 0)
                time_published = article.get("time_published", "")

                # Parse date
                source_date = None
                if time_published:
                    try:
                        source_date = datetime.strptime(time_published[:8], "%Y%m%d")
                    except:
                        source_date = datetime.now(timezone.utc)

                snippet = f"{summary} [Sentiment: {sentiment} ({sentiment_score:.2f})]"

                evidence = self._create_evidence_dict(
                    title=title,
                    snippet=snippet,
                    url=url,
                    source_date=source_date or datetime.now(timezone.utc),
                    metadata={
                        "api_source": "Alpha Vantage",
                        "data_type": "news_sentiment",
                        "sentiment_label": sentiment,
                        "sentiment_score": sentiment_score,
                    },
                )
                evidence_list.append(evidence)

            return evidence_list

        except Exception as e:
            logger.error(f"Alpha Vantage news sentiment failed: {e}")
            return []

    def _transform_response(self, raw_response: Any) -> List[Dict[str, Any]]:
        """Generic transform - handled by specific methods."""
        return []


# ========== MARKETAUX ADAPTER (Financial News) ==========


class MarketauxAdapter(GovernmentAPIClient):
    """
    Marketaux API Adapter.

    Covers: Finance (financial news, sentiment)
    Jurisdiction: Global
    Rate limits: 100 requests/day (free tier)
    API key: Required

    Key endpoints:
    - /news/all: Financial news with entity filtering
    - /entity/search: Find companies/stocks
    - /entity/trending: Trending entities
    """

    def __init__(self):
        super().__init__(
            api_name="Marketaux",
            base_url="https://api.marketaux.com/v1",
            api_key=settings.MARKETAUX_API_KEY,
            cache_ttl=600,  # 10 minutes (news updates frequently)
            timeout=15,
            max_results=10,
        )

        # Marketaux uses api_token as query parameter
        if "Authorization" in self.headers:
            del self.headers["Authorization"]

    def is_relevant_for_domain(self, domain: str, jurisdiction: str) -> bool:
        """Marketaux covers Finance globally (news focus)."""
        return domain == "Finance"

    def prepare_query(
        self,
        claim_text: str,
        entities: Optional[List[Dict[str, str]]] = None,
    ) -> str:
        """B3.5: Marketaux is corporate-news search; skip when no company is named.

        Without an ORG entity, Marketaux's free-text endpoint fuzzy-matches
        news headlines to the full claim text and returns irrelevant
        company news — TRU-87D3-6415 surfaced "Photon Energy NV" stories
        for a BP/Energy Act claim because the raw claim text mentioned
        "energy" generically.

        Same skip pattern as Companies House (Session A): return "" when
        no ORG entity is present, triggering the search_with_cache empty-
        skip path. Returning the ORG name otherwise keeps the cache key
        focused (one news search per company name, not per claim).
        """
        return extract_entity_name(claim_text, entities, label="ORG") or ""

    def search(
        self,
        query: str,
        domain: str,
        jurisdiction: str,
        entities: Optional[List[Dict[str, str]]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search Marketaux for financial news.

        Args:
            query: Search query (e.g., "Tesla news", "market crash")
            domain: Finance
            jurisdiction: Any
            entities: Optional NER entities

        Returns:
            List of evidence dictionaries
        """
        if not self.is_relevant_for_domain(domain, jurisdiction):
            return []

        if not self.api_key:
            logger.warning("Marketaux API key not configured, skipping")
            return []

        try:
            # Extract ticker symbol if available
            ticker = self._extract_ticker(query, entities)

            # Build targeted search term from entities when no ticker found
            search_term = query
            if not ticker and entities:
                # NF-15: typed entities — Marketaux is news search, accept ORG only
                org_entities = [e["text"] for e in entities if e.get("label") == "ORG"]
                if org_entities:
                    search_term = org_entities[0]
                    logger.debug(
                        f"Marketaux using entity '{search_term}' "
                        f"instead of full query"
                    )

            # Search for news
            evidence = self._search_news(search_term, ticker)

            return evidence

        except Exception as e:
            logger.error(f"Marketaux search failed for '{query}': {e}")
            return []

    def _extract_ticker(
        self, query: str, entities: Optional[List[Dict[str, str]]] = None
    ) -> Optional[str]:
        """Extract stock ticker from query or entities."""
        # Common company to ticker mapping (same as Alpha Vantage)
        company_tickers = {
            "apple": "AAPL",
            "microsoft": "MSFT",
            "google": "GOOGL",
            "alphabet": "GOOGL",
            "amazon": "AMZN",
            "tesla": "TSLA",
            "meta": "META",
            "facebook": "META",
            "nvidia": "NVDA",
            "netflix": "NFLX",
            "intel": "INTC",
            "amd": "AMD",
            "ibm": "IBM",
            "disney": "DIS",
            "boeing": "BA",
            "nike": "NKE",
            "jpmorgan": "JPM",
            "goldman": "GS",
            "visa": "V",
            "mastercard": "MA",
            "walmart": "WMT",
            "coca-cola": "KO",
            "pepsi": "PEP",
            "pfizer": "PFE",
            "exxon": "XOM",
            "chevron": "CVX",
        }

        query_lower = query.lower()

        for company, ticker in company_tickers.items():
            if company in query_lower:
                return ticker

        # Check for direct ticker symbols
        ticker_match = re.search(r"\b([A-Z]{1,5})\b", query)
        if ticker_match:
            potential_ticker = ticker_match.group(1)
            common_words = {
                "A",
                "I",
                "THE",
                "AND",
                "OR",
                "FOR",
                "TO",
                "IN",
                "ON",
                "AT",
                "IS",
                "IT",
                "BE",
                "AS",
                "BY",
            }
            if potential_ticker not in common_words:
                return potential_ticker

        return None

    def _search_news(
        self, query: str, ticker: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Search for financial news."""
        params = {"api_token": self.api_key, "language": "en", "limit": 5}

        if ticker:
            params["symbols"] = ticker
        else:
            params["search"] = query[:100]

        try:
            response = self._make_request("news/all", params=params)

            if not response or "data" not in response:
                logger.warning(f"Marketaux returned no news for {query}")
                return []

            evidence_list = []
            for article in response["data"][:5]:
                title = article.get("title", "Financial News")
                description = article.get("description", "")[:400]
                url = article.get("url", "")
                published = article.get("published_at", "")
                source_name = article.get("source", "")

                # Extract sentiment if available
                sentiment = article.get("sentiment", {})
                sentiment_score = (
                    sentiment.get("score", 0) if isinstance(sentiment, dict) else 0
                )

                # Parse date
                source_date = None
                if published:
                    try:
                        source_date = datetime.fromisoformat(
                            published.replace("Z", "+00:00")
                        )
                    except:
                        source_date = datetime.now(timezone.utc)

                # Extract relevant entities
                entities = article.get("entities", [])
                entity_names = (
                    [e.get("name", "") for e in entities[:3]] if entities else []
                )
                entity_str = (
                    f" [Related: {', '.join(entity_names)}]" if entity_names else ""
                )

                snippet = f"{description}{entity_str}"
                if sentiment_score:
                    snippet += f" [Sentiment: {sentiment_score:.2f}]"

                evidence = self._create_evidence_dict(
                    title=title,
                    snippet=snippet,
                    url=url,
                    source_date=source_date or datetime.now(timezone.utc),
                    metadata={
                        "api_source": "Marketaux",
                        "data_type": "financial_news",
                        "source_name": source_name,
                        "sentiment_score": sentiment_score,
                        "entities": entity_names,
                    },
                )
                evidence_list.append(evidence)

            logger.info(f"Marketaux returned {len(evidence_list)} news items")
            return evidence_list

        except Exception as e:
            logger.error(f"Marketaux news search failed: {e}")
            return []

    def _transform_response(self, raw_response: Any) -> List[Dict[str, Any]]:
        """Generic transform - handled by _search_news."""
        return []


# ========== WORLD BANK ADAPTER ==========


class WorldBankAdapter(GovernmentAPIClient):
    """
    World Bank Open Data API Adapter.

    Covers: Finance, Demographics
    Jurisdiction: US, Global (worldwide macro-economic indicators)
    Free tier: Unlimited — fully open, no API key required
    Docs: https://datahelpdesk.worldbank.org/knowledgebase/articles/889392
    """

    # Map common query terms to World Bank indicator codes
    INDICATOR_MAP = {
        "gdp": "NY.GDP.MKTP.CD",
        "gdp growth": "NY.GDP.MKTP.KD.ZG",
        "gdp per capita": "NY.GDP.PCAP.CD",
        "inflation": "FP.CPI.TOTL.ZG",
        "unemployment": "SL.UEM.TOTL.ZS",
        "population": "SP.POP.TOTL",
        "population growth": "SP.POP.GROW",
        "life expectancy": "SP.DYN.LE00.IN",
        "poverty": "SI.POV.DDAY",
        "trade": "NE.TRD.GNFS.ZS",
        "exports": "NE.EXP.GNFS.ZS",
        "imports": "NE.IMP.GNFS.ZS",
        "debt": "GC.DOD.TOTL.GD.ZS",
        "government debt": "GC.DOD.TOTL.GD.ZS",
        "interest rate": "FR.INR.LEND",
        "foreign investment": "BX.KLT.DINV.WD.GD.ZS",
        "fdi": "BX.KLT.DINV.WD.GD.ZS",
        "gni": "NY.GNP.MKTP.CD",
        "gni per capita": "NY.GNP.PCAP.CD",
        "co2 emissions": "EN.ATM.CO2E.KT",
        "electricity": "EG.USE.ELEC.KH.PC",
        "internet users": "IT.NET.USER.ZS",
        "literacy": "SE.ADT.LITR.ZS",
        "health expenditure": "SH.XPD.CHEX.GD.ZS",
        "education expenditure": "SE.XPD.TOTL.GD.ZS",
        "birth rate": "SP.DYN.CBRT.IN",
        "death rate": "SP.DYN.CDRT.IN",
        "fertility rate": "SP.DYN.TFRT.IN",
        "infant mortality": "SP.DYN.IMRT.IN",
        "current account": "BN.CAB.XOKA.GD.ZS",
    }

    # Map jurisdictions to World Bank country codes
    COUNTRY_MAP = {
        "UK": "GBR",
        "US": "USA",
        "EU": "EUU",
        "Global": "WLD",
    }

    def __init__(self):
        super().__init__(
            api_name="World Bank",
            base_url="https://api.worldbank.org/v2",
            api_key=None,
            cache_ttl=86400 * 7,  # 7 days — data updates quarterly
            timeout=10,
            max_results=5,
            emits_structural_metadata=True,  # NF-07-v2: indicator data, structural
        )
        # World Bank API uses no auth headers
        self.headers = {"Accept": "application/json"}

    def is_relevant_for_domain(self, domain: str, jurisdiction: str) -> bool:
        """World Bank covers Finance and Demographics globally."""
        return domain in ["Finance", "Demographics"]

    def _match_indicator(self, query: str) -> Optional[str]:
        """Match query text to a World Bank indicator code."""
        query_lower = query.lower()
        # Try exact phrase matches (longest first for specificity)
        for term in sorted(self.INDICATOR_MAP.keys(), key=len, reverse=True):
            if term in query_lower:
                return self.INDICATOR_MAP[term]
        return None

    def search(
        self,
        query: str,
        domain: str,
        jurisdiction: str,
        entities: Optional[List[Dict[str, Any]]] = None,
    ) -> List[Dict[str, Any]]:
        if not self.is_relevant_for_domain(domain, jurisdiction):
            return []

        indicator_code = self._match_indicator(query)
        if not indicator_code:
            logger.info(f"World Bank: No indicator match for query '{query}'")
            return []

        country_code = self.COUNTRY_MAP.get(jurisdiction, "WLD")

        try:
            # Fetch latest 5 years of data
            params = {
                "format": "json",
                "per_page": "5",
                "mrv": "5",  # Most recent 5 values
            }
            endpoint = f"country/{country_code}/indicator/{indicator_code}"
            response = self._make_request(endpoint, params=params)

            if not response or not isinstance(response, list) or len(response) < 2:
                return []

            metadata = response[0]
            data_entries = response[1]

            if not data_entries:
                return []

            return self._transform_response(
                {
                    "metadata": metadata,
                    "data": data_entries,
                    "indicator_code": indicator_code,
                    "country_code": country_code,
                }
            )

        except Exception as e:
            logger.error(f"World Bank search failed: {e}")
            return []

    def _transform_response(self, raw_response: Any) -> List[Dict[str, Any]]:
        """Transform World Bank API response to evidence format."""
        evidence_list = []
        data_entries = raw_response.get("data", [])
        indicator_code = raw_response.get("indicator_code", "")
        country_code = raw_response.get("country_code", "WLD")

        # Filter to entries with actual values
        valid_entries = [e for e in data_entries if e.get("value") is not None]
        if not valid_entries:
            return []

        # Build a single evidence item summarising the trend
        latest = valid_entries[0]
        indicator_name = latest.get("indicator", {}).get("value", "Economic Indicator")
        country_name = latest.get("country", {}).get("value", "World")
        latest_year = latest.get("date", "")
        latest_value = latest.get("value")

        # Format the value nicely
        if latest_value is not None:
            if abs(latest_value) >= 1_000_000_000:
                formatted = f"${latest_value / 1_000_000_000:,.1f}B"
            elif abs(latest_value) >= 1_000_000:
                formatted = f"${latest_value / 1_000_000:,.1f}M"
            elif abs(latest_value) < 100:
                formatted = f"{latest_value:.2f}"
            else:
                formatted = f"{latest_value:,.0f}"
        else:
            formatted = "N/A"

        # Build trend snippet from available years
        trend_parts = []
        for entry in valid_entries[:5]:
            year = entry.get("date", "?")
            val = entry.get("value")
            if val is not None:
                if abs(val) < 100:
                    trend_parts.append(f"{year}: {val:.2f}")
                elif abs(val) >= 1_000_000_000:
                    trend_parts.append(f"{year}: ${val / 1_000_000_000:,.1f}B")
                else:
                    trend_parts.append(f"{year}: {val:,.0f}")

        snippet = (
            f"{indicator_name} — {country_name} ({latest_year}): {formatted}. "
            f"Trend: {'; '.join(trend_parts)}. "
            f"Source: World Bank Open Data."
        )

        evidence = self._create_evidence_dict(
            title=f"{indicator_name} — {country_name}",
            snippet=snippet,
            url=f"https://data.worldbank.org/indicator/{indicator_code}?locations={country_code}",
            source_date=(
                datetime(int(latest_year), 1, 1, tzinfo=timezone.utc)
                if latest_year
                else None
            ),
            metadata={
                "indicator_code": indicator_code,
                "indicator_name": indicator_name,
                "country": country_name,
                "country_code": country_code,
                "latest_year": latest_year,
                "latest_value": latest_value,
                "data_points": len(valid_entries),
            },
        )
        evidence_list.append(evidence)

        return evidence_list
