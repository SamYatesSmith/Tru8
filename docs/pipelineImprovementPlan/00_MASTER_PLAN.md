# Tru8 Pipeline Improvement Master Plan

**Version:** 1.0
**Strategy:** Option A - Aggressive MVI (Minimum Viable Intelligence)
**Total Duration:** 7.5 weeks
**Target:** Production-ready pipeline with structural integrity + semantic intelligence

---

## 🎯 Objectives

### Primary Goals
1. **Structural Integrity:** Make pipeline safe, reliable, bias-resistant (Phase 1)
2. **Semantic Intelligence:** Make pipeline smart, accurate, context-aware (Phase 1.5 + 2)
3. **User Trust:** Build transparent, explainable fact-checking system
4. **Operational Excellence:** Cost-efficient, monitorable, maintainable

### Success Criteria
- ✅ 95% reduction in systemic bias risks
- ✅ +30% accuracy on time-sensitive claims
- ✅ +20% accuracy on previously fact-checked claims
- ✅ 80%+ user trust score (measured via feedback)
- ✅ <12s p95 latency (within performance target)
- ✅ Zero critical security vulnerabilities
- ✅ 100% test coverage on new code

---

## 📅 Timeline Overview

```
Week 1-3.5:  Phase 1 - Structural Integrity (8 Concerns)
Week 4-5.5:  Phase 1.5 - Critical Semantic Intelligence
Week 5.5-7.5: Phase 2 - User Experience & Trust
```

### Detailed Schedule

| Week | Phase | Focus | Deliverables |
|------|-------|-------|--------------|
| **1** | 1 | Setup + Domain Capping | Branch, feature flags, domain limits |
| **2** | 1 | Evidence Deduplication | Dedup utility, integration, tests |
| **3** | 1 | Source Diversity | Ownership DB, diversity checking |
| **3.5** | 1 | Claim Context + Version Control | Context grouping, model versioning |
| **4-4.5** | 1.5 | Fact-Check API Integration | Google Fact Check wrapper, fast-path |
| **4.5-5.5** | 1.5 | Temporal Context | Time-sensitive detection, evidence filtering |
| **5.5-6.5** | 2 | Claim Classification | Claim type detection, verifiability checks |
| **6.5-7.5** | 2 | Explainability | Transparency, decision trails, user trust |

### Parallel Work Streams

**Week 1-7.5 (Continuous):**
- Test suite development (3 days/week dedicated)
- Documentation updates
- Code review and quality assurance
- Performance monitoring and optimization

---

## 📊 Implementation Structure

### Phase 1: Structural Integrity (3.5 weeks)
**Documents:** `02_PHASE1_STRUCTURAL.md`

**Concerns Addressed:**
1. Domain Weight Inflation (Week 1) - LOW complexity
2. Evidence Duplication (Week 2) - MEDIUM complexity
3. Systemic Bias Amplification (Week 3) - MEDIUM complexity
4. Claim Fragmentation (Week 3.5) - LOW complexity
5. Model Version Control (Week 3.5) - LOW complexity
6. Prompt Injection Safety (Week 3.5) - MEDIUM complexity
7. Citation Integrity (Background) - MEDIUM complexity
8. Verdict Balance Monitoring (Week 3.5) - LOW complexity

**Total New Code:** ~2,500 lines
**New Files:** 5 utilities + 4 services
**Modified Files:** 12 existing files
**Database Changes:** 15 new fields, 4 indexes

### Phase 1.5: Critical Semantic Intelligence (1.5 weeks)
**Documents:** `03_PHASE1.5_FACTCHECK_API.md`, `04_PHASE1.5_TEMPORAL.md`

**Features:**
1. **Fact-Check API Integration** (1 week)
   - Google Fact Check Explorer API wrapper
   - Fast-path pipeline for pre-verified claims
   - Verdict confidence boosting from existing fact-checks
   - **ROI:** 30% cost savings + 15-20% accuracy boost

2. **Temporal Context Awareness** (1 week)
   - Time-sensitive claim detection
   - Evidence temporal filtering
   - Recency validation
   - **ROI:** +25% accuracy on time-sensitive claims

**Total New Code:** ~1,800 lines
**New Files:** 2 services
**Modified Files:** 5 existing files
**Database Changes:** 5 new fields

