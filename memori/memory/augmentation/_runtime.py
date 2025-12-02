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
import threading


class AugmentationRuntime:
    def __init__(self):
        self.loop = None
        self.ready = threading.Event()
        self.semaphore = None
        self.max_workers = 50
        self.thread = None
        self.lock = threading.Lock()
        self.started = False

    def ensure_started(self, max_workers: int):
        with self.lock:
            if self.started:
                return

            self.max_workers = max_workers
            self.thread = threading.Thread(
                target=self._run_loop, daemon=True, name="memori-augmentation"
            )
            self.thread.start()
            self.started = True

    def _run_loop(self) -> None:
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.semaphore = asyncio.Semaphore(self.max_workers)
        self.ready.set()
        self.loop.run_forever()


_runtime = AugmentationRuntime()


def get_runtime() -> AugmentationRuntime:
    return _runtime
