# Database Migration Applied - Government API Fields
**Date**: 2025-01-12
**Migration**: 2025012_gov_api
**Status**: ✅ COMPLETE

---

## Summary

Successfully applied database migration `2025012_gov_api` to add Government API integration fields to the Evidence and Check tables. All 5 columns were added successfully and verified.

---

## Migration Details

**Migration File**: `backend/alembic/versions/2025012_add_government_api_fields.py`
**Revision ID**: `2025012_gov_api`
**Parent Revision**: `f53f987eedde` (Add legal_metadata field to claims)

### Migration Chain Applied
1. `f53f987eedde` → Add legal_metadata field to claims
2. `2025012_gov_api` → Add Government API fields (this migration)

---

## Database Changes

### Evidence Table - 2 New Columns

| Column Name | Data Type | Nullable | Purpose |
|-------------|-----------|----------|---------|
| `metadata` | JSONB | Yes | API-specific response metadata (JSON storage) |
| `external_source_provider` | VARCHAR(200) | Yes | API name (e.g., "ONS Economic Statistics") |

**Usage Example**:
```python
evidence = Evidence(
    title="UK Unemployment Rate",
    snippet="Latest unemployment data from ONS...",
    url="https://api.ons.gov.uk/...",
    external_source_provider="ONS Economic Statistics",
    metadata={
        "api_source": "ONS",
        "dataset_id": "LMS",
        "release_date": "2025-01-10",
        "contact_name": "Labour Market Team"
    }
)
```

### Check Table - 3 New Columns

| Column Name | Data Type | Nullable | Default | Purpose |
|-------------|-----------|----------|---------|---------|
| `api_sources_used` | JSONB | Yes | - | List of APIs queried for this check |
| `api_call_count` | INTEGER | Yes | 0 | Total number of API calls made |
| `api_coverage_percentage` | NUMERIC(5,2) | Yes | - | Percentage of evidence from APIs (0-100) |

**Usage Example**:
```python
check = Check(
    claim_text="UK unemployment is 5.2%",
    api_sources_used=[
        {"name": "ONS Economic Statistics", "results": 3},
        {"name": "FRED", "results": 2}
    ],
    api_call_count=2,
    api_coverage_percentage=45.5  # 5 API results out of 11 total evidence items
)
```

---

## Verification Results

### Migration Status
```bash
$ alembic current
2025012_gov_api (head)
```
✅ Migration is at HEAD (latest)

### Evidence Table Verification
```sql
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'evidence'
  AND column_name IN ('metadata', 'external_source_provider');
```

**Result**:
```
[OK] external_source_provider: character varying
[OK] metadata: jsonb
```

### Check Table Verification
```sql
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'check'
  AND column_name IN ('api_sources_used', 'api_call_count', 'api_coverage_percentage');
```

**Result**:
```
[OK] api_call_count: integer
[OK] api_coverage_percentage: numeric
[OK] api_sources_used: jsonb
```

---

## SQL Migration Commands

### Upgrade (Applied)
```sql
-- Evidence table
ALTER TABLE evidence
  ADD COLUMN metadata JSONB,
  ADD COLUMN external_source_provider VARCHAR(200);

-- Check table
ALTER TABLE check
  ADD COLUMN api_sources_used JSONB,
  ADD COLUMN api_call_count INTEGER DEFAULT 0,
  ADD COLUMN api_coverage_percentage NUMERIC(5, 2);
```

### Downgrade (If Needed)
```bash
# To rollback this migration:
alembic downgrade f53f987eedde
```

```sql
-- Downgrade SQL (executed by alembic)
ALTER TABLE check
  DROP COLUMN api_coverage_percentage,
  DROP COLUMN api_call_count,
  DROP COLUMN api_sources_used;

ALTER TABLE evidence
  DROP COLUMN external_source_provider,
  DROP COLUMN metadata;
```

---

## Integration with API Adapters

These new fields will be populated by the Government API adapters:

### Evidence Population
```python
# In api_adapters.py - _create_evidence_dict()
evidence = {
    "title": "Labour Market Statistics",
    "snippet": "UK unemployment rate data...",
    "url": "https://api.ons.gov.uk/datasets/LMS",
    "external_source_provider": "ONS Economic Statistics",  # NEW
    "metadata": {  # NEW
        "api_source": "ONS",
        "dataset_id": "LMS",
        "release_date": "2025-01-10"
    }
}
```

