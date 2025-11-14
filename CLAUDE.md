# CLAUDE.md - AI Assistant Guide for Memori

This document provides comprehensive guidance for AI assistants working with the Memori codebase.

## Project Overview

**Memori** is an open-source SQL-native memory engine for AI agents that enables persistent, queryable memory using standard SQL databases. It provides a one-line integration (`memori.enable()`) that gives any LLM persistent memory across conversations.

- **Package Name**: `memorisdk`
- **Current Version**: 2.3.2
- **Python Support**: 3.10+
- **License**: Apache 2.0
- **Repository**: https://github.com/GibsonAI/memori

## Architecture Quick Reference

```
┌─────────────────────────────────────────────────────────┐
│              User Application (OpenAI/Anthropic/etc)    │
└────────────────────┬────────────────────────────────────┘
                     │
        ┌────────────▼────────────────────┐
        │     Memori Core (memory.py)     │  ← Main entry point
        │  - Recording & Retrieval        │
        │  - Context Injection            │
        └────────┬───────────┬────────────┘
                 │           │
    ┌────────────▼──┐   ┌────▼─────────────┐
    │ Memory Agents │   │ Integrations     │
    │ - Processing  │   │ - OpenAI         │
    │ - Retrieval   │   │ - Anthropic      │
    │ - Conscious   │   │ - LiteLLM        │
    └────────┬──────┘   └──────────────────┘
             │
    ┌────────▼──────────────────────┐
    │ SQLAlchemyDatabaseManager     │  ← Database abstraction
    │ - Multi-database support      │
    │ - Search (FTS/FULLTEXT/etc)   │
    └────────┬──────────────────────┘
             │
    ┌────────▼──────────┐
    │ SQLite/Postgres/  │  ← You control the data
    │ MySQL/MongoDB     │
    └───────────────────┘
```

## Core Codebase Structure

### Directory Layout

```
memori/
├── __init__.py              # Public API exports
├── core/                    # Core functionality
│   ├── memory.py           # Memori class (main entry point)
│   ├── database.py         # Legacy DatabaseManager
│   ├── conversation.py     # ConversationManager (session tracking)
│   └── providers.py        # ProviderConfig (LLM provider config)
├── config/                  # Configuration management
│   ├── manager.py          # ConfigManager (singleton)
│   ├── settings.py         # Pydantic settings models
│   └── memory_manager.py   # MemoryManager
├── database/                # Database layer
│   ├── sqlalchemy_manager.py    # Main DB interface (SQLAlchemy)
│   ├── models.py                # ORM models
│   ├── search_service.py        # Cross-DB search
│   ├── query_translator.py      # Dialect abstraction
│   ├── connectors/              # DB connectors
│   ├── adapters/                # DB-specific adapters
│   ├── queries/                 # SQL query builders
│   └── templates/               # SQL schema templates
├── agents/                  # AI agents
│   ├── memory_agent.py     # LLM-based memory processing
│   ├── retrieval_agent.py  # Intelligent memory search
│   └── conscious_agent.py  # Context promotion agent
├── integrations/            # LLM provider integrations
│   ├── openai_integration.py    # OpenAI wrapper + interception
│   ├── anthropic_integration.py # Anthropic wrapper
│   └── litellm_integration.py   # LiteLLM callbacks
├── tools/                   # LLM tools
│   └── memory_tool.py      # MemoryTool for LLM function calling
├── security/                # Security features
│   └── auth.py             # AuthProvider, JWT
└── utils/                   # Utilities
    ├── pydantic_models.py  # Data models
    ├── exceptions.py       # Custom exceptions
    ├── validators.py       # Input validation
    ├── helpers.py          # Utility functions
    ├── logging.py          # Logging setup
    └── ...
```

### Key Files and Their Purposes

