# Tru8 — Engineering Context

## What This Is
AI-powered evidence research platform. Users submit a URL or claim, the pipeline extracts claims, retrieves evidence from 30+ sources, and presents an organised evidence landscape via six profession views. Mission: "We organise; you decide."

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
| I | IN PROGRESS | Pre-release readiness. Subs LIVE in production (`SUBSCRIPTIONS_ENABLED=True` deployed long ago — confirmed 2026-05-01; I-03/I-04 closed). I-07 MCP publication DONE — `tru8-mcp` 1.0.1 on PyPI (2026-06-10). Remaining: I-06 OG cards visual review, I-07 directory submissions (mcp.so/PulseMCP/Smithery/official registry, non-blocking). See `audit/track-i/PROGRESS.md`. |
| J | COMPLETE | Test suite overhaul — 0 failures, +87 new tests. Commit `a5ed52d`. |
| K | COMPLETE | Endpoint + efficacy testing. 1,092 tests collected. Commit `14371cf` + subsequent. |
| L | COMPLETE | Agent Commerce Gateway — 3 tiers (Lookup/Quick/Full), 3 payment rails (x402/Skyfire/credits), `/agent/` endpoints, MCP tier tool. Deployment-only items remain (Stripe credit packs, PyPI publish). |
| M | COMPLETE | Evidence Infrastructure — M-01 provenance, M-02 gap enrichment + provider status, M-03 smart endpoint, M-04 manifest signing + verify endpoint, M-05 jurisdiction routing, M-06 convergence layer + consensus tier, M-07 tests (+54). Deployment items remain (migrations, signing key, MCP consensus tier). |
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
uvicorn app.main:app --reload                    # API server (port 8000)
pytest tests/ -v                                 # All tests (1,118 collected, 1,068 pass, 13 skip)
pytest tests/unit/pipeline/ -v                   # Pipeline unit tests
pytest tests/integration/ -v                     # Integration tests
alembic upgrade head                             # Run migrations

# Web
cd web
npm run dev                                      # Dev server (port 3000)
npm run build && npm run start                   # Production build

