r"""
 __  __                           _
|  \/  | ___ _ __ ___   ___  _ __(_)
| |\/| |/ _ \ '_ ` _ \ / _ \| '__| |
| |  | |  __/ | | | | | (_) | |  | |
|_|  |_|\___|_| |_| |_|\___/|_|  |_|
                  perfectam memoriam
                       memorilabs.ai
"""

from memori.storage._base import BaseStorageAdapter
from memori.storage._registry import Registry


class CursorWrapper:
    def __init__(self, cursor):
        self._cursor = cursor

    def mappings(self):
        return MappingResult(self._cursor)

    def __getattr__(self, name):
        return getattr(self._cursor, name)


class MappingResult:
    def __init__(self, cursor):
        self._cursor = cursor

    def fetchone(self):
        row = self._cursor.fetchone()
        if row is None:
            return None
        columns = [col[0] for col in self._cursor.description]
        return dict(zip(columns, row, strict=True))

    def fetchall(self):
        rows = self._cursor.fetchall()
        columns = [col[0] for col in self._cursor.description]
        return [dict(zip(columns, row, strict=True)) for row in rows]


def is_dbapi_connection(conn):
    if not (
        hasattr(conn, "cursor")
        and hasattr(conn, "commit")
        and hasattr(conn, "rollback")
        and callable(getattr(conn, "cursor", None))
        and callable(getattr(conn, "commit", None))
        and callable(getattr(conn, "rollback", None))
    ):
        return False

    if hasattr(conn, "__class__"):
        module_name = conn.__class__.__module__
        if module_name.startswith("django.db"):
            return False
        class_name = conn.__class__.__name__
        if class_name in ("Session", "scoped_session", "AsyncSession"):
            return False
        if hasattr(conn, "get_bind"):
            return False

    return True


@Registry.register_adapter(is_dbapi_connection)
class Adapter(BaseStorageAdapter):
    def commit(self):
        self.conn.commit()
        return self

    def execute(self, operation, binds=()):
        cursor = self.conn.cursor()
        try:
            cursor.execute(operation, binds)
            return CursorWrapper(cursor)
        except Exception:
            cursor.close()
            raise

    def flush(self):
        return self

    def get_dialect(self):
        module_name = type(self.conn).__module__
        dialect_mapping = {
            "postgresql": ["psycopg"],
            "mysql": ["mysql", "MySQLdb", "pymysql"],
            "sqlite": ["sqlite"],
            "oracle": ["cx_Oracle", "oracledb"],
        }
        for dialect, identifiers in dialect_mapping.items():
            if any(identifier in module_name for identifier in identifiers):
                return dialect
        raise ValueError(
            f"Unable to determine dialect from connection module: {module_name}"
        )

    def rollback(self):
        self.conn.rollback()
        return self
