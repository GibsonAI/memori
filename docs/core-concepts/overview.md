# Dual Memory Modes System

Memori introduces a revolutionary dual memory system with two distinct modes that can work independently or together to provide intelligent, context-aware AI interactions.

## What are the Dual Memory Modes?

Memori features two complementary memory modes:

### 1. Conscious Ingest Mode (`conscious_ingest=True`)
- **One-shot context injection** at conversation start
- **Persistent essential context** throughout the session
- **Conscious-info labeled memories** automatically transferred to short-term memory
- **Startup processing** - runs once when the system initializes

### 2. Auto Ingest Mode (`auto_ingest=True`)  
- **Real-time context injection** on every LLM call
- **Dynamic memory retrieval** based on current query
- **Intelligent search** to find the most relevant memories
- **Query-specific context** tailored to each user input

### 3. Combined Mode (Both enabled)
- **Maximum intelligence** with both persistent and dynamic context
- **Essential + relevant** memories for comprehensive understanding
- **Optimal performance** for complex, ongoing conversations

## How It Works

### Three-Layer Intelligence

```
┌─────────────────────┐
│ Memory Search Engine│ ← Auto-ingest: Dynamic context per query
├─────────────────────┤
│  Conscious Agent    │ ← Conscious-ingest: Essential context at startup  
├─────────────────────┤
│   Memory Agent      │ ← Processes every conversation with Pydantic models
└─────────────────────┘
```

### The Dual Process

**Conscious Ingest Process**:
1. **System Startup** → Conscious Agent scans for conscious-info labeled memories
2. **One-Shot Transfer** → Essential memories copied to short-term memory  
3. **Session Context** → Persistent context available for entire conversation
4. **No Re-processing** → Context remains fixed until next startup

**Auto Ingest Process**:
1. **Every Query** → Memory Search Engine analyzes user input
2. **Dynamic Search** → Intelligent retrieval from entire memory database
3. **Context Selection** → Up to 5 most relevant memories selected
4. **Real-time Injection** → Context automatically added to LLM call

## Enabling Dual Memory Modes

### Conscious Ingest Only

```python
from memori import Memori

memori = Memori(
    database_connect="sqlite:///my_memory.db",
    conscious_ingest=True,  # Essential context at startup
    openai_api_key="sk-..."  # Required for agents
)

memori.enable()  # Triggers conscious agent startup
```

**What Happens**: Conscious Agent copies all conscious-info labeled memories to short-term memory for persistent context throughout the session.

### Auto Ingest Only

```python
from memori import Memori

memori = Memori(
    database_connect="sqlite:///my_memory.db",
    auto_ingest=True,  # Dynamic context per query
    openai_api_key="sk-..."  # Required for agents
)

# Every LLM call automatically includes relevant context
from litellm import completion

response = completion(
    model="gpt-4o-mini", 
    messages=[{"role": "user", "content": "What are my Python preferences?"}]
)
# Automatically includes relevant memories about Python preferences
```

**What Happens**: Memory Search Engine analyzes each query and injects up to 5 relevant memories in real-time.

### Combined Mode (Maximum Intelligence)

```python
from memori import Memori

memori = Memori(
    database_connect="sqlite:///my_memory.db",
    conscious_ingest=True,  # Essential context at startup
    auto_ingest=True,       # Dynamic context per query  
    openai_api_key="sk-..."  # Required for both agents
)

memori.enable()  # Start both agents
```

**What Happens**: 
- **Startup**: Essential memories transferred to short-term memory
- **Per Query**: Additional relevant memories dynamically retrieved
- **Result**: Both persistent and dynamic context for optimal intelligence  

## Mode Comparison

### When to Use Each Mode

| Feature | Conscious Ingest | Auto Ingest | Combined |
|---------|------------------|-------------|----------|
| **Context Type** | Essential/Persistent | Dynamic/Relevant | Both |
| **Processing** | Once at startup | Every LLM call | Both |
| **Performance** | Fast (minimal overhead) | Real-time | Balanced |
| **Token Usage** | Low | Medium | Higher |
| **Best For** | Persistent identity/preferences | Query-specific context | Maximum intelligence |
| **Use Case** | Personal assistants, role-based agents | Q&A systems, search interfaces | Advanced conversational AI |

### Example Scenarios

**Conscious Ingest**: Perfect for personal assistants that need to remember your core preferences, work style, and essential facts throughout a conversation.

**Auto Ingest**: Ideal for knowledge bases, research assistants, or any system where each query might need different contextual information.