| File | Primary Class | Purpose |
|------|---------------|---------|
| `core/memory.py` | `Memori` | Main API; orchestrates all memory operations |
| `database/sqlalchemy_manager.py` | `SQLAlchemyDatabaseManager` | Cross-database ORM and CRUD operations |
| `database/models.py` | `ChatHistory`, `ShortTermMemory`, `LongTermMemory` | SQLAlchemy ORM models |
| `agents/memory_agent.py` | `MemoryAgent` | LLM-powered memory processing and extraction |
| `agents/retrieval_agent.py` | `MemorySearchEngine` | Intelligent memory search and retrieval |
| `agents/conscious_agent.py` | `ConsciouscAgent` | Promotes conscious memories to short-term |
| `config/manager.py` | `ConfigManager` | Configuration loading (file/env) |
| `integrations/openai_integration.py` | `MemoriOpenAI`, `MemoriOpenAIInterceptor` | OpenAI integration layer |
| `utils/pydantic_models.py` | `ProcessedMemory`, etc. | Memory data structures |

## Database Schema

The system uses three primary tables:

### 1. `chat_history` - Conversation Records
- Stores all conversations (user input + AI output)
- Multi-tenant fields: `user_id`, `assistant_id`, `session_id`
- Metadata: `model`, `tokens`, `timestamp`

### 2. `short_term_memory` - Recent Working Memory (~7 days)
- Processed, categorized memories with expiration
- Fields: `importance_score`, `category_primary`, `retention_type`, `expires_at`
- Searchable via `searchable_content` field
- Indexes on: user_id, category, importance, expires_at

### 3. `long_term_memory` - Consolidated Permanent Memory
- Deduplicated, scored, high-value memories
- Scoring: importance, novelty, relevance, actionability
- Classification: ESSENTIAL, CONTEXTUAL, CONVERSATIONAL, etc.
- Entity extraction: `entities_json`, `keywords_json`

### Multi-Database Support

| Database | Connection String Example | Full-Text Search |
|----------|---------------------------|------------------|
| SQLite | `sqlite:///memory.db` | FTS5 |
| PostgreSQL | `postgresql://user:pass@host/db` | tsvector + tsquery |
| MySQL | `mysql://user:pass@host/db` | FULLTEXT indexes |
| MongoDB | `mongodb://user:pass@host/db` | Text indexes |

## Development Workflows

### Setting Up Development Environment

```bash
# Clone repository
git clone https://github.com/GibsonAI/memori.git
cd memori

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install with dev dependencies
pip install -e ".[dev]"

# Install pre-commit hooks (if available)
pre-commit install
```

### Code Quality Standards

The project uses multiple tools for code quality:

#### 1. **Black** - Code Formatting
```bash
black memori/ tests/
```
- Line length: 88 characters
- Target: Python 3.10+
- Config: `[tool.black]` in `pyproject.toml`

#### 2. **Ruff** - Linting
```bash
ruff check memori/ tests/ --fix
```
- Checks: pycodestyle (E/W), pyflakes (F), isort (I), bugbear (B), comprehensions (C4), pyupgrade (UP)
- Ignores: E501 (line too long - handled by black)
- Config: `[tool.ruff]` in `pyproject.toml`

#### 3. **isort** - Import Sorting
```bash
isort memori/ tests/
```
- Profile: black
- Config: `[tool.isort]` in `pyproject.toml`

#### 4. **mypy** - Type Checking
```bash
mypy memori/
```
- Target: Python 3.10
- **Note**: Currently relaxed for CI compatibility (see `[tool.mypy]` in `pyproject.toml`)
- Future: Gradually enable stricter typing

### Running Tests

```bash
# Run all tests
pytest

# Run specific test categories
pytest -m unit           # Unit tests only
pytest -m integration    # Integration tests only
pytest -m "not slow"     # Skip slow tests

# Run with coverage
pytest --cov=memori --cov-report=html
```

### Commit Conventions

Use conventional commit format:

```
<type>: <description>

[optional body]

[optional footer]
```

**Types**:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `refactor`: Code refactoring
- `test`: Adding/updating tests
- `chore`: Maintenance tasks
- `perf`: Performance improvements

**Examples**:
```
feat: add MongoDB support for memory storage
fix: resolve PostgreSQL connection pool timeout
docs: update installation guide for Python 3.12
refactor: extract search logic into SearchService
test: add integration tests for multi-tenant isolation
```

