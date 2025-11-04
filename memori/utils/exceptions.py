"""
Custom exceptions for Memoriai with comprehensive error handling
"""

import traceback
from datetime import datetime
from typing import Any


class MemoriError(Exception):
    """Base exception for Memoriai with enhanced error context"""

    def __init__(
        self,
        message: str,
        error_code: str | None = None,
        context: dict[str, Any] | None = None,
        cause: Exception | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or self.__class__.__name__.upper()
        self.context = context or {}
        self.cause = cause
        self.timestamp = datetime.now()
        self.traceback = traceback.format_exc() if cause else None

    def to_dict(self) -> dict[str, Any]:
        """Convert exception to dictionary for logging/serialization"""
        return {
            "error_type": self.__class__.__name__,
            "error_code": self.error_code,
            "message": self.message,
            "context": self.context,
            "timestamp": self.timestamp.isoformat(),
            "cause": str(self.cause) if self.cause else None,
            "traceback": self.traceback,
        }

    def __str__(self) -> str:
        base_msg = f"[{self.error_code}] {self.message}"
        if self.context:
            base_msg += f" | Context: {self.context}"
        if self.cause:
            base_msg += f" | Caused by: {self.cause}"
        return base_msg


class DatabaseError(MemoriError):
    """Database-related errors with connection and query context"""

    def __init__(
        self,
        message: str,
        query: str | None = None,
        connection_string: str | None = None,
        error_code: str | None = None,
        cause: Exception | None = None,
    ):
        context = {}
        if query:
            context["query"] = query
        if connection_string:
            # Sanitize connection string (remove credentials)
            sanitized = self._sanitize_connection_string(connection_string)
            context["connection"] = sanitized

        super().__init__(
            message=message,
            error_code=error_code or "DB_ERROR",
            context=context,
            cause=cause,
        )

    @staticmethod
    def _sanitize_connection_string(conn_str: str) -> str:
        """Remove credentials from connection string for safe logging"""
        import re

        # Remove password from connection strings
        sanitized = re.sub(r"://[^:]+:[^@]+@", "://***:***@", conn_str)
        return sanitized


class AgentError(MemoriError):
    """Memory agent-related errors with API and processing context"""

    def __init__(
        self,
        message: str,
        agent_type: str | None = None,
        model: str | None = None,
        api_endpoint: str | None = None,
        tokens_used: int | None = None,
        error_code: str | None = None,
        cause: Exception | None = None,
    ):
        context = {}
        if agent_type:
            context["agent_type"] = agent_type
        if model:
            context["model"] = model
        if api_endpoint:
            context["api_endpoint"] = api_endpoint
        if tokens_used:
            context["tokens_used"] = tokens_used

        super().__init__(
            message=message,
            error_code=error_code or "AGENT_ERROR",
            context=context,
            cause=cause,
        )


class ConfigurationError(MemoriError):
    """Configuration-related errors with setting context"""

    def __init__(
        self,
        message: str,
        setting_path: str | None = None,
        config_file: str | None = None,
        error_code: str | None = None,
        cause: Exception | None = None,
    ):
        context = {}
        if setting_path:
            context["setting_path"] = setting_path
        if config_file:
            context["config_file"] = config_file

        super().__init__(
            message=message,
            error_code=error_code or "CONFIG_ERROR",
            context=context,
            cause=cause,
        )


class ValidationError(MemoriError):
    """Data validation errors with field context"""

    def __init__(
        self,
        message: str,
        field_name: str | None = None,
        field_value: Any | None = None,
        expected_type: str | None = None,
        error_code: str | None = None,
        cause: Exception | None = None,
    ):
        context = {}
        if field_name:
            context["field_name"] = field_name
        if field_value is not None:
            context["field_value"] = str(field_value)
        if expected_type:
            context["expected_type"] = expected_type

        super().__init__(
            message=message,
            error_code=error_code or "VALIDATION_ERROR",
            context=context,
            cause=cause,
        )


class IntegrationError(MemoriError):
    """Integration-related errors with provider context"""

    def __init__(
        self,
        message: str,
        provider: str | None = None,
        integration_type: str | None = None,
        error_code: str | None = None,
        cause: Exception | None = None,
    ):
        context = {}
        if provider:
            context["provider"] = provider
        if integration_type:
            context["integration_type"] = integration_type

        super().__init__(
            message=message,
            error_code=error_code or "INTEGRATION_ERROR",
            context=context,
            cause=cause,
        )


class AuthenticationError(MemoriError):
    """Authentication and authorization errors"""

    def __init__(
        self,
        message: str,
        auth_type: str | None = None,
        endpoint: str | None = None,
        error_code: str | None = None,
        cause: Exception | None = None,
    ):
        context = {}
        if auth_type:
            context["auth_type"] = auth_type
        if endpoint:
            context["endpoint"] = endpoint

        super().__init__(
            message=message,
            error_code=error_code or "AUTH_ERROR",
            context=context,
            cause=cause,
        )


class RateLimitError(MemoriError):
    """Rate limiting errors with quota context"""

    def __init__(
        self,
        message: str,
        provider: str | None = None,
        limit_type: str | None = None,
        retry_after: int | None = None,
        error_code: str | None = None,
        cause: Exception | None = None,
    ):
        context = {}
        if provider:
            context["provider"] = provider
        if limit_type:
            context["limit_type"] = limit_type
        if retry_after:
            context["retry_after"] = retry_after

        super().__init__(
            message=message,
            error_code=error_code or "RATE_LIMIT_ERROR",
            context=context,
            cause=cause,
        )


class MemoryNotFoundError(MemoriError):
    """Memory not found errors with search context"""

    def __init__(
        self,
        message: str,
        memory_id: str | None = None,
        user_id: str | None = None,
        search_criteria: dict[str, Any] | None = None,
        error_code: str | None = None,
        cause: Exception | None = None,
    ):
        context = {}
        if memory_id:
            context["memory_id"] = memory_id
        if user_id:
            context["user_id"] = user_id
        if search_criteria:
            context["search_criteria"] = search_criteria

        super().__init__(
            message=message,
            error_code=error_code or "MEMORY_NOT_FOUND",
            context=context,
            cause=cause,
        )


class ProcessingError(MemoriError):
    """Memory processing errors with processing context"""

    def __init__(
        self,
        message: str,
        processing_stage: str | None = None,
        input_data: dict[str, Any] | None = None,
        error_code: str | None = None,
        cause: Exception | None = None,
    ):
        context = {}
        if processing_stage:
            context["processing_stage"] = processing_stage
        if input_data:
            # Sanitize potentially sensitive data
            sanitized_data = {
                k: (v if k not in ["api_key", "password", "secret"] else "***")
                for k, v in input_data.items()
            }
            context["input_data"] = sanitized_data

        super().__init__(
            message=message,
            error_code=error_code or "PROCESSING_ERROR",
            context=context,
            cause=cause,
        )


class TimeoutError(MemoriError):
    """Timeout errors with operation context"""

    def __init__(
        self,
        message: str,
        operation: str | None = None,
        timeout_seconds: float | None = None,
        error_code: str | None = None,
        cause: Exception | None = None,
    ):
        context = {}
        if operation:
            context["operation"] = operation
        if timeout_seconds:
            context["timeout_seconds"] = timeout_seconds

        super().__init__(
            message=message,
            error_code=error_code or "TIMEOUT_ERROR",
            context=context,
            cause=cause,
        )


class ResourceExhaustedError(MemoriError):
    """Resource exhaustion errors with resource context"""

    def __init__(
        self,
        message: str,
        resource_type: str | None = None,
        current_usage: int | float | None = None,
        limit: int | float | None = None,
        error_code: str | None = None,
        cause: Exception | None = None,
    ):
        context = {}
        if resource_type:
            context["resource_type"] = resource_type
        if current_usage is not None:
            context["current_usage"] = current_usage
        if limit is not None:
            context["limit"] = limit

        super().__init__(
            message=message,
            error_code=error_code or "RESOURCE_EXHAUSTED",
            context=context,
            cause=cause,
        )


class SecurityError(MemoriError):
    """Security-related errors with security context"""

    def __init__(
        self,
        message: str,
        security_check: str | None = None,
        user_id: str | None = None,
        operation: str | None = None,
        error_code: str | None = None,
        cause: Exception | None = None,
    ):
        context = {}
        if security_check:
            context["security_check"] = security_check
        if user_id:
            context["user_id"] = user_id
        if operation:
            context["operation"] = operation

        super().__init__(
            message=message,
            error_code=error_code or "SECURITY_ERROR",
            context=context,
            cause=cause,
        )


class ConcurrentUpdateError(MemoriError):
    """Concurrent update/modification errors with version context

    TODO: Currently unused - reserved for future optimistic locking implementation.
    Will be raised when concurrent updates are detected using version column.
    """

    def __init__(
        self,
        message: str,
        resource_id: str | None = None,
        expected_version: int | None = None,
        actual_version: int | None = None,
        user_id: str | None = None,
        error_code: str | None = None,
        cause: Exception | None = None,
    ):
        context = {}
        if resource_id:
            context["resource_id"] = resource_id
        if expected_version is not None:
            context["expected_version"] = expected_version
        if actual_version is not None:
            context["actual_version"] = actual_version
        if user_id:
            context["user_id"] = user_id

        super().__init__(
            message=message,
            error_code=error_code or "CONCURRENT_UPDATE",
            context=context,
            cause=cause,
        )


# Exception utilities
class ExceptionHandler:
    """Centralized exception handling utilities"""

    @staticmethod
    def handle_database_exception(
        e: Exception, query: str | None = None
    ) -> DatabaseError:
        """Convert generic exception to DatabaseError with context"""
        if isinstance(e, DatabaseError):
            return e

        return DatabaseError(
            message=f"Database operation failed: {str(e)}",
            query=query,
            cause=e,
        )

    @staticmethod
    def handle_agent_exception(
        e: Exception, agent_type: str | None = None
    ) -> AgentError:
        """Convert generic exception to AgentError with context"""
        if isinstance(e, AgentError):
            return e

        return AgentError(
            message=f"Agent operation failed: {str(e)}",
            agent_type=agent_type,
            cause=e,
        )

    @staticmethod
    def handle_validation_exception(
        e: Exception, field_name: str | None = None
    ) -> ValidationError:
        """Convert generic exception to ValidationError with context"""
        if isinstance(e, ValidationError):
            return e

        return ValidationError(
            message=f"Validation failed: {str(e)}",
            field_name=field_name,
            cause=e,
        )

    @staticmethod
    def log_exception(exception: MemoriError, logger=None) -> None:
        """Log exception with full context"""
        if logger is None:
            from .logging import get_logger

            logger = get_logger("exceptions")

        logger.error(
            f"Exception occurred: {exception.error_code}",
            extra={
                "exception_data": exception.to_dict(),
                "error_type": exception.__class__.__name__,
            },
        )
