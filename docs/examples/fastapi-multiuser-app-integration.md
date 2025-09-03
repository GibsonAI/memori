# FastAPI Multi-User Integration Example

Complete demonstration of Memori integration in a FastAPI application with multiple isolated user memories.

## Overview

This example shows how to:

- Create a production-ready FastAPI application with Memori
- Implement isolated memory spaces for multiple users
- Build RESTful endpoints for chat and user management
- Provide interactive API documentation with Swagger UI
- Maintain persistent memory across user sessions

## Code

```python title="fastapi_multiuser_app.py"
from datetime import datetime
from typing import Dict, List
from fastapi import FastAPI, HTTPException
from memori import Memori

# Initialize FastAPI app
app = FastAPI(
    title="Multi-User Memori API",
    description="A FastAPI application demonstrating multi-user memory isolation",
    version="1.0.0"
)

# Shared database for all users
WEB_DATABASE_PATH = "sqlite:///fastapi_multiuser_memory.db"

# Global storage for user memories
user_memories: Dict[str, Memori] = {}

def get_or_create_user_memory(user_id: str) -> Memori:
    """Get existing or create new Memori instance for user"""
    if user_id not in user_memories:
        user_memory = Memori(
            database_connect=WEB_DATABASE_PATH,
            namespace=f"fastapi_user_{user_id}",
            conscious_ingest=True
        )
        user_memory.enable()
        user_memories[user_id] = user_memory
    return user_memories[user_id]

@app.post("/chat")
async def chat(message_data: ChatMessage):
    """Send chat message for specific user"""
    user_memory = get_or_create_user_memory(message_data.user_id)
    response = completion(
        model="gpt-4o-mini", 
        messages=[{"role": "user", "content": message_data.message}]
    )
    return ChatResponse(
        success=True,
        response=response.choices[0].message.content,
        user_id=message_data.user_id
    )

# Additional endpoints omitted for brevity
```

## What Happens

### 1. Application Initialization
- FastAPI app created with OpenAPI documentation
- Shared SQLite database configured for all users
- Global dictionary tracks user memory instances

### 2. User Memory Management
- Each user gets isolated namespace (`fastapi_user_{user_id}`)
- Memory instances created on-demand and cached
- Conscious ingestion enabled for intelligent context

### 3. Chat Processing
- Incoming messages routed to user's memory space
- Context automatically injected from user history
- Responses enhanced with remembered preferences

### 4. Data Persistence
- All conversations stored in shared database
- Namespaces prevent cross-user contamination
- Memory persists across user sessions

## Database Contents

The shared SQLite database (`fastapi_multiuser_memory.db`) contains:

```sql
CREATE TABLE memory_entries (
    id INTEGER PRIMARY KEY,
    namespace TEXT,      -- User isolation (fastapi_user_{user_id})
    timestamp TEXT,      -- ISO format datetime
    content TEXT,        -- Message content
    metadata JSON,       -- Additional context
    importance REAL      -- Conscious ingestion score
);
```

## Setup Instructions

1. Install required packages:
```bash
pip install fastapi uvicorn python-dotenv litellm memori-sdk
```

2. Set environment variables:
```bash
OPENAI_API_KEY=your_api_key_here
```

3. Run the application:
```bash
uvicorn fastapi_multiuser_app:app --reload
```

4. Visit documentation:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Use Cases

- **Chat Applications**: Multi-user chat systems with memory
- **Customer Support**: Persistent context for each customer
- **Educational Platforms**: Student-specific learning history
- **Personal Assistants**: Individual user preferences
- **Team Collaboration**: Isolated workspace memories

## Best Practices

1. **Memory Isolation**
   - Use consistent namespace patterns
   - Validate user_id inputs
   - Clear inactive memories

2. **Performance**
   - Cache active memory instances
   - Implement session timeouts
   - Monitor database growth

3. **Security**
   - Sanitize user inputs
   - Implement authentication
   - Regular database backups

## Next Steps

1. Add authentication middleware
2. Implement memory cleanup for inactive users
3. Add memory export/import functionality
4. Create user preference management
5. Add conversation history endpoints

## Related Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Memori SDK Reference](https://github.com/GibsonAI/memori)
- [SQLite Documentation](https://www.sqlite.org/docs.html)
- [OpenAPI Specification](https://swagger.io/specification/)

The complete example with all endpoints is available in the [examples directory](https://github.com/GibsonAI/memori/blob/main/examples/multiple-users/fastapi_multiuser_app.py).