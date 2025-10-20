# Pipeline Enhancement Implementation Risk Analysis

**Date:** October 17, 2025
**Subject:** Risk assessment for 8-concern pipeline improvements
**Current Codebase:** ~6,000 lines Python, 30 files

---

## 📊 Change Size Breakdown

### Quantitative Analysis

| Metric | Current | After Phase 1 | After All Phases | Change % |
|--------|---------|---------------|------------------|----------|
| **Python Files** | 30 | 35 (+5 new) | 42 (+12 new) | +40% |
| **Lines of Code** | ~6,000 | ~8,500 (+2,500) | ~11,500 (+5,500) | +92% |
| **Database Fields** | ~25 | ~40 (+15) | ~60 (+35) | +140% |
| **Pipeline Code** | 1,705 lines | ~2,400 (+700) | ~3,200 (+1,500) | +88% |
| **Modified Core Files** | 0 | 5 files | 12 files | - |

### Change Distribution

**Phase 1 (Critical - 2 weeks):**
- **New Files:** 3 (deduplication.py, source_independence.py, analytics.py base)
- **Modified Files:** 5 (retrieve.py, verify.py, judge.py, check.py, pipeline.py)
- **New Code:** ~2,500 lines
- **Modified Code:** ~400 lines changed
- **Database Changes:** 15 new fields, 4 indexes

**Full Implementation (All Phases - 4.5 weeks):**
- **New Files:** 12 utility/service modules
- **Modified Files:** 12 existing pipeline files
- **New Code:** ~5,500 lines
- **Modified Code:** ~800 lines changed
- **Database Changes:** 35 new fields, 8 indexes

---

## 🎯 Risk Assessment

### Overall Risk Level: 🟡 MEDIUM-HIGH

**Risk Score:** 6.5/10

While the changes are significant, they are **largely additive** rather than destructive. However, pipeline modification always carries integration risk.

### Risk Breakdown by Category

#### 1. **Code Stability Risk:** 🟠 MEDIUM (5/10)

**Why Medium:**
- ✅ Most changes are NEW utilities (not modifying core logic)
- ✅ Existing functions remain intact (we extend, not replace)
- ⚠️ Pipeline flow changes in 5 critical files
- ❌ Integration points create dependency chain

**Specific Vulnerabilities:**

| File | Risk Level | Reason |
|------|-----------|---------|
| `retrieve.py` | 🔴 HIGH | Core evidence retrieval - 3 new functions inserted |
| `verify.py` | 🟠 MEDIUM | Aggregation logic modified - adds diversity metrics |
| `judge.py` | 🟠 MEDIUM | Judgment context modified - adds safety/diversity |
| `pipeline.py` | 🟡 LOW | Only adds logging, doesn't change flow |
| `check.py` | 🟢 VERY LOW | Only schema additions, no logic |

**Current Code Safety Features:**
- ✅ Extensive try/except blocks already in place
- ✅ Fallback logic for every stage
- ✅ Pipeline continues even if enhancement fails
- ❌ No unit tests currently protecting pipeline logic

#### 2. **Database Migration Risk:** 🟡 MEDIUM-LOW (4/10)

**Why Medium-Low:**
- ✅ All new fields are NULLABLE or have DEFAULT values
- ✅ No breaking schema changes (no column drops, renames)
- ✅ Indexes can be added in background
- ⚠️ 35 new fields may cause slow migration on large tables
- ⚠️ Downgrade path not trivial (data loss if rollback)

**Migration Complexity:**

```sql
-- Phase 1 Migration (~15 fields, <5 min on empty DB)
ALTER TABLE evidence ADD COLUMN content_hash TEXT;
ALTER TABLE evidence ADD COLUMN parent_company TEXT;
-- ... 13 more ADDs

-- Risk: If production has 100k+ evidence rows, takes 10-30 mins
-- Mitigation: Run during maintenance window
```

**Safe Migration Strategy:**
1. Add columns with NULL defaults (fast)
2. Backfill asynchronously (non-blocking)
3. Add constraints later (after backfill)

#### 3. **Performance Degradation Risk:** 🔴 MEDIUM-HIGH (7/10)

