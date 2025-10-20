# Tru8 Pipeline Implementation Guide
## All Phases: Structural + Semantic + UX

**Total Duration:** 7.5 weeks
**Implementation Order:** Logical sequence minimizing risk and dependencies

---

## PHASE 1: STRUCTURAL INTEGRITY (Weeks 1-3.5)

### WEEK 1: Domain Weight Inflation + Setup

#### Day 1: Branch & Feature Flags Setup

**Tasks:**
1. Create main feature branch
2. Add all feature flags to config.py
3. Set up test infrastructure
4. Create initial documentation

**Code Changes:**

**File:** `backend/app/core/config.py`
```python
# Add after existing settings (line 68)
# Pipeline Improvement Feature Flags
ENABLE_DOMAIN_CAPPING: bool = Field(False, env="ENABLE_DOMAIN_CAPPING")
ENABLE_DEDUPLICATION: bool = Field(False, env="ENABLE_DEDUPLICATION")
ENABLE_SOURCE_DIVERSITY: bool = Field(False, env="ENABLE_SOURCE_DIVERSITY")
ENABLE_CONTEXT_PRESERVATION: bool = Field(False, env="ENABLE_CONTEXT_PRESERVATION")
ENABLE_SAFETY_CHECKING: bool = Field(False, env="ENABLE_SAFETY_CHECKING")
ENABLE_CITATION_ARCHIVAL: bool = Field(False, env="ENABLE_CITATION_ARCHIVAL")
ENABLE_VERDICT_MONITORING: bool = Field(False, env="ENABLE_VERDICT_MONITORING")
ENABLE_FACTCHECK_API: bool = Field(False, env="ENABLE_FACTCHECK_API")
ENABLE_TEMPORAL_CONTEXT: bool = Field(False, env="ENABLE_TEMPORAL_CONTEXT")
ENABLE_CLAIM_CLASSIFICATION: bool = Field(False, env="ENABLE_CLAIM_CLASSIFICATION")
ENABLE_ENHANCED_EXPLAINABILITY: bool = Field(False, env="ENABLE_ENHANCED_EXPLAINABILITY")

# Domain Capping Configuration
MAX_EVIDENCE_PER_DOMAIN: int = Field(3, env="MAX_EVIDENCE_PER_DOMAIN")
DOMAIN_DIVERSITY_THRESHOLD: float = Field(0.6, env="DOMAIN_DIVERSITY_THRESHOLD")
```

#### Day 2-3: Domain Capping Implementation

**New File:** `backend/app/utils/domain_capping.py`
```python
from typing import List, Dict, Any
from urllib.parse import urlparse
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)

class DomainCapper:
    """Enforce maximum evidence per domain to prevent single-source dominance"""

    def __init__(self, max_per_domain: int = 3, max_domain_ratio: float = 0.4):
        self.max_per_domain = max_per_domain
        self.max_domain_ratio = max_domain_ratio

    def apply_caps(self, evidence: List[Dict[str, Any]], target_count: int = 5) -> List[Dict[str, Any]]:
        """
        Apply per-domain caps to evidence list.

        Rules:
        - Max 40% of evidence from single domain
        - Prefer highest-scored evidence from each domain
        - Maintain overall target count
        """
        if not evidence:
            return []

        # Calculate effective cap
        effective_cap = max(2, min(self.max_per_domain, int(target_count * self.max_domain_ratio)))

        domain_counts = defaultdict(int)
        capped_evidence = []

        # Evidence should already be sorted by score (descending)
        for ev in evidence:
            domain = self._extract_domain(ev['url'])

            if domain_counts[domain] < effective_cap:
                capped_evidence.append(ev)
                domain_counts[domain] += 1

                if len(capped_evidence) >= target_count:
                    break

        logger.info(f"Domain capping: {len(evidence)} → {len(capped_evidence)} sources. "
                   f"Distribution: {dict(domain_counts)}")

        return capped_evidence

    def _extract_domain(self, url: str) -> str:
        """Extract clean domain from URL"""
        try:
            domain = urlparse(url).netloc
            if domain.startswith('www.'):
                domain = domain[4:]
            return domain.lower()
        except:
            return "unknown"

    def get_diversity_metrics(self, evidence: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate domain diversity metrics"""
        if not evidence:
            return {"unique_domains": 0, "max_domain_ratio": 0, "diversity_score": 0}

        domains = [self._extract_domain(ev['url']) for ev in evidence]
        domain_counts = defaultdict(int)
        for domain in domains:
            domain_counts[domain] += 1

        unique_domains = len(domain_counts)
        max_domain_count = max(domain_counts.values())
        max_domain_ratio = max_domain_count / len(domains)
        diversity_score = 1.0 - max_domain_ratio

        return {
            "unique_domains": unique_domains,
            "max_domain_ratio": round(max_domain_ratio, 2),
            "diversity_score": round(diversity_score, 2),
            "domain_distribution": dict(domain_counts)
        }
```

