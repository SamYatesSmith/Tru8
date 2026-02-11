# Tru8 — Engineering Context

## What This Is
AI-powered evidence research platform. Users submit a URL or claim, the pipeline extracts claims, retrieves evidence from multiple sources, and presents organized evidence.

**Active refactor in progress.** See `audit/PROGRESS.md` for the master tracker.

## Active Refactor: Two-Track Approach

### Track A (in progress): Infrastructure Cleanup
Clean the retrieval pipeline. 5 PRs removing dead code, dead paths, and redundant filters.
- PR-01: Dead code & dead flags (~700 lines)
- PR-02: Legacy embedding path (~200 lines)
- PR-03: Gut filter cascade (~400 lines)
- PR-05: Clean runner.py + V1 replay (~300 lines)
- PR-06: Consolidate workers + config (~500 lines)

**Detailed specs:** `audit/PR-01-dead-code-removal.md` through `audit/PR-06-consolidate-workers-config.md`

### Track B (planned after Track A): Product Pivot
Replace the judge/verdict system with an evidence analyzer. New API contract, schema migration, frontend rebuild. Track B has its own design phase — do NOT start Track B work during Track A.

### What NOT to Touch During Track A
- `judge.py` — messy, has two code paths (legacy + PATH_A). Left intentionally for Track B to replace wholesale.
- `relevance_scorer.py` — has filter mode that Track B will remove. Don't clean it now.
- Verdict-related config flags (`ENABLE_PATH_A`, `ENABLE_ABSTENTION_LOGIC`, etc.) — Track B removes these.
- Frontend verdict components — Track B redesigns these.

## Build & Test Commands

```bash
# Backend
cd backend
uvicorn app.main:app --reload                    # API server (port 8000)
pytest tests/ -v                                 # All tests
pytest tests/unit/pipeline/ -v                   # Pipeline unit tests only
pytest tests/integration/ -v                     # Integration tests
alembic upgrade head                             # Run migrations

# Web
cd web
npm run dev                                      # Dev server (port 3000)
npm run build && npm run start                   # Production build

# Infrastructure
docker-compose up -d                             # Postgres, Redis, Qdrant, MinIO
```

## Pipeline Architecture (current state)

```
Stage 1:   INGEST       → Fetch URL / OCR / transcript
Stage 2:   EXTRACT      → LLM atomizes into ≤12 claims
Stage 2.1: CLASSIFY     → LLM article classification
Stage 2.5: FACTCHECK    → Google Fact-Check API lookup
Stage 3:   RETRIEVE     → Multi-source search (Brave, SerpAPI, gov APIs)
Stage 3.5: FILTER       → Auto-exclude + content dedup + corroboration boost
Stage 3.6: URL DEDUP    → Cross-claim URL deduplication
Stage 3.7: LLM SCORER   → Relevance scoring (has filter mode + advisory mode)
Stage 3.8: DOMAIN CAP   → Global domain capping (max 3/domain)
Stage 5:   JUDGE        → LLM verdict (Track B replaces this)
Stage 6:   SUMMARY      → Overall assessment (Track B replaces this)
```

**Known issues being fixed in Track A:**
- 9 filter stages in `_apply_credibility_weighting` (Track A PR-03 reduces to 3)
- ~50 diagnostic `print()` statements in runner.py (Track A PR-05 removes)
- V1 frozen URL replay (dead, Track A PR-05 removes)
- ~10 dead feature flags (Track A PR-01 removes)
- Dead embedding ranking path (Track A PR-02 removes)

## Key Files (accurate line counts)

### Pipeline Core (Track A touches these)
| File | Lines | What It Does |
|------|-------|-------------|
| `backend/app/pipeline/runner.py` | 1470 | Pipeline orchestrator. SSE streaming. V2 frozen replay. |
| `backend/app/pipeline/retrieve.py` | 2242 | Evidence retrieval. `_apply_credibility_weighting` (lines 1364-1674) is the filter cascade. |
| `backend/app/pipeline/relevance_scorer.py` | 807 | LLM relevance scoring. `_fair_select_evidence` (round-robin). |
| `backend/app/core/config.py` | 292 | Feature flags. ~39 flags, ~10 dead, ~9 always-on. |
| `backend/app/workers/pipeline.py` | 925 | Helper functions. ~465 lines are dead/superseded. |
| `backend/app/utils/domain_capping.py` | 275 | Global domain cap logic. |
| `backend/app/pipeline/evidence_ledger.py` | 75 | Stage tracking for evidence flow. |
| `backend/app/pipeline/replay_context.py` | 17 | ContextVars for V2 frozen replay. |

### Pipeline Core (Track B replaces these)
| File | Lines | What It Does |
|------|-------|-------------|
| `backend/app/pipeline/judge.py` | 1875 | Two judge paths: legacy (lines 675-876) and PATH_A (lines 583-672). Track B replaces entirely. |

### API / Schema / Frontend
| File | Lines | What It Does |
|------|-------|-------------|
| `backend/app/api/v1/checks.py` | 1738 | Check endpoints. Verdict-coupled. Track B changes. |
| `backend/app/models/check.py` | 318 | DB schema (Check, Claim, Evidence). Verdict columns. Track B migrates. |
| `shared/types/index.ts` | 157 | TypeScript types. VerdictType is canonical. Track B replaces. |
| `shared/constants/index.ts` | 100 | Colors, limits, plans. Verdict colors. Track B updates. |
| `web/lib/api.ts` | 538 | Frontend API client. |

## Evidence Sources
- **Web:** Brave Search, SerpAPI
- **Fact-Check:** Google Fact-Check API
- **Government:** NOAA, Alpha Vantage, FRED, Football-Data.org, Weather API, Companies House, Congress API, GovInfo
- **Vector Store:** Qdrant

## V2 Frozen Evidence Replay (harness)
Determinism testing system. Freezes evidence at `judge_input_evidence` (post-filtering), injects directly before judge, skips Stages 3.6/3.7/3.8.
- **Gate 1:** URL Jaccard >= 0.90
- **Gate 2:** 0 hard_fail + 0 pipeline_fail (llm_noise OK)
- **Judge input hash:** SHA256(canonicalized context)[:16]
- **Files:** `runner.py` (bypass), `replay_context.py` (contextvars), `judge.py` (hash), `harness/compare_runs.py` (gates), `harness/run_golden_dataset.py` (runner)

## Critical Invariants
1. **Score mutations must recompute downstream.** If `credibility_score` changes, `final_score` must be recomputed.
2. **Track URLs globally, not per-claim.** Cross-claim dedup uses global URL tracking.
3. **Stage order matters.** Scoring (3.7) before capping (3.8), always.
4. **LLM truncation uses round-robin, not sequential slicing.** Sequential slicing starves tail claims.
5. **Freeze evidence at the latest stage.** `judge_input_evidence`, not `pre_weighting`.

## Database
- **PostgreSQL 16** (port 5433) via SQLModel
- **Redis 7** (port 6379) — cache + Celery broker
- **Qdrant** (port 6333) — vector similarity
- **Auth:** Clerk (JWT + JWKS)
- **Payments:** Stripe + RevenueCat

## Code Style
- Python: async/await, type hints on public functions, `black` for formatting
- TypeScript: React Query for data fetching, SSE for real-time updates
- All pipeline stages must be idempotent
- Structured logging (`logger.*`), never `print()` in pipeline code
