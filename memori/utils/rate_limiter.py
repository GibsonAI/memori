"""
Rate Limiting and Resource Quota Management

SECURITY: Prevents resource exhaustion and DoS attacks by limiting per-tenant
resource usage.

This module provides:
- Rate limiting (requests per time window)
- Storage quotas (bytes per tenant)
- Memory count limits (memories per tenant)
- API call limits (OpenAI calls per day)

Usage:
    from memori.utils.rate_limiter import RateLimiter, check_rate_limit

    # Check if user can make another request
    if not check_rate_limit(user_id, "search", limit=60):
        raise MemoriError("Rate limit exceeded")

    # Use as decorator
    @rate_limited("record_conversation", limit=100)
    def record_conversation(self, ...):
        ...
"""

import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from functools import wraps

from .logging import get_logger

logger = get_logger("rate_limiter")


class RateLimitExceeded(Exception):
    """Raised when rate limit is exceeded"""

    pass


class QuotaExceeded(Exception):
    """Raised when resource quota is exceeded"""

    pass


@dataclass
class RateLimitWindow:
    """Track rate limit for a single window"""

    count: int = 0
    reset_time: float = field(default_factory=lambda: time.time() + 60)

    def is_expired(self) -> bool:
        """Check if window has expired"""
        return time.time() > self.reset_time

    def increment(self) -> int:
        """Increment count and return new value"""
        self.count += 1
        return self.count

    def reset(self, window_seconds: int = 60):
        """Reset the window"""
        self.count = 0
        self.reset_time = time.time() + window_seconds


@dataclass
class ResourceQuota:
    """Track resource quotas for a tenant"""

    memory_count: int = 0
    storage_bytes: int = 0
    api_calls_today: int = 0
    last_reset: datetime = field(default_factory=datetime.now)

    def should_reset_daily(self) -> bool:
        """Check if daily counters should reset"""
        return datetime.now() - self.last_reset > timedelta(days=1)

    def reset_daily(self):
        """Reset daily counters"""
        self.api_calls_today = 0
        self.last_reset = datetime.now()


class RateLimiter:
    """
    Thread-safe rate limiter with resource quota management.

    Supports:
    - Per-operation rate limits (e.g., 100 searches/minute)
    - Per-tenant storage quotas (e.g., 100MB per user)
    - Per-tenant memory count limits (e.g., 10,000 memories per user)
    - Per-tenant API call limits (e.g., 1,000 OpenAI calls per day)
    """

    def __init__(self):
        self._rate_limits: dict[str, RateLimitWindow] = defaultdict(RateLimitWindow)
        self._quotas: dict[str, ResourceQuota] = defaultdict(ResourceQuota)
        self._lock = threading.Lock()

    def check_rate_limit(
        self, user_id: str, operation: str, limit: int = 100, window_seconds: int = 60
    ) -> tuple[bool, str | None]:
        """
        Check if user is within rate limit for operation.

        Args:
            user_id: User identifier
            operation: Operation name (e.g., "search", "record")
            limit: Maximum requests per window
            window_seconds: Window size in seconds

        Returns:
            Tuple of (allowed, error_message)

        Example:
            allowed, error = limiter.check_rate_limit("user123", "search", limit=60)
            if not allowed:
                raise RateLimitExceeded(error)
        """
        with self._lock:
            key = f"{user_id}:{operation}"
            window = self._rate_limits[key]

            # Reset if window expired
            if window.is_expired():
                window.reset(window_seconds)

            # Check limit
            if window.count >= limit:
                wait_time = int(window.reset_time - time.time())
                error_msg = (
                    f"Rate limit exceeded for {operation}. "
                    f"Limit: {limit} requests per {window_seconds}s. "
                    f"Try again in {wait_time}s."
                )
                logger.warning(f"Rate limit exceeded: {user_id}/{operation}")
                return False, error_msg

            # Increment counter
            window.increment()
            return True, None

    def check_storage_quota(
        self,
        user_id: str,
        additional_bytes: int,
        limit_bytes: int = 100_000_000,  # 100MB default
    ) -> tuple[bool, str | None]:
        """
        Check if user is within storage quota.

        Args:
            user_id: User identifier
            additional_bytes: Bytes to be added
            limit_bytes: Maximum storage per user

        Returns:
            Tuple of (allowed, error_message)
        """
        with self._lock:
            quota = self._quotas[user_id]

            if (quota.storage_bytes + additional_bytes) > limit_bytes:
                error_msg = (
                    f"Storage quota exceeded. "
                    f"Current: {quota.storage_bytes / 1_000_000:.1f}MB, "
                    f"Limit: {limit_bytes / 1_000_000:.1f}MB. "
                    f"Contact support to increase your quota."
                )
                logger.warning(f"Storage quota exceeded: {user_id}")
                return False, error_msg

            return True, None

    def check_memory_count_quota(
        self, user_id: str, limit: int = 10_000
    ) -> tuple[bool, str | None]:
        """
        Check if user is within memory count quota.

        Args:
            user_id: User identifier
            limit: Maximum memories per user

        Returns:
            Tuple of (allowed, error_message)
        """
        with self._lock:
            quota = self._quotas[user_id]

            if quota.memory_count >= limit:
                error_msg = (
                    f"Memory count quota exceeded. "
                    f"Limit: {limit} memories per user. "
                    f"Consider archiving or deleting old memories."
                )
                logger.warning(f"Memory count quota exceeded: {user_id}")
                return False, error_msg

            return True, None

    def check_api_call_quota(
        self, user_id: str, limit: int = 1_000
    ) -> tuple[bool, str | None]:
        """
        Check if user is within daily API call quota.

        Args:
            user_id: User identifier
            limit: Maximum API calls per day

        Returns:
            Tuple of (allowed, error_message)
        """
        with self._lock:
            quota = self._quotas[user_id]

            # Reset daily counters if needed
            if quota.should_reset_daily():
                quota.reset_daily()

            if quota.api_calls_today >= limit:
                error_msg = (
                    f"Daily API call quota exceeded. "
                    f"Limit: {limit} calls per day. "
                    f"Resets at midnight UTC."
                )
                logger.warning(f"API call quota exceeded: {user_id}")
                return False, error_msg

            return True, None

    def increment_quota(self, user_id: str, quota_type: str, amount: int = 1):
        """
        Increment quota usage.

        Args:
            user_id: User identifier
            quota_type: Type of quota ("memory_count", "storage_bytes", "api_calls_today")
            amount: Amount to increment
        """
        with self._lock:
            quota = self._quotas[user_id]

            if quota_type == "memory_count":
                quota.memory_count += amount
            elif quota_type == "storage_bytes":
                quota.storage_bytes += amount
            elif quota_type == "api_calls_today":
                if quota.should_reset_daily():
                    quota.reset_daily()
                quota.api_calls_today += amount
            else:
                logger.warning(f"Unknown quota type: {quota_type}")

    def get_quota_stats(self, user_id: str) -> dict:
        """
        Get current quota statistics for a user.

        Args:
            user_id: User identifier

        Returns:
            Dictionary with quota statistics
        """
        with self._lock:
            quota = self._quotas[user_id]

            if quota.should_reset_daily():
                quota.reset_daily()

            return {
                "memory_count": quota.memory_count,
                "storage_bytes": quota.storage_bytes,
                "storage_mb": quota.storage_bytes / 1_000_000,
                "api_calls_today": quota.api_calls_today,
                "last_reset": quota.last_reset.isoformat(),
            }


