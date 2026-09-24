# A− tier 2 Build C: one article counts once (S4); no false echo on the claim's own figure (H1)

**Date:** 2026-09-24.
**Status:** DRAFT for independent re-review.
**Rule:** founder, 2026-09-24: difficulty ≥3 is designed and reviewed before building.
**Inputs:** the tier-2 review §Build C (`audit/2026-09-24_a_minus_tier2_review.md`), which traced C2 to root cause. The copy key below was prototyped free on the 19 stored payloads (§4).

## 1. What is being fixed
- **S4 (10/19 records): the same article counted twice.** Four forms:
  - two hosts of one URL (bbc.co.uk ↔ bbc.com);
  - two URL forms (Wiley `/doi/` ↔ `/doi/epdf/`);
  - two slugs on one host (Galway `…reefs` ↔ `…reefs-1`; RocketNews ×5 under `/2026/07/` and `/2026/08/`);
  - one article under a new title prefix or host (the same paper on a journal and on a repository; PA copy in two papers; a RocketNews reprint of Carbon Brief).
- **H1 on #12 (a HARD fail): a false echo.** `nature.org` and `earthspace.nyc` were scoped as echoes of an unrelated paper because they share ONE number, "420", which is the claim's own figure. That scoping sent e1 supported → disputed via `close_split`.

## 2. Root causes (from the review's trace; verified in code there)
1. URL dedup is a raw-string `in` test at **six** sites:
   - `retrieve.py:2198/2223` (search merge), `:2292` (freshness fallback), `:1008/1160` and `:1489` (adapter pool);
   - `runner.py:1968` (coverage recovery), `:2532` (re-search).
   - #14's BBC twin arrived through recovery.
2. `EvidenceDeduplicator` (`retrieve.py:2664`, with ledger receipts) compares per-page search snippets, which differ between copies.
3. The echo gate:
   - only knows PRIMARY originals (`corroboration.py:242`);
   - compares LLM-distilled text (RocketNews vs Carbon Brief similarity 0.03–0.11);
   - skips same-domain pairs;
   - counts any shared number as a shared fact, the claim's own figure included (#12).

## 3. Design
**C1 — `canonical_url_key(url) -> str`** in `app/utils/url_identity.py`. Equality only; stored URLs are never rewritten, because goldens' Jaccard sets hold raw URLs.
- Lower-case host; strip `www.`; host aliases from an explicit short list: `bbc.co.uk→bbc.com`. `news.bgov.com→bloomberg.com` is NOT an alias: bgov is a separate property, and its twin is caught by the title rule instead.
- Path: strip the trailing `/`; `/doi/(epdf|pdf|full|abs)/` → `/doi/`.
- **Keep the query string**, minus tracking parameters (`utm_*`, `fbclid`, `gclid`, `ref`, `cmp`). The prototype found the risk: two different Eurostat pages differ ONLY by `?title=…`, and a query-dropping key merged them.
- Fragment dropped.
- Used at all six sites and in `_same_page`.

**C2a — copy key, pre-fetch** (titles and URLs exist before fetch). Two items are copies when any of these hold:
- (i) their canonical keys are equal;
- (ii) same host AND their last path segment is equal after stripping a `-N` (N ≤ 2 digits) or `.html` suffix, with the stem ≥ 20 characters (the RocketNews `/2026/07/` vs `/2026/08/` directories are ignored because only the last segment is compared);
- (iii) normalised titles are equal. Normalisation: drop a trailing ` - Site`/` | Site` suffix; strip punctuation; lower-case; ≥5 words. If either title is SERP-truncated ("…"), a prefix of ≥6 words must match instead. Shell titles never match: a list covering `reddit`, `tiktok…`, `x`, `threads`, `youtube`, `news tagged …`, `home`, `untitled`, and titles under 5 words.

A **collapse** keeps one survivor and writes a `filter_stage="copy_dedup"` URL-ledger receipt for each dropped copy, naming the survivor (invariant #5). The survivor is chosen deterministically:
1. the host the dropped title's site suffix names (" - Carbon Brief" beats a RocketNews reprint);
2. otherwise a non-aggregator host over a repository/aggregator;
3. then the earliest `published_date`;
4. then the better claim-lane rank.

Applied at the search merge and at recovery, BEFORE fetch, so copies no longer consume fetch slots or distil calls. RocketNews alone took 5 of 40 slots on #13.

**C2b — fact overlap ignores the claim's own figures.** In the echo detector's fact overlap:
- drop any numeric fact whose value appears in the claim text or the element description;
- require ≥2 shared facts after that.

This targets #12's false echo directly. It must be symmetric: it applies to both sides.

**Not attempted in Build C (named, not claimed):** unit-converted wire copies (the AFP pair on #17); an editor's X teaser (#1); reposts and re-reporting whose original is non-primary (#6, #8). Those need a change to the echo rule itself (a non-primary original), with its own design.

## 4. Prototype (free, 19 stored payloads)
The C1 + C2a rules found **25 pairs on 9 records.** By eye, every pair is a true copy:

| Record | Copies found |
|---|---|
| #14 | bbc.co.uk ↔ bbc.com |
| #6 | bloomberg ↔ bgov, by slug |
| #8 | Galway `-1` twin; Belfast Telegraph ↔ Irish News (same PA copy, identical title) |
| #19 | three papers, each on journal + repository/aggregator, by title |
| #7 | politicspa ×2, by title |
| #9 | Wiley doi ↔ epdf |
| #13 | Carbon Brief + RocketNews ×5, by title and slug |

**0 false merges after the query-string fix.** The first draft keyed without the query and would have merged two Eurostat pages; caught and fixed before this doc.

**Expected S4 clears:** #7, #9, #14, #19 fully; #13 mostly (sigmaearth + a Reddit repost remain); #6 and #8 partly. **About 4/10 full** (the review's estimate, confirmed). **#12 H1** clears via C2b, to be confirmed by replay in the build.

## 5. Risks
- **Weight moves one way:** collapses remove weight only, so a supported element can fall below the support floor. On #13 it removes challenge weight instead. The rule is symmetric; its effect depends on which side the copies were on. The replay must report state changes by direction.
- **Cassettes:** collapsing before fetch changes the fetched set, which re-keys the cassettes of any corpus claim containing copies. Expect drift. Run a control arm, then patch with `--record-missing` (pence; ask first).
- **Survivor rule:** keeping a reprint over its original would be a quality loss. It is tested explicitly (Carbon Brief must survive).
- **Title rule over-merging:** two different articles with identical generic titles, such as "Live updates" or "Weather forecast". The ≥5-word rule plus the shell list mitigate it; the build adds a test corpus of generic titles.

## 6. Verification plan
- Unit tests for `canonical_url_key`, the copy key (true pairs from §4 plus generic-title negatives, including Eurostat), survivor choice, and C2b. All mutation-checked.
- Offline replay on the 19 payloads: pairs collapsed, states changed (with direction), #12 e1 back to supported.
- Bench with a control arm; patch any re-keyed cassettes with founder approval.
- Render check on #13 and #19.
