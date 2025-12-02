#!/usr/bin/env python3

import asyncio
import os

from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI

from memori import Memori
from tests.database.core import TestDBSession

if os.environ.get("OPENAI_API_KEY", None) is None:
    raise RuntimeError("OPENAI_API_KEY is not set")

os.environ["MEMORI_TEST_MODE"] = "1"


async def run():
    session = TestDBSession
    client = ChatOpenAI(model="gpt-4.1", streaming=True)
    message = HumanMessage(content="What color is the planet Mars?")

    mem = Memori(conn=session).langchain.register(chatopenai=client)

    # Multiple registrations should not cause an issue.
    mem.langchain.register(chatopenai=client)

    mem.attribution(entity_id="123", process_id="456")

    print("-" * 25)
    print("me: What color is the planet Mars?")

    response = await client.ainvoke([message])

    print("-" * 25)
    print(f"llm: {response}")


if __name__ == "__main__":
    asyncio.run(run())
