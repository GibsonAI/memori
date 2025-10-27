"""
PostgreSQL connector for Memori v1.0
"""

from typing import Any

from loguru import logger

from ...utils.exceptions import DatabaseError, ValidationError
from .base_connector import BaseDatabaseConnector, DatabaseType


class PostgreSQLConnector(BaseDatabaseConnector):
    """PostgreSQL database connector"""

    def __init__(self, connection_config):
        """Initialize PostgreSQL connector"""
        if isinstance(connection_config, str):
            self.connection_string = connection_config
        else:
            self.connection_string = self._build_connection_string(connection_config)
        self._psycopg2 = None
        self._setup_psycopg2()
        self._ensure_database_exists()
        super().__init__(connection_config)

    def _setup_psycopg2(self):
        """Setup psycopg2 connection"""
        try:
            import psycopg2
            import psycopg2.extras
            from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

            self._psycopg2 = psycopg2
            self._extras = psycopg2.extras
            self.ISOLATION_LEVEL_AUTOCOMMIT = ISOLATION_LEVEL_AUTOCOMMIT
        except ImportError:
            raise DatabaseError(
                "psycopg2 is required for PostgreSQL support. "
                "Install it with: pip install psycopg2-binary"
            )

    def _detect_database_type(self) -> DatabaseType:
        """Detect database type from connection config"""
        return DatabaseType.POSTGRESQL

    def _build_connection_string(self, config: dict[str, Any]) -> str:
        """Build PostgreSQL connection string from config dict"""
        try:
            user = config.get("user", "postgres")
            password = config.get("password", "")
            host = config.get("host", "localhost")
            port = config.get("port", 5432)
            database = config.get("database")

            if not database:
                raise ValidationError("Database name is required")

            if password:
                return f"postgresql://{user}:{password}@{host}:{port}/{database}"
            else:
                return f"postgresql://{user}@{host}:{port}/{database}"
        except Exception as e:
            raise DatabaseError(f"Invalid PostgreSQL configuration: {e}")

    def _parse_connection_string(self):
        """Parse connection string to extract components"""
        import re

        # Parse PostgreSQL connection string
        # Format: postgresql://user:password@host:port/database
        # or: postgresql+psycopg2://user:password@host:port/database
        pattern = r"postgresql(?:\+psycopg2)?://(?:([^:]+)(?::([^@]+))?@)?([^:/]+)(?::(\d+))?/(.+)"
        match = re.match(pattern, self.connection_string)

        if not match:
            raise DatabaseError(
                f"Invalid PostgreSQL connection string: {self.connection_string}"
            )

        user, password, host, port, database = match.groups()

        return {
            "user": user or "postgres",
            "password": password or "",
            "host": host or "localhost",
            "port": port or "5432",
            "database": database,
        }

    def _ensure_database_exists(self):
        """Ensure the database exists, create if it doesn't"""
        params = self._parse_connection_string()

        try:
            # Connect to default 'postgres' database to check/create target database
            admin_conn_params = {
                "host": params["host"],
                "port": params["port"],
                "user": params["user"],
                "database": "postgres",
            }

            if params["password"]:
                admin_conn_params["password"] = params["password"]

            conn = self._psycopg2.connect(**admin_conn_params)
            conn.set_isolation_level(self.ISOLATION_LEVEL_AUTOCOMMIT)
            cursor = conn.cursor()

            # Check if database exists
            cursor.execute(
                "SELECT 1 FROM pg_database WHERE datname = %s", (params["database"],)
            )

            if not cursor.fetchone():
                # Database doesn't exist, create it
                # Use SQL identifier for database name (can't use parameter substitution for DDL)
                from psycopg2 import sql

                cursor.execute(
                    sql.SQL("CREATE DATABASE {}").format(
                        sql.Identifier(params["database"])
                    )
                )
                logger.info(f"Created PostgreSQL database: {params['database']}")

                # Set UTF-8 encoding
                cursor.execute(
                    sql.SQL("ALTER DATABASE {} SET client_encoding TO 'UTF8'").format(
                        sql.Identifier(params["database"])
                    )
                )

            cursor.close()
            conn.close()

        except self._psycopg2.OperationalError as e:
            # If we can't connect to postgres database, try connecting directly
            # This might work if the target database already exists
            logger.warning(f"Could not connect to postgres database: {e}")
            logger.info("Attempting direct connection to target database...")
        except Exception as e:
            logger.warning(f"Could not ensure database exists: {e}")

    def get_connection(self):
        """Get PostgreSQL connection"""
        try:
            conn = self._psycopg2.connect(
                self.connection_string, cursor_factory=self._extras.RealDictCursor
            )
            conn.autocommit = False
            return conn

        except Exception as e:
            raise DatabaseError(f"Failed to connect to PostgreSQL database: {e}")

    def execute_query(
        self, query: str, params: list | None = None
    ) -> list[dict[str, Any]]:
        """Execute a query and return results"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    if params:
                        cursor.execute(query, params)
                    else:
                        cursor.execute(query)

                    # Return results as list of dictionaries
                    results = []
                    for row in cursor.fetchall():
                        results.append(dict(row))

                    return results

        except Exception as e:
            raise DatabaseError(f"Failed to execute query: {e}")

    def execute_insert(self, query: str, params: list | None = None) -> str:
        """Execute an insert query and return the inserted row ID"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    if params:
                        cursor.execute(query, params)
                    else:
                        cursor.execute(query)

                    # Try to get the inserted ID
                    inserted_id = None
                    if cursor.rowcount > 0:
                        try:
                            # For PostgreSQL, we need RETURNING clause for ID
                            inserted_id = cursor.fetchone()
                            if inserted_id and hasattr(inserted_id, "values"):
                                inserted_id = str(list(inserted_id.values())[0])
                            else:
                                inserted_id = str(cursor.rowcount)
                        except Exception:
                            inserted_id = str(cursor.rowcount)

                    conn.commit()
                    return inserted_id or "0"

        except Exception as e:
            raise DatabaseError(f"Failed to execute insert: {e}")

    def execute_update(self, query: str, params: list | None = None) -> int:
        """Execute an update query and return number of affected rows"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    if params:
                        cursor.execute(query, params)
                    else:
                        cursor.execute(query)

                    conn.commit()
                    return cursor.rowcount

        except Exception as e:
            raise DatabaseError(f"Failed to execute update: {e}")

    def execute_delete(self, query: str, params: list | None = None) -> int:
        """Execute a delete query and return number of affected rows"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    if params:
                        cursor.execute(query, params)
                    else:
                        cursor.execute(query)

                    conn.commit()
                    return cursor.rowcount

        except Exception as e:
            raise DatabaseError(f"Failed to execute delete: {e}")

    def execute_transaction(self, queries: list[tuple]) -> bool:
        """Execute multiple queries in a transaction"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    for query, params in queries:
                        if params:
                            cursor.execute(query, params)
                        else:
                            cursor.execute(query)

                    conn.commit()
                    return True

        except Exception as e:
            logger.error(f"Transaction failed: {e}")
            return False

    def test_connection(self) -> bool:
        """Test if the database connection is working"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT 1")
                    return True
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False

    def initialize_schema(self, schema_sql: str | None = None):
        """Initialize PostgreSQL database schema"""
        try:
            if not schema_sql:
                # Use PostgreSQL-specific schema
                try:
                    from ..schema_generators.postgresql_schema_generator import (  # type: ignore
                        PostgreSQLSchemaGenerator,
                    )

                    schema_generator = PostgreSQLSchemaGenerator()
                    schema_sql = schema_generator.generate_full_schema()
                except ImportError:
                    # Fall back to None - let base functionality handle it
                    schema_sql = None

            # Execute schema using transaction
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    try:
                        # Split schema into individual statements
                        statements = self._split_postgresql_statements(schema_sql)

                        for statement in statements:
                            statement = statement.strip()
                            if statement and not statement.startswith("--"):
                                cursor.execute(statement)

                        conn.commit()
                        logger.info(
                            "PostgreSQL database schema initialized successfully"
                        )

                    except Exception as e:
                        conn.rollback()
                        logger.error(f"Failed to initialize PostgreSQL schema: {e}")
                        raise DatabaseError(f"Schema initialization failed: {e}")

        except Exception as e:
            logger.error(f"Failed to initialize PostgreSQL schema: {e}")
            raise DatabaseError(f"Failed to initialize PostgreSQL schema: {e}")

    def supports_full_text_search(self) -> bool:
        """Check if PostgreSQL supports full-text search"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Test tsvector functionality
                    cursor.execute(
                        "SELECT to_tsvector('english', 'test') @@ plainto_tsquery('english', 'test')"
                    )
                    result = cursor.fetchone()
                    return result[0] if result else False
        except Exception as e:
            logger.warning(f"Could not determine PostgreSQL FTS support: {e}")
            return False

    def create_full_text_index(
        self, table: str, columns: list[str], index_name: str
    ) -> str:
        """Create PostgreSQL GIN index for full-text search"""
        # Validate inputs
        try:
            from ...utils.input_validator import InputValidator

            table = InputValidator.sanitize_sql_identifier(table)
            index_name = InputValidator.sanitize_sql_identifier(index_name)
            for col in columns:
                InputValidator.sanitize_sql_identifier(col)
        except Exception as e:
            raise DatabaseError(f"Invalid index parameters: {e}")

        # Create tsvector expression
        tsvector_expr = " || ' ' || ".join(columns)
        return f"CREATE INDEX {index_name} ON {table} USING gin(to_tsvector('english', {tsvector_expr}))"

    def get_database_info(self) -> dict[str, Any]:
        """Get PostgreSQL database information and capabilities"""
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=self._extras.RealDictCursor) as cursor:
                    info = {}

                    # Basic version info
                    cursor.execute("SELECT version() as version")
                    version_result = cursor.fetchone()
                    info["version"] = (
                        version_result["version"] if version_result else "unknown"
                    )

                    # Database name
                    cursor.execute("SELECT current_database() as db_name")
                    db_result = cursor.fetchone()
                    info["database"] = db_result["db_name"] if db_result else "unknown"

                    # Extensions info
                    cursor.execute("SELECT extname FROM pg_extension")
                    extensions = cursor.fetchall()
                    info["extensions"] = (
                        [ext["extname"] for ext in extensions] if extensions else []
                    )

                    # Check for full-text search capabilities
                    info["database_type"] = self.database_type.value
                    info["fulltext_support"] = self.supports_full_text_search()

                    # Connection info
                    info["connection_string"] = (
                        self.connection_string.split("@")[1]
                        if "@" in self.connection_string
                        else "unknown"
                    )

                    return info

        except Exception as e:
            logger.warning(f"Could not get PostgreSQL database info: {e}")
            return {
                "database_type": self.database_type.value,
                "version": "unknown",
                "fulltext_support": False,
                "error": str(e),
            }

    def _split_postgresql_statements(self, schema_sql: str) -> list[str]:
        """Split SQL schema into individual statements handling PostgreSQL syntax"""
        statements = []
        current_statement = []
        in_function = False

        for line in schema_sql.split("\n"):
            line = line.strip()

            # Skip comments and empty lines
            if not line or line.startswith("--"):
                continue

            # Track function/procedure boundaries
            if line.upper().startswith(
                ("CREATE FUNCTION", "CREATE OR REPLACE FUNCTION", "CREATE PROCEDURE")
            ):
                in_function = True
            elif line.upper().startswith("$$") and in_function:
                in_function = False

            current_statement.append(line)

            # PostgreSQL uses semicolon to end statements (except within functions)
            if line.endswith(";") and not in_function:
                statement = " ".join(current_statement)
                if statement.strip():
                    statements.append(statement)
                current_statement = []

        # Add any remaining statement
        if current_statement:
            statement = " ".join(current_statement)
            if statement.strip():
                statements.append(statement)

        return statements
