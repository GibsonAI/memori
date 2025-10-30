"""
Database adapters for different database backends
Provides database-specific implementations with proper security measures
"""

from .mysql_adapter import MySQLSearchAdapter
from .postgresql_adapter import PostgreSQLSearchAdapter
from .sqlite_adapter import SQLiteSearchAdapter

try:
    from .mongodb_adapter import MongoDBAdapter

    MONGODB_ADAPTER_AVAILABLE = True
except ImportError:
    MongoDBAdapter = None  # type: ignore
    MONGODB_ADAPTER_AVAILABLE = False

try:
    from .couchbase_adapter import CouchbaseAdapter

    COUCHBASE_ADAPTER_AVAILABLE = True
except ImportError:
    CouchbaseAdapter = None  # type: ignore
    COUCHBASE_ADAPTER_AVAILABLE = False

__all__ = ["SQLiteSearchAdapter", "PostgreSQLSearchAdapter", "MySQLSearchAdapter"]

if MONGODB_ADAPTER_AVAILABLE:
    __all__.append("MongoDBAdapter")

if COUCHBASE_ADAPTER_AVAILABLE:
    __all__.append("CouchbaseAdapter")
