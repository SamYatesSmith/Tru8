"""Wikipedia Reference Mining — extract authority sources from Wikipedia bibliographies.

Wikipedia dominates many evidence searches but isn't evidence itself — it's a
community-curated index of primary sources. This module mines Wikipedia's external
links for high-authority sources (academic papers, legal instruments, statistical
datasets) that web search can't find directly.

Architecture:
  Web search returns results (some may be Wikipedia)
  → identify wikipedia.org URLs in evidence snippets
  → MediaWiki API: action=parse&prop=externallinks (single JSON call, ~200ms)
  → filter external links against AUTHORITY_DOMAINS allowlist
  → fetch matching URLs via existing _extract_from_page()
  → tag with external_source_provider="Wikipedia reference"
  → append to evidence pool BEFORE filtering cascade
"""

import asyncio
import logging
import re
from typing import TYPE_CHECKING, List
from urllib.parse import unquote, urlparse

import httpx

if TYPE_CHECKING:
    from app.services.evidence import EvidenceExtractor, EvidenceSnippet

logger = logging.getLogger(__name__)

# Maximum Wikipedia pages to mine per claim (bounds latency)
MAX_WIKI_PAGES = 2

# Maximum authority references to extract per Wikipedia page
MAX_REFS_PER_PAGE = 5

# MediaWiki API timeout
MEDIAWIKI_TIMEOUT = 5

# User-Agent per Wikipedia API etiquette
USER_AGENT = "Tru8FactChecker/1.0 (https://tru8.com; hello@trueight.com)"

# ---------------------------------------------------------------------------
# Authority domain allowlist — the ONLY references we extract.
# Everything else is ignored because web search already finds it.
# ---------------------------------------------------------------------------
AUTHORITY_DOMAINS = {
    # Academic publishers & databases
    "doi.org",
    "pubmed.ncbi.nlm.nih.gov",
    "ncbi.nlm.nih.gov",
    "arxiv.org",
    "jstor.org",
    "nature.com",
    "sciencedirect.com",
    "springer.com",
    "wiley.com",
    "tandfonline.com",
    "cambridge.org",
    "academic.oup.com",
    "pnas.org",
    "bmj.com",
    "thelancet.com",
    "nejm.org",
    "cell.com",
    "aaas.org",
    "science.org",
    # Legal (UK)
    "legislation.gov.uk",
    "judiciary.uk",
    "bailii.org",
    "parliament.uk",
    "hansard.parliament.uk",
    # Legal (US)
    "supremecourt.gov",
    "law.cornell.edu",
    "govinfo.gov",
    "congress.gov",
    "courtlistener.com",
    # Legal (International)
    "eur-lex.europa.eu",
    "echr.coe.int",
    "icj-cij.org",
    # Statistical / Data
    "ons.gov.uk",
    "data.gov.uk",
    "data.gov",
    "eurostat.ec.europa.eu",
    "worldbank.org",
    "imf.org",
    "census.gov",
    "bls.gov",
    "fred.stlouisfed.org",
    "cdc.gov",
    "who.int",
    "un.org",
    "stats.oecd.org",
}

# Pattern-based catch-alls for institutional domains
AUTHORITY_PATTERNS = [
    re.compile(r"\.edu$"),
    re.compile(r"\.ac\.uk$"),
    re.compile(r"\.edu\.au$"),
]


def _is_authority_domain(url: str) -> bool:
    """Check if a URL belongs to an authority domain."""
    try:
        domain = urlparse(url).hostname
        if not domain:
            return False
        domain = domain.lower()

        # Check exact suffix match against allowlist
        for auth_domain in AUTHORITY_DOMAINS:
            if domain == auth_domain or domain.endswith("." + auth_domain):
                return True

        # Check regex patterns (e.g. .edu, .ac.uk)
        for pattern in AUTHORITY_PATTERNS:
            if pattern.search(domain):
                return True
    except Exception:
        pass
    return False


def _extract_wiki_title(url: str) -> str | None:
    """Extract the page title from a Wikipedia URL.

    e.g. 'https://en.wikipedia.org/wiki/Russia%E2%80%93Ukraine_war' → 'Russia–Ukraine_war'
    """
    try:
        parsed = urlparse(url)
        path = parsed.path
        prefix = "/wiki/"
        idx = path.find(prefix)
        if idx == -1:
            return None
        title = path[idx + len(prefix) :]
        # Strip fragment/anchor
        if "#" in title:
            title = title.split("#")[0]
        # Decode percent-encoding
        title = unquote(title)
        return title if title else None
    except Exception:
        return None


