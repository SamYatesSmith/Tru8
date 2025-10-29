# Source Quality Control & Citation Precision Enhancement Plan

**Project:** Tru8 Fact-Checking Platform
**Date:** October 29, 2025
**Status:** Planning → Implementation
**Priority:** HIGH (Addresses critical quality gaps in evidence pipeline)

---

## 📋 Executive Summary

This plan addresses two critical gaps in the Tru8 evidence pipeline:

1. **Inappropriate Source Inclusion**: Student materials, exam guides, and educational resources are currently passing through as "General Sources" (0.6 credibility) and appearing as evidence.

2. **Citation Imprecision**: Large PDF documents (e.g., entire newspaper editions, 200-page government reports) are cited without page numbers, making verification difficult for users.

**Solution Approach**: Three-phased implementation combining heuristic filtering, enhanced citation extraction, and optional LLM-based validation.

**Target Credibility Threshold**: 0.65 (Balanced approach between coverage and quality)

---

## 🔍 Current State Analysis

### **Where Source Validation Currently Happens**

**Location**: `backend/app/pipeline/retrieve.py` (lines 163-233)

```python
def _apply_credibility_weighting(self, evidence_list):
    # Line 171: Credibility score assigned via domain lookup
    credibility_score = self._get_credibility_score(source, url, evidence)

    # Line 186-187: Current filtering (VERY PERMISSIVE)
    evidence_list = [e for e in evidence_list if e.get("credibility_score", 0.6) > 0.0]
    # ❌ Only excludes satire/blacklist (0.0) - everything else passes
```

**Credibility Database**: `backend/app/data/source_credibility.json`
- 214 domains across 15 tiers
- Scores: 1.0 (Academic) → 0.0 (Satire/Blacklist)
- Unknown domains default to 0.6 ("General Source")

**Problem Examples**:
```
✗ king-james.co.uk/revision-booklet.pdf → 0.6 (General) → PASSES ❌
✗ student-uploads.edu/exam-notes.pdf → 0.6 (General) → PASSES ❌
✓ bbc.co.uk → 0.9 (News Tier 1) → PASSES ✅
✓ nature.com → 0.95 (Scientific) → PASSES ✅
```

### **Where Citation Extraction Currently Happens**

**Location**: `backend/app/services/evidence.py` (lines 54-148)

```python
async def _extract_from_page(self, search_result, claim):
    # Line 99-106: Fetches page content
    response = await client.get(search_result.url)
    content = self._extract_main_content(response.text, url)

    # Line 113: Finds relevant snippet
    snippet_text = self._find_relevant_snippet(content, claim)

    # Line 121-128: Creates EvidenceSnippet
    return EvidenceSnippet(
        text=snippet_text,
        source=search_result.source,
        url=search_result.url,
        title=search_result.title,  # ❌ No page number metadata
        published_date=search_result.published_date,
        relevance_score=relevance_score
    )
```

**Problem**: PDF extraction uses trafilatura/readability which strips page metadata.

---

## 🎯 Solution Architecture

### **Two-Stage Filtering Approach**

```
Evidence Retrieval (retrieve.py)
         ↓
┌────────────────────────────┐
│ STAGE 1: Heuristic Filter  │ ← PHASE 1 (NEW)
│ - Content-type patterns    │
│ - URL structure analysis   │
│ - Title keyword matching   │
└────────────────────────────┘
         ↓
┌────────────────────────────┐
│ Credibility Scoring        │ ← Existing (Enhanced)
│ - Domain lookup            │
│ - Threshold: >= 0.65       │ ← CHANGED from > 0.0
└────────────────────────────┘
         ↓
┌────────────────────────────┐
│ STAGE 2: LLM Validation    │ ← PHASE 3 (Optional)
│ - Contextual assessment    │
│ - Ambiguous case handling  │
└────────────────────────────┘
         ↓
    NLI Verification
```

---

## 📅 Phase 1: Content-Type Filtering & Threshold Adjustment

**Timeline**: 2-3 hours
**Priority**: CRITICAL
**Effort**: Low
**Impact**: HIGH (Fixes immediate quality issues)

### **Objectives**

1. Filter out inappropriate content types using heuristic pattern matching
2. Raise credibility threshold to 0.65 (balanced approach)
3. Add feature flag for easy rollback
4. Log filtering decisions for transparency

### **Implementation Details**

#### **1.1 Create Source Validator Module**

**New File**: `backend/app/utils/source_validator.py`

```python
"""
Source Validator - Content-Type Heuristic Filtering
Filters out inappropriate sources before NLI verification
"""
import logging
import re
from typing import List, Dict, Any, Tuple

logger = logging.getLogger(__name__)

class SourceValidator:
    """Validate source appropriateness using heuristic pattern matching"""

    def __init__(self):
        # Educational materials (inappropriate for fact-checking)
        self.educational_patterns = [
            r'\b(revision guide|study guide|exam prep|test prep)\b',
            r'\b(student notes|class notes|lecture notes|course materials)\b',
            r'\b(homework|coursework|assignment|quiz|worksheet)\b',
            r'\b(gcse|a-level|ks[0-9]|year [0-9]{1,2} |y[0-9]{1,2} )\b',
            r'\bpaper [0-9]+ revision\b',
            r'\bexam board\b',
        ]

        # Low-quality or user-generated content
        self.low_quality_patterns = [
            r'\b(forum|discussion board|comment section)\b',
            r'\b(blog post|personal blog|opinion piece|editorial)\b',
            r'\b(promotional|advertisement|marketing|press release)\b',
            r'\buser[ -]?(generated|submitted|uploaded)\b',
            r'\b(wiki\b|reddit|quora|yahoo answers)\b',
        ]

        # URL structure patterns (educational domains)
        self.url_education_patterns = [
            r'/students?/',
            r'/revision/',
            r'/uploads/',
            r'/resources/ks[0-9]',
            r'/exam-?prep/',
            r'/study-?guides?/',
            r'/education/',  # Unless it's .gov or authoritative
        ]

        # Authoritative education domains (ALLOWED despite /education/ in URL)
        self.authoritative_education_domains = [
            'gov.uk', 'gov', 'education.gov.uk',
            'ofsted.gov.uk', 'ofqual.gov.uk',
            'ed.gov', 'department-for-education.gov.uk'
        ]

    def validate_sources(self, evidence_list: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Filter out inappropriate sources using heuristic patterns.

        Args:
            evidence_list: List of evidence dictionaries

        Returns:
            Tuple of (filtered_list, stats_dict)
        """
        validated = []
        filtered_out = []

        for evidence in evidence_list:
            title = evidence.get('title', '').lower()
            url = evidence.get('url', '').lower()
            source = evidence.get('source', '').lower()

            # Combine text for pattern matching
            combined_text = f"{title} {url} {source}"

            # Check if inappropriate
            is_inappropriate, reason = self._is_inappropriate(combined_text, url)

            if is_inappropriate:
                filtered_out.append({
                    'title': evidence.get('title'),
                    'url': evidence.get('url'),
                    'reason': reason
                })
                logger.info(f"Filtered out source: {evidence.get('title')[:50]} - Reason: {reason}")
            else:
                validated.append(evidence)

        stats = {
            'original_count': len(evidence_list),
            'validated_count': len(validated),
            'filtered_count': len(filtered_out),
            'filtered_sources': filtered_out
        }

        return validated, stats

    def _is_inappropriate(self, combined_text: str, url: str) -> Tuple[bool, str]:
        """
        Check if source is inappropriate using pattern matching.

        Returns:
            Tuple of (is_inappropriate: bool, reason: str)
        """
        # Check educational material patterns
        for pattern in self.educational_patterns:
            if re.search(pattern, combined_text, re.IGNORECASE):
                return True, f"Educational material detected (pattern: {pattern[:30]})"

        # Check low-quality patterns
        for pattern in self.low_quality_patterns:
            if re.search(pattern, combined_text, re.IGNORECASE):
                return True, f"Low-quality source detected (pattern: {pattern[:30]})"

        # Check URL structure patterns (unless authoritative domain)
        if not self._is_authoritative_education_domain(url):
            for pattern in self.url_education_patterns:
                if re.search(pattern, url, re.IGNORECASE):
                    return True, f"Educational URL structure (pattern: {pattern})"

        return False, ""

    def _is_authoritative_education_domain(self, url: str) -> bool:
        """Check if domain is an authoritative education source (e.g., gov.uk/education)"""
        for domain in self.authoritative_education_domains:
            if domain in url:
                return True
        return False

# Singleton instance
_validator_instance = None

def get_source_validator() -> SourceValidator:
    """Get singleton SourceValidator instance"""
    global _validator_instance
    if _validator_instance is None:
        _validator_instance = SourceValidator()
    return _validator_instance
```

