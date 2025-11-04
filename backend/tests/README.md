# Tru8 Pipeline Testing Suite

**Project**: Tru8 Fact-Checking Platform
**Created**: 2025-11-03
**Last Updated**: 2025-11-03 14:50:00 UTC
**Code Version**: commit 388ac66
**Status**: Phase 0 Complete - Ready for Phase 1

---

## 📚 Overview

This directory contains a comprehensive testing suite for the Tru8 fact-checking pipeline. The testing strategy follows a **phase-based approach** with clear milestones, extensive documentation, and systematic coverage of all pipeline components.

**Testing Goals**:
- 🎯 Achieve 90%+ code coverage
- 🔍 Test all 6 pipeline stages thoroughly
- 🚀 Validate performance and scalability
- 🐛 Prevent regressions with known issue tests
- 📊 Document system limits and boundaries

---

## 📁 Directory Structure

```
tests/
├── 📁 unit/                          # Isolated component tests
│   ├── 📁 pipeline/                 # Pipeline stage tests
│   │   ├── test_ingest.py          # URL/Image/Video extraction (Phase 1)
│   │   ├── test_extract.py         # Claim extraction (Phase 1)
│   │   ├── test_retrieve.py        # Evidence retrieval (Phase 1)
│   │   ├── test_verify.py          # NLI verification (Phase 1)
│   │   ├── test_judge.py           # Verdict generation (Phase 1)
│   │   └── test_query_answer.py    # Search Clarity NEW (Phase 1)
│   │
│   ├── 📁 services/                 # Service layer tests (Phase 2)
│   │   ├── test_search.py          # Brave/SERP integration
│   │   ├── test_embeddings.py      # Sentence transformers
│   │   ├── test_evidence.py        # Evidence extraction
│   │   ├── test_cache.py           # Redis caching
│   │   ├── test_vector_store.py    # Qdrant operations
│   │   ├── test_pdf_evidence.py    # PDF processing
│   │   ├── test_push_notifications.py
│   │   └── test_source_monitor.py
│   │
│   ├── 📁 utils/                    # Utility tests (EXISTING ✅)
│   │   ├── test_claim_classifier.py      ✅ 16 tests
│   │   ├── test_deduplication.py         ✅ 15 tests
│   │   ├── test_domain_capping.py        ✅ 13 tests
│   │   ├── test_explainability.py        ✅ 17 tests
│   │   ├── test_factcheck_api.py         ✅ 7 tests
│   │   ├── test_source_credibility.py    ✅ 45 tests
│   │   ├── test_source_independence.py   ✅ 11 tests
│   │   ├── test_source_validator.py      ✅ 9 tests
│   │   ├── test_temporal.py              ✅ 17 tests
│   │   └── test_abstention_logic.py      ✅ 19 tests
│   │
│   ├── 📁 models/                   # Database model tests (Phase 6)
│   │   ├── test_check_model.py
│   │   ├── test_claim_model.py
│   │   ├── test_evidence_model.py
│   │   └── test_user_model.py
│   │
│   ├── 📁 api/                      # API endpoint tests (Phase 6)
│   │   ├── test_checks_endpoint.py
│   │   ├── test_users_endpoint.py
│   │   ├── test_auth_middleware.py
│   │   └── test_rate_limiting.py
│   │
│   └── 📁 workers/                  # Worker tests (Phase 2)
│       └── test_pipeline_orchestration.py
│
├── 📁 integration/                   # Multi-component tests
│   ├── 📁 pipeline/                 # Stage-to-stage (Phase 3)
│   │   ├── test_ingest_to_extract.py
│   │   ├── test_extract_to_retrieve.py
│   │   ├── test_retrieve_to_verify.py
│   │   ├── test_verify_to_judge.py
│   │   └── test_full_pipeline.py
│   │
│   ├── 📁 features/                 # Feature combinations (Phase 3)
│   │   ├── test_feature_combinations.py
│   │   ├── test_search_clarity_flow.py
│   │   └── test_abstention_scenarios.py
│   │
│   ├── 📁 api_workflows/            # API E2E tests (Phase 3)
│   │   ├── test_check_creation.py
│   │   ├── test_check_polling.py
│   │   ├── test_sse_streaming.py
│   │   └── test_error_handling.py
│   │
│   └── test_pipeline_improvements.py  ✅ EXISTING (9 tests)
│
├── 📁 performance/                   # Load and stress tests
│   ├── 📁 load/                     # High volume (Phase 4)
│   │   ├── test_concurrent_checks.py
│   │   ├── test_high_volume_claims.py
│   │   ├── test_large_evidence_sets.py
│   │   └── test_sustained_load.py
│   │
│   ├── 📁 stress/                   # Breaking points (Phase 4)
│   │   ├── test_memory_limits.py
│   │   ├── test_api_rate_limits.py
│   │   ├── test_database_connections.py
│   │   └── test_breaking_points.py
│   │
│   ├── 📁 concurrency/              # Parallel execution (Phase 4)
│   │   ├── test_celery_workers.py
│   │   ├── test_redis_contention.py
│   │   └── test_postgres_locking.py
│   │
│   └── 📁 benchmarks/               # Existing benchmarks
│       └── test_feature_overhead.py   ✅ EXISTING (8 tests)
│
├── 📁 regression/                    # Prevent known bugs
│   ├── 📁 known_issues/             # Historical bugs (Phase 5)
│   │   ├── test_httpx_import_bug.py
│   │   ├── test_robots_txt_blocking.py
│   │   ├── test_zero_sources_bug.py
│   │   └── test_neutral_evidence_bug.py
│   │
│   └── 📁 edge_cases/               # Boundary conditions (Phase 5)
│       ├── test_empty_inputs.py
│       ├── test_extreme_sizes.py
│       ├── test_unicode_handling.py
│       ├── test_malformed_data.py
│       └── test_boundary_values.py
│
├── 📁 mocks/                         # Shared mock objects
│   ├── llm_responses.py             # OpenAI response fixtures
│   ├── search_results.py            # Brave/SERP mock data
│   ├── factcheck_data.py            # Google Fact Check mocks
│   ├── sample_content.py            # Test content library
│   └── database.py                  # DB fixtures and factories
│
├── 📁 fixtures/                      # Shared test data
│   ├── conftest.py                  # Pytest configuration & fixtures
│   ├── database.py                  # DB fixtures
│   └── clients.py                   # API client fixtures
│
├── 📁 docs/                          # Testing documentation
│   ├── TESTING_MASTER_TRACKER.md    # ⭐ MAIN TRACKING DOCUMENT
│   ├── PHASE_COMPLETION_TEMPLATE.md # Template for phase reports
│   ├── PHASE_1_COMPLETION.md        # Pipeline coverage report
│   ├── PHASE_2_COMPLETION.md        # Services report
│   ├── PHASE_3_COMPLETION.md        # Integration report
│   ├── PHASE_4_COMPLETION.md        # Performance report
│   ├── PHASE_5_COMPLETION.md        # Regression report
│   ├── PHASE_6_COMPLETION.md        # Models & API report
│   ├── LIMITS_AND_BOUNDARIES.md     # System limits (Phase 4)
│   └── KNOWN_ISSUES.md              # Issue tracking
│
├── pytest.ini                        # Pytest configuration
└── README.md                         # This file
```

