[![Memori Labs](https://s3.us-east-1.amazonaws.com/images.memorilabs.ai/banner.png)](https://memorilabs.ai/)

# Memori Troubleshooting Guide

This guide covers the most common issues developers face when using Memori and how to fix them.

## Table of Contents

1. [Installation Issues](#installation-issues)
2. [Connection Problems](#connection-problems)
3. [Configuration Errors](#configuration-errors)
4. [Attribution Issues](#attribution-issues)
5. [Memory and Storage Problems](#memory-and-storage-problems)
6. [API and Network Issues](#api-and-network-issues)
7. [LLM Integration Problems](#llm-integration-problems)
8. [Performance Issues](#performance-issues)
9. [Debug Logging](#debug-logging)

---

## Installation Issues

### Problem: Package installation fails

**Symptoms:**
- Error during `pip install memori`
- Missing dependency errors

**Solutions:**

1. Check your Python version (requires Python 3.10 or higher):
```bash
python --version
```

2. Upgrade pip before installing:
```bash
pip install --upgrade pip
pip install memori
```

3. If you have issues with binary dependencies, install them separately first:
```bash
pip install numpy>=1.24.0
pip install faiss-cpu>=1.7.0
pip install sentence-transformers>=3.0.0
pip install memori
```

## Connection Problems

### Problem: No connection factory provided

**Error Message:**
```
RuntimeError: No connection factory provided. Either pass 'conn' parameter or set MEMORI_COCKROACHDB_CONNECTION_STRING environment variable.
```

**Solutions:**

1. Pass a connection factory when initializing Memori:
```python
import sqlite3
from memori import Memori

def get_sqlite_connection():
    return sqlite3.connect("memori.db")

mem = Memori(conn=get_sqlite_connection)
```

2. Or set the environment variable:
```bash
export MEMORI_COCKROACHDB_CONNECTION_STRING="postgresql://user:pass@host:5432/db"
```

### Problem: Database connection string format is wrong

**Symptoms:**
- Connection errors
- Authentication failures
- Invalid URL errors

**Solutions:**

Use the correct format for your database:

**PostgreSQL:**
```python
"postgresql+psycopg://user:password@host:5432/database"
```

**MySQL:**
```python
"mysql+pymysql://user:password@host:3306/database"
```

**SQLite:**
```python
"sqlite:///memori.db"  # Relative path
"sqlite:////absolute/path/to/memori.db"  # Absolute path
```

**MongoDB:**
```python
from pymongo import MongoClient

def get_mongo_db():
    client = MongoClient("mongodb://host:27017/")
    return client["memori"]

mem = Memori(conn=get_mongo_db)
```

### Problem: Database connection pool errors

**Symptoms:**
- Connection timeout errors
- Too many connections errors
- Stale connection errors

**Solutions:**

1. Enable connection pool pre-ping for SQLAlchemy (recommended):
```python
engine = create_engine(
    "postgresql+psycopg://user:pass@host:5432/db",
    pool_pre_ping=True  # This checks if connections are alive
)
```

2. Configure connection pool settings (optional):
```python
engine = create_engine(
    "postgresql+psycopg://user:pass@host:5432/db",
    pool_pre_ping=True,
    pool_recycle=300  # Recycle connections after 300 seconds
)
```

Note: SQLAlchemy's `create_engine` also supports `pool_size` and `max_overflow` parameters for fine-tuning connection pooling, but the default settings work well for most use cases.

---

## Configuration Errors

### Problem: Cannot find database schema or tables

**Symptoms:**
- Table does not exist errors
- Schema not found errors

**Solutions:**

1. Build the database schema after initialization:
```python
import sqlite3
from memori import Memori

def get_sqlite_connection():
    return sqlite3.connect("memori.db")

mem = Memori(conn=get_sqlite_connection)
mem.config.storage.build()  # This creates all required tables
```

2. For MongoDB, ensure the database exists and build the schema:
```python
from pymongo import MongoClient
from memori import Memori

def get_mongo_db():
    client = MongoClient("mongodb://host:27017/")
    return client["memori"]  # Database will be created automatically

mem = Memori(conn=get_mongo_db)
mem.config.storage.build()  # Build the schema
```

### Problem: Environment variables not loading

**Symptoms:**
- API keys not recognized
- Configuration values are None

**Solutions:**

1. Export environment variables directly:
```bash
export OPENAI_API_KEY="your-key-here"
export MEMORI_API_KEY="your-memori-key"
export DATABASE_CONNECTION_STRING="postgresql://user:pass@host:5432/db"
```

2. Or create a `.env` file and use `python-dotenv` (requires installing `python-dotenv`):
```
OPENAI_API_KEY=your-key-here
MEMORI_API_KEY=your-memori-key
DATABASE_CONNECTION_STRING=postgresql://user:pass@host:5432/db
```

Then load it in your code:
```python
import os
from dotenv import load_dotenv

load_dotenv()  # Load .env file
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
```

3. Set variables directly in code (not recommended for production):
```python
import os
os.environ["MEMORI_API_KEY"] = "your-key-here"
```

---

## Attribution Issues

### Problem: No memories are being created

**Symptoms:**
- Agent cannot recall previous conversations
- Empty recall results
- No data in database

**Solutions:**

1. Set attribution before using the LLM:
```python
import sqlite3
from memori import Memori
from openai import OpenAI

def get_sqlite_connection():
    return sqlite3.connect("memori.db")

client = OpenAI(...)
mem = Memori(conn=get_sqlite_connection).llm.register(client)
mem.attribution(entity_id="user-123", process_id="my-app")
```

2. Check that attribution is valid:
```python
# entity_id and process_id must be 100 characters or less
mem.attribution(
    entity_id="user-123",  # Required
    process_id="my-app"    # Required
)
```

3. For short-lived scripts that terminate quickly, wait for background augmentation to complete:
```python
# Advanced augmentation runs asynchronously in the background
# Short-lived scripts need to wait for completion before exiting
mem.augmentation.wait()  # Available in Memori 3.1.0+
```

**Important:** If you do not provide attribution, Memori cannot make memories for you.

### Problem: Attribution ID too long

**Error Message:**
```
RuntimeError: entity_id cannot be greater than 100 characters
RuntimeError: process_id cannot be greater than 100 characters
```

**Solutions:**

Use shorter IDs that are 100 characters or less:
```python
# Keep your IDs concise
mem.attribution(
    entity_id="user-123",  # Max 100 characters
    process_id="my-app"    # Max 100 characters
)
```

**Note:** Avoid using hashed IDs as they make the data in your database more difficult to use and debug since hashing cannot be reversed.

---

## Memory and Storage Problems

### Problem: Transaction restart errors (CockroachDB)

**Error Message:**
```
OperationalError: restart transaction
```

**Solutions:**

Memori automatically retries failed transactions up to 3 times with exponential backoff. If the error persists:

1. Increase retry attempts in your application code.
2. Reduce concurrent write operations.
3. Check CockroachDB cluster health.

### Problem: Session management confusion

**Symptoms:**
- Memories from different conversations mixed together
- Cannot isolate conversation contexts

**Solutions:**

1. Use automatic session management (default):
```python
mem = Memori(conn=Session).llm.register(client)
mem.attribution(entity_id="user-123", process_id="my-app")
# Memori handles sessions automatically
```

2. Create new sessions manually for new conversations:
```python
# Start a new conversation
mem.new_session()
```

3. Restore a specific session:
```python
# Save session ID
session_id = mem.config.session_id

# Later, restore it
mem.set_session(session_id)
```

### Problem: Recall returns no results or wrong results

**Symptoms:**
- Empty recall results
- Irrelevant facts returned

**Solutions:**

1. Check that memories were created with proper attribution:
```python
mem.attribution(entity_id="user-123", process_id="my-app")
```

2. Adjust recall parameters:
```python
# Default
facts = mem.recall("what's my favorite color?")

# Increase limit
facts = mem.recall("what's my favorite color?", limit=10)
```

3. Check relevance threshold in config:
```python
# Lower threshold returns more results (less strict)
mem.config.recall_relevance_threshold = 0.05  # Default is 0.1
```

4. Increase embeddings limit:
```python
mem.config.recall_embeddings_limit = 2000  # Default is 1000
```

---

## API and Network Issues

### Problem: Quota exceeded error

**Error Message:**
```
QuotaExceededError: your IP address is over quota; register for an API key now: https://app.memorilabs.ai/signup
```

**Solutions:**

1. Sign up for a free API key at [https://app.memorilabs.ai/signup](https://app.memorilabs.ai/signup).

2. Set your API key:
```bash
export MEMORI_API_KEY="your-api-key-here"
```

3. Or set it in your `.env` file:
```
MEMORI_API_KEY=your-api-key-here
```

4. For enterprise users:
```bash
export MEMORI_ENTERPRISE=1
export MEMORI_API_KEY="your-enterprise-key"
```

### Problem: Network timeout errors

**Symptoms:**
- Requests timing out
- Connection refused errors
- Slow responses

**Solutions:**

1. Increase timeout settings:
```python
mem = Memori(conn=Session)
mem.config.request_secs_timeout = 10  # Default is 5 seconds
```

2. Adjust retry settings:
```python
mem.config.request_num_backoff = 10  # Default is 5 retries
mem.config.request_backoff_factor = 2  # Default is 1
```

3. Check your network connection and firewall settings.

---

## LLM Integration Problems

### Problem: LLM client not registered properly

**Symptoms:**
- Memory not being created during LLM calls
- No integration between Memori and LLM

**Solutions:**

1. Register your LLM client correctly:

**OpenAI:**
```python
import os
import sqlite3
from openai import OpenAI
from memori import Memori

def get_sqlite_connection():
    return sqlite3.connect("memori.db")

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
mem = Memori(conn=get_sqlite_connection).llm.register(client)
mem.attribution(entity_id="user-123", process_id="my-app")
```

**Anthropic:**
```python
import os
import sqlite3
import anthropic
from memori import Memori

def get_sqlite_connection():
    return sqlite3.connect("memori.db")

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
mem = Memori(conn=get_sqlite_connection).llm.register(client)
mem.attribution(entity_id="user-123", process_id="my-app")
```

**Google:**
```python
import os
import sqlite3
import google.generativeai as genai
from memori import Memori

def get_sqlite_connection():
    return sqlite3.connect("memori.db")

genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
client = genai.GenerativeModel("gemini-pro")
mem = Memori(conn=get_sqlite_connection).llm.register(client)
mem.attribution(entity_id="user-123", process_id="my-app")
```

**LangChain:**
```python
import sqlite3
from langchain_openai import ChatOpenAI
from memori import Memori

def get_sqlite_connection():
    return sqlite3.connect("memori.db")

chat = ChatOpenAI()
mem = Memori(conn=get_sqlite_connection).llm.register(chat)
mem.attribution(entity_id="user-123", process_id="my-app")
```

2. Make sure to call the LLM through the registered client after registration.

### Problem: Streaming not working with OpenAI

**Symptoms:**
- Stream responses not captured
- No memory from streaming calls

**Solutions:**

Enable streaming when registering:
```python
import sqlite3
from openai import OpenAI
from memori import Memori

def get_sqlite_connection():
    return sqlite3.connect("memori.db")

client = OpenAI(...)
mem = Memori(conn=get_sqlite_connection).llm.register(client, stream=True)
```

---

## Performance Issues

### Problem: Slow first run

**Symptoms:**
- Long delay on first execution
- Downloading model messages

**Cause:** Memori downloads the "all-mpnet-base-v2" embedding model on first run.

**Solutions:**

Run the setup command before first use:
```bash
python -m memori setup
```

This is a one-time download. Subsequent runs will be fast.

**Tip:** If you have automated CI/CD pipelines, include this setup command in your build process to ensure the model is pre-downloaded in your deployment environment.

### Problem: High memory usage

**Symptoms:**
- Application using too much RAM
- Out of memory errors

**Solutions:**

1. Reduce embeddings limit:
```python
mem.config.recall_embeddings_limit = 500  # Default is 1000
```

2. Reduce thread pool size (note: default is 15 workers):
```python
# This setting is configured at initialization
# The default ThreadPoolExecutor uses max_workers=15
# Lower values may reduce memory but slow down processing
```

3. Use a smaller embedding model if needed (requires custom configuration).

### Problem: Slow database writes

**Symptoms:**
- Long delays after LLM responses
- High database CPU usage

**Solutions:**

1. Use connection pooling with recommended settings:
```python
engine = create_engine(
    "postgresql+psycopg://user:pass@host:5432/db",
    pool_pre_ping=True,
    pool_recycle=300
)
```

2. Database indexes are optimized automatically by Memori.

3. Use PostgreSQL instead of SQLite for production workloads.

---

## Testing and Development

### Problem: Want to test without making production API calls

**Solutions:**

Enable test mode (routes to staging API):
```python
import os
os.environ["MEMORI_TEST_MODE"] = "1"
```

**Note:** Test mode routes requests to the staging API environment. Memories will still be created and saved. If you need to completely disable advanced augmentation and memory creation, you would need to configure this separately.

### Problem: Need to reset everything and start fresh

**Solutions:**

1. Create a new session:
```python
mem.new_session()
```

2. Clear cache:
```python
mem.config.reset_cache()
```

3. For SQLite, delete the database file:
```bash
rm memori.db
```

4. For other databases, drop tables using your database tooling, then recreate the schema:
```python
mem.config.storage.build()  # This will create/update the schema
```

---

## Common Patterns and Best Practices

### Proper initialization flow

```python
import os
import sqlite3
from openai import OpenAI
from memori import Memori

# 1. Define connection factory
def get_sqlite_connection():
    return sqlite3.connect("memori.db")

# 2. Initialize LLM client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# 3. Initialize Memori with connection factory and register LLM
mem = Memori(conn=get_sqlite_connection).llm.register(client)

# 4. Set attribution
mem.attribution(entity_id="user-123", process_id="my-app")

# 5. Build database schema (run once, or via CI/CD)
mem.config.storage.build()

# 6. Use normally
response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": "Hello!"}]
)
```

### Error handling

```python
import sqlite3
from memori import Memori, QuotaExceededError
from openai import OpenAI

def get_sqlite_connection():
    return sqlite3.connect("memori.db")

try:
    client = OpenAI(...)
    mem = Memori(conn=get_sqlite_connection).llm.register(client)
    mem.attribution(entity_id="user-123", process_id="my-app")
except QuotaExceededError:
    print("Quota exceeded. Get an API key at https://app.memorilabs.ai/signup")
except RuntimeError as e:
    print(f"Configuration error: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

---

## Debug Logging

Enable debug logging to see exactly what Memori is doing internally.

### Enable Debug Logging

```python
import logging

# Enable BEFORE importing Memori
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
)

from memori import Memori
```

### What You'll See

```
DEBUG | memori.memory.recall - Recall started - query: "What's my favorite..." (25 chars)
DEBUG | memori.llm._embeddings - Generating embedding using model: all-mpnet-base-v2
DEBUG | memori._search - Retrieved 156 embeddings from database
DEBUG | memori._search - FAISS similarity search complete - top 5 matches: [0.92, 0.87, 0.84]
DEBUG | memori.llm._invoke - Sending request to LLM - provider: openai, model: gpt-4o-mini
DEBUG | memori.llm._base - LLM response received - latency: 1.23s
DEBUG | memori.memory._writer - Transaction committed - conversation_id: 42
DEBUG | memori.memory.augmentation._manager - AA enqueued - scheduling augmentation
```

### Control Log Truncation

By default, long content is truncated in logs for readability:

```python
# Default: truncate long content (recommended)
memori = Memori(conn)

# Show full content (for deep debugging)
memori = Memori(conn, debug_truncate=False)
```

### Filter Logs by Module

```python
import logging

# Only show specific module logs
logging.getLogger("memori.memory.recall").setLevel(logging.DEBUG)
logging.getLogger("memori.llm").setLevel(logging.DEBUG)

# Silence other memori logs
logging.getLogger("memori").setLevel(logging.WARNING)
```

### Production Logging

```python
import logging

# Production: only show warnings and errors
logging.getLogger("memori").setLevel(logging.WARNING)
```

---

## Getting Help

If you are still having issues after trying these solutions:

1. Check the [GitHub Issues](https://github.com/MemoriLabs/Memori/issues).
2. Join the [Discord community](https://discord.gg/abD4eGym6v).
3. Review the [documentation](https://memorilabs.ai/docs/).
4. Check the [examples folder](https://github.com/MemoriLabs/Memori/tree/main/examples) for working code.

When asking for help, include:
- Your Python version.
- Your Memori version (`pip show memori`).
- Database type you are using.
- Complete error message and stack trace.
- Minimal code example that reproduces the issue.
