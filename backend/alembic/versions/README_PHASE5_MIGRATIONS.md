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
- Avoid SQLAlchemy reserved names: `metadata`, `query`, `session`, `registry`
- Check [SQLAlchemy reserved attributes](https://docs.sqlalchemy.org/en/14/orm/mapping_api.html#sqlalchemy.orm.registry.mapped) before naming columns

## Rollback

To rollback Phase 5 changes:
```bash
alembic downgrade f53f987eedde
```

This reverts both migrations atomically.

## Questions?

See [GOVERNMENT_API_INTEGRATION_PLAN.md](../../GOVERNMENT_API_INTEGRATION_PLAN.md) for full Phase 5 documentation.

## Related Issues

- **Issue #5**: Migration Chain Confusion (Resolved via documentation)
- **Issue #6**: Type Mismatch in Aggregation (Fixed in separate commit)
- **Issue #4**: Inconsistent JSONB Usage (Fixed via migration cb8643f82fb6)
