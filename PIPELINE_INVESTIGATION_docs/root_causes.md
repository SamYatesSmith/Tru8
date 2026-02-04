# Tru8 Report Quality Investigation: Root Causes

## Executive Summary

The investigation identified **5 primary root causes** for why irrelevant sources appear as "Evidence Sources" in Truth Reports. The core issue is a **gap between scoring and display** - evidence passes through filtering for verdict computation but the display selection ignores claim-specific relevance.

## Root Cause 1: Evidence Display Selection Ignores Relevance

**Severity:** CRITICAL

**Location:** `app/pipeline/judge.py:316, 363, 389`

**Code:**
```python
supporting_evidence=evidence[:3],  # Top 3 evidence pieces
```

**Problem:**
- The display selection simply takes the first 3 items by sort order (`final_score`)
- There is NO relevance check between the claim and evidence before display
- Evidence that passes credibility/freshness thresholds gets shown regardless of whether it actually addresses the specific claim
- The variable is misleadingly named `supporting_evidence` but it's NOT filtered for support

**Why This Causes Symptoms:**
- A source about "Tesla sales in 2023" could appear as evidence for a claim about "Tesla Q4 2022 delivery numbers"
- Both are Tesla-related, both pass credibility checks, but one doesn't address the specific claim

**Evidence:**
- Line 363: `supporting_evidence=evidence[:3]` - no relevance filter
- Line 512-515 in `_prepare_judgment_context()`: Judge sees top 5 but display shows top 3
- The evidence list is sorted by `final_score` which is credibility × recency × combined_score
- `combined_score` = (relevance_score + semantic_similarity) / 2

---

## Root Cause 2: Semantic Similarity Threshold Too Low (0.35)

**Severity:** HIGH

**Location:** `app/core/config.py:144`

**Code:**
```python
SEMANTIC_SIMILARITY_THRESHOLD: float = Field(0.35, env="SEMANTIC_SIMILARITY_THRESHOLD")
```

**Problem:**
- 0.35 is an extremely permissive threshold
- Allows topically related content to pass through as "relevant"
- A similarity of 0.35 means only ~35% semantic overlap with the claim
- For specific claims (timestamps, exact numbers, legal refs), this allows generalized content through

**Why This Causes Symptoms:**
- Claim: "Tesla reported exactly 1.31M vehicle deliveries in Q4 2022"
- Evidence: "Tesla delivery numbers show strong growth" (general Tesla coverage)
- Similarity might be 0.45-0.55 (about Tesla, about deliveries) but doesn't have the specific number

**Comparison:**
| Threshold | Effect |
|-----------|--------|
| 0.35 (current) | Topically related passes through |
| 0.50 | Moderate filtering, some irrelevant slips through |
| 0.65 | Strong filtering, requires direct relevance |
| 0.75+ | Very strict, may over-filter |

---

## Root Cause 3: Cross-Encoder Reranking Disabled

**Severity:** MEDIUM-HIGH

**Location:** `app/core/config.py:191`

**Code:**
```python
ENABLE_CROSS_ENCODER_RERANK: bool = Field(False, env="ENABLE_CROSS_ENCODER_RERANK")
```

**Problem:**
- Cross-encoders process claim+evidence pairs with full attention
- They provide much more accurate relevance scores than bi-encoders
- Bi-encoders (current) compare embeddings independently, missing nuanced relationships
- The cross-encoder is implemented (`retrieve.py:685-746`) but disabled

**Why This Causes Symptoms:**
- Bi-encoder: "Tesla deliveries 2022" vs "Tesla deliveries article" → High similarity (same topic)
- Cross-encoder: Would detect "article discusses 2023, not 2022" → Lower score

**Technical Note:**
- Cross-encoder adds ~50ms latency for 10 pairs
- Currently fully implemented but feature-flagged off
- Model: `cross-encoder/ms-marco-MiniLM-L-6-v2`

---

## Root Cause 4: NLI-Based Relevance Filtering Disabled

**Severity:** MEDIUM

**Location:** `app/core/config.py:137`

**Code:**
```python
ENABLE_EVIDENCE_RELEVANCE_FILTER: bool = Field(False, env="ENABLE_EVIDENCE_RELEVANCE_FILTER")
```

**Problem:**
- The NLI verify stage had a relevance gating mechanism
- Would filter evidence below 0.65 relevance BEFORE expensive NLI inference
- Off-topic evidence would be marked as neutral (skipped)
- The entire NLI stage is now bypassed (`pipeline.py:564-577`)

**Why This Causes Symptoms:**
- Evidence about a related but different aspect passes through unchecked
- No semantic analysis between claim assertions and evidence assertions

**Note:** The full NLI stage was disabled for performance (80-100s savings). Re-enabling relevance filtering alone (without full NLI) could help without the latency cost.

---

## Root Cause 5: No Claim-Specific Entity Matching for Display

**Severity:** MEDIUM-HIGH

**Location:** None (missing mechanism)

**Problem:**
- Claims contain specific entities: timestamps, numbers, legal references, names
- Evidence is filtered by general semantic similarity and credibility
- There is NO check that evidence contains the claim's key entities
- A claim about "January 15, 2024" could show evidence from "2023 summary articles"

**Why This Causes Symptoms:**

| Claim Type | Specific Entity | What Gets Through |
|------------|-----------------|-------------------|
| Timestamp | "posted at 3:15 PM on Jan 15" | Any article about the topic |
| Numeric | "exactly 1.31 million" | General stats articles |
| Legal | "Section 106 of the Act" | Articles about the Act generally |
| Publication | "published in Nature on Dec 5" | Any Nature article reference |

**Current State:**
- `key_entities` extracted during claim extraction (`extract.py`)
- Entities NOT used to validate evidence selection
- Entity matching exists for API routing but not for display filtering

---

## Additional Contributing Factors

### Factor A: Confidence Uses Evidence Count, Not Quality
**Location:** `judge.py:962-998`

The overall credibility score factors in evidence count. Having many topically-related sources can inflate confidence even when none directly address the claim.

### Factor B: Top-K Always Returns Something
**Location:** `retrieve.py:859-873`

Adaptive fallback keeps top 3 by credibility if all evidence would be filtered. This prevents empty results but can show low-relevance sources.

### Factor C: Evidence Snippet Length Limits Context
**Location:** `config.py:136`

`EVIDENCE_SNIPPET_LENGTH = 400` characters may truncate context needed to see that evidence doesn't match.

---

## Summary Table

| Root Cause | Location | Fix Complexity | Impact |
|------------|----------|----------------|--------|
| 1. Display ignores relevance | `judge.py:363` | LOW | HIGH |
| 2. Similarity threshold too low | `config.py:144` | LOW | MEDIUM |
| 3. Cross-encoder disabled | `config.py:191` | LOW | MEDIUM |
| 4. NLI relevance filter disabled | `config.py:137` | MEDIUM | MEDIUM |
| 5. No entity matching for display | Missing | MEDIUM | HIGH |

## Recommended Priority

1. **Immediate:** Add relevance threshold to display selection (Root Cause 1)
2. **Quick Win:** Raise semantic similarity threshold to 0.50 (Root Cause 2)
3. **Enable:** Cross-encoder reranking (Root Cause 3)
4. **Medium-term:** Implement entity matching for display (Root Cause 5)
5. **Optional:** Re-enable NLI relevance filter (Root Cause 4)
