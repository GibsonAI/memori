# Memori in Production

Learn how to use Memori in real-world applications, from simple personal projects to large-scale enterprise systems.

## What is Production-Ready?

Memori is built for production from the ground up. It handles memory for AI applications that serve thousands of users, process millions of conversations, and need reliable, intelligent context management.

### Key Production Features

- **Multi-User Support**: Each user gets their own memory space using namespaces
- **Database Options**: SQLite for development, PostgreSQL/MySQL for production  
- **Cloud Ready**: Works with AWS, Azure, Google Cloud databases
- **Memory Modes**: Choose between fast (conscious) or comprehensive (auto) memory
- **Error Handling**: Graceful failures that don't break your app
- **Performance**: Optimized for speed and low token usage

## Simple Production Setup

### 1. Basic Production Configuration

```python
from memori import Memori
from litellm import completion

# Production-ready setup
memori = Memori(
    database_connect="postgresql://user:pass@your-db.com/memori",
    namespace="your_app_name",
    conscious_ingest=True,  # Fast memory mode
    auto_ingest=False      # Disable for better performance
)
memori.enable()

# Your app works normally - memory happens automatically
response = completion(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": "Help me with my project"}]
)
```

### 2. Multi-User Applications

```python
def get_user_memory(user_id: str):
    """Each user gets their own memory space"""
    return Memori(
        database_connect="postgresql://user:pass@your-db.com/memori",
        namespace=f"user_{user_id}",  # Isolates users' memories
        conscious_ingest=True
    )

# In your API endpoint
@app.post("/chat")
def chat(user_id: str, message: str):
    user_memory = get_user_memory(user_id)
    user_memory.enable()
    
    response = completion(
        model="gpt-4o-mini", 
        messages=[{"role": "user", "content": message}]
    )
    return {"response": response.choices[0].message.content}
```

### 3. Environment Variables

Set these in your production environment:

```bash
# Database
MEMORI_DATABASE__CONNECTION_STRING=postgresql://user:pass@db.com/memori

# AI Provider
MEMORI_AGENTS__OPENAI_API_KEY=sk-your-key-here

# Memory Settings
MEMORI_MEMORY__NAMESPACE=production_app
MEMORI_LOGGING__LEVEL=INFO
```

Then use auto-configuration:

```python
from memori import ConfigManager, Memori

# Loads from environment automatically
config = ConfigManager()
config.auto_load()

memori = Memori()  # Uses loaded config
memori.enable()
```

## Production Examples

### Web Application (FastAPI)

A REST API serving multiple users with isolated memories:

```python
from fastapi import FastAPI
from memori import Memori
from litellm import completion

app = FastAPI()
user_memories = {}  # Cache user memory instances

@app.post("/chat/{user_id}")
def chat(user_id: str, message: str):
    # Get or create user memory
    if user_id not in user_memories:
        user_memories[user_id] = Memori(
            database_connect="postgresql://...",
            namespace=f"user_{user_id}",
            conscious_ingest=True
        )
        user_memories[user_id].enable()
    
    # Chat with memory
    response = completion(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": message}]
    )
    
    return {"response": response.choices[0].message.content}

@app.get("/memory/{user_id}")
def get_memory_stats(user_id: str):
    if user_id in user_memories:
        return user_memories[user_id].get_memory_stats()
    return {"error": "User not found"}
```

### Streamlit App with Memory

An interactive app that remembers user conversations:

```python
import streamlit as st
from memori import Memori
from litellm import completion

# Initialize memory for session
if "memori" not in st.session_state:
    st.session_state.memori = Memori(
        database_connect="sqlite:///streamlit_memory.db",
        namespace=f"session_{st.session_state.get('session_id', 'default')}",
        conscious_ingest=True
    )
    st.session_state.memori.enable()

st.title("AI Assistant with Memory")

# Chat input
if user_input := st.chat_input("Type your message..."):
    # Display user message
    st.chat_message("user").write(user_input)
    
    # Get AI response with memory
    with st.chat_message("assistant"):
        response = completion(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": user_input}]
        )
        st.write(response.choices[0].message.content)
```

### Research Agent with Memory

An AI agent that builds knowledge over time:

```python
from agno.agent import Agent
from agno.tools.memori import MemoriTools
from memori import Memori

# Setup memory for research agent
memori = Memori(
    database_connect="postgresql://user:pass@db.com/research",
    namespace="research_agent",
    conscious_ingest=True,
    auto_ingest=True  # For comprehensive research context
)

# Create agent with memory tools
research_agent = Agent(
    tools=[MemoriTools(
        database_connect="postgresql://user:pass@db.com/research",
        namespace="research_agent"
    )],
    model="gpt-4o",
    instructions="""
    You are a research agent with persistent memory.
    Always search your memory first for related research.
    Build upon previous findings and maintain research continuity.
    """
)

# Research builds up over time
response = research_agent.run("Research the latest AI developments")
```

