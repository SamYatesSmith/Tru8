# Cited-source gap note (Build B): independent verification (2026-10-06)

**Verifier:** a fresh agent that did not build it. Nothing was fixed or committed.
**Scope:** the uncommitted Build B diff (`cited_source.py`, `runner.py`, `re_search.py`, `config.py`, `tier_limitations.py`, `shared/types`, `evidence-coverage.ts`, `SeekerView`, `UnknownsSummaryStrip`, `ClaimSummaryPanel`, the new `CitedSourceGaps.tsx`, and 3 new test files). Checked against design §6, §11.8, §12.1, §12.2, §12.6, §§14–17.

## Verdict: PASS WITH FIXES

- **Flags off:** behaviour is byte-identical to before.
- **Lane-on:** behaviour is unchanged after the seam refactor.
- **Note on, lane off:** makes no search or fetch call.
- **Re-search:** recomputes with no model call.
- **Frontend:** the wording is exactly as specified on both hosts.
- **Tests:** they bite. 21 of 23 mutants were killed, and the 2 survivors are runner-argument gaps.
- **Open:** two MEDIUM findings. In both, the note can tell a reader "that source is not in this record" when the record shows it. Each needs a fix or a founder decision before the flag is turned on.

## What was verified (evidence)

**1. Flags off.**
- `start_names` returns `None` when `names_wanted()` is false.
- `after_post_filter`: both branches are false, so it does nothing.
- `finish_gap_note` returns on its first line.
- `stage_timings` is untouched.
- `limitations_for_tier` adds nothing.
- `recompute_missing` only touches a claim map that already has `missing`.
- Test `test_both_flags_off_start_no_task_and_write_no_field` passes.

**1b. Lane on: the refactor matches the old inline code branch for branch.**
- Old: `_cs_on = enabled() and evidence and not frozen and quick-off` → follow, else `elif enabled() and evidence` → skip with `frozen_replay`/`quick_tier`.
- New (`cited_source.py:1014`, `:1036`): the task is gated by `names_wanted()` and the same conditions; `follow_for_check` runs only if `names_task and enabled()`; the skip happens only if `names_task is None and names_wanted() and evidence`.
- With the note off, `names_wanted() == enabled()`, so the two are identical.
- Unchanged:
  - the try/except/finally around `follow_for_check`;
  - the `skip("failed")`;
  - the cancel of an unfinished task;
  - `stage_timings["cited_source"]`;
  - the `source_url` exclusion, which is passed through unchanged;
  - the 30 s deadline (inside `follow_names`).
- **Can it fail a check?** `finish_gap_note` is wrapped in try/except at `runner.py:2966` (cancellation is re-raised). `after_post_filter` keeps the lane's own catch.

**2. Note on, lane off.**
- The fake search and fetch are never called (`no_network == {"names":1,"search":0,"extract":0}`).
- The names are awaited at the end (bounded at name timeout + 5 s) and recorded with `follow: "off"`.
- `missing` is then written after coverage recovery and the B3 receipts. The source-order pin is `runner.py:2010 < 2585 < receipts < 2967`.

**3. Presence (§12.2).**
- `missing_cited_sources` → `already_present`: the host must pass `host_identifies` and the stored text must pass `carries_claim`.
- An item with no `text_provenance` never counts.
- `excluded` never counts.
- **Deviation 1, "unmapped counts as shown": agreed.** The Evidence lens lists unmapped sources in their own group. "Not in this record" about a listed source would be false. This is the right reading of "SHOWN (not excluded)". The same reasoning is what MEDIUM-1 and MEDIUM-2 below rest on.

**4. Re-search.**
- `recompute_missing` runs on `existing + candidates`.
- It reuses the stored names. A name call is wired to raise in the test, and it does not.
- It returns `False` without creating `missing` when the run wrote none.
- The baseline is the DB claim map (snake_case `cited_sources`) and `Evidence.model_dump` (snake_case `text_provenance`). The keys line up.
- `map_evidence_to_elements` mutates `metadata` in place, so the field survives.

**5. Frontend.**
- **Counter:** every Gaps counter goes through `evidenceCoverage`:
  - `ClaimSummaryPanel:123` passes `citedSourceGaps(claimMap)`;
  - `SeekerView:79`, spread into `UnknownsSummaryStrip`;
  - `CoverageMap` reads only `withEvidence`, which is correct;
  - `seeker-honesty` is updated.
