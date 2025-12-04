[![Memori Labs](https://s3.us-east-1.amazonaws.com/images.memorilabs.ai/banner.png)](https://memorilabs.ai/)

# Quickstart

Get started with Memori in under 3 minutes.

Memori is LLM, database and framework agnostic and works with the tools you already use today. In this example, we'll show Memori working with OpenAI, SQLAlchemy and SQLite.

- [Supported LLM providers](https://github.com/MemoriLabs/Memori/blob/main/docs/features/llm.md)
- [Supported databases](https://github.com/MemoriLabs/Memori/blob/main/docs/features/databases.md)

## Prerequisites

- Python 3.8 or higher
- An OpenAI API key

## Step 1: Install Libraries

Install Memori:

```bash
pip install memori
```

For this example, you may also need to install:

```bash
pip install openai sqlalchemy
```

## Step 2: Set Your OpenAI API Key

Export your OpenAI API key as an environment variable:

```bash
export OPENAI_API_KEY="your-api-key-here"
```

## Step 3: Run Your First Memori Application

Create a new Python file `quickstart.py` and add the following code:

```python
import os

from memori import Memori
from openai import OpenAI
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Setup OpenAI
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Setup SQLite
engine = create_engine("sqlite:///memori.db")
Session = sessionmaker(bind=engine)

# Setup Memori - that's it!
mem = Memori(conn=Session).openai.register(client)
mem.attribution(entity_id="user-123", process_id="my-app")
mem.config.storage.build()

# First conversation - establish facts
response1 = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": "My favorite color is blue"}],
)
print(response1.choices[0].message.content)

# Second conversation - Memori recalls context automatically
response2 = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": "What's my favorite color?"}],
)
print(response2.choices[0].message.content)  # AI remembers: "blue"!
```

## Step 4: Run the Application

Execute your Python file:

```bash
python quickstart.py
```

You should see the AI respond to both questions, with the second response correctly recalling that your favorite color is blue!

## What Just Happened?

1. **Setup**: You initialized Memori with a SQLite database and registered your OpenAI client
2. **Attribution**: You identified the user (`user-123`) and application (`my-app`) for context tracking
3. **Storage**: The database schema was automatically created
4. **Memory in Action**: Memori automatically captured the first conversation and recalled it in the second one
