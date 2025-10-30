"""
Database Connection Utilities for Auto-Creation System

This module handles parsing connection strings, creating databases automatically,
and managing multi-database scenarios for memori instances.
"""

import re
from urllib.parse import urlparse

from loguru import logger


class DatabaseConnectionUtils:
    """Utilities for parsing and managing database connections"""

    # Default system databases for each engine
    DEFAULT_DATABASES = {
        "postgresql": "postgres",
        "mysql": "mysql",
        "sqlite": None,  # SQLite doesn't need default DB
        "mongodb": None,  # MongoDB doesn't need default DB for connection
    }

    @classmethod
    def parse_connection_string(cls, connection_string: str) -> dict[str, str]:
        """
        Parse database connection string and extract components.

        Args:
            connection_string: Database connection URL

        Returns:
            Dictionary with parsed components

        Example:
            mysql://root:pass@localhost:3306/memori_dev
            -> {
                'engine': 'mysql',
                'user': 'root',
                'password': 'pass',
                'host': 'localhost',
                'port': 3306,
                'database': 'memori_dev',
                'base_url': 'mysql://root:pass@localhost:3306',
                'default_url': 'mysql://root:pass@localhost:3306/mysql'
            }
        """
        try:
            parsed = urlparse(connection_string)

            # Extract components
            engine = parsed.scheme.split("+")[
                0
            ].lower()  # Handle postgresql+psycopg2, mysql+pymysql
            driver = parsed.scheme.split("+")[1] if "+" in parsed.scheme else None
            user = parsed.username or ""
            password = parsed.password or ""
            host = parsed.hostname or "localhost"
            port = parsed.port
            database = parsed.path.lstrip("/") if parsed.path else ""

            # Build base URL without database, preserving the driver
            auth = f"{user}:{password}@" if user or password else ""
            if user and not password:
                auth = f"{user}@"

            port_str = f":{port}" if port else ""
            scheme = f"{engine}+{driver}" if driver else engine
            base_url = f"{scheme}://{auth}{host}{port_str}"

            # Create default database URL for system operations
            # DigitalOcean managed PostgreSQL uses 'defaultdb' instead of 'postgres'
            default_db = cls.DEFAULT_DATABASES.get(engine)
            host_lower = host.lower()
            if engine == "postgresql" and host_lower.endswith(".digitalocean.com"):
                default_db = "defaultdb"
                logger.debug(
                    "DigitalOcean PostgreSQL detected - using 'defaultdb' as system database"
                )

            # Preserve query parameters (especially SSL settings) for system database connections
            query_string = f"?{parsed.query}" if parsed.query else ""
            default_url = (
                f"{base_url}/{default_db}{query_string}"
                if default_db
                else f"{base_url}{query_string}"
            )

            return {
                "engine": engine,
                "user": user,
                "password": password,
                "host": host,
                "port": port,
                "database": database,
                "base_url": base_url,
                "default_url": default_url,
                "original_url": connection_string,
                "needs_creation": engine
                in ["postgresql", "mysql"],  # SQLite and MongoDB auto-create
            }

        except Exception as e:
            logger.error(f"Failed to parse connection string: {e}")
            raise ValueError(f"Invalid connection string format: {connection_string}")

    @classmethod
    def build_connection_string(
        cls, components: dict[str, str], target_database: str
    ) -> str:
        """
        Build connection string with specific database name.

        Args:
            components: Parsed connection components
            target_database: Database name to connect to

        Returns:
            Complete connection string
        """
        return f"{components['base_url']}/{target_database}"

    @classmethod
    def validate_database_name(cls, database_name: str) -> bool:
        """
        Validate database name for security and compatibility.

        Args:
            database_name: Name to validate

        Returns:
            True if valid, False otherwise
        """
        if not database_name:
            return False

        # Basic SQL injection prevention
        if any(
            char in database_name.lower()
            for char in [";", "'", '"', "\\", "/", "*", "?", "<", ">", "|"]
        ):
            return False

        # Check length (most databases have limits)
        if len(database_name) > 64:  # MySQL limit
            return False

        # Must start with letter or underscore, contain only alphanumeric, underscore, hyphen
        if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_-]*$", database_name):
            return False

        # Reserved words check (only for database creation, not connection)
        # Note: 'postgres' is a valid system database to connect to in PostgreSQL
        reserved_words = ["mysql", "information_schema", "performance_schema", "sys"]
        if database_name.lower() in reserved_words:
            return False

        return True

    @classmethod
    def generate_database_name(
        cls, base_name: str = "memori", suffix: str = None, prefix: str = None
    ) -> str:
        """
        Generate a valid database name with optional prefix/suffix.

        Args:
            base_name: Base database name
            suffix: Optional suffix (e.g., "dev", "prod", "test")
            prefix: Optional prefix (e.g., "company", "project")

        Returns:
            Generated database name

        Examples:
            generate_database_name() -> "memori"
            generate_database_name(suffix="dev") -> "memori_dev"
            generate_database_name(prefix="acme", suffix="prod") -> "acme_memori_prod"
        """
        parts = []

        if prefix:
            parts.append(prefix)

        parts.append(base_name)

        if suffix:
            parts.append(suffix)

        database_name = "_".join(parts)

        if not cls.validate_database_name(database_name):
            raise ValueError(f"Generated database name is invalid: {database_name}")

        return database_name

    @classmethod
    def extract_database_info(cls, connection_string: str) -> tuple[str, str, bool]:
        """
        Extract database engine, name, and creation requirement.

        Args:
            connection_string: Database connection URL

        Returns:
            Tuple of (engine, database_name, needs_creation)
        """
        components = cls.parse_connection_string(connection_string)
        return (
            components["engine"],
            components["database"],
            components["needs_creation"],
        )
