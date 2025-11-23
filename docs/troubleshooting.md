# Troubleshooting & FAQ

This guide helps you diagnose and resolve common issues with Memori.

## Quick Diagnostics

Run this code to check your Memori setup:

```python
from memori import Memori

memori = Memori(verbose=True)

# Check basic setup
print(f"Memori initialized: {memori is not None}")
print(f"Conscious ingest: {memori.conscious_ingest}")
print(f"Auto ingest: {memori.auto_ingest}")
print(f"Database type: {memori.db_manager.database_type}")

# Test database connection
is_connected = memori.db_manager.test_connection()
print(f"Database connected: {is_connected}")

# Check memory stats
stats = memori.get_memory_stats()
print(f"Total conversations: {stats.get('total_conversations', 0)}")
print(f"Long-term memories: {stats.get('long_term_count', 0)}")
```

---

## Common Issues

### Issue 1: "No memories retrieved in Auto Mode"

**Symptoms:**
```
[AUTO-INGEST] Direct database search returned 0 results
[AUTO-INGEST] Fallback to recent memories returned 0 results
```

**Causes:**
1. Not enough conversations recorded yet
2. Query doesn't match stored memory keywords
3. Wrong `user_id` or namespace
4. Database is empty

**Solutions:**

**Check if memories exist:**
```python
# Verify memories are being stored
stats = memori.get_memory_stats()
print(f"Total memories: {stats['long_term_count']}")

# Search manually
results = memori.search_memories("test", limit=10)
print(f"Found {len(results)} memories")

# Check what's in the database
import sqlite3
conn = sqlite3.connect('memori.db')
cursor = conn.execute("SELECT COUNT(*) FROM long_term_memory")
count = cursor.fetchone()[0]
print(f"Database has {count} memories")
```

**Verify namespace:**
```python
# Check current namespace
print(f"Current namespace: {memori.namespace}")

# Search with explicit namespace
results = memori.search_memories("test", namespace="default")
```

**Build up memory first:**
```python
from openai import OpenAI

client = OpenAI()
memori = Memori(auto_ingest=True)
memori.enable()

# Have some conversations first
conversations = [
    "I'm working on a Python FastAPI project",
    "I prefer async/await patterns",
    "I use PostgreSQL for the database"
]

for msg in conversations:
    client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": msg}]
    )

# Now auto-ingest should have data to retrieve
```

---

### Issue 2: "Context not injected into conversations"

**Symptoms:**
AI doesn't remember previous conversations, acts like it has no context

**Causes:**
1. `memori.enable()` not called
2. Wrong memory mode for your use case
3. Different `user_id` in subsequent calls
4. Memories exist but not being retrieved

**Solutions:**

**Verify Memori is enabled:**
```python
# Check if enabled
print(f"Memori enabled: {memori._enabled}")

# Enable if not already
if not memori._enabled:
    memori.enable()
```

**Check memory mode:**
```python
# Verify mode configuration
print(f"Conscious ingest: {memori.conscious_ingest}")
print(f"Auto ingest: {memori.auto_ingest}")

# If both are False, enable at least one
if not memori.conscious_ingest and not memori.auto_ingest:
    memori = Memori(conscious_ingest=True)
    memori.enable()
```

**Use consistent user_id:**
```python
from openai import OpenAI

client = OpenAI()
memori = Memori(user_id="alice")  # Set at initialization
memori.enable()

# All calls use same user_id automatically
response1 = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": "I love Python"}]
)

response2 = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": "What programming language do I prefer?"}]
)
# Should remember Python from response1
```

**Test context injection manually:**
```python
# For conscious mode
if memori.conscious_ingest:
    short_term = memori.db_manager.get_short_term_memories(
        user_id=memori.user_id
    )
    print(f"Short-term memories: {len(short_term)}")

# For auto mode
if memori.auto_ingest:
    context = memori._get_auto_ingest_context("test query")
    print(f"Auto-ingest retrieved: {len(context)} memories")
```

---

### Issue 3: "Too much context injected (token limit errors)"

**Symptoms:**
```
Error: maximum context length exceeded (token limit)
```

**Causes:**
Too many memories being injected per call, exceeding model's token limit

**Solutions:**

**Reduce context limit:**
```python
# Limit number of memories injected
memori = Memori(
    conscious_ingest=True,
    context_limit=3  # Default is 5
)
```

