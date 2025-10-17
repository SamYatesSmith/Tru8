# 🧭 Tru8 Credibility System Enhancement Plan

**Version:** 1.0
**Date:** 2025-10-16
**Status:** Ready for Review
**Priority:** CRITICAL - Foundation for Product Quality

---

## 🎯 Executive Summary

**Problem:** Current credibility system is vulnerable to misinformation validation:
- All unmatched sources default to 60% credibility
- No fact-check integration
- No source independence checking
- No blacklist/risk flagging
- Single low-quality source can validate claims
- No abstention when evidence is weak

**Risk:** If Tru8 validates propaganda or misinformation that ranks highly in search results, the product fails its core mission.

**Solution:** Implement a 9-layer "closed credibility loop" that ensures:
1. Evidence quality through multi-factor scoring
2. Source independence through ownership + duplicate detection
3. Authoritative prioritization via fact-checks + diverse retrieval
4. Transparent reasoning users can audit
5. Appropriate abstention when evidence is insufficient

**Impact:** Transforms Tru8 from "search aggregator" into "bulletproof credibility engine"

---

## 📊 Current System Analysis

### Pipeline Architecture (5 Stages)
```
Ingest → Extract → Retrieve → Verify → Judge
```

**File:** `backend/app/workers/pipeline.py:147-311`

### Critical Vulnerabilities Identified

#### 1. Default 60% Credibility
**File:** `backend/app/models/check.py:49`
```python
credibility_score: float = Field(default=0.6, ge=0, le=1)  # ALL sources get 60%
```

#### 2. Narrow Pattern Matching
**File:** `backend/app/pipeline/retrieve.py:194-219`
- Only recognizes 3-4 news outlets as tier1
- Doesn't recognize Wikipedia, official sites
- 99% of sources fall through to 'general' = 0.6

**Test Results:**
```
pariscityvision.com → 0.6 (general)
toureiffel.paris → 0.6 (general) [Official Eiffel Tower site!]
wikipedia.org → 0.6 (general) [Should be 0.85+]
```

#### 3. No Minimum Source Requirements
**File:** `backend/app/pipeline/judge.py:270-309`
```python
def _fallback_judgment(self, verification_signals):
    supporting = signals.get('supporting_count', 0)  # Could be 1!
    contradicting = signals.get('contradicting_count', 0)

    if supporting > contradicting + 1:  # 1 > 1 = FALSE, but still problematic
        verdict = "supported"
```

**Risk:** Single source with 60% credibility can influence verdict

#### 4. No Fact-Check Integration
- No IFCN signatory checking
- No Google Fact Check Explorer API
- Reinventing the wheel on already-verified claims

#### 5. Search Popularity Bias
**File:** `backend/app/services/search.py:52-90`
- Pure Brave Search results (popularity-ranked)
- No domain filtering for authoritative sources
- No diversity requirements

#### 6. No Source Independence
- No ownership database
- No duplicate content detection
- 3 outlets owned by same company = "3 independent sources"

---

## 🏗️ Comprehensive Solution: 9-Layer Credibility Loop

### Architecture Overview
```
CLAIM RECEIVED
    ↓
[1] FACT-CHECK LOOKUP (Priority Search)
    ↓
[2] DIVERSE EVIDENCE RETRIEVAL (Gov/Academic/News)
    ↓
[3] SOURCE REPUTATION CHECK (Blacklist/Risk Flags)
    ↓
[4] SOURCE INDEPENDENCE ANALYSIS (Ownership/Duplicates)
    ↓
[5] PAGE-LEVEL QUALITY SCORING (URL/Title/Content)
    ↓
[6] SEMANTIC CONTENT ANALYSIS (Citations/Hedging/Sensationalism)
    ↓
[7] CREDIBILITY AGGREGATION (Multi-factor Weighting)
    ↓
[8] CONSENSUS ANALYSIS (Minimum Requirements)
    ↓
[9] VERDICT DETERMINATION (Nuanced/Transparent/Abstention)
    ↓
DELIVER WITH FULL TRACEABILITY
```

---

## 📋 Detailed Implementation Plan

---

## AREA 1: Default Credibility & Abstention
**"Never force a verdict when the evidence is weak."**

### Current Problem
- Always returns a verdict (supported/contradicted/uncertain)
- No minimum source requirements
- No credibility threshold requirements
- Single 60% source can influence verdict

### Solution: Abstention Logic

#### Changes Required

**1. Database Schema**
```python
# backend/app/models/check.py
class Check(SQLModel, table=True):
    verdict: Optional[str] = Field(
        default=None,
        sa_column=Column(
            Enum(
                "supported",
                "contradicted",
                "uncertain",
                "insufficient_evidence",  # NEW
                "conflicting_expert_opinion",  # NEW
                "needs_primary_source",  # NEW
                "outdated_claim",  # NEW
                "lacks_context",  # NEW
                name="verdict_enum"
            )
        )
    )
    abstention_reason: Optional[str] = None  # NEW
    min_requirements_met: bool = Field(default=False)  # NEW
```

**2. Abstention Logic**
```python
# backend/app/pipeline/judge.py - INSERT before line 270

MIN_SOURCES_FOR_VERDICT = 3
MIN_HIGH_CREDIBILITY_SOURCES = 1  # At least one tier1+ source
MIN_CREDIBILITY_THRESHOLD = 0.75
MIN_CONSENSUS_STRENGTH = 0.65

def _should_abstain(self, verification_signals: Dict[str, Any]) -> tuple[bool, Optional[str]]:
    """
    Determine if we should abstain from verdict
    Returns (should_abstain: bool, reason: str)
    """
    total_sources = verification_signals.get('total_sources', 0)
    high_cred_sources = verification_signals.get('high_credibility_count', 0)
    max_credibility = verification_signals.get('max_credibility_score', 0)
    consensus_strength = verification_signals.get('consensus_strength', 0)

    # Check 1: Too few sources
    if total_sources < MIN_SOURCES_FOR_VERDICT:
        return (True, f"Insufficient sources: Found {total_sources}, need {MIN_SOURCES_FOR_VERDICT}")

    # Check 2: No authoritative sources
    if high_cred_sources == 0 or max_credibility < MIN_CREDIBILITY_THRESHOLD:
        return (True, f"No authoritative sources found (max credibility: {max_credibility:.0%})")

    # Check 3: Weak consensus
    if consensus_strength < MIN_CONSENSUS_STRENGTH:
        return (True, f"Conflicting evidence: consensus strength only {consensus_strength:.0%}")

    # Check 4: Conflicting high-credibility sources
    high_cred_supporting = verification_signals.get('high_cred_supporting', 0)
    high_cred_contradicting = verification_signals.get('high_cred_contradicting', 0)
    if high_cred_supporting > 0 and high_cred_contradicting > 0:
        return (True, "Authoritative sources disagree - expert opinion is divided")

    return (False, None)

def _fallback_judgment(self, verification_signals: Dict[str, Any]) -> Dict[str, Any]:
    """Enhanced fallback with abstention"""

    # Check if we should abstain
    should_abstain, abstention_reason = self._should_abstain(verification_signals)

    if should_abstain:
        return {
            "verdict": "insufficient_evidence",
            "confidence": 0,
            "reasoning": abstention_reason,
            "key_evidence_urls": [],
            "limitations": abstention_reason
        }

    # Proceed with existing logic but with credibility weighting
    signals = verification_signals

    # WEIGHTED voting (not simple count)
    supporting_weight = signals.get('supporting_credibility_sum', 0)
    contradicting_weight = signals.get('contradicting_credibility_sum', 0)

    if supporting_weight > contradicting_weight * 1.5:
        verdict = "supported"
        confidence = min(90, 60 + int((supporting_weight - contradicting_weight) * 20))
    elif contradicting_weight > supporting_weight * 1.5:
        verdict = "contradicted"
        confidence = min(90, 60 + int((contradicting_weight - supporting_weight) * 20))
    else:
        verdict = "uncertain"
        confidence = 50

    return {
        "verdict": verdict,
        "confidence": confidence,
        "reasoning": self._generate_reasoning(signals),
        "key_evidence_urls": signals.get('top_evidence_urls', []),
        "limitations": None
    }
```

**3. Update Verify Stage**
```python
# backend/app/pipeline/verify.py - Add to verification_signals calculation

def verify_claims(self, claims: List[Claim]) -> Dict[str, Any]:
    # ... existing code ...

    verification_signals = {
        'total_sources': len(all_evidence),
        'supporting_count': supporting_count,
        'contradicting_count': contradicting_count,
        'neutral_count': neutral_count,

        # NEW: Credibility-weighted metrics
        'supporting_credibility_sum': sum(e.credibility_score for e in all_evidence if e.stance == 'supporting'),
        'contradicting_credibility_sum': sum(e.credibility_score for e in all_evidence if e.stance == 'contradicting'),
        'high_credibility_count': sum(1 for e in all_evidence if e.credibility_score >= 0.75),
        'high_cred_supporting': sum(1 for e in all_evidence if e.credibility_score >= 0.75 and e.stance == 'supporting'),
        'high_cred_contradicting': sum(1 for e in all_evidence if e.credibility_score >= 0.75 and e.stance == 'contradicting'),
        'max_credibility_score': max((e.credibility_score for e in all_evidence), default=0),
        'consensus_strength': self._calculate_consensus_strength(all_evidence),
    }

    return verification_signals

def _calculate_consensus_strength(self, evidence: List[Evidence]) -> float:
    """Calculate how strongly evidence agrees (0-1)"""
    if not evidence:
        return 0.0

    total_weight = sum(e.credibility_score for e in evidence)
    if total_weight == 0:
        return 0.0

    supporting_weight = sum(e.credibility_score for e in evidence if e.stance == 'supporting')
    contradicting_weight = sum(e.credibility_score for e in evidence if e.stance == 'contradicting')

    max_weight = max(supporting_weight, contradicting_weight)
    return max_weight / total_weight
```

**Files Modified:**
- `backend/app/models/check.py` (lines 40-60)
- `backend/app/pipeline/judge.py` (lines 270-309)
- `backend/app/pipeline/verify.py` (add new methods)

**Migration Required:** Yes - `alembic revision` for verdict enum expansion

**Testing:**
- Test with 0, 1, 2, 3 sources
- Test with all low-credibility sources
- Test with conflicting high-credibility sources
- Verify abstention reasons are clear

---

## AREA 2: Source Independence
**"Detect duplicate or shared-source content so echoes aren't treated as consensus."**

### Current Problem
- No ownership tracking
- No duplicate content detection
- DailyMail + Metro + ThisIsMoney (all DMGT) = "3 independent sources"

### Solution: Ownership Database + Content Similarity

#### Changes Required

**1. Database Schema**
```python
# backend/app/models/check.py
class Evidence(SQLModel, table=True):
    # ... existing fields ...

    # NEW: Independence tracking
    parent_company: Optional[str] = None
    independence_flag: Optional[str] = None  # 'independent', 'shared_ownership', 'duplicate_content'
    content_similarity_score: Optional[float] = None  # Similarity to other evidence (0-1)
    ownership_group_size: int = Field(default=1)  # How many sources share same owner
```

