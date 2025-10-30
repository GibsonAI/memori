"""
PostgreSQL-specific search adapter with tsvector support and proper security
"""

from typing import Any

from loguru import logger

from ...utils.exceptions import ValidationError
from ...utils.input_validator import DatabaseInputValidator
from ...utils.query_builder import DatabaseDialect, DatabaseQueryExecutor
from ..connectors.base_connector import BaseDatabaseConnector, BaseSearchAdapter


class PostgreSQLSearchAdapter(BaseSearchAdapter):
    """PostgreSQL-specific search implementation with tsvector and security measures"""

    def __init__(self, connector: BaseDatabaseConnector):
        super().__init__(connector)
        self.query_executor = DatabaseQueryExecutor(
            connector, DatabaseDialect.POSTGRESQL
        )
        self._fts_available = None

    def execute_fulltext_search(
        self,
        query: str,
        user_id: str = "default",
        assistant_id: str | None = None,
        session_id: str = "default",
        category_filter: list[str] | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Execute PostgreSQL full-text search with tsvector"""
        try:
            # Validate all parameters
            validated = DatabaseInputValidator.validate_search_params(
                query, user_id, category_filter, limit
            )

            # Check if FTS is available
            if not self._check_fts_available():
                logger.debug(
                    "PostgreSQL FTS not available, falling back to LIKE search"
                )
                return self.execute_fallback_search(
                    validated["query"],
                    validated["user_id"],
                    assistant_id,
                    session_id,
                    validated["category_filter"],
                    validated["limit"],
                )

            # Execute PostgreSQL tsvector search
            return self.query_executor.execute_search(
                validated["query"],
                validated["user_id"],
                validated["category_filter"],
                validated["limit"],
                use_fts=True,
                assistant_id=assistant_id,
                session_id=session_id,
            )

        except ValidationError as e:
            logger.error(f"Invalid search parameters: {e}")
            return []
        except Exception as e:
            logger.error(f"PostgreSQL FTS search failed: {e}")
            return self.execute_fallback_search(
                query, user_id, assistant_id, session_id, category_filter, limit
            )

    def create_search_indexes(self) -> list[str]:
        """Create PostgreSQL-specific search indexes"""
        indexes = []

        try:
            with self.connector.get_connection() as conn:
                cursor = conn.cursor()

                # Create GIN indexes for full-text search
                fts_indexes = [
                    """
                    CREATE INDEX IF NOT EXISTS idx_short_term_fts_gin
                    ON short_term_memory
                    USING gin(to_tsvector('english', searchable_content || ' ' || summary))
                    """,
                    """
                    CREATE INDEX IF NOT EXISTS idx_long_term_fts_gin
                    ON long_term_memory
                    USING gin(to_tsvector('english', searchable_content || ' ' || summary))
                    """,
                ]

                for index_sql in fts_indexes:
                    try:
                        cursor.execute(index_sql)
                        indexes.append("gin_fts_index")
                    except Exception as e:
                        logger.warning(f"Failed to create FTS index: {e}")

                # Create standard B-tree indexes for fallback search
                standard_indexes = [
                    "CREATE INDEX IF NOT EXISTS idx_st_search_pg ON short_term_memory(user_id, assistant_id, category_primary, importance_score)",
                    "CREATE INDEX IF NOT EXISTS idx_lt_search_pg ON long_term_memory(user_id, assistant_id, category_primary, importance_score)",
                    "CREATE INDEX IF NOT EXISTS idx_st_content_pg ON short_term_memory USING gin(searchable_content gin_trgm_ops)",
                    "CREATE INDEX IF NOT EXISTS idx_lt_content_pg ON long_term_memory USING gin(searchable_content gin_trgm_ops)",
                ]

                # Enable trigram extension for better LIKE performance
                try:
                    cursor.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
                    logger.info("Enabled PostgreSQL pg_trgm extension")
                except Exception as e:
                    logger.warning(f"Could not enable pg_trgm extension: {e}")

                for index_sql in standard_indexes:
                    try:
                        cursor.execute(index_sql)
                        indexes.append(index_sql.split()[-1])
                    except Exception as e:
                        logger.warning(f"Failed to create index: {e}")

                conn.commit()
                logger.info(f"Created {len(indexes)} PostgreSQL search indexes")

        except Exception as e:
            logger.error(f"Failed to create PostgreSQL search indexes: {e}")

        return indexes

    def translate_search_query(self, query: str) -> str:
        """Translate search query to PostgreSQL tsquery syntax"""
        if not query or not query.strip():
            return ""

        # Sanitize input for tsquery
        sanitized = query.strip()

        # Remove potentially dangerous operators
        dangerous_chars = ["!", "&", "|", "(", ")", "<", ">"]
        for char in dangerous_chars:
            sanitized = sanitized.replace(char, " ")

        # Split into words and clean
        words = [word.strip() for word in sanitized.split() if word.strip()]

        if not words:
            return ""

        # Join words with AND operator (safer than allowing user operators)
        return " & ".join(words)

    def _check_fts_available(self) -> bool:
        """Check if PostgreSQL full-text search is available"""
        if self._fts_available is not None:
            return self._fts_available

        try:
            with self.connector.get_connection() as conn:
                cursor = conn.cursor()
                # Test tsvector functionality
                cursor.execute(
                    "SELECT to_tsvector('english', 'test') @@ plainto_tsquery('english', 'test')"
                )
                result = cursor.fetchone()
                self._fts_available = result[0] if result else False
        except Exception:
            self._fts_available = False

        return self._fts_available

    def execute_fallback_search(
        self,
        query: str,
        user_id: str = "default",
        assistant_id: str | None = None,
        session_id: str = "default",
        category_filter: list[str] | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Execute LIKE-based fallback search for PostgreSQL"""
        try:
            return self.query_executor.execute_search(
                query,
                user_id,
                category_filter,
                limit,
                use_fts=False,
                assistant_id=assistant_id,
                session_id=session_id,
            )
        except Exception as e:
            logger.error(f"PostgreSQL fallback search failed: {e}")
            return []

    def optimize_database(self):
        """Perform PostgreSQL-specific optimizations"""
        try:
            with self.connector.get_connection() as conn:
                cursor = conn.cursor()

                # Update table statistics
                cursor.execute("ANALYZE short_term_memory")
                cursor.execute("ANALYZE long_term_memory")

                # Reindex GIN indexes for FTS performance
                try:
                    cursor.execute("REINDEX INDEX CONCURRENTLY idx_short_term_fts_gin")
                    cursor.execute("REINDEX INDEX CONCURRENTLY idx_long_term_fts_gin")
                except Exception as e:
                    logger.debug(
                        f"Concurrent reindex failed, trying regular reindex: {e}"
                    )
                    try:
                        cursor.execute("REINDEX INDEX idx_short_term_fts_gin")
                        cursor.execute("REINDEX INDEX idx_long_term_fts_gin")
                    except Exception as e2:
                        logger.warning(f"Reindex failed: {e2}")

                conn.commit()
                logger.info("PostgreSQL database optimization completed")

        except Exception as e:
            logger.warning(f"PostgreSQL optimization failed: {e}")

    def create_materialized_views(self):
        """Create materialized views for better search performance"""
        try:
            with self.connector.get_connection() as conn:
                cursor = conn.cursor()

                # Create materialized view for search optimization
                mv_sql = """
                    CREATE MATERIALIZED VIEW IF NOT EXISTS memory_search_mv AS
                    SELECT
                        memory_id,
                        'short_term' as memory_type,
                        user_id,
                        assistant_id,
                        session_id,
                        category_primary,
                        searchable_content,
                        summary,
                        importance_score,
                        created_at,
                        to_tsvector('english', searchable_content || ' ' || summary) as search_vector
                    FROM short_term_memory
                    WHERE expires_at IS NULL OR expires_at > NOW()

                    UNION ALL

                    SELECT
                        memory_id,
                        'long_term' as memory_type,
                        user_id,
                        assistant_id,
                        session_id,
                        category_primary,
                        searchable_content,
                        summary,
                        importance_score,
                        created_at,
                        to_tsvector('english', searchable_content || ' ' || summary) as search_vector
                    FROM long_term_memory

                    ORDER BY importance_score DESC, created_at DESC
                """

                cursor.execute(mv_sql)

                # Create index on materialized view
                cursor.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_memory_search_mv_fts
                    ON memory_search_mv
                    USING gin(search_vector)
                """
                )

                cursor.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_memory_search_mv_filter
                    ON memory_search_mv (user_id, assistant_id, category_primary, memory_type)
                """
                )

                conn.commit()
                logger.info(
                    "Created PostgreSQL materialized view for search optimization"
                )

        except Exception as e:
            logger.warning(f"Failed to create materialized view: {e}")

    def refresh_materialized_views(self):
        """Refresh materialized views for up-to-date search results"""
        try:
            with self.connector.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "REFRESH MATERIALIZED VIEW CONCURRENTLY memory_search_mv"
                )
                conn.commit()
                logger.debug("Refreshed PostgreSQL materialized view")
        except Exception as e:
            logger.warning(f"Failed to refresh materialized view: {e}")
