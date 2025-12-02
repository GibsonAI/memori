r"""
 __  __                           _
|  \/  | ___ _ __ ___   ___  _ __(_)
| |\/| |/ _ \ '_ ` _ \ / _ \| '__| |
| |  | |  __/ | | | | | (_) | |  | |
|_|  |_|\___|_| |_| |_|\___/|_|  |_|
                  perfectam memoriam
                       memorilabs.ai
"""

from collections.abc import Callable
from typing import Any

from memori.storage._base import BaseStorageAdapter


class Registry:
    _adapters: dict[Callable[[Any], bool], type[BaseStorageAdapter]] = {}
    _drivers: dict[str, type] = {}

    @classmethod
    def register_adapter(cls, matcher: Callable[[Any], bool]):
        def decorator(adapter_class: type[BaseStorageAdapter]):
            cls._adapters[matcher] = adapter_class
            return adapter_class

        return decorator

    @classmethod
    def register_driver(cls, dialect: str):
        def decorator(driver_class: type):
            cls._drivers[dialect] = driver_class
            return driver_class

        return decorator

    def adapter(self, conn: Any) -> BaseStorageAdapter:
        conn_to_check = conn() if callable(conn) else conn

        for matcher, adapter_class in self._adapters.items():
            if matcher(conn_to_check):
                return adapter_class(lambda: conn_to_check)

        raise ValueError(
            f"No adapter registered for connection type: {type(conn_to_check).__module__}"
        )

    def driver(self, conn: BaseStorageAdapter):
        dialect = conn.get_dialect()
        if dialect not in self._drivers:
            raise ValueError(
                f"No driver registered for dialect: {dialect}. "
                f"Available dialects: {list(self._drivers.keys())}"
            )
        return self._drivers[dialect](conn)
