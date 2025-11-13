# 🧭 Tru8 Pipeline Enhancement Plan

**Version:** 2.0 (Merged Implementation Guide)
**Date:** 2025-10-17
**Status:** Under Review - Awaiting Implementation Approval
**Priority:** CRITICAL - Foundation for Product Quality & Trust

---

## 📖 Document Purpose

This plan merges two strategic documents:
1. **9-Layer Credibility Enhancement Plan** — Technical architecture and implementation details
2. **Consultant Helper Guide** — Development principles, safeguards, and best practices

**Goal:** Create a unified roadmap for enhancing Tru8's verification pipeline with credibility-aware, modular, transparent, and defensible improvements.

---

## 🎯 Core Principles

### Development Philosophy

**1. Learn Before Coding**
Research all relevant pipeline, service, and model files before making any changes. Never code blind.

**2. Accuracy Over Speed**
If a complete check takes 20-30 seconds but is accurate, that is acceptable. Speed comes after correctness is proven.

**3. Integrate, Don't Replace**
All new logic attaches to the pipeline as **extensions, not replacements**. Respect the existing 5-stage architecture.

**4. Fail Safely**
On partial data, degrade gracefully — return "uncertain" rather than error or silence. Every stage must have fallback mechanisms.

**5. Never Duplicate**
Reuse existing cache, telemetry, and logging infrastructure. Maintain DRY principles throughout.

**6. When Uncertain, Abstain**
Better to say "insufficient evidence" than guess wrong. This builds user trust.

**7. Preserve Explainability**
Every verdict must include a clear reasoning trail showing how and why the conclusion was reached.

---

## 🚨 Critical Problem Statement

**Current Vulnerability:**
Tru8's pipeline can validate misinformation if it ranks highly in search results because:
- All unmatched sources default to 60% credibility
- No fact-check integration
- No source independence checking
- No blacklist/risk flagging
- Single low-quality source can validate claims
- No abstention when evidence is weak

**Business Risk:**
*"If Tru8 starts saying that some of the things Trump, or other liars start selling as TRUTH, then Tru8 will never work."*

**Technical Risk:**
Pipeline has no defense against propaganda outlets, state-sponsored media, or coordinated misinformation campaigns appearing in top search results.

---

## 📊 Current System Analysis

### Pipeline Architecture (5 Stages)
```
Ingest → Extract → Retrieve → Verify → Judge → Save
```

**Files:**
- `backend/app/workers/pipeline.py:147-311` — Main orchestration
- `backend/app/pipeline/ingest.py` — URL/OCR/transcript processing
- `backend/app/pipeline/extract.py` — LLM claim extraction
- `backend/app/pipeline/retrieve.py` — Search + embeddings
- `backend/app/pipeline/verify.py` — NLI verification
- `backend/app/pipeline/judge.py` — Final verdict generation

### Critical Vulnerabilities Identified

#### 1. Default 60% Credibility (ALL SOURCES)
**File:** `backend/app/models/check.py:49`
```python
credibility_score: float = Field(default=0.6, ge=0, le=1)
```
**Impact:** Wikipedia, government sites, propaganda outlets all treated equally.

**Test Results:**
```
pariscityvision.com → 0.6 (general)
toureiffel.paris → 0.6 (general) [Official Eiffel Tower site!]
wikipedia.org → 0.6 (general) [Should be 0.85+]
rt.com → 0.6 (general) [State propaganda, should be 0.5 or flagged]
```

#### 2. Narrow Pattern Matching
**File:** `backend/app/pipeline/retrieve.py:23-30, 194-219`
- Only recognizes ~4 news outlets (BBC, Reuters, AP, Guardian)
- No Wikipedia, official sites, scientific journals beyond hardcoded list
- 99% of sources fall through to 'general' = 0.6

#### 3. No Minimum Source Requirements
**File:** `backend/app/pipeline/judge.py:270-309`
```python
def _fallback_judgment(self, verification_signals):
    supporting = signals.get('supporting_count', 0)  # Could be 1!
    if supporting > contradicting + 1:
        verdict = "supported"
```
**Risk:** Single 60% source can trigger "supported" verdict.

#### 4. No Fact-Check Integration
- Zero connection to IFCN signatories
- No Google Fact Check Explorer API
- Reinventing the wheel on already-verified claims

#### 5. Search Popularity Bias
**File:** `backend/app/services/search.py:52-90`
- Pure Brave Search results (popularity-ranked)
- What's popular ≠ what's true
- No domain filtering for authoritative sources

#### 6. No Source Independence Checking
- No ownership database (e.g., DMGT owns DailyMail, Metro, ThisIsMoney)
- No duplicate content detection
- 3 outlets owned by same company = "3 independent sources" ✗

---

## 🏗️ Comprehensive Solution Architecture

### Integration Philosophy

**Attach, Don't Replace:**
New credibility logic integrates as **modular services** at specific pipeline stages:

