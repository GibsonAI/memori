"""
Database connectors for different database backends
"""

from .mysql_connector import MySQLConnector
from .postgres_connector import PostgreSQLConnector
from .sqlite_connector import SQLiteConnector

try:
    from .mongodb_connector import MongoDBConnector

    MONGODB_AVAILABLE = True
except ImportError:
    MongoDBConnector = None  # type: ignore
    MONGODB_AVAILABLE = False

try:
    from .couchbase_connector import CouchbaseConnector

    COUCHBASE_AVAILABLE = True
except ImportError:
    CouchbaseConnector = None  # type: ignore
    COUCHBASE_AVAILABLE = False

__all__ = ["SQLiteConnector", "PostgreSQLConnector", "MySQLConnector"]

if MONGODB_AVAILABLE:
    __all__.append("MongoDBConnector")

if COUCHBASE_AVAILABLE:
    __all__.append("CouchbaseConnector")
