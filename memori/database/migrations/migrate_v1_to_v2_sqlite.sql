-- ============================================================================
-- Memori v1.x to v2.0 Migration Script (SQLite)
-- ============================================================================
-- Purpose: Migrate from namespace-based isolation to multi-tenant architecture
-- Author: Memori Team
-- Date: 2025-10-27
-- Database: SQLite 3.x
--
-- IMPORTANT: BACKUP YOUR DATABASE BEFORE RUNNING THIS MIGRATION!
-- Command: sqlite3 your_database.db ".backup backup_$(date +%Y%m%d_%H%M%S).db"
--
-- NOTE: SQLite has limited ALTER TABLE support, so we use table recreation
-- ============================================================================

-- Start transaction for atomic migration
BEGIN TRANSACTION;

-- ============================================================================
-- STEP 1: Pre-Migration Validation
-- ============================================================================

SELECT '==============================================';
SELECT 'Pre-migration record counts:';
SELECT 'chat_history:', COUNT(*) FROM chat_history;
SELECT 'short_term_memory:', COUNT(*) FROM short_term_memory;
SELECT 'long_term_memory:', COUNT(*) FROM long_term_memory;

-- ============================================================================
-- STEP 2: Migrate chat_history Table
-- ============================================================================

-- Create new chat_history table with multi-tenant columns
-- This matches the ChatHistory model in memori/database/models.py
CREATE TABLE chat_history_new (
    chat_id TEXT PRIMARY KEY,
    user_input TEXT NOT NULL,
    ai_output TEXT NOT NULL,
    model TEXT NOT NULL,
    session_id TEXT NOT NULL DEFAULT 'default',
    tokens_used INTEGER DEFAULT 0,
    metadata_json TEXT,
    user_id TEXT NOT NULL DEFAULT 'default',
    assistant_id TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    namespace_legacy TEXT  -- Keep for rollback
);

-- Copy data from old to new table (namespace -> user_id)
-- Assuming old table has columns: chat_id, user_input, ai_output, model, session_id, tokens_used, metadata_json, namespace, created_at
INSERT INTO chat_history_new (chat_id, user_input, ai_output, model, session_id, tokens_used, metadata_json, user_id, assistant_id, created_at, updated_at, namespace_legacy)
SELECT
    chat_id,
    user_input,
    ai_output,
    model,
    COALESCE(session_id, 'default') AS session_id,
    COALESCE(tokens_used, 0) AS tokens_used,
    metadata_json,
    COALESCE(namespace, 'default') AS user_id,
    NULL AS assistant_id,
    created_at,
    COALESCE(updated_at, created_at) AS updated_at,
    namespace AS namespace_legacy
FROM chat_history;

-- Drop old table and rename new table
DROP TABLE chat_history;
ALTER TABLE chat_history_new RENAME TO chat_history;

-- Recreate indexes for chat_history (matching models.py)
CREATE INDEX idx_chat_user_id ON chat_history(user_id);
CREATE INDEX idx_chat_user_assistant ON chat_history(user_id, assistant_id);
CREATE INDEX idx_chat_created ON chat_history(created_at);
CREATE INDEX idx_chat_model ON chat_history(model);

SELECT 'Step 2 complete: Migrated chat_history table';

-- ============================================================================
-- STEP 3: Migrate short_term_memory Table
-- ============================================================================

-- Create new short_term_memory table with multi-tenant columns
CREATE TABLE short_term_memory_new (
    memory_id TEXT PRIMARY KEY,
    processed_data TEXT NOT NULL,
    importance_score REAL NOT NULL DEFAULT 0.5,
    category_primary TEXT NOT NULL,
    retention_type TEXT NOT NULL DEFAULT 'short_term',
    user_id TEXT NOT NULL DEFAULT 'default',
    assistant_id TEXT,
    session_id TEXT NOT NULL DEFAULT 'default',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    searchable_content TEXT NOT NULL,
    summary TEXT NOT NULL,
    is_permanent_context BOOLEAN DEFAULT 0,
    namespace_legacy TEXT  -- Keep for rollback
);

-- Copy data from old to new table (namespace -> user_id)
INSERT INTO short_term_memory_new
SELECT
    memory_id,
    processed_data,
    importance_score,
    category_primary,
    retention_type,
    COALESCE(namespace, 'default') AS user_id,
    NULL AS assistant_id,
    COALESCE(session_id, 'default') AS session_id,
    created_at,
    expires_at,
    searchable_content,
    summary,
    is_permanent_context,
    namespace AS namespace_legacy
FROM short_term_memory;

-- Drop old table and rename new table
DROP TABLE short_term_memory;
ALTER TABLE short_term_memory_new RENAME TO short_term_memory;

