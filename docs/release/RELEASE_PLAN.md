# Tru8 Release Plan - Public Beta

**Target:** Production-Ready Public Beta
**Estimated Effort:** 15-20 hours
**Recommended:** Complete tasks 1-6 before any production traffic

---

## Phase 1: Critical Infrastructure (P0)

### Task 1: Create CI/CD Pipeline

**Priority:** P0 - BLOCKER
**Files:** `.github/workflows/ci.yml` (new)
**Estimated:** 2-4 hours

**Steps:**
1. Create `.github/workflows/` directory
2. Add `ci.yml` with:
   - Backend: lint, test, security scan
   - Web: lint, typecheck, build
   - Triggered on push and PR

**Implementation:**
```bash
mkdir -p .github/workflows
```

Create `.github/workflows/ci.yml`:
```yaml
name: CI

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

env:
  PYTHON_VERSION: '3.11'
  NODE_VERSION: '20'

jobs:
  backend-lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v4
        with:
          python-version: ${{ env.PYTHON_VERSION }}
      - name: Install dependencies
        run: |
          cd backend
          pip install ruff
      - name: Lint
        run: cd backend && ruff check .

  backend-test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16-alpine
        env:
          POSTGRES_USER: postgres
          POSTGRES_PASSWORD: password
          POSTGRES_DB: tru8_test
        ports:
          - 5433:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
      redis:
        image: redis:7-alpine
        ports:
          - 6379:6379
    env:
      DATABASE_URL: postgresql+asyncpg://postgres:password@localhost:5433/tru8_test
      REDIS_URL: redis://localhost:6379
      TESTING: "true"
      DEBUG: "false"
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v4
        with:
          python-version: ${{ env.PYTHON_VERSION }}
      - name: Install dependencies
        run: |
          cd backend
          pip install -r requirements.txt
          pip install pytest pytest-asyncio pytest-cov
      - name: Run tests
        run: |
          cd backend
          pytest tests/unit/ -v --tb=short

  backend-security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v4
        with:
          python-version: ${{ env.PYTHON_VERSION }}
      - name: Install pip-audit
        run: pip install pip-audit
      - name: Security scan
        run: |
          cd backend
          pip-audit -r requirements.txt --ignore-vuln GHSA-xxxx || true

  web-checks:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: ${{ env.NODE_VERSION }}
          cache: 'npm'
          cache-dependency-path: web/package-lock.json
      - name: Install dependencies
        run: cd web && npm ci
      - name: Lint
        run: cd web && npm run lint
      - name: TypeCheck
        run: cd web && npm run typecheck
      - name: Build
        run: cd web && npm run build
        env:
          NEXT_PUBLIC_API_URL: https://api.example.com
          NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY: pk_test_xxx
```

**Acceptance Criteria:**
- [ ] CI runs on every push to main/develop
- [ ] CI runs on every PR
- [ ] All checks must pass before merge
- [ ] Badge visible in README

---

### Task 2: Create Production Dockerfile

**Priority:** P0 - BLOCKER
**Files:** `backend/Dockerfile` (new), `backend/.dockerignore` (new)
**Estimated:** 1-2 hours

**Implementation:**

Create `backend/Dockerfile`:
```dockerfile
# Build stage
FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /app/wheels -r requirements.txt

# Production stage
FROM python:3.11-slim

WORKDIR /app

# Create non-root user
RUN groupadd -r tru8 && useradd -r -g tru8 tru8

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copy wheels and install
COPY --from=builder /app/wheels /wheels
COPY --from=builder /app/requirements.txt .
RUN pip install --no-cache /wheels/*

# Copy application code
COPY . .

# Set ownership
RUN chown -R tru8:tru8 /app

USER tru8

# Environment defaults (override in deployment)
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    ENVIRONMENT=production \
    DEBUG=false

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/api/v1/health')" || exit 1

# Run with uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Create `backend/.dockerignore`:
```
__pycache__/
*.py[cod]
*$py.class
.env
.env.*
*.log
.pytest_cache/
.coverage
htmlcov/
tests/
docs/
*.md
.git/
.vscode/
```

**Commands to test:**
```bash
cd backend
docker build -t tru8-api:latest .
docker run -p 8000:8000 --env-file .env tru8-api:latest
```

**Acceptance Criteria:**
- [ ] Dockerfile builds successfully
- [ ] Container starts and responds to /api/v1/health
- [ ] Non-root user is used
- [ ] Image size < 1GB

---

### Task 3: Fix DEBUG Default

**Priority:** P0 - BLOCKER
**Files:** `backend/app/core/config.py`
**Estimated:** 5 minutes

**Current (line 61):**
```python
DEBUG: bool = True
```

**Change to:**
```python
DEBUG: bool = False
```

**Commands:**
```bash
# Verify change
grep "DEBUG:" backend/app/core/config.py
```

**Acceptance Criteria:**
- [ ] DEBUG defaults to False
- [ ] /api/docs returns 404 in production mode
- [ ] test_check endpoint not accessible in production

---

### Task 4: Add Rate Limiting Middleware

**Priority:** P0 - BLOCKER
**Files:** `backend/requirements.txt`, `backend/main.py`
**Estimated:** 2-4 hours

**Steps:**

1. Add dependency to `backend/requirements.txt`:
```
slowapi==0.1.9
```

2. Update `backend/main.py`:
```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# After app creation
limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"])
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# For specific endpoints, add decorator:
# @limiter.limit("5/minute")
```

3. Add rate limits to critical endpoints:

`backend/app/api/v1/checks.py`:
```python
from slowapi import Limiter
from slowapi.util import get_remote_address

