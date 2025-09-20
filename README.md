[![GibsonAI](https://github.com/user-attachments/assets/878e341b-5a93-4489-a398-abeca91b6b11)](https://gibsonai.com/)

# memori

<p align="center">
  <strong>Open-Source Memory Engine for LLMs, AI Agents & Multi-Agent Systems</strong>
</p>

<p align="center">
  <i>Make LLMs context-aware with human-like memory, dual-mode retrieval, and automatic context injection.</i>
</p>

<p align="center">
  <a href="https://memori.gibsonai.com/docs">Learn more</a>
  ·
  <a href="https://www.gibsonai.com/discord">Join Discord</a>
</p>

<p align="center">
  <a href="https://badge.fury.io/py/memorisdk">
    <img src="https://badge.fury.io/py/memori.svg" alt="PyPI version">
  </a>
  <a href="https://pepy.tech/projects/memorisdk">
    <img src="https://static.pepy.tech/badge/memorisdk" alt="Downloads">
  </a>
  <a href="https://opensource.org/licenses/MIT">
    <img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License: MIT">
  </a>
  <a href="https://www.python.org/downloads/">
    <img src="https://img.shields.io/badge/python-3.8+-blue.svg" alt="Python 3.8+">
  </a>
</p>

---

## 🎯 Philosophy

- **Second-memory for all your LLM work** - Never repeat context again
- **Dual-mode memory injection** - Conscious short-term memory + Auto intelligent search
- **Flexible database connections** - SQLite, PostgreSQL, MySQL support  
- **Pydantic-based intelligence** - Structured memory processing with validation
- **Simple, reliable architecture** - Just works out of the box

## ⚡ Quick Start

Install Memori:

```bash
pip install memorisdk
```

### Example with OpenAI

1. Install OpenAI:

```bash
pip install openai
```

2. Set OpenAI API Key:

```bash
export OPENAI_API_KEY="sk-your-openai-key-here"
```

3. Run this Python script:

```python
from memori import Memori
from openai import OpenAI

# Initialize OpenAI client
openai_client = OpenAI()

# Initialize memory
memori = Memori(conscious_ingest=True)
memori.enable()

print("=== First Conversation - Establishing Context ===")
response1 = openai_client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{
        "role": "user", 
        "content": "I'm working on a Python FastAPI project"
    }]
)

print("Assistant:", response1.choices[0].message.content)
print("\n" + "="*50)
print("=== Second Conversation - Memory Provides Context ===")

response2 = openai_client.chat.completions.create(
    model="gpt-4o-mini", 
    messages=[{
        "role": "user",
        "content": "Help me add user authentication"
    }]
)
print("Assistant:", response2.choices[0].message.content)
print("\n💡 Notice: Memori automatically knows about your FastAPI Python project!")
```

---

> By default, Memori uses in-memory SQLite database. Get **FREE** serverless database instance in [GibsonAI](https://app.gibsonai.com/signup) platform.

**🚀 Ready to explore more?**
- [📖 Examples](#examples) - Basic usage patterns and code samples
- [🔌 Framework Integrations](#framework-integrations) - LangChain, Agno & CrewAI examples  
- [🎮 Interactive Demos](#interactive-demos) - Live applications & tutorials

---

## 🧠 How It Works

### 1. **Universal Recording**
```python
office_work.enable()  # Records ALL LLM conversations automatically
```

### 2. **Intelligent Processing**
- **Entity Extraction**: Extracts people, technologies, projects
- **Smart Categorization**: Facts, preferences, skills, rules
- **Pydantic Validation**: Structured, type-safe memory storage

### 3. **Dual Memory Modes**

#### **🧠 Conscious Mode** - Short-Term Working Memory
```python
conscious_ingest=True  # One-shot short-term memory injection
```
- **At Startup**: Conscious agent analyzes long-term memory patterns
- **Memory Promotion**: Moves essential conversations to short-term storage
- **One-Shot Injection**: Injects working memory once at conversation start
- **Like Human Short-Term Memory**: Names, current projects, preferences readily available

#### **🔍 Auto Mode** - Dynamic Database Search
```python
auto_ingest=True  # Continuous intelligent memory retrieval
```
- **Every LLM Call**: Retrieval agent analyzes user query intelligently
- **Full Database Search**: Searches through entire memory database
- **Context-Aware**: Injects relevant memories based on current conversation
- **Performance Optimized**: Caching, async processing, background threads

## 🧠 Memory Modes Explained

### **Conscious Mode** - Short-Term Working Memory
```python
# Mimics human conscious memory - essential info readily available
memori = Memori(
    database_connect="sqlite:///my_memory.db",
    conscious_ingest=True,  # 🧠 Short-term working memory
    openai_api_key="sk-..."
)
```

**How Conscious Mode Works:**
1. **At Startup**: Conscious agent analyzes long-term memory patterns
2. **Essential Selection**: Promotes 5-10 most important conversations to short-term
3. **One-Shot Injection**: Injects this working memory once at conversation start
4. **No Repeats**: Won't inject again during the same session

### **Auto Mode** - Dynamic Intelligent Search
```python
# Searches entire database dynamically based on user queries
memori = Memori(
    database_connect="sqlite:///my_memory.db", 
    auto_ingest=True,  # 🔍 Smart database search
    openai_api_key="sk-..."
)
```

**How Auto Mode Works:**
1. **Every LLM Call**: Retrieval agent analyzes user input
2. **Query Planning**: Uses AI to understand what memories are needed
3. **Smart Search**: Searches through entire database (short-term + long-term)
4. **Context Injection**: Injects 3-5 most relevant memories per call

### **Combined Mode** - Best of Both Worlds
```python
# Get both working memory AND dynamic search
memori = Memori(
    conscious_ingest=True,  # Working memory once
    auto_ingest=True,       # Dynamic search every call
    openai_api_key="sk-..."
)
```

### **Intelligence Layers:**

1. **Memory Agent** - Processes every conversation with Pydantic structured outputs
2. **Conscious Agent** - Analyzes patterns, promotes long-term → short-term memories
3. **Retrieval Agent** - Intelligently searches and selects relevant context

### **What gets prioritized in Conscious Mode:**
- 👤 **Personal Identity**: Your name, role, location, basic info
- ❤️ **Preferences & Habits**: What you like, work patterns, routines
- 🛠️ **Skills & Tools**: Technologies you use, expertise areas
- 📊 **Current Projects**: Ongoing work, learning goals
- 🤝 **Relationships**: Important people, colleagues, connections
- 🔄 **Repeated References**: Information you mention frequently

## 🗄️ Memory Types

| Type | Purpose | Example | Auto-Promoted |
|------|---------|---------|---------------|
| **Facts** | Objective information | "I use PostgreSQL for databases" | ✅ High frequency |
| **Preferences** | User choices | "I prefer clean, readable code" | ✅ Personal identity |
| **Skills** | Abilities & knowledge | "Experienced with FastAPI" | ✅ Expertise areas |
| **Rules** | Constraints & guidelines | "Always write tests first" | ✅ Work patterns |
| **Context** | Session information | "Working on e-commerce project" | ✅ Current projects |

## 🔧 Configuration

### Simple Setup
```python
from memori import Memori

# Conscious mode - Short-term working memory
memori = Memori(
    database_connect="sqlite:///my_memory.db",
    template="basic", 
    conscious_ingest=True,  # One-shot context injection
    openai_api_key="sk-..."
)

# Auto mode - Dynamic database search
memori = Memori(
    database_connect="sqlite:///my_memory.db",
    auto_ingest=True,  # Continuous memory retrieval
    openai_api_key="sk-..."
)

# Combined mode - Best of both worlds
memori = Memori(
    conscious_ingest=True,  # Working memory + 
    auto_ingest=True,       # Dynamic search
    openai_api_key="sk-..."
)
```

### Advanced Configuration
```python
from memori import Memori, ConfigManager

# Load from memori.json or environment
config = ConfigManager()
config.auto_load()

memori = Memori()
memori.enable()
```

Create `memori.json`:
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

## 🔌 Universal Integration

Works with **ANY** LLM library:

```python
memori.enable()  # Enable universal recording

# OpenAI
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

## 🛠️ Memory Management

### **Automatic Background Analysis**
```python
# Automatic analysis every 6 hours (when conscious_ingest=True)
memori.enable()  # Starts background conscious agent

# Manual analysis trigger
memori.trigger_conscious_analysis()

# Get essential conversations
essential = memori.get_essential_conversations(limit=5)
```

### **Memory Retrieval Tools**
```python
from memori.tools import create_memory_tool

# Create memory search tool for your LLM
memory_tool = create_memory_tool(memori)

# Use in function calling
tools = [memory_tool]
completion(model="gpt-4", messages=[...], tools=tools)
```

### **Context Control**
```python
# Get relevant context for a query
context = memori.retrieve_context("Python testing", limit=5)
# Returns: 3 essential + 2 specific memories

# Search by category
skills = memori.search_memories_by_category("skill", limit=10)

# Get memory statistics
stats = memori.get_memory_stats()
```

## 📋 Database Schema

```sql
-- Core tables created automatically
chat_history        # All conversations
short_term_memory   # Recent context (expires)
long_term_memory    # Permanent insights  
rules_memory        # User preferences
memory_entities     # Extracted entities
memory_relationships # Entity connections
```

## 📁 Project Structure

```
memori/
├── core/           # Main Memori class, database manager
├── agents/         # Memory processing with Pydantic  
├── database/       # SQLite/PostgreSQL/MySQL support
├── integrations/   # LiteLLM, OpenAI, Anthropic
├── config/         # Configuration management
├── utils/          # Helpers, validation, logging
└── tools/          # Memory search tools
```

## Examples

- **[Basic Usage](./examples/basic_usage.py)** - Simple memory setup with conscious ingestion
- **[Personal Assistant](./examples/personal_assistant.py)** - AI assistant with intelligent memory
- **[Memory Retrieval](./memory_retrival_example.py)** - Function calling with memory tools
- **[Advanced Config](./examples/advanced_config.py)** - Production configuration
- **[Interactive Demo](./memori_example.py)** - Live conscious ingestion showcase
- **[Simple Multi-User](./examples/multiple-users/simple_multiuser.py)** - Basic demonstration of user memory isolation with namespaces
- **[FastAPI Multi-User App](./examples/multiple-users/fastapi_multiuser_app.py)** - Full-featured REST API with Swagger UI for testing multi-user functionality

## Framework Integrations

Memori works seamlessly with popular AI frameworks:

| Framework | Description | Example |
|-----------|-------------|---------|
| [AgentOps](./examples/integrations/agentops_example.py) | Track and monitor Memori memory operations with comprehensive observability | Memory operation tracking with AgentOps analytics |
| [Agno](./examples/integrations/agno_example.py) | Memory-enhanced agent framework integration with persistent conversations | Simple chat agent with memory search |
| [AWS Strands](./examples/integrations/aws_strands_example.py) | Professional development coach with Strands SDK and persistent memory | Career coaching agent with goal tracking |
| [Azure AI Foundry](./examples/integrations/azure_ai_foundry_example.py) | Azure AI Foundry agents with persistent memory across conversations | Enterprise AI agents with Azure integration |
| [CamelAI](./examples/integrations/camelai_example.py) | Multi-agent communication framework with automatic memory recording and retrieval | Memory-enhanced chat agents with conversation continuity |
| [CrewAI](./examples/integrations/crewai_example.py) | Multi-agent system with shared memory across agent interactions | Collaborative agents with memory |
| [Digital Ocean AI](./examples/integrations/digital_ocean_example.py) | Memory-enhanced customer support using Digital Ocean's AI platform | Customer support assistant with conversation history |
| [LangChain](./examples/integrations/langchain_example.py) | Enterprise-grade agent framework with advanced memory integration | AI assistant with LangChain tools and memory |
| [OpenAI Agent](./examples/integrations/openai_agent_example.py) | Memory-enhanced OpenAI Agent with function calling and user preference tracking | Interactive assistant with memory search and user info storage |
| [Swarms](./examples/integrations/swarms_example.py) | Multi-agent system framework with persistent memory capabilities | Memory-enhanced Swarms agents with auto/conscious ingestion |

## Interactive Demos

Explore Memori's capabilities through these interactive demonstrations:

| Title | Description | Tools Used | Live Demo |
|------------|-------------|------------|-----------|
| 🌟 [Personal Diary Assistant](./demos/personal_diary_assistant/) | A comprehensive diary assistant with mood tracking, pattern analysis, and personalized recommendations. | Streamlit, LiteLLM, OpenAI, SQLite | [Run Demo](https://personal-diary-assistant.streamlit.app/) |
| 🌍 [Travel Planner Agent](./demos/travel_planner/) | Intelligent travel planning with CrewAI agents, real-time web search, and memory-based personalization. Plans complete itineraries with budget analysis. | CrewAI, Streamlit, OpenAI, SQLite |  |
| 🧑‍🔬 [Researcher Agent](./demos/researcher_agent/) | Advanced AI research assistant with persistent memory, real-time web search, and comprehensive report generation. Builds upon previous research sessions. | Agno, Streamlit, OpenAI, ExaAI, SQLite | [Run Demo](https://researcher-agent-memori.streamlit.app/) |

## 🤝 Contributing

- See [CONTRIBUTING.md](./CONTRIBUTING.md) for development setup and guidelines.
- Community: [Discord](https://www.gibsonai.com/discord)

## 📄 License

MIT License - see [LICENSE](./LICENSE) for details.

---

*Made for developers who want their AI agents to remember and learn*
