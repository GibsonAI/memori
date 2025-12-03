#!/usr/bin/env python3

import os

from agno.agent import Agent
from agno.models.openai import OpenAIChat

from memori import Memori
from tests.database.core import TestDBSession

if os.environ.get("OPENAI_API_KEY", None) is None:
    raise RuntimeError("OPENAI_API_KEY is not set")

os.environ["MEMORI_TEST_MODE"] = "1"

session = TestDBSession
model = OpenAIChat(id="gpt-4o-mini")

mem = Memori(conn=session).agno.register(openai_chat=model)

mem.attribution(entity_id="123", process_id="456")

agent = Agent(
    model=model,
    instructions=["Be helpful and concise"],
    markdown=True,
)

print("-" * 25)

query = "What color is the planet Mars?"
print(f"me: {query}")

print("-" * 25)

session_id = "test-openai-streaming-session"

stream = agent.run(query, session_id=session_id, stream=True)

print("llm: ", end="", flush=True)

for chunk in stream:
    if hasattr(chunk, "content") and chunk.content:
        print(chunk.content, end="", flush=True)

print()
print()
print("-" * 25)

query = "That planet we're talking about, in order from the sun which one is it?"
print(f"me: {query}")

print("-" * 25)
print("CONVERSATION INJECTION OCCURRED HERE!\n")

print("llm: ", end="", flush=True)

for chunk in agent.run(query, session_id=session_id, stream=True):
    if hasattr(chunk, "content") and chunk.content:
        print(chunk.content, end="", flush=True)

print("\n")
print("-" * 25)
