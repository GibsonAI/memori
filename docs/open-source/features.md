# Features

## Dual Memory System

### Conscious Ingest Mode
- **One-shot Working Memory**: Essential memories injected once per session
- **Background Analysis**: Automatic analysis of conversation patterns every 6 hours  
- **Essential Memory Promotion**: Key personal facts promoted for instant access
- **Human-like Memory**: Like short-term memory for immediate access to important info
- **Performance Optimized**: Minimal token usage, fast response times

### Auto Ingest Mode
- **Dynamic Context Search**: Analyzes each query for relevant memories
- **Full Database Search**: Searches entire memory database intelligently
- **Context-Aware Injection**: 3-5 most relevant memories per LLM call
- **Retrieval Agent**: AI-powered search strategy and ranking
- **Rich Context**: Higher token usage for maximum context awareness

### Combined Mode
```python
# Best of both worlds
memori = Memori(
    conscious_ingest=True,  # Essential working memory
    auto_ingest=True,       # Dynamic context search
    database_connect="postgresql://..."
)
```

### Three-Layer Intelligence
```mermaid
graph TD
    A[Retrieval Agent] --> B[Dynamic Search & Ranking]
    C[Conscious Agent] --> D[Essential Memory Promotion]
    E[Memory Agent] --> F[Structured Processing]
    
    B --> G[Auto-Ingest Context]
    D --> G[Conscious Context]
    F --> H[Categorized Storage]
    G --> I[Intelligent Context Injection]
```

## Memory Types & Categories

### Automatic Categorization
| Category | Description | Examples |
|----------|-------------|----------|
| **Facts** | Objective information | "I use PostgreSQL for databases" |
| **Preferences** | Personal choices | "I prefer clean, readable code" |
| **Skills** | Abilities & expertise | "Experienced with FastAPI" |
| **Context** | Project information | "Working on e-commerce platform" |
| **Rules** | Guidelines & constraints | "Always write tests first" |

### Retention Policies
- **Short-term**: Recent activities, temporary information (7 days)
- **Long-term**: Important information, learned skills, preferences
- **Permanent**: Critical rules, core preferences, essential facts

## Universal Integration

### Works with ANY LLM Library via LiteLLM

#### LiteLLM (Recommended)

```python
from litellm import completion
from memori import Memori

memori = Memori(
    conscious_ingest=True,
    auto_ingest=True
)
memori.enable()

# Automatic context injection with dual modes
response = completion(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": "Help me code"}]
)
```

#### OpenAI Direct

```python
import openai
from memori import Memori

memori = Memori(conscious_ingest=True)
memori.enable()

client = openai.OpenAI()
# All conversations automatically recorded
response = client.chat.completions.create(...)
```

#### Azure OpenAI

```python
from memori import Memori
from memori.core.providers import ProviderConfig

azure_provider = ProviderConfig.from_azure(
    api_key="your-azure-key",
    azure_endpoint="https://your-resource.openai.azure.com/",
    azure_deployment="gpt-4o"
)

memori = Memori(
    provider_config=azure_provider,
    conscious_ingest=True
)
memori.enable()
```

#### Anthropic
    
```python
import anthropic
from memori import Memori

memori = Memori(conscious_ingest=True)
memori.enable()

client = anthropic.Anthropic()
# All conversations automatically recorded
response = client.messages.create(...)
```

#### Custom/Ollama
```python
from memori import Memori
from memori.core.providers import ProviderConfig

ollama_provider = ProviderConfig.from_custom(
    base_url="http://localhost:11434/v1",
    api_key="ollama",
    model="llama3.2:3b"
)

memori = Memori(
    provider_config=ollama_provider,
    conscious_ingest=True
)
```

## Production Architecture

### Modular Design
```
memori/
├── core/              # Main Memori class, providers, memory modes
├── agents/            # AI-powered memory processing agents
├── database/          # Multi-database support with cloud options
├── integrations/      # LLM provider integrations (LiteLLM native)
├── config/            # Configuration management with Pydantic
├── utils/             # Helpers, validation, logging
└── tools/             # Memory search and function calling tools
```

### Database Support
- **SQLite**: Perfect for development and small applications
- **PostgreSQL**: Production-ready with full-text search and JSON support
- **MySQL**: Enterprise database support with modern features
- **Cloud Databases**: Neon, Supabase, GibsonAI serverless options
- **Connection Pooling**: Optimized performance with connection management

### Configuration Management
```python
from memori import ConfigManager

# Auto-load from multiple sources
config = ConfigManager()
config.auto_load()

# Loads from (in priority order):
# 1. Environment variables
# 2. memori.json/yaml files
# 3. Default Pydantic settings

memori = Memori()  # Uses loaded configuration
```

## Performance Features

### Dual Mode Token Optimization
```
Conscious Mode (Working Memory):
- Essential memories: 150-200 tokens
- One-shot injection per session
- Minimal overhead, maximum relevance

Auto Mode (Dynamic Search):
- Relevant context: 200-300 tokens  
- Per-query intelligent search
- Rich context, performance optimized

Traditional Context Injection:
- Full conversation history: 2000+ tokens
- No intelligence, maximum waste
```

### Efficiency Metrics
- **LiteLLM Native Integration**: No monkey-patching overhead
- **Async Background Processing**: Analysis doesn't block conversations
- **Intelligent Caching**: Smart caching of search results and promotions
- **Provider Optimization**: Efficient client management and connection reuse

### Memory Mode Comparison
| Feature | Conscious Mode | Auto Mode | Combined |
|---------|---------------|-----------|----------|
| **Token Usage** | ~150 tokens | ~250 tokens | ~300 tokens |
| **Response Time** | Fastest | Fast | Medium |
| **Context Richness** | Essential only | Query-specific | Best of both |
| **Use Case** | Quick access | Deep context | Production apps |

