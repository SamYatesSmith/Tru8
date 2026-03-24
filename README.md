# Tru8 — AI-Powered Evidence Research Platform

Tru8 organises evidence so you can decide what matters. Submit a claim or URL, and Tru8 retrieves evidence from 30+ sources, classifies it by tier (primary / reporting / commentary) and type (data / official / news / analysis / opinion / academic), decomposes claims into elements, maps evidence to those elements, and presents the full landscape — structured, not summarised.

**Mission:** "We organise; you decide."

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.11+
- Node.js 20+

### 1. Start Infrastructure

```bash
docker-compose up -d    # PostgreSQL 16, Redis 7, Qdrant
```

### 2. Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate    # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # Edit with your API keys
alembic upgrade head
uvicorn app.main:app --reload    # http://localhost:8000
```

### 3. Frontend

```bash
cd web
npm install
npm run dev    # http://localhost:3000
```

## Project Structure

```
tru8/
├── backend/              # FastAPI backend + evidence pipeline
│   ├── app/
│   │   ├── api/v1/       # REST endpoints (checks, agent, verify, payments)
│   │   ├── core/         # Config, auth, pricing, manifest signing
│   │   ├── models/       # SQLModel schemas (Check, Claim, Evidence, ClaimConsensus)
│   │   ├── pipeline/     # Two-phase evidence pipeline
│   │   ├── services/     # API adapters, search, payments, consensus
│   │   └── utils/        # Classifiers, deduplication, query planning
│   ├── alembic/          # Database migrations
│   ├── tru8_mcp/         # MCP server package for AI agents
│   └── tests/            # 990 unit + integration tests
├── web/                  # Next.js 14 frontend
│   ├── app/              # Pages (dashboard, developers, public reports)
│   ├── components/       # Evidence views, claim map, marketing
│   └── lib/              # API client, tiers, diagnostics
├── shared/               # Shared TypeScript types
├── docker-compose.yml    # PostgreSQL, Redis, Qdrant, MinIO (optional)
└── .claude/CLAUDE.md     # Full engineering context
```

## Pipeline

Two-phase pipeline with user claim selection gate (article mode):

```
Phase 1:  Ingest → Extract claims → Classify article → Rank claims
          [PAUSE — user selects claims]

Phase 2:  Fact-check lookup → Decompose into elements → Retrieve evidence →
          Score relevance → Classify tier/type → Map evidence to elements →
          Derive orientation → Complete

Post:     Coverage recovery (Stage 5.1), video recommendations, auto-archiving
```

Evidence flows through 30+ source adapters:

| Category | Sources |
|----------|---------|
| Web search | Serper.dev, Brave Search, SerpAPI (fallback chain) |
| Fact-check | Google Fact-Check API |
| Government | GOV.UK, Hansard, GovInfo, Companies House, ONS |
| Legal | UK Legislation (legislation.gov.uk) |
| Economic | FRED, Marketaux, World Bank |
| Academic | Semantic Scholar, OpenAlex, PubMed |
| Climate | NOAA, WeatherAPI, Open-Meteo, GBIF |
| Archives | Wikipedia (+ reference mining), Library of Congress, Internet Archive |
| Health | WHO |
| Sports | Transfermarkt, Football-Data.org |
| Video | YouTube Data API |

## Six Evidence Views

| View | Question it answers |
|------|-------------------|
| Cartographer | What's the shape of this conversation? |
| Librarian | Is this the full set, clearly labelled? |
| Interpreter | Does this evidence answer this sub-question? |
| Projectionist | What's been said on camera? |
| Chronologist | When did the evidence appear? |
| Seeker | What don't we know yet? |

## API & Agent Access

Tru8 exposes a developer API and MCP server for AI agents.

### Agent Commerce Gateway

```bash
# Quick check (~15s, heuristic classification)
curl -X POST https://api.trueight.com/api/v1/agent/quick \
  -H "X-API-Key: $TRU8_API_KEY" \
  -d '{"claim": "UK inflation is 3.2%"}'

# Smart endpoint with tier fallback (lookup → consensus → quick → full)
curl -X POST https://api.trueight.com/api/v1/agent/check \
  -H "X-API-Key: $TRU8_API_KEY" \
  -d '{"claim": "UK inflation is 3.2%", "max_tier": "full"}'
```

| Tier | Cost | Time | What you get |
|------|------|------|-------------|
| Lookup | ~£0.02 | instant | Cached prior analysis |
| Consensus | ~£0.03 | instant | Cross-user aggregate landscape (k>=3 checks) |
| Quick | ~£0.07 | ~15s | Web search + heuristic classification |
| Full | ~£0.15 | ~60-90s | 30+ sources, LLM classification, element decomposition |

Three payment rails: x402 (USDC/SIWE), Skyfire (JWT), prepaid credits.

### MCP Server

```json
{
  "mcpServers": {
    "tru8": {
      "command": "python",
      "args": ["-m", "tru8_mcp"],
      "env": { "TRU8_API_KEY": "tru8_sk_..." }
    }
  }
}
```

Tools: `tru8_check` (evidence research with tier fallback), `tru8_get_result` (with analytics), `tru8_get_result_raw`.

### Manifest Verification

Every completed check receives an HMAC-SHA256 signed manifest. Verify tamper-evidence:

```bash
curl https://api.trueight.com/api/v1/verify/{check_id}
```

## Testing

```bash
cd backend
pytest tests/ -v                        # Full suite (990 tests)
pytest tests/unit/pipeline/ -v          # Pipeline unit tests
pytest tests/unit/agent/ -v             # Agent/commerce tests
pytest tests/integration/ -v            # Integration tests
```

## Infrastructure

| Service | Port | Purpose |
|---------|------|---------|
| PostgreSQL 16 | 5433 | Primary database (SQLModel) |
| Redis 7 | 6379 | Cache + rate limiting |
| Qdrant | 6333 | Vector similarity search |
| MinIO (optional) | 9000 | Local S3 for file uploads |

Auth: Clerk (JWT + JWKS) for dashboard, API keys for developer access.
Payments: Stripe (4 subscription tiers) + Agent per-use payments.

## API Documentation

- **Swagger UI:** http://localhost:8000/api/docs
- **ReDoc:** http://localhost:8000/api/redoc
- **Health:** http://localhost:8000/api/v1/health/

## Environment Variables

Copy `backend/.env.example` to `backend/.env`. Key groups:

| Group | Required | Variables |
|-------|----------|-----------|
| Database | Yes | `DATABASE_URL` |
| Redis | Yes | `REDIS_URL` |
| Auth | Yes | `CLERK_SECRET_KEY`, `CLERK_JWT_ISSUER` |
| LLM | Yes | `GOOGLE_AI_API_KEY`, `OPENAI_API_KEY` |
| Search | Yes (at least one) | `SERPER_API_KEY`, `BRAVE_API_KEY`, `SERP_API_KEY` |
| Payments | For subscriptions | `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET` |
| Government APIs | Optional | `FRED_API_KEY`, `NOAA_API_KEY`, etc. |
| Manifest signing | Optional | `MANIFEST_SIGNING_ENABLED`, `MANIFEST_SIGNING_KEY` |

Feature flags (all default to sensible values): `ENABLE_API_RETRIEVAL`, `ENABLE_LLM_RELEVANCE_SCORER`, `ENABLE_QUERY_PLANNING`, etc. See `backend/.env.example` for the full list.

## Licence

Private — All rights reserved.
