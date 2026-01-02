# Tru8 - Fact-Checking Platform Configuration

## Project Context
**Project:** Tru8 - Instant fact-checking with dated evidence
**Stage:** Production-ready (Phase 5-6 complete)
**Architecture:** Mobile (React Native/Expo) + Web (Next.js 14) + API (FastAPI) + ML Pipeline

## Quick Commands

### Backend (FastAPI)
```bash
cd backend
uvicorn app.main:app --reload              # Start API server (port 8000)
celery -A app.workers.pipeline worker -l info  # Start Celery worker
pytest tests/ -v                           # Run all tests
pytest tests/unit/ -v                      # Unit tests only
pytest tests/integration/ -v               # Integration tests
alembic upgrade head                       # Run migrations
alembic revision --autogenerate -m "msg"   # Create migration
```

### Web (Next.js)
```bash
cd web
npm run dev                         # Start dev server (port 3000)
npm run build && npm run start      # Production build
npm run lint && npm run typecheck   # Validate code
```

### Mobile (React Native/Expo)
```bash
cd mobile
npx expo start                      # Start Expo
npx expo run:ios                    # iOS simulator
npx expo run:android                # Android emulator
eas build --platform all            # Build for stores
```

### Infrastructure (Docker)
```bash
docker-compose up -d                # Start Postgres, Redis, Qdrant, MinIO
docker-compose down                 # Stop services
docker-compose logs -f postgres     # View logs
```

## Project Structure
```
/
├── backend/                    # FastAPI + ML Pipeline (60+ Python files)
│   ├── app/
│   │   ├── api/v1/            # API endpoints (auth, checks, users, payments, feedback, health)
│   │   ├── core/              # Config, database, auth, logging
│   │   ├── models/            # SQLModel schemas (User, Check, Claim, Evidence)
│   │   ├── pipeline/          # 7-stage verification pipeline
│   │   ├── services/          # 16 service modules (search, embeddings, cache, etc.)
│   │   ├── utils/             # 15+ utility modules
│   │   └── workers/           # Celery task orchestration (1400+ lines)
│   ├── tests/                 # 30+ test modules (unit/integration/performance)
│   ├── alembic/               # 20+ database migrations
│   └── requirements.txt
├── web/                        # Next.js 14 frontend
│   ├── app/                   # App Router (dashboard, history, settings)
│   ├── components/            # React components (auth, marketing, layout)
│   └── lib/                   # API client, utilities
├── mobile/                     # React Native/Expo (12 route files)
│   ├── app/                   # Expo Router (tabs, auth flows)
│   ├── components/            # Native components (VerdictPill, ClaimCard, etc.)
│   └── services/              # API client
├── shared/                     # Shared TypeScript types & constants
│   ├── types/index.ts         # API types (Check, Claim, Evidence, User)
│   └── constants/index.ts     # Colors, limits, plans, feature flags
└── docker-compose.yml          # Postgres, Redis, Qdrant, MinIO, Flower
```

## Verification Pipeline (7 Stages)

```
1. INGEST      → Fetch URL content, OCR images, YouTube transcripts
2. EXTRACT     → LLM atomizes content into max 12 verifiable claims
3. CLASSIFY    → LLM categorizes article domain (sports, politics, science, etc.)
4. PLAN        → LLM generates targeted search queries per claim
5. RETRIEVE    → Multi-source search with deduplication & credibility scoring
6. VERIFY      → NLI model (BART/DeBERTa) scores entailment/contradiction
7. JUDGE       → LLM weighs evidence, generates final verdict + rationale
```

### Evidence Sources (Phase 5 Complete)
- **Web Search:** Brave Search, SerpAPI
- **Fact-Check:** Google Fact-Check API, programmatic parsing
- **Government APIs:** NOAA (climate), Alpha Vantage (stocks/forex/crypto), FRED (economics), Football-Data.org (sports), Weather API, Companies House (UK), Congress API, GovInfo (legal)
- **Vector Store:** Qdrant for semantic similarity

## Database Models (SQLModel + PostgreSQL JSONB)

### Core Tables
```python
User           # Clerk ID, email, credits, push_token, notification prefs
Subscription   # plan, credits_per_month, stripe_id, revenuecat_id
Check          # input_type, status, decision_trail (JSONB), transparency_score
Claim          # text, verdict, confidence, temporal_markers (JSONB), rhetorical_context
Evidence       # url, credibility_score, tier, is_factcheck, risk_flags (JSONB)
RawEvidence    # All sources before filtering (for transparency)
UnknownSource  # Track domains not in credibility database
```

## Feature Flag System (25+ Phases)

Located in `backend/app/core/config.py`:

| Phase | Features |
|-------|----------|
| 1 | Domain capping, deduplication, source diversity |
| 1.5 | Temporal context, fact-check API integration |
| 2 | Claim classification, explainability, decision trails |
| 3 | Credibility framework, abstention logic, source validation |
| 3.5 | Source quality control, tiered credibility |
| 4 | Legal integration (GovInfo, Congress API) |
| 5 | Government API integration (8 APIs) |
| 6 | Judge improvements, enhanced prompts |
| Tier 1 | Query expansion, semantic snippets, primary source detection |

### Key Thresholds
```python
NLI_CONFIDENCE_THRESHOLD = 0.7
SOURCE_CREDIBILITY_THRESHOLD = 0.65
MIN_SOURCES_FOR_VERDICT = 2
MAX_EVIDENCE_PER_DOMAIN = 3
GLOBAL_DOMAIN_CAP = 5
```

## Services Layer (16 Modules)

