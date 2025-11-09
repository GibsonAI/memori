[![Memori Labs](https://s3.us-east-1.amazonaws.com/images.memorilabs.ai/banner.png)](https://memorilabs.ai/)

<p align="center">
  <strong>SQL-Native Memory Engine for AI Agents</strong>
</p>

<p align="center">
  <i>One line of code to give any LLM persistent, queryable memory using standard SQL databases</i>
</p>

<p align="center">
  <a href="https://badge.fury.io/py/memorisdk">
    <img src="https://badge.fury.io/py/memori.svg" alt="PyPI version">
  </a>
  <a href="https://pepy.tech/projects/memorisdk">
    <img src="https://static.pepy.tech/badge/memorisdk" alt="Downloads">
  </a>
  <a href="https://opensource.org/license/apache-2-0">
    <img src="https://img.shields.io/badge/license-Apache%202.0-blue" alt="License">
  </a>
  <a href="https://www.python.org/downloads/">
    <img src="https://img.shields.io/badge/python-3.8+-blue.svg" alt="Python 3.8+">
  </a>
  <a href="https://discord.gg/abD4eGym6v">
    <img src="https://img.shields.io/discord/1042405378304004156?logo=discord" alt="Discord">
  </a>
</p>

---

## Overview

Memori enables any LLM to remember conversations, learn from interactions, and maintain context across sessions with a single line: `memori.enable()`. Memory is stored in standard SQL databases (SQLite, PostgreSQL, MySQL) that you fully own and control.

**Why Memori?**
- **One-line integration** - Works with OpenAI, Anthropic, LiteLLM, LangChain, and any LLM framework
- **SQL-native storage** - Portable, queryable, and auditable memory in databases you control
- **80-90% cost savings** - No expensive vector databases required
- **Zero vendor lock-in** - Export your memory as SQLite and move anywhere
- **Intelligent memory** - Automatic entity extraction, relationship mapping, and context prioritization

[Documentation](https://www.gibsonai.com/docs/memori) | [Examples](#examples) | [Discord](https://discord.gg/abD4eGym6v)

---

## Quick Start

```bash
pip install memorisdk
```

### Basic Usage

```python
from memori import Memori
from openai import OpenAI

# Initialize
memori = Memori(conscious_ingest=True)
memori.enable()

client = OpenAI()

# First conversation
response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": "I'm building a FastAPI project"}]
)

# Later conversation - Memori automatically provides context
response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": "Help me add authentication"}]
)
# LLM automatically knows about your FastAPI project
```

> **Note**: Default uses in-memory SQLite. Get a [free serverless database](https://app.gibsonai.com/signup) for persistent storage.

---

## How It Works

### Memory Modes

**Conscious Mode** - Short-term working memory
```python
memori = Memori(conscious_ingest=True)
```
Analyzes long-term memory at startup and promotes essential conversations to short-term storage. Injected once at conversation start, like human working memory.

**Auto Mode** - Dynamic search
```python
memori = Memori(auto_ingest=True)
```
Intelligently searches the entire memory database for each query and injects relevant context in real-time.

**Combined Mode** - Best of both
```python
memori = Memori(conscious_ingest=True, auto_ingest=True)
```

### Memory Types

| Type | Example | Auto-Promoted |
|------|---------|---------------|
| **Facts** | "Uses PostgreSQL database" | ✓ |
| **Preferences** | "Prefers clean code" | ✓ |
| **Skills** | "Experienced with FastAPI" | ✓ |
| **Rules** | "Always write tests first" | ✓ |
| **Context** | "Working on e-commerce" | ✓ |

---

## Configuration

### Simple Setup

```python
from memori import Memori

# With database persistence
memori = Memori(
    database_connect="sqlite:///my_memory.db",
    conscious_ingest=True,
    openai_api_key="sk-..."
)
memori.enable()
```

### Advanced Configuration

```python
from memori import Memori, ConfigManager

config = ConfigManager()
config.auto_load()  # Loads from memori.json or environment

memori = Memori()
memori.enable()
```

**memori.json**:
```json
{
  "database": {
    "connection_string": "postgresql://user:pass@localhost/memori"
  },
  "agents": {
    "openai_api_key": "sk-...",
    "conscious_ingest": true,
    "auto_ingest": false
  },
  "memory": {
    "namespace": "my_project",
    "retention_policy": "30_days"
  }
}
```

### Universal LLM Integration

```python
memori.enable()  # Works with ANY LLM library

# OpenAI
from openai import OpenAI
OpenAI().chat.completions.create(...)

# Anthropic
from anthropic import Anthropic
Anthropic().messages.create(...)

# LiteLLM
from litellm import completion
completion(model="gpt-4", messages=[...])
```

### Memory Management

```python
# Manual conscious analysis
memori.trigger_conscious_analysis()

# Get essential conversations
essential = memori.get_essential_conversations(limit=5)

# Search by category
skills = memori.search_memories_by_category("skill", limit=10)

# Create memory search tool for function calling
from memori.tools import create_memory_tool
memory_tool = create_memory_tool(memori)
```

---

## Examples

**Basic Examples**
- [Basic Usage](./examples/basic_usage.py) - Simple memory setup
- [Personal Assistant](./examples/personal_assistant.py) - AI assistant with memory
- [Memory Retrieval](./memory_retrival_example.py) - Function calling
- [Advanced Config](./examples/advanced_config.py) - Production setup

**Multi-User**
- [Simple Multi-User](./examples/multiple-users/simple_multiuser.py) - User memory isolation
- [FastAPI Multi-User App](./examples/multiple-users/fastapi_multiuser_app.py) - REST API with Swagger

**Framework Integrations**

| Framework | Description |
|-----------|-------------|
| [AgentOps](./examples/integrations/agentops_example.py) | Memory operation tracking with observability |
| [Agno](./examples/integrations/agno_example.py) | Agent framework with persistent conversations |
| [AWS Strands](./examples/integrations/aws_strands_example.py) | Strands SDK with persistent memory |
| [Azure AI Foundry](./examples/integrations/azure_ai_foundry_example.py) | Enterprise AI agents with Azure |
| [AutoGen](./examples/integrations/autogen_example.py) | Multi-agent group chat memory |
| [CamelAI](./examples/integrations/camelai_example.py) | Multi-agent communication framework |
| [CrewAI](./examples/integrations/crewai_example.py) | Multi-agent shared memory |
| [Digital Ocean AI](./examples/integrations/digital_ocean_example.py) | Customer support with history |
| [LangChain](./examples/integrations/langchain_example.py) | Enterprise agent framework |
| [OpenAI Agent](./examples/integrations/openai_agent_example.py) | Function calling with preferences |
| [Swarms](./examples/integrations/swarms_example.py) | Multi-agent persistent memory |

**Interactive Demos**

| Demo | Description | Live |
|------|-------------|------|
| [Personal Diary](./demos/personal_diary_assistant/) | Mood tracking and pattern analysis | [Try it](https://personal-diary-assistant.streamlit.app/) |
| [Travel Planner](./demos/travel_planner/) | CrewAI travel planning with memory | - |
| [Researcher](./demos/researcher_agent/) | Research assistant with web search | [Try it](https://researcher-agent-memori.streamlit.app/) |

---

## Architecture

Memori uses three intelligent agents:
- **Memory Agent** - Extracts entities and relationships using Pydantic
- **Conscious Agent** - Promotes important memories from long-term to short-term
- **Retrieval Agent** - Intelligently searches and injects relevant context

**Database Schema**:
```sql
chat_history          # All conversations
short_term_memory     # Recent context
long_term_memory      # Permanent insights
rules_memory          # User preferences
memory_entities       # Extracted entities
memory_relationships  # Entity connections
```

For detailed architecture documentation, see [docs](https://www.gibsonai.com/docs/memori).

---

## Contributing

We welcome contributions! See [CONTRIBUTING.md](./CONTRIBUTING.md) for guidelines.

---

## Support

- **Documentation**: [https://www.gibsonai.com/docs/memori](https://www.gibsonai.com/docs/memori)
- **Discord**: [https://discord.gg/abD4eGym6v](https://discord.gg/abD4eGym6v)
- **Issues**: [GitHub Issues](https://github.com/GibsonAI/memori/issues)

---

## License

Apache 2.0 - see [LICENSE](./LICENSE)

---

⭐ **Star us on GitHub** to support the project

[![Star History](https://api.star-history.com/svg?repos=GibsonAI/memori&type=date)](https://star-history.com/#GibsonAI/memori)
