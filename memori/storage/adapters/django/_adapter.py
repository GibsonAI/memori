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


def is_django_connection(conn):
    if not hasattr(conn, "__class__"):
        return False

    module_name = conn.__class__.__module__
    if not module_name.startswith("django.db"):
        return False

    if not (hasattr(conn, "cursor") and callable(getattr(conn, "cursor", None))):
        return False

    return True


@Registry.register_adapter(is_django_connection)
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
        vendor = self.conn.vendor
        dialect_mapping = {
            "postgresql": "postgresql",
            "mysql": "mysql",
            "sqlite": "sqlite",
            "oracle": "oracle",
        }
        if vendor in dialect_mapping:
            return dialect_mapping[vendor]
        raise ValueError(f"Unable to determine dialect from Django vendor: {vendor}")

    def rollback(self):
        self.conn.rollback()
        return self
