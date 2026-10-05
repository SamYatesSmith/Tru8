# Verification: cited-source lane, Build A (2026-10-05)

**Verifier:** independent; did not write the code. No repository file changed except this one.
**Reviewed:** the uncommitted diff (`cited_source.py`, `runner.py`, `claim_map_analyzer.py`, `config.py`, `tier_limitations.py`, `FLAGS.md`, `test_cited_source.py`) against design §11 rev 2, §12 rev 2.1, and review items R1–R4.
**Tests run (no network):** `test_cited_source.py` + `test_flag_register.py` 54 passed. `test_tier_limitations`, `test_text_provenance`, `test_interested_party`, `test_echo_link_*`, `test_originator_review` 177 passed. `test_runner`, `test_runner_phase2`, `test_echo_link_seam` 264 passed.

## Verdict: PASS WITH FIXES

With the flag off (the default), behaviour is unchanged, so the code is safe to commit. With the flag on it is NOT ready: two HIGH faults break the lane's own non-sycophancy caps. Fix both before any flag-on eval or bench run.

---

## HIGH

### H1. The per-claim cap and URL dedup are checked before an await, so concurrent names break both
- `follow_names` starts one task per query at once (`cited_source.py:676`). Each task checks `kept_per_claim` (`:640`) and `_already_pooled` (`:638`), then awaits `extract` (`:643`). It only counts the keep and adds the URL afterwards (`:649`, `:669`).
- With real I/O every task passes the checks before any of them records a keep. Reproduced with mocks that yield once (`await asyncio.sleep(0.01)`):
  - three names on one claim gave **3 kept items** (`ev-cs-0_0..2`), against the cap of 2 (§12.1);
  - two names that resolve to the same URL gave **the same page twice** in one claim's pool. Both copies can then be mapped as two `supports` refs from one page (weight 6 from one primary). The same race applies across claims (invariant #1).
- `test_at_most_two_kept_per_claim` passes only because its mocks never yield, so the tasks run one after another. It is vacuous for this behaviour.
- Fix: reserve before awaiting. Increment `kept_per_claim[pos]` and `existing_urls.add(url)` before `await extract`, and roll back on a `None` result. Or run each claim's names one after another (claims can still run in parallel). Make the test mocks `await asyncio.sleep(0)` so the test can fail.

### H2. The lane can fetch the submitted page and use it as evidence for its own claims
- In article mode, retrieval drops the submitted page (`retrieve._source_exclusion`, `retrieve.py:247-265`, fed by `exclude_source_url` from `workers/pipeline.py:255`) and tags its domain-mates `same_domain_as_source`.
- The lane applies neither. `follow_names` and `follow_for_check` never see the source URL, although `run_pipeline_phase2` has it (`runner.py:1602`).
- Path: a user submits a Bloomberg analysis. The pool's relays cite "a new Bloomberg analysis finds". The guard `self_outlet` only checks the CITING item's host (`cited_source.py:475`), so the name is accepted. The submitted page is not in the pool, so `already_present` is false. The query built from the name plus the claim's figures will rank the submitted page first, and host identity keeps it. The article then supports itself. That is the self-corroboration Track Q removed, now targeted (invariant #7).
- Fix: pass `source_url` into `follow_for_check`. Drop results where `_source_exclusion(...) == "skip"`, with a `[URL LEDGER] ... reason=submitted_page` line and a query receipt. Tag `same_domain` results with `metadata.same_domain_as_source = True`, as retrieval does. Add a test.

---

## MEDIUM

### M1. Rule 1 lets short acronyms and hosting-platform subdomains through
- `name_tokens` keeps tokens of ≥ 3 chars (R2), and rule 1 accepts any label that STARTS with each token (`cited_source.py:260`). For an all-caps name the single token is the acronym.
- Probed: `whoscored.com` passes for "WHO", `cdcgaming.com` for "CDC", `onsitenews.com` for "ONS", `imfnews.org` for "IMF". R3 asked that 2–3 letter acronyms match only the registrable label, for exactly this reason. Rule 2 does that, but rule 1 now admits them anyway.
- Single-token names also match a platform subdomain: `bloomberg.substack.com` passes for "Bloomberg"; `telegraphindia.com` passes for "Daily Telegraph". These are copies or other bodies.
- Fix: for a token of ≤ 4 chars, require label equality, not label-start. Treat known hosting platforms (substack.com, medium.com, blogspot.com, wordpress.com, github.io) as shared suffixes. Add the six hosts above as must-drop fixtures.

### M2. The statement-verb pattern arms on nouns and on "United States"
- `STATEMENT_CUE` matches `states` and `claims` as whole words (`cited_source.py:51-54`). "data from the United States Census Bureau" and "a Bloomberg analysis of insurance claims" both arm the interested-party subject (probed). That is the R1 failure shape: the lane's own data originals become `context`, and the eval reads "no effect".
- Fix: drop `states` and `claims` (and `says`/`announces` are fine), or require the verb right after the name (within a few tokens). Add the two cues above as must-not-arm tests, plus the #1 cue ("Delo wrote in the Daily Telegraph"), which R1 asked for and the tests omit.

