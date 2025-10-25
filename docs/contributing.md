# Contributing to Memori

Thank you for your interest in contributing to Memori! This guide will help you get started.

## Quick Start

1. **Fork the repository** on GitHub
2. **Clone your fork** locally
3. **Install development dependencies**
4. **Set up test environment** with API keys
5. **Make your changes**
6. **Test with dual memory modes**
7. **Submit a pull request**

## Development Setup

### Prerequisites
- Python 3.8+
- Git
- OpenAI API key (for testing agents)
- Optional: Azure OpenAI, Ollama, or other LLM providers

### Installation

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/memori.git
cd memori

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install development dependencies
pip install -e ".[dev]"
```

### Environment Configuration

Create a `.env` file for development:

```bash
# Required for agent testing
OPENAI_API_KEY=sk-your-openai-key-here

# Optional: Azure OpenAI
AZURE_OPENAI_API_KEY=your-azure-key
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT=gpt-4o
AZURE_API_VERSION=2024-02-01

# Optional: Custom endpoints (Ollama, etc.)
CUSTOM_BASE_URL=http://localhost:11434/v1
CUSTOM_API_KEY=not-required
```

### Development Dependencies

The development installation includes:
- `pytest` - Testing framework with async support
- `pytest-asyncio` - Async testing support  
- `black` - Code formatting
- `ruff` - Fast Python linting
- `isort` - Import sorting
- `mypy` - Type checking
- `pre-commit` - Git hooks for code quality
- `openai` - Required for memory agents
- `litellm` - Universal LLM interface

## Project Structure

```
memori/
├── memori/              # Main package
│   ├── core/           # Core memory system and providers
│   │   ├── memory.py   # Main Memori class with dual modes
│   │   ├── providers.py # LLM provider configuration system
│   │   └── database.py # Database management
│   ├── config/         # Configuration management with Pydantic
│   ├── agents/         # Memory processing agents
│   │   ├── memory_agent.py      # Structured conversation processing
│   │   ├── conscious_agent.py   # Conscious-info memory transfer
│   │   └── retrieval_agent.py   # Memory Search Engine
│   ├── database/       # Database connectors and queries
│   ├── integrations/   # LLM provider wrappers (OpenAI, Anthropic)
│   ├── tools/          # Memory search tools for function calling
│   └── utils/          # Pydantic models and utilities
├── tests/              # Test suite with memory mode testing
├── docs/               # Documentation (MkDocs)
├── examples/           # Usage examples for features
├── demos/              # Interactive demonstrations
└── scripts/            # Development and maintenance scripts
```

## Development Workflow

### 1. Code Style

We use `black` for code formatting, `ruff` for linting, and `isort` for imports:

```bash
# Format code
black memori/ tests/ examples/

# Sort imports
isort memori/ tests/ examples/

# Lint code
ruff check memori/ tests/ examples/

# Type checking
mypy memori/

# Run all quality checks
pre-commit run --all-files
```

### 2. Testing

#### Core Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=memori --cov-report=html

# Run specific test categories
pytest tests/ -m "not integration"  # Unit tests only
pytest tests/ -m "integration"      # Integration tests only

# Test specific memory modes
pytest tests/test_memory_modes.py
pytest tests/test_agent_system.py
```

#### Testing Memory Modes

Test both conscious_ingest and auto_ingest modes:

```bash
# Test conscious ingest mode
pytest tests/test_conscious_ingest.py -v

# Test auto ingest mode  
pytest tests/test_auto_ingest.py -v

# Test combined mode
pytest tests/test_combined_modes.py -v

# Test provider configurations
pytest tests/test_providers.py -v
```

#### Manual Testing

Test with the examples to verify functionality:

```bash
# Test basic functionality
cd examples
python basic_usage.py

# Test dual memory modes
python personal_assistant.py
python personal_assistant_advanced.py

# Test provider configurations
python advanced_config.py
```

### 3. Documentation

Documentation is built with MkDocs and includes interactive examples:

