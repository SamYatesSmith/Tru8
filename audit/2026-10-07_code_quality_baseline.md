# Code quality baseline (2026-10-07)

Read-only measurement before the clean-up. No code changed. Raw tool output was kept in the session scratchpad; re-run the commands below to regenerate it.

## Commands
```
cd backend
python -m ruff check app tru8_mcp main.py scripts --select E,F,W,B,SIM,C90,UP,PL --statistics --exit-zero
python -m vulture app tru8_mcp main.py --min-confidence 60
python -m radon cc app tru8_mcp main.py -s -n D      # complexity grade D or worse
python -m radon mi app -s -n C                      # maintainability index grade C
cd ../web
npx knip@5 --reporter compact ; npx next lint ; npx tsc --noEmit
```

## Headline
- **Backend:** 71,488 lines across 178 files. Average complexity B (5.9), which hides a bad tail: **68 functions graded D–F**, 12 of them F.
- **Web:** clean on ESLint and `tsc`. knip finds 19 unused files and 34 unused exports or types.
- **The backend is the problem.** The four pipeline files hold the worst of it.

## 1. Complexity: the worst functions (radon cyclomatic complexity, F = 41+)
| Function | File | CC |
|---|---|---|
| `run_pipeline_phase2` | runner.py | **252** |
| `_review_run` | relationship_scope_review.py | 85 |
| `_armed_scope_gates` | claim_map_analyzer.py | 65 |
| `run_pipeline_phase1` | runner.py | 65 |
| `_derive_element_state_with_authority` | claim_map_analyzer.py | 57 |
| `_retrieve_evidence_for_single_claim` | retrieve.py | 55 |
| `_execute_planned_queries` | retrieve.py | 55 |
| `_complete_unmapped_sources` | claim_map_analyzer.py | 48 |
| `_retrieve_from_government_apis` | retrieve.py | 46 |
| `save_check_results_async` | runner.py | 44 |
| `plan_queries_batch` | query_planner.py | 44 |
| `_inject_mechanical_secondaries` | — | 41 |

Grade counts: D 43 · E 13 · F 12.

**Maintainability index grade C** (the lowest grade; 0.00 means off the bottom of the scale): `claim_map_analyzer.py`, `runner.py`, `retrieve.py`, `checks.py`, `cited_source.py` (0.00); `extract.py` 2.9; `economic.py` 8.3; `echo_link_confirmation.py` 8.9.

**Largest files:** claim_map_analyzer 4,231 · runner 3,690 · retrieve 3,318 · checks.py 3,161 · agent.py 1,838 · extract 1,761.

## 2. Lint (ruff), by real significance
- **Signs of real problems:** 137 over-complex functions (C901) · 79 too-many-branches · 65 too-many-statements · 62 `raise` without `from` (tracebacks lose their cause) · 9 bare `except:` · 29 `global` statements · 144 function calls in default arguments (B008; mostly FastAPI `Depends`, so largely benign).
- **Dead or unused at line level:** 107 unused imports · 12 unused variables · 30 f-strings with no placeholders · 3 redefinitions (`settings` in checks.py, `re` in retrieve.py, `json` in tru8_mcp/tools.py).
- **Undefined names (F821, 5):** string forward references in models (`"User"`, `"Check"`), which are harmless, and `"AgentTransaction"` in agent.py, used as an annotation without an import (type-checking only, not a runtime fault).
- **Noise, auto-fixable:** 3,042 old-style type annotations (UP006/UP045) · 1,433 long lines · 527 imports inside functions (often deliberate, to avoid import cycles).

## 3. Dead code (vulture at 60%, routes and Pydantic fields filtered out by hand)
Vulture cannot see FastAPI routes, MCP tools or decorated handlers, so every route in its list is a false positive. What remains looks really dead (**each must be confirmed with a repo-wide grep, including tests and scripts, before deletion**):
- **Whole modules:** `factcheck_parser.py` (474), `source_monitor.py` (226). Imported only by their own tests.
- **Uncalled:**
  - `cache.py`: ~14 helpers (`get_or_set`, `cache_search_results`, `cache_url_content`, `cache_pipeline_result`, `invalidate_pattern`, `get_cache_stats`, `cleanup`, `cache_api_response`, `cache_result` …).
  - `embeddings.py`: `rank_evidence_by_similarity`, `compute_claim_evidence_similarity_matrix`, `calculate_semantic_similarity`.
  - `push_notifications.py`: three senders. `email_notifications.py`: `send_check_completed_email`, `send_check_failed_email`.
  - `government_api_client.py`: `_filter_results_by_relevance` (121 lines), `get_api_info`, `health_check`.
  - `payments/credit_provider.py`: `CreditPaymentProvider`, `check_credit_balance`. `verify_and_charge` is unused on all three providers.
  - `climate.py`: `_search_datasets`, `_create_climate_evidence`.
  - `rhetorical_analyzer.py`, `source_type_classifier.py`, `domain_status_tracker.py`: several unused methods each.
  - Single functions: `runner.run_in_executor_with_timeout`, `corroboration.annotate_derivation_chains`, `article_classifier.classify_article_sync`, `evidence_payload.evidence_for_mapping`, `query_planner.get_freshness_for_claim_type`, `temporal.filter_evidence_by_time`, `deduplication._domain_dedup`, `watchdog.supervise_re_search_task` (imported in checks.py but never called), `core.logging.clear_log_file` / `get_log_file_path`, `tracing.instrument_database`, two unused exception classes.
  - **Possibly test-only helpers** (kept for tests, not production): `jurisdiction_scope.is_out_of_jurisdiction`, `temporal_scope.is_out_of_period`, `evaluative_heads.has_evaluative_head`, `url_identity.same_url`, `tier_limitations.undeclared_reductions`. Decide per item: a test that guards a production function stays; a helper that exists only for its own test goes.
  - **Unused API schemas:** `AgentClaimCompact`, `AgentCacheMiss`, `VerifyFailureResponse`, `ResearchStartResponse`, `ResearchStatusResponse`, `SelectClaimsResponse`.