## Database Setup for Production

### GibsonAI (Serverless)

Get **FREE** serverless database instance in GibsonAI platform. You can just prompt to create and deploy a new database.

**[GibsonAI Integration Guide](open-source/databases/gibsonai)**

### PostgreSQL (Recommended)

Best for production applications with multiple users:

```python
# Connection string format
DATABASE_URL = "postgresql://username:password@host:port/database"

memori = Memori(
    database_connect=DATABASE_URL,
    namespace="your_app"
)
```

#### Cloud PostgreSQL Options:

**Neon (Serverless)**
```python
memori = Memori(
    database_connect="postgresql://user:pass@ep-cool-name.us-east-2.aws.neon.tech/memori",
    namespace="production"
)
```

**Supabase**
```python  
memori = Memori(
    database_connect="postgresql://postgres:pass@db.supabase.co:5432/postgres",
    namespace="production"
)
```

**AWS RDS**
```python
memori = Memori(
    database_connect="postgresql://user:pass@mydb.amazonaws.com:5432/memori",
    namespace="production"
)
```

### MySQL Support

```python
memori = Memori(
    database_connect="mysql://user:pass@localhost/memori",
    namespace="production"
)
```

### SQLite (Development Only)

Simple for development and testing:

```python
memori = Memori(
    database_connect="sqlite:///my_app_memory.db",
    namespace="development"
)
```

## Memory Modes for Production

Choose the right memory mode for your application:

### Conscious Mode (Recommended)

Best for most production applications - fast and efficient:

```python
memori = Memori(
    conscious_ingest=True,   # Essential memory only
    auto_ingest=False,       # Disabled for performance
    database_connect="postgresql://..."
)
```

**Benefits:**
- **Fast**: ~150 tokens of essential context
- **Cost-effective**: Minimal token usage  
- **Smart**: Most important memories readily available
- **Performance**: No search overhead

**Best for:**
- Customer support bots
- Personal assistants  
- Simple chat applications
- Cost-sensitive applications

### Auto Mode (Comprehensive)

Best for research, analysis, and complex applications:

```python
memori = Memori(
    conscious_ingest=False,  # Disabled for simplicity
    auto_ingest=True,        # Dynamic context search
    database_connect="postgresql://..."
)
```

**Benefits:**
- **Comprehensive**: Searches entire memory database
- **Relevant**: Context based on current query
- **Rich**: More detailed context per conversation

**Best for:**
- Research agents
- Complex problem-solving
- Knowledge management
- Detailed analysis tasks

### Combined Mode (Best of Both)

For applications that need both speed and depth:

```python
memori = Memori(
    conscious_ingest=True,   # Essential working memory
    auto_ingest=True,        # Plus dynamic search
    database_connect="postgresql://..."
)
```

**Benefits:**
- **Essential + Relevant**: Working memory + query-specific context
- **Balanced**: Good performance with comprehensive context
- **Flexible**: Adapts to different conversation types

**Best for:**
- Enterprise applications
- Multi-purpose AI assistants
- Production systems with varied use cases

## Performance Optimization

### Connection Pooling

For high-traffic applications:

```python
from memori import Memori

# PostgreSQL with connection pooling
memori = Memori(
    database_connect="postgresql://user:pass@db.com/memori?pool_size=20&max_overflow=0",
    namespace="high_traffic_app"
)
```

### Memory Cleanup

Automatically clean old memories:

```python
memori = Memori(
    database_connect="postgresql://...",
    memory_filters={
        "retention_days": 30,        # Keep memories for 30 days
        "min_importance": 0.3,       # Only keep important memories
        "max_memories": 10000        # Limit total memories
    }
)
```

### Token Optimization

Compare token usage across modes:

```python
# Traditional: Full conversation history
# ~2000+ tokens every request

# Conscious Mode: Essential memories
# ~150 tokens once per session  

# Auto Mode: Relevant context
# ~250 tokens per request

# Combined Mode: Both
# ~300 tokens per request
```

## Error Handling

Memori handles errors gracefully and won't break your application:

