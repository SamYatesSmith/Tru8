# Cited-source follow-up lane: design (rev 1, 2026-10-05)

**Status:** design only. Nothing is built. Each paid step needs founder approval.
**Difficulty:** 3: a new retrieval stage, one model call, invariants #5 and #7. Plan, independent review, founder approval, then build.
**Fault:** A− H3 "authoritative source missing" is the largest retrieval bucket: 6 of 19 records on 30 Sep (#1, #2, #4, #6, #15, #17). See `audit/2026-09-24_a_minus_measurement.md` and `audit/2026-09-28_retrieval_h3_review.md`.

## 1. Evidence for the idea (2026-10-05)
**The pools name the missing original.** Production pools of 30 Sep, free:

| # | Cited by pooled copies |
|---|---|
| #6 | 10 sources: "a new Bloomberg analysis finds" |
| #15 | 13: "NHS England announced" |
| #17 | 4: "data collected by the European Forest Fire Information System (EFFIS)" |
| #1 | BBC and the Guardian: Delo "wrote in the Daily Telegraph"; the donation was "revealed in the Telegraph" |
| #4 | Only "according to preliminary official results" |
| #2 | Nothing |

**Searching by the cited name finds the original.** Probe of 10 Serper calls, founder-approved; `audit/cited_source/probe_results.json`:

| # | Original found | Rank |
|---|---|---|
| #6 | bloomberg.com/graphics/2026-trump-stock-trades-congress | 1, both queries |
| #15 | england.nhs.uk/2026/07/nhs-accelerates-artificial-intelligence-rollout… | 1 |
| #17 | JRC "current situation" page; EFFIS estimates | 1 and 2 |
| #1 | The Telegraph's own reports of both donations | 1–2; the Harborne piece at rank 9 |
| #4 | wahlergebnisse.sachsen-anhalt.de | 1, **only with the German query**; the English query did not return it |

That is 5 of 5, against 0 of 3 for Phase D's rebuttal lane. **Why the difference:** a copy names its source, and a rebuttal does not. This lane follows a name the pool already holds. It does not guess at framing, so it is not a query-phrasing fix (the Phase D lesson holds).

**Caveat:** the probe queries were written by hand from names read in the pool. The build must extract the name itself, and that is §3.

**Mechanical extraction is not enough** (`audit/cited_source/extract_probe.py`, free, 41 production pools).
- Patterns ("according to X", "X said", "a new X analysis", "data from X") found Bloomberg, NHS England and the Telegraph.
- They missed EFFIS.
- They also returned people who are merely quoted (Jim Mackey, Craig Hoy, Siegmund).
- So the extraction is a model call, and a mechanical check stops the model from inventing names (§3).

## 2. Where it runs
After LLM relevance scoring and post-filter recovery (`runner.py` ~1975–2125), **before** text provenance capture, classification and distillation (~2128):

```
retrieve → url dedup → relevance scoring → post-filter recovery
  → NEW: cited-source follow-up (per claim)
  → provenance capture + page opening → classify ∥ distil → … → mapping
```

**Why there:**
- Items it adds go through the same provenance, originator review, classification, distillation, gates and receipts as any other item. No second-class path.
- It needs the pool's text, so it cannot run inside the first retrieval.
- It runs after scoring, so the names come from pages that survived relevance.

**Not on:** frozen evidence replay (the pool is fixed), the quick tier (30 s wall clock), or re-search (Strengthen supplies its own lane). Each skip leaves a receipt.

## 3. Naming the cited originals (one model call per check)
**Input.** For each claim: the claim text, plus up to 20 non-primary pool items. Each item gives its host, title and up to 600 chars of verbatim text (`text_provenance.original_snippet` and passages; never distilled text, the same lesson as echo H1), chosen as the windows around attribution verbs. Source text is marked as untrusted data.

**Question.** "Which organisation, publication or document do these sources present as the ORIGIN of the claim's specific facts or figures (the body that published the data, analysis, announcement, filing or study)? Not people quoted for opinion; not the outlets themselves unless they broke the story."

**Output per name:**
- `name`, plus an optional `document` (e.g. "Bloomberg analysis of OGE filings");
- `cue`: verbatim words from one item showing the attribution;
- `kind` ∈ {`data`, `analysis`, `announcement`, `filing`, `study`, `news_first_report`};
- `item_count`. At most 3 names per claim.

**Mechanical guards, failing closed:**
- The cue must be found verbatim (case-exact, whitespace collapsed) in a pooled item's verbatim text.
- `name` must appear verbatim in that cue.
- A name that is a pooled PRIMARY item's host or publisher is dropped as **already present**, with a receipt.

**Model:** `gemini-3.7-flash` (same family as the reviews). One call per check covers all its claims. 25 s deadline. Any failure means no lane and a receipt.

## 4. Queries and fetch
- **Queries:** per accepted name, ONE query: `"{name}" + {document if given} + the claim's key terms` (the normalised claim with numbers kept, trimmed to 12 content words). The probe's best queries had exactly this shape. Freshness is `none`, because the original often predates the coverage.
- **Caps:** ≤ 3 queries per claim and ≤ 6 per check.
- **Fetch:** the top 3 results per query go through the normal `EvidenceRetriever` fetch, extract and filter path (the same blocklist, URL identity, `_already_pooled`, PDF guards and fetch-phase deadline). The re-search path already drives that retriever with a supplied query plan (`re_search.py:80-94`).
- **Per-claim pool cap:** ≤ 4 new items. Each new item gets `metadata.cited_source = {name, cue, kind, query, rank}`. URL-ledger lines use `stage=cited_source`.
- **Relevance:** new items go through the existing relevance scorer as a mini-batch. An off-topic hit (a different Bloomberg piece) is dropped there with its normal receipt.
- **Deadline:** 30 s for the stage (search + fetch). Unfinished work gets `not_fetched: deadline`.

## 5. Receipts (invariant #5)
`claim_map.metadata.cited_sources` = `{names: [{name, kind, cue, status ∈ accepted|already_present|cue_not_found|name_not_in_cue}], queries: [{query, results: n, kept: [evidence_id]}], totals, seconds}`.
- No model reasons are stored. The cue is verbatim source text, so it is safe on `/r/`.
- A name the lane searched for and did not find stays in the receipt, and feeds a gap note (§6).

## 6. The gap note: the cheap half
**When it applies:** a name was accepted, the lane ran, and no item from the cited body reached the pool (by host match or `cited_source` metadata).

**What it does:** the claim gets a plain gap entry in the Seeker data: "Sources here cite {name} ({document}) as the origin; that original was not retrieved."
- It is computed mechanically from the receipt, with no new model text.
- **This alone moves H3 from hard to soft** under the grader brief (S9: "absent and a gap card names it").
- It also helps when the search fails, as it would have on #4 in English.

## 7. Invariants and risks
- **#7, no sycophancy:**
  - Names are taken from items on ANY side, because direction is unknown at retrieval.
  - The fetched original is classified and mapped like anything else and can challenge the claim. On #17 the original (EFFIS) refutes it.
  - The claimant's own source is a known hazard. The interested-party and recital gates still apply after mapping. When the claimant is the cited body, this lane only adds the source being recited, and the recital gate is built for that case.
- **Cost:** about 0.3p per check for the model call, plus up to 6 Serper queries (~0.6p) and fetch time.
- **Latency:** about 5–10 s on checks that use it. The quote of the real figure comes from the eval.
- **Bench:** a new stage re-keys every cassette that triggers it, so a re-record is owed (paid; ask).
- **Cache:** `RETRIEVAL_CACHE_VERSION` is bumped in the same commit (Piece 3 rule).
- **Noise:** a common outlet named as "first report" (the Telegraph on #1) is a reporting-tier original. It is still the authoritative available source for an unregistered donation, per the #1 grader note.
- **Out of scope:**
  - Native-language queries for foreign official results (#4) are a separate lane. Here, #4 gets the gap note only.
  - #2 (nothing cited) is untouched.

## 8. Evaluation (free first; each paid step asked)
1. **Extraction precision, offline** (paid: about 41 pools × 1 call ≈ 10p). Run the §3 call over the 41 production pools. A fresh agent labels each accepted name as true origin / quoted person / outlet only / wrong (free).
   - Target: ≥ 85% true origin.
   - Also measure how many pools yield ≥ 1 name.
2. **Retrieval hit rate** (paid: about 2 queries × 18 pools ≈ 4p). For accepted names, run the §4 query and record whether the cited body's own page is in the top 3 (hand-checked).
   - Target: ≥ 60% of accepted names.
3. **Bench** with flags on and `--record-missing` (paid, ask).
4. **Re-run the six H3 records** live (paid, about 15p each, ask). Grade H3 blind with the existing grader brief.

**Held-out note:** the six A− records shaped this design. Step 1 runs on all 41 pools, and the six are reported separately from the other 35.

## 9. Flags
`ENABLE_CITED_SOURCE_LANE` (default False) and `CITED_SOURCE_MODEL`. The gap note has its own flag, `ENABLE_CITED_SOURCE_GAP_NOTE`, so it can ship first if the lane underperforms. `audit/FLAGS.md` is regenerated in the same commit.

## 10. Questions for the reviewer
1. Is the placement after post-filter recovery and before provenance capture right, or should the lane share retrieval's fetch phase so it is not a second round trip?
2. Is one model call for names sound, or should the gap note use only mechanical extraction, so it never depends on a model?
3. Does following a cited name create a sycophancy path the existing gates do not cover?
4. Are the eval targets (85% and 60%) and the per-check caps right?


---

## 11. Rev 2 (2026-10-05): every finding of the review taken (`2026-10-05_cited_source_lane_design_review.md`, APPROVE WITH CHANGES, 6 HIGH)
Where rev 2 and §§1–10 disagree, rev 2 wins. The build splits in two:
- **Build A:** the lane (§11.1–11.7).
- **Build B:** the gap note (§11.8), which needs web work.

Build A ships behind its flag first. Build B follows only if Build A's eval passes or the founder asks for the note alone.

### 11.1 Placement and inputs (H1, option a)
`copy_page_opening`, `_elc.copy_page_opening` and `capture_text_provenance` move from `runner.py:2124–2140` to **before** the lane, which runs after post-filter recovery.
- Capture is idempotent (`text_provenance.py:91`).
- Lane items are captured by running the same loop again over the new items only.
- Post-filter recovery items have no `_full_text`, so they get no provenance, as today.

The lane reads exactly what is stored, `original_snippet` plus the captured passages, so the eval reads production's input (H5). It reads **no tier**: every pooled item is a possible citer.

### 11.2 Narrow search and fetch (H2, M3)
**Helper:** `cited_source.fetch_cited(query, existing_pool, deadline)`.
1. `SearchService.search_for_evidence(query, max_results=10, freshness="none")`, as post-filter recovery does (`runner.py:2032`).
2. The identity filter (§11.3) on the SEARCH RESULTS, before any fetch.
3. `EvidenceRetriever._extract_with_fallback` per kept result, under the lane's own semaphore.
4. The runtime blocklist and `_already_pooled` against the existing pool, then copy collapse (`retrieve._collapse_copy_candidates`, `retrieve.py:196`) against the pool.

It never calls `retrieve_evidence_for_claims`, so there is no planner, no adapters and no minimum-evidence top-up. A test asserts the query string issued equals the built query.

### 11.3 Identity filter: originals only (H3)
A result is kept only if it identifies as the cited body, by one of:
- (a) the host's registrable label starts with a distinctive token of the name (the label-start rule in `interested_party.py`, via `distinctive_tokens` / `interested_party_match`);
- (b) the title suffix names the host (`url_identity.suffix_names_host`);
- (c) the name, or an acronym the cue gives for it, appears in the URL path or the title's publisher segment.

Everything else is dropped with `[URL LEDGER] stage=cited_source reason=not_cited_body`.

**Caps:** at most 1 kept item per name and 2 per claim. Two reporting copies can therefore never enter together. A kept original at primary weight 3 can meet the support floor alone. That is accepted only under the gates in §11.5.

### 11.4 Names: model call, frozen guards (M5, L4)
- **Input:** for each claim, the 12 items whose stored text contains an attribution verb, chosen **round-robin** across claims. Each item gets its host, title, and up to 600 chars of stored text centred on the first attribution verb. Total prompt ≤ 40k chars.
- **Model and time:** one call per check on `CITED_SOURCE_MODEL` = gemini-3.7-flash, 25 s deadline.
- **Started alongside post-filter recovery** (M2), because the two are independent.
- **Guards:**
  - The cue is verbatim (case-exact, whitespace collapsed) in a pooled item.
  - The name is verbatim in the cue.
  - The name is not the citing item's own outlet or host.
  - The name is ≤ 80 chars and the cue 12–200 chars.
  - At most 3 names per claim.
  - A malformed answer for one claim drops only that claim.
- **Already present:** a pooled item that passes §11.3 for the name, AND whose stored text contains a figure or key term from the cue. A present but useless page (the #17 legend) does not count as present.
- **Query:** one per accepted name: `{name} {document?} {claim key terms}`, unquoted (the probe's working shape, not the untested quoted form, M1).
- **Allocation:** round-robin across claims, ≤ 6 per check.

### 11.5 Non-sycophancy (H6)
- **Self-announcements:** for `kind = announcement` (and `filing`), the cited name is passed to the interested-party check as an ORG subject **for that lane item only**. Existing release rules (`released_subjects`) are unchanged.
- **Stated plainly:** the lane mostly retrieves the claim's own source, and that is accepted only because the interested-party and recital gates apply to what it brings.
- **Not fixed:** a regulator's ruling the copies do not cite (#15's OSR) stays out of reach. This lane follows citations; it does not discover them.
- **Eval:** flag-on against flag-off, list every element whose state changed, and the direction and tier of every lane item that took a directional ref.

### 11.6 Tiers, timing, ids (M2, M4, L1, L2, L3)
- **Quick tier:** `PipelineConfig.enable_cited_source_lane` (True in full, False in `QUICK_CONFIG`), declared as `no_cited_source_lane` in `tier_limitations`. Frozen replay and re-search skip it, each with a receipt.
- **Timing:** `stage_timings["cited_source"]`. The stage has a 30 s deadline for search and fetch. The eval reports stage and total wall time at p50 and p95, flag-on against flag-off, against the `/agent` 180 s limit. Every downstream call is costed.
- **Ids:** `ev-cs-{pos}_{n}`.
- **Item metadata:** `metadata.cited_source = {name, kind, cue, query, rank, citing_ids}`. `citing_ids` is kept for later reuse by echo link confirmation.
- **Cache (L1):** no cache bump is needed, because the lane runs after the cache. Build check: `_full_text` survives the Redis round trip, so cache-hit runs still capture passages.
- **Relevance:** lane items skip the scorer. The identity filter is the guard, and the scorer would keep a same-topic wrong article anyway (M3).

### 11.7 Receipts
`claim_map.metadata.cited_sources` = `{names: [{name, kind, cue, status: accepted|already_present|cue_not_found|name_not_in_cue|self_outlet|over_cap}], queries: [{query, results, kept: [evidence_id], dropped_not_cited_body}], totals, seconds}`. No model reasons are stored.

### 11.8 Build B: the gap note (H4, M6). Specified now, built second
- **Presence:** computed at the END of the run, after coverage recovery. The body counts as present if a SHOWN (not excluded) item passes §11.3 and its stored text holds the cue's figure or key term. `re_search.research_claim` recomputes it.
- **Field:** `claim_map.metadata.cited_sources.missing = [{name, cue}]`.
- **Surface:** one shared component used by the dashboard and `/r/`. It is a row in the Gaps lens, under a heading "Cited but not in this record". It counts in the Gaps counter.
  - Wording: `Sources here attribute this to {name} ("{cue}"); that source is not in this record.`
  - When a note exists, the all-covered state reads "Each element has evidence mapped; one cited original is not in this record."
  - Shared type in `shared/types`, and tests on both hosts.
- **Flag-off form (M6):** `ENABLE_CITED_SOURCE_GAP_NOTE` alone runs name extraction with no search, and the note says "not in this record" (never "searched and not found").

### 11.9 Evaluation (H5, M1, M7), every paid step asked
1. **Names, held-out** (about 10p):
   - Freeze the prompt and guards first.
   - Run on **local** pools with stored text whose claim text is not among the 41 production pools read during design (count to be confirmed at build).
   - A fresh blind agent labels each accepted name: true origin / quoted person / outlet only / wrong.
   - **Pass:** ≥ 85% true origin, ≥ 40 accepted names, with a 95% interval. If fewer than 40 names come out, report that and stop rather than lower the bar.
   - The 41 production pools are reported as in-sample only.
2. **Retrieval, held-out** (about 5p). Run the exact query the builder produces for ≥ 20 accepted names.
   - A hit means the identity-filtered item is kept AND its stored passages carry the claim's figure or finding.
   - **Pass:** ≥ 60%.
3. **Bench** with the flag on, `--record-missing` (ask).
4. **Six H3 records**, twice each on the same day, flag-off and flag-on (about £1.80, ask).
   - Grade H3, H2 and S4 blind with the existing brief.
   - Report timing and every state change.

**Stated up front:** #2 (nothing cited) and #4 (needs a German query) cannot clear H3 through this lane (L5). The lane's ceiling on the six is #1, #6, #15 and #17.


## 12. Rev 2.1 (2026-10-05): re-review findings N1–N8 taken
These replace the named paragraphs of §11.

### 12.1 Identity rests on the HOST only (N1; replaces §11.3)
A search result is the cited body's own page only if its **host** identifies the body. Title and path are never enough: `suffix_names_host` only shows that a title names its own host, and a copy's slug can name its source.

- **Tokens:** the name's distinctive tokens, lower-cased first (`distinctive_tokens` does not lower-case). That means ≥ 3 chars, not generic. Generic words for this rule include daily, news, the, new, national, report, data, office, group and agency.
- **Rule 1, token match.** Every distinctive token is a host label or the start of one, e.g. bloomberg → `www.bloomberg.com`; telegraph → `www.telegraph.co.uk`.
  - On a **shared public suffix** (`nhs.uk`, `gov.uk`, `europa.eu`, `ac.uk`, `gov`, `edu`, `int`), every distinctive token must match a label. NHS England matches `www.england.nhs.uk` but not `surreysussex.icb.nhs.uk`.
- **Rule 2, acronym match.** The acronym the cue gives for the name ("(EFFIS)"), or the name itself when it is all capitals, equals a host label. EFFIS matches `effis.emergency.copernicus.eu`, but not `forest-fire.emergency.copernicus.eu` or `joint-research-centre.ec.europa.eu`.
  - A known miss: EFFIS's statistics app on `forest-fire.…` is not matched. The note (Build B) covers that.
- **Everything else** is dropped with `[URL LEDGER] stage=cited_source reason=not_cited_body`.
- **Caps:** unchanged at ≤ 1 per name and ≤ 2 per claim.
  - Correction to §11.3: "two copies can never enter together" holds per name, not per claim.
  - Two genuine originals on one claim can carry an element alone (weight 6 against a floor of 3). That is accepted, because both are identity-checked originals.

### 12.2 "Already present" is decided by content, not by the name (N2, N5; replaces the §11.4 and §11.8 presence tests)
A pooled (or, for the note, shown) item makes the body **present** only if both hold:
- (i) it passes §12.1 on its host;
- (ii) its stored text (`original_snippet` plus passages) holds a figure stated in the CLAIM (numbers with their unit or %), or, for a claim with no figure, at least 2 of the claim's content terms. **The name's own tokens are excluded** from those terms.

Two kinds of page never make a body present, and never count as an eval hit:
- a snippet-only item (403, timeout, or a PDF with no `_full_text`);
- the #17 legend page (host fails rule 2, and it holds no claim figure).

### 12.3 No copy collapse in the lane (N3; deletes step 4 of §11.2)
`_collapse_copy_candidates` reads search-result objects through `getattr` and knows nothing of the pool. Its survivor rule would also drop the lane's original in favour of a pooled copy. The lane uses `_already_pooled` (URL identity) plus the §12.1 host identity, and that is enough.

### 12.4 Fetch conversion (from the re-review's code check; adds to §11.2)
- `_extract_with_fallback` needs only `self.evidence_extractor`.
- The lane sets `source_path="cited_source"` and `_freshness="none"` on each search result before the call.
- It converts the returned snippet to a pool dict exactly as `retrieve.py:2089-2113` does, including `_full_text` and `date_basis`.
- A test pins that the conversion keeps `_full_text`.

### 12.5 Interested party for lane items (N4; refines §11.5)
The cited name is added as an ORG subject for that lane item when either holds:
- the model's `kind` is `announcement` or `filing`;
- the cue contains a statement verb (said, announced, published, released, reported, wrote).

It **never** overrides a release the claim already earned (`released_subjects` is unchanged and wins).

### 12.6 Build B wiring (N6; refines §11.8)
- The Gaps counter comes from one shared function, `evidenceCoverage` in `web/lib/evidence-coverage.ts`, used by the summary panel, `SeekerView`, `CoverageMap` and `seeker-honesty`.
- That function is extended with the cited-but-missing entries. `SeekerView` alone is not.
- The component lives under `web/components/evidence-views/seeker/`.

### 12.7 Held-out size (N7; refines §11.9 step 1)
- About 87 distinct local claims have stored text (the echo held-out count). Pools are de-duplicated by claim text.
- If fewer than 40 names are accepted, the result is reported as underpowered and the step stops. The bar is not lowered.
- The founder can then approve topping up with production checks created after 2026-10-05.

### 12.8 Order (N8; refines §11.1)
Provenance capture and both page-opening copies move above **post-filter recovery**, not just above the lane. The name call can then start beside post-filter recovery on text that already exists. Recovery items have no `_full_text`, so capture skips them, as today.

## 13. Build A as built (2026-10-05), flag OFF
**Code:** `app/services/cited_source.py`. In `runner.py`, source-text capture now runs before post-filter recovery, the name task starts beside it, and `follow_for_check` runs after it, with skip receipts. `claim_map_analyzer.py` carries the per-item interested-party subject. Config flags, `tier_limitations` and `FLAGS.md` are updated.

**Deviation (accepted by the verifier):** the quick-tier skip is declared in `tier_limitations` only while the flag is on, rather than through a `PipelineConfig` field. This is the same pattern as echo link confirmation.

**Verification:** `audit/2026-10-05_cited_source_build_a_verification.md`, PASS WITH FIXES. All its findings are taken:
- **H1, the race:** the pool check and the per-claim cap are decided under one lock. A URL is reserved before its fetch is awaited, and a failed fetch releases its slot and tries the next result.
- **H2, the submitted page:** `retrieve._source_exclusion` is applied. The submitted page is never kept, and other pages on its domain are tagged `same_domain_as_source`.
- **M1, the host:** identity now rests on the site's own label by **equality** (a token, the tokens joined, or the name squashed), not by prefix. That rejects whoscored.com for WHO, cdcgaming.com, onsitenews.com, bloomberg.substack.com and telegraphindia.com.
- **M2, statement verbs:** "states" and the noun "claims" are removed from the statement-verb list.
- **M3, tests:** tests now cover `_snippet_to_item`, `_default_extract` and an end-to-end `follow_for_check`.
- **LOW:** each drop now has a URL-ledger line.
- **LOW, not fixed:**
  - a names task can be orphaned on a watchdog cancel (bounded by its 25 s deadline);
  - model tokens are not in `by_stage`;
  - the stage timing overlaps post-filter recovery.

**Checks:** 70 lane tests; 22/22 applicable mutants killed; unit suite 4,542 pass; flags-off bench equals baseline (158/13/11/5 + 82CF).

**Next:** eval step 1 (paid, awaiting approval). There are 308 held-out pools rebuilt in production shape (`audit/cited_source/build_heldout.py`).

## 14. Eval step 1 result (2026-10-06): FAILS the bar, narrowly
- **Run:** the first 100 of 308 held-out pools (sorted by claim id), prompt and guards frozen at `1c68cf2`. 100/100 calls ok, 86 names accepted, 50 pools with at least one. Cost $0.33. Output: `audit/cited_source/eval_runs/names_run1_100.json`.
- **Blind labels** (one fresh agent, no knowledge of the lane): true_origin 71 · wrong 10 · outlet_only 3 · quoted_person 2. **Precision 82.6% (71/86), Wilson 95% interval 0.73–0.89, against the bar of ≥ 85%.** Labels: `eval_runs/blind1/labels.json`; key: `eval_runs/blind1_key.json`.
- **Misses by class:**
  - Too vague to search for (3): "Australian government", "the company", "government".
  - The name is the citing page's own publisher (3): CMA on gov.uk, WHO on who.int, Harvard Chan on hsph.harvard.edu.
  - Misattributed (4): NIH (PubMed indexing), Cancer Research UK (it supplied the dataset, but the finding is Google Health's), Supplemental Poverty Measure (a statistic, not a body), IPCC (only a time reference).
  - Outlet only (3), including ScienceDirect, which is arguably acceptable.
  - Quoted person (2): an individual's own estimate attributed to their institution.
- **Not a pass and not lowered.** The first two classes are mechanical guard gaps. Fixing them now and re-scoring these same rows would be in-sample. Any fix must be measured on pools 101–308, which have not been read.

## 15. Guards added, re-test on unseen pools (2026-10-06): 84.0%, still just under the bar
- **Guards (`cited_source.py`):**
  - `is_vague_name` refuses a name made only of generic heads ("government", "the company") or a nationality adjective before one ("Australian government").
  - `published_by` widens the self-outlet check on shared-suffix hosts. It refuses a name whose acronym or distinctive token is a whole host label (WHO on who.int, Harvard on hsph.harvard.edu), or whose acronym opens the page slug (CMA on gov.uk/…/cma-fines-…).
  - The 6 matching run-1 misses are refused, no run-1 true origin is refused, 87 lane tests pass, and the unit suite passes (4,559).
- **Run 2:** pools 101–308, never read before. 208/208 calls ok, 225 names accepted, $0.73. Labelled blind by three fresh agents, each working in a private folder.
- **Result:** true_origin 189 · wrong 18 · outlet_only 10 · quoted_person 8. **Precision 84.0% (189/225), Wilson 95% interval 0.79–0.88. The bar is 85%, so this fails, narrowly.**
- **Residual misses:**
  - **Self-publishers (about 8 of the 18 wrong):** university newsrooms (news.uchicago.edu for "University of Chicago", McGill, KUMC), a press release on a wire host (Royal LePage on newswire.ca), and Eurostat, ERA5, Ember and Kelley Blue Book on their own or a parent host. In the pipeline such a name usually costs nothing, because `already_present` skips the search when the citing page is the body's own and carries the claim. It is still counted as a miss here.
  - **Quoted speech via an outlet (8):** for example "the BBC" for a Zelensky interview.
  - **Data supplier vs finding (about 4):** for example UK Biobank and ATUS.
  - **Relay outlets (10):** for example AP and Interfax.
- Labels: `eval_runs/blind2_{0,1,2}/labels.json`; key `eval_runs/blind2_key.json`.

## 16. Eval step 2, retrieval (2026-10-06): FAILS badly
- **Run:** the 225 run-2 names, each followed alone through the production `follow_names` (exact query, host identity filter, production fetch, with Redis up). About 225 searches. Output: `audit/cited_source/eval_runs/retrieval_run2.json`.
- **Result:** of the 189 blind-labelled true origins, an item was **kept for 34 (18%)**, and **the kept item carried the claim's figure or finding for 18 (9.5%), against a bar of 60%.**
- **Where it was lost:**
  - On **120 names, every search result was dropped by the host identity filter.** Either the search did not return the body's own site, or the filter refused it. The per-result URLs were not logged, so the two cannot yet be told apart.
  - **16 kept items were the right body but the wrong page:** a dashboard, a report index or a login page (IISS, IEA, CBS, BP, OECD, IPCC, The Information).
- **Reading:** the 5/5 probe was on hand-picked H3 failures, and it does not generalise. The lane stays OFF. Build B (the gap note: "this source cites X, which is not in the pool") needs only the names, which run at 84% precision, and no search.
- An earlier attempt the same day was stopped at 0 names because Redis was down (extraction fell back to word overlap). It was rerun.
