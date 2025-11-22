"""
SQLAlchemy-based search service for Memori v2.0
Provides cross-database full-text search capabilities
"""

from datetime import datetime
from typing import Any

from loguru import logger
from sqlalchemy import and_, asc, desc, func, literal, or_, text, union_all
from sqlalchemy.orm import Session

from .models import LongTermMemory, ShortTermMemory


class SearchService:
    """Cross-database search service using SQLAlchemy"""

    def __init__(self, session: Session, database_type: str):
        self.session = session
        self.database_type = database_type

    def search_memories(
        self,
        query: str,
        user_id: str = "default",
        assistant_id: str | None = None,
        session_id: str | None = None,
        category_filter: list[str] | None = None,
        limit: int = 10,
        memory_types: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Search memories across different database backends

        Args:
            query: Search query string
            user_id: User identifier for multi-tenant isolation (REQUIRED)
                     Cannot be None or empty - enforced for security
            assistant_id: Assistant identifier for multi-tenant isolation
                          - If None: searches across ALL assistants for this user
                          - If specified: searches only this assistant's memories
            session_id: Session identifier for conversation grouping
                        - Applied only to short-term memories (conversation context)
                        - Long-term memories are accessible across all sessions
            category_filter: List of categories to filter by
            limit: Maximum number of results
            memory_types: Types of memory to search ('short_term', 'long_term', or both)

        Returns:
            List of memory dictionaries with search metadata

        Raises:
            ValueError: If user_id is None or empty string
        """
        # SECURITY: Validate user_id to prevent cross-user data leaks
        if not user_id or not user_id.strip():
            raise ValueError(
                "user_id cannot be None or empty - required for user isolation and security"
            )

        logger.debug(
            f"[SEARCH] Query initiated - '{query[:50]}{'...' if len(query) > 50 else ''}' | user_id: '{user_id}' | assistant_id: '{assistant_id}' | session_id: '{session_id}' | db: {self.database_type} | limit: {limit}"
        )

        if not query or not query.strip():
            logger.debug("Empty query provided, returning recent memories")
            return self._get_recent_memories(
                user_id, assistant_id, session_id, category_filter, limit, memory_types
            )

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
                    user_id,
                    assistant_id,
                    session_id,
                    category_filter,
                    limit,
                    search_short_term,
                    search_long_term,
                )
            elif self.database_type == "mysql":
                logger.debug("[SEARCH] Strategy: MySQL FULLTEXT")
                results = self._search_mysql_fulltext(
                    query,
                    user_id,
                    assistant_id,
                    session_id,
                    category_filter,
                    limit,
                    search_short_term,
                    search_long_term,
                )
            elif self.database_type == "postgresql":
                logger.debug("[SEARCH] Strategy: PostgreSQL FTS")
                results = self._search_postgresql_fts(
                    query,
                    user_id,
                    assistant_id,
                    session_id,
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
                    user_id,
                    assistant_id,
                    session_id,
                    category_filter,
                    limit,
                    search_short_term,
                    search_long_term,
                )

        except Exception as e:
            logger.error(
                f"Full-text search failed | query='{query[:50]}...' | user_id={user_id} | "
                f"assistant_id={assistant_id} | database={self.database_type} | "
                f"error={type(e).__name__}: {str(e)}"
            )
            logger.warning(
                f"Attempting LIKE fallback search | user_id={user_id} | query='{query[:30]}...'"
            )
            try:
                results = self._search_like_fallback(
                    query,
                    user_id,
                    assistant_id,
                    session_id,
                    category_filter,
                    limit,
                    search_short_term,
                    search_long_term,
                )
            except Exception as fallback_e:
                logger.error(
                    f"LIKE fallback search failed | query='{query[:30]}...' | user_id={user_id} | "
                    f"error={type(fallback_e).__name__}: {str(fallback_e)}"
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

        return final_results

    def _search_sqlite_fts(
        self,
        query: str,
        user_id: str,
        assistant_id: str | None,
        session_id: str | None,
        category_filter: list[str] | None,
        limit: int,
        search_short_term: bool,
        search_long_term: bool,
    ) -> list[dict[str, Any]]:
        """Search using SQLite FTS5"""
        try:
            logger.debug(
                f"SQLite FTS search starting for query: '{query}' in user_id: '{user_id}', assistant_id: '{assistant_id}', session_id: '{session_id}'"
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

            # Build filters
            category_clause = ""
            assistant_clause = ""
            session_clause = ""
            params = {"fts_query": fts_query, "user_id": user_id}

            # BEHAVIOR: Multi-assistant isolation
            # - Short-term memory: Accessible to all assistants for the same user (no filter)
            # - Long-term memory:
            #   - If assistant_id=None: ONLY see shared memories (assistant_id IS NULL)
            #   - If assistant_id='bot': See shared (NULL) OR own (bot) memories
            if assistant_id:
                assistant_clause = "AND (fts.memory_type = 'short_term' OR fts.assistant_id IS NULL OR fts.assistant_id = :assistant_id)"
                params["assistant_id"] = assistant_id
                logger.debug(
                    f"Assistant filter: long-term allows NULL or {assistant_id}"
                )
            else:
                # assistant_id=None: Can only see shared memories (not other assistants' private data)
                assistant_clause = (
                    "AND (fts.memory_type = 'short_term' OR fts.assistant_id IS NULL)"
                )
                logger.debug(
                    "Assistant filter: long-term allows only NULL (shared memories)"
                )

            if session_id:
                # Apply session filter only to short-term memories
                # Long-term memories should be accessible across all sessions for the same user
                session_clause = "AND (fts.memory_type = 'long_term' OR fts.session_id = :session_id)"
                params["session_id"] = session_id
                logger.debug(f"Session filter applied to short-term only: {session_id}")

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
                WHERE memory_search_fts MATCH :fts_query AND fts.user_id = :user_id
                {assistant_clause}
                {session_clause}
                {category_clause}
                ORDER BY search_score, importance_score DESC
                LIMIT {limit}
            """

            logger.debug(f"Executing SQLite FTS query with params: {params}")
            result = self.session.execute(text(sql_query), params)
            rows = [dict(row._mapping) for row in result]
            logger.debug(f"SQLite FTS search returned {len(rows)} results")

            # Log details of first result for debugging
            if rows:
                logger.debug(
                    f"Sample result: memory_id={rows[0].get('memory_id')}, type={rows[0].get('memory_type')}, score={rows[0].get('search_score')}"
                )

            return rows

        except Exception as e:
            logger.error(
                f"SQLite FTS5 search failed | query='{query[:50]}...' | user_id={user_id} | "
                f"assistant_id={assistant_id} | session_id={session_id} | "
                f"error={type(e).__name__}: {str(e)}"
            )
            # Roll back the transaction to recover from error state
            self.session.rollback()
            return []

    def _search_mysql_fulltext(
        self,
        query: str,
        user_id: str,
        assistant_id: str | None,
        session_id: str | None,
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
                short_query = self.session.query(ShortTermMemory).filter(
                    ShortTermMemory.user_id == user_id
                )
                if assistant_id:
                    short_query = short_query.filter(
                        ShortTermMemory.assistant_id == assistant_id
                    )
                if session_id:
                    short_query = short_query.filter(
                        ShortTermMemory.session_id == session_id
                    )
                short_count = short_query.count()
                if short_count == 0:
                    logger.debug(
                        "No short-term memories found in database, skipping FULLTEXT search"
                    )
                    search_short_term = False

            if search_long_term:
                long_query = self.session.query(LongTermMemory).filter(
                    LongTermMemory.user_id == user_id
                )
                if assistant_id:
                    long_query = long_query.filter(
                        LongTermMemory.assistant_id == assistant_id
                    )
                # NOTE: No session filter for long-term memories (cross-session access)
                long_count = long_query.count()
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
                    # Build filter clauses
                    category_clause = ""
                    session_clause = ""
                    params = {"query": query, "user_id": user_id}

                    # BEHAVIOR: Short-term memory is accessible to all assistants for the same user
                    # No assistant_id filter applied to short-term memory

                    if session_id:
                        session_clause = "AND session_id = :session_id"
                        params["session_id"] = session_id

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
                        WHERE user_id = :user_id
                        {session_clause}
                        AND MATCH(searchable_content, summary) AGAINST(:query IN NATURAL LANGUAGE MODE)
                        {category_clause}
                        ORDER BY search_score DESC
                        LIMIT :short_limit
                    """
                    )

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
                    # Build filter clauses
                    category_clause = ""
                    assistant_clause = ""
                    params = {"query": query, "user_id": user_id}

                    # BEHAVIOR: Multi-assistant isolation for long-term memory
                    if assistant_id:
                        # Specific assistant: see shared (NULL) OR own memories
                        assistant_clause = (
                            "AND (assistant_id IS NULL OR assistant_id = :assistant_id)"
                        )
                        params["assistant_id"] = assistant_id
                    else:
                        # No assistant: see ONLY shared memories (NULL)
                        assistant_clause = "AND assistant_id IS NULL"

                    # NOTE: No session filter for long-term memories (cross-session access)

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
                        WHERE user_id = :user_id
                        {assistant_clause}
                        AND MATCH(searchable_content, summary) AGAINST(:query IN NATURAL LANGUAGE MODE)
                        {category_clause}
                        ORDER BY search_score DESC
                        LIMIT :long_limit
                    """
                    )

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
                f"MySQL FULLTEXT search failed | query='{query[:50]}...' | user_id={user_id} | "
                f"assistant_id={assistant_id} | session_id={session_id} | "
                f"error={type(e).__name__}: {str(e)}"
            )
            # Roll back the transaction to recover from error state
            self.session.rollback()
            return []

    def _search_postgresql_fts(
        self,
        query: str,
        user_id: str,
        assistant_id: str | None,
        session_id: str | None,
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
            # Remove/sanitize special characters that cause tsquery syntax errors
            import re

            # Remove special characters, keep only alphanumeric and spaces
            sanitized_query = re.sub(r"[^\w\s]", " ", query)
            # Convert to tsquery format (join words with &)
            tsquery_text = " & ".join(sanitized_query.split())

            # Search short-term memory if requested
            if search_short_term:

                # Build filter clauses safely
                category_clause = ""
                session_clause = ""

                # BEHAVIOR: Short-term memory is accessible to all assistants for the same user
                # No assistant_id filter applied to short-term memory

                if session_id:
                    session_clause = "AND session_id = :session_id"

                if category_filter:
                    category_clause = "AND category_primary = ANY(:category_list)"

                # Use direct SQL to avoid SQLAlchemy Row conversion issues
                short_sql = text(
                    f"""
                    SELECT memory_id, processed_data, importance_score, created_at, summary, category_primary,
                           ts_rank(search_vector, to_tsquery('english', :query)) as search_score,
                           'short_term' as memory_type, 'postgresql_fts' as search_strategy
                    FROM short_term_memory
                    WHERE user_id = :user_id
                    {session_clause}
                    AND search_vector @@ to_tsquery('english', :query)
                    {category_clause}
                    ORDER BY search_score DESC
                    LIMIT :limit
                """
                )

                params = {
                    "user_id": user_id,
                    "query": tsquery_text,
                    "limit": short_limit,
                }
                if session_id:
                    params["session_id"] = session_id
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
                # Build filter clauses safely
                category_clause = ""
                assistant_clause = ""

                # BEHAVIOR: Multi-assistant isolation for long-term memory
                if assistant_id:
                    # Specific assistant: see shared (NULL) OR own memories
                    assistant_clause = (
                        "AND (assistant_id IS NULL OR assistant_id = :assistant_id)"
                    )
                else:
                    # No assistant: see ONLY shared memories (NULL)
                    assistant_clause = "AND assistant_id IS NULL"

                # NOTE: No session filter for long-term memories (cross-session access)

                if category_filter:
                    category_clause = "AND category_primary = ANY(:category_list)"

                # Use direct SQL to avoid SQLAlchemy Row conversion issues
                long_sql = text(
                    f"""
                    SELECT memory_id, processed_data, importance_score, created_at, summary, category_primary,
                           ts_rank(search_vector, to_tsquery('english', :query)) as search_score,
                           'long_term' as memory_type, 'postgresql_fts' as search_strategy
                    FROM long_term_memory
                    WHERE user_id = :user_id
                    {assistant_clause}
                    AND search_vector @@ to_tsquery('english', :query)
                    {category_clause}
                    ORDER BY search_score DESC
                    LIMIT :limit
                """
                )

                params = {
                    "user_id": user_id,
                    "query": tsquery_text,
                    "limit": long_limit,
                }
                if assistant_id:
                    params["assistant_id"] = assistant_id
                # NOTE: No session_id param for long-term
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
                f"PostgreSQL FTS search failed | query='{query[:50]}...' | user_id={user_id} | "
                f"assistant_id={assistant_id} | session_id={session_id} | "
                f"error={type(e).__name__}: {str(e)}"
            )
            # Roll back the transaction to recover from error state
            self.session.rollback()
            return []

    def _search_like_fallback(
        self,
        query: str,
        user_id: str,
        assistant_id: str | None,
        session_id: str | None,
        category_filter: list[str] | None,
        limit: int,
        search_short_term: bool,
        search_long_term: bool,
    ) -> list[dict[str, Any]]:
        """Fallback LIKE-based search with improved flexibility"""
        logger.debug(
            f"Starting LIKE fallback search for query: '{query}' in user_id: '{user_id}', assistant_id: '{assistant_id}', session_id: '{session_id}'"
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

            # Build base filter conditions
            filter_conditions = [
                ShortTermMemory.user_id == user_id,
                or_(*search_conditions),
            ]

            # BEHAVIOR: Short-term memory is accessible to all assistants for the same user
            # No assistant_id filter applied to short-term memory

            if session_id:
                filter_conditions.append(ShortTermMemory.session_id == session_id)

            short_query = self.session.query(ShortTermMemory).filter(
                and_(*filter_conditions)
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

            # Build base filter conditions
            filter_conditions = [
                LongTermMemory.user_id == user_id,
                or_(*search_conditions),
            ]

            # BEHAVIOR: Multi-assistant isolation for long-term memory
            if assistant_id:
                # Specific assistant: see shared (NULL) OR own memories
                filter_conditions.append(
                    or_(
                        LongTermMemory.assistant_id.is_(None),
                        LongTermMemory.assistant_id == assistant_id,
                    )
                )
            else:
                # No assistant: see ONLY shared memories (NULL)
                filter_conditions.append(LongTermMemory.assistant_id.is_(None))

            # NOTE: No session filter for long-term memories
            # Long-term memories should be accessible across all sessions for the same user

            long_query = self.session.query(LongTermMemory).filter(
                and_(*filter_conditions)
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
        user_id: str,
        assistant_id: str | None,
        session_id: str | None,
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
                ShortTermMemory.user_id == user_id
            )

            # BEHAVIOR: Short-term memory is accessible to all assistants for the same user
            # No assistant_id filter applied to short-term memory

            if session_id:
                short_query = short_query.filter(
                    ShortTermMemory.session_id == session_id
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
                LongTermMemory.user_id == user_id
            )

            # BEHAVIOR: Multi-assistant isolation for long-term memory
            if assistant_id:
                # Specific assistant: see shared (NULL) OR own memories
                long_query = long_query.filter(
                    or_(
                        LongTermMemory.assistant_id.is_(None),
                        LongTermMemory.assistant_id == assistant_id,
                    )
                )
            else:
                # No assistant: see ONLY shared memories (NULL)
                long_query = long_query.filter(LongTermMemory.assistant_id.is_(None))

            # NOTE: No session filter for long-term memories (cross-session access)
            # Long-term memories should be accessible across all sessions for the same user

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
        except (ValueError, TypeError, AttributeError) as e:
            logger.warning(
                f"Invalid date format for recency calculation: {created_at}, error: {e}"
            )
            return 0.0

    def list_memories(
        self,
        user_id: str,
        assistant_id: str | None = None,
        session_id: str | None = None,
        limit: int = 50,
        offset: int = 0,
        memory_type: str = "all",
        sort_by: str = "created_at",
        order: str = "desc",
    ) -> tuple[list[dict[str, Any]], int]:
        """
        List memories with pagination and flexible filtering (for dashboard views)

        Args:
            user_id: User identifier for multi-tenant isolation (REQUIRED)
                     Cannot be None or empty - enforced for security
            assistant_id: Assistant identifier for multi-tenant isolation (optional)
            session_id: Session identifier for conversation grouping (optional)
            limit: Maximum number of results per page
            offset: Number of results to skip
            memory_type: Type of memory ('short_term', 'long_term', or 'all')
            sort_by: Field to sort by ('created_at', 'importance', 'category')
            order: Sort order ('asc' or 'desc')

        Returns:
            Tuple of (results list, total count)

        Raises:
            ValueError: If user_id is None or empty string
        """
        # SECURITY: Validate user_id to prevent cross-user data leaks
        if not user_id or not user_id.strip():
            raise ValueError(
                "user_id cannot be None or empty - required for user isolation and security"
            )

        logger.debug(
            f"[LIST] Listing memories - user_id: '{user_id}' | assistant_id: '{assistant_id}' | "
            f"session_id: '{session_id}' | memory_type: '{memory_type}' | "
            f"sort: {sort_by} {order} | limit: {limit} | offset: {offset}"
        )

        # INPUT VALIDATION - Priority 3
        ALLOWED_SORT_FIELDS = {
            "created_at": "created_at",
            "importance": "importance_score",
            "category": "category_primary",
        }
        ALLOWED_MEMORY_TYPES = ["all", "short_term", "long_term"]
        ALLOWED_ORDERS = ["asc", "desc"]

        if memory_type not in ALLOWED_MEMORY_TYPES:
            logger.warning(
                f"[LIST] Invalid memory_type: {memory_type}, defaulting to 'all'"
            )
            memory_type = "all"

        if sort_by not in ALLOWED_SORT_FIELDS:
            logger.warning(
                f"[LIST] Invalid sort_by: {sort_by}, defaulting to 'created_at'"
            )
            sort_by = "created_at"
        else:
            # Map to actual field name
            sort_by = ALLOWED_SORT_FIELDS[sort_by]

        if order not in ALLOWED_ORDERS:
            logger.warning(f"[LIST] Invalid order: {order}, defaulting to 'desc'")
            order = "desc"

        # Fix ascending sort order - Priority 2
        order_clause = desc if order == "desc" else asc

        try:
            # CRITICAL FIX - Priority 1: Use UNION ALL for memory_type="all"
            if memory_type == "all":
                return self._list_all_memories_combined(
                    user_id,
                    assistant_id,
                    session_id,
                    limit,
                    offset,
                    sort_by,
                    order_clause,
                )
            elif memory_type == "short_term":
                return self._list_single_type_memories(
                    ShortTermMemory,
                    "short_term",
                    user_id,
                    assistant_id,
                    session_id,
                    limit,
                    offset,
                    sort_by,
                    order_clause,
                )
            else:  # long_term
                return self._list_single_type_memories(
                    LongTermMemory,
                    "long_term",
                    user_id,
                    assistant_id,
                    session_id,
                    limit,
                    offset,
                    sort_by,
                    order_clause,
                )

        except (AttributeError, KeyError) as e:
            logger.error(f"[LIST] Invalid sort field access: {e}")
            raise ValueError(f"Invalid sort field: {sort_by}")
        except Exception as e:
            logger.error(f"[LIST] Error listing memories: {e}", exc_info=True)
            raise

    def _list_all_memories_combined(
        self,
        user_id: str,
        assistant_id: str | None,
        session_id: str | None,
        limit: int,
        offset: int,
        sort_by: str,
        order_clause,
    ) -> tuple[list[dict[str, Any]], int]:
        """
        List memories from both tables using UNION ALL (database-level pagination)

        This fixes the critical memory exhaustion issue by using database-level
        pagination instead of loading all results into memory.
        """
        try:
            # Build short-term query
            # CRITICAL: All columns must have explicit .label() for UNION ALL subquery column access
            short_select = self.session.query(
                ShortTermMemory.memory_id.label("memory_id"),
                literal("short_term").label("memory_type"),
                ShortTermMemory.processed_data.label("processed_data"),
                ShortTermMemory.importance_score.label("importance_score"),
                ShortTermMemory.created_at.label("created_at"),
                ShortTermMemory.summary.label("summary"),
                ShortTermMemory.category_primary.label("category_primary"),
                ShortTermMemory.user_id.label("user_id"),
                ShortTermMemory.assistant_id.label("assistant_id"),
                ShortTermMemory.session_id.label("session_id"),
            )

            # SECURITY: user_id filter is ALWAYS applied (no longer conditional)
            short_select = short_select.filter(ShortTermMemory.user_id == user_id)
            if assistant_id is not None:
                short_select = short_select.filter(
                    ShortTermMemory.assistant_id == assistant_id
                )
            if session_id is not None:
                short_select = short_select.filter(
                    ShortTermMemory.session_id == session_id
                )

            # Build long-term query
            # CRITICAL: All columns must have explicit .label() for UNION ALL subquery column access
            long_select = self.session.query(
                LongTermMemory.memory_id.label("memory_id"),
                literal("long_term").label("memory_type"),
                LongTermMemory.processed_data.label("processed_data"),
                LongTermMemory.importance_score.label("importance_score"),
                LongTermMemory.created_at.label("created_at"),
                LongTermMemory.summary.label("summary"),
                LongTermMemory.category_primary.label("category_primary"),
                LongTermMemory.user_id.label("user_id"),
                LongTermMemory.assistant_id.label("assistant_id"),
                LongTermMemory.session_id.label("session_id"),
            )

            # SECURITY: user_id filter is ALWAYS applied (no longer conditional)
            long_select = long_select.filter(LongTermMemory.user_id == user_id)
            if assistant_id is not None:
                long_select = long_select.filter(
                    LongTermMemory.assistant_id == assistant_id
                )
            if session_id is not None:
                long_select = long_select.filter(
                    LongTermMemory.session_id == session_id
                )

            # Combine with UNION ALL
            combined = union_all(short_select, long_select).subquery()

            # Get total count efficiently
            count_query = self.session.query(func.count()).select_from(combined)
            total_count = count_query.scalar()

            # Apply sorting and pagination at database level
            # Use bracket notation for reliable column access in UNION ALL subqueries
            # Additional safety: Verify column exists in combined result set
            if sort_by not in combined.c:
                logger.warning(
                    f"[LIST] Sort field '{sort_by}' not found in combined results, falling back to 'created_at'"
                )
                sort_by = "created_at"
            sort_column = combined.c[sort_by]
            query = self.session.query(combined).order_by(order_clause(sort_column))
            results = query.limit(limit).offset(offset).all()

            # Convert to dictionaries
            formatted_results = []
            for row in results:
                formatted_results.append(
                    {
                        "memory_id": row.memory_id,
                        "memory_type": row.memory_type,
                        "processed_data": row.processed_data,
                        "importance_score": row.importance_score,
                        "created_at": row.created_at,
                        "summary": row.summary,
                        "category_primary": row.category_primary,
                        "user_id": row.user_id,
                        "assistant_id": row.assistant_id,
                        "session_id": row.session_id,
                    }
                )

            logger.debug(
                f"[LIST] Combined query completed - {len(formatted_results)} results returned (total: {total_count})"
            )

            return formatted_results, total_count

        except Exception as e:
            logger.error(f"[LIST] Error in combined memory query: {e}", exc_info=True)
            raise

    def _list_single_type_memories(
        self,
        model_class,
        memory_type: str,
        user_id: str,
        assistant_id: str | None,
        session_id: str | None,
        limit: int,
        offset: int,
        sort_by: str,
        order_clause,
    ) -> tuple[list[dict[str, Any]], int]:
        """
        List memories from a single table with pagination

        More efficient than combined query when filtering by specific memory type.
        """
        try:
            # Build base query
            query = self.session.query(model_class)

            # SECURITY: user_id filter is ALWAYS applied (no longer conditional)
            query = query.filter(model_class.user_id == user_id)

            if assistant_id is not None:
                query = query.filter(model_class.assistant_id == assistant_id)

            if session_id is not None:
                query = query.filter(model_class.session_id == session_id)

            # Get total count
            total_count = query.count()

            # Apply sorting and pagination
            sort_field = getattr(model_class, sort_by)
            query = query.order_by(order_clause(sort_field))
            results = query.limit(limit).offset(offset).all()

            # Convert to dictionaries
            formatted_results = []
            for result in results:
                formatted_results.append(
                    {
                        "memory_id": result.memory_id,
                        "memory_type": memory_type,
                        "processed_data": result.processed_data,
                        "importance_score": result.importance_score,
                        "created_at": result.created_at,
                        "summary": result.summary,
                        "category_primary": result.category_primary,
                        "user_id": result.user_id,
                        "assistant_id": result.assistant_id,
                        "session_id": result.session_id,
                    }
                )

            logger.debug(
                f"[LIST] Single type query completed - {len(formatted_results)} results returned (total: {total_count})"
            )

            return formatted_results, total_count

        except Exception as e:
            logger.error(
                f"[LIST] Error in single type memory query: {e}", exc_info=True
            )
            raise

    def get_list_metadata(
        self,
        user_id: str,
        assistant_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Get metadata for list endpoint (available filters and stats)

        Args:
            user_id: User identifier for multi-tenant isolation (REQUIRED)
                     Cannot be None or empty - enforced for security
            assistant_id: Optional assistant filter for scoping metadata

        Returns:
            Dictionary with available_filters and stats

        Raises:
            ValueError: If user_id is None or empty string
        """
        # SECURITY: Validate user_id to prevent cross-user data leaks
        if not user_id or not user_id.strip():
            raise ValueError(
                "user_id cannot be None or empty - required for user isolation and security"
            )

        logger.debug(
            f"[METADATA] Getting list metadata - user_id: '{user_id}' | assistant_id: '{assistant_id}'"
        )

        try:
            metadata = {
                "available_filters": {
                    "user_ids": [],
                    "assistant_ids": [],
                    "session_ids": [],
                    "memory_types": ["short_term", "long_term"],
                },
                "stats": {
                    "total_memories": 0,
                    "by_type": {"short_term": 0, "long_term": 0},
                    "by_category": {},
                },
            }

            # Get distinct user_ids (from both tables)
            short_query = self.session.query(ShortTermMemory.user_id).distinct()
            long_query = self.session.query(LongTermMemory.user_id).distinct()

            # SECURITY: user_id filter is ALWAYS applied (no longer conditional)
            short_query = short_query.filter(ShortTermMemory.user_id == user_id)
            long_query = long_query.filter(LongTermMemory.user_id == user_id)

            short_users = short_query.all()
            long_users = long_query.all()
            all_users = set([u[0] for u in short_users] + [u[0] for u in long_users])
            metadata["available_filters"]["user_ids"] = sorted(all_users)

            # Get distinct assistant_ids
            base_short_query = self.session.query(
                ShortTermMemory.assistant_id
            ).distinct()
            base_long_query = self.session.query(LongTermMemory.assistant_id).distinct()

            # SECURITY: user_id filter is ALWAYS applied (no longer conditional)
            base_short_query = base_short_query.filter(
                ShortTermMemory.user_id == user_id
            )
            base_long_query = base_long_query.filter(LongTermMemory.user_id == user_id)

            # Apply assistant_id filter if provided
            if assistant_id is not None:
                base_short_query = base_short_query.filter(
                    ShortTermMemory.assistant_id == assistant_id
                )
                base_long_query = base_long_query.filter(
                    LongTermMemory.assistant_id == assistant_id
                )

            short_assistants = base_short_query.all()
            long_assistants = base_long_query.all()
            all_assistants = set(
                [a[0] for a in short_assistants if a[0]]
                + [a[0] for a in long_assistants if a[0]]
            )
            metadata["available_filters"]["assistant_ids"] = sorted(all_assistants)

            # Get distinct session_ids
            short_sessions_query = self.session.query(
                ShortTermMemory.session_id
            ).distinct()
            long_sessions_query = self.session.query(
                LongTermMemory.session_id
            ).distinct()

            # SECURITY: user_id filter is ALWAYS applied (no longer conditional)
            short_sessions_query = short_sessions_query.filter(
                ShortTermMemory.user_id == user_id
            )
            long_sessions_query = long_sessions_query.filter(
                LongTermMemory.user_id == user_id
            )

            short_sessions = short_sessions_query.all()
            long_sessions = long_sessions_query.all()
            all_sessions = set(
                [s[0] for s in short_sessions if s[0]]
                + [s[0] for s in long_sessions if s[0]]
            )
            metadata["available_filters"]["session_ids"] = sorted(all_sessions)

            # Get counts
            short_count_query = self.session.query(ShortTermMemory)
            long_count_query = self.session.query(LongTermMemory)

            # SECURITY: user_id filter is ALWAYS applied (no longer conditional)
            short_count_query = short_count_query.filter(
                ShortTermMemory.user_id == user_id
            )
            long_count_query = long_count_query.filter(
                LongTermMemory.user_id == user_id
            )

            short_count = short_count_query.count()
            long_count = long_count_query.count()

            metadata["stats"]["by_type"]["short_term"] = short_count
            metadata["stats"]["by_type"]["long_term"] = long_count
            metadata["stats"]["total_memories"] = short_count + long_count

            # Get category breakdown (from both tables)
            short_categories_query = self.session.query(
                ShortTermMemory.category_primary, func.count().label("count")
            )
            long_categories_query = self.session.query(
                LongTermMemory.category_primary, func.count().label("count")
            )

            # SECURITY: user_id filter is ALWAYS applied (no longer conditional)
            short_categories_query = short_categories_query.filter(
                ShortTermMemory.user_id == user_id
            )
            long_categories_query = long_categories_query.filter(
                LongTermMemory.user_id == user_id
            )

            short_categories = short_categories_query.group_by(
                ShortTermMemory.category_primary
            ).all()

            long_categories = long_categories_query.group_by(
                LongTermMemory.category_primary
            ).all()

            # Combine category counts
            category_counts = {}
            for cat, count in short_categories:
                category_counts[cat] = category_counts.get(cat, 0) + count
            for cat, count in long_categories:
                category_counts[cat] = category_counts.get(cat, 0) + count

            metadata["stats"]["by_category"] = category_counts

            logger.debug(
                f"[METADATA] Completed - {metadata['stats']['total_memories']} total memories"
            )

            return metadata

        except Exception as e:
            logger.error(
                f"Failed to get list metadata | user_id={user_id} | assistant_id={assistant_id} | "
                f"error={type(e).__name__}: {str(e)}"
            )
            return {
                "available_filters": {
                    "user_ids": [],
                    "assistant_ids": [],
                    "session_ids": [],
                    "memory_types": ["short_term", "long_term"],
                },
                "stats": {
                    "total_memories": 0,
                    "by_type": {"short_term": 0, "long_term": 0},
                    "by_category": {},
                },
            }
