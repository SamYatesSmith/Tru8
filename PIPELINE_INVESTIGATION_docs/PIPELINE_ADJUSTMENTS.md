# Pipeline Adjustments: LLM Relevance Scorer Implementation

## Executive Summary

This document details the architectural change to replace **embedding-based evidence ranking** with an **LLM-based relevance scorer**. The goal is to improve evidence-claim matching by using AI that understands "does this evidence answer the claim?" rather than just "is this text topically similar?"

---

## The Problem

### Current Approach: Semantic Similarity
```
Evidence Text: "NCAS is a UK research centre focused on atmospheric science"
Claim: "NCAS published a study showing cold extremes increased"

Semantic Similarity Score: 0.72 (HIGH - same topic)
Actual Usefulness: LOW (doesn't address whether the claim is true)
```

### Needed Approach: Evidential Relevance
```
Evidence Text: "NCAS 2024 study found cold extreme events increased 40% in Europe"
Claim: "NCAS published a study showing cold extremes increased"

Evidential Relevance: HIGH (directly addresses the claim)
```

**The core issue**: Embeddings measure topical overlap, not whether evidence helps verify a claim.

---

## Proposed Solution: LLM Relevance Scorer

### New Pipeline Flow

```
BEFORE (Current):
┌──────────────┐    ┌─────────────────────┐    ┌──────────────────┐    ┌─────────────┐
│   Retrieve   │ -> │ Bi-Encoder Ranking  │ -> │ Cross-Encoder    │ -> │   Judge     │
│  (Web+API)   │    │ (semantic similarity)│    │ Reranking        │    │  (Top 5)    │
└──────────────┘    └─────────────────────┘    └──────────────────┘    └─────────────┘
                              ↑                         ↑
                         REDUNDANT                  REDUNDANT


AFTER (Proposed):
┌──────────────┐    ┌─────────────────────┐    ┌─────────────┐
│   Retrieve   │ -> │ LLM Relevance       │ -> │   Judge     │
│  (Web+API)   │    │ Scorer (GPT-4o-mini)│    │  (Top 5-10) │
└──────────────┘    └─────────────────────┘    └─────────────┘
                              ↑
                     NEW: "Does this evidence
                      address the claim?"
```

---

## Components Affected

### 1. REMOVED: Bi-Encoder Ranking

**File**: `backend/app/pipeline/retrieve.py`

**Function**: `_rank_evidence_with_embeddings()` (lines 598-720)

**What it does**:
- Takes claim text and evidence snippets
- Generates embeddings using `all-MiniLM-L6-v2` model
- Calculates cosine similarity between claim and each evidence
- Ranks evidence by similarity score
- Filters below `SEMANTIC_SIMILARITY_THRESHOLD` (0.25)

**Called by**:
- `_retrieve_evidence_for_single_claim()` at line 264

**Calls**:
- `rank_evidence_by_similarity()` from `embeddings.py:229`
- `get_embedding_service()` from `embeddings.py:317`
- `embed_claim_and_evidence()` from `embeddings.py:203`

**Config settings that become unused**:
```python
# backend/app/core/config.py
ENABLE_SEMANTIC_RELEVANCE_FILTER: bool = Field(True)  # Line 170
SEMANTIC_SIMILARITY_THRESHOLD: float = Field(0.25)    # Line 172
SIMILARITY_TIER1_LENIENT: float = Field(0.25)         # Line 97
SIMILARITY_TIER2_STANDARD: float = Field(0.40)        # Line 100
SIMILARITY_TIER3_STRICT: float = Field(0.60)          # Line 103
```

**Action**: BYPASS - Replace call at line 264 with LLM relevance scorer

---

### 2. REMOVED: Cross-Encoder Reranking

**File**: `backend/app/pipeline/retrieve.py`

**Function**: `_rerank_with_cross_encoder()` (lines 724-785)

**What it does**:
- Takes already-ranked evidence from bi-encoder
- Loads `cross-encoder/ms-marco-MiniLM-L-6-v2` model (~80MB)
- Creates (claim, evidence) pairs
- Scores each pair with cross-encoder
- Re-sorts by cross-encoder score

