# Contributing to Memori

Thank you for your interest in contributing to Memori! We welcome contributions from the community.

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/YOUR_USERNAME/memori.git`
3. Create a branch: `git checkout -b feature/your-feature-name`
4. Make your changes
5. Commit and push
6. Open a pull request

## Development Setup

```bash
# Clone and navigate to the repository
git clone https://github.com/GibsonAI/memori.git
cd memori

# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install with development dependencies
pip install -e ".[dev]"
```

## Code Standards

We follow Python best practices:

- **Style**: Follow [PEP 8](https://www.python.org/dev/peps/pep-0008/)
- **Formatting**: Use `black memori/ tests/`
- **Linting**: Use `ruff check memori/ tests/ --fix`
- **Type Hints**: Add type annotations to functions

## Commit Guidelines

Use conventional commit format:

```
<type>: <description>

Examples:
feat: add multi-user session support
fix: resolve database connection timeout
docs: update installation guide
```

**Types**: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`

## Pull Requests

- Write a clear title and description
- Link related issues (fixes #123)
- Ensure code is formatted and linted
- Update relevant documentation

## Reporting Issues

**Bug Reports**: Include steps to reproduce, expected vs actual behavior, and environment details (Python version, OS, database type)

**Feature Requests**: Describe the problem it solves and provide use cases

## Getting Help

- **Discord**: https://discord.gg/abD4eGym6v
- **GitHub Issues**: For bugs and features
- **Documentation**: https://memorilabs.ai/docs

## License

By contributing, you agree that your contributions will be licensed under Apache License 2.0.

---

Thank you for contributing to Memori!
