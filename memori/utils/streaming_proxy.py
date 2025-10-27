"""
Generic streaming proxy utilities for intercepting and processing streaming responses.

This module provides reusable classes for wrapping streaming responses,
capturing chunks, and processing them when the stream completes.
"""

from __future__ import annotations

import asyncio
import inspect
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from loguru import logger
from openai._streaming import AsyncStream, Stream
from openai.types.chat.chat_completion import (
    ChatCompletion,
)
from openai.types.chat.chat_completion import Choice as ChatCompletionChoice
from openai.types.chat.chat_completion_message import (
    ChatCompletionMessage,
)
from openai.types.chat.chat_completion_message import (
    FunctionCall as ChatCompletionFunctionCall,
)
from openai.types.chat.chat_completion_message_function_tool_call import (
    ChatCompletionMessageFunctionToolCall,
)
from openai.types.chat.chat_completion_message_function_tool_call import (
    Function as ChatCompletionToolFunction,
)
from openai.types.completion_usage import CompletionUsage


@dataclass
class _FunctionCallAccumulator:
    """Accumulates partial function call deltas."""

    name: str | None = None
    argument_parts: list[str] = field(default_factory=list)

    def add(self, delta) -> None:
        if delta is None:
            return
        if getattr(delta, "name", None):
            self.name = delta.name
        if getattr(delta, "arguments", None):
            self.argument_parts.append(delta.arguments)

    def build(self) -> ChatCompletionFunctionCall | None:
        if not (self.name or self.argument_parts):
            return None
        try:
            return ChatCompletionFunctionCall(
                name=self.name or "",
                arguments="".join(self.argument_parts),
            )
        except Exception as exc:  # pragma: no cover - defensive
            logger.debug(f"Failed to build function call: {exc}")
            return None


@dataclass
class _ToolCallAccumulator:
    """Accumulates partial tool call deltas."""

    index: int
    tool_id: str | None = None
    tool_type: str | None = None
    function_name: str | None = None
    argument_parts: list[str] = field(default_factory=list)

    def add(self, delta) -> None:
        if delta is None:
            return
        if getattr(delta, "id", None):
            self.tool_id = delta.id
        if getattr(delta, "type", None):
            self.tool_type = delta.type

        function_delta = getattr(delta, "function", None)
        if function_delta:
            if getattr(function_delta, "name", None):
                self.function_name = function_delta.name
            if getattr(function_delta, "arguments", None):
                self.argument_parts.append(function_delta.arguments)

    def build(self) -> ChatCompletionMessageFunctionToolCall | None:
        if not (self.tool_id or self.function_name or self.argument_parts):
            return None

        try:
            return ChatCompletionMessageFunctionToolCall(
                id=self.tool_id or f"tool_call_{self.index}",
                type=self.tool_type or "function",
                function=ChatCompletionToolFunction(
                    name=self.function_name or "",
                    arguments="".join(self.argument_parts),
                ),
            )
        except Exception as exc:  # pragma: no cover - defensive
            logger.debug(f"Failed to build tool call: {exc}")
            return None


@dataclass
class _ChoiceAccumulator:
    """Holds accumulated data for a single streamed choice."""

    index: int
    role: str | None = None
    content_parts: list[str] = field(default_factory=list)
    refusal_parts: list[str] = field(default_factory=list)
    finish_reason: str | None = None
    logprobs: Any = None
    function_call: _FunctionCallAccumulator = field(
        default_factory=_FunctionCallAccumulator
    )
    tool_calls: dict[int, _ToolCallAccumulator] = field(default_factory=dict)

    def add_delta(self, delta) -> None:
        if delta is None:
            return

        if getattr(delta, "role", None):
            self.role = delta.role
        if getattr(delta, "content", None):
            self.content_parts.append(delta.content)
        if getattr(delta, "refusal", None):
            self.refusal_parts.append(delta.refusal)

        self.function_call.add(getattr(delta, "function_call", None))

        tool_deltas = getattr(delta, "tool_calls", None) or []
        for tool_delta in tool_deltas:
            tool_acc = self.tool_calls.setdefault(
                getattr(tool_delta, "index", len(self.tool_calls)),
                _ToolCallAccumulator(index=getattr(tool_delta, "index", 0)),
            )
            tool_acc.add(tool_delta)

    def build_message(self) -> ChatCompletionMessage | None:
        try:
            message_kwargs = {
                "role": self.role or "assistant",
            }

            if self.content_parts:
                message_kwargs["content"] = "".join(self.content_parts)
            if self.refusal_parts:
                message_kwargs["refusal"] = "".join(self.refusal_parts)

            built_tool_calls = [
                tool_call
                for tool_call in (
                    tool_acc.build() for _, tool_acc in sorted(self.tool_calls.items())
                )
                if tool_call
            ]
            if built_tool_calls:
                message_kwargs["tool_calls"] = built_tool_calls

            function_call = self.function_call.build()
            if function_call:
                message_kwargs["function_call"] = function_call

            return ChatCompletionMessage(**message_kwargs)
        except Exception as exc:  # pragma: no cover - defensive
            logger.debug(f"Failed to build chat completion message: {exc}")
            return None


