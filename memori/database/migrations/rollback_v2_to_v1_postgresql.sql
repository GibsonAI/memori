-- ============================================================================
-- Memori v2.0 to v1.x Rollback Script (PostgreSQL)
-- ============================================================================
-- Purpose: Rollback from multi-tenant architecture to namespace-based isolation
-- Author: Memori Team
-- Date: 2025-10-27
-- Database: PostgreSQL 12+
--
-- IMPORTANT: USE THIS ONLY IF YOU NEED TO ROLLBACK AFTER MIGRATION
-- This script assumes namespace_legacy columns still exist!
--
-- BACKUP BEFORE ROLLBACK:
-- Command: pg_dump your_database > backup_before_rollback_$(date +%Y%m%d_%H%M%S).sql
-- ============================================================================

-- Start transaction for atomic rollback
BEGIN;

-- ============================================================================
-- STEP 1: Pre-Rollback Validation
-- ============================================================================

DO $$
DECLARE
    has_legacy_columns BOOLEAN;
BEGIN
    -- Check if namespace_legacy columns exist
    SELECT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'chat_history' AND column_name = 'namespace_legacy'
    ) INTO has_legacy_columns;

    IF NOT has_legacy_columns THEN
        RAISE EXCEPTION 'Rollback not possible: namespace_legacy columns do not exist!';
    END IF;

    RAISE NOTICE 'Pre-rollback validation passed';
END $$;

-- ============================================================================
-- STEP 2: Restore namespace from namespace_legacy
-- ============================================================================

-- Add namespace column back
ALTER TABLE chat_history ADD COLUMN IF NOT EXISTS namespace TEXT;
ALTER TABLE short_term_memory ADD COLUMN IF NOT EXISTS namespace TEXT;
ALTER TABLE long_term_memory ADD COLUMN IF NOT EXISTS namespace TEXT;

-- Copy data from namespace_legacy back to namespace
UPDATE chat_history SET namespace = namespace_legacy;
UPDATE short_term_memory SET namespace = namespace_legacy;
UPDATE long_term_memory SET namespace = namespace_legacy;

-- Make namespace NOT NULL with default
ALTER TABLE chat_history ALTER COLUMN namespace SET NOT NULL;
ALTER TABLE chat_history ALTER COLUMN namespace SET DEFAULT 'default';

ALTER TABLE short_term_memory ALTER COLUMN namespace SET NOT NULL;
ALTER TABLE short_term_memory ALTER COLUMN namespace SET DEFAULT 'default';

ALTER TABLE long_term_memory ALTER COLUMN namespace SET NOT NULL;
ALTER TABLE long_term_memory ALTER COLUMN namespace SET DEFAULT 'default';

RAISE NOTICE 'Step 2 complete: Restored namespace columns';

-- ============================================================================
-- STEP 3: Drop Multi-Tenant Indexes
-- ============================================================================

-- Chat History Indexes
DROP INDEX IF EXISTS idx_chat_user_id;
DROP INDEX IF EXISTS idx_chat_user_assistant;
DROP INDEX IF EXISTS idx_chat_user_session_time;

-- Short-Term Memory Indexes
DROP INDEX IF EXISTS idx_short_term_user_id;
DROP INDEX IF EXISTS idx_short_term_user_assistant;
DROP INDEX IF EXISTS idx_short_term_user_category;
DROP INDEX IF EXISTS idx_short_term_user_session;

-- Long-Term Memory Indexes
DROP INDEX IF EXISTS idx_long_term_user_id;
DROP INDEX IF EXISTS idx_long_term_user_assistant;
DROP INDEX IF EXISTS idx_long_term_user_session;
DROP INDEX IF EXISTS idx_long_term_version;

RAISE NOTICE 'Step 3 complete: Dropped multi-tenant indexes';

-- ============================================================================
-- STEP 4: Recreate v1.x Indexes
-- ============================================================================

-- Chat History v1.x Indexes
CREATE INDEX IF NOT EXISTS idx_chat_namespace_session ON chat_history(namespace, session_id);

-- Short-Term Memory v1.x Indexes
CREATE INDEX IF NOT EXISTS idx_short_term_namespace ON short_term_memory(namespace);

-- Long-Term Memory v1.x Indexes
CREATE INDEX IF NOT EXISTS idx_long_term_namespace ON long_term_memory(namespace);

