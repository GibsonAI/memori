# Memori + CockroachDB Example

**Memori + CockroachDB** brings durable, distributed memory to AI - instantly, globally, and at any scale. Memori transforms conversations into structured, queryable intelligence, while CockroachDB keeps that memory available, resilient, and consistently accurate across regions. Deploy and scale effortlessly from prototype to production with zero downtime on enterprise-grade infrastructure. Give your AI a foundation to remember, reason, and evolve - with the simplicity of cloud and the reliability and power of distributed SQL.

## Getting Started

Install Memori:

```bash
pip install memori
```

Sign up for [CockroachDB Cloud](https://www.cockroachlabs.com/product/cloud/).

You may need to record the database connection string for your implementation. Once you've signed up, your database is provisioned and ready for use with Memori.

## Quick Start

1. **Install dependencies**:
   ```bash
   uv sync
   ```

2. **Set environment variables**:
   ```bash
   export OPENAI_API_KEY=your_api_key_here
   export COCKROACHDB_CONNECTION_STRING=postgresql://user:password@host:26257/defaultdb?sslmode=verify-full
   ```

3. **Run the example**:
   ```bash
   uv run python main.py
   ```

## What This Example Demonstrates

- **Serverless CockroachDB**: Connect to CockroachDB's cloud serverless Postgres with zero database management
- **Automatic persistence**: All conversation messages are automatically stored in your CockroachDB database
- **Context preservation**: Memori injects relevant conversation history into each LLM call
- **Interactive chat**: Type messages and see how Memori maintains context across the conversation
