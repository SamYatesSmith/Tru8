# Tru8 — Engineering Context

## What This Is
AI-powered evidence research platform. Users submit a URL or claim, the pipeline extracts claims, retrieves evidence from multiple sources, and presents organized evidence.

**Active refactor in progress.** See `audit/track-b/PROGRESS.md` for the master tracker.

## Active Refactor: Two-Track Approach

### Track A: COMPLETE
Infrastructure cleanup. 5 PRs, ~2,100 lines removed. Commit `041b55f`.
**Specs:** `audit/track-a/PR-01-dead-code-removal.md` through `audit/track-a/PR-06-consolidate-workers-config.md`

### Track B (in progress): Product Pivot — Claim Map System
Replace the judge/verdict system with the Claim Map evidence analyzer. 8 PRs.
- B01: Foundation — types, schema migration, config flags
- B02: Claim Map analyzer + claim selector (new modules)
- B03: Evidence ID + element-level retrieval (direct replacement)
- B04: Pipeline wiring — new stages replace judge/summary/explainability
- B05: Harness adaptation — validate new path
- B06: API response shapes + peripheral services
- B07: Verdict system deletion (~2,500 lines)
- B08: Test suite overhaul

**Specs:** `audit/track-b/PR-B01-foundation.md` through `audit/track-b/PR-B08-test-suite-overhaul.md`
**Contract:** `audit/track-b/2026-02-12_claim-map-contract.md`
**Strategy:** Direct replacement. Pipeline offline during Track B — no feature gate. B05/B06 parallelizable after B04.

### What NOT to Touch During Track B
- Frontend verdict components — Track C redesigns these (39 files across web + mobile)
- `VerdictType` in `shared/types/index.ts` — frontend needs it until Track C

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

**Track B changes to pipeline:**
- NEW Stage: CLAIM SELECTION (article mode, rank + select ≤5 claims)
- NEW Stage: DECOMPOSITION (claim → 1-5 elements, new LLM call)
- Stage 3 RETRIEVE becomes per-element instead of per-claim
- Stage 3.7 SCORER becomes advisory-only (filter mode removed)
- Stage 5 JUDGE → EVIDENCE MAPPING (map evidence to elements + assign states)
- Stage 6 SUMMARY → removed (orientation line is mechanical)

## Key Files (post-Track A line counts)

### Pipeline Core (Track B modifies these)
| File | Lines | Track B Change |
|------|-------|---------------|
| `backend/app/pipeline/runner.py` | ~1,359 | New stages, gate logic, remove judge/summary |
| `backend/app/pipeline/retrieve.py` | ~1,700 | Element-level retrieval, evidence_id |
| `backend/app/pipeline/relevance_scorer.py` | 807 | Element-level scoring, remove filter mode |
| `backend/app/pipeline/query_planner.py` | 655 | Element-level query generation |
| `backend/app/core/config.py` | 229 | Remove verdict flags, add analyzer flags |
| `backend/app/utils/domain_capping.py` | 275 | Element-aware capping |
| `backend/app/pipeline/evidence_ledger.py` | 75 | New stage names |
| `backend/app/workers/pipeline.py` | 312 | Update retrieval helper |

### Pipeline Core (Track B deletes these)
| File | Lines | Reason |
|------|-------|--------|
| `backend/app/pipeline/judge.py` | 1,875 | Replaced by claim_map_analyzer.py |
| `backend/app/utils/explainability.py` | 193 | ClaimMap IS the explainability |

### Pipeline Core (Track B adds these)
| File | Purpose |
|------|---------|
| `backend/app/pipeline/claim_map_analyzer.py` | Decompose + map + derive orientation |
| `backend/app/pipeline/claim_selector.py` | Article mode claim ranking |
| `backend/app/models/claim_map.py` | ClaimMap types + enums |

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
