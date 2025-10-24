"""
Tests for the generic streaming proxy utilities.

This module tests the StreamingProxy, StreamingIterator, and OpenAIStreamingResponseBuilder
classes to ensure they properly handle streaming responses, error cases, and finalization.
"""

import os
import sys

# Fix imports to work from any directory
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import asyncio
import pytest  # noqa: E402
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from memori.utils.streaming_proxy import (
    StreamingProxy,
    StreamingIterator, 
    OpenAIStreamingResponseBuilder,
    create_openai_streaming_proxy
)


class MockStream:
    """Mock streaming object for testing."""
    
    def __init__(self, chunks, raise_error_at=None, has_context_manager=False):
        self.chunks = chunks
        self.index = 0
        self.raise_error_at = raise_error_at
        self.has_context_manager = has_context_manager
        self._entered = False
        self._exited = False
    
    def __aiter__(self):
        return self
    
    async def __anext__(self):
        if self.raise_error_at is not None and self.index == self.raise_error_at:
            raise Exception("Mock stream error")
        
        if self.index >= len(self.chunks):
            raise StopAsyncIteration
        
        chunk = self.chunks[self.index]
        self.index += 1
        await asyncio.sleep(0.01)  # Simulate async delay
        return chunk
    
    async def __aenter__(self):
        if not self.has_context_manager:
            raise AttributeError("__aenter__")
        self._entered = True
        return self
    
    async def __aexit__(self, exc_type, exc, tb):
        if not self.has_context_manager:
            raise AttributeError("__aexit__")
        self._exited = True


class TestStreamingProxy:
    """Test cases for StreamingProxy class."""
    
    @pytest.mark.asyncio
    async def test_basic_streaming(self):
        """Test basic streaming functionality."""
        chunks = ["chunk1", "chunk2", "chunk3"]
        stream = MockStream(chunks)
        
        proxy = StreamingProxy(stream)
        
        collected_chunks = []
        async for chunk in proxy:
            collected_chunks.append(chunk)
        
        assert collected_chunks == chunks
        assert proxy.chunks == chunks
        
        # Wait for finalization
        await asyncio.sleep(0.1)
        assert proxy.is_finalized
    
    @pytest.mark.asyncio
    async def test_chunk_processor(self):
        """Test chunk processing callback."""
        chunks = ["a", "b", "c"]
        stream = MockStream(chunks)
        
        processed_chunks = []
        def chunk_processor(chunk):
            processed_chunks.append(f"processed_{chunk}")
        
        proxy = StreamingProxy(stream, chunk_processor=chunk_processor)
        
        async for chunk in proxy:
            pass
        
        expected_processed = ["processed_a", "processed_b", "processed_c"]
        assert processed_chunks == expected_processed
    
    @pytest.mark.asyncio
    async def test_finalize_processor(self):
        """Test finalization processor callback."""
        chunks = [1, 2, 3]
        stream = MockStream(chunks)
        
        finalize_called = False
        finalize_chunks = None
        finalize_context = None
        
        async def finalize_processor(chunks_list, context):
            nonlocal finalize_called, finalize_chunks, finalize_context
            finalize_called = True
            finalize_chunks = chunks_list
            finalize_context = context
        
        context_data = {"test": "data"}
        proxy = StreamingProxy(
            stream, 
            finalize_processor=finalize_processor,
            context_data=context_data
        )
        
        async for chunk in proxy:
            pass
        
        # Wait for finalization
        await asyncio.sleep(0.1)
        
        assert finalize_called
        assert finalize_chunks == chunks
        assert finalize_context == context_data
    
    @pytest.mark.asyncio
    async def test_response_builder(self):
        """Test response builder callback."""
        chunks = ["hello", " ", "world"]
        stream = MockStream(chunks)
        
        async def response_builder(chunks_list):
            return "".join(chunks_list).upper()
        
        proxy = StreamingProxy(stream, response_builder=response_builder)
        
        async for chunk in proxy:
            pass
        
        final_response = await proxy.get_final_response()
        assert final_response == "HELLO WORLD"
    
    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test async context manager functionality."""
        chunks = ["test"]
        stream = MockStream(chunks, has_context_manager=True)
        
        async with StreamingProxy(stream) as proxy:
            async for chunk in proxy:
                assert chunk == "test"
        
        assert stream._entered
        assert stream._exited
        
        # Wait for finalization
        await asyncio.sleep(0.1)
        assert proxy.is_finalized
    
    @pytest.mark.asyncio
    async def test_context_manager_without_stream_support(self):
        """Test context manager when stream doesn't support it."""
        chunks = ["test"]
        stream = MockStream(chunks, has_context_manager=False)
        
        async with StreamingProxy(stream) as proxy:
            async for chunk in proxy:
                assert chunk == "test"
        
        # Should still work even if stream doesn't support context manager
        await asyncio.sleep(0.1)
        assert proxy.is_finalized
    
    @pytest.mark.asyncio
    async def test_attribute_delegation(self):
        """Test that attributes are delegated to the original stream."""
        stream = MockStream([])
        stream.custom_attribute = "test_value"
        
        proxy = StreamingProxy(stream)
        
        assert proxy.custom_attribute == "test_value"
    
    @pytest.mark.asyncio
    async def test_error_in_chunk_processor(self):
        """Test error handling in chunk processor."""
        chunks = ["chunk1", "chunk2"]
        stream = MockStream(chunks)
        
        def failing_processor(chunk):
            if chunk == "chunk2":
                raise Exception("Processor error")
        
        proxy = StreamingProxy(stream, chunk_processor=failing_processor)
        
        # Should still collect all chunks despite processor error
        collected = []
        async for chunk in proxy:
            collected.append(chunk)
        
        assert collected == chunks
        assert proxy.chunks == chunks
    
    @pytest.mark.asyncio
    async def test_error_in_finalize_processor(self):
        """Test error handling in finalize processor."""
        chunks = ["test"]
        stream = MockStream(chunks)
        
        async def failing_finalizer(chunks_list, context):
            raise Exception("Finalizer error")
        
        proxy = StreamingProxy(stream, finalize_processor=failing_finalizer)
        
        async for chunk in proxy:
            pass
        
        # Wait for finalization
        await asyncio.sleep(0.1)
        
        # Should still be marked as finalized despite error
        assert proxy.is_finalized
    
    @pytest.mark.asyncio
    async def test_error_in_response_builder(self):
        """Test error handling in response builder."""
        chunks = ["test"]
        stream = MockStream(chunks)
        
        async def failing_builder(chunks_list):
            raise Exception("Builder error")
        
        proxy = StreamingProxy(stream, response_builder=failing_builder)
        
        async for chunk in proxy:
            pass
        
        final_response = await proxy.get_final_response()
        assert final_response is None  # Should return None on builder error
    
    @pytest.mark.asyncio
    async def test_multiple_iterations(self):
        """Test that multiple iterations work correctly."""
        chunks = ["a", "b"]
        stream = MockStream(chunks)
        proxy = StreamingProxy(stream)
        
        # First iteration
        first_collection = []
        async for chunk in proxy:
            first_collection.append(chunk)
        
        # Should reuse the same iterator
        assert proxy._iterator is not None
        
        # Second call to __aiter__ should return the same iterator
        assert proxy.__aiter__() is proxy._iterator


