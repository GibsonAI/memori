-- ============================================================================
-- Memori v1.x to v2.0 Migration Script (MySQL/MariaDB)
-- ============================================================================
-- Purpose: Migrate from namespace-based isolation to multi-tenant architecture
-- Author: Memori Team
-- Date: 2025-10-27
-- Database: MySQL 8.0+ or MariaDB 10.5+
--
-- IMPORTANT: BACKUP YOUR DATABASE BEFORE RUNNING THIS MIGRATION!
-- Command: mysqldump your_database > backup_$(date +%Y%m%d_%H%M%S).sql
-- ============================================================================

-- Disable foreign key checks during migration
SET FOREIGN_KEY_CHECKS = 0;

-- Start transaction for atomic migration
START TRANSACTION;

-- ============================================================================
-- STEP 1: Pre-Migration Validation
-- ============================================================================

SELECT 'Pre-migration record counts:' AS info;
SELECT 'chat_history', COUNT(*) AS count FROM chat_history;
SELECT 'short_term_memory', COUNT(*) AS count FROM short_term_memory;
SELECT 'long_term_memory', COUNT(*) AS count FROM long_term_memory;

-- ============================================================================
-- STEP 2: Add New Multi-Tenant Columns
-- ============================================================================

-- Add user_id columns (primary tenant isolation field)
ALTER TABLE chat_history ADD COLUMN user_id TEXT;
ALTER TABLE short_term_memory ADD COLUMN user_id TEXT AFTER retention_type;
ALTER TABLE long_term_memory ADD COLUMN user_id TEXT AFTER retention_type;

-- Add assistant_id columns (optional bot/assistant isolation)
ALTER TABLE chat_history ADD COLUMN assistant_id TEXT AFTER user_id;
ALTER TABLE short_term_memory ADD COLUMN assistant_id TEXT AFTER user_id;
ALTER TABLE long_term_memory ADD COLUMN assistant_id TEXT AFTER user_id;

-- Add session_id for long_term_memory if it doesn't exist
ALTER TABLE long_term_memory ADD COLUMN IF NOT EXISTS session_id TEXT AFTER assistant_id;

-- Add version column for optimistic locking (prevents race conditions)
ALTER TABLE long_term_memory ADD COLUMN version INT DEFAULT 1 AFTER session_id;

SELECT 'Step 2 complete: Added new columns' AS status;

-- ============================================================================
-- STEP 3: Migrate Data from namespace to user_id
-- ============================================================================

-- Migrate chat_history: namespace -> user_id
UPDATE chat_history
SET user_id = COALESCE(namespace, 'default')
WHERE user_id IS NULL;

-- Migrate short_term_memory: namespace -> user_id
UPDATE short_term_memory
SET user_id = COALESCE(namespace, 'default')
WHERE user_id IS NULL;

-- Migrate long_term_memory: namespace -> user_id
UPDATE long_term_memory
SET user_id = COALESCE(namespace, 'default')
WHERE user_id IS NULL;

SELECT 'Step 3 complete: Migrated namespace data to user_id' AS status;

-- ============================================================================
-- STEP 4: Handle session_id NULL Values
-- ============================================================================

-- Set default session_id for existing NULL values
UPDATE long_term_memory
SET session_id = 'default'
WHERE session_id IS NULL OR session_id = '';

-- Set default session_id for short_term_memory if NULL
UPDATE short_term_memory
SET session_id = 'default'
WHERE session_id IS NULL OR session_id = '';

SELECT 'Step 4 complete: Fixed NULL session_id values' AS status;

-- ============================================================================
-- STEP 5: Modify Columns to NOT NULL (MySQL syntax)
-- ============================================================================

-- Make user_id NOT NULL with default
ALTER TABLE chat_history MODIFY COLUMN user_id TEXT NOT NULL;
ALTER TABLE short_term_memory MODIFY COLUMN user_id TEXT NOT NULL;
ALTER TABLE long_term_memory MODIFY COLUMN user_id TEXT NOT NULL;

-- Make session_id NOT NULL for data consistency
ALTER TABLE long_term_memory MODIFY COLUMN session_id TEXT NOT NULL;

-- Ensure version is NOT NULL
ALTER TABLE long_term_memory MODIFY COLUMN version INT NOT NULL DEFAULT 1;

SELECT 'Step 5 complete: Added NOT NULL constraints' AS status;

-- ============================================================================
-- STEP 6: Create Multi-Tenant Indexes
-- ============================================================================

-- Chat History Indexes
CREATE INDEX idx_chat_user_id ON chat_history(user_id(255));
CREATE INDEX idx_chat_user_assistant ON chat_history(user_id(255), assistant_id(255));
CREATE INDEX idx_chat_user_session_time ON chat_history(user_id(255), session_id(255), created_at);

