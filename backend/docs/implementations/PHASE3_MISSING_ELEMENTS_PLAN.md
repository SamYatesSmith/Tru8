# Phase 3: Missing Critical Elements Implementation Plan

**Date:** 2025-10-20
**Status:** Ready to Implement
**Priority:** CRITICAL - Required before public launch
**Duration:** 3 weeks (Weeks 8-10)

---

## Executive Summary

Based on overlap analysis, **2 critical security features** and **3 medium-priority enhancements** are missing from the current pipeline implementation. These gaps leave Tru8 vulnerable to the exact scenario the credibility plan was designed to prevent:

> *"If Tru8 starts saying that some of the things Trump, or other liars start selling as TRUTH, then Tru8 will never work."*

This plan addresses those gaps in priority order.

---

## Critical Gaps Identified

### ❌ Gap 1: Consensus & Abstention Logic (CRITICAL)
**Impact:** Pipeline can validate claims with insufficient or weak evidence
**Risk:** High - Can return "supported" with single low-quality source

### ❌ Gap 2: Domain Credibility Framework (CRITICAL)
**Impact:** All sources treated equally (Wikipedia = RT.com = propaganda sites)
**Risk:** High - No defense against misinformation outlets ranking high in search

### 🟡 Gap 3: Independence Enforcement (MEDIUM)
**Impact:** Ownership tracked but not limited (5 DailyMail articles = "5 independent sources")
**Risk:** Medium - Echo chambers not prevented

### 🟡 Gap 4: Page-Level Quality Analysis (MEDIUM)
**Impact:** BBC news = BBC entertainment gossip in scoring
**Risk:** Medium - Missing article-level nuance

### 🟡 Gap 5: Search Diversity Enforcement (MEDIUM)
**Impact:** No category diversity requirements enforced
**Risk:** Low - All evidence could be from same category

---

## Phase 3 Implementation Plan

### Timeline Overview

```
Week 8:     Consensus & Abstention Logic
Week 9:     Domain Credibility Framework
Week 10:    Independence Enforcement + Testing
```

**Total Duration:** 3 weeks
**Total New Code:** ~2,800 lines
**Database Changes:** 1 migration (12 new fields)
**Test Coverage:** 53 new unit tests

---

## Week 8: Consensus & Abstention Logic

### Objective
Never force a verdict when evidence is weak or conflicting.

### Current Vulnerability

**File:** `backend/app/pipeline/judge.py:270-309`
```python
def _fallback_judgment(self, verification_signals):
    supporting = signals.get('supporting_count', 0)  # Could be 1!
    if supporting > contradicting + 1:
        verdict = "supported"  # DANGEROUS - single source can validate
```

**Problem:** Always returns verdict, even with:
- Only 1 source
- All sources <60% credibility
- Conflicting high-credibility sources

### Implementation Tasks

#### Task 1.1: Expand Verdict Enum (2 hours)

**File:** `backend/app/models/check.py`

**Changes:**
```python
from sqlalchemy import Enum as SQLEnum

class Claim(SQLModel, table=True):
    verdict: Optional[str] = Field(
        default=None,
        sa_column=Column(
            SQLEnum(
                # Existing verdicts
                "supported",
                "contradicted",
                "uncertain",

                # NEW VERDICTS - Phase 3
                "insufficient_evidence",        # <3 sources or no high-credibility
                "conflicting_expert_opinion",   # High-quality sources disagree
                "needs_primary_source",         # Only secondary sources found
                "outdated_claim",               # Was true, circumstances changed
                "lacks_context",                # Technically true but misleading

                name="verdict_enum",
                create_constraint=True
            )
        )
    )

    # NEW FIELDS
    abstention_reason: Optional[str] = Field(default=None)
    min_requirements_met: bool = Field(default=False)
    consensus_strength: Optional[float] = Field(default=None, ge=0, le=1)
```

#### Task 1.2: Database Migration (1 hour)

**Migration File:** `backend/alembic/versions/[timestamp]_add_abstention_logic.py`

```python
"""add abstention logic

Revision ID: [auto-generated]
"""

def upgrade():
    # Add new verdict values to enum
    op.execute("""
        ALTER TYPE verdict_enum ADD VALUE 'insufficient_evidence';
        ALTER TYPE verdict_enum ADD VALUE 'conflicting_expert_opinion';
        ALTER TYPE verdict_enum ADD VALUE 'needs_primary_source';
        ALTER TYPE verdict_enum ADD VALUE 'outdated_claim';
        ALTER TYPE verdict_enum ADD VALUE 'lacks_context';
    """)

    # Add new columns to claim table
    op.add_column('claim', sa.Column('abstention_reason', sa.Text(), nullable=True))
    op.add_column('claim', sa.Column('min_requirements_met', sa.Boolean(), server_default='false'))
    op.add_column('claim', sa.Column('consensus_strength', sa.Float(), nullable=True))

def downgrade():
    op.drop_column('claim', 'consensus_strength')
    op.drop_column('claim', 'min_requirements_met')
    op.drop_column('claim', 'abstention_reason')
    # Note: Cannot remove enum values in PostgreSQL without recreating type
```

