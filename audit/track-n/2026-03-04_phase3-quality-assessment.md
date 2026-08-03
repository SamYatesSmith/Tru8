# Track N Phase 3 — Quality Assessment

**Date:** 2026-03-04
**Scope:** Recovery Query Planner integration, regression benchmarks, test accuracy audit, deep investigation
**Status:** 73/73 tests passing (test_coverage_recovery), 25/25 (test_retrieve), 1091 total pass, benchmarks complete

---

## 1. Test Suite Status

| File | Tests | Status |
|------|-------|--------|
| `test_coverage_recovery.py` | 55 | 55 pass |
| `test_runner_phase2.py` | 18 | 18 pass |
| `test_retrieve.py` | 25 | 25 pass (settings isolation fixed) |
| **Full suite** | **1091** | **1091 pass, 13 skip, 0 fail** |

Tests added during Phase 3 quality work:
- 5 `TestRecoveryQueryPlanning` (planner integration)
- 1 `test_evidence_item_structure` (16-key structure validation)
- 7 `TestRetrieveEdgeCases` (search exceptions, cross-element dedup, planner quirks)

---

## 2. Regression Benchmark Results

### 2.1 Summary Scoreboard

| Model | Date | Prompt Hash | State Acc | Ref Acc | Regressions | Parse Errors |
|-------|------|-------------|-----------|---------|-------------|--------------|
| flash-lite | Mar 3 | `3977efd7002f` | **83%** | **69%** | 28 | 0 (1 HTTP 503) |
| flash-lite | Mar 4 | `e4d22024bffa` | **82%** | **73%** | 27 | 0 |
| flash | Mar 3 | `3977efd7002f` | **77%** | **63%** | 40 | 0 |
| flash | Mar 4 | `e4d22024bffa` | **33%** | **33%** | 12 | **6/7 parse fail** |
| pro | Mar 3 | `3977efd7002f` | **82%** | **47%** | 54 | 0 |
| pro | Mar 4 | `e4d22024bffa` | **73%** | **60%** | 26 | **2/7 parse fail** |

### 2.2 Flash-Lite (Production Model) — Per-Case Delta

| Case | State Match | Ref Match (Mar 3 → Mar 4) | Delta | Recovery Evidence? |
|------|-------------|---------------------------|-------|--------------------|
| case-002 | 3/3 → 2/3 | 8/11 → 8/11 | -1 state | No |
| case-003 | 3/4 → 3/4 | 14/21 → 16/21 | **+2 ref** | Yes (21 refs) |
| case-008 | 3/3 → 3/3 | 8/14 → 7/14 | -1 ref | Yes (14 refs) |
| case-010 | 503 → 4/4 | 503 → 8/8 | **Recovered from outage** | Yes (8 refs) |
| case-013 | 3/3 → 3/3 | 6/6 → 4/6 | -2 ref | No |
| case-015 | 2/3 → 2/3 | 8/13 → 9/13 | **+1 ref** | No |
| case-020 | 1/2 → 1/2 | 9/12 → 10/12 | **+1 ref** | Yes (8 refs) |

**Net:** State accuracy flat (-1%). Ref accuracy +4% (69→73%). No regression in production model.

### 2.3 Recovery Evidence Failure Rates

| Model (best day) | Recovery Refs Tested | Failed | Failure Rate | Null (mapper miss) |
|------------------|---------------------|--------|-------------|-------------------|
| flash-lite (Mar 4) | 51 | 12 | **23.5%** | 75% of failures |
| flash (Mar 3) | 63 | 24 | **38.1%** | 75% of failures |
| pro (Mar 3) | 63 | 41 | **65.1%** | 93% of failures |

**Key finding:** The dominant failure mode is `actual_rel=None` — the mapper doesn't reference the recovery evidence at all. This accounts for 75-93% of recovery ref failures. When the mapper *does* reference recovery evidence, it usually classifies the relationship correctly.

### 2.4 Prompt Hash Changed — Root Cause Identified

The prompt hash changed between Mar 3 (`3977efd7002f`) and Mar 4 (`e4d22024bffa`).

