# Tru8 Operations Runbook

This runbook documents operational procedures for the Tru8 platform.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Deployment](#deployment)
3. [Database Operations](#database-operations)
4. [Monitoring & Alerts](#monitoring--alerts)
5. [Incident Response](#incident-response)
6. [Rollback Procedures](#rollback-procedures)
7. [Common Issues](#common-issues)

---

## Architecture Overview

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Railway   │────▶│  Railway    │────▶│  PostgreSQL │
│  (Web/SSR)  │     │  (FastAPI)  │     │  (Railway)  │
└─────────────┘     └─────────────┘     └─────────────┘
                           │
                           ▼
                    ┌─────────────┐
                    │    Redis    │
                    │  (Railway)  │
                    └─────────────┘
```

### Key Services

| Service | Provider | Purpose |
|---------|----------|---------|
| Web Frontend | Railway | Next.js SSR (containerised) |
| API Backend | Railway | FastAPI + Uvicorn |
| Database | Railway Postgres | PostgreSQL 16 |
| Cache | Railway Redis | Caching + background tasks |
| Auth | Clerk | JWT authentication |
| Payments | Stripe | Subscriptions |
| Monitoring | Sentry | Error tracking |
| Storage | Cloudflare R2 | Object storage |
| DNS/CDN | Cloudflare | DNS + CDN |

---

## Deployment

### Backend (Railway)

Railway deploys automatically from the `main` branch. Manual actions via the Railway CLI:

```bash
# Install Railway CLI (if not installed)
npm install -g @railway/cli

# Login
railway login

# Link to project (first time only)
railway link

# Trigger a deploy manually
railway up

# View logs
railway logs

# Open the Railway dashboard
railway open
```

### Frontend (Railway)

The frontend deploys on Railway using the same git-push workflow as the backend. Both services live in the same Railway project.

```bash
# Deploy to production (automatic on main branch)
git push origin main

# Manual deploy via Railway CLI
railway up

# View frontend logs
railway logs --service web
```

### Environment Variables

Set secrets via Railway dashboard or CLI:

```bash
railway variables set DATABASE_URL="postgresql+asyncpg://..."
railway variables set REDIS_URL="redis://..."
railway variables set CLERK_SECRET_KEY="sk_live_..."
railway variables set OPENAI_API_KEY="sk-..."

# List all variables
railway variables
```

Or via the Railway dashboard: **Project → Service → Variables tab**.

---

## Database Operations

### Backup

```bash
# Connect to Railway Postgres via CLI
railway connect postgres

# Or use the public database URL for pg_dump locally
# (Find the public URL in Railway dashboard → Postgres service → Connect tab)
pg_dump "postgresql://user:pass@host:port/dbname" > backup_$(date +%Y%m%d_%H%M%S).sql
```

### Restore

```bash
# Restore from backup using the public database URL
psql "postgresql://user:pass@host:port/dbname" < backup_20260312.sql
```

### Migrations

```bash
# Run migrations via Railway CLI (executes in the service environment)
railway run alembic upgrade head

# Check migration status
railway run alembic current
railway run alembic history

# Rollback last migration
railway run alembic downgrade -1
```

### Connection Issues

```bash
# Connect to database
railway connect postgres

# Check connection pool
SELECT count(*) FROM pg_stat_activity WHERE datname = 'railway';

# Kill idle connections if needed
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE datname = 'railway'
AND state = 'idle'
AND state_change < NOW() - INTERVAL '10 minutes';
```

---

## Monitoring & Alerts

### Health Checks

```bash
# API health
curl https://api.trueight.com/api/v1/health

# Readiness check
curl https://api.trueight.com/api/v1/health/ready

# Cache metrics
curl https://api.trueight.com/api/v1/health/cache-metrics
```

### Sentry

- Backend: https://sentry.io/organizations/YOUR_ORG/issues/?project=tru8-api
- Frontend: https://sentry.io/organizations/YOUR_ORG/issues/?project=tru8-web

### Key Metrics to Monitor

| Metric | Warning | Critical |
|--------|---------|----------|
| Error rate | > 1% | > 5% |
| Response time p95 | > 1s | > 3s |
| Pipeline completion | < 95% | < 90% |
| Database connections | > 80% | > 95% |
| Redis memory | > 80% | > 95% |

---

## Incident Response

### Severity Levels

| Level | Description | Response Time |
|-------|-------------|---------------|
| P0 | Service down | Immediate |
| P1 | Major feature broken | < 1 hour |
| P2 | Minor feature affected | < 4 hours |
| P3 | Low impact issue | Next business day |

### P0 Response Checklist

1. [ ] Check Sentry for error patterns
2. [ ] Check `/api/v1/health/ready`
3. [ ] Check Railway dashboard for service status
4. [ ] Check database connectivity: `railway connect postgres`
5. [ ] Check Redis connectivity
6. [ ] Check Railway logs: `railway logs`
7. [ ] If needed, rollback deployment
8. [ ] Post-incident review

### High Error Rate

```bash
# Check recent errors in logs
railway logs | grep -i error | tail -50

# Check Sentry for patterns
# Look for: repeated exceptions, specific endpoints, user patterns

# If rate limiting issue
curl -I https://api.trueight.com/api/v1/checks
# Check X-RateLimit headers
```

---

## Rollback Procedures

### Backend Rollback

Railway keeps deployment history. To rollback:

1. Go to **Railway dashboard → Service → Deployments**
2. Find the previous working deployment
3. Click **Redeploy** on that deployment

Or via CLI:
```bash
# View recent deployments
railway deployments

# Rollback by redeploying a previous commit
git revert HEAD
git push origin main
```

### Database Rollback

```bash
# Rollback last migration
railway run alembic downgrade -1

# Rollback multiple migrations
railway run alembic downgrade -3
```

### Frontend Rollback

Same as backend — Railway keeps deployment history for both services:

1. Go to **Railway dashboard → Web Service → Deployments**
2. Find the previous working deployment
3. Click **Redeploy** on that deployment

Or via git revert (triggers both services):
```bash
git revert HEAD
git push origin main
```

---

## Common Issues

### Issue: "Connection pool exhausted"

**Symptoms:** 500 errors, slow responses

**Solution:**
```bash
railway connect postgres

SELECT count(*) FROM pg_stat_activity WHERE datname = 'railway';

# Kill idle connections
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE state = 'idle' AND state_change < NOW() - INTERVAL '5 minutes';

# Restart service via Railway dashboard if needed
```

### Issue: "Redis connection timeout"

**Symptoms:** Slow API responses, background tasks stuck

**Solution:**
```bash
# Check Redis status
redis-cli -u $REDIS_URL ping

# Clear cache if corrupted
redis-cli -u $REDIS_URL FLUSHDB

# Restart service via Railway dashboard
```

### Issue: "Out of credits"

**Symptoms:** 402 errors for users

**Solution:**
```sql
-- Connect via: railway connect postgres

-- Check user credits
SELECT id, email, credits FROM "user" WHERE email = 'user@example.com';

-- Manually adjust credits if needed (support case)
UPDATE "user" SET credits = credits + 10 WHERE email = 'user@example.com';
```

### Issue: "Pipeline timeout"

**Symptoms:** Checks stuck at "processing"

**Solution:**
```bash
# Check logs for stuck tasks
railway logs | grep -i "timeout\|stuck\|error"
```

---

## Contacts

| Role | Name | Contact |
|------|------|---------|
| On-call Engineer | TBD | TBD |
| Product Owner | TBD | TBD |
| Customer Support | TBD | support@trueight.com |

---

*Last updated: 2026-03-18*