## Key Conventions and Patterns

### 1. Multi-Tenant Isolation

**CRITICAL**: All database operations MUST filter by tenant identifiers:

```python
# Always include these filters
filters = {
    "user_id": user_id,           # Required
    "assistant_id": assistant_id,  # Optional but recommended
    "session_id": session_id       # Optional
}
```

**Why**: Prevents data leakage between users/assistants/sessions.

### 2. Memory Categories

Memories are categorized into 5 types:

```python
class MemoryCategoryType(str, Enum):
    FACT = "fact"                    # Factual information
    PREFERENCE = "preference"        # User preferences
    SKILL = "skill"                  # Capabilities/skills
    CONTEXT = "context"              # Contextual information
    RULE = "rule"                    # Rules/constraints
```

### 3. Memory Classification

```python
class MemoryClassification(str, Enum):
    ESSENTIAL = "ESSENTIAL"                  # Critical, always retrieve
    CONTEXTUAL = "CONTEXTUAL"                # Retrieve when relevant
    CONVERSATIONAL = "CONVERSATIONAL"        # Recent conversation flow
    REFERENCE = "REFERENCE"                  # Background information
    PERSONAL = "PERSONAL"                    # Personal details
    CONSCIOUS_INFO = "CONSCIOUS_INFO"        # User-flagged important
```

### 4. Retention Types

```python
class RetentionType(str, Enum):
    SHORT_TERM = "short_term"      # ~7 days, working memory
    LONG_TERM = "long_term"        # Permanent, consolidated
    PERMANENT = "permanent"         # Never expires
```

### 5. Context Injection Modes

**Conscious Ingest** (`conscious_ingest=True`):
- One-time at startup
- Copies conscious-labeled memories to short-term
- Lower overhead

**Auto Ingest** (`auto_ingest=True`):
- Dynamic search before every LLM call
- Retrieves most relevant memories
- Higher accuracy, more API calls

**Combined** (`conscious_ingest=True, auto_ingest=True`):
- Best of both worlds
- Recommended for production

### 6. Configuration Loading Priority

```
1. Explicit parameters in Memori() constructor
2. Environment variables (MEMORI_*)
3. Configuration files:
   - $MEMORI_CONFIG_PATH
   - ./memori.json, ./memori.yaml
   - ./config/memori.*
   - ~/.memori/config.json
   - /etc/memori/config.json
4. Default values
```

### 7. Error Handling

The project defines 13+ custom exceptions in `utils/exceptions.py`:

```python
# Common exceptions
MemoriError                    # Base exception
ConfigurationError             # Config issues
DatabaseConnectionError        # DB connection failures
DatabaseOperationError         # DB operation failures
MemoryProcessingError          # Processing failures
SearchError                    # Search failures
ValidationError                # Input validation failures
```

**Always catch specific exceptions**, not generic `Exception`.

### 8. Logging

Use the centralized logging system:

```python
from memori.utils.logging import get_logger

logger = get_logger(__name__)

logger.debug("Detailed debug info")
logger.info("General info")
logger.warning("Warning message")
logger.error("Error occurred")
logger.exception("Error with traceback")
```

**DO NOT** use `print()` statements in production code.

### 9. Database Transactions

For multi-statement operations, use transactions:

```python
from memori.utils.transaction_manager import TransactionManager

with TransactionManager(db_session) as txn:
    # Multiple DB operations
    db_session.add(record1)
    db_session.add(record2)
    # Auto-commits on success, rolls back on error
```

### 10. Async/Await Patterns

Some agents use async operations:

```python
# memory_agent.py uses async
async def process_memory(self, ...):
    result = await self._call_llm_async(...)
    return result

# Call from sync context
import asyncio
result = asyncio.run(agent.process_memory(...))
```

## Common Development Tasks

### Adding a New Database Connector

1. Create connector in `database/connectors/`:
   ```python
   # your_db_connector.py
   from .base_connector import BaseDatabaseConnector

   class YourDBConnector(BaseDatabaseConnector):
       def connect(self) -> Any:
           # Implementation
           pass
   ```

