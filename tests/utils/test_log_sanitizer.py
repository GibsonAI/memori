"""
Unit tests for memori.utils.log_sanitizer.

This suite documents expected redaction behavior so sensitive data never leaks
through logging regressions.
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

from memori.utils.log_sanitizer import (
    LogSanitizer,
    SanitizedLogger,
    sanitize_dict_for_logging,
    sanitize_for_logging,
)


def test_log_sanitizer_replaces_sensitive_tokens():
    """Sensitive tokens (emails, cards, api keys) should be redacted."""
    raw = (
        "Contact me at user@example.com, token=abcd1234secret, "
        "and card 1234-5678-9012-3456"
    )
    sanitized = sanitize_for_logging(raw, max_length=200)

    assert "[EMAIL_REDACTED]" in sanitized
    assert "[CARD_REDACTED]" in sanitized
    assert "token=[REDACTED]" in sanitized
    assert "user@example.com" not in sanitized


def test_sanitize_dict_handles_multiple_values():
    """Dictionary sanitizer should sanitize string values and stringify others."""
    payload = {"email": "someone@example.com", "count": 5}
    sanitized = sanitize_dict_for_logging(payload, max_length=50)

    assert sanitized["email"] == "[EMAIL_REDACTED]"
    assert sanitized["count"] == "5"


def test_log_sanitizer_truncates_long_text():
    """Sanitizer should truncate when max_length is provided."""
    text = "a" * 50
    sanitized = LogSanitizer.sanitize(text, max_length=10, truncate_suffix="...")
    assert sanitized.startswith("a" * 10)
    assert sanitized.endswith("...")


def test_sanitized_logger_sanitizes_messages():
    """SanitizedLogger should emit redacted output before logging."""
    records = []

    class DummyLogger:
        def info(self, message, *args, **kwargs):
            records.append(message)

    logger = SanitizedLogger(logger_instance=DummyLogger(), max_length=200)
    logger.info("My email is admin@example.com and password is secret")

    assert len(records) == 1
    assert "[EMAIL_REDACTED]" in records[0]
    assert "password" in records[0]
