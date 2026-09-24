# A− Build C — independent design review

**Date:** 2026-09-24. **Reviews:** `audit/2026-09-24_a_minus_build_c_design.md`.
**Method:** read-only. Code read at `173a26c`. The 19 public payloads were fetched with curl (`/checks/public/<id>?detailed=true`). C1, C2a and C2b were re-implemented in a scratch script and run on those payloads, and on `corroboration.py`'s own functions for C2b. Nothing was run on the pipeline and nothing was spent.

## Verdict

| Part | Verdict |
|---|---|
| **C1** canonical URL key | **APPROVE WITH CHANGES** |
| **C2a** pre-fetch copy key + collapse | **APPROVE WITH CHANGES.** The survivor rule and the receipt path must be re-specified before building. |
| **C2b** fact overlap ignores the claim's figures | **REWORK.** It removes correct echoes on #15, and it does not clear #12's H1. |
| **Overall** | Build C1 + C2a after the changes below. Redesign C2b. Stop claiming "#12 H1 clears". |

The alignment is right: the fault is real and the stage is the right one. The design does not yet show it will improve quality without regressions, and its efficiency claim is overstated (§6).

---

## 1. Code references

| Design says | Actually |
|---|---|
| `retrieve.py:2198/2223` search merge | ✓ `_execute_planned_queries`. The merge also **unions `_element_ids`** from duplicate URLs, so a collapse must do the same. |
| `:2292` freshness fallback | ✓ |
| `:1008/1160` "adapter pool" | ✗ Wrong label. This is `_ensure_minimum_evidence` / `_recover_evidence_for_claim`, the claim-level recovery. It adds search snippets and does not fetch. |
| `:1489` "adapter pool" | ✗ Wrong label. This is `retrieve_for_elements`, i.e. **coverage recovery**. It is the site #14's `ev-rec-e3_4` twin came through, and it fetches afterwards in `_enrich_recovery_evidence`. |
| `runner.py:1968` "coverage recovery" | ✗ This is **post-filter recovery** (`ev-rpf-*`, check at `:1998`). It stores snippets only and does not fetch. |
| `runner.py:2532` "re-search" | ✗ This builds the `existing_urls` set that **coverage recovery** passes to `retrieve.py:1489`. Re-search is `re_search.py:93`, which the design does not list. |
| (missing) | **`runner.py:1751` Stage 3.6 cross-claim URL dedup** (`MAX_CLAIMS_PER_URL`). This is the actual invariant-#1 tracker, and it keys on the raw URL. |
| `EvidenceDeduplicator` `retrieve.py:2664`, receipts `:2670-2676` | ✓ These are the only **persisted** dedup receipts (`RawEvidence.filter_stage`). They are written inside `_apply_evidence_filters`, which runs **after** fetch. |
| URL-ledger receipt "API" | There is no API. Pre-fetch drops today are **log lines only**: `[URL LEDGER] dropped stage=fetch_deadline` at `:2468`, and budget drops are only counted (`dropped_by_budget=`), with no per-URL record at all. See §3.2. |
| `_detect_derivation_chains` `corroboration.py:242` | ✓ Primary-only. It needs **≥2 derived items** (`len(derived) >= 2`, `:275`). |
| Fact overlap | `_extract_key_facts` (`:91`) and `_check_fact_overlap` (`:122`). It is a **Jaccard ≥ 0.3**, not a count, and it is OR'd with `_text_similarity ≥ 0.35` (`:180-183`, a SequenceMatcher over the first 500 chars, **order-dependent**). `find_corroborating_sources` is shared by `apply_corroboration_boost` (retrieve-time corroboration groups) and `annotate_derivation_chains` (`runner.py:2292`, post-classify). |
| `_echo_fires` `claim_map_analyzer.py:3062` | ✓ It fires only when the original is counted on the same side of the same element. |

So there are **eight** URL-identity sites, not six: the six listed, plus cross-claim dedup (`runner.py:1751`) and re-search (`re_search.py:93`), plus `_same_page`.

## 2. C1: canonical URL key. APPROVE WITH CHANGES