#### **1.2 Integrate Validator into Retrieval Pipeline**

**File**: `backend/app/pipeline/retrieve.py`

**Location**: After line 228 (after all other filtering)

```python
# Add after domain capping (line 226)
# Apply source validation if enabled (Phase 1)
if settings.ENABLE_SOURCE_VALIDATION:
    from app.utils.source_validator import get_source_validator
    validator = get_source_validator()
    evidence_list, validation_stats = validator.validate_sources(evidence_list)
    logger.info(
        f"Source validation: {validation_stats['validated_count']}/{validation_stats['original_count']} sources retained, "
        f"{validation_stats['filtered_count']} filtered out"
    )
```

#### **1.3 Raise Credibility Threshold**

**File**: `backend/app/pipeline/retrieve.py`

**Location**: Line 186-187

**Change**:
```python
# OLD (too permissive):
evidence_list = [e for e in evidence_list if e.get("credibility_score", 0.6) > 0.0]

# NEW (balanced threshold):
MIN_CREDIBILITY = 0.65  # Filters out low-quality "general" sources
evidence_list = [e for e in evidence_list if e.get("credibility_score", 0.6) >= MIN_CREDIBILITY]
logger.info(f"Credibility filtering: Retained sources with score >= {MIN_CREDIBILITY}")
```

#### **1.4 Add Feature Flag**

**File**: `backend/app/core/config.py`

**Location**: After line 91 (near other Phase 3 flags)

```python
# Phase 3.5 - Source Quality Control (Week 9.5-10)
ENABLE_SOURCE_VALIDATION: bool = Field(True, env="ENABLE_SOURCE_VALIDATION")
SOURCE_CREDIBILITY_THRESHOLD: float = Field(0.65, env="SOURCE_CREDIBILITY_THRESHOLD")
```

#### **1.5 Update Retrieve Logic to Use Config**

**File**: `backend/app/pipeline/retrieve.py`

**Location**: Line 187 (modify threshold line)

```python
# Use configurable threshold
MIN_CREDIBILITY = getattr(settings, 'SOURCE_CREDIBILITY_THRESHOLD', 0.65)
evidence_list = [e for e in evidence_list if e.get("credibility_score", 0.6) >= MIN_CREDIBILITY]
```

### **Testing Strategy**

#### **Unit Tests**

**New File**: `backend/tests/unit/test_source_validator.py`

```python
import pytest
from app.utils.source_validator import SourceValidator

def test_filters_revision_guides():
    validator = SourceValidator()
    evidence = [{
        'title': 'Y13 Ethics Revision Guide Paper 2',
        'url': 'https://king-james.co.uk/wp-content/uploads/revision.pdf',
        'source': 'king-james.co.uk'
    }]

    validated, stats = validator.validate_sources(evidence)

    assert len(validated) == 0
    assert stats['filtered_count'] == 1
    assert 'Educational material' in stats['filtered_sources'][0]['reason']

def test_allows_bbc_news():
    validator = SourceValidator()
    evidence = [{
        'title': 'UK News Report on Policy Changes',
        'url': 'https://bbc.co.uk/news/uk-123456',
        'source': 'BBC'
    }]

    validated, stats = validator.validate_sources(evidence)

    assert len(validated) == 1
    assert stats['filtered_count'] == 0

def test_allows_gov_education():
    validator = SourceValidator()
    evidence = [{
        'title': 'Department for Education Statistics',
        'url': 'https://gov.uk/education/statistics-report',
        'source': 'GOV.UK'
    }]

    validated, stats = validator.validate_sources(evidence)

    assert len(validated) == 1  # Should PASS (authoritative)
    assert stats['filtered_count'] == 0

def test_filters_student_uploads():
    validator = SourceValidator()
    evidence = [{
        'title': 'Class Notes on British Politics',
        'url': 'https://university.edu/uploads/student-notes.pdf',
        'source': 'university.edu'
    }]

    validated, stats = validator.validate_sources(evidence)

    assert len(validated) == 0
    assert stats['filtered_count'] == 1
```

Run tests:
```bash
cd backend
pytest tests/unit/test_source_validator.py -v
```

#### **Integration Testing**

**Test Case 1**: Run pipeline on article that previously cited exam guide
- **Expected**: Exam guide filtered out, verdict based on remaining sources
- **Check**: Look for "Source validation" in logs

**Test Case 2**: Run on article with only high-credibility sources (BBC, Reuters)
- **Expected**: All sources retained
- **Check**: No filtering occurs

**Test Case 3**: Disable feature flag, run same article
- **Expected**: Exam guide appears again (rollback works)

### **Success Metrics**

✅ **Phase 1 Complete When**:
1. Source validator tests pass (100% coverage)
2. King-james.co.uk revision guide filtered out
3. BBC, Guardian, Gov.uk sources still appear
4. Logs show filtering decisions clearly
5. Feature flag toggle works (enable/disable)

### **Rollback Plan**

If issues occur:
```python
# In .env or config:
ENABLE_SOURCE_VALIDATION=False
```

Restart workers, filtering disabled immediately.

---

## 📅 Phase 2: Citation Precision & Evidence Context Display

**Timeline**: 7-9 hours
**Priority**: HIGH
**Effort**: Medium
**Impact**: VERY HIGH (Dramatically improves user verification experience)

### **Objectives**

1. Extract page numbers from PDF evidence
2. Display page numbers in frontend citations
3. Add enhanced snippet context (surrounding sentences)
4. **Store NLI verification stance for each evidence item** ⭐ NEW
5. **Display "why evidence supports/contradicts" directly in evidence cards** ⭐ NEW
6. Show confidence scores and reasoning without requiring extra clicks

### **Implementation Details**

#### **2.1 Install PDF Processing Library**

**File**: `backend/requirements.txt`

Add:
```txt
PyPDF2>=3.0.0  # PDF page extraction
pdfplumber>=0.10.0  # Alternative with better text extraction
```

Install:
```bash
cd backend
pip install PyPDF2 pdfplumber
```

#### **2.2 Create PDF Evidence Extractor**

**New File**: `backend/app/services/pdf_evidence.py`

```python
"""
PDF Evidence Extractor with Page Number Tracking
Extracts evidence from PDF documents with precise page citations
"""
import logging
import re
from typing import Optional, Dict, Any, List
from io import BytesIO
import httpx
import PyPDF2
import pdfplumber

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

            # Extract metadata
            metadata = self._extract_pdf_metadata(pdf_bytes)
            logger.info(f"PDF metadata: {metadata['title']}, {metadata['total_pages']} pages")

            # Search for relevant content
            pdf_bytes.seek(0)  # Reset stream
            matches = self._search_pdf_for_claim(pdf_bytes, claim, metadata['total_pages'])

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
            with pdfplumber.open(pdf_bytes) as pdf:
                pages_to_search = min(len(pdf.pages), self.max_pages_to_search)

                for page_num in range(pages_to_search):
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
```