**2. Ownership Database**
```python
# backend/app/data/ownership_database.json (NEW FILE)
{
  "dmgt": {
    "name": "Daily Mail and General Trust",
    "domains": [
      "dailymail.co.uk",
      "metro.co.uk",
      "thisismoney.co.uk",
      "mailonsunday.co.uk"
    ]
  },
  "news_corp": {
    "name": "News Corp",
    "domains": [
      "thesun.co.uk",
      "thetimes.co.uk",
      "nypost.com",
      "wsj.com"
    ]
  },
  "reach_plc": {
    "name": "Reach plc",
    "domains": [
      "mirror.co.uk",
      "express.co.uk",
      "dailystar.co.uk",
      "liverpoolecho.co.uk",
      "manchestereveningnews.co.uk"
    ]
  },
  "bbc": {
    "name": "BBC (Public)",
    "domains": ["bbc.co.uk", "bbc.com"]
  },
  "guardian_media": {
    "name": "Guardian Media Group",
    "domains": ["theguardian.com", "observer.co.uk"]
  }
  // ... expand to top 100 media companies
}
```

**3. Independence Checker Service**
```python
# backend/app/services/source_independence.py (NEW FILE)

from typing import List, Dict, Optional
import json
import tldextract
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

class SourceIndependenceChecker:
    def __init__(self):
        # Load ownership database
        with open('backend/app/data/ownership_database.json', 'r') as f:
            self.ownership_data = json.load(f)

        # Build reverse lookup: domain -> parent company
        self.domain_to_company = {}
        for company_id, data in self.ownership_data.items():
            for domain in data['domains']:
                self.domain_to_company[domain] = data['name']

        # Lightweight embedding model for content similarity
        self.model = SentenceTransformer('all-MiniLM-L6-v2')  # 80MB model

        # Thresholds
        self.DUPLICATE_CONTENT_THRESHOLD = 0.85
        self.SIMILAR_CONTENT_THRESHOLD = 0.70

    def check_independence(self, evidence_list: List[Evidence]) -> List[Evidence]:
        """
        Analyze source independence and deduplicate
        Returns enhanced evidence list with independence flags
        """
        if len(evidence_list) <= 1:
            return evidence_list

        # Step 1: Check ownership
        self._flag_shared_ownership(evidence_list)

        # Step 2: Check content similarity
        self._flag_duplicate_content(evidence_list)

        # Step 3: Apply credibility penalties
        self._apply_independence_penalties(evidence_list)

        # Step 4: Deduplicate (keep best from each cluster)
        deduplicated = self._deduplicate_evidence(evidence_list)

        return deduplicated

    def _flag_shared_ownership(self, evidence_list: List[Evidence]) -> None:
        """Flag sources with shared ownership"""
        # Group by parent company
        ownership_groups = {}

        for evidence in evidence_list:
            domain = tldextract.extract(evidence.url).registered_domain
            parent = self.domain_to_company.get(domain, 'independent')

            if parent not in ownership_groups:
                ownership_groups[parent] = []
            ownership_groups[parent].append(evidence)

            evidence.parent_company = parent

        # Flag sources in groups > 1
        for parent, group in ownership_groups.items():
            if len(group) > 1 and parent != 'independent':
                for evidence in group:
                    evidence.independence_flag = 'shared_ownership'
                    evidence.ownership_group_size = len(group)

    def _flag_duplicate_content(self, evidence_list: List[Evidence]) -> None:
        """Detect duplicate/similar content using embeddings"""
        # Generate embeddings for all snippets
        texts = [e.snippet for e in evidence_list]
        embeddings = self.model.encode(texts)

        # Calculate similarity matrix
        similarity_matrix = cosine_similarity(embeddings)

        # Flag duplicates
        for i, evidence in enumerate(evidence_list):
            for j in range(i + 1, len(evidence_list)):
                similarity = similarity_matrix[i][j]

                if similarity >= self.DUPLICATE_CONTENT_THRESHOLD:
                    # Exact duplicate - flag lower credibility source
                    if evidence_list[j].credibility_score < evidence.credibility_score:
                        evidence_list[j].independence_flag = 'duplicate_content'
                        evidence_list[j].content_similarity_score = similarity
                    else:
                        evidence.independence_flag = 'duplicate_content'
                        evidence.content_similarity_score = similarity

                elif similarity >= self.SIMILAR_CONTENT_THRESHOLD:
                    # Similar content - store similarity score
                    evidence.content_similarity_score = max(
                        evidence.content_similarity_score or 0,
                        similarity
                    )

    def _apply_independence_penalties(self, evidence_list: List[Evidence]) -> None:
        """Reduce credibility scores based on independence flags"""
        for evidence in evidence_list:
            if evidence.independence_flag == 'duplicate_content':
                # Heavy penalty - this is just an echo
                evidence.credibility_score *= 0.3

            elif evidence.independence_flag == 'shared_ownership':
                # Moderate penalty - reduces from 3 sources to ~1.5 effective sources
                penalty = 0.6 + (0.2 / evidence.ownership_group_size)
                evidence.credibility_score *= penalty

            elif evidence.content_similarity_score and evidence.content_similarity_score >= 0.70:
                # Light penalty for similar content
                penalty = 1.0 - ((evidence.content_similarity_score - 0.70) * 0.5)
                evidence.credibility_score *= penalty

    def _deduplicate_evidence(self, evidence_list: List[Evidence]) -> List[Evidence]:
        """
        Remove duplicate content, keep best from each ownership group
        """
        # Remove exact duplicates
        unique_evidence = [
            e for e in evidence_list
            if e.independence_flag != 'duplicate_content'
        ]

        # For shared ownership groups, keep top 2 per group
        ownership_groups = {}
        for evidence in unique_evidence:
            parent = evidence.parent_company or 'independent'
            if parent not in ownership_groups:
                ownership_groups[parent] = []
            ownership_groups[parent].append(evidence)

        final_evidence = []
        for parent, group in ownership_groups.items():
            # Sort by credibility, take top 2 per ownership group
            sorted_group = sorted(group, key=lambda e: e.credibility_score, reverse=True)
            if parent == 'independent':
                final_evidence.extend(sorted_group)  # Keep all independent sources
            else:
                final_evidence.extend(sorted_group[:2])  # Max 2 per company

        return final_evidence
```

**4. Integration Point**
```python
# backend/app/pipeline/retrieve.py - Insert after line 161

from app.services.source_independence import SourceIndependenceChecker

class EvidenceRetriever:
    def __init__(self):
        # ... existing code ...
        self.independence_checker = SourceIndependenceChecker()

    async def retrieve_evidence(self, claims: List[Claim]) -> List[Evidence]:
        # ... existing retrieval logic ...

        # NEW: Check independence and deduplicate
        all_evidence = self.independence_checker.check_independence(all_evidence)

        return all_evidence
```

**Files Created:**
- `backend/app/data/ownership_database.json`
- `backend/app/services/source_independence.py`

**Files Modified:**
- `backend/app/models/check.py` (new fields)
- `backend/app/pipeline/retrieve.py` (integration)

**Dependencies Added:**
```bash
# requirements.txt
sentence-transformers==2.2.2  # Lightweight embedding model
scikit-learn==1.3.0  # For cosine similarity
```

**Testing:**
- Test with 3 sources from same owner (should reduce to 2 effective)
- Test with copy-pasted content (should deduplicate)
- Test with independent sources (should keep all)
- Verify credibility penalties are applied correctly

---

## AREA 3: Page-Level Quality vs Domain Reputation
**"Rate the actual article, not just the publisher."**

### Current Problem
- Domain-only scoring: `bbc.co.uk/gossip` = `bbc.co.uk/news` = 0.9
- No article-level analysis

### Solution: Multi-Signal Page Quality Analysis

#### Changes Required

**1. Database Schema**
```python
# backend/app/models/check.py
class Evidence(SQLModel, table=True):
    # ... existing fields ...

    # NEW: Granular credibility breakdown
    base_domain_credibility: float = Field(default=0.6)  # Domain reputation
    page_quality_multiplier: float = Field(default=1.0)  # Article-level adjustment (0.5-1.2)
    quality_signals: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    # quality_signals = {
    #   "url_section": "news",  # vs "opinion", "entertainment"
    #   "citation_count": 2,
    #   "hedging_count": 1,
    #   "clickbait_score": 0.1,
    #   "length_words": 450
    # }
```

**2. Page Quality Analyzer**
```python
# backend/app/services/page_quality.py (NEW FILE)

import re
from typing import Dict, Any
from urllib.parse import urlparse

class PageQualityAnalyzer:
    def __init__(self):
        # URL section quality tiers
        self.high_quality_sections = [
            '/news/', '/science/', '/research/', '/investigation/',
            '/analysis/', '/politics/', '/world/', '/business/'
        ]

        self.low_quality_sections = [
            '/opinion/', '/blog/', '/entertainment/', '/gossip/',
            '/lifestyle/', '/celebrity/', '/showbiz/', '/sport/'
        ]

        # Clickbait indicators
        self.clickbait_patterns = [
            r"you won't believe",
            r"shocking",
            r"one weird trick",
            r"doctors hate",
            r"what happened next",
            r"\.\.\.$",  # Ending with ...
            r"!!!+",  # Multiple exclamation marks
            r"\?\?\?+",  # Multiple question marks
        ]

        # Quality content indicators
        self.citation_patterns = [
            r"according to [\w\s]+",
            r"research (shows|found|suggests|indicates)",
            r"study (published|conducted|shows|found)",
            r"data (from|shows|indicates|suggests)",
            r"\d{4} (study|report|survey|research)",
            r"(Dr\.|Professor|PhD) [\w\s]+",
            r"journal of \w+",
            r"published in \w+",
        ]

        # Hedging/uncertainty indicators
        self.hedging_patterns = [
            r"might be", r"could be", r"possibly", r"allegedly",
            r"some say", r"many believe", r"reportedly",
            r"sources claim", r"rumors suggest", r"speculation",
            r"unconfirmed", r"unverified"
        ]

    def analyze(self, url: str, title: str, snippet: str) -> Dict[str, Any]:
        """
        Analyze page-level quality signals
        Returns quality signals dict + multiplier (0.5-1.2)
        """
        signals = {}
        quality_multiplier = 1.0

        # Signal 1: URL Section Quality
        url_lower = url.lower()
        url_section = self._extract_url_section(url)
        signals['url_section'] = url_section

        if any(section in url_lower for section in self.high_quality_sections):
            quality_multiplier *= 1.1
        elif any(section in url_lower for section in self.low_quality_sections):
            quality_multiplier *= 0.7

        # Signal 2: Clickbait Detection
        clickbait_score = self._detect_clickbait(title)
        signals['clickbait_score'] = clickbait_score
        if clickbait_score > 0.3:
            quality_multiplier *= (1.0 - clickbait_score * 0.5)

        # Signal 3: Citation Density
        citation_count = self._count_patterns(snippet, self.citation_patterns)
        signals['citation_count'] = citation_count
        if citation_count > 0:
            quality_multiplier *= min(1.2, 1.0 + (citation_count * 0.05))

        # Signal 4: Hedging/Uncertainty
        hedging_count = self._count_patterns(snippet, self.hedging_patterns)
        signals['hedging_count'] = hedging_count
        if hedging_count > 2:
            quality_multiplier *= 0.85

        # Signal 5: Content Length (snippet proxy)
        word_count = len(snippet.split())
        signals['length_words'] = word_count
        if word_count < 50:
            quality_multiplier *= 0.9  # Very short snippet = less context

        # Signal 6: ALL CAPS detection
        caps_words = len([w for w in title.split() if w.isupper() and len(w) > 2])
        signals['caps_words'] = caps_words
        if caps_words > 2:
            quality_multiplier *= 0.8

        # Clamp multiplier to reasonable range
        quality_multiplier = max(0.5, min(1.2, quality_multiplier))

        return {
            'signals': signals,
            'multiplier': quality_multiplier
        }

    def _extract_url_section(self, url: str) -> str:
        """Extract section from URL path"""
        path = urlparse(url).path
        parts = [p for p in path.split('/') if p]
        if len(parts) >= 1:
            return parts[0]
        return 'unknown'

    def _detect_clickbait(self, title: str) -> float:
        """Return clickbait score (0-1)"""
        matches = sum(
            1 for pattern in self.clickbait_patterns
            if re.search(pattern, title, re.IGNORECASE)
        )
        return min(1.0, matches / 3)

    def _count_patterns(self, text: str, patterns: List[str]) -> int:
        """Count pattern matches in text"""
        return sum(
            len(re.findall(pattern, text, re.IGNORECASE))
            for pattern in patterns
        )
```

