# Tru8 — Engineering Context

## What This Is
AI-powered evidence research platform. Users submit a URL or claim, the pipeline extracts claims, retrieves evidence from the open web and ~22 specialist APIs, and presents an organised evidence landscape via six profession views. Mission: "We organise; you decide."

## Track Status (2026-03-09)

| Track | Status | Summary |
|-------|--------|---------|
| A | COMPLETE | Infrastructure cleanup. Commit `041b55f`. |
| B | COMPLETE | Backend pivot — Claim Map system. Commit `d40668b`. Contract: `audit/track-b/2026-02-12_claim-map-contract.md` |
| C | COMPLETE | Frontend verdict→ClaimMap swap. Commit `b365534`. |
| D | COMPLETE | Full frontend dark→light redesign (10 PRs, all 17 pages). Commit `1df7569`. |
| E | COMPLETE | Evidence philosophy overhaul (15 PRs). Editorial scoring deleted, tier/type classification, receipts, pipeline break, 4 evidence views. |
| F | COMPLETE | Copy overhaul + differentiation features (Chronologist, Diagnostic Highlighter, Auto-Archiving, URL persistence). |
| G | COMPLETE | The Seeker (known unknowns) + Re-search mechanism. |
| H API | COMPLETE | Agent API (8 PRs), MCP server, dual auth, webhooks, snapshot mode, sync `/run` endpoint. |
| H NAV | COMPLETE | Unified check detail — single page, state-driven claim focus. Commit `6403227`. |
| I | IN PROGRESS | Pre-release readiness. Subs LIVE in production (`SUBSCRIPTIONS_ENABLED=True` deployed long ago — confirmed 2026-05-01; I-03/I-04 closed). I-07 MCP publication DONE — **`tru8-mcp` 1.0.3 on PyPI** (1.0.0/1.0.1/1.0.2 **YANKED 2026-08-04**: they declared `mcp>=1.0.0`, and mcp 2.0.0 removed `mcp.server.fastmcp`, so every `pip install` died on ImportError **while listed on the registry**). **✅ OFFICIAL MCP REGISTRY** — `io.github.SamYatesSmith/tru8` **v1.0.3**, `isLatest`, status `active`. **✅ REMOTE MCP SERVER LIVE 2026-08-04 — `POST https://api.trueight.com/mcp`** (streamable HTTP mounted on the API; same tools, no install). `server.json` had five faults that would each have failed the publish (namespace pointed at `tru8.io`, a domain that does not exist; `registryType: "pip"`; version 1.0.0 vs PyPI 1.0.2; a 312-char description against a **server-side 100 limit** invisible to the JSON schema). **Always run `mcp-publisher validate <path>` — it catches what the schema cannot.** **2026-08-05 pre-Smithery hardening (`6e36136`, live-verified 15/15):** the endpoint was unusable from **any browser** — `mcp-session-id` was in neither `allow_headers` nor `expose_headers`, so no browser client could hold a session from any origin, our own included (Smithery playground, MCP Inspector). Fixed via `app/middleware/mcp_cors.py`, scoped to `/mcp` alone. Also fixed: the served discovery card claimed `io.tru8/mcp-server` (a namespace on a domain we do not own — the same invention that broke the first publish) at a stale 1.0.0, and a missing key told hosted callers to set an env var they cannot set. **✅ SMITHERY LIVE 2026-08-05 — `samyatessmith/tru8`, scan reports 3 tools.** It first reported *"No capabilities found"*: the SDK holds a session `NotInitialized` until the client sends `notifications/initialized`, and Smithery's scanner goes straight from initialize to listing, so every list method returned `-32602`. Fixed with `stateless_http` (`a8534a4`), which also had to state `transport_security` explicitly — FastMCP auto-enables DNS-rebinding protection with a **localhost-only** allowlist whenever `host` is the default `127.0.0.1`, so the next rebuild would have returned **421 on api.trueight.com and 403 to browser origins** with nothing in the diff to explain it. The residual `triggers/list` warning is expected: `triggers` is not an MCP method, so the SDK rejects it as unknown — every server on the official Python SDK does this. Config on their side: one parameter, `apiKey`, type string, location **query**, required — the server reads `apiKey` off the query string (`tru8_mcp/server.py:66-72`), which is how their gateway passes config; no `apiUrl`, since on the hosted route the server IS api.trueight.com. `smithery.yaml` + `Dockerfile.mcp` remain valid for the container route but are not used by it. Remaining: I-06 OG cards visual review, **`server.json` declares no `remotes[]`** so the registry advertises only the pip route (schema supports it; needs a version bump, likely a 1.0.4 PyPI release too — founder call), mcp.so + PulseMCP (they index FROM the official registry — wait ~2 weeks before submitting manually). See `audit/track-i/PROGRESS.md`. |
| J | COMPLETE | Test suite overhaul — 0 failures, +87 new tests. Commit `a5ed52d`. |
| K | COMPLETE | Endpoint + efficacy testing. 1,092 tests collected. Commit `14371cf` + subsequent. |
| L | COMPLETE | Agent Commerce Gateway — 3 tiers (Lookup/Quick/Full), 3 payment rails (x402/Skyfire/credits), `/agent/` endpoints, MCP tier tool. Deployment-only items remain (Stripe credit packs, PyPI publish). |
| M | COMPLETE (⚠️ M-06 was DEAD until 2026-08-04) | Evidence Infrastructure — M-01 provenance, M-02 gap enrichment + provider status, M-03 smart endpoint, M-04 manifest signing + verify endpoint, M-05 jurisdiction routing, M-06 convergence layer + consensus tier, M-07 tests (+54). **⚠️ M-06 NEVER RAN IN PRODUCTION until `dc61c0f`:** `ClaimConsensus` was missing from `app/models/__init__.py`, and `entrypoint.sh` bootstraps a fresh DB with `create_all` (exported models only) then `alembic stamp head` — so the table was never created AND `m06_claim_consensus` was permanently stamped past. Every `/agent` quick|full call raised `UndefinedTableError`, which `agent.py` swallowed at DEBUG **without rollback**, poisoning the session so the credit debit died with `InFailedSQLTransactionError` — a 500 whose Sentry trace accused billing. Consensus returned a tidy `hit: false` throughout, so **no user ever received one**. **✅ CONFIRMED FIXED IN PRODUCTION 2026-08-05**, all three layers checked rather than assumed: an authenticated `quick` check returned `chargedPence: 7` (**the charge is the proof, not the evidence** — the old failure killed the credit debit), `alembic current` → `claim_consensus_repair (head)`, and `to_regclass('public.claim_consensus')` confirms the table. ⚠️ **A passing request alone would NOT have proved the table exists** — a missing table throws, rolls back cleanly and returns the identical response. **0 rows is correct, not a second bug:** the batch (`main.py:98`, daily 02:00 UTC) needs **≥3 distinct users** on completed `full`-tier checks of one claim hash (`consensus.py:69-87`) — an empty table is a demand signal. Deployment items remain (signing key). |
| Quality-first package (2026-08-14→20) | A/B/C COMPLETE · **D ABANDONED** · E OPEN | A bench observability, B state behaviour (strict `>` ties, `FACTUAL_MIN_WEIGHTED_SUPPORT=3`, echo_scope gate), C claimant end-to-end + revived `seen_urls` fallback — all shipped `1ff7cc4`. **D (rebuttal retrieval) was built, measured and DELETED 2026-08-20:** four query mechanisms (counter-frame wording ×2, independent-platform `site:` targeting, claimant-anchoring) scored **0/3** on the claims that motivated it. A rebuttal is published later, on a smaller domain, in its author's framing — search ranks by authority and word-match, so it is structurally last. **This is a discovery problem, not a phrasing problem; do not re-attempt a query-side fix.** ⚠️ Any commentary-sourced lane is a sycophancy hazard by arithmetic (commentary weight 1, support floor 3 → a ceiling of 3 lets a lane badge an element `supported` alone; ceiling must be 2). Only live thread: claimant-anchoring reached **rank 1** and was blocked by `linkedin.com` being on the runtime blocklist — a link-resolution build, not a query build, and Phase C already ships the `claimant` field. Record: `audit/2026-08-20_independent_source_lane_design_review.md` §9. E = re-grade the four outreach records, then send. |
| N | COMPLETE | Mapping quality — 9 PQ items (PQ-01→PQ-09). Model upgrade (Flash Thinking), snippet 1000 chars, basis metadata, orientation reframe, adapter rebuild, heuristic classifier 93.7%, content_basis, question inputs. Register: `audit/PIPELINE_QUALITY_DISCUSSION.md`. |