#### **2.3 Integrate PDF Extractor into Evidence Service**

**File**: `backend/app/services/evidence.py`

**Location**: Modify `_extract_from_page` method (around line 89-148)

```python
async def _extract_from_page(self, search_result: SearchResult, claim: str,
                            semaphore: asyncio.Semaphore) -> Optional[EvidenceSnippet]:
    """Extract relevant content from a single page (enhanced for PDFs)"""
    async with semaphore:
        try:
            # NEW: Check if URL is a PDF
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
                        title=f"{search_result.title} (p. {best_match['page_number']})",  # ← ADD PAGE
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

            # EXISTING: Non-PDF extraction (HTML pages)
            async with httpx.AsyncClient(
                timeout=self.timeout,
                follow_redirects=True
            ) as client:
                response = await client.get(search_result.url)
                # ... rest of existing code
```

#### **2.4 Update EvidenceSnippet Class**

**File**: `backend/app/services/evidence.py`

**Location**: Lines 14-36 (EvidenceSnippet class)

```python
class EvidenceSnippet:
    """Extracted evidence snippet with metadata"""

    def __init__(self, text: str, source: str, url: str, title: str,
                 published_date: Optional[str] = None, relevance_score: float = 0.0,
                 metadata: Optional[Dict[str, Any]] = None):  # ← ADD metadata parameter
        self.text = text
        self.source = source
        self.url = url
        self.title = title
        self.published_date = published_date
        self.relevance_score = relevance_score
        self.word_count = len(text.split())
        self.metadata = metadata or {}  # ← NEW: Store page numbers, context

    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "source": self.source,
            "url": self.url,
            "title": self.title,
            "published_date": self.published_date,
            "relevance_score": self.relevance_score,
            "word_count": self.word_count,
            "metadata": self.metadata  # ← ADD to serialization
        }
```

#### **2.5 Store Citation Metadata & NLI Context in Database**

**Database Migration**: Add citation precision AND NLI context fields to Evidence model

**File**: `backend/app/models/check.py`

**Location**: Line 76-119 (Evidence model)

```python
class Evidence(SQLModel, table=True):
    # ... existing fields ...

    # Citation Precision Enhancement (Phase 2)
    page_number: Optional[int] = Field(default=None, description="Page number in PDF/document")
    context_before: Optional[str] = Field(default=None, description="Text before snippet")
    context_after: Optional[str] = Field(default=None, description="Text after snippet")

    # NLI Context Display (Phase 2 - NEW)
    nli_stance: Optional[str] = Field(default=None, description="'supporting'|'contradicting'|'neutral'")
    nli_confidence: Optional[float] = Field(default=None, ge=0, le=1, description="NLI confidence score 0-1")
    nli_entailment: Optional[float] = Field(default=None, ge=0, le=1, description="Entailment probability")
    nli_contradiction: Optional[float] = Field(default=None, ge=0, le=1, description="Contradiction probability")
```

**Create Migration**:
```bash
cd backend
alembic revision --autogenerate -m "add_citation_and_nli_context_fields"
alembic upgrade head
```

**Note**: This single migration adds 7 new fields (3 citation + 4 NLI context)

#### **2.6a Enrich Evidence with NLI Data in Judge Stage**

**File**: `backend/app/pipeline/judge.py`

**Location**: Lines 525-541 (Inside `judge_single_claim` function within `judge_all_claims` method)

**Challenge**: Evidence items need NLI verification data attached before being saved to database

**Solution**: Enrich evidence with NLI data at the point where both verifications and evidence are available

**Key Insight**: The `judge_single_claim` function in judge.py receives both:
- `verifications` (has NLI scores: relationship, confidence, entailment_score, etc.)
- `evidence` (lacks NLI scores)

These lists are in the same order (verifications[i] corresponds to evidence[i]), allowing index-based matching.

```python
async def judge_single_claim(claim: Dict[str, Any]) -> Dict[str, Any]:
    async with semaphore:
        position = str(claim.get("position", 0))
        verifications = verifications_by_claim.get(position, [])
        evidence = evidence_by_claim.get(position, [])

        # >>> NEW: Enrich evidence with NLI verification data <<<
        enriched_evidence = []
        for i, ev in enumerate(evidence):
            ev_copy = ev.copy()  # Don't mutate original

            # Attach NLI data if verification exists for this evidence
            if i < len(verifications):
                verification = verifications[i]
                relationship = verification.get("relationship", "neutral")

                # Map NLI relationship to user-friendly stance
                ev_copy["nli_stance"] = (
                    "supporting" if relationship == "entails" else
                    "contradicting" if relationship == "contradicts" else
                    "neutral"
                )
                ev_copy["nli_confidence"] = verification.get("confidence", 0.0)
                ev_copy["nli_entailment"] = verification.get("entailment_score", 0.0)
                ev_copy["nli_contradiction"] = verification.get("contradiction_score", 0.0)

            enriched_evidence.append(ev_copy)

        # Aggregate verification signals
        signals = claim_verifier.aggregate_verification_signals(verifications)

        # Get final judgment with ENRICHED evidence (now has NLI fields)
        judgment = await self.claim_judge.judge_claim(claim, signals, enriched_evidence)

        return {
            **judgment.to_dict(),  # Evidence items now include NLI fields!
            "position": claim.get("position", 0),
            "verification_signals": signals
        }
```

**Why This Location?**
1. Both `verifications` and `evidence` are available for the same claim
2. Index correspondence is maintained (verifications[i] ↔ evidence[i])
3. Enrichment happens BEFORE judgment creation
4. Evidence flows naturally to pipeline worker with NLI data already attached

#### **2.6b Update Pipeline Worker to Map NLI Fields**

**File**: `backend/app/workers/pipeline.py`

**Location**: Lines 159-170 (Evidence creation in `save_check_results_sync`)

**Action**: Map NLI fields from enriched evidence to database model

**Note**: Evidence items already have NLI fields attached from judge stage (section 2.6a above). Just map them to database fields.

```python
# In save_check_results_sync function (around line 135-175):
for claim_data in claims_data:
    # ... existing claim creation ...

    # Get evidence (already enriched with NLI data from judge stage)
    evidence_list = claim_data.get("evidence", [])

    for ev_data in evidence_list:
        evidence = Evidence(
            claim_id=claim.id,
            source=ev_data.get("source", "Unknown"),
            url=ev_data.get("url", ""),
            title=ev_data.get("title", ""),
            snippet=ev_data.get("snippet", ev_data.get("text", "")),
            published_date=None,  # Parse if needed
            relevance_score=ev_data.get("relevance_score", 0.0),
            credibility_score=ev_data.get("credibility_score", 0.6),

            # Citation Precision (Phase 2)
            page_number=ev_data.get("metadata", {}).get("page_number") if ev_data.get("metadata") else None,
            context_before=ev_data.get("metadata", {}).get("context_before") if ev_data.get("metadata") else None,
            context_after=ev_data.get("metadata", {}).get("context_after") if ev_data.get("metadata") else None,

            # NLI Context (Phase 2 - already enriched in judge.py)
            nli_stance=ev_data.get("nli_stance"),
            nli_confidence=ev_data.get("nli_confidence"),
            nli_entailment=ev_data.get("nli_entailment"),
            nli_contradiction=ev_data.get("nli_contradiction"),
        )
        session.add(evidence)
```

**Data Flow Summary**:
1. `verify.py` → Creates verifications with NLI scores
2. `judge.py` → Enriches evidence with NLI scores (Section 2.6a)
3. `judge.py` → Returns judgment with enriched evidence
4. `pipeline.py` → Receives enriched evidence, maps to database (Section 2.6b)
5. Database → Stores evidence with NLI fields