class TestStreamingIterator:
    """Test cases for StreamingIterator class."""
    
    @pytest.mark.asyncio
    async def test_iterator_protocol(self):
        """Test async iterator protocol."""
        chunks = ["x", "y", "z"]
        stream = MockStream(chunks)
        proxy = StreamingProxy(stream)
        
        iterator = StreamingIterator(proxy)
        
        # Test __aiter__ returns self
        assert iterator.__aiter__() is iterator
        
        # Test __anext__
        result1 = await iterator.__anext__()
        assert result1 == "x"
        
        result2 = await iterator.__anext__()
        assert result2 == "y"
        
        result3 = await iterator.__anext__()
        assert result3 == "z"
        
        # Should raise StopAsyncIteration
        with pytest.raises(StopAsyncIteration):
            await iterator.__anext__()
    
    @pytest.mark.asyncio
    async def test_aclose(self):
        """Test aclose functionality."""
        stream = MockStream(["test"])
        stream.aclose = AsyncMock()  # Add aclose method
        
        proxy = StreamingProxy(stream)
        iterator = StreamingIterator(proxy)
        
        await iterator.aclose()
        
        # Should call stream's aclose if available
        stream.aclose.assert_called_once()
        
        # Wait for finalization
        await asyncio.sleep(0.1)
        assert proxy.is_finalized


