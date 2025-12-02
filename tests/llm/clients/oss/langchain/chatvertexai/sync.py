#!/usr/bin/env python3

import os

from langchain_google_vertexai import ChatVertexAI

from memori import Memori
from tests.database.core import TestDBSession

if os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", None) is None:
    raise RuntimeError("GOOGLE_APPLICATION_CREDENTIALS is not set")

os.environ["MEMORI_TEST_MODE"] = "1"

session = TestDBSession
client = ChatVertexAI(
    model_name="gemini-2.0-flash",
    temperature=0,
    seed=42,
)

mem = Memori(conn=session).langchain.register(chatvertexai=client)

# Multiple registrations should not cause an issue.
mem.langchain.register(chatvertexai=client)

mem.attribution(entity_id="123", process_id="456")

print("-" * 25)

query = "What color is the planet Mars?"
print(f"me: {query}")

print("-" * 25)

response = client.invoke(query)
print(f"llm: {response.content}")

print("-" * 25)

query = "That planet we're talking about, in order from the sun which one is it?"
print(f"me: {query}")

print("-" * 25)
print("CONVERSATION INJECTION OCCURRED HERE!\n")

response = client.invoke(query)

print("-" * 25)
print(f"llm: {response.content}")

print("-" * 25)
