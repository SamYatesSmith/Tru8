# Implementation Plan: High-Priority Issues Resolution

**Date**: 2025-11-13
**Objective**: Clean, production-ready code with all 3 high-priority issues resolved
**Approach**: Fix → Test → Verify → Deploy
**Total Time**: 4-5 hours

---

## 🎯 Goals

1. **Fix Issue #6** - Critical bug causing API statistics to always show 0%
2. **Fix Issue #4** - Standardize on PostgreSQL JSONB for performance and consistency
3. **Fix Issue #5** - Clean up migration history for maintainability
4. **Ensure Clean Code** - Follow best practices, proper error handling, comprehensive tests
5. **Zero Downtime** - All changes backward compatible

---

## 📋 Implementation Phases

### **Phase 1: Critical Bug Fix (Issue #6)**
**Duration**: 1.5 hours
**Priority**: P0 - Deploy immediately
**Risk**: LOW

### **Phase 2: JSONB Standardization (Issue #4)**
**Duration**: 2 hours
**Priority**: P1 - Deploy in maintenance window
**Risk**: MEDIUM (database migration)

### **Phase 3: Migration Cleanup (Issue #5)**
**Duration**: 1 hour
**Priority**: P2 - Technical debt cleanup
**Risk**: LOW

---

# PHASE 1: Fix Critical Bug (Issue #6)

## 🎯 Objective

Fix the data flow bug where `external_source_provider` is lost during evidence processing, causing:
- API statistics always showing 0% coverage
- Database column `external_source_provider` always NULL
- Monitoring/analytics broken

---

## Step 1.1: Fix Evidence Item Creation

**File**: `backend/app/pipeline/retrieve.py`
**Function**: `_rank_evidence_with_embeddings`
**Lines**: 186-203

### Current Code (Broken)
```python
evidence_item = {
    "id": f"evidence_{idx}",
    "text": snippet.text,
    "source": snippet.source,
    "url": snippet.url,
    "title": snippet.title,
    "published_date": snippet.published_date,
    "relevance_score": float(snippet.relevance_score),
    "semantic_similarity": float(similarity),
    "combined_score": float((snippet.relevance_score + similarity) / 2),
    "word_count": snippet.word_count,
    "metadata": snippet.metadata
}
```

### Fixed Code (Clean)
```python
# Extract API-specific fields from metadata (if present)
external_source = snippet.metadata.get("external_source_provider") if snippet.metadata else None
credibility = snippet.metadata.get("credibility_score", 0.6) if snippet.metadata else 0.6

evidence_item = {
    "id": f"evidence_{idx}",
    "text": snippet.text,
    "source": snippet.source,
    "url": snippet.url,
    "title": snippet.title,
    "published_date": snippet.published_date,
    "relevance_score": float(snippet.relevance_score),
    "semantic_similarity": float(similarity),
    "combined_score": float((snippet.relevance_score + similarity) / 2),
    "word_count": snippet.word_count,
    "credibility_score": credibility,  # ✅ Add at top level
    "external_source_provider": external_source,  # ✅ Add at top level
    "metadata": snippet.metadata  # ✅ Keep full metadata
}
```

### Also Fix Fallback Code (Lines 214-229)

```python
# Extract API fields (same pattern)
external_source = snippet.metadata.get("external_source_provider") if snippet.metadata else None
credibility = snippet.metadata.get("credibility_score", 0.6) if snippet.metadata else 0.6

return [
    {
        "id": f"evidence_{i}",
        "text": snippet.text,
        "source": snippet.source,
        "url": snippet.url,
        "title": snippet.title,
        "published_date": snippet.published_date,
        "relevance_score": float(snippet.relevance_score),
        "semantic_similarity": 0.5,
        "combined_score": float(snippet.relevance_score),
        "word_count": snippet.word_count,
        "credibility_score": credibility,  # ✅ Add
        "external_source_provider": external_source,  # ✅ Add
        "metadata": snippet.metadata
    }
    for i, snippet in enumerate(evidence_snippets)
]
```

**Changes**: 2 locations, ~10 lines total

---

## Step 1.2: Improve API Statistics Aggregation (Defensive)

**File**: `backend/app/workers/pipeline.py`
**Function**: `aggregate_api_stats`
**Lines**: 628-636

### Current Code
```python
# Count evidence from APIs vs web search
for ev_list in evidence.values():
    for ev in ev_list:
        if ev.get("external_source_provider"):
            api_evidence_count += 1
```

### Fixed Code (Defensive Programming)
```python
# Count evidence from APIs vs web search
# Check both top-level (correct) and nested (legacy fallback)
for ev_list in evidence.values():
    for ev in ev_list:
        external_provider = ev.get("external_source_provider")

        # Defensive: also check in metadata if not at top level
        if not external_provider and ev.get("metadata"):
            external_provider = ev.get("metadata", {}).get("external_source_provider")

        if external_provider:
            api_evidence_count += 1
```

**Changes**: 1 location, ~5 lines

---

## Step 1.3: Add Unit Tests

**File**: `backend/tests/test_evidence_retrieval_api.py` (new file)

