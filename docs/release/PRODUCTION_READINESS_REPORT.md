# Tru8 Production Readiness Report

**Generated:** 2026-01-05
**Target:** Public Beta Release
**Prepared by:** Claude Code (Release Manager)

---

## Executive Summary

Tru8 is a fact-checking SaaS platform with a sophisticated ML pipeline. The codebase is **functionally complete** for a public beta, with solid authentication, payments, and core functionality. However, there are **critical gaps in deployment infrastructure** that must be addressed before public release.

### Overall Assessment: **NOT READY** for production
**Estimated effort to reach Ready:** 8-12 tasks (1-2 sprints)

---

## 1. System Map

```
+------------------+        +------------------+        +------------------+
|   CLIENTS        |        |   API GATEWAY    |        |   PROCESSING     |
+------------------+        +------------------+        +------------------+
|                  |        |                  |        |                  |
|  Web (Next.js)   |  HTTPS |  FastAPI         |  Redis |  Background Tasks|
|  localhost:3000  | -----> |  localhost:8000  | -----> |  (async workers) |
|                  |        |                  |        |                  |
|  Mobile (Expo)   |        |  Routes:         |        |  Tasks:          |
|  localhost:8081  |        |  - /api/v1/auth  |        |  - process_check |
|                  |        |  - /api/v1/checks|        |                  |
|  Share Extension |        |  - /api/v1/users |        |  7-Stage Pipeline|
|                  |        |  - /api/v1/pay...| |      |  INGEST->EXTRACT |
+------------------+        +------------------+        |  ->CLASSIFY->PLAN|
                                    |                   |  ->RETRIEVE      |
                                    |                   |  ->VERIFY->JUDGE |
                                    v                   +------------------+
                            +------------------+               |
                            |   DATA LAYER     |               |
                            +------------------+               |
                            |                  |               |
                            |  PostgreSQL 16   | <-------------+
                            |  (port 5433)     |
                            |                  |
                            |  Redis 7         |
                            |  (port 6379)     |
                            |                  |
                            |  Qdrant          |
                            |  (port 6333)     |
                            |                  |
                            +------------------+

+------------------+        +------------------+        +------------------+
|  EXTERNAL APIs   |        |  MONITORING      |        |  AUTH/PAYMENTS   |
+------------------+        +------------------+        +------------------+
|                  |        |                  |        |                  |
|  Brave Search    |        |  Sentry (errors) |        |  Clerk (JWT)     |
|  SerpAPI         |        |  Prometheus      |        |  Stripe          |
|  Google Factcheck|        |  Prometheus      |        |  RevenueCat      |
|  Government APIs:|        |  /metrics        |        |  Resend (email)  |
|  - NOAA          |        |  /health/ready   |        |  Expo Push       |
|  - Alpha Vantage |        |                  |        |                  |
|  - FRED          |        +------------------+        +------------------+
|  - Companies House|
|  - OpenAI/Gemini |
+------------------+
```

### Critical Data Flows

1. **Auth Flow:** Client -> Clerk -> JWT -> Backend validates via JWKS
2. **Check Flow:** POST /checks -> Credit deduction -> Background task -> SSE progress -> DB update
3. **Payment Flow:** Stripe checkout -> Webhook -> Subscription created -> Credits assigned

---

## 2. Risk Map

| # | Risk | Severity | Likelihood | Impact | Mitigation |
|---|------|----------|------------|--------|------------|
| R1 | **No CI/CD pipeline** | CRITICAL | CERTAIN | Deployment failures, no quality gates | Add GitHub Actions |
| R2 | **No Dockerfile** for application | CRITICAL | CERTAIN | Cannot containerize for production | Create Dockerfile |
| R3 | **DEBUG=True default** in production | CRITICAL | HIGH | Exposes debug info, test endpoints | Flip default to False |
| R4 | **Rate limiting not enforced** | HIGH | HIGH | DDoS/abuse vulnerability | Add middleware |
| R5 | **Hardcoded DB URL in alembic.ini** | HIGH | MEDIUM | Credential exposure | Use env vars |
| R6 | **No pip lockfile** | MEDIUM | MEDIUM | Non-deterministic builds | Generate requirements.lock |
| R7 | **S3 storage not implemented** | MEDIUM | MEDIUM | File uploads stored locally | Implement S3 |
| R8 | **No GDPR data export endpoint** | MEDIUM | LOW | Compliance gap | Add /users/me/export |
| R9 | **SSE token via query param** | MEDIUM | MEDIUM | Token exposure in logs | Implement short-lived tokens |
| R10 | **No backup/restore procedure** | HIGH | LOW | Data loss risk | Document & automate |

