# Memori

## Open-Source Memory Engine for LLMs, AI Agents & Multi-Agent Systems

!!! tip "Philosophy"
    **Second human brain for AI** - Never repeat context again and save 90% tokens. Simple, reliable architecture that just works out of the box with any relational databases.


## What is Memori?

**Memori** is an open-source memory layer to give your AI agents human-like memory. It remembers what matters, promotes what's essential, and injects structured context intelligently into LLM conversations.

## Why Memori?

Memomi uses multi-agents working together to intelligently promote essential long-term memories to short-term storage for faster context injection.

Give your AI agents structured, persistent memory with professional-grade architecture:

```python
# Before: Repeating context every time
from openai import OpenAI
client = OpenAI()

response = client.chat.completions.create(
    model="gpt-4",
    messages=[
        {"role": "system", "content": "You are a Python expert..."},
        {"role": "user", "content": "Remember, I use Flask and pytest..."},
        {"role": "user", "content": "Help me with authentication"}
    ]
)

# After: Automatic context injection
from memori import Memori

memori = Memori(openai_api_key="your-key")
memori.enable()  # Auto-records ALL LLM conversations

# Context automatically injected from memory
response = client.chat.completions.create(
    model="gpt-4", 
    messages=[{"role": "user", "content": "Help me with authentication"}]
)
```

## Key Features

- **Universal Integration**: Works with ANY LLM library (LiteLLM, OpenAI, Anthropic)
- **Intelligent Processing**: Pydantic-based memory with entity extraction
- **Auto-Context Injection**: Relevant memories automatically added to conversations  
- **Multiple Memory Types**: Short-term, long-term, rules, and entity relationships
- **Advanced Search**: Full-text search with semantic ranking
- **Production-Ready**: Comprehensive error handling, logging, and configuration
- **Database Support**: SQLite, PostgreSQL, MySQL
- **Type Safety**: Full Pydantic validation and type checking

## Memory Types

| Type | Purpose | Retention | Use Case |
|------|---------|-----------|----------|
| **Short-term** | Recent conversations | 7-30 days | Context for current session |
| **Long-term** | Important insights | Permanent | User preferences, key facts |
| **Rules** | User preferences/constraints | Permanent | "I prefer Python", "Use pytest" |
| **Entities** | People, projects, technologies | Tracked | Relationship mapping |

## Quick Start

Get started with Memori in minutes! Follow our easy quick start guide:

**[Quick Start Guide](getting-started/quick-start.md)**

Learn how to install Memori, set up your first memory-enabled agent, and see the magic of automatic context injection in action.

## Universal Integration

Works with **ANY** LLM library:

**[See all supported LLMs](open-source/llms/overview.md)**

```python
memori.enable()  # Enable universal recording

# OpenAI (recommended)
from openai import OpenAI
client = OpenAI()
client.chat.completions.create(...)

# LiteLLM
from litellm import completion
completion(model="gpt-4", messages=[...])

# Anthropic  
import anthropic
client = anthropic.Anthropic()
client.messages.create(...)

# All automatically recorded and contextualized!
```

## Multiple Database Support

Supports multiple relational databases for production-ready memory storage:

**[Database Configuration Guide](open-source/databases/overview.md)**

## Framework Integrations

Seamlessly integrates with popular AI agent frameworks and tools:

**[View All Integrations](integrations/overview.md)**

## Multi-Agent Architecture

Learn about Memori's intelligent multi-agent system that powers memory processing:

**[Understanding Memori Agents](core-concepts/agents.md)**

## Configuration

Learn more about advanced configuration options:

**[Configuration Settings Guide](configuration/settings.md)**

---

*Made for developers who want their AI agents to remember and learn*