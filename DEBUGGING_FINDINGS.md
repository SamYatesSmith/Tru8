# Debugging Findings - International Article Failure
**Date:** 2025-11-19
**Article:** Lula/Merz/Brazil (Politico EU)
**Check ID:** dded197c-226f-4a02-b26a-01c8e622efe5
**Score:** 50/100 (unchanged after threshold adjustments)

## What's Working
✅ **Search**: Brave returns 12-13 results per query
✅ **Retrieval**: 9-10 sources retrieved successfully
✅ **NLI Model**: Loads and processes evidence
✅ **Settings**: RELEVANCE_THRESHOLD correctly set to 0.65

## What's NOT Working
❌ **Evidence Disappearing**: 9 sources retrieved → Only 0-1 saved per claim
❌ **No Relevance Filter Logs**: Expected "OFF-TOPIC" or "relevance < 0.65" logs - NONE found
❌ **Evidence Quality**: The 1 source that WAS saved has relevance=0.16 (16%), not 65%+

## Key Finding from Logs

**Evidence that WAS saved (DW source):**
```
'relevance_score': 0.1634920634920635   ← 16% (should be >65%)
'nli_entailment': 0.00022               ← Near zero
'nli_contradiction': 0.0219
'nli_stance': 'neutral'                 ← My NLI change worked - it's accepting neutral
```

## The Real Problem

**The relevance filter is NOT RUNNING at all!**

Evidence:
1. No "Relevance filter" logs in output
2. No "OFF-TOPIC (relevance X < 0.65)" messages
3. Evidence with 16% relevance is being saved (should be filtered at 65%)
4. Settings are correct (ENABLE_EVIDENCE_RELEVANCE_FILTER=True, RELEVANCE_THRESHOLD=0.65)

## Where is Evidence Being Filtered?

**Pipeline Flow:**
```
Search (12 results)
  → Retrieval (9 sources)
  → ??? FILTERING HERE ???
  → NLI Verification (1 source processed)
  → Saving (0-1 sources per claim)
```

**Missing step:** Something is filtering 8-9 sources BEFORE they reach NLI

## Possible Causes

1. **Domain Capping**: Too many sources from same domain filtered out
2. **Deduplication**: Duplicate content removed
3. **Credibility Filtering**: Low-credibility sources removed early
4. **Relevance Filter Broken**: Code path not executing despite settings=True
5. **Cache**: Worker using old code from before my changes

## Next Steps to Debug

1. Check if domain capping is removing international sources
2. Find where the 8 missing sources are being filtered
3. Add more diagnostic logging to trace evidence through pipeline
4. Check if there's a different code path for international content

## My Changes (Applied but Not Helping)

1. ✅ Lowered RELEVANCE_THRESHOLD from 0.75 to 0.65
2. ✅ Adjusted NLI logic to accept low-contradiction neutral evidence
3. ❌ Relevance filter not executing, so threshold change has no effect
4. ✅ NLI logic change IS working (accepting neutral evidence)

## Conclusion

The threshold changes I made are CORRECT but they're addressing the WRONG bottleneck. The evidence is being filtered out BEFORE it reaches the relevance filter or NLI model.

**Need to find:** Where are the 8-9 missing sources being removed?