2. Create adapter in `database/adapters/`:
   ```python
   # your_db_adapter.py
   class YourDBSearchAdapter:
       def search(self, query: str) -> List[Dict]:
           # Implementation
           pass
   ```

3. Register in `database/sqlalchemy_manager.py`:
   - Update `_create_engine()` method
   - Add to `SearchService` initialization

4. Add tests in `tests/your_db_support/`

5. Add example in `examples/databases/your_db_demo.py`

### Adding a New LLM Integration

1. Create integration file in `integrations/`:
   ```python
   # your_llm_integration.py
   from memori.core.memory import Memori

   class MemoriYourLLM:
       def __init__(self, memori: Memori, **kwargs):
           self.memori = memori
           # Setup wrapper
   ```

2. Implement pre-call and post-call hooks:
   - Pre-call: Inject context from `memori.retrieve_context()`
   - Post-call: Record with `memori.record()`

3. Export in `integrations/__init__.py`

4. Add test in `tests/your_llm_support/`

5. Add example in `examples/integrations/your_llm_example.py`

### Adding a New Memory Category

1. Update `utils/pydantic_models.py`:
   ```python
   class MemoryCategoryType(str, Enum):
       FACT = "fact"
       # ... existing ...
       YOUR_CATEGORY = "your_category"
   ```

2. Update `agents/memory_agent.py` system prompt to handle new category

3. Add tests for new category classification

4. Update documentation

### Modifying Database Schema

**⚠️ IMPORTANT**: Schema changes require migration strategy!

1. **Never modify existing columns** - add new ones
2. Create migration in `database/migrations/`
3. Update ORM models in `database/models.py`
4. Update SQL templates in `database/templates/schemas/`
5. Test with all supported databases
6. Document migration in `CHANGELOG.md`

## Testing Guidelines

### Test Structure

```
tests/
├── unit/                    # Unit tests (fast, isolated)
├── integration/             # Integration tests (DB, API)
├── openai/                  # OpenAI integration tests
├── mysql_support/           # MySQL-specific tests
├── postgresql_support/      # PostgreSQL-specific tests
├── litellm_support/         # LiteLLM tests
└── utils/                   # Utility tests
```

### Test Markers

Use pytest markers to categorize tests:

```python
@pytest.mark.unit
def test_memory_validation():
    # Fast, isolated test
    pass

@pytest.mark.integration
def test_database_connection():
    # Integration test
    pass

@pytest.mark.slow
def test_full_workflow():
    # Slow end-to-end test
    pass
```

### Writing Good Tests

**DO**:
- Test one thing per test function
- Use descriptive test names: `test_memory_agent_extracts_entities_from_conversation`
- Use fixtures for common setup
- Mock external API calls (OpenAI, Anthropic)
- Clean up test data (use transactions that rollback)

**DON'T**:
- Test implementation details
- Leave test data in databases
- Make tests depend on each other
- Use hardcoded API keys (use env vars or mocks)

### Example Test Pattern

```python
import pytest
from memori import Memori
from unittest.mock import Mock, patch

@pytest.fixture
def memori_instance():
    """Fixture providing a test Memori instance."""
    return Memori(
        database_connect="sqlite:///:memory:",
        user_id="test_user",
        openai_api_key="test_key"
    )

@pytest.mark.unit
def test_memory_recording(memori_instance):
    """Test that conversations are recorded correctly."""
    # Arrange
    user_input = "Hello"
    ai_response = "Hi there!"

    # Act
    memori_instance.record(
        user_input=user_input,
        ai_response=ai_response
    )

    # Assert
    history = memori_instance.db_manager.get_chat_history(
        user_id="test_user"
    )
    assert len(history) == 1
    assert history[0].user_input == user_input
```

## Security Considerations

### 1. SQL Injection Prevention

**Always use parameterized queries**:

```python
# GOOD
session.execute(
    select(ChatHistory).where(ChatHistory.user_id == user_id)
)

# BAD - Never do this!
session.execute(f"SELECT * FROM chat_history WHERE user_id = '{user_id}'")
```

