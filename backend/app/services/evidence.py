import logging
import asyncio
import json
from typing import Dict, List, Any, Optional
from datetime import datetime
import re
import httpx
import trafilatura
from readability import Document
import bleach
from bs4 import BeautifulSoup
from app.services.search import SearchResult, SearchService
from app.utils.url_utils import extract_domain
from app.utils.domain_status_tracker import get_domain_tracker, DomainStatus
from app.utils.encoding import fix_mojibake
from app.core.config import settings

logger = logging.getLogger(__name__)


class EvidenceSnippet:
    """Extracted evidence snippet with metadata"""

    def __init__(
        self,
        text: str,
        source: str,
        url: str,
        title: str,
        published_date: Optional[str] = None,
        relevance_score: float = 0.0,
        metadata: Optional[Dict[str, Any]] = None,
        content_basis: str = "full",
        _full_text: Optional[str] = None,  # Transient — never persisted
    ):
        self.text = text
        self.source = source
        self.url = url
        self.title = title
        self.published_date = published_date
        self.relevance_score = relevance_score
        self.word_count = len(text.split())
        self.metadata = metadata or {}  # Store page numbers, context
        self.content_basis = content_basis
        self._full_text = _full_text

    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "source": self.source,
            "url": self.url,
            "title": self.title,
            "published_date": self.published_date,
            "relevance_score": self.relevance_score,
            "word_count": self.word_count,
            "metadata": self.metadata,
            "content_basis": self.content_basis,
        }


