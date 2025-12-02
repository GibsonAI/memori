r"""
 __  __                           _
|  \/  | ___ _ __ ___   ___  _ __(_)
| |\/| |/ _ \ '_ ` _ \ / _ \| '__| |
| |  | |  __/ | | | | | (_) | |  | |
|_|  |_|\___|_| |_| |_|\___/|_|  |_|
                  perfectam memoriam
                       memorilabs.ai
"""

import queue as queue_module
import threading
import time
from collections.abc import Callable

from memori.storage._connection import connection_context


class WriteTask:
    def __init__(
        self, method_path: str, args: tuple | None = None, kwargs: dict | None = None
    ):
        self.method_path = method_path
        self.args = args or ()
        self.kwargs = kwargs or {}

    def execute(self, driver):
        method = self._resolve_method(driver, self.method_path)
        if method:
            return method(*self.args, **self.kwargs)

    def _resolve_method(self, driver, method_path: str):
        parts = method_path.split(".")
        obj = driver

        for part in parts:
            if not hasattr(obj, part):
                return None
            obj = getattr(obj, part)

        return obj if callable(obj) else None


class DbWriterRuntime:
    def __init__(self):
        self.queue = None
        self.conn_factory = None
        self.batch_size = 100
        self.batch_timeout = 0.1
        self.thread = None
        self.lock = threading.Lock()
        self.started = False

    def configure(self, config):
        self.batch_size = config.db_writer_batch_size
        self.batch_timeout = config.db_writer_batch_timeout

        if self.queue is None:
            self.queue = queue_module.Queue(maxsize=config.db_writer_queue_size)

        return self

    def ensure_started(self, conn_factory: Callable) -> None:
        with self.lock:
            if self.started:
                return

            self.conn_factory = conn_factory
            self.thread = threading.Thread(
                target=self._run_loop, daemon=True, name="memori-db-writer"
            )
            self.thread.start()
            self.started = True

    def enqueue_write(self, task: WriteTask, timeout: float = 5.0) -> bool:
        try:
            if self.queue is None:
                return False
            self.queue.put(task, timeout=timeout)
            return True
        except queue_module.Full:
            return False

    def _run_loop(self) -> None:
        if self.conn_factory is None:
            return

        while True:
            try:
                with connection_context(self.conn_factory) as (conn, adapter, driver):
                    while True:
                        batch = self._collect_batch()

                        if not batch:
                            time.sleep(self.batch_timeout)
                            continue

                        try:
                            for task in batch:
                                task.execute(driver)

                            if adapter:
                                adapter.flush()
                                adapter.commit()
                        except Exception:
                            import traceback

                            traceback.print_exc()
                            if adapter:
                                try:
                                    adapter.rollback()
                                except Exception:  # nosec B110
                                    pass
            except Exception:
                import traceback

                traceback.print_exc()
                time.sleep(1)

    def _collect_batch(self) -> list[WriteTask]:
        batch = []
        deadline = time.time() + self.batch_timeout

        while len(batch) < self.batch_size and time.time() < deadline:
            try:
                timeout = max(0.01, deadline - time.time())
                task = self.queue.get(timeout=timeout)
                batch.append(task)
            except queue_module.Empty:
                break

        return batch


_db_writer = DbWriterRuntime()


def get_db_writer() -> DbWriterRuntime:
    return _db_writer
