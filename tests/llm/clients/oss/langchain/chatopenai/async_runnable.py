#!/usr/bin/env python3

import asyncio
import os

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from memori import Memori
from tests.database.core import TestDBSession

if os.environ.get("OPENAI_API_KEY", None) is None:
    raise RuntimeError("OPENAI_API_KEY is not set")

os.environ["MEMORI_TEST_MODE"] = "1"


async def main():
    session = TestDBSession
    client = ChatOpenAI(model="gpt-4o", streaming=True)
    prompt = ChatPromptTemplate.from_messages(
        [
            ("human", "{question}"),
        ]
    )
    chain = prompt | client | StrOutputParser()

    mem = Memori(conn=session).langchain.register(chatopenai=client)

    # Multiple registrations should not cause an issue.
    mem.langchain.register(chatopenai=client)

    mem.attribution(entity_id="123", process_id="456")

    print("-" * 25)

    query = "What color is the planet Mars?"
    print(f"me: {query}")

    print("-" * 25)

    print("llm: ", end="")
    async for chunk in chain.astream({"question": query}):
        print(chunk, end="", flush=True)

    print("-" * 25)

    query = "That planet we're talking about, in order from the sun which one is it?"
    print(f"me: {query}")

    print("-" * 25)
    print("CONVERSATION INJECTION OCCURRED HERE!\n")

    response = ""
    async for chunk in chain.astream({"question": query}):
        response += chunk

    print("-" * 25)
    print(f"llm: {response}", end="")

    print("-" * 25)


if __name__ == "__main__":
    asyncio.run(main())
