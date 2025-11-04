-- ============================================================================
-- Memori v1.x to v2.0 Migration Script (PostgreSQL)
-- ============================================================================
-- Purpose: Migrate from namespace-based isolation to multi-tenant architecture
-- Author: Memori Team
-- Date: 2025-10-27
-- Database: PostgreSQL 12+
--
-- IMPORTANT: BACKUP YOUR DATABASE BEFORE RUNNING THIS MIGRATION!
-- Command: pg_dump your_database > backup_$(date +%Y%m%d_%H%M%S).sql
-- ============================================================================

-- Start transaction for atomic migration
BEGIN;

-- ============================================================================
-- STEP 1: Pre-Migration Validation
-- ============================================================================

DO $$
DECLARE
    chat_count INTEGER;
    stm_count INTEGER;
    ltm_count INTEGER;
BEGIN
    -- Check if tables exist
    SELECT COUNT(*) INTO chat_count FROM chat_history LIMIT 1;
    SELECT COUNT(*) INTO stm_count FROM short_term_memory LIMIT 1;
    SELECT COUNT(*) INTO ltm_count FROM long_term_memory LIMIT 1;

    RAISE NOTICE 'Pre-migration record counts:';
    RAISE NOTICE '  - chat_history: %', chat_count;
    RAISE NOTICE '  - short_term_memory: %', stm_count;
    RAISE NOTICE '  - long_term_memory: %', ltm_count;
END $$;

-- ============================================================================
-- STEP 2: Add New Multi-Tenant Columns
-- ============================================================================

-- Add user_id columns (primary tenant isolation field)
ALTER TABLE chat_history ADD COLUMN IF NOT EXISTS user_id TEXT;
ALTER TABLE short_term_memory ADD COLUMN IF NOT EXISTS user_id TEXT;
ALTER TABLE long_term_memory ADD COLUMN IF NOT EXISTS user_id TEXT;

-- Add assistant_id columns (optional bot/assistant isolation)
ALTER TABLE chat_history ADD COLUMN IF NOT EXISTS assistant_id TEXT;
ALTER TABLE short_term_memory ADD COLUMN IF NOT EXISTS assistant_id TEXT;
ALTER TABLE long_term_memory ADD COLUMN IF NOT EXISTS assistant_id TEXT;

-- Add session_id for long_term_memory if it doesn't exist
ALTER TABLE long_term_memory ADD COLUMN IF NOT EXISTS session_id TEXT;

-- Add version column for optimistic locking (prevents race conditions)
ALTER TABLE long_term_memory ADD COLUMN IF NOT EXISTS version INTEGER DEFAULT 1;

RAISE NOTICE 'Step 2 complete: Added new columns';

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

RAISE NOTICE 'Step 3 complete: Migrated namespace data to user_id';

-- ============================================================================
-- STEP 4: Handle session_id NULL Values
-- ============================================================================

-- Set default session_id for existing NULL values
UPDATE long_term_memory
SET session_id = 'default'
WHERE session_id IS NULL;

-- Set default session_id for short_term_memory if NULL
UPDATE short_term_memory
SET session_id = 'default'
WHERE session_id IS NULL;

RAISE NOTICE 'Step 4 complete: Fixed NULL session_id values';

-- ============================================================================
-- STEP 5: Add NOT NULL Constraints
-- ============================================================================

-- Make user_id NOT NULL (required for multi-tenant isolation)
ALTER TABLE chat_history ALTER COLUMN user_id SET NOT NULL;
ALTER TABLE chat_history ALTER COLUMN user_id SET DEFAULT 'default';

ALTER TABLE short_term_memory ALTER COLUMN user_id SET NOT NULL;
ALTER TABLE short_term_memory ALTER COLUMN user_id SET DEFAULT 'default';

ALTER TABLE long_term_memory ALTER COLUMN user_id SET NOT NULL;
ALTER TABLE long_term_memory ALTER COLUMN user_id SET DEFAULT 'default';

-- Make session_id NOT NULL for data consistency
ALTER TABLE long_term_memory ALTER COLUMN session_id SET NOT NULL;
ALTER TABLE long_term_memory ALTER COLUMN session_id SET DEFAULT 'default';

-- Ensure version is NOT NULL
ALTER TABLE long_term_memory ALTER COLUMN version SET NOT NULL;

RAISE NOTICE 'Step 5 complete: Added NOT NULL constraints';

-- ============================================================================
-- STEP 6: Create Multi-Tenant Indexes
-- ============================================================================

-- Chat History Indexes
CREATE INDEX IF NOT EXISTS idx_chat_user_id ON chat_history(user_id);
CREATE INDEX IF NOT EXISTS idx_chat_user_assistant ON chat_history(user_id, assistant_id);
CREATE INDEX IF NOT EXISTS idx_chat_user_session_time ON chat_history(user_id, session_id, created_at DESC);

-- Short-Term Memory Indexes
CREATE INDEX IF NOT EXISTS idx_short_term_user_id ON short_term_memory(user_id);
CREATE INDEX IF NOT EXISTS idx_short_term_user_assistant ON short_term_memory(user_id, assistant_id);
CREATE INDEX IF NOT EXISTS idx_short_term_user_category ON short_term_memory(user_id, category_primary);
CREATE INDEX IF NOT EXISTS idx_short_term_user_session ON short_term_memory(user_id, session_id);

-- Long-Term Memory Indexes
CREATE INDEX IF NOT EXISTS idx_long_term_user_id ON long_term_memory(user_id);
CREATE INDEX IF NOT EXISTS idx_long_term_user_assistant ON long_term_memory(user_id, assistant_id);
CREATE INDEX IF NOT EXISTS idx_long_term_user_session ON long_term_memory(user_id, session_id);
CREATE INDEX IF NOT EXISTS idx_long_term_version ON long_term_memory(memory_id, version);

