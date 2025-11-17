"""
Unit tests for helper utilities in memori.utils.helpers.

Each test documents the expected behavior of key helper classes so future
refactors retain backwards compatibility.
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

import asyncio
import os
from datetime import datetime, timedelta

import pytest

from memori.utils.helpers import (
    AsyncUtils,
    DateTimeUtils,
    FileUtils,
    JsonUtils,
    RetryUtils,
    StringUtils,
)


def test_string_utils_generate_id_and_prefix():
    """StringUtils should create unique identifiers and preserve prefixes."""
    generated = StringUtils.generate_id("mem-")
    other = StringUtils.generate_id("mem-")

    assert generated.startswith("mem-")
    assert generated != other  # should be unique


def test_string_utils_truncate_and_sanitize_filename():
    """Verify truncate_text respects suffix and filenames are sanitized."""
    truncated = StringUtils.truncate_text("abcdef", max_length=4, suffix="?")
    assert truncated == "abc?"

    sanitized = StringUtils.sanitize_filename("my:/invalid*file?.txt")
    assert sanitized == "my__invalid_file_.txt"


def test_string_utils_hash_and_keyword_extraction():
    """Ensure deterministic hashing and basic keyword extraction."""
    hashed = StringUtils.hash_text("memori")
    assert hashed == StringUtils.hash_text("memori")

    keywords = StringUtils.extract_keywords(
        "The Memori memory layer connects SQL databases effortlessly", max_keywords=3
    )
    assert len(keywords) == 3
    assert all(word not in {"the", "and"} for word in keywords)


def test_datetime_utils_basic_operations():
    """DateTimeUtils helpers should format/parse and handle offsets."""
    now = DateTimeUtils.now()
    formatted = DateTimeUtils.format_datetime(now)
    parsed = DateTimeUtils.parse_datetime(formatted)

    assert isinstance(parsed, datetime)
    assert parsed.strftime("%Y-%m-%d %H:%M:%S") == formatted

    future = DateTimeUtils.add_days(now, 2)
    past = DateTimeUtils.subtract_days(now, 2)

    assert future - now == timedelta(days=2)
    assert now - past == timedelta(days=2)

    old_time = datetime.now() - timedelta(hours=5)
    assert DateTimeUtils.is_expired(old_time, expiry_hours=1)
    assert "minute" in DateTimeUtils.time_ago_string(
        datetime.now() - timedelta(minutes=3)
    )


def test_json_utils_safe_operations():
    """JsonUtils should safely merge/load/dump even with invalid inputs."""
    data = {"nested": {"value": 1}}
    merged = JsonUtils.merge_dicts(data, {"nested": {"extra": 2}, "new": True})
    assert merged["nested"]["value"] == 1
    assert merged["nested"]["extra"] == 2
    assert merged["new"] is True

    assert JsonUtils.safe_loads('{"valid": true}', default={}) == {"valid": True}
    assert JsonUtils.safe_loads("not json", default={"fallback": 1}) == {"fallback": 1}

    dumped = JsonUtils.safe_dumps({"a": 1})
    assert '"a": 1' in dumped


def test_file_utils_roundtrip(tmp_path):
    """Validate file helpers read/write/size-check and detect recency."""
    file_path = tmp_path / "memori" / "test.txt"
    FileUtils.ensure_directory(file_path.parent)

    assert FileUtils.safe_write_text(file_path, "hello")
    assert FileUtils.safe_read_text(file_path) == "hello"
    assert FileUtils.get_file_size(file_path) > 0
    assert FileUtils.is_file_recent(file_path)

    # Make file look old to ensure is_file_recent can return False
    old_timestamp = (datetime.now() - timedelta(days=3)).timestamp()
    os.utime(file_path, (old_timestamp, old_timestamp))
    assert not FileUtils.is_file_recent(file_path, hours=24)


def test_retry_utils_retries_until_success():
    """Retry decorator should retry until success within max attempts."""
    attempts = {"count": 0}

    @RetryUtils.retry_on_exception(
        max_attempts=3, delay=0, backoff=1, exceptions=(ValueError,)
    )
    def flaky():
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise ValueError("boom")
        return "ok"

    assert flaky() == "ok"
    assert attempts["count"] == 3


def test_retry_utils_raises_on_failure():
    """Retry decorator should surface final exception when retries exhausted."""

    @RetryUtils.retry_on_exception(
        max_attempts=2, delay=0, backoff=1, exceptions=(RuntimeError,)
    )
    def always_fail():
        raise RuntimeError("nope")

    with pytest.raises(RuntimeError):
        always_fail()


@pytest.mark.asyncio
async def test_async_utils_gather_with_concurrency():
    """Async gather helper should respect concurrency limits and order."""

    async def echo(value, delay=0):
        await asyncio.sleep(delay)
        return value

    tasks = [echo(i, delay=0.01) for i in range(5)]
    results = await AsyncUtils.gather_with_concurrency(2, *tasks)
    assert results == list(range(5))
