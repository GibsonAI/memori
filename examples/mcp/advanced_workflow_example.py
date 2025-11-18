#!/usr/bin/env python3
"""
Advanced MCP Workflow Example

This example demonstrates more complex workflows using the Memori MCP server,
including:
- Multi-session management
- Category-based filtering
- Importance-based search
- Memory lifecycle management
"""

import sys
import os
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Set environment variables
os.environ["MEMORI_DATABASE_URL"] = "sqlite:///advanced_mcp.db"
os.environ["OPENAI_API_KEY"] = "your-api-key-here"

from mcp.memori_mcp_server import (
    record_conversation,
    search_memories,
    get_recent_memories,
    get_memory_statistics,
    clear_session_memories,
)


def simulate_project_conversation():
    """Simulate a conversation about a software project"""

    print("\n" + "=" * 80)
    print("SCENARIO 1: Software Project Discussion")
    print("=" * 80)

    user_id = "developer_123"
    session_id = "project_planning"

    # Day 1: Initial project discussion
    print("\nDay 1: Initial Planning")
    conversations = [
        {
            "user": "I'm starting a new e-commerce platform project",
            "ai": "Exciting! Let's plan this carefully. What's your tech stack preference?",
        },
        {
            "user": "I want to use Next.js for frontend and Python FastAPI for backend",
            "ai": "Great choices! Next.js provides excellent SEO and FastAPI is very performant.",
        },
        {
            "user": "I'll need user authentication, product catalog, and payment processing",
            "ai": "Those are the core features. For auth, I'd suggest JWT tokens. For payments, Stripe is a solid choice.",
        },
    ]

    for conv in conversations:
        result = record_conversation(
            user_input=conv["user"],
            ai_response=conv["ai"],
            user_id=user_id,
            session_id=session_id,
        )
        print(f"  Recorded: {conv['user'][:50]}...")

    # Check what was recorded
    stats = get_memory_statistics(user_id=user_id)
    print(f"\n  Stats after Day 1: {stats['statistics']['total_memories']} memories")


def simulate_preference_learning():
    """Simulate learning user preferences over time"""

    print("\n" + "=" * 80)
    print("SCENARIO 2: Learning User Preferences")
    print("=" * 80)

    user_id = "power_user_456"

    preferences = [
        {
            "user": "I always prefer TypeScript over JavaScript",
            "ai": "Noted! I'll suggest TypeScript solutions from now on.",
        },
        {
            "user": "I like to write comprehensive tests for everything",
            "ai": "Great practice! I'll make sure to include test examples in my suggestions.",
        },
        {
            "user": "I prefer functional programming patterns when possible",
            "ai": "Understood! I'll focus on functional approaches and avoid mutations.",
        },
        {
            "user": "I use VS Code with Vim keybindings",
            "ai": "Nice setup! I'll keep that in mind when suggesting editor configurations.",
        },
    ]

    for pref in preferences:
        result = record_conversation(
            user_input=pref["user"],
            ai_response=pref["ai"],
            user_id=user_id,
        )
        print(f"  Learned: {pref['user']}")

    # Search for preferences
    print("\n  Searching for programming preferences...")
    results = search_memories(
        query="programming preferences",
        user_id=user_id,
        category="preference",
        limit=10,
    )

    print(f"  Found {results['total_results']} preferences:")
    for mem in results.get('results', []):
        print(f"    - {mem.get('summary', 'N/A')}")


def simulate_multi_session_workflow():
    """Simulate working across multiple sessions"""

    print("\n" + "=" * 80)
    print("SCENARIO 3: Multi-Session Workflow")
    print("=" * 80)

    user_id = "researcher_789"

    # Session 1: Research on AI
    print("\n  Session 1: AI Research")
    session1_id = "ai_research"
    for conv in [
        ("Tell me about transformer architectures", "Transformers revolutionized NLP..."),
        ("How do attention mechanisms work?", "Attention allows models to focus on relevant parts..."),
    ]:
        record_conversation(conv[0], conv[1], user_id, session_id=session1_id)
        print(f"    Recorded: {conv[0][:40]}...")

    # Session 2: Research on databases
    print("\n  Session 2: Database Research")
    session2_id = "database_research"
    for conv in [
        ("What are the benefits of PostgreSQL?", "PostgreSQL offers ACID compliance, advanced features..."),
        ("Explain database indexing", "Indexes speed up queries by creating lookup structures..."),
    ]:
        record_conversation(conv[0], conv[1], user_id, session_id=session2_id)
        print(f"    Recorded: {conv[0][:40]}...")

    # Session 3: Temporary brainstorming
    print("\n  Session 3: Temporary Brainstorming")
    session3_id = "temp_brainstorm"
    for conv in [
        ("Random idea: AI-powered code reviewer", "Interesting! That could help catch bugs..."),
        ("Another idea: Automated documentation generator", "That would save a lot of time..."),
    ]:
        record_conversation(conv[0], conv[1], user_id, session_id=session3_id)
        print(f"    Recorded: {conv[0][:40]}...")

    # Now clear the temporary session
    print("\n  Clearing temporary brainstorming session...")
    clear_result = clear_session_memories(
        session_id=session3_id,
        user_id=user_id,
    )
    print(f"    {clear_result.get('message', 'Done')}")

    # Check remaining memories
    stats = get_memory_statistics(user_id=user_id)
    print(f"\n  Final stats: {stats['statistics']['total_memories']} memories (temp session cleared)")


def demonstrate_search_filtering():
    """Demonstrate advanced search with filtering"""

    print("\n" + "=" * 80)
    print("SCENARIO 4: Advanced Search Filtering")
    print("=" * 80)

    user_id = "data_scientist_101"

    # Record various types of information
    print("\n  Recording diverse information...")

    facts = [
        "I work with pandas and numpy daily",
        "My current dataset has 10 million rows",
        "I'm using scikit-learn for machine learning",
    ]

    for fact in facts:
        record_conversation(fact, "Got it, I'll remember that.", user_id)

    # Search with different filters
    print("\n  Searching for 'data' with category filter...")
    results = search_memories(
        query="data science tools",
        user_id=user_id,
        category="fact",
        limit=5,
    )
    print(f"    Found {results['total_results']} fact-type memories")

    print("\n  Searching for high-importance memories...")
    results = search_memories(
        query="machine learning",
        user_id=user_id,
        min_importance=0.7,
        limit=5,
    )
    print(f"    Found {results['total_results']} high-importance memories")


def main():
    """Run all advanced workflow examples"""

    print("=" * 80)
    print("Memori MCP Server - Advanced Workflow Examples")
    print("=" * 80)

    # Run each scenario
    simulate_project_conversation()
    simulate_preference_learning()
    simulate_multi_session_workflow()
    demonstrate_search_filtering()

    print("\n" + "=" * 80)
    print("All scenarios completed! Check advanced_mcp.db for stored data.")
    print("=" * 80)


if __name__ == "__main__":
    main()
