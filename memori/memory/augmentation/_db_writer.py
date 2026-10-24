r"""
 __  __                           _
|  \/  | ___ _ __ ___   ___  _ __(_)
| |\/| |/ _ \ '_ ` _ \ / _ \| '__| |
| |  | |  __/ | | | | | (_) | |  | |
|_|  |_|\___|_| |_| |_|\___/|_|  |_|
                  perfectam memoriam
                       memorilabs.ai
"""

import logging
import queue as queue_module
import threading
import time
from collections.abc import Callable

from memori.storage._connection import connection_context

logger = logging.getLogger(__name__)


class WriteTask:
    def __init__(
        self,
        *,
        conn_factory: Callable,
        method_path: str,
        args: tuple | None = None,
        kwargs: dict | None = None,
    ):
        self.conn_factory = conn_factory
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

    def ensure_started(self) -> None:
        with self.lock:
            if self.started:
                return

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

    def wait(self, timeout: float | None = None) -> bool:
        """Wait for queued and in-flight batches to finish within the timeout."""
        if self.queue is None:
            return True
        # Queue emptiness excludes tasks already being processed. Its completion
        # condition includes them until task_done(), without a polling grace period.
        with self.queue.all_tasks_done:
            return self.queue.all_tasks_done.wait_for(
                lambda: self.queue.unfinished_tasks == 0, timeout=timeout
            )

    def _run_loop(self) -> None:
        logger.debug("AA DB writer thread started")
        while True:
            try:
                self._drain_batches()
            except Exception:
                import traceback

                traceback.print_exc()
                time.sleep(1)

    def _drain_batches(self) -> None:
        """Drain queued writes, only holding a DB connection while busy.

        This opens a DB connection when there is at least one pending task, processes
        batches until the queue is idle, then closes the connection by exiting the
        connection context.
        """
        if self.queue is None:
            return

        batch = self._collect_batch()
        if not batch:
            return

        while batch:
            try:
                by_factory: dict[Callable, list[WriteTask]] = {}
                for task in batch:
                    by_factory.setdefault(task.conn_factory, []).append(task)

                for factory, tasks in by_factory.items():
                    with connection_context(factory) as (_conn, adapter, driver):
                        logger.debug(
                            "AA DB writer batch started - %d writes", len(tasks)
                        )
                        try:
                            for task in tasks:
                                task.execute(driver)

                            if adapter:
                                adapter.flush()
                                adapter.commit()
                            logger.debug("AA DB writer completing - batch committed")
                        except Exception:
                            import traceback

                            logger.debug("AA DB writer batch failed - rolling back")
                            traceback.print_exc()
                            if adapter:
                                try:
                                    adapter.rollback()
                                except Exception:  # nosec B110
                                    pass
            finally:
                for _ in batch:
                    self.queue.task_done()

            batch = self._collect_batch()

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
