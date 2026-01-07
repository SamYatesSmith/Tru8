# Tru8 Production Readiness Checklist

> **Purpose:** Track all changes required before deploying to production.
> **Last Updated:** 2025-12-19
> **Status:** Pre-production (Development)

---

## Critical Priority (Must complete before launch)

### 1. Secrets & API Keys

> **URGENT:** Real API keys are currently in `.env` files. These should be rotated before production and managed via secrets manager.

| Secret | Current State | Action Required |
|--------|---------------|-----------------|
| `CLERK_SECRET_KEY` | Test key (`sk_test_*`) | Replace with production key from Clerk dashboard |
| `CLERK_PUBLISHABLE_KEY` | Test key (`pk_test_*`) | Replace with production key |
| `CLERK_JWT_ISSUER` | Dev tenant (`*.clerk.accounts.dev`) | Point to production Clerk instance |
| `STRIPE_SECRET_KEY` | Test key (`sk_test_*`) | Replace with production key |
| `STRIPE_WEBHOOK_SECRET` | Test webhook (`whsec_*`) | Create new production webhook in Stripe |
| `STRIPE_PRICE_ID_PRO` | Test price ID | Create production price in Stripe |
| `SECRET_KEY` | Hardcoded dev key | Generate cryptographically secure key |

**Files affected:**
- `backend/.env`
- `web/.env`
- `mobile/.env`

---

### 2. Environment Mode

| Setting | Dev Value | Production Value | File |
|---------|-----------|------------------|------|
| `ENVIRONMENT` | `development` | `production` | `backend/.env` |
| `DEBUG` | `true` | `false` | `backend/.env` |
| `EXPO_PUBLIC_DEV_CLIENT` | `true` | `false` | `mobile/.env` |

**Impact of DEBUG=false:**
- Disables `/api/docs` OpenAPI documentation
- Disables SQL query logging
- Hides detailed error messages

---

### 3. Database & Infrastructure URLs

| Service | Dev URL | Production Requirement |
|---------|---------|------------------------|
| `DATABASE_URL` | `postgresql+asyncpg://postgres:password@localhost:5433/tru8_dev` | Production Postgres with SSL (`sslmode=require`) |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis with AUTH + TLS |
| `QDRANT_URL` | `http://localhost:6333` | HTTPS endpoint with API key |
| `FRONTEND_URL` | `http://localhost:3000` | `https://app.tru8.com` (or production domain) |

**Database pool settings** (`backend/app/core/database.py`):
- Current: 10 connections + 20 overflow
- Production: Evaluate based on expected traffic; consider PgBouncer

---

### 4. CORS Origins

**Current** (`backend/.env` line 50):
```
CORS_ORIGINS=["http://localhost:3000", "http://localhost:3001", ...]
```

**Production:**
```
CORS_ORIGINS=["https://app.tru8.com", "https://tru8.com"]
```

**Note:** `backend/main.py:49` already handles this conditionally based on `ENVIRONMENT`.

---

### 5. Frontend API URLs

| File | Variable | Dev Value | Production Value |
|------|----------|-----------|------------------|
| `web/.env` | `NEXT_PUBLIC_API_URL` | `http://127.0.0.1:8000` | `https://api.tru8.com` |
| `web/.env` | `NEXT_PUBLIC_API_BASE_URL` | `http://127.0.0.1:8000` | `https://api.tru8.com` |
| `mobile/.env` | `EXPO_PUBLIC_API_URL` | `http://localhost:8000` | `https://api.tru8.com` |

**Hardcoded fallbacks to update:**
- `web/lib/api.ts:1` - fallback URL
- `shared/constants/index.ts:1-2` - fallback URL
- `mobile/services/notifications.ts` - fallback URL

---

## High Priority (Required for stable production)

### 6. Monitoring & Error Tracking

| Service | Current State | Action Required |
|---------|---------------|-----------------|
| `SENTRY_DSN` | Empty | Create Sentry project, add DSN |
| `POSTHOG_API_KEY` | Empty | Create PostHog project, add key |
| `NEXT_PUBLIC_SENTRY_DSN` | Empty | Add to web/.env |
| `NEXT_PUBLIC_POSTHOG_KEY` | Empty | Add to web/.env |