| Stage | Enhancement |
|-------|------------|
| **Retrieve** | Fact-check pre-search, domain credibility config, reputation filtering, source independence, page-level quality |
| **Verify** | Credibility-weighted NLI scoring |
| **Judge** | Consensus requirements, abstention logic, nuanced verdicts |
| **Save** | Metadata enrichment (reasoning trail, credibility breakdown) |
| **UI** | Expanded citations, transparency panels, reasoning display |

### The Credibility Loop
```
CLAIM RECEIVED
    ↓
[Stage 1] FACT-CHECK LOOKUP (Google Fact Check API - Priority Search)
    ↓
[Stage 2] DIVERSE EVIDENCE RETRIEVAL (Gov/Academic/News/General with diversity requirements)
    ↓
[Stage 3] SOURCE REPUTATION CHECK (Blacklist, red flags, risk assessment)
    ↓
[Stage 4] SOURCE INDEPENDENCE ANALYSIS (Ownership database, duplicate content detection)
    ↓
[Stage 5] PAGE-LEVEL QUALITY SCORING (URL section, citations, hedging, clickbait)
    ↓
[Stage 6] CREDIBILITY AGGREGATION (Multi-factor weighted scoring)
    ↓
[Stage 7] NLI VERIFICATION (Credibility-weighted entailment scoring)
    ↓
[Stage 8] CONSENSUS ANALYSIS (Minimum source/quality requirements)
    ↓
[Stage 9] VERDICT DETERMINATION (Nuanced categories + abstention + transparency)
    ↓
SAVE WITH FULL TRACEABILITY & DELIVER TO USER
```

---

## 📋 Implementation Areas (Prioritized)

---

## AREA 1: Consensus & Abstention Logic (CRITICAL)
**Priority:** Phase 1, Week 1
**Goal:** Never force a verdict when evidence is weak

### Current Problem
- Always returns verdict (supported/contradicted/uncertain)
- No minimum source count
- No credibility threshold
- Single 60% source can influence verdict

### Solution Design

**Minimum Requirements:**
```python
MIN_SOURCES_FOR_VERDICT = 3
MIN_HIGH_CREDIBILITY_SOURCES = 1  # At least one tier1+ source (≥0.8)
MIN_CREDIBILITY_THRESHOLD = 0.75
MIN_CONSENSUS_STRENGTH = 0.65  # 65% agreement after credibility weighting
```

**Abstention Triggers:**
1. Too few sources (<3)
2. No authoritative sources (max credibility <75%)
3. Weak consensus (<65% agreement)
4. Conflicting high-credibility sources (tier1 sources disagree)

**New Verdict Categories:**
- `insufficient_evidence` — Too few sources or no authoritative sources
- `conflicting_expert_opinion` — High-quality sources contradict each other
- `needs_primary_source` — Only secondary sources found
- `outdated_claim` — Was true historically, circumstances changed
- `lacks_context` — Technically true but misleading

### Database Schema Changes

```python
# backend/app/models/check.py

from sqlalchemy import Enum as SQLEnum

class Check(SQLModel, table=True):
    verdict: Optional[str] = Field(
        default=None,
        sa_column=Column(
            SQLEnum(
                "supported",
                "contradicted",
                "uncertain",
                "insufficient_evidence",  # NEW
                "conflicting_expert_opinion",  # NEW
                "needs_primary_source",  # NEW
                "outdated_claim",  # NEW
                "lacks_context",  # NEW
                name="verdict_enum",
                create_constraint=True
            )
        )
    )
    abstention_reason: Optional[str] = None  # NEW - Why we abstained
    min_requirements_met: bool = Field(default=False)  # NEW - Consensus checks passed

    # Transparency fields
    verdict_reasoning: Optional[str] = None
    evidence_breakdown: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    verdict_reasoning_trail: Optional[Dict[str, str]] = Field(default=None, sa_column=Column(JSON))
```

### Implementation Files

**Files to Modify:**
1. `backend/app/models/check.py` — Add verdict enum values + abstention fields
2. `backend/app/pipeline/verify.py` — Add credibility-weighted metrics to verification_signals
3. `backend/app/pipeline/judge.py` — Add `_should_abstain()` logic before verdict determination

**Migration Required:** Yes
```bash
alembic revision -m "add_verdict_categories_and_abstention"
alembic upgrade head
```

### Testing Requirements
- Test with 0, 1, 2, 3 sources (should abstain with <3)
- Test with all low-credibility sources (should abstain)
- Test with conflicting high-credibility sources (should flag conflict)
- Test with known false claim (should find fact-checks and contradict)

---

## AREA 2: Fact-Check Integration (CRITICAL)
**Priority:** Phase 1, Week 1
**Goal:** Prevent re-validating known misinformation

### Current Problem
- Zero fact-check integration
- Reinventing the wheel on already-verified claims
- Missing existing professional work from IFCN signatories