**Called by**:
- `_retrieve_evidence_for_single_claim()` at line 270

**Calls**:
- `CrossEncoder` from `sentence_transformers` (lazy loaded)

**Memory impact**:
- Model size: ~80MB
- Loaded on first use, stays in memory

**Action**: REMOVE - No longer needed, LLM does this better

---

### 3. MODIFIED: Display Evidence Selection

**File**: `backend/app/pipeline/judge.py`

**Function**: `_select_display_evidence()` (lines 63-117)

**What it does**:
- Receives evidence already ranked by similarity
- Applies minimum similarity thresholds:
  - `MIN_DISPLAY_SIMILARITY = 0.25` (web sources)
  - `MIN_API_DISPLAY_SIMILARITY = 0.35` (API sources)
- Returns top N items passing threshold

**Called by**:
- `judge_claim()` at lines 392, 439, 465
- `_judge_batch_fallback()` at lines 1412, 1435

**Current logic** (lines 91-117):
```python
# Sort by semantic_similarity (primary), then combined_score (fallback)
sorted_evidence = sorted(
    evidence,
    key=lambda x: (x.get('semantic_similarity', 0), x.get('combined_score', 0)),
    reverse=True
)

# Filter: ALL sources must meet relevance threshold
for e in sorted_evidence:
    similarity = e.get('semantic_similarity', 0)
    threshold = MIN_API_DISPLAY_SIMILARITY if is_api_source else MIN_DISPLAY_SIMILARITY
    if similarity >= threshold:
        filtered.append(e)
```

**Action**: MODIFY - Change to sort by `llm_relevance_score` instead of `semantic_similarity`

---

### 4. RETAINED: Embedding Service (Partial Use)

**File**: `backend/app/services/embeddings.py`

**The embedding service is still needed for**:

| Use Case | File | Lines | Keep? |
|----------|------|-------|-------|
| Evidence ranking | `retrieve.py` | 264, 598-720 | **REMOVE** |
| Cross-encoder input | `retrieve.py` | 270, 724-785 | **REMOVE** |
| Vector store storage | `retrieve.py` | 280, 1493-1524 | **KEEP** (optional) |
| Vector store retrieval | `retrieve.py` | 1527-1544 | **KEEP** (optional) |
| Snippet extraction | `evidence.py` | 579-632 | **KEEP** |
| Fact-check similarity | `factcheck_parser.py` | 200-228 | **KEEP** |
| NLI relevance filter | `verify.py` | 407-459 | Already BYPASSED |

**Decision**: Keep embedding service but it will be used less frequently

---

### 5. ALREADY BYPASSED: NLI Verification

**File**: `backend/app/workers/pipeline.py`

**Status**: Already disabled (lines 571-583)

```python
# Stage 4: NLI Verification - BYPASSED
# NLI is disabled because PASS_NLI_VERDICT_TO_JUDGE=False
verifications = {}  # Empty structure
```

**Config**:
```python
PASS_NLI_VERDICT_TO_JUDGE: bool = Field(False)  # Line 196
```

**Action**: No change needed - already bypassed

---

## New Component: LLM Relevance Scorer

### Proposed Location

**New file**: `backend/app/pipeline/relevance_scorer.py`

### Interface

```python
class LLMRelevanceScorer:
    """Score evidence relevance to claims using GPT-4o-mini"""

    async def score_evidence_batch(
        self,
        claims: List[str],                    # ALL claims together
        evidence_items: List[Dict[str, Any]],
        article_context: str,                 # Full article for context
        max_items: int = 25
    ) -> List[Dict[str, Any]]:
        """
        Score each evidence item for relevance to ANY of the claims.

        Uses article context to understand the full narrative and
        what kind of evidence would actually help verify the claims.

        Returns evidence items with new fields:
        - 'llm_relevance_score' (1-5)
        - 'llm_relevance_rationale' (brief explanation)
        - 'relevant_claims' (list of claim indices this evidence supports)

        Scores:
            5 = Directly confirms or refutes a claim with specific data/quotes
            4 = Strongly relevant, provides key supporting context
            3 = Somewhat relevant, partial information
            2 = Tangentially related, doesn't address claims directly
            1 = Off-topic or irrelevant to all claims
        """
```

