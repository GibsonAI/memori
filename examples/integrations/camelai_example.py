#!/usr/bin/env python3
"""
Lightweight CAMEL AI + Memori Integration Example

A minimal example showing how to integrate Memori memory capabilities
with CAMEL AI agents for persistent memory across conversations.

Requirements:
- pip install memorisdk 'camel-ai[all]' python-dotenv
- Set OPENAI_API_KEY in environment or .env file

Usage:
    python camelai_example.py
"""

import os

from camel.agents import ChatAgent
from camel.toolkits import FunctionTool
from dotenv import load_dotenv

from memori import Memori, create_memory_tool

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
    verbose=False,
    openai_api_key=os.getenv("OPENAI_API_KEY"),
    namespace="camel_example",
)

# Enable the memory system
memory_system.enable()

# Create memory tool for agents
memory_tool = create_memory_tool(memory_system)

print("🤖 Creating memory-enhanced CAMEL AI agent...")


# Create a memory search function for the agent
def search_memory(query: str) -> str:
    """Search the agent's memory for past conversations and information.

    Args:
        query: What to search for in memory (e.g., "past conversations about AI", "user preferences")
    
    Returns:
        Relevant memories or "No relevant memories found"
    """
    try:
        if not query.strip():
            return "Please provide a search query"

        result = memory_tool.execute(query=query.strip())
        return str(result) if result else "No relevant memories found"

    except Exception as e:
        return f"Memory search error: {str(e)}"


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
    tools=[FunctionTool(search_memory)],
    model=("openai", "gpt-4o-mini")
)


def chat_with_memory(user_input: str) -> str:
    """Process user input with memory-enhanced agent"""
    
    # Get response from the agent
    response = assistant_agent.step(user_input)
    
    # Store the conversation in memory
    memory_system.record_conversation(user_input=user_input, ai_output=response.msgs[0].content)
    
    return response.msgs[0].content


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
        response = chat_with_memory(user_input)

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


# Example of how to run specific conversations programmatically:
# 
# if __name__ == "__main__":
#     # Example conversations to test memory
#     test_conversations = [
#         "Hi! I'm a software engineer who loves hiking and cooking Italian food.",
#         "What do you remember about my hobbies?",
#         "I'm planning a weekend trip. Any suggestions based on what you know about me?",
#     ]
#     
#     for i, message in enumerate(test_conversations, 1):
#         print(f"\n=== Test Conversation {i} ===")
#         print(f"User: {message}")
#         response = chat_with_memory(message)
#         print(f"AI: {response}")
#         print("="*50)