**Implementation ready:** `backend/main.py:57-59` already initializes Sentry when DSN is set.

---

### 7. Email Configuration

| Setting | Dev Value | Production Value |
|---------|-----------|------------------|
| `EMAIL_FROM_ADDRESS` | `onboarding@resend.dev` | Verified domain (e.g., `noreply@tru8.com`) |
| `FEEDBACK_EMAIL` | `samyatessmith@gmail.com` | `support@tru8.com` or similar |

**Domain verification required:** Add DNS records in Resend dashboard for production domain.

---

### 8. API Key Rotation

> These are **real production keys** currently in dev `.env` - rotate before launch:

| Key | Service | Rate Limit |
|-----|---------|------------|
| `OPENAI_API_KEY` | OpenAI GPT-4 | Pay-per-use |
| `GOOGLE_AI_API_KEY` | Google Gemini | Pay-per-use |
| `BRAVE_API_KEY` | Brave Search | Limited |
| `SERP_API_KEY` | SerpAPI | Limited |
| `GOOGLE_FACTCHECK_API_KEY` | Google Fact Check | Limited |
| `S3_ACCESS_KEY` / `S3_SECRET_KEY` | AWS S3 | N/A |
| `RESEND_API_KEY` | Resend Email | Limited |
| `FOOTBALL_DATA_API_KEY` | Football-Data.org | 10 req/min |
| `NOAA_API_KEY` | NOAA Climate | 5 req/sec, 10k/day |
| `ALPHA_VANTAGE_API_KEY` | Alpha Vantage | 25 req/day (free) |
| `MARKETAUX_API_KEY` | Marketaux | 100 req/day (free) |
| `FRED_API_KEY` | Federal Reserve | 120 req/min |
| `WEATHER_API_KEY` | WeatherAPI | 1M req/month |
| `COMPANIES_HOUSE_API_KEY` | UK Companies House | 600 req/5min |
| `GOVINFO_API_KEY` | GovInfo.gov | 5k req/hour |

---

### 9. S3/Storage Configuration

| Setting | Dev Value | Production Value |
|---------|-----------|------------------|
| `S3_BUCKET` | `tru8-uploads` | Production bucket name |
| `S3_ENDPOINT` | `https://s3.eu-north-1.amazonaws.com` | Verify region/endpoint |

**Security:** Ensure bucket policies restrict public access; use signed URLs only.

---

## Medium Priority (Recommended before launch)

### 10. Rate Limiting

| Setting | Dev Value | Notes |
|---------|-----------|-------|
| `RATE_LIMIT_PER_MINUTE` | 60 | Evaluate for production traffic |
| `MAX_CLAIMS_PER_CHECK` | 12 | May need adjustment based on tier |

---

### 11. Pipeline Timeouts

| Setting | Dev Value | Notes |
|---------|-----------|-------|
| `PIPELINE_TIMEOUT_SECONDS` | 180 (3 min) | Adjust based on SLA requirements |
| `CACHE_TTL_SECONDS` | 3600 (1 hour) | May increase for production |
| `LEGAL_API_TIMEOUT_SECONDS` | 10 | Monitor and adjust |

---

### 12. Feature Flags Review

Review these flags for production readiness:

| Flag | Current | Recommendation |
|------|---------|----------------|
| `ENABLE_DEBERTA_NLI` | `true` | Keep - better accuracy |
| `ENABLE_JUDGE_FEW_SHOT` | `true` | Keep - improves verdicts |
| `ENABLE_CROSS_ENCODER_RERANK` | `true` | Keep if performance acceptable |
| `ENABLE_QUERY_PLANNING` | `true` | Keep - better evidence retrieval |
| `ENABLE_RHETORICAL_CONTEXT` | `true` | Keep - handles sarcasm/satire |

---

### 13. Abstention Thresholds

Current values optimized to reduce "uncertain" verdicts:

| Setting | Value | Notes |
|---------|-------|-------|
| `MIN_SOURCES_FOR_VERDICT` | 2 | Lowered from 3 |
| `MIN_CREDIBILITY_THRESHOLD` | 0.60 | Lowered from 0.75 |
| `MIN_CONSENSUS_STRENGTH` | 0.50 | Lowered from 0.65 |

