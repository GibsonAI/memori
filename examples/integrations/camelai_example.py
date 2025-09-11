#!/usr/bin/env python3
"""
Lightweight CAMEL AI + Memori Integration Example

A minimal example showing how to integrate Memori memory capabilities
with CAMEL AI agents for persistent memory across conversations.

Requirements:
- pip install memorisdk camel-ai python-dotenv
- Set OPENAI_API_KEY in environment or .env file

Usage:
    python camelai_example.py
"""

import os

from camel.agents import ChatAgent
from dotenv import load_dotenv

from memori import Memori

# Load environment variables
load_dotenv()

# Check for required API key
if not os.getenv("OPENAI_API_KEY"):
    print("❌ Error: OPENAI_API_KEY not found in environment variables")
    print("Please set your OpenAI API key:")
    print("export OPENAI_API_KEY='your-api-key-here'")
    print("or create a .env file with: OPENAI_API_KEY=your-api-key-here")
    exit(1)

print("🧠 Initializing Memori memory system...")

# Initialize Memori for persistent memory
memory_system = Memori(
    database_connect="sqlite:///camel_example_memory.db",
    conscious_ingest=True,
    openai_api_key=os.getenv("OPENAI_API_KEY"),
    namespace="camel_example",
)

# Enable the memory system
memory_system.enable()

print("🤖 Creating memory-enhanced CAMEL AI agent...")

# Create CAMEL AI agent with memory tool
assistant_agent = ChatAgent(
    system_message="""You are a helpful AI assistant with the ability to remember past
    conversations and user preferences. Your role is to:
    
    1. Always search your memory first for relevant past conversations using the search_memory tool
    2. Remember important details like preferences, tasks, and personal information
    3. Provide personalized assistance based on conversation history
    4. Help with scheduling, reminders, and general productivity
    5. Be friendly and professional while maintaining continuity
    
    If this is a new user, introduce yourself and explain that you'll remember our conversations.
    Always use the search_memory tool before responding to check for relevant past interactions.""",
    model=("openai", "gpt-4o-mini"),
)

# Main interaction loop
print("✅ Setup complete! Chat with your memory-enhanced CAMEL AI assistant.")
print("Type 'quit' or 'exit' to end the conversation.\n")

print("💡 Try asking about:")
print("- Your past conversations")
print("- Your preferences")
print("- Previous topics discussed")
print("- Any information you've shared before\n")

conversation_count = 0

while True:
    try:
        # Get user input
        user_input = input("You: ").strip()

        # Check for exit commands
        if user_input.lower() in ["quit", "exit", "bye"]:
            print("\nAI: Goodbye! I'll remember our conversation for next time. 🤖✨")
            break

        if not user_input:
            continue

        conversation_count += 1
        print(f"\nAI (thinking... conversation #{conversation_count})")

        # Get response from memory-enhanced agent
        response = assistant_agent.step(user_input)

        print(f"AI: {response}\n")

    except KeyboardInterrupt:
        print("\n\nAI: Goodbye! I'll remember our conversation for next time. 🤖✨")
        break
    except Exception as e:
        print(f"\nError: {str(e)}")
        print("Please try again.\n")

print("\n📊 Session Summary:")
print(f"- Conversations processed: {conversation_count}")
print("- Memory database: camel_example_memory.db")
print("- Namespace: camel_example")
print("\nYour memories are saved and will be available in future sessions!")