**3. Integration Point**
```python
# backend/app/pipeline/retrieve.py - Modify _get_credibility_score (line 194)

from app.services.page_quality import PageQualityAnalyzer

class EvidenceRetriever:
    def __init__(self):
        # ... existing code ...
        self.page_quality_analyzer = PageQualityAnalyzer()

    def _get_credibility_score(self, source: str, url: str, title: str, snippet: str) -> float:
        """Enhanced credibility scoring with page-level analysis"""

        # Get base domain credibility (existing logic)
        domain_credibility = self._get_domain_credibility(source)

        # NEW: Analyze page-level quality
        quality_analysis = self.page_quality_analyzer.analyze(url, title, snippet)
        page_quality_multiplier = quality_analysis['multiplier']

        # Calculate final score
        final_score = min(1.0, domain_credibility * page_quality_multiplier)

        return final_score

    def _get_domain_credibility(self, source: str) -> float:
        """Existing domain-level logic (unchanged)"""
        # Academic/research institutions
        if any(domain in source for domain in ['.edu', '.ac.uk', 'university', 'research']):
            return self.credibility_weights['academic']

        # ... rest of existing logic
```

**Files Created:**
- `backend/app/services/page_quality.py`

**Files Modified:**
- `backend/app/models/check.py` (new fields)
- `backend/app/pipeline/retrieve.py` (_get_credibility_score)

**Testing:**
- Test `bbc.co.uk/news/...` vs `bbc.co.uk/entertainment/...`
- Test articles with many citations vs none
- Test clickbait titles
- Verify multipliers are applied correctly

---

## AREA 4: Fact-Check Coverage
**"Extend beyond Snopes/PolitiFact to global ClaimReview and IFCN networks."**

### Current Problem
- Zero fact-check integration
- Reinventing the wheel on already-verified claims

### Solution: Google Fact Check Explorer + IFCN Sources

#### Changes Required

**1. Database Schema**
```python
# backend/app/models/check.py
class Evidence(SQLModel, table=True):
    # ... existing fields ...

    # NEW: Fact-check tracking
    is_factcheck: bool = Field(default=False)
    factcheck_publisher: Optional[str] = None  # e.g., "Full Fact", "Snopes"
    factcheck_rating: Optional[str] = None  # Original rating text
    factcheck_date: Optional[datetime] = None
```

**2. IFCN Source List**
```python
# backend/app/data/ifcn_sources.json (NEW FILE)
{
  "tier1_factcheckers": [
    {
      "name": "Full Fact",
      "domain": "fullfact.org",
      "country": "UK",
      "credibility": 0.95
    },
    {
      "name": "Snopes",
      "domain": "snopes.com",
      "country": "US",
      "credibility": 0.95
    },
    {
      "name": "PolitiFact",
      "domain": "politifact.com",
      "country": "US",
      "credibility": 0.95
    },
    {
      "name": "FactCheck.org",
      "domain": "factcheck.org",
      "country": "US",
      "credibility": 0.95
    },
    {
      "name": "Africa Check",
      "domain": "africacheck.org",
      "country": "Pan-Africa",
      "credibility": 0.95
    },
    {
      "name": "Reuters Fact Check",
      "domain": "reuters.com/fact-check",
      "country": "Global",
      "credibility": 0.95
    },
    {
      "name": "AP Fact Check",
      "domain": "apnews.com/APFactCheck",
      "country": "Global",
      "credibility": 0.95
    },
    {
      "name": "AFP Fact Check",
      "domain": "factcheck.afp.com",
      "country": "Global",
      "credibility": 0.95
    }
  ]
}
```

**3. Fact-Check Aggregator Service**
```python
# backend/app/services/factcheck_aggregator.py (NEW FILE)

import httpx
import json
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from app.core.config import settings

class FactCheckAggregator:
    def __init__(self):
        self.google_api_key = settings.GOOGLE_FACTCHECK_API_KEY
        self.api_base = "https://factchecktools.googleapis.com/v1alpha1"

        # Load IFCN sources
        with open('backend/app/data/ifcn_sources.json', 'r') as f:
            data = json.load(f)
            self.ifcn_sources = data['tier1_factcheckers']

        self.cache_ttl = timedelta(days=30)  # Fact-checks rarely change

    async def search_factchecks(self, claim_text: str, language: str = "en") -> List[Dict]:
        """
        Search Google Fact Check Explorer API
        Returns list of existing fact-check verdicts
        """
        if not self.google_api_key:
            logger.warning("Google Fact Check API key not configured")
            return []

        results = []

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.api_base}/claims:search",
                    params={
                        "query": claim_text,
                        "key": self.google_api_key,
                        "languageCode": language,
                        "pageSize": 10  # Get top 10 matches
                    }
                )

                if response.status_code == 200:
                    data = response.json()

                    for claim_match in data.get('claims', []):
                        claim_reviewed = claim_match.get('text', '')

                        for review in claim_match.get('claimReview', []):
                            publisher_name = review.get('publisher', {}).get('name', 'Unknown')

                            # Check if publisher is IFCN signatory
                            is_ifcn = self._is_ifcn_source(publisher_name)

                            results.append({
                                'claim_text': claim_reviewed,
                                'source': publisher_name,
                                'url': review.get('url'),
                                'title': review.get('title'),
                                'snippet': review.get('textualRating', ''),
                                'rating': review.get('textualRating'),
                                'date': review.get('reviewDate'),
                                'credibility_score': 0.95 if is_ifcn else 0.85,
                                'is_factcheck': True,
                                'factcheck_publisher': publisher_name
                            })

                elif response.status_code == 429:
                    logger.warning("Fact Check API rate limit reached")
                else:
                    logger.error(f"Fact Check API error: {response.status_code}")

        except Exception as e:
            logger.error(f"Fact check search failed: {e}")

        return results

    def _is_ifcn_source(self, publisher_name: str) -> bool:
        """Check if publisher is IFCN signatory"""
        publisher_lower = publisher_name.lower()
        return any(
            source['name'].lower() in publisher_lower or publisher_lower in source['name'].lower()
            for source in self.ifcn_sources
        )

    def normalize_verdict(self, textual_rating: str) -> str:
        """
        Map various fact-check ratings to Tru8 verdicts

        Common ratings:
        - True, Correct, Accurate, Verified → supported
        - False, Incorrect, Inaccurate, Debunked → contradicted
        - Mixture, Partly True, Mostly True, Misleading → uncertain
        """
        if not textual_rating:
            return 'uncertain'

        rating_lower = textual_rating.lower()

        # Supported
        if any(term in rating_lower for term in [
            'true', 'correct', 'accurate', 'verified', 'confirmed'
        ]):
            return 'supported'

        # Contradicted
        elif any(term in rating_lower for term in [
            'false', 'incorrect', 'inaccurate', 'debunked', 'fake', 'hoax'
        ]):
            return 'contradicted'

        # Uncertain/Mixed
        else:
            return 'uncertain'
```

**4. Integration Point - PRIORITY SEARCH**
```python
# backend/app/workers/pipeline.py - INSERT BEFORE line 216

# Stage 3a: Check fact-check databases FIRST (NEW)
self.update_state(state="PROGRESS", meta={"stage": "factcheck_lookup", "progress": 35})
stage_start = datetime.utcnow()

factcheck_aggregator = FactCheckAggregator()
factcheck_results = await factcheck_aggregator.search_factchecks(claims[0].text)

if factcheck_results:
    logger.info(f"✓ Found {len(factcheck_results)} existing fact-checks")
    # Convert to Evidence objects
    evidence_from_factchecks = []
    for fc in factcheck_results:
        evidence = Evidence(
            claim_id=claims[0].id,
            source=fc['source'],
            url=fc['url'],
            title=fc['title'],
            snippet=fc['snippet'],
            published_date=datetime.fromisoformat(fc['date']) if fc['date'] else None,
            relevance_score=0.95,  # High relevance (direct claim match)
            credibility_score=fc['credibility_score'],
            is_factcheck=True,
            factcheck_publisher=fc['factcheck_publisher'],
            factcheck_rating=fc['rating']
        )
        evidence_from_factchecks.append(evidence)

stage_timings["factcheck_lookup"] = (datetime.utcnow() - stage_start).total_seconds()

# Stage 3b: Retrieve general evidence (EXISTING, but now supplementary)
self.update_state(state="PROGRESS", meta={"stage": "retrieve", "progress": 40})
# ... existing retrieve code ...

# Combine fact-checks + general evidence
if factcheck_results:
    all_evidence = evidence_from_factchecks + evidence
else:
    all_evidence = evidence
```

**5. Configuration**
```python
# backend/app/core/config.py
class Settings(BaseSettings):
    # ... existing settings ...

    # NEW: Google Fact Check API
    GOOGLE_FACTCHECK_API_KEY: Optional[str] = None
```

**6. Environment Variable**
```bash
# backend/.env
GOOGLE_FACTCHECK_API_KEY=your_api_key_here
```

**API Key Setup:**
1. Go to https://console.cloud.google.com/
2. Enable "Fact Check Tools API"
3. Create API key
4. Add to `.env`

**Files Created:**
- `backend/app/data/ifcn_sources.json`
- `backend/app/services/factcheck_aggregator.py`

**Files Modified:**
- `backend/app/models/check.py` (new fields)
- `backend/app/workers/pipeline.py` (integration)
- `backend/app/core/config.py` (new setting)

**Dependencies Added:**
```bash
# Already have httpx
```

**Testing:**
- Test with well-known claim (e.g., "The Earth is flat")
- Test with recent political claim
- Test with claim that has no fact-checks
- Verify IFCN sources get 95% credibility

---

## AREA 5: Verdict Nuance & Transparency
**"More detailed verdicts (e.g., 'Needs Primary Source,' 'Conflicting Evidence') to earn user trust."**

### Current Problem
- Only 3 verdicts: supported, contradicted, uncertain
- "uncertain" could mean 100 different things
- No transparency on WHY verdict was reached

### Solution: Expanded Verdict Categories + Reasoning Trail

#### Changes Required

**1. Database Schema (Already covered in Area 1)**
```python
# backend/app/models/check.py
class Check(SQLModel, table=True):
    verdict: Optional[str] = Field(
        default=None,
        sa_column=Column(
            Enum(
                "supported",
                "contradicted",
                "uncertain",
                "insufficient_evidence",
                "conflicting_expert_opinion",
                "needs_primary_source",
                "outdated_claim",
                "lacks_context",
                name="verdict_enum"
            )
        )
    )

    # NEW: Transparency fields
    verdict_reasoning: Optional[str] = None  # Human-readable explanation
    evidence_breakdown: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    # {
    #   "high_credibility_supporting": 2,
    #   "high_credibility_contradicting": 1,
    #   "medium_credibility_supporting": 3,
    #   "factchecks_found": 1,
    #   "consensus_strength": 0.75,
    #   "total_sources": 6
    # }
    verdict_reasoning_trail: Optional[Dict[str, str]] = Field(default=None, sa_column=Column(JSON))
    # Step-by-step reasoning showing how verdict was reached
```

