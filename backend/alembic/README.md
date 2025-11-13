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

# Generate SQL without applying (dry run)
alembic upgrade head --sql
```

## Important Notes

### Phase 5 Migrations (Government API Integration)

Phase 5 requires **two sequential migrations**:
1. `2025012_gov_api` - Adds API columns
2. `595bc2ddd5c5` - Renames metadata → api_metadata

**Always apply both together** using `alembic upgrade head`.

See [versions/README_PHASE5_MIGRATIONS.md](versions/README_PHASE5_MIGRATIONS.md) for details.

### JSONB Optimization Migration

Migration `cb8643f82fb6` converts JSON columns to JSONB for PostgreSQL optimization.

**Changes**:
- 11 columns converted from JSON → JSONB
- Affects: check (4), claim (4), evidence (2), unknown_source (1)
- Uses safe USING clause for zero data loss
- Enables PostgreSQL-specific JSONB operators and GIN indexes

## Creating New Migrations

```bash
# Generate new migration
alembic revision -m "description_of_changes"

# Auto-generate from model changes (use with caution)
alembic revision --autogenerate -m "description"
```

## Best Practices

1. **Always backup database before migrations**
   ```bash
   pg_dump tru8_prod > backup_$(date +%Y%m%d_%H%M%S).sql
   ```

2. **Test migrations on development first**
   ```bash
   # Test upgrade
   alembic upgrade head

   # Test downgrade
   alembic downgrade -1
   alembic upgrade head
   ```

3. **Avoid SQLAlchemy reserved names**
   - `metadata` (conflicts with table metadata)
   - `query` (conflicts with query builder)
   - `session` (conflicts with session management)
   - `registry` (conflicts with mapper registry)

   Check [SQLAlchemy docs](https://docs.sqlalchemy.org/en/14/orm/mapping_api.html#sqlalchemy.orm.registry.mapped) for full list.

4. **Use descriptive migration messages**
   - Good: `alembic revision -m "add_api_integration_fields"`
   - Bad: `alembic revision -m "update_db"`

5. **Include both upgrade() and downgrade() functions**
   - Always provide rollback capability
   - Test downgrade before deploying

6. **Use USING clause for type conversions**
   ```python
   # Safe column type change
   op.execute("""
       ALTER TABLE tablename
       ALTER COLUMN columnname
       TYPE jsonb
       USING columnname::jsonb
   """)
   ```

7. **Document breaking changes**
   - Add warnings in migration docstrings
   - Document required application code changes
   - Note any manual steps required

## Migration Naming Convention

Format: `YYYYMMDD_brief_description.py`

Examples:
- `2025012_add_government_api_fields.py`
- `20250113_convert_json_to_jsonb.py`
- `20250114_add_user_preferences.py`

## Common Issues

### Issue: "Can't locate revision identified by..."
**Solution**: Migration files may be missing or revision chain broken.
```bash
alembic history --verbose  # Check migration chain
```

### Issue: "Target database is not up to date"
**Solution**: Apply pending migrations.
```bash
alembic current           # Check current revision
alembic upgrade head      # Apply all pending
```

### Issue: "FAILED: Can't locate revision"
**Solution**: Ensure all migration files exist and down_revision is correct.

## Production Deployment Checklist

- [ ] Database backup created
- [ ] Migration tested on development
- [ ] Migration tested on staging
- [ ] Downgrade procedure tested
- [ ] Application code compatible with schema changes
- [ ] Maintenance window scheduled (if needed)
- [ ] Team notified of deployment
- [ ] Monitoring ready for post-migration verification

## Migration History

### Phase 5: Government API Integration
- `2025012_gov_api` - Add API tracking columns
- `595bc2ddd5c5` - Fix metadata naming conflict
- See [versions/README_PHASE5_MIGRATIONS.md](versions/README_PHASE5_MIGRATIONS.md)

### JSONB Optimization
- `cb8643f82fb6` - Convert JSON to JSONB (11 columns)
- Performance improvement for PostgreSQL

## Resources

- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [PostgreSQL JSONB](https://www.postgresql.org/docs/current/datatype-json.html)
- [Project Migration Plan](../../GOVERNMENT_API_INTEGRATION_PLAN.md)

## Questions?

Contact the development team or check project documentation in the root directory.