**Why Medium-High:**
- ❌ New processing steps add latency at each stage
- ❌ Deduplication is O(n²) worst case
- ❌ Diversity checking requires extra queries
- ⚠️ Embeddings for dedup may double memory usage
- ✅ Most operations can be cached

**Latency Impact Estimate:**

| Stage | Current | After Phase 1 | Impact |
|-------|---------|---------------|--------|
| Ingest | 0.5s | 0.7s (+0.2s) | Sanitization overhead |
| Extract | 2.5s | 2.5s (no change) | Cached |
| Retrieve | 3.0s | 4.2s (+1.2s) | Diversity + dedup |
| Verify | 2.0s | 2.5s (+0.5s) | Diversity metrics |
| Judge | 2.0s | 2.3s (+0.3s) | Enhanced context |
| **Total** | **10s** | **12.2s (+2.2s)** | **+22% slower** |

**Performance Risk Mitigation:**
- Cache diversity lookups (ownership map) → -0.5s
- Run deduplication async (non-blocking) → -0.8s
- Batch diversity checks → -0.3s
- **Optimized Total: ~10.6s (+6% slower)** ✅ Acceptable

#### 4. **Integration Risk:** 🟠 MEDIUM (6/10)

**Why Medium:**
- ⚠️ New utilities depend on each other (cascade failures possible)
- ⚠️ External services (archival) may timeout/fail
- ❌ No current integration tests covering full pipeline
- ✅ Fallback logic prevents total failures

**Dependency Chain:**

```
Pipeline → Retrieve → Deduplicator → Embeddings (existing)
                   → SourceIndependence → ownership.json (NEW)
                   → DomainCapping (logic only)

Judge → Verify → DiversityMetrics (NEW)
      → Safety → AdversarialDetector (NEW)

Archive → ArchivalService → Wayback/Archive.today (EXTERNAL)
```

**Failure Modes:**
1. **ownership.json missing** → Diversity checking disabled, pipeline continues ✅
2. **Embedding service down** → Text-based dedup used as fallback ✅
3. **Archival service timeout** → Evidence saved without archive, async retry ✅
4. **Safety detector error** → Content used unsanitized, logged for review ⚠️

#### 5. **Data Integrity Risk:** 🟡 LOW-MEDIUM (3/10)

**Why Low-Medium:**
- ✅ New fields are additive (existing data unaffected)
- ✅ No changes to verdict calculation logic (only enhances inputs)
- ⚠️ Deduplication may remove valid evidence (false positives)
- ⚠️ Domain capping may reduce evidence below minimum threshold

**Data Consistency Concerns:**

| Concern | Risk | Impact if Wrong |
|---------|------|----------------|
| Duplicate detection false positive | 🟠 MEDIUM | Valid evidence removed, verdict less confident |
| Domain cap too aggressive | 🟠 MEDIUM | Insufficient evidence → "uncertain" verdict |
| Ownership map outdated | 🟡 LOW | Incorrect parent company assignment |
| Adversarial detection false positive | 🟡 LOW | Legitimate content flagged |

#### 6. **Rollback Risk:** 🔴 HIGH (8/10)

**Why High:**
- ❌ Database fields cannot be removed without data loss
- ❌ If pipeline breaks, rolling back code leaves orphaned data
- ❌ Cached results will be invalid after rollback
- ⚠️ No automated rollback procedure defined

**Rollback Complexity:**

```bash
# If Phase 1 fails in production:
1. Revert code deployment (easy) ✅
2. Database has new fields with partial data (orphaned) ❌
3. Cache contains results with new structure (invalid) ❌
4. Must manually:
   - Clear Redis cache
   - Decide: keep DB fields (harmless) or drop (loses data)
   - Re-run affected checks? Or accept inconsistency?
```

**Rollback Preparation Time:** 2-4 hours of manual intervention

---

## 🛡️ Risk Mitigation Strategy

### Strategy 1: Incremental Deployment with Feature Flags ⭐ RECOMMENDED

**Approach:** Deploy all code but disable enhancements with feature flags

