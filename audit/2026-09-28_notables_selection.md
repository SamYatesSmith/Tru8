# Notables selection (A− S3), 2026-09-28

**Problem.** On the 19-record re-measure, the Notables headline ("Most relevant supporting source") was wrong on 13 records. It was the supporter with the highest raw retrieval `relevanceScore`. The picks included:
- a Medium essay;
- a journalist's muckrack profile;
- a carbon-by-birth-year calculator;
- the claimant's own newsletter;
- a rewrite aggregator;
- a technical PDF that bears only on the launch date.

**Prior attempt (2026-09-24), dropped at 6/12.** It scored elements-count, tier and social-exclusion variants against the graders. The Primary tier was polluted then (trackers, social posts, news in PRIMARY). H4 rounds 1 and 2 have since cleaned it.

## Measurement (free: stored payloads + blind grades)
The labels are the graders' named best supporting source on the 15 records that have a support. #3, #16 and #17 have none. #19 is excluded because its best supporter was mis-filed as a challenge, which no rule over supports can fix. Tiers were re-derived with the round-2 caps (`_apply_quality_floor`).

| Rule | Correct |
|---|---|
| V0: relevance (the rule until now) | **3/15** |
| V1: tier, then relevance | 6/15 |
| V2: V1 without reprint/social/opinion | 6/15 |
| V3: most elements, tier, relevance | 9/15 |
| **V4: not secondhand, most elements, tier, relevance** | **9/15** |
| V5: not secondhand, tier, most elements | 8/15 |
| V6: V4 with earliest date ahead of relevance | 7/15 |

**Shipped: V4, with an exact tie broken by the earlier publication.**
- On #14, memeburn and FT tie on reach, tier and relevance (0.0), so list order decided. FT is 12 Sep and memeburn 16 Sep.
- As a main tie-break the date scored only 7/15, so it breaks exact ties only.

**The same rule applies to challenges** (invariant #7). On #18 it prefers NASA's own page over the orbitalradar tracker.

**Remaining misses:**
- #2: the grader named no best source; the scoring allowed any primary support.
- #4: rosalux.de chosen; JoD and insidestory may be filed as context.
- #5: Voltstack (tracker, now reporting) still wins on reach.
- #11: BMJ news story; expected to clear live when the override guard keeps it at reporting.
- #15: htn.co.uk chosen, not the BBC.
- #18: ntrs.nasa.gov chosen, where the grader wanted NASA's Webb pages.

**Caveat:** the rule was chosen on these 15 records, and a fresh re-measure is the real test.

**Label:** "Most relevant … source" became **"Main … source"**. The rule is no longer relevance, and "strongest" would claim an authority score the product does not make.

**Verified:**
- `web/lib/notables.ts` + 9 vitest cases; the frontend suite passes; `tsc` clean.
- Rendered locally against the prod API: #7 now picks Cook's results page, #8 the University of Galway release, #14 the FT (was bylinetimes / memeburn).
- It applies on read to every record, old ones included.
