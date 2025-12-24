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
import os
import sqlite3

from memori import Memori
from openai import OpenAI


def get_sqlite_connection():
    return sqlite3.connect("memori.db")


client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

memori = Memori(conn=get_sqlite_connection).llm.register(client)
memori.attribution(entity_id="123456", process_id="test-ai-agent")
memori.config.storage.build()

response = client.chat.completions.create(
    model="gpt-4.1-mini",
    messages=[
        {"role": "user", "content": "My favorite color is blue."}
    ]
)
print(response.choices[0].message.content + "\n")

# Advanced Augmentation runs asynchronously to efficiently
# create memories. For this example, a short lived command
# line program, we need to wait for it to finish.

memori.augmentation.wait()

# Memori stored that your favorite color is blue in SQLite.
# Now reset everything so there's no prior context.

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

memori = Memori(conn=get_sqlite_connection).llm.register(client)
memori.attribution(entity_id="123456", process_id="test-ai-agent")

response = client.chat.completions.create(
    model="gpt-4.1-mini",
    messages=[
        {"role": "user", "content": "What's my favorite color?"}
    ]
)
print(response.choices[0].message.content + "\n")
```

## Step 4: Run the Application

Execute your Python file:

```bash
python quickstart.py
```

You should see the AI respond to both questions, with the second response correctly recalling that your favorite color is blue!

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