**2. Enhanced Judge Prompt**
```python
# backend/app/pipeline/judge.py - Update JUDGE_PROMPT_TEMPLATE (around line 30)

JUDGE_PROMPT_TEMPLATE = """You are an expert fact-checking judge analyzing evidence about a claim.

**Claim:** {claim_text}

**Evidence Summary:**
Total sources: {total_sources}
- High-credibility sources (≥75%) supporting: {high_cred_supporting}
- High-credibility sources (≥75%) contradicting: {high_cred_contradicting}
- Medium-credibility sources (60-74%) supporting: {med_cred_supporting}
- Medium-credibility sources (60-74%) contradicting: {med_cred_contradicting}
- Fact-checks found: {factcheck_count}
- Consensus strength: {consensus_strength:.0%}

**Evidence Details:**
{evidence_details}

**Your Task:**
Determine the most appropriate verdict from these options:

1. **supported** - Strong consensus from authoritative sources confirms the claim
2. **contradicted** - Strong consensus from authoritative sources refutes the claim
3. **uncertain** - Mixed evidence of similar credibility, plausible either way
4. **insufficient_evidence** - Too few sources or no authoritative sources to make determination
5. **conflicting_expert_opinion** - High-quality sources directly contradict each other
6. **needs_primary_source** - Only secondary/tertiary sources found, primary research needed
7. **outdated_claim** - Claim was accurate historically but circumstances have changed
8. **lacks_context** - Claim is technically true but misleading without additional context

**Reasoning Requirements:**
- Explain which sources were most influential and why
- Address any conflicting evidence and how you weighted it
- Identify key limitations or caveats
- Specify what additional evidence would strengthen/change the verdict

**Output Format (JSON only):**
{{
  "verdict": "conflicting_expert_opinion",
  "confidence": 65,
  "reasoning": "Two tier-1 medical journals reach opposite conclusions about the efficacy of...",
  "key_evidence_urls": ["url1", "url2", "url3"],
  "limitations": "No primary research data available, only meta-analyses from 2020-2023",
  "influential_sources": ["Source 1 (95% cred)", "Source 2 (90% cred)"],
  "conflicting_note": "Nature Medicine contradicts The Lancet on methodology"
}}

Respond with ONLY valid JSON, no other text.
"""
```

**3. Evidence Breakdown Builder**
```python
# backend/app/pipeline/judge.py - Add new method

def _build_evidence_breakdown(self, verification_signals: Dict[str, Any], evidence: List[Evidence]) -> Dict[str, Any]:
    """Build detailed evidence breakdown for transparency"""

    factcheck_count = sum(1 for e in evidence if e.is_factcheck)

    breakdown = {
        'total_sources': len(evidence),
        'factchecks_found': factcheck_count,
        'high_credibility_supporting': sum(
            1 for e in evidence
            if e.credibility_score >= 0.75 and e.stance == 'supporting'
        ),
        'high_credibility_contradicting': sum(
            1 for e in evidence
            if e.credibility_score >= 0.75 and e.stance == 'contradicting'
        ),
        'medium_credibility_supporting': sum(
            1 for e in evidence
            if 0.6 <= e.credibility_score < 0.75 and e.stance == 'supporting'
        ),
        'medium_credibility_contradicting': sum(
            1 for e in evidence
            if 0.6 <= e.credibility_score < 0.75 and e.stance == 'contradicting'
        ),
        'low_credibility_supporting': sum(
            1 for e in evidence
            if e.credibility_score < 0.6 and e.stance == 'supporting'
        ),
        'low_credibility_contradicting': sum(
            1 for e in evidence
            if e.credibility_score < 0.6 and e.stance == 'contradicting'
        ),
        'consensus_strength': verification_signals.get('consensus_strength', 0),
        'average_credibility': sum(e.credibility_score for e in evidence) / max(1, len(evidence)),
        'independence_flags': sum(1 for e in evidence if e.independence_flag),
        'risk_flags': sum(1 for e in evidence if e.risk_flags)
    }

    return breakdown

def _build_reasoning_trail(self,
                          factcheck_count: int,
                          original_source_count: int,
                          deduplicated_count: int,
                          evidence_breakdown: Dict[str, Any],
                          verdict: str) -> Dict[str, str]:
    """Build step-by-step reasoning trail"""

    trail = {}

    # Step 1: Fact-check lookup
    if factcheck_count > 0:
        trail['step1_factcheck'] = f"Found {factcheck_count} existing fact-check(s) from IFCN signatories"
    else:
        trail['step1_factcheck'] = "No existing fact-checks found"

    # Step 2: Evidence retrieval
    trail['step2_retrieval'] = f"Retrieved {original_source_count} sources, deduplicated to {deduplicated_count}"

    # Step 3: Credibility scoring
    high_cred = evidence_breakdown['high_credibility_supporting'] + evidence_breakdown['high_credibility_contradicting']
    med_cred = evidence_breakdown['medium_credibility_supporting'] + evidence_breakdown['medium_credibility_contradicting']
    trail['step3_credibility'] = f"Quality: {high_cred} high-credibility (≥75%), {med_cred} medium-credibility (60-74%)"

    # Step 4: Consensus analysis
    consensus = evidence_breakdown['consensus_strength']
    trail['step4_consensus'] = f"Consensus strength: {consensus:.0%}"

    # Step 5: Verdict determination
    trail['step5_verdict'] = f"Verdict: {verdict}"

    return trail
```

**4. Update Judge Method**
```python
# backend/app/pipeline/judge.py - Modify judge_claim method (around line 164)

async def judge_claim(self, claim: Claim, evidence: List[Evidence], verification_signals: Dict[str, Any]) -> Dict[str, Any]:
    """Enhanced judging with transparency"""

    # Build evidence breakdown
    evidence_breakdown = self._build_evidence_breakdown(verification_signals, evidence)

    # Prepare prompt with all context
    prompt = JUDGE_PROMPT_TEMPLATE.format(
        claim_text=claim.text,
        total_sources=evidence_breakdown['total_sources'],
        high_cred_supporting=evidence_breakdown['high_credibility_supporting'],
        high_cred_contradicting=evidence_breakdown['high_credibility_contradicting'],
        med_cred_supporting=evidence_breakdown['medium_credibility_supporting'],
        med_cred_contradicting=evidence_breakdown['medium_credibility_contradicting'],
        factcheck_count=evidence_breakdown['factchecks_found'],
        consensus_strength=evidence_breakdown['consensus_strength'],
        evidence_details=self._format_evidence_details(evidence)
    )

    # Call LLM
    try:
        response = await self.llm_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            response_format={"type": "json_object"}
        )

        judgment = json.loads(response.choices[0].message.content)

        # Build reasoning trail
        reasoning_trail = self._build_reasoning_trail(
            factcheck_count=evidence_breakdown['factchecks_found'],
            original_source_count=verification_signals.get('original_source_count', len(evidence)),
            deduplicated_count=len(evidence),
            evidence_breakdown=evidence_breakdown,
            verdict=judgment['verdict']
        )

        # Add transparency metadata
        judgment['evidence_breakdown'] = evidence_breakdown
        judgment['reasoning_trail'] = reasoning_trail

        return judgment

    except Exception as e:
        logger.error(f"LLM judge failed: {e}, using fallback")
        return self._fallback_judgment(verification_signals, evidence_breakdown)
```

**Files Modified:**
- `backend/app/models/check.py` (new fields)
- `backend/app/pipeline/judge.py` (enhanced prompt + methods)

**Testing:**
- Test each verdict category with appropriate scenarios
- Verify reasoning trail is clear and accurate
- Verify evidence breakdown counts are correct

---

## AREA 6: Blacklist Sensitivity
**"Replace 'bad site' lists with transparent, evidence-based risk flags and allow appeals."**

### Current Problem
- No blacklist at all
- Known misinformation sites can be cited as evidence

### Solution: Multi-Source Reputation Database + Risk Flags

#### Changes Required

**1. Database Schema**
```python
# backend/app/models/check.py
class Evidence(SQLModel, table=True):
    # ... existing fields ...

    # NEW: Risk assessment
    risk_level: Optional[str] = None  # 'none', 'low', 'medium', 'high', 'satire'
    risk_flags: Optional[List[str]] = Field(default=None, sa_column=Column(JSON))
    # e.g., ['conspiracy_theories', 'failed_fact_checks', 'state_sponsored']
    reputation_sources: Optional[List[str]] = Field(default=None, sa_column=Column(JSON))
    # e.g., ['newsguard', 'mediabiasfactcheck', 'wikipedia']
    risk_reasoning: Optional[str] = None

# NEW MODEL: User appeals
# backend/app/models/reputation_appeal.py (NEW FILE)
from sqlmodel import SQLModel, Field, Column, JSON
from typing import List, Optional
from datetime import datetime

class ReputationAppeal(SQLModel, table=True):
    __tablename__ = "reputation_appeal"

    id: str = Field(default_factory=generate_uuid, primary_key=True)
    domain: str = Field(index=True)
    user_id: str = Field(foreign_key="user.id")

    # Appeal details
    current_risk_level: str
    appeal_reason: str
    supporting_evidence_urls: List[str] = Field(sa_column=Column(JSON))

    # Review status
    status: str = Field(default="pending")  # pending, approved, rejected, under_review
    admin_notes: Optional[str] = None
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None

    created_at: datetime = Field(default_factory=datetime.utcnow)
```

**2. Reputation Database**
```python
# backend/app/data/reputation_database.json (NEW FILE)
{
  "high_risk": {
    "infowars.com": {
      "risk_flags": ["conspiracy_theories", "multiple_failed_fact_checks", "medical_misinformation"],
      "sources": ["newsguard", "mediabiasfactcheck", "wikipedia"],
      "reasoning": "Extensive history of unsubstantiated conspiracy theories and debunked medical claims",
      "credibility_adjustment": 0.2
    },
    "naturalnews.com": {
      "risk_flags": ["health_misinformation", "conspiracy_theories"],
      "sources": ["newsguard", "mediabiasfactcheck"],
      "reasoning": "Known for promoting unproven alternative medicine and conspiracy theories",
      "credibility_adjustment": 0.2
    },
    "beforeitsnews.com": {
      "risk_flags": ["user_generated_unmoderated", "conspiracy_theories"],
      "sources": ["newsguard"],
      "reasoning": "Unmoderated user-generated content with no editorial oversight",
      "credibility_adjustment": 0.2
    }
  },

  "medium_risk": {
    "rt.com": {
      "risk_flags": ["state_sponsored", "propaganda_concerns", "editorial_independence"],
      "sources": ["newsguard", "wikipedia"],
      "reasoning": "Russian state-funded media with editorial independence concerns",
      "credibility_adjustment": 0.5
    },
    "sputniknews.com": {
      "risk_flags": ["state_sponsored", "propaganda_concerns"],
      "sources": ["newsguard"],
      "reasoning": "Russian state-controlled media outlet",
      "credibility_adjustment": 0.5
    },
    "presstv.ir": {
      "risk_flags": ["state_sponsored", "propaganda_concerns"],
      "sources": ["newsguard"],
      "reasoning": "Iranian state-controlled media outlet",
      "credibility_adjustment": 0.5
    },
    "breitbart.com": {
      "risk_flags": ["extreme_bias", "mixed_factual_reporting"],
      "sources": ["mediabiasfactcheck"],
      "reasoning": "Strong ideological bias with mixed record on factual reporting",
      "credibility_adjustment": 0.6
    }
  },

  "satire": {
    "theonion.com": {
      "risk_flags": ["satire"],
      "sources": ["self_declared"],
      "reasoning": "Satirical news site - content is intentionally fictional",
      "credibility_adjustment": 0.0
    },
    "newsthump.com": {
      "risk_flags": ["satire"],
      "sources": ["self_declared"],
      "reasoning": "UK satirical news site - content is intentionally fictional",
      "credibility_adjustment": 0.0
    },
    "thedailymash.co.uk": {
      "risk_flags": ["satire"],
      "sources": ["self_declared"],
      "reasoning": "Satirical news site - content is intentionally fictional",
      "credibility_adjustment": 0.0
    }
  }
}
```