**Modified File:** `backend/app/pipeline/retrieve.py` (line 89, add before return)
```python
def _apply_credibility_weighting(self, evidence_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    # ... existing credibility scoring ...

    # Sort by final weighted score
    evidence_list.sort(key=lambda x: x["final_score"], reverse=True)

    # NEW: Apply domain capping if enabled
    from app.core.config import settings
    if settings.ENABLE_DOMAIN_CAPPING:
        from app.utils.domain_capping import DomainCapper
        capper = DomainCapper(
            max_per_domain=settings.MAX_EVIDENCE_PER_DOMAIN,
            max_domain_ratio=settings.DOMAIN_DIVERSITY_THRESHOLD
        )
        evidence_list = capper.apply_caps(evidence_list, target_count=self.max_sources_per_claim)

    logger.info("Applied credibility and recency weighting")
    return evidence_list
```

**Tests:** `backend/tests/test_domain_capping.py`
```python
import pytest
from app.utils.domain_capping import DomainCapper

def test_domain_capping_single_domain_excess():
    """Test that single domain doesn't dominate"""
    evidence = [
        {"url": "https://dailymail.co.uk/1", "final_score": 0.9},
        {"url": "https://dailymail.co.uk/2", "final_score": 0.85},
        {"url": "https://dailymail.co.uk/3", "final_score": 0.8},
        {"url": "https://bbc.com/1", "final_score": 0.75},
        {"url": "https://reuters.com/1", "final_score": 0.7},
    ]

    capper = DomainCapper(max_per_domain=2)
    result = capper.apply_caps(evidence, target_count=5)

    # Should cap dailymail to 2, include other domains
    dailymail_count = sum(1 for e in result if "dailymail" in e["url"])
    assert dailymail_count <= 2
    assert len(result) == 4  # 2 dailymail + bbc + reuters

def test_diversity_metrics():
    """Test diversity score calculation"""
    evidence = [
        {"url": "https://bbc.com/1"},
        {"url": "https://reuters.com/1"},
        {"url": "https://theguardian.com/1"},
    ]

    capper = DomainCapper()
    metrics = capper.get_diversity_metrics(evidence)

    assert metrics["unique_domains"] == 3
    assert metrics["diversity_score"] > 0.6  # High diversity
```

---

### WEEK 2: Evidence Deduplication

**New File:** `backend/app/utils/deduplication.py`
```python
from typing import List, Dict, Any, Tuple
import hashlib
from difflib import SequenceMatcher
import logging

logger = logging.getLogger(__name__)

class EvidenceDeduplicator:
    """Detect and remove duplicate/near-duplicate evidence"""

    def __init__(self):
        self.text_similarity_threshold = 0.85
        self.hash_size = 16  # bytes for simhash

    def deduplicate(self, evidence_list: List[Dict[str, Any]]) -> Tuple[List[Dict], Dict[str, Any]]:
        """
        Remove duplicates using three-stage process:
        1. Exact hash deduplication (fastest)
        2. Text similarity deduplication (medium)
        3. Semantic similarity if embeddings available (slowest, most accurate)
        """
        if len(evidence_list) <= 1:
            return evidence_list, {"duplicates_removed": 0}

        # Stage 1: Exact hash
        stage1 = self._exact_hash_dedup(evidence_list)

        # Stage 2: Text similarity
        stage2 = self._text_similarity_dedup(stage1)

        stats = {
            "original_count": len(evidence_list),
            "after_hash_dedup": len(stage1),
            "final_count": len(stage2),
            "duplicates_removed": len(evidence_list) - len(stage2),
            "dedup_ratio": round((len(evidence_list) - len(stage2)) / len(evidence_list), 2)
        }

        logger.info(f"Deduplication: {stats['original_count']} → {stats['final_count']} "
                   f"({stats['duplicates_removed']} duplicates removed)")

        return stage2, stats

    def _exact_hash_dedup(self, evidence: List[Dict]) -> List[Dict]:
        """Remove exact duplicates by content hash"""
        seen_hashes = set()
        unique = []

        for ev in evidence:
            content_hash = self._hash_content(ev.get('text', ev.get('snippet', '')))
            if content_hash not in seen_hashes:
                seen_hashes.add(content_hash)
                ev['content_hash'] = content_hash  # Store for database
                unique.append(ev)

        return unique

    def _hash_content(self, text: str) -> str:
        """Create normalized hash of content"""
        # Normalize: lowercase, remove extra spaces, remove punctuation
        normalized = text.lower().strip()
        normalized = ''.join(c for c in normalized if c.isalnum() or c.isspace())
        normalized = ' '.join(normalized.split())
        return hashlib.md5(normalized.encode()).hexdigest()

    def _text_similarity_dedup(self, evidence: List[Dict]) -> List[Dict]:
        """Remove near-duplicates using sequence matching"""
        if len(evidence) <= 1:
            return evidence

        unique = [evidence[0]]

        for candidate in evidence[1:]:
            is_duplicate = False
            candidate_text = candidate.get('text', candidate.get('snippet', '')).lower()

            for existing in unique:
                existing_text = existing.get('text', existing.get('snippet', '')).lower()
                similarity = SequenceMatcher(None, candidate_text, existing_text).ratio()

                if similarity >= self.text_similarity_threshold:
                    is_duplicate = True
                    # Mark as syndicated if from different domain
                    if candidate.get('url') != existing.get('url'):
                        candidate['is_syndicated'] = True
                        candidate['original_source_url'] = existing.get('url')
                    break

            if not is_duplicate:
                unique.append(candidate)

        return unique
```

