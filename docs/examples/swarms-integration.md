# Swarms Framework Integration

A comprehensive guide to integrating Memori with the [Swarms](https://github.com/kyegomez/swarms) framework for memory-enhanced multi-agent systems.

## Overview

The Swarms framework provides a powerful foundation for building multi-agent systems. By integrating Memori, you can add persistent memory capabilities to your Swarms agents, enabling them to:

- **Remember conversations** across sessions
- **Learn user preferences** and adapt behavior accordingly
- **Maintain context** in long-running agent interactions
- **Share memory** between different agents in the same system

## Quick Start

### Installation

```bash
# Install required dependencies
pip install memorisdk swarms python-dotenv
```

### Basic Setup

```python
from swarms import Agent
from memori import Memori, create_memory_tool

# Initialize Memori memory system
swarms_memory = Memori(
    database_connect="sqlite:///swarms_memory.db",
    auto_ingest=True,        # Enable automatic ingestion
    conscious_ingest=True,   # Enable conscious ingestion
    verbose=False,           # Disable verbose logging
)

# Enable memory recording
swarms_memory.enable()

# Create Swarms agent
agent = Agent(
    model_name="gpt-4o",     # Specify the LLM
    system_prompt="You are an AI assistant with memory capabilities.",
    max_loops="auto",        # Set the number of interactions
    interactive=True,        # Enable interactive mode for real-time feedback
)

# Start conversation
agent.run("What is my name?")
```

## Configuration Options

### Memory Settings

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `database_connect` | str | `"sqlite:///memory.db"` | Database connection string |
| `auto_ingest` | bool | `True` | Enable automatic memory retrieval |
| `conscious_ingest` | bool | `True` | Enable conscious memory promotion |
| `verbose` | bool | `False` | Enable detailed logging |
| `namespace` | str | `None` | Memory namespace for isolation |

### Agent Configuration

| Parameter | Type | Description |
|-----------|------|-------------|
| `model_name` | str | LLM model (e.g., "gpt-4o", "gpt-4o-mini") |
| `system_prompt` | str | System prompt for the agent |
| `max_loops` | str/int | Number of reasoning loops ("auto" for dynamic) |
| `interactive` | bool | Enable interactive conversation mode |

## Advanced Examples

### Multi-Agent System with Shared Memory

```python
from swarms import Agent
from memori import Memori, create_memory_tool

# Shared memory system for all agents
shared_memory = Memori(
    database_connect="sqlite:///multi_agent_memory.db",
    conscious_ingest=True,
    auto_ingest=True,
    namespace="multi_agent_system",
    verbose=False
)

shared_memory.enable()

# Create specialized agents
research_agent = Agent(
    model_name="gpt-4o",
    system_prompt="You are a research specialist. Remember findings and sources.",
    max_loops=5,
    interactive=False
)

writing_agent = Agent(
    model_name="gpt-4o",
    system_prompt="You are a writing specialist. Remember style preferences and feedback.",
    max_loops=3,
    interactive=False
)

# Agents share the same memory system automatically
research_result = research_agent.run("Research the latest AI trends")
writing_result = writing_agent.run("Write a summary based on recent research")
```

### Custom Memory Tools Integration

```python
from swarms import Agent
from memori import Memori, create_memory_tool

# Initialize memory system
memory_system = Memori(
    database_connect="sqlite:///custom_tools_memory.db",
    conscious_ingest=True,
    auto_ingest=True,
    verbose=False
)

memory_system.enable()

# Create memory search tool
memory_tool = create_memory_tool(memory_system)

# Define custom agent with memory capabilities
agent = Agent(
    model_name="gpt-4o",
    system_prompt="""You are an AI assistant with memory capabilities.
    
    When users ask about previous conversations or information,
    use your memory to provide accurate, contextual responses.
    
    Available capabilities:
    - Remember all conversations and context
    - Search through past interactions
    - Provide personalized responses based on history""",
    max_loops=10,
    interactive=True,
    tools=[memory_tool]  # Add memory tool to agent's toolkit
)

```

## Memory Modes

### Conscious Mode
Promotes important memories to short-term storage for immediate access:

```python
memory_system = Memori(
    conscious_ingest=True,  # Enable conscious memory promotion
    auto_ingest=False,      # Disable automatic search
    database_connect="sqlite:///conscious_memory.db"
)
```

### Auto Mode
Dynamically searches memory database based on user queries:

```python
memory_system = Memori(
    conscious_ingest=False,  # Disable conscious promotion
    auto_ingest=True,        # Enable automatic memory search
    database_connect="sqlite:///auto_memory.db"
)
```

### Combined Mode (Recommended)
Uses both conscious promotion and dynamic search:

```python
memory_system = Memori(
    conscious_ingest=True,   # Short-term working memory
    auto_ingest=True,        # Dynamic memory search
    database_connect="sqlite:///combined_memory.db"
)
```

## Database Configuration

### SQLite (Default)
```python
memory_system = Memori(
    database_connect="sqlite:///swarms_memory.db"
)
```

### PostgreSQL
```python
memory_system = Memori(
    database_connect="postgresql://user:password@localhost/swarms_memory"
)
```

### MySQL
```python
memory_system = Memori(
    database_connect="mysql://user:password@localhost/swarms_memory"
)
```

## Best Practices

### 1. **Namespace Isolation**
Use namespaces to separate memory for different use cases:

```python
# Separate namespaces for different projects
project_a_memory = Memori(namespace="project_a")
project_b_memory = Memori(namespace="project_b")
```

### 2. **Memory Management**
Monitor and manage memory growth:

```python
# Get memory statistics
stats = memory_system.get_memory_stats()
print(f"Total memories: {stats['total_memories']}")
print(f"Memory categories: {stats['categories']}")

# Trigger conscious analysis manually
memory_system.trigger_conscious_analysis()
```

### 3. **Error Handling**
Implement robust error handling:

```python
try:
    memory_system = Memori(
        database_connect="sqlite:///swarms_memory.db",
        conscious_ingest=True,
        auto_ingest=True
    )
    memory_system.enable()
except Exception as e:
    print(f"Memory initialization failed: {e}")
    # Fallback to non-memory mode
```

### 4. **Performance Optimization**
Configure for optimal performance:

```python
memory_system = Memori(
    database_connect="sqlite:///swarms_memory.db",
    conscious_ingest=True,  # For frequently accessed info
    auto_ingest=True,       # For dynamic retrieval
    verbose=False,          # Reduce logging overhead
    background_processing=True  # Enable background tasks
)
```

## Troubleshooting

### Common Issues

**1. Memory not persisting between sessions**
- Ensure `memory_system.enable()` is called
- Check database file permissions and path
- Verify namespace consistency

**2. Poor memory retrieval accuracy**
- Increase memory context size
- Use more descriptive conversation content
- Enable both conscious and auto ingestion modes

**3. Performance issues**
- Use SQLite for development, PostgreSQL for production
- Implement proper indexing for large datasets
- Enable background processing

### Debug Mode

Enable verbose logging for troubleshooting:

```python
memory_system = Memori(
    database_connect="sqlite:///debug_memory.db",
    verbose=True,  # Enable detailed logging
    conscious_ingest=True,
    auto_ingest=True
)
```

## Next Steps

- Explore the [Advanced Configuration Guide](../configuration/settings.md)
- Check out [Multi-Agent Patterns](../examples/multi-agent-patterns.md)
- Learn about [Memory Optimization](../features.md#memory-optimization)
- Join the community on [Discord](https://www.gibsonai.com/discord)

## Resources

- [Swarms Framework Documentation](https://github.com/kyegomez/swarms)
- [Memori API Reference](../api-reference.md)
- [Example Code Repository](../../examples/integrations/)