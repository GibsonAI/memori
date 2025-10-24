"""
Generic streaming proxy utilities for intercepting and processing streaming responses.

This module provides reusable classes for wrapping streaming responses,
capturing chunks, and processing them when the stream completes.
"""

import asyncio
import inspect
from typing import Any, Awaitable, Callable, List, Optional, TypeVar, Generic
from types import SimpleNamespace

from loguru import logger

T = TypeVar('T')  # Type of stream chunks
R = TypeVar('R')  # Type of final response


class StreamingProxy(Generic[T, R]):
    """
    Generic proxy for streaming responses that captures chunks and processes them when complete.
    
    This class wraps any async iterable stream, collects all chunks, and allows
    custom processing when the stream finishes.
    
    Args:
        stream: The original async iterable stream
        chunk_processor: Optional callback to process each chunk as it arrives
        finalize_processor: Callback to process all chunks when stream completes
        response_builder: Optional callback to build final response from chunks
    """
    
    __slots__ = (
        "_stream",
        "_chunks",
        "_chunk_processor", 
        "_finalize_processor",
        "_response_builder",
        "_finalization_task",
        "_finalized",
        "_iterator",
        "_context_data"
    )
    
    def __init__(
        self, 
        stream: Any,
        chunk_processor: Optional[Callable[[T], None]] = None,
        finalize_processor: Optional[Callable[[List[T], Any], Awaitable[None]]] = None,
        response_builder: Optional[Callable[[List[T]], Awaitable[Optional[R]]]] = None,
        context_data: Any = None
    ):
        self._stream = stream
        self._chunks: List[T] = []
        self._chunk_processor = chunk_processor
        self._finalize_processor = finalize_processor
        self._response_builder = response_builder
        self._finalization_task: Optional[asyncio.Task] = None
        self._finalized = False
        self._iterator: Optional['StreamingIterator'] = None
        self._context_data = context_data
    
    def __getattr__(self, item: str) -> Any:
        """Delegate attribute access to the original stream."""
        return getattr(self._stream, item)
    
    def __aiter__(self) -> 'StreamingIterator[T]':
        """Return async iterator for the stream."""
        if self._iterator is None:
            self._iterator = StreamingIterator(self)
        return self._iterator
    
    async def __aenter__(self) -> 'StreamingProxy[T, R]':
        """Async context manager entry."""
        if hasattr(self._stream, "__aenter__"):
            try:
                await self._stream.__aenter__()
            except AttributeError:
                # Stream doesn't actually support context manager
                pass
        return self
    
    async def __aexit__(self, exc_type, exc, tb) -> None:
        """Async context manager exit - triggers finalization."""
        try:
            if hasattr(self._stream, "__aexit__"):
                try:
                    await self._stream.__aexit__(exc_type, exc, tb)
                except AttributeError:
                    # Stream doesn't actually support context manager
                    pass
        finally:
            self._schedule_finalize()
    
    def record_chunk(self, chunk: T) -> None:
        """Record a chunk and optionally process it."""
        self._chunks.append(chunk)
        if self._chunk_processor:
            try:
                self._chunk_processor(chunk)
            except Exception as e:
                logger.error(f"Chunk processor failed: {e}")
    
    def _schedule_finalize(self) -> None:
        """Schedule finalization task if not already scheduled."""
        if self._finalized or self._finalization_task is not None:
            return
        
        async def _finalize_wrapper():
            try:
                await self._finalize()
            except Exception as exc:
                logger.error(f"Streaming finalize failed: {exc}")
        
        try:
            loop = asyncio.get_running_loop()
            if loop.is_running():
                self._finalization_task = loop.create_task(_finalize_wrapper())
            else:
                self._finalization_task = asyncio.ensure_future(_finalize_wrapper())
        except RuntimeError:
            # No event loop running
            self._finalization_task = asyncio.ensure_future(_finalize_wrapper())
    
    async def _ensure_finalized(self) -> None:
        """Ensure finalization has completed."""
        if self._finalized:
            return
        
        if self._finalization_task is None:
            self._schedule_finalize()
        
        if self._finalization_task is not None:
            await self._finalization_task
    
    async def _finalize(self) -> None:
        """Execute finalization logic."""
        if self._finalized:
            return
        
        try:
            # Call finalize processor if provided
            if self._finalize_processor:
                await self._finalize_processor(self._chunks, self._context_data)
        except Exception as exc:
            logger.error(f"Finalize processor failed: {exc}")
        finally:
            self._finalized = True
    
    async def get_final_response(self) -> Optional[R]:
        """Get the final response built from all chunks."""
        await self._ensure_finalized()
        
        if self._response_builder:
            try:
                return await self._response_builder(self._chunks)
            except Exception as e:
                logger.error(f"Response builder failed: {e}")
                return None
        
        return None
    
    @property
    def chunks(self) -> List[T]:
        """Get all recorded chunks."""
        return self._chunks.copy()
    
    @property
    def is_finalized(self) -> bool:
        """Check if finalization has completed."""
        return self._finalized