### Solution Design

**API:** Google Fact Check Explorer API
- Free tier: 10,000 queries/day
- Aggregates ClaimReview data from 100+ fact-checkers
- Covers: Snopes, Full Fact, PolitiFact, Reuters Fact Check, AFP, etc.

**Strategy:** Priority search BEFORE general retrieval
- Check fact-check databases first
- If found: Use as high-credibility evidence (0.95 score)
- Still retrieve general evidence for context
- Weight fact-checks heavily in final verdict

**Citation Format:**
> "According to Full Fact (2024-09-12): rated False."

### Database Schema Changes

```python
# backend/app/models/check.py

class Evidence(SQLModel, table=True):
    # ... existing fields ...

    # NEW: Fact-check tracking
    is_factcheck: bool = Field(default=False)
    factcheck_publisher: Optional[str] = None  # "Full Fact", "Snopes"
    factcheck_rating: Optional[str] = None  # Original rating text
    factcheck_date: Optional[datetime] = None
    source_type: Optional[str] = None  # 'factcheck', 'news', 'academic', 'government', 'general'
```

### Implementation Files

**Files to Create:**
1. `backend/app/data/ifcn_sources.json` — List of IFCN signatories with credibility scores
2. `backend/app/services/factcheck_aggregator.py` — Google Fact Check API wrapper

**Files to Modify:**
1. `backend/app/core/config.py` — Add `GOOGLE_FACTCHECK_API_KEY`
2. `backend/app/workers/pipeline.py` — Insert fact-check lookup stage before retrieve
3. `backend/app/models/check.py` — Add fact-check fields to Evidence

**Environment Variable:**
```bash
# backend/.env
GOOGLE_FACTCHECK_API_KEY=your_api_key_here
```

**API Key Setup:**
1. Go to https://console.cloud.google.com/
2. Enable "Fact Check Tools API"
3. Create API key
4. Add to `.env`

### Legal & Safety Requirements

**Must Comply:**
- Fair use / fair dealing (UK/US)
- Store only: verdict summary + URL (never full article text)
- Proper attribution: "According to [Publisher] ([Date]): [Rating]"
- Legal review required before public launch

**Fail Safely:**
- If API fails → log warning, continue with general search
- If rate limited → cache aggressively, continue with existing cache
- Never crash pipeline due to fact-check API issues

### Testing Requirements
- Test with known false claim: "The Earth is flat" (should find multiple fact-checks)
- Test with recent political claim (should find fact-checks if available)
- Test with obscure claim (should gracefully fall back to general search)
- Verify fact-checks get 95% credibility score

---

## AREA 3: Domain Credibility Framework (HIGH PRIORITY)
**Priority:** Phase 1, Week 2
**Goal:** Centralized, maintainable source reputation management

### Current Problem
- Inline Python dict with ~6 hardcoded credibility weights
- No blacklist
- No governance process for adding/removing sources

### Solution Design

**Single Source of Truth:** `source_credibility.json`

Contains:
- **Tiered allowlists** (academic, government, scientific, news_tier1, news_tier2, etc.)
- **Blacklist** (known misinformation domains)
- **Risk flags** (state-sponsored, propaganda concerns, satire, etc.)

**No hardcoded domains anywhere else in codebase.**

### Configuration File Structure

```json
{
  "academic": {
    "credibility": 1.0,
    "description": "Educational and research institutions",
    "domains": [
      "*.edu",
      "*.ac.uk",
      "mit.edu",
      "stanford.edu",
      "ox.ac.uk",
      "cam.ac.uk"
    ],
    "patterns": ["university", "research institution"]
  },

  "government": {
    "credibility": 0.85,
    "description": "Government and official institutional sources",
    "domains": [
      "*.gov",
      "*.gov.uk",
      "nhs.uk",
      "who.int",
      "cdc.gov",
      "ons.gov.uk"
    ]
  },

  "scientific": {
    "credibility": 0.95,
    "description": "Peer-reviewed scientific journals",
    "domains": [
      "nature.com",
      "science.org",
      "cell.com",
      "thelancet.com",
      "nejm.org",
      "bmj.com"
    ]
  },

  "news_tier1": {
    "credibility": 0.9,
    "description": "Highest-rated international news agencies",
    "domains": [
      "bbc.co.uk",
      "bbc.com",
      "reuters.com",
      "apnews.com",
      "ap.org"
    ]
  },

  "news_tier2": {
    "credibility": 0.8,
    "description": "Reputable national news outlets",
    "domains": [
      "theguardian.com",
      "telegraph.co.uk",
      "independent.co.uk",
      "economist.com",
      "ft.com",
      "washingtonpost.com",
      "nytimes.com"
    ]
  },

  "reference": {
    "credibility": 0.85,
    "description": "Reference and knowledge bases",
    "domains": [
      "wikipedia.org",
      "britannica.com"
    ]
  },

  "blacklist": {
    "credibility": 0.2,
    "description": "Known misinformation sources",
    "domains": [
      "infowars.com",
      "naturalnews.com",
      "beforeitsnews.com"
    ],
    "risk_flags": ["conspiracy_theories", "multiple_failed_fact_checks", "medical_misinformation"],
    "auto_exclude": false
  },

  "state_media": {
    "credibility": 0.5,
    "description": "State-sponsored media with editorial independence concerns",
    "domains": [
      "rt.com",
      "sputniknews.com",
      "presstv.ir"
    ],
    "risk_flags": ["state_sponsored", "propaganda_concerns"],
    "auto_exclude": false
  },

  "satire": {
    "credibility": 0.0,
    "description": "Satirical content - intentionally fictional",
    "domains": [
      "theonion.com",
      "newsthump.com",
      "thedailymash.co.uk"
    ],
    "risk_flags": ["satire"],
    "auto_exclude": true
  },

  "general": {
    "credibility": 0.6,
    "description": "Default for unmatched sources"
  }
}
```

