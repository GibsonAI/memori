# Memori + DeepSeek Example

This example demonstrates how to use Memori with DeepSeek AI.

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up your DeepSeek API key:
```bash
export DEEPSEEK_API_KEY="your-api-key"
```

Or create a `.env` file:
```bash
cp .env.example .env
# Edit .env and add your API key
```

3. Run the example:
```bash
python main.py
```

## How It Works

This example shows Memori's memory capabilities with DeepSeek:

1. **First conversation**: Establishes facts (favorite color, city)
2. **Second conversation**: DeepSeek automatically recalls the favorite color
3. **Third conversation**: DeepSeek remembers the city

Memori automatically captures and stores conversation context, making it available for future interactions.

## Requirements

- Python 3.10+
- DeepSeek API key
- Memori Python SDK
