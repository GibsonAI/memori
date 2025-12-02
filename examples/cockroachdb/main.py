"""
Quickstart: Memori + OpenAI + CockroachDB

Demonstrates how Memori adds memory across conversations.
"""

import os

import psycopg2
from openai import OpenAI

from memori import Memori

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def get_conn():
    return psycopg2.connect(os.getenv("COCKROACHDB_CONNECTION_STRING"))


mem = Memori(conn=get_conn).openai.register(client)
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