RAISE NOTICE 'Step 6 complete: Created multi-tenant indexes';

-- ============================================================================
-- STEP 7: Rename Old Columns (Keep for Rollback Capability)
-- ============================================================================

-- Rename namespace columns instead of dropping them (safer for rollback)
ALTER TABLE chat_history RENAME COLUMN namespace TO namespace_legacy;
ALTER TABLE short_term_memory RENAME COLUMN namespace TO namespace_legacy;
ALTER TABLE long_term_memory RENAME COLUMN namespace TO namespace_legacy;

RAISE NOTICE 'Step 7 complete: Renamed namespace columns to namespace_legacy';

-- ============================================================================
-- STEP 8: Update FTS (Full-Text Search) Triggers for PostgreSQL
-- ============================================================================

-- Note: PostgreSQL uses tsvector for FTS, not FTS5 like SQLite
-- These triggers ensure searchable_content is kept in sync

-- Drop old triggers if they exist
DROP TRIGGER IF EXISTS update_short_term_search_vector ON short_term_memory;
DROP TRIGGER IF EXISTS update_long_term_search_vector ON long_term_memory;

-- Create function for updating tsvector
CREATE OR REPLACE FUNCTION update_search_vector()
RETURNS TRIGGER AS $$
BEGIN
    NEW.search_vector := to_tsvector('english',
        COALESCE(NEW.searchable_content, '') || ' ' ||
        COALESCE(NEW.summary, '')
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create triggers (if search_vector column exists)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns
               WHERE table_name = 'short_term_memory' AND column_name = 'search_vector') THEN
        CREATE TRIGGER update_short_term_search_vector
        BEFORE INSERT OR UPDATE ON short_term_memory
        FOR EACH ROW EXECUTE FUNCTION update_search_vector();
    END IF;

    IF EXISTS (SELECT 1 FROM information_schema.columns
               WHERE table_name = 'long_term_memory' AND column_name = 'search_vector') THEN
        CREATE TRIGGER update_long_term_search_vector
        BEFORE INSERT OR UPDATE ON long_term_memory
        FOR EACH ROW EXECUTE FUNCTION update_search_vector();
    END IF;
END $$;

RAISE NOTICE 'Step 8 complete: Updated FTS triggers';

-- ============================================================================
-- STEP 9: Post-Migration Validation
-- ============================================================================

DO $$
DECLARE
    chat_null_users INTEGER;
    stm_null_users INTEGER;
    ltm_null_users INTEGER;
    ltm_null_sessions INTEGER;
BEGIN
    -- Check for any NULL user_id values (should be 0)
    SELECT COUNT(*) INTO chat_null_users FROM chat_history WHERE user_id IS NULL;
    SELECT COUNT(*) INTO stm_null_users FROM short_term_memory WHERE user_id IS NULL;
    SELECT COUNT(*) INTO ltm_null_users FROM long_term_memory WHERE user_id IS NULL;
    SELECT COUNT(*) INTO ltm_null_sessions FROM long_term_memory WHERE session_id IS NULL;

    IF chat_null_users > 0 OR stm_null_users > 0 OR ltm_null_users > 0 OR ltm_null_sessions > 0 THEN
        RAISE EXCEPTION 'Migration validation failed! Found NULL values in required fields.';
    END IF;

    RAISE NOTICE 'Step 9 complete: Post-migration validation passed';
END $$;

-- ============================================================================
-- STEP 10: Generate Migration Report
-- ============================================================================

DO $$
DECLARE
    rec RECORD;
BEGIN
    RAISE NOTICE '========================================';
    RAISE NOTICE 'MIGRATION COMPLETED SUCCESSFULLY';
    RAISE NOTICE '========================================';
    RAISE NOTICE '';
    RAISE NOTICE 'Post-migration statistics:';

    -- Chat history stats
    FOR rec IN SELECT user_id, COUNT(*) as count FROM chat_history GROUP BY user_id LOOP
        RAISE NOTICE 'chat_history - user_id: %, count: %', rec.user_id, rec.count;
    END LOOP;

    -- Short-term memory stats
    FOR rec IN SELECT user_id, COUNT(*) as count FROM short_term_memory GROUP BY user_id LOOP
        RAISE NOTICE 'short_term_memory - user_id: %, count: %', rec.user_id, rec.count;
    END LOOP;

    -- Long-term memory stats
    FOR rec IN SELECT user_id, COUNT(*) as count FROM long_term_memory GROUP BY user_id LOOP
        RAISE NOTICE 'long_term_memory - user_id: %, count: %', rec.user_id, rec.count;
    END LOOP;

    RAISE NOTICE '';
    RAISE NOTICE 'IMPORTANT: Keep namespace_legacy columns for now (needed for rollback)';
    RAISE NOTICE 'After confirming the migration works, you can drop them with:';
    RAISE NOTICE '  ALTER TABLE chat_history DROP COLUMN namespace_legacy;';
    RAISE NOTICE '  ALTER TABLE short_term_memory DROP COLUMN namespace_legacy;';
    RAISE NOTICE '  ALTER TABLE long_term_memory DROP COLUMN namespace_legacy;';
    RAISE NOTICE '';
    RAISE NOTICE 'To rollback this migration, run: rollback_v2_to_v1_postgresql.sql';
END $$;

-- Commit transaction
COMMIT;

RAISE NOTICE 'Migration transaction committed successfully!';
