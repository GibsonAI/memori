#!/usr/bin/env python3
"""
Memori MCP Server

A Model Context Protocol (MCP) server that exposes Memori's persistent memory
capabilities to any MCP-compatible AI assistant like Claude.

This server provides tools for:
- Recording conversations and memories
- Searching and retrieving memories
- Managing memory lifecycle
- Getting memory statistics and insights
"""

import os
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import FastMCP

# Add parent directory to path to import memori
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from memori import Memori
from memori.utils.pydantic_models import (
    MemoryCategoryType,
    MemoryClassification,
    MemoryImportance,
)

# Initialize FastMCP server
mcp = FastMCP(
    name="memori",
    version="1.0.0",
    description="Persistent memory engine for AI assistants using SQL databases",
)

# Global Memori instance - will be configured per user
_memori_instances: Dict[str, Memori] = {}


def get_memori_instance(
    user_id: str = "default_user",
    assistant_id: str = "mcp_assistant",
    session_id: Optional[str] = None,
    database_connect: Optional[str] = None,
) -> Memori:
    """
    Get or create a Memori instance for the given user.

    Supports multiple LLM providers:
    - OpenAI (default)
    - OpenRouter (set OPENROUTER_API_KEY)
    - Azure OpenAI (set AZURE_OPENAI_API_KEY)
    - Custom OpenAI-compatible endpoints (set LLM_BASE_URL)

    Args:
        user_id: User identifier for multi-tenant isolation
        assistant_id: Assistant identifier
        session_id: Optional session identifier
        database_connect: Optional database connection string

    Returns:
        Memori instance configured for the user
    """
    # Create a unique key for this configuration
    key = f"{user_id}:{assistant_id}:{session_id or 'default'}"

    if key not in _memori_instances:
        # Get database connection from environment or use default SQLite
        db_connect = database_connect or os.getenv(
            "MEMORI_DATABASE_URL", "sqlite:///memori_mcp.db"
        )

        # Detect LLM provider configuration from environment
        llm_config = _detect_llm_provider()

        # Create new Memori instance
        _memori_instances[key] = Memori(
            database_connect=db_connect,
            user_id=user_id,
            assistant_id=assistant_id,
            session_id=session_id,
            conscious_ingest=True,  # Enable conscious memory injection
            auto_ingest=False,  # Disable auto-injection (manual via MCP)
            **llm_config,  # Unpack provider configuration
        )

    return _memori_instances[key]


def _detect_llm_provider() -> Dict[str, Any]:
    """
    Detect LLM provider from environment variables and return configuration.

    Priority order:
    1. OpenRouter (OPENROUTER_API_KEY)
    2. Azure OpenAI (AZURE_OPENAI_API_KEY)
    3. Custom endpoint (LLM_BASE_URL)
    4. OpenAI (OPENAI_API_KEY) - default

    Returns:
        Dictionary of configuration parameters for Memori.__init__
    """
    config = {}

    # Priority 1: OpenRouter
    openrouter_key = os.getenv("OPENROUTER_API_KEY")
    if openrouter_key:
        config["api_key"] = openrouter_key
        config["base_url"] = os.getenv(
            "OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"
        )
        config["model"] = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o")
        return config

    # Priority 2: Azure OpenAI
    azure_key = os.getenv("AZURE_OPENAI_API_KEY")
    if azure_key:
        config["api_key"] = azure_key
        config["api_type"] = "azure"
        config["azure_endpoint"] = os.getenv("AZURE_OPENAI_ENDPOINT")
        config["azure_deployment"] = os.getenv("AZURE_OPENAI_DEPLOYMENT")
        config["api_version"] = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")
        config["model"] = os.getenv("AZURE_OPENAI_MODEL", "gpt-4o")
        return config

    # Priority 3: Custom OpenAI-compatible endpoint
    custom_base_url = os.getenv("LLM_BASE_URL")
    if custom_base_url:
        config["api_key"] = os.getenv("LLM_API_KEY")
        config["base_url"] = custom_base_url
        config["model"] = os.getenv("LLM_MODEL", "gpt-4o")
        return config

    # Priority 4: Default OpenAI
    config["openai_api_key"] = os.getenv("OPENAI_API_KEY")
    if os.getenv("OPENAI_MODEL"):
        config["model"] = os.getenv("OPENAI_MODEL")

    return config


# ============================================================================
# TOOLS - Actions that can be performed
# ============================================================================


