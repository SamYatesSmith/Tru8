# Tru8 Report Quality Investigation: Pipeline Map

## Overview

This document maps the complete verification pipeline, identifying the files and functions responsible for each stage from claim extraction through to evidence display.

## Pipeline Flow Diagram

```
URL/Content Input
       │
       ▼
┌──────────────────┐
│  1. INGEST       │ ─── app/pipeline/ingest.py
│  (Fetch content) │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  2. EXTRACT      │ ─── app/pipeline/extract.py
│  (Atomize claims)│
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  3. CLASSIFY     │ ─── app/utils/article_classifier.py
│  (Article domain)│
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  4. PLAN         │ ─── app/utils/query_planner.py
│  (Query building)│
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  5. RETRIEVE     │ ─── app/pipeline/retrieve.py
│  (Evidence fetch)│     app/services/search.py
└────────┬─────────┘     app/services/government_api_client.py
         │
         ▼
┌──────────────────┐
│  6. RANK & FILTER│ ─── app/pipeline/retrieve.py:589-996
│  (Scoring/Filter)│     app/utils/domain_capping.py
└────────┬─────────┘     app/utils/deduplication.py
         │
         ▼
┌──────────────────┐
│  7. VERIFY (NLI) │ ─── app/pipeline/verify.py
│  [BYPASSED]      │     (Currently disabled)
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  8. JUDGE        │ ─── app/pipeline/judge.py
│  (Final verdict) │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  9. DISPLAY      │ ─── app/workers/pipeline.py:282-348
│  (Evidence shown)│     (saves to DB → API response)
└──────────────────┘
```

## Stage-by-Stage Breakdown

### Stage 1: Ingest
| Attribute | Value |
|-----------|-------|
| **File** | `app/pipeline/ingest.py` |
| **Key Functions** | `UrlIngester.ingest()`, `ImageIngester.ingest()`, `VideoIngester.ingest()` |
| **Inputs** | URL, image, or video content |
| **Outputs** | `{success, content, metadata}` |
| **Notes** | Handles YouTube transcripts, PDF extraction, OCR |

### Stage 2: Extract Claims
| Attribute | Value |
|-----------|-------|
| **File** | `app/pipeline/extract.py` (654 lines) |
| **Key Class** | `ClaimExtractor` |
| **Key Functions** | `extract_claims()`, `_extract_with_openai()`, `_validate_and_refine_claims()` |
| **Inputs** | Article content + metadata |
| **Outputs** | List of claims with `text`, `confidence`, `category`, `key_entities`, `temporal_markers` |
| **Model** | GPT-4o-mini (fallback: Gemini 1.5 Flash) |
| **Notes** | Max 12 claims per article |

### Stage 3: Classify Article
| Attribute | Value |
|-----------|-------|
| **File** | `app/utils/article_classifier.py` |
| **Key Function** | `classify_article()` |
| **Inputs** | Title, URL, content excerpt |
| **Outputs** | `ArticleClassification(primary_domain, jurisdiction, confidence)` |
| **Notes** | Runs once per check, attached to all claims |

### Stage 4: Plan Queries
| Attribute | Value |
|-----------|-------|
| **File** | `app/utils/query_planner.py` |
| **Key Class** | `LLMQueryPlanner` |
| **Key Function** | `plan_queries_batch()` |
| **Inputs** | Claims with temporal_analysis + article_classification |
| **Outputs** | Per-claim: `{queries[], freshness, claim_type, priority_sources}` |
| **Model** | GPT-4o-mini |
| **Notes** | Dynamic freshness per claim based on article context |

### Stage 5: Retrieve Evidence
| Attribute | Value |
|-----------|-------|
| **File** | `app/pipeline/retrieve.py` (1485 lines) |
| **Key Class** | `EvidenceRetriever` |
| **Key Functions** | `_retrieve_evidence_for_single_claim()` (line 143), `_execute_planned_queries()` (line 290) |
| **Inputs** | Claims, query plans |
| **Outputs** | Evidence by claim: `{url, title, snippet, published_date, relevance_score}` |
| **Notes** | Parallel web search + government API retrieval |

### Stage 6: Rank & Filter Evidence
| Attribute | Value |
|-----------|-------|
| **File** | `app/pipeline/retrieve.py` |
| **Key Functions** | `_rank_evidence_with_embeddings()` (line 589), `_apply_credibility_weighting()` (line 748) |
| **Scoring Components** | |
| - Semantic similarity | Bi-encoder embeddings (threshold: 0.35) |
| - Cross-encoder | DISABLED (`ENABLE_CROSS_ENCODER_RERANK=False`) |
| - Credibility | Domain tier lookup (threshold: 0.65) |
| - Recency | Date-based weighting |
| **Final Score** | `combined_score = (relevance + similarity) / 2` → `final_score = combined * credibility * recency` |

