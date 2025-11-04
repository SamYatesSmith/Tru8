# System Limits and Boundaries

**Project**: Tru8 Fact-Checking Platform
**Last Updated**: 2025-11-03 14:45:00 UTC
**Code Version**: commit 388ac66
**Testing Phase**: Phase 4 (Performance Testing)
**Status**: 🟡 TO BE COMPLETED IN PHASE 4

---

## 📊 Document Purpose

This document captures the measured performance limits, capacity boundaries, and breaking points of the Tru8 pipeline. All metrics are based on empirical testing conducted during Phase 4 (Performance Testing).

**Note**: This document will be fully populated during Phase 4. Current values are targets from configuration and documentation.

---

## 🎯 Performance Targets vs Actual

| Metric | Target | Actual | Status | Notes |
|--------|--------|--------|--------|-------|
| Full pipeline latency (p95) | <10s | TBD | ⏳ | To be measured in Phase 4 |
| API response time (p95) | <200ms | TBD | ⏳ | To be measured in Phase 4 |
| Token cost per check | <$0.02 | $0.022 (with query) | ⚠️ | Exceeds target with Search Clarity |
| Feature overhead total | <1300ms | TBD | ⏳ | To be measured in Phase 4 |

---

## ⏱️ PIPELINE LATENCY

### Stage-by-Stage Breakdown (p95)

| Stage | Target | Actual | % of Total | Status |
|-------|--------|--------|------------|--------|
| **1. Ingest** | TBD | TBD | TBD% | ⏳ Not measured |
| **2. Extract** | TBD | TBD | TBD% | ⏳ Not measured |
| **2.5 Fact-Check Lookup** | TBD | TBD | TBD% | ⏳ Not measured |
| **3. Retrieve** | TBD | TBD | TBD% | ⏳ Not measured |
| **4. Verify (NLI)** | TBD | TBD | TBD% | ⏳ Not measured |
| **5. Judge** | TBD | TBD | TBD% | ⏳ Not measured |
| **5.5 Query Answer** | TBD | TBD | TBD% | ⏳ Not measured |
| **6. Explainability** | TBD | TBD | TBD% | ⏳ Not measured |
| **TOTAL** | <10s | TBD | 100% | ⏳ Not measured |

### Latency by Percentile

| Percentile | URL Input | Text Input | Image Input | Video Input |
|------------|-----------|------------|-------------|-------------|
| p50 (median) | TBD | TBD | TBD | TBD |
| p75 | TBD | TBD | TBD | TBD |
| p90 | TBD | TBD | TBD | TBD |
| p95 | TBD | TBD | TBD | TBD |
| p99 | TBD | TBD | TBD | TBD |

---

## 🚀 THROUGHPUT LIMITS

### Concurrent Checks

| Concurrent Checks | Success Rate | Avg Latency | p95 Latency | Notes |
|------------------|--------------|-------------|-------------|-------|
| 1 | TBD | TBD | TBD | Baseline |
| 5 | TBD | TBD | TBD | - |
| 10 | TBD | TBD | TBD | - |
| 25 | TBD | TBD | TBD | - |
| 50 | TBD | TBD | TBD | - |
| 100 | TBD | TBD | TBD | Breaking point? |

**Maximum Concurrent Checks**: TBD (to be measured in Phase 4)
**Breaking Point**: TBD checks (point at which success rate <95%)

### Sustained Load

| Duration | Checks/min | Success Rate | Errors | Notes |
|----------|------------|--------------|--------|-------|
| 1 minute | TBD | TBD | TBD | Burst capacity |
| 5 minutes | TBD | TBD | TBD | Short-term |
| 30 minutes | TBD | TBD | TBD | Medium-term |
| 60 minutes | TBD | TBD | TBD | Sustained load |

**Maximum Sustained Throughput**: TBD checks/minute

---

## 💾 RESOURCE LIMITS

### Memory Usage

| Scenario | Baseline | Peak | Leak/Hour | Notes |
|----------|----------|------|-----------|-------|
| Idle worker | TBD MB | TBD MB | TBD MB | No checks processing |
| Single check | TBD MB | TBD MB | TBD MB | 1 check at a time |
| 10 concurrent | TBD MB | TBD MB | TBD MB | 10 checks parallel |
| 50 concurrent | TBD MB | TBD MB | TBD MB | High load |
| 100 concurrent | TBD MB | TBD MB | TBD MB | Breaking point |

**Memory Limits**:
- **Per check**: TBD MB (average), TBD MB (peak)
- **Per worker**: TBD MB (safe limit)
- **Memory leak threshold**: <10MB/hour (target)

### CPU Usage

