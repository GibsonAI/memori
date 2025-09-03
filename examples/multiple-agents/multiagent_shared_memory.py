"""
Multi-Agent Shared Memory Example with Agno

This example demonstrates how multiple Agno agents can share the same memory
using Memori. The agents collaborate on tasks while maintaining a shared
knowledge base of conversations, decisions, and context.

Scenario: AI Product Development Team
- Product Manager: Plans features and manages requirements
- Developer: Implements technical solutions
- Quality Assurance: Tests and validates features
- Project Coordinator: Manages timelines and coordination

All agents share the same memory namespace for seamless collaboration.

Run: `pip install memorisdk agno` to install dependencies
"""

from textwrap import dedent

from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.tools.memori import MemoriTools
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Shared memory configuration - all agents use the same database and namespace
shared_memori_tools = MemoriTools(
    database_connect="sqlite:///team_shared_memory.db",
    namespace="product_team",
)

# Product Manager Agent
product_manager = Agent(
    name="ProductManager",
    tools=[shared_memori_tools],
    model=OpenAIChat(id="gpt-4o"),
    show_tool_calls=True,
    markdown=True,
    instructions=dedent(
        """\
        You are the Product Manager for an AI development team. Your responsibilities:

        1. **Always search shared memory first** for project history, requirements, and decisions
        2. Define product requirements and user stories
        3. Prioritize features based on business value
        4. Make strategic decisions about product direction
        5. Coordinate with Developer, QA, and Project Coordinator
        6. Track project milestones and deliverables

        **Memory Usage:**
        - Search for previous requirements, decisions, and team discussions
        - Store new requirements, feature specs, and strategic decisions
        - Reference past conversations to maintain project continuity
        - Share context with other team members through shared memory

        Always reference and build upon previous team discussions stored in shared memory.
        """
    ),
)

# Developer Agent
developer = Agent(
    name="Developer",
    tools=[shared_memori_tools],
    model=OpenAIChat(id="gpt-4o"),
    show_tool_calls=True,
    markdown=True,
    instructions=dedent(
        """\
        You are the Lead Developer for an AI development team. Your responsibilities:

        1. **Always search shared memory first** for project context, requirements, and technical decisions
        2. Design and implement technical solutions
        3. Provide technical feasibility assessments
        4. Suggest architectural improvements
        5. Collaborate with Product Manager for requirements clarification
        6. Work with QA to ensure quality implementation

        **Memory Usage:**
        - Search for product requirements, technical specifications, and past implementations
        - Store technical decisions, code architecture, and implementation notes
        - Reference previous technical discussions and solutions
        - Share technical context and constraints with the team

        Always build upon previous technical discussions and decisions stored in shared memory.
        """
    ),
)

# Quality Assurance Agent
qa_engineer = Agent(
    name="QAEngineer",
    tools=[shared_memori_tools],
    model=OpenAIChat(id="gpt-4o"),
    show_tool_calls=True,
    markdown=True,
    instructions=dedent(
        """\
        You are the QA Engineer for an AI development team. Your responsibilities:

        1. **Always search shared memory first** for project requirements, test cases, and quality standards
        2. Design comprehensive test strategies
        3. Identify potential issues and edge cases
        4. Validate feature implementations against requirements
        5. Collaborate with Developer and Product Manager on quality standards
        6. Maintain test documentation and quality metrics

        **Memory Usage:**
        - Search for requirements, technical specs, and previous test results
        - Store test plans, quality standards, and testing outcomes
        - Reference past quality issues and solutions
        - Share testing insights and quality metrics with the team

        Always reference previous testing strategies and quality discussions from shared memory.
        """
    ),
)

# Project Coordinator Agent
project_coordinator = Agent(
    name="ProjectCoordinator",
    tools=[shared_memori_tools],
    model=OpenAIChat(id="gpt-4o"),
    show_tool_calls=True,
    markdown=True,
    instructions=dedent(
        """\
        You are the Project Coordinator for an AI development team. Your responsibilities:

        1. **Always search shared memory first** for project timelines, meetings, and coordination history
        2. Manage project timelines and milestones
        3. Coordinate team meetings and communication
        4. Track project progress and blockers
        5. Facilitate collaboration between team members
        6. Ensure project deliverables are met on time

        **Memory Usage:**
        - Search for project history, timelines, and coordination notes
        - Store meeting summaries, project updates, and timeline adjustments
        - Reference past project challenges and solutions
        - Share project status and coordination insights with the team

        Always build upon previous project coordination and timeline discussions from shared memory.
        """
    ),
)