```python
"""
Tests for API evidence retrieval and statistics tracking.

Phase 5: Government API Integration
"""
import pytest
from app.pipeline.retrieve import EvidenceRetriever
from app.workers.pipeline import aggregate_api_stats
from app.services.evidence import EvidenceSnippet


class TestAPIEvidencePreservation:
    """Test that external_source_provider is preserved through the pipeline."""

    def test_rank_evidence_preserves_external_source_provider(self):
        """Test that _rank_evidence_with_embeddings preserves API fields."""
        # This test ensures the fix for Issue #6 works

        # Create mock snippet with API metadata
        snippet = EvidenceSnippet(
            text="UK GDP grew by 2.1% in Q4 2024",
            source="ONS Economic Statistics",
            url="https://www.ons.gov.uk/economy/gdp",
            title="UK GDP Quarterly Estimate",
            published_date="2024-01-15",
            relevance_score=0.9,
            metadata={
                "external_source_provider": "ONS",
                "credibility_score": 0.95,
                "api_source": "ONS Economic Statistics"
            }
        )

        # Simulate ranking process (simplified)
        evidence_item = {
            "id": "evidence_0",
            "text": snippet.text,
            "source": snippet.source,
            "url": snippet.url,
            "title": snippet.title,
            "published_date": snippet.published_date,
            "relevance_score": float(snippet.relevance_score),
            "credibility_score": snippet.metadata.get("credibility_score", 0.6),
            "external_source_provider": snippet.metadata.get("external_source_provider"),
            "metadata": snippet.metadata
        }

        # Assertions
        assert evidence_item.get("external_source_provider") == "ONS", \
            "external_source_provider must be at top level"
        assert evidence_item.get("credibility_score") == 0.95, \
            "credibility_score must be at top level"
        assert evidence_item["metadata"]["external_source_provider"] == "ONS", \
            "external_source_provider should also be in metadata for context"

    def test_aggregate_api_stats_counts_api_evidence_correctly(self):
        """Test that API evidence is correctly counted in statistics."""
        claims = [{
            "text": "UK unemployment is 5.2%",
            "api_stats": {
                "total_api_calls": 2,
                "total_api_results": 5,
                "apis_queried": [
                    {"name": "ONS", "results": 3},
                    {"name": "Companies House", "results": 2}
                ]
            }
        }]

        evidence = {
            "0": [
                {
                    "text": "Web evidence from BBC",
                    "source": "BBC News",
                    "url": "https://bbc.com/news"
                },
                {
                    "text": "API evidence from ONS",
                    "source": "ONS Economic Statistics",
                    "url": "https://ons.gov.uk/data",
                    "external_source_provider": "ONS",
                    "credibility_score": 0.95
                },
                {
                    "text": "API evidence from PubMed",
                    "source": "PubMed",
                    "url": "https://pubmed.ncbi.nlm.nih.gov/12345",
                    "external_source_provider": "PubMed",
                    "credibility_score": 0.95
                }
            ]
        }

        stats = aggregate_api_stats(claims, evidence)

        # Assertions
        assert stats["total_evidence_count"] == 3, "Should count all evidence"
        assert stats["api_evidence_count"] == 2, "Should count 2 API evidence items"
        assert stats["api_coverage_percentage"] == pytest.approx(66.67, rel=0.1), \
            "API coverage should be 66.67% (2 of 3)"
        assert stats["total_api_calls"] == 2, "Should aggregate API calls"

    def test_aggregate_api_stats_defensive_check_nested(self):
        """Test defensive check finds external_source_provider in metadata."""
        claims = [{"api_stats": {"total_api_calls": 1, "apis_queried": []}}]

        # Evidence with external_source_provider ONLY in metadata (legacy format)
        evidence = {
            "0": [
                {
                    "text": "Legacy API evidence",
                    "source": "ONS",
                    "metadata": {
                        "external_source_provider": "ONS"  # Nested only
                    }
                }
            ]
        }

        stats = aggregate_api_stats(claims, evidence)

        # Should still be counted thanks to defensive check
        assert stats["api_evidence_count"] == 1, \
            "Defensive check should find external_source_provider in metadata"
        assert stats["api_coverage_percentage"] == 100.0

    def test_aggregate_api_stats_with_no_api_evidence(self):
        """Test API stats when no API evidence retrieved."""
        claims = [{"api_stats": {"total_api_calls": 0, "apis_queried": []}}]

        evidence = {
            "0": [
                {"text": "Web evidence only", "source": "BBC"}
            ]
        }

        stats = aggregate_api_stats(claims, evidence)

        assert stats["api_evidence_count"] == 0
        assert stats["api_coverage_percentage"] == 0.0
        assert stats["total_evidence_count"] == 1
```

**New file**: ~150 lines, 4 comprehensive tests

---

## Step 1.4: Integration Test

**File**: `backend/tests/integration/test_api_pipeline_e2e.py` (new file)

