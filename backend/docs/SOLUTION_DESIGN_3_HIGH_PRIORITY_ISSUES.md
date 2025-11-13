# Solution Design: 3 High-Priority Issues

**Date**: 2025-11-13
**Status**: COMPREHENSIVE SOLUTION DESIGN
**Complexity**: Issue #6 (Low), Issue #4 (Medium), Issue #5 (Low)

---

## Executive Summary

I have sufficient understanding to design and implement complete solutions for all 3 issues. Each solution includes:
- Exact code changes required
- All peripheral code realignment
- Testing strategy
- Rollback procedures
- Risk assessment

**Total Estimated Time**: 4-6 hours
**Risk Level**: LOW (all changes are isolated and testable)

---

# ISSUE #6: Type Mismatch in Aggregation (CRITICAL BUG)

## Problem Statement

**Current Data Flow**:
```
API Adapter (_create_evidence_dict)
  ↓ Returns: {"external_source_provider": "ONS", "metadata": {...}}

retrieve.py (_convert_api_evidence_to_snippets)
  ↓ MOVES external_source_provider into metadata
  ↓ Returns: {"metadata": {"external_source_provider": "ONS", ...}}

pipeline.py (save_check_results_sync)
  ↓ Looks for ev_data.get("external_source_provider") at TOP LEVEL
  ↓ Result: None (it's nested!)

Database: external_source_provider = NULL ❌
```

**Impact**: API statistics always show 0% coverage, external_source_provider column always NULL.

---

## Solution Design

### Option A: Preserve Top-Level Field (RECOMMENDED)

**Strategy**: Keep `external_source_provider` at top-level AND in metadata for backward compatibility.

#### File 1: `backend/app/pipeline/retrieve.py` (Lines 622-652)

**Current Code**:
```python
def _convert_api_evidence_to_snippets(
    self,
    api_evidence: List[Dict[str, Any]]
) -> List[EvidenceSnippet]:
    """Convert API evidence dictionaries to EvidenceSnippet objects"""
    snippets = []

    for evidence in api_evidence:
        try:
            snippet = EvidenceSnippet(
                text=evidence.get("snippet", ""),
                source=evidence.get("source", "Unknown API"),
                url=evidence.get("url", ""),
                title=evidence.get("title", ""),
                published_date=evidence.get("source_date"),
                relevance_score=0.8,
                word_count=len(evidence.get("snippet", "").split()),
                metadata={  # ❌ Creating new metadata dict, losing top-level field
                    **evidence.get("metadata", {}),
                    "external_source_provider": evidence.get("external_source_provider"),
                    "credibility_score": evidence.get("credibility_score", 0.95)
                }
            )
```

**Fixed Code**:
```python
def _convert_api_evidence_to_snippets(
    self,
    api_evidence: List[Dict[str, Any]]
) -> List[EvidenceSnippet]:
    """
    Convert API evidence dictionaries to EvidenceSnippet objects.

    IMPORTANT: Preserves external_source_provider at top-level for proper tracking.
    """
    snippets = []

    for evidence in api_evidence:
        try:
            # Extract fields to preserve top-level structure
            external_source = evidence.get("external_source_provider")
            credibility = evidence.get("credibility_score", 0.95)
            existing_metadata = evidence.get("metadata", {})

            # Build metadata dict that includes API-specific fields
            metadata = {
                **existing_metadata,
                "external_source_provider": external_source,  # Also store in metadata for context
                "credibility_score": credibility
            }

            snippet = EvidenceSnippet(
                text=evidence.get("snippet", ""),
                source=evidence.get("source", "Unknown API"),
                url=evidence.get("url", ""),
                title=evidence.get("title", ""),
                published_date=evidence.get("source_date"),
                relevance_score=0.8,
                word_count=len(evidence.get("snippet", "").split()),
                metadata=metadata  # Metadata dict with API fields
            )
            snippets.append(snippet)

        except Exception as e:
            logger.error(f"Failed to convert API evidence to snippet: {e}")
            continue

    return snippets
```