**3. Reputation Checker Service**
```python
# backend/app/services/source_reputation.py (NEW FILE)

import json
import tldextract
from typing import Dict, Any, Optional

class SourceReputationChecker:
    def __init__(self):
        # Load reputation database
        with open('backend/app/data/reputation_database.json', 'r') as f:
            self.reputation_db = json.load(f)

        # Flatten for easier lookup
        self.domain_lookup = {}
        for risk_level, domains in self.reputation_db.items():
            for domain, data in domains.items():
                self.domain_lookup[domain] = {
                    'risk_level': risk_level,
                    **data
                }

    def check_reputation(self, url: str) -> Dict[str, Any]:
        """
        Check source reputation and return risk assessment
        Returns transparent risk assessment with reasoning
        """
        domain = tldextract.extract(url).registered_domain

        if domain in self.domain_lookup:
            rep_data = self.domain_lookup[domain]

            return {
                'risk_level': rep_data['risk_level'],
                'risk_flags': rep_data['risk_flags'],
                'credibility_adjustment': rep_data['credibility_adjustment'],
                'reasoning': rep_data['reasoning'],
                'sources': rep_data['sources'],
                'allow_appeal': True,
                'domain': domain
            }

        # No reputation concerns found
        return {
            'risk_level': 'none',
            'risk_flags': [],
            'credibility_adjustment': 1.0,
            'reasoning': None,
            'sources': [],
            'allow_appeal': False,
            'domain': domain
        }

    def apply_reputation_adjustment(self, evidence: Evidence) -> None:
        """Apply reputation-based credibility adjustment"""
        rep_check = self.check_reputation(evidence.url)

        # Store risk metadata
        evidence.risk_level = rep_check['risk_level']
        evidence.risk_flags = rep_check['risk_flags']
        evidence.reputation_sources = rep_check['sources']
        evidence.risk_reasoning = rep_check['reasoning']

        # Apply credibility adjustment
        adjustment = rep_check['credibility_adjustment']
        evidence.credibility_score *= adjustment

        # Log if flagged
        if rep_check['risk_level'] != 'none':
            logger.warning(
                f"Source flagged: {evidence.source} "
                f"({rep_check['risk_level']} risk, "
                f"credibility reduced by {(1-adjustment)*100:.0f}%)"
            )
```

**4. Integration Point**
```python
# backend/app/pipeline/retrieve.py - Insert after page quality analysis

from app.services.source_reputation import SourceReputationChecker

class EvidenceRetriever:
    def __init__(self):
        # ... existing code ...
        self.reputation_checker = SourceReputationChecker()

    async def retrieve_evidence(self, claims: List[Claim]) -> List[Evidence]:
        # ... existing retrieval + quality scoring ...

        # NEW: Check reputation for all evidence
        for evidence in all_evidence:
            self.reputation_checker.apply_reputation_adjustment(evidence)

        # Filter out satire sources entirely
        all_evidence = [e for e in all_evidence if e.risk_level != 'satire']

        return all_evidence
```

**5. Appeal System API**
```python
# backend/app/api/v1/reputation_appeals.py (NEW FILE)

from fastapi import APIRouter, Depends, HTTPException
from typing import List
from app.models.reputation_appeal import ReputationAppeal
from app.models.user import User
from app.api.deps import get_current_user

router = APIRouter(prefix="/reputation-appeals", tags=["reputation"])

@router.post("", status_code=201)
async def submit_appeal(
    domain: str,
    appeal_reason: str,
    supporting_evidence_urls: List[str],
    current_user: User = Depends(get_current_user)
):
    """Submit an appeal for a domain's reputation rating"""

    # Check if domain exists in reputation database
    rep_checker = SourceReputationChecker()
    rep_data = rep_checker.check_reputation(f"https://{domain}")

    if rep_data['risk_level'] == 'none':
        raise HTTPException(status_code=404, detail="Domain not found in reputation database")

    # Create appeal
    appeal = ReputationAppeal(
        domain=domain,
        user_id=current_user.id,
        current_risk_level=rep_data['risk_level'],
        appeal_reason=appeal_reason,
        supporting_evidence_urls=supporting_evidence_urls
    )

    # Save to database
    db.add(appeal)
    db.commit()

    return {"message": "Appeal submitted successfully", "appeal_id": appeal.id}

@router.get("/my-appeals")
async def get_my_appeals(current_user: User = Depends(get_current_user)):
    """Get current user's reputation appeals"""
    appeals = db.query(ReputationAppeal).filter(
        ReputationAppeal.user_id == current_user.id
    ).all()

    return appeals
```

**Files Created:**
- `backend/app/data/reputation_database.json`
- `backend/app/services/source_reputation.py`
- `backend/app/models/reputation_appeal.py`
- `backend/app/api/v1/reputation_appeals.py`

**Files Modified:**
- `backend/app/models/check.py` (new fields)
- `backend/app/pipeline/retrieve.py` (integration)
- `backend/app/api/v1/__init__.py` (register appeals router)

**Migration Required:** Yes - new `reputation_appeal` table

**Testing:**
- Test with known misinformation sites
- Test with satire sites (should be excluded)
- Test with state media
- Test appeal submission flow

---

## AREA 7: Traceability & Metadata
**"Record ownership, independence, and reasoning so users can see how the verdict was formed."**

### Current Problem
- Minimal metadata stored
- No ownership tracking
- No reasoning trail
- Can't explain WHY verdict was reached

### Solution: Comprehensive Metadata + Reasoning Trail

#### Changes Required

**1. Database Schema (Consolidated from previous areas)**
```python
# backend/app/models/check.py
class Evidence(SQLModel, table=True):
    # ... existing fields ...

    # Full credibility breakdown (Area 3, 6)
    base_domain_credibility: float = Field(default=0.6)
    page_quality_multiplier: float = Field(default=1.0)
    reputation_adjustment: float = Field(default=1.0)
    independence_penalty: float = Field(default=1.0)
    # final credibility_score = base * page * reputation * independence

    # Ownership (Area 2)
    parent_company: Optional[str] = None

    # Content metadata
    author: Optional[str] = None
    publisher_type: Optional[str] = None  # 'newspaper', 'academic', 'government', 'blog'

    # Retrieval metadata
    search_rank: Optional[int] = None  # Position in search results
    retrieval_method: Optional[str] = None  # 'brave_search', 'factcheck_api', 'semantic_search'
    retrieval_timestamp: datetime = Field(default_factory=datetime.utcnow)

class Check(SQLModel, table=True):
    # ... existing fields ...

    # Reasoning trail (Area 5)
    verdict_reasoning_trail: Optional[Dict[str, str]] = Field(default=None, sa_column=Column(JSON))
    evidence_breakdown: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))

    # Evidence influence scores
    evidence_influence_scores: Optional[Dict[str, float]] = Field(default=None, sa_column=Column(JSON))
    # {"evidence_id_1": 0.35, "evidence_id_2": 0.25, ...}
```

**2. Evidence Influence Calculator**
```python
# backend/app/pipeline/judge.py - Add new method

def _calculate_evidence_influence(self, evidence: List[Evidence], verdict: str) -> Dict[str, float]:
    """
    Calculate how much each piece of evidence influenced the final verdict
    Returns dict of evidence_id -> influence_score (0-1)
    """
    total_weight = sum(e.credibility_score for e in evidence)
    if total_weight == 0:
        return {}

    influence_scores = {}

    for e in evidence:
        # Base influence = credibility weight
        base_influence = e.credibility_score / total_weight

        # Boost if stance matches verdict
        if (verdict == 'supported' and e.stance == 'supporting') or \
           (verdict == 'contradicted' and e.stance == 'contradicting'):
            base_influence *= 1.5

        # Boost if fact-check
        if e.is_factcheck:
            base_influence *= 1.3

        influence_scores[e.id] = min(1.0, base_influence)

    # Normalize to sum to 1.0
    total = sum(influence_scores.values())
    if total > 0:
        influence_scores = {k: v/total for k, v in influence_scores.items()}

    return influence_scores
```

**3. Metadata Capture During Retrieval**
```python
# backend/app/pipeline/retrieve.py - Enhance evidence creation

async def _create_evidence_from_search_result(
    self,
    result: SearchResult,
    claim_id: str,
    search_rank: int
) -> Evidence:
    """Create Evidence object with full metadata"""

    # Get domain credibility
    domain_cred = self._get_domain_credibility(result.source)

    # Analyze page quality
    quality_analysis = self.page_quality_analyzer.analyze(
        result.url,
        result.title,
        result.snippet
    )
    page_multiplier = quality_analysis['multiplier']

    # Check reputation
    rep_check = self.reputation_checker.check_reputation(result.url)
    rep_adjustment = rep_check['credibility_adjustment']

    # Calculate final credibility
    final_credibility = domain_cred * page_multiplier * rep_adjustment

    # Create evidence with full metadata
    evidence = Evidence(
        claim_id=claim_id,
        source=result.source,
        url=result.url,
        title=result.title,
        snippet=result.snippet,
        published_date=result.date,
        relevance_score=result.relevance,

        # Credibility breakdown
        base_domain_credibility=domain_cred,
        page_quality_multiplier=page_multiplier,
        reputation_adjustment=rep_adjustment,
        credibility_score=final_credibility,

        # Quality signals
        quality_signals=quality_analysis['signals'],

        # Risk assessment
        risk_level=rep_check['risk_level'],
        risk_flags=rep_check['risk_flags'],
        risk_reasoning=rep_check['reasoning'],

        # Retrieval metadata
        search_rank=search_rank,
        retrieval_method='brave_search',
        retrieval_timestamp=datetime.utcnow()
    )

    return evidence
```