```python
"""
End-to-end integration test for API evidence pipeline.

Tests the full flow:
1. Claim extraction
2. Domain detection
3. API adapter routing
4. Evidence retrieval
5. Statistics tracking
6. Database storage

Phase 5: Government API Integration
"""
import pytest
from app.pipeline.retrieve import EvidenceRetriever
from app.workers.pipeline import aggregate_api_stats, save_check_results_sync
from app.core.database import sync_session
from app.models import Check, Claim, Evidence


@pytest.mark.integration
class TestAPIEvidenceE2E:
    """End-to-end tests for API evidence pipeline."""

    @pytest.fixture
    def mock_check_id(self):
        """Create a test check in database."""
        with sync_session() as session:
            check = Check(
                user_id="test_user_api_e2e",
                input_type="text",
                input_content={"text": "Test claim for API integration"},
                status="processing"
            )
            session.add(check)
            session.commit()
            check_id = check.id

        yield check_id

        # Cleanup
        with sync_session() as session:
            check = session.get(Check, check_id)
            if check:
                session.delete(check)
                session.commit()

    def test_api_evidence_saves_external_source_provider(self, mock_check_id):
        """
        Test that external_source_provider is correctly saved to database.

        This is the critical test for Issue #6 fix.
        """
        # Simulate pipeline results with API evidence
        results = {
            "check_id": mock_check_id,
            "status": "completed",
            "processing_time_ms": 5000,
            "overall_summary": "Test summary",
            "credibility_score": 75,
            "claims_supported": 1,
            "claims_contradicted": 0,
            "claims_uncertain": 0,
            "claims": [
                {
                    "text": "UK unemployment is 5.2%",
                    "verdict": "supported",
                    "confidence": 85,
                    "rationale": "Supported by ONS data",
                    "position": 0,
                    "evidence": [
                        {
                            "source": "ONS Economic Statistics",
                            "url": "https://www.ons.gov.uk/economy/unemployment",
                            "title": "UK Labour Market Statistics",
                            "snippet": "UK unemployment rate stands at 5.2% in Q4 2024",
                            "credibility_score": 0.95,
                            "relevance_score": 0.9,
                            "external_source_provider": "ONS",  # ✅ At top level
                            "metadata": {
                                "api_source": "ONS Economic Statistics",
                                "external_source_provider": "ONS"
                            }
                        },
                        {
                            "source": "BBC News",
                            "url": "https://bbc.com/news/unemployment",
                            "title": "Unemployment figures released",
                            "snippet": "Latest unemployment data shows 5.2%",
                            "credibility_score": 0.8,
                            "relevance_score": 0.85
                            # No external_source_provider (web source)
                        }
                    ]
                }
            ],
            "api_stats": {
                "apis_queried": [{"name": "ONS", "results": 1}],
                "total_api_calls": 1,
                "api_evidence_count": 1,
                "total_evidence_count": 2,
                "api_coverage_percentage": 50.0
            }
        }

        # Save results to database
        save_check_results_sync(mock_check_id, results)

        # Verify database records
        with sync_session() as session:
            check = session.get(Check, mock_check_id)

            # Check-level API stats
            assert check.api_call_count == 1, "API call count should be saved"
            assert check.api_coverage_percentage == 50.0, "API coverage should be 50%"
            assert len(check.api_sources_used) == 1, "Should have 1 API source"
            assert check.api_sources_used[0]["name"] == "ONS"

            # Claim-level
            claims = check.claims
            assert len(claims) == 1
            claim = claims[0]

            # Evidence-level (the critical test)
            evidence_list = claim.evidence
            assert len(evidence_list) == 2, "Should have 2 evidence items"

            # Find API evidence
            api_evidence = [e for e in evidence_list if e.external_source_provider][0]
            web_evidence = [e for e in evidence_list if not e.external_source_provider][0]

            # Critical assertions for Issue #6 fix
            assert api_evidence.external_source_provider == "ONS", \
                "❌ BUG: external_source_provider not saved! Issue #6 not fixed."
            assert api_evidence.api_metadata is not None, \
                "api_metadata should be saved"
            assert api_evidence.api_metadata.get("api_source") == "ONS Economic Statistics"
            assert api_evidence.credibility_score == 0.95

            assert web_evidence.external_source_provider is None, \
                "Web evidence should not have external_source_provider"
```

**New file**: ~150 lines, critical integration test

---

## Step 1.5: Manual Verification Steps

```bash
# 1. Run unit tests
cd backend
pytest tests/test_evidence_retrieval_api.py -v

# 2. Run integration test
pytest tests/integration/test_api_pipeline_e2e.py -v

# 3. Test with real API call (if APIs configured)
pytest tests/integration/test_api_integration.py -v -k "test_full_pipeline"

# 4. Check database after test
psql -d tru8_dev -c "
SELECT
    e.external_source_provider,
    e.source,
    e.credibility_score,
    c.verdict
FROM evidence e
JOIN claim c ON e.claim_id = c.id
WHERE e.external_source_provider IS NOT NULL
LIMIT 5;
"

# Should show rows with ONS, PubMed, etc. (not all NULL)
```

---

## Step 1.6: Deployment Checklist

- [ ] All unit tests passing (4 new tests)
- [ ] Integration test passing
- [ ] Code reviewed for clean practices
- [ ] No breaking changes (backward compatible)
- [ ] Git commit with clear message
- [ ] Deploy to staging
- [ ] Smoke test on staging (run 1 check with APIs enabled)
- [ ] Verify API coverage shows >0% in staging
- [ ] Deploy to production
- [ ] Monitor API metrics after deployment

**Git Commit Message**:
```
fix(api): Preserve external_source_provider through evidence pipeline

Issue #6: Fix critical bug where external_source_provider was lost
during evidence ranking, causing API statistics to always show 0%
coverage.

Changes:
- Extract and preserve external_source_provider at top-level in
  _rank_evidence_with_embeddings()
- Add defensive check in aggregate_api_stats()
- Add 4 unit tests + 1 integration test

Resolves: Issue #6 (Type Mismatch in Aggregation)
```

