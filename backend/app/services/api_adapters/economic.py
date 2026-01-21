"""
Economic API Adapters

Adapters for financial and economic data:
- ONS (UK Office for National Statistics)
- FRED (US Federal Reserve Economic Data)
- Alpha Vantage (Stocks, Forex, Crypto)
- Marketaux (Financial News)
"""

import logging
import os
import re
from typing import List, Dict, Any, Optional
from datetime import datetime

from app.services.government_api_client import GovernmentAPIClient
from app.core.config import settings

logger = logging.getLogger(__name__)


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
            max_results=10
        )

        # ONS-specific headers
        self.headers.update({
            "Accept": "application/json"
        })

    def is_relevant_for_domain(self, domain: str, jurisdiction: str) -> bool:
        """ONS covers Finance and Demographics for UK only."""
        return (
            domain in ["Finance", "Demographics"] and
            jurisdiction in ["UK", "Global"]  # Global allows UK data
        )

    def search(self, query: str, domain: str, jurisdiction: str, entities: Optional[List[Dict[str, str]]] = None) -> List[Dict[str, Any]]:
        """
        Search ONS datasets for economic/demographic data.

        Args:
            query: Search query (e.g., "unemployment rate 2024")
            domain: Finance or Demographics
            jurisdiction: UK

        Returns:
            List of evidence dictionaries
        """
        if not self.is_relevant_for_domain(domain, jurisdiction):
            return []

        query = self._sanitize_query(query)

        # ONS API endpoint for dataset search
        params = {
            "q": query,
            "limit": self.max_results
        }

        try:
            response = self._make_request("datasets", params=params)

            if not response or "items" not in response:
                logger.warning(f"ONS API returned empty response for: {query}")
                return []

            return self._transform_response(response)

        except Exception as e:
            logger.error(f"ONS search failed for '{query}': {e}")
            return []

    def _transform_response(self, raw_response: Any) -> List[Dict[str, Any]]:
        """
        Transform ONS API response to standardized evidence format.

        ONS response structure:
        {
          "items": [
            {
              "title": "Labour Market Statistics",
              "description": "UK unemployment rate...",
              "links": {"self": {"href": "https://..."}},
              "release_date": "2024-01-15"
            }
          ]
        }
        """
        evidence_list = []

        for item in raw_response.get("items", []):
            try:
                title = item.get("title", "ONS Dataset")
                description = item.get("description", "")

                # Extract URL
                links = item.get("links", {})
                url = links.get("self", {}).get("href", "https://www.ons.gov.uk")

                # Parse release date
                release_date_str = item.get("release_date")
                source_date = None
                if release_date_str:
                    try:
                        source_date = datetime.fromisoformat(release_date_str.replace("Z", "+00:00"))
                    except Exception:
                        pass

                # Extract key statistics from description
                snippet = description[:300] if description else title

                # ONS-specific metadata
                metadata = {
                    "api_source": "ONS",
                    "dataset_id": item.get("id"),
                    "dataset_type": item.get("type"),
                    "contact_name": item.get("contacts", [{}])[0].get("name") if item.get("contacts") else None
                }

                evidence = self._create_evidence_dict(
                    title=title,
                    snippet=snippet,
                    url=url,
                    source_date=source_date,
                    metadata=metadata
                )

                evidence_list.append(evidence)

            except Exception as e:
                logger.warning(f"Failed to parse ONS item: {e}")
                continue

        logger.info(f"ONS returned {len(evidence_list)} evidence items")
        return evidence_list


# ========== FRED ADAPTER (US Federal Reserve Economic Data) ==========