### Phase 2: User Experience & Trust (2 weeks)
**Documents:** `05_PHASE2_CLAIM_CLASSIFICATION.md`, `06_PHASE2_EXPLAINABILITY.md`

**Features:**
1. **Claim Type Classification** (1 week)
   - Opinion vs. fact detection
   - Prediction vs. historical claim
   - Verifiability assessment
   - **ROI:** +30% user satisfaction, -15% wasted compute

2. **Enhanced Explainability** (1 week)
   - Transparent scoring breakdown
   - Decision trail visibility
   - Actionable uncertainty explanations
   - **ROI:** +40% user trust, -50% dispute rate

**Total New Code:** ~1,200 lines
**New Files:** 2 utilities
**Modified Files:** 4 existing files
**Database Changes:** 3 new fields

### Testing Strategy (Continuous)
**Document:** `07_TESTING_STRATEGY.md`

**Test Suite:**
- 41 unit tests (covering all new utilities)
- 12 integration tests (full pipeline scenarios)
- 8 adversarial tests (safety/security)
- 5 performance tests (latency, throughput)

**Coverage Target:** 85%+ on new code, 60%+ on modified files

---

## 🏗️ Technical Architecture

### New Components

**Utilities (app/utils/):**
```
app/utils/
├── deduplication.py          # Evidence dedup (Phase 1)
├── source_independence.py    # Domain diversity (Phase 1)
├── safety.py                 # Adversarial detection (Phase 1)
├── model_versions.py         # Version tracking (Phase 1)
├── temporal.py               # Time context (Phase 1.5)
├── claim_classifier.py       # Claim types (Phase 2)
└── explainability.py         # Transparency (Phase 2)
```

**Services (app/services/):**
```
app/services/
├── factcheck_api.py          # Fact-check integration (Phase 1.5)
├── archival.py               # URL archiving (Phase 1, background)
└── analytics.py              # Verdict monitoring (Phase 1)
```

**Data Files (backend/data/):**
```
backend/data/
├── source_ownership.json     # Media ownership database
├── factcheck_sources.json    # Trusted fact-check orgs
└── temporal_patterns.json    # Time marker patterns
```

### Modified Components

**Core Pipeline:**
- `pipeline.py` - Feature flag integration, version tracking
- `retrieve.py` - Domain capping, deduplication, diversity
- `verify.py` - Diversity metrics, temporal validation
- `judge.py` - Enhanced context, explainability, safety
- `extract.py` - Context preservation, temporal markers

**Models:**
- `check.py` - Safety tracking, temporal fields
- `models/claim.py` - Context grouping, version metadata

### Database Schema Evolution

**New Fields by Table:**

**Evidence (15 new fields):**
```sql
-- Source independence
parent_company TEXT
independence_flag TEXT
domain_cluster_id TEXT

-- Deduplication
content_hash TEXT
is_syndicated BOOLEAN
original_source_url TEXT

-- Archival
archived_url TEXT
archive_timestamp TIMESTAMP
archive_status TEXT
link_status TEXT
last_checked TIMESTAMP

-- Temporal
temporal_relevance_score FLOAT
extracted_date TEXT
is_time_sensitive BOOLEAN
temporal_window TEXT
```

**Claim (13 new fields):**
```sql
-- Context preservation
context_group_id TEXT
context_summary TEXT
depends_on_claim_ids JSONB

-- Version tracking
extraction_model_version TEXT
verification_model_version TEXT
judgment_model_version TEXT
pipeline_version TEXT
model_config_snapshot JSONB

-- Classification
claim_type TEXT
is_verifiable BOOLEAN
verifiability_reason TEXT

-- Temporal
temporal_markers JSONB
time_reference TEXT
```

**Check (5 new fields):**
```sql
-- Safety
safety_flags JSONB
adversarial_risk_score FLOAT

-- Temporal
temporal_context TEXT

-- Explainability
decision_trail JSONB
transparency_level TEXT
```

---

## 🔄 Integration Points

### Existing Systems

**Redis Cache:**
- New cache categories: `factcheck_results`, `claim_classification`, `temporal_analysis`
- Extended TTLs for fact-check data (30 days)
- Invalidation on model version changes

**Qdrant Vector Store:**
- Store temporal metadata with embeddings
- Filter by time_relevance in similarity search
- Track embedding model versions

