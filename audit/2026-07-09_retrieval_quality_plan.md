# Retrieval-quality investigation — findings & remediation plan (2026-07-09)

**Status:** SIGNED OFF (founder, 2026-07-09) → **CORE REMEDIES BUILT same day: R1a + R1b(a) + R2a + R2f(i) + R2e** (see "Build record" at the end). Deferred: R2g, R2b, R2d; dropped: R2c; R1c.
**Verification pass (2026-07-09):** every file:line claim re-read in code; PubMed behaviour confirmed empirically against the live NCBI API; the shown-pool provenance for claim 1 confirmed against prod (`api_metadata.post_filter_recovery=true` on all three rows). Four corrections were applied — see the F-R2 section, which was materially restructured: (a) PubMed has **no** year filter (its zero is query-shape, confirmed live); (b) claim 1 had **zero** initial web results (web search timed out check-wide; the provider-None excluded rows are double-written OpenAlex audit rows); (c) reddit/tiktok/yale entered via **Stage 3.8 post-filter recovery** (claim-text search, hardcoded `freshness="py"`, unscored) — a newly confirmed contributor with its own remedy; (d) "query strings persisted nowhere" was overstated — `metadata.query_used` is persisted for surviving web items; what's missing is the full query *plan* including zero-yield queries.
**Grounding:** `audit/2026-07-09_c3_capture_findings.md` (§4 defects, §5 starting points) · prod check **TRU-C051-3024** (uuid `c0513024-…`), pulled read-only via `backend/scripts/retrieval_capture_pull.py` (SELECT-only, single-check scoped) · four independent code traces (retrieve pipeline, WHO+academic adapters, relevance scorer, decompose).
**Discipline:** every assertion below carries a file:line or an artefact quote. Suspicions are labelled SUSPECTED and separated from confirmed causes. Any fix is mechanical (NF-11) and replay-bench-gated (`backend/scripts/replay_bench.py --all`).

> **See also (2026-07-14):** the non-sycophancy invariant work adds a **per-element challenge-oriented query lane** at the same augmentation seam (`retrieve.py:332-377`) — retrieval is currently topical-only and never searches the *other side* of a claim. That work ranks above the deferred remedies here (R2b/g/d) and any challenge-lane build should be reconciled with them. Docs: `audit/2026-07-14_non_sycophancy_invariant.md` (design) + `audit/2026-07-14_non_sycophancy_discussion.md` (discussion).

---

## 0. The check, as it actually ran (artefact ground truth)

TRU-C051-3024: input paragraph → 2 claims, domain=**Health**, jurisdiction=**Global**, entry_mode article. `web_search` provider status = **timeout / count 0**: the initial web-search lane produced **nothing for either claim** this run (RawEvidence contains zero engine rows at retrieve time — every included row is an API-adapter row). API adapters fired check-wide: WHO 10, PubMed 10, OpenAlex 6, Semantic Scholar 3 (pre-cap counts; PubMed/SemScholar/WHO counts are all claim 0 — each returned 0 for claim 1).

**Claim 0** — "Moderate alcohol consumption protects against heart disease" (causal_interpretive, no DATE entity). Shown pool = 9 items: 5 real academic anchors (SemScholar/PubMed/OpenAlex, scores 5/5/4/2/2) + 1 domain-cap-demoted SemScholar + **3 WHO indicator pages, all `llm_relevance_score=1`, 2 shown / 1 unmapped**. This is F-R1.

**Claim 1** — "Many doctors historically recommended a daily glass of red wine" (empirical, NO DATE entity, entities = `[Many doctors/PERSON, red wine/OTHER]`). Elements decomposed as:
- e1 "Historical records or testimonies exist detailing medical recommendations." → **unresolved, 0 refs**
- e2 "These records indicate that a portion of doctors advised daily red wine consumption." → disputed, 1 challenge
- e3 "The quantity specified in these recommendations was typically one glass." → disputed, 1 context / 1 challenge

