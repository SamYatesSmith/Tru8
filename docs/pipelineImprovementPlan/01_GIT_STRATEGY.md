# Git Strategy & Code Safety

**Purpose:** Protect existing codebase while implementing major improvements
**Risk Level:** MEDIUM-HIGH (92% code increase)
**Mitigation:** Branch strategy + feature flags + staged commits

---

## 🌿 Branch Structure

```
main (production)
│
└── feature/pipeline-improvements-v2 (main development branch)
    │
    ├── phase1/domain-capping → merge to feature/pipeline-improvements-v2
    ├── phase1/deduplication → merge to feature/pipeline-improvements-v2
    ├── phase1/source-diversity → merge to feature/pipeline-improvements-v2
    ├── phase1/context-and-versioning → merge to feature/pipeline-improvements-v2
    ├── phase1/safety-and-monitoring → merge to feature/pipeline-improvements-v2
    ├── phase1.5/factcheck-api → merge to feature/pipeline-improvements-v2
    ├── phase1.5/temporal-context → merge to feature/pipeline-improvements-v2
    ├── phase2/claim-classification → merge to feature/pipeline-improvements-v2
    └── phase2/explainability → merge to feature/pipeline-improvements-v2
```

**Merge Strategy:**
- Sub-feature branches → `feature/pipeline-improvements-v2` (after review + tests)
- `feature/pipeline-improvements-v2` → `main` (at end of each phase, after QA)

---

## 📝 Commit Guidelines

### Commit Message Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:**
- `feat`: New feature (domain capping, deduplication, etc.)
- `fix`: Bug fix
- `refactor`: Code restructuring without behavior change
- `test`: Adding tests
- `docs`: Documentation updates
- `chore`: Maintenance (dependencies, config)
- `db`: Database migrations

**Examples:**
```
feat(retrieve): Add domain capping logic
- Implement _apply_domain_caps() function
- Enforce 40% max per domain
- Add logging for domain distribution

BREAKING CHANGE: None (feature flag controlled)
Related: Phase 1, Week 1
```

```
db(evidence): Add source independence fields
- Add parent_company column (nullable)
- Add independence_flag column (nullable)
- Add domain_cluster_id column (nullable)
- Create migration script: add_source_independence_fields.sql

Related: Phase 1, Week 3
```

### Atomic Commits Strategy

**Each commit should be:**
1. **Self-contained:** Can be reverted independently
2. **Tested:** All tests pass
3. **Documented:** Clear commit message
4. **Small:** One logical change

**Bad:**
```bash
git commit -am "Add all Phase 1 features"
# Problem: Can't selectively revert, huge blast radius
```

**Good:**
```bash
git commit -am "feat(retrieve): Add domain capping utility"
git commit -am "feat(retrieve): Integrate domain capping in retrieve.py"
git commit -am "test(retrieve): Add domain capping tests"
git commit -am "db(evidence): Add domain tracking fields"
```

---

## 🔒 Branch Protection Rules

### For `main` branch:
- ✅ Require pull request reviews (minimum 1 reviewer)
- ✅ Require status checks to pass (CI/CD)
- ✅ Require branches to be up to date
- ✅ Prohibit force push
- ✅ Require signed commits (optional but recommended)

### For `feature/pipeline-improvements-v2`:
- ✅ Require status checks to pass
- ✅ Allow force push (for cleaning up history before main merge)
- ⚠️ No review required (but encouraged for major changes)

---

## 🚦 Pull Request Process

### Creating PR

**Template:**
```markdown
## Description
Brief description of changes

## Related Phase
- [ ] Phase 1 - Structural
- [ ] Phase 1.5 - Semantic
- [ ] Phase 2 - UX

## Type of Change
- [ ] New feature (non-breaking)
- [ ] Bug fix
- [ ] Database migration
- [ ] Test addition

## Testing
- [ ] All tests pass locally
- [ ] Added new tests for new code
- [ ] Manual testing completed

## Database Changes
- [ ] No database changes
- [ ] New fields added (backward compatible)
- [ ] Migration script created

## Feature Flag
- [ ] Feature flag added: ENABLE_<FEATURE_NAME>
- [ ] Default: False
- [ ] Documentation updated

## Checklist
- [ ] Code follows project style guidelines
- [ ] Comments added for complex logic
- [ ] Documentation updated
- [ ] No console.log/print statements left
- [ ] Performance impact assessed
```

### Review Checklist (Reviewer)

**Code Quality:**
- [ ] Code is readable and well-structured
- [ ] No unnecessary complexity
- [ ] Follows existing patterns
- [ ] Error handling is comprehensive