### Implementation Files

**Files to Create:**
1. `backend/app/data/source_credibility.json` — Credibility configuration (above structure)
2. `backend/app/services/source_credibility.py` — Service to load and query config

**Files to Modify:**
1. `backend/app/pipeline/retrieve.py` — Replace inline dict with config service

**Sample Service:**
```python
# backend/app/services/source_credibility.py

import json
import tldextract
from typing import Dict, Optional

class SourceCredibilityService:
    def __init__(self):
        with open('backend/app/data/source_credibility.json', 'r') as f:
            self.config = json.load(f)

    def get_credibility(self, source: str, url: str) -> Dict[str, Any]:
        """
        Returns credibility score + tier + risk flags
        """
        domain = tldextract.extract(url).registered_domain

        # Check each tier
        for tier_name, tier_config in self.config.items():
            if tier_name == 'general':
                continue

            # Check domains
            if domain in tier_config.get('domains', []):
                return {
                    'tier': tier_name,
                    'credibility': tier_config['credibility'],
                    'risk_flags': tier_config.get('risk_flags', []),
                    'auto_exclude': tier_config.get('auto_exclude', False),
                    'reasoning': f"Matched {tier_name} tier"
                }

            # Check patterns (for wildcards like *.edu)
            for pattern in tier_config.get('domains', []):
                if '*' in pattern:
                    pattern_match = pattern.replace('*.', '')
                    if domain.endswith(pattern_match):
                        return {
                            'tier': tier_name,
                            'credibility': tier_config['credibility'],
                            'risk_flags': tier_config.get('risk_flags', []),
                            'auto_exclude': tier_config.get('auto_exclude', False),
                            'reasoning': f"Matched {tier_name} pattern"
                        }

        # Default to general
        return {
            'tier': 'general',
            'credibility': self.config['general']['credibility'],
            'risk_flags': [],
            'auto_exclude': False,
            'reasoning': 'No specific tier matched'
        }
```

### Maintenance & Governance

**Update Process:**
- Monthly review of `source_credibility.json`
- Manual script or scheduled task
- Version control tracked changes
- Requires approval from senior team member

**Feature Toggle:**
```bash
# backend/.env
ENABLE_CREDIBILITY_CONFIG=true
```

### Testing Requirements
- Test all tier matches (academic, government, scientific, etc.)
- Test blacklist exclusion
- Test satire auto-exclusion
- Test wildcard patterns (*.edu, *.gov)
- Test default fallback to 'general'

---

## AREA 4: Source Independence Checking (HIGH PRIORITY)
**Priority:** Phase 2, Week 3
**Goal:** Detect duplicate/shared-source content so echoes aren't treated as consensus

### Current Problem
- No ownership tracking
- No duplicate content detection
- DailyMail + Metro + ThisIsMoney (all DMGT) = "3 independent sources" ✗

### Solution Design

**Two-Layer Detection:**
1. **Ownership Database** — Media company → domains mapping
2. **Content Similarity** — Embeddings-based duplicate detection

**Penalties:**
- Duplicate content: 70% credibility penalty (0.3× multiplier)
- Shared ownership: Moderate penalty based on group size
- Keep max 2 sources per ownership group

### Database Schema Changes

```python
# backend/app/models/check.py

class Evidence(SQLModel, table=True):
    # ... existing fields ...

    # NEW: Independence tracking
    parent_company: Optional[str] = None  # "Daily Mail and General Trust"
    independence_flag: Optional[str] = None  # 'independent', 'shared_ownership', 'duplicate_content'
    content_similarity_score: Optional[float] = None  # 0-1 similarity to other evidence
    ownership_group_size: int = Field(default=1)  # How many sources share same owner
```

### Implementation Files