-- Recreate indexes for short_term_memory
CREATE INDEX idx_short_term_category ON short_term_memory(category_primary);
CREATE INDEX idx_short_term_importance ON short_term_memory(importance_score);
CREATE INDEX idx_short_term_retention ON short_term_memory(retention_type);
CREATE INDEX idx_short_term_expires ON short_term_memory(expires_at);
CREATE INDEX idx_short_term_session ON short_term_memory(session_id);
CREATE INDEX idx_short_term_user_id ON short_term_memory(user_id);
CREATE INDEX idx_short_term_user_assistant ON short_term_memory(user_id, assistant_id);
CREATE INDEX idx_short_term_user_category ON short_term_memory(user_id, category_primary);
CREATE INDEX idx_short_term_user_session ON short_term_memory(user_id, session_id);

-- Recreate FTS5 virtual table for full-text search
DROP TABLE IF EXISTS short_term_memory_fts;
CREATE VIRTUAL TABLE short_term_memory_fts USING fts5(
    memory_id UNINDEXED,
    searchable_content,
    summary,
    user_id UNINDEXED,
    assistant_id UNINDEXED,
    session_id UNINDEXED,
    content=short_term_memory,
    content_rowid=rowid
);

-- Populate FTS5 table
INSERT INTO short_term_memory_fts(rowid, memory_id, searchable_content, summary, user_id, assistant_id, session_id)
SELECT rowid, memory_id, searchable_content, summary, user_id, assistant_id, session_id
FROM short_term_memory;

-- Create triggers to keep FTS5 in sync
CREATE TRIGGER short_term_memory_ai AFTER INSERT ON short_term_memory BEGIN
    INSERT INTO short_term_memory_fts(rowid, memory_id, searchable_content, summary, user_id, assistant_id, session_id)
    VALUES (new.rowid, new.memory_id, new.searchable_content, new.summary, new.user_id, new.assistant_id, new.session_id);
END;

CREATE TRIGGER short_term_memory_ad AFTER DELETE ON short_term_memory BEGIN
    DELETE FROM short_term_memory_fts WHERE rowid = old.rowid;
END;

CREATE TRIGGER short_term_memory_au AFTER UPDATE ON short_term_memory BEGIN
    DELETE FROM short_term_memory_fts WHERE rowid = old.rowid;
    INSERT INTO short_term_memory_fts(rowid, memory_id, searchable_content, summary, user_id, assistant_id, session_id)
    VALUES (new.rowid, new.memory_id, new.searchable_content, new.summary, new.user_id, new.assistant_id, new.session_id);
END;

SELECT 'Step 3 complete: Migrated short_term_memory table with FTS5';

-- ============================================================================
-- STEP 4: Migrate long_term_memory Table
-- ============================================================================

-- Create new long_term_memory table with multi-tenant columns and version
CREATE TABLE long_term_memory_new (
    memory_id TEXT PRIMARY KEY,
    processed_data TEXT NOT NULL,
    importance_score REAL NOT NULL DEFAULT 0.5,
    category_primary TEXT NOT NULL,
    retention_type TEXT NOT NULL DEFAULT 'long_term',
    user_id TEXT NOT NULL DEFAULT 'default',
    assistant_id TEXT,
    session_id TEXT NOT NULL DEFAULT 'default',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    searchable_content TEXT NOT NULL,
    summary TEXT NOT NULL,
    novelty_score REAL DEFAULT 0.5,
    relevance_score REAL DEFAULT 0.5,
    actionability_score REAL DEFAULT 0.5,
    classification TEXT NOT NULL DEFAULT 'conversational',
    memory_importance TEXT NOT NULL DEFAULT 'medium',
    topic TEXT,
    entities_json TEXT,
    keywords_json TEXT,
    is_user_context BOOLEAN DEFAULT 0,
    is_preference BOOLEAN DEFAULT 0,
    is_skill_knowledge BOOLEAN DEFAULT 0,
    is_current_project BOOLEAN DEFAULT 0,
    promotion_eligible BOOLEAN DEFAULT 0,
    duplicate_of TEXT,
    supersedes_json TEXT,
    related_memories_json TEXT,
    confidence_score REAL DEFAULT 0.8,
    classification_reason TEXT,
    processed_for_duplicates BOOLEAN DEFAULT 0,
    conscious_processed BOOLEAN DEFAULT 0,
    version INTEGER NOT NULL DEFAULT 1,
    namespace_legacy TEXT  -- Keep for rollback
);

-- Copy data from old to new table (namespace -> user_id)
-- NOTE: session_id may not exist in v1.x long_term_memory, so we use static default
INSERT INTO long_term_memory_new
SELECT
    memory_id,
    processed_data,
    importance_score,
    category_primary,
    retention_type,
    COALESCE(namespace, 'default') AS user_id,
    NULL AS assistant_id,
    'default' AS session_id,
    created_at,
    searchable_content,
    summary,
    novelty_score,
    relevance_score,
    actionability_score,
    classification,
    memory_importance,
    topic,
    entities_json,
    keywords_json,
    is_user_context,
    is_preference,
    is_skill_knowledge,
    is_current_project,
    promotion_eligible,
    duplicate_of,
    supersedes_json,
    related_memories_json,
    confidence_score,
    classification_reason,
    processed_for_duplicates,
    conscious_processed,
    1 AS version,  -- Initialize version to 1
    namespace AS namespace_legacy
