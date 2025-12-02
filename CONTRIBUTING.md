[![Memori Labs](https://s3.us-east-1.amazonaws.com/images.memorilabs.ai/banner.png)](https://memorilabs.ai/)

# Contributing to Memori Python SDK

Thank you for your interest in contributing to Memori!

## Development Setup

We use `uv` for fast dependency management and Docker for integration testing. You can develop locally or use our Docker environment.

### Prerequisites

- Python 3.10+ (3.12 recommended)
- [uv](https://github.com/astral-sh/uv) - Fast Python package installer
- Docker and Docker Compose (for integration tests)
- Make

### Quick Start (Local Development)

```bash
# Install uv if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone the repository
git clone https://github.com/MemoriLabs/python-sdk.git
cd python-sdk

# Install dependencies
uv sync

# Install pre-commit hooks
uv run pre-commit install

# Run unit tests
uv run pytest
```

### Quick Start (Docker)

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env and add your API keys (optional for unit tests)
# Required for integration tests: OPENAI_API_KEY, ANTHROPIC_API_KEY, GOOGLE_API_KEY

# Start the environment
make dev-up
```

This will:
- Build the Docker container with Python 3.12
- Install all dependencies with uv
- Start PostgreSQL, MySQL, and MongoDB for integration tests
- Start Mongo Express (web UI for MongoDB at http://localhost:8081)

### Development Commands

#### Local Development
```bash
# Run unit tests
uv run pytest

# Format code
uv run ruff format .

# Check linting
uv run ruff check .

# Run with coverage
uv run pytest --cov=memori

# Run security scans
uv run bandit -r memori -ll -ii
uv run pip-audit --require-hashes --disable-pip || true
```

#### Docker Development
```bash
# Enter the development container
make dev-shell

# Run unit tests (fast, no external dependencies)
make test

# Initialize database schemas
make init-postgres  # PostgreSQL
make init-mysql     # MySQL
make init-mongodb   # MongoDB
make init-sqlite    # SQLite

# Run a specific integration test script
make run-integration FILE=tests/llm/clients/oss/openai/async.py

# Format code
make format

# Check linting
make lint

# Run security scans
make security

# Stop the environment
make dev-down

# Clean up everything (containers, volumes, cache)
make clean
```

## Testing

We use `pytest` with coverage reporting and `pytest-mock` for mocking.

### Unit Tests
Unit tests use mocks and run without external dependencies:
```bash
# Local
uv run pytest

# Docker
make test
```

### Integration Tests
Integration tests require:
- Database instances (PostgreSQL, MySQL, MongoDB, or SQLite)
- LLM API keys (OpenAI, Anthropic, Google)

```bash
# Set API keys in .env first
# OPENAI_API_KEY=sk-...
# ANTHROPIC_API_KEY=sk-ant-...
# GOOGLE_API_KEY=...

# Initialize database schema
make init-postgres  # or init-mysql, init-mongodb, init-sqlite

# Run integration test scripts
make run-integration FILE=tests/llm/clients/oss/openai/sync.py
```

### Test Coverage

We maintain high test coverage. Coverage reports are generated automatically:
- Terminal output (summary)
- HTML report in `htmlcov/`
- XML report in `coverage.xml`

View HTML coverage:
```bash
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

## Project Structure

```
memori/              # SDK source code
  llm/               # LLM provider integrations (OpenAI, Anthropic, Google, etc.)
  memory/            # Memory system and augmentation
  storage/           # Storage adapters (PostgreSQL, MySQL, MongoDB, SQLite, etc.)
  api/               # API client for Memori Advanced Augmentation
  __init__.py        # Main Memori class and public API
  py.typed           # PEP 561 type hint marker
tests/               # Test files
  build/             # Database initialization scripts
  llm/               # LLM provider tests (unit & integration)
  memory/            # Memory system tests
  storage/           # Storage adapter tests
conftest.py          # Pytest fixtures
pyproject.toml       # Project metadata and dependencies
uv.lock              # Locked dependency versions
CHANGELOG.md         # Version history
```

## Code Quality

We use [Ruff](https://docs.astral.sh/ruff/) for linting and formatting (configured in `pyproject.toml`):

```bash
# Format code
uv run ruff format .     # or: make format

# Check linting
uv run ruff check .      # or: make lint

# Auto-fix issues
uv run ruff check --fix .

# Run security scans (Bandit + pip-audit)
uv run bandit -r memori -ll -ii
uv run pip-audit --require-hashes --disable-pip || true
```

### Pre-commit Hooks

We use pre-commit to automatically format and lint code:

```bash
# Install hooks (one-time setup)
uv run pre-commit install

# Run manually
uv run pre-commit run --all-files
```

### Code Standards

- Follow PEP 8 standards
- Line length: 88 characters (Black-compatible)
- Python 3.10+ syntax (use modern type hints)
- All public APIs must have type hints
- Lean, simple code preferred over complex solutions (KISS, YAGNI)
- Minimize unnecessary comments - code should be self-documenting

## Pull Request Guidelines

1. **Fork and branch**: Create a feature branch from `main`
2. **Write tests**: Add/update tests for your changes
3. **Pass all checks**: Ensure tests, linting, and formatting pass
4. **Update docs**: Update README or docs if adding features
5. **Changelog**: Add entry to CHANGELOG.md under "Unreleased"
6. **Atomic commits**: Keep commits focused and well-described

## Supported Integrations

### LLM Providers
- OpenAI (sync/async, streaming)
- Anthropic Claude (sync/async, streaming)
- Google Gemini (sync/async, streaming)
- AWS Bedrock

### Frameworks
- LangChain
- Pydantic AI

### Database Adapters
- PostgreSQL (via psycopg2, psycopg3)
- MySQL / MariaDB (via pymysql)
- MongoDB (via pymongo)
- Oracle (via cx_Oracle, python-oracledb)
- SQLite (stdlib)
- CockroachDB
- Neon, Supabase (PostgreSQL-compatible)
- Django ORM
- DB-API 2.0 compatible connections

## CLI Commands

Memori provides CLI commands for managing your account and quota:

```bash
# Check your API quota
python3 -m memori quota

# Sign up for Memori Advanced Augmentation
python3 -m memori sign-up <email_address>
```

These commands help you:
- Monitor your memory quota and usage
- Sign up for increased limits (always free for developers)
- Obtain API keys for Advanced Augmentation features

## Development Notes

- Docker files (Dockerfile, docker-compose.yml, Makefile) are for development only
- They are NOT included in the PyPI package
- The SDK has minimal runtime dependencies - fully self-contained
- Development dependencies (LLM clients, database drivers) are in `[dependency-groups]`