| Load Level | CPU % (avg) | CPU % (peak) | Notes |
|------------|-------------|--------------|-------|
| Idle | TBD% | TBD% | Background tasks |
| Light (1-5 checks) | TBD% | TBD% | Normal operation |
| Medium (10-25 checks) | TBD% | TBD% | Busy period |
| Heavy (50+ checks) | TBD% | TBD% | Peak load |

**CPU Limits**:
- **Safe operating range**: TBD-TBD% utilization
- **Throttling threshold**: TBD% (worker should slow down)

### Database Connections

| Pool Size | Concurrent Checks | Saturation Point | Notes |
|-----------|------------------|------------------|-------|
| 10 | TBD | TBD | Default config |
| 20 | TBD | TBD | - |
| 50 | TBD | TBD | - |

**Database Limits**:
- **Connection pool size**: 10 (configured)
- **Saturation point**: TBD concurrent checks
- **Query latency under load**: TBD ms (p95)

### Redis Connections

| Scenario | Connections | Operations/sec | Notes |
|----------|-------------|----------------|-------|
| Idle | TBD | TBD | Background |
| Light load | TBD | TBD | 1-10 checks |
| Heavy load | TBD | TBD | 50+ checks |

**Redis Limits**:
- **Max connections**: TBD
- **Max operations/sec**: TBD
- **Cache hit rate**: TBD% (target: >80%)

---

## 📏 INPUT LIMITS

### Content Size Limits

| Input Type | Max Size | Configured | Enforced | Notes |
|------------|----------|------------|----------|-------|
| URL content | Unlimited | - | No | Limited by timeout |
| Text input | 5000 chars | Yes | Yes | UI validation |
| Text input (min) | 10 chars | Yes | Yes | UI validation |
| Image file | 6 MB | Yes | Yes | Backend validation |
| Video duration | 8 minutes | Yes | Yes | Quick mode limit |
| PDF file | TBD | No | No | Not yet implemented |

### Processing Limits

| Item | Limit | Configured | Reason |
|------|-------|------------|--------|
| Claims per check | 12 | Yes | Cost optimization (MVP) |
| Evidence per claim | ~10-15 | No (dynamic) | Relevance threshold |
| Max evidence per domain | 3 | Yes | Diversity requirement |
| Max domain ratio | 40% | Yes | Prevent dominance |
| Content word limit (extract) | 2500 words | Yes | Cost optimization |
| NLI model token limit | 512 tokens | Model constraint | BART-MNLI limit |

---

## 💰 COST LIMITS

### Token Usage

| Component | Model | Tokens/Check (avg) | Cost/Check | Notes |
|-----------|-------|-------------------|------------|-------|
| Claim Extraction | gpt-4o-mini | TBD | $0.0075 (est) | 12 claims |
| Judge (per claim) | gpt-4o-mini | TBD | $0.01 (est) | 12 claims |
| Query Answer | gpt-4o-mini | TBD | $0.005 (est) | If query provided |
| Overall Assessment | gpt-4o-mini | TBD | TBD | Summary generation |
| **TOTAL** | - | TBD | **$0.022** (est) | With query |

**Cost Targets**:
- **Per check (no query)**: <$0.02 ✅
- **Per check (with query)**: $0.022 ⚠️ (exceeds target by 10%)
- **Daily limit (1000 checks)**: $22/day
- **Monthly estimate (30K checks)**: $660/month

### API Quota Limits

| Service | Plan | Quota | Cost/Call | Notes |
|---------|------|-------|-----------|-------|
| OpenAI | Pay-as-go | Unlimited | Variable | Token-based |
| Brave Search | Paid | TBD/month | $0.001 | Per search |
| Google Fact Check | Free | 10K/day | Free | Rate limited |
| YouTube API | Free | 10K/day | Free | Transcript access |

---

## 🔥 BREAKING POINTS

### Load Breaking Points

| Resource | Breaking Point | Symptoms | Mitigation |
|----------|---------------|----------|------------|
| Worker memory | TBD GB | OOM errors, crashes | Scale horizontally |
| Database connections | TBD concurrent | Timeouts, queue buildup | Increase pool size |
| Redis connections | TBD ops/sec | Cache misses, slowdown | Add Redis replicas |
| Celery workers | TBD workers | Task queue buildup | Add more workers |
| External API rate limits | TBD req/min | 429 errors, failures | Implement backoff |

### Failure Scenarios

| Scenario | Impact | Observed Behavior | Recovery Time |
|----------|--------|-------------------|---------------|
| Database down | Critical | All checks fail | TBD |
| Redis down | High | Slower, no caching | TBD |
| OpenAI API down | Critical | No extracts/judgments | TBD |
| Brave Search down | High | No evidence | TBD |
| NLI model OOM | Critical | Verification fails | TBD |