**Combined Mode**: Best for sophisticated AI agents that need both persistent personality/preferences AND dynamic knowledge retrieval.

## Choosing the Right Memory Mode

### Decision Matrix

Use this table to quickly select the optimal mode for your use case:

| Use Case | Recommended Mode | Why |
|----------|------------------|-----|
| **Personal AI Assistant** | Conscious | Stable user context, low latency, consistent personality |
| **Customer Support Bot** | Auto | Diverse customer queries need dynamic history retrieval |
| **Code Completion Copilot** | Conscious | Fast responses, stable user preferences, minimal overhead |
| **Research Assistant** | Combined | Needs both user context AND query-specific knowledge |
| **Multi-User SaaS** | Auto or Combined | Diverse users with varied, changing contexts |
| **RAG Knowledge Base** | Auto | Each query requires different document context |
| **Personal Journaling AI** | Conscious | Core identity/preferences stable, conversations build on them |
| **Tech Support Chatbot** | Combined | Needs user profile + technical documentation |

### Quick Selection Guide

**Choose Conscious Mode (`conscious_ingest=True`) if:**

- Your users have stable preferences/context that rarely change
- You want minimal latency overhead (instant context access)
- Core facts persist across sessions (name, role, preferences)
- Token efficiency is a priority (lower cost)
- Building personal assistants or role-based agents
- Context is small and essential (5-10 key facts)

**Choose Auto Mode (`auto_ingest=True`) if:**

- Each query needs different context from memory
- Your memory database is large and diverse (100+ memories)
- Query topics vary significantly conversation to conversation
- Real-time relevance is more important than speed
- Building Q&A systems or knowledge retrievers
- Users ask about many different topics

**Choose Combined Mode (both enabled) if:**

- You need both persistent identity AND dynamic knowledge
- Token cost is acceptable for better intelligence
- Building sophisticated conversational AI
- User context + query specificity both matter
- Maximum accuracy is priority over performance
- Building enterprise-grade assistants

### Performance Trade-offs

| Metric | Conscious Only | Auto Only | Combined |
|--------|----------------|-----------|----------|
| **Startup Time** | ~50ms (one-time) | Instant | ~50ms (one-time) |
| **Per-Query Overhead** | Instant (~0ms) | ~10-15ms | ~12-18ms |
| **Token Usage per Call** | 150-300 tokens | 200-500 tokens | 300-800 tokens |
| **API Calls Required** | Startup only | Every query + memory agent | Both startup + every query |
| **Memory Accuracy** | Fixed essential context | Dynamic relevant context | Optimal (both) |
| **Best For** | Stable workflows | Dynamic queries | Maximum intelligence |
| **Typical Cost/1000 calls** | $0.05 (minimal) | $0.15-$0.25 | $0.30-$0.40 |

### When to Upgrade from One Mode to Another

**Start with Conscious → Upgrade to Combined when:**

- User's knowledge base grows large (>1,000 memories)
- Queries span multiple domains/projects
- Need both "who the user is" AND "specific query context"
- Users request information from varied past conversations

**Start with Auto → Upgrade to Combined when:**

- Need consistent user personality across sessions
- Want to reduce per-query token usage for common facts
- Users have stable preferences that should persist
- Building assistant with both identity and knowledge

**Start with Combined → Downgrade when:**

- Token costs are too high for your use case
- Latency becomes an issue
- User context is actually stable (go Conscious only)
- Queries are always diverse (go Auto only)

## Memory Categories

Every piece of information gets categorized for intelligent retrieval across both modes:

| Category | Description | Conscious Ingest | Auto Ingest |
|----------|-------------|------------------|-------------|
| **fact** | Objective information, technical details | If labeled conscious-info | High relevance matching |
| **preference** | Personal choices, likes/dislikes | If labeled conscious-info | Preference-based queries |
| **skill** | Abilities, expertise, learning progress | If labeled conscious-info | Skill-related questions |
| **context** | Project info, work environment | If labeled conscious-info | Project-specific queries |
| **rule** | Guidelines, policies, constraints | If labeled conscious-info | Rule/policy questions |

## Context Injection Strategy

### Conscious Ingest Strategy

```python
# At startup
conscious_memories = scan_for_conscious_labels()
transfer_to_short_term_memory(conscious_memories)

# During conversation  
context = get_short_term_memories()  # Always available
inject_into_conversation(context)
```

### Auto Ingest Strategy