**Integration:** `backend/app/pipeline/retrieve.py` (line 95, after domain capping)
```python
# NEW: Deduplicate evidence if enabled
if settings.ENABLE_DEDUPLICATION:
    from app.utils.deduplication import EvidenceDeduplicator
    deduplicator = EvidenceDeduplicator()
    evidence_list, dedup_stats = deduplicator.deduplicate(evidence_list)
    logger.info(f"Deduplication stats: {dedup_stats}")
```

**Migration:** `backend/migrations/002_add_deduplication_fields.sql`
```sql
-- Add deduplication tracking fields to evidence table
ALTER TABLE evidence ADD COLUMN content_hash TEXT;
ALTER TABLE evidence ADD COLUMN is_syndicated BOOLEAN DEFAULT FALSE;
ALTER TABLE evidence ADD COLUMN original_source_url TEXT;

-- Create index for hash-based lookups
CREATE INDEX idx_evidence_content_hash ON evidence(content_hash) WHERE content_hash IS NOT NULL;
```

---

### WEEK 3: Source Diversity

**New File:** `backend/app/utils/source_independence.py`
```python
from typing import Dict, Any, List
from collections import Counter
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class SourceIndependenceChecker:
    """Track and enforce source diversity across evidence"""

    def __init__(self):
        self.ownership_map = self._load_ownership_database()

    def _load_ownership_database(self) -> Dict[str, str]:
        """Load domain → parent company mapping"""
        try:
            data_file = Path(__file__).parent.parent / "data" / "source_ownership.json"
            if data_file.exists():
                with open(data_file) as f:
                    return json.load(f)
            else:
                logger.warning("source_ownership.json not found, using empty map")
                return {}
        except Exception as e:
            logger.error(f"Failed to load ownership database: {e}")
            return {}

    def check_diversity(self, evidence_list: List[Dict]) -> Dict[str, Any]:
        """Calculate diversity metrics and flag violations"""
        if not evidence_list:
            return {"passes_diversity_threshold": True, "diversity_score": 1.0}

        domains = [self._extract_domain(ev['url']) for ev in evidence_list]

        # Check domain concentration
        domain_counts = Counter(domains)
        max_domain_ratio = max(domain_counts.values()) / len(domains)

        # Check parent company clustering
        parent_companies = [self.ownership_map.get(d, d) for d in domains]
        parent_counts = Counter(parent_companies)
        max_parent_ratio = max(parent_counts.values()) / len(parent_companies)

        diversity_score = 1.0 - max_parent_ratio
        passes_threshold = max_parent_ratio < 0.6

        return {
            "unique_domains": len(domain_counts),
            "unique_parent_companies": len(parent_counts),
            "max_domain_concentration": round(max_domain_ratio, 2),
            "max_parent_concentration": round(max_parent_ratio, 2),
            "diversity_score": round(diversity_score, 2),
            "passes_diversity_threshold": passes_threshold,
            "domain_distribution": dict(domain_counts),
            "parent_distribution": dict(parent_counts)
        }

    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL"""
        from urllib.parse import urlparse
        try:
            domain = urlparse(url).netloc.replace('www.', '').lower()
            return domain
        except:
            return "unknown"

    def enrich_evidence_with_ownership(self, evidence_list: List[Dict]) -> List[Dict]:
        """Add parent company information to evidence"""
        for ev in evidence_list:
            domain = self._extract_domain(ev['url'])
            ev['parent_company'] = self.ownership_map.get(domain, None)

            # Set independence flag
            if ev['parent_company']:
                ev['independence_flag'] = 'corporate'
            elif any(marker in domain for marker in ['.gov', '.edu', '.ac.uk']):
                ev['independence_flag'] = 'government' if '.gov' in domain else 'academic'
            else:
                ev['independence_flag'] = 'independent'

        return evidence_list
```

