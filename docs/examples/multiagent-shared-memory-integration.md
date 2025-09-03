# Multi-Agent Shared Memory Integration

Advanced demonstration of multiple Agno agents collaborating through shared memory workspace.

## Overview

This example demonstrates how to:

- Create multiple specialized AI agents that share memory
- Enable seamless team collaboration through shared context
- Maintain consistent knowledge across agent interactions
- Implement role-based agent responsibilities
- Coordinate complex multi-agent workflows

## Code

```python title="multiagent_shared_memory.py"
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.tools.memori import MemoriTools
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Shared memory configuration
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
    instructions="""
        You are the Product Manager for an AI development team.
        Always search shared memory first for project context.
        Define requirements and coordinate with team members.
    """
)

# Additional specialized agents (Developer, QA, Coordinator)
developer = Agent(
    name="Developer",
    tools=[shared_memori_tools],
    model=OpenAIChat(id="gpt-4o"),
    instructions="Technical implementation specialist..."
)

qa_engineer = Agent(
    name="QAEngineer", 
    tools=[shared_memori_tools],
    model=OpenAIChat(id="gpt-4o"),
    instructions="Quality assurance expert..."
)

project_coordinator = Agent(
    name="ProjectCoordinator",
    tools=[shared_memori_tools],
    model=OpenAIChat(id="gpt-4o"),
    instructions="Project management specialist..."
)
```

## What Happens

### 1. Shared Memory Setup
```python
shared_memori_tools = MemoriTools(
    database_connect="sqlite:///team_shared_memory.db",
    namespace="product_team",
)
```
- Creates unified memory workspace for all agents
- Enables cross-agent knowledge sharing
- Maintains consistent context across team

### 2. Agent Initialization
```python
product_manager = Agent(
    name="ProductManager",
    tools=[shared_memori_tools],
    model=OpenAIChat(id="gpt-4o"),
    instructions="..."
)
```
- Configures specialized agent roles
- Assigns shared memory access
- Defines role-specific instructions

### 3. Team Collaboration
```python
# Phase 1: Project Kickoff
product_manager.print_response(
    "We're starting a new AI chatbot feature..."
)

# Phase 2: Technical Assessment  
developer.print_response(
    "Let me assess technical feasibility..."
)
```
- Agents collaborate on shared objectives
- Access common knowledge base
- Build upon previous discussions

## Database Contents

The shared SQLite database contains:

```sql
CREATE TABLE memories (
    id INTEGER PRIMARY KEY,
    namespace TEXT,           -- Shared team workspace
    content TEXT,            -- Conversation content
    metadata JSON,           -- Context and role info
    timestamp DATETIME,      -- Creation time
    agent_id TEXT,           -- Source agent
    importance FLOAT         -- Priority ranking
);
```

## Setup Requirements

1. Install dependencies:
```bash
pip install memorisdk agno python-dotenv
```

2. Configure environment variables:
```bash
OPENAI_API_KEY=sk-...
```

3. Initialize database:
```python
from memori import Memori
Memori.init_db("sqlite:///team_shared_memory.db")
```

## Use Cases

- **Product Development Teams**: Coordinate between PM, Dev, and QA
- **Customer Service**: Multiple agents handling support tickets
- **Content Creation**: Writers, editors, and fact-checkers collaboration
- **Research Teams**: Share findings and insights across specialists
- **Project Management**: Coordinate timelines and deliverables

## Best Practices

1. **Memory Organization**
   - Use consistent namespace for team workspace
   - Tag conversations with agent roles
   - Maintain clear conversation threads

2. **Agent Configuration**
   - Define clear role responsibilities
   - Provide detailed agent instructions
   - Enable appropriate memory access

3. **Collaboration Flow**
   - Search memory before taking action
   - Build upon existing context
   - Document key decisions

## Next Steps

- Explore [Advanced Multi-Agent Patterns](../advanced/multi-agent-patterns.md)
- Learn about [Memory Optimization](../guides/memory-optimization.md)
- See [Production Deployment](../deployment/production-setup.md)

## Related Resources

- [Agent Configuration Guide](../guides/agent-config.md)
- [Memory Management](../guides/memory-management.md)
- [Team Collaboration Patterns](../patterns/team-collaboration.md)

The complete example code is available in the [examples repository](https://github.com/GibsonAI/memori/blob/main/examples/multiple-agents/multiagent_shared_memory.py).