```python
# config.py
class Settings(BaseSettings):
    # Feature flags for gradual rollout
    ENABLE_SOURCE_DIVERSITY: bool = Field(False, env="ENABLE_SOURCE_DIVERSITY")
    ENABLE_DEDUPLICATION: bool = Field(False, env="ENABLE_DEDUPLICATION")
    ENABLE_DOMAIN_CAPPING: bool = Field(False, env="ENABLE_DOMAIN_CAPPING")
    ENABLE_SAFETY_CHECKING: bool = Field(False, env="ENABLE_SAFETY_CHECKING")

# retrieve.py modifications
if settings.ENABLE_DEDUPLICATION:
    deduplicated, dedup_stats = deduplicator.deduplicate(evidence_list, embeddings)
else:
    deduplicated = evidence_list  # No-op, existing behavior
```

**Benefits:**
- ✅ Code deployed once, enabled incrementally
- ✅ Can A/B test each enhancement separately
- ✅ Instant rollback via env var (no code redeployment)
- ✅ Monitor impact of each feature in isolation

**Rollout Plan:**
1. **Week 1:** Deploy all code, flags OFF → Validate no regressions
2. **Week 2:** Enable domain capping (low risk) → Monitor latency
3. **Week 3:** Enable deduplication → Monitor verdict changes
4. **Week 4:** Enable source diversity → Full system test
5. **Week 5:** Enable all flags → Production-ready

**Rollback:** Set flag to `False` in env → instant disable, zero downtime

---

### Strategy 2: Parallel Pipeline (Shadow Mode)

**Approach:** Run enhanced pipeline alongside existing, compare results

```python
# pipeline.py
async def process_check(self, check_id: str, ...):
    # Run existing pipeline
    result_v1 = await self._run_pipeline_v1(...)

    # Run enhanced pipeline in background (non-blocking)
    if settings.ENABLE_SHADOW_PIPELINE:
        asyncio.create_task(self._run_pipeline_v2_shadow(check_id, ...))

    # Return v1 results to user
    return result_v1

async def _run_pipeline_v2_shadow(self, check_id: str, ...):
    """Run enhanced pipeline, compare to v1, log differences"""
    result_v2 = await self._run_pipeline_v2(...)

    # Compare verdicts
    comparison = self._compare_results(result_v1, result_v2)
    logger.info(f"Shadow comparison: {comparison}")

    # Store in separate table for analysis
    await self._store_shadow_result(check_id, result_v2, comparison)
```

**Benefits:**
- ✅ Zero risk to production users (v1 always used)
- ✅ Real-world testing with production traffic
- ✅ Can analyze verdict changes before going live
- ✅ Gradual confidence building

**Drawbacks:**
- ❌ Doubles compute cost (running 2 pipelines)
- ❌ Slower to production (requires analysis period)

**Timeline:**
- Week 1-2: Shadow mode, collect data
- Week 3: Analyze differences, tune thresholds
- Week 4: Switch to v2 if results acceptable

---

### Strategy 3: Staged Rollout by User Tier

**Approach:** Enable enhancements for internal users first, then Pro, then Free

```python
# pipeline.py
def should_use_enhanced_pipeline(user_id: str) -> bool:
    # Stage 1: Internal users only
    if user_id in settings.INTERNAL_USER_IDS:
        return True

    # Stage 2: Pro subscribers (after 1 week)
    if user_tier == "pro" and datetime.now() > settings.PRO_ROLLOUT_DATE:
        return True

    # Stage 3: All users (after 2 weeks)
    if datetime.now() > settings.FULL_ROLLOUT_DATE:
        return True

    return False
```

**Benefits:**
- ✅ Limit blast radius (internal users affected first)
- ✅ Can gather feedback from trusted users
- ✅ Gradual load increase (performance testing)

**Drawbacks:**
- ⚠️ Inconsistent user experience during rollout
- ⚠️ Requires user tier tracking

---

### Strategy 4: Comprehensive Testing Before Merge ⭐ ESSENTIAL

**Approach:** Build robust test suite before implementation