class EvidenceExtractor:
    """Extract relevant evidence snippets from web pages"""

    # META-SOURCE DOMAINS: Sites about fact-checking methodology, tools, or aggregators
    # These NEVER contain evidence about specific claims - only about fact-checking itself
    META_SOURCE_DOMAINS = {
        # Fact-checking tool directories and guides
        "libguides.com",  # Library research guides (e.g., "Web Sites for Fact Checking")
        "library.ucdavis.edu",  # Library guides about fact-checking
        "guides.library.cornell.edu",  # Cornell fact-checking guides
        # News aggregators (index pages, not actual news)
        "newsnow.com",  # News aggregator index
        "newsnow.co.uk",  # UK version
        # Academic meta-research about misinformation (not evidence)
        "misinforeview.hks.harvard.edu",  # HKS Misinformation Review (research ABOUT fact-checking)
        # Tool/methodology pages
        "toolbox.google.com",  # Google Fact Check Tools Explorer
        "reporterslab.org",  # Duke Reporters' Lab (fact-checker directory)
    }

    # Title patterns that indicate meta-sources (case-insensitive)
    META_SOURCE_TITLE_PATTERNS = [
        r"web\s*sites?\s*for\s*fact\s*check",  # "Web Sites for Fact Checking"
        r"fact[- ]?check(ing)?\s*tools?",  # "Fact Checking Tools", "Fact-Check Tools"
        r"how\s+to\s+fact[- ]?check",  # "How to Fact Check"
        r"guide\s+to\s+fact[- ]?check",  # "Guide to Fact Checking"
        r"fact[- ]?check(ing)?\s+resources?",  # "Fact Checking Resources"
        r'"fact[- ]?check(ing)?"\s+fact[- ]?check',  # Meta: fact-checking fact-checkers
        r"misinformation.*review",  # Academic journals about misinformation
    ]

    # SC-11: Authoritative canonical-source TLDs that bypass the runtime blocklist.
    # The tracker (domain_status_tracker.py) is "one-time collection" with no TTL,
    # so a single stray 403 permanently excludes the domain. That has silently
    # blocklisted primary-tier public sources (bls.gov, congress.gov, sec.gov,
    # pmc.ncbi.nlm.nih.gov, law.stanford.edu, imperial.ac.uk, etc.). These TLDs
    # represent canonical government + academic sources where a stale 403 must
    # not override the platform's "no hidden curation" invariant.
    AUTHORITATIVE_TLDS = (
        ".gov",  # US federal + any *.gov (bls.gov, sec.gov, congress.gov, nih.gov)
        ".gov.uk",  # UK government (local.gov.uk, data.gov.uk)
        ".gov.au",  # Australian government
        ".gov.ca",  # Canadian government
        ".edu",  # US academic (law.stanford.edu, mitpress.mit.edu)
        ".ac.uk",  # UK academic (imperial.ac.uk, lshtm.ac.uk)
        ".int",  # International organisations (who.int, un.int)
        ".mil",  # Military public information
    )

    def __init__(self):
        self.search_service = SearchService()
        self.timeout = getattr(settings, "URL_FETCH_TIMEOUT", 8)
        self.max_snippet_words = 200
        self.max_concurrent = 3

        # Blocked domains - now dynamically populated from tracker
        self._init_blocked_domains()

        # Compile meta-source title patterns for efficiency
        self._meta_title_patterns = [
            re.compile(pattern, re.IGNORECASE)
            for pattern in self.META_SOURCE_TITLE_PATTERNS
        ]

        # Common fact-checking terms to look for
        self.fact_indicators = [
            "according to",
            "study shows",
            "research indicates",
            "data reveals",
            "statistics show",
            "report states",
            "findings suggest",
            "analysis shows",
            "evidence indicates",
            "survey found",
            "poll shows",
            "investigation revealed",
        ]

    def _is_meta_source(self, url: str, title: str = "") -> bool:
        """Check if a source is a meta-source (about fact-checking, not evidence).

        Args:
            url: The URL of the source
            title: The title of the source (optional)

        Returns:
            True if this is a meta-source that should be filtered out
        """
        # Check domain
        domain = extract_domain(url, fallback="").lower()
        for meta_domain in self.META_SOURCE_DOMAINS:
            if meta_domain in domain:
                logger.debug(f"[META-SOURCE] Filtered by domain: {domain}")
                return True

        # Check title patterns
        if title:
            for pattern in self._meta_title_patterns:
                if pattern.search(title):
                    logger.debug(
                        f"[META-SOURCE] Filtered by title pattern: {title[:50]}..."
                    )
                    return True

        return False

    def _is_authoritative_tld(self, domain: str) -> bool:
        """SC-11: True if domain ends with an AUTHORITATIVE_TLDS entry.

        Such domains bypass the runtime blocklist — a stale 403 from two months
        ago must not permanently exclude canonical government + academic sources.
        """
        if not domain:
            return False
        d = domain.lower().strip()
        if d.startswith("www."):
            d = d[4:]
        return any(d.endswith(tld) for tld in self.AUTHORITATIVE_TLDS)

    def _init_blocked_domains(self) -> None:
        """Initialize blocked domains from tracker.

        Blocks BOT_BLOCKED (403) and TIMEOUT domains — both consistently
        return no usable content and waste fetch time.  Rate-limited (429),
        paywall, and JS-required are NOT blocked — they may succeed on retry
        or return partial content.
        """
        try:
            tracker = get_domain_tracker()
            bot_blocked = tracker.get_domains_by_status(DomainStatus.BOT_BLOCKED)
            timed_out = tracker.get_domains_by_status(DomainStatus.TIMEOUT)

            self.blocked_domains = set()
            for d in (*bot_blocked, *timed_out):
                domain = d.get("domain", "")
                self.blocked_domains.add(domain)
                self.blocked_domains.add(f"www.{domain}")

            logger.info(
                f"[EVIDENCE] Loaded {len(self.blocked_domains)} blocked domains "
                f"({len(bot_blocked)} bot-blocked, {len(timed_out)} timeout)"
            )
        except Exception as e:
            logger.warning(f"[EVIDENCE] Failed to load blocked domains: {e}")
            # Fallback to hardcoded list
            self.blocked_domains = {"yahoo.com", "www.yahoo.com"}

    async def extract_evidence_for_claim(
        self,
        claim: str,
        max_sources: int = 5,
        subject_context: str = None,
        key_entities: list = None,
        excluded_domain: Optional[str] = None,
        temporal_analysis: Dict = None,
        article_title: Optional[str] = None,
        article_date: Optional[str] = None,
        url_fetch_semaphore: Optional[asyncio.Semaphore] = None,
        search_country: Optional[str] = None,
    ) -> List[EvidenceSnippet]:
        """
        Extract evidence snippets for a specific claim.

        Args:
            claim: The claim text to verify
            max_sources: Maximum number of evidence sources
            subject_context: Main subject/topic for context-aware search
            key_entities: Key entities to boost in search query
            excluded_domain: Domain to exclude from search results (for self-citation filtering)
            temporal_analysis: Temporal analysis from claim extraction (for query refinement)
            article_title: Title of source article (for context grounding)
            article_date: Publication date of source article (for temporal context)
            url_fetch_semaphore: Shared semaphore for cross-claim URL fetch concurrency control
        """
        try:
            # Step 1: Build context-enriched search query
            # TIER 1 IMPROVEMENT: Enhanced query formulation
            from app.core.config import settings

            search_query = claim
            logger.info(f"Search query: '{search_query[:80]}...'")
            if subject_context and key_entities:
                # Only add entities that AREN'T already in the claim text (avoid duplication)
                unique_entities = [
                    e for e in key_entities[:3] if e.lower() not in claim.lower()
                ]
                if unique_entities:
                    entities_str = " ".join(
                        unique_entities[:2]
                    )  # Max 2 additional entities
                    search_query = f"{claim} {entities_str}"
                    logger.info(
                        f"Context-enriched search with {len(unique_entities)} unique entities: '{search_query}'"
                    )

            # Step 2: Search for relevant pages
            search_kwargs = {"max_results": max_sources * 2}
            if search_country is not None:
                search_kwargs["country"] = search_country
            search_results = await self.search_service.search_for_evidence(
                search_query, **search_kwargs
            )

            # DIAGNOSTIC: Log search results
            logger.info(
                f"🔍 SEARCH RESULTS | Found: {len(search_results)} results | Requested: {max_sources * 2}"
            )

            # Filter out excluded domain (self-citation prevention)
            if excluded_domain:
                original_count = len(search_results)
                search_results = [
                    result
                    for result in search_results
                    if extract_domain(result.url) != excluded_domain
                ]
                filtered_count = original_count - len(search_results)
                if filtered_count > 0:
                    logger.info(
                        f"Excluded {filtered_count} search results from source domain: {excluded_domain}"
                    )

            # Filter out meta-sources (fact-checking guides, aggregators, methodology pages)
            original_count = len(search_results)
            search_results = [
                result
                for result in search_results
                if not self._is_meta_source(result.url, result.title)
            ]
            meta_filtered = original_count - len(search_results)
            if meta_filtered > 0:
                logger.info(
                    f"[META-SOURCE] Filtered {meta_filtered} meta-sources from search results"
                )

            if not search_results:
                logger.warning(f"No search results for claim: {claim[:50]}...")
                return []

            # Step 2: Extract content from top results (with concurrency limit)
            # Use shared pool if provided (work-stealing across claims),
            # otherwise fall back to per-claim pool for standalone use.
            semaphore = url_fetch_semaphore or asyncio.Semaphore(self.max_concurrent)
            tasks = [
                self._extract_from_page(result, claim, semaphore)
                for result in search_results[
                    : max_sources * 2
                ]  # Get extra in case some fail
            ]

            extracted_results = await asyncio.gather(*tasks, return_exceptions=True)

            # Step 3: Filter successful extractions and rank by relevance
            evidence_snippets = []
            failed_count = 0
            for result in extracted_results:
                if isinstance(result, EvidenceSnippet):
                    evidence_snippets.append(result)
                elif isinstance(result, Exception):
                    failed_count += 1
                    logger.warning(f"Evidence extraction failed: {result}")

            # DIAGNOSTIC: Log extraction success rate
            total_attempts = len(extracted_results)
            success_rate = (
                (len(evidence_snippets) / total_attempts * 100)
                if total_attempts > 0
                else 0
            )
            logger.info(
                f"📄 EXTRACTION | Success: {len(evidence_snippets)}/{total_attempts} ({success_rate:.1f}%) | Failed: {failed_count}"
            )

            # Step 4: Rank by relevance and return top results
            ranked_snippets = self._rank_snippets(evidence_snippets, claim)
            logger.info(
                f"🎯 FINAL EVIDENCE | Returning: {len(ranked_snippets[:max_sources])} snippets (requested: {max_sources})"
            )
            return ranked_snippets[:max_sources]

        except Exception as e:
            import traceback

            logger.error(
                f"[EVIDENCE DEBUG] Evidence extraction EXCEPTION: {type(e).__name__}: {e}"
            )
            logger.error(f"[EVIDENCE DEBUG] Full traceback:\n{traceback.format_exc()}")
            return []

    async def _extract_from_page(
        self, search_result: SearchResult, claim: str, semaphore: asyncio.Semaphore
    ) -> Optional[EvidenceSnippet]:
        """Extract relevant content from a single page (enhanced for PDFs)"""
        async with semaphore:
            try:
                # Check if URL is a PDF
                if search_result.url.lower().endswith(".pdf"):
                    from app.services.pdf_evidence import get_pdf_extractor

                    pdf_extractor = get_pdf_extractor()

                    # Extract PDF evidence with page numbers
                    pdf_matches = await pdf_extractor.extract_evidence_from_pdf(
                        search_result.url, claim, max_results=1  # Best match only
                    )

                    if pdf_matches:
                        best_match = pdf_matches[0]
                        return EvidenceSnippet(
                            text=best_match["text"],
                            source=search_result.source,
                            url=search_result.url,
                            title=f"{search_result.title} (p. {best_match['page_number']})",
                            published_date=search_result.published_date,
                            relevance_score=best_match["relevance_score"],
                            metadata={
                                "page_number": best_match["page_number"],
                                "context_before": best_match.get("context_before"),
                                "context_after": best_match.get("context_after"),
                            },
                            content_basis="pdf",
                        )
                    else:
                        logger.warning(
                            f"No relevant content found in PDF: {search_result.url}"
                        )
                        return None

                # Non-PDF extraction (HTML pages)
                # Block domains with rate limiting issues
                domain = extract_domain(search_result.url, fallback="unknown")

                if any(blocked in domain.lower() for blocked in self.blocked_domains):
                    if self._is_authoritative_tld(domain):
                        logger.info(
                            f"[ALLOWLIST BYPASS] {domain} — authoritative TLD "
                            f"overrides stale runtime blocklist (SC-11)"
                        )
                    else:
                        logger.info(f"⛔ Skipping blocked domain: {domain}")
                        return None

                async with httpx.AsyncClient(
                    timeout=self.timeout, follow_redirects=True
                ) as client:
                    response = await client.get(search_result.url)
                    response.raise_for_status()

                    if response.status_code != 200:
                        return None

                    # Extract main content
                    content = self._extract_main_content(
                        response.text, search_result.url
                    )
                    domain = extract_domain(search_result.url, fallback="unknown")

                    _fell_back_to_snippet = False
                    if not content:
                        # Track as JS-required (page loaded but no content extracted)
                        try:
                            get_domain_tracker().record_access_result(
                                domain,
                                DomainStatus.JS_REQUIRED,
                                {"reason": "empty_extraction"},
                            )
                        except Exception:
                            pass
                        # Fallback to search snippet if extraction fails
                        content = search_result.snippet
                        _fell_back_to_snippet = True
                    else:
                        # Track successful extraction
                        try:
                            get_domain_tracker().record_access_result(
                                domain, DomainStatus.ACCESSIBLE
                            )
                        except Exception:
                            pass

                    # Find most relevant snippet (now async for semantic extraction)
                    snippet_text = await self._find_relevant_snippet(content, claim)

                    if not snippet_text:
                        return None

                    # Calculate relevance score
                    relevance_score = self._calculate_relevance(snippet_text, claim)

                    # Extract date from HTML if not provided by search API
                    published_date = search_result.published_date
                    if not published_date:
                        published_date = self._extract_date_from_html(response.text)
                        if published_date:
                            logger.debug(
                                f"Extracted date from HTML: {published_date} for {search_result.url}"
                            )

                    return EvidenceSnippet(
                        text=snippet_text,
                        source=search_result.source,
                        url=search_result.url,
                        title=search_result.title,
                        published_date=published_date,
                        relevance_score=relevance_score,
                        content_basis="snippet" if _fell_back_to_snippet else "full",
                        _full_text=content if not _fell_back_to_snippet else None,
                    )

            except httpx.TimeoutException:
                logger.warning(f"Timeout fetching evidence from: {search_result.url}")
                # Track domain status (one-time collection)
                try:
                    domain = extract_domain(search_result.url, fallback="unknown")
                    get_domain_tracker().record_access_result(
                        domain, DomainStatus.TIMEOUT
                    )
                except Exception:
                    pass  # Don't let tracking affect pipeline
                return None
            except httpx.HTTPStatusError as e:
                domain = extract_domain(search_result.url, fallback="unknown")
                status_code = e.response.status_code

                # Track domain status (one-time collection)
                try:
                    if status_code == 403:
                        get_domain_tracker().record_access_result(
                            domain, DomainStatus.BOT_BLOCKED, {"status_code": 403}
                        )
                    elif status_code == 429:
                        get_domain_tracker().record_access_result(
                            domain, DomainStatus.RATE_LIMITED, {"status_code": 429}
                        )
                    elif status_code == 402:
                        get_domain_tracker().record_access_result(
                            domain, DomainStatus.PAYWALL, {"status_code": 402}
                        )
                except Exception:
                    pass  # Don't let tracking affect pipeline

                if status_code == 403 or status_code == 429:
                    logger.warning(f"Access denied to: {search_result.url}")
                    # Return search snippet as fallback
                    return EvidenceSnippet(
                        text=search_result.snippet,
                        source=search_result.source,
                        url=search_result.url,
                        title=search_result.title,
                        published_date=search_result.published_date,
                        relevance_score=0.5,  # Lower score for fallback
                        content_basis="snippet",
                    )
                return None
            except Exception as e:
                logger.warning(f"Error extracting from {search_result.url}: {e}")
                return None

    def _extract_main_content(self, html: str, url: str) -> Optional[str]:
        """Extract main content from HTML"""
        try:
            # Try trafilatura first (better for news articles)
            extracted = trafilatura.extract(
                html,
                include_comments=False,
                include_tables=True,
                with_metadata=False,
                url=url,
            )

            if extracted and len(extracted.strip()) > 100:
                return self._sanitize_content(extracted)

            # Fallback to readability
            doc = Document(html)
            content = doc.summary()

            if content and len(content.strip()) > 100:
                # Extract text from HTML
                clean_content = bleach.clean(content, tags=[], strip=True)
                return self._sanitize_content(clean_content)

            return None

        except Exception as e:
            logger.warning(f"Content extraction error: {e}")
            return None

    def _sanitize_content(self, content: str) -> str:
        """Clean and sanitize extracted content"""
        # Fix mojibake from double-encoded UTF-8 (Latin-1 decoded UTF-8 bytes)
        content = fix_mojibake(content)

        # Remove excessive whitespace
        content = re.sub(r"\s+", " ", content).strip()

        # Remove common navigation/footer text
        noise_patterns = [
            r"Cookie Policy.*?$",
            r"Privacy Policy.*?$",
            r"Terms of Service.*?$",
            r"Subscribe to.*?$",
            r"Follow us on.*?$",
            r"Share this article.*?$",
            r"Related articles.*?$",
        ]

        for pattern in noise_patterns:
            content = re.sub(pattern, "", content, flags=re.IGNORECASE)

        return content.strip()

    def _extract_date_from_html(self, html: str) -> Optional[str]:
        """
        Extract publication date from HTML content.

        Checks multiple sources in order of reliability:
        1. JSON-LD structured data (most reliable)
        2. Open Graph meta tags (article:published_time)
        3. Standard meta tags (date, article:published)
        4. Time elements with datetime attribute

        Returns:
            ISO format date string (YYYY-MM-DD) or None if not found
        """
        try:
            soup = BeautifulSoup(html, "html.parser")

            # 1. Try JSON-LD structured data (most reliable)
            for script in soup.find_all("script", type="application/ld+json"):
                try:
                    data = json.loads(script.string or "")
                    # Handle both single objects and arrays
                    items = data if isinstance(data, list) else [data]
                    for item in items:
                        if isinstance(item, dict):
                            # Check for datePublished in various schema types
                            date_published = item.get("datePublished") or item.get(
                                "dateCreated"
                            )
                            if date_published:
                                return self._normalize_date(date_published)
                            # Check @graph array (common in WordPress sites)
                            if "@graph" in item:
                                for graph_item in item["@graph"]:
                                    if isinstance(graph_item, dict):
                                        date_published = graph_item.get(
                                            "datePublished"
                                        ) or graph_item.get("dateCreated")
                                        if date_published:
                                            return self._normalize_date(date_published)
                except (json.JSONDecodeError, TypeError):
                    continue

            # 2. Try Open Graph meta tags
            og_tags = [
                ("property", "article:published_time"),
                ("property", "og:article:published_time"),
                ("property", "article:published"),
            ]
            for attr, value in og_tags:
                meta = soup.find("meta", {attr: value})
                if meta and meta.get("content"):
                    return self._normalize_date(meta["content"])

            # 3. Try standard meta tags
            meta_names = [
                "date",
                "article:published",
                "pubdate",
                "publishdate",
                "publish_date",
                "DC.date.issued",
                "dcterms.date",
            ]
            for name in meta_names:
                meta = soup.find("meta", {"name": name})
                if meta and meta.get("content"):
                    return self._normalize_date(meta["content"])

            # 4. Try time elements with datetime
            time_elem = soup.find("time", datetime=True)
            if time_elem and time_elem.get("datetime"):
                return self._normalize_date(time_elem["datetime"])

            return None

        except Exception as e:
            logger.debug(f"Date extraction error: {e}")
            return None

    def _normalize_date(self, date_str: str) -> Optional[str]:
        """Normalize date string to ISO format (YYYY-MM-DD)"""
        if not date_str:
            return None

        try:
            # Handle ISO format with time (2024-01-15T10:30:00Z)
            if "T" in date_str:
                date_str = date_str.split("T")[0]

            # Handle ISO format with timezone offset
            if "+" in date_str and "T" not in date_str:
                date_str = date_str.split("+")[0]

            # Validate it looks like a date
            if re.match(r"^\d{4}-\d{2}-\d{2}", date_str):
                return date_str[:10]  # Return YYYY-MM-DD portion

            # Try parsing various formats
            formats = [
                "%Y-%m-%d",
                "%Y/%m/%d",
                "%d-%m-%Y",
                "%d/%m/%Y",
                "%B %d, %Y",
                "%b %d, %Y",
            ]
            for fmt in formats:
                try:
                    parsed = datetime.strptime(date_str.strip(), fmt)
                    return parsed.strftime("%Y-%m-%d")
                except ValueError:
                    continue

            return None
        except Exception:
            return None

    async def _find_relevant_snippet(self, content: str, claim: str) -> Optional[str]:
        """
        Find the most relevant snippet from content for the claim.

        TIER 1 IMPROVEMENT: Uses semantic similarity (embeddings) when enabled,
        falls back to word overlap for backward compatibility.
        """
        from app.core.config import settings

        if not content or len(content) < 50:
            return None

        # Split into sentences
        sentences = [s.strip() for s in re.split(r"[.!?]+", content) if s.strip()]

        if not sentences:
            return None

        # TIER 1 IMPROVEMENT: Semantic snippet extraction (if enabled)
        if settings.ENABLE_SEMANTIC_SNIPPET_EXTRACTION:
            try:
                return await self._extract_semantic_snippet(claim, sentences)
            except Exception as e:
                logger.error(
                    f"Semantic snippet extraction failed: {e}, falling back to word overlap"
                )
                # Fall through to existing logic

        # FALLBACK: Existing word overlap logic (preserved for backward compatibility)
        scored_sentences = []
        claim_words = set(claim.lower().split())

        for sentence in sentences:
            if len(sentence) < 20:  # Skip very short sentences
                continue

            sentence_words = set(sentence.lower().split())

            # Calculate word overlap
            word_overlap = len(claim_words & sentence_words) / len(claim_words)

            # Bonus for fact-indicating phrases
            fact_bonus = (
                sum(
                    1
                    for indicator in self.fact_indicators
                    if indicator in sentence.lower()
                )
                * 0.2
            )

            # Bonus for numbers/dates (often important for facts)
            number_bonus = len(re.findall(r"\d+", sentence)) * 0.1

            total_score = word_overlap + fact_bonus + number_bonus
            scored_sentences.append((sentence, total_score))

        if not scored_sentences:
            # Fallback: return first substantial paragraph
            paragraphs = [
                p.strip() for p in content.split("\n\n") if len(p.strip()) > 100
            ]
            if paragraphs:
                return paragraphs[0][: self.max_snippet_words * 6]  # Rough word limit
            return None

        # Sort by score and build snippet from top sentences
        scored_sentences.sort(key=lambda x: x[1], reverse=True)

        # Take top 2-3 sentences up to word limit
        snippet_sentences = []
        total_words = 0

        for sentence, score in scored_sentences[:3]:
            words = sentence.split()
            if total_words + len(words) <= self.max_snippet_words:
                snippet_sentences.append(sentence)
                total_words += len(words)
            else:
                break

        if snippet_sentences:
            return ". ".join(snippet_sentences) + "."
        else:
            # Return the best sentence even if it's long
            return scored_sentences[0][0][: self.max_snippet_words * 6]

    async def _extract_semantic_snippet(
        self, claim: str, sentences: List[str]
    ) -> Optional[str]:
        """
        Extract snippet using semantic similarity with embeddings.

        TIER 1 IMPROVEMENT: Better than word overlap for:
        - Paraphrasing ("car" vs "vehicle")
        - Synonyms ("study found" vs "research shows")
        - Technical/scientific terminology
        """
        from app.services.embeddings import get_embedding_service
        from app.core.config import settings

        # Filter very short sentences
        valid_sentences = [
            (i, sent) for i, sent in enumerate(sentences) if len(sent) > 20
        ]
        if not valid_sentences:
            return None

        # Generate embeddings for claim and all sentences
        embedding_service = await get_embedding_service()
        claim_embedding = await embedding_service.embed_text(claim)

        sentence_texts = [sent for _, sent in valid_sentences]
        sentence_embeddings = await embedding_service.embed_batch(sentence_texts)

        # Calculate semantic similarity for each sentence
        similarities = []
        for i, (orig_idx, sent_text) in enumerate(valid_sentences):
            similarity = await embedding_service.compute_similarity(
                claim_embedding, sentence_embeddings[i]
            )
            similarities.append((orig_idx, sent_text, similarity))

        # Sort by similarity
        similarities.sort(key=lambda x: x[2], reverse=True)

        # Filter by threshold
        threshold = settings.SNIPPET_SEMANTIC_THRESHOLD
        relevant_sentences = [
            (idx, text, sim) for idx, text, sim in similarities if sim >= threshold
        ]

        if not relevant_sentences:
            # No sentences meet threshold - return best match anyway
            best_match = similarities[0]
            logger.debug(
                f"No sentences above threshold {threshold}, using best: {best_match[2]:.2f}"
            )
            return best_match[1][: self.max_snippet_words * 6]

        # Build snippet from top sentences WITH CONTEXT
        # Include N sentences before/after for coherence (using only valid sentences)
        context_window = settings.SNIPPET_CONTEXT_SENTENCES
        best_orig_idx = relevant_sentences[0][0]  # Original index of best sentence

        # Find position in valid_sentences list
        valid_idx = next(
            i
            for i, (orig_idx, _) in enumerate(valid_sentences)
            if orig_idx == best_orig_idx
        )

        # Build context from valid_sentences only (excludes short sentences)
        start_idx = max(0, valid_idx - context_window)
        end_idx = min(len(valid_sentences), valid_idx + context_window + 1)

        snippet_sentences = [sent for _, sent in valid_sentences[start_idx:end_idx]]
        snippet = ". ".join(snippet_sentences).strip()

        # Enforce max length
        if len(snippet.split()) > self.max_snippet_words:
            words = snippet.split()
            snippet = " ".join(words[: self.max_snippet_words]) + "..."

        logger.debug(f"Semantic snippet similarity: {relevant_sentences[0][2]:.2f}")
        return snippet

    def _calculate_relevance(self, snippet: str, claim: str) -> float:
        """Calculate relevance score between snippet and claim"""
        try:
            snippet_words = set(snippet.lower().split())
            claim_words = set(claim.lower().split())

            # Word overlap
            overlap = len(claim_words & snippet_words) / len(
                claim_words | snippet_words
            )

            # Boost for fact-indicating language
            fact_boost = (
                sum(
                    1
                    for indicator in self.fact_indicators
                    if indicator in snippet.lower()
                )
                * 0.1
            )

            # Boost for specific numbers/dates
            number_boost = len(re.findall(r"\b\d+(?:\.\d+)?%?\b", snippet)) * 0.05

            # Length penalty for very short snippets
            length_penalty = 0 if len(snippet.split()) > 20 else -0.2

            score = min(1.0, overlap + fact_boost + number_boost + length_penalty)
            return max(0.0, score)

        except Exception as e:
            logger.warning(f"Relevance calculation error: {e}")
            return 0.5  # Default moderate relevance

    def _rank_snippets(
        self, snippets: List[EvidenceSnippet], claim: str
    ) -> List[EvidenceSnippet]:
        """
        Rank evidence snippets by relevance and credibility.

        """

        def scoring_function(snippet: EvidenceSnippet) -> float:
            # Base relevance score
            score = snippet.relevance_score

            # EXISTING: Length boost for substantial snippets
            if snippet.word_count > 50:
                score += 0.1

            return score

        # Sort by combined score
        return sorted(snippets, key=scoring_function, reverse=True)