```python
# For each user query
user_query = "What are my Python preferences?"
relevant_memories = search_database(query=user_query, limit=5)
context = select_most_relevant(relevant_memories)
inject_into_conversation(context)
```

### Combined Strategy

```python
# Startup + per-query
essential_context = get_short_term_memories()      # Conscious ingest
dynamic_context = search_relevant(user_query)     # Auto ingest
combined_context = merge_contexts(essential_context, dynamic_context)
inject_into_conversation(combined_context)
```

## Examples

### Personal Assistant (Conscious Ingest)

```python
# Set up personal assistant with persistent context
memori = Memori(conscious_ingest=True)

# Label important preferences (one-time setup)
memori.add_memory("I prefer Python and FastAPI for web development", 
                  category="preference", 
                  labels=["conscious-info"])

# Every conversation automatically includes your core preferences
response = completion(
    model="gpt-4",
    messages=[{"role": "user", "content": "Help me choose technologies for a new API"}]
)
# AI automatically knows you prefer Python and FastAPI
```

### Knowledge Q&A (Auto Ingest)

```python
# Set up Q&A system with dynamic context
memori = Memori(auto_ingest=True)

# Build knowledge base through conversations
conversations = [
    "Our authentication system uses JWT tokens",
    "The database runs on PostgreSQL 14",
    "We deploy using Docker containers on AWS ECS"
]

for conv in conversations:
    completion(model="gpt-4", messages=[{"role": "user", "content": conv}])

# Later queries automatically get relevant context
response = completion(
    model="gpt-4",
    messages=[{"role": "user", "content": "How does our authentication work?"}]
)
# Automatically includes JWT token information
```

### Advanced Assistant (Combined Mode)

```python
# Maximum intelligence with both modes
memori = Memori(conscious_ingest=True, auto_ingest=True)

# Essential context (conscious ingest)
memori.add_memory("I'm a senior Python developer at TechCorp", 
                  labels=["conscious-info"])
memori.add_memory("I prefer clean, documented code with type hints", 
                  category="preference", 
                  labels=["conscious-info"])

# Dynamic knowledge base (auto ingest)
memori.add_memory("Currently working on microservices migration project")
memori.add_memory("Using FastAPI, PostgreSQL, and Docker")

# Every query gets both personal context + relevant project info
response = completion(
    model="gpt-4",
    messages=[{"role": "user", "content": "Review this API endpoint code"}]
)
# AI knows: You're a senior dev, prefer clean code, working on microservices with FastAPI
```

## Manual Control

### Memory Management

```python
# Add conscious-info labeled memories
memori.add_memory(
    "I'm a Python developer who prefers minimal dependencies",
    category="preference",
    labels=["conscious-info"]  # Will be picked up by conscious ingest
)

# Test auto-ingest context retrieval  
context = memori._get_auto_ingest_context("What are my coding preferences?")
print(f"Retrieved {len(context)} relevant memories")

# Check short-term memory (conscious ingest)
short_term = memori.db_manager.get_short_term_memories(namespace=memori.namespace)
print(f"Short-term memories: {len(short_term)}")
```

### Mode Testing

```python
# Test conscious ingest
if memori.conscious_ingest:
    print("Conscious ingest enabled - essential context at startup")
    
# Test auto ingest  
if memori.auto_ingest:
    print("Auto ingest enabled - dynamic context per query")
    context = memori._get_auto_ingest_context("test query")
    print(f"Auto-ingest working: {len(context)} results")

# Memory statistics
stats = memori.get_memory_stats()
print(f"Total conversations: {stats['total_conversations']}")
```

### Memory Search

```python
# Search specific categories (works with both modes)
preferences = memori.search_memories_by_category("preference", limit=5)
facts = memori.search_memories_by_category("fact", limit=5)
skills = memori.search_memories_by_category("skill", limit=5)

# Search by keywords
python_memories = memori.search_memories(query="Python", limit=10)

# Get all conscious-info labeled memories
conscious_memories = memori.search_memories_by_labels(["conscious-info"])
```

## Configuration Options

### Provider Configuration

Both modes work with any LLM provider:

```python
from memori.core.providers import ProviderConfig

# Azure OpenAI
azure_config = ProviderConfig.from_azure(
    api_key="your-azure-key",
    azure_endpoint="https://your-resource.openai.azure.com/",
    azure_deployment="gpt-4o",
    api_version="2024-02-01"
)

# Custom endpoint (Ollama, etc.)
custom_config = ProviderConfig.from_custom(
    base_url="http://localhost:11434/v1",
    api_key="not-required",
    model="llama3"
)

memori = Memori(
    database_connect="sqlite:///memory.db",
    provider_config=azure_config,  # Works with both modes
    conscious_ingest=True,
    auto_ingest=True
)
```