Claim 1's entire initial pool was **OpenAlex ×3 — all score=1, all excluded** (illicit spirits 2024, brain-computer interfaces 2024, asylum history 2024; the three provider-None `llm_relevance` rows in RawEvidence are these same items double-written by the exclusion audit path, which omits `external_source_provider` — `runner.py:1678-1691`). **PubMed and Semantic Scholar returned zero for this claim; web search returned zero (timeout).** So after the scorer, claim 1's pool was **EMPTY**. The shown **reddit.com / tiktok.com / yalemedicine.org** all entered later via **Stage 3.8 post-filter recovery** (confirmed in prod: `api_metadata.post_filter_recovery=true` on all three). This is F-R2.

---

## F-R1 — WHO indicator noise in the shown pool

### Root cause (three independent contributors; each individually admits the noise)

**(1) The WHO adapter returns policy/administrative indicator NAMES, not evidence.** `app/services/api_adapters/health.py:413` hits the GHO OData `/Indicator` catalogue (a list of indicator *definitions*), then substring-matches the mapped concept keyword against `IndicatorName` (`health.py:420-425`):
```python
matching_indicators = [ind for ind in indicator_response.get("value", [])
                       if query_lower in ind.get("IndicatorName", "").lower()][: self.max_results]
```
Any indicator whose *name* contains "alcohol" matches — including the three admin/policy indicators seen. Snippet is the fallback `f"WHO health indicator: {title}"` because these rows carry no `Definition` (`health.py:447-451`); url is a generic indicator-details landing page; `source_date=None` (`health.py:445,463`). Near-zero topical value **by construction**.

**(2) The NF-07 structural-metadata bypass keeps them despite the scorer scoring them 1/5.** The relevance scorer did its job — all three carry `llm_relevance_score=1` with correct rationales ("describes a WHO health indicator … not relevant to the claims"). But WHO declares `emits_structural_metadata=True` (`health.py:360`), so the score==1 exclusion is bypassed (`relevance_scorer.py:724-733`):
```python
if score == 1:
    if _adapter_emits_structural_metadata(provider):
        ev["relevance_scorer_bypass"] = "api_adapter_canonical_source"
        kept.append(ev)          # ← kept despite score 1
```
The bypass exists so canonical *data* adapters (ONS observations, taxonomy) aren't discarded by an LLM that undervalues terse structured snippets. **WHO's `/Indicator` output is not substantive data — it is a catalogue of indicator titles.** The flag is correct for WHO's stat indicators but misapplied to its policy/admin indicator names.