def run_team_collaboration_demo():
    """Demonstrate multi-agent collaboration with shared memory"""

    print("🚀 Starting AI Product Development Team Collaboration Demo")
    print("=" * 60)
    print("👥 Team Members:")
    print("   - Product Manager: Requirements and strategy")
    print("   - Developer: Technical implementation")
    print("   - QA Engineer: Quality assurance and testing")
    print("   - Project Coordinator: Timeline and coordination")
    print("🧠 Shared Memory: All agents share the same knowledge base")
    print("=" * 60)

    # Phase 1: Project Kickoff
    print("\n📋 PHASE 1: Project Kickoff")
    print("-" * 30)

    product_manager.print_response(
        "We're starting a new AI chatbot feature for our application. "
        "I need to define the initial requirements: The chatbot should handle "
        "customer support queries, integrate with our existing knowledge base, "
        "and provide personalized responses. Priority is high due to customer demand."
    )

    # Phase 2: Technical Assessment
    print("\n💻 PHASE 2: Technical Assessment")
    print("-" * 30)

    developer.print_response(
        "I've seen the Product Manager's requirements for the AI chatbot feature. "
        "Let me assess the technical feasibility and propose an architecture. "
        "What are the specific technical requirements and constraints I should consider?"
    )

    # Phase 3: Quality Planning
    print("\n🔍 PHASE 3: Quality Assurance Planning")
    print("-" * 30)

    qa_engineer.print_response(
        "I've reviewed the chatbot requirements and technical approach from the team. "
        "I need to create a comprehensive testing strategy. What quality standards "
        "and test scenarios should we implement for this AI chatbot feature?"
    )

    # Phase 4: Project Coordination
    print("\n📅 PHASE 4: Project Timeline Coordination")
    print("-" * 30)

    project_coordinator.print_response(
        "Based on the team's discussions about the AI chatbot feature, I need to "
        "create a project timeline. What are the key milestones, dependencies, "
        "and timeline estimates for this project?"
    )

    # Phase 5: Cross-Team Discussion
    print("\n🤝 PHASE 5: Cross-Team Collaboration")
    print("-" * 30)

    product_manager.print_response(
        "Let me check what the team has discussed so far about timelines and "
        "technical implementation. Are there any adjustments needed to the "
        "requirements based on the technical and QA feedback?"
    )

    developer.print_response(
        "I want to review the QA testing strategy and project timeline. "
        "Are there any technical considerations I should address based on "
        "the team's feedback?"
    )

    # Phase 6: Memory Validation
    print("\n🧠 PHASE 6: Shared Memory Validation")
    print("-" * 30)

    qa_engineer.print_response(
        "Can you summarize all the key decisions, requirements, and plans "
        "that our team has made for the AI chatbot project? I want to ensure "
        "our testing strategy aligns with everything discussed."
    )


def demonstrate_memory_consistency():
    """Demonstrate that all agents share the same memory"""

    print("\n🔍 MEMORY CONSISTENCY TEST")
    print("=" * 40)
    print("Testing that all agents can access the same shared information...")

    # Each agent asks about the same project to verify shared memory
    agents = [
        ("Product Manager", product_manager),
        ("Developer", developer),
        ("QA Engineer", qa_engineer),
        ("Project Coordinator", project_coordinator),
    ]

    for agent_name, agent in agents:
        print(f"\n🤖 {agent_name} checking shared memory:")
        print("-" * 30)
        agent.print_response(
            "What do you remember about our AI chatbot project? "
            "Give me a brief summary of the key points discussed by the team."
        )


if __name__ == "__main__":
    print("🧠 Multi-Agent Shared Memory Demo with Agno")
    print("🔧 Each agent accesses the same shared memory namespace")
    print("📝 All conversations and decisions are preserved across agents")
    print()

    # Run the main collaboration demo
    run_team_collaboration_demo()

    # Demonstrate memory consistency across agents
    demonstrate_memory_consistency()

    print("\n✅ Demo Complete!")
    print("🎯 Key Takeaways:")
    print("   - All agents share the same memory namespace")
    print("   - Each agent can access conversations from other agents")
    print("   - Shared memory enables seamless team collaboration")
    print("   - Context is preserved across all team interactions")
    print("   - Decisions and requirements persist across agent sessions")
