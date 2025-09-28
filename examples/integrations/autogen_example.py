"""
AutoGen + Memori Integration Example

This demonstrates a Software Development Consultant scenario where agents remember:
- Client project requirements and preferences
- Technical decisions and architecture choices
- Past recommendations and implementation details

Requirements:
- pip install memorisdk autogen-agentchat "autogen-ext[openai]" python-dotenv
- Set OPENAI_API_KEY in environment or .env file

Usage:
    python autogen_example.py
"""

import asyncio
import os

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.conditions import MaxMessageTermination
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_ext.models.openai import OpenAIChatCompletionClient
from dotenv import load_dotenv

from memori import Memori

# Load environment variables
load_dotenv()

# Initialize Memori for software development consulting with persistent memory
dev_consulting_memory = Memori(
    database_connect="sqlite:///dev_consulting_memory.db",
    auto_ingest=True,  # Automatically store conversation history
    conscious_ingest=True,  # Store important client preferences and decisions
    verbose=False,  # Enable logging for audit purposes
    namespace="dev_consulting",
)

dev_consulting_memory.enable()

print("=== Software Development Consulting Session ===")
print("🧠 Memori memory system enabled for persistent client context\n")


async def create_consulting_team():
    """Create a team of AutoGen agents for software development consulting"""

    # Initialize OpenAI client
    model_client = OpenAIChatCompletionClient(
        model="gpt-4o-mini",
        api_key=os.getenv("OPENAI_API_KEY"),
    )

    # Create technical architect agent
    architect = AssistantAgent(
        name="TechArchitect",
        model_client=model_client,
        system_message="""You are Alex, a Senior Technical Architect with extensive experience in system design.
        You have persistent memory of client projects, requirements, and technical decisions.
        Always reference past discussions and maintain consistency with previous recommendations.""",
    )

    # Create full-stack developer agent
    developer = AssistantAgent(
        name="FullStackDev",
        model_client=model_client,
        system_message="""You are Sam, a Senior Full-Stack Developer with expertise in modern web technologies.
        You remember client preferences, coding standards, and implementation details from past conversations.
        Build upon previous discussions and maintain consistency in technology recommendations.""",
    )

    # Create termination condition (shorter for demo)
    termination = MaxMessageTermination(max_messages=4)

    # Create round-robin team
    team = RoundRobinGroupChat(
        participants=[architect, developer], termination_condition=termination
    )

    return team


async def run_consulting_scenarios():
    """Run software development consulting scenarios demonstrating memory persistence"""

    team = await create_consulting_team()

    scenarios = [
        # Initial client requirements gathering
        """
        Hi team! I'm building a new e-commerce platform for my retail business.
        I need to handle 10,000+ products, process payments securely, and manage inventory.
        I prefer modern tech stack and have a budget of $50K. My team knows React and Python.
        What architecture would you recommend?
        """,
        # Follow-up technical discussion (should remember previous context)
        """
        Great recommendations! Now I'm concerned about the database choice.
        Given our product catalog size and the budget constraints we discussed,
        what specific database solution would work best?
        """,
        # Implementation details (should remember client preferences and decisions)
        """
        Perfect! Now for the development approach - should we build this as
        a monolith first or go with microservices? Remember our team size
        and the timeline we mentioned.
        """,
    ]

    for i, scenario in enumerate(scenarios, 1):
        print(f"\n--- Consulting Session {i} ---")
        print(f"Client: {scenario.strip()}")
        print("\nConsulting Team Response:")

        # Run the team conversation
        result = await team.run(task=scenario)

        # Print the team's response
        if result.messages:
            for message in result.messages:
                if hasattr(message, "content") and hasattr(message, "source"):
                    print(f"{message.source}: {message.content[:500]}...")

        print("\n" + "=" * 80)

        # Pause between scenarios for readability
        if i < len(scenarios):
            input("Press Enter to continue to next scenario...")


async def main():
    """Main function to run the AutoGen + Memori consulting example"""

    print("🚀 Software Development Consulting with AutoGen + Memori")
    print("=" * 60)
    print("Demonstrating multi-agent consulting with persistent memory")
    print("✅ Technical Architect + Full-Stack Developer team")
    print("✅ Persistent memory across conversation sessions")
    print("✅ Context-aware recommendations")

    try:
        await run_consulting_scenarios()

        print("\n🎯 Session Complete!")
        print("- All conversations automatically saved to memory")
        print("- Context will be available in future sessions")
        print("- Memory database: dev_consulting_memory.db")

    except Exception as e:
        print(f"❌ Error: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(asyncio.run(main()))
