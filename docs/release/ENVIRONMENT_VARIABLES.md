# Tru8 Environment Variables

Complete reference for all environment variables across backend, web, and mobile.

---

## Backend Environment Variables

### Core Configuration

| Variable | Required | Default | Purpose | Example |
|----------|----------|---------|---------|---------|
| `ENVIRONMENT` | Yes | `development` | Environment mode | `production`, `staging`, `development` |
| `DEBUG` | Yes | `False` | Enable debug mode | `false` |
| `SECRET_KEY` | Yes | - | Application secret key | `your-super-secret-key-here` |
| `LOG_LEVEL` | No | `INFO` | Logging level | `DEBUG`, `INFO`, `WARNING`, `ERROR` |

### Database

| Variable | Required | Default | Purpose | Example |
|----------|----------|---------|---------|---------|
| `DATABASE_URL` | Yes | - | PostgreSQL connection string | `postgresql+asyncpg://user:pass@host:5432/db` |
| `DATABASE_POOL_SIZE` | No | `10` | Connection pool size | `10` |
| `DATABASE_MAX_OVERFLOW` | No | `20` | Max overflow connections | `20` |

### Cache & Message Queue

| Variable | Required | Default | Purpose | Example |
|----------|----------|---------|---------|---------|
| `REDIS_URL` | Yes | - | Redis connection string | `redis://localhost:6379` |
| `REDIS_TTL` | No | `3600` | Default cache TTL (seconds) | `3600` |

### Authentication (Clerk)

| Variable | Required | Default | Purpose | Example |
|----------|----------|---------|---------|---------|
| `CLERK_SECRET_KEY` | Yes | - | Clerk backend secret | `sk_live_xxxx` |
| `CLERK_JWT_ISSUER` | Yes | - | JWT issuer for validation | `https://your-app.clerk.accounts.dev` |
| `CLERK_JWKS_URL` | No | Auto | JWKS endpoint | Auto-derived from issuer |

### LLM & AI

| Variable | Required | Default | Purpose | Example |
|----------|----------|---------|---------|---------|
| `OPENAI_API_KEY` | Yes* | - | OpenAI API key for GPT | `sk-xxxx` |
| `GEMINI_API_KEY` | No | - | Google Gemini API key | `AIza...` |
| `LLM_PROVIDER` | No | `openai` | LLM provider to use | `openai`, `gemini` |
| `LLM_MODEL` | No | `gpt-4o` | Model name | `gpt-4o`, `gpt-4o-mini` |

### Search APIs

| Variable | Required | Default | Purpose | Example |
|----------|----------|---------|---------|---------|
| `BRAVE_API_KEY` | Recommended | - | Brave Search API | `BSA_xxxx` |
| `SERP_API_KEY` | No | - | SerpAPI for Google search | `xxxx` |
| `GOOGLE_FACTCHECK_API_KEY` | No | - | Google Fact Check API | `AIza...` |

### Government APIs

| Variable | Required | Default | Purpose | Example |
|----------|----------|---------|---------|---------|
| `NOAA_API_TOKEN` | No | - | NOAA weather/climate data | `xxxx` |
| `ALPHA_VANTAGE_API_KEY` | No | - | Stock/forex data | `xxxx` |
| `FRED_API_KEY` | No | - | Federal Reserve economic data | `xxxx` |
| `FOOTBALL_DATA_API_KEY` | No | - | Football statistics | `xxxx` |
| `WEATHER_API_KEY` | No | - | Weather data | `xxxx` |
| `COMPANIES_HOUSE_API_KEY` | No | - | UK company data | `xxxx` |
| `CONGRESS_API_KEY` | No | - | US Congress data | `xxxx` |

### Payments (Stripe)