class TestOpenAIStreamingResponseBuilder:
    """Test cases for OpenAIStreamingResponseBuilder class."""
    
    def test_safe_get_with_object(self):
        """Test _safe_get with object attributes."""
        obj = SimpleNamespace(attr1="value1", attr2=None)
        
        assert OpenAIStreamingResponseBuilder._safe_get(obj, "attr1") == "value1"
        assert OpenAIStreamingResponseBuilder._safe_get(obj, "attr2") is None
        assert OpenAIStreamingResponseBuilder._safe_get(obj, "nonexistent", "default") == "default"
    
    def test_safe_get_with_dict(self):
        """Test _safe_get with dictionary."""
        data = {"key1": "value1", "key2": None}
        
        assert OpenAIStreamingResponseBuilder._safe_get(data, "key1") == "value1"
        assert OpenAIStreamingResponseBuilder._safe_get(data, "key2") is None
        assert OpenAIStreamingResponseBuilder._safe_get(data, "nonexistent", "default") == "default"
    
    @pytest.mark.asyncio
    async def test_build_chat_completion_empty_chunks(self):
        """Test building response from empty chunks."""
        result = await OpenAIStreamingResponseBuilder.build_chat_completion([])
        assert result is None
    
    @pytest.mark.asyncio
    async def test_build_chat_completion_simple(self):
        """Test building response from simple chunks."""
        chunks = [
            SimpleNamespace(
                id="chatcmpl-123",
                model="gpt-4",
                created=1234567890,
                choices=[SimpleNamespace(
                    index=0,
                    delta=SimpleNamespace(role="assistant", content="Hello"),
                    finish_reason=None
                )]
            ),
            SimpleNamespace(
                id="chatcmpl-123",
                choices=[SimpleNamespace(
                    index=0,
                    delta=SimpleNamespace(content=" world!"),
                    finish_reason="stop"
                )],
                usage=SimpleNamespace(total_tokens=10)
            )
        ]
        
        result = await OpenAIStreamingResponseBuilder.build_chat_completion(chunks)
        
        assert result is not None
        assert result.id == "chatcmpl-123"
        assert result.model == "gpt-4"
        assert result.created == 1234567890
        assert result.object == "chat.completion"
        assert len(result.choices) == 1
        
        choice = result.choices[0]
        assert choice.index == 0
        assert choice.message.role == "assistant"
        assert choice.message.content == "Hello world!"
        assert choice.finish_reason == "stop"
        assert result.usage.total_tokens == 10
    
    @pytest.mark.asyncio
    async def test_build_chat_completion_with_function_call(self):
        """Test building response with function calls."""
        chunks = [
            SimpleNamespace(
                id="chatcmpl-456",
                choices=[SimpleNamespace(
                    index=0,
                    delta=SimpleNamespace(
                        role="assistant",
                        function_call=SimpleNamespace(name="get_weather", arguments='{"loc')
                    ),
                    finish_reason=None
                )]
            ),
            SimpleNamespace(
                choices=[SimpleNamespace(
                    index=0,
                    delta=SimpleNamespace(
                        function_call=SimpleNamespace(arguments='ation": "NYC"}')
                    ),
                    finish_reason="function_call"
                )]
            )
        ]
        
        result = await OpenAIStreamingResponseBuilder.build_chat_completion(chunks)
        
        assert result is not None
        choice = result.choices[0]
        assert hasattr(choice.message, 'function_call')
        assert choice.message.function_call.name == "get_weather"
        assert choice.message.function_call.arguments == '{"location": "NYC"}'
        assert choice.finish_reason == "function_call"
    
    @pytest.mark.asyncio
    async def test_build_chat_completion_with_tool_calls(self):
        """Test building response with tool calls."""
        chunks = [
            SimpleNamespace(
                id="chatcmpl-789",
                choices=[SimpleNamespace(
                    index=0,
                    delta=SimpleNamespace(
                        role="assistant",
                        tool_calls=[SimpleNamespace(
                            index=0,
                            id="call_123",
                            type="function",
                            function=SimpleNamespace(name="calculate", arguments='{"x":')
                        )]
                    ),
                    finish_reason=None
                )]
            ),
            SimpleNamespace(
                choices=[SimpleNamespace(
                    index=0,
                    delta=SimpleNamespace(
                        tool_calls=[SimpleNamespace(
                            index=0,
                            function=SimpleNamespace(arguments=' 5, "y": 3}')
                        )]
                    ),
                    finish_reason="tool_calls"
                )]
            )
        ]
        
        result = await OpenAIStreamingResponseBuilder.build_chat_completion(chunks)
        
        assert result is not None
        choice = result.choices[0]
        assert choice.message.tool_calls is not None
        assert len(choice.message.tool_calls) == 1
        
        tool_call = choice.message.tool_calls[0]
        assert tool_call.id == "call_123"
        assert tool_call.type == "function"
        assert tool_call.function.name == "calculate"
        assert tool_call.function.arguments == '{"x": 5, "y": 3}'
    
    @pytest.mark.asyncio
    async def test_build_chat_completion_with_reasoning(self):
        """Test building response with reasoning content."""
        chunks = [
            SimpleNamespace(
                choices=[SimpleNamespace(
                    index=0,
                    delta=SimpleNamespace(
                        role="assistant",
                        reasoning_content="Let me think..."
                    ),
                    finish_reason=None
                )]
            ),
            SimpleNamespace(
                choices=[SimpleNamespace(
                    index=0,
                    delta=SimpleNamespace(content="The answer is 42"),
                    finish_reason="stop"
                )]
            )
        ]
        
        result = await OpenAIStreamingResponseBuilder.build_chat_completion(chunks)
        
        assert result is not None
        choice = result.choices[0]
        # Reasoning should be prepended to content
        assert choice.message.content == "Let me think...The answer is 42"