```python
# tests/pipeline/test_deduplication.py
def test_exact_duplicate_removal():
    """Ensure exact duplicates are removed"""
    evidence = [
        {"text": "GDP grew by 3%", "url": "bbc.com/1"},
        {"text": "GDP grew by 3%", "url": "yahoo.com/bbc"},  # Syndicated
    ]
    deduplicator = EvidenceDeduplicator()
    deduplicated, stats = deduplicator.deduplicate(evidence)

    assert len(deduplicated) == 1
    assert stats["duplicates_removed"] == 1

def test_domain_capping():
    """Ensure no domain exceeds 40% of evidence"""
    evidence = [
        {"url": "dailymail.co.uk/1", "final_score": 0.9},
        {"url": "dailymail.co.uk/2", "final_score": 0.85},
        {"url": "dailymail.co.uk/3", "final_score": 0.8},
        {"url": "bbc.com/1", "final_score": 0.75},
        {"url": "reuters.com/1", "final_score": 0.7},
    ]
    retriever = EvidenceRetriever()
    capped = retriever._apply_domain_caps(evidence)

    # Max 40% = max 2 from dailymail (out of 5 total)
    dailymail_count = sum(1 for e in capped if "dailymail" in e["url"])
    assert dailymail_count <= 2

# tests/pipeline/test_integration.py
@pytest.mark.asyncio
async def test_full_pipeline_with_enhancements():
    """Integration test: full pipeline with all enhancements enabled"""
    input_data = {
        "input_type": "text",
        "content": "The GDP grew by 3% in 2023."
    }

    result = await process_check(check_id="test", user_id="test", input_data=input_data)

    assert result["status"] == "completed"
    assert len(result["claims"]) > 0
    assert result["claims"][0]["verdict"] in ["supported", "contradicted", "uncertain"]

    # Verify enhancements applied
    claim = result["claims"][0]
    assert "verification_signals" in claim
    assert "source_diversity_score" in claim["verification_signals"]
```

**Test Coverage Required:**

| Component | Unit Tests | Integration Tests | Total |
|-----------|-----------|-------------------|-------|
| Deduplication | 8 tests | 2 tests | 10 |
| Source Diversity | 6 tests | 2 tests | 8 |
| Domain Capping | 5 tests | 1 test | 6 |
| Safety Checking | 10 tests | 2 tests | 12 |
| Full Pipeline | - | 5 tests | 5 |
| **Total** | **29** | **12** | **41 tests** |

**Testing Timeline:**
- Write tests: 3 days (parallel with implementation)
- Run tests before merge: 1 hour
- Fix failures: 1-2 days contingency

---

### Strategy 5: Database Migration Safety

**Approach:** Zero-downtime migrations with backfill strategy

```sql
-- Step 1: Add columns (fast, non-blocking)
ALTER TABLE evidence ADD COLUMN content_hash TEXT;
ALTER TABLE evidence ADD COLUMN parent_company TEXT;
-- ... (all new fields)

-- Step 2: Backfill asynchronously (background job)
-- backend/workers/backfill.py
@celery_app.task(name="backfill_content_hashes")
def backfill_content_hashes():
    """Backfill content_hash for existing evidence"""
    with sync_session() as session:
        # Process in batches to avoid lock contention
        batch_size = 1000
        offset = 0

        while True:
            stmt = select(Evidence).where(Evidence.content_hash == None).limit(batch_size)
            evidence_list = session.execute(stmt).scalars().all()

            if not evidence_list:
                break

            for evidence in evidence_list:
                # Calculate hash
                from app.utils.deduplication import EvidenceDeduplicator
                deduplicator = EvidenceDeduplicator()
                evidence.content_hash = deduplicator._hash_content(evidence.snippet)

            session.commit()
            offset += batch_size
            logger.info(f"Backfilled {offset} content hashes")

# Step 3: Add constraints AFTER backfill complete
-- (Run manually after backfill finishes)
-- ALTER TABLE evidence ADD CONSTRAINT ...
```

**Benefits:**
- ✅ No downtime during migration
- ✅ Existing data gradually enhanced
- ✅ Can rollback before constraints added

**Rollback Safety:**
```sql
-- Safe rollback (before constraints)
ALTER TABLE evidence DROP COLUMN content_hash;
-- Data lost, but no corruption

-- After constraints added: More complex
-- May need to disable constraints first
```

---

## 🎯 Recommended Mitigation Plan

### Hybrid Approach: Feature Flags + Comprehensive Testing + Staged Rollout

**Phase 1 Implementation Plan (2 weeks):**

#### Week 1: Build with Safety
1. **Day 1-2:** Write all 41 unit + integration tests
2. **Day 3-5:** Implement domain capping, deduplication, diversity checking
3. **Day 3-5:** Wrap ALL new code in feature flags (default: OFF)
4. **Day 5:** Database migration (add columns, start backfill)
5. **Day 5:** Deploy to dev environment, run full test suite
6. **Day 5:** Code review + security review

