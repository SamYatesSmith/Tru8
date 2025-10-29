"""
PDF Evidence Extractor with Page Number Tracking
Extracts evidence from PDF documents with precise page citations
"""
import logging
import re
import asyncio
from typing import Optional, Dict, Any, List
from io import BytesIO
import httpx

logger = logging.getLogger(__name__)

class PDFEvidenceExtractor:
    """Extract evidence from PDFs with page-level precision"""

    def __init__(self):
        self.timeout = 30  # PDFs can be large
        self.max_pages_to_search = 200  # Prevent timeout on huge PDFs

    async def extract_evidence_from_pdf(
        self,
        url: str,
        claim: str,
        max_results: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Extract relevant evidence snippets from PDF with page numbers.

        Args:
            url: PDF URL
            claim: Claim text to search for
            max_results: Maximum number of snippets to return

        Returns:
            List of evidence dictionaries with page_number metadata
        """
        try:
            # Download PDF
            logger.info(f"Downloading PDF: {url}")
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url)
                response.raise_for_status()

            pdf_bytes = BytesIO(response.content)

            # Run blocking PDF operations in executor to avoid blocking event loop
            loop = asyncio.get_event_loop()

            # Extract metadata (blocking operation)
            metadata = await loop.run_in_executor(None, self._extract_pdf_metadata, pdf_bytes)
            logger.info(f"PDF metadata: {metadata['title']}, {metadata['total_pages']} pages")

            # Search for relevant content (blocking operation)
            pdf_bytes.seek(0)  # Reset stream
            matches = await loop.run_in_executor(
                None, self._search_pdf_for_claim, pdf_bytes, claim, metadata['total_pages']
            )

            # Return top matches
            return matches[:max_results]

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to download PDF {url}: {e}")
            return []
        except Exception as e:
            logger.error(f"PDF extraction error for {url}: {e}")
            return []

    def _extract_pdf_metadata(self, pdf_bytes: BytesIO) -> Dict[str, Any]:
        """Extract PDF metadata (title, author, pages)"""
        try:
            import PyPDF2
            reader = PyPDF2.PdfReader(pdf_bytes)
            metadata = reader.metadata or {}

            return {
                'title': metadata.get('/Title', 'Untitled Document'),
                'author': metadata.get('/Author', 'Unknown'),
                'total_pages': len(reader.pages),
                'creation_date': metadata.get('/CreationDate', '')
            }
        except Exception as e:
            logger.warning(f"Failed to extract PDF metadata: {e}")
            return {
                'title': 'Document',
                'author': 'Unknown',
                'total_pages': 0,
                'creation_date': ''
            }

    def _search_pdf_for_claim(
        self,
        pdf_bytes: BytesIO,
        claim: str,
        total_pages: int
    ) -> List[Dict[str, Any]]:
        """
        Search PDF for relevant passages matching claim.

        Returns list of matches with page numbers and relevance scores.
        """
        matches = []
        claim_keywords = self._extract_keywords(claim)

        # Use pdfplumber for better text extraction
        try:
            import pdfplumber
            with pdfplumber.open(pdf_bytes) as pdf:
                pages_to_search = min(len(pdf.pages), self.max_pages_to_search)
                logger.info(f"Searching {pages_to_search} pages for relevant content")

                for page_num in range(pages_to_search):
                    # Log progress every 20 pages for large PDFs
                    if page_num % 20 == 0 and page_num > 0:
                        logger.info(f"PDF search progress: {page_num}/{pages_to_search} pages processed")

                    page = pdf.pages[page_num]
                    page_text = page.extract_text()

                    if not page_text:
                        continue

                    # Calculate relevance score
                    relevance_score = self._calculate_relevance(page_text, claim, claim_keywords)

                    if relevance_score > 0.3:  # Threshold for relevance
                        # Extract relevant snippet from page
                        snippet = self._extract_relevant_snippet(page_text, claim, claim_keywords)

                        matches.append({
                            'text': snippet,
                            'page_number': page_num + 1,  # 1-indexed
                            'relevance_score': relevance_score,
                            'context_before': self._get_context(page_text, snippet, before=True),
                            'context_after': self._get_context(page_text, snippet, after=True)
                        })

        except Exception as e:
            logger.error(f"Error searching PDF: {e}")
            return []

        # Sort by relevance
        matches.sort(key=lambda x: x['relevance_score'], reverse=True)
        return matches

    def _extract_keywords(self, text: str) -> List[str]:
        """Extract important keywords from claim text"""
        # Remove stopwords and extract meaningful terms
        stopwords = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
        words = re.findall(r'\b\w+\b', text.lower())
        keywords = [w for w in words if w not in stopwords and len(w) > 3]
        return keywords

    def _calculate_relevance(self, page_text: str, claim: str, keywords: List[str]) -> float:
        """Calculate relevance score for page text"""
        page_lower = page_text.lower()
        claim_lower = claim.lower()

        # Exact phrase match (highest weight)
        if claim_lower in page_lower:
            return 1.0

        # Keyword density
        keyword_matches = sum(1 for kw in keywords if kw in page_lower)
        keyword_score = keyword_matches / len(keywords) if keywords else 0

        return keyword_score

    def _extract_relevant_snippet(
        self,
        page_text: str,
        claim: str,
        keywords: List[str],
        snippet_length: int = 300
    ) -> str:
        """Extract most relevant snippet from page"""
        sentences = re.split(r'[.!?]+', page_text)

        best_sentence_idx = 0
        best_score = 0

        # Find sentence with most keyword matches
        for idx, sentence in enumerate(sentences):
            sentence_lower = sentence.lower()
            score = sum(1 for kw in keywords if kw in sentence_lower)

            if score > best_score:
                best_score = score
                best_sentence_idx = idx

        # Extract snippet around best sentence
        start_idx = max(0, best_sentence_idx - 1)
        end_idx = min(len(sentences), best_sentence_idx + 2)

        snippet = '. '.join(sentences[start_idx:end_idx]).strip()

        # Truncate if too long
        if len(snippet) > snippet_length:
            snippet = snippet[:snippet_length] + "..."

        return snippet

    def _get_context(self, page_text: str, snippet: str, before: bool = False, after: bool = False) -> str:
        """Get surrounding context for snippet"""
        # Find snippet position
        snippet_start = page_text.find(snippet)
        if snippet_start == -1:
            return ""

        if before:
            # Get 100 chars before
            context_start = max(0, snippet_start - 100)
            return "..." + page_text[context_start:snippet_start].strip()

        if after:
            # Get 100 chars after
            snippet_end = snippet_start + len(snippet)
            context_end = min(len(page_text), snippet_end + 100)
            return page_text[snippet_end:context_end].strip() + "..."

        return ""

# Singleton instance
_pdf_extractor_instance = None

def get_pdf_extractor() -> PDFEvidenceExtractor:
    """Get singleton PDFEvidenceExtractor instance"""
    global _pdf_extractor_instance
    if _pdf_extractor_instance is None:
        _pdf_extractor_instance = PDFEvidenceExtractor()
    return _pdf_extractor_instance