# Infrastructure
docker-compose up -d                             # Postgres, Redis, Qdrant, MinIO
```

## LLM providers — Google is PRIMARY, OpenAI is the FALLBACK
**Every** LLM stage tries Google Gemini first and falls back to OpenAI only if the primary is
absent, errors, or times out. Verify in code, never infer: `query_planner.py` (*"Try Google
first, then OpenAI as fallback"*), `claim_map_analyzer.py:1797` (*"Fall back to OpenAI"*),
`evidence_classifier.py:838` (same), `claim_selector.py`. `GOOGLE_AI_API_KEY` is the key that
matters; `ANTHROPIC_API_KEY` is deprecated (`config.py:59`).

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
  RETRIEVE (60%)      → **Per-element as of Phase 2 (`36d3f4e`, 2026-07-27) — it genuinely was NOT before.** For months this line described an intent: `retrieve.py` read `claim["elements"]`, decompose wrote `claim["claim_map"]["elements"]`, nothing wrote the key it read, so the planner got the raw claim text as ONE synthetic element on EVERY check (prod-proved: `1 element plans for 1 claims` on a 4-element claim, 3 Serper calls). Worst effect — for an opinion claim the claim text IS the judgement, so the pool was gathered by searching its own valence ("success metrics" for "was a triumph"): invariant #7 breached at pool constitution. **Now:** each claim gets a CLAIM lane (`c0` — the old synthetic element, kept so the factual path is unchanged) + one lane per Claim Map element (≤5). Claim lane ≤3 queries incl. class-targeted `site:` variants (claim-lane only); element lanes ≤2 each → **13 queries/claim full, 6 quick, ≤65/check**. Fetch cap unchanged (40); claim lane keeps 13 results/query, element lanes 5; the 40 fetch slots are allocated by **weighted round-robin, claim lane 2:1** — a plain slice starves the last lanes. F1-D3 hedge applies per lane (each lane's 2nd query unwindowed unless planner chose pd/pw); two-year claims get both years anchored — F1-D1. Re-search (`re_search.py`) supplies its own single element and is deliberately unwired — no claim lane. Rollback `ENABLE_ELEMENT_RETRIEVAL=False`. Design: `audit/2026-07-27_phase2_element_retrieval_build_design.md`. **LIVE-VERIFIED 2026-07-28** (`wired=True` 3/3, Grenfell matches baseline) after `7bc670a` fixed a live failure in which the planner omitted the `c0` plan on 3/3 checks and the per-lane sizing silently never ran. **"Add, don't replace" is SETTLED (founder, 2026-07-29 — D3 closed, no build):** the user's claim MUST be searched *and* the decoupled elements must also be searched and be relevant to their line of enquiry, so the full context is grasped and relayed. Do not re-open it, and never remove the claim lane in the name of criterion 17 — the valence query already fell from the whole pool to 1 of 13 queries / 8 of 40 fetch slots, and balance lives in the element lanes beside it. ⚠️ **Every replay cassette is dead** (query strings are cassette keys) — F7 re-gold owed, runbook in `audit/OPEN_WORK.md`
  SCORE (65%)         → LLM topical relevance scoring (1-5 scale, max 50 items)
  CLASSIFY (75%)      → Tier/Type classification (batched LLM + heuristic fallback). Post-classify (needs tiers): mechanical derivation annotation writes per-element basis sourcing notes — echo (a primary re-reported by ≥2 derivatives), F4 repetition (≥3 non-primary sources reciting the same wording across ≥2 ownership groups with NO primary anchor — sentence-shingle, `corroboration.annotate_repetition_clusters`, 2026-07-07), thin (commentary-only / single-outlet). Surfaced as grey no-verdict notes (dashboard + `/r/`); a flagged element is toppable via "Strengthen this claim". Parity-locked `support_structure.py` ↔ `support-structure.ts`
  MAP (85%)           → Evidence → element mapping + state assignment (Gemini 2.5 Flash, 1000-char snippets; thinking OFF in prod via MAPPING_THINKING_BUDGET=0 — sweep-verified equal-or-better quality at −64-74% latency, 2026-07-02). Mapper also emits per-element scope_caveat (evidence's narrower reach) — F3-B2
  ORIENTATION         → Mechanical derivation from element states (no LLM) + orientation_basis + F3 scope caveats in state_derivation.caveat (neutral channel): universal ("only/first" cannot be established, tier-gated — F3-B1) + reach ("evidence covers X, narrower than Y", LLM∧tagger-gated — F3-B2). State never changes; describes evidential limit, never adjudicates
                        **Grounds-routed (opinion) claims: prose orientation SUPPRESSED (`None`) — Phase 1 `007cf5c`.** Summing elements DERIVED FROM an opinion reads as a verdict on it (invariant #7, witnessed both directions). Single decision point `apply_orientation()`; `orientation_basis` still ALWAYS computed (it is in the manifest canonical payload — signing unaffected). Frontend must render NOTHING there — shared `web/lib/orientation.ts::isOrientationSuppressed`, 4 surfaces. Also `GROUNDS_MIN_WEIGHTED_SUPPORT=3`: a question-shaped element badged `supported` off one thin source now reads `unresolved` and reaches the Seeker; factual path untouched (floor defaults 0)
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

## Six Profession Views

| View | Question | Level | Source |
|------|----------|-------|--------|
| Cartographer | Shape of the conversation? | Overview + Detail | Dagre cascade layout |
| Librarian | Full set, clearly labelled? | Overview + Detail | Tier×Type heatmap + ledger + receipts |
| Correspondent | Answer this sub-question? | Detail only | Disposition panel with element focus (renamed from Interpreter for audience reasons) |
| Projectionist | What's said on camera? | Overview + Detail | YouTube video cards |
| Chronologist | When did evidence appear? | Overview + Detail | Pure SVG timeline |
| Seeker | What don't we know? | Detail only | Unknowns ledger + bounty text + re-search |

Cross-cutting: Diagnostic Value Highlighter (ACH toggle on Cartographer + Librarian), URL-persisted view state (`?view=`), auto-archive links.

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
| `backend/app/services/video_recommendations.py` | YouTube video provider |
| `backend/app/services/computed_analytics.py` | Computed analytics + freshness |
| `backend/app/services/consensus.py` | Convergence layer — daily batch consensus computation |
| `backend/app/core/manifest_signer.py` | HMAC-SHA256 manifest signing, canonical payload, pipeline fingerprint |
| `backend/app/services/payments/` | PaymentProvider ABC, credit + Skyfire providers |
| `backend/app/services/usage_ledger.py` | Ledger gate/debit/refund: `enforce_usage_limit` (FOR UPDATE row lock → gate+debit atomic), `record_usage`, `refund_usage` (mirrors `drew_trial` — subscriber refunds never mint trial credits). Re-searches/top-ups COUNT against the plan (1 credit/run); debit commits BEFORE background work fires. Design: `audit/2026-07-10_usage_ledger_design.md` |
| `backend/app/core/agent_auth.py` | Agent auth + concurrency limits |
| `backend/app/core/client_origin.py` | `resolve_client(request)` — normalises `X-Tru8-Client` header (e.g. `mcp/1.0.2` → `mcp`) onto `Check.client` for first-party usage attribution |
| `backend/app/core/agent_pricing.py` | Agent pricing (lookup $0.02, consensus $0.03, quick $0.07, full $0.15) |
| `backend/app/middleware/x402_audit.py` | x402 payment middleware |
| `backend/tru8_mcp/server.py` | MCP server for Claude/agents — 3 tools: `tru8_check` (submit with tier fallback), `tru8_get_result` (computed analytics), `tru8_get_result_raw` (raw data). Thin HTTP client over `/agent/*` + `/checks/*`; inherits pipeline upgrades automatically. Sends `X-Tru8-Client: mcp/<version>` on every request (see `tru8_mcp/tools.py::_headers`). |
| `backend/scripts/mcp_usage.py` | "Is the MCP package being used?" report — counts `Check.client` by client with 24h/7d/30d windows + distinct users. Run `python -m scripts.mcp_usage` (or `railway run python -m scripts.mcp_usage` against prod). |

### Frontend
| Directory / File | Purpose |
|------------------|---------|
| `web/components/evidence-views/` | All 6 profession views + shared components (ViewSelector, TierBadge, TypeBadge) |
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
- **Payments:** Stripe. **Current lineup (2026-06-29 pricing decision, unified 2026-07-10): Free trial / Console £20/mo · £200/yr (200 checks/month HARD cap) / Teams from £75 (sales-led, CTA /contact, nothing programmed behind it) / API per-call rates (from £0.02, full £0.15).** Agent payments (x402/Skyfire/credits — x402+Skyfire OFF in prod; credits rail funded via Stripe credit packs, env vars not yet set). ⚠️ **RETIRED, no longer sold or displayed anywhere: Starter £7 / Professional £29** — their Stripe products + env vars (`STRIPE_PRICE_ID_PRO`/`_DEVELOPER` → backend tiers `starter`/`professional`) survive ONLY for existing subscribers' webhook re-derivation. **Console + credit-pack Stripe products exist in TEST mode only (2026-07-13, all test payments proven; wiring built, live mode pending)** — see `audit/OPEN_WORK.md` 2026-07-13 entry for IDs; provisioning via global skill `~/.claude/skills/stripe-provision`. Any doc describing Starter/Professional as the live lineup is stale.

## Latency review state (2026-07-02 — full check ~96s → high-50s, quality gated throughout)
Shipped same day, all deployed: **V1** `f00e0e4` (cost_telemetry gains `timing.stage_timings_s` per-stage seconds + Gemini `thinking_tokens`; classify/distil timed separately; classifier+distiller tokens reach `by_stage` for the first time — a NameError had silently dropped them since inception). **M1** `b1c838b` + Railway env `MAPPING_THINKING_BUDGET=0` LIVE (mapping thinking OFF: 35–50s → ~11–15s; sweep across 5 pools incl. adversarial = equal-or-better quality, disputed-detection 3/3; rollback = delete env var, or `=1024` first on regression). **D1** `a324e8b` (`DISTIL_BATCH_SIZE=5` concurrent distil batches: 16.7–24.5s flaky → ~10s reliable, 15/17 items distilled vs 2/17 — old 15-article batch sat ON its own 15s timeout). **Bench** `9ba5266` re-baselined + GREEN (date-normalised cassette signatures; mapping schema enums `sorted()` — `list(set)` had made every mapping body unreplayable per-process; loud CASSETTE DRIFT failures; `--record-missing` patch mode; 3 hard invariants adjusted with dated in-file notes). Docs: `audit/2026-07-02_pipeline_timing_context.md` + `audit/2026-07-02_pipeline_latency_options.md` (local-only). **NEXT:** read prod `stage_timings_s` distribution after a few days of real checks → decides retrieve-tail work (R1/R2) and whether A1 (quick-tier lite mapping) is still needed. Local `OPENAI_API_KEY` is dead (401) — that is the **fallback**, so only the fallback chain is inoperative locally; the **primary (Google) key is set and unaffected**. Prod OpenAI key unverified — parked by founder. See "LLM providers" above before inferring anything from this line.

## Pending deploy / verify (2026-07-10 — usage ledger)
- **`usage_events` migration** ships with the 2026-07-10 push (runs automatically via `entrypoint.sh`; backfills debit + adjustment events, parity-preserving). Verify: `railway run python -m alembic current` → `usage_events (head)`. **This MUST be live before the Stripe Console tier is wired** — Console = 200 credits/month hard cap (founder-decided 2026-07-10; the webhook maps get `("console", 200)`).
- Remaining ledger phases: B (frontend — Seeker gate fix B2 reads the trial field and blocks paying subscribers; /pricing credit sentence) + C (non-admin meter proof). Register: `audit/OPEN_WORK.md`.

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