**4. Frontend Transparency Component**
```typescript
// web/components/check-detail/evidence-transparency-panel.tsx (NEW FILE)

import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Alert } from '@/components/ui/alert'

interface Evidence {
  source: string
  url: string
  base_domain_credibility: number
  page_quality_multiplier: number
  reputation_adjustment: number
  independence_penalty: number
  credibility_score: number
  parent_company?: string
  risk_flags?: string[]
  risk_reasoning?: string
  quality_signals?: {
    citation_count: number
    hedging_count: number
    clickbait_score: number
    url_section: string
  }
}

export function EvidenceTransparencyPanel({ evidence }: { evidence: Evidence }) {
  return (
    <Card className="p-6">
      <h3 className="font-bold text-lg mb-4">How We Scored This Source</h3>

      {/* Credibility Breakdown */}
      <div className="space-y-2 mb-6">
        <ScoreRow
          label="Base Domain Credibility"
          value={evidence.base_domain_credibility}
          description="Reputation of the publisher domain"
        />
        <ScoreRow
          label="× Article Quality"
          value={evidence.page_quality_multiplier}
          isMultiplier
          description={`Citations: ${evidence.quality_signals?.citation_count || 0}, Section: ${evidence.quality_signals?.url_section}`}
        />
        <ScoreRow
          label="× Reputation Check"
          value={evidence.reputation_adjustment}
          isMultiplier
          description={evidence.risk_reasoning || "No concerns found"}
        />
        {evidence.independence_penalty !== 1.0 && (
          <ScoreRow
            label="× Independence Penalty"
            value={evidence.independence_penalty}
            isMultiplier
            description={evidence.parent_company ? `Part of ${evidence.parent_company} media group` : "Content similarity detected"}
          />
        )}
        <div className="border-t pt-2 mt-2">
          <ScoreRow
            label="Final Credibility Score"
            value={evidence.credibility_score}
            bold
          />
        </div>
      </div>

      {/* Metadata */}
      <div className="grid grid-cols-2 gap-4 mb-6 text-sm">
        <div>
          <span className="text-gray-500">Publisher:</span>
          <p className="font-medium">{evidence.source}</p>
        </div>
        {evidence.parent_company && (
          <div>
            <span className="text-gray-500">Parent Company:</span>
            <p className="font-medium">{evidence.parent_company}</p>
          </div>
        )}
      </div>

      {/* Risk Flags */}
      {evidence.risk_flags && evidence.risk_flags.length > 0 && (
        <Alert variant="warning" className="mb-4">
          <strong>Risk Flags:</strong>
          <div className="flex flex-wrap gap-2 mt-2">
            {evidence.risk_flags.map(flag => (
              <Badge key={flag} variant="warning">
                {flag.replace(/_/g, ' ')}
              </Badge>
            ))}
          </div>
          <p className="text-sm mt-2">{evidence.risk_reasoning}</p>
        </Alert>
      )}

      {/* Quality Signals */}
      {evidence.quality_signals && (
        <div className="text-sm text-gray-600">
          <p>Quality indicators: {evidence.quality_signals.citation_count} citations,
          {evidence.quality_signals.hedging_count} hedging phrases</p>
        </div>
      )}
    </Card>
  )
}

function ScoreRow({ label, value, isMultiplier = false, bold = false, description = '' }: {
  label: string
  value: number
  isMultiplier?: boolean
  bold?: boolean
  description?: string
}) {
  const percentage = Math.round(value * 100)
  const color = value >= 0.75 ? 'text-green-600' : value >= 0.6 ? 'text-yellow-600' : 'text-red-600'

  return (
    <div>
      <div className="flex justify-between items-center">
        <span className={bold ? 'font-bold' : ''}>{label}</span>
        <span className={`${color} ${bold ? 'font-bold text-lg' : ''}`}>
          {isMultiplier ? `${value.toFixed(2)}×` : `${percentage}%`}
        </span>
      </div>
      {description && (
        <p className="text-xs text-gray-500 ml-4">{description}</p>
      )}
    </div>
  )
}
```

**5. Reasoning Trail Display**
```typescript
// web/components/check-detail/reasoning-trail.tsx (NEW FILE)

export function ReasoningTrail({ check }: { check: Check }) {
  if (!check.verdict_reasoning_trail) return null

  const steps = Object.entries(check.verdict_reasoning_trail)

  return (
    <Card className="p-6">
      <h3 className="font-bold text-lg mb-4">How This Verdict Was Reached</h3>

      <ol className="space-y-4">
        {steps.map(([key, description], index) => (
          <li key={key} className="flex gap-4">
            <div className="flex-shrink-0 w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center font-bold text-blue-700">
              {index + 1}
            </div>
            <div className="flex-1">
              <p className="text-sm font-medium text-gray-700 capitalize">
                {key.replace(/^step\d+_/, '').replace(/_/g, ' ')}
              </p>
              <p className="text-sm text-gray-600 mt-1">{description}</p>
            </div>
          </li>
        ))}
      </ol>

      {/* Evidence Breakdown */}
      {check.evidence_breakdown && (
        <div className="mt-6 p-4 bg-gray-50 rounded-lg">
          <h4 className="font-semibold mb-2">Evidence Summary</h4>
          <dl className="grid grid-cols-2 gap-2 text-sm">
            <div>
              <dt className="text-gray-600">Total Sources:</dt>
              <dd className="font-medium">{check.evidence_breakdown.total_sources}</dd>
            </div>
            <div>
              <dt className="text-gray-600">Fact-checks Found:</dt>
              <dd className="font-medium">{check.evidence_breakdown.factchecks_found}</dd>
            </div>
            <div>
              <dt className="text-gray-600">High-Credibility Supporting:</dt>
              <dd className="font-medium text-green-600">{check.evidence_breakdown.high_credibility_supporting}</dd>
            </div>
            <div>
              <dt className="text-gray-600">High-Credibility Contradicting:</dt>
              <dd className="font-medium text-red-600">{check.evidence_breakdown.high_credibility_contradicting}</dd>
            </div>
            <div>
              <dt className="text-gray-600">Consensus Strength:</dt>
              <dd className="font-medium">{Math.round(check.evidence_breakdown.consensus_strength * 100)}%</dd>
            </div>
          </dl>
        </div>
      )}
    </Card>
  )
}
```

**Files Created:**
- `web/components/check-detail/evidence-transparency-panel.tsx`
- `web/components/check-detail/reasoning-trail.tsx`

**Files Modified:**
- `backend/app/models/check.py` (comprehensive metadata fields)
- `backend/app/pipeline/retrieve.py` (capture metadata)
- `backend/app/pipeline/judge.py` (calculate influence scores)

**Testing:**
- Verify all metadata is captured correctly
- Verify credibility breakdown math is accurate
- Test frontend transparency components render correctly

---

## AREA 8: Keyword Filter Reliability
**"Replace brittle 'red flag' word lists with smarter content-level signals."**

### Current Problem
- No content analysis at all
- Simple keyword matching is brittle and gameable

### Solution: Semantic Content Analysis (Already covered in Area 3)

**Implementation:** Area 3's `PageQualityAnalyzer` replaces keyword filters with:
- Citation density (positive signal)
- Hedging detection (negative signal)
- Sensationalism scoring (negative signal)
- Content coherence analysis

**No additional implementation needed** - covered by Area 3's page quality analysis.

---

## AREA 9: Search Bias & Source Diversity
**"Move beyond popularity rankings; surface government, academic, and official sources."**

### Current Problem
- Pure Brave Search results (popularity-biased)
- No diversity requirements
- All 5 sources could be from same category

### Solution: Multi-Source Retrieval + Diversity Requirements

#### Changes Required

**1. Enhanced Retrieval Strategy**
```python
# backend/app/pipeline/retrieve.py - Major refactor

class EvidenceRetriever:
    def __init__(self):
        # ... existing code ...
        self.min_source_categories = 3  # Require at least 3 different types
        self.max_per_category = 2  # Max 2 from same category

    async def retrieve_evidence(self, claims: List[Claim]) -> List[Evidence]:
        """
        Multi-source retrieval with diversity requirements
        Priority: Fact-checks → Authoritative → News → General
        """
        all_evidence = []

        for claim in claims:
            evidence_pool = []

            # PRIORITY 1: Fact-check databases
            logger.info(f"[Retrieve] Stage 1: Searching fact-check databases")
            factcheck_results = await self.factcheck_aggregator.search_factchecks(claim.text)
            if factcheck_results:
                logger.info(f"[Retrieve] ✓ Found {len(factcheck_results)} fact-checks")
                evidence_pool.extend(await self._convert_factchecks_to_evidence(factcheck_results, claim.id))

            # PRIORITY 2: Authoritative sources (government, academic, official)
            logger.info(f"[Retrieve] Stage 2: Searching authoritative sources")
            auth_results = await self._search_authoritative_sources(claim.text)
            if auth_results:
                logger.info(f"[Retrieve] ✓ Found {len(auth_results)} authoritative sources")
                evidence_pool.extend(auth_results)

            # PRIORITY 3: News sources (tier1 + tier2)
            logger.info(f"[Retrieve] Stage 3: Searching news sources")
            news_results = await self._search_news_sources(claim.text)
            if news_results:
                logger.info(f"[Retrieve] ✓ Found {len(news_results)} news sources")
                evidence_pool.extend(news_results)

            # PRIORITY 4: General web search (fallback)
            if len(evidence_pool) < self.max_sources_per_claim:
                logger.info(f"[Retrieve] Stage 4: Searching general web")
                general_results = await self._search_general_web(claim.text)
                evidence_pool.extend(general_results)

            # Apply quality scoring to all evidence
            for evidence in evidence_pool:
                # Page quality analysis
                quality_analysis = self.page_quality_analyzer.analyze(
                    evidence.url, evidence.title, evidence.snippet
                )
                evidence.page_quality_multiplier = quality_analysis['multiplier']
                evidence.quality_signals = quality_analysis['signals']

                # Reputation check
                self.reputation_checker.apply_reputation_adjustment(evidence)

                # Update final credibility
                evidence.credibility_score = (
                    evidence.base_domain_credibility *
                    evidence.page_quality_multiplier *
                    evidence.reputation_adjustment
                )

            # Check independence and deduplicate
            evidence_pool = self.independence_checker.check_independence(evidence_pool)

            # Select diverse evidence
            selected_evidence = self._select_diverse_evidence(
                evidence_pool,
                min_categories=self.min_source_categories,
                max_per_category=self.max_per_category
            )

            all_evidence.extend(selected_evidence)

        return all_evidence

    async def _search_authoritative_sources(self, claim_text: str) -> List[Evidence]:
        """Targeted search of government, academic, and official sources"""
        authoritative_queries = [
            f'site:.gov {claim_text}',
            f'site:.edu {claim_text}',
            f'site:.ac.uk {claim_text}',
            f'(site:who.int OR site:cdc.gov OR site:nhs.uk) {claim_text}',
            f'site:.org (research OR study OR data) {claim_text}'
        ]

        all_results = []

        for query in authoritative_queries:
            try:
                results = await self.search_service.search(query, max_results=2)
                for rank, result in enumerate(results):
                    evidence = await self._create_evidence_from_search_result(
                        result,
                        claim_id=None,  # Set by caller
                        search_rank=rank
                    )
                    evidence.retrieval_method = 'authoritative_search'
                    all_results.append(evidence)
            except Exception as e:
                logger.error(f"Authoritative search failed for query '{query}': {e}")
                continue

        return all_results

    async def _search_news_sources(self, claim_text: str) -> List[Evidence]:
        """Targeted search of tier1 and tier2 news sources"""
        tier1_outlets = ['bbc.co.uk', 'reuters.com', 'apnews.com']
        tier2_outlets = ['theguardian.com', 'telegraph.co.uk', 'independent.co.uk']

        all_results = []

        # Search tier1 first
        for outlet in tier1_outlets[:2]:  # Top 2 tier1 outlets
            query = f'site:{outlet} {claim_text}'
            try:
                results = await self.search_service.search(query, max_results=1)
                for result in results:
                    evidence = await self._create_evidence_from_search_result(result, None, 0)
                    evidence.retrieval_method = 'news_tier1_search'
                    all_results.append(evidence)
            except:
                continue

        # Then tier2
        for outlet in tier2_outlets[:2]:
            query = f'site:{outlet} {claim_text}'
            try:
                results = await self.search_service.search(query, max_results=1)
                for result in results:
                    evidence = await self._create_evidence_from_search_result(result, None, 0)
                    evidence.retrieval_method = 'news_tier2_search'
                    all_results.append(evidence)
            except:
                continue

        return all_results

    async def _search_general_web(self, claim_text: str) -> List[Evidence]:
        """General web search (existing Brave Search logic)"""
        results = await self.search_service.search(claim_text, max_results=5)
        evidence_list = []

        for rank, result in enumerate(results):
            evidence = await self._create_evidence_from_search_result(result, None, rank)
            evidence.retrieval_method = 'brave_search'
            evidence_list.append(evidence)

        return evidence_list

    def _categorize_source(self, evidence: Evidence) -> str:
        """Categorize source into type"""
        if evidence.is_factcheck:
            return 'factcheck'
        elif evidence.base_domain_credibility >= 0.95:
            return 'scientific'
        elif evidence.base_domain_credibility >= 0.90:
            return 'tier1_news'
        elif evidence.base_domain_credibility >= 0.85:
            return 'government'
        elif evidence.base_domain_credibility >= 0.80:
            return 'tier2_news'
        elif evidence.base_domain_credibility >= 0.70:
            return 'academic'
        else:
            return 'general'

    def _select_diverse_evidence(
        self,
        evidence_pool: List[Evidence],
        min_categories: int = 3,
        max_per_category: int = 2
    ) -> List[Evidence]:
        """
        Select evidence ensuring source diversity
        Maximizes credibility while enforcing diversity constraints
        """
        # Categorize evidence
        categories = {}
        for evidence in evidence_pool:
            category = self._categorize_source(evidence)
            if category not in categories:
                categories[category] = []
            categories[category].append(evidence)

        # Sort each category by credibility
        for category in categories:
            categories[category].sort(key=lambda e: e.credibility_score, reverse=True)

        # Selection algorithm: Round-robin with credibility ordering
        selected = []
        category_counts = {cat: 0 for cat in categories}

        # Priority order for categories
        priority_order = [
            'factcheck', 'scientific', 'government', 'academic',
            'tier1_news', 'tier2_news', 'general'
        ]

        # Phase 1: Take top 1 from each priority category
        for category in priority_order:
            if category in categories and len(categories[category]) > 0:
                selected.append(categories[category][0])
                category_counts[category] += 1

        # Phase 2: Fill remaining slots with highest credibility
        remaining_slots = self.max_sources_per_claim - len(selected)

        if remaining_slots > 0:
            # Create pool of remaining evidence
            remaining = []
            for category, items in categories.items():
                available_count = min(
                    max_per_category - category_counts[category],
                    len(items) - category_counts[category]
                )
                remaining.extend(items[category_counts[category]:category_counts[category] + available_count])

            # Sort by credibility and take top N
            remaining.sort(key=lambda e: e.credibility_score, reverse=True)
            selected.extend(remaining[:remaining_slots])

        # Check diversity requirement
        unique_categories = len(set(self._categorize_source(e) for e in selected))
        if unique_categories < min_categories:
            logger.warning(
                f"Diversity requirement not met: Only {unique_categories} categories found, "
                f"need {min_categories}. Consider abstaining."
            )

        logger.info(f"[Retrieve] Selected {len(selected)} sources from {unique_categories} categories")

        return selected[:self.max_sources_per_claim]
```

