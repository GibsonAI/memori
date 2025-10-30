"""
Base database connector interface for Memori
Provides abstraction layer for different database backends
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any


class DatabaseType(str, Enum):
    """Supported database types"""

    SQLITE = "sqlite"
    MYSQL = "mysql"
    POSTGRESQL = "postgresql"
    MONGODB = "mongodb"
    COUCHBASE = "couchbase"


class SearchStrategy(str, Enum):
    """Available search strategies"""

    NATIVE = "native"  # Use database-specific full-text search
    LIKE_FALLBACK = "like"  # Use LIKE queries with indexing
    HYBRID = "hybrid"  # Native with fallback to LIKE
    EXTERNAL = "external"  # External search engine (future)


class BaseDatabaseConnector(ABC):
    """Abstract base class for database connectors"""

    def __init__(self, connection_config: dict[str, Any]):
        self.connection_config = connection_config
        self.database_type = self._detect_database_type()

    @abstractmethod
    def _detect_database_type(self) -> DatabaseType:
        """Detect the database type from connection config"""
        pass

    @abstractmethod
    def get_connection(self):
        """Get database connection"""
        pass

    @abstractmethod
    def execute_query(
        self, query: str, params: list[Any] | None = None
    ) -> list[dict[str, Any]]:
        """Execute a query and return results"""
        pass

    @abstractmethod
    def execute_insert(self, query: str, params: list[Any] | None = None) -> str:
        """Execute an insert query and return the inserted row ID"""
        pass

    @abstractmethod
    def execute_update(self, query: str, params: list[Any] | None = None) -> int:
        """Execute an update query and return number of affected rows"""
        pass

    @abstractmethod
    def execute_delete(self, query: str, params: list[Any] | None = None) -> int:
        """Execute a delete query and return number of affected rows"""
        pass

    @abstractmethod
    def execute_transaction(self, queries: list[tuple[str, list[Any] | None]]) -> bool:
        """Execute multiple queries in a transaction"""
        pass

    @abstractmethod
    def test_connection(self) -> bool:
        """Test if the database connection is working"""
        pass

    @abstractmethod
    def initialize_schema(self, schema_sql: str | None = None):
        """Initialize database schema"""
        pass

    @abstractmethod
    def supports_full_text_search(self) -> bool:
        """Check if the database supports native full-text search"""
        pass

    @abstractmethod
    def create_full_text_index(
        self, table: str, columns: list[str], index_name: str
    ) -> str:
        """Create database-specific full-text search index"""
        pass

    @abstractmethod
    def get_database_info(self) -> dict[str, Any]:
        """Get database information and capabilities"""
        pass


class BaseSearchAdapter(ABC):
    """Abstract base class for search adapters"""

    def __init__(self, connector: BaseDatabaseConnector):
        self.connector = connector
        self.database_type = connector.database_type

    @abstractmethod
    def execute_fulltext_search(
        self,
        query: str,
        namespace: str = "default",
        category_filter: list[str] | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Execute full-text search using database-specific methods"""
        pass

    @abstractmethod
    def create_search_indexes(self) -> list[str]:
        """Create search indexes for optimal performance"""
        pass

    @abstractmethod
    def translate_search_query(self, query: str) -> str:
        """Translate search query to database-specific syntax"""
        pass

    def execute_fallback_search(
        self,
        query: str,
        namespace: str = "default",
        category_filter: list[str] | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Execute fallback LIKE-based search with proper parameterization"""
        try:
            # Input validation and sanitization
            sanitized_query = str(query).strip() if query else ""
            sanitized_namespace = str(namespace).strip()
            sanitized_limit = max(1, min(int(limit), 1000))  # Limit between 1 and 1000

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
                short_term_query = f"""
                    SELECT *, 'short_term' as memory_type, 'like_fallback' as search_strategy
                    FROM short_term_memory
                    WHERE namespace = ? AND (searchable_content LIKE ? OR summary LIKE ?)
                    AND category_primary IN ({category_placeholders})
                    ORDER BY importance_score DESC, created_at DESC
                    LIMIT ?
                """
                short_term_params = (
                    [
                        sanitized_namespace,
                        f"%{sanitized_query}%",
                        f"%{sanitized_query}%",
                    ]
                    + sanitized_categories
                    + [sanitized_limit]
                )
            else:
                short_term_query = """
                    SELECT *, 'short_term' as memory_type, 'like_fallback' as search_strategy
                    FROM short_term_memory
                    WHERE namespace = ? AND (searchable_content LIKE ? OR summary LIKE ?)
                    ORDER BY importance_score DESC, created_at DESC
                    LIMIT ?
                """
                short_term_params = [
                    sanitized_namespace,
                    f"%{sanitized_query}%",
                    f"%{sanitized_query}%",
                    sanitized_limit,
                ]

            try:
                results.extend(
                    self.connector.execute_query(short_term_query, short_term_params)
                )
            except Exception:
                # Log error but continue with long-term search
                pass

            # Search long-term memory with parameterized query
            if sanitized_categories:
                category_placeholders = ",".join(["?"] * len(sanitized_categories))
                long_term_query = f"""
                    SELECT *, 'long_term' as memory_type, 'like_fallback' as search_strategy
                    FROM long_term_memory
                    WHERE namespace = ? AND (searchable_content LIKE ? OR summary LIKE ?)
                    AND category_primary IN ({category_placeholders})
                    ORDER BY importance_score DESC, created_at DESC
                    LIMIT ?
                """
                long_term_params = (
                    [
                        sanitized_namespace,
                        f"%{sanitized_query}%",
                        f"%{sanitized_query}%",
                    ]
                    + sanitized_categories
                    + [sanitized_limit]
                )
            else:
                long_term_query = """
                    SELECT *, 'long_term' as memory_type, 'like_fallback' as search_strategy
                    FROM long_term_memory
                    WHERE namespace = ? AND (searchable_content LIKE ? OR summary LIKE ?)
                    ORDER BY importance_score DESC, created_at DESC
                    LIMIT ?
                """
                long_term_params = [
                    sanitized_namespace,
                    f"%{sanitized_query}%",
                    f"%{sanitized_query}%",
                    sanitized_limit,
                ]

            try:
                results.extend(
                    self.connector.execute_query(long_term_query, long_term_params)
                )
            except Exception:
                # Log error but continue
                pass

            return results[:sanitized_limit]  # Ensure final limit

        except Exception:
            # Return empty results on error instead of raising exception
            return []


class BaseSchemaGenerator(ABC):
    """Abstract base class for database-specific schema generators"""

    def __init__(self, database_type: DatabaseType):
        self.database_type = database_type

    @abstractmethod
    def generate_core_schema(self) -> str:
        """Generate core tables schema"""
        pass

    @abstractmethod
    def generate_indexes(self) -> str:
        """Generate database-specific indexes"""
        pass

    @abstractmethod
    def generate_search_setup(self) -> str:
        """Generate search-related schema (indexes, triggers, etc.)"""
        pass

    @abstractmethod
    def get_data_type_mappings(self) -> dict[str, str]:
        """Get database-specific data type mappings"""
        pass

    def generate_full_schema(self) -> str:
        """Generate complete schema"""
        schema_parts = [
            "-- Generated schema for " + self.database_type.value.upper(),
            "",
            self.generate_core_schema(),
            "",
            self.generate_indexes(),
            "",
            self.generate_search_setup(),
        ]
        return "\n".join(schema_parts)
