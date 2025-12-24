[![Memori Labs](https://s3.us-east-1.amazonaws.com/images.memorilabs.ai/banner.png)](https://memorilabs.ai/)

# Quickstart

Get started with Memori in under 3 minutes.

Memori is LLM, database and framework agnostic and works with the tools you already use today. In this example, we'll show Memori working with OpenAI, SQLAlchemy and SQLite.

- [Supported LLM providers](https://github.com/MemoriLabs/Memori/blob/main/docs/features/llm.md)
- [Supported databases](https://github.com/MemoriLabs/Memori/blob/main/docs/features/databases.md)

## Prerequisites

- Python 3.10 or higher
- An OpenAI API key

## Step 1: Install Libraries

Install Memori:

```bash
pip install memori
```

For this example, you may also need to install:

```bash
pip install openai
```

## Step 2: Set environment variables

Set your OpenAI API key in an environment variable:

```bash
export OPENAI_API_KEY="your-api-key-here"
```

## Step 3: Run Your First Memori Application

Create a new Python file `quickstart.py` and add the following code:

```python
"""

This Quickstart shows chat working and 
the underlying storage provided by Memori.

This script performs the following steps:

- Initializes a local SQLite database
- Adds a memory ("User likes Fried Rice")
- IMMEDIATELY verifies it via Vector Search (mem.recall)
- Verify it via SQL Inspection (Raw Logs)
- USES the memory in a follow-up question (Recall Loop)

"""

import os

import sqlite3
from dotenv import load_dotenv
from memori import Memori
from openai import OpenAI
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


# Setup
# =====

load_dotenv()
if not os.getenv("OPENAI_API_KEY"):
    raise ValueError("Missing OPENAI_API_KEY in .env")

# 1. Initialize Database (Local Mode)
# -----------------------------------
DB_FILE = "memori_quickstart.db"
# Clean slate for the demo
if os.path.exists(DB_FILE):
    os.remove(DB_FILE)

# 2. Configure Memori with SQLAlchemy
# -----------------------------------
engine = create_engine(f"sqlite:///{DB_FILE}")
session = sessionmaker(bind=engine)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# 3. Initialize Memory
# --------------------
# Wrap the OpenAI clientso that Memoru can intercept 
# requests and responses to store memories.
print(f"[ MEMORI ]: Initializing agent (DB: {DB_FILE})...")
mem = Memori(conn=session).llm.register(client)

# Attribution tracks WHO said WHAT (Critical for Enterprise Context)
mem.attribution(entity_id="demo_user", process_id="quickstart_script") 
mem.config.storage.build()


# Inspection tools
# ================

def inspect_memories(subject):
    print(f"""\nMemories on "{subject}" ---""")
    
    # Recall
    # ------
    # Ask Memori "What do you know about [subject]?"
    try:
        facts = mem.recall(subject, limit=5)
        if facts:
            for i, fact in enumerate(facts):
                print(f"""- {fact["content"]} (Score: {fact["similarity"]:.2%})""")
        else:
            print(f"""[MISSING]: No memories found on "{subject}".""")
    except Exception as e:
        print(f"[ERROR]: Recall failed: {e}")

    # Raw SQL Logs
    # ------------
    # Prove the data is physically on disk.
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT content FROM memori_conversation_message ORDER BY date_created DESC LIMIT 1")
        row = cursor.fetchone()
        if row:
            print(f"""[SQL LOG]: Last message stored on disk: "{row[0]}" """)
        conn.close()
    except Exception as e:
        print(f"[ERROR]: SQL Inspection failed: {e}")


if __name__ == "__main__":
    
    # Provide the initial fact
    # ------------------------
    user_input = "My favorite food is Fried Rice because I grew up in Toronto."
    print(f"\nUser: {user_input}")
    
    # Send the chat to OpenAI via Memori's wrapper.
    # This automatically triggers the extraction pipeline.
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": user_input}],
    )
    print(f"AI: {response.choices[0].message.content}")

    # Pause until memories from the above chat are fully processed.
    print("\n[Processing] Storing memories...")
    mem.augmentation.wait()

    # Verification
    # ------------
    # Instead of ending the script here, we prove it worked.
    inspect_memories("Fried Rice")
    inspect_memories("Toronto")
    print("\nSUCCESS! Memories persisted and verified.")

    #  Recall
    # -------
    # Ask the AI a question that requires the memory it just formed.
    print("\nRECALL TEST")
    recall_question = "Based on what you just learned, what is my favorite food?"
    print(f"User: {recall_question}")
    
    recall_response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": recall_question}],
    )
    print(f"AI: {recall_response.choices[0].message.content}")
    
    print("\nSUCCESS: Memory persisted, verified, and retrieved.")
```

## Step 4: Run the Application

Execute your Python file:

```bash
python quickstart.py
```

You should see:

- The AI response to the initial statement, “My favorite food is Fried Rice because I grew up in Toronto.”
- The program displaying the memories stored about the subjects “Fried Rice” and “Toronto”, as well as the last thing you said in the chat.
- The AI response to a question about your favorite food, based on a memory provided by Memori.

## Step 5: Check the memories created

```bash
/bin/echo "select * from memori_conversation_message" | /usr/bin/sqlite3 memori.db
/bin/echo "select * from memori_entity_fact" | /usr/bin/sqlite3 memori.db
/bin/echo "select * from memori_process_attribute" | /usr/bin/sqlite3 memori.db
/bin/echo "select * from memori_knowledge_graph" | /usr/bin/sqlite3 memori.db
```

## What Just Happened?

1. **Setup**: You initialized Memori with a SQLite database and registered your OpenAI client
2. **Attribution**: You identified the user (`user-123`) and application (`my-app`) for context tracking
3. **Storage**: The database schema was automatically created
4. **Memory in Action**: Memori automatically captured the first conversation and recalled it in the second one