#### Week 2: Cautious Rollout
7. **Day 8:** Deploy to production with flags OFF → validate no regressions
8. **Day 9:** Enable domain capping for internal users only
9. **Day 10:** Enable deduplication for internal users → monitor
10. **Day 11:** Enable source diversity for internal users → analyze results
11. **Day 12:** If no issues, enable for 10% of Pro users (canary)
12. **Day 13:** Monitor canary group (verdict distribution, latency, errors)
13. **Day 14:** If canary successful, enable for all users
14. **Day 14:** Post-deployment monitoring + incident response readiness

**Success Criteria for Each Stage:**
- ✅ Error rate <2% (same as baseline)
- ✅ p95 latency <12s (within +20% target)
- ✅ Verdict distribution 15-25% uncertain (healthy)
- ✅ No user complaints about incorrect verdicts
- ❌ If any criterion fails → rollback flag, investigate

**Emergency Rollback Procedure:**
```bash
# Instant rollback (< 5 minutes)
1. Set env var: ENABLE_SOURCE_DIVERSITY=false
2. Set env var: ENABLE_DEDUPLICATION=false
3. Set env var: ENABLE_DOMAIN_CAPPING=false
4. Restart API servers (rolling restart, zero downtime)
5. Clear Redis cache: redis-cli FLUSHDB
6. Monitor for recovery
```

---

## 📋 Risk Summary & Recommendation

### Quantified Risk Assessment

| Risk Category | Score | Mitigation Effectiveness | Residual Risk |
|--------------|-------|-------------------------|---------------|
| Code Stability | 5/10 | Feature flags + tests → 2/10 | 🟢 LOW |
| Database Migration | 4/10 | Zero-downtime strategy → 2/10 | 🟢 LOW |
| Performance | 7/10 | Caching + async → 4/10 | 🟡 MEDIUM |
| Integration | 6/10 | Comprehensive testing → 3/10 | 🟢 LOW |
| Data Integrity | 3/10 | Conservative thresholds → 2/10 | 🟢 LOW |
| Rollback | 8/10 | Feature flags → 2/10 | 🟢 LOW |

**Overall Residual Risk:** 🟢 2.5/10 (LOW) with full mitigation strategy

---

## ✅ Final Recommendation

### Proceed with Phase 1 Implementation

**Confidence Level:** HIGH (8/10)

**Reasoning:**
1. Changes are significant but **largely additive** (not destructive)
2. **Feature flags** provide instant rollback capability
3. **Existing fallback logic** in pipeline already handles failures gracefully
4. **Risk is well-contained** with proper testing and staged rollout
5. **Benefits outweigh risks** - pipeline quality is fundamental to product trust

### Critical Success Factors

**DO:**
- ✅ Write comprehensive test suite BEFORE implementation
- ✅ Use feature flags for all enhancements
- ✅ Deploy with flags OFF initially
- ✅ Enable for internal users first (1 week testing)
- ✅ Monitor performance and error rates closely
- ✅ Have rollback procedure documented and rehearsed

**DON'T:**
- ❌ Deploy all enhancements at once without testing
- ❌ Skip feature flags (removes rollback safety)
- ❌ Add database constraints before backfill complete
- ❌ Enable for all users immediately
- ❌ Ignore performance metrics during rollout

### Estimated Probability of Success

- **Without mitigation:** 60% (HIGH RISK)
- **With feature flags only:** 80% (MEDIUM RISK)
- **With full mitigation plan:** 95% (LOW RISK)

### Timeline with Safety Measures

**Original estimate:** 2 weeks
**With comprehensive testing:** +3 days
**With staged rollout:** +5 days
**Total conservative timeline:** 3.5 weeks for Phase 1

**Trade-off:** Extra week of caution vs. lower risk → **Recommended**

---

**Conclusion:** This is a **manageable change** with **well-defined mitigation strategies**. The key is disciplined execution: feature flags, comprehensive testing, and staged rollout. With these safeguards, the risk is LOW and the pipeline quality improvements are achievable without jeopardizing the existing codebase.

