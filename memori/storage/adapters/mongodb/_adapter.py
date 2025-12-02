r"""
 __  __                           _
|  \/  | ___ _ __ ___   ___  _ __(_)
| |\/| |/ _ \ '_ ` _ \ / _ \| '__| |
| |  | |  __/ | | | | | (_) | |  | |
|_|  |_|\___|_| |_| |_|\___/|_|  |_|
                  perfectam memoriam
                       memorilabs.ai
"""

from pymongo.synchronous.mongo_client import MongoClient

from memori.storage._base import BaseStorageAdapter
from memori.storage._registry import Registry


@Registry.register_adapter(
    lambda conn: hasattr(conn, "database") and hasattr(conn, "list_collection_names")
)
class Adapter(BaseStorageAdapter):
    """MongoDB storage adapter for MongoDB database connections."""

    def execute(self, collection_name_or_ops, operation=None, *args, **kwargs):
        """Execute MongoDB operations.

        Args:
            collection_name_or_ops: Collection name, list of ops, or single op dict
            operation: MongoDB operation (find_one, insert_one, etc.) - optional
            *args: Positional arguments for the operation
            **kwargs: Keyword arguments for the operation
        """
        if isinstance(self.conn, MongoClient):
            db = self.conn.get_default_database()
        else:
            db = self.conn

        if db is None:
            raise RuntimeError("MongoDB database connection is None")

        if operation is None:
            if isinstance(collection_name_or_ops, list):
                for op in collection_name_or_ops:
                    self._execute_operation(db, op)
            elif isinstance(collection_name_or_ops, dict):
                self._execute_operation(db, collection_name_or_ops)
            return None

        collection = db[collection_name_or_ops]
        return getattr(collection, operation)(*args, **kwargs)

    def commit(self):
        """MongoDB doesn't require explicit commits for single operations."""
        pass

    def flush(self):
        """MongoDB doesn't require explicit flushes for single operations."""
        pass

    def rollback(self):
        """MongoDB doesn't require explicit rollbacks for single operations."""
        pass

    def close(self):
        """MongoDB client connection should not be closed per-operation.

        The MongoClient is designed to be long-lived and shared across threads.
        Closing it would invalidate all connections from the client pool.
        """
        pass

    def get_dialect(self):
        return "mongodb"

    def _execute_operation(self, db, op):
        """Execute a single MongoDB operation from a dict.

        Args:
            db: MongoDB database instance
            op: Dict with 'collection', 'method', 'args', and 'kwargs' keys
        """
        collection = db[op["collection"]]
        method = getattr(collection, op["method"])
        args = op.get("args", [])
        kwargs = op.get("kwargs", {})
        method(*args, **kwargs)