**Use Conscious Mode only (less tokens):**
```python
# Conscious mode uses fewer tokens than Auto mode
memori = Memori(
    conscious_ingest=True,
    auto_ingest=False  # Disable auto for lower token usage
)
```

**Adjust importance threshold:**
```python
from memori.config import ConfigManager

config = ConfigManager()
config.update_setting("memory.importance_threshold", 0.7)  # Higher = fewer memories
```

**Monitor token usage:**
```python
# Check how many tokens are being used
stats = memori.get_memory_stats()
print(f"Average tokens per call: {stats.get('avg_tokens', 0)}")
```

---

### Issue 4: "Database is locked" (SQLite)

**Symptoms:**
```
sqlite3.OperationalError: database is locked
```

**Cause:**
Multiple processes/threads trying to write to the same SQLite file simultaneously

**Solutions:**

**Option 1: Use PostgreSQL for multi-process:**
```python
memori = Memori(
    database_connect="postgresql://user:pass@localhost/memori"
)
```

**Option 2: Enable WAL mode (Write-Ahead Logging):**
```python
memori = Memori(
    database_connect="sqlite:///memori.db?mode=wal"
)
```

**Option 3: Separate databases per process:**
```python
import os

process_id = os.getpid()
memori = Memori(
    database_connect=f"sqlite:///memori_{process_id}.db"
)
```

---

### Issue 5: "Memory Agent failed to initialize"

**Symptoms:**
```
Memory Agent initialization failed: No API key provided
ERROR: Failed to initialize memory agent
```

**Cause:**
OpenAI API key not set (required for memory processing)

**Solutions:**

**Set API key via environment variable:**
```bash
export OPENAI_API_KEY="sk-your-api-key-here"
```

**Or set in code:**
```python
memori = Memori(
    openai_api_key="sk-your-api-key-here"
)
```

**Verify API key is set:**
```python
import os

api_key = os.getenv("OPENAI_API_KEY")
if api_key:
    print(f"API key set: {api_key[:10]}...")
else:
    print("ERROR: OPENAI_API_KEY not set")
```

---

### Issue 6: "Memories not persisting across sessions"

**Symptoms:**
After restarting Python, previous conversations are forgotten

**Causes:**
1. Using in-memory database
2. Database file in temporary location
3. Different database file being used

**Solutions:**

**Use persistent database file:**
```python
# Specify absolute path
memori = Memori(
    database_connect="sqlite:////absolute/path/to/memori.db"
)

# Or relative path (creates in current directory)
memori = Memori(
    database_connect="sqlite:///./memori.db"
)
```

**Verify database location:**
```python
import os

db_path = "memori.db"
if os.path.exists(db_path):
    size = os.path.getsize(db_path)
    print(f"Database exists: {db_path} ({size} bytes)")
else:
    print(f"Database not found: {db_path}")
```

**Check database has data:**
```python
stats = memori.get_memory_stats()
print(f"Long-term memories: {stats['long_term_count']}")
print(f"Chat history: {stats['chat_history_count']}")
```

---

### Issue 7: "Slow query performance"

**Symptoms:**
Memory retrieval taking longer than expected (>50ms)

**Solutions:**

**Ensure indexes are created:**
```python
# Initialize schema explicitly
memori.db_manager.initialize_schema()
```

**Check index usage:**
```sql
-- For SQLite
EXPLAIN QUERY PLAN
SELECT * FROM long_term_memory
WHERE user_id = 'default' AND is_current_project = 1;
```

**Reduce search scope:**
```python
# Limit memory retrieval
memori = Memori(
    context_limit=3,  # Retrieve fewer memories
    auto_ingest=True
)
```

---

## Frequently Asked Questions (FAQ)

### Q: Does Memori work with Claude/Anthropic?

**A:** Yes! Memori intercepts all LLM calls:

```python
from memori import Memori
import anthropic

memori = Memori()
memori.enable()

client = anthropic.Anthropic()
response = client.messages.create(
    model="claude-3-5-sonnet-20241022",
    messages=[{"role": "user", "content": "Hello"}],
    max_tokens=1024
)
# Automatically recorded and contextualized
```

---

### Q: How do I export/backup my memories?

**A:** For SQLite, just copy the `.db` file:

```bash
# Backup
cp memori.db memori_backup_$(date +%Y%m%d).db

# Restore
cp memori_backup_20241201.db memori.db
```