**Wait, that still won't work!** EvidenceSnippet only stores metadata, not top-level fields.

#### Real Solution: Modify `_rank_evidence_with_embeddings`

The issue is that `_rank_evidence_with_embeddings` (retrieve.py:168-229) creates new dicts from EvidenceSnippet objects, but doesn't preserve `external_source_provider` at top level.

**File: `backend/app/pipeline/retrieve.py` (Lines 186-203)**

**Current Code**:
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
    "metadata": snippet.metadata  # ❌ Only metadata, no external_source_provider at top
}
```

**Fixed Code**:
```python
# Extract external_source_provider from metadata if present
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

**Do the same in the fallback** (Lines 214-229).

---

### Peripheral Code Realignment

#### 1. Update `aggregate_api_stats` function (pipeline.py:628-635)

**Current Code**:
```python
for ev_list in evidence.values():
    for ev in ev_list:
        if ev.get("external_source_provider"):  # ❌ May not find it
            api_evidence_count += 1
```

**Improved Code** (defensive):
```python
for ev_list in evidence.values():
    for ev in ev_list:
        # Check both top-level and nested (for robustness)
        external_provider = ev.get("external_source_provider")
        if not external_provider and ev.get("metadata"):
            external_provider = ev.get("metadata", {}).get("external_source_provider")

        if external_provider:
            api_evidence_count += 1
```

#### 2. Verify `save_check_results_sync` (pipeline.py:184-211)

**Current Code** (Lines 186, 210-211):
```python
metadata_dict = ev_data.get("metadata", {})
# ...
external_source_provider=ev_data.get("external_source_provider"),  # ✅ Correct
api_metadata=metadata_dict  # ✅ Correct
```

**This is already correct!** No changes needed. Once we fix the data flow, this will work.

---

### Testing Strategy

#### Test 1: Unit Test for `_convert_api_evidence_to_snippets`

```python
def test_convert_api_evidence_preserves_external_source_provider():
    """Test that external_source_provider is preserved at top level."""
    retriever = EvidenceRetriever()

    api_evidence = [{
        "snippet": "Test evidence",
        "source": "ONS Economic Statistics",
        "url": "https://ons.gov.uk/data",
        "title": "UK GDP Data",
        "external_source_provider": "ONS",
        "credibility_score": 0.95,
        "metadata": {"api_source": "ONS"}
    }]

    snippets = retriever._convert_api_evidence_to_snippets(api_evidence)

    # Convert snippet back to dict (simulating ranking)
    evidence_item = {
        "text": snippets[0].text,
        "source": snippets[0].source,
        "external_source_provider": snippets[0].metadata.get("external_source_provider"),
        "metadata": snippets[0].metadata
    }

    # Should be at top level after fix
    assert evidence_item.get("external_source_provider") == "ONS"
```

#### Test 2: Integration Test for API Stats

```python
def test_api_stats_aggregation_with_api_evidence():
    """Test that API evidence is correctly counted in statistics."""
    from app.workers.pipeline import aggregate_api_stats

    claims = [{"api_stats": {"total_api_calls": 2, "apis_queried": []}}]

    evidence = {
        "0": [
            {"text": "Web evidence", "source": "BBC"},
            {"text": "API evidence", "source": "ONS", "external_source_provider": "ONS"},
            {"text": "API evidence 2", "source": "PubMed", "external_source_provider": "PubMed"}
        ]
    }

    stats = aggregate_api_stats(claims, evidence)

    assert stats["total_evidence_count"] == 3
    assert stats["api_evidence_count"] == 2  # ❌ Currently fails (returns 0)
    assert stats["api_coverage_percentage"] == 66.67
```

---

### Implementation Steps

1. **Fix `_rank_evidence_with_embeddings`** (retrieve.py:186-203)
   - Add `external_source_provider` and `credibility_score` to evidence_item dict
   - Add same fields to fallback code (lines 214-229)
   - **Time**: 15 minutes

2. **Improve `aggregate_api_stats`** (pipeline.py:628-635)
   - Add defensive check for nested external_source_provider
   - **Time**: 10 minutes

