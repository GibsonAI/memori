[![Memori Labs](https://s3.us-east-1.amazonaws.com/images.memorilabs.ai/banner.png)](https://memorilabs.ai/)

## Supported LLM Providers

| Provider          | Modes Supported                  | Integration Method        |
| ----------------- | -------------------------------- | ------------------------- |
| **OpenAI**        | Sync, Async, Streamed, Unstreamed | Direct SDK wrapper        |
| **Anthropic**     | Sync, Async, Streamed, Unstreamed | Direct SDK wrapper        |
| **Google (Gemini)** | Sync, Async, Streamed, Unstreamed | Direct SDK wrapper        |
| **xAI (Grok)**    | Sync, Async, Streamed, Unstreamed | Direct SDK wrapper        |
| **Bedrock**       | Via LangChain                    | LangChain ChatBedrock     |
| **LangChain**     | All LangChain chat models        | Native framework support  |
| **Pydantic AI**   | All providers                    | Native framework support  |

## Quick Start Examples

### OpenAI

```python
from memori import Memori
from openai import OpenAI
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

engine = create_engine("sqlite:///memori.db")
SessionLocal = sessionmaker(bind=engine)

client = OpenAI()

mem = Memori(conn=SessionLocal).openai.register(client)
mem.attribution(entity_id="user_123", process_id="my_agent")

response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": "Hello!"}]
)
```

### Anthropic

```python
from anthropic import Anthropic
from memori import Memori
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

engine = create_engine("sqlite:///anthropic_demo.db")
SessionLocal = sessionmaker(bind=engine)

client = Anthropic()

mem = Memori(conn=SessionLocal).anthropic.register(client)
mem.attribution(entity_id="user_123", process_id="claude_assistant")

response = client.messages.create(
    model="claude-3-5-sonnet-20241022",
    max_tokens=1024,
    messages=[{"role": "user", "content": "Hello"}]
)
```

### Google

```python
import os

from memori import Memori
import google.generativeai as genai
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

engine = create_engine("sqlite:///gemini_demo.db")
SessionLocal = sessionmaker(bind=engine)

genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
client = genai.GenerativeModel("gemini-2.0-flash-exp")

mem = Memori(conn=SessionLocal).google.register(client)
mem.attribution(entity_id="user_123", process_id="gemini_assistant")

response = client.generate_content("Hello")
```

### LangChain

```python
from langchain_openai import ChatOpenAI
from memori import Memori
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

engine = create_engine("sqlite:///langchain_demo.db")
SessionLocal = sessionmaker(bind=engine)

client = ChatOpenAI(model="gpt-4o-mini")

mem = Memori(conn=SessionLocal).langchain.register(client)
mem.attribution(entity_id="user_123", process_id="langchain_agent")

response = client.invoke("Hello")
```

### Pydantic AI

```python
from memori import Memori
from pydantic_ai import Agent
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

engine = create_engine("sqlite:///pydantic_demo.db")
SessionLocal = sessionmaker(bind=engine)

agent = Agent("openai:gpt-4o-mini")

mem = Memori(conn=SessionLocal).pydantic_ai.register(agent)
mem.attribution(entity_id="user_123", process_id="pydantic_agent")

result = agent.run_sync("Hello")
```
