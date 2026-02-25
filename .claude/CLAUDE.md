# Tru8 — Engineering Context

## What This Is
AI-powered evidence research platform. Users submit a URL or claim, the pipeline extracts claims, retrieves evidence from multiple sources, and presents organized evidence via Claim Maps.

## Refactor Status

### Track A: COMPLETE (2026-02-11)
Infrastructure cleanup. 5 PRs, ~2,100 lines removed. Commit `041b55f`.

### Track B: COMPLETE (2026-02-13)
Backend pivot — Claim Map system. 8 PRs, ~7,000 lines removed. Final commit `d40668b`.
**Contract:** `audit/track-b/2026-02-12_claim-map-contract.md`

### Track C: COMPLETE (2026-02-14)
Frontend verdict-to-ClaimMap component swap. 9 PRs, ~500 net lines removed. Final commit `b365534`.
Replaced verdict UI with Claim Map components on product pages (dashboard, check detail, history, settings, public report, mobile screens). Kept dark theme.

### Track D (in progress): Full Frontend Redesign
Convert entire web frontend from dark theme to Stitch light theme. Rebuild marketing pages, re-theme all dashboard/legal pages, align all copy with evidence-research positioning. 10 PRs planned.

**Specs:** `audit/track-d/PROGRESS.md` (master tracker)
**Design decisions:** `audit/track-d/00_design_decisions.md`
**Page gap analysis:** `audit/track-d/01_page_gap_analysis.md`
**Copy audit:** `audit/track-d/02_copy_audit.md`
**Stitch style guide:** `audit/track-c/stitch/STITCH_STYLE_GUIDE.md`
**Stitch page specs:** `audit/track-c/stitch/pages/W-01..W-19` (web), `M-01..M-12` (mobile)

**Key decisions:**
- Full light theme (white surfaces, Inter + JetBrains Mono, 1px borders, no shadows)
- "Analysis" not "verification", "evidence research" not "fact-checking"
- Stitch designs are the mirror — faithful reproduction, no omissions. Spec-sheet aesthetic (micro-labels, system IDs, metadata rows) IS the design language.
- Track C Claim Map components retained and re-themed
- Only permitted adaptation: Lucide icons instead of Material Symbols

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

## Pipeline Architecture (post-Track B)

```
Stage 1:   INGEST           → Fetch URL / OCR / transcript
Stage 2:   EXTRACT          → LLM atomizes into ≤12 claims
Stage 2.1: CLASSIFY         → LLM article classification
Stage 2.5: FACTCHECK        → Google Fact-Check API lookup
Stage 2.5: CLAIM SELECTION  → Article mode: rank + select ≤5 claims
Stage 3:   RETRIEVE         → Per-element multi-source search (Serper, Brave, SerpAPI, gov APIs)
Stage 3.5: FILTER           → Auto-exclude + content dedup + corroboration boost
Stage 3.6: URL DEDUP        → Cross-claim URL deduplication
Stage 3.7: LLM SCORER       → Advisory-only relevance scoring
Stage 3.8: DOMAIN CAP       → Global domain capping (max 3/domain)
Stage 4:   DECOMPOSITION    → Claim → 1-5 elements (LLM call)
Stage 5:   EVIDENCE MAPPING → Map evidence to elements + assign states (LLM call)
           ORIENTATION      → Mechanical derivation from element states (no LLM)
```

## Key Files

### Backend (post-Track B)
| File | Purpose |
|------|---------|
| `backend/app/pipeline/runner.py` | Orchestrator with claim selection + decomposition + evidence mapping |
| `backend/app/pipeline/retrieve.py` | Element-level retrieval + filter cascade |
| `backend/app/pipeline/claim_map_analyzer.py` | Decompose + map + derive orientation |
| `backend/app/pipeline/claim_selector.py` | Article mode claim ranking |
| `backend/app/models/claim_map.py` | ClaimMap types + enums |
| `backend/app/api/v1/checks.py` | API endpoints (claim map shapes) |
| `backend/app/models/check.py` | DB schema (Check, Claim, Evidence) |

### Frontend (post-Track C, pre-Track D)
| File | Purpose | Track D Change |
|------|---------|---------------|
| `web/app/layout.tsx` | Root layout (dark theme) | Light theme |
| `web/app/page.tsx` | Landing page (old marketing) | Full rebuild |
| `web/app/dashboard/layout.tsx` | Dashboard shell (dark) | Light theme |
| `web/components/layout/navigation.tsx` | Dark hover-pill nav | Full rebuild |
| `web/components/layout/footer.tsx` | Dark footer | Full rebuild |
| `web/components/marketing/*.tsx` | 6 old marketing components | Delete + rebuild |
| `web/components/claim-map/` | ClaimMapView + 5 components | Re-theme only |
| `web/components/legal/legal-page-layout.tsx` | Dark legal wrapper | Light theme |
| `shared/types/index.ts` | TypeScript types (no VerdictType) | No change |
| `shared/constants/index.ts` | Constants (no verdict colors) | No change |

## Evidence Sources
- **Web:** Serper (primary), Brave Search (secondary), SerpAPI (tertiary)
- **Fact-Check:** Google Fact-Check API
- **Government:** NOAA, Alpha Vantage, FRED, Football-Data.org, Weather API, Companies House, Congress API, GovInfo
- **Vector Store:** Qdrant

## Critical Invariants
1. **Score mutations must recompute downstream.** `credibility_score` → recompute `final_score`.
2. **Track URLs globally, not per-claim.** Cross-claim dedup uses global URL tracking.
3. **Stage order matters.** Scoring (3.7) before capping (3.8), always.
4. **LLM truncation uses round-robin.** Never sequential slicing.
5. **Freeze at latest stage.** `claim_map_input_hash` (renamed from `judge_input_hash`).
6. **Claim Map `evidence_refs` is source of truth.** `element_ids` on evidence is derived.

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
