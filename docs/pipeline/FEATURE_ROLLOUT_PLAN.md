# Pipeline Improvements Feature Rollout Plan

## Overview
Gradual rollout strategy for pipeline improvement features to ensure stability and performance.

## Feature Flag Status
All features currently **disabled** by default in production. Enable incrementally after validation.

## Rollout Phases

### Phase 1: Testing & Validation (Week 1)
**Goal:** Verify features work correctly in isolation

#### Step 1.1: Enable Deduplication Only
```bash
# In backend/.env or config
ENABLE_EVIDENCE_DEDUPLICATION=true
```

**Validation:**
- Run 50 test checks with known duplicate content
- Verify `content_hash`, `is_syndicated`, `original_source_url` populated
- Check evidence count reduced appropriately
- Verify no performance degradation (<10s pipeline time)

**Success Criteria:**
- ✓ Duplicate detection rate >80% for known duplicates
- ✓ False positive rate <5%
- ✓ Processing time increase <500ms

#### Step 1.2: Enable Source Diversity
```bash
ENABLE_SOURCE_DIVERSITY=true
```

**Validation:**
- Run 50 checks on claims with known ownership clusters
- Verify `parent_company`, `independence_flag`, `domain_cluster_id` populated
- Check diversity scoring working correctly
- Monitor for over-penalization of legitimate sources

**Success Criteria:**
- ✓ Domain clustering accuracy >70%
- ✓ Independence flags assigned correctly
- ✓ No single-owner domination in top 10 results

#### Step 1.3: Enable Fact-check Integration
```bash
ENABLE_FACTCHECK_INTEGRATION=true
```

**Validation:**
- Run 30 checks on claims with known fact-checks
- Verify fact-checks detected via Google Fact Check API
- Check `is_factcheck`, `factcheck_publisher`, `factcheck_rating` populated
- Validate fact-check weight bonus applied correctly

**Success Criteria:**
- ✓ Fact-check detection rate >85% for known fact-checks
- ✓ Publisher names normalized correctly
- ✓ Ratings mapped to verdict appropriately

### Phase 2: Temporal & Classification (Week 2)

#### Step 2.1: Enable Temporal Context
```bash
ENABLE_TEMPORAL_CONTEXT=true
```

**Validation:**
- Run 40 checks: 20 time-sensitive, 20 timeless
- Verify `temporal_markers`, `time_reference`, `is_time_sensitive` populated
- Check temporal filtering applied in evidence retrieval
- Validate temporal relevance scoring

**Success Criteria:**
- ✓ Time-sensitive detection accuracy >75%
- ✓ Temporal markers extracted correctly
- ✓ Evidence filtered to relevant time windows
- ✓ Old evidence downranked appropriately

#### Step 2.2: Enable Claim Classification
```bash
ENABLE_CLAIM_CLASSIFICATION=true
```

**Validation:**
- Run 60 checks across claim types:
  - 15 factual claims
  - 15 opinions
  - 15 predictions
  - 15 personal experiences
- Verify `claim_type`, `is_verifiable`, `verifiability_reason` populated
- Check non-verifiable claims handled gracefully

**Success Criteria:**
- ✓ Classification accuracy >80% per type
- ✓ Clear explanations for non-verifiable claims
- ✓ No false "unverifiable" flags on factual claims

### Phase 3: Explainability (Week 3)

#### Step 3.1: Enable Enhanced Explainability
```bash
ENABLE_ENHANCED_EXPLAINABILITY=true
```

**Validation:**
- Run 50 checks with varied evidence quality
- Verify `decision_trail`, `transparency_score` populated
- Check `uncertainty_explanation` present for uncertain verdicts
- Validate `confidence_breakdown` factors make sense

**Success Criteria:**
- ✓ Decision trails complete for all checks
- ✓ Transparency scores correlate with evidence quality
- ✓ Uncertainty explanations helpful and accurate
- ✓ Confidence breakdowns match rationale

### Phase 4: Combined Integration (Week 4)

#### Step 4.1: Enable All Features
```bash
ENABLE_EVIDENCE_DEDUPLICATION=true
ENABLE_SOURCE_DIVERSITY=true
ENABLE_FACTCHECK_INTEGRATION=true
ENABLE_TEMPORAL_CONTEXT=true
ENABLE_CLAIM_CLASSIFICATION=true
ENABLE_ENHANCED_EXPLAINABILITY=true
```

**Validation:**
- Run 100 diverse real-world checks
- Verify all features interact correctly
- Check for feature conflicts or unexpected interactions
- Monitor overall performance impact

**Success Criteria:**
- ✓ All features working simultaneously
- ✓ No feature conflicts or bugs
- ✓ Total processing time <12s p95
- ✓ Token cost increase <30%

## Performance Monitoring

### Key Metrics to Track