#### Task 1.3: Implement Abstention Logic (8 hours)

**File:** `backend/app/pipeline/judge.py`

**New Method:**
```python
class JudgeService:
    # Configuration
    MIN_SOURCES_FOR_VERDICT = 3
    MIN_HIGH_CREDIBILITY_SOURCES = 1
    MIN_CREDIBILITY_THRESHOLD = 0.75
    MIN_CONSENSUS_STRENGTH = 0.65

    def _should_abstain(
        self,
        evidence: List[Evidence],
        verification_signals: Dict[str, Any]
    ) -> Optional[Tuple[str, str]]:
        """
        Determine if we should abstain from making a verdict.

        Returns:
            Tuple[verdict, reason] if should abstain, None otherwise
        """
        # Check 1: Too few sources
        if len(evidence) < self.MIN_SOURCES_FOR_VERDICT:
            return (
                "insufficient_evidence",
                f"Only {len(evidence)} source(s) found. Need at least {self.MIN_SOURCES_FOR_VERDICT} for reliable verdict."
            )

        # Check 2: No authoritative sources
        high_cred_sources = [e for e in evidence if e.credibility_score >= self.MIN_CREDIBILITY_THRESHOLD]
        if len(high_cred_sources) < self.MIN_HIGH_CREDIBILITY_SOURCES:
            max_cred = max([e.credibility_score for e in evidence]) if evidence else 0
            return (
                "insufficient_evidence",
                f"No high-credibility sources (≥{self.MIN_CREDIBILITY_THRESHOLD:.0%}). "
                f"Highest credibility: {max_cred:.0%}. Need authoritative sources for verdict."
            )

        # Check 3: Weak consensus
        consensus_strength = self._calculate_consensus_strength(evidence, verification_signals)
        if consensus_strength < self.MIN_CONSENSUS_STRENGTH:
            return (
                "conflicting_expert_opinion",
                f"Evidence shows weak consensus ({consensus_strength:.0%}). "
                f"High-credibility sources disagree on this claim."
            )

        # Check 4: Conflicting high-credibility sources
        high_cred_supporting = sum(1 for e in high_cred_sources if e.stance == 'supporting')
        high_cred_contradicting = sum(1 for e in high_cred_sources if e.stance == 'contradicting')

        if high_cred_supporting > 0 and high_cred_contradicting > 0:
            return (
                "conflicting_expert_opinion",
                f"High-credibility sources conflict: {high_cred_supporting} support, "
                f"{high_cred_contradicting} contradict. Expert opinion divided."
            )

        # Check 5: Temporal issues (claim was true, now outdated)
        if verification_signals.get('temporal_flag') == 'outdated':
            return (
                "outdated_claim",
                "Claim may have been accurate historically, but circumstances have changed. "
                "Evidence suggests this is no longer current."
            )

        # No abstention needed
        return None

    def _calculate_consensus_strength(
        self,
        evidence: List[Evidence],
        verification_signals: Dict[str, Any]
    ) -> float:
        """
        Calculate consensus strength using credibility-weighted agreement.

        Returns:
            Float 0-1 representing strength of consensus
        """
        if not evidence:
            return 0.0

        # Weight votes by credibility
        supporting_weight = sum(
            e.credibility_score
            for e in evidence
            if verification_signals.get(e.id, {}).get('stance') == 'supporting'
        )

        contradicting_weight = sum(
            e.credibility_score
            for e in evidence
            if verification_signals.get(e.id, {}).get('stance') == 'contradicting'
        )

        total_weight = supporting_weight + contradicting_weight

        if total_weight == 0:
            return 0.0

        # Consensus = majority weight / total weight
        majority_weight = max(supporting_weight, contradicting_weight)
        consensus = majority_weight / total_weight

        return consensus

    async def judge_claim(
        self,
        claim: Claim,
        evidence: List[Evidence],
        verification_signals: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Enhanced judge method with abstention logic.
        """
        # CHECK FOR ABSTENTION FIRST
        abstention = self._should_abstain(evidence, verification_signals)

        if abstention:
            verdict, reason = abstention
            return {
                'verdict': verdict,
                'confidence': 0.0,  # No confidence when abstaining
                'rationale': reason,
                'abstention_reason': reason,
                'min_requirements_met': False,
                'consensus_strength': self._calculate_consensus_strength(evidence, verification_signals)
            }

        # Minimum requirements met - proceed with normal judgment
        consensus_strength = self._calculate_consensus_strength(evidence, verification_signals)

        # ... existing judgment logic ...

        return {
            'verdict': final_verdict,
            'confidence': confidence_score,
            'rationale': rationale,
            'abstention_reason': None,
            'min_requirements_met': True,
            'consensus_strength': consensus_strength
        }
```

#### Task 1.4: Update Pipeline Worker (2 hours)

**File:** `backend/app/workers/pipeline.py`

**Changes:**
```python
# In run_verification_check function, around line 250

judgment = await judge.judge_claim(claim, evidence, verification_signals)

# Save abstention fields
claim.abstention_reason = judgment.get('abstention_reason')
claim.min_requirements_met = judgment.get('min_requirements_met', False)
claim.consensus_strength = judgment.get('consensus_strength')
```

