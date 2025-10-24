import asyncio
from types import SimpleNamespace

import pytest
from openai._streaming import AsyncStream, Stream
from openai.types.completion_usage import CompletionUsage

from memori.utils.streaming_proxy import create_openai_streaming_proxy


class DummyStream(Stream):
    """Minimal synchronous OpenAI stream stub for testing."""

    def __init__(self, chunks):
        self._chunks = iter(chunks)
        self.response = SimpleNamespace(close=lambda: None)

    def __iter__(self):
        return self

    def __next__(self):
        return next(self._chunks)

    def close(self):
        self.response.close()


class DummyAsyncStream(AsyncStream):
    """Minimal asynchronous OpenAI stream stub for testing."""

    def __init__(self, chunks):
        self._chunks = iter(chunks)
        self.response = SimpleNamespace(aclose=lambda: None)

    def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            return next(self._chunks)
        except StopIteration as exc:  # pragma: no cover - mirrors real behaviour
            raise StopAsyncIteration from exc

    async def aclose(self):
        await asyncio.sleep(0)


def _make_chunk(
    *,
    content: str | None = None,
    finish_reason: str | None = None,
    role: str | None = None,
    usage: CompletionUsage | None = None,
):
    delta_attrs = {}
    if content is not None:
        delta_attrs["content"] = content
    if role is not None:
        delta_attrs["role"] = role

    choice = SimpleNamespace(
        index=0,
        delta=SimpleNamespace(**delta_attrs) if delta_attrs else None,
        finish_reason=finish_reason,
        logprobs=None,
    )

    return SimpleNamespace(
        id="chatcmpl-test",
        created=123,
        model="gpt-4o",
        choices=[choice],
        service_tier="scale" if finish_reason else None,
        system_fingerprint="fingerprint-xyz",
        usage=usage,
    )


def test_sync_streaming_proxy_aggregates_chunks_and_invokes_finalize():
    usage = CompletionUsage(prompt_tokens=5, completion_tokens=7, total_tokens=12)
    chunks = [
        _make_chunk(content="Hello", role="assistant"),
        _make_chunk(content=" world", finish_reason="stop", usage=usage),
    ]

    captured = {}

    async def finalize_callback(final_response, context):
        captured["response"] = final_response
        captured["context"] = context

    proxy = create_openai_streaming_proxy(
        DummyStream(chunks),
        finalize_callback=finalize_callback,
        context_data={"req": 1},
    )

    emitted_chunks = list(proxy)

    assert emitted_chunks == chunks
    assert captured["context"] == {"req": 1}
    final = captured["response"]
    assert final is not None
    assert final.model == "gpt-4o"
    assert final.choices[0].message.content == "Hello world"
    assert final.choices[0].finish_reason == "stop"
    assert final.usage and final.usage.total_tokens == 12


@pytest.mark.asyncio
async def test_async_streaming_proxy_invokes_async_finalize_callback():
    usage = CompletionUsage(prompt_tokens=3, completion_tokens=4, total_tokens=7)
    chunks = [
        _make_chunk(content="Streaming", role="assistant"),
        _make_chunk(content=" done", finish_reason="stop", usage=usage),
    ]

    captured = {}

    async def finalize_callback(final_response, context):
        captured["response"] = final_response
        captured["context"] = context

    proxy = create_openai_streaming_proxy(
        DummyAsyncStream(chunks),
        finalize_callback=finalize_callback,
        context_data=("ctx",),
    )

    emitted_chunks = []
    async for chunk in proxy:
        emitted_chunks.append(chunk)

    assert emitted_chunks == chunks
    assert captured["context"] == ("ctx",)
    final = captured["response"]
    assert final is not None
    assert final.choices[0].message.content == "Streaming done"
    assert final.choices[0].finish_reason == "stop"
    assert final.usage and final.usage.total_tokens == 7