| Service | Purpose |
|---------|---------|
| `search.py` | Brave Search, SerpAPI, Qdrant integration |
| `embeddings.py` | Sentence-transformers for semantic similarity |
| `evidence.py` | HTML extraction, snippet generation |
| `vector_store.py` | Qdrant vector database operations |
| `factcheck_api.py` | Google Fact-Check API |
| `government_api_client.py` | 8 government APIs |
| `source_credibility.py` | Tier1/Tier2/Tier3 domain scoring |
| `cache.py` | Redis caching with TTL |
| `circuit_breaker.py` | Resilience pattern for external APIs |
| `email_notifications.py` | Resend email service |
| `push_notifications.py` | Expo push notifications |
| `pdf_evidence.py` | PDF extraction and report generation |

## Utils Layer (15+ Modules)

| Utility | Purpose |
|---------|---------|
| `article_classifier.py` | LLM-based domain classification |
| `claim_keyword_router.py` | Route claims to appropriate APIs |
| `query_planner.py` | LLM generates search queries |
| `rhetorical_analyzer.py` | Sarcasm/mockery detection |
| `source_credibility.py` | Tiered source classification |
| `legal_claim_detector.py` | Identify legal/court claims |
| `deduplication.py` | Content-hash based dedup |
| `domain_capping.py` | Limit sources per domain |
| `source_independence.py` | Media ownership analysis |
| `source_type_classifier.py` | Detect factcheck/news/academic |
| `temporal.py` | Date/time extraction |
| `explainability.py` | Decision trail generation |

## Design System

**Reference:** `DESIGN_SYSTEM.md`

### Colors (CSS Variables)
```css
--tru8-primary: #1E40AF;           /* Deep Blue */
--gradient-primary: linear-gradient(135deg, #1E40AF 0%, #7C3AED 100%);
--verdict-supported: #059669;       /* Emerald */
--verdict-contradicted: #DC2626;    /* Red */
--verdict-uncertain: #D97706;       /* Amber */
```

### Mandatory Components
1. **VerdictPill** - Semantic verdict badges
2. **ConfidenceBar** - Animated progress bars
3. **CitationChip** - `Publisher · Date · Credibility`
4. **ClaimCard** - Claim display with evidence drawer

## Testing Structure

```
tests/
├── unit/pipeline/           # Pipeline stage tests
│   ├── test_extract.py
│   ├── test_ingest.py
│   ├── test_judge.py
│   └── test_verify.py
├── integration/             # API + pipeline E2E
│   ├── test_api_integration.py
│   └── test_api_pipeline_e2e.py
├── performance/             # Load and timing tests
│   ├── test_api_performance.py
│   └── test_cache_monitoring.py
└── mocks/                   # Test fixtures
    ├── database.py
    ├── search_results.py
    └── llm_responses.py
```

## Infrastructure

### Docker Services (docker-compose.yml)
| Service | Port | Purpose |
|---------|------|---------|
| postgres:16 | 5433 | Primary database |
| redis:7 | 6379 | Cache + Celery broker |
| qdrant | 6333 | Vector database |
| minio | 9000/9001 | Local S3 storage |
| flower | 5555 | Celery monitoring |

### External Services
- **Auth:** Clerk (JWT with JWKS caching)
- **Payments:** Stripe + RevenueCat
- **Email:** Resend
- **Push:** Expo notifications
- **Monitoring:** Sentry, Prometheus, OpenTelemetry
- **Analytics:** PostHog

## Development Guidelines

### API Development
- Async-first with `async/await`
- Pydantic models for validation
- Auto-create user on first API call
- Credit refunds on pipeline failure
- Rate limiting per user & IP

### Pipeline Development
- Each stage must be idempotent
- Structured logging throughout
- Circuit breakers for external APIs
- Feature flags for gradual rollout
- Monitor token usage and costs

### Frontend Development
- Mobile-first responsive design
- SSE for real-time progress updates
- React Query for caching
- Shared types from `shared/` package

## Performance Targets
- **Pipeline latency:** <10s for Quick mode
- **API response:** <200ms p95
- **Web Core Vitals:** LCP <2.5s, FID <100ms
- **Mobile app size:** <50MB
- **Token cost:** <$0.02 per check

## Security (Implemented)
- [x] Clerk JWT validation with JWKS caching
- [x] Rate limiting by user & IP
- [x] CORS configuration
- [x] Connection pooling (10 min, 20 max overflow)
- [x] Credit reservation before processing
- [x] Automatic refunds on failure
- [ ] GDPR compliance endpoints (planned)
- [ ] Prompt injection guards (in progress)

## Critical Files

| File | Lines | Purpose |
|------|-------|---------|
| `backend/app/workers/pipeline.py` | 1452 | Celery task orchestration |
| `backend/app/pipeline/judge.py` | 1307 | LLM verdict generation |
| `backend/app/core/config.py` | 232 | Feature flags & settings |
| `backend/app/models/check.py` | 230+ | Database schema |
| `web/lib/api.ts` | 100+ | Backend API client |
| `shared/types/index.ts` | 100+ | Type definitions |

## Deployment

```bash
# Backend (Fly.io)
fly deploy

# Web (Vercel)
vercel --prod

# Mobile (Expo EAS)
eas build --auto-submit
```

## Current Priorities

### Active Development
- Beta feedback collection and iteration
- Source credibility refinements
- Query planning optimization
- Government API coverage expansion

### Next Phases
- Deep mode for comprehensive analysis
- Reverse image search integration
- Long video support (>10 min)
- Light theme option

---
*Tru8 - Production-ready fact-checking platform*
