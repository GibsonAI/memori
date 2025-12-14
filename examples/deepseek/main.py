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
    print("背景信息：我叫berry peng，是一名agent开发工程师，目前住在上海")
    response1 = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {
                "role": "user",
                "content": "我叫berry peng，是一名agent开发工程师，目前住在上海",
            }
        ],
    )
    print(f"AI: {response1.choices[0].message.content}\n")

    # Second conversation - Memori recalls context automatically
    print("You: 我住在哪？")
    response2 = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": "我住在哪？"}],
    )
    print(f"AI: {response2.choices[0].message.content}\n")

    # Third conversation - context is maintained
    print("You: 我的职业是什么")
    response3 = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": "我的职业是什么"}],
    )
    print(f"AI: {response3.choices[0].message.content}")
