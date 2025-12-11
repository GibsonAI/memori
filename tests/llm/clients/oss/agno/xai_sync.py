#!/usr/bin/env python3

import os

from agno.agent import Agent
from agno.models.xai import xAI

from memori import Memori
from tests.database.core import TestDBSession

if os.environ.get("XAI_API_KEY", None) is None:
    raise RuntimeError("XAI_API_KEY is not set")

os.environ["MEMORI_TEST_MODE"] = "1"

session = TestDBSession
model = xAI(id="grok-3")

mem = Memori(conn=session).llm.register(xai=model)

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

response = agent.run(query)
print(f"llm: {response.content}")

print("-" * 25)

query = "That planet we're talking about, in order from the sun which one is it?"
print(f"me: {query}")

print("-" * 25)
print("CONVERSATION INJECTION OCCURRED HERE!\n")

response = agent.run(query)

print("-" * 25)
print(f"llm: {response.content}")

print("-" * 25)