**Testing:**
- [ ] Tests cover new functionality
- [ ] Edge cases are tested
- [ ] Tests are meaningful (not just coverage padding)

**Safety:**
- [ ] Feature flag in place
- [ ] Backward compatible
- [ ] No breaking changes to existing code
- [ ] Rollback procedure documented

**Performance:**
- [ ] No obvious performance issues
- [ ] Database queries are optimized
- [ ] Caching is used appropriately

---

## 🗃️ Database Migration Strategy

### Migration File Naming

```
migrations/
├── 001_add_source_independence_fields.sql
├── 002_add_deduplication_fields.sql
├── 003_add_claim_context_fields.sql
├── 004_add_version_tracking_fields.sql
├── 005_add_safety_tracking_fields.sql
├── 006_add_temporal_fields.sql
├── 007_add_classification_fields.sql
└── 008_add_explainability_fields.sql
```

### Migration Commit Strategy

**Separate migration commits:**
```bash
# Wrong: Mix code + migration
git add backend/app/pipeline/retrieve.py backend/migrations/001_*.sql
git commit -m "feat: Add domain capping with migration"

# Right: Separate commits
git add backend/migrations/001_add_source_independence_fields.sql
git commit -m "db(evidence): Add source independence fields"

git add backend/app/pipeline/retrieve.py
git commit -m "feat(retrieve): Implement domain capping logic"
```

**Why:** If code has bugs but migration is fine, we can revert code commit while keeping migration.

### Migration Testing

**Before commit:**
```bash
# Test migration up
psycopg2 -f migrations/001_add_source_independence_fields.sql

# Test migration down (rollback)
psycopg2 -f migrations/rollback/001_rollback_source_independence.sql

# Verify both work without errors
```

---

## ⚡ Emergency Rollback Procedures

### Level 1: Feature Flag Disable (5 minutes)

**When:** Feature is causing errors but code/DB are fine

```bash
# 1. Set environment variable
export ENABLE_DOMAIN_CAPPING=false
export ENABLE_DEDUPLICATION=false

# 2. Restart API servers (zero downtime rolling restart)
kubectl rollout restart deployment/tru8-api  # If using k8s
# OR
pm2 restart tru8-api  # If using pm2

# 3. Clear affected cache
redis-cli
> FLUSHDB

# 4. Verify feature disabled
curl http://localhost:8000/api/v1/health
```

**Verification:**
- Check logs: Feature should not execute
- Run test check: Verify old behavior
- Monitor error rate: Should drop to baseline

---

### Level 2: Code Revert (30 minutes)

**When:** Feature flag disable doesn't help, code has fundamental issue

```bash
# 1. Identify problematic commit
git log --oneline feature/pipeline-improvements-v2

# 2. Create revert commit (preserves history)
git revert <commit-hash>
# Example: git revert a1b2c3d

# 3. Push to feature branch
git push origin feature/pipeline-improvements-v2

# 4. Deploy reverted code
# Trigger CI/CD pipeline or manual deploy

# 5. Clear cache
redis-cli FLUSHDB

# 6. Verify revert
# Run full test suite
pytest backend/tests/ -v
```

**DO NOT:**
- `git reset --hard` (loses history, dangerous)
- Force push to main (breaks other developers)
- Delete commits (makes debugging harder)

**DO:**
- Use `git revert` (creates new commit that undoes changes)
- Document why revert was necessary
- Create issue to fix and re-apply

---

### Level 3: Database Rollback (1-4 hours)

**When:** Migration caused data corruption or schema issues

**⚠️ HIGH RISK - Only if absolutely necessary**

```bash
# 1. BACKUP DATABASE FIRST
pg_dump tru8_production > backup_$(date +%Y%m%d_%H%M%S).sql

# 2. Run rollback migration
psycopg2 -f migrations/rollback/001_rollback_source_independence.sql

# 3. Verify schema
psql tru8_production
\d evidence  # Check columns are reverted

# 4. Restart services
# 5. Monitor for errors

# 6. If rollback fails, restore from backup
psql tru8_production < backup_20251017_120000.sql
```

**Prevention:**
- Test migrations on staging first
- Keep migrations small and focused
- Always create rollback scripts alongside migrations
- Never drop columns (mark as deprecated instead)

---

## 🧪 Pre-Merge Checklist

Before merging any branch to `feature/pipeline-improvements-v2`:

### Code Quality
- [ ] All tests pass: `pytest backend/tests/ -v`
- [ ] Linting passes: `black backend/ --check && isort backend/ --check`
- [ ] Type checking passes: `mypy backend/app/`
- [ ] No print statements or debug code
- [ ] Code coverage >85% for new files