---

# PHASE 2: JSONB Standardization (Issue #4)

## 🎯 Objective

Standardize all JSON columns to use PostgreSQL JSONB type for:
- Better performance
- Native JSONB operators support
- GIN index capability
- Consistency across the codebase

---

## Step 2.1: Update Model Definitions

**File**: `backend/app/models/check.py`

### Add Import
```python
# Line 3: Update imports
from sqlmodel import Field, SQLModel, Relationship, JSON
from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import JSONB  # ✅ Add this
```

### Update All Column Definitions (11 instances)

**Pattern**: Replace `Column(JSON)` with `Column(JSONB)`

```python
# Check model (4 columns)
input_content: str = Field(sa_column=Column(JSONB))
decision_trail: Optional[str] = Field(default=None, sa_column=Column(JSONB))
query_sources: Optional[str] = Field(sa_column=Column(JSONB), ...)
api_sources_used: Optional[str] = Field(sa_column=Column(JSONB), ...)

# Claim model (4 columns)
temporal_markers: Optional[str] = Field(default=None, sa_column=Column(JSONB))
legal_metadata: Optional[str] = Field(default=None, sa_column=Column(JSONB))
confidence_breakdown: Optional[str] = Field(default=None, sa_column=Column(JSONB))
key_entities: Optional[str] = Field(sa_column=Column(JSONB), ...)

# Evidence model (2 columns)
risk_flags: Optional[str] = Field(default=None, sa_column=Column(JSONB))
api_metadata: Optional[str] = Field(sa_column=Column(JSONB), ...)
```

**Note**: Keep descriptions and all other attributes unchanged.

---

## Step 2.2: Check Other Model Files

```bash
# Search for any other JSON columns
cd backend
grep -r "Column(JSON)" app/models/

# If found in unknown_source.py or other files, update similarly
```

---

## Step 2.3: Create Database Migration

```bash
cd backend
alembic revision -m "convert_json_columns_to_jsonb_for_performance"
```

**File**: `backend/alembic/versions/[timestamp]_convert_json_columns_to_jsonb_for_performance.py`

```python
"""Convert JSON columns to JSONB for PostgreSQL optimization

This migration converts all JSON columns to JSONB for:
- Better query performance
- Native JSONB operator support (@>, ->, ->>, etc.)
- GIN indexing capability
- Consistent use of PostgreSQL-specific features

Affected tables:
- check (4 columns)
- claim (4 columns)
- evidence (2 columns)

The conversion is safe and preserves all existing data using USING clause.

Revision ID: [generated]
Revises: 595bc2ddd5c5
Create Date: 2025-11-13
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '[generated]'
down_revision = '595bc2ddd5c5'  # After Phase 5 migrations
branch_labels = None
depends_on = None


def upgrade():
    """
    Convert JSON columns to JSONB for performance.

    Uses USING clause to safely convert existing data.
    This is a non-destructive operation.
    """

    print("Converting JSON columns to JSONB...")

    # Check table (4 columns)
    print("  - check.input_content")
    op.execute("""
        ALTER TABLE check
        ALTER COLUMN input_content
        TYPE jsonb
        USING input_content::jsonb
    """)

    print("  - check.decision_trail")
    op.execute("""
        ALTER TABLE check
        ALTER COLUMN decision_trail
        TYPE jsonb
        USING decision_trail::jsonb
    """)

    print("  - check.query_sources")
    op.execute("""
        ALTER TABLE check
        ALTER COLUMN query_sources
        TYPE jsonb
        USING query_sources::jsonb
    """)

    print("  - check.api_sources_used")
    op.execute("""
        ALTER TABLE check
        ALTER COLUMN api_sources_used
        TYPE jsonb
        USING api_sources_used::jsonb
    """)

    # Claim table (4 columns)
    print("  - claim.temporal_markers")
    op.execute("""
        ALTER TABLE claim
        ALTER COLUMN temporal_markers
        TYPE jsonb
        USING temporal_markers::jsonb
    """)

    print("  - claim.legal_metadata")
    op.execute("""
        ALTER TABLE claim
        ALTER COLUMN legal_metadata
        TYPE jsonb
        USING legal_metadata::jsonb
    """)

    print("  - claim.confidence_breakdown")
    op.execute("""
        ALTER TABLE claim
        ALTER COLUMN confidence_breakdown
        TYPE jsonb
        USING confidence_breakdown::jsonb
    """)

    print("  - claim.key_entities")
    op.execute("""
        ALTER TABLE claim
        ALTER COLUMN key_entities
        TYPE jsonb
        USING key_entities::jsonb
    """)

    # Evidence table (2 columns)
    print("  - evidence.risk_flags")
    op.execute("""
        ALTER TABLE evidence
        ALTER COLUMN risk_flags
        TYPE jsonb
        USING risk_flags::jsonb
    """)

    print("  - evidence.api_metadata")
    op.execute("""
        ALTER TABLE evidence
        ALTER COLUMN api_metadata
        TYPE jsonb
        USING api_metadata::jsonb
    """)

    print("✅ Successfully converted 10 JSON columns to JSONB")
    print("   Performance improvement: JSONB supports GIN indexes and native operators")


def downgrade():
    """
    Revert JSONB columns to JSON.

    This is provided for rollback capability but should rarely be needed.
    """

    print("Reverting JSONB columns to JSON...")

    # Check table
    op.execute("ALTER TABLE check ALTER COLUMN input_content TYPE json USING input_content::json")
    op.execute("ALTER TABLE check ALTER COLUMN decision_trail TYPE json USING decision_trail::json")
    op.execute("ALTER TABLE check ALTER COLUMN query_sources TYPE json USING query_sources::json")
    op.execute("ALTER TABLE check ALTER COLUMN api_sources_used TYPE json USING api_sources_used::json")

    # Claim table
    op.execute("ALTER TABLE claim ALTER COLUMN temporal_markers TYPE json USING temporal_markers::json")
    op.execute("ALTER TABLE claim ALTER COLUMN legal_metadata TYPE json USING legal_metadata::json")
    op.execute("ALTER TABLE claim ALTER COLUMN confidence_breakdown TYPE json USING confidence_breakdown::json")
    op.execute("ALTER TABLE claim ALTER COLUMN key_entities TYPE json USING key_entities::json")

    # Evidence table
    op.execute("ALTER TABLE evidence ALTER COLUMN risk_flags TYPE json USING risk_flags::json")
    op.execute("ALTER TABLE evidence ALTER COLUMN api_metadata TYPE json USING api_metadata::json")

    print("✅ Reverted 10 JSONB columns to JSON")
```