class FREDAdapter(GovernmentAPIClient):
    """
    FRED (Federal Reserve Economic Data) API Adapter.

    Covers: Finance
    Jurisdiction: US
    Free tier: 1,000 requests/day
    API key: Required
    """

    def __init__(self):
        api_key = os.getenv("FRED_API_KEY")

        super().__init__(
            api_name="FRED",
            base_url="https://api.stlouisfed.org/fred",
            api_key=api_key,
            cache_ttl=86400 * 7,  # 7 days (economic data changes slowly)
            timeout=10,
            max_results=10
        )

        # FRED uses API key as query parameter
        if self.api_key:
            del self.headers["Authorization"]

    def is_relevant_for_domain(self, domain: str, jurisdiction: str) -> bool:
        """FRED covers Finance for US."""
        return domain == "Finance" and jurisdiction in ["US", "Global"]

    def search(self, query: str, domain: str, jurisdiction: str, entities: Optional[List[Dict[str, str]]] = None) -> List[Dict[str, Any]]:
        """
        Search FRED for US economic data series.

        Args:
            query: Search query (e.g., "unemployment rate")
            domain: Finance
            jurisdiction: US

        Returns:
            List of evidence dictionaries
        """
        if not self.is_relevant_for_domain(domain, jurisdiction):
            return []

        if not self.api_key:
            logger.warning("FRED API key not configured, skipping")
            return []

        query = self._sanitize_query(query)

        # FRED series search
        params = {
            "search_text": query,
            "api_key": self.api_key,
            "file_type": "json",
            "limit": self.max_results
        }

        try:
            response = self._make_request("/series/search", params=params)

            if not response or "seriess" not in response:
                logger.warning(f"FRED returned empty response for: {query}")
                return []

            return self._transform_response(response)

        except Exception as e:
            logger.error(f"FRED search failed for '{query}': {e}")
            return []

    def _transform_response(self, raw_response: Any) -> List[Dict[str, Any]]:
        """Transform FRED API response to standardized evidence format."""
        evidence_list = []

        for series in raw_response.get("seriess", []):
            try:
                series_id = series.get("id")
                title = series.get("title", f"FRED Series {series_id}")
                notes = series.get("notes", "")

                # Build URL
                url = f"https://fred.stlouisfed.org/series/{series_id}"

                # Build snippet from notes
                snippet = notes[:300] if notes else f"Economic data series: {title}"

                # Parse dates
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
                    "frequency": series.get("frequency"),
                    "units": series.get("units"),
                    "seasonal_adjustment": series.get("seasonal_adjustment")
                }

                evidence = self._create_evidence_dict(
                    title=title,
                    snippet=snippet,
                    url=url,
                    source_date=source_date,
                    metadata=metadata
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
            max_results=10
        )

        # Alpha Vantage uses apikey as query parameter, not header
        if "Authorization" in self.headers:
            del self.headers["Authorization"]

    def is_relevant_for_domain(self, domain: str, jurisdiction: str) -> bool:
        """Alpha Vantage covers Finance globally."""
        return domain == "Finance"

    def search(self, query: str, domain: str, jurisdiction: str, entities: Optional[List[Dict[str, str]]] = None) -> List[Dict[str, Any]]:
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
            if any(term in query_lower for term in ["oil", "crude", "brent", "wti", "petroleum", "natural gas", "commodity", "barrel"]):
                evidence.extend(self._get_commodity_price(query))
            elif any(term in query_lower for term in ["bitcoin", "crypto", "ethereum", "btc", "eth"]):
                evidence.extend(self._get_crypto_rate(query))
            elif any(term in query_lower for term in ["exchange rate", "forex", "currency", "usd", "eur", "gbp"]):
                evidence.extend(self._get_forex_rate(query))
            elif any(term in query_lower for term in ["stock", "share", "price", "trading"]):
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

    def _extract_ticker(self, query: str, entities: Optional[List[Dict[str, str]]] = None) -> Optional[str]:
        """Extract stock ticker from query or entities."""
        # Common company to ticker mapping
        company_tickers = {
            "apple": "AAPL", "microsoft": "MSFT", "google": "GOOGL", "alphabet": "GOOGL",
            "amazon": "AMZN", "tesla": "TSLA", "meta": "META", "facebook": "META",
            "nvidia": "NVDA", "netflix": "NFLX", "intel": "INTC", "amd": "AMD",
            "ibm": "IBM", "oracle": "ORCL", "salesforce": "CRM", "adobe": "ADBE",
            "paypal": "PYPL", "uber": "UBER", "airbnb": "ABNB", "spotify": "SPOT",
            "twitter": "X", "snap": "SNAP", "pinterest": "PINS", "zoom": "ZM",
            "shopify": "SHOP", "square": "SQ", "block": "SQ", "coinbase": "COIN",
            "disney": "DIS", "warner": "WBD", "comcast": "CMCSA", "verizon": "VZ",
            "at&t": "T", "boeing": "BA", "lockheed": "LMT", "raytheon": "RTX",
            "jpmorgan": "JPM", "goldman": "GS", "morgan stanley": "MS", "citi": "C",
            "bank of america": "BAC", "wells fargo": "WFC", "visa": "V", "mastercard": "MA",
            "walmart": "WMT", "target": "TGT", "costco": "COST", "home depot": "HD",
            "nike": "NKE", "starbucks": "SBUX", "mcdonald": "MCD", "coca-cola": "KO",
            "pepsi": "PEP", "procter": "PG", "johnson": "JNJ", "pfizer": "PFE",
            "moderna": "MRNA", "exxon": "XOM", "chevron": "CVX", "shell": "SHEL",
        }

        query_lower = query.lower()

        # Check for company name matches
        for company, ticker in company_tickers.items():
            if company in query_lower:
                return ticker

        # Check for direct ticker symbols (uppercase, 1-5 chars)
        ticker_match = re.search(r'\b([A-Z]{1,5})\b', query)
        if ticker_match:
            potential_ticker = ticker_match.group(1)
            # Verify it's likely a ticker (not a common word)
            common_words = {"A", "I", "THE", "AND", "OR", "FOR", "TO", "IN", "ON", "AT", "IS", "IT", "BE", "AS", "BY"}
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
        params = {
            "function": "GLOBAL_QUOTE",
            "symbol": ticker,
            "apikey": self.api_key
        }

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
                source_date=datetime.utcnow(),
                metadata={
                    "api_source": "Alpha Vantage",
                    "data_type": "stock_quote",
                    "ticker": ticker,
                    "price": price,
                    "change": change,
                    "change_percent": change_pct,
                    "volume": volume
                }
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
            "apikey": self.api_key
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
                    source_date=datetime.utcnow(),
                    metadata={
                        "api_source": "Alpha Vantage",
                        "data_type": "symbol_search",
                        "ticker": symbol,
                        "company_name": name,
                        "type": match_type,
                        "region": region
                    }
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
            "bitcoin": "BTC", "btc": "BTC",
            "ethereum": "ETH", "eth": "ETH",
            "litecoin": "LTC", "ltc": "LTC",
            "ripple": "XRP", "xrp": "XRP",
            "dogecoin": "DOGE", "doge": "DOGE",
            "cardano": "ADA", "ada": "ADA",
            "solana": "SOL", "sol": "SOL",
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
            "apikey": self.api_key
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
                source_date=datetime.utcnow(),
                metadata={
                    "api_source": "Alpha Vantage",
                    "data_type": "crypto_rate",
                    "crypto": crypto,
                    "rate_usd": rate
                }
            )
            return [evidence]

        except Exception as e:
            logger.error(f"Alpha Vantage crypto rate failed: {e}")
            return []

    def _get_forex_rate(self, query: str) -> List[Dict[str, Any]]:
        """Get forex exchange rate."""
        # Extract currency pair from query
        currencies = {
            "usd": "USD", "dollar": "USD",
            "eur": "EUR", "euro": "EUR",
            "gbp": "GBP", "pound": "GBP", "sterling": "GBP",
            "jpy": "JPY", "yen": "JPY",
            "cad": "CAD", "canadian": "CAD",
            "aud": "AUD", "australian": "AUD",
            "chf": "CHF", "swiss": "CHF",
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
            "apikey": self.api_key
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
                source_date=datetime.utcnow(),
                metadata={
                    "api_source": "Alpha Vantage",
                    "data_type": "forex_rate",
                    "from_currency": from_curr,
                    "to_currency": to_curr,
                    "rate": rate
                }
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
            "apikey": self.api_key
        }

        try:
            response = self._make_request("", params=params)

            if not response or "data" not in response:
                logger.warning(f"Alpha Vantage returned no data for commodity {function_name}")
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
            source_date = datetime.utcnow()
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
                    "unit": "USD/barrel" if "Oil" in commodity_name else "USD"
                }
            )

            logger.info(f"Alpha Vantage commodity price: {commodity_name} = ${current_value}")
            return [evidence]

        except Exception as e:
            logger.error(f"Alpha Vantage commodity price failed for {function_name}: {e}")
            return []

    def _get_news_sentiment(self, query: str) -> List[Dict[str, Any]]:
        """Get news with sentiment analysis."""
        params = {
            "function": "NEWS_SENTIMENT",
            "tickers": query if query.isupper() and len(query) <= 5 else "",
            "topics": "" if query.isupper() else query[:50],
            "limit": 5,
            "apikey": self.api_key
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
                        source_date = datetime.utcnow()

                snippet = f"{summary} [Sentiment: {sentiment} ({sentiment_score:.2f})]"

                evidence = self._create_evidence_dict(
                    title=title,
                    snippet=snippet,
                    url=url,
                    source_date=source_date or datetime.utcnow(),
                    metadata={
                        "api_source": "Alpha Vantage",
                        "data_type": "news_sentiment",
                        "sentiment_label": sentiment,
                        "sentiment_score": sentiment_score
                    }
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
            max_results=10
        )

        # Marketaux uses api_token as query parameter
        if "Authorization" in self.headers:
            del self.headers["Authorization"]

    def is_relevant_for_domain(self, domain: str, jurisdiction: str) -> bool:
        """Marketaux covers Finance globally (news focus)."""
        return domain == "Finance"

    def search(self, query: str, domain: str, jurisdiction: str, entities: Optional[List[Dict[str, str]]] = None) -> List[Dict[str, Any]]:
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

            # Search for news
            evidence = self._search_news(query, ticker)

            return evidence

        except Exception as e:
            logger.error(f"Marketaux search failed for '{query}': {e}")
            return []

    def _extract_ticker(self, query: str, entities: Optional[List[Dict[str, str]]] = None) -> Optional[str]:
        """Extract stock ticker from query or entities."""
        # Common company to ticker mapping (same as Alpha Vantage)
        company_tickers = {
            "apple": "AAPL", "microsoft": "MSFT", "google": "GOOGL", "alphabet": "GOOGL",
            "amazon": "AMZN", "tesla": "TSLA", "meta": "META", "facebook": "META",
            "nvidia": "NVDA", "netflix": "NFLX", "intel": "INTC", "amd": "AMD",
            "ibm": "IBM", "disney": "DIS", "boeing": "BA", "nike": "NKE",
            "jpmorgan": "JPM", "goldman": "GS", "visa": "V", "mastercard": "MA",
            "walmart": "WMT", "coca-cola": "KO", "pepsi": "PEP", "pfizer": "PFE",
            "exxon": "XOM", "chevron": "CVX",
        }

        query_lower = query.lower()

        for company, ticker in company_tickers.items():
            if company in query_lower:
                return ticker

        # Check for direct ticker symbols
        ticker_match = re.search(r'\b([A-Z]{1,5})\b', query)
        if ticker_match:
            potential_ticker = ticker_match.group(1)
            common_words = {"A", "I", "THE", "AND", "OR", "FOR", "TO", "IN", "ON", "AT", "IS", "IT", "BE", "AS", "BY"}
            if potential_ticker not in common_words:
                return potential_ticker

        return None

    def _search_news(self, query: str, ticker: Optional[str] = None) -> List[Dict[str, Any]]:
        """Search for financial news."""
        params = {
            "api_token": self.api_key,
            "language": "en",
            "limit": 5
        }

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
                sentiment_score = sentiment.get("score", 0) if isinstance(sentiment, dict) else 0

                # Parse date
                source_date = None
                if published:
                    try:
                        source_date = datetime.fromisoformat(published.replace("Z", "+00:00"))
                    except:
                        source_date = datetime.utcnow()

                # Extract relevant entities
                entities = article.get("entities", [])
                entity_names = [e.get("name", "") for e in entities[:3]] if entities else []
                entity_str = f" [Related: {', '.join(entity_names)}]" if entity_names else ""

                snippet = f"{description}{entity_str}"
                if sentiment_score:
                    snippet += f" [Sentiment: {sentiment_score:.2f}]"

                evidence = self._create_evidence_dict(
                    title=title,
                    snippet=snippet,
                    url=url,
                    source_date=source_date or datetime.utcnow(),
                    metadata={
                        "api_source": "Marketaux",
                        "data_type": "financial_news",
                        "source_name": source_name,
                        "sentiment_score": sentiment_score,
                        "entities": entity_names
                    }
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