**Data File:** `backend/app/data/source_ownership.json`
```json
{
  "bbc.co.uk": "BBC",
  "bbc.com": "BBC",
  "skynews.com": "Comcast",
  "nbcnews.com": "Comcast",
  "msnbc.com": "Comcast",
  "thesun.co.uk": "News Corp",
  "nypost.com": "News Corp",
  "wsj.com": "News Corp",
  "foxnews.com": "News Corp",
  "cnn.com": "Warner Bros Discovery",
  "huffpost.com": "BuzzFeed",
  "dailymail.co.uk": "DMGT",
  "metro.co.uk": "DMGT",
  "theguardian.com": "Guardian Media Group",
  "telegraph.co.uk": "Telegraph Media Group",
  "independent.co.uk": "Independent Digital News & Media",
  "mirror.co.uk": "Reach plc",
  "express.co.uk": "Reach plc"
}
```

**Integration:** `backend/app/pipeline/retrieve.py` (after dedup)
```python
# NEW: Check source diversity if enabled
if settings.ENABLE_SOURCE_DIVERSITY:
    from app.utils.source_independence import SourceIndependenceChecker
    diversity_checker = SourceIndependenceChecker()

    # Enrich evidence with ownership data
    evidence_list = diversity_checker.enrich_evidence_with_ownership(evidence_list)

    # Check diversity metrics
    diversity_metrics = diversity_checker.check_diversity(evidence_list)
    logger.info(f"Source diversity: {diversity_metrics}")

    # If diversity fails, log warning (don't block, just warn)
    if not diversity_metrics['passes_diversity_threshold']:
        logger.warning(f"Low source diversity detected: {diversity_metrics['diversity_score']}")
```

---

### WEEK 3.5: Context Preservation + Version Control + Safety + Monitoring

#### Context Preservation

**Modified:** `backend/app/pipeline/extract.py` (update system prompt, line 42)
```python
self.system_prompt = """You are a fact-checking assistant that extracts atomic, verifiable claims from content.

RULES:
1. Extract ONLY factual claims that can be verified against external sources
2. Make claims atomic (one fact per claim) and specific
3. Avoid opinions, speculation, or subjective statements
4. Include numbers, dates, names when present
5. Maximum {max_claims} claims for Quick mode
6. Focus on the most important/checkable claims
7. Always return a valid JSON response with the required format

CONTEXT PRESERVATION (NEW):
8. When claims are causally related (e.g., "X happened, causing Y"), assign them the same context_group_id
9. For compound statements, preserve the linking context in context_summary
10. If claim B depends on claim A for understanding, note this in depends_on_claims

RESPONSE FORMAT:
{{
  "claims": [
    {{
      "text": "GDP grew by 3% in 2023",
      "confidence": 0.95,
      "category": "economic",
      "context_group_id": "gdp_trend_2022_2023",  // OPTIONAL: Group related claims
      "context_summary": "GDP growth reversed prior decline",  // OPTIONAL: Preserve context
      "depends_on_claims": [1]  // OPTIONAL: Index of prerequisite claims
    }}
  ]
}}
"""
```

**Migration:** `backend/migrations/003_add_claim_context_fields.sql`
```sql
ALTER TABLE claim ADD COLUMN context_group_id TEXT;
ALTER TABLE claim ADD COLUMN context_summary TEXT;
ALTER TABLE claim ADD COLUMN depends_on_claim_ids JSONB;

CREATE INDEX idx_claim_context_group ON claim(context_group_id) WHERE context_group_id IS NOT NULL;
```

#### Model Version Control

**New File:** `backend/app/utils/model_versions.py`
```python
from typing import Dict, Any
import hashlib

class ModelVersionRegistry:
    """Central registry for all ML models used in pipeline"""

    MODELS = {
        "claim_extractor": {
            "provider": "openai",
            "model_id": "gpt-4o-mini-2024-07-18",
            "version": "2024-07-18",
            "config": {"temperature": 0.1, "max_tokens": 1500}
        },
        "nli_verifier": {
            "provider": "huggingface",
            "model_id": "facebook/bart-large-mnli",
            "version": "1.0",
            "config": {"max_length": 512, "batch_size": 8}
        },
        "claim_judge": {
            "provider": "openai",
            "model_id": "gpt-4o-mini-2024-07-18",
            "version": "2024-07-18",
            "config": {"temperature": 0.3, "max_tokens": 1000}
        }
    }

    @classmethod
    def get_version_snapshot(cls) -> Dict[str, str]:
        """Get current versions of all models"""
        return {
            key: f"{meta['model_id']}_{meta['version']}"
            for key, meta in cls.MODELS.items()
        }
```