### Mode-Specific Settings

```python
# Conscious ingest only
memori_conscious = Memori(
    conscious_ingest=True,
    verbose=True  # See startup processing
)

# Auto ingest only
memori_auto = Memori(
    auto_ingest=True, 
    verbose=True  # See per-query processing
)

# Combined with namespacing
memori_combined = Memori(
    conscious_ingest=True,
    auto_ingest=True,
    namespace="my_project",  # Separate memory space
    verbose=True  # See all activity
)
```

### Environment Configuration

```python
# Using environment variables
import os
os.environ['OPENAI_API_KEY'] = 'sk-...'

# Configuration file support
from memori.config import ConfigManager

config = ConfigManager()
memori = Memori.from_config(config, conscious_ingest=True, auto_ingest=True)
```

## Performance & Token Usage

### Efficiency Features

- **Structured Outputs**: Pydantic models reduce parsing overhead
- **Smart Context Limits**: Automatic limits prevent token overflow (5 memories max for auto-ingest)
- **Mode Selection**: Choose the right mode for your performance needs
- **Provider Flexibility**: Use cost-effective models like GPT-4o-mini
- **Recursion Protection**: Auto-ingest prevents infinite loops automatically

### Token Optimization

**Traditional Context Injection**:
```
2000+ tokens of conversation history
```

**Conscious Ingest Mode**:
```
100-300 tokens of essential facts (one-time at startup)
```

**Auto Ingest Mode**:
```
200-500 tokens of relevant context (per query)
```

**Combined Mode**:
```
300-800 tokens of essential + relevant context (optimal intelligence)
```

### Performance Comparison

| Metric | Conscious Only | Auto Only | Combined |
|--------|----------------|-----------|----------|
| **Startup Time** | Fast | Instant | Fast |
| **Per-Query Time** | Instant | Fast | Fast |
| **Token Usage** | Low | Medium | Higher |
| **API Calls** | Minimal | Per query | Both |
| **Memory Accuracy** | Fixed context | Dynamic context | Optimal |

## Monitoring

### Log Messages

With `verbose=True`, you'll see different messages for each mode:

**Conscious Ingest**:
```
[CONSCIOUS] Starting conscious ingest at startup
[CONSCIOUS] Found 3 conscious-info labeled memories  
[CONSCIOUS] Copied 3 memories to short-term memory
[CONSCIOUS] Conscious ingest complete
```

**Auto Ingest**:
```
[AUTO-INGEST] Starting context retrieval for query: 'Python preferences?'
[AUTO-INGEST] Direct database search returned 4 results
[AUTO-INGEST] Context injection successful: 4 memories
```

**Memory Processing**:
```
[MEMORY] Processing conversation: "I prefer FastAPI"
[MEMORY] Categorized as 'preference', importance: 0.8
[MEMORY] Extracted entities: {'technologies': ['FastAPI']}
```

### Health Checks

```python
# Check mode status
print(f"Conscious ingest: {memori.conscious_ingest}")
print(f"Auto ingest: {memori.auto_ingest}")

# Test conscious ingest
if memori.conscious_ingest:
    short_term = memori.db_manager.get_short_term_memories(namespace=memori.namespace)
    print(f"Short-term memories loaded: {len(short_term)}")

# Test auto ingest
if memori.auto_ingest:
    context = memori._get_auto_ingest_context("test query")
    print(f"Auto-ingest functional: {len(context)} results")

# Memory statistics
stats = memori.get_memory_stats()
for key, value in stats.items():
    print(f"{key}: {value}")
```

## Troubleshooting

### Common Issues

**No API Key**
```
Memory Agent initialization failed: No API key provided
```
Solution: Set `OPENAI_API_KEY` environment variable or use provider configuration

**Auto-Ingest No Results**
```
Auto-ingest: Direct database search returned 0 results
```
Solution: Build up more memory data through conversations

**Conscious Ingest No Memories**
```
ConsciouscAgent: No conscious-info memories found
```
Solution: Label important memories with conscious-info or add more conversations

**Recursion Protection Triggered**
```
Auto-ingest: Recursion detected, using direct database search
```
Solution: This is normal behavior to prevent infinite loops - the system continues working

