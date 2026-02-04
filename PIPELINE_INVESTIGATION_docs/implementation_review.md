# Tru8 Evidence Display Quality: Investigation & Implementation Review

**Date:** January 2025
**Status:** Partial implementation deployed to production
**Scope:** Fix for irrelevant sources appearing in Truth Report "Evidence Sources" section

---

## Background

Users reported that "Evidence Sources" shown in Truth Reports sometimes displayed sources that were topically related to a claim but did not actually provide evidence for or against the specific assertion. For example, a claim about "Tesla Q4 2022 deliveries of 1.31M vehicles" might show general Tesla coverage articles rather than sources containing the specific delivery figure.

---

## Investigation Summary

A comprehensive codebase investigation was conducted, producing the following artifacts:

- `report_quality_pipeline_map.md` - Full pipeline flow documentation
- `root_causes.md` - 5 identified root causes with severity ratings
- `fix_plan.md` - Proposed fixes with implementation order and rollout strategy
- `report_quality_trace.md` - Example failure traces
- `pipeline_trace.py` - Diagnostic script for reproducing issues

### Root Causes Identified

| # | Root Cause | Severity | Location |
|---|------------|----------|----------|
| 1 | Evidence display selection ignores relevance | CRITICAL | `judge.py:316, 363, 389` |
| 2 | Semantic similarity threshold too low (0.35) | HIGH | `config.py:144` |
| 3 | Cross-encoder reranking disabled | MEDIUM-HIGH | `config.py:191` |
| 4 | NLI-based relevance filtering disabled | MEDIUM | `config.py:137` |
| 5 | No claim-specific entity matching for display | MEDIUM-HIGH | Not implemented |

### Core Problem

The critical issue was in `judge.py` where evidence for display was selected using:

```python
supporting_evidence = evidence[:3]  # Simply takes first 3 by sort order
```

This selection:
- Took the first 3 items sorted by `final_score` (credibility × recency × combined_score)
- Applied NO relevance check between claim and evidence
- Was misleadingly named `supporting_evidence` but wasn't filtered for actual support

---

## Proposed Fix Plan

The investigation recommended a phased approach:

**Phase 1 (Config-only, no deploy):**
1. Set `SEMANTIC_SIMILARITY_THRESHOLD=0.50` (raise from 0.35)
2. Set `ENABLE_CROSS_ENCODER_RERANK=True`

**Phase 2 (Code deploy):**
3. Add relevance threshold filter to display selection (Fix 1)
4. Add `semantic_similarity` field to database for monitoring (Fix 5)

**Phase 3 (Medium-term):**
5. Implement entity matching for display (Fix 4)

---

## What Was Actually Implemented

### Deployed to Production

**Fix 1: Display Relevance Filter** - IMPLEMENTED

A new helper function `_select_display_evidence()` was added to `judge.py`:

```python
def _select_display_evidence(evidence: List[Dict[str, Any]], max_items: int = 3) -> List[Dict[str, Any]]:
    if not evidence:
        return []

    MIN_DISPLAY_SIMILARITY = 0.40

    # Sort by semantic_similarity (primary), then combined_score (fallback)
    sorted_evidence = sorted(
        evidence,
        key=lambda x: (x.get('semantic_similarity', 0), x.get('combined_score', 0)),
        reverse=True
    )

    # Filter: require minimum relevance OR API source (always trustworthy)
    filtered = [
        e for e in sorted_evidence
        if e.get('semantic_similarity', 0) >= MIN_DISPLAY_SIMILARITY
        or e.get('external_source_provider')
    ]

    # Return filtered if available, else top 1 as fallback
    return filtered[:max_items] if filtered else sorted_evidence[:1]
```

**Call sites updated:** 5 locations (investigation identified 3, implementation found 2 additional in `PipelineJudge` class)
- Line 355: Abstention path
- Line 402: Main judgment path
- Line 428: Error fallback path
- Line 1375: Pipeline fallback
- Line 1398: Pipeline error fallback

**Tests:** All 22 unit tests in `test_judge.py` passed after implementation.

**Deployment:** Successfully deployed to Fly.io production (both web and worker machines).

---

## Implementation Gaps

