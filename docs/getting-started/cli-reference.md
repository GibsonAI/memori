# CLI Reference

Memori CLI is automatically available after `pip install memorisdk`.

## Quick Reference

| Command | Purpose |
|---------|---------|
| `memori --version` | Show version |
| `memori init` | Create `memori.json` config |
| `memori init --force` | Overwrite config |
| `memori health` | Validate setup |
| `memori health --check-db` | Check database connection |
| `memori health --config <path>` | Validate custom config |

---

## Commands

### `memori --version`

Display installed version:
```bash
memori --version
# Output: memori version 2.3.0
```

### `memori init`

Create a starter configuration with sensible defaults:
```bash
memori init
memori init --force    # Overwrite existing config
```

Creates `memori.json` with:
- SQLite database connection
- OpenAI API key placeholder
- Memory namespace and retention policy
- Logging configuration

See [Configuration Guide](../configuration/settings.md) for detailed structure.

### `memori health`

Validate environment, dependencies, and configuration:
```bash
memori health
memori health --config custom.json  # Validate custom config
memori health --check-db             # Include database test
```

**Checks performed:**
1. Package import
2. Core dependencies (Pydantic, SQLAlchemy, OpenAI, LiteLLM, Loguru, python-dotenv)
3. Configuration file validity and required sections
4. Database connectivity (with `--check-db`)

**Exit codes:**
- `0`: All checks passed
- Non-zero: At least one check failed

---

## Workflow

```bash
# 1. Create config
memori init

# 2. Edit memori.json
# Set your OpenAI API key and adjust settings as needed

# 3. Validate setup
memori health --check-db

# 4. Use in Python
python your_script.py
```

## CI/CD Integration

```yaml
# .github/workflows/test.yml
- name: Install dependencies
  run: pip install memorisdk

- name: Verify memori setup
  run: memori health --check-db
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Command not found | `pip install memorisdk` |
| Config not found | `memori init` |
| Invalid JSON | `memori init --force` |
| Missing dependencies | `pip install memorisdk[all]` |
| Database connection error | Check `connection_string` in `memori.json` |

---

## Help

```bash
memori --help              # Show all commands
memori init --help         # Show init options
memori health --help       # Show health options
```

---

**Next:** [Configuration Guide](../configuration/settings.md) • [Basic Usage](basic-usage.md) • [Examples](../examples/overview.md)
