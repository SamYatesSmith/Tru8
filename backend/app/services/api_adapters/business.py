"""
Business API Adapters

Adapters for business and company data:
- Companies House (UK company registry)
- Wikidata (structured knowledge base)
"""

import logging
import base64
from typing import List, Dict, Any, Optional
from datetime import datetime

from app.services.government_api_client import GovernmentAPIClient

logger = logging.getLogger(__name__)


# ========== COMPANIES HOUSE ADAPTER ==========


class CompaniesHouseAdapter(GovernmentAPIClient):
    """
    Companies House (UK) API Adapter.

    Covers: Government, Finance
    Jurisdiction: UK
    Free tier: 600 requests/hour
    API key: Required (get from https://developer.company-information.service.gov.uk/)
    """

    def __init__(self):
        from app.core.config import settings

        api_key = settings.COMPANIES_HOUSE_API_KEY or None

        super().__init__(
            api_name="Companies House",
            base_url="https://api.company-information.service.gov.uk",
            api_key=api_key,
            cache_ttl=86400 * 3,  # 3 days (company data changes slowly)
            timeout=10,
            max_results=10,
        )

        # Companies House uses HTTP Basic Auth with API key as username
        if self.api_key:
            credentials = base64.b64encode(f"{self.api_key}:".encode()).decode()
            self.headers["Authorization"] = f"Basic {credentials}"

    def is_relevant_for_domain(self, domain: str, jurisdiction: str) -> bool:
        """Companies House covers Politics and Finance for UK only."""
        return (
            domain in ["Politics", "Finance"]
            and jurisdiction == "UK"  # UK-specific, not Global
        )

    def search(
        self,
        query: str,
        domain: str,
        jurisdiction: str,
        entities: Optional[List[Dict[str, str]]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search Companies House for UK company information.

        Args:
            query: Search query (e.g., "BP PLC")
            domain: Government or Finance
            jurisdiction: UK

        Returns:
            List of evidence dictionaries
        """
        if not self.is_relevant_for_domain(domain, jurisdiction):
            return []

        if not self.api_key:
            logger.warning("Companies House API key not configured, skipping")
            return []

        query = self._sanitize_query(query)

        # Companies House search endpoint
        params = {"q": query, "items_per_page": self.max_results}

        try:
            response = self._make_request("/search/companies", params=params)

            if not response or "items" not in response:
                logger.warning(f"Companies House returned empty response for: {query}")
                return []

            return self._transform_response(response)

        except Exception as e:
            logger.error(f"Companies House search failed for '{query}': {e}")
            return []

    def _transform_response(self, raw_response: Any) -> List[Dict[str, Any]]:
        """
        Transform Companies House API response to standardized evidence format.

        Companies House response structure:
        {
          "items": [
            {
              "title": "BP P.L.C.",
              "company_number": "00102498",
              "company_status": "active",
              "date_of_creation": "1909-04-14",
              "company_type": "plc",
              "address": {...}
            }
          ]
        }
        """
        evidence_list = []

        for item in raw_response.get("items", []):
            try:
                title = item.get("title", "UK Company")
                company_number = item.get("company_number")
                company_status = item.get("company_status", "unknown")
                company_type = item.get("company_type", "")

                # Build URL to company page
                url = f"https://find-and-update.company-information.service.gov.uk/company/{company_number}"

                # Build snippet
                snippet = (
                    f"{title} (Company No. {company_number}). "
                    f"Status: {company_status}. "
                    f"Type: {company_type}."
                )

                # Parse creation date
                creation_date_str = item.get("date_of_creation")
                source_date = None
                if creation_date_str:
                    try:
                        source_date = datetime.fromisoformat(creation_date_str)
                    except Exception:
                        pass

                # Companies House metadata
                metadata = {
                    "api_source": "Companies House",
                    "company_number": company_number,
                    "company_status": company_status,
                    "company_type": company_type,
                    "address": item.get("address", {}),
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
                logger.warning(f"Failed to parse Companies House item: {e}")
                continue

        logger.info(f"Companies House returned {len(evidence_list)} evidence items")
        return evidence_list


# ========== WIKIDATA ADAPTER ==========


class WikidataAdapter(GovernmentAPIClient):
    """
    Wikidata Query Service Adapter.

    Covers: General
    Jurisdiction: Global
    Free tier: Unlimited (polite usage)
    API key: Not required
    """

    def __init__(self):
        super().__init__(
            api_name="Wikidata",
            base_url="https://www.wikidata.org/w/api.php",
            api_key=None,
            cache_ttl=86400 * 30,  # 30 days (structured data stable)
            timeout=15,
            max_results=10,
            priority_tier=3,  # General reference
        )

    def is_relevant_for_domain(self, domain: str, jurisdiction: str) -> bool:
        """Wikidata covers structured data for General domain."""
        return domain == "General"

    def search(
        self,
        query: str,
        domain: str,
        jurisdiction: str,
        entities: Optional[List[Dict[str, str]]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search Wikidata entities.

        Args:
            query: Search query
            domain: General
            jurisdiction: Any

        Returns:
            List of evidence dictionaries
        """
        if not self.is_relevant_for_domain(domain, jurisdiction):
            return []

        query = self._sanitize_query(query)

        params = {
            "action": "wbsearchentities",
            "search": query,
            "language": "en",
            "limit": self.max_results,
            "format": "json",
        }

        try:
            response = self._make_request("", params=params)

            if not response or "search" not in response:
                logger.warning(f"Wikidata returned empty response for: {query}")
                return []

            return self._transform_response(response)

        except Exception as e:
            logger.error(f"Wikidata search failed for '{query}': {e}")
            return []

    def _transform_response(self, raw_response: Any) -> List[Dict[str, Any]]:
        """Transform Wikidata API response to standardized evidence format."""
        evidence_list = []

        for item in raw_response.get("search", []):
            try:
                entity_id = item.get("id")
                title = item.get("label", f"Wikidata Entity {entity_id}")
                description = item.get("description", "")

                url = f"https://www.wikidata.org/wiki/{entity_id}"

                snippet = description if description else f"Wikidata entity: {title}"

                metadata = {
                    "api_source": "Wikidata",
                    "entity_id": entity_id,
                    "concepturi": item.get("concepturi"),
                }

                evidence = self._create_evidence_dict(
                    title=title,
                    snippet=snippet,
                    url=url,
                    source_date=None,
                    metadata=metadata,
                )

                evidence_list.append(evidence)

            except Exception as e:
                logger.warning(f"Failed to parse Wikidata item: {e}")
                continue

        logger.info(f"Wikidata returned {len(evidence_list)} evidence items")
        return evidence_list
