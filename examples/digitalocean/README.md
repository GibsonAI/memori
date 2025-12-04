# Memori + DigitalOcean Gradient Example

Example showing how to use Memori with DigitalOcean Gradient AI Agents to add persistent memory across conversations.

## Quick Start

1. **Install dependencies**:
   ```bash
   uv sync
   ```

2. **Set environment variables**:
   Create a `.env` file:
   ```bash
   AGENT_ENDPOINT=your_gradient_agent_endpoint
   AGENT_ACCESS_KEY=your_gradient_access_key
   DATABASE_CONNECTION_STRING=postgresql+psycopg2://user:password@localhost:5432/dbname
   ```

3. **Run the example**:
   ```bash
   uv run python main.py
   ```

## What This Example Demonstrates

- **DigitalOcean Gradient integration**: Use Memori with DigitalOcean's Gradient AI platform
- **Persistent memory**: Conversations are stored in PostgreSQL and recalled automatically
- **OpenAI-compatible API**: Gradient agents use OpenAI's API format for easy integration
- **Context awareness**: The agent remembers details from earlier in the conversation