**Celery Workers:**
- New background tasks: `archive_evidence_urls`, `check_link_health`, `monitor_verdict_distribution`
- Scheduled tasks for analytics and maintenance
- Priority queues for fact-check lookups (high priority)

### External APIs

**New Integrations:**
- Google Fact Check Explorer API (Phase 1.5)
- Internet Archive Wayback Machine API (Phase 1, background)
- Optional: Archive.today API (fallback)

**Enhanced Existing:**
- Brave Search: Add temporal filters
- OpenAI: Track model versions, token usage per feature
- Embeddings: Version tracking, cache invalidation on model updates

---

## ⚙️ Feature Flags

### Configuration (config.py)

```python
class Settings(BaseSettings):
    # Phase 1 - Structural
    ENABLE_DOMAIN_CAPPING: bool = Field(False, env="ENABLE_DOMAIN_CAPPING")
    ENABLE_DEDUPLICATION: bool = Field(False, env="ENABLE_DEDUPLICATION")
    ENABLE_SOURCE_DIVERSITY: bool = Field(False, env="ENABLE_SOURCE_DIVERSITY")
    ENABLE_CONTEXT_PRESERVATION: bool = Field(False, env="ENABLE_CONTEXT_PRESERVATION")
    ENABLE_SAFETY_CHECKING: bool = Field(False, env="ENABLE_SAFETY_CHECKING")
    ENABLE_CITATION_ARCHIVAL: bool = Field(False, env="ENABLE_CITATION_ARCHIVAL")
    ENABLE_VERDICT_MONITORING: bool = Field(False, env="ENABLE_VERDICT_MONITORING")

    # Phase 1.5 - Semantic
    ENABLE_FACTCHECK_API: bool = Field(False, env="ENABLE_FACTCHECK_API")
    ENABLE_TEMPORAL_CONTEXT: bool = Field(False, env="ENABLE_TEMPORAL_CONTEXT")

    # Phase 2 - UX
    ENABLE_CLAIM_CLASSIFICATION: bool = Field(False, env="ENABLE_CLAIM_CLASSIFICATION")
    ENABLE_ENHANCED_EXPLAINABILITY: bool = Field(False, env="ENABLE_ENHANCED_EXPLAINABILITY")

    # Rollout Controls
    FEATURE_ROLLOUT_PERCENTAGE: int = Field(0, env="FEATURE_ROLLOUT_PERCENTAGE")
    INTERNAL_USER_IDS: List[str] = Field([], env="INTERNAL_USER_IDS")
```

### Rollout Strategy

**Week 1-3.5:** Deploy all code with flags OFF
**Week 4:** Enable Phase 1 features for internal users (10 test accounts)
**Week 5:** Enable for 10% of Pro users (canary group)
**Week 6:** Enable Phase 1.5 for internal users
**Week 7:** Enable Phase 1.5 for canary, expand to 25% users
**Week 7.5:** Enable Phase 2, full rollout to 100% if metrics pass

**Metrics for Progression:**
- Error rate <2% (baseline)
- p95 latency <12s
- Verdict distribution 15-25% uncertain
- User feedback >70% positive
- No critical bugs reported

---

## 🛡️ Risk Mitigation

### Git Strategy
**Document:** `01_GIT_STRATEGY.md`

**Branch Structure:**
```
main
└── feature/pipeline-improvements-v2
    ├── phase1/domain-capping
    ├── phase1/deduplication
    ├── phase1/source-diversity
    ├── phase1.5/factcheck-api
    ├── phase1.5/temporal-context
    ├── phase2/claim-classification
    └── phase2/explainability
```

**Safeguards:**
- Feature branches merge to main feature branch first
- All merges require tests passing + code review
- Database migrations in separate commits (can revert code without losing data)
- Feature flags prevent activation until ready

### Rollback Procedures

**Instant Rollback (< 5 min):**
```bash
# Disable feature flag via env var
export ENABLE_FEATURE_NAME=false
# Restart API servers (zero downtime)
# Clear cache
```

**Code Rollback (30 min):**
```bash
git revert <commit-hash>
git push origin feature/pipeline-improvements-v2
# Redeploy
```

**Database Rollback (variable):**
- Add new fields: Safe, keep them (data preserved)
- Drop fields: Only if absolutely necessary, manual backup first
- Change constraints: Revert constraint, keep data

### Performance Safeguards