**Files Modified:**
- `backend/app/pipeline/retrieve.py` (major refactor)

**Testing:**
- Test with claim that has fact-checks available
- Test with claim that has government sources
- Test with claim that only has news sources
- Verify diversity requirements are enforced
- Verify priority ordering (fact-checks > gov > news > general)

---

## 📊 Database Migration Plan

### Migration Script
```python
# backend/alembic/versions/002_credibility_enhancements.py

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON, ENUM

def upgrade():
    # 1. Expand verdict enum
    op.execute("ALTER TYPE verdict_enum ADD VALUE IF NOT EXISTS 'insufficient_evidence'")
    op.execute("ALTER TYPE verdict_enum ADD VALUE IF NOT EXISTS 'conflicting_expert_opinion'")
    op.execute("ALTER TYPE verdict_enum ADD VALUE IF NOT EXISTS 'needs_primary_source'")
    op.execute("ALTER TYPE verdict_enum ADD VALUE IF NOT EXISTS 'outdated_claim'")
    op.execute("ALTER TYPE verdict_enum ADD VALUE IF NOT EXISTS 'lacks_context'")

    # 2. Add columns to evidence table
    op.add_column('evidence', sa.Column('parent_company', sa.String(), nullable=True))
    op.add_column('evidence', sa.Column('independence_flag', sa.String(), nullable=True))
    op.add_column('evidence', sa.Column('content_similarity_score', sa.Float(), nullable=True))
    op.add_column('evidence', sa.Column('ownership_group_size', sa.Integer(), default=1))

    op.add_column('evidence', sa.Column('is_factcheck', sa.Boolean(), default=False))
    op.add_column('evidence', sa.Column('factcheck_publisher', sa.String(), nullable=True))
    op.add_column('evidence', sa.Column('factcheck_rating', sa.String(), nullable=True))
    op.add_column('evidence', sa.Column('factcheck_date', sa.DateTime(), nullable=True))

    op.add_column('evidence', sa.Column('risk_level', sa.String(), nullable=True))
    op.add_column('evidence', sa.Column('risk_flags', JSON(), nullable=True))
    op.add_column('evidence', sa.Column('reputation_sources', JSON(), nullable=True))
    op.add_column('evidence', sa.Column('risk_reasoning', sa.String(), nullable=True))

    op.add_column('evidence', sa.Column('base_domain_credibility', sa.Float(), default=0.6))
    op.add_column('evidence', sa.Column('page_quality_multiplier', sa.Float(), default=1.0))
    op.add_column('evidence', sa.Column('reputation_adjustment', sa.Float(), default=1.0))
    op.add_column('evidence', sa.Column('independence_penalty', sa.Float(), default=1.0))
    op.add_column('evidence', sa.Column('quality_signals', JSON(), nullable=True))

    op.add_column('evidence', sa.Column('author', sa.String(), nullable=True))
    op.add_column('evidence', sa.Column('publisher_type', sa.String(), nullable=True))
    op.add_column('evidence', sa.Column('search_rank', sa.Integer(), nullable=True))
    op.add_column('evidence', sa.Column('retrieval_method', sa.String(), nullable=True))

    # 3. Add columns to check table
    op.add_column('check', sa.Column('abstention_reason', sa.String(), nullable=True))
    op.add_column('check', sa.Column('verdict_reasoning', sa.String(), nullable=True))
    op.add_column('check', sa.Column('evidence_breakdown', JSON(), nullable=True))
    op.add_column('check', sa.Column('verdict_reasoning_trail', JSON(), nullable=True))
    op.add_column('check', sa.Column('evidence_influence_scores', JSON(), nullable=True))
    op.add_column('check', sa.Column('min_requirements_met', sa.Boolean(), default=False))

    # 4. Create reputation_appeal table
    op.create_table(
        'reputation_appeal',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('domain', sa.String(), nullable=False, index=True),
        sa.Column('user_id', sa.String(), sa.ForeignKey('user.id'), nullable=False),
        sa.Column('current_risk_level', sa.String(), nullable=False),
        sa.Column('appeal_reason', sa.String(), nullable=False),
        sa.Column('supporting_evidence_urls', JSON(), nullable=False),
        sa.Column('status', sa.String(), default='pending'),
        sa.Column('admin_notes', sa.String(), nullable=True),
        sa.Column('reviewed_by', sa.String(), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False)
    )

def downgrade():
    # Drop new columns and table
    op.drop_table('reputation_appeal')

    # Drop evidence columns
    evidence_columns = [
        'parent_company', 'independence_flag', 'content_similarity_score', 'ownership_group_size',
        'is_factcheck', 'factcheck_publisher', 'factcheck_rating', 'factcheck_date',
        'risk_level', 'risk_flags', 'reputation_sources', 'risk_reasoning',
        'base_domain_credibility', 'page_quality_multiplier', 'reputation_adjustment',
        'independence_penalty', 'quality_signals', 'author', 'publisher_type',
        'search_rank', 'retrieval_method'
    ]
    for col in evidence_columns:
        op.drop_column('evidence', col)

    # Drop check columns
    check_columns = [
        'abstention_reason', 'verdict_reasoning', 'evidence_breakdown',
        'verdict_reasoning_trail', 'evidence_influence_scores', 'min_requirements_met'
    ]
    for col in check_columns:
        op.drop_column('check', col)
```

**Run Migration:**
```bash
cd backend
alembic revision --autogenerate -m "credibility_enhancements"
alembic upgrade head
```

---

## 📦 Dependencies & Setup

### New Dependencies
```bash
# backend/requirements.txt - ADD these lines

# Source independence (embeddings + similarity)
sentence-transformers==2.2.2
scikit-learn==1.3.0

# Already have:
# httpx (for fact-check API)
# openai (for LLM)
# fastapi, sqlmodel, etc.
```

### Install Dependencies
```bash
cd backend
pip install -r requirements.txt
```

### Environment Variables
```bash
# backend/.env - ADD this line
GOOGLE_FACTCHECK_API_KEY=your_api_key_here
```

### Data Files to Create
```
backend/app/data/
├── ownership_database.json       # Media ownership (Area 2)
├── ifcn_sources.json            # Fact-check sources (Area 4)
└── reputation_database.json     # Risk/blacklist (Area 6)
```

---

## 🧪 Testing Strategy

### Unit Tests

**1. Test Abstention Logic**
```python
# backend/tests/test_judge_abstention.py
def test_abstains_with_too_few_sources():
    signals = {'total_sources': 2}
    should_abstain, reason = judge._should_abstain(signals)
    assert should_abstain == True
    assert "Insufficient sources" in reason

def test_abstains_with_no_high_credibility():
    signals = {'total_sources': 5, 'max_credibility_score': 0.65}
    should_abstain, reason = judge._should_abstain(signals)
    assert should_abstain == True
    assert "No authoritative sources" in reason

def test_does_not_abstain_with_good_evidence():
    signals = {
        'total_sources': 5,
        'max_credibility_score': 0.90,
        'consensus_strength': 0.80
    }
    should_abstain, reason = judge._should_abstain(signals)
    assert should_abstain == False
```

**2. Test Source Independence**
```python
# backend/tests/test_source_independence.py
def test_flags_shared_ownership():
    evidence = [
        Evidence(source='dailymail.co.uk', url='https://dailymail.co.uk/news/...'),
        Evidence(source='metro.co.uk', url='https://metro.co.uk/news/...'),
    ]
    checker = SourceIndependenceChecker()
    result = checker.check_independence(evidence)

    assert all(e.independence_flag == 'shared_ownership' for e in result)
    assert all(e.parent_company == 'DMGT' for e in result)

def test_detects_duplicate_content():
    evidence = [
        Evidence(snippet="The Eiffel Tower was completed in 1889."),
        Evidence(snippet="The Eiffel Tower was completed in 1889."),  # Exact duplicate
    ]
    checker = SourceIndependenceChecker()
    result = checker.check_independence(evidence)

    # One should be flagged as duplicate
    assert len([e for e in result if e.independence_flag == 'duplicate_content']) >= 1
```

**3. Test Reputation Checker**
```python
# backend/tests/test_reputation.py
def test_flags_known_misinformation_site():
    checker = SourceReputationChecker()
    rep = checker.check_reputation('https://infowars.com/article')

    assert rep['risk_level'] == 'high_risk'
    assert 'conspiracy_theories' in rep['risk_flags']
    assert rep['credibility_adjustment'] == 0.2

def test_excludes_satire():
    checker = SourceReputationChecker()
    rep = checker.check_reputation('https://theonion.com/article')

    assert rep['risk_level'] == 'satire'
    assert rep['credibility_adjustment'] == 0.0
```

**4. Test Page Quality Analyzer**
```python
# backend/tests/test_page_quality.py
def test_detects_clickbait():
    analyzer = PageQualityAnalyzer()
    result = analyzer.analyze(
        url='https://example.com/news/article',
        title='You Won\'t Believe What Happened Next!!!',
        snippet='Some content'
    )
    assert result['signals']['clickbait_score'] > 0.5
    assert result['multiplier'] < 1.0

def test_rewards_citations():
    analyzer = PageQualityAnalyzer()
    result = analyzer.analyze(
        url='https://example.com/news/article',
        title='Study Shows Benefits',
        snippet='According to research published in Nature, data shows...'
    )
    assert result['signals']['citation_count'] > 0
    assert result['multiplier'] > 1.0
```