### Debug Commands

```python
# Mode verification
print(f"Conscious ingest: {memori.conscious_ingest}")
print(f"Auto ingest: {memori.auto_ingest}")
print(f"Provider: {memori.provider_config.api_type if memori.provider_config else 'Default'}")

# Test memory agents
try:
    # Test conscious ingest
    if memori.conscious_ingest:
        short_term = memori.db_manager.get_short_term_memories(namespace=memori.namespace)
        print(f"Conscious ingest working: {len(short_term)} short-term memories")
    
    # Test auto ingest
    if memori.auto_ingest:
        context = memori._get_auto_ingest_context("test preferences")
        print(f"Auto ingest working: {len(context)} context memories")
        
    # Test memory processing
    if hasattr(memori, 'memory_agent'):
        print("Memory agent available and configured")
        
except Exception as e:
    print(f"Agent test failed: {e}")

# Memory statistics
stats = memori.get_memory_stats()
for key, value in stats.items():
    print(f"{key}: {value}")
```

## Best Practices

### Mode Selection

1. **Choose Conscious Ingest** for:
   - Personal assistants that need consistent personality
   - Role-based agents with fixed preferences
   - Applications where core context rarely changes
   - Scenarios prioritizing performance and low token usage

2. **Choose Auto Ingest** for:
   - Q&A systems with dynamic knowledge bases
   - Research assistants needing query-specific context
   - Applications where context varies significantly per query
   - Systems requiring real-time memory retrieval

3. **Choose Combined Mode** for:
   - Advanced conversational AI requiring both personality and knowledge
   - Enterprise assistants needing persistent identity + dynamic expertise
   - Applications where maximum intelligence is worth higher token costs
   - Complex multi-domain systems

### For Better Results

1. **Label Strategically**: Use conscious-info labels for truly essential, persistent information
2. **Be Specific**: Share clear information about yourself, preferences, and projects
3. **Be Consistent**: Use consistent terminology for technologies and concepts
4. **Build Gradually**: Let the system learn through natural conversation
5. **Monitor Performance**: Use verbose mode to understand system behavior

### For Developers

1. **Provider Configuration**: Use ProviderConfig for flexible LLM provider setup
2. **API Key Security**: Always use environment variables for API keys
3. **Error Handling**: Implement graceful degradation when agents fail
4. **Performance Monitoring**: Track token usage and response times
5. **Testing**: Test with different memory modes and conversation patterns
6. **Resource Planning**: Consider API costs when choosing between modes

## Comparison

### Without Dual Memory Modes

```python
# Traditional approach - manual context management
memori = Memori()  # No intelligent context injection

messages = [
    {"role": "system", "content": "User prefers Python, FastAPI, PostgreSQL..."},
    {"role": "user", "content": "Help me build an API"}
]
# Manual context specification required every time
```

### With Conscious Ingest

```python
# Persistent context approach
memori = Memori(conscious_ingest=True)

# Label essential preferences once
memori.add_memory("I prefer Python, FastAPI, PostgreSQL", 
                  labels=["conscious-info"])

# All future conversations include this context automatically
messages = [{"role": "user", "content": "Help me build an API"}]
# System knows: Python, FastAPI, PostgreSQL preferences
```

### With Auto Ingest

```python
# Dynamic context approach
memori = Memori(auto_ingest=True)

# Build knowledge through conversations
conversations = [
    "I'm working on a microservices project",
    "We use Docker containers for deployment", 
    "Our main database is PostgreSQL"
]

# Every query gets relevant context
messages = [{"role": "user", "content": "How should we deploy the API?"}]
# System automatically retrieves: Docker, microservices info
```

### With Combined Mode

```python
# Maximum intelligence approach
memori = Memori(conscious_ingest=True, auto_ingest=True)

# Essential context (conscious) + dynamic context (auto)
messages = [{"role": "user", "content": "Review this database query"}]
# System knows: Your preferences (conscious) + current project details (auto)
```

## Getting Started

Ready to try conscious ingestion? Start with our examples:

- [Examples](https://github.com/GibsonAI/memori/tree/main/examples) - Explore more examples
- [Framework Integrations](https://github.com/GibsonAI/memori/tree/main/examples/integrations) - See how Memori works seamlessly with popular AI Agent frameworks
- [Demos](https://github.com/GibsonAI/memori/tree/main/demos) - Explore Memori's capabilities through these demos

The future of AI memory is here - no more repeating yourself!