| Variable | Required | Default | Purpose | Example |
|----------|----------|---------|---------|---------|
| `STRIPE_SECRET_KEY` | Yes for payments | - | Stripe backend key | `sk_live_xxxx` |
| `STRIPE_WEBHOOK_SECRET` | Yes for payments | - | Webhook signature verification | `whsec_xxxx` |
| `STRIPE_PRICE_ID_STARTER` | No | - | Starter plan price ID | `price_xxxx` |
| `STRIPE_PRICE_ID_PRO` | No | - | Pro plan price ID | `price_xxxx` |

### Notifications

| Variable | Required | Default | Purpose | Example |
|----------|----------|---------|---------|---------|
| `RESEND_API_KEY` | No | - | Email notifications | `re_xxxx` |
| `RESEND_FROM_EMAIL` | No | `noreply@tru8.com` | Sender email | `noreply@tru8.com` |
| `FEEDBACK_EMAIL` | No | - | Feedback email recipient | `feedback@tru8.com` |

### Monitoring

| Variable | Required | Default | Purpose | Example |
|----------|----------|---------|---------|---------|
| `SENTRY_DSN` | Recommended | - | Sentry error tracking | `https://xxx@sentry.io/xxx` |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | No | - | OpenTelemetry endpoint | `http://localhost:4317` |

### Vector Database

| Variable | Required | Default | Purpose | Example |
|----------|----------|---------|---------|---------|
| `QDRANT_URL` | No | `http://localhost:6333` | Qdrant vector DB | `http://localhost:6333` |
| `QDRANT_API_KEY` | No | - | Qdrant API key (cloud) | `xxxx` |

### Security

| Variable | Required | Default | Purpose | Example |
|----------|----------|---------|---------|---------|
| `CORS_ORIGINS` | Yes for prod | See default | Allowed CORS origins | `["https://tru8.com"]` |
| `RATE_LIMIT_PER_MINUTE` | No | `100` | API rate limit | `100` |
| `CHECK_RATE_LIMIT_PER_MINUTE` | No | `10` | Check creation rate limit | `10` |

### Feature Flags

| Variable | Required | Default | Purpose | Example |
|----------|----------|---------|---------|---------|
| `ENABLE_API_RETRIEVAL` | No | `true` | Enable government APIs | `true` |
| `ENABLE_DEEP_MODE` | No | `false` | Enable deep analysis mode | `false` |
| `MAX_CLAIMS_PER_CHECK` | No | `12` | Maximum claims to extract | `12` |

### Pipeline Configuration

| Variable | Required | Default | Purpose | Example |
|----------|----------|---------|---------|---------|
| `PIPELINE_TIMEOUT_SECONDS` | No | `180` | Task timeout | `180` |
| `NLI_CONFIDENCE_THRESHOLD` | No | `0.7` | NLI minimum confidence | `0.7` |
| `SOURCE_CREDIBILITY_THRESHOLD` | No | `0.65` | Minimum source credibility | `0.65` |
| `MIN_SOURCES_FOR_VERDICT` | No | `2` | Minimum sources required | `2` |

---

## Web Frontend Environment Variables

| Variable | Required | Default | Purpose | Example |
|----------|----------|---------|---------|---------|
| `NEXT_PUBLIC_API_URL` | Yes | `http://localhost:8000` | Backend API URL | `https://api.trueight.com` |
| `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` | Yes | - | Clerk frontend key | `pk_live_xxxx` |
| `NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY` | Yes for payments | - | Stripe frontend key | `pk_live_xxxx` |
| `NEXT_PUBLIC_SUBSCRIPTIONS_ENABLED` | No | `false` | Enable paid subscriptions | `true` or `false` |
| `NEXT_PUBLIC_SENTRY_DSN` | Recommended | - | Frontend error tracking | `https://xxx@sentry.io/xxx` |
| `NEXT_PUBLIC_POSTHOG_KEY` | No | - | PostHog analytics | `phc_xxxx` |

---

## Mobile Environment Variables