**Filtering Pipeline:**
1. **Semantic filter** (line 614-625): Removes evidence < 0.35 similarity
2. **Auto-exclude** (line 826-838): Removes blacklisted sources
3. **Credibility threshold** (line 847-871): Removes < 0.65 credibility
4. **Deduplication** (line 930-941): Content-hash based
5. **Source diversity** (line 941-953): Ownership analysis
6. **Domain capping** (line 953-971): Max 3 per domain

### Stage 7: NLI Verification (BYPASSED)
| Attribute | Value |
|-----------|-------|
| **File** | `app/pipeline/verify.py` (759 lines) |
| **Status** | **BYPASSED** (see `pipeline.py:564-577`) |
| **Reason** | `PASS_NLI_VERDICT_TO_JUDGE=False` means Judge ignores NLI anyway |
| **Notes** | Saves 80-100 seconds per check |

### Stage 8: Judge
| Attribute | Value |
|-----------|-------|
| **File** | `app/pipeline/judge.py` (1374 lines) |
| **Key Class** | `ClaimJudge` |
| **Key Functions** | `judge_claim()`, `_prepare_judgment_context()` (line 489), `_should_abstain()` (line 843) |
| **Inputs** | Claim, verification_signals (empty), evidence |
| **Outputs** | `JudgmentResult(verdict, confidence, rationale, supporting_evidence)` |
| **Model** | GPT-4o-mini (fallback: Gemini 1.5 Flash) |

### Stage 9: Evidence Selection for Display
| Attribute | Value |
|-----------|-------|
| **File** | `app/pipeline/judge.py` |
| **Key Lines** | 316, 363, 389 |
| **Selection Logic** | `supporting_evidence=evidence[:3]` |
| **CRITICAL** | **Simply takes first 3 items by sort order - NO relevance check for display** |

## Data Flow: Evidence Through Pipeline

```
Search Results (Brave/SerpAPI)
       │
       ▼
┌─────────────────────────────────────┐
│ Content Extraction                   │
│ - Full page fetch OR                 │
│ - Search snippet fallback            │
└─────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────┐
│ Semantic Ranking                     │
│ - Bi-encoder: claim vs evidence text │
│ - Filter if similarity < 0.35       │
│ - Add: semantic_similarity field     │
└─────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────┐
│ Credibility Weighting                │
│ - Domain tier lookup                 │
│ - Recency score                      │
│ - Auto-exclude blacklist             │
│ - Filter if credibility < 0.65       │
│ - Add: final_score field             │
└─────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────┐
│ Dedup + Diversity + Capping          │
│ - Remove duplicates                  │
│ - Check ownership diversity          │
│ - Cap at 3 per domain                │
└─────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────┐
│ Evidence to Judge (sorted by final_score)
│ - Top 5 shown to LLM for reasoning   │
│ - TOP 3 SELECTED FOR DISPLAY         │
│ - NO additional relevance check!     │
└─────────────────────────────────────┘
```

## Existing Anti-Laundering Mechanisms

| Mechanism | Location | Status | Threshold |
|-----------|----------|--------|-----------|
| Semantic similarity filter | `retrieve.py:614-625` | **ENABLED** | 0.35 (LOW) |
| Cross-encoder reranking | `retrieve.py:685-746` | **DISABLED** | N/A |
| NLI relevance gating | `verify.py:406-465` | **DISABLED** | 0.65 |
| Credibility threshold | `retrieve.py:847` | **ENABLED** | 0.65 |
| Domain capping | `domain_capping.py` | **ENABLED** | 3/domain |
| Source deduplication | `deduplication.py` | **ENABLED** | 95% similarity |
| Fact-check similarity | `retrieve.py` | **ENABLED** | 0.70 |

## Key Configuration (config.py)

```python
# ENABLED but with issues
SEMANTIC_SIMILARITY_THRESHOLD = 0.35        # TOO LOW - allows topically related but not evidential
SOURCE_CREDIBILITY_THRESHOLD = 0.65         # Reasonable

# DISABLED - potential improvements
ENABLE_CROSS_ENCODER_RERANK = False         # Could provide better relevance
ENABLE_EVIDENCE_RELEVANCE_FILTER = False    # Could gate off-topic evidence
PASS_NLI_VERDICT_TO_JUDGE = False           # NLI bypassed entirely
ENABLE_PRIMARY_SOURCE_DETECTION = False     # Could prioritize primary sources
```

## Critical Finding: Evidence Display Selection

**Location:** `app/pipeline/judge.py:363`

```python
supporting_evidence=evidence[:3],  # Top 3 evidence pieces
```

**Problem:** The variable is named `supporting_evidence` but:
1. It does NOT filter for evidence that actually supports the claim
2. It simply takes the first 3 items sorted by `final_score`
3. `final_score` is based on credibility × recency × (relevance + similarity)/2
4. There is NO claim-specific entity matching or relevance validation before display

This is the **primary root cause** of showing topically related but not evidential sources.