### Integration Point

**File**: `backend/app/pipeline/retrieve.py`

**Location**: The LLM Relevance Scorer runs ONCE per check (not per claim) after all evidence is gathered.

**Integration strategy**:

1. Gather all evidence from web + APIs for ALL claims (existing code)
2. Call LLM Relevance Scorer ONCE with:
   - All claims together
   - All evidence items (up to 50)
   - Article context
3. Filter to items scoring >= 4
4. Distribute scored evidence back to claims

```python
# IN PIPELINE (workers/pipeline.py) - After retrieve, before judge

from app.pipeline.relevance_scorer import get_relevance_scorer

# Score evidence relevance using LLM
scorer = await get_relevance_scorer()
scored_evidence = await scorer.score_evidence_batch(
    claims=[c.get('text') for c in claims],
    evidence_items=all_evidence[:50],  # Limit to prevent token overflow
    article_context=article_excerpt
)

# Filter to high-relevance items only
relevant_evidence = [
    e for e in scored_evidence
    if e.get('llm_relevance_score', 0) >= settings.LLM_RELEVANCE_MIN_SCORE
]
```

---

## Config Changes

### New Settings

```python
# backend/app/core/config.py

# LLM Relevance Scorer
ENABLE_LLM_RELEVANCE_SCORER: bool = Field(True, env="ENABLE_LLM_RELEVANCE_SCORER")
LLM_RELEVANCE_MODEL: str = Field("gpt-4o-mini-2024-07-18", env="LLM_RELEVANCE_MODEL")
LLM_RELEVANCE_MIN_SCORE: int = Field(4, env="LLM_RELEVANCE_MIN_SCORE")  # Minimum score to keep (4 = strongly relevant)
LLM_RELEVANCE_MAX_EVIDENCE: int = Field(50, env="LLM_RELEVANCE_MAX_EVIDENCE")  # Max items to score per check
LLM_RELEVANCE_CACHE_TTL: int = Field(3600, env="LLM_RELEVANCE_CACHE_TTL")  # Cache TTL in seconds (1 hour)
```

### Deprecated Settings (Can Remove Later)

```python
# These become unused but can be kept for fallback
ENABLE_SEMANTIC_RELEVANCE_FILTER: bool  # No longer primary filter
SEMANTIC_SIMILARITY_THRESHOLD: float    # No longer used
SIMILARITY_TIER1_LENIENT: float         # No longer used
SIMILARITY_TIER2_STANDARD: float        # No longer used
SIMILARITY_TIER3_STRICT: float          # No longer used
```

---

## Performance Impact

### Removed Operations (Per Claim)

| Operation | Time | Memory |
|-----------|------|--------|
| Bi-encoder embedding (30 items) | ~500ms | ~50MB model |
| Cross-encoder scoring (30 items) | ~800ms | ~80MB model |
| **Total removed** | **~1.3s** | **~130MB** |

### Added Operations (Per Claim)

| Operation | Time | Cost |
|-----------|------|------|
| GPT-4o-mini API call | ~2-4s | ~$0.001 |

### Net Impact

- **Time**: Potentially +1-2s per claim (but better accuracy)
- **Memory**: -130MB (no ML models loaded for ranking)
- **Cost**: +$0.001-0.002 per claim (~$0.01-0.02 per check with 12 claims)
- **Accuracy**: Significantly improved (AI understands evidential value)

---

## Code Changes Summary

### Files to Modify

| File | Action | Changes |
|------|--------|---------|
| `backend/app/pipeline/retrieve.py` | **MAJOR** | Replace bi-encoder + cross-encoder with LLM scorer |
| `backend/app/pipeline/judge.py` | **MINOR** | Update `_select_display_evidence` to use new score field |
| `backend/app/core/config.py` | **ADD** | New LLM relevance settings |

