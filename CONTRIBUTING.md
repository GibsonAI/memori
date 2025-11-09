# Contributing to Memori

We welcome contributions to Memori! This guide will help you get started with contributing to the project.

## Quick Start

1. Fork the repository
2. Clone your fork: `git clone https://github.com/YOUR_USERNAME/memori.git`
3. Create a branch: `git checkout -b feature/your-feature-name`
4. Install dependencies: `pip install -e ".[dev]"`
5. Make your changes
6. Run tests: `pytest`
7. Format code: `black memori/ tests/` and `ruff check memori/ tests/ --fix`
8. Commit and push your changes
9. Create a pull request

---

## Development Setup

### Prerequisites

- Python 3.8 or higher
- Git

### Environment Setup

```bash
# Clone the repository
git clone https://github.com/GibsonAI/memori.git
cd memori

# Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install development dependencies
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=memori --cov-report=html

# Run specific test file
pytest tests/test_basic_functionality.py
```

### Code Quality Tools

```bash
# Format code
black memori/ tests/ examples/ scripts/
isort memori/ tests/ examples/ scripts/

# Lint code
ruff check memori/ tests/ examples/ scripts/

# Type checking
mypy memori/

# Security checks
bandit -r memori/
safety check
```

---

## Code Standards

### Style Guidelines

- Follow [PEP 8](https://www.python.org/dev/peps/pep-0008/)
- Use [Black](https://black.readthedocs.io/) for code formatting
- Use [Ruff](https://docs.astral.sh/ruff/) for linting
- Write type hints for all functions and methods
- Keep line length to 88 characters

### Commit Message Format

Follow conventional commit format:

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Build process or tooling changes

**Examples:**
```
feat(memory): add context-aware memory retrieval
fix(database): resolve connection timeout issues
docs(readme): update installation instructions
```

### Documentation

- Update documentation for any new features or API changes
- Add docstrings to all public functions and classes
- Use Google style docstrings:

```python
def example_function(param1: str, param2: int) -> bool:
    """Brief description of the function.

    Args:
        param1: Description of param1
        param2: Description of param2

    Returns:
        Description of return value

    Raises:
        ValueError: Description of when this is raised
    """
    pass
```

---

## Pull Request Process

1. Create descriptive PR title following conventional commit format
2. Fill out PR template with all required information
3. Link related issues using keywords (fixes #123, closes #456)
4. Ensure all checks pass:
   - Tests pass
   - Code coverage maintained
   - Code style checks pass
   - Security scans pass
5. Request review from maintainers
6. Address feedback promptly

---

## Reporting Issues

### Bug Reports

When reporting bugs, please include:

1. Clear, descriptive title
2. Steps to reproduce the bug
3. Expected behavior
4. Actual behavior
5. Environment details:
   - Python version
   - Memori version
   - Operating system
   - Database type (if applicable)
6. Code snippet or minimal example
7. Error messages and stack traces

### Feature Requests

When suggesting new features:

1. Check existing issues to avoid duplicates
2. Describe the problem the feature would solve
3. Explain the proposed solution
4. Consider implementation complexity
5. Provide use cases and examples

---

## Development Guidelines

### Architecture Principles

1. **Modular Design**: Keep components loosely coupled
2. **Clean Interfaces**: Use clear, documented APIs
3. **Database Agnostic**: Support multiple database backends
4. **LLM Agnostic**: Work with any LLM provider
5. **Type Safety**: Use static typing throughout
6. **Error Handling**: Provide clear, actionable error messages

### Adding New Features

1. Start with an issue describing the feature
2. Design the API before implementation
3. Write tests first (TDD approach recommended)
4. Implement incrementally with small, focused commits
5. Document thoroughly including examples
6. Consider backward compatibility

### Database Migrations

When modifying database schemas:

1. Create migration files in `memori/database/migrations/`
2. Test migrations on sample data
3. Document migration steps
4. Consider rollback procedures

### Integration Testing

For new integrations:

1. Create integration tests in `tests/integration/`
2. Mock external services when possible
3. Test error conditions and edge cases
4. Document integration setup

---

## Getting Help

- **GitHub Discussions**: For questions and general discussion
- **GitHub Issues**: For bug reports and feature requests
- **Discord**: Join our community at https://discord.gg/abD4eGym6v
- **Documentation**: Check https://www.gibsonai.com/docs/memori

---

## License

By contributing to Memori, you agree that your contributions will be licensed under the Apache License 2.0.

---

## Recognition

Contributors will be recognized in:
- The Memori website contributors page
- `CHANGELOG.md` for their contributions
- GitHub contributors list
- Release notes for significant contributions

Thank you for contributing to Memori!
