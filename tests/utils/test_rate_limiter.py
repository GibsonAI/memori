"""
Unit tests for memori.utils.rate_limiter covering window/quota helpers.
"""

import sys
import types

if "memori.config.pool_config" not in sys.modules:
    pool_module = types.ModuleType("memori.config.pool_config")

    class PoolConfig:
        DEFAULT_POOL_SIZE = 2
        DEFAULT_MAX_OVERFLOW = 3
        DEFAULT_POOL_TIMEOUT = 30
        DEFAULT_POOL_RECYCLE = 3600
        DEFAULT_POOL_PRE_PING = True

    pool_module.PoolConfig = PoolConfig
    pool_module.pool_config = PoolConfig()
    sys.modules["memori.config.pool_config"] = pool_module

import pytest

from memori.utils import rate_limiter as rl
from memori.utils.rate_limiter import QuotaExceeded, RateLimiter, RateLimitExceeded


def test_rate_limiter_enforces_limit_and_resets(monkeypatch):
    """Rate limiter should enforce limits per window and reset after expiry."""
    fake_time = {"value": 0.0}

    def _fake_time():
        return fake_time["value"]

    monkeypatch.setattr(rl.time, "time", _fake_time)

    limiter = RateLimiter()
    allowed, _ = limiter.check_rate_limit("user", "op", limit=1, window_seconds=10)
    assert allowed

    allowed, error = limiter.check_rate_limit("user", "op", limit=1, window_seconds=10)
    assert not allowed
    assert "Rate limit exceeded" in error

    fake_time["value"] = 65
    allowed, _ = limiter.check_rate_limit("user", "op", limit=1, window_seconds=10)
    assert allowed  # window reset


def test_rate_limiter_storage_and_memory_quotas():
    """Storage and memory quotas should enforce limits and track increments."""
    limiter = RateLimiter()

    ok, _ = limiter.check_storage_quota("user", additional_bytes=50, limit_bytes=100)
    assert ok
    limiter.increment_quota("user", "storage_bytes", amount=50)

    allowed, message = limiter.check_storage_quota(
        "user", additional_bytes=60, limit_bytes=80
    )
    assert not allowed
    assert "Storage quota exceeded" in message

    limiter.increment_quota("user", "memory_count", amount=5)
    allowed, message = limiter.check_memory_count_quota("user", limit=5)
    assert not allowed
    assert "Memory count quota exceeded" in message


def test_rate_limiter_api_calls_reset(monkeypatch):
    """Daily API quota should reset when the last reset timestamp is stale."""
    limiter = RateLimiter()

    quota = limiter._quotas["user"]
    quota.api_calls_today = 1_000
    quota.last_reset = quota.last_reset - rl.timedelta(days=2)

    allowed, _ = limiter.check_api_call_quota("user", limit=1_000)
    assert allowed
    assert quota.api_calls_today == 0


def test_rate_limit_decorator_raises(monkeypatch):
    """rate_limited decorator should raise when exceeding allowed invocations."""
    local_limiter = RateLimiter()
    monkeypatch.setattr(rl, "_global_limiter", local_limiter)

    class Dummy:
        user_id = "user"

        @rl.rate_limited("op", limit=1, window_seconds=60)
        def action(self):
            return "done"

    instance = Dummy()
    assert instance.action() == "done"

    with pytest.raises(RateLimitExceeded):
        instance.action()


def test_storage_quota_decorator(monkeypatch):
    """storage_quota decorator should raise QuotaExceeded when payload is heavy."""
    local_limiter = RateLimiter()
    monkeypatch.setattr(rl, "_global_limiter", local_limiter)

    class Dummy:
        user_id = "user"

        @rl.storage_quota(limit_bytes=10)
        def save(self, user_input="", ai_output=""):
            return len(user_input) + len(ai_output)

    d = Dummy()
    with pytest.raises(QuotaExceeded):
        d.save(user_input="a" * 20, ai_output="b")
