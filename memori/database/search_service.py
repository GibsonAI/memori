"""
SQLAlchemy-based search service for Memori v2.0
Provides cross-database full-text search capabilities
"""

from datetime import datetime
from typing import Any

from loguru import logger
from sqlalchemy import and_, desc, or_, text
from sqlalchemy.orm import Session

from ..utils.cache import TTLCache
from .models import LongTermMemory, ShortTermMemory


class SearchService:
    """Cross-database search service using SQLAlchemy"""

    # Class-level cache shared across all instances for query results
    # Increased cache for remote DB to minimize network latency
    # Limit individual cached values to 10MB to prevent cache poisoning
    _search_cache = TTLCache(max_size=2000, ttl_seconds=600, max_value_size_mb=10.0)

    def __init__(self, session: Session, database_type: str):
        self.session = session
        self.database_type = database_type

    def search_memories(
        self,
        query: str,
        namespace: str = "default",
        category_filter: list[str] | None = None,
        limit: int = 10,
        memory_types: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Search memories across different database backends

        Args:
            query: Search query string
            namespace: Memory namespace
            category_filter: List of categories to filter by
            limit: Maximum number of results
            memory_types: Types of memory to search ('short_term', 'long_term', or both)

        Returns:
            List of memory dictionaries with search metadata
        """
        logger.debug(
            f"[SEARCH] Query initiated - '{query[:50]}{'...' if len(query) > 50 else ''}' | namespace: '{namespace}' | db: {self.database_type} | limit: {limit}"
        )

        if not query or not query.strip():
            logger.debug("Empty query provided, returning recent memories")
            return self._get_recent_memories(
                namespace, category_filter, limit, memory_types
            )

        # Create cache key from search parameters
        cache_key = self._make_cache_key(
            query, namespace, category_filter, limit, memory_types
        )

        # Check cache first
        cached_results = self._search_cache.get(cache_key)
        if cached_results is not None:
            logger.debug(
                f"[SEARCH] Cache HIT for query: '{query[:30]}...' (returned {len(cached_results)} results)"
            )
            return cached_results

        results = []

        # Determine which memory types to search
        search_short_term = not memory_types or "short_term" in memory_types
        search_long_term = not memory_types or "long_term" in memory_types

        logger.debug(
            f"[SEARCH] Target scope - short_term: {search_short_term} | long_term: {search_long_term} | categories: {category_filter or 'all'}"
        )

        try:
            # Try database-specific full-text search first
            if self.database_type == "sqlite":
                logger.debug("[SEARCH] Strategy: SQLite FTS5")
                results = self._search_sqlite_fts(
                    query,
                    namespace,
                    category_filter,
                    limit,
                    search_short_term,
                    search_long_term,
                )
            elif self.database_type == "mysql":
                logger.debug("[SEARCH] Strategy: MySQL FULLTEXT")
                results = self._search_mysql_fulltext(
                    query,
                    namespace,
                    category_filter,
                    limit,
                    search_short_term,
                    search_long_term,
                )
            elif self.database_type == "postgresql":
                logger.debug("[SEARCH] Strategy: PostgreSQL FTS")
                results = self._search_postgresql_fts(
                    query,
                    namespace,
                    category_filter,
                    limit,
                    search_short_term,
                    search_long_term,
                )

            logger.debug(f"[SEARCH] Primary strategy results: {len(results)} matches")

            # If no results or full-text search failed, fall back to LIKE search
            if not results:
                logger.debug(
                    "[SEARCH] Primary strategy empty, falling back to LIKE search"
                )
                results = self._search_like_fallback(
                    query,
                    namespace,
                    category_filter,
                    limit,
                    search_short_term,
                    search_long_term,
                )

        except Exception as e:
            logger.error(
                f"[SEARCH] Full-text search failed for '{query[:30]}...' in '{namespace}' - {type(e).__name__}: {e}"
            )
            logger.debug("[SEARCH] Full-text error details", exc_info=True)
            logger.warning("[SEARCH] Attempting LIKE fallback search")
            try:
                results = self._search_like_fallback(
                    query,
                    namespace,
                    category_filter,
                    limit,
                    search_short_term,
                    search_long_term,
                )
                logger.debug(f"[SEARCH] LIKE fallback results: {len(results)} matches")
            except Exception as fallback_e:
                logger.error(
                    f"[SEARCH] LIKE fallback also failed - {type(fallback_e).__name__}: {fallback_e}"
                )
                results = []

        final_results = self._rank_and_limit_results(results, limit)
        logger.debug(
            f"[SEARCH] Completed - {len(final_results)} results after ranking and limiting"
        )

        if final_results:
            top_result = final_results[0]
            memory_id = str(top_result.get("memory_id", "unknown"))[:8]
            score = top_result.get("composite_score", 0)
            strategy = top_result.get("search_strategy", "unknown")
            logger.debug(
                f"[SEARCH] Top result: {memory_id}... | score: {score:.3f} | strategy: {strategy}"
            )

        # Cache the results before returning (graceful failure if oversized)
        try:
            self._search_cache.set(cache_key, final_results)
            logger.debug(
                f"[SEARCH] Cached {len(final_results)} results for query: '{query[:30]}...'"
            )
        except ValueError as e:
            logger.warning(f"[SEARCH] Cache rejected oversized result: {e}")

        return final_results

    def _search_sqlite_fts(
        self,
        query: str,
        namespace: str,
        category_filter: list[str] | None,
        limit: int,
        search_short_term: bool,
        search_long_term: bool,
    ) -> list[dict[str, Any]]:
        """Search using SQLite FTS5"""
        try:
            logger.debug(
                f"SQLite FTS search starting for query: '{query}' in namespace: '{namespace}'"
            )

            # Use parameters to validate search scope
            if not search_short_term and not search_long_term:
                logger.debug("No memory types specified for search, defaulting to both")
                search_short_term = search_long_term = True

            logger.debug(
                f"Search scope - short_term: {search_short_term}, long_term: {search_long_term}"
            )

            # Build FTS query
            fts_query = f'"{query.strip()}"'
            logger.debug(f"FTS query built: {fts_query}")

            # Build category filter
            category_clause = ""
            params = {"fts_query": fts_query, "namespace": namespace}

            if category_filter:
                category_placeholders = ",".join(
                    [f":cat_{i}" for i in range(len(category_filter))]
                )
                category_clause = (
                    f"AND fts.category_primary IN ({category_placeholders})"
                )
                for i, cat in enumerate(category_filter):
                    params[f"cat_{i}"] = cat
                logger.debug(f"Category filter applied: {category_filter}")

            # SQLite FTS5 search query with COALESCE to handle NULL values
            sql_query = f"""
                SELECT
                    fts.memory_id,
                    fts.memory_type,
                    fts.category_primary,
                    COALESCE(
                        CASE
                            WHEN fts.memory_type = 'short_term' THEN st.processed_data
                            WHEN fts.memory_type = 'long_term' THEN lt.processed_data
                        END,
                        '{{}}'
                    ) as processed_data,
                    COALESCE(
                        CASE
                            WHEN fts.memory_type = 'short_term' THEN st.importance_score
                            WHEN fts.memory_type = 'long_term' THEN lt.importance_score
                            ELSE 0.5
                        END,
                        0.5
                    ) as importance_score,
                    COALESCE(
                        CASE
                            WHEN fts.memory_type = 'short_term' THEN st.created_at
                            WHEN fts.memory_type = 'long_term' THEN lt.created_at
                        END,
                        datetime('now')
                    ) as created_at,
                    COALESCE(fts.summary, '') as summary,
                    COALESCE(rank, 0.0) as search_score,
                    'sqlite_fts5' as search_strategy
                FROM memory_search_fts fts
                LEFT JOIN short_term_memory st ON fts.memory_id = st.memory_id AND fts.memory_type = 'short_term'
                LEFT JOIN long_term_memory lt ON fts.memory_id = lt.memory_id AND fts.memory_type = 'long_term'
                WHERE memory_search_fts MATCH :fts_query AND fts.namespace = :namespace
                {category_clause}
                ORDER BY search_score, importance_score DESC
                LIMIT {limit}
            """

            logger.debug(f"Executing SQLite FTS query with params: {params}")
            result = self.session.execute(text(sql_query), params)
            rows = [dict(row) for row in result]
            logger.debug(f"SQLite FTS search returned {len(rows)} results")

            # Log details of first result for debugging
            if rows:
                logger.debug(
                    f"Sample result: memory_id={rows[0].get('memory_id')}, type={rows[0].get('memory_type')}, score={rows[0].get('search_score')}"
                )

            return rows

        except Exception as e:
            logger.error(
                f"SQLite FTS5 search failed for query '{query}' in namespace '{namespace}': {e}"
            )
            logger.debug(
                f"SQLite FTS5 error details: {type(e).__name__}: {str(e)}",
                exc_info=True,
            )
            # Roll back the transaction to recover from error state
            self.session.rollback()
            return []

    def _search_mysql_fulltext(
        self,
        query: str,
        namespace: str,
        category_filter: list[str] | None,
        limit: int,
        search_short_term: bool,
        search_long_term: bool,
    ) -> list[dict[str, Any]]:
        """Search using MySQL FULLTEXT"""
        results = []

        try:
            # First check if there are any records in the database
            if search_short_term:
                short_count = (
                    self.session.query(ShortTermMemory)
                    .filter(ShortTermMemory.namespace == namespace)
                    .count()
                )
                if short_count == 0:
                    logger.debug(
                        "No short-term memories found in database, skipping FULLTEXT search"
                    )
                    search_short_term = False

            if search_long_term:
                long_count = (
                    self.session.query(LongTermMemory)
                    .filter(LongTermMemory.namespace == namespace)
                    .count()
                )
                if long_count == 0:
                    logger.debug(
                        "No long-term memories found in database, skipping FULLTEXT search"
                    )
                    search_long_term = False

            # If no records exist, return empty results
            if not search_short_term and not search_long_term:
                logger.debug("No memories found in database for FULLTEXT search")
                return []

            # Apply limit proportionally between memory types
            short_limit = (
                limit // 2 if search_short_term and search_long_term else limit
            )
            long_limit = (
                limit - short_limit if search_short_term and search_long_term else limit
            )

            # Search short-term memory if requested
            if search_short_term:
                try:
                    # Build category filter clause
                    category_clause = ""
                    params = {"query": query}
                    if category_filter:
                        category_placeholders = ",".join(
                            [f":cat_{i}" for i in range(len(category_filter))]
                        )
                        category_clause = (
                            f"AND category_primary IN ({category_placeholders})"
                        )
                        for i, cat in enumerate(category_filter):
                            params[f"cat_{i}"] = cat

                    # Use direct SQL query for more reliable results
                    sql_query = text(
                        f"""
                        SELECT
                            memory_id,
                            processed_data,
                            importance_score,
                            created_at,
                            summary,
                            category_primary,
                            MATCH(searchable_content, summary) AGAINST(:query IN NATURAL LANGUAGE MODE) as search_score,
                            'short_term' as memory_type,
                            'mysql_fulltext' as search_strategy
                        FROM short_term_memory
                        WHERE namespace = :namespace
                        AND MATCH(searchable_content, summary) AGAINST(:query IN NATURAL LANGUAGE MODE)
                        {category_clause}
                        ORDER BY search_score DESC
                        LIMIT :short_limit
                    """
                    )

                    params["namespace"] = namespace
                    params["short_limit"] = short_limit

                    short_results = self.session.execute(sql_query, params).fetchall()

                    # Convert rows to dictionaries safely
                    for row in short_results:
                        try:
                            if hasattr(row, "_mapping"):
                                row_dict = dict(row._mapping)
                            else:
                                # Create dict from row values and keys
                                row_dict = {
                                    "memory_id": row[0],
                                    "processed_data": row[1],
                                    "importance_score": row[2],
                                    "created_at": row[3],
                                    "summary": row[4],
                                    "category_primary": row[5],
                                    "search_score": float(row[6]) if row[6] else 0.0,
                                    "memory_type": row[7],
                                    "search_strategy": row[8],
                                }
                            results.append(row_dict)
                        except Exception as e:
                            logger.warning(
                                f"Failed to convert short-term memory row to dict: {e}"
                            )
                            continue

                except Exception as e:
                    logger.warning(f"Short-term memory FULLTEXT search failed: {e}")
                    # Continue to try long-term search

            # Search long-term memory if requested
            if search_long_term:
                try:
                    # Build category filter clause
                    category_clause = ""
                    params = {"query": query}
                    if category_filter:
                        category_placeholders = ",".join(
                            [f":cat_{i}" for i in range(len(category_filter))]
                        )
                        category_clause = (
                            f"AND category_primary IN ({category_placeholders})"
                        )
                        for i, cat in enumerate(category_filter):
                            params[f"cat_{i}"] = cat

                    # Use direct SQL query for more reliable results
                    sql_query = text(
                        f"""
                        SELECT
                            memory_id,
                            processed_data,
                            importance_score,
                            created_at,
                            summary,
                            category_primary,
                            MATCH(searchable_content, summary) AGAINST(:query IN NATURAL LANGUAGE MODE) as search_score,
                            'long_term' as memory_type,
                            'mysql_fulltext' as search_strategy
                        FROM long_term_memory
                        WHERE namespace = :namespace
                        AND MATCH(searchable_content, summary) AGAINST(:query IN NATURAL LANGUAGE MODE)
                        {category_clause}
                        ORDER BY search_score DESC
                        LIMIT :long_limit
                    """
                    )

                    params["namespace"] = namespace
                    params["long_limit"] = long_limit

                    long_results = self.session.execute(sql_query, params).fetchall()

                    # Convert rows to dictionaries safely
                    for row in long_results:
                        try:
                            if hasattr(row, "_mapping"):
                                row_dict = dict(row._mapping)
                            else:
                                # Create dict from row values and keys
                                row_dict = {
                                    "memory_id": row[0],
                                    "processed_data": row[1],
                                    "importance_score": row[2],
                                    "created_at": row[3],
                                    "summary": row[4],
                                    "category_primary": row[5],
                                    "search_score": float(row[6]) if row[6] else 0.0,
                                    "memory_type": row[7],
                                    "search_strategy": row[8],
                                }
                            results.append(row_dict)
                        except Exception as e:
                            logger.warning(
                                f"Failed to convert long-term memory row to dict: {e}"
                            )
                            continue

                except Exception as e:
                    logger.warning(f"Long-term memory FULLTEXT search failed: {e}")
                    # Continue with whatever results we have

            return results

        except Exception as e:
            logger.error(
                f"MySQL FULLTEXT search failed for query '{query}' in namespace '{namespace}': {e}"
            )
            logger.debug(
                f"MySQL FULLTEXT error details: {type(e).__name__}: {str(e)}",
                exc_info=True,
            )
            # Roll back the transaction to recover from error state
            self.session.rollback()
            return []

    def _search_postgresql_fts(
        self,
        query: str,
        namespace: str,
        category_filter: list[str] | None,
        limit: int,
        search_short_term: bool,
        search_long_term: bool,
    ) -> list[dict[str, Any]]:
        """Search using PostgreSQL tsvector"""
        results = []

        try:
            # Apply limit proportionally between memory types
            short_limit = (
                limit // 2 if search_short_term and search_long_term else limit
            )
            long_limit = (
                limit - short_limit if search_short_term and search_long_term else limit
            )

            # Prepare query for tsquery - handle spaces and special characters
            # Convert simple query to tsquery format (join words with &)
            tsquery_text = " & ".join(query.split())

            # Search short-term memory if requested
            if search_short_term:

                # Build category filter clause safely
                category_clause = ""
                if category_filter:
                    category_clause = "AND category_primary = ANY(:category_list)"

                # Use direct SQL to avoid SQLAlchemy Row conversion issues
                short_sql = text(
                    f"""
                    SELECT memory_id, processed_data, importance_score, created_at, summary, category_primary,
                           ts_rank(search_vector, to_tsquery('english', :query)) as search_score,
                           'short_term' as memory_type, 'postgresql_fts' as search_strategy
                    FROM short_term_memory
                    WHERE namespace = :namespace
                    AND search_vector @@ to_tsquery('english', :query)
                    {category_clause}
                    ORDER BY search_score DESC
                    LIMIT :limit
                """
                )

                params = {
                    "namespace": namespace,
                    "query": tsquery_text,
                    "limit": short_limit,
                }
                if category_filter:
                    params["category_list"] = category_filter

                short_results = self.session.execute(short_sql, params).fetchall()

                # Convert to dictionaries manually with proper column mapping
                for row in short_results:
                    results.append(
                        {
                            "memory_id": row[0],
                            "processed_data": row[1],
                            "importance_score": row[2],
                            "created_at": row[3],
                            "summary": row[4],
                            "category_primary": row[5],
                            "search_score": row[6],
                            "memory_type": row[7],
                            "search_strategy": row[8],
                        }
                    )

            # Search long-term memory if requested
            if search_long_term:
                # Build category filter clause safely
                category_clause = ""
                if category_filter:
                    category_clause = "AND category_primary = ANY(:category_list)"

                # Use direct SQL to avoid SQLAlchemy Row conversion issues
                long_sql = text(
                    f"""
                    SELECT memory_id, processed_data, importance_score, created_at, summary, category_primary,
                           ts_rank(search_vector, to_tsquery('english', :query)) as search_score,
                           'long_term' as memory_type, 'postgresql_fts' as search_strategy
                    FROM long_term_memory
                    WHERE namespace = :namespace
                    AND search_vector @@ to_tsquery('english', :query)
                    {category_clause}
                    ORDER BY search_score DESC
                    LIMIT :limit
                """
                )

                params = {
                    "namespace": namespace,
                    "query": tsquery_text,
                    "limit": long_limit,
                }
                if category_filter:
                    params["category_list"] = category_filter

                long_results = self.session.execute(long_sql, params).fetchall()

                # Convert to dictionaries manually with proper column mapping
                for row in long_results:
                    results.append(
                        {
                            "memory_id": row[0],
                            "processed_data": row[1],
                            "importance_score": row[2],
                            "created_at": row[3],
                            "summary": row[4],
                            "category_primary": row[5],
                            "search_score": row[6],
                            "memory_type": row[7],
                            "search_strategy": row[8],
                        }
                    )

            return results

        except Exception as e:
            logger.error(
                f"PostgreSQL FTS search failed for query '{query}' in namespace '{namespace}': {e}"
            )
            logger.debug(
                f"PostgreSQL FTS error details: {type(e).__name__}: {str(e)}",
                exc_info=True,
            )
            # Roll back the transaction to recover from error state
            self.session.rollback()
            return []

    def _search_like_fallback(
        self,
        query: str,
        namespace: str,
        category_filter: list[str] | None,
        limit: int,
        search_short_term: bool,
        search_long_term: bool,
    ) -> list[dict[str, Any]]:
        """Fallback LIKE-based search with improved flexibility"""
        logger.debug(
            f"Starting LIKE fallback search for query: '{query}' in namespace: '{namespace}'"
        )
        results = []

        # Create multiple search patterns for better matching
        search_patterns = [
            f"%{query}%",  # Original full query
        ]

        # Add individual word patterns for better matching
        words = query.strip().split()
        if len(words) > 1:
            for word in words:
                if len(word) > 2:  # Skip very short words
                    search_patterns.append(f"%{word}%")

        logger.debug(f"LIKE search patterns: {search_patterns}")

        # Search short-term memory
        if search_short_term:
            # Build OR conditions for all search patterns
            search_conditions = []
            for pattern in search_patterns:
                search_conditions.extend(
                    [
                        ShortTermMemory.searchable_content.like(pattern),
                        ShortTermMemory.summary.like(pattern),
                    ]
                )

            short_query = self.session.query(ShortTermMemory).filter(
                and_(
                    ShortTermMemory.namespace == namespace,
                    or_(*search_conditions),
                )
            )

            if category_filter:
                short_query = short_query.filter(
                    ShortTermMemory.category_primary.in_(category_filter)
                )

            short_results = (
                short_query.order_by(
                    desc(ShortTermMemory.importance_score),
                    desc(ShortTermMemory.created_at),
                )
                .limit(limit)
                .all()
            )

            logger.debug(f"LIKE fallback found {len(short_results)} short-term results")

            for result in short_results:
                memory_dict = {
                    "memory_id": result.memory_id,
                    "memory_type": "short_term",
                    "processed_data": result.processed_data,
                    "importance_score": result.importance_score,
                    "created_at": result.created_at,
                    "summary": result.summary,
                    "category_primary": result.category_primary,
                    "search_score": 0.4,  # Fixed score for LIKE search
                    "search_strategy": f"{self.database_type}_like_fallback",
                }
                results.append(memory_dict)

        # Search long-term memory
        if search_long_term:
            # Build OR conditions for all search patterns
            search_conditions = []
            for pattern in search_patterns:
                search_conditions.extend(
                    [
                        LongTermMemory.searchable_content.like(pattern),
                        LongTermMemory.summary.like(pattern),
                    ]
                )

            long_query = self.session.query(LongTermMemory).filter(
                and_(
                    LongTermMemory.namespace == namespace,
                    or_(*search_conditions),
                )
            )

            if category_filter:
                long_query = long_query.filter(
                    LongTermMemory.category_primary.in_(category_filter)
                )

            long_results = (
                long_query.order_by(
                    desc(LongTermMemory.importance_score),
                    desc(LongTermMemory.created_at),
                )
                .limit(limit)
                .all()
            )

            logger.debug(f"LIKE fallback found {len(long_results)} long-term results")

            for result in long_results:
                memory_dict = {
                    "memory_id": result.memory_id,
                    "memory_type": "long_term",
                    "processed_data": result.processed_data,
                    "importance_score": result.importance_score,
                    "created_at": result.created_at,
                    "summary": result.summary,
                    "category_primary": result.category_primary,
                    "search_score": 0.4,  # Fixed score for LIKE search
                    "search_strategy": f"{self.database_type}_like_fallback",
                }
                results.append(memory_dict)

        logger.debug(
            f"LIKE fallback search completed, returning {len(results)} total results"
        )
        return results

    def _get_recent_memories(
        self,
        namespace: str,
        category_filter: list[str] | None,
        limit: int,
        memory_types: list[str] | None,
    ) -> list[dict[str, Any]]:
        """Get recent memories when no search query is provided"""
        results = []

        search_short_term = not memory_types or "short_term" in memory_types
        search_long_term = not memory_types or "long_term" in memory_types

        # Get recent short-term memories
        if search_short_term:
            short_query = self.session.query(ShortTermMemory).filter(
                ShortTermMemory.namespace == namespace
            )

            if category_filter:
                short_query = short_query.filter(
                    ShortTermMemory.category_primary.in_(category_filter)
                )

            short_results = (
                short_query.order_by(desc(ShortTermMemory.created_at))
                .limit(limit // 2)
                .all()
            )

            for result in short_results:
                memory_dict = {
                    "memory_id": result.memory_id,
                    "memory_type": "short_term",
                    "processed_data": result.processed_data,
                    "importance_score": result.importance_score,
                    "created_at": result.created_at,
                    "summary": result.summary,
                    "category_primary": result.category_primary,
                    "search_score": 1.0,
                    "search_strategy": "recent_memories",
                }
                results.append(memory_dict)

        # Get recent long-term memories
        if search_long_term:
            long_query = self.session.query(LongTermMemory).filter(
                LongTermMemory.namespace == namespace
            )

            if category_filter:
                long_query = long_query.filter(
                    LongTermMemory.category_primary.in_(category_filter)
                )

            long_results = (
                long_query.order_by(desc(LongTermMemory.created_at))
                .limit(limit // 2)
                .all()
            )

            for result in long_results:
                memory_dict = {
                    "memory_id": result.memory_id,
                    "memory_type": "long_term",
                    "processed_data": result.processed_data,
                    "importance_score": result.importance_score,
                    "created_at": result.created_at,
                    "summary": result.summary,
                    "category_primary": result.category_primary,
                    "search_score": 1.0,
                    "search_strategy": "recent_memories",
                }
                results.append(memory_dict)

        return results

    def _rank_and_limit_results(
        self, results: list[dict[str, Any]], limit: int
    ) -> list[dict[str, Any]]:
        """Rank and limit search results"""
        # Calculate composite score
        for result in results:
            search_score = result.get("search_score", 0.4)
            importance_score = result.get("importance_score", 0.5)
            recency_score = self._calculate_recency_score(result.get("created_at"))

            # Weighted composite score
            result["composite_score"] = (
                search_score * 0.5 + importance_score * 0.3 + recency_score * 0.2
            )

        # Sort by composite score and limit
        results.sort(key=lambda x: x.get("composite_score", 0), reverse=True)
        return results[:limit]

    def _calculate_recency_score(self, created_at) -> float:
        """Calculate recency score (0-1, newer = higher)"""
        try:
            if not created_at:
                return 0.0

            if isinstance(created_at, str):
                created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))

            days_old = (datetime.now() - created_at).days
            return max(0, 1 - (days_old / 30))  # Full score for recent, 0 after 30 days
        except:
            return 0.0

    def _make_cache_key(
        self,
        query: str,
        namespace: str,
        category_filter: list[str] | None,
        limit: int,
        memory_types: list[str] | None,
    ) -> str:
        """Create cache key from search parameters"""
        import hashlib

        # Create deterministic key from parameters
        key_parts = [
            query[:200],  # First 200 chars of query
            namespace,
            str(sorted(category_filter or [])),  # Sorted for consistency
            str(limit),
            str(sorted(memory_types or [])),  # Sorted for consistency
        ]
        key_string = "|".join(key_parts)
        return hashlib.md5(key_string.encode()).hexdigest()
