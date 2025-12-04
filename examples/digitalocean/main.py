"""
Memori + DigitalOcean Gradient AI Example

Demonstrates how Memori adds persistent memory to DigitalOcean Gradient AI Agents.
"""

import os

from dotenv import load_dotenv
from openai import OpenAI
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from memori import Memori

load_dotenv()

agent_endpoint = os.getenv("AGENT_ENDPOINT")
agent_access_key = os.getenv("AGENT_ACCESS_KEY")

if not agent_endpoint or not agent_access_key:
    raise ValueError("AGENT_ENDPOINT and AGENT_ACCESS_KEY must be set in .env")

base_url = (
    agent_endpoint
    if agent_endpoint.endswith("/api/v1/")
    else f"{agent_endpoint}/api/v1/"
)
client = OpenAI(base_url=base_url, api_key=agent_access_key)

engine = create_engine(os.getenv("DATABASE_CONNECTION_STRING"))
Session = sessionmaker(bind=engine)

mem = Memori(conn=Session).openai.register(client)
mem.attribution(entity_id="user-123", process_id="gradient-agent")
mem.config.storage.build()

if __name__ == "__main__":
    print("You: My favorite color is blue and I live in Paris")
    response1 = client.chat.completions.create(
        model="n/a",
        messages=[
            {"role": "user", "content": "My favorite color is blue and I live in Paris"}
        ],
    )
    print(f"AI: {response1.choices[0].message.content}\n")

    print("You: What's my favorite color?")
    response2 = client.chat.completions.create(
        model="n/a",
        messages=[{"role": "user", "content": "What's my favorite color?"}],
    )
    print(f"AI: {response2.choices[0].message.content}\n")

    print("You: What city do I live in?")
    response3 = client.chat.completions.create(
        model="n/a",
        messages=[{"role": "user", "content": "What city do I live in?"}],
    )
    print(f"AI: {response3.choices[0].message.content}")
