"""
Memoriai - The Open-Source Memory Layer for AI Agents & Multi-Agent Systems v1.0

Professional-grade memory layer with comprehensive error handling, configuration
management, and modular architecture for production AI systems.
"""

__version__ = "2.3.0"
__author__ = "Harshal More"
__email__ = "harshalmore2468@gmail.com"

from typing import Any, Optional

# Configuration system
from .config import (
    AgentSettings,
    ConfigManager,
    DatabaseSettings,
    LoggingSettings,
    MemoriSettings,
)
from .core.database import DatabaseManager

# Core components
from .core.memory import Memori

# Database system
from .database.connectors import MySQLConnector, PostgreSQLConnector, SQLiteConnector
from .database.queries import (  # EntityQueries removed (graph search simplified)
    BaseQueries,
    ChatQueries,
    MemoryQueries,
)

# Wrapper integrations
from .integrations import MemoriAnthropic, MemoriOpenAI

# Tools and integrations
from .tools.memory_tool import MemoryTool, create_memory_search_tool, create_memory_tool

# Utils and models
from .utils import (  # Pydantic models; Enhanced exceptions; Validators and helpers; Logging
    AgentError,
    AsyncUtils,
    AuthenticationError,
    ConcurrentUpdateError,
    ConfigurationError,
    ConversationContext,
    DatabaseError,
    DataValidator,
    DateTimeUtils,
    EntityType,
    ExceptionHandler,
    ExtractedEntities,
    FileUtils,
    IntegrationError,
    JsonUtils,
    LoggingManager,
    MemoriError,
    MemoryCategory,
    MemoryCategoryType,
    MemoryImportance,
    MemoryNotFoundError,
    MemoryValidator,
    PerformanceUtils,
    ProcessedMemory,
    ProcessingError,
    RateLimitError,
    ResourceExhaustedError,
    RetentionType,
    RetryUtils,
    SecurityError,
    StringUtils,
    TimeoutError,
    ValidationError,
    get_logger,
)

# Memory agents (dynamically imported to avoid import errors)
MemoryAgent: Any | None = None
MemorySearchEngine: Any | None = None
_AGENTS_AVAILABLE = False

try:
    from .agents.memory_agent import MemoryAgent
    from .agents.retrieval_agent import MemorySearchEngine

    _AGENTS_AVAILABLE = True
except ImportError:
    # Agents are not available, use placeholder None values
    pass

# Build __all__ list dynamically based on available components
_all_components = [
    # Core
    "Memori",
    "DatabaseManager",
    # Configuration
    "MemoriSettings",
    "DatabaseSettings",
    "AgentSettings",
    "LoggingSettings",
    "ConfigManager",
    # Database
    "SQLiteConnector",
    "PostgreSQLConnector",
    "MySQLConnector",
    "BaseQueries",
    "MemoryQueries",
    "ChatQueries",
    # "EntityQueries",  # Removed: graph search simplified
    # Tools
    "MemoryTool",
    "create_memory_tool",
    "create_memory_search_tool",
    # Integrations
    "MemoriOpenAI",
    "MemoriAnthropic",
    # Pydantic Models
    "ProcessedMemory",
    "MemoryCategory",
    "ExtractedEntities",
    "MemoryImportance",
    "ConversationContext",
    "MemoryCategoryType",
    "RetentionType",
    "EntityType",
    # Enhanced Exceptions
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

# Add agents only if available
if _AGENTS_AVAILABLE:
    _all_components.extend(["MemoryAgent", "MemorySearchEngine"])

__all__ = _all_components
