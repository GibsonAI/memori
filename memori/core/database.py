"""
Database Manager - Pydantic-based memory storage with entity indexing
"""

import json
import sqlite3
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from loguru import logger

from ..utils.exceptions import DatabaseError, ValidationError
from ..utils.input_validator import DatabaseInputValidator, InputValidator
from ..utils.pydantic_models import (
    ProcessedLongTermMemory,
    ProcessedMemory,
    RetentionType,
)
from ..utils.transaction_manager import TransactionManager, TransactionOperation


class DatabaseManager:
    """Manages Pydantic-based memory storage with streamlined schema and FTS search"""

    # Database type identifier for database-agnostic code
    database_type = "sql"

    def __init__(self, database_connect: str, template: str = "basic"):
        self.database_connect = database_connect
        self.template = template
        self.db_path = self._parse_connection_string(database_connect)
        self.transaction_manager = TransactionManager(self)

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
                    user_id TEXT NOT NULL DEFAULT 'default',
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
                    user_id TEXT NOT NULL DEFAULT 'default',
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
                    user_id TEXT NOT NULL DEFAULT 'default',
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
        user_id: str = "default",
        assistant_id: str = None,
        tokens_used: int = 0,
        metadata: dict[str, Any] | None = None,
    ):
        """Store chat history with input validation and multi-tenant isolation"""
        try:
            # Validate and sanitize all inputs
            validated_data = DatabaseInputValidator.validate_insert_params(
                "chat_history",
                {
                    "chat_id": chat_id,
                    "user_input": user_input,
                    "ai_output": ai_output,
                    "model": model,
                    "timestamp": timestamp,
                    "session_id": session_id,
                    "user_id": user_id,
                    "assistant_id": assistant_id,
                    "tokens_used": max(0, int(tokens_used)) if tokens_used else 0,
                    "metadata": metadata or {},
                },
            )
        except (ValidationError, ValueError) as e:
            logger.error(f"Invalid chat history data: {e}")
            raise DatabaseError(f"Cannot store chat history: {e}")

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO chat_history
                (chat_id, user_input, ai_output, model, timestamp, session_id, user_id, assistant_id, tokens_used, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    validated_data["chat_id"],
                    validated_data["user_input"],
                    validated_data["ai_output"],
                    validated_data["model"],
                    validated_data["timestamp"],
                    validated_data["session_id"],
                    validated_data["user_id"],
                    validated_data["assistant_id"],
                    validated_data["tokens_used"],
                    validated_data["metadata"],
                ),
            )
            conn.commit()

    def get_chat_history(
        self,
        user_id: str = "default",
        session_id: str | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Get chat history with optional session filtering"""
        try:
            # Validate inputs
            user_id = InputValidator.validate_user_id(user_id)
            limit = InputValidator.validate_limit(limit)
            if session_id:
                session_id = InputValidator.validate_memory_id(session_id)
        except ValidationError as e:
            logger.error(f"Invalid chat history parameters: {e}")
            return []

        with self._get_connection() as conn:
            cursor = conn.cursor()

            if session_id:
                cursor.execute(
                    """
                    SELECT chat_id, user_input, ai_output, model, timestamp,
                           session_id, user_id, assistant_id, tokens_used, metadata
                    FROM chat_history
                    WHERE user_id = ? AND session_id = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                    """,
                    (user_id, session_id, limit),
                )
            else:
                cursor.execute(
                    """
                    SELECT chat_id, user_input, ai_output, model, timestamp,
                           session_id, user_id, assistant_id, tokens_used, metadata
                    FROM chat_history
                    WHERE user_id = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                    """,
                    (user_id, limit),
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

    def store_long_term_memory_enhanced(
        self,
        memory: ProcessedLongTermMemory,
        chat_id: str,
        user_id: str = "default",
        assistant_id: str = None,
        session_id: str = "default",
    ) -> str:
        """Store a ProcessedLongTermMemory with enhanced schema using transactions and multi-tenant isolation"""
        try:
            memory_id = str(uuid.uuid4())

            # Validate inputs
            chat_id = InputValidator.validate_memory_id(chat_id)
            user_id = InputValidator.validate_user_id(user_id)

            # Prepare operations for atomic execution
            operations = []

            # Main memory insert operation
            insert_operation = TransactionOperation(
                query="""
                    INSERT INTO long_term_memory (
                        memory_id, original_chat_id, processed_data, importance_score, category_primary,
                        retention_type, user_id, assistant_id, session_id, created_at, searchable_content, summary,
                        novelty_score, relevance_score, actionability_score, classification, memory_importance,
                        topic, entities_json, keywords_json, is_user_context, is_preference, is_skill_knowledge,
                        is_current_project, promotion_eligible, duplicate_of, supersedes_json, related_memories_json,
                        confidence_score, extraction_timestamp, classification_reason, processed_for_duplicates, conscious_processed
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                params=[
                    memory_id,
                    chat_id,
                    json.dumps(memory.model_dump(mode="json")),
                    memory.importance_score,
                    memory.classification.value,
                    "long_term",
                    user_id,
                    assistant_id,
                    session_id,
                    datetime.now().isoformat(),
                    memory.content,
                    memory.summary,
                    0.5,
                    0.5,
                    0.5,  # novelty, relevance, actionability scores
                    memory.classification.value,
                    memory.importance.value,
                    memory.topic,
                    json.dumps(memory.entities),
                    json.dumps(memory.keywords),
                    memory.is_user_context,
                    memory.is_preference,
                    memory.is_skill_knowledge,
                    memory.is_current_project,
                    memory.promotion_eligible,
                    memory.duplicate_of,
                    json.dumps(memory.supersedes),
                    json.dumps(memory.related_memories),
                    memory.confidence_score,
                    memory.extraction_timestamp.isoformat(),
                    memory.classification_reason,
                    False,  # processed_for_duplicates
                    False,  # conscious_processed
                ],
                operation_type="insert",
                table="long_term_memory",
                expected_rows=1,
            )

            operations.append(insert_operation)

            # Execute all operations atomically
            result = self.transaction_manager.execute_atomic_operations(operations)

            if result.success:
                logger.debug(f"Stored enhanced long-term memory {memory_id}")
                return memory_id
            else:
                raise DatabaseError(
                    f"Failed to store enhanced long-term memory: {result.error_message}"
                )

        except ValidationError as e:
            logger.error(f"Invalid memory data: {e}")
            raise DatabaseError(f"Cannot store long-term memory: {e}")
        except Exception as e:
            logger.error(f"Failed to store enhanced long-term memory: {e}")
            raise DatabaseError(f"Failed to store enhanced long-term memory: {e}")

    def _store_short_term_memory(
        self,
        cursor: sqlite3.Cursor,
        memory_id: str,
        memory: ProcessedMemory,
        chat_id: str,
        user_id: str,
        assistant_id: str = None,
        session_id: str = "default",
    ):
        """Store memory in short-term table with multi-tenant isolation"""
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
             retention_type, user_id, assistant_id, session_id, created_at, expires_at, access_count,
             searchable_content, summary)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                memory_id,
                chat_id,
                memory.model_dump_json(),
                memory.importance.importance_score,
                memory.category.primary_category.value,
                memory.importance.retention_type.value,
                user_id,
                assistant_id,
                session_id,
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
        user_id: str,
        assistant_id: str = None,
        session_id: str = "default",
    ):
        """Store memory in long-term table with multi-tenant isolation"""
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
             retention_type, user_id, assistant_id, session_id, created_at, access_count, searchable_content, summary,
             novelty_score, relevance_score, actionability_score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                memory_id,
                chat_id,
                memory.model_dump_json(),
                memory.importance.importance_score,
                memory.category.primary_category.value,
                memory.importance.retention_type.value,
                user_id,
                assistant_id,
                session_id,
                created_at,
                0,
                memory.searchable_content,
                memory.summary,
                memory.importance.novelty_score,
                memory.importance.relevance_score,
                memory.importance.actionability_score,
            ),
        )

    def search_memories(
        self,
        query: str,
        user_id: str = "default",
        category_filter: list[str] | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Advanced memory search with hybrid approach: FTS + Entity + Category filtering"""
        try:
            # Validate and sanitize all input parameters
            validated_params = DatabaseInputValidator.validate_search_params(
                query, user_id, category_filter, limit
            )
            query = validated_params["query"]
            user_id = validated_params["user_id"]
            category_filter = validated_params["category_filter"]
            limit = validated_params["limit"]

        except ValidationError as e:
            logger.error(f"Invalid search parameters: {e}")
            return []

        all_results = []

        with self._get_connection() as conn:
            cursor = conn.cursor()

            # 1. Try FTS search first (most relevant)
            fts_results = self._execute_fts_search(
                cursor, query, user_id, category_filter, limit
            )
            if fts_results:
                for result in fts_results:
                    result["search_strategy"] = "fts_search"
                    result["search_score"] = 1.0
                    all_results.append(result)

            # Note: Entity-based search removed in streamlined schema

            # 3. Category-based search if specified
            if category_filter:
                category_results = self._execute_category_search(
                    cursor, query, user_id, category_filter, limit
                )
                for result in category_results:
                    result["search_strategy"] = "category_search"
                    result["search_score"] = 0.6
                    all_results.append(result)

            # 4. Fallback to LIKE search if no other results
            if not all_results:
                like_results = self._execute_like_search(
                    cursor, query, user_id, category_filter, limit
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
        user_id: str,
        category_filter: list[str] | None,
        limit: int,
    ):
        """Execute FTS5 search with proper parameterization"""
        try:
            # Sanitize and prepare FTS query
            if query and query.strip():
                # Escape FTS5 special characters and wrap in quotes for phrase search
                sanitized_query = query.strip().replace('"', '""')  # Escape quotes
                fts_query = f'"{sanitized_query}"'
            else:
                # Use a simple match-all query for empty searches
                fts_query = "*"

            # Build parameterized query - avoid string concatenation
            params = [fts_query, user_id]

            if category_filter and isinstance(category_filter, list):
                # Validate category filter is a list of strings
                sanitized_categories = [str(cat) for cat in category_filter if cat]
                if sanitized_categories:
                    category_placeholders = ",".join("?" * len(sanitized_categories))
                    params.extend(sanitized_categories)
                    params.append(limit)

                    sql_query = f"""
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
                            rank
                        FROM memory_search_fts fts
                        LEFT JOIN short_term_memory st ON fts.memory_id = st.memory_id AND fts.memory_type = 'short_term'
                        LEFT JOIN long_term_memory lt ON fts.memory_id = lt.memory_id AND fts.memory_type = 'long_term'
                        WHERE memory_search_fts MATCH ? AND fts.user_id = ?
                            AND fts.category_primary IN ({category_placeholders})
                        ORDER BY rank, importance_score DESC
                        LIMIT ?
                    """
                else:
                    # No valid categories, proceed without filter
                    params.append(limit)
                    sql_query = """
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
                            rank
                        FROM memory_search_fts fts
                        LEFT JOIN short_term_memory st ON fts.memory_id = st.memory_id AND fts.memory_type = 'short_term'
                        LEFT JOIN long_term_memory lt ON fts.memory_id = lt.memory_id AND fts.memory_type = 'long_term'
                        WHERE memory_search_fts MATCH ? AND fts.user_id = ?
                        ORDER BY rank, importance_score DESC
                        LIMIT ?
                    """
            else:
                params.append(limit)
                sql_query = """
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
                        rank
                    FROM memory_search_fts fts
                    LEFT JOIN short_term_memory st ON fts.memory_id = st.memory_id AND fts.memory_type = 'short_term'
                    LEFT JOIN long_term_memory lt ON fts.memory_id = lt.memory_id AND fts.memory_type = 'long_term'
                    WHERE memory_search_fts MATCH ? AND fts.user_id = ?
                    ORDER BY rank, importance_score DESC
                    LIMIT ?
                """

            cursor.execute(sql_query, params)
            return [dict(row) for row in cursor.fetchall()]

        except sqlite3.OperationalError as e:
            logger.debug(f"FTS not available: {e}")
            return []
        except Exception as e:
            logger.error(f"FTS search error: {e}")
            return []

    def _execute_category_search(
        self, cursor, query: str, user_id: str, category_filter: list[str], limit: int
    ):
        """Execute category-based search with proper input validation"""
        try:
            # Input validation
            if not isinstance(category_filter, list) or not category_filter:
                return []

            # Sanitize inputs
            sanitized_query = str(query).strip() if query else ""
            sanitized_user_id = str(user_id).strip()
            sanitized_categories = [str(cat).strip() for cat in category_filter if cat]
            sanitized_limit = max(1, min(int(limit), 1000))  # Limit between 1 and 1000

            if not sanitized_categories:
                return []

            # Build parameterized query
            category_placeholders = ",".join(["?"] * len(sanitized_categories))

            # Use parameterized query with proper escaping
            sql_query = f"""
                SELECT memory_id, processed_data, importance_score, created_at, summary,
                       category_primary, 'long_term' as memory_type
                FROM long_term_memory
                WHERE user_id = ? AND category_primary IN ({category_placeholders})
                  AND (searchable_content LIKE ? OR summary LIKE ?)
                ORDER BY importance_score DESC, created_at DESC
                LIMIT ?
            """

            # Build parameters safely
            params = (
                [sanitized_user_id]
                + sanitized_categories
                + [f"%{sanitized_query}%", f"%{sanitized_query}%", sanitized_limit]
            )

            cursor.execute(sql_query, params)
            return [dict(row) for row in cursor.fetchall()]

        except Exception as e:
            logger.error(f"Category search error: {e}")
            return []

    def _execute_like_search(
        self,
        cursor,
        query: str,
        user_id: str,
        category_filter: list[str] | None,
        limit: int,
    ):
        """Execute fallback LIKE search with proper input validation"""
        try:
            # Input validation and sanitization
            sanitized_query = str(query).strip() if query else ""
            sanitized_user_id = str(user_id).strip()
            sanitized_limit = max(1, min(int(limit), 1000))  # Limit between 1 and 1000
            current_timestamp = datetime.now()

            results = []

            # Validate and sanitize category filter
            sanitized_categories = []
            if category_filter and isinstance(category_filter, list):
                sanitized_categories = [
                    str(cat).strip() for cat in category_filter if cat
                ]

            # Search short-term memory with parameterized query
            if sanitized_categories:
                category_placeholders = ",".join(["?"] * len(sanitized_categories))
                short_term_sql = f"""
                    SELECT *, 'short_term' as memory_type FROM short_term_memory
                    WHERE user_id = ? AND (searchable_content LIKE ? OR summary LIKE ?)
                    AND (expires_at IS NULL OR expires_at > ?)
                    AND category_primary IN ({category_placeholders})
                    ORDER BY importance_score DESC, created_at DESC
                    LIMIT ?
                """
                short_term_params = (
                    [
                        sanitized_user_id,
                        f"%{sanitized_query}%",
                        f"%{sanitized_query}%",
                        current_timestamp,
                    ]
                    + sanitized_categories
                    + [sanitized_limit]
                )
            else:
                short_term_sql = """
                    SELECT *, 'short_term' as memory_type FROM short_term_memory
                    WHERE user_id = ? AND (searchable_content LIKE ? OR summary LIKE ?)
                    AND (expires_at IS NULL OR expires_at > ?)
                    ORDER BY importance_score DESC, created_at DESC
                    LIMIT ?
                """
                short_term_params = [
                    sanitized_user_id,
                    f"%{sanitized_query}%",
                    f"%{sanitized_query}%",
                    current_timestamp,
                    sanitized_limit,
                ]

            cursor.execute(short_term_sql, short_term_params)
            results.extend([dict(row) for row in cursor.fetchall()])

            # Search long-term memory with parameterized query
            if sanitized_categories:
                category_placeholders = ",".join(["?"] * len(sanitized_categories))
                long_term_sql = f"""
                    SELECT *, 'long_term' as memory_type FROM long_term_memory
                    WHERE user_id = ? AND (searchable_content LIKE ? OR summary LIKE ?)
                    AND category_primary IN ({category_placeholders})
                    ORDER BY importance_score DESC, created_at DESC
                    LIMIT ?
                """
                long_term_params = (
                    [
                        sanitized_user_id,
                        f"%{sanitized_query}%",
                        f"%{sanitized_query}%",
                    ]
                    + sanitized_categories
                    + [sanitized_limit]
                )
            else:
                long_term_sql = """
                    SELECT *, 'long_term' as memory_type FROM long_term_memory
                    WHERE user_id = ? AND (searchable_content LIKE ? OR summary LIKE ?)
                    ORDER BY importance_score DESC, created_at DESC
                    LIMIT ?
                """
                long_term_params = [
                    sanitized_user_id,
                    f"%{sanitized_query}%",
                    f"%{sanitized_query}%",
                    sanitized_limit,
                ]

            cursor.execute(long_term_sql, long_term_params)
            results.extend([dict(row) for row in cursor.fetchall()])

            return results[:sanitized_limit]  # Ensure final limit

        except Exception as e:
            logger.error(f"LIKE search error: {e}")
            return []

    def _calculate_recency_score(self, created_at_str: str) -> float:
        """Calculate recency score (0-1, newer = higher)"""
        try:
            if not created_at_str:
                return 0.0
            created_at = datetime.fromisoformat(created_at_str).replace(tzinfo=None)
            days_old = (datetime.now() - created_at).days
            # Exponential decay: score decreases as days increase
            return max(0, 1 - (days_old / 30))  # Full score for recent, 0 after 30 days
        except (ValueError, TypeError, AttributeError) as e:
            logger.warning(
                f"Invalid date format for recency calculation: {created_at_str}, error: {e}"
            )
            return 0.0

    def _determine_storage_location(self, memory: ProcessedMemory) -> str:
        """Determine where to store the memory based on its properties"""
        # Note: rules_memory removed in streamlined schema - rules stored as long_term
        if memory.importance.retention_type in [
            RetentionType.long_term,
            RetentionType.permanent,
        ]:
            return "long_term_memory"
        else:
            return "short_term_memory"

    def get_memory_stats(self, user_id: str = "default") -> dict[str, Any]:
        """Get comprehensive memory statistics"""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            stats = {}

            # Basic counts
            cursor.execute(
                "SELECT COUNT(*) FROM chat_history WHERE user_id = ?", (user_id,)
            )
            stats["chat_history_count"] = cursor.fetchone()[0]

            cursor.execute(
                "SELECT COUNT(*) FROM short_term_memory WHERE user_id = ?",
                (user_id,),
            )
            stats["short_term_count"] = cursor.fetchone()[0]

            cursor.execute(
                "SELECT COUNT(*) FROM long_term_memory WHERE user_id = ?",
                (user_id,),
            )
            stats["long_term_count"] = cursor.fetchone()[0]

            # Note: rules_memory and memory_entities tables removed in v2.0 streamlined schema
            stats["rules_count"] = 0
            stats["total_entities"] = 0

            # Category breakdown
            cursor.execute(
                """
                SELECT category_primary, COUNT(*) as count
                FROM (
                    SELECT category_primary FROM short_term_memory WHERE user_id = ?
                    UNION ALL
                    SELECT category_primary FROM long_term_memory WHERE user_id = ?
                )
                GROUP BY category_primary
            """,
                (user_id, user_id),
            )

            stats["memories_by_category"] = {
                row[0]: row[1] for row in cursor.fetchall()
            }

            # Average importance
            cursor.execute(
                """
                SELECT AVG(importance_score) FROM (
                    SELECT importance_score FROM short_term_memory WHERE user_id = ?
                    UNION ALL
                    SELECT importance_score FROM long_term_memory WHERE user_id = ?
                )
            """,
                (user_id, user_id),
            )

            avg_importance = cursor.fetchone()[0]
            stats["average_importance"] = avg_importance if avg_importance else 0.0

            return stats

    def clear_memory(self, user_id: str = "default", memory_type: str | None = None):
        """Clear memory data with multi-tenant isolation"""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            if memory_type == "short_term":
                cursor.execute(
                    "DELETE FROM short_term_memory WHERE user_id = ?", (user_id,)
                )
            elif memory_type == "long_term":
                cursor.execute(
                    "DELETE FROM long_term_memory WHERE user_id = ?", (user_id,)
                )
            elif memory_type == "chat_history":
                cursor.execute("DELETE FROM chat_history WHERE user_id = ?", (user_id,))
            else:  # Clear all
                cursor.execute(
                    "DELETE FROM short_term_memory WHERE user_id = ?", (user_id,)
                )
                cursor.execute(
                    "DELETE FROM long_term_memory WHERE user_id = ?", (user_id,)
                )
                cursor.execute("DELETE FROM chat_history WHERE user_id = ?", (user_id,))

            conn.commit()
