#!/usr/bin/env python3

import asyncio
import os

from google import genai

from memori import Memori
from tests.database.core import TestDBSession

if os.environ.get("GEMINI_API_KEY", None) is None:
    raise RuntimeError("GEMINI_API_KEY is not set")

os.environ["MEMORI_TEST_MODE"] = "1"


async def main():
    session = TestDBSession
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

    mem = Memori(conn=session).google.register(client)

    # Multiple registrations should not cause an issue.
    mem.google.register(client)

    mem.attribution(entity_id="123", process_id="456")

    print("-" * 25)

    query = "What color is the planet Mars?"
    print(f"me: {query}")
    response = await client.aio.models.generate_content(
        model="gemini-2.0-flash",
        contents=[{"role": "user", "parts": [{"text": query}]}],
    )

    print("-" * 25)

    print(f"llm: {response.candidates[0].content.parts[0].text}")

    print("-" * 25)

    query = "That planet we're talking about, in order from the sun which one is it?"
    print(f"me: {query}")

    print("-" * 25)
    print("CONVERSATION INJECTION OCCURRED HERE!\n")

    response = await client.aio.models.generate_content(
        model="gemini-2.0-flash",
        contents=[{"role": "user", "parts": [{"text": query}]}],
    )

    print("-" * 25)

    print(f"llm: {response.candidates[0].content.parts[0].text}")

    print("-" * 25)


if __name__ == "__main__":
    asyncio.run(main())
