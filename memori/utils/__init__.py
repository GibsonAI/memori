"""
Utils package for Memoriai - Comprehensive utilities and helpers
"""

# Enhanced exception handling
from .exceptions import (
    AgentError,
    AuthenticationError,
    ConcurrentUpdateError,
    ConfigurationError,
    DatabaseError,
    ExceptionHandler,
    IntegrationError,
    MemoriError,
    MemoryNotFoundError,
    ProcessingError,
    RateLimitError,
    ResourceExhaustedError,
    SecurityError,
    TimeoutError,
    ValidationError,
)

# Helper utilities
from .helpers import (
    AsyncUtils,
    DateTimeUtils,
    FileUtils,
    JsonUtils,
    PerformanceUtils,
    RetryUtils,
    StringUtils,
)

# Logging utilities
from .logging import LoggingManager, get_logger

# Core Pydantic models
from .pydantic_models import (
    ConversationContext,
    EntityType,
    ExtractedEntities,
    MemoryCategory,
    MemoryCategoryType,
    MemoryImportance,
    ProcessedMemory,
    RetentionType,
)

# Validation utilities
from .validators import DataValidator, MemoryValidator

__all__ = [
    # Pydantic Models
    "ProcessedMemory",
    "MemoryCategory",
    "ExtractedEntities",
    "MemoryImportance",
    "ConversationContext",
    "MemoryCategoryType",
    "RetentionType",
    "EntityType",
    # Exceptions
    "MemoriError",
    "DatabaseError",
    "AgentError",
    "ConfigurationError",
    "ValidationError",
    "IntegrationError",
    "AuthenticationError",
    "RateLimitError",
    "MemoryNotFoundError",
    "ProcessingError",
    "TimeoutError",
    "ResourceExhaustedError",
    "SecurityError",
    "ConcurrentUpdateError",
    "ExceptionHandler",
    # Validators
    "DataValidator",
    "MemoryValidator",
    # Helpers
    "StringUtils",
    "DateTimeUtils",
    "JsonUtils",
    "FileUtils",
    "RetryUtils",
    "PerformanceUtils",
    "AsyncUtils",
    # Logging
    "LoggingManager",
    "get_logger",
]
