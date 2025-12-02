# Memori + SQLite Example

Example showing how to use Memori with SQLite.

## Quick Start

1. **Install dependencies**:
   ```bash
   uv sync
   ```

2. **Set environment variables**:
   ```bash
   export OPENAI_API_KEY=your_api_key_here
   ```

3. **Run the example**:
   ```bash
   uv run python main.py
   ```

## What This Example Demonstrates

- **Automatic persistence**: All conversation messages are automatically stored in the SQLite database
- **Context preservation**: Memori injects relevant conversation history into each LLM call
- **Interactive chat**: Type messages and see how Memori maintains context across the conversation
- **Portable**: The database file can be copied, backed up, or shared easily
