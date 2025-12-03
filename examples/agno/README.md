# Memori + Agno Example

Example showing how to use Memori with Agno agents to add persistent memory across conversations.

## Quick Start

1. **Install dependencies**:
   ```bash
   uv sync
   ```

2. **Set your OpenAI API key**:
   Create a `.env` file:
   ```bash
   OPENAI_API_KEY=your_api_key_here
   ```

3. **Run the example**:
   ```bash
   uv run python main.py
   ```

## What This Example Demonstrates

- **Agno integration**: Use Memori with Agno's agent framework
- **Persistent memory**: Conversations are stored in SQLite and recalled automatically
- **Context awareness**: The agent remembers details from earlier in the conversation
- **Customer support use case**: Shows a realistic scenario where memory is valuable
