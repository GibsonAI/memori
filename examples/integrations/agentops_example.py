"""
Memori AgentOps Integration Example
==================================

Track and monitor Memori memory operations with [AgentOps](https://www.agentops.ai/)

- Memory Recording: Track when conversations are automatically captured and stored
- Context Injection: Monitor how memory is automatically added to LLM context
- Conversation Flow: Understand the complete dialogue history across sessions
- Memory Effectiveness: Analyze how historical context improves response quality
- Performance Impact: Track latency and token usage from memory operations
- Error Tracking: Identify issues with memory recording or context retrieval

AgentOps automatically instruments Memori to provide complete observability
of your memory operations.

Installation
-----------
pip install agentops memorisdk openai python-dotenv

Requirements
-----------
- OPENAI_API_KEY environment variable
- AGENTOPS_API_KEY environment variable
"""

import agentops
from openai import OpenAI

from memori import Memori

# Start a trace to group related operations
agentops.start_trace("memori_conversation_flow", tags=["memori_memory_example"])

try:
    # Initialize OpenAI client
    openai_client = OpenAI()

    # Initialize Memori with conscious ingestion enabled
    # AgentOps tracks the memory configuration
    memori = Memori(
        database_connect="sqlite:///agentops_example.db",
        conscious_ingest=True,
        auto_ingest=True,
    )

    memori.enable()

    # First conversation - AgentOps tracks LLM call and memory recording
    response1 = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "user", "content": "I'm working on a Python FastAPI project"}
        ],
    )

    print("Assistant:", response1.choices[0].message.content)

    # Second conversation - AgentOps tracks memory retrieval and context injection
    response2 = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "Help me add user authentication"}],
    )

    print("Assistant:", response2.choices[0].message.content)
    print("💡 Notice: Memori automatically provided FastAPI project context!")

    # End trace - AgentOps aggregates all operations
    agentops.end_trace(end_state="success")

except Exception:
    agentops.end_trace(end_state="error")