### Integration Tests

**1. Test Full Pipeline with Abstention**
```python
# backend/tests/test_pipeline_integration.py
async def test_abstains_with_insufficient_evidence(mock_search_returns_one_source):
    check = await run_verification_pipeline(
        content="Obscure claim with no evidence"
    )
    assert check.verdict == 'insufficient_evidence'
    assert check.abstention_reason is not None
```

**2. Test Fact-Check Priority**
```python
async def test_prioritizes_factchecks(mock_factcheck_api):
    mock_factcheck_api.return_value = [{'source': 'Full Fact', 'rating': 'False'}]

    check = await run_verification_pipeline(content="The Earth is flat")

    # Should find fact-check first
    assert any(e.is_factcheck for e in check.claims[0].evidence)
    assert check.verdict == 'contradicted'
```

**3. Test Source Diversity**
```python
async def test_enforces_source_diversity():
    check = await run_verification_pipeline(
        content="Claim with diverse evidence"
    )

    categories = set(
        categorize_source(e) for e in check.claims[0].evidence
    )
    assert len(categories) >= 3  # Minimum diversity requirement
```

### Manual Testing Scenarios

**Test Case 1: Known False Claim**
```
Input: "The Earth is flat"
Expected:
- Verdict: contradicted
- Confidence: 95%+
- Fact-checks found: Yes (multiple IFCN sources)
- High-credibility evidence: 4-5 sources
```

**Test Case 2: Ambiguous Claim**
```
Input: "Drinking 8 glasses of water daily is necessary"
Expected:
- Verdict: uncertain OR lacks_context
- Mixed evidence from medical sources
- Reasoning explains nuance
```

**Test Case 3: Obscure Claim**
```
Input: "The mayor of Small Town UK resigned yesterday"
Expected:
- Verdict: insufficient_evidence
- Abstention reason: Too few sources
- No high-credibility sources found
```

**Test Case 4: Propaganda Source**
```
Input: Text from RT.com article
Expected:
- Evidence includes risk_flags: ['state_sponsored']
- Credibility reduced to ~50%
- Reasoning mentions editorial independence concerns
```

---

## 📅 Implementation Phases

### Phase 1: Critical Foundation (Week 2)
**Goal:** Prevent misinformation validation

**Tasks:**
1. ✅ Area 1: Abstention Logic (2 days)
   - Database migration (verdict enum)
   - Implement `_should_abstain()` logic
   - Update fallback judgment
   - Add verification signal calculations
   - Unit tests

2. ✅ Area 4: Fact-Check Integration (2 days)
   - Get Google Fact Check API key
   - Create IFCN sources list
   - Implement `FactCheckAggregator`
   - Integrate into pipeline (priority search)
   - Unit + integration tests

3. ✅ Area 9: Diverse Retrieval (3 days)
   - Implement authoritative source search
   - Implement news source search
   - Implement diversity selection algorithm
   - Refactor retrieve stage
   - Integration tests

**Deliverable:** Pipeline that abstains when evidence is weak, prioritizes fact-checks, and enforces source diversity

---

### Phase 2: Quality Scoring (Week 3)
**Goal:** Accurate credibility assessment

**Tasks:**
1. ✅ Area 3: Page-Level Quality (2 days)
   - Create `PageQualityAnalyzer` service
   - Add quality signals to evidence model
   - Integrate into credibility scoring
   - Unit tests

2. ✅ Area 6: Reputation/Blacklist (2 days)
   - Create reputation database (top 50 sites)
   - Implement `SourceReputationChecker`
   - Add risk flags to evidence model
   - Filter satire sources
   - Unit tests

3. ✅ Area 2: Source Independence (3 days)
   - Create ownership database
   - Implement embedding-based duplicate detection
   - Create `SourceIndependenceChecker`
   - Integrate into retrieve stage
   - Unit tests

**Deliverable:** Evidence scored with page-level quality, reputation checks, and independence analysis

---

### Phase 3: Transparency & Nuance (Week 4)
**Goal:** User trust through transparency

**Tasks:**
1. ✅ Area 5: Nuanced Verdicts (2 days)
   - Update judge prompt with new categories
   - Implement evidence breakdown builder
   - Implement reasoning trail builder
   - Update judge method
   - Unit tests

2. ✅ Area 7: Traceability (2 days)
   - Add comprehensive metadata fields
   - Capture metadata during retrieval
   - Calculate evidence influence scores
   - Build frontend transparency components
   - Integration tests

3. ✅ Area 8: Content Analysis (1 day)
   - Already covered in Area 3
   - Add any additional semantic analysis if needed

4. ✅ Reputation Appeals System (1 day)
   - Create appeals model
   - Implement appeals API endpoints
   - Basic admin review interface (optional for MVP)

**Deliverable:** Full transparency on verdicts with detailed reasoning and metadata

---

### Phase 4: Testing & Refinement (Week 5)
**Goal:** Production-ready system

**Tasks:**
1. ✅ Comprehensive Testing (3 days)
   - Unit tests for all new services
   - Integration tests for full pipeline
   - Manual testing with real claims
   - Performance testing (latency/tokens)

2. ✅ Data Expansion (1 day)
   - Expand ownership database to 200+ companies
   - Expand reputation database to 200+ sites
   - Expand IFCN sources to full list

3. ✅ Documentation (1 day)
   - API documentation updates
   - Frontend documentation for new components
   - Admin documentation for appeals review

**Deliverable:** Tested, documented, production-ready credibility system

---

## 📈 Success Metrics

### Quality Metrics
- **Abstention Rate:** 15-25% (shows we're not guessing)
- **Fact-Check Hit Rate:** 30%+ of claims have existing fact-checks
- **Source Diversity:** Average 3.5+ categories per check
- **High-Credibility Evidence:** 60%+ of evidence ≥75% credibility
- **Risk Flag Rate:** <5% of evidence flagged (shows search is working)

### Performance Metrics
- **Pipeline Latency:** <15s for Quick mode (was <10s, +5s acceptable)
- **Token Usage:** <$0.03 per check (was $0.02, embedding models add cost)
- **API Response Time:** <300ms p95 (was <200ms, +100ms acceptable)

### User Trust Metrics
- **Transparency Engagement:** 40%+ users expand evidence details
- **Appeal Rate:** <2% of verdicts (shows system is fair)
- **Verdict Reversal Rate:** <5% (shows we're getting it right)
- **User Confidence:** Survey score >4/5 on "I trust Tru8's verdicts"

---

## 🚨 Risks & Mitigations

### Risk 1: Increased Latency
**Problem:** 9-layer analysis adds processing time

**Mitigation:**
- Run searches in parallel (fact-check + authoritative + news)
- Cache fact-check results (30-day TTL)
- Use lightweight embedding model (all-MiniLM-L6-v2, 80MB)
- Implement timeout with graceful degradation

### Risk 2: API Costs
**Problem:** Google Fact Check API + embedding model

**Mitigation:**
- Google Fact Check API is free (quota: 10,000/day)
- Use CPU-based embedding model (no GPU needed)
- Cache duplicate detection results
- Monitor token usage per check

### Risk 3: False Positives on Blacklist
**Problem:** Legitimate sources flagged incorrectly

**Mitigation:**
- Use multiple reputation sources (NewsGuard + MBFC + Wikipedia)
- Transparent reasoning shown to users
- User appeal system with admin review
- Regular audits of reputation database

### Risk 4: Incomplete Databases
**Problem:** Ownership/reputation databases can't cover all sites

**Mitigation:**
- Start with top 200 sites (covers 80% of traffic)
- Graceful fallback to general credibility tier
- Crowdsource suggestions via appeal system
- Quarterly updates to databases

### Risk 5: LLM Hallucination
**Problem:** Judge might hallucinate reasoning

**Mitigation:**
- Use structured JSON output
- Validate all fields are present
- Fallback to rule-based judgment if LLM fails
- Log all judgments for audit

---

## 🎯 Definition of Done

### Phase 1 Complete When:
- ✅ Pipeline abstains with <3 sources
- ✅ Pipeline abstains with no high-credibility sources
- ✅ Fact-check API integrated and working
- ✅ Diverse evidence retrieval enforced
- ✅ All unit tests passing
- ✅ Manual test: "Earth is flat" → finds fact-checks, contradicted verdict

### Phase 2 Complete When:
- ✅ Page quality analysis reduces clickbait credibility
- ✅ Page quality analysis rewards citations
- ✅ Known misinformation sites flagged and penalized
- ✅ Satire sites excluded from evidence
- ✅ Duplicate content detected and deduplicated
- ✅ Shared ownership flagged and penalized
- ✅ Manual test: 3 DMGT sources → reduced to 2 effective sources

### Phase 3 Complete When:
- ✅ All 8 verdict categories working
- ✅ Evidence breakdown stored in database
- ✅ Reasoning trail stored in database
- ✅ Frontend transparency components render correctly
- ✅ Reputation appeal system functional
- ✅ Manual test: User can see full credibility breakdown

### Phase 4 Complete When:
- ✅ All unit tests passing (>90% coverage)
- ✅ All integration tests passing
- ✅ 20+ manual test scenarios validated
- ✅ Performance benchmarks met
- ✅ Documentation complete
- ✅ Databases expanded (200+ entries each)
- ✅ **USER ACCEPTANCE:** User confirms system meets quality standards

---

## 🔄 Rollout Strategy

### Week 2-3: Development
- Implement in feature branch: `feature/credibility-enhancements`
- Use feature flags to test in staging

### Week 4: Staging Testing
- Deploy to staging environment
- Run comprehensive tests
- User acceptance testing with real claims

### Week 5: Gradual Rollout
- Day 1: Enable for 10% of users
- Day 2: Monitor metrics, expand to 25%
- Day 3: Expand to 50%
- Day 4: Expand to 100%
- Monitor abstention rate, latency, user feedback

### Week 6: Optimization
- Analyze performance metrics
- Optimize slow queries
- Expand databases based on real usage
- Address any user feedback

---

## 📚 References

### External Resources
- Google Fact Check Tools API: https://toolbox.google.com/factcheck/apis
- IFCN Signatory List: https://ifcncodeofprinciples.poynter.org/signatories
- NewsGuard: https://www.newsguardtech.com/
- Media Bias/Fact Check: https://mediabiasfactcheck.com/
- Wikipedia Unreliable Sources: https://en.wikipedia.org/wiki/Wikipedia:Reliable_sources/Perennial_sources

### Internal Documentation
- `backend/app/pipeline/README.md` - Pipeline architecture
- `backend/app/models/README.md` - Database schema
- `DESIGN_SYSTEM.md` - Frontend components

---

## ✅ Review Checklist

Before marking this plan as approved:

- [ ] All 9 areas comprehensively addressed
- [ ] Database schema changes documented
- [ ] Migration script complete
- [ ] Integration points clearly identified
- [ ] Testing strategy defined
- [ ] Phased rollout plan specified
- [ ] Success metrics defined
- [ ] Risks identified with mitigations
- [ ] Dependencies and setup documented
- [ ] User-facing changes explained

---

**Next Steps:**
1. User reviews this comprehensive plan
2. User confirms approach aligns with vision
3. User approves to proceed with Phase 1 implementation
4. Begin Week 2 development: Abstention + Fact-Checks + Diversity

---

*This plan transforms Tru8 from a search aggregator into a bulletproof credibility engine that users can trust to never validate misinformation.*