## Where the reasoning lives (changed 2026-07-27)
`audit/` is now **TRACKED** (`a003759`) — 50 live docs including `audit/OPEN_WORK.md` (single
source of truth for what is open NOW; edit it FIRST on every ship) and
`audit/DECOUPLING_STATE.md` (SOT for the decoupling track). It was gitignored since
inception, so design reasoning never travelled with the commits it explained. Still
untracked by choice: `audit/_archive/` (230 retired docs — history, never resurrect as a live
plan) and the outreach contact map (third-party personal data).

## Build & Test Commands

```bash
# Backend
cd backend
uvicorn main:app --reload                        # API server (port 8000) — module is main:app, NOT app.main (start-backend.sh / entrypoint.sh)
pytest tests/ -q --no-cov                        # All tests (3,517 pass, 66 skip, ~85s as of 2026-08-17)
# Redis + Postgres must be up or ~26 cache/perf tests fail on connection refused, not on logic.
pytest tests/unit/pipeline/ -v                   # Pipeline unit tests
pytest tests/integration/ -v                     # Integration tests
alembic upgrade head                             # Run migrations

# Replay bench — run before EVERY pipeline-quality commit (replay itself is free; ~10 min)
docker-compose up -d                             # REQUIRED: the bench writes a Check row
python scripts/replay_bench.py --all             # expect exactly: 175 ok / 10 warn / 2 fail (2026-08-17)
# ⚠️ THE BENCH CANNOT VERIFY SMALL RETRIEVAL CHANGES (measured 2026-08-20). Two
# recordings of TRU-018F-44AA taken an hour apart with IDENTICAL settings differed
# by 25 of 40 URLs — 62% churn — and their tier mixes disagreed wildly
# (primary 2 vs 4, commentary 4 vs 16). Anything worth ~3 fetch slots is INVISIBLE
# in that noise, and reading a single before/after pair as a regression is how two
# false conclusions were drawn in one day. **Run a control arm (same settings,
# twice) before attributing any pool change to your edit.** For a retrieval idea,
# the honest test is to issue the query and read the results — pence, seconds, and
# it answers directly. See audit/2026-08-20_independent_source_lane_design_review.md.
# The 2 fails are accepted: TRU-82CF-2F81 KNOWN-FLAKY (timing-dependent fetch queue) and
# TRU-A3E8-3199 factual_weight_share 0.0 (record-time pool drift). 10 claims since
# TRU-018F-44AA joined 2026-08-17. Full pass-state history: tests/replay_corpus/README.md.
# ⚠️ The bench runs against the WORKING TREE: any uncommitted PROMPT change makes every
# claim fail on cassette_drift, because request signatures are cassette keys — the held
# reframe must be patched out first (protocol in audit/OPEN_WORK.md START HERE).
# Anything worse is a real regression. Do NOT make missed evidence fetches non-fatal to
# reach a clean sweep: it weakens the drift guard corpus-wide.

# Web
cd web
npm run dev                                      # Dev server (port 3000)
npm run build && npm run start                   # Production build

# Infrastructure
docker-compose up -d                             # Postgres, Redis, Qdrant, MinIO
```