#### **2.7 Update Frontend: Enhanced Evidence Cards with Direct Display**

**File**: `web/app/dashboard/check/[id]/components/claims-section.tsx`

**Location**: Lines 171-249 (Evidence card display - completely redesigned)

**Design Philosophy**: Show all context information directly when Evidence Sources expand - NO extra button needed.

```typescript
{/* Evidence List (Collapsible) */}
{isExpanded && (
  <div className="mt-4 space-y-3">
    {sortedEvidence.map((evidence) => (
      <div
        key={evidence.id}
        className="p-4 bg-slate-900/50 border border-slate-700 rounded-lg hover:border-slate-600 transition-colors"
      >
        {/* 1. STANCE BADGE (Top, Prominent) - NEW */}
        {evidence.nliStance && (
          <div className="mb-3">
            {evidence.nliStance === 'supporting' && (
              <div className="flex items-center gap-2">
                <span className="px-3 py-1 bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 rounded-full text-sm font-bold">
                  🟢 SUPPORTS CLAIM
                </span>
                <span className="text-xs text-emerald-400/70">
                  {Math.round((evidence.nliConfidence || 0) * 100)}% confident
                </span>
              </div>
            )}
            {evidence.nliStance === 'contradicting' && (
              <div className="flex items-center gap-2">
                <span className="px-3 py-1 bg-red-500/20 text-red-400 border border-red-500/30 rounded-full text-sm font-bold">
                  🔴 CONTRADICTS CLAIM
                </span>
                <span className="text-xs text-red-400/70">
                  {Math.round((evidence.nliConfidence || 0) * 100)}% confident
                </span>
              </div>
            )}
            {evidence.nliStance === 'neutral' && (
              <div className="flex items-center gap-2">
                <span className="px-3 py-1 bg-slate-500/20 text-slate-400 border border-slate-500/30 rounded-full text-sm font-bold">
                  ⚪ NEUTRAL
                </span>
                <span className="text-xs text-slate-400/70">
                  {Math.round((evidence.nliConfidence || 0) * 100)}% confident
                </span>
              </div>
            )}
          </div>
        )}

        {/* 2. FACT-CHECK BADGE (if applicable) */}
        {evidence.isFactcheck && evidence.factcheckPublisher && (
          <FactCheckBadge
            publisher={evidence.factcheckPublisher}
            rating={evidence.factcheckRating}
          />
        )}

        {/* 3. TITLE */}
        <div className="flex items-center gap-2 mb-2">
          <span className="text-sm font-medium text-white">
            {evidence.title}
          </span>
          <ExternalLink
            size={14}
            className="text-slate-400 hover:text-white transition-colors flex-shrink-0 cursor-pointer"
            onClick={() => window.open(evidence.url, '_blank', 'noopener,noreferrer')}
          />
        </div>

        {/* 4. CONTEXT SECTION (Grey Box) - NEW */}
        <div className="my-3 space-y-2">
          {/* Context Before (subtle, grey) */}
          {evidence.contextBefore && (
            <p className="text-xs text-slate-500 italic line-clamp-2">
              ...{evidence.contextBefore}
            </p>
          )}

          {/* Main Snippet (highlighted passage - BRAND ORANGE) */}
          <div className="p-3 bg-orange-500/10 border-l-4 border-[#f57a07] rounded">
            <p className="text-sm text-white leading-relaxed">
              {evidence.snippet}
            </p>
          </div>

          {/* Context After (subtle, grey) */}
          {evidence.contextAfter && (
            <p className="text-xs text-slate-500 italic line-clamp-2">
              {evidence.contextAfter}...
            </p>
          )}
        </div>

        {/* 5. REASONING (Why this supports/contradicts) - NEW */}
        {evidence.nliStance && evidence.nliStance !== 'neutral' && (
          <div className="p-3 bg-slate-800/50 border border-slate-700 rounded text-xs text-slate-300 mb-3">
            <span className="font-semibold text-slate-200">
              💬 Why this {evidence.nliStance === 'supporting' ? 'supports' : 'contradicts'}:
            </span>
            <p className="mt-1">
              {generateNliExplanation(evidence.nliStance, evidence.nliConfidence)}
            </p>
          </div>
        )}

        {/* 6. METADATA: Source · Date · Page · Credibility */}
        <div className="flex items-center gap-2 text-xs text-slate-500 flex-wrap">
          <span className="font-medium">{evidence.source}</span>

          {/* Page Number */}
          {evidence.pageNumber && (
            <>
              <span>·</span>
              <span className="text-blue-400" title="Page number in document">
                p. {evidence.pageNumber}
              </span>
            </>
          )}

          {evidence.parentCompany && (
            <>
              <span>·</span>
              <span title="Parent Company">{evidence.parentCompany}</span>
            </>
          )}

          <span>·</span>
          <span>{formatMonthYear(evidence.publishedDate || null)}</span>

          {/* Credibility Label */}
          {evidence.credibilityScore && (
            <>
              <span>·</span>
              <span className={`font-medium ${
                evidence.credibilityScore >= 0.9 ? 'text-emerald-400' :
                evidence.credibilityScore >= 0.8 ? 'text-blue-400' :
                evidence.credibilityScore >= 0.6 ? 'text-slate-400' :
                'text-amber-400'
              }`}>
                {evidence.credibilityScore >= 0.9 ? 'Expert Source' :
                 evidence.credibilityScore >= 0.8 ? 'Verified Source' :
                 evidence.credibilityScore >= 0.6 ? 'General Source' :
                 'Unverified Source'}
              </span>
            </>
          )}

          {evidence.temporalRelevanceScore !== undefined && (
            <>
              <span>·</span>
              <span title="Temporal Relevance" className="text-amber-400">
                Time-Relevant
              </span>
            </>
          )}
        </div>

        {/* 7. TECHNICAL DETAILS (Optional, Collapsible) - NEW */}
        {evidence.nliEntailment !== undefined && (
          <details className="mt-2">
            <summary className="text-xs text-slate-500 cursor-pointer hover:text-slate-400">
              Technical NLI Scores ▼
            </summary>
            <div className="mt-2 pl-3 space-y-1 text-xs text-slate-400">
              <div>Entailment: {((evidence.nliEntailment || 0) * 100).toFixed(1)}%</div>
              <div>Contradiction: {((evidence.nliContradiction || 0) * 100).toFixed(1)}%</div>
              <div>Neutral: {((1 - (evidence.nliEntailment || 0) - (evidence.nliContradiction || 0)) * 100).toFixed(1)}%</div>
            </div>
          </details>
        )}
      </div>
    ))}
  </div>
)}
```

**Helper Function** (add to component):

```typescript
// Generate simple explanation based on stance and confidence
function generateNliExplanation(stance: string, confidence?: number): string {
  const confidenceLevel = (confidence || 0) >= 0.8 ? 'strongly' :
                          (confidence || 0) >= 0.6 ? 'moderately' : 'weakly';

  if (stance === 'supporting') {
    return `This evidence ${confidenceLevel} confirms key aspects of the claim. The passage directly corroborates the claim's assertions.`;
  } else if (stance === 'contradicting') {
    return `This evidence ${confidenceLevel} disputes the claim. The passage contains information that conflicts with what the claim asserts.`;
  }
  return 'This evidence provides context but neither clearly supports nor contradicts the claim.';
}
```

#### **2.8 Update TypeScript Evidence Interface**

**File**: `web/app/dashboard/check/[id]/components/claims-section.tsx`

**Location**: Lines 40-62 (Evidence interface)

```typescript
interface Evidence {
  id: string;
  source: string;
  url: string;
  title: string;
  snippet: string;
  publishedDate?: string;
  relevanceScore: number;
  credibilityScore?: number;