---

## 3. Audit Findings by Section

### A) Build & Reproducibility

| Area | Status | Finding | Location |
|------|--------|---------|----------|
| README | PASS | Clear setup instructions | `README.md` |
| Python version | PARTIAL | Requires 3.11+ but not pinned | `README.md:8` |
| Node version | PARTIAL | Requires 20+ but not pinned | `README.md:7` |
| pip lockfile | FAIL | No `requirements.lock` | `backend/` |
| npm lockfile | PASS | `package-lock.json` exists | `web/`, `mobile/` |
| Dockerfile | FAIL | No application Dockerfile | Root directory |
| Dev vs prod flags | PARTIAL | DEBUG default=True | `backend/app/core/config.py:61` |

**Recommendations:**
1. Add `requirements.lock` via `pip freeze > requirements.lock`
2. Add `.python-version` file (e.g., `3.11.7`)
3. Add `.nvmrc` file (e.g., `20.10.0`)
4. Create production Dockerfile
5. Change DEBUG default to `False`

---

### B) Configuration & Secrets

| Area | Status | Finding | Location |
|------|--------|---------|----------|
| .env.example | PASS | Comprehensive template | `backend/.env.example` |
| Secrets in git | PASS | `.gitignore` covers all patterns | `.gitignore:1-6` |
| web/.env | PASS | Not tracked in git | Verified via `git ls-files` |
| alembic.ini | FAIL | Hardcoded DB URL | `backend/alembic.ini:40` |
| CORS defaults | PARTIAL | Permissive `allow_methods=["*"]` | `backend/main.py:51` |

**Env Vars Required (Production):**

| Variable | Required | Purpose |
|----------|----------|---------|
| `DATABASE_URL` | Yes | PostgreSQL connection |
| `REDIS_URL` | Yes | Cache + task broker |
| `CLERK_SECRET_KEY` | Yes | JWT validation |
| `CLERK_JWT_ISSUER` | Yes | Token issuer |
| `OPENAI_API_KEY` | Yes | LLM for extraction/judgment |
| `BRAVE_API_KEY` | Recommended | Primary search API |
| `STRIPE_SECRET_KEY` | Yes for payments | Payment processing |
| `SENTRY_DSN` | Recommended | Error tracking |
| `SECRET_KEY` | Yes | Application secret |
| `ENVIRONMENT` | Yes | Must be `production` |
| `DEBUG` | Yes | Must be `false` |
| `CORS_ORIGINS` | Yes | Production domains only |

---

### C) Security Baseline

| Area | Status | Finding | Location |
|------|--------|---------|----------|
| Auth mechanism | PASS | Clerk JWT with JWKS caching | `backend/app/core/auth.py:12-17` |
| Token expiry | PASS | 60s leeway for clock skew | `backend/app/core/auth.py:33` |
| Password storage | N/A | Delegated to Clerk | - |
| Rate limiting | FAIL | Config exists but no middleware | `backend/app/core/config.py:69` |
| CORS | PARTIAL | Permissive in dev, needs prod config | `backend/main.py:47-54` |
| CSRF | PARTIAL | SameSite not explicitly set | Clerk handles |
| Input validation | PASS | Pydantic models for all inputs | All endpoints |
| SQL injection | PASS | SQLModel with parameterized queries | All queries |
| XSS | PASS | JSON responses only (no HTML) | - |
| Dependency vulns | NOT CHECKED | No automated scanning | - |

**Threat Model (Top 5):**

1. **Account Takeover** - Mitigated by Clerk, but monitor for JWT leakage
2. **Credit Abuse** - Rate limiting needed to prevent check-spam
3. **API Key Exposure** - Government/Search API keys in backend only
4. **DDoS on Pipeline** - Task queue could be overwhelmed, add concurrency limits
5. **Prompt Injection** - User queries flow to LLM, add sanitization

**Recommendations:**
1. Add rate limiting middleware (e.g., `slowapi`)
2. Set explicit CORS origins for production
3. Add `pip-audit` to CI pipeline
4. Implement prompt injection guards for user_query field

---

### D) Data & Privacy

| Area | Status | Finding | Location |
|------|--------|---------|----------|
| User data stored | PARTIAL | Email, name, usage stats, checks | `backend/app/models/user.py` |
| PII in logs | RISK | Logger may include user emails | Various |
| Data retention | MISSING | No automated cleanup policy | - |
| Account deletion | PASS | Full cascade delete implemented | `backend/app/api/v1/users.py:414-522` |
| Data export | MISSING | No GDPR export endpoint | - |
| Backups | MISSING | No backup procedure documented | - |