#### Task 1.5: Feature Flag (30 minutes)

**File:** `backend/app/core/config.py`

```python
class Settings(BaseSettings):
    # Phase 3 - Consensus & Abstention
    ENABLE_ABSTENTION_LOGIC: bool = Field(False, env="ENABLE_ABSTENTION_LOGIC")

    # Abstention thresholds (configurable)
    MIN_SOURCES_FOR_VERDICT: int = Field(3, env="MIN_SOURCES_FOR_VERDICT")
    MIN_CREDIBILITY_THRESHOLD: float = Field(0.75, env="MIN_CREDIBILITY_THRESHOLD")
    MIN_CONSENSUS_STRENGTH: float = Field(0.65, env="MIN_CONSENSUS_STRENGTH")
```

**File:** `backend/.env`

```bash
# Phase 3: Consensus & Abstention Logic
ENABLE_ABSTENTION_LOGIC=false

# Thresholds (defaults shown)
MIN_SOURCES_FOR_VERDICT=3
MIN_CREDIBILITY_THRESHOLD=0.75
MIN_CONSENSUS_STRENGTH=0.65
```

#### Task 1.6: Unit Tests (6 hours)

**File:** `backend/tests/unit/test_abstention_logic.py`

**Test Coverage:**
```python
import pytest
from app.pipeline.judge import JudgeService
from app.models.check import Evidence

class TestAbstentionLogic:

    def test_abstains_with_too_few_sources(self):
        """Should abstain when <3 sources"""
        evidence = [Evidence(credibility_score=0.9, url="test.com")]
        judge = JudgeService()

        result = judge._should_abstain(evidence, {})

        assert result is not None
        verdict, reason = result
        assert verdict == "insufficient_evidence"
        assert "Only 1 source" in reason

    def test_abstains_with_no_high_credibility_sources(self):
        """Should abstain when all sources <75% credibility"""
        evidence = [
            Evidence(credibility_score=0.6, url="a.com"),
            Evidence(credibility_score=0.65, url="b.com"),
            Evidence(credibility_score=0.7, url="c.com"),
        ]
        judge = JudgeService()

        result = judge._should_abstain(evidence, {})

        assert result is not None
        verdict, reason = result
        assert verdict == "insufficient_evidence"
        assert "No high-credibility sources" in reason

    def test_abstains_with_weak_consensus(self):
        """Should abstain when consensus <65%"""
        evidence = [
            Evidence(id="1", credibility_score=0.9, url="a.com"),
            Evidence(id="2", credibility_score=0.85, url="b.com"),
            Evidence(id="3", credibility_score=0.8, url="c.com"),
        ]
        signals = {
            "1": {"stance": "supporting"},
            "2": {"stance": "contradicting"},
            "3": {"stance": "neutral"}
        }
        judge = JudgeService()

        result = judge._should_abstain(evidence, signals)

        assert result is not None
        verdict, reason = result
        assert verdict == "conflicting_expert_opinion"

    def test_abstains_with_conflicting_high_credibility_sources(self):
        """Should abstain when tier1 sources disagree"""
        evidence = [
            Evidence(id="1", credibility_score=0.9, url="reuters.com"),
            Evidence(id="2", credibility_score=0.9, url="bbc.co.uk"),
            Evidence(id="3", credibility_score=0.8, url="guardian.com"),
        ]
        signals = {
            "1": {"stance": "supporting"},
            "2": {"stance": "contradicting"},
            "3": {"stance": "supporting"}
        }
        judge = JudgeService()

        result = judge._should_abstain(evidence, signals)

        assert result is not None
        verdict, reason = result
        assert verdict == "conflicting_expert_opinion"
        assert "High-credibility sources conflict" in reason

    def test_proceeds_with_sufficient_evidence(self):
        """Should NOT abstain when requirements met"""
        evidence = [
            Evidence(id="1", credibility_score=0.9, url="a.com"),
            Evidence(id="2", credibility_score=0.85, url="b.com"),
            Evidence(id="3", credibility_score=0.8, url="c.com"),
        ]
        signals = {
            "1": {"stance": "supporting"},
            "2": {"stance": "supporting"},
            "3": {"stance": "supporting"}
        }
        judge = JudgeService()

        result = judge._should_abstain(evidence, signals)

        assert result is None  # No abstention

    def test_consensus_strength_calculation(self):
        """Test credibility-weighted consensus"""
        evidence = [
            Evidence(id="1", credibility_score=0.9, url="a.com"),
            Evidence(id="2", credibility_score=0.6, url="b.com"),
        ]
        signals = {
            "1": {"stance": "supporting"},    # 0.9 weight
            "2": {"stance": "contradicting"}  # 0.6 weight
        }
        judge = JudgeService()

        consensus = judge._calculate_consensus_strength(evidence, signals)

        # 0.9 / (0.9 + 0.6) = 0.6 (60% consensus)
        assert abs(consensus - 0.6) < 0.01

    # ... 8 more tests covering edge cases, outdated claims, etc.
```