  // Citation Precision (Phase 2)
  pageNumber?: number;
  contextBefore?: string;
  contextAfter?: string;

  // NLI Context Display (Phase 2 - NEW)
  nliStance?: 'supporting' | 'contradicting' | 'neutral';
  nliConfidence?: number;
  nliEntailment?: number;
  nliContradiction?: number;

  // Existing fields...
  isFactcheck?: boolean;
  factcheckPublisher?: string;
  factcheckRating?: string;
  parentCompany?: string;
  independenceFlag?: string;
  temporalRelevanceScore?: number;
  isTimeSensitive?: boolean;
}
```

**Key UX Decisions**:
1. **No extra button** - All context shown immediately when Evidence Sources expand
2. **Visual hierarchy** - Stance badge most prominent, metadata least prominent
3. **Highlighted passage** - Orange-bordered box (brand color #f57a07) draws eye to cited text
4. **Graceful degradation** - Old checks without NLI data still work (fields optional)
5. **Progressive disclosure** - Technical NLI scores hidden in collapsible details
6. **Brand consistency** - Orange accent matches Tru8's primary brand color throughout

### **Testing Strategy**

#### **Unit Tests**

**New File**: `backend/tests/unit/test_pdf_evidence.py`

```python
import pytest
from app.services.pdf_evidence import PDFEvidenceExtractor

@pytest.mark.asyncio
async def test_extract_from_pdf_with_page_numbers():
    extractor = PDFEvidenceExtractor()

    # Use a real government PDF (Khan Review mentioned in screenshot)
    url = "https://assets.publishing.service.gov.uk/media/65fdbfd265ca2ffef17da79c/The_Khan_review.pdf"
    claim = "social cohesion report recommendations"

    results = await extractor.extract_evidence_from_pdf(url, claim, max_results=3)

    assert len(results) > 0
    assert results[0]['page_number'] is not None
    assert results[0]['page_number'] > 0
    assert 'text' in results[0]
    assert len(results[0]['text']) > 50

@pytest.mark.asyncio
async def test_pdf_extractor_handles_non_pdf():
    extractor = PDFEvidenceExtractor()

    # Test with HTML URL (should fail gracefully)
    url = "https://bbc.co.uk/news/article"
    claim = "test claim"

    results = await extractor.extract_evidence_from_pdf(url, claim)

    assert len(results) == 0  # Should return empty, not crash
```

Run tests:
```bash
cd backend
pytest tests/unit/test_pdf_evidence.py -v
```

#### **Integration Testing**

**Test Case 1**: Submit article that cites Khan Review PDF
- **Expected**: Evidence shows "The Khan Review (p. 47)" with page number
- **Check**: Frontend displays "p. 47" in metadata
- **NEW**: Stance badge shows "🟢 SUPPORTS" or "🔴 CONTRADICTS"
- **NEW**: Context before/after visible, highlighted passage in orange-bordered box (brand color)

**Test Case 2**: Submit article with HTML sources only
- **Expected**: No page numbers shown (graceful degradation)
- **Check**: Existing behavior unchanged
- **NEW**: NLI stance still displayed (works for all source types)

**Test Case 3**: Check created before Phase 2 deployment
- **Expected**: Evidence cards work without nliStance fields
- **Check**: Graceful degradation - stance badges don't render, rest of card works

**Test Case 4**: Verify NLI stance accuracy
- **Expected**: Evidence marked "supporting" actually supports claim
- **Check**: Manually verify 10 random evidence items match their stance
- **Target**: >90% accuracy (NLI model threshold)

### **Success Metrics**

✅ **Phase 2 Complete When**:
1. PDF page extraction tests pass (Section 2.2-2.3)
2. Khan Review PDF shows page numbers in frontend (Section 2.7)
3. Database migration adds 7 new fields successfully (Section 2.5)
4. **Judge stage enriches evidence with NLI data correctly (Section 2.6a)** ⭐ NEW
5. **Database stores nli_stance, nli_confidence fields correctly (Section 2.6b)** ⭐ NEW
6. **Frontend displays stance badges for all evidence (Section 2.7)** ⭐ NEW
7. **Context before/after/reasoning visible without extra clicks (Section 2.7)** ⭐ NEW
8. Non-PDF sources work as before (no regression)
9. Old checks (without NLI data) still render correctly (graceful degradation)
10. **User verification time reduces by >70%** ⭐ NEW (measured via analytics)

---

## 📅 Phase 3: LLM-Powered Source Validation (Optional)

**Timeline**: 6-8 hours
**Priority**: MEDIUM (Future Enhancement)
**Effort**: High
**Impact**: HIGH (Most comprehensive solution)

### **Objectives**

1. Use LLM to judge source appropriateness for ambiguous cases
2. Provide contextual assessment of source quality
3. Lay groundwork for author-level credibility tracking
4. Handle edge cases not caught by heuristics

### **Implementation Details**

#### **3.1 Create LLM Source Judge**

**New File**: `backend/app/services/source_judge.py`

```python
"""
LLM-Powered Source Judge
Uses language model to assess source appropriateness for fact-checking
"""
import logging
import json
from typing import Dict, Any, List
import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)

class SourceJudge:
    """LLM-powered source quality assessment"""

    def __init__(self):
        self.openai_api_key = settings.OPENAI_API_KEY
        self.timeout = 15

        self.system_prompt = """You are an expert in evaluating source credibility for fact-checking.

Your task is to assess whether a source is APPROPRIATE for verifying factual claims.

INAPPROPRIATE sources (return "INAPPROPRIATE"):
- Student materials (revision guides, exam prep, study notes)
- Educational resources designed for learning, not authoritative reference
- Personal blogs, opinion pieces without editorial oversight
- Forums, comment sections, user-generated content
- Promotional materials, press releases, marketing content
- Secondary sources that merely summarize other sources

APPROPRIATE sources (return "APPROPRIATE"):
- News articles from established media outlets
- Government reports, official documents, statistics
- Academic peer-reviewed publications
- Expert statements, interviews with subject matter experts
- Primary source documents (laws, treaties, original research)
- Fact-check articles from recognized organizations (if addressing the same claim)

AMBIGUOUS cases (return "UNCERTAIN"):
- Educational materials from authoritative institutions (e.g., university publications)
- Think tank reports (consider political bias vs. research quality)
- Trade publications (industry-specific but may have bias)

Return JSON:
{
  "verdict": "APPROPRIATE" | "INAPPROPRIATE" | "UNCERTAIN",
  "confidence": 0.85,
  "reasoning": "One sentence explaining your assessment",
  "flags": ["flag1", "flag2"]
}

Flags to use:
- "educational_material": Student or teaching resources
- "opinion_content": Editorial, opinion, or commentary
- "user_generated": Forums, comments, wikis
- "promotional": Marketing or promotional content
- "secondary_source": Aggregates other sources without original reporting
- "questionable_authority": Unclear editorial oversight or expertise
- "potential_bias": Known political or commercial bias
"""

    async def judge_sources(
        self,
        evidence_list: List[Dict[str, Any]],
        claim: str
    ) -> List[Dict[str, Any]]:
        """
        Use LLM to judge source appropriateness.

        Only called for sources that pass heuristics but need deeper assessment.

        Args:
            evidence_list: Evidence items to judge
            claim: Original claim (for context)

        Returns:
            List of evidence with judgment metadata added
        """
        judged_evidence = []

        for evidence in evidence_list:
            # Check if already clearly appropriate (high credibility score)
            if evidence.get('credibility_score', 0) >= 0.9:
                # Skip LLM for obviously good sources (saves cost)
                evidence['source_judgment'] = {
                    'verdict': 'APPROPRIATE',
                    'confidence': 1.0,
                    'reasoning': 'High credibility domain',
                    'method': 'heuristic'
                }
                judged_evidence.append(evidence)
                continue

            # Use LLM for uncertain cases
            judgment = await self._judge_single_source(evidence, claim)
            evidence['source_judgment'] = judgment

            # Only keep APPROPRIATE or UNCERTAIN (with high confidence)
            if judgment['verdict'] == 'APPROPRIATE':
                judged_evidence.append(evidence)
            elif judgment['verdict'] == 'UNCERTAIN' and judgment['confidence'] < 0.7:
                # Keep uncertain sources if confidence is low (benefit of doubt)
                judged_evidence.append(evidence)
            else:
                logger.info(
                    f"LLM filtered source: {evidence.get('title')} - "
                    f"{judgment['verdict']} ({judgment['reasoning']})"
                )

        return judged_evidence

    async def _judge_single_source(
        self,
        evidence: Dict[str, Any],
        claim: str
    ) -> Dict[str, Any]:
        """Judge a single source using LLM"""
        try:
            user_prompt = f"""
Claim being fact-checked: "{claim}"

Source to evaluate:
- Title: {evidence.get('title', 'Unknown')}
- URL: {evidence.get('url', 'Unknown')}
- Publisher: {evidence.get('source', 'Unknown')}
- Snippet: {evidence.get('snippet', evidence.get('text', ''))[:300]}

Is this source APPROPRIATE for fact-checking the claim?
"""

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.openai_api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "gpt-4o-mini-2024-07-18",
                        "messages": [
                            {"role": "system", "content": self.system_prompt},
                            {"role": "user", "content": user_prompt}
                        ],
                        "max_tokens": 200,
                        "temperature": 0.1,  # Low temperature for consistency
                        "response_format": {"type": "json_object"}
                    }
                )

                if response.status_code == 200:
                    result = response.json()
                    judgment_json = json.loads(result["choices"][0]["message"]["content"])
                    judgment_json['method'] = 'llm'
                    return judgment_json
                else:
                    logger.error(f"OpenAI API error: {response.status_code}")
                    return self._fallback_judgment()

        except Exception as e:
            logger.error(f"LLM source judgment error: {e}")
            return self._fallback_judgment()

    def _fallback_judgment(self) -> Dict[str, Any]:
        """Fallback when LLM unavailable"""
        return {
            'verdict': 'UNCERTAIN',
            'confidence': 0.5,
            'reasoning': 'LLM judgment unavailable, defaulting to uncertain',
            'flags': [],
            'method': 'fallback'
        }