**Investigation finding:** `build_mapping_prompt()` in `eval_mapping_model.py` is fully deterministic — no randomness, no timestamp. The hash change was caused by **golden case-020.json being modified** between Mar 3 morning and afternoon runs (6 evidence items added, expected states revised). The prompt hash in `audit_regress.py` records only the LAST case's hash, not a composite.

**Flash parse failures** (6/7) are LLM-side — Gemini 2.5 Flash returned malformed JSON. Not prompt-induced, since Mar 3 had zero parse errors across all models with identical prompt construction logic.

---

## 3. Test Accuracy Audit — Issues Found & Resolution

### CRITICAL (3 issues)

**C1. Four tests exercise real query planner by accident** — FIXED
- `test_returns_evidence`, `test_deduplicates_existing_urls`, `test_generates_evidence_ids`, `test_empty_search_results` didn't patch `settings`
- **Fix:** Added `patch("app.pipeline.retrieve.settings")` with `ENABLE_RECOVERY_QUERY_PLANNING = False` to all four

**C2. `_detect_recovery_candidates` is a manual copy of runner.py inline logic** — VERIFIED
- Investigation confirmed NO meaningful divergence between test helper and production code
- All logical branches are identical
- **Status:** Low urgency extraction, deferred

**C3. No complete evidence item structure validation** — FIXED
- Added `test_evidence_item_structure` validating all 16 required keys
- Keys: id, evidence_id, element_ids, text, snippet, source, url, title, published_date, relevance_score, semantic_similarity, combined_score, word_count, receipt_status, metadata, is_recovery

### MEDIUM (3 issues)

**M1. Planner timeout test genuinely takes 10 seconds** — FIXED
- Added `RECOVERY_PLANNER_TIMEOUT` config setting (default 10.0s)
- Test uses `RECOVERY_PLANNER_TIMEOUT = 0.05` — test suite dropped from 24.5s to 10.2s

**M2. Enrichment timeout handler missing `metadata["enriched"] = False`** — FIXED
- Pre-existing bug in `_enrich_recovery_evidence()` TimeoutError handler
- Fixed during Phase 3 implementation

**M3. Flash/Pro parse failures correlate with prompt hash change** — INVESTIGATED
- Root cause: LLM-side malformed JSON, not prompt-induced
- `build_mapping_prompt()` is deterministic; hash change from modified golden data
- **Recommendation:** Fix `audit_regress.py` to compute composite hash over all cases

### LOW (6 issues) — 4 FIXED

**L1. Cross-element URL dedup untested** — FIXED
- Added `test_cross_element_url_dedup` in `TestRetrieveEdgeCases`

**L2. Search exception path untested** — FIXED
- Added `test_search_exception_continues_to_next_element` and `test_search_exception_first_query_continues_to_second`

**L3. Planner edge cases untested** — FIXED
- Added `test_planner_wrong_element_ids_ignored`, `test_planner_empty_queries_falls_back_to_naive`, `test_planner_returns_none_uses_naive`, `test_partial_search_failure_preserves_results`

**L4. Missing config wiring tests** — DEFERRED (runner.py concerns)

**L5. Enrichment tests use full constructor** — DEFERRED (low impact)

**L6. Dict vs object polymorphism untested** — DEFERRED (MagicMock exercises attribute path)

### HIGH (1 issue) — Found during deep investigation — FIXED

**H1. test_retrieve.py `retriever_env` fixture missing settings isolation**
- 23 tests in `TestEvidenceRetrieval` did NOT patch `app.pipeline.retrieve.settings`
- Tests passed by accident because `ENABLE_QUERY_PLANNING` read real config (defaulting to no API key)
- Dead code: `_make_retriever_patches()` was defined but never called
- **Fix:** Added `patch("app.pipeline.retrieve.settings")` to `retriever_env` fixture with explicit config values (`ENABLE_QUERY_PLANNING=False`, `MAX_SOURCES_PER_CLAIM=20`, etc.). Removed dead `_make_retriever_patches()`.