**Integration:** `backend/app/workers/pipeline.py` (save results function, line 100)
```python
# Add to claim creation
from app.utils.model_versions import ModelVersionRegistry
version_snapshot = ModelVersionRegistry.get_version_snapshot()

claim = Claim(
    # ... existing fields ...
    extraction_model_version=claim_data.get("extraction_model_version"),
    pipeline_version=settings.PIPELINE_VERSION if hasattr(settings, 'PIPELINE_VERSION') else "1.0.0",
    model_config_snapshot=version_snapshot
)
```

**Migration:** `backend/migrations/004_add_version_tracking_fields.sql`
```sql
ALTER TABLE claim ADD COLUMN extraction_model_version TEXT;
ALTER TABLE claim ADD COLUMN verification_model_version TEXT;
ALTER TABLE claim ADD COLUMN judgment_model_version TEXT;
ALTER TABLE claim ADD COLUMN pipeline_version TEXT DEFAULT '1.0.0';
ALTER TABLE claim ADD COLUMN model_config_snapshot JSONB;

CREATE INDEX idx_claim_pipeline_version ON claim(pipeline_version);
```

---

## PHASE 1.5: SEMANTIC INTELLIGENCE (Weeks 4-5.5)

### Fact-Check API Integration (Week 4-4.5)

**New File:** `backend/app/services/factcheck_api.py`
```python
import logging
import httpx
from typing import List, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class FactCheckAPI:
    """Google Fact Check Explorer API integration"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://factchecktools.googleapis.com/v1alpha1/claims:search"
        self.timeout = 10

    async def search_fact_checks(self, claim_text: str, language: str = "en") -> List[Dict[str, Any]]:
        """Search for existing fact-checks of a claim"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    self.base_url,
                    params={
                        "query": claim_text,
                        "languageCode": language,
                        "key": self.api_key
                    }
                )

                if response.status_code != 200:
                    logger.warning(f"Fact Check API error: {response.status_code}")
                    return []

                data = response.json()
                claims = data.get("claims", [])

                return self._parse_fact_checks(claims)

        except httpx.TimeoutException:
            logger.warning("Fact Check API timeout")
            return []
        except Exception as e:
            logger.error(f"Fact Check API error: {e}")
            return []

    def _parse_fact_checks(self, claims: List[Dict]) -> List[Dict[str, Any]]:
        """Parse API response into standard format"""
        parsed = []

        for claim in claims[:5]:  # Top 5 fact-checks
            claim_reviews = claim.get("claimReview", [])

            for review in claim_reviews:
                parsed.append({
                    "claim_text": claim.get("text", ""),
                    "claim_date": claim.get("claimDate"),
                    "publisher": review.get("publisher", {}).get("name"),
                    "url": review.get("url"),
                    "title": review.get("title"),
                    "rating": review.get("textualRating"),
                    "language": review.get("languageCode"),
                    "review_date": review.get("reviewDate"),
                    "verdict": self._map_rating_to_verdict(review.get("textualRating", ""))
                })

        return parsed

    def _map_rating_to_verdict(self, rating: str) -> str:
        """Map fact-check rating to our verdict system"""
        rating_lower = rating.lower()

        if any(word in rating_lower for word in ["true", "correct", "accurate", "verified"]):
            return "supported"
        elif any(word in rating_lower for word in ["false", "incorrect", "wrong", "pants on fire"]):
            return "contradicted"
        else:
            return "uncertain"
```

**Integration:** Insert new stage in `backend/app/workers/pipeline.py` (after extract, before retrieve, line 216)
```python
# NEW STAGE: Fact-Check Lookup (if enabled)
if settings.ENABLE_FACTCHECK_API:
    self.update_state(state="PROGRESS", meta={"stage": "factcheck_lookup", "progress": 30})
    stage_start = datetime.utcnow()

    factcheck_results = asyncio.run(lookup_factchecks_with_cache(claims, cache_service))

    # If high-confidence fact-checks found, use them as evidence
    if factcheck_results.get("has_factchecks"):
        logger.info(f"Found {factcheck_results['factcheck_count']} fact-checks, using fast-path")
        # Skip retrieve/verify, go straight to judge with fact-check evidence
        # (Implementation details in separate commit)

    stage_timings["factcheck_lookup"] = (datetime.utcnow() - stage_start).total_seconds()
```

