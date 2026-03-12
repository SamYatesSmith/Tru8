# Tru8 Release Checklist

**Version:** Public Beta
**Date:** ____________
**Release Manager:** ____________

Use this checklist for final go/no-go decision. All P0 items must be checked.

---

## Pre-Release (Complete Before Deploy)

### P0 - Blockers (All Must Pass)

| # | Task | Status | Verified By |
|---|------|--------|-------------|
| 1 | CI/CD pipeline exists and passes | [ ] | ____________ |
| 2 | Dockerfile builds and runs | [ ] | ____________ |
| 3 | `DEBUG=false` in production config | [ ] | ____________ |
| 4 | Rate limiting active on /checks | [ ] | ____________ |
| 5 | No hardcoded credentials in codebase | [ ] | ____________ |
| 6 | CORS configured for production domains only | [ ] | ____________ |

### P1 - Important (Should Pass)

| # | Task | Status | Verified By |
|---|------|--------|-------------|
| 7 | `requirements.lock` exists | [ ] | ____________ |
| 8 | pip-audit passes (or exceptions documented) | [ ] | ____________ |
| 9 | Frontend Sentry configured | [ ] | ____________ |
| 10 | Backup procedure documented | [ ] | ____________ |
| 11 | Global exception handler returns safe errors | [ ] | ____________ |

---

## Environment Verification

### Production Environment Variables

| Variable | Set? | Verified Value |
|----------|------|----------------|
| `ENVIRONMENT=production` | [ ] | ____________ |
| `DEBUG=false` | [ ] | ____________ |
| `SECRET_KEY` (strong, unique) | [ ] | ____________ |
| `DATABASE_URL` (production DB) | [ ] | ____________ |
| `REDIS_URL` (production Redis) | [ ] | ____________ |
| `CLERK_SECRET_KEY` (`sk_live_*`) | [ ] | ____________ |
| `CLERK_JWT_ISSUER` (production) | [ ] | ____________ |
| `OPENAI_API_KEY` | [ ] | ____________ |
| `BRAVE_API_KEY` | [ ] | ____________ |
| `SENTRY_DSN` (production project) | [ ] | ____________ |
| `CORS_ORIGINS` (prod domains only) | [ ] | ____________ |
| `STRIPE_SECRET_KEY` (`sk_live_*`) | [ ] | ____________ |
| `STRIPE_WEBHOOK_SECRET` | [ ] | ____________ |

### Web Production Variables

| Variable | Set? | Verified Value |
|----------|------|----------------|
| `NEXT_PUBLIC_API_URL` (https://api.tru8.com) | [ ] | ____________ |
| `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` (`pk_live_*`) | [ ] | ____________ |
| `NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY` | [ ] | ____________ |

---

## Smoke Tests (Post-Deploy)

### Health Checks

| Test | Expected | Actual | Pass? |
|------|----------|--------|-------|
| `GET /api/v1/health` | `{"status": "healthy"}` | ____________ | [ ] |
| `GET /api/v1/health/ready` | `{"ready": true}` | ____________ | [ ] |
| `GET /metrics` | Prometheus output | ____________ | [ ] |

### Authentication

| Test | Expected | Actual | Pass? |
|------|----------|--------|-------|
| Sign up new user | User created, 3 credits | ____________ | [ ] |
| Sign in existing user | Profile returned | ____________ | [ ] |
| Invalid token | 401 Unauthorized | ____________ | [ ] |

### Core Functionality

| Test | Expected | Actual | Pass? |
|------|----------|--------|-------|
| Create URL check | Check created, SSE stream starts | ____________ | [ ] |
| Check completes | Claims + evidence returned | ____________ | [ ] |
| View check history | List of user's checks | ____________ | [ ] |
| Credit deduction | Credits decremented on check | ____________ | [ ] |

### Payments (if enabled)

| Test | Expected | Actual | Pass? |
|------|----------|--------|-------|
| Start checkout | Redirect to Stripe | ____________ | [ ] |
| Webhook (test) | Subscription created | ____________ | [ ] |
| Cancel subscription | Status = cancelled | ____________ | [ ] |

### Error Handling

| Test | Expected | Actual | Pass? |
|------|----------|--------|-------|
| Invalid input | 422 with error details | ____________ | [ ] |
| Rate limit exceeded | 429 Too Many Requests | ____________ | [ ] |
| Unauthorized endpoint | 401 Unauthorized | ____________ | [ ] |
| Server error | 500 with safe message | ____________ | [ ] |

---

## Monitoring Verification

| System | Working? | Dashboard URL |
|--------|----------|---------------|
| Sentry (backend) | [ ] | ____________ |
| Sentry (frontend) | [ ] | ____________ |
| Prometheus/Grafana | [ ] | ____________ |
| Background task logs | [ ] | ____________ |

---

## Rollback Ready

| Item | Verified? |
|------|-----------|
| Previous version image available | [ ] |
| Database backup taken before deploy | [ ] |
| Rollback command documented | [ ] |
| Team notified of release window | [ ] |

**Rollback command:**
```bash
railway up --service tru8-api --environment production
# Or redeploy a previous commit from the Railway dashboard
```

---

## Final Approval

### Go/No-Go Decision

| Criterion | Status |
|-----------|--------|
| All P0 items passed | [ ] Yes [ ] No |
| All smoke tests passed | [ ] Yes [ ] No |
| Monitoring active | [ ] Yes [ ] No |
| Rollback plan ready | [ ] Yes [ ] No |

### Sign-Off

| Role | Name | Signature | Date |
|------|------|-----------|------|
| Release Manager | ____________ | ____________ | ____________ |
| Tech Lead | ____________ | ____________ | ____________ |
| QA | ____________ | ____________ | ____________ |

---

## Post-Release Monitoring

### First 24 Hours

| Check | Time | Status | Notes |
|-------|------|--------|-------|
| Error rate < 1% | T+1h | [ ] | ____________ |
| Error rate < 1% | T+4h | [ ] | ____________ |
| Error rate < 1% | T+24h | [ ] | ____________ |
| Pipeline completion rate > 95% | T+4h | [ ] | ____________ |
| Response time p95 < 500ms | T+4h | [ ] | ____________ |
| No customer escalations | T+24h | [ ] | ____________ |

### Success Criteria

- [ ] No P0 bugs reported in first 24 hours
- [ ] Error rate < 1%
- [ ] Pipeline success rate > 95%
- [ ] No security incidents

---

## Incident Contacts

| Role | Name | Contact |
|------|------|---------|
| On-call Engineer | ____________ | ____________ |
| Product Owner | ____________ | ____________ |
| Customer Support | ____________ | ____________ |

---

## Release Notes

**Changes in this release:**
- ____________
- ____________
- ____________

**Known Issues:**
- ____________
- ____________

---

*Checklist generated by Claude Code for Tru8 Public Beta release.*
