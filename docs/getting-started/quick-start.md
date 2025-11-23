# Quick Start

Get Memori running in less than a minute.

## 1. Install

```bash
pip install memorisdk openai
```

## 2. Set API Key

```bash
export OPENAI_API_KEY="sk-your-openai-key-here"
```

## 3. Basic Usage

Create `demo.py`:

```python
from memori import Memori
from openai import OpenAI

# Initialize OpenAI client
openai_client = OpenAI()

# Initialize memory
memori = Memori(conscious_ingest=True)
memori.enable()

# First conversation - establish context
response1 = openai_client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{
        "role": "user", 
        "content": "I'm working on a Python FastAPI project"
    }]
)
print("Assistant:", response1.choices[0].message.content)

# Second conversation - memory provides context  
response2 = openai_client.chat.completions.create(
    model="gpt-4o-mini", 
    messages=[{
        "role": "user",
        "content": "Help me add user authentication"
    }]
)
print("Assistant:", response2.choices[0].message.content)
```

## 4. Run

```bash
python demo.py
```

## 5. See Results

- First response: General FastAPI help
- Second response: **Contextual authentication help** (knows about your FastAPI project!)
- Database created: `memori.db` with your conversation memories

## What Happened?

1. **Universal Recording**: `memori.enable()` automatically captures ALL LLM conversations
2. **Intelligent Processing**: Extracts entities (Python, FastAPI, projects) and categorizes memories
3. **Context Injection**: Second conversation automatically includes relevant memories
4. **Persistent Storage**: All memories stored in SQLite database for future sessions

## Under the Hood: The Magic Explained

Let's break down exactly what happened in each step.

### Step 1: `memori.enable()`

When you call `enable()`, Memori:

- Registers with LiteLLM's native callback system
- **No monkey-patching** - uses official LiteLLM hooks
- Now intercepts ALL OpenAI/Anthropic/LiteLLM calls automatically

**Your code doesn't change** - pure interception pattern.

### Step 2: First Conversation

Your code sent:
```python
messages=[{"role": "user", "content": "I'm working on a Python FastAPI project"}]
```

**Memori's Process:**

1. **Pre-Call**: No context yet (first conversation) → messages passed through unchanged
2. **Call**: Forwarded to OpenAI API
3. **Post-Call**: Memory Agent analyzed the conversation and extracted:
   ```json
   {
     "content": "User is working on Python FastAPI project",
     "category": "context",
     "entities": ["Python", "FastAPI"],
     "is_current_project": true,
     "importance": 0.8
   }
   ```
4. **Storage**: Wrote to `memori.db` with full-text search index

**Result**: Memory stored for future use.

### Step 3: Second Conversation

Your code sent:
```python
messages=[{"role": "user", "content": "Help me add user authentication"}]
```

**Memori's Process:**

1. **Pre-Call - Memory Retrieval**: Searched database with:
   ```sql
   SELECT content FROM long_term_memory
   WHERE user_id = 'default'
     AND is_current_project = true
   ORDER BY importance_score DESC
   LIMIT 5;
   ```
   **Found**: "User is working on Python FastAPI project"

2. **Context Injection**: Modified your messages to:
   ```python
   [
     {
       "role": "system",
       "content": "CONTEXT: User is working on a Python FastAPI project"
     },
     {
       "role": "user",
       "content": "Help me add user authentication"
     }
   ]
   ```

3. **Call**: Forwarded enriched messages to OpenAI
4. **Result**: AI received context and provided **FastAPI-specific** authentication code!
5. **Post-Call**: Stored new memories about authentication discussion

### The Flow Diagram

```
Your App → memori.enable() → [Memori Interceptor]
                                     ↓
                              SQL Database
                                     ↓
User sends message → Retrieve Context → Inject Context → OpenAI API
                                                              ↓
                     Store New Memories ← Extract Entities ← Response
                                                              ↓
                                                     Return to Your App
```

### Why This Works

- **Zero Refactoring**: Your OpenAI code stays unchanged
- **Framework Agnostic**: Works with any LLM library
- **Transparent**: Memory operations happen outside response delivery
- **Persistent**: Memories survive across sessions

## Inspect Your Database

Want to see what was stored? Your `memori.db` file now contains:

```python
# View all memories
import sqlite3
conn = sqlite3.connect('memori.db')
cursor = conn.execute("""
    SELECT category_primary, summary, importance_score, created_at
    FROM long_term_memory
""")
for row in cursor:
    print(row)
```

Or use SQL directly:

```bash
sqlite3 memori.db "SELECT summary, category_primary FROM long_term_memory;"
```

## Test Memory Persistence

Close Python, restart, and run this:

```python
from memori import Memori
from openai import OpenAI

memori = Memori(conscious_ingest=True)
memori.enable()

client = OpenAI()

# Memori remembers from previous session!
response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": "What project am I working on?"}]
)
print(response.choices[0].message.content)
# Output: "You're working on a Python FastAPI project"
```

**The memory persisted!** This is true long-term memory across sessions.

!!! tip "Pro Tip"
    Try asking the same questions in a new session - Memori will remember your project context!