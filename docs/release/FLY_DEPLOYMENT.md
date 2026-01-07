# Fly.io Deployment Guide

**Purpose:** Deploy Tru8 API backend to Fly.io for beta testing

---

## Prerequisites

1. **Fly.io Account:** https://fly.io/app/sign-up
2. **Fly CLI installed:**
   ```bash
   # Windows (PowerShell)
   powershell -Command "iwr https://fly.io/install.ps1 -useb | iex"

   # macOS
   brew install flyctl

   # Linux
   curl -L https://fly.io/install.sh | sh
   ```
3. **Logged in:**
   ```bash
   fly auth login
   ```

---

## Quick Deploy (First Time)

### Step 1: Launch the App

```bash
cd backend
fly launch --no-deploy
```

When prompted:
- **App name:** `trueight-api` (or your preferred name)
- **Region:** `lhr` (London) - or closest to your users
- **PostgreSQL:** Yes, create one
- **Redis:** Yes, create one (via Upstash)

### Step 2: Create PostgreSQL Database

```bash
fly postgres create --name trueight-db --region lhr
fly postgres attach trueight-db --app trueight-api
```

This automatically sets `DATABASE_URL` secret.

### Step 3: Create Redis

```bash
fly redis create --name trueight-redis --region lhr
```

Note the connection URL provided.

### Step 4: Set Secrets

```bash
# Core secrets (REQUIRED)
fly secrets set \
  SECRET_KEY="your-production-secret-key-min-32-chars" \
  REDIS_URL="redis://your-redis-url-from-step-3"

# Clerk Authentication (REQUIRED)
fly secrets set \
  CLERK_SECRET_KEY="sk_live_your_clerk_secret" \
  CLERK_PUBLISHABLE_KEY="pk_live_your_clerk_publishable" \
  CLERK_JWT_ISSUER="your-clerk-issuer.clerk.accounts.dev"

# Email (REQUIRED for feedback/waitlist)
fly secrets set \
  RESEND_API_KEY="re_your_resend_key" \
  FEEDBACK_EMAIL="sam@trueight.com" \
  EMAIL_FROM_ADDRESS="hello@trueight.com"

# LLM APIs (REQUIRED)
fly secrets set \
  OPENAI_API_KEY="sk-your-openai-key"

# Search APIs (REQUIRED)
fly secrets set \
  BRAVE_API_KEY="BSA_your_brave_key" \
  SERP_API_KEY="your_serp_key" \
  GOOGLE_FACTCHECK_API_KEY="your_google_key"

# Stripe (optional for beta - subscriptions disabled)
fly secrets set \
  STRIPE_SECRET_KEY="sk_test_your_stripe_key" \
  STRIPE_WEBHOOK_SECRET="whsec_your_webhook_secret" \
  STRIPE_PRICE_ID_PRO="price_your_price_id"

# Government APIs (optional - enhances fact-checking)
fly secrets set \
  GOVINFO_API_KEY="your_govinfo_key" \
  NOAA_API_KEY="your_noaa_key" \
  ALPHA_VANTAGE_API_KEY="your_alphavantage_key" \
  FRED_API_KEY="your_fred_key" \
  WEATHER_API_KEY="your_weather_key" \
  FOOTBALL_DATA_API_KEY="your_football_data_key" \
  COMPANIES_HOUSE_API_KEY="your_companies_house_key"

# Beta testers (optional)
fly secrets set \
  BETA_TESTER_EMAILS='["tester1@example.com","tester2@example.com"]'

# Frontend URL for CORS
fly secrets set \
  FRONTEND_URL="https://trueight.com" \
  CORS_ORIGINS='["https://trueight.com","https://www.trueight.com"]'
```

### Step 5: Run Database Migrations

```bash
# SSH into the app to run migrations
fly ssh console --app trueight-api

# Inside the container:
cd /app
alembic upgrade head
exit
```

### Step 6: Deploy

```bash
fly deploy
```

### Step 7: Verify

```bash
# Check status
fly status

# View logs
fly logs

# Test health endpoint
curl https://trueight-api.fly.dev/api/v1/health
```

---

## Subsequent Deployments

After initial setup, deploy changes with:

```bash
cd backend
fly deploy
```

---

## Useful Commands

```bash
# View app status
fly status

# Stream logs
fly logs

# SSH into container
fly ssh console

# Scale up (more memory/CPU)
fly scale vm shared-cpu-2x --memory 2048

# Scale horizontally (multiple instances)
fly scale count 2

# View secrets (names only, not values)
fly secrets list

# Update a secret
fly secrets set KEY=value

# Open app in browser
fly open

# View metrics
fly dashboard
```

---

## Environment Variables Reference

### Set via `fly.toml` (non-sensitive)

| Variable | Value | Description |
|----------|-------|-------------|
| ENVIRONMENT | production | Runtime environment |
| DEBUG | false | Disable debug mode |
| SUBSCRIPTIONS_ENABLED | false | Beta: payments disabled |
| ENABLE_* | true/false | Feature flags |

### Set via `fly secrets` (sensitive)

| Secret | Required | Description |
|--------|----------|-------------|
| SECRET_KEY | Yes | App secret (32+ chars) |
| DATABASE_URL | Auto | Set by postgres attach |
| REDIS_URL | Yes | Redis connection string |
| CLERK_SECRET_KEY | Yes | Clerk backend key |
| CLERK_PUBLISHABLE_KEY | Yes | Clerk frontend key |
| CLERK_JWT_ISSUER | Yes | Clerk JWT issuer URL |
| OPENAI_API_KEY | Yes | OpenAI API key |
| RESEND_API_KEY | Yes | Email service key |
| BRAVE_API_KEY | Yes | Search API key |
| SERP_API_KEY | Yes | Backup search key |
| STRIPE_SECRET_KEY | No | Payment processing |
| BETA_TESTER_EMAILS | No | JSON array of emails |

---

## Troubleshooting

### App won't start
```bash
fly logs --app trueight-api
```
Check for missing environment variables or database connection issues.

### Database connection errors
```bash
# Verify postgres is attached
fly postgres list

# Re-attach if needed
fly postgres attach trueight-db --app trueight-api
```

### Health check failing
```bash
# Test locally first
curl http://localhost:8000/api/v1/health

# Check container health
fly ssh console
curl http://localhost:8000/api/v1/health
```

### Out of memory
```bash
# Scale up VM
fly scale vm shared-cpu-2x --memory 2048
```

---

## Monitoring

### Fly.io Dashboard
https://fly.io/apps/trueight-api

### Logs
```bash
fly logs --app trueight-api
```

### Metrics
```bash
fly dashboard --app trueight-api
```

---

## Costs (Estimated)

| Resource | Specification | Monthly Cost |
|----------|---------------|--------------|
| App VM | shared-cpu-1x, 1GB RAM | ~$5-7 |
| PostgreSQL | 1GB RAM | ~$7 |
| Redis (Upstash) | Pay-per-use | ~$0-5 |
| **Total** | | **~$12-20** |

---

## Custom Domain Setup

1. Add domain in Fly dashboard or CLI:
   ```bash
   fly certs add api.trueight.com
   ```

2. Add DNS records (provided by Fly):
   - CNAME: `api.trueight.com` -> `trueight-api.fly.dev`

3. Update CORS:
   ```bash
   fly secrets set CORS_ORIGINS='["https://trueight.com","https://api.trueight.com"]'
   ```

---

## Rollback

If a deployment fails:

```bash
# List releases
fly releases

# Rollback to previous version
fly deploy --image registry.fly.io/trueight-api:v123
```

---

*Last updated: January 2026*
