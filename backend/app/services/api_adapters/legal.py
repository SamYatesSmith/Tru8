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
from app.utils.adapter_query_helpers import extract_topic_phrase

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
            # P2: capped 10->5. GOV.UK is single-domain (gov.uk); 10 same-domain
            # results flooded multi-claim pools, spiking top_domain_share and
            # diluting factual_weight_share (replay bench, TRU-B4A3). 5 keeps the
            # primary-source win without dominating the landscape.
            max_results=5,
        )

    def prepare_query(self, claim_text, entities=None):
        # GOV.UK search ranks on topic-keyword overlap; full sentences score
        # poorly. extract_topic_phrase falls back to claim_text when no
        # priority entity is present (B5: _build_targeted_query was the
        # legacy fallback, deleted alongside the rest of Session B cleanup).
        return extract_topic_phrase(claim_text, entities)

    def is_relevant_for_domain(self, domain: str, jurisdiction: str) -> bool:
        """GOV.UK covers Politics, General, History, Law, and Finance for UK only.

        P2: Finance was wrongly excluded — Treasury/HMRC/OBR/Budget & Autumn
        Statement content is squarely on gov.uk. A live probe showed the same
        query returning 0 under Finance routing but 10 under Politics, so fiscal
        claims (which classify as Finance) were self-excluded from the primary
        UK-gov corpus. See audit/2026-05-15_adapter_prepare_query_audit.md.
        """
        return (
            domain in ["Politics", "General", "History", "Law", "Finance"]
            and jurisdiction == "UK"
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

        # B5: query is already shaped by prepare_query upstream.
        params = {"q": query, "count": self.max_results}

        try:
            # GOV.UK search doesn't use /api/ prefix in base_url
            response = self._make_request("", params=params)

            if not response or "results" not in response:
                logger.warning(f"GOV.UK returned empty response for: {query}")
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
                # NF-10: GOV.UK search API sometimes returns an absolute URL in
                # `link` (e.g. pointing to legislation.gov.uk when the result
                # is an external cross-reference). Prepending the base URL
                # unconditionally produced malformed URLs like
                # "https://www.gov.ukhttps://www.legislation.gov.uk/",
                # which urlparse mangled into domain "www.gov.ukhttps:" in
                # evidence analytics. Guard by checking scheme first — same
                # pattern UK Legislation's _transform_response uses at
                # line ~651.
                link = item.get("link", "")
                if link.startswith(("http://", "https://")):
                    url = link
                else:
                    url = f"https://www.gov.uk{link}"

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
            # P2: capped 10->5 (same single-domain flooding concern as GOV.UK —
            # parliament.uk). Applies to debates + surfaced contributions combined.
            max_results=5,
        )

    def prepare_query(self, claim_text, entities=None):
        # Hansard's searchTerm is a topic-keyword index — sentences match nothing.
        return extract_topic_phrase(claim_text, entities)

    def is_relevant_for_domain(self, domain: str, jurisdiction: str) -> bool:
        """Hansard covers Politics, Law, and Finance for UK only.

        P2: Finance was wrongly excluded — Treasury questions, Budget/Autumn
        Statement debates and Bank of England discussions are core Hansard
        content. Fiscal claims classify as Finance and were self-excluded.
        """
        return domain in ["Politics", "Law", "Finance"] and jurisdiction == "UK"

    def search(
        self,
        query: str,
        domain: str,
        jurisdiction: str,
        entities: Optional[List[Dict[str, str]]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search UK Parliament Hansard debates + contributions.

        Args:
            query: Search query
            domain: Politics or Law
            jurisdiction: UK

        Returns:
            List of evidence dictionaries
        """
        if not self.is_relevant_for_domain(domain, jurisdiction):
            return []

        query = self._sanitize_query(query)

        params = {"searchTerm": query, "take": self.max_results}

        try:
            # NF-06: /search.json (not /search/debates.json) returns Debates +
            # Contributions side-by-side. Cross-matching yields topical debate
            # metadata with real speech-text snippets. Response envelope has
            # no "Response" wrapper — arrays are at the top level.
            response = self._make_request("/search.json", params=params)

            if not response or (
                "Debates" not in response and "Contributions" not in response
            ):
                logger.warning(f"Hansard returned empty response for: {query}")
                return []

            return self._transform_response(response)

        except Exception as e:
            logger.error(f"Hansard search failed for '{query}': {e}")
            return []

    def _transform_response(self, raw_response: Any) -> List[Dict[str, Any]]:
        """Transform Hansard /search.json response to standardised evidence.

        NF-06: Debates are topical (match by title), Contributions contain
        actual speech text. Cross-match by DebateSectionExtId so topical
        debates get real speech snippets; fall back to synthesised metadata
        snippet if a debate has no matching contribution.
        """
        evidence_list: List[Dict[str, Any]] = []

        # Index contributions by debate ID for snippet enrichment.
        contributions_by_debate: Dict[str, List[Dict[str, Any]]] = {}
        for c in raw_response.get("Contributions") or []:
            did = c.get("DebateSectionExtId")
            if did:
                contributions_by_debate.setdefault(did, []).append(c)

        for debate in raw_response.get("Debates") or []:
            try:
                title = debate.get("Title") or "Parliamentary Debate"
                ext_id = debate.get("DebateSectionExtId")
                sitting_date_str = debate.get("SittingDate")
                house = debate.get("House") or "Commons"
                debate_section = debate.get("DebateSection")

                source_date = None
                date_short = ""
                if sitting_date_str:
                    try:
                        source_date = datetime.fromisoformat(
                            sitting_date_str.replace("Z", "+00:00")
                        )
                        date_short = source_date.strftime("%Y-%m-%d")
                    except Exception:
                        pass

                # Clickable URL for human follow-through to the debate page.
                # The public UI blocks automated fetches but resolves for browsers.
                if ext_id and date_short:
                    url = (
                        f"https://hansard.parliament.uk/{house}/{date_short}"
                        f"/debates/{ext_id}/"
                    )
                else:
                    url = "https://hansard.parliament.uk/"

                # Prefer actual speech text; fall back to metadata-shaped snippet.
                snippet = ""
                for c in contributions_by_debate.get(ext_id, []):
                    text = (
                        c.get("ContributionText") or c.get("ContributionTextFull") or ""
                    ).strip()
                    if text:
                        snippet = text[:300]
                        break
                if not snippet:
                    snippet = (
                        f"UK Parliament {house} debate on "
                        f"{date_short or 'unknown date'}: {title}"
                    )

                metadata = {
                    "api_source": "UK Parliament Hansard",
                    "house": house,
                    "debate_section": debate_section,
                    "debate_ext_id": ext_id,
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
                logger.warning(f"Failed to parse Hansard debate: {e}")
                continue

        # P2: surface Contributions whose debate wasn't in the returned Debates
        # set. These carry real speech text and were previously discarded — a
        # topic-keyword query that returns 0 Debates can still return several
        # Contributions (live-verified), so the adapter yielded 0 despite having
        # genuine evidence in hand. Capped at max_results.
        returned_debate_ids = {
            d.get("DebateSectionExtId") for d in (raw_response.get("Debates") or [])
        }
        for c in raw_response.get("Contributions") or []:
            if len(evidence_list) >= self.max_results:
                break
            did = c.get("DebateSectionExtId")
            if did and did in returned_debate_ids:
                continue  # already represented by its debate above
            text = (
                c.get("ContributionText") or c.get("ContributionTextFull") or ""
            ).strip()
            if not text:
                continue
            try:
                section = c.get("DebateSection") or "Parliamentary Contribution"
                member = c.get("MemberName")
                house = c.get("House") or "Commons"
                sitting_date_str = c.get("SittingDate")

                source_date = None
                date_short = ""
                if sitting_date_str:
                    try:
                        source_date = datetime.fromisoformat(
                            sitting_date_str.replace("Z", "+00:00")
                        )
                        date_short = source_date.strftime("%Y-%m-%d")
                    except Exception:
                        pass

                if did and date_short:
                    url = (
                        f"https://hansard.parliament.uk/{house}/{date_short}"
                        f"/debates/{did}/"
                    )
                else:
                    url = "https://hansard.parliament.uk/"

                title = f"{section} — {member}" if member else section
                metadata = {
                    "api_source": "UK Parliament Hansard",
                    "house": house,
                    "member": member,
                    "debate_section": section,
                    "contribution_ext_id": c.get("ContributionExtId"),
                }
                evidence_list.append(
                    self._create_evidence_dict(
                        title=title,
                        snippet=text[:300],
                        url=url,
                        source_date=source_date,
                        metadata=metadata,
                    )
                )
            except Exception as e:
                logger.warning(f"Failed to parse Hansard contribution: {e}")
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
        """UK Legislation — temporarily disabled (SC-05).

        The National Archives are returning HTTP 437 to every request
        from both local dev IPs and Railway production IPs as of
        2026-04-24. The error body is a bespoke "Dear Customer, please
        contact Legislation@nationalarchives.gov.uk" page served via
        CloudFront — this is a deliberate IP block, not a UA or path
        issue (verified across 5 UAs and 7 endpoints, all 437).

        Returning False here prevents the adapter from being selected,
        which avoids wasting 20s per UK Law claim (2 attempts × 10s)
        on guaranteed 437 responses. The XML parsing code and custom
        _make_request override are preserved — they work fine when
        the origin is reachable.

        When access is restored, revert this method to:
            return domain == "Law" and jurisdiction in ["UK", "Global"]

        Parallel work: SC-15 tracks a fallback UK Parliament Bills API
        adapter to provide UK Law coverage independently of
        legislation.gov.uk.
        """
        return False

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


# ========== UK PARLIAMENT BILLS ADAPTER (SC-15) ==========


class UKParliamentBillsAdapter(GovernmentAPIClient):
    """
    UK Parliament Bills API Adapter (SC-15).

    Covers: Law, Politics
    Jurisdiction: UK
    Free tier: Unlimited (no API key required, no documented rate limits)
    Format: JSON

    Purpose: primary-source UK legislative coverage independent of
    legislation.gov.uk (which is currently IP-blocked for our caller —
    see SC-05). This adapter hits bills-api.parliament.uk which returns
    the Bills index with stage, dates, and Acts status. Complements
    Hansard (debate text) — together they cover the full legislative
    lifecycle for a claim.

    The public bills.parliament.uk UI 403s automated fetches but URLs
    resolve for users in browsers — same pattern as Hansard, fine for
    clickable citation.
    """

    # SC-15: bill titles are short noun phrases (usually 2-5 words).
    # The Bills API returns 0 on full-sentence claim queries but matches
    # well on focused bill-name terms. These boundary words terminate
    # the noun-phrase prefix of a typical claim.
    _BILL_QUERY_STOPWORDS = frozenset({"the", "a", "an"})
    _BILL_QUERY_BOUNDARY_WORDS = frozenset(
        {
            "is",
            "are",
            "was",
            "were",
            "be",
            "been",
            "has",
            "have",
            "had",
            "requires",
            "require",
            "required",
            "provides",
            "provide",
            "provided",
            "makes",
            "make",
            "made",
            "allows",
            "allow",
            "allowed",
            "prohibits",
            "prohibit",
            "prohibited",
            "introduces",
            "introduce",
            "introduced",
            "repeals",
            "repeal",
            "repealed",
            "amends",
            "amend",
            "amended",
            "passed",
            "passes",
            "enacts",
            "enacted",
        }
    )
    _BILL_QUERY_MAX_TOKENS = 5

    def __init__(self):
        super().__init__(
            api_name="UK Parliament Bills",
            base_url="https://bills-api.parliament.uk",
            api_key=None,
            cache_ttl=86400,  # 1 day — bill stages change during active sessions
            timeout=15,
            max_results=5,
            priority_tier=1,  # Domain specialist
            emits_structural_metadata=True,  # NF-07-v2: bill records, structural snippets
        )

    def is_relevant_for_domain(self, domain: str, jurisdiction: str) -> bool:
        """Bills API covers Law and Politics for UK."""
        return domain in ["Law", "Politics"] and jurisdiction == "UK"

    def prepare_query(
        self,
        claim_text: str,
        entities: Optional[List[Dict[str, str]]] = None,
    ) -> str:
        """B2.3: expose SC-15 bill-title trim via prepare_query.

        _extract_bill_query has SC-15-specific logic (drops 4-digit
        years because bill short titles don't contain the year as
        searchable text — "Online Safety Act 2023" → 0 hits;
        "Online Safety Act" → 9 hits). extract_topic_phrase doesn't
        have year-stripping, so we keep the adapter-local trim rather
        than promoting to the shared helper.

        Entities unused — the trim works on word position in the
        claim text (leading-stopword strip, copula-boundary stop,
        4-digit year drop). Adding an entity-priority pass would be
        possible but the trim already wins on the SC-15 verification
        cases.
        """
        del entities
        return self._extract_bill_query(claim_text)

    def _extract_bill_query(self, query: str) -> str:
        """Reduce a claim sentence to a likely bill-title noun phrase.

        The Bills API returned 0 on the full Online Safety Act claim
        sentence during SC-15 probe but matched "Online Safety" or
        "Online Safety Act" with 9 topical results. Same class of
        query-shape mismatch as GBIF pre-SC-06: full sentence -> 0;
        trimmed noun prefix -> hit.
        """
        words = query.split()
        while words and words[0].lower() in self._BILL_QUERY_STOPWORDS:
            words.pop(0)
        trimmed: List[str] = []
        for w in words:
            clean = w.lower().rstrip(".,;:!?")
            if clean in self._BILL_QUERY_BOUNDARY_WORDS:
                break
            # SC-15: 4-digit years (e.g. "2023") kill matches against the
            # Bills API because bill short titles don't contain the year
            # as searchable text. "Online Safety Act 2023" returns 0; drop
            # the year and "Online Safety Act" returns 9.
            if len(clean) == 4 and clean.isdigit():
                break
            trimmed.append(w)
            if len(trimmed) >= self._BILL_QUERY_MAX_TOKENS:
                break
        return " ".join(trimmed).strip() or query

    def search(
        self,
        query: str,
        domain: str,
        jurisdiction: str,
        entities: Optional[List[Dict[str, str]]] = None,
    ) -> List[Dict[str, Any]]:
        """Search UK Parliament Bills API for legislative items."""
        if not self.is_relevant_for_domain(domain, jurisdiction):
            return []

        query = self._sanitize_query(query)

        # Try the trimmed noun-phrase query first; fall back to the full
        # claim if trimming produced an empty result set. Same cascade
        # shape as SC-06 GBIF — covers both the "claim starts with bill
        # name" case and the "bill name is elsewhere in the sentence" case.
        trimmed = self._extract_bill_query(query)
        params = {"SearchTerm": trimmed, "Take": self.max_results}

        try:
            response = self._make_request("/api/v1/Bills", params=params)

            items = (response or {}).get("items") or []
            if not items and trimmed != query:
                # Trimmed query gave nothing; retry with the full claim.
                response = self._make_request(
                    "/api/v1/Bills",
                    params={"SearchTerm": query, "Take": self.max_results},
                )
                items = (response or {}).get("items") or []

            if not items:
                logger.info(f"UK Parliament Bills returned 0 results for: {query[:60]}")
                return []

            return self._transform_response({"items": items})

        except Exception as e:
            logger.error(f"UK Parliament Bills search failed for '{query}': {e}")
            return []

    def _transform_response(self, raw_response: Any) -> List[Dict[str, Any]]:
        """Transform Bills API response items to standardised evidence dicts."""
        evidence_list: List[Dict[str, Any]] = []

        for item in (raw_response or {}).get("items") or []:
            try:
                title = item.get("shortTitle") or "UK Parliament Bill"
                bill_id = item.get("billId")
                is_act = bool(item.get("isAct"))
                house = (
                    item.get("currentHouse")
                    or item.get("originatingHouse")
                    or "Parliament"
                )
                stage = (item.get("currentStage") or {}).get(
                    "description"
                ) or "unknown stage"

                # Parse last-update timestamp for source_date.
                source_date = None
                date_short = ""
                last_update = item.get("lastUpdate")
                if last_update:
                    try:
                        source_date = datetime.fromisoformat(
                            last_update.replace("Z", "+00:00")
                        )
                        date_short = source_date.strftime("%Y-%m-%d")
                    except Exception:
                        pass

                url = (
                    f"https://bills.parliament.uk/bills/{bill_id}"
                    if bill_id
                    else "https://bills.parliament.uk/"
                )

                # Synthesise a snippet from the metadata. The Bills API
                # does not return a summary; the structured fields we
                # have (house, stage, Act status, date) are the signal.
                status_phrase = "Act" if is_act else f"Bill, {stage}"
                snippet = (
                    f"UK Parliament {status_phrase} in {house}"
                    + (f" (last updated {date_short})." if date_short else ".")
                    + f" Title: {title}"
                )

                metadata = {
                    "api_source": "UK Parliament Bills",
                    "bill_id": bill_id,
                    "house": house,
                    "current_stage": stage,
                    "is_act": is_act,
                }

                evidence_list.append(
                    self._create_evidence_dict(
                        title=title,
                        snippet=snippet,
                        url=url,
                        source_date=source_date,
                        metadata=metadata,
                    )
                )

            except Exception as e:
                logger.warning(f"Failed to parse UK Parliament Bills item: {e}")
                continue

        logger.info(
            f"UK Parliament Bills returned {len(evidence_list)} bill references"
        )
        return evidence_list