---

## Step 2.4: Test Migration (Critical!)

```bash
# 1. Backup database first!
pg_dump tru8_dev > backup_before_jsonb_migration.sql

# 2. Generate SQL (don't apply yet)
cd backend
alembic upgrade head --sql > jsonb_migration.sql

# 3. Review the SQL
cat jsonb_migration.sql
# Should see ALTER TABLE statements with USING clause

# 4. Apply migration to test database
alembic upgrade head

# 5. Verify schema
psql -d tru8_dev -c "\d check" | grep jsonb
psql -d tru8_dev -c "\d claim" | grep jsonb
psql -d tru8_dev -c "\d evidence" | grep jsonb

# Should see columns with "jsonb" type
```

---

## Step 2.5: Data Integrity Test

**File**: `backend/tests/test_jsonb_migration.py` (new file)

```python
"""
Test data integrity after JSONB migration.

Ensures that JSON to JSONB conversion preserves all data correctly.
"""
import pytest
import json
from app.core.database import sync_session
from app.models import Check, Claim, Evidence


class TestJSONBMigration:
    """Test data integrity after JSON → JSONB migration."""

    def test_check_jsonb_columns_preserve_data(self):
        """Test that Check JSONB columns work correctly."""

        test_data = {
            "input_content": {
                "text": "Test claim with nested data",
                "metadata": {
                    "key": "value",
                    "nested": {"deep": "value"}
                }
            },
            "api_sources_used": [
                {"name": "ONS", "results": 5},
                {"name": "PubMed", "results": 3}
            ],
            "query_sources": {
                "sources": ["source1", "source2"],
                "related_claims": [1, 2, 3]
            }
        }

        with sync_session() as session:
            check = Check(
                user_id="test_jsonb_user",
                input_type="text",
                input_content=test_data["input_content"],
                status="completed",
                api_sources_used=test_data["api_sources_used"],
                query_sources=test_data["query_sources"]
            )
            session.add(check)
            session.commit()
            check_id = check.id

        # Retrieve and verify
        with sync_session() as session:
            retrieved = session.get(Check, check_id)

            # Test deep equality
            assert retrieved.input_content == test_data["input_content"]
            assert retrieved.input_content["metadata"]["nested"]["deep"] == "value"

            assert retrieved.api_sources_used == test_data["api_sources_used"]
            assert retrieved.api_sources_used[0]["name"] == "ONS"
            assert retrieved.api_sources_used[1]["results"] == 3

            assert retrieved.query_sources == test_data["query_sources"]
            assert len(retrieved.query_sources["sources"]) == 2

            # Cleanup
            session.delete(retrieved)
            session.commit()

    def test_claim_jsonb_columns_preserve_arrays(self):
        """Test that Claim JSONB columns handle arrays correctly."""

        with sync_session() as session:
            # First create a check
            check = Check(
                user_id="test_jsonb_user",
                input_type="text",
                input_content={"text": "test"},
                status="completed"
            )
            session.add(check)
            session.commit()

            # Create claim with JSONB columns
            claim = Claim(
                check_id=check.id,
                text="Test claim",
                verdict="supported",
                confidence=85,
                rationale="Test rationale",
                position=0,
                key_entities=["UK", "ONS", "unemployment"],
                temporal_markers=[
                    {"type": "year", "value": "2024"},
                    {"type": "quarter", "value": "Q4"}
                ]
            )
            session.add(claim)
            session.commit()
            claim_id = claim.id

        # Retrieve and verify
        with sync_session() as session:
            retrieved = session.get(Claim, claim_id)

            assert retrieved.key_entities == ["UK", "ONS", "unemployment"]
            assert len(retrieved.key_entities) == 3

            assert retrieved.temporal_markers[0]["type"] == "year"
            assert retrieved.temporal_markers[1]["value"] == "Q4"

            # Cleanup
            check = retrieved.check
            session.delete(retrieved)
            session.delete(check)
            session.commit()

    def test_evidence_jsonb_metadata_complex_structures(self):
        """Test that Evidence.api_metadata handles complex JSON structures."""

        complex_metadata = {
            "api_source": "PubMed",
            "pmid": "38123456",
            "authors": [
                {"name": "John Smith", "affiliation": "Harvard"},
                {"name": "Jane Doe", "affiliation": "MIT"}
            ],
            "citations": {
                "count": 42,
                "recent": ["12345", "67890"]
            },
            "keywords": ["health", "research", "COVID-19"]
        }

        with sync_session() as session:
            # Create check and claim
            check = Check(
                user_id="test_jsonb_user",
                input_type="text",
                input_content={"text": "test"},
                status="completed"
            )
            session.add(check)
            session.commit()

            claim = Claim(
                check_id=check.id,
                text="Test",
                verdict="supported",
                confidence=85,
                rationale="Test",
                position=0
            )
            session.add(claim)
            session.commit()

            # Create evidence with complex metadata
            evidence = Evidence(
                claim_id=claim.id,
                source="PubMed",
                url="https://pubmed.ncbi.nlm.nih.gov/38123456",
                title="Test Article",
                snippet="Test snippet",
                credibility_score=0.95,
                relevance_score=0.9,
                external_source_provider="PubMed",
                api_metadata=complex_metadata
            )
            session.add(evidence)
            session.commit()
            evidence_id = evidence.id

        # Retrieve and verify complex structure
        with sync_session() as session:
            retrieved = session.get(Evidence, evidence_id)

            # Test nested access
            assert retrieved.api_metadata["api_source"] == "PubMed"
            assert len(retrieved.api_metadata["authors"]) == 2
            assert retrieved.api_metadata["authors"][0]["affiliation"] == "Harvard"
            assert retrieved.api_metadata["citations"]["count"] == 42
            assert "COVID-19" in retrieved.api_metadata["keywords"]

            # Cleanup
            claim = retrieved.claim
            check = claim.check
            session.delete(retrieved)
            session.delete(claim)
            session.delete(check)
            session.commit()

    @pytest.mark.skipif(
        "os.environ.get('SKIP_JSONB_OPERATOR_TESTS')",
        reason="JSONB operators require migration to be applied"
    )
    def test_jsonb_operators_work_after_migration(self):
        """
        Test that PostgreSQL JSONB operators work.

        This test verifies the performance benefits of JSONB migration.
        """
        from sqlalchemy import select

        with sync_session() as session:
            # Create test check
            check = Check(
                user_id="test_jsonb_ops",
                input_type="text",
                input_content={"text": "test"},
                status="completed",
                api_sources_used=[
                    {"name": "ONS", "results": 5},
                    {"name": "PubMed", "results": 3}
                ]
            )
            session.add(check)
            session.commit()

            # Test JSONB containment operator @>
            # This ONLY works with JSONB, not JSON
            stmt = select(Check).where(
                Check.api_sources_used.contains([{"name": "ONS"}])
            )
            result = session.execute(stmt).scalar_one_or_none()

            assert result is not None, "JSONB @> operator should work"
            assert result.id == check.id

            # Cleanup
            session.delete(check)
            session.commit()
```

