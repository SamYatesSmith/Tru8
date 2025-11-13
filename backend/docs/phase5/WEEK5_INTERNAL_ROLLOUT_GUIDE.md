# Week 5: Internal Rollout Guide
**Phase 5: Government API Integration - Internal Testing**

**Date**: 2025-11-12
**Status**: Ready for Internal Rollout
**Version**: 1.0.0

---

## Table of Contents
1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Deployment Steps](#deployment-steps)
4. [Monitoring & Metrics](#monitoring--metrics)
5. [Testing Guidelines](#testing-guidelines)
6. [Troubleshooting](#troubleshooting)
7. [Feedback Collection](#feedback-collection)

---

## Overview

### Purpose
Enable Government API Integration for internal team testing to:
- Validate functionality in production-like environment
- Collect performance metrics
- Identify edge cases and issues
- Gather qualitative feedback before public rollout

### Scope
- **Users**: Internal team only (development, QA, product)
- **Duration**: 1-2 weeks
- **Coverage Target**: 20-30% of claims enhanced with API data
- **Rollback**: Instant via feature flag

### Success Criteria
✅ <10s P95 latency (no regression)
✅ 20-30% API coverage achieved
✅ <1% error rate
✅ 60%+ cache hit rate
✅ No circuit breakers stuck open
✅ Positive internal feedback

---

## Prerequisites

### Infrastructure
- [x] ✅ PostgreSQL with API-related columns (Evidence.api_metadata, Check.api_sources_used)
- [x] ✅ Redis for caching (with 7-day TTL on metrics)
- [x] ✅ All 10 API adapters registered
- [x] ✅ Circuit breakers initialized
- [x] ✅ Monitoring endpoints deployed

### Configuration
- [x] ✅ API keys configured in `.env` (optional - works without)
- [x] ✅ Feature flag `ENABLE_API_RETRIEVAL` available
- [x] ✅ Cache TTLs optimized per adapter
- [x] ✅ Circuit breaker thresholds set

### Testing
- [x] ✅ 37/37 tests passing (Week 4)
- [x] ✅ Integration tests verified
- [x] ✅ Performance benchmarks established

---

## Deployment Steps

### Step 1: Enable Feature Flag (Staging/Internal)

**Option A: Environment Variable**
```bash
# Set in .env or deployment config
ENABLE_API_RETRIEVAL=true
```

**Option B: Runtime Toggle** (if implemented)
```bash
# Via admin API or database config
curl -X POST http://localhost:8000/api/v1/admin/feature-flags \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{"ENABLE_API_RETRIEVAL": true}'
```

**Verify Enabled**:
```bash
# Check health endpoint
curl http://localhost:8000/api/v1/health/ready

# Should show adapters initialized in logs
grep "Registered API adapter" logs/app.log
```

### Step 2: Verify Adapter Initialization

```bash
# Check circuit breaker status
curl http://localhost:8000/api/v1/health/circuit-breakers

# Expected response: All adapters in "closed" state
{
  "ONS": {"state": "closed", "failure_count": 0},
  "PubMed": {"state": "closed", "failure_count": 0},
  ...
}
```

### Step 3: Reset Cache Metrics (Optional)

If redeploying or starting fresh metrics:

```python
from app.services.cache import get_sync_cache_service

cache = get_sync_cache_service()
cache.reset_cache_metrics()  # Reset all metrics
```

### Step 4: Monitor Initialization

**Check Logs** for successful startup:
```bash
# Look for these log entries
tail -f logs/app.log | grep "API"

# Expected:
# "Sync cache service initialized"
# "Circuit breaker initialized for ONS (threshold=5, timeout=60s)"
# "Registered API adapter: ONS"
# ... (repeat for all 10 adapters)
```

### Step 5: Create Test Check

Run a test fact-check to verify end-to-end:

```bash
curl -X POST http://localhost:8000/api/v1/checks \
  -H "Authorization: Bearer $USER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "input_type": "text",
    "input_content": {
      "text": "UK inflation rate is 3.2% according to the ONS"
    }
  }'
```

**Expected**: Check completes in <10s, includes API evidence in results

---

## Monitoring & Metrics

### Real-Time Dashboards

#### 1. Cache Performance

**Endpoint**: `GET /api/v1/health/cache-metrics`

```bash
# Overall metrics
curl http://localhost:8000/api/v1/health/cache-metrics

# Per-API metrics
curl "http://localhost:8000/api/v1/health/cache-metrics?api_name=ONS"
```

**Key Metrics**:
- `hit_rate_percentage` - Target: ≥60%
- `total_queries` - Volume indicator
- `status` - "excellent" (≥75%), "good" (60-74%), "acceptable" (40-59%), "needs_optimization" (<40%)

**Alert Thresholds**:
- ⚠️ Warning: Hit rate <60%
- 🚨 Critical: Hit rate <40%

#### 2. Circuit Breaker Status

**Endpoint**: `GET /api/v1/health/circuit-breakers`

```bash
# All circuit breakers
curl http://localhost:8000/api/v1/health/circuit-breakers

# Specific API
curl "http://localhost:8000/api/v1/health/circuit-breakers?api_name=ONS"
```

**Key Metrics**:
- `state` - "closed" (✅), "half_open" (⚠️), "open" (🚨)
- `failure_count` - Failures before opening
- `time_until_retry_seconds` - Recovery countdown

**Alert Thresholds**:
- ⚠️ Warning: Any breaker in "half_open" state
- 🚨 Critical: Any breaker in "open" state for >5 minutes

#### 3. Pipeline Performance

**Database Queries** (use your preferred SQL client):

```sql
-- P50, P95, P99 latency for checks with API retrieval
SELECT
    percentile_cont(0.50) WITHIN GROUP (ORDER BY processing_time_ms) AS p50_ms,
    percentile_cont(0.95) WITHIN GROUP (ORDER BY processing_time_ms) AS p95_ms,
    percentile_cont(0.99) WITHIN GROUP (ORDER BY processing_time_ms) AS p99_ms,
    AVG(processing_time_ms) AS avg_ms,
    COUNT(*) AS total_checks
FROM "check"
WHERE
    status = 'completed'
    AND api_call_count > 0
    AND created_at > NOW() - INTERVAL '24 hours';

-- Expected: P95 < 10000ms (10s)
```

#### 4. API Coverage

```sql
-- Percentage of checks using API data
SELECT
    COUNT(CASE WHEN api_call_count > 0 THEN 1 END) AS checks_with_api,
    COUNT(*) AS total_checks,
    ROUND(
        COUNT(CASE WHEN api_call_count > 0 THEN 1 END)::numeric /
        COUNT(*)::numeric * 100,
        2
    ) AS api_coverage_percentage
FROM "check"
WHERE
    status = 'completed'
    AND created_at > NOW() - INTERVAL '24 hours';

-- Target: 20-30% initially
```

#### 5. API Sources Used

```sql
-- Most frequently used APIs
SELECT
    api->>'name' AS api_name,
    COUNT(*) AS usage_count,
    AVG((api->>'results')::int) AS avg_results_per_call
FROM "check",
     jsonb_array_elements(api_sources_used::jsonb) AS api
WHERE
    created_at > NOW() - INTERVAL '24 hours'
GROUP BY api->>'name'
ORDER BY usage_count DESC;
```

#### 6. Error Rates

```sql
-- Error rate by status
SELECT
    status,
    COUNT(*) AS count,
    ROUND(COUNT(*)::numeric / SUM(COUNT(*)) OVER () * 100, 2) AS percentage
FROM "check"
WHERE created_at > NOW() - INTERVAL '24 hours'
GROUP BY status
ORDER BY count DESC;

-- Target: <1% failed
```

### Grafana Dashboard (Optional)

**Recommended Panels**:
1. **Cache Hit Rate** - Line graph, refresh 1m
2. **Circuit Breaker States** - Status panel, refresh 30s
3. **API Coverage %** - Gauge, target 20-30%
4. **P95 Latency** - Line graph, alert if >10s
5. **Error Rate** - Single stat, alert if >1%
6. **Top APIs Used** - Bar chart

### Log Monitoring

**Critical Logs to Watch**:

```bash
# API errors
tail -f logs/app.log | grep "ERROR.*API"

# Circuit breaker state changes
tail -f logs/app.log | grep "circuit breaker.*OPEN\|HALF_OPEN"

# Cache misses (high volume might indicate issue)
tail -f logs/app.log | grep "cache MISS"

# Slow pipeline (>10s)
tail -f logs/app.log | grep "processing took.*[1-9][0-9]\{4,\}"
```

---

## Testing Guidelines

### For Internal Team

#### Test Scenarios

**1. Finance Claims (ONS, FRED)**
```
Test: "UK unemployment rate is 5.2%"
Expected: ONS adapter called, economic data in evidence
```

**2. Health Claims (PubMed, WHO)**
```
Test: "COVID-19 vaccine efficacy is 95%"
Expected: PubMed/WHO adapter called, medical research in evidence
```

**3. Government Claims (Companies House)**
```
Test: "Acme Corp is registered in the UK with company number 12345678"
Expected: Companies House adapter called, company data in evidence
```

**4. Climate Claims (Met Office)**
```
Test: "London temperature will be 18C tomorrow"
Expected: Met Office adapter called, weather forecast in evidence
```

**5. Multi-Domain Claims**
```
Test: "NHS spending increased by £10 billion"
Expected: Health OR Government adapter called (domain routing tested)
```

**6. No API Match**
```
Test: "This pizza is delicious"
Expected: No API calls (General domain), web search only
```

#### What to Test

✅ **Functional Testing**:
- Verify API evidence appears in results
- Check credibility scores (API sources should be ≥0.90)
- Confirm source attribution ("ONS Economic Statistics", etc.)
- Validate evidence quality and relevance

✅ **Performance Testing**:
- Time how long checks take (<10s target)
- Test with multiple concurrent checks
- Verify no noticeable slowdown vs. without APIs

✅ **Error Handling**:
- Test with invalid API keys (should fall back gracefully)
- Test during API downtime (circuit breaker should open)
- Verify partial failures don't crash pipeline

✅ **Edge Cases**:
- Very long claims (>500 chars)
- Claims with typos or misspellings
- Ambiguous domains (e.g., "NHS spending" - health or finance?)
- Non-English claims (should handle gracefully)

#### Testing Checklist

- [ ] Finance domain claim works (ONS/FRED)
- [ ] Health domain claim works (PubMed/WHO)
- [ ] API evidence has high credibility (≥0.90)
- [ ] Pipeline completes in <10s
- [ ] Cache hit rate improves on repeated queries
- [ ] Circuit breaker opens after API failures
- [ ] No crashes or errors in logs
- [ ] Evidence properly attributed to API source

---

## Troubleshooting

### Issue: No API Evidence Appearing

**Symptoms**: Checks complete but no API sources in results

**Diagnosis**:
```bash
# Check if feature flag enabled
grep "ENABLE_API_RETRIEVAL" .env

# Check adapters registered
curl http://localhost:8000/api/v1/health/circuit-breakers

# Check logs for API calls
grep "cache MISS.*calling API" logs/app.log
```

**Solutions**:
1. Verify `ENABLE_API_RETRIEVAL=true` in config
2. Restart application after config change
3. Check claim domain matches API coverage (Finance, Health, etc.)
4. Verify network access to external APIs

---

### Issue: Circuit Breaker Stuck Open

**Symptoms**: Specific API showing `"state": "open"` for extended period

**Diagnosis**:
```bash
# Check circuit breaker status
curl http://localhost:8000/api/v1/health/circuit-breakers?api_name=ONS

# Check API health manually
curl "https://api.ons.gov.uk/..." # (actual API endpoint)
```

**Solutions**:
1. Wait for `recovery_timeout` (default 60s) for automatic retry
2. If API is down, circuit breaker is working correctly (preventing timeouts)
3. If API is up but breaker stuck, check for network/firewall issues
4. Manual reset (if needed):
   ```python
   from app.services.circuit_breaker import get_circuit_breaker_registry
   registry = get_circuit_breaker_registry()
   registry.get_breaker("ONS").force_close()
   ```

---

### Issue: Low Cache Hit Rate (<40%)

**Symptoms**: Cache metrics showing `"status": "needs_optimization"`

**Diagnosis**:
```bash
# Check cache metrics
curl http://localhost:8000/api/v1/health/cache-metrics

# Check Redis connection
redis-cli ping  # Should return "PONG"

# Check cache TTLs
redis-cli TTL "tru8:api_response:ONS:..."
```

**Solutions**:
1. **New deployment**: Low hit rate is normal initially (cache is empty)
2. **Diverse queries**: If every query is unique, low hit rate is expected
3. **Short TTLs**: Review TTL settings in adapters
4. **Redis issues**: Verify Redis is running and accessible

**Expected Behavior**: Hit rate should improve over time as cache populates

---

### Issue: Slow Pipeline (>10s P95)

**Symptoms**: Checks taking longer than 10s consistently

**Diagnosis**:
```sql
-- Check which stage is slow
SELECT
    AVG(processing_time_ms) AS avg_ms,
    MAX(processing_time_ms) AS max_ms,
    COUNT(*) AS count
FROM "check"
WHERE
    api_call_count > 0
    AND created_at > NOW() - INTERVAL '1 hour'
    AND processing_time_ms > 10000;
```

```bash
# Check API response times in logs
grep "API.*took.*ms" logs/app.log | tail -20
```

**Solutions**:
1. **API timeouts**: Review timeout settings (default 10s)
2. **Too many APIs**: Review domain routing (should call 1-3 APIs max)
3. **Slow external APIs**: Circuit breaker will help by failing fast
4. **Network latency**: Check network connection to API endpoints

---

### Issue: High Error Rate (>1%)

**Symptoms**: Many checks with `status = 'failed'`

**Diagnosis**:
```sql
-- Check error messages
SELECT
    error_message,
    COUNT(*) AS count
FROM "check"
WHERE
    status = 'failed'
    AND created_at > NOW() - INTERVAL '1 hour'
GROUP BY error_message
ORDER BY count DESC
LIMIT 10;
```

```bash
# Check application logs
grep "ERROR" logs/app.log | tail -50
```

**Solutions**:
1. **API key issues**: Check if API keys are valid (optional for most adapters)
2. **Rate limiting**: Circuit breaker should handle this, but check rate limits
3. **Network issues**: Verify outbound network access
4. **Code bugs**: Check stack traces in logs, report to development team

---

## Feedback Collection

### Qualitative Feedback

**For Internal Testers**: Please provide feedback on:

1. **Evidence Quality**:
   - Is API evidence more relevant than web search results?
   - Are credibility scores accurate?
   - Is source attribution clear?

2. **Performance**:
   - Does the pipeline feel slower?
   - Are there noticeable delays?
   - Does caching make repeat queries faster?

3. **Accuracy**:
   - Do API sources improve verdict accuracy?
   - Are there any false positives/negatives?
   - Is domain routing working correctly?

4. **Issues Encountered**:
   - Any errors or crashes?
   - Any confusing behavior?
   - Any missing features?

5. **User Experience**:
   - Is API evidence displayed clearly in UI?
   - Is it obvious which sources are from APIs vs web?
   - Any suggestions for improvement?

### Feedback Form Template

```markdown
## API Integration Feedback

**Date**: ___________
**Tester**: ___________

### Test Claim
Claim Text: ___________

### Results
- [ ] API evidence appeared
- [ ] Evidence was relevant
- [ ] Credibility scores appropriate
- [ ] Completed in <10s

### Quality (1-5 stars)
- Evidence Relevance: ⭐⭐⭐⭐⭐
- Source Quality: ⭐⭐⭐⭐⭐
- Performance: ⭐⭐⭐⭐⭐

### Comments
___________

### Issues
___________
```

### Feedback Submission

**Internal Slack Channel**: `#api-integration-testing`
**Feedback Form**: [Link to Google Form / Internal Tool]
**Bug Reports**: GitHub Issues with label `api-integration`

---

## Metrics Tracking (Week 5 Goals)

### Daily Tracking

| Metric | Target | How to Measure |
|--------|--------|----------------|
| **API Coverage** | 20-30% | SQL query (#4 in Monitoring) |
| **P95 Latency** | <10s | SQL query (#3) |
| **Error Rate** | <1% | SQL query (#6) |
| **Cache Hit Rate** | ≥60% | `/health/cache-metrics` endpoint |
| **Circuit Breakers** | All closed | `/health/circuit-breakers` endpoint |
| **Internal Feedback** | Positive | Qualitative (form responses) |

### End-of-Week Review

After 1 week of internal testing, review:

✅ **Go/No-Go for Week 6 Public Rollout**:
- [ ] All metrics within targets
- [ ] No critical bugs reported
- [ ] Positive internal feedback
- [ ] Stable for 3+ consecutive days

---

## Rollback Plan

### Instant Rollback (If Critical Issue)

**Step 1**: Disable feature flag
```bash
# Set in .env
ENABLE_API_RETRIEVAL=false
```

**Step 2**: Restart application
```bash
# Kubernetes
kubectl rollout restart deployment/tru8-backend

# Docker
docker-compose restart backend

# PM2
pm2 restart tru8-backend
```

**Step 3**: Verify disabled
```bash
# Check logs - should NOT see "Registered API adapter"
tail -f logs/app.log | grep "API adapter"

# API calls should stop immediately
```

**Impact**: Pipeline reverts to web-only search, no data loss

---

## Support Contacts

**Technical Issues**:
- Development Team Lead: [Name/Email]
- Backend Engineer: [Name/Email]

**Product Feedback**:
- Product Manager: [Name/Email]

**Infrastructure**:
- DevOps: [Name/Email]

**Escalation**:
- Slack: `#api-integration` or `#engineering`
- Email: engineering@tru8.com

---

## Next Steps

### After Week 5 (Internal Rollout)

**If Successful** (metrics meet targets):
→ Proceed to **Week 6.1**: 10% Public Rollout

**If Issues Found**:
→ Fix issues, extend internal testing
→ Re-test until stable

**Week 6 Plan**:
- 10% of users (A/B test)
- Monitor for 2-3 days
- If stable → 50% rollout
- If stable → 100% (General Availability)

---

## Appendix

### API Adapter Reference

| Adapter | Domain | Jurisdiction | TTL | Free Tier |
|---------|--------|--------------|-----|-----------|
| **ONS** | Finance | UK | 7 days | Yes (rate limited) |
| **FRED** | Finance | US | 7 days | Yes (API key recommended) |
| **PubMed** | Health | Global | 7 days | Yes (no key required) |
| **WHO** | Health | Global | 7 days | Yes |
| **Met Office** | Climate | UK | 1 hour | Yes (key required) |
| **Companies House** | Government | UK | 7 days | Yes (key required) |
| **Wikidata** | General | Global | 30 days | Yes |
| **GOV.UK** | Government | UK | 3 days | Yes |
| **Hansard** | Law | UK | 30 days | Yes |
| **CrossRef** | Science | Global | 30 days | Yes |

### Configuration Reference

```bash
# Feature Flag
ENABLE_API_RETRIEVAL=true

# Optional: API Keys (adapters work without, but with rate limits)
FRED_API_KEY=your_key_here
MET_OFFICE_API_KEY=your_key_here
COMPANIES_HOUSE_API_KEY=your_key_here

# Circuit Breaker Settings (defaults shown)
CIRCUIT_BREAKER_FAILURE_THRESHOLD=5
CIRCUIT_BREAKER_RECOVERY_TIMEOUT=60
CIRCUIT_BREAKER_SUCCESS_THRESHOLD=2

# Performance Tuning
API_REQUEST_TIMEOUT=10
MAX_API_RETRIES=3
```

---

**Document Version**: 1.0.0
**Last Updated**: 2025-11-12
**Prepared By**: Claude Code
**Status**: Ready for Internal Rollout
