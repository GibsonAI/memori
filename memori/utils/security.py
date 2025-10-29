"""
Security utilities for multi-tenant isolation and validation

This module provides decorators and utilities to enforce security constraints
in multi-tenant environments, including user_id validation and audit logging.
"""

import functools
import inspect
from collections.abc import Callable
from datetime import datetime
from typing import Any

from .exceptions import SecurityError
from .logging import get_logger

logger = get_logger("security")


def require_user_id(func: Callable) -> Callable:
    """
    Decorator to enforce that user_id parameter is provided and valid.

    This decorator ensures multi-tenant isolation by requiring a valid user_id
    for all database operations. It prevents accidental cross-tenant data access.

    Args:
        func: The function to decorate

    Returns:
        Decorated function that validates user_id

    Raises:
        SecurityError: If user_id is missing, empty, or invalid

    Example:
        @require_user_id
        def get_memories(self, user_id: str, limit: int = 10):
            # user_id is guaranteed to be valid here
            pass
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Extract user_id from kwargs or positional args
        user_id = kwargs.get("user_id")

        # If not in kwargs, try to find it in positional args using function signature
        if user_id is None:
            sig = inspect.signature(func)
            param_names = list(sig.parameters.keys())

            # Find position of user_id parameter
            try:
                user_id_index = param_names.index("user_id")
                if user_id_index < len(args):
                    user_id = args[user_id_index]
            except (ValueError, IndexError):
                # user_id parameter not found in function signature
                pass

        # Validate user_id is provided
        if user_id is None:
            raise SecurityError(
                message=f"{func.__name__} requires a valid user_id parameter for multi-tenant isolation",
                security_check="require_user_id",
                operation=func.__name__,
                error_code="MISSING_USER_ID",
            )

        # Validate user_id is not empty
        if not isinstance(user_id, str) or not user_id.strip():
            raise SecurityError(
                message=f"{func.__name__} requires a non-empty user_id string",
                security_check="require_user_id",
                user_id=str(user_id),
                operation=func.__name__,
                error_code="INVALID_USER_ID",
            )

        # Warn if using 'default' user_id (should only be for dev/testing)
        if user_id.strip() == "default":
            logger.warning(
                f"[SECURITY] Function '{func.__name__}' called with user_id='default'. "
                f"This should only be used in development/testing environments."
            )

        # Log security-validated operation
        logger.debug(
            f"[SECURITY] Validated user_id for {func.__name__}: user_id='{user_id[:8]}...'"
        )

        return func(*args, **kwargs)

    return wrapper


def require_valid_session_id(func: Callable) -> Callable:
    """
    Decorator to enforce that session_id parameter is provided and valid.

    Args:
        func: The function to decorate

    Returns:
        Decorated function that validates session_id

    Raises:
        SecurityError: If session_id is missing or invalid

    Example:
        @require_valid_session_id
        def get_chat_history(self, user_id: str, session_id: str):
            pass
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        session_id = kwargs.get("session_id")

        # If not in kwargs, try positional args
        if session_id is None:
            sig = inspect.signature(func)
            param_names = list(sig.parameters.keys())

            try:
                session_id_index = param_names.index("session_id")
                if session_id_index < len(args):
                    session_id = args[session_id_index]
            except (ValueError, IndexError):
                # session_id parameter not found in function signature
                pass

        # Validate session_id
        if session_id is None:
            raise SecurityError(
                message=f"{func.__name__} requires a valid session_id parameter",
                security_check="require_valid_session_id",
                operation=func.__name__,
                error_code="MISSING_SESSION_ID",
            )

        if not isinstance(session_id, str) or not session_id.strip():
            raise SecurityError(
                message=f"{func.__name__} requires a non-empty session_id string",
                security_check="require_valid_session_id",
                operation=func.__name__,
                error_code="INVALID_SESSION_ID",
            )

        return func(*args, **kwargs)

    return wrapper