---

## 🎯 Testing Phases

### **Phase 0: Infrastructure Setup** ✅ COMPLETE
**Duration**: 1 day
**Status**: ✅ Complete (2025-11-03)

Created test infrastructure:
- ✅ Folder structure
- ✅ Master tracking document
- ✅ Documentation templates
- ⏳ Pytest configuration (pending)
- ⏳ Mock libraries (pending)

### **Phase 1: Critical Pipeline Coverage** ⏳ NEXT
**Duration**: 3 days
**Target**: 150 tests, 80%+ coverage
**Priority**: 🔴 CRITICAL

Test all 6 pipeline stages:
- `test_ingest.py` - 30 tests
- `test_extract.py` - 25 tests
- `test_retrieve.py` - 30 tests
- `test_verify.py` - 25 tests
- `test_judge.py` - 25 tests
- `test_query_answer.py` - 15 tests (NEW Search Clarity)

### **Phase 2: Services & Orchestration** ⏳ PENDING
**Duration**: 4 days
**Target**: 100 tests, 80%+ coverage
**Priority**: 🔴 CRITICAL

Test service layer and Celery workers:
- 8 service modules
- Pipeline orchestration
- External API integration

### **Phase 3: Integration Flows** ⏳ PENDING
**Duration**: 3 days
**Target**: 80 tests
**Priority**: 🟡 HIGH

Test component interactions:
- Stage-to-stage integration (5 files)
- Feature combinations (3 files)
- API workflows (4 files)