```python
from memori import Memori
import logging

# Setup logging to see what happens
logging.basicConfig(level=logging.INFO)

memori = Memori(
    database_connect="postgresql://...",
    conscious_ingest=True
)

try:
    memori.enable()
except Exception as e:
    # Memori will log the error but continue working
    print(f"Memory initialization issue: {e}")
    # Your app continues working without memory
```

### Fallback Strategies

Memori automatically handles common issues:

- **Database Connection Lost**: Tries to reconnect automatically
- **AI Provider Issues**: Continues recording, skips analysis temporarily  
- **Memory Analysis Fails**: Falls back to basic recording
- **Search Errors**: Returns empty context instead of failing

## Monitoring Production

### Memory Statistics

Track how your memory system is performing:

```python
# Get memory statistics
stats = memori.get_memory_stats()
print(f"Total conversations: {stats.get('chat_history_count', 0)}")
print(f"Short-term memories: {stats.get('short_term_count', 0)}")
print(f"Long-term memories: {stats.get('long_term_count', 0)}")

# Essential memories (conscious mode)
essential = memori.get_essential_conversations()
print(f"Essential memories: {len(essential)}")
```

### Health Checks

For monitoring systems:

```python
def check_memori_health():
    try:
        stats = memori.get_memory_stats()
        return {
            "status": "healthy",
            "memory_count": stats.get('long_term_count', 0),
            "database": "connected",
            "modes": {
                "conscious": memori.conscious_ingest,
                "auto": memori.auto_ingest
            }
        }
    except Exception as e:
        return {
            "status": "error", 
            "error": str(e)
        }
```

### Performance Metrics

Track key metrics for your application:

- **Response Time**: How fast memory lookup happens
- **Token Usage**: Cost of memory context per request
- **Memory Growth**: How fast memories accumulate
- **Search Quality**: Relevance of retrieved memories
- **User Activity**: Active users and conversations per day

## Security in Production

### User Isolation

Each user's memories are completely isolated:

```python
# User A's memories
user_a_memory = Memori(
    database_connect="postgresql://...",
    namespace="user_12345"  # Isolated namespace
)

# User B's memories  
user_b_memory = Memori(
    database_connect="postgresql://...",
    namespace="user_67890"  # Different namespace
)
```

### API Key Security

Never hardcode API keys:

```python
import os

memori = Memori(
    database_connect=os.getenv("DATABASE_URL"),
    openai_api_key=os.getenv("OPENAI_API_KEY"),  # From environment
    namespace="production"
)
```

### Database Security

Use secure database connections:

```python
# SSL enabled PostgreSQL
DATABASE_URL = "postgresql://user:pass@db.com/memori?sslmode=require"

memori = Memori(database_connect=DATABASE_URL)
```

## Deployment Patterns

### Docker Deployment

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Environment variables
ENV MEMORI_DATABASE__CONNECTION_STRING=postgresql://...
ENV MEMORI_AGENTS__OPENAI_API_KEY=sk-...

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Kubernetes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: memori-app
spec:
  replicas: 3
  selector:
    matchLabels:
      app: memori-app
  template:
    metadata:
      labels:
        app: memori-app
    spec:
      containers:
      - name: memori-app
        image: your-app:latest
        env:
        - name: MEMORI_DATABASE__CONNECTION_STRING
          valueFrom:
            secretKeyRef:
              name: memori-secrets
              key: database-url
        - name: MEMORI_AGENTS__OPENAI_API_KEY
          valueFrom:
            secretKeyRef:
              name: memori-secrets
              key: openai-key
```

### Serverless (AWS Lambda)

```python
import json
from memori import Memori
from litellm import completion

# Initialize once outside handler
memori = Memori(
    database_connect=os.getenv("DATABASE_URL"),
    namespace="lambda_app",
    conscious_ingest=True
)
memori.enable()

def lambda_handler(event, context):
    user_message = event['message']
    user_id = event['user_id']
    
    # Use user-specific namespace
    user_memori = Memori(
        database_connect=os.getenv("DATABASE_URL"),
        namespace=f"user_{user_id}",
        conscious_ingest=True
    )
    user_memori.enable()
    
    response = completion(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": user_message}]
    )
    
    return {
        'statusCode': 200,
        'body': json.dumps({
            'response': response.choices[0].message.content
        })
    }
```

## Common Production Patterns

### Customer Support Bot

```python
from memori import Memori
from litellm import completion

