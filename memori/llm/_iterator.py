r"""
 __  __                           _
|  \/  | ___ _ __ ___   ___  _ __(_)
| |\/| |/ _ \ '_ ` _ \ / _ \| '__| |
| |  | |  __/ | | | | | (_) | |  | |
|_|  |_|\___|_| |_| |_|\___/|_|  |_|
                  perfectam memoriam
                       memorilabs.ai
"""

import time

from memori.llm._base import BaseIterator
from memori.memory._manager import Manager as MemoryManager


class AsyncIterator(BaseIterator):
    def __aiter__(self):
        self.iterator = self.source_iterator.__aiter__()
        return self

    async def __anext__(self):
        try:
            if self.iterator is None:
                raise RuntimeError("Iterator not initialized")
            chunk = await self.iterator.__anext__()

            self.set_raw_response()
            self.process_chunk(chunk)

            return chunk
        except StopAsyncIteration:
            MemoryManager(self.config).execute(
                self.invoke._format_payload(
                    self.config.framework.provider,
                    self.config.llm.provider,
                    self.config.llm.version,
                    self._time_start,
                    time.time(),
                    self.invoke._format_kwargs(self._kwargs),
                    self.invoke._format_response(self.raw_response),
                )
            )
            raise

    async def __aenter__(self):
        await self.source_iterator.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return await self.source_iterator.__aexit__(exc_type, exc, tb)


class Iterator(BaseIterator):
    def __iter__(self):
        return self

    def __next__(self):
        try:
            chunk = next(self.source_iterator)

            self.set_raw_response()
            self.process_chunk(chunk)

            return chunk
        except StopIteration:
            MemoryManager(self.config).execute(
                self.invoke._format_payload(
                    self.config.framework.provider,
                    self.config.llm.provider,
                    self.config.llm.version,
                    self._time_start,
                    time.time(),
                    self.invoke._format_kwargs(self._kwargs),
                    self.invoke._format_response(self.raw_response),
                )
            )

            raise

    def __enter__(self):
        self.source_iterator.__enter__()
        return self

    def __exit__(self, exc_type, exc, tb):
        return self.source_iterator.__exit__(exc_type, exc, tb)