### 2. Multi-Tenant Isolation

**Always validate tenant identifiers**:

```python
from memori.utils.validators import DataValidator

# Validate user_id before use
if not DataValidator.is_valid_uuid(user_id):
    raise ValidationError("Invalid user_id format")
```

### 3. API Key Management

**Never hardcode API keys**:

```python
# GOOD
import os
api_key = os.getenv("OPENAI_API_KEY")

# BAD
api_key = "sk-..."
```

### 4. Sensitive Data Handling

**Sanitize logs**:

```python
# The LoggingManager automatically sanitizes sensitive data
from memori.utils.logging import get_logger

logger = get_logger(__name__)
logger.info(f"Processing for user {user_id}")  # Safe
# API keys, passwords automatically redacted from logs
```

### 5. Input Validation

**Validate all external input**:

```python
from memori.utils.validators import MemoryValidator

# Validate memory data before storage
MemoryValidator.validate_memory_input(memory_data)
```

## Performance Optimization

### 1. Database Connection Pooling

```python
# Configured in pyproject.toml / settings.py
pool_size = 2           # Base connections
max_overflow = 3        # Extra connections
pool_timeout = 30       # Wait time (seconds)
pool_recycle = 3600     # Recycle after (seconds)
pool_pre_ping = True    # Verify before use
```

### 2. Batch Operations

For bulk inserts, use batch operations:

```python
# GOOD - Batch insert
db_manager.batch_insert_memories(memories_list)

# AVOID - Individual inserts in loop
for memory in memories_list:
    db_manager.insert_memory(memory)
```

### 3. Index Usage

Ensure queries use indexes:

- `user_id` - Always indexed
- `category_primary` - Indexed for filtering
- `importance_score` - Indexed for sorting
- `expires_at` - Indexed for cleanup
- `searchable_content` - Full-text indexed

### 4. Memory Cleanup

Short-term memories auto-expire. For manual cleanup:

```python
# Runs automatically, but can be triggered
db_manager.cleanup_expired_memories()
```

### 5. Caching

Consider caching for frequently accessed data:

```python
# ConfigManager uses singleton pattern
from memori.config import ConfigManager

config = ConfigManager()  # Reuses existing instance
```

## Debugging Tips

### 1. Enable SQL Echo

See all SQL queries:

```python
memori = Memori(
    database_connect="sqlite:///debug.db?echo=true"
)
```

Or in settings:
```python
DatabaseSettings(echo_sql=True)
```

### 2. Increase Log Level

```python
from memori.utils.logging import LoggingManager

LoggingManager.set_log_level("DEBUG")
```

### 3. Inspect Memory Processing

```python
# See what the MemoryAgent extracted
from memori.agents import MemoryAgent

agent = MemoryAgent(openai_api_key="...")
result = await agent.process_conversation(
    user_input="I love Python",
    ai_response="That's great!"
)
print(result)  # Shows entities, categories, scores
```

### 4. Test Database State

```python
# Check what's in the database
with memori.db_manager.get_session() as session:
    memories = session.query(ShortTermMemory).all()
    for mem in memories:
        print(f"{mem.category_primary}: {mem.summary}")
```

### 5. Mock LLM Calls

For testing without API calls:

```python
from unittest.mock import patch

with patch('openai.ChatCompletion.create') as mock_create:
    mock_create.return_value = {"choices": [...]}
    # Your test code
```

## Common Pitfalls and Solutions

### ❌ Pitfall 1: Forgetting Multi-Tenant Filters

```python
# WRONG - Leaks data between users
memories = session.query(ShortTermMemory).all()

# RIGHT - Filter by user_id
memories = session.query(ShortTermMemory).filter_by(
    user_id=user_id
).all()
```

### ❌ Pitfall 2: Not Handling Async Properly

```python
# WRONG - Async function not awaited
result = memory_agent.process_memory(...)

# RIGHT
import asyncio
result = asyncio.run(memory_agent.process_memory(...))
```

