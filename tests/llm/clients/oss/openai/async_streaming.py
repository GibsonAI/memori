#!/usr/bin/env python3

import asyncio
import os

from openai import AsyncOpenAI

from memori import Memori
from tests.database.core import TestDBSession

if os.environ.get("OPENAI_API_KEY", None) is None:
    raise RuntimeError("OPENAI_API_KEY is not set")

os.environ["MEMORI_TEST_MODE"] = "1"


async def run():
    session = TestDBSession
    client = AsyncOpenAI()

    mem = Memori(conn=session).openai.register(client, stream=True)

    # Multiple registrations should not cause an issue.
    mem.openai.register(client)

    mem.attribution(entity_id="123", process_id="456")

    print("-" * 25)

    query = "What color is the planet Mars?"
    print(f"me: {query}")

    print("-" * 25)

    response = ""
    async for chunk in client.chat.completions.create(
        model="gpt-4o-mini", messages=[{"role": "user", "content": query}], stream=True
    ):
        try:
            if chunk.choices[0].delta.content is not None:
                response += chunk.choices[0].delta.content
        except IndexError:
            pass

    print(f"llm: {response}")

    print("-" * 25)

    query = "That planet we're talking about, in order from the sun which one is it?"
    print(f"me: {query}")

    print("-" * 25)
    print("CONVERSATION INJECTION OCCURRED HERE!\n")

    response = ""
    async for chunk in client.chat.completions.create(
        model="gpt-4o-mini", messages=[{"role": "user", "content": query}], stream=True
    ):
        try:
            if chunk.choices[0].delta.content is not None:
                response += chunk.choices[0].delta.content
        except IndexError:
            pass

    print("-" * 25)

    print(f"llm: {response}")

    print("-" * 25)


if __name__ == "__main__":
    asyncio.run(run())