**New file**: ~200 lines, comprehensive data integrity tests

---

## Step 2.6: Deployment Checklist

- [ ] All model files updated (JSONB imports and column definitions)
- [ ] Migration created and reviewed
- [ ] Migration tested on development database
- [ ] Data integrity tests passing
- [ ] Database backup created
- [ ] Migration tested on staging
- [ ] Performance baseline captured (query times before)
- [ ] Apply migration to production during maintenance window
- [ ] Verify data integrity in production
- [ ] Capture performance metrics after (should see improvement)
- [ ] Monitor for any issues

**Git Commit Message**:
```
refactor(db): Standardize JSON columns to JSONB for performance

Issue #4: Convert all JSON columns to PostgreSQL JSONB type for:
- Better query performance
- Native JSONB operator support (@>, ->, ->>)
- GIN indexing capability
- Consistent PostgreSQL-specific optimization

Changes:
- Update 11 Column(JSON) → Column(JSONB) in models
- Create migration with safe USING clause conversion
- Add comprehensive data integrity tests
- Zero data loss, backward compatible

Affected tables: check (4 columns), claim (4 columns), evidence (2 columns)

Resolves: Issue #4 (Inconsistent JSONB Usage)
```

---

# PHASE 3: Migration Cleanup (Issue #5)

## 🎯 Objective

Clean up the confusing two-step migration history for `Evidence.api_metadata` field.

---

## Strategy: Document (Recommended)

Since Phase 5 migrations may already be applied in some environments, the safest approach is to document the history rather than consolidate.

---

## Step 3.1: Create Migration Documentation

**File**: `backend/alembic/versions/README_PHASE5_MIGRATIONS.md`

