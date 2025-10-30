"""
Log Sanitization Utility

SECURITY: Prevents sensitive data (PII, credentials, tokens) from being logged.

This module provides utilities to sanitize logs before they're written, preventing
accidental leakage of sensitive information to log files, log aggregation services,
or monitoring systems.

Usage:
    from memori.utils.log_sanitizer import sanitize_for_logging

    # Sanitize before logging
    safe_message = sanitize_for_logging(user_input)
    logger.info(f"Processing: {safe_message}")
"""

import re
from typing import Any


class LogSanitizer:
    """
    Sanitize sensitive data from log messages.

    Detects and redacts:
    - Email addresses
    - Phone numbers
    - Social Security Numbers (SSN)
    - Credit card numbers
    - API keys and tokens
    - Passwords and secrets
    - IP addresses (optional)
    - URLs with credentials
    """

    # Sensitive data patterns (compiled for performance)
    PATTERNS = [
        # Email addresses
        (
            re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),
            "[EMAIL_REDACTED]",
        ),
        # SSN (US format)
        (re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "[SSN_REDACTED]"),
        # Credit card numbers (various formats)
        (re.compile(r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b"), "[CARD_REDACTED]"),
        # Phone numbers (US format)
        (re.compile(r"\b\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}\b"), "[PHONE_REDACTED]"),
        # API keys and tokens (common patterns)
        (
            re.compile(
                r'(?i)(api[_-]?key|token|secret|password|pwd|auth)["\']?\s*[:=]\s*["\']?[\w\-\.]{8,}'
            ),
            lambda m: f"{m.group(1)}=[REDACTED]",
        ),
        # Bearer tokens
        (re.compile(r"Bearer\s+[\w\-\.=]+"), "Bearer [TOKEN_REDACTED]"),
        # AWS access keys
        (re.compile(r"AKIA[0-9A-Z]{16}"), "[AWS_KEY_REDACTED]"),
        # JWT tokens (basic detection)
        (
            re.compile(r"eyJ[A-Za-z0-9_-]*\.eyJ[A-Za-z0-9_-]*\.[A-Za-z0-9_-]*"),
            "[JWT_REDACTED]",
        ),
        # URLs with credentials
        (re.compile(r"(https?://)[^:]+:[^@]+@"), r"\1[CREDENTIALS_REDACTED]@"),
        # Private IP addresses (optional - uncomment if needed)
        # (
        #     re.compile(r'\b(?:10|172\.(?:1[6-9]|2[0-9]|3[01])|192\.168)\.\d{1,3}\.\d{1,3}\b'),
        #     '[IP_REDACTED]'
        # ),
    ]

    @classmethod
    def sanitize(
        cls,
        text: Any,
        max_length: int | None = None,
        truncate_suffix: str = "...[truncated]",
    ) -> str:
        """
        Sanitize sensitive data from text.

        Args:
            text: Text to sanitize (converted to string if not already)
            max_length: Maximum length of output (None for no limit)
            truncate_suffix: Suffix to add when truncating

        Returns:
            Sanitized text safe for logging

        Example:
            >>> sanitize("My email is john@example.com and password is secret123")
            "My email is [EMAIL_REDACTED] and password is [REDACTED]"
        """
        if text is None:
            return "None"

        # Convert to string
        text_str = str(text)

        # Apply all sanitization patterns
        sanitized = text_str
        for pattern, replacement in cls.PATTERNS:
            if callable(replacement):
                sanitized = pattern.sub(replacement, sanitized)
            else:
                sanitized = pattern.sub(replacement, sanitized)

        # Truncate if needed
        if max_length and len(sanitized) > max_length:
            sanitized = sanitized[:max_length] + truncate_suffix

        return sanitized

    @classmethod
    def sanitize_dict(cls, data: dict, max_length: int | None = None) -> dict:
        """
        Sanitize all values in a dictionary.

        Args:
            data: Dictionary to sanitize
            max_length: Maximum length for each value

        Returns:
            Dictionary with sanitized values

        Example:
            >>> sanitize_dict({"email": "test@example.com", "count": 5})
            {"email": "[EMAIL_REDACTED]", "count": "5"}
        """
        return {
            key: cls.sanitize(value, max_length=max_length)
            for key, value in data.items()
        }


# Convenience functions
def sanitize_for_logging(text: Any, max_length: int | None = 100) -> str:
    """
    Sanitize text for safe logging.

    Args:
        text: Text to sanitize
        max_length: Maximum length (default: 100)

    Returns:
        Sanitized text

    Example:
        logger.info(f"User input: {sanitize_for_logging(user_input)}")
    """
    return LogSanitizer.sanitize(text, max_length=max_length)


def sanitize_dict_for_logging(data: dict, max_length: int | None = 100) -> dict:
    """
    Sanitize dictionary for safe logging.

    Args:
        data: Dictionary to sanitize
        max_length: Maximum length for each value

    Returns:
        Sanitized dictionary

    Example:
        logger.info(f"Request data: {sanitize_dict_for_logging(request_data)}")
    """
    return LogSanitizer.sanitize_dict(data, max_length=max_length)


# Logger wrapper that automatically sanitizes
class SanitizedLogger:
    """
    Logger wrapper that automatically sanitizes all log messages.

    Usage:
        from memori.utils.log_sanitizer import SanitizedLogger

        logger = SanitizedLogger()
        logger.info(f"User email: {user_email}")  # Automatically sanitized
    """

    def __init__(self, logger_instance=None, max_length: int = 200):
        """
        Initialize sanitized logger.

        Args:
            logger_instance: Loguru logger instance (uses default if None)
            max_length: Maximum length for log messages
        """
        if logger_instance is None:
            from loguru import logger as default_logger

            logger_instance = default_logger

        self.logger = logger_instance
        self.max_length = max_length

    def _sanitize_args(self, args):
        """Sanitize all arguments"""
        return tuple(LogSanitizer.sanitize(arg, self.max_length) for arg in args)

    def debug(self, message, *args, **kwargs):
        """Log debug message with sanitization"""
        sanitized_msg = LogSanitizer.sanitize(message, self.max_length)
        self.logger.debug(sanitized_msg, *self._sanitize_args(args), **kwargs)

    def info(self, message, *args, **kwargs):
        """Log info message with sanitization"""
        sanitized_msg = LogSanitizer.sanitize(message, self.max_length)
        self.logger.info(sanitized_msg, *self._sanitize_args(args), **kwargs)

    def warning(self, message, *args, **kwargs):
        """Log warning message with sanitization"""
        sanitized_msg = LogSanitizer.sanitize(message, self.max_length)
        self.logger.warning(sanitized_msg, *self._sanitize_args(args), **kwargs)

    def error(self, message, *args, **kwargs):
        """Log error message with sanitization"""
        sanitized_msg = LogSanitizer.sanitize(message, self.max_length)
        self.logger.error(sanitized_msg, *self._sanitize_args(args), **kwargs)

    def critical(self, message, *args, **kwargs):
        """Log critical message with sanitization"""
        sanitized_msg = LogSanitizer.sanitize(message, self.max_length)
        self.logger.critical(sanitized_msg, *self._sanitize_args(args), **kwargs)