### Check Tracking
```python
# After API retrieval
check.api_sources_used = [
    {"name": "ONS Economic Statistics", "results": 3},
    {"name": "PubMed", "results": 5}
]
check.api_call_count = 2
check.api_coverage_percentage = (8 / 15) * 100  # 8 API results out of 15 total
```

---

## Performance Impact

### Storage
- **JSONB columns**: Efficient binary JSON storage with indexing support
- **VARCHAR(200)**: Small fixed-length string for API names
- **INTEGER**: 4 bytes per check
- **NUMERIC(5,2)**: 6 bytes per check (stores values 0.00-999.99)

**Estimated storage per check**: ~200-500 bytes additional (depending on JSON size)

### Indexes (Future Optimization)
Consider adding indexes for common queries:

```sql
-- Index for filtering by API source
CREATE INDEX idx_evidence_api_source ON evidence(external_source_provider);

-- GIN index for JSONB searches
CREATE INDEX idx_evidence_metadata_gin ON evidence USING GIN(metadata);
CREATE INDEX idx_check_api_sources_gin ON check USING GIN(api_sources_used);
```

---

## Testing

### Manual Testing
```python
# Test Evidence insertion
from app.models.check import Evidence

evidence = Evidence(
    title="Test Evidence",
    snippet="Test snippet",
    url="https://example.com",
    external_source_provider="Test API",
    metadata={"test_key": "test_value"}
)
session.add(evidence)
await session.commit()

# Verify
result = await session.execute(
    select(Evidence).where(Evidence.external_source_provider == "Test API")
)
assert result.scalar_one().metadata["test_key"] == "test_value"
```

### Integration Testing
```bash
# Run integration tests (when implemented)
pytest tests/integration/test_api_retrieval.py -v
```

---

## Rollback Instructions

If issues occur, rollback to previous migration:

```bash
# Check current migration
alembic current

# Rollback one step
alembic downgrade -1

# Or rollback to specific revision
alembic downgrade f53f987eedde

# Verify rollback
alembic current
# Should show: f53f987eedde
```

**Note**: Rollback will DROP the 5 new columns. Any data stored in these columns will be lost.

---

## Next Steps

### Immediate (Phase 5 - Week 2)
1. ✅ Update SQLModel models to include new fields
2. ✅ Update API adapters to populate `external_source_provider` and `metadata`
3. ✅ Update pipeline to track `api_sources_used` and calculate `api_coverage_percentage`
4. ✅ Add logging/monitoring for API usage

### Future Optimizations
1. Add indexes for common queries (see Performance Impact section)
2. Implement JSONB schema validation in application code
3. Add database constraints for `api_coverage_percentage` (0-100 range)
4. Consider partitioning tables if Evidence table grows very large

---

## Troubleshooting

### Issue: Migration fails with "column already exists"
**Solution**: Column was already added manually. Run:
```bash
alembic stamp 2025012_gov_api
```

### Issue: Cannot connect to database
**Solution**: Check DATABASE_URL in .env and ensure PostgreSQL is running:
```bash
# Windows
pg_ctl status

# Check connection
psql -h localhost -U postgres -d tru8
```

### Issue: Migration shows as applied but columns missing
**Solution**: Check you're connected to correct database:
```sql
SELECT current_database();
-- Should return: tru8
```

---

## References

- Migration file: `backend/alembic/versions/2025012_add_government_api_fields.py`
- Issue tracking: `WEEK1_ISSUES_AND_IMPROVEMENTS.md` (Issue #4)
- Fix documentation: `CRITICAL_FIXES_APPLIED.md` (Fix #5)
- Original plan: `GOVERNMENT_API_INTEGRATION_PLAN.md` (Week 1, Task 4)

---

## Sign-off

**Migration Status**: ✅ APPLIED SUCCESSFULLY
**Verification Status**: ✅ ALL COLUMNS VERIFIED
**Ready for**: Week 2 - API Adapter Integration
**Date Applied**: 2025-01-12
**Applied By**: Alembic (automated migration)

---

**Last Updated**: 2025-01-12
**Database Version**: 2025012_gov_api (HEAD)
