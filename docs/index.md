# Memori

## Open-Source Memory Engine for LLMs, AI Agents & Multi-Agent Systems

!!! tip "Philosophy"
    **Second human brain for AI** - Never repeat context again and save 90% tokens. Simple, reliable architecture that just works out of the box with any relational databases.


## What is Memori?

**Memori** is an open-source memory layer to give your AI agents human-like memory. It remembers what matters, promotes what's essential, and injects structured context intelligently into LLM conversations.

## Why Memori?

Memori uses multi-agents working together to intelligently promote essential long-term memories to short-term storage for faster context injection.

### SQL-Native: Transparent, Portable & 80-90% Cheaper

Unlike vector databases (Pinecone, Weaviate), Memori stores memories in **standard SQL databases**:

| Feature | Vector Databases | Memori (SQL-Native) | Winner |
|---------|------------------|---------------------|--------|
| **Cost (100K memories)** | $80-100/month | $0-15/month | **Memori 80-90% cheaper** |
| **Portability** | Vendor lock-in | Export as `.db` file | **Memori** |
| **Transparency** | Black-box embeddings | Human-readable SQL | **Memori** |
| **Query Speed** | 25-40ms (semantic) | 8-12ms (keywords) | **Memori 3x faster** |
| **Complex Queries** | Limited (distance only) | Full SQL power | **Memori** |

**Why SQL wins for conversational memory:**

- **90% of queries are explicit**: "What's my tech stack?" not "Find similar documents"
- **Boolean logic**: Search "FastAPI AND authentication NOT migrations"
- **Multi-factor ranking**: Combine importance, recency, and categories
- **Complete ownership**: Your data in portable format you control

!!! tip "When to Use Vector Databases"
    Use vectors for **semantic similarity across unstructured documents**. Use Memori (SQL) for **conversational AI memory** where users know what they're asking for.

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
# Memori automatically knows about your FastAPI Python project!
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

### Use with serverless databases

Get FREE serverless database instance in GibsonAI platform. You can just prompt to create and deploy a new database.

**[GibsonAI Integration Guide](open-source/databases/gibsonai.md)**

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