---

### Temporal Context (Week 4.5-5.5)

**New File:** `backend/app/utils/temporal.py`
```python
import re
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class TemporalAnalyzer:
    """Detect and analyze temporal context in claims"""

    def __init__(self):
        # Temporal marker patterns
        self.time_markers = {
            "present": r"\b(today|now|currently|at present|this year|2025)\b",
            "recent_past": r"\b(yesterday|last week|last month|recently)\b",
            "specific_year": r"\b(in 20\d{2}|during 20\d{2})\b",
            "historical": r"\b(in the past|historically|previously)\b",
            "future": r"\b(will|going to|next year|in the future|2026)\b"
        }

    def analyze_claim(self, claim_text: str) -> Dict[str, Any]:
        """Determine if claim is time-sensitive and extract temporal context"""
        claim_lower = claim_text.lower()

        # Detect temporal markers
        detected_markers = {}
        for category, pattern in self.time_markers.items():
            matches = re.findall(pattern, claim_lower, re.IGNORECASE)
            if matches:
                detected_markers[category] = matches

        is_time_sensitive = bool(detected_markers)

        # Determine temporal window for evidence
        if "present" in detected_markers:
            temporal_window = "last_30_days"
            max_evidence_age_days = 30
        elif "recent_past" in detected_markers:
            temporal_window = "last_90_days"
            max_evidence_age_days = 90
        elif "specific_year" in detected_markers:
            year = self._extract_year(claim_text)
            temporal_window = f"year_{year}"
            max_evidence_age_days = 365  # Accept evidence from that year
        else:
            temporal_window = "timeless"
            max_evidence_age_days = None

        return {
            "is_time_sensitive": is_time_sensitive,
            "temporal_markers": detected_markers,
            "temporal_window": temporal_window,
            "max_evidence_age_days": max_evidence_age_days,
            "claim_type": self._classify_temporal_type(detected_markers)
        }

    def _extract_year(self, text: str) -> Optional[str]:
        """Extract specific year from claim"""
        match = re.search(r"20\d{2}", text)
        return match.group(0) if match else None

    def _classify_temporal_type(self, markers: Dict) -> str:
        """Classify claim by temporal type"""
        if "future" in markers:
            return "prediction"
        elif "present" in markers:
            return "current_state"
        elif "specific_year" in markers:
            return "historical_fact"
        else:
            return "timeless_fact"

    def filter_evidence_by_time(self, evidence: List[Dict], temporal_analysis: Dict) -> List[Dict]:
        """Filter evidence based on temporal requirements"""
        if not temporal_analysis["is_time_sensitive"]:
            return evidence

        max_age_days = temporal_analysis["max_evidence_age_days"]
        if max_age_days is None:
            return evidence

        cutoff_date = datetime.now() - timedelta(days=max_age_days)
        filtered = []

        for ev in evidence:
            pub_date = ev.get("published_date")
            if pub_date:
                try:
                    # Parse various date formats
                    ev_date = self._parse_date(pub_date)
                    if ev_date and ev_date >= cutoff_date:
                        filtered.append(ev)
                    else:
                        logger.debug(f"Evidence too old: {pub_date} (cutoff: {cutoff_date})")
                except:
                    # If can't parse, include it (benefit of doubt)
                    filtered.append(ev)
            else:
                # No date = assume recent enough
                filtered.append(ev)

        logger.info(f"Temporal filtering: {len(evidence)} → {len(filtered)} "
                   f"(max age: {max_age_days} days)")

        return filtered

    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse various date formats"""
        # Try ISO format
        try:
            return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        except:
            pass

        # Try common formats
        formats = ["%Y-%m-%d", "%Y/%m/%d", "%d-%m-%Y", "%B %d, %Y"]
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except:
                continue

        # Extract year and assume Jan 1
        match = re.search(r"20\d{2}", date_str)
        if match:
            year = int(match.group(0))
            return datetime(year, 1, 1)

        return None
```

**Integration:** `backend/app/pipeline/extract.py` (after claim extraction, line 150)
```python
# NEW: Analyze temporal context if enabled
if settings.ENABLE_TEMPORAL_CONTEXT:
    from app.utils.temporal import TemporalAnalyzer
    temporal_analyzer = TemporalAnalyzer()

    for i, claim in enumerate(claims):
        temporal_analysis = temporal_analyzer.analyze_claim(claim["text"])
        claims[i]["temporal_analysis"] = temporal_analysis
        claims[i]["is_time_sensitive"] = temporal_analysis["is_time_sensitive"]
```

