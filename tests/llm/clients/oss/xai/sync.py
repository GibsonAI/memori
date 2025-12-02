#!/usr/bin/env python3

import os

from xai_sdk import Client
from xai_sdk.chat import user

from memori import Memori
from tests.database.core import TestDBSession

if os.environ.get("XAI_API_KEY", None) is None:
    raise RuntimeError("XAI_API_KEY is not set")

os.environ["MEMORI_TEST_MODE"] = "1"

session = TestDBSession
client = Client(api_key=os.environ.get("XAI_API_KEY"))

mem = Memori(conn=session).xai.register(client)

mem.xai.register(client)

mem.attribution(entity_id="123", process_id="456")

print("-" * 25)

query = "What color is the planet Mars?"
print(f"me: {query}")
chat = client.chat.create(
    model="grok-4",
    messages=[user(query)],
)
response = chat.sample()

print("-" * 25)

print(f"llm: {response.content}")

print("-" * 25)

query = "That planet we're talking about, in order from the sun which one is it?"
print(f"me: {query}")

print("-" * 25)
print("CONVERSATION INJECTION OCCURRED HERE!\n")

chat = client.chat.create(
    model="grok-4",
    messages=[user(query)],
)
response = chat.sample()

print("-" * 25)

print(f"llm: {response.content}")

print("-" * 25)