**User Data Inventory:**

| Field | Sensitivity | Retention |
|-------|-------------|-----------|
| `email` | PII | Indefinite |
| `name` | PII | Indefinite |
| `checks.input_url` | Low | Indefinite |
| `checks.input_content` | Medium | May contain personal info |
| `push_token` | Device ID | Until unregistered |

**Recommendations:**
1. Add `GET /api/v1/users/me/export` for GDPR data portability
2. Implement data retention policy (e.g., 12 months for checks)
3. Scrub PII from logs in production
4. Document and automate database backups

---

### E) Database & Migrations

| Area | Status | Finding | Location |
|------|--------|---------|----------|
| Database | PostgreSQL 16 | Production-grade | `docker-compose.yml:4` |
| ORM | SQLModel | Async support | `backend/app/core/database.py` |
| Migrations | Alembic | 22+ migrations present | `backend/alembic/versions/` |
| Connection pooling | PASS | pool_size=10, max_overflow=20 | `backend/app/core/database.py:11-14` |
| Seed data | PARTIAL | Test user in debug mode only | `backend/app/api/v1/checks.py:124-138` |
| Rollback plan | MISSING | No documented procedure | - |

**Migration Files:** 22 migrations from 2025-10 to 2025-12

**Recommendations:**
1. Fix hardcoded URL in `alembic.ini` to use `${DATABASE_URL}`
2. Add pre-deploy migration check to CI
3. Document rollback procedure for each migration
4. Add `alembic check` to CI to detect pending migrations

---

### F) Reliability & Error Handling

| Area | Status | Finding | Location |
|------|--------|---------|----------|
| Global exception handler | MISSING | No FastAPI exception_handler | `backend/main.py` |
| API error format | PARTIAL | HTTPException used but not standardized | Various |
| Task failure handling | PASS | Credit refund on failure | `backend/app/workers/pipeline.py:31-66` |
| Circuit breakers | PASS | Implemented for external APIs | `backend/app/services/circuit_breaker.py` |
| Timeouts | PASS | PIPELINE_TIMEOUT_SECONDS=180 | `backend/app/core/config.py:73` |
| Retry logic | PASS | Task retry + API circuit breakers | - |

**Recommendations:**
1. Add global exception handler returning standardized error format
2. Implement structured error codes (e.g., `TRU8-001`)
3. Add request-id/correlation-id to all responses

---

### G) Observability

| Area | Status | Finding | Location |
|------|--------|---------|----------|
| Logging | PASS | Structured logging with levels | `backend/app/core/logging.py` |
| Log format | PARTIAL | Basic format, no correlation IDs | `backend/app/core/logging.py:26-27` |
| Metrics | PASS | Prometheus endpoint at /metrics | `backend/main.py:62-63` |
| Tracing | PARTIAL | OpenTelemetry deps but not wired | `backend/requirements.txt:51-53` |
| Health checks | PASS | /health and /health/ready | `backend/app/api/v1/health.py` |
| Sentry | PARTIAL | Configured but DSN optional | `backend/main.py:57-59` |

**Recommendations:**
1. Make SENTRY_DSN required for production
2. Add correlation IDs to log format
3. Wire OpenTelemetry for distributed tracing
4. Add custom metrics for pipeline stages

---

### H) Testing Strategy

| Area | Status | Finding | Location |
|------|--------|---------|----------|
| Test structure | PASS | unit/integration/performance | `backend/tests/` |
| Test count | ~50 test files | Good coverage structure | `backend/tests/**/*.py` |
| Fixtures | PASS | Comprehensive fixture library | `backend/tests/fixtures/conftest.py` |
| Mocks | PASS | OpenAI, Search, Redis mocked | `backend/tests/mocks/` |
| CI integration | FAIL | No CI to run tests | - |
| Coverage reporting | PASS | HTML coverage output | `backend/tests/coverage_html/` |

**Test Commands:**
```bash
cd backend
pytest tests/ -v                    # All tests
pytest tests/unit/ -v               # Unit tests only
pytest tests/integration/ -v        # Integration tests
pytest --cov=app tests/             # With coverage
```

**Recommendations:**
1. Add test execution to CI pipeline
2. Set minimum coverage threshold (e.g., 70%)
3. Add smoke tests for critical paths

---

### I) CI/CD Pipeline

| Area | Status | Finding | Location |
|------|--------|---------|----------|
| CI exists | FAIL | No `.github/workflows/` | Root |
| Deployment config | FAIL | No `railway.toml`, `vercel.json` | Root |
| Environment separation | PARTIAL | Config supports it, not automated | - |

