#!/usr/bin/env python3

import argparse
import asyncio
import os

from xai_sdk import AsyncClient
from xai_sdk.chat import user

from memori import Memori
from tests.database.core import (
    MongoTestDBSession,
    MySQLTestDBSession,
    OracleTestDBSession,
    PostgresTestDBSession,
    SQLiteTestDBSession,
    TestDBSession,
)

if os.environ.get("XAI_API_KEY", None) is None:
    raise RuntimeError("XAI_API_KEY is not set")

os.environ["MEMORI_TEST_MODE"] = "1"


async def run(db_backend: str = "default"):
    if db_backend == "mongodb":
        session = MongoTestDBSession
    elif db_backend == "mysql":
        session = MySQLTestDBSession
    elif db_backend == "oracle":
        session = OracleTestDBSession
    elif db_backend == "postgres":
        session = PostgresTestDBSession
    elif db_backend == "sqlite":
        session = SQLiteTestDBSession
    else:
        session = TestDBSession

    client = AsyncClient(api_key=os.environ.get("XAI_API_KEY"))

    mem = Memori(conn=session).xai.register(client)

    mem.config.storage.build()

    mem.xai.register(client)

    mem.attribution(entity_id="123", process_id="456")

    print("-" * 25)

    query = "What color is the planet Mars?"
    print(f"me: {query}")
    chat = client.chat.create(
        model="grok-4",
        messages=[user(query)],
    )
    response = await chat.sample()

    print("-" * 25)

    print(f"llm: {response.content}")

    print("-" * 25)

    query = "That planet we're talking about, in order from the sun which one is it?"
    print(f"me: {query}")

    print("-" * 25)
    print("CONVERSATION INJECTION OCCURRED HERE!\n")

    chat = client.chat.create(
        model="grok-4",
        messages=[user(query)],
    )
    response = await chat.sample()

    print("-" * 25)

    print(f"llm: {response.content}")

    print("-" * 25)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Test XAI async client with various database backends"
    )
    parser.add_argument(
        "--db",
        choices=["default", "postgres", "mysql", "oracle", "mongodb", "sqlite"],
        default="default",
        help="Database backend to use (default: uses DATABASE_URL env var)",
    )
    args = parser.parse_args()

    asyncio.run(run(args.db))
