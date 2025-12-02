#!/usr/bin/env python3

import os

from openai import OpenAI

from memori import Memori
from tests.database.core import TestDBSession

if os.environ.get("OPENAI_API_KEY", None) is None:
    raise RuntimeError("OPENAI_API_KEY is not set")

os.environ["MEMORI_TEST_MODE"] = "1"

session = TestDBSession
client = OpenAI()

mem = Memori(conn=session).openai.register(client)

# Multiple registrations should not cause an issue.
mem.openai.register(client)

mem.attribution(entity_id="123", process_id="456")

print("-" * 25)

query = "What color is the planet Mars?"
print(f"me: {query}")
response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": query}],
)

print("-" * 25)

print(f"llm: {response.choices[0].message.content}")

print("-" * 25)

query = "That planet we're talking about, in order from the sun which one is it?"
print(f"me: {query}")

print("-" * 25)
print("CONVERSATION INJECTION OCCURRED HERE!\n")

response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": query}],
)

print("-" * 25)

print(f"llm: {response.choices[0].message.content}")

print("-" * 25)