FROM long_term_memory;

-- Drop old table and rename new table
DROP TABLE long_term_memory;
ALTER TABLE long_term_memory_new RENAME TO long_term_memory;

-- Recreate indexes for long_term_memory
CREATE INDEX idx_long_term_category ON long_term_memory(category_primary);
CREATE INDEX idx_long_term_importance ON long_term_memory(importance_score);
CREATE INDEX idx_long_term_classification ON long_term_memory(classification);
CREATE INDEX idx_long_term_duplicate ON long_term_memory(duplicate_of);
CREATE INDEX idx_long_term_user_id ON long_term_memory(user_id);
CREATE INDEX idx_long_term_user_assistant ON long_term_memory(user_id, assistant_id);
CREATE INDEX idx_long_term_user_session ON long_term_memory(user_id, session_id);
CREATE INDEX idx_long_term_version ON long_term_memory(memory_id, version);

-- Recreate FTS5 virtual table for full-text search
DROP TABLE IF EXISTS long_term_memory_fts;
CREATE VIRTUAL TABLE long_term_memory_fts USING fts5(
    memory_id UNINDEXED,
    searchable_content,
    summary,
    user_id UNINDEXED,
    assistant_id UNINDEXED,
    session_id UNINDEXED,
    content=long_term_memory,
    content_rowid=rowid
);

-- Populate FTS5 table
INSERT INTO long_term_memory_fts(rowid, memory_id, searchable_content, summary, user_id, assistant_id, session_id)
SELECT rowid, memory_id, searchable_content, summary, user_id, assistant_id, session_id
FROM long_term_memory;

-- Create triggers to keep FTS5 in sync
CREATE TRIGGER long_term_memory_ai AFTER INSERT ON long_term_memory BEGIN
    INSERT INTO long_term_memory_fts(rowid, memory_id, searchable_content, summary, user_id, assistant_id, session_id)
    VALUES (new.rowid, new.memory_id, new.searchable_content, new.summary, new.user_id, new.assistant_id, new.session_id);
END;

CREATE TRIGGER long_term_memory_ad AFTER DELETE ON long_term_memory BEGIN
    DELETE FROM long_term_memory_fts WHERE rowid = old.rowid;
END;

CREATE TRIGGER long_term_memory_au AFTER UPDATE ON long_term_memory BEGIN
    DELETE FROM long_term_memory_fts WHERE rowid = old.rowid;
    INSERT INTO long_term_memory_fts(rowid, memory_id, searchable_content, summary, user_id, assistant_id, session_id)
    VALUES (new.rowid, new.memory_id, new.searchable_content, new.summary, new.user_id, new.assistant_id, new.session_id);
END;

SELECT 'Step 4 complete: Migrated long_term_memory table with FTS5 and version column';

-- ============================================================================
-- STEP 5: Post-Migration Validation
-- ============================================================================

SELECT '==============================================';
SELECT 'Post-migration validation:';

-- Check for any NULL user_id values (should be 0)
SELECT 'Checking for NULL user_id in chat_history:', COUNT(*) FROM chat_history WHERE user_id IS NULL;
SELECT 'Checking for NULL user_id in short_term_memory:', COUNT(*) FROM short_term_memory WHERE user_id IS NULL;
SELECT 'Checking for NULL user_id in long_term_memory:', COUNT(*) FROM long_term_memory WHERE user_id IS NULL;
SELECT 'Checking for NULL session_id in long_term_memory:', COUNT(*) FROM long_term_memory WHERE session_id IS NULL;

-- ============================================================================
-- STEP 6: Generate Migration Report
-- ============================================================================

SELECT '==============================================';
SELECT 'MIGRATION COMPLETED SUCCESSFULLY';
SELECT '==============================================';
SELECT '';
SELECT 'Post-migration statistics:';

-- Chat history stats by user
SELECT 'chat_history', user_id, COUNT(*) AS count FROM chat_history GROUP BY user_id;

-- Short-term memory stats by user
SELECT 'short_term_memory', user_id, COUNT(*) AS count FROM short_term_memory GROUP BY user_id;

-- Long-term memory stats by user
SELECT 'long_term_memory', user_id, COUNT(*) AS count FROM long_term_memory GROUP BY user_id;

SELECT '';
SELECT 'IMPORTANT: Keep namespace_legacy columns for now (needed for rollback)';
SELECT 'After confirming the migration works, you can recreate tables without namespace_legacy';
SELECT '';
SELECT 'To rollback this migration, restore from backup:';
SELECT '  cp backup_YYYYMMDD_HHMMSS.db your_database.db';

-- Commit transaction
COMMIT;

SELECT 'Migration transaction committed successfully!';
