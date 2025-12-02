import os

from pymongo import MongoClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool, StaticPool

# Default test session - uses DATABASE_URL environment variable
# Falls back to PostgreSQL for backward compatibility
test_db_uri = os.environ.get(
    "DATABASE_URL", "postgresql://memori:memori@postgres:5432/memori_test"
)

test_db_core = create_engine(test_db_uri, pool_pre_ping=True, pool_recycle=300)

TestDBSession = sessionmaker(autocommit=False, autoflush=False, bind=test_db_core)

# PostgreSQL-specific session
postgres_test_uri = os.environ.get(
    "POSTGRES_DATABASE_URL", "postgresql://memori:memori@postgres:5432/memori_test"
)

postgres_test_db_core = create_engine(
    postgres_test_uri, pool_pre_ping=True, pool_recycle=300
)

PostgresTestDBSession = sessionmaker(
    autocommit=False, autoflush=False, bind=postgres_test_db_core
)

# MySQL-specific session
mysql_test_uri = os.environ.get(
    "MYSQL_DATABASE_URL", "mysql+pymysql://memori:memori@mysql:3306/memori_test"
)

mysql_test_db_core = create_engine(mysql_test_uri, pool_pre_ping=True, pool_recycle=300)

MySQLTestDBSession = sessionmaker(
    autocommit=False, autoflush=False, bind=mysql_test_db_core
)

# SQLite-specific session
sqlite_test_uri = os.environ.get("SQLITE_DATABASE_URL", "sqlite:///memori_test.db")

sqlite_test_db_core = create_engine(
    sqlite_test_uri,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool if ":memory:" in sqlite_test_uri else NullPool,
)


@event.listens_for(sqlite_test_db_core, "connect")
def set_sqlite_pragma(dbapi_conn, connection_record):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.close()


SQLiteTestDBSession = sessionmaker(
    autocommit=False, autoflush=False, bind=sqlite_test_db_core
)

oracle_test_uri = os.environ.get(
    "ORACLE_DATABASE_URL",
    "oracle+oracledb://system:memori@oracle:1521/?service_name=FREEPDB1",
)

_oracle_test_db_core = None


def OracleTestDBSession():
    global _oracle_test_db_core
    if _oracle_test_db_core is None:
        _oracle_test_db_core = create_engine(
            oracle_test_uri, pool_pre_ping=True, pool_recycle=300
        )
    return sessionmaker(autocommit=False, autoflush=False, bind=_oracle_test_db_core)()


# MongoDB-specific session
mongodb_test_uri = os.environ.get(
    "MONGODB_URL", "mongodb://memori:memori@mongodb:27017/memori_test?authSource=admin"
)


def MongoTestDBSession():
    """Get a fresh MongoDB client instance."""
    return MongoClient(mongodb_test_uri)