class _ChatCompletionStreamAggregator:
    """Aggregates OpenAI chat completion chunks into a final response."""

    def __init__(self) -> None:
        self._choices: dict[int, _ChoiceAccumulator] = {}
        self._has_chunks = False
        self._id: str | None = None
        self._created: int | None = None
        self._model: str | None = None
        self._service_tier: str | None = None
        self._system_fingerprint: str | None = None
        self._usage: CompletionUsage | None = None

    def add_chunk(self, chunk: Any) -> None:
        if chunk is None:
            return

        try:
            self._has_chunks = True

            if getattr(chunk, "id", None) and not self._id:
                self._id = chunk.id
            if getattr(chunk, "created", None) and not self._created:
                self._created = chunk.created
            if getattr(chunk, "model", None) and not self._model:
                self._model = chunk.model

            if getattr(chunk, "service_tier", None):
                self._service_tier = chunk.service_tier
            if getattr(chunk, "system_fingerprint", None):
                self._system_fingerprint = chunk.system_fingerprint
            if getattr(chunk, "usage", None):
                self._usage = chunk.usage

            for choice in getattr(chunk, "choices", []) or []:
                index = getattr(choice, "index", 0)
                accumulator = self._choices.setdefault(
                    index, _ChoiceAccumulator(index=index)
                )
                accumulator.add_delta(getattr(choice, "delta", None))

                if getattr(choice, "finish_reason", None):
                    accumulator.finish_reason = choice.finish_reason
                if getattr(choice, "logprobs", None):
                    accumulator.logprobs = choice.logprobs

        except Exception as exc:  # pragma: no cover - defensive
            logger.debug(f"Failed to aggregate streaming chunk: {exc}")

    def build(self) -> ChatCompletion | None:
        if not self._has_chunks or not self._choices:
            return None

        try:
            choices: list[ChatCompletionChoice] = []
            for index, accumulator in sorted(self._choices.items()):
                message = accumulator.build_message()
                if message is None:
                    continue

                choice_kwargs = {
                    "index": index,
                    "message": message,
                    "finish_reason": accumulator.finish_reason or "stop",
                }

                if accumulator.logprobs is not None:
                    choice_kwargs["logprobs"] = accumulator.logprobs

                choices.append(ChatCompletionChoice(**choice_kwargs))

            if not choices:
                return None

            chat_kwargs = {
                "id": self._id or "streaming_response",
                "choices": choices,
                "created": self._created or int(time.time()),
                "model": self._model or "unknown",
                "object": "chat.completion",
            }

            if self._service_tier is not None:
                chat_kwargs["service_tier"] = self._service_tier
            if self._system_fingerprint is not None:
                chat_kwargs["system_fingerprint"] = self._system_fingerprint
            if self._usage is not None:
                chat_kwargs["usage"] = self._usage

            return ChatCompletion(**chat_kwargs)
        except Exception as exc:  # pragma: no cover - defensive
            logger.debug(f"Failed to build aggregated chat completion: {exc}")
            return None


def _execute_finalize_callback_sync(
    callback: Callable[[Any, Any], Awaitable[None] | None] | None,
    final_response: Any,
    context_data: Any,
) -> None:
    if callback is None:
        return

    try:
        result = callback(final_response, context_data)
        if inspect.isawaitable(result):
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                asyncio.run(result)
            else:
                loop.create_task(result)
    except Exception as exc:  # pragma: no cover - defensive
        logger.error(f"Streaming finalize callback failed: {exc}")


async def _execute_finalize_callback_async(
    callback: Callable[[Any, Any], Awaitable[None] | None] | None,
    final_response: Any,
    context_data: Any,
) -> None:
    if callback is None:
        return

    try:
        result = callback(final_response, context_data)
        if inspect.isawaitable(result):
            await result
    except Exception as exc:  # pragma: no cover - defensive
        logger.error(f"Streaming finalize callback failed: {exc}")


