"""
SQLite FTS5 search adapter for Memori
Maintains existing FTS5 functionality
"""

import sqlite3
from typing import Any

from loguru import logger

from ..connectors.base_connector import BaseDatabaseConnector, BaseSearchAdapter


class SQLiteSearchAdapter(BaseSearchAdapter):
    """SQLite-specific search adapter with FTS5 support"""

    def __init__(self, connector: BaseDatabaseConnector):
        super().__init__(connector)
        self.fts5_available = self._check_fts5_support()

    def _check_fts5_support(self) -> bool:
        """Check if FTS5 is supported in this SQLite installation"""
        try:
            with self.connector.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("CREATE VIRTUAL TABLE fts_test USING fts5(content)")
                cursor.execute("DROP TABLE fts_test")
                return True
        except sqlite3.OperationalError:
            logger.warning("FTS5 not available, falling back to LIKE searches")
            return False

    def execute_fulltext_search(
        self,
        query: str,
        namespace: str = "default",
        category_filter: list[str] | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Execute FTS5 search or fallback to LIKE search"""
        if self.fts5_available:
            try:
                return self._execute_fts5_search(
                    query, namespace, category_filter, limit
                )
            except sqlite3.OperationalError as e:
                logger.debug(f"FTS5 search failed: {e}, falling back to LIKE search")

        # Fallback to LIKE search
        return self.execute_fallback_search(query, namespace, category_filter, limit)

    def _execute_fts5_search(
        self,
        query: str,
        namespace: str,
        category_filter: list[str] | None,
        limit: int,
    ) -> list[dict[str, Any]]:
        """Execute FTS5 search (adapted from original implementation)"""
        # Build FTS query with category filter - handle empty queries
        if query and query.strip():
            fts_query = f'"{query.strip()}"'
        else:
            # Use a simple match-all query for empty searches
            fts_query = "*"

        category_clause = ""
        params = [fts_query, namespace]

        if category_filter:
            category_placeholders = ",".join("?" * len(category_filter))
            category_clause = (
                "AND fts.category_primary IN (" + category_placeholders + ")"
            )
            params.extend(category_filter)

        params.append(limit)

        base_query = """
            SELECT
                fts.memory_id, fts.memory_type, fts.category_primary,
                CASE
                    WHEN fts.memory_type = 'short_term' THEN st.processed_data
                    WHEN fts.memory_type = 'long_term' THEN lt.processed_data
                END as processed_data,
                CASE
                    WHEN fts.memory_type = 'short_term' THEN st.importance_score
                    WHEN fts.memory_type = 'long_term' THEN lt.importance_score
                    ELSE 0.5
                END as importance_score,
                CASE
                    WHEN fts.memory_type = 'short_term' THEN st.created_at
                    WHEN fts.memory_type = 'long_term' THEN lt.created_at
                END as created_at,
                fts.summary,
                rank,
                'fts5_search' as search_strategy
            FROM memory_search_fts fts
            LEFT JOIN short_term_memory st ON fts.memory_id = st.memory_id AND fts.memory_type = 'short_term'
            LEFT JOIN long_term_memory lt ON fts.memory_id = lt.memory_id AND fts.memory_type = 'long_term'
            WHERE memory_search_fts MATCH ? AND fts.namespace = ?"""

        if category_clause:
            sql_query = (
                base_query
                + " "
                + category_clause
                + """
            ORDER BY rank, importance_score DESC
            LIMIT ?"""
            )
        else:
            sql_query = (
                base_query
                + """
            ORDER BY rank, importance_score DESC
            LIMIT ?"""
            )

        return self.connector.execute_query(sql_query, params)

    def create_search_indexes(self) -> list[str]:
        """Create FTS5 virtual table and triggers"""
        if not self.fts5_available:
            logger.warning("FTS5 not available, skipping FTS index creation")
            return []

        commands = [
            # Create FTS5 virtual table
            """
            CREATE VIRTUAL TABLE IF NOT EXISTS memory_search_fts USING fts5(
                memory_id UNINDEXED,
                memory_type UNINDEXED,
                namespace UNINDEXED,
                searchable_content,
                summary,
                category_primary UNINDEXED
            )
            """,
            # Triggers to maintain FTS index
            """
            CREATE TRIGGER IF NOT EXISTS short_term_memory_fts_insert AFTER INSERT ON short_term_memory
            BEGIN
                INSERT INTO memory_search_fts(memory_id, memory_type, namespace, searchable_content, summary, category_primary)
                VALUES (NEW.memory_id, 'short_term', NEW.namespace, NEW.searchable_content, NEW.summary, NEW.category_primary);
            END
            """,
            """
            CREATE TRIGGER IF NOT EXISTS long_term_memory_fts_insert AFTER INSERT ON long_term_memory
            BEGIN
                INSERT INTO memory_search_fts(memory_id, memory_type, namespace, searchable_content, summary, category_primary)
                VALUES (NEW.memory_id, 'long_term', NEW.namespace, NEW.searchable_content, NEW.summary, NEW.category_primary);
            END
            """,
            """
            CREATE TRIGGER IF NOT EXISTS short_term_memory_fts_delete AFTER DELETE ON short_term_memory
            BEGIN
                DELETE FROM memory_search_fts WHERE memory_id = OLD.memory_id AND memory_type = 'short_term';
            END
            """,
            """
            CREATE TRIGGER IF NOT EXISTS long_term_memory_fts_delete AFTER DELETE ON long_term_memory
            BEGIN
                DELETE FROM memory_search_fts WHERE memory_id = OLD.memory_id AND memory_type = 'long_term';
            END
            """,
        ]

        return commands

    def translate_search_query(self, query: str) -> str:
        """Translate search query to FTS5 syntax"""
        if not query or not query.strip():
            return "*"

        # For FTS5, wrap in quotes for exact phrase matching
        # More sophisticated query translation could be added here
        return f'"{query.strip()}"'