**Total Tests:** 15 unit tests

---

## Week 9: Domain Credibility Framework

### Objective
Replace default 0.6 credibility with tiered, transparent source reputation system.

### Current Vulnerability

**File:** `backend/app/models/check.py:49`
```python
credibility_score: float = Field(default=0.6, ge=0, le=1)
```

**File:** `backend/app/pipeline/retrieve.py:194-219` (inline dict)
```python
DOMAIN_CREDIBILITY = {
    'bbc.co.uk': 0.9,
    'reuters.com': 0.9,
    'apnews.com': 0.9,
    'theguardian.com': 0.8,
}
# Only ~6 domains hardcoded!
```

**Problem:**
- Wikipedia (0.6) = RT.com (0.6) = propaganda sites (0.6)
- No blacklist for known misinformation
- No risk flags for state media
- No governance process for adding sources

### Implementation Tasks

#### Task 2.1: Create Source Credibility Config (4 hours)

**File:** `backend/app/data/source_credibility.json` (NEW)

```json
{
  "academic": {
    "credibility": 1.0,
    "description": "Educational and research institutions",
    "domains": [
      "*.edu",
      "*.ac.uk",
      "*.edu.au",
      "mit.edu",
      "stanford.edu",
      "ox.ac.uk",
      "cam.ac.uk",
      "harvard.edu",
      "ethz.ch"
    ],
    "tier": "tier1"
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
      "ons.gov.uk",
      "fda.gov",
      "epa.gov",
      "nasa.gov"
    ],
    "tier": "tier1"
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
      "bmj.com",
      "plos.org",
      "arxiv.org"
    ],
    "tier": "tier1"
  },

  "news_tier1": {
    "credibility": 0.9,
    "description": "Highest-rated international news agencies",
    "domains": [
      "bbc.co.uk",
      "bbc.com",
      "reuters.com",
      "apnews.com",
      "ap.org",
      "afp.com"
    ],
    "tier": "tier1"
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
      "nytimes.com",
      "wsj.com",
      "cnn.com",
      "npr.org",
      "pbs.org"
    ],
    "tier": "tier2"
  },

  "reference": {
    "credibility": 0.85,
    "description": "Reference and knowledge bases",
    "domains": [
      "wikipedia.org",
      "britannica.com",
      "archive.org"
    ],
    "tier": "tier1"
  },

  "factcheck": {
    "credibility": 0.95,
    "description": "Professional fact-checking organizations (IFCN signatories)",
    "domains": [
      "snopes.com",
      "factcheck.org",
      "fullfact.org",
      "politifact.com",
      "apnews.com/APFactCheck",
      "reuters.com/fact-check",
      "afp.com/factcheck"
    ],
    "tier": "tier1"
  },

  "blacklist": {
    "credibility": 0.2,
    "description": "Known misinformation sources",
    "domains": [
      "infowars.com",
      "naturalnews.com",
      "beforeitsnews.com",
      "yournewswire.com",
      "newspunch.com"
    ],
    "risk_flags": [
      "conspiracy_theories",
      "multiple_failed_fact_checks",
      "medical_misinformation"
    ],
    "auto_exclude": false,
    "tier": "blacklist"
  },

  "state_media": {
    "credibility": 0.5,
    "description": "State-sponsored media with editorial independence concerns",
    "domains": [
      "rt.com",
      "sputniknews.com",
      "presstv.ir",
      "cgtn.com",
      "xinhuanet.com"
    ],
    "risk_flags": [
      "state_sponsored",
      "propaganda_concerns",
      "editorial_independence_questioned"
    ],
    "auto_exclude": false,
    "tier": "flagged"
  },

  "satire": {
    "credibility": 0.0,
    "description": "Satirical content - intentionally fictional",
    "domains": [
      "theonion.com",
      "newsthump.com",
      "thedailymash.co.uk",
      "clickhole.com"
    ],
    "risk_flags": ["satire"],
    "auto_exclude": true,
    "tier": "excluded"
  },

  "general": {
    "credibility": 0.6,
    "description": "Default for unmatched sources",
    "tier": "general"
  }
}
```

#### Task 2.2: Create Credibility Service (6 hours)

**File:** `backend/app/services/source_credibility.py` (NEW)

