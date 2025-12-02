# Memori + Neon Example

Sign up for [Neon serverless Postgres](https://neon.tech).

You may need to record the database connection string for your implementation. Once you've signed up, your database is provisioned and ready for use with Memori.

## Quick Start

1. **Install dependencies**:
   ```bash
   uv sync
   ```

2. **Set environment variables**:
   ```bash
   export OPENAI_API_KEY=your_api_key_here
   export NEON_CONNECTION_STRING=postgresql://user:pass@ep-xyz-123.us-east-2.aws.neon.tech/dbname?sslmode=require
   ```

3. **Run the example**:
   ```bash
   uv run python main.py
   ```

## What This Example Demonstrates

- **Serverless PostgreSQL**: Connect to Neon's serverless Postgres with zero database management
- **Automatic persistence**: All conversation messages are automatically stored in your Neon database
- **Context preservation**: Memori injects relevant conversation history into each LLM call
- **Interactive chat**: Type messages and see how Memori maintains context across the conversation