| Variable | Required | Default | Purpose | Example |
|----------|----------|---------|---------|---------|
| `EXPO_PUBLIC_API_URL` | Yes | - | Backend API URL | `https://api.tru8.com` |
| `EXPO_PUBLIC_CLERK_PUBLISHABLE_KEY` | Yes | - | Clerk frontend key | `pk_live_xxxx` |
| `EXPO_PUBLIC_REVENUECAT_API_KEY` | Yes for payments | - | RevenueCat key | `xxxx` |

---

## Environment-Specific Values

### Development

```env
# backend/.env
ENVIRONMENT=development
DEBUG=true
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5433/tru8_dev
REDIS_URL=redis://localhost:6379
SECRET_KEY=dev-secret-key-not-for-production
CLERK_SECRET_KEY=sk_test_xxxx
CLERK_JWT_ISSUER=https://dev-xxx.clerk.accounts.dev
OPENAI_API_KEY=sk-xxxx
BRAVE_API_KEY=BSA_xxxx
```

```env
# web/.env.local
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_xxxx
```

### Staging

```env
# backend (Fly.io secrets)
ENVIRONMENT=staging
DEBUG=false
DATABASE_URL=postgresql+asyncpg://xxx:xxx@xxx-db.internal:5432/tru8_staging
REDIS_URL=redis://xxx:xxx@xxx-redis.internal:6379
SECRET_KEY=staging-secret-key
CLERK_SECRET_KEY=sk_test_xxxx
CLERK_JWT_ISSUER=https://staging-xxx.clerk.accounts.dev
SENTRY_DSN=https://xxx@sentry.io/xxx
CORS_ORIGINS=["https://staging.tru8.com"]
```

### Production

```env
# backend (Fly.io secrets)
ENVIRONMENT=production
DEBUG=false
DATABASE_URL=postgresql+asyncpg://xxx:xxx@xxx-db.internal:5432/tru8_prod
REDIS_URL=redis://xxx:xxx@xxx-redis.internal:6379
SECRET_KEY=<strong-random-key>
CLERK_SECRET_KEY=sk_live_xxxx
CLERK_JWT_ISSUER=https://clerk.tru8.com
SENTRY_DSN=https://xxx@sentry.io/xxx
CORS_ORIGINS=["https://tru8.com","https://www.tru8.com","https://app.tru8.com"]
STRIPE_SECRET_KEY=sk_live_xxxx
STRIPE_WEBHOOK_SECRET=whsec_xxxx
RESEND_API_KEY=re_xxxx
```

---

## Where Variables Are Used

| Variable | File(s) |
|----------|---------|
| `DATABASE_URL` | `backend/app/core/database.py:8` |
| `REDIS_URL` | `backend/app/workers/__init__.py:27`, `backend/app/services/cache.py` |
| `CLERK_SECRET_KEY` | `backend/app/core/auth.py:12` |
| `OPENAI_API_KEY` | `backend/app/pipeline/extract.py`, `backend/app/pipeline/judge.py` |
| `SENTRY_DSN` | `backend/main.py:57` |
| `STRIPE_SECRET_KEY` | `backend/app/api/v1/users.py:16`, `backend/app/api/v1/payments.py` |
| `NEXT_PUBLIC_API_URL` | `web/lib/api.ts:1` |

---

## Validation Checklist

Before deploying to production, verify:

- [ ] `ENVIRONMENT=production`
- [ ] `DEBUG=false`
- [ ] `SECRET_KEY` is strong and unique
- [ ] `DATABASE_URL` points to production database
- [ ] `CORS_ORIGINS` lists only production domains
- [ ] `SENTRY_DSN` is configured for production project
- [ ] All `*_live_*` keys are used (not `*_test_*`)
- [ ] `STRIPE_WEBHOOK_SECRET` is set up in Stripe dashboard

---

## Generating Secrets

```bash
# Generate a secure SECRET_KEY
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Verify required vars are set
echo "DATABASE_URL: ${DATABASE_URL:?Required}"
echo "REDIS_URL: ${REDIS_URL:?Required}"
echo "CLERK_SECRET_KEY: ${CLERK_SECRET_KEY:?Required}"
```

---

*Environment variables reference generated by Claude Code.*