# Singleton
_source_judge_instance = None

def get_source_judge() -> SourceJudge:
    """Get singleton SourceJudge instance"""
    global _source_judge_instance
    if _source_judge_instance is None:
        _source_judge_instance = SourceJudge()
    return _source_judge_instance
```

#### **3.2 Integrate LLM Judge into Pipeline**

**File**: `backend/app/pipeline/retrieve.py`

**Location**: After source validation (after Phase 1 integration point)

```python
# Phase 1: Heuristic validation (fast, catches obvious cases)
if settings.ENABLE_SOURCE_VALIDATION:
    from app.utils.source_validator import get_source_validator
    validator = get_source_validator()
    evidence_list, validation_stats = validator.validate_sources(evidence_list)
    logger.info(f"Heuristic validation: {validation_stats['validated_count']} retained")

# Phase 3: LLM validation (optional, for ambiguous cases)
if settings.ENABLE_LLM_SOURCE_VALIDATION:
    from app.services.source_judge import get_source_judge
    judge = get_source_judge()
    evidence_list = await judge.judge_sources(evidence_list, claim.get("text", ""))
    logger.info(f"LLM validation: {len(evidence_list)} sources approved")
```

#### **3.3 Add Feature Flag**

**File**: `backend/app/core/config.py`

```python
# Phase 3 - LLM Source Validation (Optional, Expensive)
ENABLE_LLM_SOURCE_VALIDATION: bool = Field(False, env="ENABLE_LLM_SOURCE_VALIDATION")
```

#### **3.4 Store Source Judgments in Database**

**File**: `backend/app/models/check.py`

**Location**: Evidence model

```python
class Evidence(SQLModel, table=True):
    # ... existing fields ...

    # Source Quality Judgment (Phase 3)
    source_judgment: Optional[str] = Field(default=None, sa_column=Column(JSON), description="LLM source quality assessment")
```

**Migration**:
```bash
cd backend
alembic revision --autogenerate -m "add_source_judgment_field"
alembic upgrade head
```

#### **3.5 Display Judgment in Frontend (Optional)**

**File**: `web/app/dashboard/check/[id]/components/claims-section.tsx`

```typescript
{/* Show source quality badge if available */}
{evidence.sourceJudgment && evidence.sourceJudgment.verdict === 'APPROPRIATE' && (
  <span className="px-2 py-0.5 bg-emerald-500/20 text-emerald-400 text-xs rounded">
    Verified Source ✓
  </span>
)}
```

### **Testing Strategy**

#### **Unit Tests**

**File**: `backend/tests/unit/test_source_judge.py`

```python
import pytest
from app.services.source_judge import SourceJudge

@pytest.mark.asyncio
async def test_llm_filters_exam_guide():
    judge = SourceJudge()

    evidence = [{
        'title': 'Y13 Ethics Revision Guide',
        'url': 'https://school.edu/revision.pdf',
        'source': 'School Website',
        'snippet': 'Study guide for A-Level ethics exam...',
        'credibility_score': 0.6
    }]

    judged = await judge.judge_sources(evidence, "claim about ethics")

    # Should be filtered out
    assert len(judged) == 0 or judged[0]['source_judgment']['verdict'] == 'INAPPROPRIATE'

@pytest.mark.asyncio
async def test_llm_approves_bbc():
    judge = SourceJudge()

    evidence = [{
        'title': 'UK Policy Report',
        'url': 'https://bbc.co.uk/news/uk-123',
        'source': 'BBC',
        'snippet': 'Government announces new policy...',
        'credibility_score': 0.9
    }]

    judged = await judge.judge_sources(evidence, "policy claim")

    assert len(judged) == 1
    assert judged[0]['source_judgment']['verdict'] == 'APPROPRIATE'
```

### **Success Metrics**

✅ **Phase 3 Complete When**:
1. LLM source judge tests pass
2. Ambiguous sources correctly assessed
3. Cost per check remains <$0.05 (LLM calls optimized)
4. Judgments stored in database for transparency
5. Feature flag allows disabling for cost control

### **Cost Management**

LLM calls are expensive. Optimize by:
- Skip LLM for sources with credibility ≥ 0.9
- Skip LLM for sources already filtered by heuristics
- Use GPT-4o-mini (cheapest)
- Cache judgments by URL (Redis)

**Expected cost**: ~$0.01-0.02 per check (3-5 sources × $0.003 per call)

---

## 📊 Success Metrics & Monitoring

### **Key Performance Indicators**

#### **Source Quality Metrics**

Track via logging and monitoring dashboard:

```python
# In retrieve.py, log filtering stats:
logger.info(json.dumps({
    'event': 'source_filtering',
    'original_count': original_count,
    'heuristic_filtered': heuristic_filtered_count,
    'llm_filtered': llm_filtered_count,
    'threshold_filtered': threshold_filtered_count,
    'final_count': final_count,
    'filtered_sources': [
        {'url': url, 'reason': reason, 'credibility': score}
        for url, reason, score in filtered_sources
    ]
}))
```

**Metrics to Track**:
1. **Filtering Rate**: % of sources filtered at each stage
   - Target: 10-20% filtered (catching inappropriate sources without over-filtering)
2. **Credibility Distribution**: Average credibility score of retained sources
   - Target: Mean credibility ≥ 0.75
3. **Insufficient Evidence Rate**: % of checks with <3 sources after filtering
   - Target: <15% (filtering shouldn't starve verification)
4. **User Feedback**: User ratings of evidence quality
   - Target: >4.0/5.0 stars

#### **Citation Precision Metrics**

1. **PDF Page Number Coverage**: % of PDF evidence with page numbers
   - Target: >80% of PDFs
2. **Citation Click-Through Rate**: % of users clicking evidence links
   - Hypothesis: Should increase with page numbers (easier verification)
3. **User Verification Time**: Time spent viewing evidence
   - Hypothesis: Should decrease with page numbers (find content faster)

### **Monitoring Dashboard**

Create dashboard queries:

```sql
-- Source filtering effectiveness
SELECT
    DATE(created_at) as date,
    COUNT(*) as total_checks,
    AVG(claims_count) as avg_claims_per_check,
    AVG(evidence_count) as avg_evidence_per_claim,
    AVG(evidence_credibility) as avg_credibility