- **Plus the default-off features from the architecture review:** passage mapping (~620), structured extraction (~120), the cited-source search half (~550).
- **Debug-only routes in production code:** `checks.py` has three `/test/*` endpoints (~280 lines), 404 unless `DEBUG`. They are not exposed, but they are clutter in the largest API file. Delete unless a script uses them.

## 4. Web (knip)
- **Unused files (19):** six dashboard graphics (`compass`, `prism`, `tree`, `justice-scales`, `glowing-border-card`, `time-sensitive-indicator`), the whole `components/claim-map/` folder (the Track C components, superseded), two auth wrappers, three marketing components (`code-disclosure`, `copy-code-button`, `screenshot-lightbox` + css), `lib/usage-utils.ts`.
- **Unused dependencies:** `dagre`, `yet-another-react-lightbox`, `@types/dagre`, `@testing-library/user-event`. (`react-dom`, `eslint` and `@tru8/shared` are false positives: Next and the lint script use them.)
- **Unused exports (20) and types (14):** mostly barrel `index.ts` re-exports nobody imports through.

## 5. Structural faults no tool scores (from the architecture review)
- The "save receipts → rebuild basis → restore → re-derive state" sequence is copied **5 times**, and state is derived from 6 call sites.
- 14 separate source-independence mechanisms with no shared identity model.
- Five correctness defects in coverage recovery (D1–D5).
- Rule overlap between the gates and the model review (period/place/measure, figures, absence of evidence, count-once, self-interest).

## Progress (2026-10-07)
**Verification protocol used for every deletion:** a repo-wide reference search (app, scripts, tests, web, mobile, shared) plus an AST import graph of every `app` module; decorators checked (a Pydantic validator looked dead to vulture and was kept); the unit suite's pass count must drop by exactly the deleted tests; the flags-off bench must equal a **control arm** (the same bench on the pre-change commit `93029ab`, run in a separate worktree).

| Commit | What | Suite | Bench |
|---|---|---|---|
| `4bb0609` | 4 dead modules (`factcheck_parser`, `source_monitor`, `rhetorical_analyzer`, `source_type_classifier`) + 37 zero-reference functions | 4,863 → 4,808 (−55 = the 4 deleted test files) | 121/14/15/2, identical to control claim by claim |
| `c629a1e` | Web: 19 unused files, 4 unused packages | vitest 252/252, tsc/lint clean, `next build` OK, `npm ci` OK (Docker + CI forms) | n/a |
| `60cc71c` | 12 test-only helpers (incl. the never-constructed `CreditPaymentProvider`) + `supervise_re_search_task` (superseded 2026-09-08 by `research_operations`' own ceiling) | 4,808 → 4,775 (−33 = exactly the removed tests) | identical to control |

**Bench note:** `--all` today gives 121 ok / 14 warn / 15 fail / 2 unexercised, with timing drift on 93DD and B4A3 as well as 82CF. Each replays clean alone (93DD 14/1/2, B4A3 17/3/0), and the pre-change control shows identical drift counts. The README's 152/18/15 figure is not what `--all` produces on this machine today.

**Kept deliberately:** `UnknownSource` model (its table exists; removing the model needs a migration decision), test-facing wrappers that pin live gate logic (`is_out_of_period`, `is_out_of_jurisdiction`, `has_evaluative_head`), drift guards (`undeclared_reductions`), test-support helpers (`force_open`, `reset_all`, `reset_cache_metrics`, `inflight_count`), `evidence_for_mapping` (round-trip contract in 4 test files), the `cache.invalidate_pattern` the bench uses.

| `031e4bf` | Cited-source search lane (failed eval, never on); gap note kept | 4,775 → 4,739 (−36 removed cases) | identical to control |
| `2fb6308` | 6 unused API schemas | unchanged | n/a (no runtime reference) |
| `db4b9a0` | 3 DEBUG-only `/checks/test/*` routes | unchanged | n/a (routes only) |
| `d5c190d` | Passage mapping + structured extraction (plan, review, verification) | 4,739 → 4,632 (−109 removed, +2 restored legacy-reader tests) | identical to control |

**Not yet done:** Build B legacy readers (needs a production read), stale `web/package-lock.json` (Docker and CI both resolve the root workspace lock; CI only uses it as a cache key).

## Proposed order
1. **Delete dead code** (sections 3 and 4), one commit per area, each confirmed by grep, unit suite and flags-off bench equal.
2. **Mechanical lint** (unused imports and variables, redefinitions, bare `except`, `raise … from`). Hold the 3,000 annotation rewrites; they churn every file for no behaviour gain.
3. **Structure:** one receipt/state function replacing the 5 copies; split `run_pipeline_phase2` and `_armed_scope_gates`; fix D1–D5.
4. Re-run this baseline after each step and record the deltas here.
