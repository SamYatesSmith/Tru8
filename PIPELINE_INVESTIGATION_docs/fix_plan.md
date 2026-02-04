# Tru8 Report Quality Investigation: Fix Plan

## Overview

This document proposes minimal, incremental fixes to address the root causes identified in the investigation. Each fix is PR-sized and can be tested independently.

---

## Fix 1: Add Relevance Threshold to Display Selection

**Root Cause Addressed:** #1 - Evidence display selection ignores relevance

**What to Change:**
Filter evidence for display to only include items above a relevance threshold.

**Where to Change:**
`app/pipeline/judge.py:363` (and lines 316, 389)

**Proposed Code:**
```python
# Before:
supporting_evidence=evidence[:3],  # Top 3 evidence pieces

# After:
# Filter for display: only show evidence with sufficient relevance
MIN_DISPLAY_RELEVANCE = 0.45  # Could be config-driven
display_evidence = [
    ev for ev in evidence
    if ev.get('semantic_similarity', 0) >= MIN_DISPLAY_RELEVANCE
    or ev.get('external_source_provider')  # Always show API sources
][:3]
supporting_evidence=display_evidence if display_evidence else evidence[:1],
```

**Why This Fixes the Root Cause:**
- Evidence must have semantic_similarity >= 0.45 to be shown
- API sources (authoritative data) always shown
- Falls back to showing at least 1 source if none pass threshold

**How to Test:**
1. Run pipeline with claim: "Tesla reported exactly 1.31M deliveries in Q4 2022"
2. Check that generic Tesla articles don't appear as evidence
3. Verify specific delivery count articles do appear

**Feature Flag:**
Add `MIN_DISPLAY_RELEVANCE_THRESHOLD` to config.py (default: 0.45)

---

## Fix 2: Raise Semantic Similarity Threshold

**Root Cause Addressed:** #2 - Threshold too low (0.35)

**What to Change:**
Increase `SEMANTIC_SIMILARITY_THRESHOLD` from 0.35 to 0.50

**Where to Change:**
`app/core/config.py:144`

**Proposed Code:**
```python
# Before:
SEMANTIC_SIMILARITY_THRESHOLD: float = Field(0.35, env="SEMANTIC_SIMILARITY_THRESHOLD")

# After:
SEMANTIC_SIMILARITY_THRESHOLD: float = Field(0.50, env="SEMANTIC_SIMILARITY_THRESHOLD")
```

**Why This Fixes the Root Cause:**
- 0.50 requires ~50% semantic overlap instead of 35%
- Filters out topically related but not directly relevant content
- Still allows legitimate evidence with moderate similarity

**How to Test:**
1. Compare before/after for a sample of 10 checks
2. Measure: % of displayed evidence that human reviewers rate as "directly relevant"
3. Monitor for over-filtering (claims with 0 evidence)

**Feature Flag:**
Already exists as env var `SEMANTIC_SIMILARITY_THRESHOLD`

**Rollback:**
Set `SEMANTIC_SIMILARITY_THRESHOLD=0.35` in env to revert

---

## Fix 3: Enable Cross-Encoder Reranking

**Root Cause Addressed:** #3 - Cross-encoder disabled

**What to Change:**
Enable the existing cross-encoder implementation

**Where to Change:**
`app/core/config.py:191`

**Proposed Code:**
```python
# Before:
ENABLE_CROSS_ENCODER_RERANK: bool = Field(False, env="ENABLE_CROSS_ENCODER_RERANK")

# After:
ENABLE_CROSS_ENCODER_RERANK: bool = Field(True, env="ENABLE_CROSS_ENCODER_RERANK")
```

**Why This Fixes the Root Cause:**
- Cross-encoder processes claim+evidence pairs with full attention
- Catches nuanced mismatches bi-encoder misses
- Already implemented and tested at `retrieve.py:685-746`

**How to Test:**
1. Enable on staging environment first
2. Compare ranking changes (logged at `retrieve.py:734`)
3. Measure latency impact (~50ms per 10 pairs)

**Feature Flag:**
Already exists as env var `ENABLE_CROSS_ENCODER_RERANK`

**Rollback:**
Set `ENABLE_CROSS_ENCODER_RERANK=False` in env

---

## Fix 4: Implement Display-Level Entity Validation

**Root Cause Addressed:** #5 - No entity matching for display

**What to Change:**
Add entity overlap check before selecting evidence for display.

**Where to Change:**
`app/pipeline/judge.py` - new helper function