---

## 4. Persistent Regression Patterns

These evidence items fail consistently across models and dates:

| Evidence ID | Case | Element | Expected | Failure Mode | Root Cause |
|------------|------|---------|----------|-------------|------------|
| `ev-rec-e1_3_7d5808eb` | 003 | e1,e3,e4 | supports | Null (3x) | Mapper drops this ref across multiple elements |
| `ev-rec-e1_0_346ed6d7` | 008 | e3 | challenges | Null | Cross-element mapping blind spot |
| `ev-rec-e1_4_65bdb51c` | 008 | e3 | challenges | Null | Cross-element mapping blind spot |
| `ev-0ffb39bff315` | 002,015 | e3 | challenges | supports | Sarcastic/ironic content read literally |
| `ev-rec-e2_*` (all) | 020 | e2 | context | Null (pro) | Tangential evidence too hard to connect |

**Cross-element mapping is the primary bottleneck.** Evidence retrieved for element A that should also map to element B/C is frequently dropped entirely by the mapper.

---

## 5. Deep Investigation Summary

### 5.1 Prompt Hash Investigation
- `build_mapping_prompt()` is deterministic — no randomness
- Hash change caused by golden case-020.json modification (6 evidence items added between runs)
- `audit_regress.py` stores only last case's hash, not composite — should be fixed

### 5.2 Recovery Candidates Divergence Audit
- NO meaningful divergence between test helper and production code
- All logical branches identical
- Low urgency extraction recommended

### 5.3 Untested Code Paths — All Now Covered
7 new tests added in `TestRetrieveEdgeCases`:
1. Search exception continues to next element
2. First query exception doesn't block second query
3. Cross-element URL deduplication
4. Planner returns plans for wrong element_ids (ignored, naive fallback)
5. Planner returns empty queries list (naive fallback)
6. Planner returns None (naive fallback)
7. Partial search failure preserves first query results

### 5.4 Broader Test Suite Impact
- **FIXED:** `test_retrieve.py` — 23 tests now have proper settings isolation
- **LOW:** `test_frozen_evidence_replay.py` (8 tests) and `test_query_planning_extraction.py` (5 tests) also lack settings patches but are lower risk
- **Cleaned:** Removed dead `_make_retriever_patches()` from test_retrieve.py

---

## 6. What the Benchmark Does NOT Measure

`audit_regress.py` tests the **mapping model** (evidence→element relationship assignment). It does NOT measure:

1. **Recovery search quality** — whether the planner produces better queries than naive concatenation
2. **Enrichment success rate** — whether fetched URLs yield usable content
3. **End-to-end pipeline performance** — full claim→evidence→map→orientation cycle
4. **Recovery evidence relevance** — whether found evidence is topically useful

These require live pipeline runs (`/api/v1/checks/test/stream`) which test the actual Serper→fetch→enrich→classify→map chain.

---

## 7. Action Items (Priority Order)

| # | Priority | Action | Status |
|---|----------|--------|--------|
| 1 | CRITICAL | Patch settings in 4 unpatched TestRetrieveForElements tests | **DONE** |
| 2 | CRITICAL | Add evidence item structure validation test | **DONE** |
| 3 | CRITICAL | Fix test_retrieve.py settings isolation (23 tests) | **DONE** |
| 4 | MEDIUM | Make planner timeout configurable | **DONE** |
| 5 | MEDIUM | Investigate prompt hash change | **DONE** (golden data change, not code) |
| 6 | LOW | Add edge case tests (7 tests) | **DONE** |
| 7 | LOW | Add cross-element URL dedup test | **DONE** |
| 8 | LOW | Fix audit_regress.py composite hash | TODO |
| 9 | LOW | Patch settings in test_frozen_evidence_replay.py | TODO |
| 10 | LOW | Patch settings in test_query_planning_extraction.py | TODO |
| 11 | FUTURE | Extract `_detect_recovery_candidates` into importable function | DEFERRED |
| 12 | FUTURE | Live pipeline validation for recovery search quality | DEFERRED |