## Security & Reliability

### Data Protection
- **Input Sanitization**: Protection against injection attacks
- **Credential Safety**: Secure handling of API keys and secrets
- **Error Context**: Detailed logging without exposing sensitive data
- **Graceful Degradation**: Continues operation when components fail

### Production Ready
- **Connection Pooling**: Automatic database connection management
- **Resource Cleanup**: Proper cleanup of resources and connections
- **Error Handling**: Comprehensive exception handling with context
- **Monitoring**: Built-in logging and performance metrics

## Developer Experience

### Simple Setup
```python
# One line to enable dual memory modes
memori = Memori(
    conscious_ingest=True,
    auto_ingest=True
)
memori.enable()

# No more repeating context!
```

### Advanced Configuration
```python
# Production configuration with provider support
from memori.core.providers import ProviderConfig

azure_provider = ProviderConfig.from_azure(
    api_key="your-azure-key",
    azure_endpoint="https://your-resource.openai.azure.com/",
    azure_deployment="gpt-4o"
)

memori = Memori(
    database_connect="postgresql://user:pass@localhost/memori",
    provider_config=azure_provider,
    conscious_ingest=True,
    auto_ingest=True,
    namespace="production_app"
)
```

### Memory Tools & Function Calling
```python
from memori import create_memory_tool

# Create memory search tool
memory_tool = create_memory_tool(memori)

# Use with AI agents and function calling
def search_memory(query: str) -> str:
    """Search agent's memory for past conversations"""
    result = memory_tool.execute(query=query)
    return str(result) if result else "No relevant memories found"

# Function calling integration
tools = [{
    "type": "function",
    "function": {
        "name": "search_memory",
        "description": "Search memory for relevant information",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"}
            },
            "required": ["query"]
        }
    }
}]

completion(model="gpt-4o", messages=[...], tools=tools)
```

## Memory Analytics

### Real-time Statistics
```python
# Get comprehensive memory insights
stats = memori.get_memory_stats()
print(f"Total conversations: {stats.get('chat_history_count', 0)}")
print(f"Short-term memories: {stats.get('short_term_count', 0)}")
print(f"Long-term memories: {stats.get('long_term_count', 0)}")

# Get essential conversations (conscious mode)
essential = memori.get_essential_conversations()

# Trigger manual analysis
memori.trigger_conscious_analysis()

# Search by category
skills = memori.search_memories_by_category("skill")
preferences = memori.search_memories_by_category("preference")
```

### Memory Mode Monitoring
```python
# Check which modes are enabled
print(f"Conscious mode: {memori.conscious_ingest}")
print(f"Auto mode: {memori.auto_ingest}")

# Monitor performance
config_info = memori.memory_manager.get_config_info()
print(f"Provider: {memori.provider_config.api_type if memori.provider_config else 'default'}")
```

### Debug Mode
```python
# See what's happening behind the scenes
memori = Memori(
    conscious_ingest=True,
    auto_ingest=True,
    verbose=True  # Shows agent activity and mode switching
)
```

## Extensibility

### Custom Memory Processing
- Create specialized agents for specific domains
- Extend memory processing with custom logic
- Domain-specific categorization and entity extraction
- Custom retention policies and importance scoring

### Provider System
```python
# Extend provider support
class CustomProviderConfig(ProviderConfig):
    @classmethod
    def from_custom_service(cls, endpoint, auth):
        return cls(base_url=endpoint, api_key=auth, ...)
```

### Memory Tools Extensions
- Custom search functions for specific use cases
- Domain-specific memory tools
- Integration with AI agent frameworks
- Function calling extensions for complex workflows

### Plugin Architecture
- Memory processing plugins for different domains
- Custom database adapters for specialized storage
- Integration with external knowledge systems
- Event-driven architecture for real-time processing

## Scalability

### Enterprise Features
- **Multi-tenant Support**: Separate memory spaces with namespaces
- **Horizontal Scaling**: Distributed database support and load balancing
- **Provider Flexibility**: Support for Azure, AWS, custom endpoints
- **Configuration Management**: Centralized config with environment-specific settings
- **Monitoring**: Comprehensive observability for production deployments

### Performance Optimization
- **Indexed Search**: Full-text search with proper indexing and ranking
- **Memory Compression**: Intelligent consolidation over time
- **Adaptive Analysis**: Dynamic frequency based on usage patterns
- **Connection Pooling**: Optimized database connections for high throughput
- **Provider Caching**: Smart caching for frequently accessed memories

### Cloud-Native Support
```python
# Serverless database integration
memori = Memori(
    database_connect="postgresql://user:pass@neon-serverless:5432/memori",
    provider_config=azure_provider,
    conscious_ingest=True,
    auto_ingest=True
)

# Environment-based configuration
# MEMORI_DATABASE__CONNECTION_STRING=postgresql://...
# MEMORI_AGENTS__OPENAI_API_KEY=sk-...
config = ConfigManager()
config.auto_load()
```

## Future Roadmap

### Planned Features
- **Enhanced Provider Support**: Claude, Gemini, and more structured outputs
- **Vector Search**: Semantic similarity search with embeddings
- **Memory Relationships**: Understanding connections between facts and entities
- **Team Memory**: Shared memory spaces for collaborative AI applications
- **Memory Migration**: Easy import/export of memory data between instances
- **Advanced Analytics**: Memory insights, conversation patterns, and usage analytics
- **Real-time Sync**: Multi-instance memory synchronization for distributed systems