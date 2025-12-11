#!/usr/bin/env python3

import os

from agno.agent import Agent
from agno.models.google import Gemini

from memori import Memori
from tests.database.core import TestDBSession

if os.environ.get("GEMINI_API_KEY", None) is None:
    raise RuntimeError("GEMINI_API_KEY is not set")

os.environ["MEMORI_TEST_MODE"] = "1"

session = TestDBSession
model = Gemini(id="gemini-2.0-flash")

mem = Memori(conn=session).llm.register(gemini=model)

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

session_id = "test-gemini-streaming-session"

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
