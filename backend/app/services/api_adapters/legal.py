"""
Legal API Adapters

Adapters for legal and government data:
- GOV.UK (UK government content)
- Hansard (UK Parliament debates)
- GovInfo (US federal statutes)
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from app.services.government_api_client import GovernmentAPIClient
from app.services.legal_search import LegalSearchService

logger = logging.getLogger(__name__)


# ========== GOV.UK CONTENT API ADAPTER ==========


class GovUKAdapter(GovernmentAPIClient):
    """
    GOV.UK Content API Adapter.

    Covers: Government, General
    Jurisdiction: UK
    Free tier: Unlimited
    API key: Not required
    """

    def __init__(self):
        super().__init__(
            api_name="GOV.UK Content API",
            base_url="https://www.gov.uk/api/search.json",
            api_key=None,
            cache_ttl=86400,  # 1 day
            timeout=10,
            max_results=10,
        )

    def is_relevant_for_domain(self, domain: str, jurisdiction: str) -> bool:
        """GOV.UK covers Politics, General, History, and Law for UK only."""
        return (
            domain in ["Politics", "General", "History", "Law"] and jurisdiction == "UK"
        )

    def search(
        self,
        query: str,
        domain: str,
        jurisdiction: str,
        entities: Optional[List[Dict[str, str]]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search GOV.UK content.

        Args:
            query: Search query
            domain: Government or General
            jurisdiction: UK

        Returns:
            List of evidence dictionaries
        """
        if not self.is_relevant_for_domain(domain, jurisdiction):
            return []

        targeted_query = self._build_targeted_query(query, entities)

        params = {"q": targeted_query, "count": self.max_results}

        try:
            # GOV.UK search doesn't use /api/ prefix in base_url
            response = self._make_request("", params=params)

            if not response or "results" not in response:
                logger.warning(f"GOV.UK returned empty response for: {targeted_query}")
                return []

            return self._transform_response(response)

        except Exception as e:
            logger.error(f"GOV.UK search failed for '{query}': {e}")
            return []

    def _transform_response(self, raw_response: Any) -> List[Dict[str, Any]]:
        """Transform GOV.UK API response to standardized evidence format."""
        evidence_list = []

        for item in raw_response.get("results", []):
            try:
                title = item.get("title", "GOV.UK Content")
                description = item.get("description", "")
                url = f"https://www.gov.uk{item.get('link', '')}"

                snippet = description[:300] if description else title

                # Parse public timestamp
                public_timestamp = item.get("public_timestamp")
                source_date = None
                if public_timestamp:
                    try:
                        source_date = datetime.fromisoformat(
                            public_timestamp.replace("Z", "+00:00")
                        )
                    except Exception:
                        pass

                metadata = {
                    "api_source": "GOV.UK",
                    "format": item.get("format"),
                    "organisations": item.get("organisations", []),
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
                logger.warning(f"Failed to parse GOV.UK item: {e}")
                continue

        logger.info(f"GOV.UK returned {len(evidence_list)} evidence items")
        return evidence_list


# ========== UK PARLIAMENT HANSARD ADAPTER ==========


class HansardAdapter(GovernmentAPIClient):
    """
    UK Parliament Hansard API Adapter.

    Covers: Government, Law
    Jurisdiction: UK
    Free tier: Unlimited
    API key: Not required
    """

    def __init__(self):
        super().__init__(
            api_name="UK Parliament Hansard",
            base_url="https://hansard-api.parliament.uk",
            api_key=None,
            cache_ttl=86400 * 7,  # 7 days (historical records)
            timeout=15,
            max_results=10,
        )

    def is_relevant_for_domain(self, domain: str, jurisdiction: str) -> bool:
        """Hansard covers Politics and Law for UK only."""
        return domain in ["Politics", "Law"] and jurisdiction == "UK"

    def search(
        self,
        query: str,
        domain: str,
        jurisdiction: str,
        entities: Optional[List[Dict[str, str]]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search UK Parliament Hansard debates.

        Args:
            query: Search query
            domain: Government or Law
            jurisdiction: UK

        Returns:
            List of evidence dictionaries
        """
        if not self.is_relevant_for_domain(domain, jurisdiction):
            return []

        query = self._sanitize_query(query)

        params = {"searchTerm": query, "take": self.max_results}

        try:
            response = self._make_request("/search/debates.json", params=params)

            if not response or "Response" not in response:
                logger.warning(f"Hansard returned empty response for: {query}")
                return []

            return self._transform_response(response)

        except Exception as e:
            logger.error(f"Hansard search failed for '{query}': {e}")
            return []

    def _transform_response(self, raw_response: Any) -> List[Dict[str, Any]]:
        """Transform Hansard API response to standardized evidence format."""
        evidence_list = []

        for item in raw_response.get("Response", {}).get("Results", []):
            try:
                title = item.get("Title", "Parliamentary Debate")
                excerpt = item.get("Excerpt", "")
                url = item.get("Url", "https://hansard.parliament.uk/")

                snippet = excerpt[:300] if excerpt else title

                # Parse date
                date_str = item.get("Date")
                source_date = None
                if date_str:
                    try:
                        source_date = datetime.fromisoformat(
                            date_str.replace("Z", "+00:00")
                        )
                    except Exception:
                        pass

                metadata = {
                    "api_source": "UK Parliament Hansard",
                    "debate_type": item.get("DebateType"),
                    "member": item.get("Member"),
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
                logger.warning(f"Failed to parse Hansard item: {e}")
                continue

        logger.info(f"Hansard returned {len(evidence_list)} evidence items")
        return evidence_list


# ========== GOVINFO.GOV LEGAL STATUTES ADAPTER ==========


class GovInfoAdapter(GovernmentAPIClient):
    """
    GovInfo.gov API Adapter for US Legal Statutes.

    Wraps the existing LegalSearchService (Phase 4) to integrate with
    Phase 5 Government API adapter system.

    Coverage:
    - US federal statutes and legislation
    - Congress.gov for bills and laws
    - Direct citation lookup (fastest)
    - Year + keyword search (filtered)
    - Full-text search (broad)

    Domain: Law
    Jurisdiction: US
    API: GovInfo.gov (requires GOVINFO_API_KEY)
    """

    def __init__(self):
        from app.core.config import settings

        # Initialize legal search service (handles GovInfo + Congress APIs)
        self.legal_service = LegalSearchService()

        super().__init__(
            api_name="GovInfo.gov",
            base_url="https://api.govinfo.gov",
            timeout=(
                settings.LEGAL_API_TIMEOUT_SECONDS
                if hasattr(settings, "LEGAL_API_TIMEOUT_SECONDS")
                else 10
            ),
            max_results=5,  # Statutes are high-quality, don't need many
        )

        # Check if API key is configured
        if not settings.GOVINFO_API_KEY:
            logger.warning(
                "GOVINFO_API_KEY not configured - GovInfo adapter will return empty results"
            )

    def is_relevant_for_domain(self, domain: str, jurisdiction: str) -> bool:
        """
        GovInfo covers Law, Politics, and History for US jurisdiction.

        Political articles frequently reference legislation (e.g., "DROP Act of 2025"),
        so we include Politics to ensure congressional acts are properly verified.

        Args:
            domain: Domain classification (Law, History, Politics, etc.)
            jurisdiction: US, UK, EU, Global

        Returns:
            True if this adapter can handle the domain/jurisdiction
        """
        return domain in ["Law", "History", "Politics"] and jurisdiction in [
            "US",
            "Global",
        ]

    def search(
        self,
        query: str,
        domain: str,
        jurisdiction: str,
        entities: Optional[List[Dict[str, str]]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search US federal statutes and legislation.

        Uses three-tier search strategy:
        1. Direct citation lookup (if citation detected)
        2. Year + keyword search (if year detected)
        3. Full-text search (fallback)

        Args:
            query: Search query (claim text)
            domain: Law
            jurisdiction: US

        Returns:
            List of evidence dictionaries with statute excerpts
        """
        logger.info(
            f"[GOVINFO] search() CALLED - query: '{query[:100]}...', domain: {domain}, jurisdiction: {jurisdiction}"
        )

        if not self.is_relevant_for_domain(domain, jurisdiction):
            logger.info(
                f"   [GOVINFO] Not relevant for domain={domain}, jurisdiction={jurisdiction}"
            )
            return []

        logger.info(f"   [GOVINFO] Domain/jurisdiction match confirmed")

        try:
            # Extract legal metadata from query using classifier
            # (This is fast - just regex patterns)
            from app.utils.legal_claim_detector import LegalClaimDetector

            detector = LegalClaimDetector()
            result = detector.classify(query)

            # Only proceed if classified as legal
            if not result.get("is_legal"):
                logger.info(
                    f"GovInfo: Query not classified as legal, skipping: {query[:50]}"
                )
                return []

            legal_metadata = result.get("metadata", {})

            logger.info(
                f"GovInfo: Searching for legal claim with metadata: "
                f"year={legal_metadata.get('year')}, "
                f"jurisdiction={legal_metadata.get('jurisdiction')}"
            )

            # Call legal search service (async, so we need to run it)
            import asyncio

            try:
                # Try to get running loop
                loop = asyncio.get_running_loop()
                # We're in a sync context called from async via asyncio.to_thread
                # So we can't use await here, but the service handles this
                results = asyncio.run(
                    self.legal_service.search_statutes(query, legal_metadata)
                )
            except RuntimeError:
                # No running loop, create new one
                results = asyncio.run(
                    self.legal_service.search_statutes(query, legal_metadata)
                )

            # Transform legal search results to standardized evidence format
            return self._transform_response(results)

        except Exception as e:
            logger.error(f"GovInfo search failed for '{query}': {e}", exc_info=True)
            return []

    def _transform_response(
        self, legal_results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Transform LegalSearchService results to standardized evidence format.

        LegalSearchService returns:
        {
            "title": "Act name and section",
            "text": "Statute text excerpt",
            "url": "govinfo.gov or legislation.gov.uk URL",
            "source_date": "YYYY-MM-DD",
            "citation": "Formal citation",
            "jurisdiction": "US" or "UK"
        }

        Standardized format:
        {
            "text": "Evidence text",
            "source": "GovInfo.gov",
            "url": "...",
            "title": "...",
            "published_date": "...",
            "external_source_provider": "GovInfo.gov",
            "metadata": {...}
        }
        """
        evidence_list = []

        for item in legal_results:
            try:
                # Extract fields from legal search result
                title = item.get("title", "Federal Statute")
                text = item.get("text", "")
                url = item.get("url", "")
                citation = item.get("citation", "")
                jurisdiction = item.get("jurisdiction", "US")

                # Parse source_date (may be string or datetime)
                source_date = item.get("source_date")
                if source_date and isinstance(source_date, str):
                    try:
                        source_date = datetime.fromisoformat(
                            source_date.replace("Z", "+00:00")
                        )
                    except (ValueError, AttributeError):
                        source_date = None

                # Create metadata dict with legal-specific fields
                metadata = {
                    "citation": citation,
                    "jurisdiction": jurisdiction,
                    "statute_type": item.get("statute_type", "federal"),
                    "section": item.get("section"),
                    "year": item.get("year"),
                }

                # Create standardized evidence dict using base class helper
                evidence = self._create_evidence_dict(
                    title=title,
                    snippet=text,
                    url=url,
                    source_date=source_date,
                    metadata=metadata,
                )

                evidence_list.append(evidence)

            except Exception as e:
                logger.warning(f"Failed to parse GovInfo legal result: {e}")
                continue

        logger.info(f"GovInfo returned {len(evidence_list)} statute excerpts")
        return evidence_list


# ========== UK LEGISLATION ADAPTER ==========


class LegislationGovUKAdapter(GovernmentAPIClient):
    """
    legislation.gov.uk Adapter for UK statute text.

    Covers: Law
    Jurisdiction: UK, Global
    Free tier: Unlimited (no API key required, no documented rate limits)
    Format: Atom XML feeds

    Provides access to all UK primary legislation (Acts), secondary legislation
    (Statutory Instruments), and retained EU law.
    """

    def __init__(self):
        super().__init__(
            api_name="UK Legislation",
            base_url="https://www.legislation.gov.uk",
            api_key=None,
            cache_ttl=86400,  # 1 day (legislation text is stable)
            timeout=10,
            max_results=5,
            priority_tier=1,  # Domain specialist
        )
        # legislation.gov.uk returns Atom XML, not JSON
        self.headers["Accept"] = "application/atom+xml"

    def is_relevant_for_domain(self, domain: str, jurisdiction: str) -> bool:
        """UK Legislation covers Law for UK and Global."""
        return domain == "Law" and jurisdiction in ["UK", "Global"]

    def _make_request(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        method: str = "GET",
    ) -> Optional[Any]:
        """Override to return raw XML text instead of JSON."""
        import httpx

        url = f"{self.base_url}/{endpoint.lstrip('/')}"

        try:
            with httpx.Client(timeout=self.timeout, follow_redirects=True) as client:
                response = client.get(url, headers=self.headers, params=params)
                response.raise_for_status()
                return response.text
        except Exception as e:
            logger.warning(f"UK Legislation request failed: {e}")
            return None

    def search(
        self,
        query: str,
        domain: str,
        jurisdiction: str,
        entities: Optional[List[Dict[str, str]]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search legislation.gov.uk for UK statutes via Atom feeds.

        Args:
            query: Search query (e.g., "Online Safety Act")
            domain: Law
            jurisdiction: UK or Global

        Returns:
            List of evidence dictionaries with statute references
        """
        if not self.is_relevant_for_domain(domain, jurisdiction):
            return []

        query = self._sanitize_query(query)

        params = {
            "text": query,
            "results-count": self.max_results,
        }

        try:
            # Search across all legislation types
            response = self._make_request("all/data.feed", params=params)

            if not response:
                logger.warning(f"UK Legislation returned empty response for: {query}")
                return []

            return self._transform_response(response)

        except Exception as e:
            logger.error(f"UK Legislation search failed for '{query}': {e}")
            return []

    def _transform_response(self, raw_response: Any) -> List[Dict[str, Any]]:
        """Parse Atom XML feed and extract legislation entries."""
        import xml.etree.ElementTree as ET

        evidence_list = []
        atom_ns = "http://www.w3.org/2005/Atom"

        try:
            root = ET.fromstring(raw_response)

            for entry in root.findall(f"{{{atom_ns}}}entry"):
                try:
                    title_el = entry.find(f"{{{atom_ns}}}title")
                    title = (
                        title_el.text
                        if title_el is not None and title_el.text
                        else "UK Legislation"
                    )

                    # Get the legislation URL
                    link_el = entry.find(f"{{{atom_ns}}}link[@rel='alternate']")
                    if link_el is None:
                        link_el = entry.find(f"{{{atom_ns}}}link")
                    url = link_el.get("href", "") if link_el is not None else ""
                    if url and not url.startswith("http"):
                        url = f"https://www.legislation.gov.uk{url}"

                    # Get updated date
                    updated_el = entry.find(f"{{{atom_ns}}}updated")
                    source_date = None
                    if updated_el is not None and updated_el.text:
                        try:
                            source_date = datetime.fromisoformat(
                                updated_el.text.replace("Z", "+00:00")
                            )
                        except Exception:
                            pass

                    # Extract summary/content
                    summary_el = entry.find(f"{{{atom_ns}}}summary")
                    snippet = ""
                    if summary_el is not None and summary_el.text:
                        snippet = summary_el.text[:300]
                    else:
                        snippet = f"UK legislation: {title}"

                    # Extract category (legislation type)
                    category_el = entry.find(f"{{{atom_ns}}}category")
                    leg_type = (
                        category_el.get("term", "") if category_el is not None else ""
                    )

                    metadata = {
                        "api_source": "UK Legislation",
                        "legislation_type": leg_type,
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
                    logger.warning(f"Failed to parse legislation entry: {e}")
                    continue

        except ET.ParseError as e:
            logger.error(f"Failed to parse legislation XML: {e}")

        logger.info(f"UK Legislation returned {len(evidence_list)} statute references")
        return evidence_list
