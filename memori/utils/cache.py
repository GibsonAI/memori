"""
Simple in-memory caching utilities for performance optimization.
Provides TTL-based caching without complex async dependencies.
"""

import atexit
import hashlib
import sys
import threading
import time
from collections import OrderedDict
from typing import Any

from loguru import logger


class TTLCache:
    """
    Simple Time-To-Live cache with LRU eviction.
    Thread-safe with RLock protection for concurrent access.
    """

    def __init__(
        self,
        max_size: int = 1000,
        ttl_seconds: int = 300,
        max_value_size_mb: float | None = None,
    ):
        """
        Initialize TTL cache.

        Args:
            max_size: Maximum number of cached items
            ttl_seconds: Time-to-live for cached items in seconds
            max_value_size_mb: Maximum size for a single cached value in MB.
                               None = no size limit (default). Use cautiously.

        Raises:
            ValueError: If parameters are invalid
        """
        # Validate parameters
        if not isinstance(max_size, int) or max_size <= 0:
            raise ValueError(f"max_size must be a positive integer, got {max_size}")
        if not isinstance(ttl_seconds, int | float) or ttl_seconds <= 0:
            raise ValueError(
                f"ttl_seconds must be a positive number, got {ttl_seconds}"
            )
        if max_value_size_mb is not None and (
            not isinstance(max_value_size_mb, int | float) or max_value_size_mb <= 0
        ):
            raise ValueError(
                f"max_value_size_mb must be None or a positive number, got {max_value_size_mb}"
            )

        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.max_value_size_bytes = (
            int(max_value_size_mb * 1024 * 1024) if max_value_size_mb else None
        )
        self._cache: OrderedDict[str, tuple[Any, float]] = OrderedDict()
        self._hits = 0
        self._misses = 0
        self._lock = threading.RLock()  # Thread-safe operations
        self._cleanup_interval = 60  # Cleanup every 60 seconds
        self._shutdown_event = threading.Event()  # Interruptible shutdown signal

        # Start background cleanup thread
        self._cleanup_thread = threading.Thread(
            target=self._periodic_cleanup, daemon=True, name="cache-cleanup"
        )
        self._cleanup_thread.start()

        # Register shutdown hook
        atexit.register(self.shutdown)

    def get(self, key: str) -> Any | None:
        """
        Get item from cache if exists and not expired.
        Thread-safe operation.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found/expired
        """
        with self._lock:
            if key in self._cache:
                value, timestamp = self._cache[key]
                # Check if expired
                if time.time() - timestamp < self.ttl_seconds:
                    # Move to end (LRU)
                    self._cache.move_to_end(key)
                    self._hits += 1
                    return value
                else:
                    # Expired, remove
                    del self._cache[key]
                    self._misses += 1
                    return None

            self._misses += 1
            return None

    def set(self, key: str, value: Any) -> None:
        """
        Set item in cache with current timestamp.
        Thread-safe operation.

        Args:
            key: Cache key
            value: Value to cache

        Raises:
            ValueError: If value is invalid or too large
        """
        # Validate value before acquiring lock
        if value is None:
            raise ValueError("Cannot cache None values (ambiguous with cache miss)")

        # Check value size if limit is set
        if self.max_value_size_bytes is not None:
            value_size = sys.getsizeof(value)
            if value_size > self.max_value_size_bytes:
                raise ValueError(
                    f"Value size ({value_size / 1024 / 1024:.2f}MB) exceeds max_value_size_mb "
                    f"({self.max_value_size_bytes / 1024 / 1024:.2f}MB)"
                )

        with self._lock:
            # If at capacity and key is new, make space
            if len(self._cache) >= self.max_size and key not in self._cache:
                # First try to evict expired items
                current_time = time.time()
                expired_keys = [
                    k
                    for k, (_, timestamp) in self._cache.items()
                    if current_time - timestamp >= self.ttl_seconds
                ]

                if expired_keys:
                    # Remove expired items first
                    for k in expired_keys:
                        del self._cache[k]
                    logger.debug(
                        f"Evicted {len(expired_keys)} expired items during cache set"
                    )
                else:
                    # No expired items, evict oldest (LRU)
                    self._cache.popitem(last=False)

            # Store with timestamp
            self._cache[key] = (value, time.time())
            # Move to end (most recently used)
            self._cache.move_to_end(key)

    def clear(self) -> None:
        """Clear all cached items. Thread-safe."""
        with self._lock:
            self._cache.clear()
            self._hits = 0
            self._misses = 0

    def get_stats(self) -> dict[str, Any]:
        """
        Get cache statistics.
        Thread-safe operation.

        Returns:
            Dictionary with cache stats
        """
        with self._lock:
            total = self._hits + self._misses
            hit_rate = (self._hits / total * 100) if total > 0 else 0

            return {
                "size": len(self._cache),
                "max_size": self.max_size,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": f"{hit_rate:.1f}%",
                "ttl_seconds": self.ttl_seconds,
            }

    def cleanup_expired(self) -> int:
        """
        Remove expired entries from cache.
        Thread-safe operation.

        Returns:
            Number of expired entries removed
        """
        with self._lock:
            current_time = time.time()
            expired_keys = [
                key
                for key, (_, timestamp) in self._cache.items()
                if current_time - timestamp >= self.ttl_seconds
            ]

            for key in expired_keys:
                del self._cache[key]

            if expired_keys:
                logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")

            return len(expired_keys)

    def _periodic_cleanup(self) -> None:
        """Background thread that periodically cleans up expired entries."""
        while not self._shutdown_event.is_set():
            # Use Event.wait() instead of time.sleep() for interruptible waiting
            if self._shutdown_event.wait(timeout=self._cleanup_interval):
                # Event was set (shutdown requested), exit immediately
                break

            try:
                self.cleanup_expired()
            except Exception as e:
                logger.error(f"Cache cleanup error: {e}")

    def shutdown(self) -> None:
        """Shutdown background cleanup thread gracefully."""
        self._shutdown_event.set()  # Signal shutdown
        if hasattr(self, "_cleanup_thread") and self._cleanup_thread.is_alive():
            self._cleanup_thread.join(timeout=2.0)
            if self._cleanup_thread.is_alive():
                logger.warning("Cache cleanup thread did not stop within timeout")
            else:
                logger.debug("Cache cleanup thread stopped gracefully")


