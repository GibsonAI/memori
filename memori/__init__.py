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
from .database.queries import BaseQueries, ChatQueries, EntityQueries, MemoryQueries

# Wrapper integrations (legacy - will show deprecation warnings)
from .integrations import MemoriAnthropic, MemoriOpenAI

# Tools and integrations
from .tools.memory_tool import MemoryTool, create_memory_search_tool, create_memory_tool

# Utils and models
from .utils import (  # Pydantic models; Enhanced exceptions; Validators and helpers; Logging
    AgentError,
    AsyncUtils,
    AuthenticationError,
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

# Integration factory functions (recommended way to use integrations)
create_openai_client: Any | None = None
create_genai_model: Any | None = None
setup_openai_interceptor: Any | None = None
setup_genai_interceptor: Any | None = None
_INTEGRATIONS_AVAILABLE = {"openai": False, "genai": False, "anthropic": False}

try:
    from .integrations.openai_integration import (
        create_openai_client,
        setup_openai_interceptor,
    )
    _INTEGRATIONS_AVAILABLE["openai"] = True
except ImportError:
    pass

try:
    from .integrations.google_genai_integration import (
        create_genai_model,
        setup_genai_interceptor,
    )
    _INTEGRATIONS_AVAILABLE["genai"] = True
except ImportError:
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
    "EntityQueries",
    # Tools
    "MemoryTool",
    "create_memory_tool",
    "create_memory_search_tool",
    # Integrations (legacy wrappers)
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

# Add integration factory functions if available
if _INTEGRATIONS_AVAILABLE["openai"]:
    _all_components.extend(["create_openai_client", "setup_openai_interceptor"])

if _INTEGRATIONS_AVAILABLE["genai"]:
    _all_components.extend(["create_genai_model", "setup_genai_interceptor"])

__all__ = _all_components


# Convenience function to show available integrations
def get_available_integrations():
    """
    Get a dictionary of available LLM integrations.
    
    Returns:
        dict: Dictionary with provider names as keys and availability as values
    """
    return _INTEGRATIONS_AVAILABLE.copy()


def get_integration_status():
    """
    Print a formatted status of all available integrations.
    """
    logger = get_logger(__name__)
    logger.info("🔌 Memori Integration Status:")
    logger.info(f"  OpenAI: {'✅ Available' if _INTEGRATIONS_AVAILABLE['openai'] else '❌ Not installed'}")
    logger.info(f"  Google GenAI: {'✅ Available' if _INTEGRATIONS_AVAILABLE['genai'] else '❌ Not installed'}")
    logger.info(f"  Anthropic: {'✅ Available' if _INTEGRATIONS_AVAILABLE['anthropic'] else '❌ Not installed'}")
    logger.info(f"  Agents: {'✅ Available' if _AGENTS_AVAILABLE else '❌ Not available'}")


# Add these to __all__ as well
_all_components.extend(["get_available_integrations", "get_integration_status"])
__all__ = _all_components