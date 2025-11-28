"""
Programmatic Fact-Check Parser

Parses fact-check articles from sites like Snopes and PolitiFact to extract:
- Target claim they're fact-checking
- Their verdict/rating
- Relevance to our claim

This fixes issues where fact-check meta-claims confuse the judge
(e.g., Snopes saying "fake rendering" being misinterpreted as "fake project")
"""

import logging
import re
import httpx
from typing import Dict, List, Any, Optional
from bs4 import BeautifulSoup
from app.core.config import settings

logger = logging.getLogger(__name__)


class FactCheckParser:
    """
    Main fact-check parser that detects and delegates to site-specific parsers.
    """

    def __init__(self):
        self.parsers = {
            'snopes.com': SnopesParser(),
            'politifact.com': PolitiFactParser()
        }
        self.embedding_service = None  # Lazy load

    async def parse_factcheck_evidence(
        self,
        claims: List[Dict[str, Any]],
        evidence_by_claim: Dict[str, List[Dict[str, Any]]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Parse and filter fact-check evidence based on relevance.

        Args:
            claims: List of extracted claims
            evidence_by_claim: Dict mapping claim position to evidence list

        Returns:
            Updated evidence dict with parsed fact-check metadata
        """
        if not evidence_by_claim:
            return evidence_by_claim

        updated_evidence = {}

        for claim in claims:
            position = str(claim.get("position", 0))
            evidence_list = evidence_by_claim.get(position, [])

            if not evidence_list:
                updated_evidence[position] = []
                continue

            updated_list = []
            for evidence in evidence_list:
                # Check if this is fact-check evidence
                if evidence.get('is_factcheck') or self._is_factcheck_domain(evidence.get('url', '')):
                    # Attempt to parse
                    parsed = await self._parse_and_enrich(claim, evidence)
                    updated_list.append(parsed)
                else:
                    # Regular evidence, pass through
                    updated_list.append(evidence)

            updated_evidence[position] = updated_list

        return updated_evidence

    def _is_factcheck_domain(self, url: str) -> bool:
        """Check if URL is from a fact-checking site"""
        factcheck_domains = ['snopes.com', 'politifact.com', 'factcheck.org', 'fullfact.org']
        return any(domain in url.lower() for domain in factcheck_domains)

    async def _parse_and_enrich(
        self,
        claim: Dict[str, Any],
        evidence: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Parse fact-check article and enrich evidence with metadata.

        Returns evidence dict with added fields:
        - factcheck_target_claim
        - factcheck_rating
        - factcheck_claim_similarity
        - factcheck_parse_success
        """
        url = evidence.get('url', '')
        claim_text = claim.get('text', '')

        # Detect parser
        parser = None
        for domain, domain_parser in self.parsers.items():
            if domain in url.lower():
                parser = domain_parser
                break

        if not parser:
            logger.debug(f"No parser for fact-check URL: {url}")
            evidence['factcheck_parse_success'] = False
            evidence['is_factcheck'] = True  # Mark as fact-check even if not parsed
            return evidence

        try:
            # Fetch and parse article
            parsed_data = await self._fetch_and_parse(url, parser)

            if not parsed_data or not parsed_data.get('target_claim'):
                logger.warning(f"Failed to extract target claim from {url}")
                evidence['factcheck_parse_success'] = False
                evidence['is_factcheck'] = True
                return evidence

            # Calculate similarity between our claim and their target claim
            similarity = await self._calculate_claim_similarity(
                claim_text,
                parsed_data['target_claim']
            )

            # Enrich evidence with parsed metadata
            evidence['factcheck_target_claim'] = parsed_data['target_claim']
            evidence['factcheck_rating'] = parsed_data.get('rating', 'Unknown')
            evidence['factcheck_claim_similarity'] = similarity
            evidence['factcheck_parse_success'] = True
            evidence['is_factcheck'] = True

            # Apply relevance-based filtering
            if similarity < settings.FACTCHECK_SIMILARITY_THRESHOLD:
                # Low relevance - heavily downweight
                logger.info(
                    f"Low-relevance fact-check detected (similarity={similarity:.2f}): "
                    f"Our claim: '{claim_text[:50]}...' vs "
                    f"Their claim: '{parsed_data['target_claim'][:50]}...'"
                )
                # Reduce relevance score dramatically
                evidence['relevance_score'] = evidence.get('relevance_score', 1.0) * settings.FACTCHECK_LOW_RELEVANCE_PENALTY
                evidence['factcheck_low_relevance'] = True
            else:
                logger.info(
                    f"High-relevance fact-check found (similarity={similarity:.2f})"
                )
                evidence['factcheck_low_relevance'] = False

            return evidence

        except Exception as e:
            logger.error(f"Error parsing fact-check {url}: {e}")
            evidence['factcheck_parse_success'] = False
            evidence['is_factcheck'] = True
            return evidence

    async def _fetch_and_parse(
        self,
        url: str,
        parser
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch article content and parse with site-specific parser.

        Returns dict with:
        - target_claim: The claim being fact-checked
        - rating: Their verdict
        - Additional site-specific data
        """
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                headers = {
                    'User-Agent': 'Tru8Bot/1.0 (Fact-checking service)'
                }
                response = await client.get(url, headers=headers, follow_redirects=True)
                response.raise_for_status()

                html_content = response.text
                soup = BeautifulSoup(html_content, 'html.parser')

                # Delegate to site-specific parser
                return parser.parse(soup, url)

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error fetching {url}: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error fetching/parsing {url}: {e}")
            return None

    async def _calculate_claim_similarity(
        self,
        our_claim: str,
        their_claim: str
    ) -> float:
        """
        Calculate semantic similarity between our claim and fact-check target claim.

        Uses embedding service for semantic understanding.

        Returns float 0-1 (0 = completely different, 1 = identical)
        """
        try:
            # Lazy load embedding service
            if self.embedding_service is None:
                from app.services.embeddings import get_embedding_service
                self.embedding_service = await get_embedding_service()

            # Generate embeddings
            our_embedding = await self.embedding_service.embed_text(our_claim)
            their_embedding = await self.embedding_service.embed_text(their_claim)

            # Calculate cosine similarity
            similarity = await self.embedding_service.compute_similarity(
                our_embedding,
                their_embedding
            )

            return float(similarity)

        except Exception as e:
            logger.error(f"Error calculating claim similarity: {e}")
            # Conservative fallback: assume low similarity
            return 0.5


class SnopesParser:
    """
    Parser for Snopes.com fact-check articles.

    Snopes structure:
    - Claim: <div class="claim_cont"> or meta property="og:description"
    - Rating: <div class="rating_title_wrap"> or <span class="rating">
    - What's True/False: <div class="single-body">
    """

    def parse(self, soup: BeautifulSoup, url: str) -> Optional[Dict[str, Any]]:
        """
        Extract structured data from Snopes article.

        Returns:
            {
                'target_claim': str,
                'rating': str,
                'what_is_true': str,
                'what_is_false': str
            }
        """
        try:
            # Extract claim (multiple fallback strategies)
            target_claim = self._extract_claim(soup)

            if not target_claim:
                logger.warning(f"Could not extract claim from Snopes URL: {url}")
                return None

            # Extract rating
            rating = self._extract_rating(soup)

            # Extract what's true/false context
            what_is_true = self._extract_whats_true(soup)
            what_is_false = self._extract_whats_false(soup)

            return {
                'target_claim': target_claim,
                'rating': rating or 'Unknown',
                'what_is_true': what_is_true,
                'what_is_false': what_is_false
            }

        except Exception as e:
            logger.error(f"Error parsing Snopes article: {e}")
            return None

    def _extract_claim(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract the claim being fact-checked"""
        # Strategy 1: claim_cont div
        claim_div = soup.find('div', class_='claim_cont')
        if claim_div:
            return claim_div.get_text(strip=True)

        # Strategy 2: claim-text class
        claim_text = soup.find(class_='claim-text')
        if claim_text:
            return claim_text.get_text(strip=True)

        # Strategy 3: og:description meta tag
        meta_desc = soup.find('meta', property='og:description')
        if meta_desc and meta_desc.get('content'):
            desc = meta_desc['content']
            # Snopes often includes "Claim:" prefix
            if desc.startswith('Claim:'):
                return desc.replace('Claim:', '').strip()
            return desc

        # Strategy 4: Article headline (h1)
        h1 = soup.find('h1')
        if h1:
            return h1.get_text(strip=True)

        return None

    def _extract_rating(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract Snopes rating (True, False, Mixture, etc.)"""
        # Strategy 1: rating_title_wrap
        rating_div = soup.find('div', class_='rating_title_wrap')
        if rating_div:
            return rating_div.get_text(strip=True)

        # Strategy 2: rating span
        rating_span = soup.find('span', class_='rating')
        if rating_span:
            return rating_span.get_text(strip=True)

        # Strategy 3: Look for rating image alt text
        rating_img = soup.find('img', class_='rating_img')
        if rating_img and rating_img.get('alt'):
            return rating_img['alt']

        return None

    def _extract_whats_true(self, soup: BeautifulSoup) -> str:
        """Extract 'What's True' section if present"""
        whats_true = soup.find(text=re.compile(r"What's True", re.IGNORECASE))
        if whats_true and whats_true.parent:
            # Get next paragraph
            next_elem = whats_true.parent.find_next_sibling()
            if next_elem:
                return next_elem.get_text(strip=True)
        return ""

    def _extract_whats_false(self, soup: BeautifulSoup) -> str:
        """Extract 'What's False' section if present"""
        whats_false = soup.find(text=re.compile(r"What's False", re.IGNORECASE))
        if whats_false and whats_false.parent:
            # Get next paragraph
            next_elem = whats_false.parent.find_next_sibling()
            if next_elem:
                return next_elem.get_text(strip=True)
        return ""


class PolitiFactParser:
    """
    Parser for PolitiFact.com fact-check articles.

    PolitiFact structure:
    - Claim: <div class="m-statement__quote"> or <p class="m-statement__desc">
    - Rating: <div class="m-statement__meter"> or alt text of Truth-O-Meter image
    - Summary: <div class="m-textblock">
    """

    def parse(self, soup: BeautifulSoup, url: str) -> Optional[Dict[str, Any]]:
        """
        Extract structured data from PolitiFact article.

        Returns:
            {
                'target_claim': str,
                'rating': str,  # True, Mostly True, Half True, Mostly False, False, Pants on Fire
                'summary': str
            }
        """
        try:
            # Extract claim
            target_claim = self._extract_claim(soup)

            if not target_claim:
                logger.warning(f"Could not extract claim from PolitiFact URL: {url}")
                return None

            # Extract Truth-O-Meter rating
            rating = self._extract_rating(soup)

            # Extract article summary
            summary = self._extract_summary(soup)

            return {
                'target_claim': target_claim,
                'rating': rating or 'Unknown',
                'summary': summary
            }

        except Exception as e:
            logger.error(f"Error parsing PolitiFact article: {e}")
            return None

    def _extract_claim(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract the claim being fact-checked"""
        # Strategy 1: m-statement__quote (newer layout)
        quote_div = soup.find('div', class_='m-statement__quote')
        if quote_div:
            return quote_div.get_text(strip=True).strip('"')

        # Strategy 2: m-statement__desc
        desc_div = soup.find('p', class_='m-statement__desc')
        if desc_div:
            return desc_div.get_text(strip=True)

        # Strategy 3: statement__text (older layout)
        statement_div = soup.find('div', class_='statement__text')
        if statement_div:
            return statement_div.get_text(strip=True).strip('"')

        # Strategy 4: og:description meta tag
        meta_desc = soup.find('meta', property='og:description')
        if meta_desc and meta_desc.get('content'):
            return meta_desc['content']

        return None

    def _extract_rating(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract PolitiFact Truth-O-Meter rating"""
        # Strategy 1: m-statement__meter
        meter_div = soup.find('div', class_='m-statement__meter')
        if meter_div:
            # Look for img alt text
            img = meter_div.find('img')
            if img and img.get('alt'):
                return img['alt']

        # Strategy 2: c-image__original (truth-o-meter image)
        meter_img = soup.find('img', class_='c-image__original')
        if meter_img and meter_img.get('alt'):
            alt = meter_img['alt']
            # Extract rating from alt text like "pants-fire"
            if 'pants' in alt.lower() or 'fire' in alt.lower():
                return "Pants on Fire"
            elif 'true' in alt.lower():
                return "True"
            elif 'false' in alt.lower():
                return "False"
            return alt

        # Strategy 3: Look for rating class
        rating_elem = soup.find(class_=re.compile(r'rating'))
        if rating_elem:
            return rating_elem.get_text(strip=True)

        return None

    def _extract_summary(self, soup: BeautifulSoup) -> str:
        """Extract article summary/first paragraph"""
        # Look for main content area
        textblock = soup.find('div', class_='m-textblock')
        if textblock:
            # Get first paragraph
            first_p = textblock.find('p')
            if first_p:
                return first_p.get_text(strip=True)

        # Fallback: find first substantial paragraph
        paragraphs = soup.find_all('p')
        for p in paragraphs:
            text = p.get_text(strip=True)
            if len(text) > 100:  # Substantial paragraph
                return text

        return ""


# Singleton instance
_parser = None

def get_factcheck_parser() -> FactCheckParser:
    """Get singleton parser instance"""
    global _parser
    if _parser is None:
        _parser = FactCheckParser()
    return _parser