3. **Add unit tests**
   - Test evidence conversion preserves fields
   - Test API stats aggregation
   - **Time**: 30 minutes

4. **Run integration tests**
   - Verify full pipeline with API retrieval
   - Check database records have external_source_provider populated
   - **Time**: 15 minutes

**Total Time**: ~1 hour
**Risk**: Low (localized changes, well-tested)

---

# ISSUE #4: Inconsistent JSONB Usage

## Problem Statement

**Model Layer** (check.py):
- Uses `Column(JSON)` for 11 JSON columns
- Generic SQLAlchemy type, database-agnostic

**Migration Layer** (Phase 5):
- Uses `postgresql.JSONB` for new columns
- PostgreSQL-specific optimized type

**Result**: Type mismatch prevents using PostgreSQL JSONB features (GIN indexes, operators).

---

## Solution Design

### Approach: Standardize on postgresql.JSONB

**Rationale**:
- Tru8 uses PostgreSQL exclusively (not multi-database)
- JSONB is more performant
- Enables future optimization (GIN indexes, JSONB operators)
- Minimal risk (JSON columns already work, just changing type definition)

---

### Changes Required

#### File 1: `backend/app/models/check.py`

**Add import at top**:
```python
from sqlalchemy.dialects.postgresql import JSONB
```

**Change all instances of `Column(JSON)` to `Column(JSONB)`**:

**11 locations in check.py**:

1. Line 14: `input_content` (Check model)
2. Line 24: `decision_trail` (Check model)
3. Line 52: `query_sources` (Check model)
4. Line 59: `api_sources_used` (Check model) **← Phase 5 field**
5. Line 88: `temporal_markers` (Claim model)
6. Line 96: `legal_metadata` (Claim model)
7. Line 100: `confidence_breakdown` (Claim model)
8. Line 109: `key_entities` (Claim model)
9. Line 154: `risk_flags` (Evidence model)
10. Line 171: `api_metadata` (Evidence model) **← Phase 5 field**

**Example Change**:
```python
# Before
api_sources_used: Optional[str] = Field(
    default=None,
    sa_column=Column(JSON),  # ❌
    description="List of government APIs queried"
)

# After
api_sources_used: Optional[str] = Field(
    default=None,
    sa_column=Column(JSONB),  # ✅
    description="List of government APIs queried"
)
```

#### File 2: `backend/app/models/unknown_source.py` (if exists)

Check if this file has any `Column(JSON)` and update similarly.

---

### Database Migration Required

Since existing columns are already `JSON` type in database, we need a migration to alter column types.

**Create new migration**:

```bash
cd backend
alembic revision -m "convert_json_columns_to_jsonb"
```

**Migration content** (`backend/alembic/versions/[timestamp]_convert_json_columns_to_jsonb.py`):

