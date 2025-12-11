#!/usr/bin/env python3

import asyncio
import os

from agno.agent import Agent
from agno.models.anthropic import Claude

from memori import Memori
from tests.database.core import TestDBSession

if os.environ.get("ANTHROPIC_API_KEY", None) is None:
    raise RuntimeError("ANTHROPIC_API_KEY is not set")

os.environ["MEMORI_TEST_MODE"] = "1"


async def main():
    session = TestDBSession
    model = Claude(id="claude-3-5-haiku-20241022")

    mem = Memori(conn=session).llm.register(claude=model)
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

    session_id = "test-anthropic-async-session"
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