### Files to Add

| File | Purpose |
|------|---------|
| `backend/app/pipeline/relevance_scorer.py` | New LLM relevance scorer class |

### Files Unchanged (But Less Used)

| File | Notes |
|------|-------|
| `backend/app/services/embeddings.py` | Still used for snippets, vector store, fact-check parsing |
| `backend/app/pipeline/verify.py` | Already bypassed, no change |

---

## Fallback Strategy

If LLM relevance scorer fails (API error, timeout, etc.):

```python
try:
    ranked_evidence = await scorer.score_evidence_batch(claim_text, evidence)
except Exception as e:
    logger.warning(f"LLM relevance scorer failed: {e}, falling back to embedding ranking")
    # Fallback to existing bi-encoder ranking
    ranked_evidence = await self._rank_evidence_with_embeddings(claim_text, evidence)
```

This keeps the existing code available as a fallback, just not the primary path.

---

## Downstream Effects

### Judge Stage

**Current**: Receives evidence sorted by `semantic_similarity`
**After**: Receives evidence sorted by `llm_relevance_score`

The Judge's `_prepare_judgment_context()` (line 565) doesn't need changes - it just takes top 5 evidence items. The items will now be more relevant.

### Evidence Storage

**Current**: Stores evidence with `semantic_similarity` field
**After**: Stores evidence with `llm_relevance_score` field

Update `_store_evidence_embeddings()` to include the new score field.

### Raw Evidence Tracking

**Current**: `raw_evidence` includes `semantic_similarity`
**After**: Include both for debugging:
```python
{
    "semantic_similarity": 0.72,      # Legacy, for comparison
    "llm_relevance_score": 4,         # New primary score
    "llm_relevance_rationale": "..."  # Optional: why the score
}
```

---

## Testing Plan

### Unit Tests

1. Test LLM relevance scorer with mock API responses
2. Test fallback behavior when API fails
3. Test score filtering logic

### Integration Tests

1. Run full pipeline with LLM scorer enabled
2. Compare results with legacy embedding ranking
3. Measure time/cost impact

### Quality Tests

1. Run same article through both systems
2. Compare evidence selected for each claim
3. Manual review: Is LLM-selected evidence more useful?

---

## Migration Path

### Phase 1: Add LLM Scorer (Parallel)
- Add new `relevance_scorer.py`
- Add config settings
- Run BOTH systems, log comparison

### Phase 2: Switch Primary
- Change retrieve.py to use LLM scorer as primary
- Keep embedding ranking as fallback
- Monitor production performance

### Phase 3: Remove Legacy (Later)
- Remove bi-encoder ranking code
- Remove cross-encoder code
- Clean up deprecated config

---

## Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| LLM API latency | Batch evidence in single call; use fast model |
| LLM API cost | GPT-4o-mini is cheap (~$0.001/claim) |
| LLM API failure | Fallback to embedding ranking |
| Inconsistent scoring | Use structured output, low temperature |
| Rate limiting | Implement retry with backoff |

---

## Open Questions - RESOLVED

1. **Batch across claims?** → **YES, with article context**
   - Include the article context in the prompt so LLM understands the full narrative
   - Batch ALL claims and their evidence in a SINGLE API call
   - This provides better context for scoring (LLM can see how evidence relates to multiple claims)

2. **Include rationale?** → **YES**
   - Include brief rationale for each score (useful for debugging and transparency)
   - Rationale stored in `llm_relevance_rationale` field

3. **Score threshold?** → **4/5 minimum**
   - Start with `LLM_RELEVANCE_MIN_SCORE = 4`
   - This ensures only "strongly relevant" or "direct proof" evidence passes through
   - Can tune down to 3 if too restrictive

4. **Cache scores?** → **YES, if no performance impact**
   - Cache claim+evidence hash → score
   - Same evidence for same claim should get same score
   - Use Redis with reasonable TTL (1 hour)

---

## Article Context Flow Pattern