**Files to Create:**
1. `backend/app/data/ownership_database.json` — Media company ownership mappings
2. `backend/app/services/source_independence.py` — Independence checker service

**Files to Modify:**
1. `backend/app/models/check.py` — Add independence fields
2. `backend/app/pipeline/retrieve.py` — Integrate independence checking after retrieval

**Dependencies:**
```bash
# requirements.txt
sentence-transformers==2.2.2  # Lightweight embedding model (80MB)
scikit-learn==1.3.0  # For cosine similarity
```

**Ownership Database Sample:**
```json
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
      "dailystar.co.uk"
    ]
  }
}
```

### Testing Requirements
- Test with 3 sources from same owner (should reduce to 2 effective sources)
- Test with copy-pasted content (should flag as duplicate)
- Test with independent sources (should keep all)
- Verify credibility penalties applied correctly

---

## AREA 5: Page-Level Quality Analysis (MEDIUM PRIORITY)
**Priority:** Phase 2, Week 3
**Goal:** Rate the actual article, not just the publisher

### Current Problem
- Domain-only scoring: `bbc.co.uk/gossip` = `bbc.co.uk/news` = 0.9
- No article-level signals

### Solution Design

**Multi-Signal Analysis:**
1. URL section quality (`/news/` vs `/entertainment/`, `/opinion/`)
2. Citation density (positive signal)
3. Hedging/uncertainty language (negative signal)
4. Clickbait detection (title analysis)
5. Content length (very short = low context)
6. ALL CAPS detection (sensationalism)

**Quality Multiplier:** 0.5 - 1.2
- Applied to base domain credibility
- Example: BBC (0.9) × opinion section (0.7) = 0.63 final

### Database Schema Changes

```python
# backend/app/models/check.py

class Evidence(SQLModel, table=True):
    # ... existing fields ...

    # NEW: Granular credibility breakdown
    base_domain_credibility: float = Field(default=0.6)  # Domain reputation
    page_quality_multiplier: float = Field(default=1.0)  # Article-level adjustment (0.5-1.2)
    reputation_adjustment: float = Field(default=1.0)  # Risk/blacklist penalty
    independence_penalty: float = Field(default=1.0)  # Ownership/duplicate penalty
    # Final credibility_score = base × page × reputation × independence

    quality_signals: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    # quality_signals = {
    #   "url_section": "news",
    #   "citation_count": 2,
    #   "hedging_count": 1,
    #   "clickbait_score": 0.1,
    #   "length_words": 450
    # }
```

### Implementation Files

**Files to Create:**
1. `backend/app/services/page_quality.py` — Page quality analyzer

**Files to Modify:**
1. `backend/app/models/check.py` — Add quality fields
2. `backend/app/pipeline/retrieve.py` — Apply page quality analysis during credibility scoring

### Testing Requirements
- Test `bbc.co.uk/news/...` vs `bbc.co.uk/entertainment/...` (should score differently)
- Test articles with many citations (should boost score)
- Test clickbait titles (should reduce score)

---

## AREA 6: Search Diversity Requirements (MEDIUM PRIORITY)
**Priority:** Phase 2, Week 4
**Goal:** Move beyond popularity rankings; surface authoritative sources

### Current Problem
- Pure Brave Search results (popularity-biased)
- All 5 sources could be from same category (e.g., all tabloids)

### Solution Design

**Multi-Source Retrieval Strategy:**
1. Fact-check databases (priority)
2. Government/academic sources (`.gov`, `.edu`, WHO, CDC, NHS)
3. News sources (tier1 + tier2)
4. General web (fallback)

**Diversity Requirements:**
- Minimum 3 source categories per check
- Maximum 2 sources per category
- Round-robin selection with credibility ranking

### Implementation Files

**Files to Modify:**
1. `backend/app/pipeline/retrieve.py` — Add targeted search methods + diversity selection

**No Database Changes Required**

### Testing Requirements
- Test that fact-checks are prioritized when available
- Test that source categories are diverse (not all news, not all general)
- Test diversity constraint enforcement

---

## AREA 7: Verdict Transparency & Reasoning (MEDIUM PRIORITY)
**Priority:** Phase 3, Week 4
**Goal:** Users see HOW verdict was reached

### Current Problem
- Verdict + confidence + generic rationale
- No transparency on which sources influenced decision
- Can't audit reasoning

### Solution Design

**Transparency Layers:**
1. **Evidence Breakdown** — Counts by credibility tier + stance
2. **Reasoning Trail** — Step-by-step: fact-check lookup → retrieval → scoring → consensus → verdict
3. **Evidence Influence Scores** — Which pieces of evidence had most impact
4. **Credibility Breakdown** — Show calculation: base × page × reputation × independence

### Database Schema Changes