1. **Tracking-parameter list is incomplete, as measured on the payloads.**
   - `srsltid` (Google's SERP click id) appears on Statista in #3 and #12.
   - `syn-25a6b1a6=1` (FT syndication) appears in #5, #10 and #14.

   As designed, two SERP visits to one Statista page do **not** match. Add `srsltid`, `syn-*`, `mc_cid`, `mc_eid`, `ocid`, `smid` and `_ga`.

   Keeping the rest of the query string is right, and the payloads confirm it: `youtube.com/watch?v=…` and `wwf.eu/?21225366/…` carry their identity in the query.
2. **Do not make `_same_page` stricter.** Today it drops the whole query string on purpose (docstring: "query string … presentation, not identity"), because it decides whether a result IS the submitted page.

   Swapping in C1, which keeps non-tracking queries, means `?amp=1` or `?page=1` variants of the submitted page stop being "skip". The submitted page could then enter as evidence for its own claim, which is the S7 failure.

   Use C1 as an **additional** match in `_same_page` (either key matching counts), never as a replacement.
3. **Apply the key at cross-claim dedup (`runner.py:1751`) and at `re_search.py:93` too**, or give a reason for leaving them out.
4. The review asked for DOI/PMID/PMC identity (`study_identity`) instead of a `/doi/epdf/` special case. The design dropped this silently.

   That is acceptable, because the same-study gate already handles academic hosts post-fetch. But say why in the design, and keep the epdf rule narrow: `/doi/(epdf|pdf|full|abs)/` followed by `10.`.

## 3. C2a: copy key and collapse. APPROVE WITH CHANGES

### 3.1 Where it must run
- **Main path:** in `_execute_planned_queries`, after the merge and freshness fallback, and **after** `_allocate_fetch_budget` orders the list but **before** the `[:max_sources]` cut.
  - Walk the ordered list. Each copy group's survivor takes the **earliest position of any member**.
  - Union every member's `_element_ids` into the survivor.
  - If you collapse before allocation instead, a survivor found only by an element lane moves to that lane's bucket and can fall below the 40 cut where its claim-lane copy would have been fetched.
- **Coverage recovery:** in `retrieve_for_elements`, after collection and **before** `_enrich_recovery_evidence`. Its `existing_urls: set[str]` parameter must become existing copy keys (URL keys plus normalised titles) built from the pool.
- **Also at post-filter recovery (`runner.py:1998`) and `_recover_evidence_for_claim` (`:1160`).** These do not fetch, but they can still add a copy of a pooled item.
- **At recovery, the item already in the pool always survives.** It has been fetched, distilled, classified and mapped, so the survivor rule does not apply. The recovery copy's `target_element` must be carried onto the survivor, so that recovery mapping re-offers that item for the element.

  On #14 the pooled bbc.co.uk item is `context` on e3 while its bbc.com twin is `supports` (the mapper disagreed with itself). Collapsing moves e3 from **unresolved (2v0, support_floor) to contextual (0v0)**. That is correct, but the replay report must show it.

### 3.2 Receipts (invariant #5)
A pre-fetch collapse drops the item before `_apply_evidence_filters` builds `raw_evidence_tracking`. **No `RawEvidence` row is written**, and a log line alone is not a receipt a user or export can see (`checks.py:2571` reads `filter_stage` from `RawEvidence`).

Required:
- Attach `_copies = [{url, title, source, published_date, reason}]` to the survivor.
- In the raw-tracking snapshot, emit one `is_included=False, filter_stage="copy_dedup", filter_reason="Copy of <survivor url> (<rule i/ii/iii>)"` row per copy.
- Add `copy_dedup` to the `filter_stage` description in `models/check.py:520`, and to any frontend stage label map.
- If the survivor's fetch returns None, its copies' receipts must still be written.

### 3.3 Survivor rule: not deterministic enough, and wrong on its motivating case
- **Rule 1 does not pick Carbon Brief.** Every RocketNews title ends in "- RocketNews", and Carbon Brief's ends in "- Carbon Brief". Each title names its own host, so rule 1 ties.
  - Rule 3 ties too: Carbon Brief and `rocketnews.com/2026/07/…` are both dated 2026-07-24.
  - Carbon Brief then survives only through rule 2, and only if `rocketnews.com` is on an aggregator list. The design never defines that list, and rule 4's "claim-lane rank" is not a stored field.

  Rule 1 discriminates only when a reprint carries the *original's* suffix, as in "… - Carbon Brief" hosted on msn.com. Keep it for that case.
- **"Suffix names the host" is fragile.** It works when the compressed suffix equals the domain label (carbonbrief, rocketnews, bbc). It fails on "Cato Institute" → cato.org, "Office for National Statistics" → ons.gov.uk, "Scientific Reports" → nature.com, and "PMC - NIH". Specify the matching exactly (lower-case, alphanumerics only, equal to the registrable label or a prefix of it) and test those four negatives.
- **Rule 2 ("non-aggregator over repository") loses content on #19.** The journal copies are snippet-only (`contentBasis=snippet`: sagepub, OUP, PMC). The repository or author-site copies were fetched in full (`distilled`: lu.se, healthdata.org).

  Preferring the journal pre-fetch keeps the paywalled page and drops the text. Either:
  - keep the collapsed copies as **ordered fetch fallbacks** for the survivor, so that when its fetch returns None or snippet-only, the next copy is tried in the same slot; or
  - for academic groups, prefer the open copy (PMC, repositories, author institution) and record the version of record in the receipt.
- A concrete, deterministic order that works on every payload group:
  1. The existing pool item (recovery only).
  2. A host named by *another* member's title suffix.
  3. Not on an explicit `REPRINT_HOSTS` list (rocketnews, msn, yahoo, newsbreak, flipboard, ground.news, publicnow, biggo, sigmaearth).
  4. The earliest parseable SERP date, with None last. SERP dates can be relative ("3 days ago"), so parse them against the run time.
  5. The earliest round-robin position.
  6. The lexicographically smallest canonical key.

### 3.4 False merges the design missed
The prototype reproduced **23 pairs on 8 records**, all true copies, with zero false merges on the stored items. But:

- **The prototype saw the wrong population.** Public payloads hold only the **retained** evidence: 275 items across 19 records, e.g. #12 holds 8 of 27 reviewed. C2a runs on the **pre-fetch candidate pool**, about 40–130 per claim, which has far more tag pages, social posts and generic titles. "0 false merges" is measured on roughly a quarter of the real population, and on its cleanest part.
- **Social handle titles pass the ≥5-word floor.** Observed titles:
  - "The Journal (@thejournal_ie) on Threads" (#8)
  - "Pippa Crerar (@PippaCrerar) on X" (#1)
  - "Brilliant Maps (@brilliantmaps) on Threads" (#4)
  - "Unbelievable Facts (@unbfacts) on Threads" (#12)

  Each normalises to exactly 5 words, and two different posts from one account share the title. **Add a regex shell:** `\(@[\w.]+\) on (x|threads|instagram|tiktok|bluesky)$`. Also cover `TikTok - Make Your Day`, `Just a moment`, `Access denied` and `Log in`.
- **Raw HTML in titles.** #3's Eurostat title is `<span class="mw-page-title-main">Government expenditure by function – COFOG</span>`. After punctuation stripping, every Statistics Explained page begins with the same 6 tokens, so the truncated-prefix rule can merge two different pages. **Strip tags before normalising.** This is the same Eurostat risk the design fixed for the query string, arriving by the title route.
- **The `-N` slug strip merges series.** `…-part-1` / `…-part-2`, `…-day-1` / `…-day-2` and `…-episode-12` all reduce to one stem. Require one of:
  - rule (ii) also needs equal normalised titles, or both titles are shells (true of Galway and RocketNews); or
  - the token before `-N` is not in {part, day, week, episode, chapter, vol, no, round, stage, phase, series}.
- **Recurring pages that share a slug or title across years** on one host (e.g. `/news/2025/budget-statement-to-parliament` and `/2026/…`). Add a date guard: never merge when both SERP dates are known and more than 45 days apart. RocketNews' spread is 21 days.
- **A 6-word truncated prefix is weak for academic titles.** "Excess mortality during the COVID-19 …" gives 6 tokens after "COVID-19" splits in two. Raise the floor to ≥8 tokens and ≥45 characters, or require a second signal (the same DOI/host family, or dates within 7 days).
- **#6 bloomberg ↔ bgov contradicts the design's own rule.** Rule (ii) requires the same host. The titles differ: "21000 Trades" vs "21,000 Trades … (1)". My prototype does not reproduce that pair, so the prototype used a rule the doc does not state. Choose one:
  - allow a cross-host slug match with ≥6 hyphen tokens (this bgov slug has 8); a lower floor would merge topical tag slugs such as `cost-of-living-crisis`; or
  - in title normalisation, drop digit-group commas before stripping punctuation and drop a trailing `\(\d+\)`.

  Then fix the §4 table.

### 3.5 The per-claim cache and the bench
- **`RETRIEVAL_CACHE_VERSION` must be bumped in the same commit** (`config.py:461` says so for any change to what retrieval gathers). The design does not mention it. Without the bump, repeated claims replay pools that still contain copies for 24 hours, and the 19-record re-measure could come back void, the way Build A's TTE control arm did.
- The bench's golden `url_ledger_flat` Jaccard sets come from `[URL LEDGER] … kept` lines. Collapsing removes kept URLs, so Jaccard moves as well as cassettes.
- **Before building, check every golden's `must_have` URLs against the copy key.** A must-have that loses a survivor contest fails a tolerance-0 pin.
- `frozen_evidence_replay` skips cross-claim dedup (`runner.py:1757`). If C1 goes there, keep the bypass.

## 4. C2b: fact overlap. REWORK

I re-ran `corroboration.py`'s own functions on the stored snippets of every `echo_scope` receipt in the 19 payloads:

| Record | Scoped derivative ← original | fact J | text sim | shared facts | after the claim's figures are removed |
|---|---|---|---|---|---|
| #12 e1 | earthspace.nyc ← doi (Gondwana) | 0.50 | 0.15 | {420} | ∅, link lost |
| #12 e1 | nature.org ← doi | 0.25 | **0.34 / 0.39** (order-dependent) | {420} | ∅, but fact J was already below 0.3; **the link is text similarity** |
| **#15 e2** | **resultsense.com ×2 ← NHS ICB** | 0.50 | **0.30 / 0.32** | {29} | **∅, link lost** |
| #15 e2 | intelligenthealth.tech ← NHS ICB | 1.00 | 0.68 | {29} | kept by text |
| #18 e2 | livescience, ebsco ← esawebb | 0.25/0.33 | 0.40/0.55 | {6.5} | kept by text |
| #18 e3 | medium ← science.nasa.gov | 0.38 | 0.17 | {2021, 25, dec 25 2021} | {25, dec 25 2021}, kept |
| #8 e1 | thejournal, independent ← Galway | 0 | 0.70/0.51 | ∅ | kept by text |

The table shows three faults:

1. **C2b regresses #15 (TTE, an outreach record).**
   - Both resultsense links rest only on "29", the claim's own figure.
   - Removing them leaves the NHS chain with one derivative, below `len(derived) >= 2`, so the **whole chain vanishes**. intelligenthealth, a true re-report at 0.68 similarity, is un-scoped with them.
   - Three correct echo receipts are lost; the #15 grader credited them ("three echoes set to context"). S4 gets worse on #15.
   - The principle is wrong too: **the claim's own figure is precisely what an echo recites.** Excluding it attacks the signal the gate exists for (the NHS "1 original + 6 wire copies" case).
2. **#12 clears only by accident.** C2b removes earthspace. nature.org's link is text similarity (0.34–0.39 against a 0.35 threshold), so it is untouched. The chain then dies only because one derivative is left. One more borderline page would bring the false echo back.
3. **#12's H1 does not clear, even then.** With both echoes restored as supports, e1 is doi (3) + threads (1) + nature (1) + earthspace (1) = **6 against 3** (the ACS "current 416 ppm" challenge). The rule is `weighted_supports > 2 * weighted_challenges` (`claim_map_analyzer.py:1134`), and 6 > 6 is false, so e1 is **still `close_split` → disputed**.

   The grader's "4 vs 3 produced close_split" is right, but so does 6 vs 3. H1 on #12 also needs the H2 fix (the ACS review's stale "current" figure filed as a challenge), which is outside Build C. **Remove "#12 H1 clears via C2b" from §1 and §4.**

**Required redesign:**
- Scope any change to **derivation chains only**. Pass the claim's figures into `annotate_derivation_chains`, not into the shared `find_corroborating_sources`, or the retrieve-time corroboration groups shown on the MAP view change as well.
- Chains are built per claim pool, before any per-element view. "The element description" therefore means the union of all elements' descriptions, or the check moves into `_echo_fires`. State which.
- **Candidate rule, to measure rather than adopt:** a fact-overlap-only link (text similarity < 0.35) counts toward a chain only if it shares at least one fact that is **not** the claim's figure, **or** its text similarity is ≥ 0.25.
  - On the payloads this keeps #15 resultsense (0.30–0.32), #18 and #8.
  - It drops #12 earthspace (0.15).
  - Measure it on the 19 payloads and on every corpus observation with `echo_scope` (10 corpus claims carry it) before choosing 0.25.
- Do the same honest accounting for the **text-similarity leg**, which is how nature.org linked. A SequenceMatcher ratio of 0.35 over 500 characters of LLM-distilled bullets is weak evidence of derivation. Any change there must be measured the same way.
- Replay must report echo receipts **gained and lost** per record, not only #12.

## 5. Symmetry, the manifest, and the weight direction
- The collapse and the chain change are side-agnostic. ✓
- Measured on stored refs with the design's own pairs:
  - #13 e1 goes from 2v10 to 2v6 and e2 from 0v11 to 0v5. Both stay disputed (`all_challenges`); challenge weight falls.
  - #8 e1 goes from 20v0 to 15v0 and #7 e3 from 5v0 to 3v0 (still ≥ the floor of 3). Both stay supported.
  - #14 e3 goes from unresolved to contextual.
  - **No state changes direction.**
- The review's point stands: weight only ever falls, and a single challenge still gives `all_challenges`. Report the net per direction.
- The manifest signs `content_basis` and evidence snapshots for new checks only. A different pool is a new check, not a re-signing. ✓ No change is needed, but do **not** write `_copies` back onto the survivor's stored `Evidence` fields that the manifest canonicalises. Keep them only in `RawEvidence`.

## 6. Efficiency: overstated
"Copies no longer consume fetch slots or distil calls" is true per copy. But `fetch_set = fetch_candidates[:max_sources]` refills freed slots with the next candidates, so a normal claim still fetches 40 and distils the same number.

The gain is **pool diversity** (five more distinct pages on #13), not cost or latency. The refill comes from deeper, lower-ranked results, and S5 (off-topic rows) already fails 13/19. Say this plainly, and watch S5 in the re-measure. Compute cost is negligible: dict keys for rules (i) and (ii) plus a title-key dict, O(n).

## 7. A simpler, safer route
Ship C1 + C2a in **shadow mode** first:
- compute the groups and survivors, and log `[COPY DEDUP] would_drop=<url> survivor=<url> rule=<i|ii|iii>`, without dropping anything;
- run the founder-approved 19-record re-measure that is already planned, at no extra cost;
- read every would-drop line over the full candidate pool, the population the prototype never saw;
- then flip to enforcing, with the cache bump and the corpus re-record together.

This is the only way to measure false merges on pre-fetch titles without spending anything extra. The bench cannot do it, given 62% URL churn.

## 8. Required changes, in priority order
1. **C2b:** withdraw as designed. Redesign per §4, and drop the "#12 H1 clears" claim.
2. **C2a survivor:** use the explicit order in §3.3, including the pooled item winning at recovery, `REPRINT_HOSTS`, and fetch fallbacks or an open-copy preference for academic groups. Test that Carbon Brief survives *and* that lu.se/PMC full text is not lost.
3. **C2a receipts:** persist `RawEvidence` rows with `filter_stage="copy_dedup"` naming the survivor (§3.2), and union `_element_ids` / `target_element` into the survivor.
4. **C2a false-merge guards:** the handle-title shell regex, HTML tag stripping, the `-N` series guard, the 45-day date guard, a stronger truncated-prefix floor, and a decision on #6 bgov (§3.4).
5. **Position:** collapse after `_allocate_fetch_budget`, with the survivor at the earliest member position.
6. **C1:** add `srsltid` and `syn-*` to the tracking list, keep `_same_page` query-insensitive (C1 only as an additional match), and cover `runner.py:1751` and `re_search.py:93`.
7. **Cache and bench:** bump `RETRIEVAL_CACHE_VERSION` in the build commit, and pre-check goldens' `must_have` URLs against the copy key.
8. **Shadow mode first** (§7). Correct the site labels in §2 of the design.