---

## 📊 SCALABILITY ANALYSIS

### Horizontal Scaling

| Workers | Throughput | Latency (p95) | Cost/Hour | Notes |
|---------|------------|---------------|-----------|-------|
| 1 | TBD checks/min | TBD | TBD | Baseline |
| 2 | TBD checks/min | TBD | TBD | Linear? |
| 5 | TBD checks/min | TBD | TBD | - |
| 10 | TBD checks/min | TBD | TBD | Breaking point? |

**Scaling Factor**: TBD (linear/sublinear/superlinear)
**Optimal Worker Count**: TBD (cost vs performance)

### Vertical Scaling

| CPU/Memory | Throughput | Latency | Cost/Hour | Notes |
|------------|------------|---------|-----------|-------|
| 2 CPU / 4GB | TBD | TBD | TBD | Baseline |
| 4 CPU / 8GB | TBD | TBD | TBD | - |
| 8 CPU / 16GB | TBD | TBD | TBD | - |

**Scaling Factor**: TBD
**Optimal Configuration**: TBD

---

## 🎯 FEATURE OVERHEAD

### Individual Feature Overhead (from existing tests)

| Feature | Overhead (ms) | % of Target | Budget | Status |
|---------|--------------|-------------|--------|--------|
| Deduplication | <200ms | 15% | 200ms | ✅ Within budget |
| Source Independence | <100ms | 8% | 100ms | ✅ Within budget |
| Fact-Check Detection | <50ms | 4% | 50ms | ✅ Within budget |
| Temporal Analysis | <150ms | 12% | 150ms | ✅ Within budget |
| Claim Classification | <100ms | 8% | 100ms | ✅ Within budget |
| Explainability | <200ms | 15% | 200ms | ✅ Within budget |
| Domain Capping | <50ms | 4% | 50ms | ✅ Within budget |
| **TOTAL** | **<850ms** | **65%** | **1300ms** | ✅ Within budget |

**Remaining Budget**: 450ms (for other features)

### Feature Combinations

| Features Enabled | Overhead (ms) | Notes |
|------------------|--------------|-------|
| All Phase 1 | TBD | Phase 1 features only |
| All Phase 1-2 | TBD | + Temporal + Classification |
| All Phase 1-3 | TBD | + Credibility + Abstention |
| All features | TBD | Full feature set |

---

## 🚨 CAPACITY PLANNING

### Production Sizing Recommendations

**Based on Phase 4 testing results** (to be completed):

| User Load | Checks/Day | Workers | Database | Redis | Est. Cost/Month |
|-----------|------------|---------|----------|-------|-----------------|
| Low (MVP) | 100 | TBD | TBD | TBD | TBD |
| Medium | 1,000 | TBD | TBD | TBD | TBD |
| High | 10,000 | TBD | TBD | TBD | TBD |

### Monitoring Thresholds

| Metric | Warning | Critical | Action |
|--------|---------|----------|--------|
| Pipeline latency (p95) | >8s | >12s | Scale workers |
| Memory per worker | >TBD MB | >TBD MB | Restart worker |
| Database connections | >80% pool | >95% pool | Increase pool |
| Redis operations/sec | >TBD | >TBD | Add replica |
| Error rate | >5% | >10% | Page on-call |
| Queue depth | >100 | >500 | Scale workers |

---

## 📝 TEST METHODOLOGY

### How These Limits Were Measured

*(To be completed in Phase 4)*

**Test Environment**:
- Hardware: TBD
- OS: TBD
- Python version: TBD
- Database: TBD
- Redis: TBD

**Test Methodology**:
1. Baseline measurement (single check)
2. Incremental load increase (1, 5, 10, 25, 50, 100 concurrent)
3. Sustained load test (1 hour)
4. Breaking point identification
5. Resource profiling (memory, CPU, I/O)
6. Cost analysis

**Test Data**:
- Representative content samples
- Various input types (URL, text, image, video)
- Claims of varying complexity
- Mock external API responses (controlled latency)

---

## 🔗 Related Documentation

- [TESTING_MASTER_TRACKER.md](./TESTING_MASTER_TRACKER.md) - Overall testing progress
- [PHASE_4_COMPLETION.md](./PHASE_4_COMPLETION.md) - Performance testing results
- [KNOWN_ISSUES.md](./KNOWN_ISSUES.md) - Known limitations
- [Backend Configuration](../../app/core/config.py) - All configured limits

---

**Document Status**: 🟡 DRAFT - To be completed in Phase 4
**Last Updated**: 2025-11-03 14:45:00 UTC
**Version**: 0.1.0 (Template)
**Maintained By**: Testing Team