For PostgreSQL:

```bash
# Backup
pg_dump memori > memori_backup.sql

# Restore
psql memori < memori_backup.sql
```

---

### Q: Can I inspect memories directly?

**A:** Yes! Use any SQL tool:

```python
# Python
import sqlite3
conn = sqlite3.connect('memori.db')
cursor = conn.execute("""
    SELECT category_primary, summary, importance_score, created_at
    FROM long_term_memory
    ORDER BY created_at DESC
    LIMIT 10
""")
for row in cursor:
    print(row)
```

```bash
# SQLite CLI
sqlite3 memori.db "SELECT category_primary, summary FROM long_term_memory;"
```

---

### Q: How do I delete all memories for testing?

**A:**

```python
# Delete all memories
memori.db_manager.clear_all_memories()

# Delete for specific user
memori.db_manager.clear_user_memories(user_id="test_user")

# Or use SQL directly
import sqlite3
conn = sqlite3.connect('memori.db')
conn.execute("DELETE FROM long_term_memory WHERE user_id = ?", ("test_user",))
conn.commit()
```

---

### Q: Does Memori add latency to my LLM calls?

**A:** Minimal latency:

- **Conscious Mode:** ~2-3ms (short-term memory lookup via primary key)
- **Auto Mode:** ~10-15ms (database search with full-text indexing)
- **Combined Mode:** ~12-18ms (both lookups)

The enriched context often **reduces overall latency** by providing better information up-front, reducing follow-up calls.

**Measure latency yourself:**

```python
import time

start = time.time()
response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": "test"}]
)
elapsed = (time.time() - start) * 1000
print(f"Total latency: {elapsed:.0f}ms")
```

---

### Q: Can I use custom LLM providers (Ollama, vLLM, etc.)?

**A:** Yes, via custom provider configuration:

```python
from memori import Memori
from memori.core.providers import ProviderConfig

# Ollama
ollama_config = ProviderConfig.from_custom(
    base_url="http://localhost:11434/v1",
    api_key="not-required",
    model="llama3"
)

memori = Memori(provider_config=ollama_config)
memori.enable()

# Now use any OpenAI-compatible client
from openai import OpenAI
client = OpenAI(
    base_url="http://localhost:11434/v1",
    api_key="not-required"
)
```

---

### Q: How much does Memori cost to run?

**A:**

**Infrastructure costs:**
- **SQLite:** Free (local file)
- **PostgreSQL (managed):** $15-30/month (Neon, Supabase, etc.)

**API costs (for Memory Agent):**
- Uses OpenAI for memory processing (~$0.01 per 10 conversations with GPT-4o-mini)
- Approximately $5-20/month for typical usage

**Total:** ~$5-50/month depending on scale

**Comparison to vector databases:**
- Pinecone/Weaviate: $80-100/month for 100K memories
- **Memori: 80-90% cheaper**

---

### Q: Can I use Memori in production?

**A:** Yes! Memori is production-ready:

**Use PostgreSQL for production:**
```python
memori = Memori(
    database_connect="postgresql://user:pass@prod-db.company.com/memori"
)
```

**Enable proper error handling:**
```python
try:
    memori.enable()
except Exception as e:
    logger.error(f"Memori initialization failed: {e}")
    # App continues without memory (graceful degradation)
```

**Monitor performance:**
```python
stats = memori.get_memory_stats()
logger.info(f"Memory stats: {stats}")
```

---

### Q: How do I handle multi-tenant applications?

**A:** Use `user_id` parameter for isolation:

```python
from fastapi import FastAPI, Depends
from fastapi.security import OAuth2PasswordBearer

app = FastAPI()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

memori = Memori()  # Single global instance
memori.enable()

def get_current_user(token: str = Depends(oauth2_scheme)) -> str:
    """Extract user_id from JWT"""
    return decode_jwt_token(token)["user_id"]

@app.post("/chat")
async def chat(message: str, user_id: str = Depends(get_current_user)):
    from openai import OpenAI
    client = OpenAI()

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": message}],
        user=user_id  # Automatic memory isolation per user
    )
    return {"response": response.choices[0].message.content}
```

Every query automatically filters: `WHERE user_id = ?` for complete isolation.

---

## Debugging Tips

### Enable Verbose Logging

```python
memori = Memori(verbose=True)
```