```python
import json
import tldextract
from pathlib import Path
from typing import Dict, Any, Optional, List
from app.core.config import settings

class SourceCredibilityService:
    """
    Centralized source credibility management.
    Single source of truth for domain reputation.
    """

    def __init__(self):
        config_path = Path(__file__).parent.parent / "data" / "source_credibility.json"
        with open(config_path, 'r') as f:
            self.config = json.load(f)

        # Cache for performance
        self._domain_cache: Dict[str, Dict[str, Any]] = {}

    def get_credibility(self, source: str, url: str) -> Dict[str, Any]:
        """
        Get credibility score and metadata for a source.

        Args:
            source: Source name (e.g., "BBC News")
            url: Full URL

        Returns:
            {
                'tier': 'news_tier1',
                'credibility': 0.9,
                'risk_flags': [],
                'auto_exclude': False,
                'reasoning': 'Matched news_tier1 tier',
                'description': 'Highest-rated international news agencies'
            }
        """
        # Extract domain
        parsed = tldextract.extract(url)
        domain = parsed.registered_domain.lower()

        # Check cache
        if domain in self._domain_cache:
            return self._domain_cache[domain]

        # Check each tier
        result = self._match_domain_to_tier(domain, parsed)

        # Cache result
        self._domain_cache[domain] = result

        return result

    def _match_domain_to_tier(self, domain: str, parsed) -> Dict[str, Any]:
        """Match domain against all tiers in config"""

        for tier_name, tier_config in self.config.items():
            if tier_name == 'general':
                continue  # Check general last

            # Check exact domain matches
            if 'domains' in tier_config:
                for pattern in tier_config['domains']:
                    if self._matches_pattern(domain, pattern, parsed):
                        return {
                            'tier': tier_name,
                            'credibility': tier_config['credibility'],
                            'risk_flags': tier_config.get('risk_flags', []),
                            'auto_exclude': tier_config.get('auto_exclude', False),
                            'reasoning': f"Matched {tier_name} tier (domain: {domain})",
                            'description': tier_config.get('description', '')
                        }

        # Default to general
        return {
            'tier': 'general',
            'credibility': self.config['general']['credibility'],
            'risk_flags': [],
            'auto_exclude': False,
            'reasoning': f'No specific tier matched, using general (domain: {domain})',
            'description': self.config['general']['description']
        }

    def _matches_pattern(self, domain: str, pattern: str, parsed) -> bool:
        """
        Check if domain matches pattern (supports wildcards)

        Examples:
            *.edu matches mit.edu, stanford.edu
            bbc.co.uk matches exactly
        """
        if pattern.startswith('*.'):
            # Wildcard pattern - match TLD suffix
            suffix = pattern[2:]  # Remove *.
            return domain.endswith(suffix)
        else:
            # Exact match
            return domain == pattern.lower()

    def should_exclude(self, url: str) -> bool:
        """Check if source should be auto-excluded (satire, etc.)"""
        cred_info = self.get_credibility("", url)
        return cred_info.get('auto_exclude', False)

    def get_risk_assessment(self, url: str) -> Dict[str, Any]:
        """
        Get detailed risk assessment for a source.

        Returns:
            {
                'risk_level': 'high' | 'medium' | 'low' | 'none',
                'risk_flags': ['state_sponsored', 'propaganda_concerns'],
                'should_flag_to_user': True,
                'warning_message': '...'
            }
        """
        cred_info = self.get_credibility("", url)
        risk_flags = cred_info.get('risk_flags', [])

        # Determine risk level
        if not risk_flags:
            risk_level = 'none'
        elif 'conspiracy_theories' in risk_flags or 'medical_misinformation' in risk_flags:
            risk_level = 'high'
        elif 'state_sponsored' in risk_flags or 'propaganda_concerns' in risk_flags:
            risk_level = 'medium'
        else:
            risk_level = 'low'

        # Generate warning message
        warning = None
        if risk_level == 'high':
            warning = f"Source has history of spreading misinformation ({', '.join(risk_flags)})"
        elif risk_level == 'medium':
            warning = f"Source editorial independence concerns ({', '.join(risk_flags)})"

        return {
            'risk_level': risk_level,
            'risk_flags': risk_flags,
            'should_flag_to_user': risk_level in ['high', 'medium'],
            'warning_message': warning
        }

    def get_tier_summary(self) -> Dict[str, int]:
        """Get count of domains in each tier (for admin dashboard)"""
        summary = {}
        for tier_name, tier_config in self.config.items():
            if 'domains' in tier_config:
                summary[tier_name] = len(tier_config['domains'])
        return summary
```

#### Task 2.3: Integrate into Retrieve Stage (4 hours)

**File:** `backend/app/pipeline/retrieve.py`

**Changes:**
```python
from app.services.source_credibility import SourceCredibilityService

class RetrieveService:
    def __init__(self):
        # ... existing init ...
        if settings.ENABLE_DOMAIN_CREDIBILITY_FRAMEWORK:
            self.credibility_service = SourceCredibilityService()

    async def _score_evidence(self, evidence: Evidence, claim: Claim) -> float:
        """Enhanced scoring with credibility framework"""

        # Get base credibility from framework (if enabled)
        if settings.ENABLE_DOMAIN_CREDIBILITY_FRAMEWORK:
            cred_info = self.credibility_service.get_credibility(
                evidence.source,
                evidence.url
            )

            base_credibility = cred_info['credibility']

            # Check for auto-exclusion (satire)
            if cred_info['auto_exclude']:
                return 0.0  # Exclude from results

            # Store metadata
            evidence.tier = cred_info['tier']
            evidence.risk_flags = cred_info.get('risk_flags', [])
            evidence.credibility_reasoning = cred_info['reasoning']

        else:
            # Fallback to old hardcoded dict (backward compatibility)
            base_credibility = self._get_legacy_credibility(evidence.url)

        # Apply existing multipliers (relevance, etc.)
        final_score = base_credibility * evidence.relevance_score

        return final_score
```