### **Phase 4: Performance Testing** ⏳ PENDING
**Duration**: 3 days
**Target**: 50 tests + metrics documentation
**Priority**: 🟡 HIGH

Measure limits and breaking points:
- Load testing (concurrent checks, sustained load)
- Stress testing (memory, API limits, breaking points)
- Concurrency testing (workers, cache, DB)

**Deliverable**: `LIMITS_AND_BOUNDARIES.md`

### **Phase 5: Regression & Edge Cases** ⏳ PENDING
**Duration**: 3 days
**Target**: 70 tests
**Priority**: 🟢 MEDIUM

Prevent known bugs:
- 4 known issue regression tests
- 5 edge case test suites

**Deliverable**: `KNOWN_ISSUES.md` updates

### **Phase 6: Models & API Layer** ⏳ PENDING
**Duration**: 3 days
**Target**: 60 tests
**Priority**: 🟢 MEDIUM

Complete coverage:
- 4 model validation suites
- 4 API endpoint test suites

---

## 🏃 Quick Start

### Running All Tests

```bash
# Navigate to backend directory
cd backend

# Run all tests
pytest tests/

# Run with coverage
pytest tests/ --cov=app --cov-report=html

# Run specific phase
pytest tests/ -m phase1

# Run specific category
pytest tests/unit/
pytest tests/integration/
pytest tests/performance/
```

### Running Tests by Marker

```bash
# Critical tests only
pytest tests/ -m critical

# Unit tests only
pytest tests/ -m unit

# Performance tests (slow)
pytest tests/ -m performance

# Integration tests
pytest tests/ -m integration

# Regression tests
pytest tests/ -m regression
```

### Running Specific Test Files

```bash
# Single file
pytest tests/unit/pipeline/test_ingest.py

# Single test
pytest tests/unit/pipeline/test_ingest.py::TestUrlIngester::test_successful_extraction

# Multiple files
pytest tests/unit/pipeline/test_ingest.py tests/unit/pipeline/test_extract.py
```

---

## 📊 Current Test Status

### Coverage Summary (as of 2025-11-03)

```
Module Category          Tests    Coverage
────────────────────────────────────────────
Pipeline Stages (6)        0         0%    ⏳ Phase 1
Services (10)              0        20%    ⏳ Phase 2
Utilities (9)            169        78%    ✅ Complete
Models (4)                 0         0%    ⏳ Phase 6
API Endpoints (5)          0         0%    ⏳ Phase 6
Workers (1)                0         0%    ⏳ Phase 2
────────────────────────────────────────────
TOTAL (34 modules)       169        26%    🟡 In Progress
```

### Test Distribution

- **Unit Tests**: 169 (existing) + 310 (planned) = **479 total**
- **Integration Tests**: 9 (existing) + 71 (planned) = **80 total**
- **Performance Tests**: 8 (existing) + 42 (planned) = **50 total**
- **Regression Tests**: 0 (existing) + 70 (planned) = **70 total**

**TOTAL**: **~679 tests** (169 existing + 510 new)

---

## 🧪 Test File Template

Every test file should follow this structure:

```python
"""
Tests for [Module Name]
Created: YYYY-MM-DD HH:MM:SS UTC
Last Updated: YYYY-MM-DD HH:MM:SS UTC
Tested Code Version: commit [hash]
Last Successful Run: YYYY-MM-DD HH:MM:SS UTC
Test Framework: pytest 8.x
Python Version: 3.12

Coverage: X% (target: 80%+)
Test Count: X
Performance: All tests < 5s

Purpose:
    Test [component] functionality including:
    - Feature 1
    - Feature 2
    - Edge cases and error handling

Phase: Phase N
Priority: Critical/High/Medium/Low
"""

import pytest
from datetime import datetime

# Test metadata
TEST_VERSION = "commit_hash"
LAST_RUN = "YYYY-MM-DD HH:MM:SS UTC"

class TestComponentName:
    """
    Test suite for [Component]
    Created: YYYY-MM-DD
    """

    @pytest.mark.unit
    @pytest.mark.phase1
    @pytest.mark.critical
    def test_happy_path(self):
        """
        Test: [Description]
        Created: YYYY-MM-DD
        Last Passed: YYYY-MM-DD HH:MM:SS UTC
        """
        # Arrange
        # Act
        # Assert
        pass
```

---

## 📝 Documentation

### Key Documents

