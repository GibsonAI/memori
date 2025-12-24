r"""
 __  __                           _
|  \/  | ___ _ __ ___   ___  _ __(_)
| |\/| |/ _ \ '_ ` _ \ / _ \| '__| |
| |  | |  __/ | | | | | (_) | |  | |
|_|  |_|\___|_| |_| |_|\___/|_|  |_|
                 perfectam memoriam
                      memorilabs.ai
"""

import asyncio
import logging
from collections.abc import Callable
from concurrent.futures import Future
from typing import Any

from memori._config import Config
from memori.memory.augmentation._base import AugmentationContext
from memori.memory.augmentation._db_writer import WriteTask, get_db_writer
from memori.memory.augmentation._registry import Registry as AugmentationRegistry
from memori.memory.augmentation._runtime import get_runtime
from memori.memory.augmentation.input import AugmentationInput
from memori.storage._connection import connection_context

logger = logging.getLogger(__name__)

MAX_WORKERS = 50
DB_WRITER_BATCH_SIZE = 100
DB_WRITER_BATCH_TIMEOUT = 0.1
DB_WRITER_QUEUE_SIZE = 1000
RUNTIME_READY_TIMEOUT = 1.0


class Manager:
    def __init__(self, config: Config) -> None:
        self.config = config
        self.augmentations = AugmentationRegistry().augmentations(config=config)
        self.conn_factory: Callable | None = None
        self._active = False
        self.max_workers = MAX_WORKERS
        self.db_writer_batch_size = DB_WRITER_BATCH_SIZE
        self.db_writer_batch_timeout = DB_WRITER_BATCH_TIMEOUT
        self.db_writer_queue_size = DB_WRITER_QUEUE_SIZE
        self._quota_error: Exception | None = None
        self._pending_futures: list[Future[Any]] = []

    def start(self, conn: Callable | Any) -> "Manager":
        """Start the augmentation manager with a database connection.

        Args:
            conn: Either a callable that returns a connection (e.g. sessionmaker)
                  or a connection instance (will be wrapped in a lambda).
        """
        if conn is None:
            return self

        if callable(conn):
            self.conn_factory = conn
        else:
            self.conn_factory = lambda: conn

        self._active = True

        runtime = get_runtime()
        runtime.ensure_started(self.max_workers)

        db_writer = get_db_writer()
        db_writer.configure(self)
        db_writer.ensure_started(self.conn_factory)

        return self

    def enqueue(self, input_data: AugmentationInput) -> "Manager":
        if self._quota_error:
            raise self._quota_error

        if not self._active or not self.conn_factory:
            logger.debug("Augmentation enqueue skipped - not active or no connection")
            return self

        runtime = get_runtime()

        if not runtime.ready.wait(timeout=RUNTIME_READY_TIMEOUT):
            raise RuntimeError("Augmentation runtime is not available")

        if runtime.loop is None:
            raise RuntimeError("Event loop is not available")

        logger.debug("AA enqueued - scheduling augmentation processing")
        future = asyncio.run_coroutine_threadsafe(
            self._process_augmentations(input_data), runtime.loop
        )
        self._pending_futures.append(future)
        future.add_done_callback(lambda f: self._handle_augmentation_result(f))
        return self

    def _handle_augmentation_result(self, future: Future[Any]) -> None:
        from memori._exceptions import QuotaExceededError

        try:
            future.result()
        except QuotaExceededError as e:
            self._quota_error = e
            self._active = False
            logger.error(f"Quota exceeded, disabling augmentation: {e}")
        except Exception as e:
            logger.error(f"Augmentation task failed: {e}", exc_info=True)
        finally:
            if future in self._pending_futures:
                self._pending_futures.remove(future)

    async def _process_augmentations(self, input_data: AugmentationInput) -> None:
        if not self.augmentations:
            logger.debug("No augmentations configured")
            return

        runtime = get_runtime()
        if runtime.semaphore is None:
            return

        logger.debug("AA processing started")
        async with runtime.semaphore:
            ctx = AugmentationContext(payload=input_data)

            try:
                with connection_context(self.conn_factory) as (conn, adapter, driver):
                    for aug in self.augmentations:
                        if aug.enabled:
                            try:
                                logger.debug(
                                    "Running augmentation: %s", aug.__class__.__name__
                                )
                                ctx = await aug.process(ctx, driver)
                            except Exception as e:
                                from memori._exceptions import QuotaExceededError

                                if isinstance(e, QuotaExceededError):
                                    raise
                                logger.error(
                                    f"Error in augmentation {aug.__class__.__name__}: {e}",
                                    exc_info=True,
                                )

                    if ctx.writes:
                        logger.debug("AA scheduling %d DB writes", len(ctx.writes))
                        self._enqueue_writes(ctx.writes)
            except Exception as e:
                from memori._exceptions import QuotaExceededError

                if isinstance(e, QuotaExceededError):
                    raise
                logger.error(f"Error processing augmentations: {e}", exc_info=True)

    def _enqueue_writes(self, writes: list[dict[str, Any]]) -> None:
        db_writer = get_db_writer()

        for write_op in writes:
            task = WriteTask(
                method_path=write_op["method_path"],
                args=write_op["args"],
                kwargs=write_op["kwargs"],
            )
            db_writer.enqueue_write(task)

    def wait(self, timeout: float | None = None) -> bool:
        import concurrent.futures
        import time

        start_time = time.time()

        # Wait for pending futures to complete
        if self._pending_futures:
            try:
                concurrent.futures.wait(
                    self._pending_futures,
                    timeout=timeout,
                    return_when=concurrent.futures.ALL_COMPLETED,
                )
            except Exception:
                return False

            if self._pending_futures:
                return False

        # Wait for db_writer queue to drain and batch to process
        db_writer = get_db_writer()
        if db_writer.queue is None:
            return True

        deadline = None if timeout is None else start_time + timeout
        poll_interval = 0.01

        # Wait for queue to be empty
        while not db_writer.queue.empty():
            if deadline and time.time() >= deadline:
                return False
            time.sleep(poll_interval)

        # Wait for final batch processing (2x batch_timeout)
        extra_wait = db_writer.batch_timeout * 2
        if deadline:
            extra_wait = min(extra_wait, deadline - time.time())

        if extra_wait > 0:
            time.sleep(extra_wait)

        return True
