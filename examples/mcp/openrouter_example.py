#!/usr/bin/env python3
"""
OpenRouter MCP Example

This example demonstrates how to use the Memori MCP server with OpenRouter,
which provides access to 100+ LLMs including Claude, GPT-4, Llama, Mistral, and more.

Benefits of using OpenRouter:
- Access to 100+ models through a single API
- Competitive pricing with automatic fallbacks
- No need for multiple API keys
- Free models available (Llama, Mistral, etc.)
- Usage tracking and analytics

Setup:
1. Get your OpenRouter API key from https://openrouter.ai/keys
2. Set environment variables
3. Run this script to test

Cost comparison (approximate):
- Claude 3.5 Sonnet: $0.003/1K tokens (input), $0.015/1K tokens (output)
- GPT-4o: $0.005/1K tokens (input), $0.015/1K tokens (output)
- Llama 3.1 70B: FREE (community-hosted)
- Mistral 8x7B: $0.00024/1K tokens (input), $0.00024/1K tokens (output)
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Configure environment for OpenRouter
print("=" * 80)
print("Memori MCP Server - OpenRouter Example")
print("=" * 80)
print()

# Check for OpenRouter API key
openrouter_key = os.getenv("OPENROUTER_API_KEY")
if not openrouter_key:
    print("❌ OPENROUTER_API_KEY not set!")
    print()
    print("To use OpenRouter:")
    print("1. Get your API key from https://openrouter.ai/keys")
    print("2. Set environment variable:")
    print("   export OPENROUTER_API_KEY='sk-or-v1-your-key-here'")
    print()
    print("Or for testing, set it in this script:")
    print("   os.environ['OPENROUTER_API_KEY'] = 'sk-or-v1-your-key-here'")
    print()
    sys.exit(1)

# Configure OpenRouter settings
os.environ["MEMORI_DATABASE_URL"] = "sqlite:///openrouter_mcp_test.db"
os.environ["OPENROUTER_API_KEY"] = openrouter_key

# Choose your model
# Popular options:
# - anthropic/claude-3.5-sonnet (best for structured tasks)
# - anthropic/claude-3-opus (most capable)
# - openai/gpt-4o (fastest GPT-4)
# - meta-llama/llama-3.1-70b-instruct (FREE!)
# - google/gemini-pro-1.5 (Google's Gemini)
# - mistralai/mixtral-8x7b-instruct (cost-effective)

model = os.getenv("OPENROUTER_MODEL", "anthropic/claude-3.5-sonnet")
os.environ["OPENROUTER_MODEL"] = model

# Optional: Set app name for OpenRouter rankings
os.environ["OPENROUTER_APP_NAME"] = "Memori MCP Example"
os.environ["OPENROUTER_SITE_URL"] = "https://github.com/GibsonAI/memori"

print(f"✓ Using OpenRouter with model: {model}")
print(f"✓ Database: openrouter_mcp_test.db")
print()

# Import the MCP server tools
from mcp.memori_mcp_server import (
    record_conversation,
    search_memories,
    get_recent_memories,
    get_memory_statistics,
)


def main():
    """Run OpenRouter MCP examples"""

    user_id = "openrouter_demo_user"

    print("=" * 80)
    print("Testing Memori MCP with OpenRouter")
    print("=" * 80)
    print()

    # Example 1: Record some conversations
    print("1. Recording conversations with OpenRouter model...")
    print()

    conversations = [
        {
            "user": "I'm interested in machine learning and AI",
            "ai": "That's great! ML and AI are exciting fields. What aspects interest you most?",
        },
        {
            "user": "I'm particularly interested in large language models and how they work",
            "ai": "LLMs are fascinating! They use transformer architectures with attention mechanisms. Would you like to learn about the technical details?",
        },
        {
            "user": "Yes, and I also want to build practical applications with them",
            "ai": "Excellent! Building with LLMs involves understanding prompting, fine-tuning, and RAG patterns. Let's explore these together.",
        },
    ]

    for i, conv in enumerate(conversations, 1):
        print(f"   Recording conversation {i}...")
        result = record_conversation(
            user_input=conv["user"],
            ai_response=conv["ai"],
            user_id=user_id,
        )

        if result.get("success"):
            print(f"   ✓ Recorded (chat_id: {result.get('chat_id')})")
        else:
            print(f"   ✗ Failed: {result.get('error')}")
        print()

    print()

    # Example 2: Get memory statistics
    print("2. Getting memory statistics...")
    stats = get_memory_statistics(user_id=user_id)

    if stats.get("success"):
        s = stats["statistics"]
        print(f"   ✓ Total conversations: {s['total_conversations']}")
        print(f"   ✓ Total memories: {s['total_memories']}")
        print(f"   ✓ Short-term: {s['short_term_memories']}")
        print(f"   ✓ Long-term: {s['long_term_memories']}")

        if s["category_distribution"]:
            print(f"   ✓ Categories: {', '.join(s['category_distribution'].keys())}")
    else:
        print(f"   ✗ Failed: {stats.get('error')}")

    print()

    # Example 3: Search memories
    print("3. Searching for memories about 'machine learning'...")
    search_results = search_memories(
        query="machine learning and AI",
        user_id=user_id,
        limit=5,
    )

    if search_results.get("success"):
        print(f"   ✓ Found {search_results.get('total_results')} results")
        for i, mem in enumerate(search_results.get('results', []), 1):
            print(f"   {i}. {mem.get('summary', 'N/A')[:60]}...")
            print(f"      Category: {mem.get('category')} | Importance: {mem.get('importance_score', 0):.2f}")
    else:
        print(f"   ✗ Failed: {search_results.get('error')}")

    print()

    # Example 4: Get recent memories
    print("4. Getting recent memories...")
    recent = get_recent_memories(user_id=user_id, limit=5)

    if recent.get("success"):
        print(f"   ✓ Found {recent.get('total_results')} recent memories")
        for i, mem in enumerate(recent.get('memories', []), 1):
            print(f"   {i}. {mem.get('summary', 'N/A')[:60]}...")
    else:
        print(f"   ✗ Failed: {recent.get('error')}")

    print()

    # Example 5: Model comparison tip
    print("=" * 80)
    print("💡 Model Selection Tips")
    print("=" * 80)
    print()
    print("For memory processing (entity extraction, categorization):")
    print()
    print("Best quality:")
    print("  - anthropic/claude-3.5-sonnet ($$$)")
    print("  - openai/gpt-4o ($$$)")
    print()
    print("Good balance:")
    print("  - anthropic/claude-3-haiku ($$)")
    print("  - openai/gpt-4o-mini ($$)")
    print()
    print("Free/cheap:")
    print("  - meta-llama/llama-3.1-70b-instruct (FREE)")
    print("  - mistralai/mixtral-8x7b-instruct ($)")
    print()
    print("To change model, set environment variable:")
    print("  export OPENROUTER_MODEL='anthropic/claude-3.5-sonnet'")
    print()
    print("See all models: https://openrouter.ai/models")
    print()

    print("=" * 80)
    print("Example completed!")
    print("=" * 80)
    print()
    print(f"Database: openrouter_mcp_test.db")
    print(f"Model used: {model}")
    print()
    print("Next steps:")
    print("1. Try different models by changing OPENROUTER_MODEL")
    print("2. Check your usage at https://openrouter.ai/activity")
    print("3. Configure in Claude Desktop - see mcp/claude_desktop_config_openrouter.json")
    print()


if __name__ == "__main__":
    main()