Monitor verdict distribution in production and adjust if needed.

---

## Deployment Configuration (Missing)

### 14. CI/CD Pipeline

**Currently missing - need to create:**

- [ ] `.github/workflows/backend.yml` - Backend CI/CD
- [ ] `.github/workflows/web.yml` - Web frontend CI/CD
- [ ] `fly.toml` - Fly.io backend deployment config
- [ ] `vercel.json` - Vercel web deployment config (or use Vercel auto-detect)

---

### 15. Secrets Management

**Current:** All secrets in `.env` files (not secure for production)

**Recommended approach:**
- Use Fly.io secrets (`fly secrets set KEY=value`)
- Use Vercel environment variables (encrypted)
- Use GitHub Actions secrets for CI/CD
- Consider: AWS Secrets Manager, HashiCorp Vault, or Doppler

---

## Code Changes Required

### 16. Remove Development-Only Code

| File | Line | Issue |
|------|------|-------|
| `backend/app/workers/pipeline.py` | 502, 567-576, 605, 613, 1235, 1310-1335 | Mock verification fallbacks in development mode |
| `backend/app/api/v1/feedback.py` | 146 | Footer says "will be removed in production" |
| `backend/app/services/legal_search.py` | 402-406 | Comments mention production parser needed |

---

### 17. Hardcoded URLs to Environment Variables

| File | Line | Current | Change To |
|------|------|---------|-----------|
| `backend/main.py` | 39-46 | Hardcoded localhost origins | Use `CORS_ORIGINS` only |
| `web/lib/api.ts` | 1 | `'http://localhost:8000'` fallback | Remove fallback or use build-time env |
| `shared/constants/index.ts` | 1-2 | `'http://localhost:8000'` fallback | Remove fallback |

---

## Mobile App Specific

### 18. App Store Preparation

| Item | Status | Notes |
|------|--------|-------|
| Bundle ID | `com.tru8.mobile` | Verify availability in App Store Connect / Play Console |
| RevenueCat | `EXPO_PUBLIC_REVENUECAT_API_KEY` empty | Configure for in-app purchases |
| Deep Links | Not configured | Add for universal links |
| App Icons | Unknown | Verify all sizes provided |
| Privacy Policy | Required | Must be hosted publicly |

---

## Pre-Launch Verification

### 19. Security Checklist

- [ ] All API keys rotated
- [ ] DEBUG mode disabled
- [ ] CORS restricted to production domains
- [ ] Database SSL enabled
- [ ] Redis AUTH enabled
- [ ] No secrets in git history (consider git-filter-repo if needed)
- [ ] Rate limiting configured
- [ ] Error messages don't expose internals

### 20. Performance Checklist

- [ ] Database connection pooling configured
- [ ] Redis caching working
- [ ] CDN configured for static assets
- [ ] Gzip/Brotli compression enabled
- [ ] Image optimization (Next.js Image component)

### 21. Monitoring Checklist

- [ ] Sentry configured and tested
- [ ] PostHog configured and tested
- [ ] Uptime monitoring (e.g., Better Uptime, Pingdom)
- [ ] Log aggregation (e.g., Fly.io logs, Papertrail)
- [ ] Cost alerts for pay-per-use APIs

---

## Quick Reference: Environment Files

```bash
# Backend production .env template
ENVIRONMENT=production
DEBUG=false
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/tru8_prod?sslmode=require
REDIS_URL=rediss://user:pass@host:6379/0
QDRANT_URL=https://your-qdrant-instance.cloud
FRONTEND_URL=https://app.tru8.com
CORS_ORIGINS=["https://app.tru8.com","https://tru8.com"]
CLERK_SECRET_KEY=sk_live_...
STRIPE_SECRET_KEY=sk_live_...
SENTRY_DSN=https://...@sentry.io/...
EMAIL_FROM_ADDRESS=noreply@tru8.com
```

```bash
# Web production .env template
NEXT_PUBLIC_API_URL=https://api.tru8.com
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_live_...
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_live_...
NEXT_PUBLIC_SENTRY_DSN=https://...@sentry.io/...
NEXT_PUBLIC_POSTHOG_KEY=phc_...
```

---

*This checklist should be reviewed and updated as the codebase evolves.*
