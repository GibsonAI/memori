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
            return self

        runtime = get_runtime()

        if not runtime.ready.wait(timeout=RUNTIME_READY_TIMEOUT):
            raise RuntimeError("Augmentation runtime is not available")

        if runtime.loop is None:
            raise RuntimeError("Event loop is not available")

        future = asyncio.run_coroutine_threadsafe(
            self._process_augmentations(input_data), runtime.loop
        )
        future.add_done_callback(lambda f: self._handle_augmentation_result(f))
        return self

    def _handle_augmentation_result(self, future: asyncio.Future[None]) -> None:
        from memori._exceptions import QuotaExceededError

        try:
            future.result()
        except QuotaExceededError as e:
            self._quota_error = e
            self._active = False
            logger.error(f"Quota exceeded, disabling augmentation: {e}")
        except Exception as e:
            logger.error(f"Augmentation task failed: {e}", exc_info=True)

    async def _process_augmentations(self, input_data: AugmentationInput) -> None:
        if not self.augmentations:
            return

        runtime = get_runtime()
        if runtime.semaphore is None:
            return

        async with runtime.semaphore:
            ctx = AugmentationContext(payload=input_data)

            try:
                with connection_context(self.conn_factory) as (conn, adapter, driver):
                    for aug in self.augmentations:
                        if aug.enabled:
                            try:
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
