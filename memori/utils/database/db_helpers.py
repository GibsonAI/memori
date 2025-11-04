"""
Database Helper Utilities

Provides database-agnostic utilities for handling different database types
(PostgreSQL, MySQL, SQLite, MongoDB) and their specific requirements.
"""

import json
from typing import Any

from ..logging import get_logger

logger = get_logger("db_helpers")


def detect_database_type(connection: Any) -> str:
    """
    Detect the database type from a connection or engine.

    Args:
        connection: SQLAlchemy connection, engine, or session

    Returns:
        Database type as lowercase string: "postgresql", "mysql", "sqlite", "mongodb"

    Example:
        >>> db_type = detect_database_type(connection)
        >>> if db_type == "postgresql":
        ...     # PostgreSQL-specific logic
    """
    try:
        # Handle different types of connection objects
        if hasattr(connection, "engine"):
            # Session or Connection object
            engine = connection.engine
        elif hasattr(connection, "dialect"):
            # Engine object directly
            engine = connection
        else:
            # Try to get engine from bind
            engine = getattr(connection, "bind", connection)

        # Get dialect name (e.g., "postgresql", "mysql", "sqlite")
        db_type = str(engine.dialect.name).lower()

        logger.debug(f"Detected database type: {db_type}")
        return db_type

    except Exception as e:
        logger.warning(f"Could not detect database type, defaulting to 'unknown': {e}")
        return "unknown"


def serialize_json_for_db(data: Any, db_type: str | None = None) -> str:
    """
    Serialize data to JSON string for database storage.

    Handles conversion of dictionaries and other objects to JSON strings
    suitable for database storage.

    Args:
        data: Data to serialize (dict, list, str, etc.)
        db_type: Optional database type for type-specific handling

    Returns:
        JSON string suitable for database storage

    Example:
        >>> data = {"key": "value"}
        >>> json_str = serialize_json_for_db(data, "postgresql")
    """
    if data is None:
        return json.dumps(None)

    # If already a string, return as-is
    if isinstance(data, str):
        # Validate it's valid JSON
        try:
            json.loads(data)
            return data
        except (json.JSONDecodeError, TypeError):
            # Not valid JSON, wrap it
            return json.dumps(data)

    # Serialize dict, list, or other JSON-serializable objects
    try:
        return json.dumps(data, ensure_ascii=False, default=str)
    except (TypeError, ValueError) as e:
        logger.warning(f"Error serializing data to JSON: {e}, converting to string")
        return json.dumps(str(data))


def get_json_cast_clause(db_type: str, column_name: str = "processed_data") -> str:
    """
    Get the appropriate SQL CAST clause for JSON data based on database type.

    Different databases handle JSON differently:
    - PostgreSQL: Use JSONB type with CAST
    - MySQL 5.7+: Use JSON type
    - SQLite: Store as TEXT
    - MongoDB: Native JSON support

    Args:
        db_type: Database type ("postgresql", "mysql", "sqlite", etc.)
        column_name: Name of the column (for parameterized queries use :column_name)

    Returns:
        SQL fragment for casting JSON (e.g., "CAST(:processed_data AS JSONB)")

    Example:
        >>> cast_clause = get_json_cast_clause("postgresql", ":processed_data")
        >>> # Returns: "CAST(:processed_data AS JSONB)"
        >>> query = f"INSERT INTO table (data) VALUES ({cast_clause})"
    """
    db_type = db_type.lower()

    if db_type == "postgresql":
        # PostgreSQL uses JSONB for better performance
        return f"CAST({column_name} AS JSONB)"

    elif db_type == "mysql":
        # MySQL 5.7+ supports JSON type
        return f"CAST({column_name} AS JSON)"

    else:
        # SQLite and others: store as TEXT, no casting needed
        return column_name


def build_json_insert_clause(
    db_type: str, columns_with_json: list[str]
) -> dict[str, str]:
    """
    Build column name to SQL clause mapping for INSERT statements with JSON columns.

    Args:
        db_type: Database type
        columns_with_json: List of column names that contain JSON data

    Returns:
        Dictionary mapping column names to SQL clauses

    Example:
        >>> clauses = build_json_insert_clause("postgresql", ["processed_data", "metadata_json"])
        >>> # Returns: {
        >>>     "processed_data": "CAST(:processed_data AS JSONB)",
        >>>     "metadata_json": "CAST(:metadata_json AS JSONB)"
        >>> }
    """
    return {col: get_json_cast_clause(db_type, f":{col}") for col in columns_with_json}


def is_postgres(connection: Any) -> bool:
    """
    Quick check if connection is PostgreSQL.

    Args:
        connection: Database connection/engine/session

    Returns:
        True if PostgreSQL, False otherwise
    """
    return detect_database_type(connection) == "postgresql"


def is_mysql(connection: Any) -> bool:
    """
    Quick check if connection is MySQL.

    Args:
        connection: Database connection/engine/session

    Returns:
        True if MySQL, False otherwise
    """
    return detect_database_type(connection) == "mysql"


def is_sqlite(connection: Any) -> bool:
    """
    Quick check if connection is SQLite.

    Args:
        connection: Database connection/engine/session

    Returns:
        True if SQLite, False otherwise
    """
    return detect_database_type(connection) == "sqlite"


def get_insert_statement(
    table_name: str,
    columns: list[str],
    db_type: str,
    json_columns: list[str] | None = None,
) -> str:
    """
    Generate a database-agnostic INSERT statement with proper JSON casting.

    Args:
        table_name: Name of the table
        columns: List of column names
        db_type: Database type
        json_columns: List of columns that contain JSON data (optional)

    Returns:
        SQL INSERT statement with proper casting

    Example:
        >>> stmt = get_insert_statement(
        ...     "short_term_memory",
        ...     ["memory_id", "processed_data", "importance_score"],
        ...     "postgresql",
        ...     json_columns=["processed_data"]
        ... )
        >>> # Returns INSERT statement with CAST(:processed_data AS JSONB)
    """
    json_columns = json_columns or []

    # Build column list
    columns_str = ", ".join(columns)

    # Build values list with proper casting
    values = []
    for col in columns:
        if col in json_columns:
            values.append(get_json_cast_clause(db_type, f":{col}"))
        else:
            values.append(f":{col}")

    values_str = ", ".join(values)

    return f"INSERT INTO {table_name} ({columns_str}) VALUES ({values_str})"


# Convenience function for common case
def prepare_json_data(data: Any, connection: Any) -> str:
    """
    Convenience function to detect DB type and serialize JSON in one call.

    Args:
        data: Data to serialize
        connection: Database connection

    Returns:
        JSON string suitable for the detected database type

    Example:
        >>> json_str = prepare_json_data({"key": "value"}, connection)
    """
    db_type = detect_database_type(connection)
    return serialize_json_for_db(data, db_type)
