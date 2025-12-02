#!/usr/bin/env python3

import asyncio
import os

import anthropic

from memori import Memori
from tests.database.core import TestDBSession

if os.environ.get("ANTHROPIC_API_KEY", None) is None:
    raise RuntimeError("ANTHROPIC_API_KEY is not set")

os.environ["MEMORI_TEST_MODE"] = "1"


async def run():
    session = TestDBSession
    client = anthropic.AsyncAnthropic()

    mem = Memori(conn=session).anthropic.register(client)

    # Multiple registrations should not cause an issue.
    mem.anthropic.register(client)

    mem.attribution(entity_id="123", process_id="456")

    print("-" * 25)

    query = "What color is the planet Mars?"
    print(f"me: {query}")

    response = await client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        messages=[{"role": "user", "content": query}],
    )

    print("-" * 25)

    print(f"llm: {response.content[0].text}")

    print("-" * 25)

    query = "That planet we're talking about, in order from the sun which one is it?"
    print(f"me: {query}")

    print("-" * 25)
    print("CONVERSATION INJECTION OCCURRED HERE!\n")

    response = await client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        messages=[{"role": "user", "content": query}],
    )

    print("-" * 25)

    print(f"llm: {response.content[0].text}")

    print("-" * 25)


if __name__ == "__main__":
    asyncio.run(run())