- **Wording:** exact:
  - the row: `Sources here attribute this to {name} ("{cue}"); that source is not in this record.`;
  - the heading: "Cited but not in this record";
  - the all-covered line: "one cited original is" / "two cited originals are".
- **Hosts:** `/r/` (`public-report-client.tsx:484`) and the dashboard (`check-detail-client.tsx:626`) both render `SeekerView`. The test covers both.
- **Phone layout:** `break-words`, with no truncate, line-clamp or `title`.
- **No verdict:** neutral zinc styling, and no "searched", "not found" or verdict words.
- **Deviation 5** (the all-covered state depends on the elements only): agreed. It matches §11.8's sentence for the case where a note exists.

## Findings

### MEDIUM-1: the note says "not in this record" while the body's own page is shown
**Where:**
- `cited_source.py:414-427` (`already_present` → `stored_text`, `:180`);
- `runner.py` coverage recovery (`2585`–`2890`), which never captures `text_provenance`;
- `capture_text_provenance` only runs before classify (`runner.py:2002`, `2188`), and recovery items are neither captured nor distilled.

**What is wrong:** §12.2 says a snippet-only item never makes a body present. That rule was written for the lane: do not skip a search because a useless page is pooled. Applied to the note, it produces a false sentence.

**Scenario:**
1. `www.bloomberg.com/graphics/…` is pooled, but the fetch returns 403 (paywall), so the item is the search snippet only.
2. It is shown in the Evidence lens.
3. The Gaps lens says: *"Sources here attribute this to Bloomberg ("a new Bloomberg analysis finds…"); that source is not in this record."*

The same happens to any original that coverage recovery brings in. Recovery items get no `text_provenance`, so **running the note "after coverage recovery" can never clear a note**: the timing the builder cites has no effect. Paywalled originals (Bloomberg, Telegraph, FT) are exactly the bodies this note names.

**Fix (founder or spec call):** any one of these:
- (a) For the note only, a shown host-identified item counts as present when its stored text OR its snippet carries the claim.
- (b) Capture provenance on coverage-recovery items before the note runs.
- (c) Reword the row to "…that source's page is not readable in this record". Option (a) is the smallest.