You'll see detailed logs:
```
[MEMORY] Processing conversation: "I prefer FastAPI"
[MEMORY] Categorized as 'preference', importance: 0.8
[MEMORY] Extracted entities: ['FastAPI']
[AUTO-INGEST] Starting context retrieval for query
[AUTO-INGEST] Retrieved 3 relevant memories
[AUTO-INGEST] Context injection successful
```

---

### Check Database Connection

```python
# Test connection
is_connected = memori.db_manager.test_connection()
print(f"Database connected: {is_connected}")

# Get connection details
try:
    info = memori.db_manager.get_connection_info()
    print(f"Database type: {info.get('type')}")
    print(f"Connection string: {info.get('url')}")
except Exception as e:
    print(f"Connection check failed: {e}")
```

---

### Verify Memory Agent

```python
# Check if Memory Agent is initialized
if hasattr(memori, 'memory_agent') and memori.memory_agent:
    print("Memory agent available")
else:
    print("Memory agent not initialized")
    print("Ensure OPENAI_API_KEY is set")

# Test memory agent
try:
    from memori.utils.pydantic_models import ProcessedLongTermMemory
    # If import succeeds, models are available
    print("Pydantic models loaded successfully")
except ImportError as e:
    print(f"Model import failed: {e}")
```

---

### Check Memory Processing Pipeline

```python
# Enable verbose mode
memori = Memori(verbose=True)

# Record a test conversation
from openai import OpenAI
client = OpenAI()

response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": "I love Python programming"}]
)

# Check if memory was stored
import time
time.sleep(2)  # Wait for async processing

stats = memori.get_memory_stats()
print(f"Memories after test: {stats['long_term_count']}")

# Search for the memory
results = memori.search_memories("Python", limit=5)
print(f"Found {len(results)} memories about Python")
```

---

### Inspect Full Database Contents

```python
import sqlite3

conn = sqlite3.connect('memori.db')

# Check all tables
cursor = conn.execute("""
    SELECT name FROM sqlite_master
    WHERE type='table'
    ORDER BY name
""")
tables = cursor.fetchall()
print(f"Tables: {[t[0] for t in tables]}")

# Check memory counts
cursor = conn.execute("SELECT COUNT(*) FROM long_term_memory")
print(f"Long-term memories: {cursor.fetchone()[0]}")

cursor = conn.execute("SELECT COUNT(*) FROM short_term_memory")
print(f"Short-term memories: {cursor.fetchone()[0]}")

cursor = conn.execute("SELECT COUNT(*) FROM chat_history")
print(f"Chat history entries: {cursor.fetchone()[0]}")

# View recent memories
cursor = conn.execute("""
    SELECT category_primary, summary, importance_score
    FROM long_term_memory
    ORDER BY created_at DESC
    LIMIT 5
""")
print("\nRecent memories:")
for row in cursor:
    print(f"  {row[0]}: {row[1]} (importance: {row[2]})")
```

---

### Monitor Memory Mode Status

```python
# Check mode configuration
print(f"Conscious ingest enabled: {memori.conscious_ingest}")
print(f"Auto ingest enabled: {memori.auto_ingest}")

# Test Conscious mode
if memori.conscious_ingest:
    try:
        short_term = memori.db_manager.get_short_term_memories(
            user_id=memori.user_id
        )
        print(f"Conscious mode: {len(short_term)} short-term memories loaded")
    except Exception as e:
        print(f"Conscious mode test failed: {e}")

# Test Auto mode
if memori.auto_ingest:
    try:
        context = memori._get_auto_ingest_context("test preferences")
        print(f"Auto mode: Retrieved {len(context)} context memories")
    except Exception as e:
        print(f"Auto mode test failed: {e}")
```

---

## Getting Help

If you're still experiencing issues:

1. **Search existing issues:** https://github.com/GibsonAI/memori/issues
2. **Join Discord community:** https://discord.gg/abD4eGym6v
3. **Check documentation:** https://www.gibsonai.com/docs/memori
4. **Report a bug:** https://github.com/GibsonAI/memori/issues/new

When reporting issues, please include:
- Python version (`python --version`)
- Memori version (`pip show memorisdk`)
- Database type (SQLite, PostgreSQL, MySQL)
- Minimal reproducible code example
- Full error traceback
- Relevant logs (with `verbose=True`)
