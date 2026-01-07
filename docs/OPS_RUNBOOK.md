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
│   Vercel    │────▶│   Fly.io    │────▶│  PostgreSQL │
│  (Web/SSR)  │     │  (FastAPI)  │     │  (Fly.io)   │
└─────────────┘     └─────────────┘     └─────────────┘
                           │
                           ▼
                    ┌─────────────┐
                    │    Redis    │
                    │  (Upstash)  │
                    └─────────────┘
                           │
                           ▼
                    ┌─────────────┐
                    │   Celery    │
                    │  (Workers)  │
                    └─────────────┘
```

### Key Services

| Service | Provider | Purpose |
|---------|----------|---------|
| Web Frontend | Vercel | Next.js SSR |
| API Backend | Fly.io | FastAPI + Uvicorn |
| Database | Fly.io Postgres | PostgreSQL 16 |
| Cache/Queue | Upstash/Redis | Celery broker + caching |
| Auth | Clerk | JWT authentication |
| Payments | Stripe | Subscriptions |
| Monitoring | Sentry | Error tracking |

---

## Deployment

### Backend (Fly.io)

```bash
# Deploy to production
fly deploy --app tru8-api

# Deploy to staging
fly deploy --app tru8-api-staging

# View deployment status
fly status --app tru8-api

# View logs
fly logs --app tru8-api

# SSH into running instance
fly ssh console --app tru8-api
```

### Frontend (Vercel)

```bash
# Deploy to production (automatic on main branch)
git push origin main

# Manual deploy
vercel --prod

# Preview deploy
vercel
```

### Environment Variables

Set secrets via Fly.io:
```bash
fly secrets set DATABASE_URL="postgresql+asyncpg://..." --app tru8-api
fly secrets set REDIS_URL="redis://..." --app tru8-api
fly secrets set CLERK_SECRET_KEY="sk_live_..." --app tru8-api
fly secrets set OPENAI_API_KEY="sk-..." --app tru8-api

# List all secrets
fly secrets list --app tru8-api
```

---

## Database Operations

### Backup

```bash
# Manual backup (Fly.io Postgres)
fly postgres connect --app tru8-db
# Then run: pg_dump tru8_prod > backup.sql

# Or use fly proxy for pg_dump locally
fly proxy 5432:5432 --app tru8-db &
pg_dump -h localhost -U postgres tru8_prod > backup_$(date +%Y%m%d_%H%M%S).sql
```

### Restore

```bash
# Restore from backup
fly proxy 5432:5432 --app tru8-db &
psql -h localhost -U postgres -d tru8_prod < backup_20260105.sql
```

### Migrations

```bash
# Run migrations (via SSH)
fly ssh console --app tru8-api
cd /app
alembic upgrade head

# Check migration status
alembic current
alembic history

# Rollback last migration
alembic downgrade -1
```

### Connection Issues

```bash
# Check database status
fly postgres connect --app tru8-db

# Check connection pool
SELECT count(*) FROM pg_stat_activity WHERE datname = 'tru8_prod';

# Kill idle connections if needed
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE datname = 'tru8_prod'
AND state = 'idle'
AND state_change < NOW() - INTERVAL '10 minutes';
```

---

## Monitoring & Alerts

### Health Checks

```bash
# API health
curl https://api.tru8.com/api/v1/health

# Readiness check
curl https://api.tru8.com/api/v1/health/ready

# Metrics
curl https://api.tru8.com/metrics
```

### Sentry

- Backend: https://sentry.io/organizations/YOUR_ORG/issues/?project=tru8-api
- Frontend: https://sentry.io/organizations/YOUR_ORG/issues/?project=tru8-web

### Flower (Celery Monitoring)

```bash
# Access Flower dashboard
fly proxy 5555:5555 --app tru8-api &
open http://localhost:5555
```

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

1. [ ] Acknowledge in Slack/PagerDuty
2. [ ] Check Sentry for error patterns
3. [ ] Check `/api/v1/health/ready`
4. [ ] Check Fly.io status: `fly status --app tru8-api`
5. [ ] Check database: `fly postgres connect --app tru8-db`
6. [ ] Check Redis connectivity
7. [ ] If needed, rollback deployment
8. [ ] Communicate status to stakeholders
9. [ ] Post-incident review

### High Error Rate

```bash
# Check recent errors in logs
fly logs --app tru8-api | grep -i error | tail -50

# Check Sentry for patterns
# Look for: repeated exceptions, specific endpoints, user patterns

# If rate limiting issue
curl -I https://api.tru8.com/api/v1/checks
# Check X-RateLimit headers
```

### Queue Backup (Celery)

```bash
# Check queue length via Flower
fly proxy 5555:5555 --app tru8-api &

# Purge stale tasks (CAUTION)
fly ssh console --app tru8-api
celery -A app.workers purge

# Scale workers if needed
fly scale count 2 --app tru8-api
```

---

## Rollback Procedures

### Backend Rollback

```bash
# List recent deployments
fly releases --app tru8-api

# Rollback to previous version
fly deploy --image registry.fly.io/tru8-api:sha-<PREVIOUS_SHA> --app tru8-api

# Or rollback to specific release
fly releases rollback <RELEASE_NUMBER> --app tru8-api
```

### Database Rollback

```bash
# Rollback last migration
fly ssh console --app tru8-api
cd /app
alembic downgrade -1

# Rollback multiple migrations
alembic downgrade -3  # Go back 3 migrations
```

### Frontend Rollback

```bash
# Via Vercel dashboard
# Go to: Deployments > Select previous deployment > Promote to Production

# Or via CLI
vercel rollback
```

---

## Common Issues

### Issue: "Connection pool exhausted"

**Symptoms:** 500 errors, slow responses

**Solution:**
```bash
# Check connections
fly postgres connect --app tru8-db
SELECT count(*) FROM pg_stat_activity WHERE datname = 'tru8_prod';

# Kill idle connections
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE state = 'idle' AND state_change < NOW() - INTERVAL '5 minutes';

# Restart API if needed
fly apps restart tru8-api
```

### Issue: "Redis connection timeout"

**Symptoms:** Slow API responses, Celery tasks stuck

**Solution:**
```bash
# Check Redis status
redis-cli -u $REDIS_URL ping

# Clear cache if corrupted
redis-cli -u $REDIS_URL FLUSHDB

# Restart workers
fly apps restart tru8-api
```

### Issue: "Out of credits"

**Symptoms:** 402 errors for users

**Solution:**
```sql
-- Check user credits
SELECT id, email, credits FROM "user" WHERE email = 'user@example.com';

-- Manually adjust credits if needed (support case)
UPDATE "user" SET credits = credits + 10 WHERE email = 'user@example.com';
```

### Issue: "Pipeline timeout"

**Symptoms:** Checks stuck at "processing"

**Solution:**
```bash
# Check Celery worker status
fly ssh console --app tru8-api
celery -A app.workers inspect active

# Revoke stuck task
celery -A app.workers control revoke <TASK_ID> --terminate

# Check for resource constraints
fly status --app tru8-api
```

---

## Contacts

| Role | Name | Contact |
|------|------|---------|
| On-call Engineer | TBD | TBD |
| Product Owner | TBD | TBD |
| Customer Support | TBD | support@tru8.com |

---

*Last updated: 2026-01-05*