### Feature Completeness
- [ ] Feature flag added and documented
- [ ] Feature works with flag ON
- [ ] Pipeline works with flag OFF (backward compatible)
- [ ] Error handling for all failure modes
- [ ] Logging added for debugging

### Database Safety
- [ ] Migration script tested on dev database
- [ ] Rollback script created and tested
- [ ] New fields are nullable (safe addition)
- [ ] Indexes added for performance
- [ ] Migration documented in changelog

### Documentation
- [ ] Code comments for complex logic
- [ ] README updated if setup changes
- [ ] API docs updated if endpoints change
- [ ] CHANGELOG.md entry added

### Testing
- [ ] Unit tests for new utilities
- [ ] Integration test for pipeline flow
- [ ] Edge case tests
- [ ] Performance test if latency-sensitive
- [ ] Manual testing completed

---

## 📊 Merge Frequency

### Sub-feature → Main Feature Branch
**Frequency:** Daily to every 2 days
**Size:** Small, focused changes
**Review:** Optional but encouraged

### Main Feature Branch → Main
**Frequency:** End of each phase (3 major merges over 7.5 weeks)
**Size:** Large, but well-tested
**Review:** MANDATORY, full QA

**Schedule:**
- Week 3.5: Phase 1 complete → Merge to main
- Week 5.5: Phase 1.5 complete → Merge to main
- Week 7.5: Phase 2 complete → Merge to main

---

## 🔍 Code Review Focus Areas

### Reviewers Should Check

**Architecture:**
- Does this follow existing patterns?
- Is this in the right place?
- Does this introduce tight coupling?

**Safety:**
- What happens if this fails?
- Is error handling comprehensive?
- Can this be rolled back?

**Performance:**
- Will this add latency?
- Is caching used appropriately?
- Are database queries optimized?

**Testing:**
- Do tests actually test the feature?
- Are edge cases covered?
- Can I understand what the test does?

**Security:**
- Is user input sanitized?
- Are there injection vulnerabilities?
- Is sensitive data handled properly?

---

## 🎯 Git Workflow Example

### Day 1: Start Domain Capping Feature

```bash
# 1. Create feature branch from main development branch
git checkout feature/pipeline-improvements-v2
git pull origin feature/pipeline-improvements-v2
git checkout -b phase1/domain-capping

# 2. Add feature flag
# Edit backend/app/core/config.py
ENABLE_DOMAIN_CAPPING: bool = Field(False, env="ENABLE_DOMAIN_CAPPING")

git add backend/app/core/config.py
git commit -m "feat(config): Add ENABLE_DOMAIN_CAPPING feature flag"

# 3. Implement domain capping utility
# Create backend/app/utils/domain_capping.py
git add backend/app/utils/domain_capping.py
git commit -m "feat(utils): Add domain capping utility with 40% limit"

# 4. Write tests
git add backend/tests/test_domain_capping.py
git commit -m "test(utils): Add domain capping tests (5 scenarios)"

# 5. Integrate into retrieve.py
git add backend/app/pipeline/retrieve.py
git commit -m "feat(retrieve): Integrate domain capping with feature flag"

# 6. Update documentation
git add docs/pipelineImprovementPlan/02_PHASE1_STRUCTURAL.md
git commit -m "docs: Update Phase 1 documentation with domain capping details"

# 7. Push feature branch
git push origin phase1/domain-capping

# 8. Create pull request
# Use GitHub/GitLab UI to create PR
# phase1/domain-capping → feature/pipeline-improvements-v2
```

### Day 2: Review and Merge

```bash
# After approval:
git checkout feature/pipeline-improvements-v2
git pull origin feature/pipeline-improvements-v2
git merge --no-ff phase1/domain-capping  # --no-ff preserves branch history
git push origin feature/pipeline-improvements-v2

# Delete feature branch (cleanup)
git branch -d phase1/domain-capping
git push origin --delete phase1/domain-capping
```

---

## 🚨 What NOT to Do

### ❌ DON'T:
1. Commit directly to `main`
2. Force push to shared branches
3. Mix unrelated changes in one commit
4. Commit without testing
5. Leave debug code (print, console.log)
6. Commit secrets or API keys
7. Create huge commits (>500 lines)
8. Skip writing commit messages
9. Merge without review
10. Delete migration files

### ✅ DO:
1. Use feature branches
2. Write meaningful commit messages
3. Keep commits atomic
4. Test before committing
5. Use feature flags
6. Document changes
7. Review others' code
8. Ask for help when stuck
9. Keep branches up to date
10. Clean up after merging

---

**Status:** Git strategy defined and ready to implement
**First Action:** Create `feature/pipeline-improvements-v2` branch (Day 1, Hour 1)

