# Memori + Nebius AI Studio Example

Example showing how to use Memori with Nebius AI Studio to add persistent memory across conversations.

[Nebius AI Studio](https://nebius.com/ai-studio) provides an OpenAI-compatible API for state-of-the-art open-source models including Llama, Qwen, DeepSeek, and more. Since Nebius uses the OpenAI SDK, it works seamlessly with Memori's automatic instrumentation.

## Quick Start

1. **Install dependencies**:
   ```bash
   uv sync
   ```

2. **Get a Nebius API key**:
   - Sign up at [https://studio.nebius.ai/](https://studio.nebius.ai/)
   - Get your API key from the dashboard

3. **Set your API key**:
   Create a `.env` file:
   ```bash
   NEBIUS_API_KEY=your_api_key_here
   ```

4. **Run the example**:
   ```bash
   uv run python main.py
   ```

## What This Example Demonstrates

- **Nebius AI Studio integration**: Use Memori with Nebius's OpenAI-compatible API
- **Open-source models**: Access to models like Llama 3.1 70B with persistent memory
- **Automatic registration**: Simply use `.llm.register(client)` - Memori auto-detects Nebius
- **Persistent memory**: Conversations are stored in SQLite and recalled automatically
- **Context awareness**: The LLM remembers details from earlier in the conversation

## Available Models

Nebius AI Studio supports 60+ open-source models. Check the [model catalog](https://studio.nebius.ai/) for the full list including:
- Meta Llama 3.1 (8B, 70B, 405B)
- Qwen 2.5
- DeepSeek
- Mistral
- And many more

## Alternative Base URLs

Nebius offers multiple endpoints:
- Studio API: `https://api.studio.nebius.com/v1/`
- Token Factory: `https://api.tokenfactory.nebius.com/`

Simply change the `base_url` parameter to use a different endpoint.