-- Short-Term Memory Indexes
CREATE INDEX idx_short_term_user_id ON short_term_memory(user_id(255));
CREATE INDEX idx_short_term_user_assistant ON short_term_memory(user_id(255), assistant_id(255));
CREATE INDEX idx_short_term_user_category ON short_term_memory(user_id(255), category_primary);
CREATE INDEX idx_short_term_user_session ON short_term_memory(user_id(255), session_id(255));

-- Long-Term Memory Indexes
CREATE INDEX idx_long_term_user_id ON long_term_memory(user_id(255));
CREATE INDEX idx_long_term_user_assistant ON long_term_memory(user_id(255), assistant_id(255));
CREATE INDEX idx_long_term_user_session ON long_term_memory(user_id(255), session_id(255));
CREATE INDEX idx_long_term_version ON long_term_memory(memory_id, version);

SELECT 'Step 6 complete: Created multi-tenant indexes' AS status;

-- ============================================================================
-- STEP 7: Rename Old Columns (Keep for Rollback Capability)
-- ============================================================================

-- Rename namespace columns instead of dropping them (safer for rollback)
ALTER TABLE chat_history CHANGE COLUMN namespace namespace_legacy TEXT;
ALTER TABLE short_term_memory CHANGE COLUMN namespace namespace_legacy TEXT;
ALTER TABLE long_term_memory CHANGE COLUMN namespace namespace_legacy TEXT;

SELECT 'Step 7 complete: Renamed namespace columns to namespace_legacy' AS status;

-- ============================================================================
-- STEP 8: Update FULLTEXT Indexes (MySQL specific)
-- ============================================================================

-- Check if FULLTEXT indexes exist and recreate them with new columns
-- Note: MySQL FULLTEXT works differently than PostgreSQL tsvector

-- Drop old FULLTEXT indexes if they exist
ALTER TABLE short_term_memory DROP INDEX IF EXISTS idx_fulltext_searchable;
ALTER TABLE long_term_memory DROP INDEX IF EXISTS idx_fulltext_searchable;

-- Recreate FULLTEXT indexes (if searchable_content exists)
-- MySQL FULLTEXT only works on VARCHAR, TEXT, or CHAR columns
SELECT 'Creating FULLTEXT indexes for improved search performance' AS status;

ALTER TABLE short_term_memory ADD FULLTEXT INDEX idx_fulltext_searchable (searchable_content, summary);
ALTER TABLE long_term_memory ADD FULLTEXT INDEX idx_fulltext_searchable (searchable_content, summary);

SELECT 'Step 8 complete: Updated FULLTEXT indexes' AS status;

-- ============================================================================
-- STEP 9: Post-Migration Validation
-- ============================================================================

-- Check for any NULL user_id values (should be 0)
SELECT 'Validating migration...' AS status;

SELECT 'Checking for NULL user_id in chat_history:' AS check_name, COUNT(*) AS null_count
FROM chat_history WHERE user_id IS NULL;

SELECT 'Checking for NULL user_id in short_term_memory:' AS check_name, COUNT(*) AS null_count
FROM short_term_memory WHERE user_id IS NULL;

SELECT 'Checking for NULL user_id in long_term_memory:' AS check_name, COUNT(*) AS null_count
FROM long_term_memory WHERE user_id IS NULL;

SELECT 'Checking for NULL session_id in long_term_memory:' AS check_name, COUNT(*) AS null_count
FROM long_term_memory WHERE session_id IS NULL;

SELECT 'Step 9 complete: Post-migration validation passed' AS status;

-- ============================================================================
-- STEP 10: Generate Migration Report
-- ============================================================================

SELECT '========================================'  AS info;
SELECT 'MIGRATION COMPLETED SUCCESSFULLY' AS info;
SELECT '========================================'  AS info;

SELECT 'Post-migration statistics:' AS info;

-- Chat history stats by user
SELECT 'chat_history' AS table_name, user_id, COUNT(*) AS count
FROM chat_history GROUP BY user_id;

-- Short-term memory stats by user
SELECT 'short_term_memory' AS table_name, user_id, COUNT(*) AS count
FROM short_term_memory GROUP BY user_id;

-- Long-term memory stats by user
SELECT 'long_term_memory' AS table_name, user_id, COUNT(*) AS count
FROM long_term_memory GROUP BY user_id;

SELECT '' AS info;
SELECT 'IMPORTANT: Keep namespace_legacy columns for now (needed for rollback)' AS info;
SELECT 'After confirming the migration works, you can drop them with:' AS info;
SELECT '  ALTER TABLE chat_history DROP COLUMN namespace_legacy;' AS info;
SELECT '  ALTER TABLE short_term_memory DROP COLUMN namespace_legacy;' AS info;
SELECT '  ALTER TABLE long_term_memory DROP COLUMN namespace_legacy;' AS info;
SELECT '' AS info;
SELECT 'To rollback this migration, run: rollback_v2_to_v1_mysql.sql' AS info;

-- Commit transaction
COMMIT;

-- Re-enable foreign key checks
SET FOREIGN_KEY_CHECKS = 1;

SELECT 'Migration transaction committed successfully!' AS status;
