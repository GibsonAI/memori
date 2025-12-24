# Quickstart: Memori + DeepSeek + SQLite

# Demonstrates how Memori adds memory across conversations with DeepSeek.

import os
from dotenv import load_dotenv

load_dotenv()

# Note: DeepSeek uses OpenAI-compatible API
from openai import OpenAI
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from memori import Memori

# Setup DeepSeek client (OpenAI-compatible API)
client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY", "<your_deepseek_api_key_here>"),
    base_url="https://api.deepseek.com/v1",
)

# Setup SQLite
engine = create_engine("sqlite:///deepseek_memori.db")
Session = sessionmaker(bind=engine)

# Setup Memori with DeepSeek (uses OpenAI-compatible API)
mem = Memori(conn=Session).llm.register(client)
mem.attribution(entity_id="user-123", process_id="deepseek-app")
mem.config.storage.build()

if __name__ == "__main__":
    # First conversation - establish facts
    print("")
    response1 = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {
                "role": "user",
                "content": "You: 我正在开发一个基于 Python 的开源项目，我更倾向于使用简洁的代码风格。",
            }
        ],
    )
    print(f"AI: {response1.choices[0].message.content}\n")

    # Second conversation - Memori recalls context automatically
    print("You: 我之前提到我正在开发什么类型的项目？")
    response2 = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": "我住在哪？"}],
    )
    print(f"AI: {response2.choices[0].message.content}\n")

    # Third conversation - context is maintained
    print("You: 我对代码风格有什么要求？")
    response3 = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": "我的职业是什么"}],
    )
    print(f"AI: {response3.choices[0].message.content}")