**Latency Impact:**
```
Target: p95 processing time <12s (up from 10s baseline)

Per-feature impact budget:
- Deduplication: +200ms (hashing overhead)
- Diversity: +100ms (clustering lookups)
- Fact-check: +500ms (API calls)
- Temporal: +150ms (regex analysis)
- Classification: +100ms (pattern matching)
- Explainability: +200ms (trail generation)

Total budget: +1250ms = 11.25s total
```

**Token Cost Impact:**
```
Baseline: $0.02 per check

Expected increases:
- Deduplication: No increase (filtering)
- Diversity: No increase (metadata only)
- Fact-check: +$0.001 (API calls, not LLM)
- Temporal: No increase (regex only)
- Classification: No increase (regex only)
- Explainability: No increase (aggregation only)

Target: <$0.022 per check (+10%)
```

**Quality Improvements:**
```
- Evidence diversity score increase: +20%
- Duplicate reduction: -30% redundant evidence
- Fact-check inclusion rate: +15%
- Temporal accuracy: +25% for time-sensitive claims
- Transparency score avg: >0.7
```

## Rollback Procedures

### If Feature Causes Issues

**Quick Disable:**
```bash
# Disable specific feature immediately
export ENABLE_[FEATURE_NAME]=false
# Restart workers
supervisorctl restart celery-worker
```

**Partial Rollback:**
```bash
# Keep working features, disable problematic one
ENABLE_EVIDENCE_DEDUPLICATION=true
ENABLE_SOURCE_DIVERSITY=true
ENABLE_FACTCHECK_INTEGRATION=false  # ← Disabled
ENABLE_TEMPORAL_CONTEXT=true
ENABLE_CLAIM_CLASSIFICATION=true
ENABLE_ENHANCED_EXPLAINABILITY=true
```

**Full Rollback:**
```bash
# Disable all new features
ENABLE_EVIDENCE_DEDUPLICATION=false
ENABLE_SOURCE_DIVERSITY=false
ENABLE_FACTCHECK_INTEGRATION=false
ENABLE_TEMPORAL_CONTEXT=false
ENABLE_CLAIM_CLASSIFICATION=false
ENABLE_ENHANCED_EXPLAINABILITY=false
```

**Database Rollback (if critical):**
```bash
cd backend
alembic downgrade -1  # Rollback one migration
# WARNING: This removes all new fields and data
```

## Gradual User Exposure

### Internal Testing (Days 1-3)
- Enable for test accounts only
- Manual checks with known claims
- Monitor logs closely

### Beta Users (Days 4-7)
- Enable for 10% of users (feature flag)
- Mix of power users and regular users
- Collect feedback via in-app survey

### Gradual Rollout (Days 8-14)
- 25% of users (Day 8)
- 50% of users (Day 10)
- 75% of users (Day 12)
- 100% of users (Day 14)

### Monitoring During Rollout
- Check error rates every 2 hours
- Monitor Sentry for new exceptions
- Track user feedback sentiment
- Watch PostHog funnel completion rates

## Post-Rollout Validation

### After Full Rollout (Day 15+)

**Quantitative Checks:**
- [ ] Average transparency score >0.7
- [ ] <5% increase in error rate
- [ ] Processing time p95 <12s
- [ ] Token cost <$0.025 per check
- [ ] User retention unchanged or improved

**Qualitative Checks:**
- [ ] User feedback predominantly positive
- [ ] No increase in support tickets
- [ ] Team confidence in stability
- [ ] Clear improvements in verdict quality

**Success Declaration:**
Once all checks pass for 7 consecutive days, features considered stable and default-enabled.

## Feature-Specific Gotchas

### Deduplication
⚠️ **Watch for:** Over-aggressive deduplication removing legitimate similar sources
🔧 **Fix:** Adjust content hash normalization sensitivity

### Source Diversity
⚠️ **Watch for:** Incorrect parent company mappings
🔧 **Fix:** Update domain ownership database regularly

### Fact-check Integration
⚠️ **Watch for:** Google API rate limits (quota exhaustion)
🔧 **Fix:** Implement caching, consider alternative APIs

### Temporal Context
⚠️ **Watch for:** False positives on time-sensitive detection
🔧 **Fix:** Refine regex patterns, add confidence thresholds

### Claim Classification
⚠️ **Watch for:** Factual claims misclassified as opinions
🔧 **Fix:** Improve pattern matching, consider ML classifier

### Explainability
⚠️ **Watch for:** Decision trails too verbose or unclear
🔧 **Fix:** Simplify language, add structured formatting

## Communication Plan

### Internal Team
- Daily standups during rollout
- Slack alerts for critical metrics
- Weekly review of user feedback

### Users
- In-app changelog announcement
- Email to active users highlighting improvements
- Blog post explaining new features
- Help docs updated with examples

### Stakeholders
- Weekly progress reports
- Demo of improvements with real examples
- Metrics dashboard showing impact

---

**Next Review:** After Phase 1 completion (Week 1)
**Owner:** Engineering Team
**Last Updated:** 2025-10-20