```python
# backend/app/models/check.py

class Check(SQLModel, table=True):
    # ... existing fields ...

    evidence_breakdown: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    # {
    #   "total_sources": 6,
    #   "factchecks_found": 1,
    #   "high_credibility_supporting": 2,
    #   "high_credibility_contradicting": 1,
    #   "consensus_strength": 0.75
    # }

    verdict_reasoning_trail: Optional[Dict[str, str]] = Field(default=None, sa_column=Column(JSON))
    # {
    #   "step1_factcheck": "Found 1 existing fact-check from Full Fact",
    #   "step2_retrieval": "Retrieved 8 sources, deduplicated to 5",
    #   "step3_credibility": "Quality: 2 high-credibility (≥75%), 3 medium (60-74%)",
    #   "step4_consensus": "Consensus strength: 75%",
    #   "step5_verdict": "Verdict: supported"
    # }

    evidence_influence_scores: Optional[Dict[str, float]] = Field(default=None, sa_column=Column(JSON))
    # {"evidence_id_1": 0.35, "evidence_id_2": 0.25}  # Normalized to sum=1.0
```

### Implementation Files

**Files to Modify:**
1. `backend/app/models/check.py` — Add transparency fields
2. `backend/app/pipeline/judge.py` — Build evidence breakdown + reasoning trail + influence scores

**Frontend Files to Create:**
1. `web/components/check-detail/evidence-transparency-panel.tsx` — Credibility breakdown UI
2. `web/components/check-detail/reasoning-trail.tsx` — Step-by-step reasoning UI

### Testing Requirements
- Verify evidence breakdown counts are accurate
- Verify reasoning trail is clear and logical
- Verify influence scores sum to 1.0

---

## 📊 Database Migration Summary

### New Tables Required

```sql
-- User reputation appeals
CREATE TABLE reputation_appeal (
    id VARCHAR PRIMARY KEY,
    domain VARCHAR NOT NULL,
    user_id VARCHAR NOT NULL REFERENCES "user"(id),
    current_risk_level VARCHAR NOT NULL,
    appeal_reason TEXT NOT NULL,
    supporting_evidence_urls JSON NOT NULL,
    status VARCHAR DEFAULT 'pending',
    admin_notes TEXT,
    reviewed_by VARCHAR,
    reviewed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_reputation_appeal_domain ON reputation_appeal(domain);
CREATE INDEX idx_reputation_appeal_user ON reputation_appeal(user_id);
```

### Schema Modifications Required

```sql
-- Expand verdict enum
ALTER TYPE verdict_enum ADD VALUE 'insufficient_evidence';
ALTER TYPE verdict_enum ADD VALUE 'conflicting_expert_opinion';
ALTER TYPE verdict_enum ADD VALUE 'needs_primary_source';
ALTER TYPE verdict_enum ADD VALUE 'outdated_claim';
ALTER TYPE verdict_enum ADD VALUE 'lacks_context';

-- Add columns to check table
ALTER TABLE "check" ADD COLUMN abstention_reason TEXT;
ALTER TABLE "check" ADD COLUMN min_requirements_met BOOLEAN DEFAULT FALSE;
ALTER TABLE "check" ADD COLUMN verdict_reasoning TEXT;
ALTER TABLE "check" ADD COLUMN evidence_breakdown JSON;
ALTER TABLE "check" ADD COLUMN verdict_reasoning_trail JSON;
ALTER TABLE "check" ADD COLUMN evidence_influence_scores JSON;

-- Add columns to evidence table
ALTER TABLE evidence ADD COLUMN parent_company TEXT;
ALTER TABLE evidence ADD COLUMN independence_flag TEXT;
ALTER TABLE evidence ADD COLUMN content_similarity_score FLOAT;
ALTER TABLE evidence ADD COLUMN ownership_group_size INT DEFAULT 1;
ALTER TABLE evidence ADD COLUMN is_factcheck BOOLEAN DEFAULT FALSE;
ALTER TABLE evidence ADD COLUMN factcheck_publisher TEXT;
ALTER TABLE evidence ADD COLUMN factcheck_rating TEXT;
ALTER TABLE evidence ADD COLUMN factcheck_date TIMESTAMP;
ALTER TABLE evidence ADD COLUMN source_type TEXT;
ALTER TABLE evidence ADD COLUMN base_domain_credibility FLOAT DEFAULT 0.6;
ALTER TABLE evidence ADD COLUMN page_quality_multiplier FLOAT DEFAULT 1.0;
ALTER TABLE evidence ADD COLUMN reputation_adjustment FLOAT DEFAULT 1.0;
ALTER TABLE evidence ADD COLUMN independence_penalty FLOAT DEFAULT 1.0;
ALTER TABLE evidence ADD COLUMN quality_signals JSON;
ALTER TABLE evidence ADD COLUMN risk_level TEXT;
ALTER TABLE evidence ADD COLUMN risk_flags JSON;
ALTER TABLE evidence ADD COLUMN reputation_sources JSON;
ALTER TABLE evidence ADD COLUMN risk_reasoning TEXT;
ALTER TABLE evidence ADD COLUMN search_rank INT;
ALTER TABLE evidence ADD COLUMN retrieval_method TEXT;
ALTER TABLE evidence ADD COLUMN author TEXT;
ALTER TABLE evidence ADD COLUMN publisher_type TEXT;
```