1. **[TESTING_MASTER_TRACKER.md](docs/TESTING_MASTER_TRACKER.md)** ⭐
   - Main oversight document
   - Phase-by-phase checklist
   - Progress logging
   - Blocker tracking

2. **[KNOWN_ISSUES.md](docs/KNOWN_ISSUES.md)**
   - Active issue tracking
   - Historical bug reference
   - Regression test mapping

3. **[LIMITS_AND_BOUNDARIES.md](docs/LIMITS_AND_BOUNDARIES.md)**
   - Performance limits
   - Capacity planning
   - Breaking points
   - *(To be completed in Phase 4)*

4. **Phase Completion Reports**
   - Detailed phase summaries
   - Test results
   - Coverage reports
   - Issues discovered

---

## 🛠️ Development Workflow

### Adding New Tests

1. **Check Phase**: Determine which phase the test belongs to
2. **Update Tracker**: Mark test as "In Progress" in `TESTING_MASTER_TRACKER.md`
3. **Create Test File**: Use template above with timestamps
4. **Write Tests**: Follow AAA pattern (Arrange, Act, Assert)
5. **Mock External APIs**: Never hit real APIs in tests
6. **Add Markers**: Use appropriate pytest markers
7. **Run Tests**: Verify all pass
8. **Update Tracker**: Mark test as "Complete" with metrics
9. **Update Coverage**: Document coverage achieved

### Reporting Issues

1. **Identify Issue**: During testing, note unexpected behavior
2. **Add to KNOWN_ISSUES.md**: Use template provided
3. **Link to Tracker**: Reference issue in phase progress log
4. **Create Regression Test**: Once resolved, add test to `regression/known_issues/`

### Phase Completion

1. **Run All Phase Tests**: Verify 100% pass rate
2. **Generate Coverage Report**: Ensure target met
3. **Complete Phase Report**: Use `PHASE_COMPLETION_TEMPLATE.md`
4. **Update Master Tracker**: Mark phase complete
5. **Team Review**: Get sign-off
6. **Proceed to Next Phase**

---

## 🔧 Configuration

### pytest.ini

Pytest configuration includes:
- Test discovery patterns
- Async test mode
- Markers for all phases
- Coverage reporting
- Output formatting

### conftest.py

Shared fixtures:
- Database fixtures (test DB)
- API client fixtures
- Mock fixtures (OpenAI, Search APIs)
- Sample data fixtures

---

## 📈 Success Criteria

### Per-Phase Criteria

- [ ] All planned tests created
- [ ] All tests passing (100%)
- [ ] Coverage target met (80%+)
- [ ] All external APIs mocked
- [ ] Documentation complete
- [ ] Phase completion report signed off

### Overall Success

- [ ] 510+ new tests created
- [ ] 90%+ overall coverage
- [ ] All 6 phases complete
- [ ] Performance limits documented
- [ ] Known issues tracked
- [ ] Regression tests for all bugs
- [ ] CI/CD integration ready

---

## 🔗 Related Documentation

- [Backend README](../README.md) - Backend setup
- [API Documentation](../app/api/) - API endpoints
- [Pipeline Documentation](../app/pipeline/) - Pipeline stages
- [MVP Master Plan](../../docs/MVP_MASTER_PLAN.md) - Project roadmap

---

## 👥 Contribution Guidelines

When contributing tests:

1. **Follow the template** - Use provided test file template
2. **Add timestamps** - Created, updated, last passed dates
3. **Use markers** - Apply appropriate pytest markers
4. **Update tracker** - Log progress in TESTING_MASTER_TRACKER.md
5. **Document issues** - Add to KNOWN_ISSUES.md if found
6. **Mock APIs** - Never hit external APIs
7. **Keep tests fast** - Unit tests <1s, integration <5s

---

## 📞 Support

For questions about the testing strategy:
- Review [TESTING_MASTER_TRACKER.md](docs/TESTING_MASTER_TRACKER.md)
- Check [KNOWN_ISSUES.md](docs/KNOWN_ISSUES.md)
- Consult phase completion reports

---

**Testing Suite Status**: Phase 0 Complete ✅
**Next Phase**: Phase 1 (Pipeline Coverage)
**Overall Progress**: 0/510 new tests (26% existing coverage)
**Target Completion**: 2025-12-01

**Last Updated**: 2025-11-03 14:50:00 UTC
**Maintained By**: Testing Team
**Version**: 1.0.0
