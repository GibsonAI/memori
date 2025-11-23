"""
MySQL FULLTEXT search adapter for Memori
Implements MySQL-specific search functionality
"""

from typing import Any

from loguru import logger

from ..connectors.base_connector import BaseDatabaseConnector, BaseSearchAdapter


class MySQLSearchAdapter(BaseSearchAdapter):
    """MySQL-specific search adapter with FULLTEXT support"""

    def __init__(self, connector: BaseDatabaseConnector):
        super().__init__(connector)
        self.fulltext_available = self._check_fulltext_support()

    def _check_fulltext_support(self) -> bool:
        """Check if FULLTEXT search is available and properly configured"""
        try:
            # Check if FULLTEXT indexes exist
            check_query = """
                SELECT COUNT(*) as index_count
                FROM information_schema.STATISTICS
                WHERE table_schema = DATABASE()
                AND index_type = 'FULLTEXT'
                AND table_name IN ('short_term_memory', 'long_term_memory')
            """

            result = self.connector.execute_query(check_query)
            index_count = result[0]["index_count"] if result else 0

            if index_count >= 2:  # Expect FULLTEXT indexes on both tables
                logger.info("MySQL FULLTEXT indexes found and available")
                return True
            else:
                logger.warning(
                    "MySQL FULLTEXT indexes not found, will use LIKE fallback"
                )
                return False

        except Exception as e:
            logger.warning(f"Could not check MySQL FULLTEXT support: {e}")
            return False

    def execute_fulltext_search(
        self,
        query: str,
        namespace: str = "default",
        category_filter: list[str] | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Execute MySQL FULLTEXT search or fallback to LIKE search"""
        if self.fulltext_available and query and query.strip():
            try:
                return self._execute_mysql_fulltext_search(
                    query, namespace, category_filter, limit
                )
            except Exception as e:
                logger.debug(
                    f"MySQL FULLTEXT search failed: {e}, falling back to LIKE search"
                )

        # Fallback to LIKE search
        return self.execute_fallback_search(query, namespace, category_filter, limit)

    def _execute_mysql_fulltext_search(
        self,
        query: str,
        namespace: str,
        category_filter: list[str] | None,
        limit: int,
    ) -> list[dict[str, Any]]:
        """Execute MySQL FULLTEXT search"""
        results = []
        translated_query = self.translate_search_query(query)

        # Search short-term memory
        category_clause = ""
        params = [namespace, translated_query]

        if category_filter:
            category_placeholders = ",".join(["%s"] * len(category_filter))
            category_clause = f"AND category_primary IN ({category_placeholders})"
            params.extend(category_filter)

        params.append(limit)

        short_term_query = f"""
            SELECT
                *,
                'short_term' as memory_type,
                'mysql_fulltext' as search_strategy,
                MATCH(searchable_content, summary) AGAINST(%s IN NATURAL LANGUAGE MODE) as relevance_score
            FROM short_term_memory
            WHERE namespace = %s
            AND MATCH(searchable_content, summary) AGAINST(%s IN NATURAL LANGUAGE MODE)
            {category_clause}
            ORDER BY relevance_score DESC, importance_score DESC, created_at DESC
            LIMIT %s
        """

        # Note: MySQL uses %s placeholders, need to adjust params
        mysql_params = [translated_query, namespace, translated_query]
        if category_filter:
            mysql_params.extend(category_filter)
        mysql_params.append(limit)

        short_results = self.connector.execute_query(short_term_query, mysql_params)
        results.extend(short_results)

        # Search long-term memory
        long_term_query = f"""
            SELECT
                *,
                'long_term' as memory_type,
                'mysql_fulltext' as search_strategy,
                MATCH(searchable_content, summary) AGAINST(%s IN NATURAL LANGUAGE MODE) as relevance_score
            FROM long_term_memory
            WHERE namespace = %s
            AND MATCH(searchable_content, summary) AGAINST(%s IN NATURAL LANGUAGE MODE)
            {category_clause}
            ORDER BY relevance_score DESC, importance_score DESC, created_at DESC
            LIMIT %s
        """

        long_results = self.connector.execute_query(long_term_query, mysql_params)
        results.extend(long_results)

        # Sort combined results by relevance and limit
        results.sort(
            key=lambda x: (
                x.get("relevance_score", 0) * 0.5
                + x.get("importance_score", 0) * 0.3
                + self._calculate_recency_score(x.get("created_at")) * 0.2
            ),
            reverse=True,
        )

        return results[:limit]

    def _calculate_recency_score(self, created_at) -> float:
        """Calculate recency score for MySQL datetime"""
        try:
            if not created_at:
                return 0.0

            from datetime import datetime

            # Handle different datetime formats
            if isinstance(created_at, str):
                created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            elif hasattr(created_at, "replace"):
                created_at = created_at.replace(tzinfo=None)

            days_old = (datetime.now() - created_at).days
            return max(0, 1 - (days_old / 30))
        except (ValueError, TypeError, AttributeError) as e:
            logger.warning(
                f"Invalid date format for recency calculation: {created_at}, error: {e}"
            )
            return 0.0

    def create_search_indexes(self) -> list[str]:
        """Create MySQL FULLTEXT indexes"""
        commands = [
            # Create FULLTEXT index on short_term_memory
            """
            ALTER TABLE short_term_memory
            ADD FULLTEXT INDEX ft_short_term_search (searchable_content, summary)
            """,
            # Create FULLTEXT index on long_term_memory
            """
            ALTER TABLE long_term_memory
            ADD FULLTEXT INDEX ft_long_term_search (searchable_content, summary)
            """,
            # Additional composite indexes for better performance
            """
            CREATE INDEX IF NOT EXISTS idx_short_term_namespace_category
            ON short_term_memory(namespace, category_primary, importance_score)
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_long_term_namespace_category
            ON long_term_memory(namespace, category_primary, importance_score)
            """,
        ]

        return commands

    def translate_search_query(self, query: str) -> str:
        """Translate search query to MySQL FULLTEXT syntax"""
        if not query or not query.strip():
            return ""

        # Clean and prepare the query for MySQL FULLTEXT
        cleaned_query = query.strip()

        # For basic natural language search, we can use the query as-is
        # More sophisticated query translation could be added here:
        # - Handle boolean operators (+, -, etc.)
        # - Escape special characters
        # - Add wildcard support

        return cleaned_query

    def execute_fallback_search(
        self,
        query: str,
        namespace: str = "default",
        category_filter: list[str] | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Execute fallback LIKE-based search with MySQL syntax"""
        results = []

        # Search short-term memory
        category_clause = ""
        params = [namespace, f"%{query}%", f"%{query}%"]

        if category_filter:
            category_placeholders = ",".join(["%s"] * len(category_filter))
            category_clause = f"AND category_primary IN ({category_placeholders})"
            params.extend(category_filter)

        params.append(limit)

        # Use MySQL-specific placeholder syntax
        mysql_params = [namespace, f"%{query}%", f"%{query}%"]
        if category_filter:
            mysql_params.extend(category_filter)
        mysql_params.append(limit)

        short_term_query = f"""
            SELECT *, 'short_term' as memory_type, 'mysql_like_fallback' as search_strategy
            FROM short_term_memory
            WHERE namespace = %s AND (searchable_content LIKE %s OR summary LIKE %s)
            {category_clause}
            ORDER BY importance_score DESC, created_at DESC
            LIMIT %s
        """

        results.extend(self.connector.execute_query(short_term_query, mysql_params))

        # Search long-term memory
        long_term_query = f"""
            SELECT *, 'long_term' as memory_type, 'mysql_like_fallback' as search_strategy
            FROM long_term_memory
            WHERE namespace = %s AND (searchable_content LIKE %s OR summary LIKE %s)
            {category_clause}
            ORDER BY importance_score DESC, created_at DESC
            LIMIT %s
        """

        results.extend(self.connector.execute_query(long_term_query, mysql_params))

        return results[:limit]
