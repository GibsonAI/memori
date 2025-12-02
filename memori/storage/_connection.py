r"""
 __  __                           _
|  \/  | ___ _ __ ___   ___  _ __(_)
| |\/| |/ _ \ '_ ` _ \ / _ \| '__| |
| |  | |  __/ | | | | | (_) | |  | |
|_|  |_|\___|_| |_| |_|\___/|_|  |_|
                  perfectam memoriam
                       memorilabs.ai
"""

from collections.abc import Callable, Generator
from contextlib import contextmanager
from typing import Any

from memori.storage._base import BaseStorageAdapter
from memori.storage._registry import Registry


@contextmanager
def connection_context(
    conn_factory: Callable[[], Any] | None,
) -> Generator[
    tuple[Any, BaseStorageAdapter, Any] | tuple[None, None, None], None, None
]:
    if conn_factory is None:
        yield None, None, None
        return

    conn = conn_factory()
    adapter = Registry().adapter(conn)
    driver = Registry().driver(adapter)

    try:
        yield conn, adapter, driver
        adapter.commit()
    except Exception:
        try:
            adapter.rollback()
        except Exception:  # nosec B110
            pass
        raise
    finally:
        try:
            adapter.close()
        except Exception:  # nosec B110
            pass
