# Simple Multi-User Memory Integration

Demonstration of isolated memory management for multiple users using Memori namespaces.

## Overview

This example shows how to:

- Create isolated memory spaces for different users
- Manage shared database with unique namespaces
- Maintain memory separation between users
- Dynamically add new users at runtime
- Test memory isolation and context boundaries

## Code

```python title="simple_multiuser.py"
from dotenv import load_dotenv
from litellm import completion
from memori import Memori

load_dotenv()

# Global database for all users
DATABASE_PATH = "sqlite:///multiuser_memory.db"

def create_user_memory(user_id: str) -> Memori:
    """Create a Memori instance for a specific user using unique namespace"""
    print(f"👤 Creating memory for user: {user_id}")

    # Each user gets their own namespace in the shared database
    user_memory = Memori(
        database_connect=DATABASE_PATH,
        namespace=f"user_{user_id}",
        conscious_ingest=True,
    )

    user_memory.enable()
    return user_memory

def user_chat(user_id: str, message: str) -> str:
    """Handle a chat message from a specific user"""
    response = completion(
        model="gpt-4o-mini", 
        messages=[{"role": "user", "content": message}]
    )
    return response.choices[0].message.content

# Full example code continues...
```

## What Happens

### 1. Shared Database Setup
```python
DATABASE_PATH = "sqlite:///multiuser_memory.db"
```
- Single database file stores all user memories
- Efficient resource usage with shared storage
- Simplified deployment and maintenance

### 2. User Memory Initialization
```python
user_memory = Memori(
    database_connect=DATABASE_PATH,
    namespace=f"user_{user_id}",
    conscious_ingest=True,
)
```
- Creates isolated namespace per user
- Enables conscious ingestion for smart context
- Maintains memory boundaries automatically

### 3. Memory Isolation
- Each user's context stays separate
- Cross-user information leakage prevented
- Dynamic user addition supported

## Database Contents

The shared SQLite database contains:

```sql
CREATE TABLE memories (
    id INTEGER PRIMARY KEY,
    namespace TEXT,  -- Format: user_{user_id}
    content TEXT,    -- Memory content
    timestamp DATETIME,
    metadata JSON
);
```

## Setup Requirements

1. Install required packages:
```bash
pip install memori litellm python-dotenv
```

2. Configure environment variables:
```env
OPENAI_API_KEY=your_api_key_here
```

3. Initialize database:
```python
from memori import Memori
Memori.init_database("sqlite:///multiuser_memory.db")
```

## Use Cases

- **Chat Applications**: Separate memory for each user
- **Customer Support**: Individual context per customer
- **Educational Platforms**: Student-specific learning history
- **Multi-tenant Systems**: Isolated tenant memories

## Best Practices

1. **Namespace Convention**
   - Use consistent prefix: `user_`
   - Add tenant/org identifiers if needed
   - Keep namespaces unique and descriptive

2. **Memory Management**
   - Enable conscious ingestion for smart context
   - Implement user cleanup procedures
   - Monitor database growth

3. **Security Considerations**
   - Validate user IDs before namespace creation
   - Implement access controls
   - Regular security audits

## Next Steps

- Implement user authentication
- Add memory persistence controls
- Scale with production database
- Monitor memory usage
- Add backup procedures

## Related Resources

- [FastAPI Multi-User Example](../fastapi-multiuser.md)
- [Production Configuration](../advanced-config.md)
- [Memory Security Guide](../security.md)
- [Database Scaling](../scaling.md)

This implementation provides a solid foundation for multi-user applications while maintaining memory isolation and efficient resource usage.