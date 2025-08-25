"""
Database Manager - Pydantic-based memory storage with entity indexing
"""

import json
import sqlite3
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger

from ..utils.exceptions import DatabaseError
from ..utils.pydantic_models import MemoryCategoryType, ProcessedMemory, RetentionType


class DatabaseManager:
    """Manages Pydantic-based memory storage with entity indexing and FTS search"""

    def __init__(self, database_connect: str, template: str = "basic"):
        self.database_connect = database_connect
        self.template = template
        self.db_path = self._parse_connection_string(database_connect)

    def _parse_connection_string(self, connect_str: str) -> str:
        """Parse database connection string"""
        if connect_str.startswith("sqlite:///"):
            return connect_str.replace("sqlite:///", "")
        elif connect_str.startswith("sqlite://"):
            return connect_str.replace("sqlite://", "")
        else:
            # For now, only SQLite is implemented
            raise DatabaseError(f"Unsupported database type: {connect_str}")

    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection with FTS5 support"""
        try:
            # Ensure directory exists
            db_dir = Path(self.db_path).parent
            db_dir.mkdir(parents=True, exist_ok=True)

            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row  # Enable dict-like access

            # Enable FTS features
            conn.execute("PRAGMA enable_fts3_tokenizer=1")
            # Set up other performance optimizations
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("PRAGMA cache_size=10000")

            return conn
        except Exception as e:
            raise DatabaseError(f"Failed to connect to database: {e}")

    def initialize_schema(self):
        """Initialize database schema based on template"""
        try:
            # Check if FTS5 is available
            if not self._check_fts5_support():
                logger.warning(
                    "FTS5 not available, search functionality will be limited"
                )

            # Read and execute schema from file
            schema_path = (
                Path(__file__).parent.parent
                / "database"
                / "templates"
                / "schemas"
                / f"{self.template}.sql"
            )

            if schema_path.exists():
                with open(schema_path) as f:
                    schema_sql = f.read()

                with self._get_connection() as conn:
                    # Execute schema using executescript for better multi-statement handling
                    try:
                        conn.executescript(schema_sql)
                        logger.info("Database schema initialized successfully")
                    except sqlite3.Error as e:
                        logger.warning(
                            f"Schema execution issue: {e}, falling back to statement-by-statement"
                        )
                        # Fallback to statement-by-statement execution
                        self._execute_schema_statements(conn, schema_sql)

            else:
                # Fallback to basic schema
                self._create_basic_schema()

        except Exception as e:
            logger.error(f"Failed to initialize schema: {e}")
            # Fallback to basic schema
            self._create_basic_schema()

    def _check_fts5_support(self) -> bool:
        """Check if FTS5 is supported in this SQLite installation"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("CREATE VIRTUAL TABLE fts_test USING fts5(content)")
                cursor.execute("DROP TABLE fts_test")
                return True
        except sqlite3.OperationalError:
            return False

    def _execute_schema_statements(self, conn: sqlite3.Connection, schema_sql: str):
        """Execute schema statements one by one with better error handling"""
        # Split by semicolons but be smarter about it
        statements = []
        current_statement = []
        in_trigger = False

        for line in schema_sql.split("\n"):
            line = line.strip()
            if not line or line.startswith("--"):
                continue

            if line.upper().startswith("CREATE TRIGGER"):
                in_trigger = True
            elif line.upper().startswith("END;") and in_trigger:
                current_statement.append(line)
                statements.append("\n".join(current_statement))
                current_statement = []
                in_trigger = False
                continue

            current_statement.append(line)

            if line.endswith(";") and not in_trigger:
                statements.append("\n".join(current_statement))
                current_statement = []

        # Execute each statement
        for statement in statements:
            if statement.strip():
                try:
                    conn.execute(statement)
                except sqlite3.Error as e:
                    logger.debug(f"Schema statement warning: {e}")

        conn.commit()

    def _create_basic_schema(self):
        """Create basic schema if SQL file is not available"""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Basic tables for fallback
            cursor.execute(
                """
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
            """
            )

            cursor.execute(
                """
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
                    summary TEXT NOT NULL
                )
            """
            )

            cursor.execute(
                """
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
            """
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS memory_entities (
                    entity_id TEXT PRIMARY KEY,
                    memory_id TEXT NOT NULL,
                    memory_type TEXT NOT NULL,
                    entity_type TEXT NOT NULL,
                    entity_value TEXT NOT NULL,
                    relevance_score REAL NOT NULL DEFAULT 0.5,
                    entity_context TEXT,
                    namespace TEXT NOT NULL DEFAULT 'default',
                    created_at TIMESTAMP NOT NULL
                )
            """
            )

            conn.commit()
            logger.info("Basic database schema created")

    def store_chat_history(
        self,
        chat_id: str,
        user_input: str,
        ai_output: str,
        model: str,
        timestamp: datetime,
        session_id: str,
        namespace: str = "default",
        tokens_used: int = 0,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Store chat history"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO chat_history
                (chat_id, user_input, ai_output, model, timestamp, session_id, namespace, tokens_used, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    chat_id,
                    user_input,
                    ai_output,
                    model,
                    timestamp,
                    session_id,
                    namespace,
                    tokens_used,
                    json.dumps(metadata or {}),
                ),
            )
            conn.commit()

    def get_chat_history(
        self,
        namespace: str = "default",
        session_id: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Get chat history with optional session filtering"""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            if session_id:
                cursor.execute(
                    """
                    SELECT chat_id, user_input, ai_output, model, timestamp,
                           session_id, namespace, tokens_used, metadata
                    FROM chat_history
                    WHERE namespace = ? AND session_id = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                    """,
                    (namespace, session_id, limit),
                )
            else:
                cursor.execute(
                    """
                    SELECT chat_id, user_input, ai_output, model, timestamp,
                           session_id, namespace, tokens_used, metadata
                    FROM chat_history
                    WHERE namespace = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                    """,
                    (namespace, limit),
                )

            rows = cursor.fetchall()

            # Convert to list of dictionaries and parse metadata JSON
            result = []
            for row in rows:
                row_dict = dict(row)
                try:
                    row_dict["metadata"] = json.loads(row_dict["metadata"] or "{}")
                except (json.JSONDecodeError, TypeError):
                    row_dict["metadata"] = {}
                result.append(row_dict)

            return result

    def store_processed_memory(
        self, memory: ProcessedMemory, chat_id: str, namespace: str = "default"
    ) -> str:
        """Store a processed memory with entity indexing"""

        if not memory.should_store:
            logger.debug(f"Memory not stored: {memory.storage_reasoning}")
            return ""

        memory_id = str(uuid.uuid4())
        storage_location = self._determine_storage_location(memory)

        with self._get_connection() as conn:
            cursor = conn.cursor()

            try:
                if storage_location == "short_term_memory":
                    self._store_short_term_memory(
                        cursor, memory_id, memory, chat_id, namespace
                    )
                elif storage_location == "long_term_memory":
                    self._store_long_term_memory(
                        cursor, memory_id, memory, chat_id, namespace
                    )
                elif storage_location == "rules_memory":
                    self._store_rules_memory(cursor, memory_id, memory, namespace)

                # Store entities for indexing
                self._store_entities(
                    cursor, memory_id, memory, storage_location, namespace
                )

                conn.commit()
                logger.debug(f"Stored memory {memory_id} in {storage_location}")
                return memory_id

            except Exception as e:
                conn.rollback()
                logger.error(f"Failed to store memory: {e}")
                raise DatabaseError(f"Failed to store memory: {e}")

    def _store_short_term_memory(
        self,
        cursor: sqlite3.Cursor,
        memory_id: str,
        memory: ProcessedMemory,
        chat_id: str,
        namespace: str,
    ):
        """Store memory in short-term table"""
        # Ensure we have a valid timestamp (timezone-naive for SQLite compatibility)
        created_at = memory.timestamp
        if created_at is None:
            created_at = datetime.now()
        elif hasattr(created_at, "replace"):
            # Make timezone-naive if timezone-aware
            created_at = created_at.replace(tzinfo=None)

        expires_at = datetime.now() + timedelta(days=7)  # 7-day expiration

        cursor.execute(
            """
            INSERT INTO short_term_memory
            (memory_id, chat_id, processed_data, importance_score, category_primary,
             retention_type, namespace, created_at, expires_at, access_count,
             searchable_content, summary)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                memory_id,
                chat_id,
                memory.model_dump_json(),
                memory.importance.importance_score,
                memory.category.primary_category.value,
                memory.importance.retention_type.value,
                namespace,
                created_at,
                expires_at,
                0,
                memory.searchable_content,
                memory.summary,
            ),
        )

    def _store_long_term_memory(
        self,
        cursor: sqlite3.Cursor,
        memory_id: str,
        memory: ProcessedMemory,
        chat_id: str,
        namespace: str,
    ):
        """Store memory in long-term table"""
        # Ensure we have a valid timestamp (timezone-naive for SQLite compatibility)
        created_at = memory.timestamp
        if created_at is None:
            created_at = datetime.now()
        elif hasattr(created_at, "replace"):
            # Make timezone-naive if timezone-aware
            created_at = created_at.replace(tzinfo=None)

        cursor.execute(
            """
            INSERT INTO long_term_memory
            (memory_id, original_chat_id, processed_data, importance_score, category_primary,
             retention_type, namespace, created_at, access_count, searchable_content, summary,
             novelty_score, relevance_score, actionability_score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                memory_id,
                chat_id,
                memory.model_dump_json(),
                memory.importance.importance_score,
                memory.category.primary_category.value,
                memory.importance.retention_type.value,
                namespace,
                created_at,
                0,
                memory.searchable_content,
                memory.summary,
                memory.importance.novelty_score,
                memory.importance.relevance_score,
                memory.importance.actionability_score,
            ),
        )

    def _store_rules_memory(
        self,
        cursor: sqlite3.Cursor,
        memory_id: str,
        memory: ProcessedMemory,
        namespace: str,
    ):
        """Store rule-type memory in rules table"""
        # Ensure we have a valid timestamp (timezone-naive for SQLite compatibility)
        created_at = memory.timestamp
        if created_at is None:
            created_at = datetime.now()
        elif hasattr(created_at, "replace"):
            # Make timezone-naive if timezone-aware
            created_at = created_at.replace(tzinfo=None)

        cursor.execute(
            """
            INSERT INTO rules_memory
            (rule_id, rule_text, rule_type, priority, active, namespace,
             created_at, updated_at, processed_data)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                memory_id,
                memory.summary,
                "rule",
                5,
                True,
                namespace,
                created_at,
                created_at,
                memory.model_dump_json(),
            ),
        )

    def _store_entities(
        self,
        cursor: sqlite3.Cursor,
        memory_id: str,
        memory: ProcessedMemory,
        memory_type: str,
        namespace: str,
    ):
        """Store extracted entities for indexing"""

        # Simple entities (lists), In future we can make it to dynamically handle more entity types

        entity_mappings = [
            (memory.entities.people, "person"),
            (memory.entities.technologies, "technology"),
            (memory.entities.topics, "topic"),
            (memory.entities.skills, "skill"),
            (memory.entities.projects, "project"),
            (memory.entities.keywords, "keyword"),
        ]

        for entity_list, entity_type in entity_mappings:
            for entity_value in entity_list:
                entity_id = str(uuid.uuid4())
                cursor.execute(
                    """
                    INSERT INTO memory_entities
                    (entity_id, memory_id, memory_type, entity_type, entity_value,
                     relevance_score, namespace, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        entity_id,
                        memory_id,
                        memory_type.replace("_memory", ""),
                        entity_type,
                        entity_value,
                        0.8,
                        namespace,
                        datetime.now(),
                    ),
                )

        # Structured entities (with metadata)
        for structured_entity in memory.entities.structured_entities:
            entity_id = str(uuid.uuid4())
            cursor.execute(
                """
                INSERT INTO memory_entities
                (entity_id, memory_id, memory_type, entity_type, entity_value,
                 relevance_score, entity_context, namespace, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    entity_id,
                    memory_id,
                    memory_type.replace("_memory", ""),
                    structured_entity.entity_type.value,
                    structured_entity.value,
                    structured_entity.relevance_score,
                    structured_entity.context,
                    namespace,
                    datetime.now(),
                ),
            )

    def search_memories(
        self,
        query: str,
        namespace: str = "default",
        category_filter: Optional[List[str]] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Advanced memory search with hybrid approach: FTS + Entity + Category filtering"""
        all_results = []

        with self._get_connection() as conn:
            cursor = conn.cursor()

            # 1. Try FTS search first (most relevant)
            fts_results = self._execute_fts_search(
                cursor, query, namespace, category_filter, limit
            )
            if fts_results:
                for result in fts_results:
                    result["search_strategy"] = "fts_search"
                    result["search_score"] = 1.0
                    all_results.append(result)

            # 2. Entity-based search for better context matching
            entity_results = self._execute_entity_search(
                cursor, query, namespace, category_filter, limit
            )
            for result in entity_results:
                result["search_strategy"] = "entity_search"
                result["search_score"] = 0.8
                all_results.append(result)

            # 3. Category-based search if specified
            if category_filter:
                category_results = self._execute_category_search(
                    cursor, query, namespace, category_filter, limit
                )
                for result in category_results:
                    result["search_strategy"] = "category_search"
                    result["search_score"] = 0.6
                    all_results.append(result)

            # 4. Fallback to LIKE search if no other results
            if not all_results:
                like_results = self._execute_like_search(
                    cursor, query, namespace, category_filter, limit
                )
                for result in like_results:
                    result["search_strategy"] = "like_search"
                    result["search_score"] = 0.4
                    all_results.append(result)

            # Remove duplicates while preserving the best search score
            unique_results = {}
            for result in all_results:
                memory_id = result.get("memory_id")
                if (
                    memory_id not in unique_results
                    or result["search_score"]
                    > unique_results[memory_id]["search_score"]
                ):
                    unique_results[memory_id] = result

            # Sort by composite score (search_score + importance + recency)
            final_results = list(unique_results.values())
            final_results.sort(
                key=lambda x: (
                    x.get("search_score", 0) * 0.4
                    + x.get("importance_score", 0) * 0.4
                    + self._calculate_recency_score(x.get("created_at")) * 0.2
                ),
                reverse=True,
            )

            return final_results[:limit]

    def _execute_fts_search(
        self,
        cursor,
        query: str,
        namespace: str,
        category_filter: Optional[List[str]],
        limit: int,
    ):
        """Execute FTS5 search"""
        try:
            # Build FTS query with category filter
            fts_query = f'"{query}"' if query else "*"
            category_clause = ""
            params = [fts_query, namespace]

            if category_filter:
                category_placeholders = ",".join("?" * len(category_filter))
                category_clause = (
                    f"AND fts.category_primary IN ({category_placeholders})"
                )
                params.extend(category_filter)

            params.append(limit)

            # Build the complete query string safely
            # category_clause is safely constructed with proper placeholders above
            base_query = (  # nosec B608
                """
                SELECT
                    fts.memory_id, fts.memory_type, fts.category_primary,
                    CASE
                        WHEN fts.memory_type = 'short_term' THEN st.processed_data
                        WHEN fts.memory_type = 'long_term' THEN lt.processed_data
                        WHEN fts.memory_type = 'rules' THEN r.processed_data
                    END as processed_data,
                    CASE
                        WHEN fts.memory_type = 'short_term' THEN st.importance_score
                        WHEN fts.memory_type = 'long_term' THEN lt.importance_score
                        ELSE 0.5
                    END as importance_score,
                    CASE
                        WHEN fts.memory_type = 'short_term' THEN st.created_at
                        WHEN fts.memory_type = 'long_term' THEN lt.created_at
                        WHEN fts.memory_type = 'rules' THEN r.created_at
                    END as created_at,
                    fts.summary,
                    rank
                FROM memory_search_fts fts
                LEFT JOIN short_term_memory st ON fts.memory_id = st.memory_id AND fts.memory_type = 'short_term'
                LEFT JOIN long_term_memory lt ON fts.memory_id = lt.memory_id AND fts.memory_type = 'long_term'
                LEFT JOIN rules_memory r ON fts.memory_id = r.rule_id AND fts.memory_type = 'rules'
                WHERE memory_search_fts MATCH ? AND fts.namespace = ? """
                + category_clause  # nosec B608
                + """
                ORDER BY rank, importance_score DESC
                LIMIT ?
                """
            )

            cursor.execute(
                base_query,
                params,
            )

            return [dict(row) for row in cursor.fetchall()]

        except sqlite3.OperationalError as e:
            logger.debug(f"FTS not available: {e}")
            return []

    def _execute_entity_search(
        self,
        cursor,
        query: str,
        namespace: str,
        category_filter: Optional[List[str]],
        limit: int,
    ):
        """Execute entity-based search"""
        category_clause = ""
        params = [f"%{query}%", namespace]

        if category_filter:
            category_placeholders = ",".join("?" * len(category_filter))
            category_clause = f"AND m.category_primary IN ({category_placeholders})"
            params.extend(category_filter)

        params.append(limit)

        # Build the complete query string safely
        # category_clause is safely constructed with proper placeholders above
        base_query = (  # nosec B608
            """
            SELECT DISTINCT m.memory_id, m.processed_data, m.importance_score, m.created_at,
                   m.summary, m.category_primary, 'long_term' as memory_type,
                   e.entity_type, e.entity_value, e.relevance_score
            FROM long_term_memory m
            JOIN memory_entities e ON m.memory_id = e.memory_id
            WHERE e.entity_value LIKE ? AND m.namespace = ? """
            + category_clause  # nosec B608
            + """
            ORDER BY e.relevance_score DESC, m.importance_score DESC
            LIMIT ?
            """
        )

        cursor.execute(base_query, params)

        return [dict(row) for row in cursor.fetchall()]

    def _execute_category_search(
        self, cursor, query: str, namespace: str, category_filter: List[str], limit: int
    ):
        """Execute category-based search"""
        category_placeholders = ",".join("?" * len(category_filter))
        params = [namespace] + category_filter + [f"%{query}%", f"%{query}%", limit]

        # Build the complete query string safely
        # category_placeholders is safely constructed with proper placeholders above
        base_query = f"""
            SELECT memory_id, processed_data, importance_score, created_at, summary,
                   category_primary, 'long_term' as memory_type
            FROM long_term_memory
            WHERE namespace = ? AND category_primary IN ({category_placeholders})
              AND (searchable_content LIKE ? OR summary LIKE ?)
            ORDER BY importance_score DESC, created_at DESC
            LIMIT ?
            """  # nosec B608

        cursor.execute(base_query, params)

        return [dict(row) for row in cursor.fetchall()]

    def _execute_like_search(
        self,
        cursor,
        query: str,
        namespace: str,
        category_filter: Optional[List[str]],
        limit: int,
    ):
        """Execute fallback LIKE search"""
        results = []

        # Search short-term memory
        category_clause = ""
        params = [namespace, f"%{query}%", f"%{query}%", datetime.now()]

        if category_filter:
            category_placeholders = ",".join("?" * len(category_filter))
            category_clause = f"AND category_primary IN ({category_placeholders})"
            params.extend(category_filter)

        params.append(limit)

        # Build the complete query string safely
        # category_clause is safely constructed with proper placeholders above
        base_query = (  # nosec B608
            """
            SELECT *, 'short_term' as memory_type FROM short_term_memory
            WHERE namespace = ? AND (searchable_content LIKE ? OR summary LIKE ?)
            AND (expires_at IS NULL OR expires_at > ?) """
            + category_clause  # nosec B608
            + """
            ORDER BY importance_score DESC, created_at DESC
            LIMIT ?
            """
        )

        cursor.execute(base_query, params)
        results.extend([dict(row) for row in cursor.fetchall()])

        # Search long-term memory
        params = [namespace, f"%{query}%", f"%{query}%"]
        if category_filter:
            params.extend(category_filter)
        params.append(limit)

        # Build the complete query string safely
        # category_clause is safely constructed with proper placeholders above
        base_query = (  # nosec B608
            """
            SELECT *, 'long_term' as memory_type FROM long_term_memory
            WHERE namespace = ? AND (searchable_content LIKE ? OR summary LIKE ?) """
            + category_clause  # nosec B608
            + """
            ORDER BY importance_score DESC, created_at DESC
            LIMIT ?
            """
        )

        cursor.execute(base_query, params)
        results.extend([dict(row) for row in cursor.fetchall()])

        return results

    def _calculate_recency_score(self, created_at_str: str) -> float:
        """Calculate recency score (0-1, newer = higher)"""
        try:
            if not created_at_str:
                return 0.0
            created_at = datetime.fromisoformat(created_at_str).replace(tzinfo=None)
            days_old = (datetime.now() - created_at).days
            # Exponential decay: score decreases as days increase
            return max(0, 1 - (days_old / 30))  # Full score for recent, 0 after 30 days
        except:
            return 0.0

    def _search_by_entities(
        self, cursor: sqlite3.Cursor, query: str, namespace: str, limit: int
    ) -> List[Dict[str, Any]]:
        """Search memories by entity matching"""
        cursor.execute(
            """
            SELECT
                e.memory_id, e.memory_type, e.relevance_score,
                CASE
                    WHEN e.memory_type = 'short_term' THEN st.processed_data
                    WHEN e.memory_type = 'long_term' THEN lt.processed_data
                END as processed_data,
                CASE
                    WHEN e.memory_type = 'short_term' THEN st.importance_score
                    WHEN e.memory_type = 'long_term' THEN lt.importance_score
                END as importance_score,
                CASE
                    WHEN e.memory_type = 'short_term' THEN st.category_primary
                    WHEN e.memory_type = 'long_term' THEN lt.category_primary
                END as category_primary,
                CASE
                    WHEN e.memory_type = 'short_term' THEN st.created_at
                    WHEN e.memory_type = 'long_term' THEN lt.created_at
                END as created_at
            FROM memory_entities e
            LEFT JOIN short_term_memory st ON e.memory_id = st.memory_id AND e.memory_type = 'short_term'
            LEFT JOIN long_term_memory lt ON e.memory_id = lt.memory_id AND e.memory_type = 'long_term'
            WHERE e.namespace = ? AND e.entity_value LIKE ?
            ORDER BY e.relevance_score DESC, importance_score DESC
            LIMIT ?
        """,
            (namespace, f"%{query}%", limit),
        )

        return [dict(row) for row in cursor.fetchall()]

    def _determine_storage_location(self, memory: ProcessedMemory) -> str:
        """Determine where to store the memory based on its properties"""
        if memory.category.primary_category == MemoryCategoryType.rule:
            return "rules_memory"
        elif memory.importance.retention_type in [
            RetentionType.long_term,
            RetentionType.permanent,
        ]:
            return "long_term_memory"
        else:
            return "short_term_memory"

    def get_memory_stats(self, namespace: str = "default") -> Dict[str, Any]:
        """Get comprehensive memory statistics"""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            stats = {}

            # Basic counts
            cursor.execute(
                "SELECT COUNT(*) FROM chat_history WHERE namespace = ?", (namespace,)
            )
            stats["chat_history_count"] = cursor.fetchone()[0]

            cursor.execute(
                "SELECT COUNT(*) FROM short_term_memory WHERE namespace = ?",
                (namespace,),
            )
            stats["short_term_count"] = cursor.fetchone()[0]

            cursor.execute(
                "SELECT COUNT(*) FROM long_term_memory WHERE namespace = ?",
                (namespace,),
            )
            stats["long_term_count"] = cursor.fetchone()[0]

            cursor.execute(
                "SELECT COUNT(*) FROM rules_memory WHERE namespace = ?", (namespace,)
            )
            stats["rules_count"] = cursor.fetchone()[0]

            cursor.execute(
                "SELECT COUNT(*) FROM memory_entities WHERE namespace = ?", (namespace,)
            )
            stats["total_entities"] = cursor.fetchone()[0]

            # Category breakdown
            cursor.execute(
                """
                SELECT category_primary, COUNT(*) as count
                FROM (
                    SELECT category_primary FROM short_term_memory WHERE namespace = ?
                    UNION ALL
                    SELECT category_primary FROM long_term_memory WHERE namespace = ?
                )
                GROUP BY category_primary
            """,
                (namespace, namespace),
            )

            stats["memories_by_category"] = {
                row[0]: row[1] for row in cursor.fetchall()
            }

            # Average importance
            cursor.execute(
                """
                SELECT AVG(importance_score) FROM (
                    SELECT importance_score FROM short_term_memory WHERE namespace = ?
                    UNION ALL
                    SELECT importance_score FROM long_term_memory WHERE namespace = ?
                )
            """,
                (namespace, namespace),
            )

            avg_importance = cursor.fetchone()[0]
            stats["average_importance"] = avg_importance if avg_importance else 0.0

            return stats

    def clear_memory(
        self, namespace: str = "default", memory_type: Optional[str] = None
    ):
        """Clear memory data with entity cleanup"""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            if memory_type == "short_term":
                cursor.execute(
                    "DELETE FROM memory_entities WHERE namespace = ? AND memory_type = 'short_term'",
                    (namespace,),
                )
                cursor.execute(
                    "DELETE FROM short_term_memory WHERE namespace = ?", (namespace,)
                )
            elif memory_type == "long_term":
                cursor.execute(
                    "DELETE FROM memory_entities WHERE namespace = ? AND memory_type = 'long_term'",
                    (namespace,),
                )
                cursor.execute(
                    "DELETE FROM long_term_memory WHERE namespace = ?", (namespace,)
                )
            elif memory_type == "chat_history":
                cursor.execute(
                    "DELETE FROM chat_history WHERE namespace = ?", (namespace,)
                )
            else:  # Clear all
                cursor.execute(
                    "DELETE FROM memory_entities WHERE namespace = ?", (namespace,)
                )
                cursor.execute(
                    "DELETE FROM short_term_memory WHERE namespace = ?", (namespace,)
                )
                cursor.execute(
                    "DELETE FROM long_term_memory WHERE namespace = ?", (namespace,)
                )
                cursor.execute(
                    "DELETE FROM rules_memory WHERE namespace = ?", (namespace,)
                )
                cursor.execute(
                    "DELETE FROM chat_history WHERE namespace = ?", (namespace,)
                )

            conn.commit()
