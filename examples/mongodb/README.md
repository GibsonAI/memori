# Memori + MongoDB Example

Example showing how to use Memori with MongoDB.

## Quick Start

1. **Install dependencies**:
   ```bash
   uv sync
   ```

2. **Set environment variables**:
   ```bash
   export OPENAI_API_KEY=your_api_key_here
   export MONGODB_CONNECTION_STRING=mongodb+srv://user:password@cluster.mongodb.net/dbname
   ```

3. **Run the example**:
   ```bash
   uv run python main.py
   ```

## What This Example Demonstrates

- **NoSQL flexibility**: Store conversation data in MongoDB's document model
- **Automatic persistence**: All conversation messages are automatically stored in MongoDB collections
- **Context preservation**: Memori injects relevant conversation history into each LLM call
- **Interactive chat**: Type messages and see how Memori maintains context across the conversation
- **Cloud-ready**: Works seamlessly with MongoDB Atlas free tier