@mcp.tool()
def record_conversation(
    user_input: str,
    ai_response: str,
    user_id: str = "default_user",
    assistant_id: str = "mcp_assistant",
    session_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Record a conversation turn in Memori's persistent memory.

    This stores both the user input and AI response, processes them to extract
    entities, categories, and importance, and makes them available for future
    retrieval.

    Args:
        user_input: The user's message or question
        ai_response: The AI's response to the user
        user_id: User identifier (default: "default_user")
        assistant_id: Assistant identifier (default: "mcp_assistant")
        session_id: Optional session identifier for conversation grouping
        metadata: Optional metadata dictionary to attach to the conversation

    Returns:
        Dictionary with recording status and chat_id

    Example:
        record_conversation(
            user_input="I'm working on a Python project",
            ai_response="That's great! What kind of Python project?",
            user_id="user123"
        )
    """
    try:
        memori = get_memori_instance(user_id, assistant_id, session_id)

        # Record the conversation
        chat_id = memori.record(
            user_input=user_input,
            ai_response=ai_response,
            metadata=metadata or {},
        )

        return {
            "success": True,
            "message": "Conversation recorded successfully",
            "chat_id": chat_id,
            "user_id": user_id,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to record conversation",
        }


@mcp.tool()
def search_memories(
    query: str,
    user_id: str = "default_user",
    assistant_id: str = "mcp_assistant",
    limit: int = 10,
    category: Optional[str] = None,
    min_importance: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Search for relevant memories based on a query.

    Uses intelligent search to find memories that are semantically relevant to
    the query. Can filter by category and importance level.

    Args:
        query: The search query or topic
        user_id: User identifier
        assistant_id: Assistant identifier
        limit: Maximum number of results to return (default: 10)
        category: Optional filter by category (fact, preference, skill, context, rule)
        min_importance: Optional minimum importance score (0.0 to 1.0)

    Returns:
        Dictionary with search results and metadata

    Example:
        search_memories(
            query="Python projects",
            user_id="user123",
            category="fact",
            limit=5
        )
    """
    try:
        memori = get_memori_instance(user_id, assistant_id)

        # Build search filters
        filters = {}
        if category:
            filters["category_primary"] = category
        if min_importance is not None:
            filters["importance_score_min"] = min_importance

        # Search memories
        results = memori.db_manager.search_memories(
            query=query, user_id=user_id, limit=limit, **filters
        )

        # Format results
        formatted_results = []
        for memory in results:
            formatted_results.append(
                {
                    "memory_id": memory.memory_id,
                    "summary": memory.summary,
                    "category": memory.category_primary,
                    "importance_score": memory.importance_score,
                    "created_at": (
                        memory.created_at.isoformat() if memory.created_at else None
                    ),
                    "entities": (
                        memory.entities_json if hasattr(memory, "entities_json") else []
                    ),
                }
            )

        return {
            "success": True,
            "query": query,
            "total_results": len(formatted_results),
            "results": formatted_results,
            "filters_applied": filters,
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to search memories",
        }


@mcp.tool()
def get_recent_memories(
    user_id: str = "default_user",
    assistant_id: str = "mcp_assistant",
    limit: int = 20,
    memory_type: str = "short_term",
) -> Dict[str, Any]:
    """
    Get the most recent memories for a user.

    Retrieves memories in reverse chronological order, useful for understanding
    recent context and conversation history.

    Args:
        user_id: User identifier
        assistant_id: Assistant identifier
        limit: Maximum number of memories to return (default: 20)
        memory_type: Type of memory to retrieve ("short_term" or "long_term")

    Returns:
        Dictionary with recent memories

    Example:
        get_recent_memories(user_id="user123", limit=10)
    """
    try:
        memori = get_memori_instance(user_id, assistant_id)

        # Get recent memories from database
        with memori.db_manager.get_session() as session:
            if memory_type == "short_term":
                from memori.database.models import ShortTermMemory

                memories = (
                    session.query(ShortTermMemory)
                    .filter_by(user_id=user_id, assistant_id=assistant_id)
                    .order_by(ShortTermMemory.created_at.desc())
                    .limit(limit)
                    .all()
                )
            else:
                from memori.database.models import LongTermMemory

                memories = (
                    session.query(LongTermMemory)
                    .filter_by(user_id=user_id, assistant_id=assistant_id)
                    .order_by(LongTermMemory.created_at.desc())
                    .limit(limit)
                    .all()
                )

            # Format results
            formatted_memories = []
            for mem in memories:
                formatted_memories.append(
                    {
                        "memory_id": mem.memory_id,
                        "summary": mem.summary,
                        "category": mem.category_primary,
                        "importance_score": mem.importance_score,
                        "created_at": mem.created_at.isoformat() if mem.created_at else None,
                    }
                )

        return {
            "success": True,
            "memory_type": memory_type,
            "total_results": len(formatted_memories),
            "memories": formatted_memories,
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to retrieve recent memories",
        }


@mcp.tool()
def get_memory_statistics(
    user_id: str = "default_user",
    assistant_id: str = "mcp_assistant",
) -> Dict[str, Any]:
    """
    Get statistics about stored memories for a user.

    Provides insights into memory distribution by category, importance levels,
    total counts, and other useful metrics.

    Args:
        user_id: User identifier
        assistant_id: Assistant identifier

    Returns:
        Dictionary with memory statistics

    Example:
        get_memory_statistics(user_id="user123")
    """
    try:
        memori = get_memori_instance(user_id, assistant_id)

        with memori.db_manager.get_session() as session:
            from memori.database.models import (
                ChatHistory,
                LongTermMemory,
                ShortTermMemory,
            )
            from sqlalchemy import func

            # Count total conversations
            total_conversations = (
                session.query(func.count(ChatHistory.chat_id))
                .filter_by(user_id=user_id, assistant_id=assistant_id)
                .scalar()
            )

            # Count short-term memories
            short_term_count = (
                session.query(func.count(ShortTermMemory.memory_id))
                .filter_by(user_id=user_id, assistant_id=assistant_id)
                .scalar()
            )

            # Count long-term memories
            long_term_count = (
                session.query(func.count(LongTermMemory.memory_id))
                .filter_by(user_id=user_id, assistant_id=assistant_id)
                .scalar()
            )

            # Get category distribution (short-term)
            category_dist = (
                session.query(
                    ShortTermMemory.category_primary,
                    func.count(ShortTermMemory.memory_id),
                )
                .filter_by(user_id=user_id, assistant_id=assistant_id)
                .group_by(ShortTermMemory.category_primary)
                .all()
            )

            categories = {cat: count for cat, count in category_dist if cat}

        return {
            "success": True,
            "user_id": user_id,
            "statistics": {
                "total_conversations": total_conversations or 0,
                "short_term_memories": short_term_count or 0,
                "long_term_memories": long_term_count or 0,
                "total_memories": (short_term_count or 0) + (long_term_count or 0),
                "category_distribution": categories,
            },
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to retrieve statistics",
        }


@mcp.tool()
def get_conversation_history(
    user_id: str = "default_user",
    assistant_id: str = "mcp_assistant",
    session_id: Optional[str] = None,
    limit: int = 50,
) -> Dict[str, Any]:
    """
    Get conversation history for a user or session.

    Retrieves the raw conversation turns (user input and AI responses) in
    chronological order.

    Args:
        user_id: User identifier
        assistant_id: Assistant identifier
        session_id: Optional session identifier to filter by
        limit: Maximum number of conversation turns to return (default: 50)

    Returns:
        Dictionary with conversation history

    Example:
        get_conversation_history(user_id="user123", limit=20)
    """
    try:
        memori = get_memori_instance(user_id, assistant_id, session_id)

        # Get chat history
        history = memori.db_manager.get_chat_history(
            user_id=user_id, assistant_id=assistant_id, session_id=session_id, limit=limit
        )

        # Format results
        formatted_history = []
        for chat in history:
            formatted_history.append(
                {
                    "chat_id": chat.chat_id,
                    "user_input": chat.user_input,
                    "ai_output": chat.ai_output,
                    "model": chat.model,
                    "timestamp": chat.created_at.isoformat() if chat.created_at else None,
                }
            )

        return {
            "success": True,
            "total_conversations": len(formatted_history),
            "conversations": formatted_history,
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to retrieve conversation history",
        }


@mcp.tool()
def clear_session_memories(
    session_id: str,
    user_id: str = "default_user",
    assistant_id: str = "mcp_assistant",
) -> Dict[str, Any]:
    """
    Clear all memories for a specific session.

    Useful for resetting conversation context or removing temporary memories.
    Only affects the specified session, not the user's entire memory.

    Args:
        session_id: Session identifier to clear
        user_id: User identifier
        assistant_id: Assistant identifier

    Returns:
        Dictionary with deletion status

    Example:
        clear_session_memories(session_id="temp_session", user_id="user123")
    """
    try:
        memori = get_memori_instance(user_id, assistant_id, session_id)

        with memori.db_manager.get_session() as session:
            from memori.database.models import ChatHistory, ShortTermMemory

            # Delete chat history for session
            deleted_chats = (
                session.query(ChatHistory)
                .filter_by(
                    user_id=user_id, assistant_id=assistant_id, session_id=session_id
                )
                .delete()
            )

            # Delete short-term memories for session
            deleted_memories = (
                session.query(ShortTermMemory)
                .filter_by(
                    user_id=user_id, assistant_id=assistant_id, session_id=session_id
                )
                .delete()
            )

            session.commit()

        return {
            "success": True,
            "message": f"Cleared {deleted_chats} conversations and {deleted_memories} memories",
            "deleted_conversations": deleted_chats,
            "deleted_memories": deleted_memories,
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to clear session memories",
        }


# ============================================================================
# RESOURCES - Read-only data access
# ============================================================================


@mcp.resource("memori://memories/{user_id}")
def get_user_memories(user_id: str) -> str:
    """
    Get all memories for a specific user as a formatted text resource.

    Args:
        user_id: User identifier

    Returns:
        Formatted text representation of user memories
    """
    try:
        memori = get_memori_instance(user_id)

        with memori.db_manager.get_session() as session:
            from memori.database.models import ShortTermMemory

            memories = (
                session.query(ShortTermMemory)
                .filter_by(user_id=user_id)
                .order_by(ShortTermMemory.importance_score.desc())
                .limit(100)
                .all()
            )

            if not memories:
                return f"No memories found for user: {user_id}"

            # Format as text
            output = f"# Memories for {user_id}\n\n"
            output += f"Total memories: {len(memories)}\n\n"

            for mem in memories:
                output += f"## {mem.category_primary.upper() if mem.category_primary else 'UNCATEGORIZED'}\n"
                output += f"**Summary**: {mem.summary}\n"
                output += f"**Importance**: {mem.importance_score:.2f}\n"
                output += f"**Created**: {mem.created_at.isoformat() if mem.created_at else 'Unknown'}\n"
                output += "\n---\n\n"

            return output
    except Exception as e:
        return f"Error retrieving memories: {str(e)}"


@mcp.resource("memori://stats/{user_id}")
def get_user_stats(user_id: str) -> str:
    """
    Get memory statistics for a user as a formatted text resource.

    Args:
        user_id: User identifier

    Returns:
        Formatted text representation of statistics
    """
    stats = get_memory_statistics(user_id)

    if not stats.get("success"):
        return f"Error: {stats.get('error', 'Unknown error')}"

    s = stats["statistics"]
    output = f"# Memory Statistics for {user_id}\n\n"
    output += f"- **Total Conversations**: {s['total_conversations']}\n"
    output += f"- **Short-term Memories**: {s['short_term_memories']}\n"
    output += f"- **Long-term Memories**: {s['long_term_memories']}\n"
    output += f"- **Total Memories**: {s['total_memories']}\n\n"

    if s["category_distribution"]:
        output += "## Category Distribution\n\n"
        for cat, count in s["category_distribution"].items():
            output += f"- **{cat}**: {count}\n"

    return output


# ============================================================================
# PROMPTS - Reusable interaction patterns
# ============================================================================


@mcp.prompt()
def memory_search_prompt(topic: str, user_id: str = "default_user") -> str:
    """
    Generate a prompt to search and summarize memories about a topic.

    Args:
        topic: The topic to search for
        user_id: User identifier

    Returns:
        Formatted prompt for the AI
    """
    return f"""Please search the user's memories for information about "{topic}" and provide a comprehensive summary.

User ID: {user_id}

Use the search_memories tool to find relevant memories, then:
1. Summarize what you found
2. Highlight the most important facts
3. Note any preferences or context that might be relevant
4. Suggest follow-up questions if appropriate
"""


@mcp.prompt()
def conversation_context_prompt(user_id: str = "default_user", limit: int = 10) -> str:
    """
    Generate a prompt to retrieve recent conversation context.

    Args:
        user_id: User identifier
        limit: Number of recent memories to retrieve

    Returns:
        Formatted prompt for the AI
    """
    return f"""Please retrieve the recent conversation context for this user.

User ID: {user_id}

Use the get_recent_memories tool (limit={limit}) to:
1. Get the last {limit} memories
2. Summarize the key topics discussed
3. Note any ongoing tasks or preferences
4. Provide context for continuing the conversation
"""


# ============================================================================
# Main entry point
# ============================================================================

if __name__ == "__main__":
    # Run the MCP server
    mcp.run()