async def _fetch_external_links(title: str) -> List[str]:
    """Fetch external links from a Wikipedia page via the MediaWiki API."""
    url = "https://en.wikipedia.org/w/api.php"
    params = {
        "action": "parse",
        "page": title,
        "prop": "externallinks",
        "format": "json",
    }
    try:
        async with httpx.AsyncClient(timeout=MEDIAWIKI_TIMEOUT) as client:
            resp = await client.get(
                url,
                params=params,
                headers={"User-Agent": USER_AGENT},
            )
            if resp.status_code != 200:
                logger.warning(
                    f"[WIKI MINING] MediaWiki API returned {resp.status_code} for '{title}'"
                )
                return []
            data = resp.json()
            links = data.get("parse", {}).get("externallinks", [])
            return links if isinstance(links, list) else []
    except httpx.TimeoutException:
        logger.warning(f"[WIKI MINING] MediaWiki API timeout for '{title}'")
        return []
    except Exception as e:
        logger.warning(f"[WIKI MINING] MediaWiki API error for '{title}': {e}")
        return []


async def mine_wikipedia_references(
    snippets: List["EvidenceSnippet"],
    claim_text: str,
    evidence_extractor: "EvidenceExtractor",
    semaphore: "asyncio.Semaphore",
) -> List["EvidenceSnippet"]:
    """Mine Wikipedia external links for authority sources.

    Scans web search results for Wikipedia URLs, fetches their external links
    via the MediaWiki API, filters against the authority domain allowlist,
    and extracts content from matching URLs.

    Args:
        snippets: Web search results (to scan for Wikipedia URLs)
        claim_text: Claim text for relevance context during extraction
        evidence_extractor: Reuse its _extract_from_page() for fetching
        semaphore: Shared concurrency limiter

    Returns:
        List of EvidenceSnippet objects tagged with external_source_provider
    """
    from app.services.search import SearchResult

    # 1. Find Wikipedia URLs in search results
    wiki_urls = []
    for snippet in snippets:
        if not snippet.url:
            continue
        if "wikipedia.org/wiki/" in snippet.url.lower():
            title = _extract_wiki_title(snippet.url)
            if title:
                wiki_urls.append((snippet.url, title))

    if not wiki_urls:
        return []

    # Cap at MAX_WIKI_PAGES to bound latency
    wiki_urls = wiki_urls[:MAX_WIKI_PAGES]
    logger.info(
        f"[WIKI MINING] Found {len(wiki_urls)} Wikipedia page(s) to mine: "
        f"{[t for _, t in wiki_urls]}"
    )

    # 2. Fetch external links from each Wikipedia page
    mined_snippets: List["EvidenceSnippet"] = []

    for wiki_url, title in wiki_urls:
        external_links = await _fetch_external_links(title)
        if not external_links:
            continue

        # 3. Filter against authority domains
        authority_links = [
            link for link in external_links if _is_authority_domain(link)
        ]

        if not authority_links:
            logger.debug(
                f"[WIKI MINING] No authority links found in '{title}' "
                f"({len(external_links)} total external links)"
            )
            continue

        # Cap per-page extractions
        authority_links = authority_links[:MAX_REFS_PER_PAGE]
        logger.info(
            f"[WIKI MINING] '{title}': {len(authority_links)} authority links "
            f"(from {len(external_links)} total)"
        )

        # 4. Extract content from each authority link
        for ref_url in authority_links:
            try:
                domain = urlparse(ref_url).hostname or ""
                search_result = SearchResult(
                    url=ref_url,
                    title="",
                    snippet="",
                    source=domain,
                )
                extracted = await evidence_extractor._extract_from_page(
                    search_result, claim_text, semaphore
                )
                if extracted is not None:
                    extracted.metadata = extracted.metadata or {}
                    extracted.metadata["external_source_provider"] = (
                        "Wikipedia reference"
                    )
                    extracted.metadata["wikipedia_source_page"] = wiki_url
                    mined_snippets.append(extracted)
            except Exception as e:
                logger.debug(f"[WIKI MINING] Failed to extract {ref_url}: {e}")

    if mined_snippets:
        logger.info(
            f"[WIKI MINING] Found {len(mined_snippets)} authority references from Wikipedia"
        )

    return mined_snippets