### Migration Command

```bash
cd backend
alembic revision -m "credibility_system_enhancements"
alembic upgrade head
```

---

## 🧪 Testing Strategy

### Unit Tests Required

**Per Area:**
1. **Abstention Logic** — Test all abstention triggers
2. **Fact-Check API** — Test API integration + fallback
3. **Credibility Config** — Test all tier matches
4. **Independence Checking** — Test ownership + duplicate detection
5. **Page Quality** — Test all signal detections
6. **Diversity Selection** — Test category constraints

### Integration Tests Required

**End-to-End Scenarios:**
1. **Known False Claim** → Should find fact-checks, return "contradicted"
2. **Weak Evidence** → Should abstain with "insufficient_evidence"
3. **Propaganda Source** → Should flag and reduce credibility
4. **Duplicate Content** → Should deduplicate and penalize
5. **Conflicting High-Quality Sources** → Should flag "conflicting_expert_opinion"

### Manual Test Cases

**Must Test:**
- "The Earth is flat" → Contradicted (multiple fact-checks)
- "Drinking 8 glasses of water daily is necessary" → Uncertain or lacks_context
- "Mayor of obscure town resigned yesterday" → insufficient_evidence (too few sources)
- Claim from RT.com article → Source flagged, credibility reduced

---

## 🚀 Phased Implementation Plan

### Phase 1: Core Credibility (Weeks 1-2) 🔴 CRITICAL

**Week 1:**
1. ✅ Consensus & Abstention Logic (Area 1)
2. ✅ Fact-Check Integration (Area 2)
3. ✅ Database migration for verdict enum + abstention fields

**Week 2:**
4. ✅ Domain Credibility Config (Area 3)
5. ✅ Basic reputation checking (blacklist only)
6. ✅ Integration testing

**Deliverable:** Pipeline that abstains when evidence is weak and prioritizes fact-checks

---

### Phase 2: Source Quality (Weeks 3-4) 🟡 HIGH PRIORITY

**Week 3:**
7. ✅ Source Independence Checking (Area 4)
8. ✅ Page-Level Quality Analysis (Area 5)

**Week 4:**
9. ✅ Search Diversity Requirements (Area 6)
10. ✅ Full integration testing

**Deliverable:** Evidence scored with multi-factor credibility, duplicates removed, diverse sources

---

### Phase 3: Transparency (Weeks 5-6) 🟢 IMPORTANT

**Week 5:**
11. ✅ Verdict Transparency (Area 7)
12. ✅ Frontend transparency components

**Week 6:**
13. ✅ Full system testing
14. ✅ User acceptance testing
15. ✅ Performance optimization

**Deliverable:** Users can audit full reasoning trail with credibility breakdowns

---

## 📈 Success Metrics

