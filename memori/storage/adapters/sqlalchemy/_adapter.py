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


@Registry.register_adapter(
    lambda conn: type(conn).__module__ == "sqlalchemy.orm.session"
)
class Adapter(BaseStorageAdapter):
    def commit(self):
        self.conn.commit()
        return self

    def execute(self, operation, binds=()):
        return self.conn.connection().exec_driver_sql(operation, binds)

    def flush(self):
        self.conn.flush()
        return self

    def get_dialect(self):
        return self.conn.get_bind().dialect.name

    def rollback(self):
        self.conn.rollback()
        return self