**Integration:** `backend/app/pipeline/retrieve.py` (after evidence retrieval, before ranking, line 85)
```python
# NEW: Apply temporal filtering if claim is time-sensitive
if settings.ENABLE_TEMPORAL_CONTEXT and claim.get("temporal_analysis"):
    from app.utils.temporal import TemporalAnalyzer
    temporal_analyzer = TemporalAnalyzer()
    ranked_evidence = temporal_analyzer.filter_evidence_by_time(
        ranked_evidence,
        claim["temporal_analysis"]
    )
```

---

## PHASE 2: USER EXPERIENCE (Weeks 5.5-7.5)

### Claim Classification (Week 5.5-6.5)

**New File:** `backend/app/utils/claim_classifier.py`
```python
import re
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

class ClaimClassifier:
    """Classify claims by type and verifiability"""

    def __init__(self):
        # Opinion indicators
        self.opinion_patterns = [
            r"\b(i think|i believe|in my opinion|i feel|seems like)\b",
            r"\b(beautiful|ugly|amazing|terrible|best|worst)\b",
            r"\b(should|ought to|must|need to)\b"  # Normative
        ]

        # Prediction indicators
        self.prediction_patterns = [
            r"\b(will|going to|predict|forecast|expect)\b",
            r"\b(in the future|next year|by 20\d{2})\b"
        ]

        # Personal experience indicators
        self.personal_patterns = [
            r"\b(i saw|i heard|i experienced|happened to me)\b"
        ]

    def classify(self, claim_text: str) -> Dict[str, Any]:
        """Classify claim type and assess verifiability"""
        claim_lower = claim_text.lower()

        # Check for opinion
        if any(re.search(pattern, claim_lower) for pattern in self.opinion_patterns):
            return {
                "claim_type": "opinion",
                "is_verifiable": False,
                "reason": "This appears to be a subjective opinion or value judgment",
                "confidence": 0.85
            }

        # Check for prediction
        if any(re.search(pattern, claim_lower) for pattern in self.prediction_patterns):
            return {
                "claim_type": "prediction",
                "is_verifiable": False,  # Can't verify future
                "reason": "This is a prediction about future events",
                "confidence": 0.8,
                "note": "We can assess the basis for the prediction, but cannot verify its truth"
            }

        # Check for personal experience
        if any(re.search(pattern, claim_lower) for pattern in self.personal_patterns):
            return {
                "claim_type": "personal_experience",
                "is_verifiable": False,
                "reason": "This is a personal experience that cannot be externally verified",
                "confidence": 0.75
            }

        # Default: factual claim
        return {
            "claim_type": "factual",
            "is_verifiable": True,
            "reason": "This appears to be a factual claim that can be verified",
            "confidence": 0.7
        }
```

**Integration:** `backend/app/pipeline/extract.py` (after extraction, line 150)
```python
# NEW: Classify claims if enabled
if settings.ENABLE_CLAIM_CLASSIFICATION:
    from app.utils.claim_classifier import ClaimClassifier
    classifier = ClaimClassifier()

    for i, claim in enumerate(claims):
        classification = classifier.classify(claim["text"])
        claims[i]["classification"] = classification
        claims[i]["is_verifiable"] = classification["is_verifiable"]

        # If not verifiable, mark for early exit
        if not classification["is_verifiable"]:
            claims[i]["verdict"] = "not_fact_checkable"
            claims[i]["rationale"] = classification["reason"]
```

---

### Enhanced Explainability (Week 6.5-7.5)

