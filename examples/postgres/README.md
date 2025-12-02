# Memori + PostgreSQL Example

Example showing how to use Memori with PostgreSQL.

## Quick Start

1. **Install dependencies**:
   ```bash
   uv sync
   ```

2. **Set environment variables**:
   ```bash
   export OPENAI_API_KEY=your_api_key_here
   export DATABASE_CONNECTION_STRING=postgresql+psycopg://user:password@localhost:5432/dbname
   ```

3. **Run the example**:
   ```bash
   uv run python main.py
   ```

## What This Example Demonstrates

- **PostgreSQL integration**: Connect to any PostgreSQL database (local, AWS RDS, or other managed database services)
- **Automatic persistence**: All conversation messages are automatically stored in your database
- **Context preservation**: Memori injects relevant conversation history into each LLM call
- **Interactive chat**: Type messages and see how Memori maintains context across the conversation
