import pytest
import asyncio

from memori.utils.helpers import RetryUtils


def test_retry_on_exception_reraises_last_exception():
    calls = {"count": 0}

    @RetryUtils.retry_on_exception(max_attempts=3, delay=0.0, backoff=1.0)
    def always_fails():
        calls["count"] += 1
        raise ValueError("boom")

    with pytest.raises(ValueError) as excinfo:
        always_fails()

    assert "boom" in str(excinfo.value)
    assert calls["count"] == 3


@pytest.mark.asyncio
async def test_async_retry_on_exception_reraises_last_exception():
    calls = {"count": 0}

    @awaitable := RetryUtils.async_retry_on_exception(max_attempts=2, delay=0.0, backoff=1.0)
    async def always_fails_async():
        calls["count"] += 1
        raise RuntimeError("async boom")

    # The decorator factory returns a decorator, so we need to apply it
    decorated = awaitable(always_fails_async)

    with pytest.raises(RuntimeError) as excinfo:
        await decorated()

    assert "async boom" in str(excinfo.value)
    assert calls["count"] == 2
