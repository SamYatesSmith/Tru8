# A− tier 2 Build C: one article counts once (S4); no false echo on the claim's own figure (H1)

**Date:** 2026-09-24.
**Status:** REVISED 2026-09-25 after the independent review (`audit/2026-09-24_a_minus_build_c_review.md`). §9 supersedes §§2–6 wherever they disagree.
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


## 9. Revision after review (2026-09-25)
The review's eight required changes, taken in its priority order. Nothing here is built yet.

### 9.1 C2b withdrawn
C2b as designed removed three correct echo receipts on #15 (TTE). It also did not clear #12's H1: with both echoes restored, e1 is 6 v 3, and `6 > 2×3` is false, so it is still `close_split`. #12 H1 needs the H2 fix (the ACS "current 416 ppm" challenge), which is outside Build C. The claim "#12 H1 clears" is withdrawn from §1 and §4.

Any derivation-chain change will be a separate design. It will be measured first, on the 19 payloads plus every corpus observation carrying `echo_scope`. The review's candidate rule is a starting point: a fact-only link counts if it shares a fact that is not the claim's figure, or if text similarity is ≥ 0.25. Gained and lost receipts are reported per record.

### 9.2 Build C = C1 + C2a, SHADOW FIRST
**Phase 1 (this build) logs and drops nothing.** It emits:
- `[COPY DEDUP] would_drop=<url> survivor=<url> rule=<i|ii|iii> site=<main|recovery|postfilter|claim_recovery|research>`; and
- `[URL KEY] would_match=<url> existing=<url>` wherever C1 would equal-match two raw-different URLs.

**Free shadow measurement: bench cassettes.** They hold the full SERP responses, so a replay reconstructs the real pre-fetch candidate pool (40–130 per claim). That is the population the stored-payload prototype never saw. Every would-drop line on the 10 corpus claims is read by eye before phase 2. The 19-record paid re-measure, when the founder approves it, adds a second population at no extra cost.

**Phase 2 (after the shadow read):** switch to enforcing (`ENABLE_COPY_DEDUP`). Bump `RETRIEVAL_CACHE_VERSION` in the same commit, and re-record the corpus with a control arm (paid, so ask first).

### 9.3 C1: the canonical URL key
- Tracking parameters dropped: `utm_*`, `fbclid`, `gclid`, `ref`, `cmp`, `srsltid`, `syn-*`, `mc_cid`, `mc_eid`, `ocid`, `smid`, `_ga`. Every other parameter is kept (Eurostat `?title=`, YouTube `?v=`, wwf.eu).
- The DOI rule is narrow: `/doi/(epdf|pdf|full|abs)/10.` → `/doi/10.`. The broader academic identity (DOI, PMID, PMC) is already handled post-fetch by the same-study gate (`study_identity`), so C1 does not duplicate it.
- `_same_page` stays query-insensitive. C1 is added as a second match (either key equal counts) and never replaces it, so `?amp=1` variants of the submitted page are still skipped (S7).
- Sites, corrected from the review. All eight use the key, for equality only; stored URLs are never rewritten:
  - search merge and freshness fallback (`_execute_planned_queries`);
  - claim recovery (`_recover_evidence_for_claim` / `_ensure_minimum_evidence`);
  - coverage recovery (`retrieve_for_elements`, whose `existing_urls` becomes existing copy keys);
  - post-filter recovery (`runner.py` ~1998);
  - the cross-claim tracker (`runner.py` ~1751, invariant #1), keeping the `frozen_evidence_replay` bypass;
  - re-search (`re_search.py:93`).

### 9.4 C2a: the copy key, with the review's false-merge guards
Two candidates are copies if any rule holds:
- **(i)** equal C1 keys.
- **(ii)** same host, and equal last path segment after stripping `-N`/`.html`, with a stem ≥ 20 chars. Series guard: never when the token before `-N` is in {part, day, week, episode, chapter, vol, no, round, stage, phase, series}. The normalised titles must also be equal, or both be shells.
- **(iii)** equal normalised titles. Normalisation:
  - strip HTML tags first (the Eurostat `<span class="mw-page-title-main">` case);
  - drop digit-group commas and a trailing `(N)`;
  - drop a ` - Site` / ` | Site` suffix;
  - strip punctuation and lower-case.

  The result must be ≥5 words. A SERP-truncated title needs a prefix of ≥8 tokens and ≥45 chars.

  **Shells never match:**
  - the handle regex `\(@[\w.]+\) on (x|threads|instagram|tiktok|bluesky)$`;
  - `reddit`, `tiktok - make your day`, `youtube`, `news tagged …`, `home`, `untitled`, `just a moment`, `access denied`, `log in`;
  - anything under 5 words.
- **Date guard** on every rule: never merge when both SERP dates parse and are more than 45 days apart.
- **#6 bloomberg ↔ bgov:** caught by title rule (iii) once commas and `(1)` are normalised. No cross-host slug rule.

### 9.5 Where it runs, and who survives
- **Main path:** after `_allocate_fetch_budget` has ordered the list, and before `fetch_set = fetch_candidates[:max_sources]` (`retrieve.py` ~2345). The survivor takes the earliest position of any member, and every member's `_element_ids` are unioned into it.
- **Recovery sites:** the item already in the pool always survives. The recovery copy's `target_element` is carried onto it.
- **Survivor order:**
  1. the pooled item (recovery only);
  2. a host named by *another* member's title suffix;
  3. not on `REPRINT_HOSTS` (rocketnews, msn, yahoo, newsbreak, flipboard, ground.news, publicnow, biggo, sigmaearth);
  4. for academic groups, an open copy (PMC, repositories, author institution) over a paywalled version of record, with the version of record named in the receipt;
  5. the earliest parseable SERP date (relative dates parsed against run time; None last);
  6. the earliest round-robin position;
  7. the smallest canonical key.

  Suffix matching is defined exactly: lower-case, alphanumerics only, equal to the registrable label or a prefix of it. Tested negatives: Cato Institute, Office for National Statistics, Scientific Reports, "PMC - NIH".
- **Fetch fallback:** the collapsed copies stay on the survivor as ordered fallbacks. If the survivor's fetch returns None or snippet-only, the next copy is fetched in the same slot. This prevents the #19 loss, where the journal copy is paywalled and the repository copy has full text.

### 9.6 Receipts (invariant #5)
- Each survivor carries `_copies = [{url, title, source, published_date, rule}]`.
- The raw-tracking snapshot writes one `RawEvidence` row per copy: `is_included=False`, `filter_stage="copy_dedup"`, `filter_reason="Copy of <survivor url> (rule i|ii|iii)"`. This happens even when the survivor's fetch fails.
- `copy_dedup` is added to the `filter_stage` description (`models/check.py:520`) and to any frontend stage label.
- `_copies` is never written onto manifest-canonicalised `Evidence` fields.

### 9.7 Efficiency, stated honestly
Freed fetch slots are refilled from deeper results, so fetch and distil counts do not fall. The gain is pool diversity. The refill is lower-ranked, and S5 (off-topic rows) already fails 13/19, so S5 is watched in the re-measure.

### 9.8 Before phase 2
- Check every golden's `must_have` URLs against the copy key. A must-have that loses a survivor contest would break a tolerance-0 pin.
- Replay reports states changed per record by direction. The review's stored-ref simulation found no direction changes; #14 e3 moves unresolved → contextual, which is correct.