### How Article Content Currently Reaches LLM Prompts

The pipeline already passes article content to the Judge stage. The LLM Relevance Scorer will reuse this exact pattern.

#### Step 1: Extract Article Text

**File:** `backend/app/workers/pipeline.py` (line 598)

```python
# Extract article excerpt for context-aware judgment
article_excerpt = content.get("content", "")[:5000]
```

The `content` dict contains the full ingested article. We take the first 5000 characters to stay within token limits.

#### Step 2: Pass Through Pipeline

**File:** `backend/app/workers/pipeline.py` (line 602)

```python
results = asyncio.run(
    asyncio.wait_for(
        judge_claims_with_llm(claims, verifications, evidence, article_context=article_excerpt),
        timeout=judge_timeout
    )
)
```

The article excerpt is passed as `article_context` parameter through the async chain.

#### Step 3: Build Context Section

**File:** `backend/app/pipeline/judge.py` (lines 669-682)

```python
article_context_section = ""
if article_context:
    article_context_section = f"""
ARTICLE CONTEXT (for detecting cherry-picked claims, satire, or missing qualifiers):
{article_context[:5000]}

IMPORTANT: Use this article context to:
- Detect if the claim is cherry-picked or taken out of context
- Identify satirical or humorous content that shouldn't be fact-checked literally
- Understand the full narrative before judging isolated claims
- Notice qualifiers or caveats in the surrounding text
"""
```

#### Step 4: Assemble Full Prompt

**File:** `backend/app/pipeline/judge.py` (lines 774-787)

```python
base_context = f"""
CLAIM TO JUDGE:
{claim_text}
{temporal_warning}{stale_warning}{rhetorical_warning}{article_context_section}
EVIDENCE ANALYSIS:
Total Evidence Pieces: {signals.get('total_evidence', 0)}
...
EVIDENCE DETAILS:
{chr(10).join(evidence_summary)}

Based on this analysis, provide your final judgment."""
```

#### Step 5: Send to OpenAI

**File:** `backend/app/pipeline/judge.py` (lines 806-815)

```python
json={
    "model": "gpt-4o-mini-2024-07-18",
    "messages": [
        {"role": "system", "content": self.system_prompt},
        {"role": "user", "content": context}  # The assembled prompt
    ],
    "max_tokens": self.judge_max_tokens,
    "temperature": self.temperature,
    "response_format": {"type": "json_object"}
}
```

### Adapting for LLM Relevance Scorer

The same pattern applies to the new LLM Relevance Scorer:

```python
async def score_evidence_relevance(
    claims: List[str],
    evidence_items: List[Dict],
    article_context: str  # Same article excerpt already available
) -> List[Dict]:
    """
    Score all evidence items for relevance to the claims.
    Uses article context for better understanding of what the claims need.
    """

    # Format evidence for scoring
    evidence_text = "\n\n".join([
        f"[{i+1}] {e.get('title', 'No title')}\n"
        f"Source: {e.get('source', 'Unknown')}\n"
        f"Snippet: {e.get('snippet', e.get('content', ''))[:500]}"
        for i, e in enumerate(evidence_items[:25])  # Limit to 25
    ])

    # Build prompt with article context
    prompt = f"""
ARTICLE CONTEXT:
{article_context[:5000]}

CLAIMS TO VERIFY:
{chr(10).join([f"{i+1}. {c}" for i, c in enumerate(claims)])}

EVIDENCE ITEMS TO SCORE:
{evidence_text}

For EACH evidence item, score 1-5 how well it helps verify/refute ANY of the claims:

5 = Direct proof or refutation with specific data/quotes
4 = Strongly relevant, provides key supporting context
3 = Somewhat relevant, partial information
2 = Tangentially related, doesn't address claims directly
1 = Off-topic or irrelevant to all claims

Respond with JSON array: [{{"item": 1, "score": 5, "rationale": "brief reason"}}, ...]
"""

    # Send to GPT-4o-mini (same pattern as Judge)
    response = await client.post(
        "https://api.openai.com/v1/chat/completions",
        json={
            "model": "gpt-4o-mini-2024-07-18",
            "messages": [
                {"role": "system", "content": "You are an evidence relevance scorer..."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.1,  # Low for consistency
            "response_format": {"type": "json_object"}
        }
    )
```

