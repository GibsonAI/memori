"""
Database Auto-Creation System

This module automatically creates databases if they don't exist, supporting
PostgreSQL and MySQL with proper error handling and security validation.
"""

import ssl
from urllib.parse import parse_qs, urlparse

from loguru import logger
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError, ProgrammingError

from .connection_utils import DatabaseConnectionUtils


class DatabaseAutoCreator:
    """Handles automatic database creation for PostgreSQL and MySQL"""

    def __init__(self, schema_init: bool = True):
        """
        Initialize database auto-creator.

        Args:
            schema_init: Whether to enable automatic database creation
        """
        self.schema_init = schema_init
        self.utils = DatabaseConnectionUtils()

    def _is_gibsonai_temp_connection(self, components: dict[str, str] | None) -> bool:
        """Detect GibsonAI temporary database credentials to avoid noisy warnings."""
        if not components:
            return False

        host = (components.get("host") or "").lower()
        if "gibsonai.com" not in host:
            return False

        user = components.get("user") or components.get("username") or ""
        database = components.get("database") or ""

        # GibsonAI temporary credentials follow predictable us_/db_ prefixes
        return user.startswith("us_") or database.startswith("db_")

    def ensure_database_exists(self, connection_string: str) -> str:
        """
        Ensure target database exists, creating it if necessary.

        Args:
            connection_string: Original database connection string

        Returns:
            Connection string to use (may be unchanged if creation not needed)

        Raises:
            DatabaseCreationError: If database creation fails
        """
        if not self.schema_init:
            logger.debug("Auto-creation disabled, using original connection string")
            return connection_string

        components = None
        try:
            # Parse connection string
            components = self.utils.parse_connection_string(connection_string)

            # SQLite doesn't need database creation
            if not components["needs_creation"]:
                logger.debug(
                    f"Database engine {components['engine']} auto-creates, no action needed"
                )
                return connection_string

            # Skip noisy warnings for managed GibsonAI temporary databases
            if self._is_gibsonai_temp_connection(components):
                logger.debug(
                    "[DB_SETUP] GibsonAI managed database detected - skipping auto-creation checks"
                )
                return connection_string

            # Validate database name
            if not self.utils.validate_database_name(components["database"]):
                raise ValueError(f"Invalid database name: {components['database']}")

            # Check if database exists
            if self._database_exists(components):
                logger.debug(f"Database '{components['database']}' already exists")
                return connection_string

            # Create database
            self._create_database(components)
            logger.info(f"Successfully created database '{components['database']}'")
            return connection_string

        except PermissionError as e:
            if components and self._is_gibsonai_temp_connection(components):
                logger.debug(
                    "[DB_SETUP] GibsonAI managed database does not allow auto-creation (permission denied)"
                )
                return connection_string

            logger.error(f"[DB_SETUP] Permission denied - {e}")
            if components:
                logger.warning(
                    f"[DB_SETUP] Database '{components['database']}' may need manual creation with proper permissions"
                )
            else:
                logger.warning(
                    "[DB_SETUP] Database may need manual creation with proper permissions"
                )
            return connection_string
        except RuntimeError as e:
            logger.error(f"[DB_SETUP] Database creation error - {e}")
            logger.info(
                "[DB_SETUP] Proceeding with original connection string, database may need manual setup"
            )
            return connection_string
        except Exception as e:
            logger.error(
                f"[DB_SETUP] Unexpected database auto-creation failure - {type(e).__name__}: {e}"
            )
            if components:
                logger.debug(
                    f"[DB_SETUP] Connection string: {components['engine']}://{components['host']}:{components['port']}/{components['database']}"
                )
            else:
                logger.debug(f"[DB_SETUP] Connection string: {connection_string}")
            return connection_string

    def _database_exists(self, components: dict[str, str]) -> bool:
        """Check if target database exists."""
        try:
            engine = components["engine"]

            if engine == "postgresql":
                return self._postgresql_database_exists(components)
            elif engine == "mysql":
                return self._mysql_database_exists(components)
            else:
                logger.warning(f"Database existence check not supported for {engine}")
                return False

        except Exception as e:
            if self._is_gibsonai_temp_connection(components):
                logger.debug(
                    "[DB_CONNECTION] Skipping GibsonAI database existence check due to restricted permissions"
                )
            else:
                logger.error(f"Failed to check database existence: {e}")
            return False

    def _postgresql_database_exists(self, components: dict[str, str]) -> bool:
        """Check if PostgreSQL database exists."""
        try:
            # Connect to postgres system database
            engine = create_engine(components["default_url"])

            with engine.connect() as conn:
                result = conn.execute(
                    text("SELECT 1 FROM pg_database WHERE datname = :dbname"),
                    {"dbname": components["database"]},
                )
                exists = result.fetchone() is not None

            engine.dispose()
            return exists

        except Exception as e:
            logger.error(f"PostgreSQL database existence check failed: {e}")
            return False

    def _get_mysql_connect_args(self, original_url: str) -> dict:
        """Get MySQL connection arguments with SSL support for system database connections."""
        connect_args = {"charset": "utf8mb4"}

        # Parse original URL for SSL parameters
        parsed = urlparse(original_url)
        if parsed.query:
            query_params = parse_qs(parsed.query)

            # Handle SSL parameters for PyMySQL - same logic as sqlalchemy_manager
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
                elif query_params.get("ssl_disabled", ["true"])[0].lower() == "false":
                    # Enable SSL with secure configuration for required secure transport
                    connect_args["ssl"] = {
                        "ssl_disabled": False,
                        "check_hostname": False,
                        "verify_mode": ssl.CERT_NONE,
                    }
                    # Also add ssl_disabled=False for PyMySQL
                    connect_args["ssl_disabled"] = False

        return connect_args

    def _mysql_database_exists(self, components: dict[str, str]) -> bool:
        """Check if MySQL database exists."""
        try:
            # Connect to mysql system database with SSL support
            connect_args = self._get_mysql_connect_args(components["original_url"])
            engine = create_engine(components["default_url"], connect_args=connect_args)

            with engine.connect() as conn:
                result = conn.execute(
                    text(
                        "SELECT SCHEMA_NAME FROM INFORMATION_SCHEMA.SCHEMATA WHERE SCHEMA_NAME = :dbname"
                    ),
                    {"dbname": components["database"]},
                )
                exists = result.fetchone() is not None

            engine.dispose()
            return exists

        except ModuleNotFoundError as e:
            if "mysql" in str(e).lower():
                logger.error(f"MySQL database existence check failed: {e}")
                error_msg = (
                    "ERROR: MySQL driver not found for database existence check. Install one of:\n"
                    "- pip install mysql-connector-python\n"
                    "- pip install PyMySQL\n"
                    "- pip install memorisdk[mysql]"
                )
                logger.error(error_msg)
            return False
        except Exception as e:
            if self._is_gibsonai_temp_connection(components):
                logger.debug(
                    f"[DB_CONNECTION] GibsonAI existence check bypassed for '{components['database']}' ({e})"
                )
            else:
                logger.error(
                    f"[DB_CONNECTION] MySQL database existence check failed for '{components['database']}': {e}"
                )
                logger.debug(
                    f"[DB_CONNECTION] Connection details - host: {components.get('host')}, port: {components.get('port')}, user: {components.get('user') or components.get('username')}"
                )
            return False

    def _create_database(self, components: dict[str, str]) -> None:
        """Create the target database."""
        engine = components["engine"]

        if engine == "postgresql":
            self._create_postgresql_database(components)
        elif engine == "mysql":
            self._create_mysql_database(components)
        else:
            raise ValueError(f"Database creation not supported for {engine}")

    def _create_postgresql_database(self, components: dict[str, str]) -> None:
        """Create PostgreSQL database."""
        try:
            logger.info(f"Creating PostgreSQL database '{components['database']}'...")

            # Connect to postgres system database
            engine = create_engine(components["default_url"])

            # PostgreSQL requires autocommit for CREATE DATABASE
            with engine.connect() as conn:
                # Set autocommit mode
                conn = conn.execution_options(isolation_level="AUTOCOMMIT")

                # Create database (can't use parameters for database name)
                # Database name is already validated, so this is safe
                conn.execute(text(f'CREATE DATABASE "{components["database"]}"'))

            engine.dispose()
            logger.info(
                f"PostgreSQL database '{components['database']}' created successfully"
            )

        except (OperationalError, ProgrammingError) as e:
            error_msg = str(e)
            if "already exists" in error_msg.lower():
                logger.info(
                    f"PostgreSQL database '{components['database']}' already exists"
                )
                return
            elif "permission denied" in error_msg.lower():
                raise PermissionError(
                    f"Insufficient permissions to create database '{components['database']}'"
                )
            else:
                raise RuntimeError(f"Failed to create PostgreSQL database: {e}")

        except Exception as e:
            raise RuntimeError(f"Unexpected error creating PostgreSQL database: {e}")

    def _create_mysql_database(self, components: dict[str, str]) -> None:
        """Create MySQL database."""
        try:
            logger.info(f"Creating MySQL database '{components['database']}'...")

            # Connect to mysql system database with SSL support
            connect_args = self._get_mysql_connect_args(components["original_url"])
            engine = create_engine(components["default_url"], connect_args=connect_args)

            with engine.connect() as conn:
                # Create database (can't use parameters for database name)
                # Database name is already validated, so this is safe
                conn.execute(
                    text(
                        f'CREATE DATABASE `{components["database"]}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci'
                    )
                )
                conn.commit()

            engine.dispose()
            logger.info(
                f"MySQL database '{components['database']}' created successfully"
            )

        except ModuleNotFoundError as e:
            if "mysql" in str(e).lower():
                error_msg = (
                    "ERROR: MySQL driver not found for database creation. Install one of:\n"
                    "- pip install mysql-connector-python\n"
                    "- pip install PyMySQL\n"
                    "- pip install memorisdk[mysql]"
                )
                logger.error(error_msg)
                raise RuntimeError(error_msg)
            else:
                raise RuntimeError(f"Missing dependency for database creation: {e}")
        except (OperationalError, ProgrammingError) as e:
            error_msg = str(e)
            if "database exists" in error_msg.lower():
                logger.info(f"MySQL database '{components['database']}' already exists")
                return
            elif "access denied" in error_msg.lower():
                raise PermissionError(
                    f"Insufficient permissions to create database '{components['database']}'"
                )
            else:
                raise RuntimeError(f"Failed to create MySQL database: {e}")

        except Exception as e:
            raise RuntimeError(f"Unexpected error creating MySQL database: {e}")

    def get_database_info(self, connection_string: str) -> dict[str, str]:
        """
        Get detailed information about database from connection string.

        Args:
            connection_string: Database connection URL

        Returns:
            Dictionary with database information
        """
        try:
            components = self.utils.parse_connection_string(connection_string)

            info = {
                "engine": components["engine"],
                "database": components["database"],
                "host": components["host"],
                "port": components["port"],
                "needs_creation": components["needs_creation"],
                "auto_creation_enabled": self.schema_init,
            }

            # Add existence check if auto-creation is enabled
            if self.schema_init and components["needs_creation"]:
                info["exists"] = self._database_exists(components)

            return info

        except Exception as e:
            logger.error(f"Failed to get database info: {e}")
            return {"error": str(e)}


class DatabaseCreationError(Exception):
    """Raised when database creation fails"""

    pass
