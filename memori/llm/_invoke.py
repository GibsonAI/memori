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
from collections.abc import AsyncIterator, Iterator

from botocore.eventstream import EventStream
from grpc.experimental.aio import UnaryStreamCall

from memori._utils import merge_chunk
from memori.llm._base import BaseInvoke
from memori.llm._iterable import Iterable as MemoriIterable
from memori.llm._iterator import AsyncIterator as MemoriAsyncIterator
from memori.llm._iterator import Iterator as MemoriIterator
from memori.llm._streaming import StreamingBody as MemoriStreamingBody
from memori.llm._utils import client_is_bedrock


class Invoke(BaseInvoke):
    def invoke(self, **kwargs):
        start = time.time()

        kwargs = self.inject_conversation_messages(
            self.inject_recalled_facts(self.configure_for_streaming_usage(kwargs))
        )

        raw_response = self._method(**kwargs)

        if isinstance(raw_response, Iterator):
            return (
                MemoriIterator(self.config, raw_response)
                .configure_invoke(self)
                .configure_request(kwargs, start)
            )
        elif client_is_bedrock(
            self.config.framework.provider, self.config.llm.provider
        ):
            if isinstance(raw_response["body"], EventStream):
                raw_response["body"] = (
                    MemoriIterable(self.config, raw_response["body"])
                    .configure_invoke(self)
                    .configure_request(kwargs, start)
                )
            else:
                raw_response["body"] = (
                    MemoriStreamingBody(self.config, raw_response["body"])
                    .configure_invoke(self)
                    .configure_request(kwargs, start)
                )

            return raw_response
        else:
            self.handle_post_response(kwargs, start, raw_response)
            return raw_response


class InvokeAsync(BaseInvoke):
    async def invoke(self, **kwargs):
        start = time.time()

        kwargs = self.inject_conversation_messages(
            self.inject_recalled_facts(self.configure_for_streaming_usage(kwargs))
        )

        raw_response = await self._method(**kwargs)
        self.handle_post_response(kwargs, start, raw_response)
        return raw_response


class InvokeAsyncIterator(BaseInvoke):
    async def invoke(self, **kwargs):
        start = time.time()

        kwargs = self.inject_conversation_messages(
            self.inject_recalled_facts(self.configure_for_streaming_usage(kwargs))
        )

        raw_response = await self._method(**kwargs)
        if isinstance(raw_response, AsyncIterator) or isinstance(
            raw_response, UnaryStreamCall
        ):
            return (
                MemoriAsyncIterator(self.config, raw_response)
                .configure_invoke(self)
                .configure_request(kwargs, start)
            )
        else:
            self.handle_post_response(kwargs, start, raw_response)
            return raw_response


class InvokeAsyncStream(BaseInvoke):
    async def invoke(self, **kwargs):
        start = time.time()

        kwargs = self.inject_conversation_messages(
            self.inject_recalled_facts(self.configure_for_streaming_usage(kwargs))
        )

        stream = await self._method(**kwargs)

        raw_response = {}
        async for chunk in stream:
            raw_response = merge_chunk(raw_response, chunk.__dict__)
            yield chunk

        self.handle_post_response(kwargs, start, raw_response)


class InvokeStream(BaseInvoke):
    async def invoke(self, **kwargs):
        start = time.time()

        kwargs = self.inject_conversation_messages(
            self.inject_recalled_facts(self.configure_for_streaming_usage(kwargs))
        )

        raw_response = await self._method(**kwargs)

        self.handle_post_response(kwargs, start, raw_response)
        return raw_response