### Key Insight: Single API Call for All Claims

Instead of calling the API once per claim, we batch:
- 1 article context (shared)
- N claims (listed together)
- M evidence items (scored once, checked against all claims)

This is efficient because:
1. Same evidence often relevant to multiple claims
2. Article context provides shared understanding
3. Reduces API calls from N to 1 per retrieve stage

---

## Score System Analysis

### All Scores Currently Collected

| Score | Where Set | Purpose | Status After Change |
|-------|-----------|---------|---------------------|
| `relevance_score` | `evidence.py:280` | Word overlap with claim | **KEEP** - Initial retrieval ordering |
| `semantic_similarity` | `retrieve.py:649` | Embedding cosine similarity | **REDUNDANT** - Replaced by LLM |
| `combined_score` | `retrieve.py:650` | `(relevance + similarity) / 2` | **REDUNDANT** - Used similarity |
| `cross_encoder_score` | `retrieve.py:765` | Cross-encoder reranking | **REDUNDANT** - Removed |
| `bi_encoder_score` | `retrieve.py:766` | Backup of combined_score | **REDUNDANT** - Removed |
| `credibility_score` | `retrieve.py:840` | Source trustworthiness | **KEEP** - Orthogonal to relevance |
| `recency_score` | `retrieve.py:843` | How recent the evidence is | **KEEP** - Still valuable |
| `final_score` | `retrieve.py:847` | `base * credibility * recency` | **MODIFY** - Use LLM score as base |
| `llm_relevance_score` | NEW | LLM's 1-5 rating | **NEW** - Primary ranking signal |

### Score Flow - BEFORE

```
evidence.py                     retrieve.py                              judge.py
┌─────────────────┐            ┌─────────────────────────────────────┐   ┌───────────────┐
│ relevance_score │ ──────────>│ semantic_similarity (bi-encoder)    │   │               │
│ (word overlap)  │            │         ↓                           │   │ Sort by       │
└─────────────────┘            │ combined_score = (rel + sim) / 2    │   │ semantic_     │
                               │         ↓                           │──>│ similarity    │
                               │ cross_encoder_score (rerank)        │   │               │
                               │         ↓                           │   │ Filter by     │
                               │ final_score = base * cred * recency │   │ threshold     │
                               └─────────────────────────────────────┘   └───────────────┘
```

### Score Flow - AFTER

```
evidence.py                     retrieve.py                              judge.py
┌─────────────────┐            ┌─────────────────────────────────────┐   ┌───────────────┐
│ relevance_score │ ──────────>│ llm_relevance_score (GPT-4o-mini)   │   │               │
│ (word overlap)  │            │         ↓                           │   │ Sort by       │
│ (for initial    │            │ Filter: keep score >= 4             │   │ llm_relevance │
│  ordering only) │            │         ↓                           │──>│ _score        │
└─────────────────┘            │ final_score = llm * cred * recency  │   │               │
                               │         ↓                           │   │ (No threshold │
                               │ credibility_score (unchanged)       │   │  - already    │
                               │ recency_score (unchanged)           │   │  filtered)    │
                               └─────────────────────────────────────┘   └───────────────┘
```

### Tier Systems - Clarification

**TWO DIFFERENT TIER SYSTEMS EXIST:**

1. **Similarity Tiers** (config.py:97-103) → **BECOME REDUNDANT**
   ```python
   SIMILARITY_TIER1_LENIENT = 0.25   # Used for semantic filtering
   SIMILARITY_TIER2_STANDARD = 0.40  # Used for display
   SIMILARITY_TIER3_STRICT = 0.60    # Used for high-confidence
   ```
   **These are thresholds for semantic similarity scores. With LLM scoring, these are replaced by `LLM_RELEVANCE_MIN_SCORE`.**

