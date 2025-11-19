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
from app.utils.url_utils import extract_domain

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

        # Blocked domains (rate limiting issues)
        self.blocked_domains = {'yahoo.com', 'www.yahoo.com'}

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
        excluded_domain: Optional[str] = None,
        temporal_analysis: Dict = None
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
        """
        try:
            # Step 1: Build context-enriched search query
            # TIER 1 IMPROVEMENT: Enhanced query formulation
            from app.core.config import settings

            if settings.ENABLE_QUERY_EXPANSION:
                from app.utils.query_formulation import get_query_formulator
                formulator = get_query_formulator()
                search_query = formulator.formulate_query(
                    claim,
                    subject_context,
                    key_entities,
                    temporal_analysis
                )
                logger.info(f"🔎 QUERY EXPANDED | Claim: '{claim[:60]}...'")
                logger.info(f"🔎 QUERY RESULT  | Query: '{search_query}'")
            else:
                # FALLBACK: Existing logic (preserve backward compatibility)
                search_query = claim
                logger.info(f"🔎 QUERY BASIC | Using claim as-is: '{search_query[:80]}...')")
                if subject_context and key_entities:
                    # Only add entities that AREN'T already in the claim text (avoid duplication)
                    unique_entities = [e for e in key_entities[:3] if e.lower() not in claim.lower()]
                    if unique_entities:
                        entities_str = " ".join(unique_entities[:2])  # Max 2 additional entities
                        search_query = f"{claim} {entities_str}"
                        logger.info(f"Context-enriched search with {len(unique_entities)} unique entities: '{search_query}'")
                    else:
                        logger.info(f"No context enrichment needed (entities already in claim)")

            # Step 2: Search for relevant pages
            search_results = await self.search_service.search_for_evidence(search_query, max_results=max_sources * 2)

            # DIAGNOSTIC: Log search results
            logger.info(f"🔍 SEARCH RESULTS | Found: {len(search_results)} results | Requested: {max_sources * 2}")

            # Filter out excluded domain (self-citation prevention)
            if excluded_domain:
                original_count = len(search_results)
                search_results = [
                    result for result in search_results
                    if extract_domain(result.url) != excluded_domain
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
            failed_count = 0
            for result in extracted_results:
                if isinstance(result, EvidenceSnippet):
                    evidence_snippets.append(result)
                elif isinstance(result, Exception):
                    failed_count += 1
                    logger.warning(f"Evidence extraction failed: {result}")

            # DIAGNOSTIC: Log extraction success rate
            total_attempts = len(extracted_results)
            success_rate = (len(evidence_snippets) / total_attempts * 100) if total_attempts > 0 else 0
            logger.info(f"📄 EXTRACTION | Success: {len(evidence_snippets)}/{total_attempts} ({success_rate:.1f}%) | Failed: {failed_count}")

            # Step 4: Rank by relevance and return top results
            ranked_snippets = self._rank_snippets(evidence_snippets, claim)
            logger.info(f"🎯 FINAL EVIDENCE | Returning: {len(ranked_snippets[:max_sources])} snippets (requested: {max_sources})")
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
                # Block domains with rate limiting issues
                domain = extract_domain(search_result.url, fallback="unknown")

                if any(blocked in domain.lower() for blocked in self.blocked_domains):
                    logger.info(f"⛔ Skipping blocked domain: {domain}")
                    return None

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

                    # Find most relevant snippet (now async for semantic extraction)
                    snippet_text = await self._find_relevant_snippet(content, claim)

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
        sentences = [s.strip() for s in re.split(r'[.!?]+', content) if s.strip()]

        if not sentences:
            return None

        # TIER 1 IMPROVEMENT: Semantic snippet extraction (if enabled)
        if settings.ENABLE_SEMANTIC_SNIPPET_EXTRACTION:
            try:
                return await self._extract_semantic_snippet(claim, sentences)
            except Exception as e:
                logger.error(f"Semantic snippet extraction failed: {e}, falling back to word overlap")
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

    async def _extract_semantic_snippet(self, claim: str, sentences: List[str]) -> Optional[str]:
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
        valid_sentences = [(i, sent) for i, sent in enumerate(sentences) if len(sent) > 20]
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
                claim_embedding,
                sentence_embeddings[i]
            )
            similarities.append((orig_idx, sent_text, similarity))

        # Sort by similarity
        similarities.sort(key=lambda x: x[2], reverse=True)

        # Filter by threshold
        threshold = settings.SNIPPET_SEMANTIC_THRESHOLD
        relevant_sentences = [
            (idx, text, sim) for idx, text, sim in similarities
            if sim >= threshold
        ]

        if not relevant_sentences:
            # No sentences meet threshold - return best match anyway
            best_match = similarities[0]
            logger.debug(f"No sentences above threshold {threshold}, using best: {best_match[2]:.2f}")
            return best_match[1][:self.max_snippet_words * 6]

        # Build snippet from top sentences WITH CONTEXT
        # Include N sentences before/after for coherence (using only valid sentences)
        context_window = settings.SNIPPET_CONTEXT_SENTENCES
        best_orig_idx = relevant_sentences[0][0]  # Original index of best sentence

        # Find position in valid_sentences list
        valid_idx = next(i for i, (orig_idx, _) in enumerate(valid_sentences) if orig_idx == best_orig_idx)

        # Build context from valid_sentences only (excludes short sentences)
        start_idx = max(0, valid_idx - context_window)
        end_idx = min(len(valid_sentences), valid_idx + context_window + 1)

        snippet_sentences = [sent for _, sent in valid_sentences[start_idx:end_idx]]
        snippet = '. '.join(snippet_sentences).strip()

        # Enforce max length
        if len(snippet.split()) > self.max_snippet_words:
            words = snippet.split()
            snippet = ' '.join(words[:self.max_snippet_words]) + '...'

        logger.debug(f"Semantic snippet similarity: {relevant_sentences[0][2]:.2f}")
        return snippet
    
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
        """
        Rank evidence snippets by relevance and credibility.

        TIER 1 IMPROVEMENT: Enhanced with primary source detection.
        """
        from app.core.config import settings

        def scoring_function(snippet: EvidenceSnippet) -> float:
            # Base relevance score
            score = snippet.relevance_score

            # TIER 1 IMPROVEMENT: Primary source detection and boosting
            if settings.ENABLE_PRIMARY_SOURCE_DETECTION:
                from app.utils.source_type_classifier import get_source_type_classifier
                classifier = get_source_type_classifier()

                source_info = classifier.classify_source(
                    snippet.url,
                    snippet.title,
                    snippet.text
                )

                # Store in metadata for transparency
                snippet.metadata['source_type'] = source_info['source_type']
                snippet.metadata['primary_indicators'] = source_info['primary_indicators']
                snippet.metadata['is_original_research'] = source_info['is_original_research']

                # Apply credibility boost/penalty
                score += source_info['credibility_boost']

                # Extra boost for original research
                if source_info['is_original_research']:
                    score += 0.15
                    logger.info(f"Original research detected: {snippet.source}")

                logger.debug(
                    f"Source classification: {source_info['source_type']} "
                    f"(boost: {source_info['credibility_boost']:+.2f})"
                )

            # EXISTING: Detect and deprioritize fact-check meta-content
            factcheck_sites = ['snopes', 'factcheck.org', 'politifact', 'fullfact']
            is_factcheck = any(site in snippet.source.lower() or site in snippet.url.lower()
                             for site in factcheck_sites)
            if is_factcheck:
                score *= 0.3  # Heavily deprioritize fact-check sites

            # EXISTING: Domain credibility boost for primary sources (kept as fallback)
            if not settings.ENABLE_PRIMARY_SOURCE_DETECTION:
                primary_sources = [
                    '.edu', '.gov', '.org', 'bbc', 'reuters', 'nature', 'science',
                    'pnas.org', 'nasa.gov', 'noaa.gov', 'who.int', 'nhs.uk'
                ]
                if any(indicator in snippet.source.lower() for indicator in primary_sources):
                    score += 0.3  # Increased boost for primary sources

            # EXISTING: Recent content boost
            if snippet.published_date:
                try:
                    # Simple boost for more recent content
                    if '2024' in snippet.published_date or '2023' in snippet.published_date:
                        score += 0.1
                except:
                    pass

            # EXISTING: Length boost for substantial snippets
            if snippet.word_count > 50:
                score += 0.1

            return score

        # Sort by combined score
        return sorted(snippets, key=scoring_function, reverse=True)