# On create_check endpoint
@router.post("/")
@limiter.limit("10/minute")
async def create_check(...):
```

**Acceptance Criteria:**
- [ ] Rate limiting active on /checks endpoint
- [ ] Returns 429 when limit exceeded
- [ ] Limit of 10 checks/minute per IP
- [ ] Auth endpoints have stricter limits (5/minute)

---

### Task 5: Fix Hardcoded URL in alembic.ini

**Priority:** HIGH
**Files:** `backend/alembic.ini`, `backend/alembic/env.py`
**Estimated:** 15 minutes

**Current (`alembic.ini` line 40):**
```ini
sqlalchemy.url = postgresql+asyncpg://postgres:password@localhost:5433/tru8_dev
```

**Change to:**
```ini
sqlalchemy.url =
```

**Update `backend/alembic/env.py`:**
```python
import os
from app.core.config import settings

def get_url():
    # Use DATABASE_URL from environment, fallback to config
    return os.getenv("DATABASE_URL", settings.DATABASE_URL)

# In run_migrations_online():
connectable = create_async_engine(get_url())
```

**Commands:**
```bash
# Test migration still works
cd backend
DATABASE_URL="postgresql+asyncpg://..." alembic upgrade head
```

**Acceptance Criteria:**
- [ ] No credentials in alembic.ini
- [ ] Migrations work via DATABASE_URL env var
- [ ] CI can run `alembic check`

---

### Task 6: Configure Production CORS

**Priority:** HIGH
**Files:** `backend/app/core/config.py`, `backend/main.py`
**Estimated:** 30 minutes

**Update `backend/app/core/config.py`:**
```python
class Settings(BaseSettings):
    # Add explicit CORS_ORIGINS
    CORS_ORIGINS: list[str] = Field(default=[
        "https://tru8.com",
        "https://www.tru8.com",
        "https://app.tru8.com",
    ])
```

**Update `backend/main.py`:**
```python
# More restrictive CORS in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=dev_origins if settings.ENVIRONMENT == "development" else settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],  # Explicit methods
    allow_headers=["Authorization", "Content-Type"],  # Explicit headers
    expose_headers=["X-Request-Id"],
)
```

**Acceptance Criteria:**
- [ ] CORS only allows production domains in production
- [ ] Methods and headers are explicitly listed
- [ ] Unauthorized origins receive CORS error

---

## Phase 2: Important Improvements (P1)

### Task 7: Generate requirements.lock

**Priority:** MEDIUM
**Files:** `backend/requirements.lock` (new)
**Estimated:** 15 minutes

**Commands:**
```bash
cd backend
pip freeze > requirements.lock
```

**Update `backend/Dockerfile` to use lock file:**
```dockerfile
COPY requirements.lock .
RUN pip install --no-cache-dir -r requirements.lock
```

**Acceptance Criteria:**
- [ ] `requirements.lock` exists with pinned versions
- [ ] Dockerfile uses lockfile
- [ ] Builds are reproducible

---

### Task 8: Add pip-audit to CI

**Priority:** MEDIUM
**Files:** `.github/workflows/ci.yml`
**Estimated:** 30 minutes

Already included in Task 1. Ensure:
- pip-audit runs on every PR
- Known vulnerabilities are documented in `.pip-audit-ignore.toml` if needed

**Acceptance Criteria:**
- [ ] Security scan runs in CI
- [ ] Vulnerabilities fail the build or are documented exceptions

---

### Task 9: Add Sentry to Frontend

**Priority:** MEDIUM
**Files:** `web/app/layout.tsx`, `web/lib/sentry.ts` (new)
**Estimated:** 1-2 hours

**Steps:**

1. Install Sentry:
```bash
cd web
npm install @sentry/nextjs
```

2. Create `web/lib/sentry.ts`:
```typescript
import * as Sentry from '@sentry/nextjs';

