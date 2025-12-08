"""
Memori + Agno + SQLite Example

Demonstrates how Memori adds persistent memory to Agno agents.
"""

import os

from agno.agent import Agent
from agno.models.openai import OpenAIChat
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from memori import Memori

load_dotenv()

db_path = os.getenv("DATABASE_PATH", "memori_agno.db")
engine = create_engine(f"sqlite:///{db_path}")
Session = sessionmaker(bind=engine)

model = OpenAIChat(id="gpt-4o-mini")

mem = Memori(conn=Session).llm.register(openai_chat=model)
mem.attribution(entity_id="customer-456", process_id="support-agent")
mem.config.storage.build()

agent = Agent(
    model=model,
    instructions=[
        "You are a helpful customer support agent.",
        "Remember customer preferences and history from previous conversations.",
    ],
    markdown=True,
)

if __name__ == "__main__":
    print("Customer: Hi, I'd like to order a large pepperoni pizza with extra cheese")
    response1 = agent.run(
        "Hi, I'd like to order a large pepperoni pizza with extra cheese"
    )
    print(f"Agent: {response1.content}\n")

    print("Customer: Actually, can you remind me what I just ordered?")
    response2 = agent.run("Actually, can you remind me what I just ordered?")
    print(f"Agent: {response2.content}\n")

    print("Customer: Perfect! And what size was that again?")
    response3 = agent.run("Perfect! And what size was that again?")
    print(f"Agent: {response3.content}")
