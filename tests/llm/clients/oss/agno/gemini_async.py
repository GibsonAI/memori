#!/usr/bin/env python3

import asyncio
import os

from agno.agent import Agent
from agno.models.google import Gemini

from memori import Memori
from tests.database.core import TestDBSession

if os.environ.get("GEMINI_API_KEY", None) is None:
    raise RuntimeError("GEMINI_API_KEY is not set")

os.environ["MEMORI_TEST_MODE"] = "1"


async def main():
    session = TestDBSession
    model = Gemini(id="gemini-2.0-flash")

    mem = Memori(conn=session).agno.register(gemini=model)

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

    session_id = "test-gemini-async-session"
    response = await agent.arun(query, session_id=session_id)
    print(f"llm: {response.content}")

    print("-" * 25)

    query = "That planet we're talking about, in order from the sun which one is it?"
    print(f"me: {query}")

    print("-" * 25)
    print("CONVERSATION INJECTION OCCURRED HERE!\n")

    response = await agent.arun(query, session_id=session_id)

    print("-" * 25)
    print(f"llm: {response.content}")

    print("-" * 25)


if __name__ == "__main__":
    asyncio.run(main())