class ContextCache:
    """
    Specialized cache for conversation context.
    Creates cache keys from user messages and namespace.
    """

    def __init__(self, max_size: int = 100, ttl_seconds: int = 300):
        """
        Initialize context cache.

        Args:
            max_size: Maximum cached contexts
            ttl_seconds: TTL for cached contexts (default 5 minutes)
        """
        # Limit context cache values to 5MB (smaller than search cache)
        self._cache = TTLCache(
            max_size=max_size, ttl_seconds=ttl_seconds, max_value_size_mb=5.0
        )
        logger.info(
            f"ContextCache initialized: max_size={max_size}, ttl={ttl_seconds}s"
        )

    def get_context(self, namespace: str, user_input: str, mode: str) -> list | None:
        """
        Get cached context for user input.

        Args:
            namespace: Memory namespace
            user_input: User message content
            mode: Injection mode ('conscious' or 'auto')

        Returns:
            Cached context list or None
        """
        cache_key = self._make_key(namespace, user_input, mode)
        context = self._cache.get(cache_key)

        if context is not None:
            logger.debug(
                f"Context cache HIT for query: '{user_input[:30]}...' (mode={mode})"
            )

        return context

    def set_context(
        self, namespace: str, user_input: str, mode: str, context: list
    ) -> None:
        """
        Cache context for user input.

        Args:
            namespace: Memory namespace
            user_input: User message content
            mode: Injection mode ('conscious' or 'auto')
            context: Context list to cache
        """
        cache_key = self._make_key(namespace, user_input, mode)
        self._cache.set(cache_key, context)
        logger.debug(
            f"Context cached for query: '{user_input[:30]}...' (mode={mode}, items={len(context)})"
        )

    def _make_key(self, namespace: str, user_input: str, mode: str) -> str:
        """
        Create cache key from namespace, user input, and mode.

        Args:
            namespace: Memory namespace
            user_input: User message
            mode: Injection mode

        Returns:
            Hash-based cache key
        """
        # Use first 200 chars of user input to create key
        # This balances specificity with cache hit rate
        input_prefix = user_input[:200] if user_input else ""
        key_string = f"{namespace}:{mode}:{input_prefix}"
        return hashlib.md5(key_string.encode()).hexdigest()

    def clear(self) -> None:
        """Clear all cached contexts."""
        self._cache.clear()
        logger.info("Context cache cleared")

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        return self._cache.get_stats()

    def cleanup_expired(self) -> int:
        """Remove expired entries."""
        return self._cache.cleanup_expired()