## ⏳ DEADLINE — Gemini 2.5 retires 16 October 2026; EVERY primary stage is on it
`GOOGLE_LLM_MODEL=gemini-2.5-flash-lite` + `MAPPING_GOOGLE_MODEL=gemini-2.5-flash` both retire
(https://ai.google.dev/gemini-api/docs/deprecations). **Not a model-string swap:** thinking
cannot be fully disabled on any Gemini 3 model (our `MAPPING_THINKING_BUDGET=0` has no
successor), a lone `thinkingBudget` is a **hard 400** on 3.x so every mapping call breaks the
day the string changes (`google_ai.py:333` needs a `thinking_level` branch in the same commit),
and `temperature` is advised removed. Verified live 2026-08-01 — the flat
`responseMimeType`/`responseSchema` we send **does** still work on 3.x, so structured output
needs no work. Candidates `gpt-5.6-luna` / `gemini-3.5-flash-lite` (NOT `3.1-flash-lite` — it
retires 7 May 2027). Every Gemini path raises cost; Google's own recommendation is 3.65×.
Full record + what is owed: `audit/OPEN_WORK.md` 2026-08-01.

## LLM providers — Google is PRIMARY, OpenAI is the FALLBACK
**Most** LLM stages try Google Gemini first and fall back to OpenAI only if the primary is
absent, errors, or times out. Verify in code, never infer: `query_planner.py` (*"Try Google
first, then OpenAI as fallback"*), `claim_map_analyzer.py:1797` (*"Fall back to OpenAI"*),
`evidence_classifier.py:838` (same), `claim_selector.py`, `relevance_scorer.py:648`.
⚠️ **"Every" was wrong — two stages are GOOGLE-ONLY with no fallback at all** (audited
2026-08-01): `evidence_distiller.py` (only import is `call_google_ai_with_usage`, `:19` — and it
is the pipeline's *largest* consumer, ~60% of counted input tokens and its slowest stage at
~63s) and `extract.py:1125` claim synthesis (whose fallback is a string concat, not a model).
`GOOGLE_AI_API_KEY` is the key that matters; `ANTHROPIC_API_KEY` is deprecated (`config.py:59`).

A dead `OPENAI_API_KEY` therefore does **not** stop the pipeline — it removes the safety net.
Do not read "the local OpenAI key is dead" as "there is no working local LLM key": the local
`GOOGLE_AI_API_KEY` is set. Anything claiming otherwise is stale and should be corrected in
place, not worked around.

## Pipeline Architecture (post-Track N)

Two-phase pipeline with user claim selection gate:

```
Phase 1 (0-30%):
  INGEST (10%)        → Fetch URL / OCR / transcript
  EXTRACT (20%)       → LLM atomises into ≤12 claims (questions accepted via implicit claim extraction). Opinion decoupling LIVE 2026-07-23 (`ENABLE_OPINION_REFRAME` default True): main-predicate evaluative claims are KEPT affirmative in the author's direction + hinted `normative` (Rule 6 exception), never dropped. Attributed/reported stances stay plain claims. Known: hint boundary noisy both directions (P13 under-fire / P18 over-fire — see `audit/2026-07-23_decoupling_live_test_plan.md`)
  SELECT/RANK (28%)   → Article classification + claim ranking
  [PAUSE]             → waiting_for_selection (ALL input modes — text checks pause too; verified live 2026-07-06)

Phase 2 (30-100%):
  FACTCHECK (35%)     → Google Fact-Check API lookup
  DECOMPOSE (45%)     → Claim → 1-5 elements (LLM call); each element tagged with scope_flags {geographic,universal} — mechanical scope-sensitivity tagger, F3 Phase A 2026-07-07 (app/utils/scope_sensitivity.py). Normative-hinted claims (flag ON): elements rebuilt as NEUTRAL open questions by the grounds stage (`opinion_symmetry.apply_grounds_stage` — value-predicate lock, on-subject, structural coverage; balance lives in retrieval+mapping, never forced route symmetry). **Elements are ATOMIC as of Phase 3a (`2d77e7b`, 2026-07-29, `ENABLE_ELEMENT_ATOMICITY` default True):** an element asking two questions at once was graded by whichever half the mapper read — and the trivially-satisfiable enumerative half ("What were the stated targets?") badged the whole element `supported` while the half bearing on the claim ("...and were they met?") went unchecked. Measured at **21.2% of grounds elements, 13.8% mixed-shape** before the fix; 0.0% after. A mechanical detector (`app/utils/atomicity.py` — splits only on a coordinator followed by a second interrogative head, so conjoined noun phrases like "efficacy and evidence base" stay ONE question) triggers a repair call that **rewrites 1→1, never splits** — splitting would blow the 5-element contract and drop the trailing, judgement-bearing conjunct. Repair runs **BEFORE the value-predicate lock** (a rewrite can collapse into the judgement itself). Design: `audit/2026-07-29_element_atomicity_design.md`. SOT: `audit/DECOUPLING_STATE.md`
  RETRIEVE (60%)      → **Per-element as of Phase 2 (`36d3f4e`, 2026-07-27) — it genuinely was NOT before.** For months this line described an intent: `retrieve.py` read `claim["elements"]`, decompose wrote `claim["claim_map"]["elements"]`, nothing wrote the key it read, so the planner got the raw claim text as ONE synthetic element on EVERY check (prod-proved: `1 element plans for 1 claims` on a 4-element claim, 3 Serper calls). Worst effect — for an opinion claim the claim text IS the judgement, so the pool was gathered by searching its own valence ("success metrics" for "was a triumph"): invariant #7 breached at pool constitution. **Now:** each claim gets a CLAIM lane (`c0` — the old synthetic element, kept so the factual path is unchanged) + one lane per Claim Map element (≤5). Claim lane ≤3 queries incl. class-targeted `site:` variants (claim-lane only); element lanes ≤2 each → **13 queries/claim full, 6 quick, ≤65/check**. Fetch cap unchanged (40); claim lane keeps 13 results/query, element lanes 5; the 40 fetch slots are allocated by **weighted round-robin, claim lane 2:1** — a plain slice starves the last lanes. F1-D3 hedge applies per lane (each lane's 2nd query unwindowed unless planner chose pd/pw); two-year claims get both years anchored — F1-D1. Re-search (`re_search.py`) supplies its own single element and is deliberately unwired — no claim lane. Rollback `ENABLE_ELEMENT_RETRIEVAL=False`. Design: `audit/2026-07-27_phase2_element_retrieval_build_design.md`. **Build A (2026-09-02, `ENABLE_CLAIM_LANE_UNWINDOWED_TWIN` default True): the claim lane's LEAD query gets a freshness=`none` twin at lane position 1** (fixed depth 10, fetch weight 1, excluded from the lead's depth divisor; `query_twin_of` parallel array; pd/pw exempt like F1-D3). Why: the F1-D3 hedge unwindows a lane's SECOND query and the claim lane had one, so **the claim's own words never ran without the inherited window** — with `pm` Google returned only blocklisted social links and the lane contributed nothing; the TTE critic then appeared on one run (`11f54993`) and not the next (`b0398fca`). Unwindowed, the plain claim text finds the TTE and Scotland rebuttals at rank 3 (`audit/2026-09-02_dissent_discovery_probe.md`). Design: `audit/2026-09-02_claim_lane_unwindowed_twin_design.md`. ⚠️ Re-keys every wired corpus cassette — bench re-record owed. **Piece 3 (2026-09-02): the per-claim evidence cache key carries `RETRIEVAL_CACHE_VERSION` (24 h TTL; 1 h for pd/pw claims) — BUMP IT IN THE SAME COMMIT as any change to what retrieval gathers, or repeated claims keep the old pool for a day and any re-run inside the window is a replay (`web_search=0` in the metrics line is the tell).** **LIVE-VERIFIED 2026-07-28** (`wired=True` 3/3, Grenfell matches baseline) after `7bc670a` fixed a live failure in which the planner omitted the `c0` plan on 3/3 checks and the per-lane sizing silently never ran. **"Add, don't replace" is SETTLED (founder, 2026-07-29 — D3 closed, no build):** the user's claim MUST be searched *and* the decoupled elements must also be searched and be relevant to their line of enquiry, so the full context is grasped and relayed. Do not re-open it, and never remove the claim lane in the name of criterion 17 — the valence query already fell from the whole pool to 1 of 13 queries / 8 of 40 fetch slots, and balance lives in the element lanes beside it. ✅ **F7 re-gold DONE 2026-07-30** (`f6fd038`) — cassettes were all dead (query strings are cassette keys); re-derived, and the goldens are the proof this stage improved quality rather than merely changing it: **primary-tier evidence rose on every corpus claim** (2→10, 6→11, 7→11, 4→9, 0→4, 1→3) while reporting/commentary fell by roughly the same amount. Substitution, not a bigger pool.
  SCORE (65%)         → LLM topical relevance scoring (1-5 scale, max 50 items)
  CLASSIFY (75%)      → Tier/Type classification (batched LLM + heuristic fallback). Post-classify (needs tiers): mechanical derivation annotation writes per-element basis sourcing notes — echo (a primary re-reported by ≥2 derivatives), F4 repetition (≥3 non-primary sources reciting the same wording across ≥2 ownership groups with NO primary anchor — sentence-shingle, `corroboration.annotate_repetition_clusters`, 2026-07-07), thin (commentary-only / single-outlet). Surfaced as grey no-verdict notes (dashboard + `/r/`); a flagged element is toppable via "Strengthen this claim". Parity-locked `support_structure.py` ↔ `support-structure.ts`
  MAP (85%)           → Evidence → element mapping + state assignment (Gemini 2.5 Flash, 1000-char snippets; thinking OFF in prod via MAPPING_THINKING_BUDGET=0 — sweep-verified equal-or-better quality at −64-74% latency, 2026-07-02). Mapper also emits per-element scope_caveat (evidence's narrower reach) — F3-B2
                        **SIX mechanical scope gates share ONE driver as of 2026-08-17** (`_apply_scope_gates` ← `_armed_scope_gates`, over an `_index_evidence` cache built once per claim): temporal · jurisdiction · measure (2026-08-06) · interested-party · recital (2026-08-13, TRU-018F-44AA) · echo (2026-08-17, Shape B — a derivative of an original already counted on the same side; `ENABLE_ECHO_SCOPE_GATE`). Each re-labels a directional ref to `context` — never deletes — BEFORE the state is derived, and writes a receipt into the element `basis`. All six are **symmetric** (`supports` scoped exactly as `challenges`). ⚠️ **Three invariants live only in tests, not in the code's shape: gate ORDER is behaviour** (temporal FIRST, echo LAST — the ordering holds the corpus tolerance-0 assertions: `temporal_scoped_refs` on 0005, recital/interested-party pins on 018F), **one gate owns a reference** (the `break`; remove it and an exclusion double-counts in two receipts), **and a new gate must join `_SCOPE_RECEIPT_KEYS`** or both post-mapping merge paths silently drop its receipts. (1) **temporal** — a different period, below. (2) **jurisdiction** (`945f2d1`, `ENABLE_JURISDICTION_SCOPE_GATE`, `app/utils/jurisdiction_scope.py`) — a national OFFICIAL source of another country cannot support/challenge a country-scoped claim; prod check `757f02c2` had the **Irish CSO** disputing a true UK CPI claim and **the snippet never says "Ireland" — only the domain does**, so no prompt could comply. Never fires on foreign PRESS, never on supranational bodies (World Bank/IMF/OECD/Eurostat are deliberately absent), never when the item's text names the claim's jurisdiction. Reads `claim_map["metadata"]["jurisdiction"]`, written by `runner.attach_claim_jurisdiction`. (3) **measure** (`182e194`, `ENABLE_MEASURE_SCOPE_GATE`, `temporal_scope.interval_ends`) — a rate of change is identified by its interval's **END**: "between September 2024 and September 2025" is not "the twelve months to September 2024" even though both name September 2024, which is why the period rule correctly declines and why a **UK** source making the same error needed its own gate. Design: `audit/2026-08-06_jurisdiction_scope_gate.md`, `audit/2026-08-06_f1_temporal_gate_extension.md`
                        **Temporal scope gate (F1, `656618b`, `ENABLE_TEMPORAL_SCOPE_GATE` default True):** where an element pins ONE month-level period and an evidence item asserts periods of which none match, the relationship is re-labelled `context` — never deleted — BEFORE the state is derived, with a receipt in `basis.temporal_scope`. **Symmetric: scopes `supports` as readily as `challenges`**, because a source about June bears on September in neither direction and a gate that only removed challenges would be a sycophancy mechanism. Prod check `618efbc4` returned a TRUE, ONS-sourced "UK CPI below 2% in September 2024" as `disputed` on June/May/annual-2024 figures; `MAPPING_PROMPT` already forbade that, but the evidence payload carries no date in any form, so the rule was unaskable (NF-11). ✅ **Both known gaps CLOSED 2026-08-06 (`eca56c6`):** two-digit/delimited years (`September-25`, and `September-2025` — the separator had required whitespace) now parse, and a **bare month resolves against `published_date`** behind three guards — a `date_basis` allowlist (`url_inferred_suspect` refused by name), a required temporal preposition, and required capitalisation (the preposition alone admits "began to march"). That inferring half has its **own** flag, `ENABLE_TEMPORAL_PUBLICATION_RESOLUTION`, so it rolls back without taking the lexical half. ⚠️ **It fires on corpus `TRU-C1A0-0005` but has NEVER fired on a live check (3 attempts, 45p)** — and that corpus claim guards the GATE, not the extension (mutation-checked: it still passes with both 2026-08-06 halves disabled). ⚠️ `page_metadata` dates are sometimes badly wrong (a CSO *September 2025* release dated `2026-04-21`) yet sit on the trust allowlist; if mis-scoping appears in the wild, tighten the allowlist rather than adding a prompt rule. See `audit/2026-08-06_f1_temporal_gate_extension.md`
  ORIENTATION         → Mechanical derivation from element states (no LLM) + orientation_basis + F3 scope caveats in state_derivation.caveat (neutral channel): universal ("only/first" cannot be established, tier-gated — F3-B1) + reach ("evidence covers X, narrower than Y", LLM∧tagger-gated — F3-B2). State never changes; describes evidential limit, never adjudicates
                        **Grounds-routed (opinion) claims: prose orientation SUPPRESSED (`None`) — Phase 1 `007cf5c`.** Summing elements DERIVED FROM an opinion reads as a verdict on it (invariant #7, witnessed both directions). Single decision point `apply_orientation()`; `orientation_basis` still ALWAYS computed (it is in the manifest canonical payload — signing unaffected). Frontend must render NOTHING there — shared `web/lib/orientation.ts::isOrientationSuppressed`, 4 surfaces. Also `GROUNDS_MIN_WEIGHTED_SUPPORT=3`: a question-shaped element badged `supported` off one thin source now reads `unresolved` and reaches the Seeker. **Factual claims gained their own floor 2026-08-17 (`FACTUAL_MIN_WEIGHTED_SUPPORT=3`, rule `support_floor`):** one primary alone still suffices; a lone reporting/commentary ref reads `unresolved` — and the dominant rules are strict `>` both sides (an exact 2× tie is `close_split` → `disputed`)
  QUERY (90%)         → Optional search clarity
  COMPLETE (100%)

Stage 5.1: COVERAGE RECOVERY → Targeted retrieval for low-coverage claims (cross-element mapping)

Parallel tasks (fire-and-forget):
  - Video recommendations (YouTube API, max 5/claim)
  - Auto-archiving (Wayback Machine, ~15 req/min)
```

## Reliability guarantees (2026-07-23 — a check always ends honestly, never hangs)
Two incident classes closed in one day (design doc `audit/2026-07-23_hang_proofing_design.md`):
- **PDF memory guards** (`df0095f`): evidence `.pdf` downloads capped at 20MB (content-length precheck + mid-stream cap, skip logged) and pypdf parses serialised module-wide (`pdf_evidence.py` semaphore of 1) — one 7.8MB treaty PDF measured ~600MB RSS and concurrent parses under the shared 25-slot fetch semaphore OOM-killed the container (SIGKILL = no exception, no Sentry, stranded row, CORS-less proxy errors in the browser).
- **Hang-proofing** (`c7b4d4d`): ONE owner of a pipeline task's lifetime — the task itself; streams report, never control. W1 task-level watchdog on all 6 task sites (`app/core/watchdog.py`; `PIPELINE_WATCHDOG_SECONDS=300` / `RESEARCH_WATCHDOG_SECONDS=150`; breach → existing `handle_pipeline_failure` fail+refund, then re-raise so streams never announce "completed" for a failed check; re-search breach terminates the Redis status, parent check stays completed). W2 boot-time stale sweep (`inflight.sweep_stale_checks`, lifespan startup; `check.processing_started_at` column ages paused-then-resumed article checks correctly; excludes `waiting_for_selection`) — OOM strandings self-heal on next boot. W3 `progress.events()` stream bound is connection-only (the old branch cancelled the pipeline AND claimed a refund it never made — defect D3, dead). W4 frontend 45s calm stall notice.
Worst case for a user: failed honestly, credit returned, told plainly.

## Six Views (labels are actions, not professions — user-facing since D-R1)

| Tab | Question | Level | Source |
|------|----------|-------|--------|
| MAP (cartographer) | Shape of the conversation? | Overview + Detail | Dagre cascade layout |
| EVIDENCE (librarian) | Full set, clearly labelled? | Overview + Detail | Tier×Type heatmap + ledger + receipts |
| COMPARE (compare) | Where do two sources differ? | Detail only | **Replaced SOURCES/correspondent 2026-08-26** — user picks two shown sources, ONE model call returns summaryA/summaryB/divergence + a mechanical collision table computed on READ from evidence_refs (never stored). Budget 3/check +1 per re-search; the `claim_comparison` row count IS the spend. Design: `audit/2026-08-26_compare_tab_design.md`. ⚠️ `?view=correspondent` deep links translate to librarian WITH a notice in both hosts |
| VIDEO (projectionist) | What's said on camera? | Overview + Detail | YouTube video cards |
| TIMELINE (chronologist) | When did evidence appear? | Overview + Detail | Pure SVG timeline |
| GAPS (seeker) | What don't we know? | Detail only | Unknowns ledger + bounty text + re-search |

Cross-cutting: Diagnostic Value Highlighter (ACH toggle on Cartographer + Librarian), URL-persisted view state (`?view=`), auto-archive links. COMPARE hides itself (<2 shown sources anywhere; no stored comparisons on `/r/`) — absent, not disabled, like VIDEO.

## Key Files

### Backend — Pipeline
| File | Purpose |
|------|---------|
| `backend/app/pipeline/runner.py` | Two-phase orchestrator + coverage recovery + quick mode config |
| `backend/app/pipeline/retrieve.py` | Element-level retrieval + filter cascade |
| `backend/app/pipeline/claim_map_analyzer.py` | Decompose + map + derive orientation + basis metadata |
| `backend/app/pipeline/evidence_classifier.py` | Tier/Type classification (batched LLM + heuristic, 93.7% accuracy) |
| `backend/app/pipeline/relevance_scorer.py` | Topical relevance scoring (no source authority) |
| `backend/app/pipeline/claim_selector.py` | Article mode claim ranking |
| `backend/app/pipeline/re_search.py` | Targeted element re-query (Seeker) |
| `backend/app/utils/temporal_scope.py` | Temporal-scope tagger (F1) — pure lexical period extraction, no LLM. Fires only when the element pins one month-level period AND the evidence states periods none of which match; **undated evidence is left alone on purpose** (inferring a period from silence over-fires and hides genuine disputes) |

### Backend — Models & API
| File | Purpose |
|------|---------|
| `backend/app/models/claim_map.py` | ClaimMap types + enums (includes basis, orientation_basis) |
| `backend/app/models/check.py` | DB schema (Evidence has tier, type, receipt_status, content_basis, archived_url, provenance fields; Check has manifest JSONB + `client` first-party-attribution column) |
| `backend/app/models/agent_transaction.py` | Agent transaction model (5 statuses, idempotency) |
| `backend/app/models/usage_event.py` | `usage_events` ledger — SINGLE SOURCE OF TRUTH for dashboard credits (2026-07-10). Append-only: +1 per check/re-search/top-up, -1 refund; all entitlement gates + meters sum it. Legacy counters (User.credits/total_credits_used, Check.credits_used) dual-written for API back-compat only — no gate reads them |
| `backend/app/models/claim_consensus.py` | ClaimConsensus model (k≥3 cross-user consensus, stability classification) |
| `backend/app/api/v1/checks.py` | API endpoints (dual auth, computed analytics, snapshot mode) |
| `backend/app/api/v1/agent.py` | Agent Commerce Gateway (lookup/consensus/quick/full/check endpoints) |
| `backend/app/api/v1/verify.py` | Public manifest verification endpoint (`GET /verify/{check_id}`) |
| `backend/app/api/v1/response_builder.py` | Shared response builder (agent + dashboard, landscape schema) |
| `backend/app/api/v1/api_keys.py` | API key management |
| `backend/app/api/v1/webhooks.py` | Webhook completion notifications |

### Backend — Services
| File | Purpose |
|------|---------|
| `backend/app/services/wayback_archive.py` | Auto-archiving service |
| `backend/app/services/lifecycle_emails.py` | Funnel emails (welcome on first arrival, trial-exhausted on the 3rd check). Eligibility + exactly-once claiming (`UPDATE ... WHERE marker IS NULL`) + off-loop dispatch. Reuses `get_usage_snapshot` — never re-derive the trial limit. Design: `audit/2026-08-04_funnel_lifecycle_emails_design.md` |
| `backend/app/services/video_recommendations.py` | YouTube video provider |
| `backend/app/services/computed_analytics.py` | Computed analytics + freshness |
| `backend/app/services/consensus.py` | Convergence layer — daily batch consensus computation |
| `backend/app/core/manifest_signer.py` | HMAC-SHA256 manifest signing, canonical payload, pipeline fingerprint |
| `backend/app/services/payments/` | PaymentProvider ABC, credit + Skyfire providers |
| `backend/app/services/usage_ledger.py` | Ledger gate/debit/refund: `enforce_usage_limit` (FOR UPDATE row lock → gate+debit atomic), `record_usage`, `refund_usage` (mirrors `drew_trial` — subscriber refunds never mint trial credits). Re-searches/top-ups COUNT against the plan (1 credit/run); debit commits BEFORE background work fires. Design: `audit/2026-07-10_usage_ledger_design.md` |
| `backend/app/core/agent_auth.py` | Agent auth + concurrency limits |
| `backend/app/core/client_origin.py` | `resolve_client(request)` — normalises `X-Tru8-Client` header (e.g. `mcp/1.0.2` → `mcp`) onto `Check.client` for first-party usage attribution |
| `backend/app/core/agent_pricing.py` | Agent pricing (lookup $0.02, consensus $0.03, quick $0.07, full $0.15) |
| `backend/app/core/tier_limitations.py` | **Single source of truth for `_meta.limitations`, derived from the config diff** (`aa91888`). The hand-written list declared 6 omissions while `QUICK_CONFIG` disabled 10, and was duplicated in `agent_x402.py`. Disabling a stage without declaring it now fails a drift guard. Cache/lookup/result paths must pass `Check.executed_tier` — a caller asking for `full` can be served a cached `quick` analysis, and used to be told `limitations: []` |
| `backend/app/middleware/x402_audit.py` | x402 payment middleware |
| `backend/tru8_mcp/server.py` | MCP server — 3 tools: `tru8_check`, `tru8_get_result`, `tru8_get_result_raw`. Thin HTTP client over `/agent/*` + `/checks/*`; inherits pipeline upgrades automatically. Sends `X-Tru8-Client: mcp/<version>`. **TWO TRANSPORTS off ONE instance (2026-08-04):** stdio via the published `tru8-mcp` PyPI package, and **streamable HTTP mounted at `POST /mcp` on the API** (`main.py`). ⚠️ Credentials resolve **PER REQUEST** (`_get_client()`) — the old module-level client singleton was a credential-crossing bug the moment one process served two callers. Never cache it. Guard: `tests/unit/test_mcp_request_auth.py`. |
| `backend/app/middleware/mcp_cors.py` | CORS for `/mcp` ONLY (2026-08-05). The app-level policy is right for the Clerk-authenticated API and wrong for a public protocol endpoint: it rejected `mcp-session-id` as a request header and never exposed it, so **no browser MCP client could hold a session — from any origin, including ours** (Smithery playground, MCP Inspector). ⚠️ Two ways to silently break it: **registration order** (Starlette answers preflights without calling downstream, so this must be added AFTER the app-level `CORSMiddleware` to sit OUTSIDE it) and **policy stacking** (Starlette adds its headers to any request bearing an `Origin`, allowlist or not — hence `_OriginStripped`, so exactly one policy applies). `allow_credentials=False` is what makes `allow_origins=*` safe here. Guards: `tests/unit/test_mcp_cors.py`, `tests/unit/test_mcp_identity.py`. |
| `backend/scripts/mcp_usage.py` | "Is the MCP package being used?" report — counts `Check.client` by client with 24h/7d/30d windows + distinct users. Run `python -m scripts.mcp_usage` (or `railway run python -m scripts.mcp_usage` against prod). |

### Frontend
| Directory / File | Purpose |
|------------------|---------|
| `web/components/evidence-views/` | All 6 views + shared components (ViewSelector, TierBadge, TypeBadge) |
| `web/components/claim-selection/` | Pipeline break claim selection UI |
| `web/components/claim-map/` | Base ClaimMap components (Track C, re-themed) |
| `web/components/marketing/` | Stitch landing page components (Hero, Process, Features, Pricing, Video) |
| `web/lib/diagnostic-value.ts` | ACH diagnostic value computation |
| `web/lib/tiers.ts` | Pricing tier configuration (Free/Pro/Developer/Enterprise) |
| `web/app/dashboard/check/[id]/` | Unified check detail (single page, state-driven) |
| `web/app/r/[id]/` | Public report (same pattern as dashboard) |
| `web/app/developers/` | Developer portal + API docs |
| `shared/types/index.ts` | TypeScript types (CheckStatus includes waiting_for_selection) |

## Evidence Sources

**Web search:** Serper.dev → Brave Search → SerpAPI (fallback chain)
**Fact-check:** Google Fact-Check API
**Government:** GOV.UK, Hansard, GovInfo, Companies House, ONS
**Legal:** UK Legislation (legislation.gov.uk)
**Economic:** FRED, Marketaux, World Bank
**Academic:** Semantic Scholar, OpenAlex, PubMed
**Climate/Nature:** NOAA, WeatherAPI, Open-Meteo, GBIF
**Archives:** Wikipedia (+ reference mining), Library of Congress, Internet Archive
**Health:** WHO
**Sports:** Transfermarkt, Football-Data.org
**Video:** YouTube Data API

*Removed in PQ-06: Alpha Vantage (25 req/day unusable), CrossRef (redundant with Semantic Scholar + OpenAlex).*

## Critical Invariants
1. **Track URLs globally, not per-claim.** Cross-claim dedup uses global URL tracking.
2. **LLM truncation uses round-robin.** Never sequential slicing.
3. **Freeze at latest stage.** `claim_map_input_hash`.
4. **Claim Map `evidence_refs` is source of truth.** `element_ids` on evidence is derived.
5. **No hidden curation.** Every exclusion has a receipt.
6. **Classify, don't score.** Tier + Type, not credibility numbers.
7. **Never sycophantic, never false-balancing.** The submitted claim is the starting context for an honest search, never a conclusion to defend — and never a thing to artificially two-side. Distortion in *either* direction is the enemy: a false claim must not look supported, and a well-evidenced grave claim SHOULD look one-sided. Enforced mechanically (neutral question-shaped grounds, honest mapping), never by prompt alone; balance lives in retrieval and mapping, never in forced route symmetry. *(Wording drafted 2026-07-23 at the flag flip — founder to confirm/adjust.)*

## Database
- **PostgreSQL 16** (port 5433) via SQLModel
- **Redis 7** (port 6379) — cache + Celery broker
- **Qdrant** (port 6333) — vector similarity
- **Auth:** Clerk (JWT + JWKS) + API keys (dual auth)
- **Payments:** Stripe. **Current lineup (2026-06-29 pricing decision, unified 2026-07-10): Free trial / Console £20/mo · £200/yr (200 checks/month HARD cap) / Teams from £75 (sales-led, CTA /contact, nothing programmed behind it) / API per-call rates (from £0.02, full £0.15).** Agent payments (x402/Skyfire/credits — x402+Skyfire OFF in prod; credits rail funded via Stripe credit packs, live price IDs set on Railway). ⚠️ **RETIRED, no longer sold or displayed anywhere: Starter £7 / Professional £29** — their Stripe products + env vars (`STRIPE_PRICE_ID_PRO`/`_DEVELOPER` → backend tiers `starter`/`professional`) survive ONLY for existing subscribers' webhook re-derivation. **Console + credit packs are LIVE (2026-07-13) — real payments work end-to-end; this was the last code-path launch blocker and it is CLOSED.** Live price IDs on Railway (backend `STRIPE_PRICE_ID_*`, web `NEXT_PUBLIC_STRIPE_PRICE_ID_CONSOLE{,_ANNUAL}`); live webhook `we_1TEtiA`; smoke-tested with a real £3 credit-pack purchase (webhook fulfilled, balance moved). IDs + the full record: `audit/OPEN_WORK.md` 2026-07-13 entry; provisioning via global skill `~/.claude/skills/stripe-provision`. ⚠️ Watch: webhook api_version `2025-09-30.clover` moved `current_period_start` onto subscription items — the checkout path re-fetches via SDK (fine), but a live subscription RENEWAL is still un-eyeballed. Any doc describing Starter/Professional as the live lineup is stale.

## Latency review state (2026-07-02 — full check ~96s → high-50s, quality gated throughout)
Shipped same day, all deployed: **V1** `f00e0e4` (cost_telemetry gains `timing.stage_timings_s` per-stage seconds + Gemini `thinking_tokens`; classify/distil timed separately; classifier+distiller tokens reach `by_stage` for the first time — a NameError had silently dropped them since inception). **M1** `b1c838b` + Railway env `MAPPING_THINKING_BUDGET=0` LIVE (mapping thinking OFF: 35–50s → ~11–15s; sweep across 5 pools incl. adversarial = equal-or-better quality, disputed-detection 3/3; rollback = delete env var, or `=1024` first on regression). **D1** `a324e8b` (`DISTIL_BATCH_SIZE=5` concurrent distil batches: 16.7–24.5s flaky → ~10s reliable, 15/17 items distilled vs 2/17 — old 15-article batch sat ON its own 15s timeout). **Bench** `9ba5266` re-baselined + GREEN (date-normalised cassette signatures; mapping schema enums `sorted()` — `list(set)` had made every mapping body unreplayable per-process; loud CASSETTE DRIFT failures; `--record-missing` patch mode; 3 hard invariants adjusted with dated in-file notes). Docs: `audit/2026-07-02_pipeline_timing_context.md` + `audit/2026-07-02_pipeline_latency_options.md` (local-only). **NEXT:** read prod `stage_timings_s` distribution after a few days of real checks → decides retrieve-tail work (R1/R2) and whether A1 (quick-tier lite mapping) is still needed. Local `OPENAI_API_KEY` is dead (401) — that is the **fallback**, so only the fallback chain is inoperative locally; the **primary (Google) key is set and unaffected**. Prod OpenAI key unverified — parked by founder. See "LLM providers" above before inferring anything from this line.

## Pending deploy / verify (2026-07-10 — usage ledger)
- **`usage_events` migration** ships with the 2026-07-10 push (runs automatically via `entrypoint.sh`; backfills debit + adjustment events, parity-preserving). Verify: `railway run python -m alembic current` → `usage_events (head)`. **This MUST be live before the Stripe Console tier is wired** — Console = 200 credits/month hard cap (founder-decided 2026-07-10; the webhook maps get `("console", 200)`).
- Remaining ledger phases: B (frontend — **Seeker gate bug B2, CONFIRMED IN CODE 2026-07-31 and ANNUAL-PLAN SPECIFIC**; /pricing credit sentence) + C (non-admin meter proof). Register: `audit/OPEN_WORK.md`.
- **B2, precisely** (the earlier "reads the trial field" wording was wrong): `api/v1/users.py` returns `"creditsRemaining": user.credits` — the legacy counter this file already says no gate should read. The gate itself is correct (`get_usage_snapshot` uses a rolling monthly window, `f51c59d`), but `user.credits` only resets on the **Stripe billing period**, which for an ANNUAL plan fires once a year. So a £200/yr subscriber who spends 200 checks in month 1 reads `creditsRemaining: 0` for eleven months, and `ResearchButton.tsx` disables Seeker re-search on exactly that value while the backend would have served it. Fix = derive from the snapshot (`credits_per_period - period_credits_used`). Monthly plans unaffected, which is why the 2026-07-13 smoke test missed it.

## Pending deploy / verify (as of 2026-06-11 — MCP-origin tracking)
1. ✅ **Pushed 2026-06-11** — `7ca2689..4818c54` (feat `932cd9d` X-Tru8-Client + migration; docs `4818c54`). Railway auto-deploy triggered; backend `/api/v1/health/` → healthy/production post-push.
2. ✅ **`tru8-mcp` 1.0.2 published to PyPI 2026-06-11** — https://pypi.org/project/tru8-mcp/1.0.2/. `twine check` PASSED; shipped wheel confirmed to contain the `X-Tru8-Client` header (1.0.1 did NOT — MCP usage only tracks once users install ≥1.0.2).
3. ⏳ **VERIFY (needs Railway login — interactive):**
   - **Migration applied:** `railway run python -m alembic current` → expect `client_origin (head)` (runs automatically via `entrypoint.sh` on deploy; `check.client` varchar32 indexed, single head, revises `classification_method_64`).
   - **Tracking works:** after one MCP-submitted check on 1.0.2, `railway run python -m scripts.mcp_usage` → `mcp` row non-zero. (Local fast test: `pytest tests/unit/test_client_origin.py` — 9 pass.)

## Code Style
- Python: async/await, type hints on public functions, `black` for formatting
- TypeScript: Next.js 14, SSE for real-time updates, Tailwind CSS
- All pipeline stages must be idempotent
- Structured logging (`logger.*`), never `print()` in pipeline code
- UK English throughout (analyse, organise, colour)
- Terminology: "analysis" not "verification", "evidence research" not "fact-checking"