**New File:** `backend/app/utils/explainability.py`
```python
from typing import Dict, Any, List

class ExplainabilityEnhancer:
    """Add transparency and detailed explanations to verdicts"""

    def create_decision_trail(self, claim: Dict, evidence: List[Dict],
                             verification_signals: Dict, judgment: Dict) -> Dict[str, Any]:
        """Create detailed decision trail for transparency"""

        trail = {
            "stages": [
                {
                    "stage": "evidence_retrieval",
                    "description": f"Searched for evidence using optimized query",
                    "result": f"Found {len(evidence)} sources",
                    "details": {
                        "unique_domains": len(set(ev.get('source') for ev in evidence)),
                        "avg_credibility": round(sum(ev.get('credibility_score', 0.6) for ev in evidence) / max(len(evidence), 1), 2)
                    }
                },
                {
                    "stage": "verification",
                    "description": "Analyzed evidence using NLI model",
                    "result": f"{verification_signals.get('supporting_count', 0)} supporting, "
                             f"{verification_signals.get('contradicting_count', 0)} contradicting",
                    "details": verification_signals
                },
                {
                    "stage": "judgment",
                    "description": "Final verdict determined by LLM judge",
                    "result": f"{judgment.get('verdict')} ({judgment.get('confidence')}% confidence)",
                    "details": {
                        "rationale": judgment.get('rationale'),
                        "evidence_used": len(evidence)
                    }
                }
            ],
            "transparency_score": self._calculate_transparency_score(evidence, verification_signals)
        }

        return trail

    def _calculate_transparency_score(self, evidence: List, signals: Dict) -> float:
        """Calculate how transparent/explainable the verdict is"""
        score = 0.5  # Base score

        # More evidence = more transparent
        if len(evidence) >= 3:
            score += 0.2

        # High quality evidence = more transparent
        if signals.get('evidence_quality') == 'high':
            score += 0.2

        # Clear consensus = more transparent
        supporting = signals.get('supporting_count', 0)
        contradicting = signals.get('contradicting_count', 0)
        if abs(supporting - contradicting) >= 2:
            score += 0.1

        return min(1.0, score)

    def create_uncertainty_explanation(self, verdict: str, signals: Dict, evidence: List) -> str:
        """Explain why verdict is uncertain"""
        if verdict != "uncertain":
            return ""

        total_evidence = len(evidence)

        if total_evidence < 3:
            return f"Insufficient evidence found (only {total_evidence} sources). More research needed."

        supporting = signals.get('supporting_count', 0)
        contradicting = signals.get('contradicting_count', 0)

        if abs(supporting - contradicting) <= 1:
            return f"Conflicting evidence from equally credible sources ({supporting} supporting vs {contradicting} contradicting)."

        if signals.get('evidence_quality') == 'low':
            return "Available evidence is low quality or lacks authoritative sources."

        return "Evidence is mixed or insufficient for a definitive determination."
```

**Integration:** `backend/app/pipeline/judge.py` (in judge_claim function, line 130)
```python
# NEW: Add explainability if enabled
if settings.ENABLE_ENHANCED_EXPLAINABILITY:
    from app.utils.explainability import ExplainabilityEnhancer
    explainer = ExplainabilityEnhancer()

    decision_trail = explainer.create_decision_trail(
        claim, evidence, verification_signals, judgment_data
    )

    # Add to result
    result.decision_trail = decision_trail
    result.transparency_level = "high" if decision_trail["transparency_score"] > 0.7 else "medium"

    # If uncertain, add detailed explanation
    if result.verdict == "uncertain":
        result.uncertainty_explanation = explainer.create_uncertainty_explanation(
            result.verdict, verification_signals, evidence
        )
```

---

## TESTING STRATEGY

### Test File Structure

```
backend/tests/
├── unit/
│   ├── test_domain_capping.py
│   ├── test_deduplication.py
│   ├── test_source_independence.py
│   ├── test_temporal.py
│   ├── test_claim_classifier.py
│   ├── test_explainability.py
│   └── test_model_versions.py
├── integration/
│   ├── test_pipeline_with_domain_capping.py
│   ├── test_pipeline_with_deduplication.py
│   ├── test_pipeline_with_factcheck.py
│   ├── test_pipeline_with_temporal.py
│   └── test_full_pipeline_flags.py
└── fixtures/
    ├── sample_claims.json
    ├── sample_evidence.json
    └── mock_factcheck_responses.json
```

### Running Tests

```bash
# Run all tests
pytest backend/tests/ -v

# Run specific category
pytest backend/tests/unit/ -v
pytest backend/tests/integration/ -v

# Run with coverage
pytest backend/tests/ --cov=backend/app --cov-report=html

# Run specific test file
pytest backend/tests/unit/test_domain_capping.py -v
```

---

## DEPLOYMENT CHECKLIST

### Before Each Phase Deployment

- [ ] All tests pass locally
- [ ] Code review completed
- [ ] Database migrations tested on dev
- [ ] Feature flags added to .env
- [ ] Documentation updated
- [ ] Performance benchmarks run
- [ ] Rollback procedure documented

### Phase 1 Deployment (Week 3.5)
- [ ] All structural features implemented
- [ ] Database has 15 new fields
- [ ] 5 new utilities working
- [ ] Domain capping tested
- [ ] Deduplication tested
- [ ] Source diversity tested
- [ ] All flags default to FALSE

### Phase 1.5 Deployment (Week 5.5)
- [ ] Fact-check API integrated
- [ ] Temporal context working
- [ ] Fast-path tested
- [ ] Time-sensitive claims handled correctly

### Phase 2 Deployment (Week 7.5)
- [ ] Claim classification working
- [ ] Explainability enhanced
- [ ] Decision trails visible
- [ ] Full system tested end-to-end

---

**Status:** Implementation guide complete and ready for execution
**Next Step:** Create feature branch and begin Week 1, Day 1 tasks

