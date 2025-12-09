"""
Memori + Nebius AI Studio + SQLite Example

Demonstrates how Memori adds persistent memory to Nebius AI Studio LLMs.
Nebius AI Studio provides an OpenAI-compatible API with state-of-the-art open-source models.
"""

import os

from dotenv import load_dotenv
from openai import OpenAI
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from memori import Memori

load_dotenv()

db_path = os.getenv("DATABASE_PATH", "memori_nebius.db")
engine = create_engine(f"sqlite:///{db_path}")
Session = sessionmaker(bind=engine)

client = OpenAI(
    base_url="https://api.studio.nebius.com/v1/",
    api_key=os.getenv("NEBIUS_API_KEY"),
)

mem = Memori(conn=Session).llm.register(client)
mem.attribution(entity_id="user-789", process_id="nebius-chat-app")
mem.config.storage.build()

if __name__ == "__main__":
    print("User: My favorite color is blue and I live in Paris")
    response1 = client.chat.completions.create(
        model="meta-llama/Llama-3.3-70B-Instruct",
        messages=[
            {
                "role": "user",
                "content": "My favorite color is blue and I live in Paris.",
            }
        ],
    )
    print(f"Assistant: {response1.choices[0].message.content}\n")

    print("User: What's my favorite color?")
    response2 = client.chat.completions.create(
        model="meta-llama/Llama-3.3-70B-Instruct",
        messages=[{"role": "user", "content": "What's my favorite color?"}],
    )
    print(f"Assistant: {response2.choices[0].message.content}\n")

    print("User: Where do I live?")
    response3 = client.chat.completions.create(
        model="meta-llama/Llama-3.3-70B-Instruct",
        messages=[{"role": "user", "content": "Where do I live?"}],
    )
    print(f"Assistant: {response3.choices[0].message.content}")

    # Advanced Augmentation runs asynchronously to efficiently
    # create memories. For this example, a short lived command
    # line program, we need to wait for it to finish.
    mem.augmentation.wait()