### MEDIUM-2: presence is per claim, but URLs are deduplicated across claims
**Where:** `cited_source.py:1097` (`(evidence or {}).get(pos)`), against cross-claim URL dedup at `runner.py:1865` (invariant #1).

**What is wrong:** a URL lives in only one claim's pool.

**Scenario:**
1. An article check has two claims.
2. The Bloomberg original was pooled under claim 0.
3. Claim 1's copies also cite Bloomberg.
4. Claim 1's Gaps lens says the source "is not in this record", while it is listed on the same report under claim 0.

**Fix:** test the host against the shown items of ALL claims, and the content (`carries_claim`) against this claim's text. Alternatively, reword the row to "not among this claim's sources".

### LOW-1: a failed name call writes `missing: []`, not "no field" (deviation 5 and §17 are inaccurate)
**Where:** `name_cited_sources` catches every model failure itself (`cited_source.py:657-665`), so `finish_gap_note` takes the success path and writes `missing: []`, with `totals.status = "failed"`. The quick-tier and frozen-replay skips also write `missing: []`.

**Proof:** a scratch probe with a model call that raises printed:

`{'names': [], 'queries': [], 'totals': {'items': 1, 'status': 'failed', ..., 'follow': 'off'}, 'missing': []}`

**What the test covers:** `test_a_failed_name_task_means_no_note_and_no_failed_check` makes `name_cited_sources_default` itself raise. Production never takes that path for a model failure.

**Effect:** nothing is visible to the user. But `missing: []` cannot be told apart from "every cited original is present" by any consumer that reads the field alone.

**Fix:** write `missing` only when `totals.status == "ok"` and there is no skip `detail`, or correct §17.

### LOW-2: the runner's quick/frozen arguments to `start_names` are untested
Mutants R1 (`quick=False`) and R2 (`frozen=False`) at `runner.py:2010` both **survive**. The seam tests call `start_names` directly.

**Fix:** a source pin, in the style of the existing order test, asserting `frozen=_is_frozen_evidence_replay` and `quick=config.mode == "quick"`.

### LOW-3: "Adjacent investigations" is now hidden when only a note exists
`SeekerView.tsx:90` makes `hasUnknowns` include `citedMissing`. That gates the explore fetch and the panel (`:232`) while the all-covered state still shows. This behaviour change is not in the spec. It is minor, but it should be decided rather than left as a side effect.

### LOW-4: an elementless claim with a note gives a dead link
`ClaimSummaryPanel.tsx:270` can read "1 gap — open the Gaps lens", but `SeekerView.tsx:138` returns "No elements available" before `CitedSourceGaps` (`:193`) renders. This is an edge case: it needs a claim whose decomposition yielded 0 elements.

### LOW-5: a cue can come from an item excluded later
`select_items` does not filter on `receipt_status`. Relevance exclusions are removed from `evidence[pos]` earlier, so they are safe. A later classifier exclusion (arXiv smell, `evidence_classifier.py:1031`) can still be the citing item. "Sources here attribute this…" then quotes a source the reader cannot find. This is rare. The fix is to drop names whose citing item ends up excluded.

### LOW-6 (known, declared in §17): orphaned task and missing telemetry
- The gap-note-only names task is orphaned if the check fails mid-run.
- That path records no `stage_timings["cited_source"]` and no tokens in `by_stage`.

## Mutant table
Every mutant was applied, run and restored by script. The backend ran `test_cited_source.py` + `test_cited_source_gap_note.py`; the web ran `cited-source-gaps`, `seeker-honesty` and `ClaimSummaryPanel.coverage`.

| # | Mutant | Result | Killing test |
|---|---|---|---|
| M1 | presence: every name reported missing | KILLED | `test_present_when_the_bodys_own_host_carries_the_claim` |
| M2 | presence: excluded items count | KILLED | `test_excluded_items_do_not_count` |
| M3 | presence: host identity dropped | KILLED | `test_cited_source.py::test_a_copy_carrying_the_figure_is_not_the_original` |
| M4 | re-search recompute call removed | KILLED | `test_research_that_finds_the_original_clears_the_note` |
| M5 | runner skips `finish_gap_note` | KILLED | `test_runner_wires_the_seam_and_decides_the_note_after_recovery_and_receipts` |
| M6 | lane-off path calls search (`enabled()` → `names_wanted()`) | KILLED | `test_gap_note_alone_names_without_searching_and_writes_missing` |
| M7 | `finish_gap_note` ignores its flag | KILLED | `test_lane_on_without_the_note_is_unchanged` |
| M8 | `start_names` ignores quick tier | KILLED | `test_gap_note_skips_replay_and_quick_with_a_receipt[quick_tier]` |
| M9 | `accepted_names` drops `already_present`/`over_query_cap` | KILLED | `test_accepted_names_reads_every_guard_passing_status` |
| M10 | `recompute_missing` creates the field | KILLED | `test_recompute_never_adds_a_note_the_run_did_not_write` |
| M11 | re-search recomputes on `existing` only | KILLED | `test_research_that_finds_the_original_clears_the_note` |
| M12 | name dedup removed | KILLED | `test_names_are_deduplicated_case_insensitively` |
| M14 | quick/frozen skip receipt dropped | KILLED | `test_gap_note_skips_replay_and_quick_with_a_receipt[frozen_replay]` |
| M15 | lane-on: note path re-awaits the names | KILLED | `test_lane_and_note_together_follow_then_note` |
| R1 | runner passes `quick=False` to `start_names` | **SURVIVED** | none (LOW-2) |
| R2 | runner passes `frozen=False` to `start_names` | **SURVIVED** | none (LOW-2) |
| F1 | `gaps` ignores cited entries | KILLED | 4 tests in `cited-source-gaps.test.tsx` |
| F2 | `SeekerView` drops `<CitedSourceGaps>` | KILLED | 4 tests |
| F3 | plural phrase always singular | KILLED | "pluralises for more than one" (both hosts) |
| F4 | summary panel ignores cited entries | KILLED | "counts the cited original in the Gaps link" |
| F5 | all-covered hidden when a note exists | KILLED | 4 tests |
| F6 | row drops the cue | KILLED | "lists each cited original… verbatim" (both hosts) |
| F7 | `citedSourceGaps` keeps malformed entries | KILLED | "reads only well-formed entries" |

(M13 was not applied: the pattern did not match, and it was superseded by LOW-1's probe.)

**Restoration check:**
- Before and after the mutants, `git diff | sha256sum` = `74970dff656b1029f2b7a09ad4d8c58ec5a0bd6146389985c4dc3b71fb1352fe`.
- The four untracked files' sha256 values are unchanged:
  - `test_cited_source_gap_note.py` `e1c5b25f…`
  - `test_cited_source_gap_note_payload.py` `84dd2724…`
  - `CitedSourceGaps.tsx` `a8fe6ada…`
  - `cited-source-gaps.test.tsx` `cfffaafb…`

The tree is at the builder's state.

## Test output (exact lines)
- `python -m pytest tests/unit/pipeline/test_cited_source.py tests/unit/pipeline/test_cited_source_gap_note.py -q --no-cov` → `110 passed, 210 warnings in 2.35s`
- `python -m pytest tests/integration/test_cited_source_gap_note_payload.py -q --no-cov` (Docker Postgres and Redis) → `1 passed, 210 warnings in 2.55s`
- Flag-register tests (`-k "flag_register or flags_md or FLAGS"`) → `13 passed, 4878 deselected` (`FLAGS.md` is current).
- `npx tsc --noEmit` → no output (clean).
- `npx vitest run` → `Test Files  39 passed (39)` · `Tests  249 passed (249)`

No paid call was made: no live LLM, search or check.

---

## Re-verification (2026-10-06, round 2)

**Scope:** the builder's fixes in `cited_source.py`, `re_search.py`, `research_operations.py` (newly touched), `SeekerView.tsx` and the three test files. I re-read the diff, re-ran every mutant against the new code, added one mutant per fix, and ran a scratch end-to-end probe through the real `name_cited_sources_default`. Only the Gemini call was faked. Nothing was fixed or committed, and no paid call was made.

### Final verdict: PASS
Every earlier finding is closed, with evidence below. Two test gaps remain, both LOW (R2-LOW-1 and R2-LOW-2). Neither is a code defect. Both are worth closing before the flag is turned on.

### Each claim checked
- **MEDIUM-1, closed.**
  - **The new rule:** for the note, a body counts as present when ANY shown item in the record has a host that identifies it (`cited_source.py:476`). Stored text is no longer required.
  - **The lane is unchanged:** its `already_present` is untouched (`test_the_lane_keeps_its_stricter_content_test`).
  - **Probe:** a snippet-only, unmapped `bloomberg.com` item under another claim gives `missing: []`.
  - **The trade-off, accepted:** any shown page on the body's host now suppresses the note, even an unrelated one. That is the fail-closed direction: fewer notes, and never a false "not in this record".
- **MEDIUM-2, closed in all three places:**
  - **The runner:** `record_items_of(evidence)` (`:1133`) covers every claim. The `_excluded` bucket is filtered out by `_shown`.
  - **Re-search:** `recompute_missing(updated, existing + candidates, record + candidates)`.
  - **Strengthen:** builds `record_evidence` from every baseline claim (`research_operations.py:294`).
- **The `research_operations.py` change cannot alter the baseline hash or the committed snapshot:**
  - `{**claim, "record_evidence": …}` is a new dict. The list holds references to the baseline evidence dicts, which are only read.
  - `research_claim` deep-copies `claimMap`, copies `existing` items with `{**e}`, and `recompute_missing` only reads the record items.
  - `commit_result` takes the hash from `capture_report(session, check)`, which reads the DB, and compares it with the stored `op.baseline_hash`. Both the `before` and the `after` snapshots also come from the DB.
  - `record_evidence` is never put on the claim map that gets committed.
  - Empirically, an in-place mutant (X-M2d, which writes `record_evidence` into the baseline dict itself) still passes the hash comparison in the integration test. That shows even a careless edit here could not move the hash.
- **LOW-1, closed.** `note_decidable` (`:494`) writes `missing` only when `totals.status` is `ok` or `no_attributions` and no skip `detail` is present. `test_a_failed_model_call_writes_no_missing` goes through the real `name_cited_sources_default`, faking only the Gemini call (raises, times out, invalid). The quick and frozen skips now write no `missing`.
- **LOW-2, closed.** `test_runner_passes_the_real_tier_and_replay_to_both_seam_calls` kills R1 and R2.
- **LOW-3, closed.** `hasUnknowns` is element-only again (`SeekerView.tsx:90`), so the explore fetch and panel behave as before the build. The test "LOW-3: a note never hides Adjacent investigations" passes.
- **LOW-4, closed.** The elementless branch renders `<CitedSourceGaps>` (`:147`). Tested on both hosts.
- **LOW-5, closed.**
  - Receipts now carry `citing_id` (`:685`).
  - A name is dropped unless its citing item is shown in this claim.
  - The end-to-end probe confirms production receipts carry it (`['ev-1']`) and that the note is written.

### Remaining findings
- **R2-LOW-1: nothing pins `citing_id` on the receipts.**
  - Mutant X-L5b removes `"citing_id"` from the accepted receipt at `cited_source.py:685`, and it **survives**. The runner-seam tests use a fixture that fabricates receipts which already carry `citing_id`.
  - In production, that one-line regression would drop every name (`None` is never a shown id), so the note would silently never appear.
  - Fix: assert `citing_id` on the receipts that `validate_names` returns, or route one seam test through the real `name_cited_sources` (as the LOW-1 test already does) and assert `missing` is non-empty.
- **R2-LOW-2: the baseline-immutability assertion tests nothing.**
  - `test_cited_source_gap_note_payload.py:95` checks `op.baseline` on the object `admit()` returned, not the one `execute_operation` loads. Mutant X-M2d, which mutates the baseline in place, survives.
  - The code is correct (it uses a shallow copy), and the hash is safe either way (see above). The test should either be fixed or have its claim dropped.

### Round-2 mutant table
All run by script, each reverted immediately. The backend ran `test_cited_source.py`, `test_cited_source_gap_note.py` and the payload integration file; the web ran the three coverage/gap test files.

| # | Mutant | Result |
|---|---|---|
| M1 | presence: every name missing | KILLED (9 tests) |
| M2 | excluded items count | KILLED |
| M3 | any host counts as present | KILLED (7) |
| M4 | re-search recompute removed | KILLED |
| M5 | runner skips `finish_gap_note` | KILLED |
| M6 | lane-off path calls search | KILLED |
| M7 | finish ignores its flag | KILLED |
| M8 | `start_names` ignores quick | KILLED |
| M9 | `accepted_names` narrowed | KILLED |
| M10 | recompute creates the field | KILLED |
| M11 | re-search record omits candidates | KILLED |
| M12 | dedup removed | KILLED |
| M14 | skip receipts dropped | KILLED |
| M15 | lane-on note re-awaits names | KILLED |
| R1 | runner `quick=False` | KILLED (was SURVIVED) |
| R2 | runner `frozen=False` | KILLED (was SURVIVED) |
| X-M1 | note requires stored text again | KILLED |
| X-M2a | runner uses a per-claim record | KILLED |
| X-M2b | re-search uses a per-claim record | KILLED |
| X-M2c | strengthen passes no `record_evidence` | KILLED (integration) |
| X-M2d | strengthen mutates the baseline in place | **SURVIVED** (R2-LOW-2; hash unaffected) |
| X-L1 | `note_decidable` always true | KILLED |
| X-L1b | skip `detail` ignored | KILLED |
| X-L5a | citing-item check removed | KILLED |
| X-L5b | `citing_id` removed from receipts | **SURVIVED** (R2-LOW-1) |
| X-L5c | citing ids not limited to shown | KILLED |
| X-L3 | note hides explore again | KILLED |
| X-L4 | elementless branch drops the note | KILLED |
| F1 | `gaps` ignores cited entries | KILLED |
| F5 | all-covered hidden when a note exists | KILLED |

**Restoration check:**
- `git diff | sha256sum` = `1374efcf0b16baf1008f8014b39b899e0d7547fa4dd1e937f213be46f65e5e24` both before and after the mutants.
- The untracked files are unchanged:
  - `test_cited_source_gap_note.py` `6bec2b4f…`
  - payload test `6bdfca21…`
  - `CitedSourceGaps.tsx` `a8fe6ada…`
  - web test `d528c0e5…`

### Round-2 test output (exact lines)
- Unit (`test_cited_source.py` + `test_cited_source_gap_note.py`): `122 passed, 210 warnings in 2.28s`
- Integration (`test_cited_source_gap_note_payload.py` + `test_research_operations.py`, Docker Postgres and Redis): `14 passed, 210 warnings in 18.54s`
- `npx tsc --noEmit`: exit 0, no output
- `npx vitest run`: `Test Files  39 passed (39)` · `Tests  252 passed (252)`