**Latency Monitoring:**
- Track p50, p95, p99 latency per pipeline stage
- Alert if p95 >12s
- Automatic flag disable if p99 >20s (circuit breaker)

**Cost Monitoring:**
- Track token usage per feature
- Alert if daily cost >$100
- Per-user cost caps enforced

---

## 📈 Success Metrics

### Accuracy Metrics

| Metric | Baseline | Target | Measurement |
|--------|----------|--------|-------------|
| Overall verdict accuracy | 70% | 85% | Manual review of 100 checks/week |
| Time-sensitive claim accuracy | 55% | 80% | Date-specific claims validation |
| Previously fact-checked accuracy | 75% | 95% | Compare to known fact-checks |
| Uncertain verdict ratio | 35% | 15-25% | Automated tracking |

### Performance Metrics

| Metric | Baseline | Target | Measurement |
|--------|----------|--------|-------------|
| p50 latency | 8s | <10s | APM monitoring |
| p95 latency | 14s | <12s | APM monitoring |
| p99 latency | 20s | <15s | APM monitoring |
| Cost per check | $0.035 | <$0.03 | Token usage tracking |

### User Experience Metrics

| Metric | Baseline | Target | Measurement |
|--------|----------|--------|-------------|
| User trust score | N/A | >70% | Post-check survey |
| Dispute rate | N/A | <10% | "Report incorrect" clicks |
| Repeat usage rate | 40% | >60% | User retention analytics |
| Feedback sentiment | N/A | >75% positive | NPS + feedback analysis |

### Operational Metrics

| Metric | Baseline | Target | Measurement |
|--------|----------|--------|-------------|
| Error rate | 3% | <2% | Sentry tracking |
| Cache hit rate | 45% | >65% | Redis metrics |
| Test coverage | 0% | >85% new code | pytest-cov |
| Code review turnaround | N/A | <24h | GitHub metrics |

---

## 👥 Team & Resources

### Required Expertise
- **Backend Development:** Python, FastAPI, async/await patterns
- **ML/NLP:** LLM prompting, NLI models, embeddings
- **Database:** PostgreSQL migrations, indexing, query optimization
- **Testing:** pytest, integration testing, mocking
- **DevOps:** Feature flags, deployment, monitoring

### External Dependencies
- Google Fact Check Explorer API access
- Internet Archive API (rate limits)
- OpenAI API stability
- Redis/Qdrant uptime

### Documentation
- Code comments for all new functions
- API documentation for new endpoints
- README updates for setup/deployment
- Runbooks for rollback procedures

---

## 🎯 Next Steps

### Immediate Actions (Week 1, Day 1)

1. **Git Setup:**
   - Create feature branch: `feature/pipeline-improvements-v2`
   - Set up branch protection rules
   - Configure CI/CD for new branch

2. **Environment Setup:**
   - Add all feature flags to `.env.example`
   - Set all flags to `False` initially
   - Document flag purposes in config.py

3. **Team Alignment:**
   - Review master plan
   - Assign phase ownership
   - Schedule daily standups

4. **Testing Infrastructure:**
   - Set up pytest configuration
   - Create test fixtures for pipeline
   - Install coverage tools

### Weekly Checkpoints

**Every Friday:**
- Review completed tasks vs. plan
- Run full test suite
- Check performance metrics
- Adjust next week's priorities if needed

**Every Monday:**
- Sprint planning for the week
- Identify blockers
- Coordinate dependencies

---

## 📚 Document Index

1. **00_MASTER_PLAN.md** (this document) - Overview and coordination
2. **01_GIT_STRATEGY.md** - Branching, commits, rollback procedures
3. **02_PHASE1_STRUCTURAL.md** - 8 structural integrity concerns
4. **03_PHASE1.5_FACTCHECK_API.md** - Fact-check integration detailed plan
5. **04_PHASE1.5_TEMPORAL.md** - Temporal context awareness detailed plan
6. **05_PHASE2_CLAIM_CLASSIFICATION.md** - Claim type classification plan
7. **06_PHASE2_EXPLAINABILITY.md** - Enhanced transparency plan
8. **07_TESTING_STRATEGY.md** - Comprehensive test suite specification

---

**Status:** READY TO BEGIN
**First Task:** Create feature branch and set up feature flags (Day 1)
**First Implementation:** Domain capping (Week 1)