# Global rate limiter instance
_global_limiter = RateLimiter()


def get_rate_limiter() -> RateLimiter:
    """Get the global rate limiter instance"""
    return _global_limiter


def check_rate_limit(
    user_id: str, operation: str, limit: int = 100, window_seconds: int = 60
) -> bool:
    """
    Convenience function to check rate limit.

    Args:
        user_id: User identifier
        operation: Operation name
        limit: Maximum requests per window
        window_seconds: Window size in seconds

    Returns:
        True if allowed, False if rate limited

    Raises:
        RateLimitExceeded: If rate limit is exceeded
    """
    allowed, error = _global_limiter.check_rate_limit(
        user_id, operation, limit, window_seconds
    )
    if not allowed:
        raise RateLimitExceeded(error)
    return True


# Decorators for easy integration
def rate_limited(operation: str, limit: int = 100, window_seconds: int = 60):
    """
    Decorator to rate limit a method.

    Args:
        operation: Operation name
        limit: Maximum requests per window
        window_seconds: Window size in seconds

    Example:
        @rate_limited("search", limit=60)
        def search(self, query: str):
            ...
    """

    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            # Get user_id from self
            user_id = getattr(self, "user_id", "default")

            # Check rate limit
            allowed, error = _global_limiter.check_rate_limit(
                user_id, operation, limit, window_seconds
            )
            if not allowed:
                raise RateLimitExceeded(error)

            return func(self, *args, **kwargs)

        return wrapper

    return decorator


def storage_quota(limit_bytes: int = 100_000_000):
    """
    Decorator to check storage quota.

    Args:
        limit_bytes: Maximum storage per user

    Example:
        @storage_quota(limit_bytes=100_000_000)  # 100MB
        def record_conversation(self, user_input: str, ai_output: str):
            ...
    """

    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            # Get user_id from self
            user_id = getattr(self, "user_id", "default")

            # Estimate storage size
            user_input = kwargs.get("user_input", "")
            ai_output = kwargs.get("ai_output", "")
            estimated_bytes = len(str(user_input).encode("utf-8")) + len(
                str(ai_output).encode("utf-8")
            )

            # Check quota
            allowed, error = _global_limiter.check_storage_quota(
                user_id, estimated_bytes, limit_bytes
            )
            if not allowed:
                raise QuotaExceeded(error)

            # Execute function
            result = func(self, *args, **kwargs)

            # Increment quota after successful operation
            _global_limiter.increment_quota(user_id, "storage_bytes", estimated_bytes)

            return result

        return wrapper

    return decorator


def memory_count_quota(limit: int = 10_000):
    """
    Decorator to check memory count quota.

    Args:
        limit: Maximum memories per user

    Example:
        @memory_count_quota(limit=10_000)
        def record_conversation(self, ...):
            ...
    """

    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            # Get user_id from self
            user_id = getattr(self, "user_id", "default")

            # Check quota
            allowed, error = _global_limiter.check_memory_count_quota(user_id, limit)
            if not allowed:
                raise QuotaExceeded(error)

            # Execute function
            result = func(self, *args, **kwargs)

            # Increment quota after successful operation
            _global_limiter.increment_quota(user_id, "memory_count", 1)

            return result

        return wrapper

    return decorator
