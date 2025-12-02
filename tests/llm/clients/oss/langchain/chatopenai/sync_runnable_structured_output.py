#!/usr/bin/env python3

import os

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel

from memori import Memori
from tests.database.core import TestDBSession

if os.environ.get("OPENAI_API_KEY", None) is None:
    raise RuntimeError("OPENAI_API_KEY is not set")

os.environ["MEMORI_TEST_MODE"] = "1"


class Color(BaseModel):
    color: str


class Order(BaseModel):
    order: str


session = TestDBSession
client = ChatOpenAI(model="gpt-4o")

mem = Memori(conn=session).langchain.register(chatopenai=client)

# Multiple registrations should not cause an issue.
mem.langchain.register(chatopenai=client)

mem.attribution(entity_id="123", process_id="456")

print("-" * 25)

query = "What color is the planet Mars: {color}"
print(f"me: {query}")

prompt = ChatPromptTemplate.from_messages([("user", query)])
chain = prompt | client.with_structured_output(Color)

print("-" * 25)

print("llm: ", end="")
print(chain.invoke({"color": "red"}))

print("-" * 25)

query = "What order number is the planet we're talking about from the sun: {order}"
print(f"me: {query}")

prompt = ChatPromptTemplate.from_messages([("user", query)])
chain = prompt | client.with_structured_output(Order)

print("-" * 25)
print("CONVERSATION INJECTION OCCURRED HERE!\n")

response = chain.invoke({"order": "4th"})

print("-" * 25)
print(f"llm: {response}")

print("-" * 25)