def audit_log(
    operation: str,
    user_id: str,
    resource_id: str | None = None,
    success: bool = True,
    details: dict[str, Any] | None = None,
    level: str = "info",
):
    """
    Log security-relevant operations for audit trail.

    Args:
        operation: The operation being performed (e.g., "update_memory", "delete_chat")
        user_id: The user performing the operation
        resource_id: The resource being accessed (e.g., memory_id)
        success: Whether the operation succeeded
        details: Additional context about the operation
        level: Log level ("info", "warning", "error")

    Example:
        audit_log("delete_memory", user_id="user123", resource_id="mem_456", success=True)
    """
    log_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "operation": operation,
        "user_id": user_id,
        "resource_id": resource_id,
        "success": success,
        "details": details or {},
    }

    log_message = f"[AUDIT] {operation} | user_id={user_id}"
    if resource_id:
        log_message += f" | resource={resource_id}"
    log_message += f" | success={success}"

    # Log at appropriate level
    if level == "error" or not success:
        logger.error(log_message, extra={"audit_data": log_entry})
    elif level == "warning":
        logger.warning(log_message, extra={"audit_data": log_entry})
    else:
        logger.info(log_message, extra={"audit_data": log_entry})


def sanitize_for_logging(data: dict[str, Any]) -> dict[str, Any]:
    """
    Remove sensitive fields from data before logging.

    Args:
        data: Dictionary that may contain sensitive data

    Returns:
        Sanitized dictionary safe for logging

    Example:
        sanitized = sanitize_for_logging({"user": "john", "password": "secret123"})
        # Returns: {"user": "john", "password": "***REDACTED***"}
    """
    sensitive_fields = {
        "password",
        "token",
        "api_key",
        "secret",
        "credential",
        "auth",
        "private_key",
        "access_token",
        "refresh_token",
    }

    def is_sensitive(key: str) -> bool:
        """Check if key name suggests sensitive data"""
        key_lower = key.lower()
        return any(sensitive in key_lower for sensitive in sensitive_fields)

    return {k: "***REDACTED***" if is_sensitive(k) else v for k, v in data.items()}


def validate_memory_id(memory_id: str) -> str:
    """
    Validate and sanitize memory_id to prevent injection attacks.

    Args:
        memory_id: The memory ID to validate

    Returns:
        Validated memory ID

    Raises:
        SecurityError: If memory_id is invalid

    Example:
        validated_id = validate_memory_id("mem_12345")
    """
    if not isinstance(memory_id, str):
        raise SecurityError(
            message="memory_id must be a string",
            security_check="validate_memory_id",
            error_code="INVALID_MEMORY_ID_TYPE",
        )

    if not memory_id.strip():
        raise SecurityError(
            message="memory_id cannot be empty",
            security_check="validate_memory_id",
            error_code="EMPTY_MEMORY_ID",
        )

    # Check length (reasonable limit to prevent DOS)
    if len(memory_id) > 255:
        raise SecurityError(
            message="memory_id exceeds maximum length of 255 characters",
            security_check="validate_memory_id",
            error_code="MEMORY_ID_TOO_LONG",
        )

    # Optional: Check for suspicious patterns
    # NOTE: This is warning-only (not rejection) because:
    # 1. memory_ids are typically UUIDs generated by the system
    # 2. Parameterized queries (used throughout codebase) prevent SQL injection
    # 3. Legitimate memory content may contain SQL keywords
    # This serves as an audit trail for anomaly detection
    suspicious_patterns = ["'", '"', ";", "--", "/*", "*/"]
    suspicious_keywords = ["DROP", "DELETE", "UPDATE"]

    # Check for special characters (case-sensitive patterns)
    for pattern in suspicious_patterns:
        if pattern in memory_id:
            logger.warning(
                f"[SECURITY] Suspicious pattern '{pattern}' detected in memory_id: {memory_id[:20]}... "
                f"(Warning only - parameterized queries provide protection)"
            )

    # Check for SQL keywords (case-insensitive)
    memory_id_upper = memory_id.upper()
    for keyword in suspicious_keywords:
        if keyword in memory_id_upper:
            logger.warning(
                f"[SECURITY] Suspicious SQL keyword '{keyword}' detected in memory_id: {memory_id[:20]}... "
                f"(Warning only - parameterized queries provide protection)"
            )

    return memory_id


def escape_sql_like_pattern(value: str) -> str:
    """
    Escape special characters in SQL LIKE patterns to prevent injection.

    Args:
        value: The value to escape

    Returns:
        Escaped value safe for use in LIKE patterns

    Example:
        escaped = escape_sql_like_pattern("test_value%")
        # Returns: "test\\_value\\%"
    """
    # Escape backslash first, then % and _
    escaped = value.replace("\\", "\\\\")
    escaped = escaped.replace("%", "\\%")
    escaped = escaped.replace("_", "\\_")
    return escaped


# Export public API
__all__ = [
    "require_user_id",
    "require_valid_session_id",
    "audit_log",
    "sanitize_for_logging",
    "validate_memory_id",
    "escape_sql_like_pattern",
]
