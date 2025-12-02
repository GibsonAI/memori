"""
Quickstart: Memori + OpenAI + MongoDB

Demonstrates how Memori adds memory across conversations.
"""

import os

from openai import OpenAI
from pymongo import MongoClient

from memori import Memori

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

mongo_client = MongoClient(os.getenv("MONGODB_CONNECTION_STRING"))
db = mongo_client["memori"]

mem = Memori(conn=lambda: db).openai.register(client)
mem.attribution(entity_id="user-123", process_id="my-app")
mem.config.storage.build()

if __name__ == "__main__":
    print("You: My favorite color is blue and I live in Paris")
    response1 = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "user", "content": "My favorite color is blue and I live in Paris"}
        ],
    )
    print(f"AI: {response1.choices[0].message.content}\n")

    print("You: What's my favorite color?")
    response2 = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "What's my favorite color?"}],
    )
    print(f"AI: {response2.choices[0].message.content}\n")

    print("You: What city do I live in?")
    response3 = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "What city do I live in?"}],
    )
    print(f"AI: {response3.choices[0].message.content}")