#### Task 2.4: Database Migration (1 hour)

**File:** `backend/alembic/versions/[timestamp]_add_credibility_framework_fields.py`

```python
def upgrade():
    # Add tier tracking
    op.add_column('evidence', sa.Column('tier', sa.Text(), nullable=True))
    op.add_column('evidence', sa.Column('risk_flags', sa.JSON(), nullable=True))
    op.add_column('evidence', sa.Column('credibility_reasoning', sa.Text(), nullable=True))

    # Add risk assessment fields
    op.add_column('evidence', sa.Column('risk_level', sa.Text(), nullable=True))
    op.add_column('evidence', sa.Column('risk_warning', sa.Text(), nullable=True))

def downgrade():
    op.drop_column('evidence', 'risk_warning')
    op.drop_column('evidence', 'risk_level')
    op.drop_column('evidence', 'credibility_reasoning')
    op.drop_column('evidence', 'risk_flags')
    op.drop_column('evidence', 'tier')
```

#### Task 2.5: Feature Flag (30 minutes)

**File:** `backend/app/core/config.py`

```python
ENABLE_DOMAIN_CREDIBILITY_FRAMEWORK: bool = Field(False, env="ENABLE_DOMAIN_CREDIBILITY_FRAMEWORK")
```

**File:** `backend/.env`

```bash
ENABLE_DOMAIN_CREDIBILITY_FRAMEWORK=false
```

#### Task 2.6: Unit Tests (6 hours)

**File:** `backend/tests/unit/test_source_credibility.py` (NEW)

**Test Coverage:**
```python
class TestSourceCredibilityService:

    def test_matches_academic_domain(self):
        service = SourceCredibilityService()
        result = service.get_credibility("MIT", "https://mit.edu/article")

        assert result['tier'] == 'academic'
        assert result['credibility'] == 1.0
        assert result['risk_flags'] == []

    def test_matches_wildcard_edu_pattern(self):
        service = SourceCredibilityService()
        result = service.get_credibility("Stanford", "https://stanford.edu/research")

        assert result['tier'] == 'academic'
        assert result['credibility'] == 1.0

    def test_matches_government_domain(self):
        service = SourceCredibilityService()
        result = service.get_credibility("CDC", "https://cdc.gov/health")

        assert result['tier'] == 'government'
        assert result['credibility'] == 0.85

    def test_matches_news_tier1(self):
        service = SourceCredibilityService()
        result = service.get_credibility("BBC", "https://bbc.co.uk/news/123")

        assert result['tier'] == 'news_tier1'
        assert result['credibility'] == 0.9

    def test_blacklist_low_credibility(self):
        service = SourceCredibilityService()
        result = service.get_credibility("InfoWars", "https://infowars.com/article")

        assert result['tier'] == 'blacklist'
        assert result['credibility'] == 0.2
        assert 'conspiracy_theories' in result['risk_flags']
        assert result['auto_exclude'] == False  # Track but don't exclude

    def test_state_media_flagged(self):
        service = SourceCredibilityService()
        result = service.get_credibility("RT", "https://rt.com/news/123")

        assert result['tier'] == 'state_media'
        assert result['credibility'] == 0.5
        assert 'state_sponsored' in result['risk_flags']

    def test_satire_auto_excluded(self):
        service = SourceCredibilityService()
        result = service.get_credibility("The Onion", "https://theonion.com/funny")

        assert result['tier'] == 'satire'
        assert result['credibility'] == 0.0
        assert result['auto_exclude'] == True

    def test_should_exclude_satire(self):
        service = SourceCredibilityService()
        assert service.should_exclude("https://theonion.com/article") == True
        assert service.should_exclude("https://bbc.co.uk/news") == False

    def test_general_fallback_for_unknown_domain(self):
        service = SourceCredibilityService()
        result = service.get_credibility("Unknown Blog", "https://randomblog.com/post")

        assert result['tier'] == 'general'
        assert result['credibility'] == 0.6
        assert result['risk_flags'] == []

    def test_risk_assessment_high_risk(self):
        service = SourceCredibilityService()
        risk = service.get_risk_assessment("https://infowars.com/article")

        assert risk['risk_level'] == 'high'
        assert risk['should_flag_to_user'] == True
        assert 'misinformation' in risk['warning_message'].lower()

    def test_risk_assessment_medium_risk(self):
        service = SourceCredibilityService()
        risk = service.get_risk_assessment("https://rt.com/news")

        assert risk['risk_level'] == 'medium'
        assert risk['should_flag_to_user'] == True

    def test_risk_assessment_no_risk(self):
        service = SourceCredibilityService()
        risk = service.get_risk_assessment("https://bbc.co.uk/news")

        assert risk['risk_level'] == 'none'
        assert risk['should_flag_to_user'] == False

    # ... 8 more tests for caching, edge cases, etc.
```

**Total Tests:** 20 unit tests

---

## Week 10: Independence Enforcement + Integration Testing

### Task 3.1: Enforce Ownership Limits (4 hours)

**File:** `backend/app/pipeline/retrieve.py`