FROM checks
WHERE status = 'completed'
GROUP BY date
ORDER BY date DESC;

-- Page number coverage
SELECT
    COUNT(*) as total_evidence,
    SUM(CASE WHEN page_number IS NOT NULL THEN 1 ELSE 0 END) as evidence_with_pages,
    ROUND(100.0 * SUM(CASE WHEN page_number IS NOT NULL THEN 1 ELSE 0 END) / COUNT(*), 2) as page_coverage_pct
FROM evidence
WHERE url LIKE '%.pdf';

-- Filtered sources breakdown
SELECT
    filtered_reason,
    COUNT(*) as count
FROM source_filtering_log
GROUP BY filtered_reason
ORDER BY count DESC;
```

---

## 🔄 Rollback Plans

### **Phase 1 Rollback**

If heuristic filtering causes issues:

```bash
# Option 1: Disable via env variable
ENABLE_SOURCE_VALIDATION=False

# Option 2: Lower threshold temporarily
SOURCE_CREDIBILITY_THRESHOLD=0.55

# Option 3: Code rollback
git revert <commit-hash>
```

**Rollback Trigger**: If "Insufficient Evidence" verdicts increase >20%

### **Phase 2 Rollback**

If PDF extraction causes timeouts:

```bash
# Disable PDF enhancement
# In evidence.py, comment out PDF detection:
# if search_result.url.lower().endswith('.pdf'):
#     # ... PDF extraction code

# Or add timeout safeguard
PDF_EXTRACTION_TIMEOUT = 10  # seconds
```

**Rollback Trigger**: If pipeline latency exceeds 15 seconds

### **Phase 3 Rollback**

If LLM costs too high:

```bash
# Disable LLM validation immediately
ENABLE_LLM_SOURCE_VALIDATION=False
```

**Rollback Trigger**: If cost per check exceeds $0.05

---

## 📁 File Structure Summary

### **New Files Created**

```
backend/
├── app/
│   ├── services/
│   │   ├── pdf_evidence.py          # Phase 2 - PDF extraction with page numbers
│   │   └── source_judge.py          # Phase 3 - LLM source validation
│   └── utils/
│       └── source_validator.py      # Phase 1 - Heuristic content-type filtering
├── tests/
│   └── unit/
│       ├── test_source_validator.py # Phase 1 tests
│       ├── test_pdf_evidence.py     # Phase 2 tests
│       └── test_source_judge.py     # Phase 3 tests
└── alembic/
    └── versions/
        ├── xxx_add_citation_precision_fields.py  # Phase 2 migration
        └── xxx_add_source_judgment_field.py      # Phase 3 migration

SOURCE_QUALITY_CONTROL_PLAN.md        # This document
```

### **Modified Files**

```
backend/
├── app/
│   ├── core/
│   │   └── config.py                # Add feature flags
│   ├── models/
│   │   └── check.py                 # Add 7 fields (page_number, nli_stance, etc.)
│   ├── pipeline/
│   │   ├── retrieve.py              # Integrate validators, raise threshold
│   │   └── judge.py                 # ⭐ NEW: Enrich evidence with NLI data (Section 2.6a)
│   ├── services/
│   │   └── evidence.py              # Add PDF detection, metadata handling
│   └── workers/
│       └── pipeline.py              # Map NLI fields to database (Section 2.6b)
└── requirements.txt                 # Add PyPDF2, pdfplumber

web/
└── app/
    └── dashboard/
        └── check/[id]/
            └── components/
                └── claims-section.tsx  # Display page numbers, stance badges, context
```

---

## 🚀 Implementation Timeline

### **Week 1: Phase 1 (Quick Wins)**

**Day 1-2** (4 hours):
- ✅ Create `source_validator.py` with heuristic patterns
- ✅ Write unit tests (test_source_validator.py)
- ✅ Integrate into retrieve.py
- ✅ Add feature flag to config.py

**Day 3** (2 hours):
- ✅ Raise credibility threshold to 0.65
- ✅ Test on real articles (check filtering effectiveness)
- ✅ Monitor logs for filtering decisions
- ✅ Adjust patterns based on results

**Deliverable**: Exam guides and student materials filtered out immediately.

---

### **Week 2: Phase 2 (Citation Precision & NLI Context Display)**

**Day 1-2** (6 hours):
- ✅ Install PyPDF2/pdfplumber (Section 2.1)
- ✅ Create `pdf_evidence.py` with page extraction (Section 2.2)
- ✅ Write unit tests (test_pdf_evidence.py)
- ✅ Integrate PDF detection into evidence.py (Section 2.3)
- ✅ Update EvidenceSnippet class with metadata parameter (Section 2.4)

**Day 3** (4 hours):
- ✅ Create database migration adding 7 fields (3 citation + 4 NLI) (Section 2.5)
- ✅ **Enrich evidence with NLI data in judge.py (Section 2.6a)** ⭐ NEW
- ✅ Update pipeline worker to map NLI fields (Section 2.6b)
- ✅ Run migration: `alembic upgrade head`

**Day 4** (3 hours):
- ✅ Update frontend TypeScript Evidence interface (Section 2.8)
- ✅ Implement enhanced evidence cards with stance badges (Section 2.7)
- ✅ Add NLI explanation helper function
- ✅ Test with Khan Review PDF

**Day 5** (2 hours):
- ✅ Test on multiple PDF sources
- ✅ Verify page numbers display correctly
- ✅ **Verify NLI stance badges appear correctly** ⭐ NEW
- ✅ **Test graceful degradation (old checks without NLI data)** ⭐ NEW
- ✅ Monitor PDF extraction performance

**Deliverable**:
- PDF citations show page numbers (e.g., "Khan Review (p. 47)")
- **Evidence cards display stance badges (🟢 SUPPORTS / 🔴 CONTRADICTS)** ⭐ NEW
- **Context and reasoning visible without extra clicks** ⭐ NEW

---

### **Week 3: Phase 3 (LLM Validation)** - OPTIONAL

**Day 1-2** (6 hours):
- ⚠️ Create `source_judge.py` with LLM integration
- ⚠️ Write unit tests (test_source_judge.py)
- ⚠️ Integrate into retrieve.py (after heuristics)
- ⚠️ Add feature flag (disabled by default)

**Day 3** (3 hours):
- ⚠️ Create database migration (add source_judgment field)
- ⚠️ Test on ambiguous sources
- ⚠️ Monitor LLM costs
- ⚠️ Optimize caching to reduce calls

**Deliverable**: Ambiguous sources assessed by LLM (optional, cost-controlled)

---

## 💰 Cost Analysis

### **Phase 1: Heuristic Filtering**

**Cost**: $0 (regex pattern matching, no API calls)
**Performance Impact**: Negligible (<1ms per source)

### **Phase 2: PDF Page Extraction**

**Cost**: $0 (local PDF processing)
**Performance Impact**: +2-5 seconds per PDF (acceptable for improved UX)
**Mitigation**: Cache PDF extractions, timeout after 10s

### **Phase 3: LLM Source Validation**

**Cost per check**: ~$0.01-0.02
- 3-5 sources per claim × 5 claims = 15-25 sources
- Skip high-credibility sources (0.9+) → ~5-10 LLM calls
- GPT-4o-mini: $0.0015 per call
- **Total**: $0.0075-0.015 per check

**Annual cost (10,000 checks)**: ~$100-150

**Optimization strategies**:
1. Cache judgments by URL (99% of URLs repeat)
2. Skip LLM for sources already filtered by heuristics
3. Use feature flag to disable if budget constrained

---

## 🧪 Testing Checklist

### **Phase 1 Testing**

- [ ] Unit tests pass (test_source_validator.py)
- [ ] Exam guide (king-james.co.uk) filtered out
- [ ] BBC news still appears
- [ ] GOV.UK education pages still appear
- [ ] Logs show filtering reasons clearly
- [ ] Feature flag toggle works

### **Phase 2 Testing**

**Citation Precision (Sections 2.1-2.4):**
- [ ] Unit tests pass (test_pdf_evidence.py)
- [ ] Khan Review PDF shows page numbers
- [ ] Page number displays in frontend
- [ ] Non-PDF sources work as before
- [ ] PDF extraction timeouts handled gracefully

**NLI Context Display (Sections 2.5-2.8):**
- [ ] Database migration adds 7 fields successfully (Section 2.5)
- [ ] **Judge stage enriches evidence with NLI data (Section 2.6a)** ⭐ NEW
- [ ] **Pipeline worker stores NLI fields correctly (Section 2.6b)** ⭐ NEW
- [ ] **Stance badges display correctly (🟢/🔴/⚪) (Section 2.7)** ⭐ NEW
- [ ] **Context before/after visible without extra clicks (Section 2.7)** ⭐ NEW
- [ ] **NLI explanation text generates appropriately (Section 2.7)** ⭐ NEW
- [ ] **TypeScript interface includes new fields (Section 2.8)** ⭐ NEW
- [ ] **Old checks without NLI data render gracefully** ⭐ NEW
- [ ] **Verify index correspondence (verifications[i] ↔ evidence[i])** ⭐ NEW

### **Phase 3 Testing** (if implemented)

- [ ] Unit tests pass (test_source_judge.py)
- [ ] LLM correctly identifies exam guides as inappropriate
- [ ] LLM approves BBC, Reuters, GOV.UK
- [ ] Costs remain under $0.05 per check
- [ ] Feature flag disables LLM calls
- [ ] Fallback works when OpenAI unavailable

---

## 📚 Documentation Updates

### **User-Facing Documentation**

**Update**: `docs/how-it-works.md`

Add section:
```markdown
## Evidence Quality Control

