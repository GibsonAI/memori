# Multi-User Memori Examples

This folder demonstrates how Memori can handle multiple users with isolated memory sessions. Each user gets their own namespace within a shared database, ensuring complete memory isolation while optimizing resource usage.

## Architecture

- **Shared Database**: All users share a single database file
- **Namespace Isolation**: Each user gets a unique namespace (e.g., `user_alice`, `fastapi_user_bob`)
- **Memory Persistence**: User conversations persist across sessions
- **Conscious Ingestion**: Memori automatically stores relevant context

## Examples

### 1. Simple Multi-User Demo (`simple_multiuser.py`)
Basic demonstration of creating isolated memory instances for different users.

```bash
python simple_multiuser.py
```

**Features:**
- Shows how to create user-specific namespaces
- Demonstrates memory isolation between users
- Simple command-line interface

### 2. FastAPI Multi-User Application (`fastapi_multiuser_app.py`)
Full-featured web API with Swagger UI for testing multi-user functionality.

```bash
# Install dependencies
pip install -r requirements.txt

# Run the application
uvicorn fastapi_multiuser_app:app --reload --host 0.0.0.0 --port 8000
```

**Features:**
- 🚀 **FastAPI** with automatic OpenAPI documentation
- 📖 **Swagger UI** at http://localhost:8000/docs
- 📚 **ReDoc** at http://localhost:8000/redoc
- 🔒 **Isolated memory** per user using namespaces
- 💾 **Persistent** memory across sessions
- ✅ **Type validation** with Pydantic models

## API Endpoints

### POST `/chat`
Send a chat message for a specific user
```json
{
  "user_id": "alice",
  "message": "Hello, remember my favorite color is blue"
}
```

### GET `/users`
List all active users with memory sessions

### GET `/user/{user_id}/info`
Get detailed information about a user's memory session

### GET `/health`
Health check endpoint

## Quick Test with Swagger UI

1. **Start the FastAPI app**: `uvicorn fastapi_multiuser_app:app --reload`
2. **Open Swagger UI**: http://localhost:8000/docs
3. **Try the POST /chat endpoint** with different user IDs:
   - Send a message as "alice": "My favorite color is blue"
   - Send a message as "bob": "I'm learning Python"
   - Send another message as "alice": "What's my favorite color?"
   - See how Alice's memory is isolated from Bob's!

## Testing Memory Isolation

```python
# User Alice
POST /chat
{
  "user_id": "alice",
  "message": "I work as a software engineer"
}

# User Bob  
POST /chat
{
  "user_id": "bob", 
  "message": "I'm a student studying biology"
}

# Test Alice's memory
POST /chat
{
  "user_id": "alice",
  "message": "What do I do for work?"
}
# Response will remember Alice is a software engineer

# Test Bob's memory
POST /chat
{
  "user_id": "bob",
  "message": "What am I studying?"
}
# Response will remember Bob is studying biology
```

## Database Structure

```
fastapi_multiuser_memory.db
├── namespace: fastapi_user_alice
│   ├── User conversations
│   └── Context memory
├── namespace: fastapi_user_bob
│   ├── User conversations  
│   └── Context memory
└── namespace: fastapi_user_carol
    ├── User conversations
    └── Context memory
```

## Dependencies

- **FastAPI**: Modern web framework for APIs
- **Uvicorn**: ASGI server for running FastAPI
- **Pydantic**: Data validation using Python type annotations
- **Memori SDK**: Memory management and conscious ingestion
- **LiteLLM**: LLM completions with multiple providers
- **Python-dotenv**: Environment variable management

## Environment Variables

Create a `.env` file:
```env
OPENAI_API_KEY=your_api_key_here
# or other LLM provider keys
```

## Benefits

1. **Resource Efficiency**: Single database file instead of multiple
2. **Scalability**: Better performance with many users  
3. **Isolation**: Complete memory separation between users
4. **API-First**: RESTful design with automatic documentation
5. **Type Safety**: Pydantic models ensure data validation
6. **Interactive Testing**: Swagger UI for easy API exploration