### ❌ Pitfall 3: Hardcoding Database Paths

```python
# WRONG
memori = Memori(database_connect="sqlite:///memori.db")

# RIGHT - Use environment or config
import os
db_url = os.getenv("MEMORI_DB_URL", "sqlite:///memori.db")
memori = Memori(database_connect=db_url)
```

### ❌ Pitfall 4: Not Cleaning Up Test Data

```python
# WRONG - Leaves data in DB
def test_something():
    memori.record(...)
    # Test assertions
    # No cleanup!

# RIGHT - Use transactions or cleanup
def test_something():
    memori.record(...)
    # Test assertions
    memori.db_manager.delete_all_for_user(test_user_id)
```

### ❌ Pitfall 5: Ignoring Connection Pool Limits

```python
# WRONG - Creates new connection per call
for i in range(1000):
    memori = Memori(...)  # New connection each time!
    memori.record(...)

# RIGHT - Reuse instance
memori = Memori(...)
for i in range(1000):
    memori.record(...)
```

## File Modification Guidelines

### High-Risk Files (Modify with Extreme Care)

These files affect core functionality. Changes require extensive testing:

- `core/memory.py` - Main API, used by all integrations
- `database/sqlalchemy_manager.py` - Database operations
- `database/models.py` - Schema changes require migrations
- `integrations/*_integration.py` - Breaking changes affect users
- `utils/pydantic_models.py` - Data structure changes cascade

### Medium-Risk Files (Test Thoroughly)

- `agents/*.py` - Agent behavior changes
- `database/search_service.py` - Search functionality
- `config/manager.py` - Configuration loading
- `utils/validators.py` - Validation logic

### Low-Risk Files (Safer to Modify)

- `examples/*.py` - Example code
- `docs/*.md` - Documentation
- `tests/*.py` - Tests (but don't break them!)
- `utils/helpers.py` - Utility functions (if well-isolated)

## Pull Request Checklist

Before submitting a PR:

- [ ] Code formatted with `black memori/ tests/`
- [ ] Linting passes: `ruff check memori/ tests/ --fix`
- [ ] Imports sorted: `isort memori/ tests/`
- [ ] Type hints added for new functions
- [ ] Tests written and passing: `pytest`
- [ ] Tests cover new code (check with `pytest --cov`)
- [ ] Documentation updated (docstrings, README, CHANGELOG)
- [ ] Examples updated if API changed
- [ ] Commit messages follow conventional format
- [ ] No hardcoded secrets or API keys
- [ ] Multi-tenant isolation maintained
- [ ] Database migrations provided if schema changed
- [ ] Works with all supported databases (if DB change)
- [ ] Works with all supported Python versions (3.10+)

## Resources

### Documentation
- Main Docs: https://www.gibsonai.com/docs/memori
- GitHub: https://github.com/GibsonAI/memori
- PyPI: https://pypi.org/project/memorisdk/

### Community
- Discord: https://discord.gg/abD4eGym6v
- Issues: https://github.com/GibsonAI/memori/issues

### Key Dependencies Documentation
- SQLAlchemy 2.0: https://docs.sqlalchemy.org/
- Pydantic: https://docs.pydantic.dev/
- LiteLLM: https://docs.litellm.ai/
- Loguru: https://loguru.readthedocs.io/

## Version History

See [CHANGELOG.md](./CHANGELOG.md) for detailed version history.

## Quick Reference: Common Commands

```bash
# Setup
pip install -e ".[dev]"

# Code Quality
black memori/ tests/
ruff check memori/ tests/ --fix
isort memori/ tests/
mypy memori/

# Testing
pytest                          # All tests
pytest -m unit                  # Unit tests only
pytest -m "not slow"            # Skip slow tests
pytest --cov=memori            # With coverage

# Documentation
mkdocs serve                    # Local docs server

# Package
python -m build                 # Build distribution
pip install -e .                # Install locally
```

---

**Last Updated**: 2025-11-14
**For**: AI Assistants working with Memori codebase
**Maintained By**: Memori Labs Team
