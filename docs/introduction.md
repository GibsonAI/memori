[![Memori Labs](https://s3.us-east-1.amazonaws.com/images.memorilabs.ai/banner.png)](https://memorilabs.ai/)

# What is Memori?

**Memori** is an open source system that gives your AI agents a structured, persistent memory layer. It automatically captures conversations, extracts meaningful facts, and makes them searchable across entities, processes, and sessions.

## Why Memori?

Memori uses an intelligent system called [Advanced Augmentation](https://github.com/MemoriLabs/Memori/blob/main/docs/AdvancedAugmentation.md) to automatically enhance your memories with facts, preferences, attributes, events, relationships, and more. Since it runs in the background there is no added latency to your AI processes.

Memori doesn't require you to rewrite code or use yet another framework. It plugs directly into your existing systems and is database, LLM and framework agnostic. Best of all, it's SQL-native so it uses infrastructure you already have and know how to scale.

Build AI applications with enterprise-grade memory capabilities:

```python
from memori import Memori
from openai import OpenAI

client = OpenAI()
mem = Memori(conn=db_session_factory).openai.register(client)

# Track conversations by user and process
mem.attribution(entity_id="user_123", process_id="support_agent")

# All conversations automatically persisted and recalled
response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": "What color is Mars?"}]
)

# Recall facts later using semantic search
facts = mem.recall("Mars color")
# Returns: [{"fact": "Mars is red", "entity_id": "user_123", ...}]
```

## Key Features

- **LLM Provider Support**: OpenAI, Anthropic, Bedrock, Gemini, Grok (xAI) - all modes (streamed, unstreamed, sync, async)
- **Framework Integration**: Native support for LangChain and Pydantic AI
- **Universal Database Support**: DB API 2.0, SQLAlchemy, Django ORM
- **Multiple Datastores**: PostgreSQL, MySQL/MariaDB, SQLite, MongoDB, CockroachDB, Neon, Supabase, Oracle, and more
- **Attribution System**: Track memories by entity (user), process (agent), and session
- **Recall API**: Semantic search across facts using embeddings
- **Background Augmentation**: AI-powered memory augmentation with no latency impact
- **Production-Ready**: Type-safe, comprehensive error handling, and battle-tested

## Core Concepts

| Concept          | Description                             | Example                                  |
| ---------------- | --------------------------------------- | ---------------------------------------- |
| **Entity**       | Person, place, or thing (like a user)   | `entity_id="user_123"`                   |
| **Process**      | Your agent, LLM interaction, or program | `process_id="support_agent"`             |
| **Session**      | Groups LLM interactions together        | Auto-generated UUID, manually manageable |
| **Augmentation** | Background AI enhancement of memories   | Extracts facts, preferences, skills, etc |
| **Recall**       | Semantic search across stored facts     | `mem.recall("Mars color", limit=5)`      |
