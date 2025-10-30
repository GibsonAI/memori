# Database Migration Scripts - Memori v1.x → v2.0

## Quick Start

```bash
# Backup your database first!
pg_dump your_database > backup_$(date +%Y%m%d_%H%M%S).sql

# Run migration (auto-detects database type)
python migrate_v1_to_v2.py --database "postgresql://user:pass@localhost/memori_db"
```

## Available Scripts

### Migration Scripts

- **migrate_v1_to_v2_postgresql.sql** - PostgreSQL 12+ migration
- **migrate_v1_to_v2_mysql.sql** - MySQL 8.0+ / MariaDB 10.5+ migration
- **migrate_v1_to_v2_sqlite.sql** - SQLite 3.35+ migration
- **migrate_v1_to_v2.py** - Python helper (recommended, auto-detects DB type)

### Rollback Scripts

- **rollback_v2_to_v1_postgresql.sql** - PostgreSQL rollback only

## What This Migration Does

1. ✅ Adds multi-tenant columns (`user_id`, `assistant_id`)
2. ✅ Migrates `namespace` → `user_id` data
3. ✅ Makes `session_id` NOT NULL with default
4. ✅ Adds `version` column for optimistic locking
5. ✅ Creates multi-tenant indexes
6. ✅ Keeps `namespace_legacy` for rollback safety

## Usage Examples

### Python Helper (Recommended)

```bash
# With backup prompt
python migrate_v1_to_v2.py --database "postgresql://localhost/memori"

# Skip backup prompt (not recommended)
python migrate_v1_to_v2.py --database "postgresql://localhost/memori" --skip-backup

# Dry run (see what would happen)
python migrate_v1_to_v2.py --database "postgresql://localhost/memori" --dry-run

# Force migration even if validation fails
python migrate_v1_to_v2.py --database "postgresql://localhost/memori" --force
```

### Direct SQL Execution

```bash
# PostgreSQL
psql your_database < migrate_v1_to_v2_postgresql.sql

# MySQL
mysql your_database < migrate_v1_to_v2_mysql.sql

# SQLite
sqlite3 your_database.db < migrate_v1_to_v2_sqlite.sql
```

## Pre-Migration Checklist

- [ ] Backup database (CRITICAL!)
- [ ] Test on development/staging first
- [ ] Review current `namespace` values
- [ ] Plan downtime window (5-30 min)
- [ ] Update application code for v2.0 API

## Post-Migration Verification

```bash
# Verify migration succeeded
python migrate_v1_to_v2.py --database "your_connection_string" --dry-run

# Check for NULL user_id (should be 0)
SELECT COUNT(*) FROM long_term_memory WHERE user_id IS NULL;

# View user distribution
SELECT user_id, COUNT(*) FROM long_term_memory GROUP BY user_id;
```

## Rollback

### Option 1: Restore from Backup (Safest)
```bash
# PostgreSQL
psql your_database < backup_YYYYMMDD_HHMMSS.sql

# MySQL
mysql your_database < backup_YYYYMMDD_HHMMSS.sql

# SQLite
cp backup_YYYYMMDD_HHMMSS.db your_database.db
```

### Option 2: Use Rollback Script (PostgreSQL only)
```bash
psql your_database < rollback_v2_to_v1_postgresql.sql
```

*Note: Rollback script only works if `namespace_legacy` columns still exist*

## Common Issues

### "column namespace does not exist"
**Cause:** Migration already run
**Solution:** This is expected after migration

### "user_id cannot be NULL"
**Cause:** Missing user_id in new records
**Solution:** Ensure application code provides user_id

### Connection pool errors
**Cause:** Old pool settings with new architecture
**Solution:** Update to pool_size=5, max_overflow=10

## Migration Time Estimates

| Records | PostgreSQL | MySQL | SQLite |
|---------|-----------|-------|--------|
| < 10K | 1-2 min | 2-3 min | 1 min |
| 10K-100K | 5-10 min | 10-15 min | 3-5 min |
| 100K-1M | 15-30 min | 30-45 min | 10-20 min |
| 1M+ | 30-60 min | 60-90 min | 30-60 min |

## Support

- **Migration Guide:** See `/MIGRATION.md` in repo root
- **Issues:** https://github.com/your-repo/memori-saas/issues
- **Help:** Run `python migrate_v1_to_v2.py --help`

## File Structure

```
migrations/
├── README.md (this file)
├── migrate_v1_to_v2_postgresql.sql
├── migrate_v1_to_v2_mysql.sql
├── migrate_v1_to_v2_sqlite.sql
├── migrate_v1_to_v2.py
└── rollback_v2_to_v1_postgresql.sql
```

---

**⚠️ IMPORTANT: Always backup your database before running migrations!**