class StreamingIterator(Generic[T]):
    """
    Async iterator that records chunks and triggers finalize when complete.
    """
    
    __slots__ = ("_proxy", "_aiter")
    
    def __init__(self, proxy: StreamingProxy[T, Any]):
        self._proxy = proxy
        self._aiter = proxy._stream.__aiter__()
    
    def __aiter__(self) -> 'StreamingIterator[T]':
        return self
    
    async def __anext__(self) -> T:
        try:
            chunk = await self._aiter.__anext__()
        except StopAsyncIteration:
            self._proxy._schedule_finalize()
            raise
        
        self._proxy.record_chunk(chunk)
        return chunk
    
    async def aclose(self) -> None:
        """Close the iterator and trigger finalization."""
        if hasattr(self._aiter, "aclose"):
            await self._aiter.aclose()
        self._proxy._schedule_finalize()


class OpenAIStreamingResponseBuilder:
    """
    Utility class for building OpenAI-style responses from streaming chunks.
    
    This handles the complex logic of reconstructing a complete chat completion
    response from individual streaming deltas.
    """
    
    @staticmethod
    def _safe_get(obj: Any, attr: str, default: Any = None) -> Any:
        """Safely get attribute from object or dict."""
        if hasattr(obj, attr):
            return getattr(obj, attr)
        if isinstance(obj, dict):
            return obj.get(attr, default)
        return default
    
    @classmethod
    async def build_chat_completion(cls, chunks: List[Any]) -> Optional[SimpleNamespace]:
        """
        Build a complete chat completion response from streaming chunks.
        
        Args:
            chunks: List of streaming response chunks
            
        Returns:
            Complete chat completion response or None if no chunks
        """
        if not chunks:
            return None
        
        # Try to use provider-native reconstruction if available
        # This assumes the first chunk's stream has these methods
        if chunks and hasattr(chunks[0], '_stream'):
            stream = chunks[0]._stream
            if hasattr(stream, "get_final_response"):
                try:
                    final_response = await stream.get_final_response()
                    if final_response is not None:
                        return final_response
                except Exception as e:
                    logger.debug(f"Provider-native reconstruction failed: {e}")
            
            if hasattr(stream, "completion") and stream.completion is not None:
                return stream.completion
        
        # Manual reconstruction from chunks
        return cls._build_from_chunks(chunks)
    
    @classmethod
    def _build_from_chunks(cls, chunks: List[Any]) -> Optional[SimpleNamespace]:
        """Manually build response from chunks."""
        choices_map = {}
        model = None
        response_id = None
        created = None
        usage = None
        system_fingerprint = None
        service_tier = None
        
        for chunk in chunks:
            model = model or cls._safe_get(chunk, "model")
            response_id = response_id or cls._safe_get(chunk, "id")
            created = created or cls._safe_get(chunk, "created")
            chunk_usage = cls._safe_get(chunk, "usage")
            usage = chunk_usage or usage
            system_fingerprint = cls._safe_get(chunk, "system_fingerprint") or system_fingerprint
            service_tier = cls._safe_get(chunk, "service_tier") or service_tier
            
            for choice in cls._safe_get(chunk, "choices", []) or []:
                idx = cls._safe_get(choice, "index", 0)
                choice_entry = choices_map.setdefault(idx, {
                    "content_parts": [],
                    "reasoning_parts": [],
                    "role": None,
                    "finish_reason": None,
                    "logprobs": None,
                    "function_call": {"name": "", "arguments": ""},
                    "tool_calls": {},
                })
                
                delta = cls._safe_get(choice, "delta")
                if delta:
                    cls._process_content_delta(delta, choice_entry)
                    cls._process_function_delta(delta, choice_entry)
                    cls._process_tool_calls_delta(delta, choice_entry)
                    
                    role = cls._safe_get(delta, "role")
                    if role:
                        choice_entry["role"] = role
                
                finish_reason = cls._safe_get(choice, "finish_reason")
                if finish_reason:
                    choice_entry["finish_reason"] = finish_reason
                
                logprobs = cls._safe_get(choice, "logprobs")
                if logprobs is not None:
                    choice_entry["logprobs"] = logprobs
        
        assembled_choices = cls._assemble_choices(choices_map)
        if not assembled_choices:
            return None
        
        return SimpleNamespace(
            id=response_id,
            model=model,
            created=created,
            choices=assembled_choices,
            usage=usage,
            system_fingerprint=system_fingerprint,
            service_tier=service_tier,
            object="chat.completion",
        )
    
    @classmethod
    def _process_content_delta(cls, delta: Any, choice_entry: dict) -> None:
        """Process content and reasoning content from delta."""
        content_piece = cls._safe_get(delta, "content")
        if content_piece:
            if isinstance(content_piece, list):
                normalized = "".join(
                    part.get("text", "") if isinstance(part, dict) else str(part)
                    for part in content_piece
                )
            else:
                normalized = str(content_piece)
            if normalized:
                choice_entry["content_parts"].append(normalized)
        
        reasoning_piece = cls._safe_get(delta, "reasoning_content")
        if reasoning_piece:
            if isinstance(reasoning_piece, list):
                normalized_reasoning = "".join(
                    part.get("text", "") if isinstance(part, dict) else str(part)
                    for part in reasoning_piece
                )
            else:
                normalized_reasoning = str(reasoning_piece)
            if normalized_reasoning:
                choice_entry["reasoning_parts"].append(normalized_reasoning)
    
    @classmethod
    def _process_function_delta(cls, delta: Any, choice_entry: dict) -> None:
        """Process function call delta."""
        function_delta = cls._safe_get(delta, "function_call")
        if function_delta:
            if cls._safe_get(function_delta, "name"):
                choice_entry["function_call"]["name"] = cls._safe_get(function_delta, "name")
            if cls._safe_get(function_delta, "arguments"):
                choice_entry["function_call"]["arguments"] += cls._safe_get(function_delta, "arguments") or ""
    
    @classmethod
    def _process_tool_calls_delta(cls, delta: Any, choice_entry: dict) -> None:
        """Process tool calls delta."""
        tool_call_deltas = cls._safe_get(delta, "tool_calls")
        if tool_call_deltas:
            for tool_delta in tool_call_deltas:
                tool_idx = cls._safe_get(tool_delta, "index", 0)
                tool_entry = choice_entry["tool_calls"].setdefault(tool_idx, {
                    "id": "",
                    "type": cls._safe_get(tool_delta, "type"),
                    "function": {"name": "", "arguments": ""},
                })
                
                tool_id = cls._safe_get(tool_delta, "id")
                if tool_id:
                    tool_entry["id"] = tool_id
                
                tool_type = cls._safe_get(tool_delta, "type")
                if tool_type:
                    tool_entry["type"] = tool_type
                
                tool_function = cls._safe_get(tool_delta, "function")
                if tool_function:
                    fn_name = cls._safe_get(tool_function, "name")
                    if fn_name:
                        tool_entry["function"]["name"] = fn_name
                    fn_args = cls._safe_get(tool_function, "arguments")
                    if fn_args:
                        tool_entry["function"]["arguments"] += fn_args or ""
    
    @classmethod
    def _assemble_choices(cls, choices_map: dict) -> List[SimpleNamespace]:
        """Assemble final choices from processed deltas."""
        assembled_choices = []
        for idx, entry in sorted(choices_map.items()):
            content = "".join(entry["content_parts"])
            reasoning = "".join(entry["reasoning_parts"])
            if reasoning:
                content = reasoning + content
            
            tool_calls_list = []
            for tool_idx, tool_data in sorted(entry["tool_calls"].items()):
                tool_call = SimpleNamespace(
                    id=tool_data["id"] or None,
                    type=tool_data["type"] or "function",
                    function=SimpleNamespace(
                        name=tool_data["function"]["name"] or "",
                        arguments=tool_data["function"]["arguments"] or "",
                    ),
                )
                tool_calls_list.append(tool_call)
            
            message = SimpleNamespace(
                role=entry["role"] or "assistant",
                content=content or None,
                tool_calls=tool_calls_list or None,
            )
            
            function_call = entry["function_call"]
            if function_call["name"] or function_call["arguments"]:
                message.function_call = SimpleNamespace(
                    name=function_call["name"],
                    arguments=function_call["arguments"],
                )
            
            assembled_choice = SimpleNamespace(
                index=idx,
                message=message,
                finish_reason=entry["finish_reason"],
                logprobs=entry["logprobs"],
            )
            assembled_choices.append(assembled_choice)
        
        return assembled_choices


# Convenience function for creating OpenAI streaming proxies
def create_openai_streaming_proxy(
    stream: Any, 
    finalize_callback: Callable[[Any, Any], Awaitable[None]],
    context_data: Any = None
) -> StreamingProxy:
    """
    Create a streaming proxy specifically for OpenAI responses.
    
    Args:
        stream: Original OpenAI stream
        finalize_callback: Callback to execute when stream completes
        context_data: Additional context data to pass to callback
        
    Returns:
        Configured StreamingProxy for OpenAI streams
    """
    return StreamingProxy(
        stream=stream,
        finalize_processor=finalize_callback,
        response_builder=OpenAIStreamingResponseBuilder.build_chat_completion,
        context_data=context_data
    )