class TestCreateOpenAIStreamingProxy:
    """Test cases for create_openai_streaming_proxy function."""
    
    @pytest.mark.asyncio
    async def test_create_proxy(self):
        """Test creating OpenAI streaming proxy."""
        chunks = ["test"]
        stream = MockStream(chunks)
        
        callback_called = False
        callback_chunks = None
        callback_context = None
        
        async def finalize_callback(chunks_list, context_data):
            nonlocal callback_called, callback_chunks, callback_context
            callback_called = True
            callback_chunks = chunks_list
            callback_context = context_data
        
        context_data = {"model": "gpt-4"}
        
        proxy = create_openai_streaming_proxy(
            stream=stream,
            finalize_callback=finalize_callback,
            context_data=context_data
        )
        
        # Consume the stream
        async for chunk in proxy:
            pass
        
        # Wait for finalization
        await asyncio.sleep(0.1)
        
        assert callback_called
        assert callback_chunks == chunks
        assert callback_context == context_data
        
        # Should have response builder configured
        assert proxy._response_builder is not None


@pytest.mark.asyncio
async def test_integration_scenario():
    """Integration test simulating real-world usage."""
    # Simulate OpenAI-like streaming response
    openai_chunks = [
        SimpleNamespace(
            id="chatcmpl-integration",
            model="gpt-4",
            created=1234567890,
            choices=[SimpleNamespace(
                index=0,
                delta=SimpleNamespace(role="assistant", content="Integration"),
                finish_reason=None
            )]
        ),
        SimpleNamespace(
            choices=[SimpleNamespace(
                index=0,
                delta=SimpleNamespace(content=" test"),
                finish_reason=None
            )]
        ),
        SimpleNamespace(
            choices=[SimpleNamespace(
                index=0,
                delta=SimpleNamespace(content=" successful!"),
                finish_reason="stop"
            )],
            usage=SimpleNamespace(total_tokens=15)
        )
    ]
    
    stream = MockStream(openai_chunks)
    
    # Track processing
    processed_chunks = []
    finalization_data = {}
    
    def chunk_processor(chunk):
        processed_chunks.append(chunk)
    
    async def finalize_processor(chunks, context):
        finalization_data['chunks'] = chunks
        finalization_data['context'] = context
        finalization_data['completed'] = True
    
    # Create proxy with all callbacks
    proxy = StreamingProxy(
        stream=stream,
        chunk_processor=chunk_processor,
        finalize_processor=finalize_processor,
        response_builder=OpenAIStreamingResponseBuilder.build_chat_completion,
        context_data={"session_id": "test_session"}
    )
    
    # Consume stream
    received_chunks = []
    async for chunk in proxy:
        received_chunks.append(chunk)
    
    # Verify immediate results
    assert received_chunks == openai_chunks
    assert processed_chunks == openai_chunks
    assert proxy.chunks == openai_chunks
    
    # Wait for async finalization
    await asyncio.sleep(0.1)
    
    # Verify finalization
    assert proxy.is_finalized
    assert finalization_data.get('completed')
    assert finalization_data['chunks'] == openai_chunks
    assert finalization_data['context']['session_id'] == "test_session"
    
    # Verify response building
    final_response = await proxy.get_final_response()
    assert final_response is not None
    assert final_response.id == "chatcmpl-integration"
    assert final_response.model == "gpt-4"
    assert final_response.choices[0].message.content == "Integration test successful!"
    assert final_response.usage.total_tokens == 15


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])