### M3. The fetch adapter and the runner wiring have no tests
- §12.4 asks for a test that the conversion keeps `_full_text`. `_snippet_to_item` (`cited_source.py:748-767`) and `_default_extract` (`:770-782`) are never called by a test. `test_only_the_cited_bodys_own_page_is_kept` asserts `_full_text == "full"`, but that value comes from the test's own mock `extract`, so it proves nothing about the adapter.
- No test runs `run_pipeline_phase2` with the lane on or off. Nothing pins: the names task is cancelled on exit; `quick_tier` and `frozen_replay` skip receipts are written; the second `_capture_source_text()` captures lane items; flag-off output is unchanged.
- Fix: a unit test that feeds an `EvidenceSnippet` with `_full_text` and `date_basis` through `_snippet_to_item`. A runner seam test (in the style of `test_echo_link_seam.py`) for: flag off → no `cited_sources` metadata and no task; quick → skip receipt; lane item gains `text_provenance` before classify.

---

## LOW

- **L1. Orphaned names task on cancellation.** The task starts at `runner.py:2015`. If the watchdog cancels the pipeline during post-filter recovery, nothing cancels it; it runs its model call (≤ 25 s, about 1p) to the end. The same holds for the `run_one` tasks if `follow_names` is cancelled inside `asyncio.wait` (`cited_source.py:678`). Post-filter recovery cannot raise (it is fully wrapped), so only cancellation matters. Fix: wrap from task creation to `follow_for_check` in `try/finally` that cancels the task; in `follow_names`, cancel all tasks in a `finally`.
- **L2. A failed fetch ends the name.** `not item` breaks (`cited_source.py:644-646`), so a blocklisted, JS-only or empty first result stops the name, and the next identity-passing result is never tried (N5's recommendation). A 403 snippet fallback is kept and uses the slot with no `_full_text`. The blocklist is applied inside the fetch (`evidence.py:467`), not before it as N5 asked. Fix: `continue` on `None` within the deadline; check `is_domain_blocked` before the fetch.
- **L3. Some drops have no URL-ledger line.** `not_extracted`, `dropped_over_cap` and the blocklist skip are in the claim-map receipt but not in `[URL LEDGER]` (invariant #5). `deadline_hit` is set on every claim, not only those with a pending query (`:686-688`). Fix: add ledger lines; set `deadline_hit` per position of the pending tasks.
- **L4. Release check compares strings, not subjects.** `_item_subjects` adds the lane subject when `extra not in _s` (`claim_map_analyzer.py:3182-3186`). "the nhs england" or "nhs england's" would pass beside a released "nhs england" and override the release §12.5 says always wins. The direction is safe (it only scopes to context). Fix: skip the extra subject when any of its distinctive tokens belongs to a released subject. Add a release-wins test.
- **L5. Scorer-excluded URLs can return.** `existing` holds only pooled URLs (`cited_source.py:792-795`). A page the LLM scorer excluded as off-topic, or the evidence filters dropped, can be re-added by the lane, and then appears as both excluded and included in the record. Post-filter recovery has the same gap. Fix: seed `existing` from `raw_evidence_data` URLs too, or accept and record it.
- **L6. Re-search has no skip receipt.** §11.6 says re-search skips the lane with a receipt. `re_search.py` never touches the lane, so it skips, but writes nothing. Fix: write `cited_sources.totals.detail = "re_search"` or amend the spec.
- **L7. Model tokens do not reach cost telemetry.** Usage goes only into `claim_map.metadata.cited_sources.totals.usage` (`cited_source.py:719-736`), not `llm_usage_by_stage`. The eval can read it there, but the per-check cost line will under-count. Fix: add a `cited_source` entry to `by_stage`.
- **L8. `stage_timings["cited_source"]` overlaps post-filter recovery** (it starts at `runner.py:2014`). Summing stage timings double-counts. Fine for the eval if stated; `names.seconds` and `follow_seconds` are separate in the receipt.
- **L9. Rule 2 uses the leftmost label as well as the site label** (`cited_source.py:275`). R3 asked for the registrable label or the first label under a shared suffix. Leftmost is needed for EFFIS, so this is a reasonable reading, but it should be stated in §12.1.

---

## Deliberate deviation: quick-tier skip via the flag, not a `PipelineConfig` field
Acceptable. It matches echo link confirmation (`tier_limitations.py:91-104`). It avoids a false `no_cited_source_lane` receipt while the flag is off. The runner's test is `config.mode != "quick"` (`runner.py:2012`), and `QUICK_CONFIG` is the only `mode="quick"` config. Two costs, both shared with echo: the quick skip cannot be switched per tier, and `limitations_for_tier` reads the flag at serve time, so a cached quick result served after a flag flip reports the current flag, not the one it ran under. Record that in the design.

---

## Checks that pass

**Flag off (question 2):**
- `_cs_on` is false, no task is created, and the `elif` writes no receipt (`runner.py:2008-2018`, `:2186`). `tier_limitations` adds nothing (test `test_quick_tier_declares_the_lane_only_while_it_is_on`).
- Capture move is behaviour-neutral. All three writers are idempotent given unchanged `_full_text`: `capture_text_provenance` returns on an existing `text_provenance` (`text_provenance.py:91`); both `copy_page_opening` functions only re-write the same slice of `_full_text` (`originator_review.py:131-140`, `echo_link_confirmation.py:139-143`). Nothing between the two positions touches `_full_text`, `snippet`, `text` or elements: post-filter recovery only reads URLs and appends items with no `_full_text` (`runner.py:2096-2118`). Its ledger count (`:2140-2150`) reads `is_recovery`, not provenance. The second call (`:2199`) visits recovery items exactly as the old single call did, and they are skipped as before. Only `captured_at` moves by the length of recovery.
- Interested-party gate: with no item carrying `interested_subject`, `_lane_subjects` is false, so the arming condition is `subjects` as before; `_item_subjects` returns `subjects` unchanged; `pins` and `summary` are unchanged. The only caller passes `ev_index` (`claim_map_analyzer.py:3523`). Pinned by `test_same_page_without_the_lane_mark_is_not_scoped`.

**Rev 2 / 2.1 requirements met:**
- Inputs are stored text only (`stored_text`, `cited_source.py:168-184`); no tier read; test `test_prompt_never_sees_distilled_text`.
- 12 items per claim with an attribution verb, 600-char window on the first verb, round-robin, 40k cap (`:382-421`); frozen verb list (N7).
- One call, `gemini-3.7-flash`, 25 s `wait_for`, schema-constrained, per-claim parse failure isolated (`:497-539`, `:714-737`).
- Guards: cue verbatim (whitespace-collapsed, case-exact) in the cited item, name in cue, self-outlet, ≤ 80 / 12–200 chars, ≤ 3 names (`:449-494`).
- Presence (§12.2): host identity AND claim figure, or ≥ 2 claim terms with the name's tokens excluded; snippet-only items never count (`:317-344`); #17-style legend test present.
- Identity (§12.1): host only, no title or path; R2 own token helper with ≥ 3 chars and the union of stop lists (`:200-215`); shared suffixes need whole labels; R3 squashed-name rule off shared suffixes; rule 2 acronym on site or leftmost label. #6 relays drop; bloomberg, telegraph, england.nhs.uk, EFFIS, ONS keep.
- No copy collapse in the lane (§12.3); `_already_pooled` with `UrlKeySet` (`:638`, `:788-795`).
- Fetch (§12.4, R4): `_extract_with_fallback` via `EvidenceRetriever`, `_freshness="none"` set before, `source_path="cited_source"` set after (`:653`, `:778`). `_snippet_to_item` mirrors `retrieve.py:2089-2113` field for field, including `_full_text`, `date_basis` and `content_basis`; `element_ids` is `[]` and `external_source_provider` is `None`, both correct for this lane.
- Query: `{name} {document?} {claim terms}`, unquoted, every figure kept; issued exactly as built through `_try_providers` with no window and no country. Skipping `search_for_evidence` is right, because it rewrites the query (`search.py:772`).
- Caps in plan: ≤ 6 queries per check, round-robin across claims (`:589-610`) with `over_query_cap` receipts.
- Ids `ev-cs-{pos}_{k}` are unique per check (the counter step has no await between read and write). Item metadata `{name, kind, cue, query, rank, citing_ids}` (§11.6).
- R1: statement verbs only (said, announced, stated, claimed, press release, statement); `published / reported / wrote / released` removed; `kind ∈ {announcement, filing}` still arms. Gate test end-to-end through `_parse_mapping_response` scopes the NHS England page to `context` with a receipt.
- Receipts (§11.7): `claim_map.metadata.cited_sources` with names and statuses, queries, totals, seconds; no model reasons; quick, frozen and failure write a `skip` receipt. Claim-map metadata survives mapping (mapping mutates in place).
- Lane items skip the scorer and pass classify, distil, capture and every scope gate.
- Async: the names task never raises except on cancellation; the follow step is wrapped so a fault cannot fail the check; finished searches survive the 30 s deadline; `done` task exceptions are retrieved, so no "exception never retrieved" warnings.
- Flags: `ENABLE_CITED_SOURCE_LANE` default False; `FLAGS.md` regenerated and the register test passes.
