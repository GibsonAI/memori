"""
Base database queries and schema operations
"""

from abc import ABC, abstractmethod


class BaseQueries(ABC):
    """Abstract base class for database queries"""

    @abstractmethod
    def get_table_creation_queries(self) -> dict[str, str]:
        """Return dictionary of table creation SQL statements"""
        pass

    @abstractmethod
    def get_index_creation_queries(self) -> dict[str, str]:
        """Return dictionary of index creation SQL statements"""
        pass

    @abstractmethod
    def get_trigger_creation_queries(self) -> dict[str, str]:
        """Return dictionary of trigger creation SQL statements"""
        pass


class SchemaQueries:
    """Schema management queries"""

    TABLE_CREATION = {
        "chat_history": """
            CREATE TABLE IF NOT EXISTS chat_history (
                chat_id TEXT PRIMARY KEY,
                user_input TEXT NOT NULL,
                ai_output TEXT NOT NULL,
                model TEXT NOT NULL,
                timestamp TIMESTAMP NOT NULL,
                session_id TEXT NOT NULL,
                namespace TEXT NOT NULL DEFAULT 'default',
                tokens_used INTEGER DEFAULT 0,
                metadata TEXT DEFAULT '{}'
            )
        """,
        "short_term_memory": """
            CREATE TABLE IF NOT EXISTS short_term_memory (
                memory_id TEXT PRIMARY KEY,
                chat_id TEXT,
                processed_data TEXT NOT NULL,
                importance_score REAL NOT NULL DEFAULT 0.5,
                category_primary TEXT NOT NULL,
                retention_type TEXT NOT NULL DEFAULT 'short_term',
                namespace TEXT NOT NULL DEFAULT 'default',
                created_at TIMESTAMP NOT NULL,
                expires_at TIMESTAMP,
                access_count INTEGER DEFAULT 0,
                last_accessed TIMESTAMP,
                searchable_content TEXT NOT NULL,
                summary TEXT NOT NULL,
                FOREIGN KEY (chat_id) REFERENCES chat_history (chat_id)
            )
        """,
        "long_term_memory": """
            CREATE TABLE IF NOT EXISTS long_term_memory (
                memory_id TEXT PRIMARY KEY,
                original_chat_id TEXT,
                processed_data TEXT NOT NULL,
                importance_score REAL NOT NULL DEFAULT 0.5,
                category_primary TEXT NOT NULL,
                retention_type TEXT NOT NULL DEFAULT 'long_term',
                namespace TEXT NOT NULL DEFAULT 'default',
                created_at TIMESTAMP NOT NULL,
                access_count INTEGER DEFAULT 0,
                last_accessed TIMESTAMP,
                searchable_content TEXT NOT NULL,
                summary TEXT NOT NULL,
                novelty_score REAL DEFAULT 0.5,
                relevance_score REAL DEFAULT 0.5,
                actionability_score REAL DEFAULT 0.5
            )
        """,
        # REMOVED: Graph search tables simplified - entities/relationships stored as JSON
        # "rules_memory": """
        #     CREATE TABLE IF NOT EXISTS rules_memory (
        #         rule_id TEXT PRIMARY KEY,
        #         rule_text TEXT NOT NULL,
        #         rule_type TEXT NOT NULL,
        #         priority INTEGER DEFAULT 5,
        #         active BOOLEAN DEFAULT TRUE,
        #         context_conditions TEXT,
        #         namespace TEXT NOT NULL DEFAULT 'default',
        #         created_at TIMESTAMP NOT NULL,
        #         updated_at TIMESTAMP NOT NULL,
        #         processed_data TEXT,
        #         metadata TEXT DEFAULT '{}'
        #     )
        # """,
        # "memory_entities": """
        #     CREATE TABLE IF NOT EXISTS memory_entities (
        #         entity_id TEXT PRIMARY KEY,
        #         memory_id TEXT NOT NULL,
        #         memory_type TEXT NOT NULL,
        #         entity_type TEXT NOT NULL,
        #         entity_value TEXT NOT NULL,
        #         relevance_score REAL NOT NULL DEFAULT 0.5,
        #         entity_context TEXT,
        #         namespace TEXT NOT NULL DEFAULT 'default',
        #         created_at TIMESTAMP NOT NULL
        #     )
        # """,
        # "memory_relationships": """
        #     CREATE TABLE IF NOT EXISTS memory_relationships (
        #         relationship_id TEXT PRIMARY KEY,
        #         source_memory_id TEXT NOT NULL,
        #         target_memory_id TEXT NOT NULL,
        #         relationship_type TEXT NOT NULL,
        #         strength REAL NOT NULL DEFAULT 0.5,
        #         reasoning TEXT,
        #         namespace TEXT NOT NULL DEFAULT 'default',
        #         created_at TIMESTAMP NOT NULL
        #     )
        # """,
        "memory_search_fts": """
            CREATE VIRTUAL TABLE IF NOT EXISTS memory_search_fts USING fts5(
                memory_id,
                memory_type,
                namespace,
                searchable_content,
                summary,
                category_primary,
                content='',
                contentless_delete=1
            )
        """,
    }

    INDEX_CREATION = {
        # Chat History Indexes
        "idx_chat_namespace_session": "CREATE INDEX IF NOT EXISTS idx_chat_namespace_session ON chat_history(namespace, session_id)",
        "idx_chat_timestamp": "CREATE INDEX IF NOT EXISTS idx_chat_timestamp ON chat_history(timestamp)",
        "idx_chat_model": "CREATE INDEX IF NOT EXISTS idx_chat_model ON chat_history(model)",
        # Short-term Memory Indexes
        "idx_short_term_namespace": "CREATE INDEX IF NOT EXISTS idx_short_term_namespace ON short_term_memory(namespace)",
        "idx_short_term_category": "CREATE INDEX IF NOT EXISTS idx_short_term_category ON short_term_memory(category_primary)",
        "idx_short_term_importance": "CREATE INDEX IF NOT EXISTS idx_short_term_importance ON short_term_memory(importance_score)",
        "idx_short_term_expires": "CREATE INDEX IF NOT EXISTS idx_short_term_expires ON short_term_memory(expires_at)",
        "idx_short_term_created": "CREATE INDEX IF NOT EXISTS idx_short_term_created ON short_term_memory(created_at)",
        "idx_short_term_searchable": "CREATE INDEX IF NOT EXISTS idx_short_term_searchable ON short_term_memory(searchable_content)",
        "idx_short_term_access": "CREATE INDEX IF NOT EXISTS idx_short_term_access ON short_term_memory(access_count, last_accessed)",
        # Long-term Memory Indexes
        "idx_long_term_namespace": "CREATE INDEX IF NOT EXISTS idx_long_term_namespace ON long_term_memory(namespace)",
        "idx_long_term_category": "CREATE INDEX IF NOT EXISTS idx_long_term_category ON long_term_memory(category_primary)",
        "idx_long_term_importance": "CREATE INDEX IF NOT EXISTS idx_long_term_importance ON long_term_memory(importance_score)",
        "idx_long_term_created": "CREATE INDEX IF NOT EXISTS idx_long_term_created ON long_term_memory(created_at)",
        "idx_long_term_searchable": "CREATE INDEX IF NOT EXISTS idx_long_term_searchable ON long_term_memory(searchable_content)",
        "idx_long_term_access": "CREATE INDEX IF NOT EXISTS idx_long_term_access ON long_term_memory(access_count, last_accessed)",
        "idx_long_term_scores": "CREATE INDEX IF NOT EXISTS idx_long_term_scores ON long_term_memory(novelty_score, relevance_score, actionability_score)",
        # REMOVED: Graph search indexes - tables simplified
        # # Rules Memory Indexes
        # "idx_rules_namespace": "CREATE INDEX IF NOT EXISTS idx_rules_namespace ON rules_memory(namespace)",
        # "idx_rules_active": "CREATE INDEX IF NOT EXISTS idx_rules_active ON rules_memory(active)",
        # "idx_rules_priority": "CREATE INDEX IF NOT EXISTS idx_rules_priority ON rules_memory(priority)",
        # "idx_rules_type": "CREATE INDEX IF NOT EXISTS idx_rules_type ON rules_memory(rule_type)",
        # "idx_rules_updated": "CREATE INDEX IF NOT EXISTS idx_rules_updated ON rules_memory(updated_at)",
        # # Entity Indexes
        # "idx_entities_namespace": "CREATE INDEX IF NOT EXISTS idx_entities_namespace ON memory_entities(namespace)",
        # "idx_entities_type": "CREATE INDEX IF NOT EXISTS idx_entities_type ON memory_entities(entity_type)",
        # "idx_entities_value": "CREATE INDEX IF NOT EXISTS idx_entities_value ON memory_entities(entity_value)",
        # "idx_entities_memory": "CREATE INDEX IF NOT EXISTS idx_entities_memory ON memory_entities(memory_id, memory_type)",
        # "idx_entities_relevance": "CREATE INDEX IF NOT EXISTS idx_entities_relevance ON memory_entities(relevance_score)",
        # "idx_entities_value_type": "CREATE INDEX IF NOT EXISTS idx_entities_value_type ON memory_entities(entity_value, entity_type)",
        # # Relationship Indexes
        # "idx_relationships_source": "CREATE INDEX IF NOT EXISTS idx_relationships_source ON memory_relationships(source_memory_id)",
        # "idx_relationships_target": "CREATE INDEX IF NOT EXISTS idx_relationships_target ON memory_relationships(target_memory_id)",
        # "idx_relationships_type": "CREATE INDEX IF NOT EXISTS idx_relationships_type ON memory_relationships(relationship_type)",
        # "idx_relationships_strength": "CREATE INDEX IF NOT EXISTS idx_relationships_strength ON memory_relationships(strength)",
    }

    TRIGGER_CREATION = {
        "short_term_memory_fts_insert": """
            CREATE TRIGGER IF NOT EXISTS short_term_memory_fts_insert AFTER INSERT ON short_term_memory
            BEGIN
                INSERT INTO memory_search_fts(memory_id, memory_type, namespace, searchable_content, summary, category_primary)
                VALUES (NEW.memory_id, 'short_term', NEW.namespace, NEW.searchable_content, NEW.summary, NEW.category_primary);
            END
        """,
        "long_term_memory_fts_insert": """
            CREATE TRIGGER IF NOT EXISTS long_term_memory_fts_insert AFTER INSERT ON long_term_memory
            BEGIN
                INSERT INTO memory_search_fts(memory_id, memory_type, namespace, searchable_content, summary, category_primary)
                VALUES (NEW.memory_id, 'long_term', NEW.namespace, NEW.searchable_content, NEW.summary, NEW.category_primary);
            END
        """,
        "short_term_memory_fts_delete": """
            CREATE TRIGGER IF NOT EXISTS short_term_memory_fts_delete AFTER DELETE ON short_term_memory
            BEGIN
                DELETE FROM memory_search_fts WHERE memory_id = OLD.memory_id AND memory_type = 'short_term';
            END
        """,
        "long_term_memory_fts_delete": """
            CREATE TRIGGER IF NOT EXISTS long_term_memory_fts_delete AFTER DELETE ON long_term_memory
            BEGIN
                DELETE FROM memory_search_fts WHERE memory_id = OLD.memory_id AND memory_type = 'long_term';
            END
        """,
    }
