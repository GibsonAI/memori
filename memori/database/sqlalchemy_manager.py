"""
SQLAlchemy-based database manager for Memori v2.0
Replaces the existing database.py with cross-database compatibility
"""

import importlib.util
import json
import ssl
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from loguru import logger
from sqlalchemy import create_engine, func, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker

from ..utils.exceptions import DatabaseError
from ..utils.pydantic_models import (
    ProcessedLongTermMemory,
)
from .auto_creator import DatabaseAutoCreator
from .models import (
    Base,
    ChatHistory,
    LongTermMemory,
    ShortTermMemory,
)
from .query_translator import QueryParameterTranslator
from .search_service import SearchService


class SQLAlchemyDatabaseManager:
    """SQLAlchemy-based database manager with cross-database support"""

    def __init__(
        self, database_connect: str, template: str = "basic", schema_init: bool = True
    ):
        self.database_connect = database_connect
        self.template = template
        self.schema_init = schema_init

        # Initialize database auto-creator
        self.auto_creator = DatabaseAutoCreator(schema_init)

        # Ensure database exists (create if necessary)
        self.database_connect = self.auto_creator.ensure_database_exists(
            database_connect
        )

        # Parse connection string and create engine
        self.engine = self._create_engine(self.database_connect)
        self.database_type = self.engine.dialect.name

        # Create session factory
        self.SessionLocal = sessionmaker(bind=self.engine)

        # Initialize search service
        self._search_service = None

        # Initialize query parameter translator for cross-database compatibility
        self.query_translator = QueryParameterTranslator(self.database_type)

        logger.info(f"Initialized SQLAlchemy database manager for {self.database_type}")

    def _validate_database_dependencies(self, database_connect: str):
        """Validate that required database drivers are installed"""
        if database_connect.startswith("mysql:") or database_connect.startswith(
            "mysql+"
        ):
            # Check for MySQL drivers
            mysql_drivers = []

            if (
                "mysqlconnector" in database_connect
                or "mysql+mysqlconnector" in database_connect
            ):
                if importlib.util.find_spec("mysql.connector") is not None:
                    mysql_drivers.append("mysql-connector-python")

            if "pymysql" in database_connect:
                if importlib.util.find_spec("pymysql") is not None:
                    mysql_drivers.append("PyMySQL")

            # If using generic mysql:// try both drivers
            if database_connect.startswith("mysql://"):
                if importlib.util.find_spec("mysql.connector") is not None:
                    mysql_drivers.append("mysql-connector-python")
                if importlib.util.find_spec("pymysql") is not None:
                    mysql_drivers.append("PyMySQL")

            if not mysql_drivers:
                error_msg = (
                    "❌ No MySQL driver found. Install one of the following:\n\n"
                    "Option 1 (Recommended): pip install mysql-connector-python\n"
                    "Option 2: pip install PyMySQL\n"
                    "Option 3: pip install memorisdk[mysql]\n\n"
                    "Then update your connection string:\n"
                    "- For mysql-connector-python: mysql+mysqlconnector://user:pass@host:port/db\n"
                    "- For PyMySQL: mysql+pymysql://user:pass@host:port/db"
                )
                raise DatabaseError(error_msg)

        elif database_connect.startswith("postgresql:") or database_connect.startswith(
            "postgresql+"
        ):
            # Check for PostgreSQL drivers
            if (
                importlib.util.find_spec("psycopg2") is None
                and importlib.util.find_spec("asyncpg") is None
            ):
                error_msg = (
                    "❌ No PostgreSQL driver found. Install one of the following:\n\n"
                    "Option 1 (Recommended): pip install psycopg2-binary\n"
                    "Option 2: pip install memorisdk[postgres]\n\n"
                    "Then use connection string: postgresql://user:pass@host:port/db"
                )
                raise DatabaseError(error_msg)

    def _create_engine(self, database_connect: str):
        """Create SQLAlchemy engine with appropriate configuration"""
        try:
            # Validate database driver dependencies first
            self._validate_database_dependencies(database_connect)
            # Parse connection string
            if database_connect.startswith("sqlite:"):
                # Ensure directory exists for SQLite
                if ":///" in database_connect:
                    db_path = database_connect.replace("sqlite:///", "")
                    db_dir = Path(db_path).parent
                    db_dir.mkdir(parents=True, exist_ok=True)

                # SQLite-specific configuration
                engine = create_engine(
                    database_connect,
                    json_serializer=json.dumps,
                    json_deserializer=json.loads,
                    echo=False,
                    # SQLite-specific options
                    connect_args={
                        "check_same_thread": False,  # Allow multiple threads
                    },
                )

            elif database_connect.startswith("mysql:") or database_connect.startswith(
                "mysql+"
            ):
                # MySQL-specific configuration
                connect_args = {"charset": "utf8mb4"}

                # Parse URL for SSL parameters
                parsed = urlparse(database_connect)
                if parsed.query:
                    query_params = parse_qs(parsed.query)

                    # Handle SSL parameters for PyMySQL - enforce secure transport
                    if any(key in query_params for key in ["ssl", "ssl_disabled"]):
                        if query_params.get("ssl", ["false"])[0].lower() == "true":
                            # Enable SSL with secure configuration for required secure transport
                            connect_args["ssl"] = {
                                "ssl_disabled": False,
                                "check_hostname": False,
                                "verify_mode": ssl.CERT_NONE,
                            }
                            # Also add ssl_disabled=False for PyMySQL
                            connect_args["ssl_disabled"] = False
                        elif (
                            query_params.get("ssl_disabled", ["true"])[0].lower()
                            == "false"
                        ):
                            # Enable SSL with secure configuration for required secure transport
                            connect_args["ssl"] = {
                                "ssl_disabled": False,
                                "check_hostname": False,
                                "verify_mode": ssl.CERT_NONE,
                            }
                            # Also add ssl_disabled=False for PyMySQL
                            connect_args["ssl_disabled"] = False

                # Different args for different MySQL drivers
                if "pymysql" in database_connect:
                    # PyMySQL-specific arguments
                    connect_args.update(
                        {
                            "charset": "utf8mb4",
                            "autocommit": False,
                        }
                    )
                elif (
                    "mysqlconnector" in database_connect
                    or "mysql+mysqlconnector" in database_connect
                ):
                    # MySQL Connector/Python-specific arguments
                    connect_args.update(
                        {
                            "charset": "utf8mb4",
                            "use_pure": True,
                        }
                    )

                engine = create_engine(
                    database_connect,
                    json_serializer=json.dumps,
                    json_deserializer=json.loads,
                    echo=False,
                    connect_args=connect_args,
                    pool_pre_ping=True,  # Validate connections
                    pool_recycle=3600,  # Recycle connections every hour
                )

            elif database_connect.startswith(
                "postgresql:"
            ) or database_connect.startswith("postgresql+"):
                # PostgreSQL-specific configuration
                engine = create_engine(
                    database_connect,
                    json_serializer=json.dumps,
                    json_deserializer=json.loads,
                    echo=False,
                    pool_pre_ping=True,
                    pool_recycle=3600,
                )

            else:
                raise DatabaseError(f"Unsupported database type: {database_connect}")

            # Test connection
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))

            return engine

        except DatabaseError:
            # Re-raise our custom database errors with helpful messages
            raise
        except ModuleNotFoundError as e:
            if "mysql" in str(e).lower():
                error_msg = (
                    "❌ MySQL driver not found. Install one of the following:\n\n"
                    "Option 1 (Recommended): pip install mysql-connector-python\n"
                    "Option 2: pip install PyMySQL\n"
                    "Option 3: pip install memorisdk[mysql]\n\n"
                    f"Original error: {e}"
                )
                raise DatabaseError(error_msg)
            elif "psycopg" in str(e).lower() or "postgresql" in str(e).lower():
                error_msg = (
                    "❌ PostgreSQL driver not found. Install one of the following:\n\n"
                    "Option 1 (Recommended): pip install psycopg2-binary\n"
                    "Option 2: pip install memorisdk[postgres]\n\n"
                    f"Original error: {e}"
                )
                raise DatabaseError(error_msg)
            else:
                raise DatabaseError(f"Missing required dependency: {e}")
        except SQLAlchemyError as e:
            error_msg = f"Database connection failed: {e}\n\nCheck your connection string and ensure the database server is running."
            raise DatabaseError(error_msg)
        except Exception as e:
            raise DatabaseError(f"Failed to create database engine: {e}")

    def initialize_schema(self):
        """Initialize database schema"""
        try:
            # Create all tables
            Base.metadata.create_all(bind=self.engine)

            # Setup database-specific features
            self._setup_database_features()

            logger.info(
                f"Database schema initialized successfully for {self.database_type}"
            )

        except Exception as e:
            logger.error(f"Failed to initialize schema: {e}")
            raise DatabaseError(f"Failed to initialize schema: {e}")

    def _setup_database_features(self):
        """Setup database-specific features like full-text search"""
        try:
            with self.engine.connect() as conn:
                if self.database_type == "sqlite":
                    self._setup_sqlite_fts(conn)
                elif self.database_type == "mysql":
                    self._setup_mysql_fulltext(conn)
                elif self.database_type == "postgresql":
                    self._setup_postgresql_fts(conn)

                conn.commit()

        except Exception as e:
            logger.warning(f"Failed to setup database-specific features: {e}")

    def _setup_sqlite_fts(self, conn):
        """Setup SQLite FTS5"""
        try:
            # Create FTS5 virtual table
            conn.execute(
                text(
                    """
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
            """
                )
            )

            # Create triggers
            conn.execute(
                text(
                    """
                CREATE TRIGGER IF NOT EXISTS short_term_memory_fts_insert AFTER INSERT ON short_term_memory
                BEGIN
                    INSERT INTO memory_search_fts(memory_id, memory_type, namespace, searchable_content, summary, category_primary)
                    VALUES (NEW.memory_id, 'short_term', NEW.namespace, NEW.searchable_content, NEW.summary, NEW.category_primary);
                END
            """
                )
            )

            conn.execute(
                text(
                    """
                CREATE TRIGGER IF NOT EXISTS long_term_memory_fts_insert AFTER INSERT ON long_term_memory
                BEGIN
                    INSERT INTO memory_search_fts(memory_id, memory_type, namespace, searchable_content, summary, category_primary)
                    VALUES (NEW.memory_id, 'long_term', NEW.namespace, NEW.searchable_content, NEW.summary, NEW.category_primary);
                END
            """
                )
            )

            logger.info("SQLite FTS5 setup completed")

        except Exception as e:
            logger.warning(f"SQLite FTS5 setup failed: {e}")

    def _setup_mysql_fulltext(self, conn):
        """Setup MySQL FULLTEXT indexes"""
        try:
            # Check if indexes exist before creating them
            index_check_query = text(
                """
                SELECT COUNT(*) as index_count
                FROM information_schema.statistics
                WHERE table_schema = DATABASE()
                AND index_name IN ('ft_short_term_search', 'ft_long_term_search')
            """
            )

            result = conn.execute(index_check_query)
            existing_indexes = result.fetchone()[0]

            if existing_indexes < 2:
                logger.info(
                    f"Creating missing MySQL FULLTEXT indexes ({existing_indexes}/2 exist)..."
                )

                # Check and create short_term_memory index if missing
                short_term_check = conn.execute(
                    text(
                        """
                        SELECT COUNT(*) FROM information_schema.statistics
                        WHERE table_schema = DATABASE()
                        AND table_name = 'short_term_memory'
                        AND index_name = 'ft_short_term_search'
                        """
                    )
                ).fetchone()[0]

                if short_term_check == 0:
                    conn.execute(
                        text(
                            "ALTER TABLE short_term_memory ADD FULLTEXT INDEX ft_short_term_search (searchable_content, summary)"
                        )
                    )
                    logger.info("Created ft_short_term_search index")

                # Check and create long_term_memory index if missing
                long_term_check = conn.execute(
                    text(
                        """
                        SELECT COUNT(*) FROM information_schema.statistics
                        WHERE table_schema = DATABASE()
                        AND table_name = 'long_term_memory'
                        AND index_name = 'ft_long_term_search'
                        """
                    )
                ).fetchone()[0]

                if long_term_check == 0:
                    conn.execute(
                        text(
                            "ALTER TABLE long_term_memory ADD FULLTEXT INDEX ft_long_term_search (searchable_content, summary)"
                        )
                    )
                    logger.info("Created ft_long_term_search index")

                logger.info("MySQL FULLTEXT indexes setup completed")
            else:
                logger.debug(
                    "MySQL FULLTEXT indexes already exist (2/2), skipping creation"
                )

        except Exception as e:
            logger.warning(f"MySQL FULLTEXT setup failed: {e}")

    def _setup_postgresql_fts(self, conn):
        """Setup PostgreSQL full-text search"""
        try:
            # Add tsvector columns
            conn.execute(
                text(
                    "ALTER TABLE short_term_memory ADD COLUMN IF NOT EXISTS search_vector tsvector"
                )
            )
            conn.execute(
                text(
                    "ALTER TABLE long_term_memory ADD COLUMN IF NOT EXISTS search_vector tsvector"
                )
            )

            # Create GIN indexes
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_short_term_search_vector ON short_term_memory USING GIN(search_vector)"
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_long_term_search_vector ON long_term_memory USING GIN(search_vector)"
                )
            )

            # Create update functions and triggers
            conn.execute(
                text(
                    """
                CREATE OR REPLACE FUNCTION update_short_term_search_vector() RETURNS trigger AS $$
                BEGIN
                    NEW.search_vector := to_tsvector('english', COALESCE(NEW.searchable_content, '') || ' ' || COALESCE(NEW.summary, ''));
                    RETURN NEW;
                END
                $$ LANGUAGE plpgsql;
            """
                )
            )

            conn.execute(
                text(
                    """
                DROP TRIGGER IF EXISTS update_short_term_search_vector_trigger ON short_term_memory;
                CREATE TRIGGER update_short_term_search_vector_trigger
                BEFORE INSERT OR UPDATE ON short_term_memory
                FOR EACH ROW EXECUTE FUNCTION update_short_term_search_vector();
            """
                )
            )

            logger.info("PostgreSQL FTS setup completed")

        except Exception as e:
            logger.warning(f"PostgreSQL FTS setup failed: {e}")

    def _get_search_service(self) -> SearchService:
        """Get search service instance with fresh session and proper error handling"""
        try:
            if not self.SessionLocal:
                logger.error("SessionLocal not available for search service")
                return None

            # Always create a new session to avoid stale connections
            session = self.SessionLocal()
            if not session:
                logger.error("Failed to create database session")
                return None

            search_service = SearchService(session, self.database_type)
            logger.debug(
                f"Created new search service instance for database type: {self.database_type}"
            )
            return search_service

        except Exception as e:
            logger.error(f"Failed to create search service: {e}")
            logger.debug(
                f"Search service creation error: {type(e).__name__}: {str(e)}",
                exc_info=True,
            )
            return None

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
        metadata: dict[str, Any] | None = None,
    ):
        """Store chat history"""
        with self.SessionLocal() as session:
            try:
                chat_history = ChatHistory(
                    chat_id=chat_id,
                    user_input=user_input,
                    ai_output=ai_output,
                    model=model,
                    timestamp=timestamp,
                    session_id=session_id,
                    namespace=namespace,
                    tokens_used=tokens_used,
                    metadata_json=metadata or {},
                )

                session.merge(chat_history)  # Use merge for INSERT OR REPLACE behavior
                session.commit()

            except SQLAlchemyError as e:
                session.rollback()
                raise DatabaseError(f"Failed to store chat history: {e}")

    def get_chat_history(
        self,
        namespace: str = "default",
        session_id: str | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Get chat history with optional session filtering"""
        with self.SessionLocal() as session:
            try:
                query = session.query(ChatHistory).filter(
                    ChatHistory.namespace == namespace
                )

                if session_id:
                    query = query.filter(ChatHistory.session_id == session_id)

                results = (
                    query.order_by(ChatHistory.timestamp.desc()).limit(limit).all()
                )

                # Convert to dictionaries
                return [
                    {
                        "chat_id": result.chat_id,
                        "user_input": result.user_input,
                        "ai_output": result.ai_output,
                        "model": result.model,
                        "timestamp": result.timestamp,
                        "session_id": result.session_id,
                        "namespace": result.namespace,
                        "tokens_used": result.tokens_used,
                        "metadata": result.metadata_json or {},
                    }
                    for result in results
                ]

            except SQLAlchemyError as e:
                raise DatabaseError(f"Failed to get chat history: {e}")

    def _check_milestone(self, memory_count: int):
        """
        Check and celebrate memory storage milestones to encourage user engagement.
        Displays celebration messages at key milestones: 10, 50, 100, 500, 1000 memories.

        Args:
            memory_count: Current count of long-term memories
        """
        milestones = [10, 50, 100, 500, 1000]

        if memory_count in milestones:
            celebration_msg = (
                f"\n{'=' * 60}\n"
                f"🎉 Milestone Achieved: {memory_count} memories stored!\n"
                f"{'=' * 60}\n"
                f"⭐️ Loving Memori? Give us a star on GitHub!\n"
                f"👉 https://github.com/GibsonAI/memori\n"
                f"Your support helps us build better open AI memory tools ❤️\n"
                f"{'=' * 60}\n"
            )
            logger.info(celebration_msg)

    def store_long_term_memory_enhanced(
        self, memory: ProcessedLongTermMemory, chat_id: str, namespace: str = "default"
    ) -> str:
        """Store a ProcessedLongTermMemory with enhanced schema"""
        memory_id = str(uuid.uuid4())

        with self.SessionLocal() as session:
            try:
                long_term_memory = LongTermMemory(
                    memory_id=memory_id,
                    original_chat_id=chat_id,
                    processed_data=memory.model_dump(mode="json"),
                    importance_score=memory.importance_score,
                    category_primary=memory.classification.value,
                    retention_type="long_term",
                    namespace=namespace,
                    created_at=datetime.now(),
                    searchable_content=memory.content,
                    summary=memory.summary,
                    novelty_score=0.5,
                    relevance_score=0.5,
                    actionability_score=0.5,
                    classification=memory.classification.value,
                    memory_importance=memory.importance.value,
                    topic=memory.topic,
                    entities_json=memory.entities,
                    keywords_json=memory.keywords,
                    is_user_context=memory.is_user_context,
                    is_preference=memory.is_preference,
                    is_skill_knowledge=memory.is_skill_knowledge,
                    is_current_project=memory.is_current_project,
                    promotion_eligible=memory.promotion_eligible,
                    duplicate_of=memory.duplicate_of,
                    supersedes_json=memory.supersedes,
                    related_memories_json=memory.related_memories,
                    confidence_score=memory.confidence_score,
                    extraction_timestamp=memory.extraction_timestamp,
                    classification_reason=memory.classification_reason,
                    processed_for_duplicates=False,
                    conscious_processed=False,
                )

                session.add(long_term_memory)
                session.commit()

                logger.debug(f"Stored enhanced long-term memory {memory_id}")

                # Get current memory count and check for milestones
                total_memories = (
                    session.query(LongTermMemory)
                    .filter(LongTermMemory.namespace == namespace)
                    .count()
                )

                # Celebrate milestone if reached
                self._check_milestone(total_memories)

                return memory_id

            except SQLAlchemyError as e:
                session.rollback()
                logger.error(f"Failed to store enhanced long-term memory: {e}")
                raise DatabaseError(f"Failed to store enhanced long-term memory: {e}")

    def search_memories(
        self,
        query: str,
        namespace: str = "default",
        category_filter: list[str] | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Search memories using the cross-database search service"""
        search_service = None
        try:
            logger.debug(
                f"Starting memory search for query '{query}' in namespace '{namespace}' with category_filter={category_filter}"
            )
            search_service = self._get_search_service()

            if not search_service:
                logger.error("Failed to create search service instance")
                return []

            results = search_service.search_memories(
                query, namespace, category_filter, limit
            )
            logger.debug(f"Search for '{query}' returned {len(results)} results")

            # Validate results structure
            if not isinstance(results, list):
                logger.warning(
                    f"Search service returned unexpected type: {type(results)}, converting to list"
                )
                results = list(results) if results else []

            return results

        except Exception as e:
            logger.error(
                f"Memory search failed for query '{query}' in namespace '{namespace}': {e}"
            )
            logger.debug(
                f"Search error details: {type(e).__name__}: {str(e)}", exc_info=True
            )
            # Return empty list instead of raising exception to avoid breaking auto_ingest
            return []

        finally:
            # Ensure session is properly closed, even if an exception occurred
            if search_service and hasattr(search_service, "session"):
                try:
                    if search_service.session:
                        logger.debug("Closing search service session")
                        search_service.session.close()
                except Exception as session_e:
                    logger.warning(f"Error closing search service session: {session_e}")

    def get_memory_stats(self, namespace: str = "default") -> dict[str, Any]:
        """Get comprehensive memory statistics"""
        with self.SessionLocal() as session:
            try:
                stats = {}

                # Basic counts
                stats["chat_history_count"] = (
                    session.query(ChatHistory)
                    .filter(ChatHistory.namespace == namespace)
                    .count()
                )

                stats["short_term_count"] = (
                    session.query(ShortTermMemory)
                    .filter(ShortTermMemory.namespace == namespace)
                    .count()
                )

                stats["long_term_count"] = (
                    session.query(LongTermMemory)
                    .filter(LongTermMemory.namespace == namespace)
                    .count()
                )

                # Category breakdown
                categories = {}

                # Short-term categories
                short_categories = (
                    session.query(
                        ShortTermMemory.category_primary,
                        func.count(ShortTermMemory.memory_id).label("count"),
                    )
                    .filter(ShortTermMemory.namespace == namespace)
                    .group_by(ShortTermMemory.category_primary)
                    .all()
                )

                for cat, count in short_categories:
                    categories[cat] = categories.get(cat, 0) + count

                # Long-term categories
                long_categories = (
                    session.query(
                        LongTermMemory.category_primary,
                        func.count(LongTermMemory.memory_id).label("count"),
                    )
                    .filter(LongTermMemory.namespace == namespace)
                    .group_by(LongTermMemory.category_primary)
                    .all()
                )

                for cat, count in long_categories:
                    categories[cat] = categories.get(cat, 0) + count

                stats["memories_by_category"] = categories

                # Average importance
                short_avg = (
                    session.query(func.avg(ShortTermMemory.importance_score))
                    .filter(ShortTermMemory.namespace == namespace)
                    .scalar()
                    or 0
                )

                long_avg = (
                    session.query(func.avg(LongTermMemory.importance_score))
                    .filter(LongTermMemory.namespace == namespace)
                    .scalar()
                    or 0
                )

                total_memories = stats["short_term_count"] + stats["long_term_count"]
                if total_memories > 0:
                    # Weight averages by count
                    total_avg = (
                        (short_avg * stats["short_term_count"])
                        + (long_avg * stats["long_term_count"])
                    ) / total_memories
                    stats["average_importance"] = float(total_avg) if total_avg else 0.0
                else:
                    stats["average_importance"] = 0.0

                # Database info
                stats["database_type"] = self.database_type
                stats["database_url"] = (
                    self.database_connect.split("@")[-1]
                    if "@" in self.database_connect
                    else self.database_connect
                )

                return stats

            except SQLAlchemyError as e:
                raise DatabaseError(f"Failed to get memory stats: {e}")

    def clear_memory(self, namespace: str = "default", memory_type: str | None = None):
        """Clear memory data"""
        with self.SessionLocal() as session:
            try:
                if memory_type == "short_term":
                    session.query(ShortTermMemory).filter(
                        ShortTermMemory.namespace == namespace
                    ).delete()
                elif memory_type == "long_term":
                    session.query(LongTermMemory).filter(
                        LongTermMemory.namespace == namespace
                    ).delete()
                elif memory_type == "chat_history":
                    session.query(ChatHistory).filter(
                        ChatHistory.namespace == namespace
                    ).delete()
                else:  # Clear all
                    session.query(ShortTermMemory).filter(
                        ShortTermMemory.namespace == namespace
                    ).delete()
                    session.query(LongTermMemory).filter(
                        LongTermMemory.namespace == namespace
                    ).delete()
                    session.query(ChatHistory).filter(
                        ChatHistory.namespace == namespace
                    ).delete()

                session.commit()

            except SQLAlchemyError as e:
                session.rollback()
                raise DatabaseError(f"Failed to clear memory: {e}")

    def execute_with_translation(self, query: str, parameters: dict[str, Any] = None):
        """
        Execute a query with automatic parameter translation for cross-database compatibility.

        Args:
            query: SQL query string
            parameters: Query parameters

        Returns:
            Query result
        """
        if parameters:
            translated_params = self.query_translator.translate_parameters(parameters)
        else:
            translated_params = {}

        with self.engine.connect() as conn:
            result = conn.execute(text(query), translated_params)
            conn.commit()
            return result

    def _get_connection(self):
        """
        Compatibility method for legacy code that expects raw database connections.

        Returns a context manager that provides a SQLAlchemy connection with
        automatic parameter translation support.

        This is used by memory.py for direct SQL queries.
        """
        from contextlib import contextmanager

        @contextmanager
        def connection_context():
            class TranslatingConnection:
                """Wrapper that adds parameter translation to SQLAlchemy connections"""

                def __init__(self, conn, translator):
                    self._conn = conn
                    self._translator = translator

                def execute(self, query, parameters=None):
                    """Execute query with automatic parameter translation"""
                    if parameters:
                        # Handle both text() queries and raw strings
                        if hasattr(query, "text"):
                            # SQLAlchemy text() object
                            translated_params = self._translator.translate_parameters(
                                parameters
                            )
                            return self._conn.execute(query, translated_params)
                        else:
                            # Raw string query
                            translated_params = self._translator.translate_parameters(
                                parameters
                            )
                            return self._conn.execute(
                                text(str(query)), translated_params
                            )
                    else:
                        return self._conn.execute(query)

                def commit(self):
                    """Commit transaction"""
                    return self._conn.commit()

                def rollback(self):
                    """Rollback transaction"""
                    return self._conn.rollback()

                def close(self):
                    """Close connection"""
                    return self._conn.close()

                def fetchall(self):
                    """Compatibility method for cursor-like usage"""
                    # This is for backwards compatibility with code that expects cursor.fetchall()
                    return []

                def scalar(self):
                    """Compatibility method for cursor-like usage"""
                    return None

                def __getattr__(self, name):
                    """Delegate unknown attributes to the underlying connection"""
                    return getattr(self._conn, name)

            conn = self.engine.connect()
            try:
                yield TranslatingConnection(conn, self.query_translator)
            finally:
                conn.close()

        return connection_context()

    def close(self):
        """Close database connections"""
        if self._search_service and hasattr(self._search_service, "session"):
            self._search_service.session.close()

        if hasattr(self, "engine"):
            self.engine.dispose()

    def get_database_info(self) -> dict[str, Any]:
        """Get database information and capabilities"""
        base_info = {
            "database_type": self.database_type,
            "database_url": (
                self.database_connect.split("@")[-1]
                if "@" in self.database_connect
                else self.database_connect
            ),
            "driver": self.engine.dialect.driver,
            "server_version": getattr(self.engine.dialect, "server_version_info", None),
            "supports_fulltext": True,  # Assume true for SQLAlchemy managed connections
            "auto_creation_enabled": self.enable_auto_creation,
        }

        # Add auto-creation specific information
        if hasattr(self, "auto_creator"):
            creation_info = self.auto_creator.get_database_info(self.database_connect)
            base_info.update(creation_info)

        return base_info