class SupportBot:
    def __init__(self):
        self.memori = Memori(
            database_connect="postgresql://...",
            namespace="customer_support",
            conscious_ingest=True  # Fast responses for support
        )
        self.memori.enable()
    
    def handle_ticket(self, customer_id: str, message: str):
        # Use customer-specific memory
        customer_memory = Memori(
            database_connect="postgresql://...",
            namespace=f"customer_{customer_id}",
            conscious_ingest=True
        )
        customer_memory.enable()
        
        # Get response with customer history
        response = completion(
            model="gpt-4o-mini",
            messages=[{
                "role": "system",
                "content": "You are a helpful customer support agent."
            }, {
                "role": "user", 
                "content": message
            }]
        )
        
        return response.choices[0].message.content
```

### Research Platform

```python
class ResearchPlatform:
    def __init__(self):
        self.memori = Memori(
            database_connect="postgresql://...",
            namespace="research_platform",
            conscious_ingest=True,
            auto_ingest=True  # Comprehensive research context
        )
        self.memori.enable()
    
    def conduct_research(self, user_id: str, topic: str):
        # User-specific research memory
        user_memory = Memori(
            database_connect="postgresql://...",
            namespace=f"researcher_{user_id}",
            conscious_ingest=True,
            auto_ingest=True
        )
        user_memory.enable()
        
        # Research builds on previous work
        response = completion(
            model="gpt-4o",
            messages=[{
                "role": "system",
                "content": "You are a research agent. Build upon previous research."
            }, {
                "role": "user",
                "content": f"Research: {topic}"
            }]
        )
        
        return response.choices[0].message.content
```

### Personal AI Assistant

```python
class PersonalAssistant:
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.memori = Memori(
            database_connect="postgresql://...",
            namespace=f"assistant_{user_id}",
            conscious_ingest=True,  # Personal preferences ready
            auto_ingest=False       # Fast personal responses
        )
        self.memori.enable()
    
    def chat(self, message: str):
        response = completion(
            model="gpt-4o-mini",
            messages=[{
                "role": "system",
                "content": "You are a personal AI assistant with perfect memory."
            }, {
                "role": "user",
                "content": message
            }]
        )
        
        return response.choices[0].message.content
    
    def get_user_preferences(self):
        """Get user's stored preferences from memory"""
        return self.memori.search_memories_by_category("preference")
```

## Scaling Considerations

### Database Scaling

As your application grows:

1. **Start with SQLite** for development
2. **Move to PostgreSQL** for production
3. **Add read replicas** for high read loads
4. **Consider sharding** by user or namespace for massive scale

### Memory Management

For large applications:

```python
# Set memory limits per user
memori = Memori(
    database_connect="postgresql://...",
    memory_filters={
        "max_memories_per_user": 1000,      # Limit per namespace
        "retention_days": 90,               # Auto-cleanup old memories
        "min_importance": 0.4               # Only keep important memories
    }
)
```

### Cost Optimization

Reduce AI API costs:

1. **Use Conscious Mode** for most applications (lower token usage)
2. **Set retention policies** to avoid storing unnecessary data
3. **Use smaller models** for memory processing (gpt-4o-mini vs gpt-4o)
4. **Monitor token usage** and optimize prompts

## Best Practices

### Do's

- **Use namespaces** to isolate different users or applications
- **Start with conscious mode** for better performance
- **Use PostgreSQL** for production applications
- **Store API keys** in environment variables
- **Monitor memory growth** and set cleanup policies
- **Test error scenarios** to ensure graceful degradation
- **Use connection pooling** for high-traffic applications

### Don'ts

- **Don't hardcode** database connections or API keys
- **Don't ignore** memory cleanup - it grows over time
- **Don't use SQLite** for multi-user production applications
- **Don't enable both modes** unless you need comprehensive context
- **Don't store sensitive data** without encryption
- **Don't skip monitoring** - watch for performance issues

## Getting Help

If you run into issues in production:

1. **Check the logs** - Memori provides detailed logging
2. **Monitor memory stats** - Use `get_memory_stats()` for insights
3. **Test database connection** - Ensure your database is accessible
4. **Verify API keys** - Make sure your OpenAI/provider keys work
5. **Join our Discord** - Get help from the community: [Discord](https://discord.gg/abD4eGym6v)

## Summary

Memori is designed to be production-ready from day one. Whether you're building a simple personal assistant or a complex multi-user research platform, Memori handles the memory management so you can focus on building great AI applications.

Key takeaways for production:

- **Choose the right memory mode** for your use case
- **Use PostgreSQL** for production databases  
- **Implement proper user isolation** with namespaces
- **Monitor performance** and set up proper error handling
- **Scale gradually** from SQLite → PostgreSQL → optimized setup

Start simple, monitor performance, and scale as needed. Memori grows with your application.