**Proposed Code:**
```python
def _filter_evidence_for_display(
    self,
    evidence: List[Dict[str, Any]],
    claim: Dict[str, Any],
    max_display: int = 3
) -> List[Dict[str, Any]]:
    """
    Filter evidence for display, prioritizing items that contain claim entities.

    For claims with specific entities (numbers, dates, names), evidence
    should contain those entities to be shown as supporting evidence.
    """
    key_entities = claim.get('key_entities', [])
    claim_text = claim.get('text', '')

    # Extract numbers from claim for numeric claims
    import re
    claim_numbers = set(re.findall(r'\d+(?:\.\d+)?', claim_text))

    def entity_overlap_score(ev: Dict[str, Any]) -> float:
        """Score how many claim entities appear in evidence."""
        ev_text = (ev.get('snippet', '') + ' ' + ev.get('title', '')).lower()

        # Check key entities
        entity_matches = sum(
            1 for entity in key_entities
            if entity.lower() in ev_text
        )

        # Check numbers (for numeric claims)
        number_matches = sum(
            1 for num in claim_numbers
            if num in ev_text
        )

        # Normalize by total entities
        total_entities = len(key_entities) + len(claim_numbers)
        if total_entities == 0:
            return 1.0  # No specific entities = any evidence OK

        return (entity_matches + number_matches) / total_entities

    # Score and sort by entity overlap × semantic similarity
    scored_evidence = []
    for ev in evidence:
        entity_score = entity_overlap_score(ev)
        sem_sim = ev.get('semantic_similarity', 0.5)
        combined = (entity_score * 0.4) + (sem_sim * 0.6)
        scored_evidence.append((combined, ev))

    scored_evidence.sort(key=lambda x: x[0], reverse=True)

    # Return top items that pass minimum threshold
    MIN_COMBINED = 0.35
    filtered = [ev for score, ev in scored_evidence if score >= MIN_COMBINED]

    return filtered[:max_display] if filtered else evidence[:1]
```

**Usage (replace evidence[:3]):**
```python
# In judge_claim():
display_evidence = self._filter_evidence_for_display(evidence, claim)
supporting_evidence=display_evidence,
```

**Why This Fixes the Root Cause:**
- Claims about "1.31M deliveries" require evidence containing "1.31" or "1.31 million"
- Claims about "January 15, 2024" require evidence with that date
- Legal claims about "Section 106" require that text in evidence

**How to Test:**
1. Create test cases for each claim type (timestamp, numeric, legal)
2. Verify entity overlap scoring works correctly
3. Check that relevant evidence is prioritized over general coverage

**Feature Flag:**
Add `ENABLE_ENTITY_MATCHING_FOR_DISPLAY` (default: True)

---

## Fix 5: Add Relevance Score to Database & API Response

**Root Cause Addressed:** Visibility for debugging

**What to Change:**
Include `semantic_similarity` in the Evidence model and API response.

**Where to Change:**
1. `app/models/evidence.py` - add field
2. `app/workers/pipeline.py:288-312` - save field
3. API response schema - include field

**Proposed Code (models):**
```python
# app/models/evidence.py
class Evidence(SQLModel, table=True):
    # ... existing fields ...
    semantic_similarity: Optional[float] = Field(default=None)  # NEW
```

**Proposed Code (pipeline):**
```python
# app/workers/pipeline.py:288-312
evidence = Evidence(
    # ... existing fields ...
    semantic_similarity=ev_data.get("semantic_similarity"),  # NEW
)
```

**Why This Fixes the Root Cause:**
- Enables monitoring of relevance scores in production
- Allows frontend to display relevance indicators
- Supports debugging when evidence seems off-topic

**How to Test:**
1. Run migration
2. Verify field is populated
3. Check API response includes the field

---

## Implementation Order

| Order | Fix | Effort | Risk | Impact |
|-------|-----|--------|------|--------|
| 1 | Fix 2: Raise threshold to 0.50 | 1 line | Low | Medium |
| 2 | Fix 3: Enable cross-encoder | 1 line | Low | Medium |
| 3 | Fix 1: Add display relevance filter | 10 lines | Low | High |
| 4 | Fix 5: Add semantic_similarity to DB | Migration | Low | Debugging |
| 5 | Fix 4: Entity matching | 50 lines | Medium | High |

## Rollout Strategy

### Phase 1: Config Changes (No Code Deploy)
1. Set `SEMANTIC_SIMILARITY_THRESHOLD=0.50` in env
2. Set `ENABLE_CROSS_ENCODER_RERANK=True` in env
3. Monitor for 48 hours
4. Measure: evidence relevance, pipeline latency, user feedback

### Phase 2: Code Deploy (Feature Flagged)
1. Deploy Fix 1 with `ENABLE_DISPLAY_RELEVANCE_FILTER=False`
2. Enable on staging, test thoroughly
3. Enable for internal users first
4. Gradual rollout to 10% → 50% → 100%

### Phase 3: Entity Matching
1. Deploy Fix 4 with `ENABLE_ENTITY_MATCHING_FOR_DISPLAY=False`
2. Enable on staging with comprehensive test suite
3. A/B test with beta users
4. Full rollout after validation

## Success Metrics

| Metric | Before | Target |
|--------|--------|--------|
| Evidence directly addresses claim (human eval) | ~60% | >85% |
| User reports of "wrong evidence" | Baseline | -50% |
| Evidence contains claim entities (for specific claims) | ~40% | >75% |
| Pipeline latency increase | 0ms | <100ms |

## Monitoring

After deployment, monitor:
1. `semantic_similarity` distribution in production
2. Evidence display count per claim (should rarely be 0)
3. User feedback specifically about evidence quality
4. Pipeline latency percentiles (p50, p95, p99)