RAISE NOTICE 'Step 4 complete: Recreated v1.x indexes';

-- ============================================================================
-- STEP 5: Drop Multi-Tenant Columns
-- ============================================================================

-- Drop user_id, assistant_id, and version columns
ALTER TABLE chat_history DROP COLUMN IF EXISTS user_id;
ALTER TABLE chat_history DROP COLUMN IF EXISTS assistant_id;

ALTER TABLE short_term_memory DROP COLUMN IF EXISTS user_id;
ALTER TABLE short_term_memory DROP COLUMN IF EXISTS assistant_id;

ALTER TABLE long_term_memory DROP COLUMN IF EXISTS user_id;
ALTER TABLE long_term_memory DROP COLUMN IF EXISTS assistant_id;
ALTER TABLE long_term_memory DROP COLUMN IF EXISTS version;

-- Drop legacy columns
ALTER TABLE chat_history DROP COLUMN IF EXISTS namespace_legacy;
ALTER TABLE short_term_memory DROP COLUMN IF EXISTS namespace_legacy;
ALTER TABLE long_term_memory DROP COLUMN IF EXISTS namespace_legacy;

RAISE NOTICE 'Step 5 complete: Dropped multi-tenant columns';

-- ============================================================================
-- STEP 6: Restore FTS Triggers (if needed)
-- ============================================================================

-- Drop v2.0 FTS triggers if they exist
DROP TRIGGER IF EXISTS update_short_term_search_vector ON short_term_memory;
DROP TRIGGER IF EXISTS update_long_term_search_vector ON long_term_memory;

-- Note: If you had custom FTS triggers in v1.x, restore them here

RAISE NOTICE 'Step 6 complete: FTS triggers handled';

-- ============================================================================
-- STEP 7: Post-Rollback Validation
-- ============================================================================

DO $$
DECLARE
    chat_null_namespaces INTEGER;
    stm_null_namespaces INTEGER;
    ltm_null_namespaces INTEGER;
BEGIN
    -- Check for any NULL namespace values (should be 0)
    SELECT COUNT(*) INTO chat_null_namespaces FROM chat_history WHERE namespace IS NULL;
    SELECT COUNT(*) INTO stm_null_namespaces FROM short_term_memory WHERE namespace IS NULL;
    SELECT COUNT(*) INTO ltm_null_namespaces FROM long_term_memory WHERE namespace IS NULL;

    IF chat_null_namespaces > 0 OR stm_null_namespaces > 0 OR ltm_null_namespaces > 0 THEN
        RAISE EXCEPTION 'Rollback validation failed! Found NULL values in namespace fields.';
    END IF;

    RAISE NOTICE 'Step 7 complete: Post-rollback validation passed';
END $$;

-- ============================================================================
-- STEP 8: Generate Rollback Report
-- ============================================================================

DO $$
DECLARE
    rec RECORD;
BEGIN
    RAISE NOTICE '========================================';
    RAISE NOTICE 'ROLLBACK COMPLETED SUCCESSFULLY';
    RAISE NOTICE '========================================';
    RAISE NOTICE '';
    RAISE NOTICE 'Post-rollback statistics:';

    -- Chat history stats
    FOR rec IN SELECT namespace, COUNT(*) as count FROM chat_history GROUP BY namespace LOOP
        RAISE NOTICE 'chat_history - namespace: %, count: %', rec.namespace, rec.count;
    END LOOP;

    -- Short-term memory stats
    FOR rec IN SELECT namespace, COUNT(*) as count FROM short_term_memory GROUP BY namespace LOOP
        RAISE NOTICE 'short_term_memory - namespace: %, count: %', rec.namespace, rec.count;
    END LOOP;

    -- Long-term memory stats
    FOR rec IN SELECT namespace, COUNT(*) as count FROM long_term_memory GROUP BY namespace LOOP
        RAISE NOTICE 'long_term_memory - namespace: %, count: %', rec.namespace, rec.count;
    END LOOP;

    RAISE NOTICE '';
    RAISE NOTICE 'Database has been rolled back to v1.x schema';
    RAISE NOTICE 'You can now use the v1.x version of Memori';
END $$;

-- Commit transaction
COMMIT;

RAISE NOTICE 'Rollback transaction committed successfully!';
