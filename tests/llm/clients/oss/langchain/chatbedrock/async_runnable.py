#!/usr/bin/env python3

import asyncio
import os

from database.core import TestDBSession
from langchain_aws import ChatBedrock
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from memori import Memori

if os.environ.get("AWS_BEARER_TOKEN_BEDROCK", None) is None:
    raise RuntimeError("AWS_BEARER_TOKEN_BEDROCK is not set")

os.environ["MEMORI_TEST_MODE"] = "1"


async def main():
    session = TestDBSession()
    client = ChatBedrock(
        model_id="anthropic.claude-3-5-sonnet-20240620-v1:0", region_name="us-east-1"
    )
    prompt = ChatPromptTemplate.from_messages(
        [
            ("human", "{question}"),
        ]
    )
    chain = prompt | client | StrOutputParser()

    mem = Memori(conn=session).langchain.register(chatbedrock=client)

    # Multiple registrations should not cause an issue.
    mem.langchain.register(chatbedrock=client)

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