**Proposed CI Pipeline:**

```yaml
# .github/workflows/ci.yml
name: CI
on: [push, pull_request]
jobs:
  backend:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16-alpine
      redis:
        image: redis:7-alpine
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install -r backend/requirements.txt
      - run: pip-audit
      - run: cd backend && pytest tests/ -v
      - run: cd backend && alembic check

  web:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
      - run: cd web && npm ci
      - run: cd web && npm run lint
      - run: cd web && npm run typecheck
      - run: cd web && npm run build
```

---

### J) Frontend Production Concerns

| Area | Status | Finding | Location |
|------|--------|---------|----------|
| Build optimization | PASS | Next.js production build | `web/package.json` |
| Source maps | DEFAULT | Not explicitly configured | - |
| Error reporting | MISSING | No frontend Sentry | - |
| API base URL | PASS | Environment variable | `web/lib/api.ts:1` |
| SSR/caching | DEFAULT | No explicit cache strategy | - |
| reactStrictMode | DISABLED | Set to false | `web/next.config.js:3` |
| Image optimization | PASS | Remote patterns configured | `web/next.config.js:4-9` |

**Web Environment Variables:**
```
NEXT_PUBLIC_API_URL=https://api.tru8.com
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_live_...
```

**Recommendations:**
1. Add Sentry to frontend
2. Enable `reactStrictMode` for better error catching
3. Configure explicit caching headers
4. Add web vitals monitoring

---

### K) Documentation for Release

| Area | Status | Finding | Location |
|------|--------|---------|----------|
| README | PASS | Good quickstart | `README.md` |
| API docs | PASS | Auto-generated OpenAPI | `/api/docs` (dev only) |
| Ops runbook | MISSING | No deployment guide | - |
| Architecture | PARTIAL | In CLAUDE.md | `.claude/CLAUDE.md` |
| Troubleshooting | MISSING | No incident playbook | - |

---

## 4. Must Fix Before Public Beta

### P0 - Blockers (Must fix)

| # | Task | Severity | Est. Effort |
|---|------|----------|-------------|
| 1 | Create CI/CD pipeline (GitHub Actions) | CRITICAL | 2-4 hours |
| 2 | Create production Dockerfile | CRITICAL | 1-2 hours |
| 3 | Change DEBUG default to False | CRITICAL | 5 minutes |
| 4 | Add rate limiting middleware | HIGH | 2-4 hours |
| 5 | Fix hardcoded URL in alembic.ini | HIGH | 15 minutes |
| 6 | Configure production CORS origins | HIGH | 30 minutes |

### P1 - Important (Should fix)

| # | Task | Severity | Est. Effort |
|---|------|----------|-------------|
| 7 | Generate requirements.lock | MEDIUM | 15 minutes |
| 8 | Add pip-audit to CI | MEDIUM | 30 minutes |
| 9 | Add Sentry to frontend | MEDIUM | 1-2 hours |
| 10 | Document backup/restore procedure | MEDIUM | 1-2 hours |
| 11 | Add global exception handler | MEDIUM | 1 hour |

### P2 - Nice to have (Can defer)

| # | Task | Severity | Est. Effort |
|---|------|----------|-------------|
| 12 | Implement S3 for file uploads | LOW | 2-4 hours |
| 13 | Add GDPR data export endpoint | LOW | 2-3 hours |
| 14 | Add correlation IDs to logging | LOW | 1-2 hours |
| 15 | Wire OpenTelemetry tracing | LOW | 2-4 hours |

---

## Appendix A: File Reference

| File | Purpose | Lines |
|------|---------|-------|
| `backend/main.py` | FastAPI entry point | 75 |
| `backend/app/core/config.py` | All settings + feature flags | 232 |
| `backend/app/core/auth.py` | JWT verification | 177 |
| `backend/app/core/database.py` | DB connections | 40 |
| `backend/app/workers/pipeline.py` | Background task orchestration | 1452 |
| `backend/app/pipeline/judge.py` | LLM verdict generation | 1307 |
| `web/middleware.ts` | Auth routing | 46 |
| `web/lib/api.ts` | Backend API client | 392 |

---

## Appendix B: Version Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| Python | 3.11 | 3.11.7 |
| Node.js | 20 | 20.10.0 |
| PostgreSQL | 16 | 16-alpine |
| Redis | 7 | 7-alpine |
| Docker | 20.10 | Latest |

---

*Report generated by Claude Code as part of release readiness audit.*