**New Method:**
```python
def enforce_ownership_limits(self, evidence_list: List[Evidence]) -> List[Evidence]:
    """
    Limit evidence per ownership group to max 2 sources.
    Apply independence penalties for same-owner sources.
    """
    if not settings.ENABLE_SOURCE_DIVERSITY:
        return evidence_list

    MAX_PER_OWNER = 2
    SAME_OWNER_PENALTY = 0.7  # 30% penalty

    # Group by parent company
    ownership_groups = {}
    for evidence in evidence_list:
        owner = evidence.parent_company or "independent"
        if owner not in ownership_groups:
            ownership_groups[owner] = []
        ownership_groups[owner].append(evidence)

    # Keep top 2 per owner, apply penalties
    filtered_evidence = []

    for owner, group in ownership_groups.items():
        # Sort by credibility * relevance
        sorted_group = sorted(
            group,
            key=lambda e: e.credibility_score * e.relevance_score,
            reverse=True
        )

        # Keep max 2
        kept = sorted_group[:MAX_PER_OWNER]

        # Apply penalty if multiple from same owner
        if len(kept) > 1 and owner != "independent":
            for evidence in kept:
                evidence.independence_penalty = SAME_OWNER_PENALTY
                evidence.credibility_score *= SAME_OWNER_PENALTY
                evidence.independence_flag = "shared_ownership"
        else:
            for evidence in kept:
                evidence.independence_penalty = 1.0
                evidence.independence_flag = "independent"

        filtered_evidence.extend(kept)

    return filtered_evidence
```

### Task 3.2: Integration Testing (8 hours)

**File:** `backend/tests/integration/test_phase3_integration.py` (NEW)

**Scenarios:**
```python
class TestPhase3Integration:

    @pytest.mark.asyncio
    async def test_abstains_with_weak_evidence(self):
        """
        End-to-end test: Pipeline abstains when only 2 low-quality sources
        """
        # Submit claim with mock search returning 2 sources <75% credibility
        # Verify verdict = "insufficient_evidence"
        # Verify abstention_reason populated

    @pytest.mark.asyncio
    async def test_blacklist_source_low_credibility(self):
        """
        Test that blacklisted source gets 0.2 credibility
        """
        # Mock infowars.com result
        # Verify credibility = 0.2
        # Verify risk_flags = ["conspiracy_theories", ...]

    @pytest.mark.asyncio
    async def test_state_media_flagged(self):
        """
        Test that RT.com gets flagged with state_sponsored
        """
        # Mock rt.com result
        # Verify credibility = 0.5
        # Verify risk_flags contains "state_sponsored"

    @pytest.mark.asyncio
    async def test_ownership_limit_enforced(self):
        """
        Test that 5 DailyMail articles reduced to 2 max
        """
        # Mock 5 results from dailymail.co.uk, metro.co.uk (both DMGT)
        # Verify only 2 kept from DMGT group
        # Verify independence_penalty applied

    @pytest.mark.asyncio
    async def test_high_credibility_consensus_proceeds(self):
        """
        Test that 3 tier1 sources agreeing = verdict rendered
        """
        # Mock 3 BBC/Reuters/AP sources supporting claim
        # Verify min_requirements_met = True
        # Verify verdict = "supported"

    @pytest.mark.asyncio
    async def test_wikipedia_gets_85_percent_credibility(self):
        """
        Regression test: Wikipedia should be 0.85, not 0.6
        """
        # Mock wikipedia.org result
        # Verify credibility = 0.85
        # Verify tier = "reference"

    # ... 12 more integration tests
```

**Total Integration Tests:** 18 tests

### Task 3.3: Documentation (4 hours)

**Files to Create:**
1. `docs/credibility/CREDIBILITY_FRAMEWORK_GUIDE.md` - How the system works
2. `docs/credibility/ABSTENTION_LOGIC_GUIDE.md` - When and why we abstain
3. `docs/credibility/SOURCE_TIER_GUIDE.md` - Tier definitions and governance

---

## Database Migration Summary

### Total New Fields (Week 8-10)

**Claim table:**
- `abstention_reason` (TEXT)
- `min_requirements_met` (BOOLEAN)
- `consensus_strength` (FLOAT)

**Evidence table:**
- `tier` (TEXT)
- `risk_flags` (JSON)
- `credibility_reasoning` (TEXT)
- `risk_level` (TEXT)
- `risk_warning` (TEXT)
- `independence_penalty` (FLOAT) - already exists from Phase 1

**Total:** 9 new fields (3 migrations)

---

## Testing Summary

### Unit Tests by Week

| Week | Test File | Tests | Coverage |
|------|-----------|-------|----------|
| Week 8 | `test_abstention_logic.py` | 15 | Abstention triggers, consensus calculation |
| Week 9 | `test_source_credibility.py` | 20 | Tier matching, risk assessment, wildcards |
| Week 10 | `test_ownership_enforcement.py` | 8 | Limit enforcement, penalties |

**Total Unit Tests:** 43 tests

### Integration Tests (Week 10)

**File:** `test_phase3_integration.py`
**Tests:** 18 end-to-end scenarios
**Coverage:** Full pipeline with all Phase 3 features enabled