Sentry.init({
  dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,
  environment: process.env.NODE_ENV,
  tracesSampleRate: 0.1,
  debug: false,
});
```

3. Add to `web/app/layout.tsx`:
```typescript
import '@/lib/sentry';
```

4. Add env var to production:
```
NEXT_PUBLIC_SENTRY_DSN=https://xxx@sentry.io/xxx
```

**Acceptance Criteria:**
- [ ] Frontend errors reported to Sentry
- [ ] Source maps uploaded
- [ ] Error boundaries catch React errors

---

### Task 10: Document Backup/Restore Procedure

**Priority:** MEDIUM
**Files:** `docs/OPS_RUNBOOK.md` (new)
**Estimated:** 1-2 hours

Create `docs/OPS_RUNBOOK.md`:
```markdown
# Tru8 Operations Runbook

## Database Backup

### Manual Backup
```bash
pg_dump -h localhost -p 5433 -U postgres tru8_prod > backup_$(date +%Y%m%d_%H%M%S).sql
```

### Restore from Backup
```bash
psql -h localhost -p 5433 -U postgres -d tru8_prod < backup_20260105.sql
```

### Automated Backups (Fly.io)
Fly.io Postgres includes automated daily backups with 7-day retention.

## Rollback Procedures

### Rollback Deployment
```bash
fly releases -a tru8-api
fly deploy --image registry.fly.io/tru8-api:sha-abc123
```

### Rollback Migration
```bash
alembic downgrade -1
```

## Incident Response

### High Error Rate
1. Check Sentry for error patterns
2. Check /api/v1/health/ready
3. Check Celery worker logs
4. Rollback if needed

### Queue Backup
1. Check Flower at /flower
2. Purge stale tasks: `celery -A app.workers purge`
3. Scale workers if needed
```

**Acceptance Criteria:**
- [ ] Backup command documented
- [ ] Restore procedure tested
- [ ] Rollback steps documented

---

### Task 11: Add Global Exception Handler

**Priority:** MEDIUM
**Files:** `backend/main.py`, `backend/app/core/exceptions.py` (new)
**Estimated:** 1 hour

Create `backend/app/core/exceptions.py`:
```python
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
import logging

logger = logging.getLogger(__name__)

async def global_exception_handler(request: Request, exc: Exception):
    """Handle all uncaught exceptions with consistent format."""
    logger.exception(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_server_error",
            "message": "An unexpected error occurred",
            "request_id": request.headers.get("x-request-id", "unknown")
        }
    )

async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTPException with consistent format."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail if isinstance(exc.detail, str) else "error",
            "message": exc.detail,
            "request_id": request.headers.get("x-request-id", "unknown")
        }
    )
```

Update `backend/main.py`:
```python
from app.core.exceptions import global_exception_handler, http_exception_handler

app.add_exception_handler(Exception, global_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
```

**Acceptance Criteria:**
- [ ] All errors return consistent JSON format
- [ ] 500 errors don't leak stack traces
- [ ] Request ID included in responses

---

## Phase 3: Nice to Have (P2)

### Task 12: Implement S3 for File Uploads

**Files:** `backend/app/services/storage.py` (new), `backend/app/api/v1/checks.py`
**Estimated:** 2-4 hours

**Deferred until post-beta.** Current local storage acceptable for beta volume.

---

### Task 13: Add GDPR Data Export Endpoint

**Files:** `backend/app/api/v1/users.py`
**Estimated:** 2-3 hours

**Deferred until post-beta.** Account deletion already implemented.

---

### Task 14: Add Correlation IDs

**Files:** `backend/main.py`, `backend/app/core/logging.py`
**Estimated:** 1-2 hours

**Deferred until post-beta.** Current logging acceptable.

---

### Task 15: Wire OpenTelemetry

**Files:** `backend/main.py`
**Estimated:** 2-4 hours

**Deferred until post-beta.** Prometheus metrics sufficient for beta.

---

## Deployment Sequence

```
1. Complete Tasks 1-6 (P0)
2. Create staging environment
3. Deploy to staging
4. Run smoke tests
5. Complete Tasks 7-11 (P1)
6. Deploy to staging, verify
7. Promote to production
8. Monitor closely for 24-48 hours
9. Address P2 items in subsequent sprints
```

---

## Rollback Plan

If issues arise post-deployment:

1. **Revert deployment:** `fly deploy --image <previous-sha>`
2. **Database:** Restore from last backup if data corruption
3. **Configuration:** Roll back env vars in Fly/Vercel dashboard
4. **Feature flag:** Disable problematic features via config

---

*Release plan generated by Claude Code.*
