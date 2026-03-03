# Tru8 — Engineering Context

## What This Is
AI-powered evidence research platform. Users submit a URL or claim, the pipeline extracts claims, retrieves evidence from 30+ sources, and presents an organised evidence landscape via six profession views. Mission: "We organise; you decide."

## Track Status (2026-02-27)

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
| I | IN PROGRESS | Pre-release readiness. Pricing tiers done (`d103ce3`). Remaining: Stripe setup, OG cards, MCP distribution, developer polish. See `audit/track-i/PROGRESS.md`. |
| J | COMPLETE | Test suite overhaul — 0 failures, +87 new tests. Commit `a5ed52d`. |
| K | IN PROGRESS | Endpoint + efficacy testing. 814 passed, 13 skipped, 0 failed. |
| L | PLANNED (R6) | Agent Commerce Gateway — 3 tiers (Lookup/Quick/Full), 3 payment rails (x402/Skyfire/credits), `/agent/` endpoints. Plan: `audit/track-l/2026-02-27_track-l-plan.md`. |
| M | PLANNED | Evidence Infrastructure — signed manifests, provenance persistence, smart endpoint, landscape signal, convergence layer. Plan: `audit/track-m/2026-02-27_track-m-plan.md`. |

## Build & Test Commands

```bash
# Backend
cd backend
uvicorn app.main:app --reload                    # API server (port 8000)
pytest tests/ -v                                 # All tests (814 pass, 13 skip)
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

## Pipeline Architecture (post-Track E)

Two-phase pipeline with user claim selection gate:

```
Phase 1 (0-30%):
  INGEST (10%)        → Fetch URL / OCR / transcript
  EXTRACT (20%)       → LLM atomises into ≤12 claims
  SELECT/RANK (28%)   → Article classification + claim ranking
  [PAUSE]             → waiting_for_selection (article mode only)

Phase 2 (30-100%):
  FACTCHECK (35%)     → Google Fact-Check API lookup
  DECOMPOSE (45%)     → Claim → 1-5 elements (LLM call)
  RETRIEVE (60%)      → Per-element multi-source search (2 queries/element)
  CLASSIFY (75%)      → Tier/Type classification (batched LLM)
  ANALYZE (85%)       → Evidence mapping + state assignment (LLM call)
  ORIENTATION         → Mechanical derivation from element states (no LLM)
  QUERY (90%)         → Optional search clarity
  COMPLETE (100%)

Stage 5.1: COVERAGE RECOVERY → Targeted retrieval for low-coverage claims

Parallel tasks (fire-and-forget):
  - Video recommendations (YouTube API, max 5/claim)
  - Auto-archiving (Wayback Machine, ~15 req/min)
```

## Six Profession Views

| View | Question | Level | Source |
|------|----------|-------|--------|
| Cartographer | Shape of the conversation? | Overview + Detail | Dagre cascade layout |
| Librarian | Full set, clearly labelled? | Overview + Detail | Tier×Type heatmap + ledger + receipts |
| Interpreter | Answer this sub-question? | Detail only | Disposition panel with element focus |
| Projectionist | What's said on camera? | Overview + Detail | YouTube video cards |
| Chronologist | When did evidence appear? | Overview + Detail | Pure SVG timeline |
| Seeker | What don't we know? | Detail only | Unknowns ledger + bounty text + re-search |

Cross-cutting: Diagnostic Value Highlighter (ACH toggle on Cartographer + Librarian), URL-persisted view state (`?view=`), auto-archive links.

## Key Files

### Backend
| File | Purpose |
|------|---------|
| `backend/app/pipeline/runner.py` | Two-phase orchestrator + coverage recovery |
| `backend/app/pipeline/retrieve.py` | Element-level retrieval + filter cascade |
| `backend/app/pipeline/claim_map_analyzer.py` | Decompose + map + derive orientation |
| `backend/app/pipeline/evidence_classifier.py` | Tier/Type classification (batched LLM + heuristic fallback) |
| `backend/app/pipeline/relevance_scorer.py` | Topical relevance scoring (no source authority) |
| `backend/app/pipeline/claim_selector.py` | Article mode claim ranking |
| `backend/app/pipeline/re_search.py` | Targeted element re-query (Seeker) |
| `backend/app/models/claim_map.py` | ClaimMap types + enums |
| `backend/app/models/check.py` | DB schema (Evidence has tier, type, receipt_status, archived_url) |
| `backend/app/api/v1/checks.py` | API endpoints (dual auth, computed analytics, snapshot mode) |
| `backend/app/api/v1/api_keys.py` | API key management |
| `backend/app/api/v1/webhooks.py` | Webhook completion notifications |
| `backend/app/services/wayback_archive.py` | Auto-archiving service |
| `backend/app/services/video_recommendations.py` | YouTube video provider |
| `backend/tru8_mcp/server.py` | MCP server for Claude/agents |

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

**Web search:** Brave Search, SerpAPI (Google results)
**Fact-check:** Google Fact-Check API
**Government:** GOV.UK, Hansard, GovInfo, Companies House, ONS
**Economic:** FRED, Alpha Vantage, Marketaux
**Academic:** CrossRef, Semantic Scholar, OpenAlex, PubMed
**Climate/Nature:** NOAA, WeatherAPI, GBIF
**Archives:** Wikipedia, Library of Congress, Internet Archive
**Health:** WHO
**Sports:** Transfermarkt, Football-Data.org
**Video:** YouTube Data API

## Critical Invariants
1. **Track URLs globally, not per-claim.** Cross-claim dedup uses global URL tracking.
2. **LLM truncation uses round-robin.** Never sequential slicing.
3. **Freeze at latest stage.** `claim_map_input_hash`.
4. **Claim Map `evidence_refs` is source of truth.** `element_ids` on evidence is derived.
5. **No hidden curation.** Every exclusion has a receipt.
6. **Classify, don't score.** Tier + Type, not credibility numbers.

## Database
- **PostgreSQL 16** (port 5433) via SQLModel
- **Redis 7** (port 6379) — cache + Celery broker
- **Qdrant** (port 6333) — vector similarity
- **Auth:** Clerk (JWT + JWKS) + API keys (dual auth)
- **Payments:** Stripe (4 tiers: Free/Pro/Developer/Enterprise)

## Code Style
- Python: async/await, type hints on public functions, `black` for formatting
- TypeScript: Next.js 14, SSE for real-time updates, Tailwind CSS
- All pipeline stages must be idempotent
- Structured logging (`logger.*`), never `print()` in pipeline code
- UK English throughout (analyse, organise, colour)
- Terminology: "analysis" not "verification", "evidence research" not "fact-checking"
