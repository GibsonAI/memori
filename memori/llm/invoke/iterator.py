import time

from memori.llm._base import BaseIterator
from memori.llm.helpers.serialization import format_kwargs, format_response
from memori.llm.pipelines.post_invoke import format_payload, run_post_invoke


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
            run_post_invoke(
                self.invoke,
                self._kwargs,
                format_payload(
                    self.invoke,
                    self.config.framework.provider,
                    self.config.llm.provider,
                    self.config.llm.version,
                    self._time_start,
                    time.time(),
                    format_kwargs(
                        self._kwargs,
                        uses_protobuf=self.invoke._uses_protobuf,
                        framework_provider=self.config.framework.provider,
                        injected_count=self.invoke._injected_message_count,
                    ),
                    format_response(
                        self.raw_response, uses_protobuf=self.invoke._uses_protobuf
                    ),
                ),
            )
            raise

    async def __aenter__(self):
        if hasattr(self.source_iterator, "__aenter__"):
            await self.source_iterator.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        if hasattr(self.source_iterator, "__aexit__"):
            return await self.source_iterator.__aexit__(exc_type, exc, tb)
        return False


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
            run_post_invoke(
                self.invoke,
                self._kwargs,
                format_payload(
                    self.invoke,
                    self.config.framework.provider,
                    self.config.llm.provider,
                    self.config.llm.version,
                    self._time_start,
                    time.time(),
                    format_kwargs(
                        self._kwargs,
                        uses_protobuf=self.invoke._uses_protobuf,
                        framework_provider=self.config.framework.provider,
                        injected_count=self.invoke._injected_message_count,
                    ),
                    format_response(
                        self.raw_response, uses_protobuf=self.invoke._uses_protobuf
                    ),
                ),
            )

            raise

    def __enter__(self):
        if hasattr(self.source_iterator, "__enter__"):
            self.source_iterator.__enter__()
        return self

    def __exit__(self, exc_type, exc, tb):
        if hasattr(self.source_iterator, "__exit__"):
            return self.source_iterator.__exit__(exc_type, exc, tb)
        return False
