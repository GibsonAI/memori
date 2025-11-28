"""
SQLite-specific search adapter with FTS5 support and proper security
"""

import sqlite3
from typing import Any

from loguru import logger

from ...utils.exceptions import ValidationError
from ...utils.input_validator import DatabaseInputValidator
from ...utils.query_builder import DatabaseDialect, DatabaseQueryExecutor
from ..connectors.base_connector import BaseDatabaseConnector, BaseSearchAdapter


class SQLiteSearchAdapter(BaseSearchAdapter):
    """SQLite-specific search implementation with FTS5 and security measures"""

    def __init__(self, connector: BaseDatabaseConnector):
        super().__init__(connector)
        self.query_executor = DatabaseQueryExecutor(connector, DatabaseDialect.SQLITE)
        self._fts_available = None

    def execute_fulltext_search(
        self,
        query: str,
        namespace: str = "default",
        category_filter: list[str] | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Execute SQLite FTS5 search with proper validation"""
        try:
            # Validate all parameters
            validated = DatabaseInputValidator.validate_search_params(
                query, namespace, category_filter, limit
            )

            # Check if FTS is available
            if not self._check_fts_available():
                logger.debug("FTS not available, falling back to LIKE search")
                return self.execute_fallback_search(
                    validated["query"],
                    validated["namespace"],
                    validated["category_filter"],
                    validated["limit"],
                )

            # Execute FTS search
            return self.query_executor.execute_search(
                validated["query"],
                validated["namespace"],
                validated["category_filter"],
                validated["limit"],
                use_fts=True,
            )

        except ValidationError as e:
            logger.error(f"Invalid search parameters: {e}")
            return []
        except Exception as e:
            logger.error(f"SQLite FTS search failed: {e}")
            # Fallback to LIKE search on error
            return self.execute_fallback_search(
                query, namespace, category_filter, limit
            )

    def create_search_indexes(self) -> list[str]:
        """Create SQLite-specific search indexes"""
        indexes = []

        try:
            with self.connector.get_connection() as conn:
                cursor = conn.cursor()

                # Create FTS5 virtual table if not exists (non-contentless for full data access)
                fts_sql = """
                    CREATE VIRTUAL TABLE IF NOT EXISTS memory_search_fts USING fts5(
                        memory_id UNINDEXED,
                        memory_type UNINDEXED,
                        namespace UNINDEXED,
                        searchable_content,
                        summary,
                        category_primary UNINDEXED
                    )
                """
                cursor.execute(fts_sql)
                indexes.append("memory_search_fts")

                # Create standard indexes for fallback search
                standard_indexes = [
                    "CREATE INDEX IF NOT EXISTS idx_st_search ON short_term_memory(namespace, category_primary, importance_score)",
                    "CREATE INDEX IF NOT EXISTS idx_lt_search ON long_term_memory(namespace, category_primary, importance_score)",
                    "CREATE INDEX IF NOT EXISTS idx_st_content ON short_term_memory(searchable_content)",
                    "CREATE INDEX IF NOT EXISTS idx_lt_content ON long_term_memory(searchable_content)",
                ]

                for index_sql in standard_indexes:
                    try:
                        cursor.execute(index_sql)
                        indexes.append(index_sql.split()[-1])  # Extract index name
                    except sqlite3.Error as e:
                        logger.warning(f"Failed to create index: {e}")

                # Create triggers to maintain FTS index
                triggers = [
                    """
                    CREATE TRIGGER IF NOT EXISTS short_term_memory_fts_insert
                    AFTER INSERT ON short_term_memory
                    BEGIN
                        INSERT INTO memory_search_fts(memory_id, memory_type, namespace, searchable_content, summary, category_primary)
                        VALUES (NEW.memory_id, 'short_term', NEW.namespace, NEW.searchable_content, NEW.summary, NEW.category_primary);
                    END
                    """,
                    """
                    CREATE TRIGGER IF NOT EXISTS long_term_memory_fts_insert
                    AFTER INSERT ON long_term_memory
                    BEGIN
                        INSERT INTO memory_search_fts(memory_id, memory_type, namespace, searchable_content, summary, category_primary)
                        VALUES (NEW.memory_id, 'long_term', NEW.namespace, NEW.searchable_content, NEW.summary, NEW.category_primary);
                    END
                    """,
                    """
                    CREATE TRIGGER IF NOT EXISTS short_term_memory_fts_delete
                    AFTER DELETE ON short_term_memory
                    BEGIN
                        DELETE FROM memory_search_fts WHERE memory_id = OLD.memory_id AND memory_type = 'short_term';
                    END
                    """,
                    """
                    CREATE TRIGGER IF NOT EXISTS long_term_memory_fts_delete
                    AFTER DELETE ON long_term_memory
                    BEGIN
                        DELETE FROM memory_search_fts WHERE memory_id = OLD.memory_id AND memory_type = 'long_term';
                    END
                    """,
                ]

                for trigger_sql in triggers:
                    try:
                        cursor.execute(trigger_sql)
                    except sqlite3.Error as e:
                        logger.warning(f"Failed to create trigger: {e}")

                conn.commit()
                logger.info(f"Created {len(indexes)} SQLite search indexes")

        except Exception as e:
            logger.error(f"Failed to create SQLite search indexes: {e}")

        return indexes

    def translate_search_query(self, query: str) -> str:
        """Translate search query to SQLite FTS5 syntax"""
        if not query or not query.strip():
            return "*"

        # Escape FTS5 special characters
        sanitized = query.replace('"', '""')  # Escape quotes

        # Remove potentially dangerous FTS operators
        dangerous_operators = ["AND", "OR", "NOT", "NEAR", "^"]
        for op in dangerous_operators:
            sanitized = sanitized.replace(op, "")

        # Wrap in quotes for phrase search (safer than operators)
        return f'"{sanitized.strip()}"'

    def _check_fts_available(self) -> bool:
        """Check if FTS5 is available in SQLite"""
        if self._fts_available is not None:
            return self._fts_available

        try:
            with self.connector.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("CREATE VIRTUAL TABLE fts_test USING fts5(content)")
                cursor.execute("DROP TABLE fts_test")
                self._fts_available = True
        except sqlite3.OperationalError:
            self._fts_available = False
        except Exception:
            self._fts_available = False

        return self._fts_available

    def execute_fallback_search(
        self,
        query: str,
        namespace: str = "default",
        category_filter: list[str] | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Execute LIKE-based fallback search for SQLite"""
        try:
            return self.query_executor.execute_search(
                query, namespace, category_filter, limit, use_fts=False
            )
        except Exception as e:
            logger.error(f"SQLite fallback search failed: {e}")
            return []

    def optimize_database(self):
        """Perform SQLite-specific optimizations"""
        try:
            with self.connector.get_connection() as conn:
                cursor = conn.cursor()

                # Analyze tables for better query planning
                cursor.execute("ANALYZE")

                # Optimize FTS index if available
                if self._check_fts_available():
                    try:
                        cursor.execute(
                            "INSERT INTO memory_search_fts(memory_search_fts) VALUES('optimize')"
                        )
                    except sqlite3.Error as e:
                        logger.debug(f"FTS optimization skipped: {e}")

                # Update table statistics
                cursor.execute("PRAGMA optimize")

                conn.commit()
                logger.info("SQLite database optimization completed")

        except Exception as e:
            logger.warning(f"SQLite optimization failed: {e}")