**Grand Total:** 43 unit + 18 integration = **61 new tests**

---

## Feature Flags Configuration

**File:** `backend/.env`

```bash
# Phase 3: Critical Missing Elements
ENABLE_ABSTENTION_LOGIC=false
ENABLE_DOMAIN_CREDIBILITY_FRAMEWORK=false
# ENABLE_SOURCE_DIVERSITY already exists from Phase 1

# Abstention Thresholds
MIN_SOURCES_FOR_VERDICT=3
MIN_CREDIBILITY_THRESHOLD=0.75
MIN_CONSENSUS_STRENGTH=0.65
```

---

## Rollout Strategy for Phase 3

### Week 11: Internal Testing
1. Enable abstention logic → test 50 checks
2. Enable credibility framework → test 50 checks
3. Enable ownership enforcement → test 50 checks

### Week 12: Gradual Rollout
1. Internal users (100%)
2. Beta users (20%) - Days 1-3
3. Expand to 50% - Days 4-7
4. Full rollout (100%) - Day 8

### Success Criteria
- ✅ Abstention rate: 15-25% (shows we don't guess)
- ✅ No blacklisted sources in final evidence
- ✅ Wikipedia credibility = 0.85 (not 0.6)
- ✅ Max 2 sources per ownership group
- ✅ No performance regression (p95 <12s)

---

## Risk Mitigation

### Backward Compatibility
- ✅ All features behind feature flags (default OFF)
- ✅ New database fields nullable
- ✅ Graceful fallback if config file missing
- ✅ Existing checks unaffected

### Rollback Procedures
**Instant (< 2 min):**
```bash
export ENABLE_ABSTENTION_LOGIC=false
export ENABLE_DOMAIN_CREDIBILITY_FRAMEWORK=false
# Restart servers
```

**Code Rollback (< 30 min):**
```bash
git revert [commit-hash]
# Redeploy
```

**Database Rollback:**
- Alembic downgrade migrations
- Data preserved (fields nullable)

---

## Expected Impact

### Before Phase 3
- ❌ Single low-quality source can validate claim
- ❌ All sources scored 0.6 (Wikipedia = propaganda)
- ❌ 5 articles from same owner = "5 independent sources"
- ❌ No protection against known misinformation sites

### After Phase 3
- ✅ Minimum 3 sources required
- ✅ At least 1 high-credibility source (≥75%) required
- ✅ Wikipedia = 0.85, RT.com = 0.5, InfoWars = 0.2
- ✅ Max 2 sources per ownership group
- ✅ Blacklisted sites flagged with risk warnings
- ✅ Abstains when evidence is weak/conflicting

### Performance Impact
- Latency: +300ms (credibility lookups cached)
- Token cost: No change
- Abstention rate: +15-20% (feature, not bug)

---

## Success Metrics

### Quality Improvements
- **Abstention rate:** 15-25% (shows we don't force verdicts)
- **High-credibility evidence:** 70%+ of evidence ≥75% credibility
- **Source diversity:** Max 2 per ownership group enforced
- **Risk flagging:** 100% of blacklisted sources flagged

### User Trust
- **Transparency:** Users see tier + risk flags
- **Confidence:** Fewer "contradicted" verdicts on weak evidence
- **Appeal rate:** <2% (shows fairness)

### Technical Metrics
- **Test coverage:** >85% on new code
- **Performance:** p95 <12s (within target)
- **Error rate:** <2% (baseline maintained)

---

## Deliverables Checklist

### Week 8: Abstention Logic
- [ ] Verdict enum expanded (5 new values)
- [ ] `_should_abstain()` method implemented
- [ ] Consensus strength calculation
- [ ] Database migration applied
- [ ] 15 unit tests passing
- [ ] Feature flag configured
- [ ] Documentation updated

### Week 9: Credibility Framework
- [ ] `source_credibility.json` created (200+ domains)
- [ ] `SourceCredibilityService` implemented
- [ ] Retrieve stage integration
- [ ] Database migration applied
- [ ] 20 unit tests passing
- [ ] Feature flag configured
- [ ] Tier governance process documented

### Week 10: Enforcement + Testing
- [ ] Ownership limit enforcement (max 2)
- [ ] Independence penalties applied
- [ ] 8 unit tests passing
- [ ] 18 integration tests passing
- [ ] Full system testing complete
- [ ] Documentation complete
- [ ] Rollout plan approved

---

## Conclusion

Phase 3 implementation addresses the **2 most critical security gaps** identified in the overlap analysis:

1. **Consensus & Abstention Logic** - Prevents weak evidence validation
2. **Domain Credibility Framework** - Prevents propaganda/misinformation source validation

Combined with Phase 1-2 features, this completes the vision from CREDIBILITY_ENHANCEMENT_PLAN.md to create a:

> "Transparent, auditable, defensible credibility engine"

**Total Implementation Time:** 3 weeks
**Total New Code:** ~2,800 lines
**Total Tests:** 61 new tests
**Database Changes:** 9 new fields

**Ready to proceed?** Start with Week 8: Consensus & Abstention Logic.