```bash
# Install docs dependencies (if not already installed)
pip install -r docs/requirements.txt

# Serve docs locally (with live reload)
mkdocs serve

# Build docs for production
mkdocs build

# Test documentation examples
python docs/examples/test_examples.py
```

## Contributing Guidelines

### Code Quality

1. **Follow PEP 8** - Use `black` for formatting and `isort` for imports
2. **Add type hints** - Use Python type annotations throughout
3. **Write docstrings** - Use Google-style docstrings with examples
4. **Add tests** - Maintain high test coverage, especially for memory modes
5. **Update docs** - Keep documentation current with features
6. **Test providers** - Verify compatibility with different LLM providers

### Memory Mode Testing

When contributing features that affect memory modes:

1. **Test Both Modes**: Verify functionality with `conscious_ingest` and `auto_ingest`
2. **Test Combined Mode**: Ensure features work when both modes are enabled
3. **Provider Compatibility**: Test with OpenAI, Azure, and custom providers
4. **Performance Impact**: Consider token usage and API call implications

### Commit Messages

Use conventional commit format with memory-specific scopes:

```
feat(memory): add vector search support for auto-ingest
fix(agents): resolve conscious agent startup issues
docs(modes): update dual memory mode examples
test(providers): add Azure OpenAI integration tests
perf(search): optimize memory retrieval performance
```

Scopes for Memori:
- `memory`: Core memory functionality
- `agents`: Memory processing agents  
- `providers`: LLM provider system
- `modes`: Conscious/auto ingest modes
- `config`: Configuration management
- `database`: Database operations
- `tools`: Memory search tools
- `integrations`: LLM wrapper integrations

### Pull Requests

1. **Create a feature branch** from `main`
2. **Make focused changes** - One feature per PR
3. **Add comprehensive tests** for new functionality:
   - Unit tests for core logic
   - Integration tests for memory modes
   - Provider compatibility tests
4. **Update documentation** including:
   - API documentation
   - Usage examples
   - Configuration examples
5. **Ensure CI passes** - All tests, linting, and type checks
6. **Test memory modes** - Verify both conscious and auto ingest work
7. **Consider backward compatibility** - Don't break existing APIs

### Documentation Standards

When updating documentation:

1. **Include Code Examples**: Provide working code snippets
2. **Show Memory Modes**: Demonstrate both conscious_ingest and auto_ingest
3. **Provider Examples**: Show configuration for different providers
4. **Performance Notes**: Include token usage and performance considerations
5. **Update Architecture**: Reflect current system design

Example documentation format:

```python
def new_feature(param: str) -> Dict[str, Any]:
    """Brief description of the new feature.
    
    This feature works with both memory modes and all provider configurations.
    
    Args:
        param: Description of parameter
        
    Returns:
        Description of return value
        
    Examples:
        Basic usage:
        >>> memori = Memori(conscious_ingest=True)
        >>> result = memori.new_feature("example")
        
        With auto-ingest mode:
        >>> memori = Memori(auto_ingest=True)
        >>> result = memori.new_feature("example")
        
        With Azure provider:
        >>> config = ProviderConfig.from_azure(...)
        >>> memori = Memori(provider_config=config)
        >>> result = memori.new_feature("example")
    """
```

## Types of Contributions

### Bug Reports

Use the GitHub issue template and include:
- Clear description of the bug
- Steps to reproduce
- Expected vs actual behavior
- **Memory mode being used** (conscious_ingest, auto_ingest, or both)
- **Provider configuration** (OpenAI, Azure, custom)
- Environment details (Python version, OS, database)
- **Code snippet** with minimal reproduction
- Error messages and stack traces

### Feature Requests

Before implementing a new feature:
1. **Check existing issues** - Avoid duplicates
2. **Open a discussion** - Propose the feature first
3. **Consider memory modes** - How will it work with both modes?
4. **Provider compatibility** - Will it work with all providers?
5. **Wait for approval** - Ensure it aligns with project goals