### Quality Metrics (Accuracy)
- **Abstention Rate:** 15-25% (shows we don't guess)
- **Fact-Check Hit Rate:** 30%+ of claims have existing fact-checks
- **Source Diversity:** Average 3.5+ categories per check
- **High-Credibility Evidence:** 60%+ of evidence ≥75% credibility

### Trust Metrics (User Confidence)
- **Transparency Engagement:** 40%+ users expand evidence details
- **Appeal Rate:** <2% of verdicts (shows system is fair)
- **Verdict Reversal Rate:** <5% (shows we're accurate first time)

### Performance Metrics
- **Pipeline Latency:** <30 seconds acceptable (accuracy > speed)
- **Token Cost:** <$0.03 per check (was $0.02, +50% acceptable for quality)
- **API Response Time:** <300ms p95 (was <200ms, +50% acceptable)

---

## 🚨 Safety & Compliance

### Legal Requirements

**Fair Use / Fair Dealing:**
- Store only verdict summaries + URLs (never full article text)
- Proper attribution: "According to [Publisher] ([Date]): [Rating]"
- Legal review required before public launch
- UK/US jurisdictions compliance

**Citation Standards:**
- Full citation format: Source, Title, Author (if available), Date, URL
- Graceful fallback if fields missing: "citation data incomplete"
- Never interrupt pipeline due to citation failures

### Bias Mitigation

**Ideological Balance:**
- Maintain geographic diversity in source tiers
- Include international sources (US, UK, EU, Global South)
- Avoid US-centric or UK-centric bias

**Update Governance:**
- Monthly review of `source_credibility.json`
- Version control tracked changes
- Requires senior approval for tier changes

### Feature Toggles (Env Flags)

```bash
# backend/.env
ENABLE_FACTCHECK=true
ENABLE_CREDIBILITY_CONFIG=true
ENABLE_INDEPENDENCE_CHECK=true
ENABLE_PAGE_QUALITY_ANALYSIS=true
ENABLE_REPUTATION_APPEALS=true
```

### Fail-Safe Requirements

**Every new component must:**
1. Have fallback mechanism (primary → secondary → mock/skip)
2. Log failures without crashing pipeline
3. Degrade gracefully (return "uncertain" not error)
4. Maintain explainability even on partial failure

**Example:**
```python
try:
    factcheck_results = await factcheck_aggregator.search_factchecks(claim_text)
except Exception as e:
    logger.warning(f"Fact-check API failed: {e}, continuing without fact-checks")
    factcheck_results = []
```

---

## 🔧 Development Standards

### Code Quality

**Modular Services:**
- All new logic lives in isolated services (`backend/app/services/`)
- Never inline large code blocks in pipeline
- Single Responsibility Principle

**Reuse Infrastructure:**
- Use existing cache service (Redis)
- Use existing logging infrastructure
- Use existing telemetry (if any)

**Defensive Programming:**
- Handle missing data gracefully (never crash on nulls)
- Validate all inputs (Pydantic models)
- Type hints everywhere (`typing` module)

### Documentation

**Every new function must have:**
- Docstring with purpose
- Parameter descriptions
- Return value description
- Example usage (if complex)

**Example:**
```python
def check_independence(self, evidence_list: List[Evidence]) -> List[Evidence]:
    """
    Analyze source independence and deduplicate

    Args:
        evidence_list: List of evidence to check for independence

    Returns:
        Deduplicated evidence list with independence flags applied

    Example:
        >>> evidence = [Evidence(url='dailymail.co.uk/...'), Evidence(url='metro.co.uk/...')]
        >>> checker.check_independence(evidence)
        [Evidence(parent_company='DMGT', independence_flag='shared_ownership')]
    """
```

### Testing Philosophy

**Priorities:**
1. **Correctness** — Test that logic is accurate
2. **Edge Cases** — Test with 0, 1, many inputs
3. **Failure Modes** — Test graceful degradation
4. **Performance** — Only after correctness proven

**Coverage Target:** >80% for new services

---

## 🎯 Final Implementation Checklist

### Before Starting Implementation

- [ ] All stakeholders reviewed this plan
- [ ] Database backup created
- [ ] Staging environment ready
- [ ] API keys acquired (Google Fact Check)
- [ ] Dependencies approved (sentence-transformers, scikit-learn)

### Phase 1 Definition of Done

- [ ] Verdict enum expanded with 5 new categories
- [ ] Abstention logic implemented and tested
- [ ] Fact-check API integrated
- [ ] Minimum source requirements enforced
- [ ] All Phase 1 unit tests passing
- [ ] Integration test: Known false claim → contradicted

### Phase 2 Definition of Done

- [ ] Source credibility config file created
- [ ] Ownership database populated (top 50 media companies)
- [ ] Independence checking service implemented
- [ ] Page quality analysis implemented
- [ ] All Phase 2 unit tests passing
- [ ] Integration test: Duplicate sources → deduplicated

### Phase 3 Definition of Done

- [ ] Evidence breakdown stored in database
- [ ] Reasoning trail generated for all verdicts
- [ ] Frontend transparency components built
- [ ] All Phase 3 unit tests passing
- [ ] User acceptance testing completed
- [ ] Performance benchmarks met

---

## 📝 Notes & Considerations

### Not Included in This Plan

**Deferred Features:**
1. **Source Leaderboard** — Legal/reputational risk, needs further discussion
2. **Red-Flag Classifier** — Keyword-based detection is brittle, covered by page quality analysis
3. **Temporal Context Awareness** — Over-engineered for MVP, basic recency weighting sufficient
4. **Advanced NLI Models** — Current BART-large-mnli is sufficient, GPU requirements unnecessary

**Rationale:** Focus on high-impact, low-risk improvements that directly prevent misinformation validation.

### Open Questions for Product Team

1. **Abstention Rate Target:** Is 15-25% acceptable? Higher = more cautious but fewer answers
2. **Latency Tolerance:** Confirmed 20-30 seconds acceptable for accuracy?
3. **Blacklist Transparency:** Show risk flags to users or keep internal only?
4. **Appeal System:** Build immediately or Phase 4?

---

## ✅ Approval & Sign-Off

**Plan Status:** Under Review
**Next Step:** Stakeholder approval → Phase 1 implementation kickoff

**Prepared By:** Technical Team
**Review Required By:** Product Owner, Engineering Lead, Legal (for fact-check integration)

---

**End of Document**

*This plan represents a comprehensive, safety-first approach to transforming Tru8's verification pipeline into a transparent, auditable, defensible credibility engine. All recommendations are grounded in existing codebase analysis and industry best practices for fact-checking platforms.*