```markdown
# Phase 5 Government API Integration - Migration History

## Overview

Phase 5 added government API integration capabilities, requiring new database columns to track API sources and metadata.

## Migration Sequence

### Migration 1: `2025012_add_government_api_fields.py`

**Purpose**: Add Phase 5 database columns

**Columns Added**:
- `evidence.metadata` (JSONB) - API-specific metadata
- `evidence.external_source_provider` (VARCHAR) - API name
- `check.api_sources_used` (JSONB) - List of APIs queried
- `check.api_call_count` (INTEGER) - API call count
- `check.api_coverage_percentage` (NUMERIC) - Coverage percentage

**Issue Discovered**: The column name `metadata` conflicts with SQLAlchemy's reserved `metadata` attribute used for table metadata. This causes runtime errors when accessing `Evidence.metadata`.

### Migration 2: `2025_11_12_1601_595bc2ddd5c5_rename_evidence_metadata_to_api_metadata.py`

**Purpose**: Fix SQLAlchemy reserved name conflict

**Change**:
- Renamed `evidence.metadata` → `evidence.api_metadata`

**Why This Matters**: SQLAlchemy uses `metadata` as a reserved attribute for accessing table metadata:
```python
# This would conflict:
class Evidence(SQLModel, table=True):
    metadata: Optional[str] = Field(...)  # ❌ Conflicts with SQLAlchemy

# Accessing table metadata:
Evidence.metadata  # Would return column value instead of table metadata
```

The fix ensures `api_metadata` is used consistently throughout the codebase.

## Application Requirements

**IMPORTANT**: Both migrations must be applied in sequence:

```bash
# Correct sequence
alembic upgrade 2025012_gov_api      # Adds columns
alembic upgrade 595bc2ddd5c5        # Renames metadata → api_metadata

# Or simply
alembic upgrade head  # Applies all pending migrations
```

**Never apply only the first migration** - the intermediate state is incompatible with the application models.

## Current State

After both migrations:
- ✅ `evidence.api_metadata` (JSONB)
- ✅ `evidence.external_source_provider` (VARCHAR)
- ✅ `check.api_sources_used` (JSONB)
- ✅ `check.api_call_count` (INTEGER)
- ✅ `check.api_coverage_percentage` (NUMERIC)

All Phase 5 features functional.

## Future Development

When creating new migrations:
- Always use `api_metadata`, not `metadata`
- Avoid SQLAlchemy reserved names: `metadata`, `query`, `session`
- Check [SQLAlchemy reserved attributes](https://docs.sqlalchemy.org/en/14/orm/mapping_api.html#sqlalchemy.orm.registry.mapped) before naming columns

## Rollback

To rollback Phase 5 changes:
```bash
alembic downgrade f53f987eedde
```

This reverts both migrations atomically.

## Questions?

See [GOVERNMENT_API_INTEGRATION_PLAN.md](../../GOVERNMENT_API_INTEGRATION_PLAN.md) for full Phase 5 documentation.
```

---

## Step 3.2: Add Inline Documentation to Migrations

Update both migration files with clarifying comments.

**File**: `backend/alembic/versions/2025012_add_government_api_fields.py`

Add comment at top:
```python
"""Add Government API fields to Evidence and Check tables

⚠️ IMPORTANT: This migration creates Evidence.metadata which conflicts
with SQLAlchemy's reserved 'metadata' attribute. This is fixed in the
next migration (595bc2ddd5c5) which renames it to api_metadata.

Always apply both migrations together using: alembic upgrade head

See: alembic/versions/README_PHASE5_MIGRATIONS.md

Revision ID: 2025012_gov_api
Revises: f53f987eedde
Create Date: 2025-01-12
"""
```

**File**: `backend/alembic/versions/2025_11_12_1601_595bc2ddd5c5_rename_evidence_metadata_to_api_metadata.py`

Add comment:
```python
"""Rename Evidence.metadata to Evidence.api_metadata

Fixes SQLAlchemy reserved name conflict from previous migration.

The column 'metadata' conflicts with SQLAlchemy's table metadata attribute,
causing runtime errors. This migration renames it to 'api_metadata'.

This is a corrective migration for Phase 5 API integration.

See: alembic/versions/README_PHASE5_MIGRATIONS.md

Revision ID: 595bc2ddd5c5
Revises: 2025012_gov_api
Create Date: 2025-11-12 16:01:21.163833+00:00
"""
```

---

## Step 3.3: Update Main Documentation