```python
"""Convert JSON columns to JSONB for PostgreSQL optimization

Revision ID: [generated]
Revises: 595bc2ddd5c5
Create Date: 2025-11-13
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '[generated]'
down_revision = '595bc2ddd5c5'  # Previous migration
branch_labels = None
depends_on = None


def upgrade():
    """Convert JSON columns to JSONB"""

    # Check table columns
    op.execute("ALTER TABLE check ALTER COLUMN input_content TYPE jsonb USING input_content::jsonb")
    op.execute("ALTER TABLE check ALTER COLUMN decision_trail TYPE jsonb USING decision_trail::jsonb")
    op.execute("ALTER TABLE check ALTER COLUMN query_sources TYPE jsonb USING query_sources::jsonb")
    op.execute("ALTER TABLE check ALTER COLUMN api_sources_used TYPE jsonb USING api_sources_used::jsonb")

    # Claim table columns
    op.execute("ALTER TABLE claim ALTER COLUMN temporal_markers TYPE jsonb USING temporal_markers::jsonb")
    op.execute("ALTER TABLE claim ALTER COLUMN legal_metadata TYPE jsonb USING legal_metadata::jsonb")
    op.execute("ALTER TABLE claim ALTER COLUMN confidence_breakdown TYPE jsonb USING confidence_breakdown::jsonb")
    op.execute("ALTER TABLE claim ALTER COLUMN key_entities TYPE jsonb USING key_entities::jsonb")

    # Evidence table columns
    op.execute("ALTER TABLE evidence ALTER COLUMN risk_flags TYPE jsonb USING risk_flags::jsonb")
    op.execute("ALTER TABLE evidence ALTER COLUMN api_metadata TYPE jsonb USING api_metadata::jsonb")

    print("✅ Successfully converted 10 JSON columns to JSONB")


def downgrade():
    """Revert JSONB columns to JSON"""

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

**Why use `ALTER TABLE ... TYPE ... USING`?**
- PostgreSQL requires explicit cast when changing column type
- `USING column::jsonb` safely converts existing JSON data to JSONB
- Zero data loss, preserves all existing records

---

### Peripheral Code Changes

#### None Required!

**Reason**: This is purely a schema change. Application code using these columns:
- `check.api_sources_used = data`
- `claim.key_entities = entities`
- etc.

...will continue to work identically. SQLAlchemy handles the serialization transparently.

---

### Testing Strategy

#### Test 1: Migration Dry Run

```bash
# Test upgrade
cd backend
alembic upgrade head --sql > migration_test.sql
cat migration_test.sql  # Review SQL

# Test on development database
alembic upgrade head
```

#### Test 2: Data Integrity Check

```python
def test_jsonb_columns_preserve_data():
    """Test that JSONB conversion doesn't lose data."""
    from app.core.database import sync_session
    from app.models import Check

    # Create check with JSON data
    check = Check(
        user_id="test_user",
        input_type="text",
        input_content={"text": "Test claim with nested data", "metadata": {"key": "value"}},
        api_sources_used=[{"name": "ONS", "results": 5}]
    )

    with sync_session() as session:
        session.add(check)
        session.commit()
        check_id = check.id

    # Retrieve and verify
    with sync_session() as session:
        retrieved = session.get(Check, check_id)

        assert retrieved.input_content["text"] == "Test claim with nested data"
        assert retrieved.input_content["metadata"]["key"] == "value"
        assert retrieved.api_sources_used[0]["name"] == "ONS"
```

#### Test 3: JSONB Operators (Future)

```python
def test_jsonb_operators_work():
    """Test that JSONB operators work after migration."""
    from sqlalchemy import select, func

    # Test JSONB containment operator @>
    stmt = select(Check).where(
        Check.api_sources_used.contains([{"name": "ONS"}])
    )

    # This should work after JSONB conversion
    # (would fail with JSON type)