**(3) Provider→primary tiering** guarantees any API-sourced item lands `tier=primary`: the heuristic/high-confidence rule returns `("primary","data")` whenever `external_source_provider` is set (`evidence_classifier.py:290-295`), and the override wins over the LLM on tier disagreement. On this check the LLM itself classified them primary/**official_statement** (`classification_method=llm` in the artefact) — either path ends at primary. Contributing (makes the noise look authoritative), not the reason it is in the pool.

**Net effect:** 2 WHO indicator pages surfaced (mapped as context). Low orientation harm, but they platform our weakest sourcing exactly where a prospect compares source columns.

### Remedies (ranked)

| id | Remedy | File(s) | Blast radius | Verification |
|----|--------|---------|--------------|--------------|
| **R1a** *(preferred)* | In the WHO adapter, drop indicators whose `IndicatorName` matches a policy/admin lexicon (`policy`, `strategy`, `action plan`, `standards of care`, `operational`, `legislation`, `involves … activities`, `national … plan`) **and/or** that have an empty `Definition`. Mechanical name/field filter in `_transform_response` / the match step. | `health.py` only | WHO-scoped. Risk = over-filtering real WHO stat indicators → key on the policy lexicon + empty-Definition, never a blanket cut. Unit test: policy names dropped, a real stat indicator kept. |
| **R1b** | Narrow the NF-07 bypass so it can't rescue score-1 items with a fallback/stub snippet. Either (a) skip bypass when snippet matches the `"WHO health indicator: …"` fallback shape, or (b) split the flag into `emits_structural_metadata` (classification) vs a new `bypass_relevance_score_1` (scorer) and set WHO's to False. | `relevance_scorer.py` (+ optionally `government_api_client.py`, all 13 adapters) | **Shared scorer — 13 adapters carry the flag** (climate/business/sports/nature/legal/economic/health). (b) is broad; (a) is narrow. This is the *general* fix (stops the next catalogue-style adapter repeating it) but higher risk. | Confirm ONS/Companies House/legal still bypass legitimately (their score-1 canonical rows must survive). Bench + per-adapter unit tests. |
| R1c | Stop auto-promoting content-less API items to `primary`. | `evidence_classifier.py` | Wide — changes tier semantics across all API sources. | **Defer.** Kill the noise upstream instead. |

**Recommendation:** **R1a now** (cheapest, WHO-scoped, removes the pages at source). **R1b(a) as a companion** (snippet-stub guard — closes the general hole with minimal blast radius). R1c deferred.

---

## F-R2 — historical-claim retrieval failure

### Root cause (verified chain — every step artefact- or code-confirmed)

**(1) RUN-SPECIFIC — the initial web-search lane returned nothing for the whole check** (`provider_status.web_search = timeout/0`; zero engine rows in RawEvidence at retrieve time). On a healthy run both claims would have carried scored web evidence. This degradation is why the structural failures below had nothing to hide behind. (Why web search timed out check-wide is a separate reliability question — worth watching, not in this plan's scope.)

**(2) CONFIRMED — Semantic Scholar and OpenAlex year-window the historical literature out at the API.** Both apply `_resolve_min_year(current_year, entities)` = `current_year - 2` = **2024** (`academic.py:22-36`), widening backward *only* when a DATE entity carries an older year:
```python
min_year = current_year - fallback_years        # 2024
claim_year = extract_claim_year(entities)        # None — claim has no DATE entity
if claim_year and claim_year < min_year: return claim_year
return min_year                                  # stays 2024
```
Semantic Scholar sends `year={min_year}-{current_year}` (`academic.py:268-269`); OpenAlex sends `filter=from_publication_date:{min_year}-01-01` (`academic.py:418-419`). **A claim about historical medical advice was searched only across 2024-2026 publications** — the French-paradox / history-of-medicine literature (1990s-2000s) was excluded by construction. Semantic Scholar returned 0; OpenAlex returned 3 tangential 2024 papers (all scored 1, all excluded).

**(2b) CONFIRMED (corrected in verification, empirically tested) — PubMed's zero is QUERY SHAPE, not the window.** PubMed applies **no year filter** (`health.py:126-134` — `term`/`retmax`/`sort` only; no `mindate`/`datetype`; it does not call `_resolve_min_year`). It sends the **raw claim sentence** as the search term (B5 passthrough, `health.py:119-121`). Live NCBI check (2026-07-09): `term="Many doctors historically recommended a daily glass of red wine"` → **count 0** (NCBI ANDs every mapped term); control `term="french paradox red wine"` → **137 results**. So the literature is in PubMed and reachable — the full-sentence AND semantics can't reach it. R2a alone does **not** fix PubMed.

**KEY STRUCTURAL INSIGHT (verified):** the shipped recency safety nets — F1-D3 second-query unwindowing (`retrieve.py:151-168`) and B4 historical DATE-entity unwindowing (`query_planner.py:67-111`) — operate on the **web-search freshness** parameter only. They do not touch the academic adapters' year filters, nor Stage 3.8 recovery (below). **Neither the academic path nor the recovery path has a historical safety net.** The 328c329 hedge does not cover this failure mode.

**(3) CONFIRMED — "historically" produces no DATE entity, so no backward widening fires anywhere.** Entities were `[Many doctors/PERSON, red wine/OTHER]` — no DATE. The scope tagger has only geographic/universal lexicons, no temporal one (`scope_sensitivity.py:39-79`). A historical-without-a-year claim silently gets the narrow now-2y academic window (and, per B4, windowed web queries) every time.

**(4) CONFIRMED — after the scorer, claim 1's pool was EMPTY; everything shown came from Stage 3.8 post-filter recovery, which is recency-locked and unscored.** The scorer correctly excluded the 3 off-topic OpenAlex papers → 0 items. Stage 3.8 (`runner.py:1716-1810`) then backfilled by re-searching the **raw claim text** with **hardcoded `freshness="py"`** (`runner.py:1763-1765`) — no element queries, no query planner, no F1-D3 hedge, no historical handling — and appended results **without relevance scoring** (`llm_relevance_score=None` on all three shown rows). Prod confirms provenance: `api_metadata.post_filter_recovery=true` on reddit/tiktok/yale, and all three published dates (2025-09-30, 2025-10-10, 2026-06-22) sit inside the past-year window of the check date — the `py` lock visibly selected recent social chatter for a historical claim.

**(5) CONFIRMED — coverage recovery (Stage 5.1) never ran, two independent reasons.** Skipped because the check had exactly 2 selected claims (`runner.py:2228-2229`); and even absent that, claim 1's unresolved ratio was 1/3 = 33% < the 40% threshold (`runner.py:2256`) because its weak elements landed *disputed*, not *unresolved*.

**(6) NOT IMPLICATED IN THIS CHECK — meta-shaped decompose elements.** e1-e3 are evidence-about-evidence ("records or testimonies exist…"), and the decompose prompt has nothing discouraging that shape (`claim_map_analyzer.py:145-170`; "testable" at `:153` mildly invites it). But verification showed the element-planned web queries **never produced any of this check's pool** (initial web timed out; recovery and the academic adapters both use raw claim text, not element descriptions). The element shapes likely degraded *mapping* (e1 unresolved with 0 refs) but played no confirmed role in the retrieval failure. Kept as a watch item (R2c), demoted.

### Remedies (ranked)

| id | Remedy | File(s) | Blast radius | Verification |
|----|--------|---------|--------------|--------------|
| **R2a** *(primary)* | When a historical signal is present (mechanical temporal-marker lexicon: `historically`, `historical`, `traditionally`, `used to`, `for centuries`, `in the past`, … OR `time_reference=='historical'`), drop/greatly-widen the academic `min_year` floor (e.g. no lower bound, or 1900) so period literature surfaces. Fixes Semantic Scholar + OpenAlex. **Does not touch PubMed** (no year filter — see 2b). | `academic.py` (`_resolve_min_year` + a new mechanical marker fn) | Academic adapters. Guard: only widen on a historical signal, never for recent-events claims. | New replay corpus entry from claim 1: assert ≥1 period/academic source enters the pool. Unit test on `_resolve_min_year` with/without a historical marker. Extend existing `scripts/f1_recency_eval.py`. |
| **R2f** *(new from verification — co-primary)* | Fix the Stage 3.8 recovery lane: (i) drop the hardcoded `freshness="py"` to `"none"` (or apply the same historical-signal logic) at `runner.py:1763-1765`; (ii) optionally run recovery items through the relevance scorer instead of appending unscored. For THIS check, (i) alone would have let the recovery search reach pre-2025 material. | `runner.py:1763-1765` (+ scorer call if (ii)) | Recovery lane only. (ii) adds one LLM call + latency on thin checks — can ship (i) alone first. | Unit test: recovery search called with freshness none/derived. Replay corpus assertion that recovery items carry scores if (ii). |
| **R2e** *(enabler)* | Persist the per-element query **plan** (all planned queries + freshness per element, including zero-yield ones — e.g. onto `claim_map.metadata` at save time). Today only `metadata.query_used` on *surviving* web items reaches the DB (`runner.py:2928`); queries that returned nothing leave no trace, which is exactly the blind spot when diagnosing a miss. Non-behavioural. | `retrieve.py` / claim_map persistence | None (additive). | Next real check: pull artefacts and see the full plan. Unblocks all future retrieval diagnosis. |
| R2b | Consolidate temporal signalling: emit a mechanical `temporal='historical'` tag once (sibling to scope_sensitivity) and consume it in `_resolve_min_year`, query-planner freshness AND recovery freshness. Supersedes R2a's local marker fn and R2f(i)'s local logic. | `scope_sensitivity.py` (+ callers) | Wider but cleaner (one source of truth). | Same as R2a/R2f + a scope-tagger unit test. |
| R2d | Let a thin / social-only / zero-primary pool trigger coverage recovery (Stage 5.1) regardless of claim count, instead of the blanket ≤2-claim skip. | `runner.py:2228` | Latency on small checks (the reason for the skip) — scope narrowly (only social-only/zero-primary, not all small checks). | Recovery-trigger unit test; bench latency check. |
| R2g | PubMed query shape for zero-hit sentences: on `count 0`, retry with a reduced term set (entity nouns, e.g. "red wine" + "doctors" + "recommendation") instead of the full ANDed sentence. Mechanical retry, adapter-local. | `health.py` (PubMed `search`) | PubMed only. Guard against over-broad retries (cap at one retry, require ≥2 content terms). | Unit test with a canned zero-hit esearch response; live check of the reduced-term query shape. |
| R2c | Discourage meta-shaped decompose elements (object-level phrasing over "records/testimonies exist"). | `claim_map_analyzer.py` prompt | Decompose-wide; prompt-only ⇒ fragile (NF-11). | **Demoted — verification showed element shapes played no role in this check's retrieval failure** (element queries never produced the pool). Revisit only if R2e artefacts implicate them on a future check; the mapping-side effect (e1 unresolved) is a different investigation. |

**Recommendation:** **R2a + R2f(i) together are the fix for this failure class** — both mechanical, small, independently testable; R2a reopens the academic window, R2f unlocks the safety net that actually filled this pool. **R2e alongside** (cheap, closes the diagnostic blind spot). **R2g** if you want PubMed to contribute on historical claims (its zero was query shape, not recency). Prefer **R2b** over R2a+R2f(i)'s local markers if you want one temporal source of truth (slightly bigger change, cleaner). **R2d follow-up. R2c dropped/demoted.**

---

## Cross-cutting instrumentation gap

The full per-element query **plan** is the one artefact we needed and did not have. `provider_status`, `api_sources_used`, `cost_telemetry` reach the DB, and `metadata.query_used` reaches `Evidence.api_metadata` for items that *survived* (`runner.py:2928`) — but queries that yielded nothing (the diagnostic case) leave no trace. R2e closes this. Recommend adopting it regardless of the F-R2 decision.

---

## Verification plan (whichever remedies are chosen)

1. **Replay bench gates every change** — `python scripts/replay_bench.py --all` before commit. Add a new corpus entry built from TRU-C051-3024's two claims (or a synthesised historical-medicine claim) with assertions: (a) no WHO policy-indicator names in the shown pool; (b) the historical claim's pool contains ≥1 period/academic source.
2. **Targeted unit tests** — WHO policy-lexicon filter (R1a); `_resolve_min_year` historical widening (R2a/R2b); recovery freshness derivation (R2f); NF-07 bypass snippet-stub guard + regression that ONS/legal canonical score-1 rows still bypass (R1b). Test the wired seam, not just the halves (NF-18 lesson).
3. **Existing eval harnesses** — extend `scripts/f1_recency_eval.py` (recency) and reuse `scripts/f3_scope_eval.py` patterns; both are already present (untracked) from the F1/F3 work.
4. **Prod re-verification** — after deploy, re-run the capture claim through the pipeline and pull artefacts again with `scripts/retrieval_capture_pull.py`; confirm the WHO pages are gone and the historical claim pulls period literature. This also feeds the C3 "re-run after fixes land" revival route.

---

## Scope notes

- **Not in scope:** Webcite / competitor anything (C3 stays parked; revival routes unchanged in the findings doc §6).
- **Blast-radius flag:** R1b and R2b touch shared machinery (13-adapter scorer flag; the scope-tagger). If the founder wants the lowest-risk path, R1a (WHO adapter only), R2a (academic adapters only) and R2f(i) (one hardcoded freshness in the recovery lane) are each narrowly scoped and independently shippable.
- **Run-specific vs structural:** the check-wide web-search timeout (cause 1) inflated how bad this specimen looked, but every structural defect above reproduces on any historical-no-year Health claim whenever academic yield is the pool's backbone. The timeout itself is a reliability observation to watch, not part of this plan.
- New script `backend/scripts/retrieval_capture_pull.py` is read-only and reusable for any check-id (change the `PREFIX` constant).

---

## Build record (2026-07-09, post-sign-off)

| Remedy | What shipped | Tests |
|--------|--------------|-------|
| R1a | `WHO_POLICY_INDICATOR_PATTERN` in `health.py` — policy/admin indicator names dropped before the max_results slice; the three TRU-C051-3024 noise rows are the test fixtures. | `test_api_adapters_week2.py::TestWHOAdapter::test_policy_indicators_filtered_from_search` |
| R1b(a) | `_is_stub_snippet` in `relevance_scorer.py` — the NF-07 bypass refuses score-1 items whose snippet merely restates the title (≤40 extra chars). Canonical structured snippets unaffected. | `test_relevance_scorer_bypass.py::TestFR1bStubSnippetGuard` (4 tests) + all 32 existing bypass regressions green |
| R2a | NEW `app/utils/temporal_markers.py` (shared historical lexicon, deliberately narrow) + `_resolve_min_year(..., claim_text=)` widens to `HISTORICAL_MIN_YEAR=1900` on marker with no older DATE year. Wired: Semantic Scholar, OpenAlex, CrossRef. Explicit DATE year still wins. | `test_temporal_markers.py` (24 cases) + `test_academic_year_window.py` (+5, incl. wired HTTP seam with the live claim shape) |
| R2f(i) | Stage 3.8 recovery freshness derived: `"none"` on historical marker, else `"py"` (`runner.py`). Engines already omit the window on `"none"` (B4). | `test_recovery_freshness.py` — wired seam through `run_pipeline_phase2`, asserts the freshness reaching `SearchService.search_for_evidence` |
| R2e | Merged query plan (queries / element_ids / freshness, incl. zero-yield) persisted onto `claim_map.metadata.query_plan` at result-build (`runner.py`). Additive `NotRequired` key on `ClaimMapMetadata`; API camelCases to `queryPlan`; TS type added in `shared/types/index.ts`. | `test_query_plan_persistence.py` — wired through phase 2 with retrieve-time mutation; absence-is-meaningful control test |

Gates: full unit suite **2,363 passed / 44 skipped (live-LLM only)**; `web` tsc clean; replay bench **54 ok / 1 warn / 5 fail — identical to a stash-verified clean-main baseline** (the 5 cassette-drift fails are the pre-existing F7 re-gold debt; comparable per-golden miss counts match exactly), i.e. the remedies are bench-neutral. **Shipped `c61d9a5`, pushed 2026-07-09.**

Post-deploy verification owed (prod eyeball): re-run the capture claim, pull artefacts with `retrieval_capture_pull.py`, confirm (a) no WHO policy pages, (b) historical claim pulls period literature, (c) `claim_map.metadata.query_plan` populated.