class _SyncOpenAIStreamProxy:
    """Proxy for synchronous OpenAI streaming responses."""

    def __init__(
        self,
        stream: Stream,
        finalize_callback: Callable[[Any, Any], Awaitable[None] | None] | None,
        context_data: Any,
    ) -> None:
        self._stream = stream
        self._finalize_callback = finalize_callback
        self._context_data = context_data
        self._aggregator = _ChatCompletionStreamAggregator()
        self._final_response: ChatCompletion | None = None
        self._finalized = False

    def __getattr__(self, item: str) -> Any:
        return getattr(self._stream, item)

    def __iter__(self) -> _SyncOpenAIStreamProxy:
        return self

    def __next__(self) -> Any:
        try:
            chunk = next(self._stream)
        except StopIteration:
            self._finalize()
            raise
        else:
            self._aggregator.add_chunk(chunk)
            return chunk

    def __enter__(self) -> _SyncOpenAIStreamProxy:
        if hasattr(self._stream, "__enter__"):
            self._stream.__enter__()
        return self

    def __exit__(self, exc_type, exc, exc_tb) -> None:
        try:
            if hasattr(self._stream, "__exit__"):
                self._stream.__exit__(exc_type, exc, exc_tb)
        finally:
            self._finalize()

    def close(self) -> None:
        try:
            if hasattr(self._stream, "close"):
                self._stream.close()
        finally:
            self._finalize()

    def _finalize(self) -> None:
        if self._finalized:
            return
        self._finalized = True
        self._final_response = self._aggregator.build()
        _execute_finalize_callback_sync(
            self._finalize_callback, self._final_response, self._context_data
        )

    @property
    def final_response(self) -> ChatCompletion | None:
        if self._final_response is None:
            self._final_response = self._aggregator.build()
        return self._final_response


class _AsyncOpenAIStreamProxy:
    """Proxy for asynchronous OpenAI streaming responses."""

    def __init__(
        self,
        stream: AsyncStream,
        finalize_callback: Callable[[Any, Any], Awaitable[None] | None] | None,
        context_data: Any,
    ) -> None:
        self._stream = stream
        self._finalize_callback = finalize_callback
        self._context_data = context_data
        self._aggregator = _ChatCompletionStreamAggregator()
        self._final_response: ChatCompletion | None = None
        self._finalized = False

    def __getattr__(self, item: str) -> Any:
        return getattr(self._stream, item)

    def __aiter__(self) -> _AsyncOpenAIStreamProxy:
        return self

    async def __anext__(self) -> Any:
        try:
            chunk = await self._stream.__anext__()
        except StopAsyncIteration:
            await self._finalize()
            raise
        else:
            self._aggregator.add_chunk(chunk)
            return chunk

    async def __aenter__(self) -> _AsyncOpenAIStreamProxy:
        if hasattr(self._stream, "__aenter__"):
            await self._stream.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc, exc_tb) -> None:
        try:
            if hasattr(self._stream, "__aexit__"):
                await self._stream.__aexit__(exc_type, exc, exc_tb)
        finally:
            await self._finalize()

    async def aclose(self) -> None:
        try:
            if hasattr(self._stream, "aclose"):
                await self._stream.aclose()
        finally:
            await self._finalize()

    async def _finalize(self) -> None:
        if self._finalized:
            return
        self._finalized = True
        self._final_response = self._aggregator.build()
        await _execute_finalize_callback_async(
            self._finalize_callback, self._final_response, self._context_data
        )

    @property
    def final_response(self) -> ChatCompletion | None:
        if self._final_response is None:
            self._final_response = self._aggregator.build()
        return self._final_response


# Convenience function for creating OpenAI streaming proxies
def create_openai_streaming_proxy(
    stream: Stream | AsyncStream,
    finalize_callback: Callable[[Any, Any], Awaitable[None] | None] | None = None,
    context_data: Any = None,
) -> Stream | AsyncStream:
    """
    Create a StreamingProxy specialized for OpenAI streaming responses.
    Args:
        stream: The original OpenAI streaming response (Stream or AsyncStream).
        finalize_callback: An optional async callback to be called when the stream
            completes.
        context_data: Optional context provided to the callback.
    Returns:
        Stream or AsyncStream
    """

    if finalize_callback is None:
        return stream

    if isinstance(stream, AsyncStream):
        return _AsyncOpenAIStreamProxy(stream, finalize_callback, context_data)

    if isinstance(stream, Stream):
        return _SyncOpenAIStreamProxy(stream, finalize_callback, context_data)

    logger.warning(
        "create_openai_streaming_proxy received an unsupported stream type: %s",
        type(stream),
    )
    return stream