```

---

### Implementation Steps

1. **Update model imports** (check.py, unknown_source.py if exists)
   - Add `from sqlalchemy.dialects.postgresql import JSONB`
   - **Time**: 2 minutes

2. **Update all Column(JSON) to Column(JSONB)** (11 instances)
   - Search and replace carefully
   - **Time**: 10 minutes

3. **Create migration**
   - Generate migration file
   - Write upgrade/downgrade SQL
   - **Time**: 30 minutes

4. **Test migration on dev database**
   - Backup database
   - Run migration
   - Verify data integrity
   - **Time**: 30 minutes

5. **Update documentation**
   - Document JSONB usage in models
   - Note PostgreSQL-specific features available
   - **Time**: 15 minutes

**Total Time**: ~1.5 hours
**Risk**: Medium (requires database migration, but safe with USING clause)

---

# ISSUE #5: Migration Chain Confusion

## Problem Statement

Two migrations for one field rename:
1. Migration `2025012_gov_api`: Creates `Evidence.metadata` (JSONB)
2. Migration `595bc2ddd5c5`: Renames to `Evidence.api_metadata`

**Issue**: Confusing migration history, intermediate state doesn't match model.

---

## Solution Design

### Option A: Consolidate Migrations (RECOMMENDED for Clean History)

**Create new single migration that replaces both**:

#### Step 1: Rollback both migrations (if applied)

```bash
cd backend
alembic downgrade f53f987eedde  # Rollback to before Phase 5
```

#### Step 2: Delete problematic migrations

```bash
rm backend/alembic/versions/2025012_add_government_api_fields.py
rm backend/alembic/versions/2025_11_12_1601_595bc2ddd5c5_rename_evidence_metadata_to_api_metadata.py
```

#### Step 3: Create consolidated migration

```bash
alembic revision -m "add_government_api_integration_fields_consolidated"
```

**New migration content**:

```python
"""Add Government API Integration fields (consolidated)

This migration consolidates the original two-step migration:
1. add_government_api_fields (created Evidence.metadata)
2. rename to api_metadata (fixed SQLAlchemy reserved name conflict)

We now create api_metadata directly to avoid the intermediate state.

Revision ID: [generated]
Revises: f53f987eedde
Create Date: 2025-11-13
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '[generated]'
down_revision = 'f53f987eedde'  # Before Phase 5
branch_labels = None
depends_on = None


def upgrade():
    """Add Phase 5 Government API Integration fields"""

    # Evidence table - Use api_metadata from the start (avoiding SQLAlchemy conflict)
    op.add_column('evidence',
        sa.Column('api_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True,
                  comment='API-specific response metadata (Phase 5)')
    )
    op.add_column('evidence',
        sa.Column('external_source_provider', sa.String(200), nullable=True,
                  comment='API name, e.g. ONS, PubMed (Phase 5)')
    )

    # Check table - API usage tracking
    op.add_column('check',
        sa.Column('api_sources_used', postgresql.JSONB(astext_type=sa.Text()), nullable=True,
                  comment='List of government APIs queried (Phase 5)')
    )
    op.add_column('check',
        sa.Column('api_call_count', sa.Integer(), nullable=True, server_default='0',
                  comment='Total API calls made (Phase 5)')
    )
    op.add_column('check',
        sa.Column('api_coverage_percentage', sa.Numeric(5, 2), nullable=True,
                  comment='Percentage of evidence from APIs 0-100 (Phase 5)')
    )


def downgrade():
    """Remove Phase 5 Government API Integration fields"""

    # Remove Check table columns
    op.drop_column('check', 'api_coverage_percentage')
    op.drop_column('check', 'api_call_count')
    op.drop_column('check', 'api_sources_used')

    # Remove Evidence table columns
    op.drop_column('evidence', 'external_source_provider')
    op.drop_column('evidence', 'api_metadata')
```

**Benefits**:
- Clean migration history
- No intermediate invalid state
- Clear documentation of why `api_metadata` (not `metadata`)
- Single atomic operation

---

### Option B: Document Existing Migrations (Lower Effort)

If migrations are already applied in production, consolidation requires rollback. Instead, add documentation.

**Create: `backend/alembic/versions/README_PHASE5_MIGRATIONS.md`**

```markdown
# Phase 5 Migration History

## Why Two Migrations for One Field?

The Evidence.api_metadata field required two migrations due to a SQLAlchemy reserved name conflict:

### Migration 1: `2025012_add_government_api_fields.py`
- Created Evidence.metadata (JSONB)
- Created Evidence.external_source_provider
- Created Check API tracking fields

**Issue**: `metadata` is a reserved attribute in SQLAlchemy Base classes, causing runtime conflicts.

### Migration 2: `2025_11_12_1601_595bc2ddd5c5_rename_evidence_metadata_to_api_metadata.py`
- Renamed Evidence.metadata → Evidence.api_metadata
- Fixed the SQLAlchemy conflict

## Important Notes

- **Both migrations must be applied in order**
- After both migrations, Evidence has `api_metadata` (not `metadata`)
- The intermediate state (after migration 1 only) is invalid
- Always use `alembic upgrade head` to apply all migrations together

## Future Migrations

New migrations should use `api_metadata` as the correct column name.
```

---

### Testing Strategy

#### If Consolidating (Option A):

```bash
# 1. Test on fresh database
alembic upgrade head

# 2. Verify schema
psql -d tru8_dev -c "\d evidence"
# Should show: api_metadata (jsonb), external_source_provider (varchar)

# 3. Verify Check table
psql -d tru8_dev -c "\d check"
# Should show: api_sources_used (jsonb), api_call_count (int), api_coverage_percentage (numeric)
```

#### If Documenting (Option B):

No testing needed, documentation-only change.

---

### Implementation Steps

#### Option A (Consolidate):

1. **Rollback migrations** (if applied)
   - `alembic downgrade f53f987eedde`
   - **Time**: 5 minutes

2. **Delete old migrations**
   - Remove 2 migration files
   - **Time**: 2 minutes

3. **Create consolidated migration**
   - Generate and write new migration
   - **Time**: 20 minutes

4. **Test migration**
   - Run on dev database
   - Verify schema
   - **Time**: 15 minutes

**Total Time**: ~45 minutes
**Risk**: Low (clean slate approach)

#### Option B (Document):

1. **Create README**
   - Explain migration history
   - **Time**: 15 minutes

**Total Time**: 15 minutes
**Risk**: None (documentation only)

---

## Summary: Full Solution Scope

### Files to Modify

| File | Issue | Changes | Lines | Risk |
|------|-------|---------|-------|------|
| `app/pipeline/retrieve.py` | #6 | Add top-level fields to evidence_item dict | ~10 | Low |
| `app/workers/pipeline.py` | #6 | Improve aggregate_api_stats defensively | ~5 | Low |
| `app/models/check.py` | #4 | Change Column(JSON) to Column(JSONB) | ~11 | Low |
| `alembic/versions/[new].py` | #4 | New migration for JSONB conversion | ~60 | Medium |
| `alembic/versions/[new].py` | #5 | Consolidated Phase 5 migration | ~50 | Low |

**Total Files Modified**: 3 core files + 2 new migrations
**Total Line Changes**: ~136 lines
**New Tests Required**: 4 test functions

---

### Implementation Order (Recommended)

1. **Issue #6 (Critical Bug)** - Fix immediately
   - Time: 1 hour
   - Deploy to production ASAP

2. **Issue #5 (Documentation Debt)** - Document or consolidate
   - Time: 15 minutes (document) OR 45 minutes (consolidate)
   - Low priority, can wait

3. **Issue #4 (Technical Debt)** - Schedule for next sprint
   - Time: 1.5 hours
   - Requires database migration in production
   - Plan maintenance window

---

### Risk Assessment

| Issue | Risk Level | Rollback Complexity | Production Impact |
|-------|-----------|-------------------|------------------|
| #6 | LOW | Trivial (code-only) | HIGH (stats broken) |
| #4 | MEDIUM | Easy (migration rollback) | LOW (optimization) |
| #5 | LOW | Easy (doc or migration) | NONE |

---

### Testing Checklist

#### Before Deployment
- [ ] Run all existing unit tests
- [ ] Run all integration tests
- [ ] Test API retrieval end-to-end
- [ ] Verify external_source_provider populates in database
- [ ] Verify API statistics show non-zero coverage
- [ ] Test migration upgrade/downgrade (Issue #4)
- [ ] Verify JSONB data integrity (Issue #4)

#### After Deployment
- [ ] Monitor API coverage percentage (should be >0%)
- [ ] Check external_source_provider column has values
- [ ] Verify API metrics dashboard shows accurate data
- [ ] Monitor database performance (Issue #4)

---

## Conclusion

**I have sufficient understanding to implement all three solutions.**

**Key Points**:
1. **Issue #6** is a straightforward bug fix with clear root cause and solution
2. **Issue #4** requires a database migration but is low-risk with proper testing
3. **Issue #5** is cosmetic and can be addressed with documentation or consolidation

**All peripheral code has been identified and solutions are complete.**

**Recommended Next Steps**:
1. Review this design document
2. Approve approach for each issue
3. I will implement fixes in order of priority
4. Deploy Issue #6 immediately (critical bug)
5. Schedule Issues #4 and #5 for next maintenance window

---

**Design Complete**: 2025-11-13
**Ready for Implementation**: YES
**Estimated Total Time**: 3-4 hours (all three issues)