### Documentation

Documentation improvements are always welcome:
- Fix typos and grammar
- Add examples for features
- Update configuration guides
- Improve dual memory mode explanations
- Add provider setup tutorials
- Translate to other languages

### Testing

Help improve test coverage:
- Add unit tests for untested code
- Create integration tests for memory modes
- Add provider compatibility tests
- Test edge cases and error conditions
- Add performance benchmarks
- Test real-world scenarios

### Development Areas

Priority areas for contribution:

#### Memory System
- Vector search integration
- Memory relationship analysis
- Performance optimizations
- Advanced filtering and categorization

#### Provider Support
- New LLM provider integrations
- Enhanced provider configuration
- Custom endpoint support
- Authentication improvements

#### Agent System
- Custom agent development
- Advanced memory processing
- Multi-model support
- Reasoning capabilities

#### Database Support
- New database connectors
- Cloud database optimization
- Migration utilities
- Performance tuning

## Development Tips

### Testing Memory Modes

Test your changes with both memory modes:

```bash
# Test conscious ingest mode
cd examples
python -c "
from memori import Memori
memori = Memori(conscious_ingest=True, verbose=True)
memori.enable()
print('Conscious ingest mode working')
"

# Test auto ingest mode
python -c "
from memori import Memori
from litellm import completion

memori = Memori(auto_ingest=True, verbose=True)
response = completion(
    model='gpt-4o-mini',
    messages=[{'role': 'user', 'content': 'Hello'}]
)
print('Auto ingest mode working')
"

# Test combined mode
python personal_assistant_advanced.py
```

### Provider Testing

Test with different LLM providers:

```bash
# OpenAI (default)
export OPENAI_API_KEY="sk-..."
python examples/basic_usage.py

# Azure OpenAI
export AZURE_OPENAI_API_KEY="..."
export AZURE_OPENAI_ENDPOINT="https://..."
python examples/advanced_config.py

# Custom endpoint (Ollama)
python -c "
from memori import Memori
from memori.core.providers import ProviderConfig

config = ProviderConfig.from_custom(
    base_url='http://localhost:11434/v1',
    api_key='not-required',
    model='llama3'
)
memori = Memori(provider_config=config)
print('Custom provider working')
"
```

### Database Testing

Test with different databases:

```bash
# SQLite (default)
python -c "from memori import Memori; m = Memori(); print('SQLite OK')"

# PostgreSQL (requires setup)
python -c "
from memori import Memori
m = Memori(database_connect='postgresql://user:pass@localhost/memori')
print('PostgreSQL OK')
"

# MySQL (requires setup)  
python -c "
from memori import Memori
m = Memori(database_connect='mysql://user:pass@localhost/memori')
print('MySQL OK')
"
```

### Memory Inspection

Debug and inspect memory during development:

```python
from memori import Memori

# Set up with verbose logging
memori = Memori(
    conscious_ingest=True,
    auto_ingest=True,
    verbose=True
)
memori.enable()

# Inspect memories
stats = memori.get_memory_stats()
print(f"Memory statistics: {stats}")

# Check short-term memory (conscious ingest)
short_term = memori.db_manager.get_short_term_memories(
    namespace=memori.namespace
)
print(f"Short-term memories: {len(short_term)}")

# Test auto-ingest context retrieval
context = memori._get_auto_ingest_context("test query")
print(f"Auto-ingest context: {len(context)} memories")

# Search by category
preferences = memori.search_memories_by_category("preference", limit=5)
print(f"Preferences: {len(preferences)}")

# Get all conscious-info labeled memories
conscious_memories = memori.search_memories_by_labels(["conscious-info"])
print(f"Conscious-info memories: {len(conscious_memories)}")
```

### Performance Testing

Monitor performance impact of changes:

```python
import time
from memori import Memori

# Measure startup time
start = time.time()
memori = Memori(conscious_ingest=True, auto_ingest=True)
memori.enable()
startup_time = time.time() - start
print(f"Startup time: {startup_time:.2f}s")

# Measure query time
start = time.time()
context = memori._get_auto_ingest_context("What are my preferences?")
query_time = time.time() - start
print(f"Query time: {query_time:.2f}s, Context size: {len(context)}")

# Token usage estimation
total_tokens = sum(len(str(memory)) for memory in context) // 4
print(f"Estimated tokens: {total_tokens}")
```

## Architecture Guidelines

### Code Organization

- **Separation of concerns** - Each module has a clear purpose
- **Dependency injection** - Use ProviderConfig for LLM dependencies
- **Error handling** - Use custom exceptions with detailed context
- **Type safety** - Full type annotations and Pydantic validation
- **Memory mode agnostic** - Features should work with both modes

### Memory System Design

- **Dual mode support** - All features must work with conscious_ingest and auto_ingest
- **Provider agnostic** - Support OpenAI, Azure, and custom endpoints
- **Structured data** - Use Pydantic models for all memory operations
- **Categorization** - Proper memory categorization (fact, preference, skill, context, rule)
- **Performance aware** - Consider token usage and API call implications

### Database Design

- **SQL in query modules** - Centralized query management in `database/queries/`
- **Connection pooling** - Efficient resource usage with SQLAlchemy
- **Migration support** - Schema versioning for database updates
- **Multi-database** - Support SQLite, PostgreSQL, MySQL, and cloud databases
- **Namespace isolation** - Support for multi-tenant memory spaces

### API Design

- **Simple interface** - Minimal required configuration with sensible defaults
- **Pydantic validation** - Type-safe data structures throughout
- **Error context** - Detailed error information with troubleshooting hints
- **Backwards compatibility** - Careful API evolution with deprecation warnings
- **Provider flexibility** - Easy switching between LLM providers

### Agent System Architecture

When working with the agent system:

1. **Memory Agent**: Focus on structured output processing with Pydantic
2. **Conscious Agent**: Simple transfer of conscious-info labeled memories
3. **Memory Search Engine**: Intelligent context retrieval for auto-ingest
4. **Provider Integration**: Ensure all agents work with configured providers

### Testing Architecture

- **Unit tests** - Test individual components in isolation
- **Integration tests** - Test memory modes and provider combinations
- **Performance tests** - Monitor token usage and response times
- **Mock external services** - Use mock providers for CI/CD
- **Real provider tests** - Optional tests with actual API keys

## Getting Help

- **GitHub Discussions** - Ask questions and share ideas about features
- **GitHub Issues** - Report bugs and request features
- **Discord Community** - Join us at https://discord.gg/abD4eGym6v
- **Documentation** - Check docs for configuration and usage examples
- **Examples Directory** - Working code examples for all major features
- **Email** - Direct contact at noc@gibsonai.com for sensitive issues

### Common Questions

**Q: How do I test both memory modes?**
A: Use the examples in `/examples/` that demonstrate both conscious_ingest and auto_ingest modes.

**Q: Which provider should I use for testing?**
A: OpenAI GPT-4o-mini is recommended for development due to cost-effectiveness and reliability.

**Q: How do I set up Azure OpenAI for testing?**
A: See the provider configuration examples in `/examples/advanced_config.py`.

**Q: Why are my tests failing with "No API key"?**
A: Set up your `.env` file with the required API keys as shown in the setup section.

**Q: How do I debug memory retrieval issues?**
A: Use `verbose=True` in your Memori configuration to see detailed logging.

## Recognition

Contributors will be:
- Listed in the project README and CHANGELOG
- Credited in release notes for significant contributions
- Invited to join the maintainers team (for ongoing contributors)
- Featured in community highlights

### Contribution Levels

- **Bug fixes**: Listed in CHANGELOG
- **Feature additions**: Featured in release notes
- **Documentation improvements**: Recognized in community updates
- **Major contributions**: Invited to maintainer discussions

Thank you for helping make Memori better! Your contributions help build the future of AI memory systems.