Tru8 uses multiple layers to ensure evidence quality:

1. **Domain Credibility**: 214+ domains rated across 15 tiers
2. **Content-Type Filtering**: Automatically excludes student materials, exam guides
3. **Minimum Threshold**: Only sources with ≥0.65 credibility used
4. **Citation Precision**: PDF sources include page numbers for easy verification

[View our credibility framework →]
```

### **Developer Documentation**

**Update**: `docs/pipeline-architecture.md`

Add flowchart:
```
Evidence Retrieval
      ↓
Heuristic Filter (Phase 1)
  - Student materials ❌
  - Exam guides ❌
  - User-generated ❌
      ↓
Credibility Threshold (≥0.65)
  - General sources ❌
  - Unverified ❌
      ↓
LLM Validation (Phase 3, Optional)
  - Ambiguous cases reviewed
      ↓
NLI Verification
```

---

## 🎯 Success Criteria

### **Phase 1 Success**
✅ Exam guides no longer appear as evidence
✅ Filtering rate: 10-20% of sources
✅ No increase in "Insufficient Evidence" verdicts (>20%)
✅ Mean credibility score: ≥0.75

### **Phase 2 Success**
✅ 80%+ of PDF evidence shows page numbers
✅ User verification time decreases
✅ PDF extraction completes in <10s per document
✅ No performance regression on HTML sources

### **Phase 3 Success** (if implemented)
✅ LLM correctly filters ambiguous sources
✅ Cost per check: <$0.05
✅ Cache hit rate: >90% for repeated URLs
✅ Feature flag allows disabling for cost control

---

## 🔮 Future Enhancements

### **Post-MVP Improvements**

**Author-Level Credibility** (mentioned by user):
- Track individual journalist/author credibility
- Consider author's previous fact-check accuracy
- Weight evidence by author reputation
- Database schema:
  ```sql
  CREATE TABLE authors (
    id UUID PRIMARY KEY,
    name TEXT,
    credibility_score FLOAT,
    track_record JSON,
    publications TEXT[]
  );
  ```

**Enhanced Citation Formatting**:
- Full Oxford-style references
- Clickable page anchors (PDF.js integration)
- "Jump to page" functionality
- Export citations in BibTeX format

**Dynamic Source Scoring**:
- Real-time credibility updates based on retractions
- Community feedback on source quality
- Automated bias detection
- Cross-referencing with fact-check verdicts

---

## 📞 Support & Questions

**Implementation Questions**: Review this document, check existing codebase
**Testing Issues**: Run unit tests, check logs for filtering decisions
**Performance Problems**: Monitor pipeline latency, check PDF extraction timeouts
**Cost Concerns**: Disable Phase 3 LLM validation, use heuristics only

---

## ✅ Approval & Sign-Off

**Plan Approved By**: _____________
**Start Date**: _____________
**Target Completion**: Phase 1: 3 hours, Phase 2: 1 week, Phase 3: Optional

**Risk Assessment**: LOW (feature flags allow rollback, phases are independent)
**User Impact**: HIGH (significantly improves evidence quality)
**Technical Complexity**: MEDIUM (well-scoped, clear integration points)

---

## 📝 Plan Revisions

### **Revision 1.1 - Corrected NLI Data Flow (October 29, 2025)**

**Issue Identified**: Original Section 2.6 showed enriching evidence with NLI data in `pipeline.py` save stage, but verification data is not available at that point in the pipeline.

**Root Cause Analysis**:
- `verify.py` returns `verifications_by_claim` (has NLI scores)
- `judge.py` receives verifications and evidence as SEPARATE parameters
- `JudgmentResult.to_dict()` only returns evidence (without NLI fields)
- `pipeline.py` receives `claim_data["evidence"]` without NLI data
- Attempting `claim_data.get("verifications")` returns empty list

**Corrected Approach**:
- **Split Section 2.6 into 2.6a and 2.6b**
  - **2.6a**: Enrich evidence in `judge.py` where both lists are available
  - **2.6b**: Pipeline worker simply maps already-enriched fields
- **Location**: `judge.py` line 525-541 in `judge_single_claim()` function
- **Timing**: Enrichment happens BEFORE `judgment.to_dict()` is called
- **Result**: Evidence items flow to pipeline worker with NLI data already attached

**Key Improvement**: Index correspondence (verifications[i] ↔ evidence[i]) is guaranteed at judge stage, making enrichment safe and straightforward.

**Files Updated**:
- Section 2.6 → Split into 2.6a (judge.py enrichment) and 2.6b (pipeline.py mapping)
- Success Metrics → Added references to 2.6a and 2.6b
- Implementation Timeline → Updated Day 3 tasks with corrected approach
- Modified Files → Added judge.py to list
- Testing Checklist → Split Phase 2 into Citation Precision and NLI Context Display sections

---

**Document Version**: 1.1 (Revised)
**Last Updated**: October 29, 2025
**Status**: Ready for Implementation