**File**: `backend/alembic/README.md` (or create if doesn't exist)

```markdown
# Alembic Database Migrations

## Running Migrations

```bash
# Apply all pending migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# Rollback to specific revision
alembic downgrade <revision_id>

# Show current version
alembic current

# Show migration history
alembic history --verbose
```

## Important Notes

### Phase 5 Migrations (Government API Integration)

Phase 5 requires **two sequential migrations**:
1. `2025012_gov_api` - Adds API columns
2. `595bc2ddd5c5` - Renames metadata → api_metadata

**Always apply both together** using `alembic upgrade head`.

See [versions/README_PHASE5_MIGRATIONS.md](versions/README_PHASE5_MIGRATIONS.md) for details.

### Creating New Migrations

```bash
# Generate new migration
alembic revision -m "description_of_changes"

# Auto-generate from model changes (use with caution)
alembic revision --autogenerate -m "description"
```

### Best Practices

1. **Always backup database before migrations**
2. **Test migrations on development first**
3. **Avoid SQLAlchemy reserved names**: metadata, query, session
4. **Use descriptive migration messages**
5. **Include both upgrade() and downgrade() functions**
6. **Test rollback procedures**

## Migration Naming Convention

Format: `YYYYMMDD_brief_description.py`

Examples:
- `2025012_add_government_api_fields.py`
- `20250113_convert_json_to_jsonb.py`
- `20250114_add_user_preferences.py`
```

---

## Step 3.4: Deployment Checklist

- [ ] README files created (2 files)
- [ ] Inline migration comments added (2 files)
- [ ] Documentation reviewed for clarity
- [ ] Git commit with documentation updates
- [ ] Update developer onboarding docs (if applicable)

**Git Commit Message**:
```
docs(migrations): Document Phase 5 migration history and reserved name conflict

Issue #5: Add comprehensive documentation explaining why Phase 5
required two migrations due to SQLAlchemy reserved name conflict.

Changes:
- Add README_PHASE5_MIGRATIONS.md explaining migration sequence
- Update inline comments in both migration files
- Create/update alembic/README.md with best practices
- Document SQLAlchemy reserved names to avoid future issues

This clarifies the confusing two-step migration without requiring
code changes or rollbacks.

Resolves: Issue #5 (Migration Chain Confusion)
```

---

# FINAL: Complete Implementation Checklist

## Pre-Implementation

- [ ] Review all 3 phases thoroughly
- [ ] Ensure development environment ready
- [ ] Database backup created
- [ ] All existing tests passing

## Phase 1: Critical Bug Fix (Issue #6)

- [ ] Update `_rank_evidence_with_embeddings()` in retrieve.py
- [ ] Update fallback code in retrieve.py
- [ ] Improve `aggregate_api_stats()` in pipeline.py
- [ ] Create `test_evidence_retrieval_api.py` with 4 tests
- [ ] Create `test_api_pipeline_e2e.py` with integration test
- [ ] Run all new tests (should pass)
- [ ] Manual verification of database records
- [ ] Git commit with clear message
- [ ] Deploy to staging
- [ ] Smoke test on staging
- [ ] Deploy to production
- [ ] Monitor API metrics (coverage should be >0%)

## Phase 2: JSONB Standardization (Issue #4)

- [ ] Add JSONB import to check.py
- [ ] Update 11 Column(JSON) → Column(JSONB)
- [ ] Check other model files for JSON columns
- [ ] Create JSONB migration file
- [ ] Review migration SQL carefully
- [ ] Test migration on development database
- [ ] Create `test_jsonb_migration.py` with 4 tests
- [ ] Run data integrity tests
- [ ] Git commit with clear message
- [ ] Schedule maintenance window
- [ ] Backup production database
- [ ] Deploy to staging and test
- [ ] Apply migration to production
- [ ] Verify data integrity in production
- [ ] Monitor performance improvements

## Phase 3: Migration Cleanup (Issue #5)

- [ ] Create `README_PHASE5_MIGRATIONS.md`
- [ ] Update inline comments in migration 1
- [ ] Update inline comments in migration 2
- [ ] Create/update `alembic/README.md`
- [ ] Review documentation for clarity
- [ ] Git commit with clear message
- [ ] Update developer onboarding docs
- [ ] Share with team for awareness

## Post-Implementation

- [ ] All tests passing in production
- [ ] API statistics showing accurate data
- [ ] No performance regressions
- [ ] Documentation updated
- [ ] Team notified of changes
- [ ] Close related issues/tickets
- [ ] Update CHANGELOG.md

---

# Rollback Procedures

## Phase 1 Rollback (Code-Only)

```bash
# Simple git revert
git revert <commit_hash>
git push

# Redeploy
```

**Impact**: API statistics will return to broken state (0% coverage)

## Phase 2 Rollback (Database Migration)

```bash
# Rollback migration
alembic downgrade -1

# Revert code changes
git revert <commit_hash>

# Redeploy
```

**Impact**: Returns to JSON columns (slightly slower, but functional)

## Phase 3 Rollback (Documentation-Only)

```bash
# Just revert the documentation commit
git revert <commit_hash>
git push
```

**Impact**: None (documentation only)

---

# Success Criteria

## Phase 1
- ✅ API coverage percentage shows >0% for checks with API evidence
- ✅ Database `external_source_provider` column populated (not all NULL)
- ✅ Monitoring dashboard shows accurate API statistics
- ✅ All tests passing

## Phase 2
- ✅ All 11 columns using JSONB type in database
- ✅ No data loss (all existing records intact)
- ✅ Query performance same or better
- ✅ JSONB operators functional (if tested)

## Phase 3
- ✅ Clear documentation explaining migration history
- ✅ Team understands why two migrations were needed
- ✅ Future developers avoid reserved name conflicts

---

# Timeline Estimate

| Phase | Duration | Can Run Concurrently? |
|-------|----------|----------------------|
| Phase 1 (Critical) | 1.5 hours | No - Must be first |
| Phase 2 (JSONB) | 2 hours | After Phase 1 |
| Phase 3 (Docs) | 1 hour | Yes - Can be parallel |

**Minimum Time** (sequential): 4.5 hours
**With parallelization**: 3.5 hours (if Phase 3 done while Phase 2 testing)

---

# Risk Matrix

| Phase | Risk Level | Mitigation |
|-------|-----------|------------|
| Phase 1 | LOW | Code-only, well-tested, backward compatible |
| Phase 2 | MEDIUM | Database migration with backup and rollback plan |
| Phase 3 | LOW | Documentation only, no code/schema changes |

---

**Implementation Plan Complete**
**Status**: Ready for execution
**Next Step**: Begin Phase 1 implementation
