import logging
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime
import re
import httpx
import trafilatura
from readability import Document
import bleach
from app.services.search import SearchResult, SearchService

logger = logging.getLogger(__name__)

class EvidenceSnippet:
    """Extracted evidence snippet with metadata"""

    def __init__(self, text: str, source: str, url: str, title: str,
                 published_date: Optional[str] = None, relevance_score: float = 0.0,
                 metadata: Optional[Dict[str, Any]] = None):
        self.text = text
        self.source = source
        self.url = url
        self.title = title
        self.published_date = published_date
        self.relevance_score = relevance_score
        self.word_count = len(text.split())
        self.metadata = metadata or {}  # Store page numbers, context

    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "source": self.source,
            "url": self.url,
            "title": self.title,
            "published_date": self.published_date,
            "relevance_score": self.relevance_score,
            "word_count": self.word_count,
            "metadata": self.metadata
        }

class EvidenceExtractor:
    """Extract relevant evidence snippets from web pages"""
    
    def __init__(self):
        self.search_service = SearchService()
        self.timeout = 15
        self.max_snippet_words = 200
        self.max_concurrent = 3
        
        # Common fact-checking terms to look for
        self.fact_indicators = [
            'according to', 'study shows', 'research indicates', 'data reveals',
            'statistics show', 'report states', 'findings suggest', 'analysis shows',
            'evidence indicates', 'survey found', 'poll shows', 'investigation revealed'
        ]
    
    async def extract_evidence_for_claim(
        self,
        claim: str,
        max_sources: int = 5,
        subject_context: str = None,
        key_entities: list = None,
        excluded_domain: Optional[str] = None
    ) -> List[EvidenceSnippet]:
        """
        Extract evidence snippets for a specific claim.

        Args:
            claim: The claim text to verify
            max_sources: Maximum number of evidence sources
            subject_context: Main subject/topic for context-aware search
            key_entities: Key entities to boost in search query
            excluded_domain: Domain to exclude from search results (for self-citation filtering)
        """
        try:
            # Step 1: Build context-enriched search query
            search_query = claim
            if subject_context and key_entities:
                # Boost query with key entities for disambiguation
                entities_str = " ".join(key_entities[:3])  # Top 3 entities
                search_query = f"{claim} {entities_str}"
                logger.info(f"Context-enriched search: '{search_query}'")

            # Step 2: Search for relevant pages
            search_results = await self.search_service.search_for_evidence(search_query, max_results=max_sources * 2)

            # Filter out excluded domain (self-citation prevention)
            if excluded_domain:
                original_count = len(search_results)
                search_results = [
                    result for result in search_results
                    if self._extract_domain(result.url) != excluded_domain
                ]
                filtered_count = original_count - len(search_results)
                if filtered_count > 0:
                    logger.info(f"Excluded {filtered_count} search results from source domain: {excluded_domain}")

            if not search_results:
                logger.warning(f"No search results for claim: {claim[:50]}...")
                return []
            
            # Step 2: Extract content from top results (with concurrency limit)
            semaphore = asyncio.Semaphore(self.max_concurrent)
            tasks = [
                self._extract_from_page(result, claim, semaphore)
                for result in search_results[:max_sources * 2]  # Get extra in case some fail
            ]
            
            extracted_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Step 3: Filter successful extractions and rank by relevance
            evidence_snippets = []
            for result in extracted_results:
                if isinstance(result, EvidenceSnippet):
                    evidence_snippets.append(result)
                elif isinstance(result, Exception):
                    logger.warning(f"Evidence extraction failed: {result}")
            
            # Step 4: Rank by relevance and return top results
            ranked_snippets = self._rank_snippets(evidence_snippets, claim)
            return ranked_snippets[:max_sources]
            
        except Exception as e:
            logger.error(f"Evidence extraction error for claim: {e}")
            return []
    
    async def _extract_from_page(self, search_result: SearchResult, claim: str,
                                semaphore: asyncio.Semaphore) -> Optional[EvidenceSnippet]:
        """Extract relevant content from a single page (enhanced for PDFs)"""
        async with semaphore:
            try:
                # Check if URL is a PDF
                if search_result.url.lower().endswith('.pdf'):
                    from app.services.pdf_evidence import get_pdf_extractor
                    pdf_extractor = get_pdf_extractor()

                    # Extract PDF evidence with page numbers
                    pdf_matches = await pdf_extractor.extract_evidence_from_pdf(
                        search_result.url,
                        claim,
                        max_results=1  # Best match only
                    )

                    if pdf_matches:
                        best_match = pdf_matches[0]
                        return EvidenceSnippet(
                            text=best_match['text'],
                            source=search_result.source,
                            url=search_result.url,
                            title=f"{search_result.title} (p. {best_match['page_number']})",
                            published_date=search_result.published_date,
                            relevance_score=best_match['relevance_score'],
                            metadata={
                                'page_number': best_match['page_number'],
                                'context_before': best_match.get('context_before'),
                                'context_after': best_match.get('context_after')
                            }
                        )
                    else:
                        logger.warning(f"No relevant content found in PDF: {search_result.url}")
                        return None

                # Non-PDF extraction (HTML pages)
                async with httpx.AsyncClient(
                    timeout=self.timeout,
                    follow_redirects=True
                ) as client:
                    response = await client.get(search_result.url)
                    response.raise_for_status()

                    if response.status_code != 200:
                        return None

                    # Extract main content
                    content = self._extract_main_content(response.text, search_result.url)

                    if not content:
                        # Fallback to search snippet if extraction fails
                        content = search_result.snippet

                    # Find most relevant snippet
                    snippet_text = self._find_relevant_snippet(content, claim)

                    if not snippet_text:
                        return None

                    # Calculate relevance score
                    relevance_score = self._calculate_relevance(snippet_text, claim)

                    return EvidenceSnippet(
                        text=snippet_text,
                        source=search_result.source,
                        url=search_result.url,
                        title=search_result.title,
                        published_date=search_result.published_date,
                        relevance_score=relevance_score
                    )
                    
            except httpx.TimeoutException:
                logger.warning(f"Timeout fetching evidence from: {search_result.url}")
                return None
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 403 or e.response.status_code == 429:
                    logger.warning(f"Access denied to: {search_result.url}")
                    # Return search snippet as fallback
                    return EvidenceSnippet(
                        text=search_result.snippet,
                        source=search_result.source,
                        url=search_result.url,
                        title=search_result.title,
                        published_date=search_result.published_date,
                        relevance_score=0.5  # Lower score for fallback
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
                url=url
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
        # Remove excessive whitespace
        content = re.sub(r'\s+', ' ', content).strip()
        
        # Remove common navigation/footer text
        noise_patterns = [
            r'Cookie Policy.*?$',
            r'Privacy Policy.*?$',
            r'Terms of Service.*?$',
            r'Subscribe to.*?$',
            r'Follow us on.*?$',
            r'Share this article.*?$',
            r'Related articles.*?$'
        ]
        
        for pattern in noise_patterns:
            content = re.sub(pattern, '', content, flags=re.IGNORECASE)
        
        return content.strip()
    
    def _find_relevant_snippet(self, content: str, claim: str) -> Optional[str]:
        """Find the most relevant snippet from content for the claim"""
        if not content or len(content) < 50:
            return None
        
        # Split into sentences
        sentences = [s.strip() for s in re.split(r'[.!?]+', content) if s.strip()]
        
        if not sentences:
            return None
        
        # Score sentences for relevance
        scored_sentences = []
        claim_words = set(claim.lower().split())
        
        for sentence in sentences:
            if len(sentence) < 20:  # Skip very short sentences
                continue
            
            sentence_words = set(sentence.lower().split())
            
            # Calculate word overlap
            word_overlap = len(claim_words & sentence_words) / len(claim_words)
            
            # Bonus for fact-indicating phrases
            fact_bonus = sum(1 for indicator in self.fact_indicators if indicator in sentence.lower()) * 0.2
            
            # Bonus for numbers/dates (often important for facts)
            number_bonus = len(re.findall(r'\d+', sentence)) * 0.1
            
            total_score = word_overlap + fact_bonus + number_bonus
            scored_sentences.append((sentence, total_score))
        
        if not scored_sentences:
            # Fallback: return first substantial paragraph
            paragraphs = [p.strip() for p in content.split('\n\n') if len(p.strip()) > 100]
            if paragraphs:
                return paragraphs[0][:self.max_snippet_words * 6]  # Rough word limit
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
            return '. '.join(snippet_sentences) + '.'
        else:
            # Return the best sentence even if it's long
            return scored_sentences[0][0][:self.max_snippet_words * 6]
    
    def _calculate_relevance(self, snippet: str, claim: str) -> float:
        """Calculate relevance score between snippet and claim"""
        try:
            snippet_words = set(snippet.lower().split())
            claim_words = set(claim.lower().split())
            
            # Word overlap
            overlap = len(claim_words & snippet_words) / len(claim_words | snippet_words)
            
            # Boost for fact-indicating language
            fact_boost = sum(1 for indicator in self.fact_indicators if indicator in snippet.lower()) * 0.1
            
            # Boost for specific numbers/dates
            number_boost = len(re.findall(r'\b\d+(?:\.\d+)?%?\b', snippet)) * 0.05
            
            # Length penalty for very short snippets
            length_penalty = 0 if len(snippet.split()) > 20 else -0.2
            
            score = min(1.0, overlap + fact_boost + number_boost + length_penalty)
            return max(0.0, score)
            
        except Exception as e:
            logger.warning(f"Relevance calculation error: {e}")
            return 0.5  # Default moderate relevance
    
    def _rank_snippets(self, snippets: List[EvidenceSnippet], claim: str) -> List[EvidenceSnippet]:
        """Rank evidence snippets by relevance and credibility"""
        def scoring_function(snippet: EvidenceSnippet) -> float:
            # Base relevance score
            score = snippet.relevance_score

            # Detect and deprioritize fact-check meta-content
            factcheck_sites = ['snopes', 'factcheck.org', 'politifact', 'fullfact']
            is_factcheck = any(site in snippet.source.lower() or site in snippet.url.lower()
                             for site in factcheck_sites)
            if is_factcheck:
                score *= 0.3  # Heavily deprioritize fact-check sites

            # Domain credibility boost for primary sources
            primary_sources = [
                '.edu', '.gov', '.org', 'bbc', 'reuters', 'nature', 'science',
                'pnas.org', 'nasa.gov', 'noaa.gov', 'who.int', 'nhs.uk'
            ]
            if any(indicator in snippet.source.lower() for indicator in primary_sources):
                score += 0.3  # Increased boost for primary sources

            # Recent content boost
            if snippet.published_date:
                try:
                    # Simple boost for more recent content
                    if '2024' in snippet.published_date or '2023' in snippet.published_date:
                        score += 0.1
                except:
                    pass

            # Length boost for substantial snippets
            if snippet.word_count > 50:
                score += 0.1

            return score

        # Sort by combined score
        return sorted(snippets, key=scoring_function, reverse=True)

    def _extract_domain(self, url: str) -> str:
        """Extract clean domain from URL for comparison"""
        from urllib.parse import urlparse

        try:
            parsed = urlparse(url)
            domain = parsed.netloc

            # Remove www. prefix
            if domain.startswith('www.'):
                domain = domain[4:]

            return domain.lower()
        except Exception as e:
            logger.warning(f"Failed to extract domain from URL '{url}': {e}")
            return ""