| Planned Item | Status | Notes |
|--------------|--------|-------|
| Fix 1: Display relevance filter | **DONE** | Deployed with 0.40 threshold |
| Fix 2: Raise upstream threshold to 0.50 | **NOT DONE** | Requires env var change in Fly.io |
| Fix 3: Enable cross-encoder | **ALREADY DONE** | Discovery: `fly.toml` already has `ENABLE_CROSS_ENCODER_RERANK=true` |
| Fix 4: Entity matching | **NOT DONE** | Planned for Phase 3 |
| Fix 5: Add semantic_similarity to DB | **NOT DONE** | Requires migration |

### Threshold Discrepancy

- **Plan suggested:** 0.45 minimum display similarity
- **Implemented:** 0.40 minimum display similarity

The implemented threshold is slightly more permissive than proposed. This was a deliberate choice to reduce risk of over-filtering on initial deployment.

### Configuration

The `MIN_DISPLAY_SIMILARITY` constant is currently hardcoded in the function rather than config-driven. The plan recommended adding it to `config.py` for runtime adjustability.

---

## Recommended Next Steps

### Immediate (Config Changes)

1. **Raise upstream threshold:** Set `SEMANTIC_SIMILARITY_THRESHOLD=0.50` in Fly.io environment variables. This filters low-relevance evidence earlier in the pipeline (at retrieve stage) rather than only at display stage.

### Short-term (Code Changes)

2. **Make threshold configurable:** Move `MIN_DISPLAY_SIMILARITY` to `config.py` so it can be adjusted via environment variable without code deploy.

3. **Add semantic_similarity to database:** Create migration to add `semantic_similarity` field to Evidence model. This enables:
   - Production monitoring of relevance scores
   - Frontend display of relevance indicators
   - Debugging when evidence seems off-topic

### Medium-term

4. **Implement entity matching:** For claims with specific entities (numbers, dates, legal references), validate that displayed evidence contains those entities. The fix plan includes a proposed implementation (~50 lines).

---

## Verification

To verify the fix is working:

1. **Run diagnostic script:**
   ```bash
   python scripts/pipeline_trace.py --url "https://example.com/article"
   ```
   Check `trace_summary.md` for `semantic_similarity` scores of displayed evidence.

2. **Production monitoring:**
   - Watch for claims with fewer than 3 displayed evidence items (indicates filtering is active)
   - Monitor user feedback for "wrong evidence" reports
   - Check pipeline latency (should be minimal impact)

3. **Manual review:**
   - Sample 10 recent checks
   - Verify displayed evidence directly addresses specific claims
   - Compare against pre-fix behavior if baseline data available

---

## Files Modified

| File | Change |
|------|--------|
| `backend/app/pipeline/judge.py` | Added `_select_display_evidence()` function, updated 5 call sites |

## Files Created (Investigation)

| File | Purpose |
|------|---------|
| `PIPELINE_INVESTIGATION_docs/report_quality_pipeline_map.md` | Pipeline architecture documentation |
| `PIPELINE_INVESTIGATION_docs/root_causes.md` | Root cause analysis |
| `PIPELINE_INVESTIGATION_docs/fix_plan.md` | Proposed fixes and rollout strategy |
| `PIPELINE_INVESTIGATION_docs/report_quality_trace.md` | Example failure traces |
| `PIPELINE_INVESTIGATION_docs/pipeline_trace.py` | Diagnostic tracing script |

---

## Git History

```
bb43ae7 Fix evidence display selection to prioritize relevance
```

Commit includes:
- New `_select_display_evidence()` helper function (lines 63-98)
- 5 call site updates replacing `evidence[:3]` with `_select_display_evidence(evidence)`

---

## Questions for Review

1. **Threshold value:** Is 0.40 appropriate, or should it be raised to the originally proposed 0.45?

2. **Fallback behavior:** Currently falls back to showing 1 item if nothing passes threshold. Should this be configurable or should it show nothing?

3. **Entity matching priority:** Should Fix 4 (entity matching) be prioritized higher given its potential impact on timestamp/numeric claims?

4. **Monitoring:** What metrics should be tracked to measure success of this fix?
