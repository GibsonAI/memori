# Memori MCP Server - Quick Start Guide

Get the Memori MCP server running in Claude Desktop in under 5 minutes!

## Prerequisites

- Claude Desktop installed
- Python 3.10+ installed
- OpenAI API key (for memory processing)

## 5-Minute Setup

### Step 1: Install uv (30 seconds)

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### Step 2: Clone Memori (1 minute)

```bash
git clone https://github.com/GibsonAI/memori.git
cd memori
```

### Step 3: Configure Claude Desktop (2 minutes)

**macOS**: Open `~/Library/Application Support/Claude/claude_desktop_config.json`

**Windows**: Open `%APPDATA%\Claude\claude_desktop_config.json`

**Linux**: Open `~/.config/Claude/claude_desktop_config.json`

Add this configuration (replace `/absolute/path/to/memori` and `your-api-key`):

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

### Step 4: Restart Claude Desktop (30 seconds)

Completely quit and restart Claude Desktop.

### Step 5: Verify (30 seconds)

Look for the 🔨 hammer icon in Claude Desktop. You should see the "memori" server with 6 tools available.

## Try It Out!

Start a conversation in Claude:

**You**: "Record this: I'm working on a Python FastAPI project with PostgreSQL"

**Claude**: [Uses the record_conversation tool and confirms]

**You**: "What do you remember about my projects?"

**Claude**: [Uses search_memories to recall what you told it]

That's it! Claude now has persistent memory.

## What's Happening?

1. **When you talk to Claude**, it can use Memori tools to remember important information
2. **Conversations are stored** in a local SQLite database (memori_mcp.db)
3. **Memories are processed** using OpenAI to extract entities, categories, and importance
4. **Claude can search** these memories in future conversations

## Common Issues

### "Server not found" or hammer icon doesn't appear

- Check the config file path is correct for your OS
- Verify the JSON syntax is valid (use a JSON validator)
- Make sure the absolute path to memori is correct
- Restart Claude Desktop completely

### "Command not found: uv"

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Add to PATH (if needed)
export PATH="$HOME/.cargo/bin:$PATH"
```

### "OpenAI API Error"

- Check your OPENAI_API_KEY is correct
- Verify you have API credits
- Ensure the key has necessary permissions

### "Database errors"

- Check the MEMORI_DATABASE_URL path is writable
- For SQLite, ensure the directory exists
- For PostgreSQL/MySQL, verify connection credentials

## Next Steps

- Read the [full MCP README](README.md) for advanced usage
- Try the [example scripts](../examples/mcp/)
- Configure a production database (PostgreSQL/MySQL)
- Explore the 6 available tools in Claude
- Check memory statistics with "How many memories do you have about me?"

## Database Options

### Local SQLite (Default - Good for personal use)
```json
"MEMORI_DATABASE_URL": "sqlite:///memori_mcp.db"
```

### PostgreSQL (Production)
```json
"MEMORI_DATABASE_URL": "postgresql://user:password@localhost/memori"
```

### MySQL (Production)
```json
"MEMORI_DATABASE_URL": "mysql://user:password@localhost/memori"
```

### Cloud PostgreSQL (Neon, Supabase, etc.)
```json
"MEMORI_DATABASE_URL": "postgresql://user:password@host.region.provider.com/memori"
```

## Available Tools

Once configured, Claude can use these tools:

1. **record_conversation** - Store conversations
2. **search_memories** - Find relevant memories
3. **get_recent_memories** - Get recent context
4. **get_memory_statistics** - View memory stats
5. **get_conversation_history** - See past conversations
6. **clear_session_memories** - Reset session

## Multi-User Setup

Each user gets isolated memories by default. To use with different users:

**In Claude**: "Record this for user 'alice': She prefers Python over JavaScript"

The server automatically handles multi-tenant isolation.

## Security Notes

- Your database is LOCAL (SQLite) or on YOUR server (PostgreSQL/MySQL)
- OpenAI API is only used for processing (extracting entities/importance)
- No data is sent to Memori servers (it's open-source, runs locally)
- Multi-tenant isolation ensures user privacy

## Cost Estimate

- **Memori software**: Free (open-source)
- **Database**: Free (SQLite) or your hosting cost
- **OpenAI API**: ~$0.01-0.10 per conversation for processing
- **Total**: Minimal cost, full control

## Support

- **GitHub Issues**: https://github.com/GibsonAI/memori/issues
- **Discord**: https://discord.gg/abD4eGym6v
- **Documentation**: https://www.gibsonai.com/docs/memori

## What's Next?

Explore advanced features:
- Session management for different contexts
- Category filtering (facts, preferences, skills)
- Importance-based search
- Long-term vs short-term memory
- Custom memory processing

Happy remembering! 🧠
