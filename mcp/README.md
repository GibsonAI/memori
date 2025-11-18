# Memori MCP Server

A [Model Context Protocol (MCP)](https://modelcontextprotocol.io) server that exposes Memori's persistent memory capabilities to any MCP-compatible AI assistant like Claude Desktop.

## What is MCP?

The Model Context Protocol (MCP) is an open protocol that enables AI assistants to securely access external tools and data sources. Think of it as a standardized way for AI systems to "remember" and access information across conversations.

## What Does This Server Do?

The Memori MCP Server gives Claude (or any MCP-compatible AI) the ability to:

- **Remember conversations** across sessions
- **Store and retrieve facts** about users, projects, and preferences
- **Search past memories** intelligently
- **Track conversation history** with full context
- **Manage memory lifecycle** (short-term vs long-term)
- **Get insights** from stored memories

## Features

### Tools (Actions)

1. **record_conversation** - Store user/AI conversation turns
2. **search_memories** - Intelligent memory search with filters
3. **get_recent_memories** - Get recent context
4. **get_memory_statistics** - Memory analytics and insights
5. **get_conversation_history** - Raw conversation history
6. **clear_session_memories** - Reset session context

### Resources (Data Access)

1. **memori://memories/{user_id}** - View all memories for a user
2. **memori://stats/{user_id}** - View memory statistics

### Prompts (Templates)

1. **memory_search_prompt** - Search and summarize memories
2. **conversation_context_prompt** - Get recent context

## Installation

### Prerequisites

- Python 3.10+
- [uv](https://docs.astral.sh/uv/) package manager
- Claude Desktop (or any MCP-compatible client)

### Step 1: Install uv

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### Step 2: Clone Memori Repository

```bash
git clone https://github.com/GibsonAI/memori.git
cd memori
```

### Step 3: Install Memori with MCP Support

```bash
# Install with MCP dependencies
pip install -e ".[all]"
pip install mcp fastmcp
```

### Step 4: Configure Claude Desktop

#### macOS

Edit `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "memori": {
      "command": "uv",
      "args": [
        "--directory",
        "/absolute/path/to/memori",
        "run",
        "--with",
        "mcp",
        "--with",
        "fastmcp",
        "--with-editable",
        ".",
        "python",
        "mcp/memori_mcp_server.py"
      ],
      "env": {
        "MEMORI_DATABASE_URL": "sqlite:///memori_mcp.db",
        "OPENAI_API_KEY": "your-openai-api-key-here"
      }
    }
  }
}
```

#### Windows

Edit `%APPDATA%\Claude\claude_desktop_config.json` with the same content (use Windows-style paths).

#### Linux

Edit `~/.config/Claude/claude_desktop_config.json` with the same content.

### Step 5: Restart Claude Desktop

After saving the configuration, restart Claude Desktop completely (quit and reopen).

### Step 6: Verify Installation

Look for the 🔨 hammer icon in Claude Desktop. Click it to see available MCP servers. You should see "memori" listed with 6 tools available.

## Configuration

### LLM Provider Configuration

The MCP server supports multiple LLM providers for memory processing. Choose one:

#### Option 1: OpenAI (Default)

```json
"env": {
  "MEMORI_DATABASE_URL": "sqlite:///memori_mcp.db",
  "OPENAI_API_KEY": "sk-your-api-key-here"
}
```

#### Option 2: OpenRouter (Recommended - Access 100+ Models)

OpenRouter provides access to 100+ LLMs including Claude, GPT-4, Llama, Mistral, and more through a single API.

```json
"env": {
  "MEMORI_DATABASE_URL": "sqlite:///memori_mcp.db",
  "OPENROUTER_API_KEY": "sk-or-v1-your-api-key-here",
  "OPENROUTER_MODEL": "anthropic/claude-3.5-sonnet",
  "OPENROUTER_APP_NAME": "Memori MCP Server",
  "OPENROUTER_SITE_URL": "https://github.com/GibsonAI/memori"
}
```

**Popular OpenRouter Models:**
- `anthropic/claude-3.5-sonnet` - Best for structured tasks
- `anthropic/claude-3-opus` - Most capable Claude model
- `openai/gpt-4o` - OpenAI's fastest GPT-4
- `openai/gpt-4-turbo` - GPT-4 with 128k context
- `meta-llama/llama-3.1-70b-instruct` - Free, open-source
- `google/gemini-pro-1.5` - Google's Gemini Pro
- `mistralai/mixtral-8x7b-instruct` - Fast, cost-effective

**Get your OpenRouter API key:** https://openrouter.ai/keys

#### Option 3: Azure OpenAI

```json
"env": {
  "MEMORI_DATABASE_URL": "sqlite:///memori_mcp.db",
  "AZURE_OPENAI_API_KEY": "your-azure-key",
  "AZURE_OPENAI_ENDPOINT": "https://your-resource.openai.azure.com",
  "AZURE_OPENAI_DEPLOYMENT": "your-deployment-name",
  "AZURE_OPENAI_API_VERSION": "2024-02-15-preview",
  "AZURE_OPENAI_MODEL": "gpt-4o"
}
```

#### Option 4: Custom OpenAI-Compatible Endpoint

For Ollama, LM Studio, LocalAI, or any OpenAI-compatible API:

```json
"env": {
  "MEMORI_DATABASE_URL": "sqlite:///memori_mcp.db",
  "LLM_BASE_URL": "http://localhost:11434/v1",
  "LLM_API_KEY": "not-needed-for-local",
  "LLM_MODEL": "llama3.1:8b"
}
```

### Environment Variables Reference

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `MEMORI_DATABASE_URL` | Database connection string | `sqlite:///memori_mcp.db` | No |
| **OpenAI** |||
| `OPENAI_API_KEY` | OpenAI API key | None | Yes (if using OpenAI) |
| `OPENAI_MODEL` | Model to use | `gpt-4o` | No |
| **OpenRouter** |||
| `OPENROUTER_API_KEY` | OpenRouter API key | None | Yes (if using OpenRouter) |
| `OPENROUTER_MODEL` | Model to use | `openai/gpt-4o` | No |
| `OPENROUTER_BASE_URL` | API base URL | `https://openrouter.ai/api/v1` | No |
| `OPENROUTER_APP_NAME` | Your app name (for rankings) | None | No |
| `OPENROUTER_SITE_URL` | Your site URL (for rankings) | None | No |
| **Azure OpenAI** |||
| `AZURE_OPENAI_API_KEY` | Azure API key | None | Yes (if using Azure) |
| `AZURE_OPENAI_ENDPOINT` | Azure endpoint URL | None | Yes (if using Azure) |
| `AZURE_OPENAI_DEPLOYMENT` | Deployment name | None | Yes (if using Azure) |
| `AZURE_OPENAI_API_VERSION` | API version | `2024-02-15-preview` | No |
| `AZURE_OPENAI_MODEL` | Model name | `gpt-4o` | No |
| **Custom/Local** |||
| `LLM_BASE_URL` | Custom API base URL | None | Yes (if using custom) |
| `LLM_API_KEY` | Custom API key | None | No (for local) |
| `LLM_MODEL` | Model to use | `gpt-4o` | No |

### Database Options

The server supports all Memori database backends:

#### SQLite (Default - Local File)
```json
"env": {
  "MEMORI_DATABASE_URL": "sqlite:///memori_mcp.db"
}
```

#### PostgreSQL (Production)
```json
"env": {
  "MEMORI_DATABASE_URL": "postgresql://user:password@localhost/memori"
}
```

#### MySQL (Production)
```json
"env": {
  "MEMORI_DATABASE_URL": "mysql://user:password@localhost/memori"
}
```

## Usage Examples

### Recording a Conversation

In Claude Desktop, you can say:

> "Record this conversation: I told you I'm working on a Python web app using FastAPI, and you suggested using SQLAlchemy for the database."

Claude will use the `record_conversation` tool to store this memory.

### Searching Memories

> "What do you remember about my Python projects?"

Claude will use `search_memories` to find relevant information.

### Getting Context

> "What were we talking about recently?"

Claude will use `get_recent_memories` to retrieve recent context.

### Memory Statistics

> "How many memories do you have about me?"

Claude will use `get_memory_statistics` to provide insights.

## Multi-User Support

The MCP server supports multi-tenant isolation using `user_id`. Each user's memories are completely isolated.

By default, the server uses:
- `user_id`: "default_user"
- `assistant_id`: "mcp_assistant"
- `session_id`: Optional (for conversation grouping)

You can specify different user IDs when using the tools:

```python
# In Claude, you might say:
"Record this for user 'alice': She prefers Python over JavaScript"
```

## Security Considerations

### API Keys

**Never commit your OpenAI API key to version control.** Always use environment variables or secure configuration management.

### Database Access

The MCP server has full access to the configured database. Ensure:
- Database credentials are kept secure
- Connection strings use authentication
- Multi-tenant isolation is maintained via `user_id`

### Multi-Tenant Isolation

All tools enforce user isolation. Memories from one user cannot be accessed by another user (unless explicitly shared).

## Development

### Running the Server Standalone

You can test the server without Claude Desktop:

```bash
# From the memori directory
cd mcp
python memori_mcp_server.py
```

This starts the MCP server in stdio mode, ready to accept MCP protocol messages.

### Testing Tools

Use the MCP Inspector for interactive testing:

```bash
npx @modelcontextprotocol/inspector uv --directory /path/to/memori run --with mcp --with fastmcp --with-editable . python mcp/memori_mcp_server.py
```

### Adding New Tools

To add a new tool to the MCP server:

1. Add a function decorated with `@mcp.tool()`:

```python
@mcp.tool()
def my_new_tool(param1: str, param2: int) -> Dict[str, Any]:
    """
    Description of what this tool does.

    Args:
        param1: Description
        param2: Description

    Returns:
        Result dictionary
    """
    # Implementation
    return {"success": True, "result": "..."}
```

2. Restart the MCP server (restart Claude Desktop)

### Adding New Resources

```python
@mcp.resource("memori://my-resource/{identifier}")
def get_my_resource(identifier: str) -> str:
    """Resource description"""
    return f"Resource data for {identifier}"
```

### Adding New Prompts

```python
@mcp.prompt()
def my_prompt_template(param: str) -> str:
    """Prompt description"""
    return f"Generated prompt using {param}"
```

## Troubleshooting

### Server Not Appearing in Claude

1. Check the config file location and syntax (valid JSON)
2. Ensure `uv` is installed and in PATH
3. Verify the absolute path to memori directory
4. Restart Claude Desktop completely
5. Check Claude Desktop logs:
   - macOS: `~/Library/Logs/Claude/`
   - Windows: `%APPDATA%\Claude\logs\`

### "Command not found: uv"

Install uv:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Database Connection Errors

- Check the `MEMORI_DATABASE_URL` format
- Ensure database server is running (for PostgreSQL/MySQL)
- Verify credentials are correct
- Check file permissions (for SQLite)

### Import Errors

Ensure Memori is installed in editable mode:
```bash
cd /path/to/memori
pip install -e .
```

### API Key Errors

- Verify `OPENAI_API_KEY` is set in the config
- Check the API key is valid
- Ensure you have credits/quota remaining

## Architecture

```
┌─────────────────────────────────────────┐
│         Claude Desktop / MCP Client     │
└────────────────┬────────────────────────┘
                 │ MCP Protocol (stdio)
        ┌────────▼──────────┐
        │  Memori MCP Server│
        │  (FastMCP)        │
        └────────┬──────────┘
                 │
        ┌────────▼──────────┐
        │   Memori SDK      │
        │  - Memory Agent   │
        │  - Search Engine  │
        │  - DB Manager     │
        └────────┬──────────┘
                 │
        ┌────────▼──────────┐
        │  SQL Database     │
        │  (SQLite/PG/MySQL)│
        └───────────────────┘
```

## Performance Considerations

### Database Choice

- **SQLite**: Great for personal use, single user, local storage
- **PostgreSQL**: Best for production, multi-user, cloud deployment
- **MySQL**: Alternative for production workloads

### Memory Management

The server caches Memori instances per user to avoid repeated initialization. Instances are kept in memory for the server's lifetime.

### Search Performance

- Uses database-native full-text search (FTS5, FULLTEXT, tsvector)
- Indexed on user_id, category, importance
- Limit results to avoid overwhelming the AI

## Examples

See the `examples/mcp/` directory for:
- `basic_usage.py` - Simple MCP client example
- `advanced_workflow.py` - Complex multi-tool workflows
- `custom_integration.py` - Integrating with your own MCP client

## FAQ

### Q: Can I use this with other AI assistants besides Claude?

Yes! Any MCP-compatible client can use this server. The protocol is open and client-agnostic.

### Q: How much does it cost to run?

The server itself is free (open-source). Costs:
- Database: Free (SQLite) or hosting costs (PostgreSQL/MySQL)
- OpenAI API: Used for memory processing (~$0.01-0.10 per conversation)

### Q: Can multiple users share memories?

By default, no. Each `user_id` has isolated memories. You could build cross-user sharing by creating a "shared" user_id.

### Q: How do I backup my memories?

Memories are stored in your database. Backup strategies:
- SQLite: Copy the .db file
- PostgreSQL/MySQL: Use standard database backup tools (pg_dump, mysqldump)

### Q: Can I export my memories?

Yes! Memories are stored in standard SQL tables. You can:
- Query directly with SQL
- Export to CSV/JSON
- Use Memori's export tools (coming soon)

### Q: How long are memories retained?

- **Short-term**: ~7 days (configurable via `expires_at`)
- **Long-term**: Permanent (promoted from short-term based on importance)
- **Chat history**: Permanent (unless manually deleted)

## Resources

- **Memori Documentation**: https://www.gibsonai.com/docs/memori
- **MCP Documentation**: https://modelcontextprotocol.io
- **FastMCP**: https://github.com/jlowin/fastmcp
- **Discord Community**: https://discord.gg/abD4eGym6v

## Contributing

Contributions welcome! See [CONTRIBUTING.md](../CONTRIBUTING.md) for guidelines.

## License

Apache 2.0 - see [LICENSE](../LICENSE)

---

**Questions or issues?** Open an issue on [GitHub](https://github.com/GibsonAI/memori/issues) or join our [Discord](https://discord.gg/abD4eGym6v).
