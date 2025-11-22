# Framework Integrations

Memori works seamlessly with popular AI frameworks:

| Framework | Description | Example |
|-----------|-------------|---------|
| [AgentOps](https://github.com/GibsonAI/memori/blob/main/examples/integrations/agentops_example.py) | Track and monitor Memori memory operations with comprehensive observability | Memory operation tracking with AgentOps analytics |
| [Agno](https://github.com/GibsonAI/memori/blob/main/examples/integrations/agno_example.py) | Memory-enhanced agent framework integration with persistent conversations | Simple chat agent with memory search |
| [AWS Strands](https://github.com/GibsonAI/memori/blob/main/examples/integrations/aws_strands_example.py) | Professional development coach with Strands SDK and persistent memory | Career coaching agent with goal tracking |
| [Azure AI Foundry](https://github.com/GibsonAI/memori/blob/main/examples/integrations/azure_ai_foundry_example.py) | Azure AI Foundry agents with persistent memory across conversations | Enterprise AI agents with Azure integration |
| [AutoGen](https://github.com/GibsonAI/memori/blob/main/examples/integrations/autogen_example.py) | Multi-agent group chat memory recording | Agent chats with memory integration |
| [Autogent](https://github.com/GibsonAI/memori/blob/main/examples/integrations/autogent_example.py) | Lightweight agent orchestration with built-in Memori memory storage | Minimal agent loop with automatic memory ingestion |
| [CamelAI](https://github.com/GibsonAI/memori/blob/main/examples/integrations/camelai_example.py) | Multi-agent communication framework with automatic memory recording and retrieval | Memory-enhanced chat agents with conversation continuity |
| [CrewAI](https://github.com/GibsonAI/memori/blob/main/examples/integrations/crewai_example.py) | Multi-agent system with shared memory across agent interactions | Collaborative agents with memory |
| [Digital Ocean AI](https://github.com/GibsonAI/memori/blob/main/examples/integrations/digital_ocean_example.py) | Memory-enhanced customer support using Digital Ocean's AI platform | Customer support assistant with conversation history |
| [LangChain](https://github.com/GibsonAI/memori/blob/main/examples/integrations/langchain_example.py) | Enterprise-grade agent framework with advanced memory integration | AI assistant with LangChain tools and memory |
| [OpenAI Agent](https://github.com/GibsonAI/memori/blob/main/examples/integrations/openai_agent_example.py) | Memory-enhanced OpenAI Agent with function calling and user preference tracking | Interactive assistant with memory search and user info storage |
| [Swarms](https://github.com/GibsonAI/memori/blob/main/examples/integrations/swarms_example.py) | Multi-agent system framework with persistent memory capabilities | Memory-enhanced Swarms agents with auto/conscious ingestion |

"""
Autogent + Memori Integration Example

This example shows how to use Memori as a persistent memory layer inside an
Autogent lightweight agent loop. Each agent turn both retrieves memory and
stores new user/agent messages.

Requirements:
    pip install memori autogent
"""

from autogent.agent import Agent
from memori import Memori


def main():
    # Initialize Memori
    memori = Memori(user_id="autogent_user")

    # Initialize Autogent agent
    agent = Agent(
        name="AutogentAssistant",
        instructions="You are a helpful assistant with long-term memory.",
    )

    print("Autogent + Memori example. Type 'exit' to stop.\n")

    while True:
        user_input = input("You: ")
        if user_input.lower() == "exit":
            break

        # Store user message into memory
        memori.auto(user_input)

        # Retrieve relevant memories to add as context
        memories = memori.search(user_input)
        context_notes = "\n".join([m.content for m in memories])

        # Agent response with memory-augmented context
        response = agent.run(
            f"User said: {user_input}\n\nRelevant past memories:\n{context_notes}"
        )

        print(f"Assistant: {response}")

        # Store the assistant response in memory
        memori.auto(response)


if __name__ == "__main__":
    main()

