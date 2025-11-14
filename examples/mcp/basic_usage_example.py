#!/usr/bin/env python3
"""
Basic MCP Usage Example

This example demonstrates how to test the Memori MCP server tools directly
without needing a full MCP client like Claude Desktop.

This is useful for:
- Testing the MCP server functionality
- Understanding how the tools work
- Debugging issues
- Development and iteration
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Set environment variables
os.environ["MEMORI_DATABASE_URL"] = "sqlite:///test_mcp.db"
os.environ["OPENAI_API_KEY"] = "your-api-key-here"

# Import the MCP server tools
from mcp.memori_mcp_server import (
    record_conversation,
    search_memories,
    get_recent_memories,
    get_memory_statistics,
    get_conversation_history,
)


def main():
    """Run basic MCP tool examples"""

    print("=" * 80)
    print("Memori MCP Server - Basic Usage Example")
    print("=" * 80)
    print()

    user_id = "demo_user"

    # Example 1: Record a conversation
    print("1. Recording a conversation...")
    result = record_conversation(
        user_input="I'm building a web application with FastAPI and PostgreSQL",
        ai_response="That's great! FastAPI is excellent for building high-performance APIs. Would you like help with the database setup?",
        user_id=user_id,
    )
    print(f"   Result: {result}")
    print()

    # Example 2: Record another conversation
    print("2. Recording another conversation...")
    result = record_conversation(
        user_input="Yes, I need help setting up SQLAlchemy models",
        ai_response="I can help you with that. Let's start by defining your database models using SQLAlchemy ORM.",
        user_id=user_id,
    )
    print(f"   Result: {result}")
    print()

    # Example 3: Record a preference
    print("3. Recording a user preference...")
    result = record_conversation(
        user_input="I prefer using async/await patterns in Python",
        ai_response="Noted! I'll keep that in mind and suggest async patterns when appropriate.",
        user_id=user_id,
    )
    print(f"   Result: {result}")
    print()

    # Example 4: Get memory statistics
    print("4. Getting memory statistics...")
    stats = get_memory_statistics(user_id=user_id)
    print(f"   Statistics: {stats}")
    print()

    # Example 5: Search for memories
    print("5. Searching for memories about 'Python'...")
    search_results = search_memories(
        query="Python programming",
        user_id=user_id,
        limit=5,
    )
    print(f"   Found {search_results.get('total_results', 0)} results")
    for i, memory in enumerate(search_results.get('results', []), 1):
        print(f"   {i}. {memory.get('summary', 'N/A')} (Category: {memory.get('category', 'N/A')})")
    print()

    # Example 6: Get recent memories
    print("6. Getting recent memories...")
    recent = get_recent_memories(
        user_id=user_id,
        limit=5,
    )
    print(f"   Found {recent.get('total_results', 0)} recent memories")
    for i, memory in enumerate(recent.get('memories', []), 1):
        print(f"   {i}. {memory.get('summary', 'N/A')}")
    print()

    # Example 7: Get conversation history
    print("7. Getting conversation history...")
    history = get_conversation_history(
        user_id=user_id,
        limit=10,
    )
    print(f"   Found {history.get('total_conversations', 0)} conversations")
    for i, conv in enumerate(history.get('conversations', []), 1):
        print(f"   {i}. User: {conv.get('user_input', 'N/A')[:50]}...")
        print(f"      AI:   {conv.get('ai_output', 'N/A')[:50]}...")
    print()

    print("=" * 80)
    print("Example completed! Check test_mcp.db for stored data.")
    print("=" * 80)


if __name__ == "__main__":
    main()
