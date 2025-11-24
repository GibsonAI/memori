[![Memori Labs](https://s3.us-east-1.amazonaws.com/images.memorilabs.ai/banner.png)](https://memorilabs.ai/)

<p align="center">
  <strong>An open-source SQL-Native memory engine for AI

</strong>
</p>

<p align="center">
  <i>One line of code to give any LLM persistent, queryable memory using standard SQL databases</i>
</p>
<p align="center">
  <a href="https://trendshift.io/repositories/15418">
    <img src="https://trendshift.io/_next/image?url=https%3A%2F%2Ftrendshift.io%2Fapi%2Fbadge%2Frepositories%2F15418&w=640&q=75" alt="GibsonAI%2FMemori | Trendshif">
  </a>
</p>

<p align="center">
  <a href="https://badge.fury.io/py/memorisdk">
    <img src="https://badge.fury.io/py/memorisdk.svg" alt="PyPI version">
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

<p align="center">
  <a href="https://github.com/GibsonAI/memori/stargazers">
    <img src="https://img.shields.io/badge/⭐%20Give%20a%20Star-Support%20the%20project-orange?style=for-the-badge" alt="Give a Star">
  </a>
</p>

---

## What is Memori

Memori enables any LLM to remember conversations, learn from interactions, and maintain context across sessions with a single line: `memori.enable()`. Memory is stored in standard SQL databases (SQLite, PostgreSQL, MySQL) that you fully own and control.

**Why Memori?**
- **One-line integration** - Works with OpenAI, Anthropic, LiteLLM, LangChain, and any LLM framework
- **SQL-native storage** - Portable, queryable, and auditable memory in databases you control
- **80-90% cost savings** - No expensive vector databases required
- **Zero vendor lock-in** - Export your memory as SQLite and move anywhere
- **Intelligent memory** - Automatic entity extraction, relationship mapping, and context prioritization

[Documentation](https://memorilabs.ai/docs) | [Examples](#examples) | [Discord](https://discord.gg/abD4eGym6v)

## Memori v3 coming soon

We’re opening a small private beta group for **Memori v3**. If you want to know more and get early access to the new memory fabric for enterprise AI, join our [beta testing program here](https://github.com/GibsonAI/Memori/discussions/176).

---

## Quick Start

```bash
pip install memorisdk
```

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


---

## Database Support

Memori works with any SQL database you already use:

| Database | Connection String Example |
|----------|--------------------------|
| **SQLite** | `sqlite:///my_memory.db` |
| **PostgreSQL** | `postgresql://user:pass@localhost/memori` |
| **MySQL** | `mysql://user:pass@localhost/memori` |
| **Neon** | `postgresql://user:pass@ep-*.neon.tech/memori` |
| **Supabase** | `postgresql://postgres:pass@db.*.supabase.co/postgres` |

---

## LLM Framework Support

Works with any LLM framework through LiteLLM's native callback system:

| Framework | Status | Usage |
|-----------|--------|-------|
| **OpenAI** | ✓ Native | `from openai import OpenAI` |
| **Anthropic** | ✓ Native | `from anthropic import Anthropic` |
| **LiteLLM** | ✓ Native | `from litellm import completion` |
| **LangChain** | ✓ Supported | Use with LiteLLM integration |
| **Azure OpenAI** | ✓ Supported | Configure with `ProviderConfig.from_azure()` |
| **100+ Models** | ✓ Supported | Any LiteLLM-compatible provider |

---

## Configuration

### Persistent Storage

```python
from memori import Memori

memori = Memori(
    database_connect="postgresql://user:pass@localhost/memori",
    conscious_ingest=True,  # Short-term working memory
    auto_ingest=True,       # Dynamic search per query
    openai_api_key="sk-..."
)
memori.enable()
```

### Memory Modes

**Conscious Mode** - One-shot working memory injection
```python
memori = Memori(conscious_ingest=True)
```

**Auto Mode** - Dynamic search per query
```python
memori = Memori(auto_ingest=True)
```

**Combined Mode** - Best of both
```python
memori = Memori(conscious_ingest=True, auto_ingest=True)
```

### Using ConfigManager

```python
from memori import Memori, ConfigManager

config = ConfigManager()
config.auto_load()  # Loads from environment or config files

memori = Memori()
memori.enable()
```

Set environment variables:
```bash
export MEMORI_DATABASE__CONNECTION_STRING="postgresql://..."
export MEMORI_AGENTS__OPENAI_API_KEY="sk-..."
export MEMORI_MEMORY__NAMESPACE="production"
```

---

## Architecture Overview

Memori works by **intercepting** LLM calls - injecting context before the call and recording after:

```mermaid
graph LR
    A[Your App] -->|1. client.chat.completions.create| B[Memori Interceptor]
    B -->|2. Get Context| C[(SQL Database)]
    C -->|3. Relevant Memories| B
    B -->|4. Inject Context + Call| D[OpenAI/Anthropic/etc]
    D -->|5. Response| B
    B -->|6. Extract & Store| C
    B -->|7. Return Response| A

    E[Conscious Agent] -.->|Background: Analyze & Promote| C
```

### How It Works

**Pre-Call (Context Injection)**

1. Your app calls `client.chat.completions.create(messages=[...])`
2. Memori intercepts the call transparently
3. **Retrieval Agent** (auto mode) or **Conscious Agent** (conscious mode) retrieves relevant memories
4. Context injected into messages before sending to the LLM provider

**Post-Call (Recording)**

5. LLM provider returns response
6. **Memory Agent** extracts entities, categorizes (facts, preferences, skills, rules, context)
7. Conversation stored in SQL database with full-text search indexes
8. Original response returned to your app

**Background (every 6 hours)**

- **Conscious Agent** analyzes patterns and promotes essential memories from long-term to short-term storage

For detailed architecture documentation, see [docs/architecture.md](https://memorilabs.ai/docs/open-source/architecture).

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

---

## Framework Integrations

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

---

## Interactive Demos

| Demo | Description | Live |
|------|-------------|------|
| [Personal Diary](./demos/personal_diary_assistant/) | Mood tracking and pattern analysis | [Try it](https://personal-diary-assistant.streamlit.app/) |
| [Researcher](./demos/researcher_agent/) | Research assistant with web search | [Try it](https://researcher-agent-memori.streamlit.app/) |

---

## Contributing

We welcome contributions from the community! Please see our [Contributing Guidelines](./CONTRIBUTING.md) for details on:

- Setting up your development environment
- Code style and standards
- Submitting pull requests
- Reporting issues

---

## Support

- **Documentation**: [https://memorilabs.ai/docs](https://memorilabs.ai/docs)
- **Discord**: [https://discord.gg/abD4eGym6v](https://discord.gg/abD4eGym6v)
- **Issues**: [GitHub Issues](https://github.com/GibsonAI/memori/issues)

---

## License

Apache 2.0 - see [LICENSE](./LICENSE)

---

**Star us on GitHub** to support the project

[![Star History](https://api.star-history.com/svg?repos=GibsonAI/memori&type=date)](https://star-history.com/#GibsonAI/memori)