2. **Source Credibility Tiers** (source_credibility.json) → **KEEP**
   ```python
   news_tier1: BBC, Reuters, AP        # Credibility: 0.9
   news_tier2: Guardian, Telegraph     # Credibility: 0.8
   news_tier3_regional: Local news     # Credibility: 0.6
   academic: Universities, journals    # Credibility: 0.95
   government: .gov sites              # Credibility: 0.95
   ```
   **These are about source trustworthiness, NOT relevance. Still needed.**

### Compound Effects of Removing Similarity Tiers

| Code Location | Current Use | Impact |
|---------------|-------------|--------|
| `judge.py:86` | `MIN_DISPLAY_SIMILARITY = TIER1_LENIENT` | **CHANGE** to `MIN_DISPLAY_RELEVANCE = 4` (LLM score) |
| `retrieve.py:627` | `if similarity < SEMANTIC_SIMILARITY_THRESHOLD` | **REMOVE** - LLM does filtering at score >= 4 |
| `retrieve.py:665` | Fallback references TIER1 | **REMOVE** - LLM handles edge cases |
| `config.py:171` | Comment referencing TIER1 | **UPDATE** comment |

### What Scores Are Still Relevant?

| Score | Relevant? | Reasoning |
|-------|-----------|-----------|
| `credibility_score` | **YES** | Source quality still matters |
| `recency_score` | **YES** | Fresh evidence still matters |
| `relevance_score` | **PARTIAL** | Only for initial ordering before LLM |
| `llm_relevance_score` | **YES (NEW)** | Primary ranking signal |
| `final_score` | **YES** | But formula changes: `llm * cred * recency` |
| `semantic_similarity` | **NO** | Replaced by LLM |
| `combined_score` | **NO** | Replaced by LLM |
| `cross_encoder_score` | **NO** | Removed entirely |

---

## Appendix: Affected Code Locations

### `retrieve.py` - Lines to Modify

```
Line 8:     from app.services.embeddings import get_embedding_service, rank_evidence_by_similarity
            → Remove rank_evidence_by_similarity import

Line 264:   ranked_evidence = await self._rank_evidence_with_embeddings(...)
            → Replace with LLM scorer call

Line 270:   ranked_evidence = await self._rerank_with_cross_encoder(...)
            → Remove entirely

Line 598-720: def _rank_evidence_with_embeddings(...)
            → Keep for fallback, mark as legacy

Line 724-785: def _rerank_with_cross_encoder(...)
            → Keep for fallback, mark as legacy
```

### `judge.py` - Lines to Modify

```
Line 86:    MIN_DISPLAY_SIMILARITY = getattr(settings, 'SIMILARITY_TIER1_LENIENT', 0.25)
            → Change to MIN_DISPLAY_RELEVANCE = 4 (LLM score - "strongly relevant" or better)

Line 91-96: sorted_evidence = sorted(..., key=lambda x: (x.get('semantic_similarity', 0), ...))
            → Change to sort by llm_relevance_score

Line 107:   if similarity >= threshold:
            → if llm_score >= MIN_DISPLAY_RELEVANCE:
```

### `config.py` - Lines to Add

```
After line 196 (PASS_NLI_VERDICT_TO_JUDGE):
    # LLM Relevance Scorer
    ENABLE_LLM_RELEVANCE_SCORER: bool = Field(True, env="ENABLE_LLM_RELEVANCE_SCORER")
    LLM_RELEVANCE_MODEL: str = Field("gpt-4o-mini-2024-07-18", env="LLM_RELEVANCE_MODEL")
    LLM_RELEVANCE_MIN_SCORE: int = Field(4, env="LLM_RELEVANCE_MIN_SCORE")  # 4 = strongly relevant
    LLM_RELEVANCE_MAX_EVIDENCE: int = Field(50, env="LLM_RELEVANCE_MAX_EVIDENCE")  # Per check
    LLM_RELEVANCE_CACHE_TTL: int = Field(3600, env="LLM_RELEVANCE_CACHE_TTL")  # 1 hour
```
