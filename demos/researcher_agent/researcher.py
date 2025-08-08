import os
from datetime import datetime
from pathlib import Path
from textwrap import dedent

from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.tools.exa import ExaTools
from dotenv import load_dotenv

from memori import Memori, create_memory_tool

# Load environment variables
load_dotenv()

# Create tmp directory for saving reports
cwd = Path(__file__).parent.resolve()
tmp = cwd.joinpath("tmp")
if not tmp.exists():
    tmp.mkdir(exist_ok=True, parents=True)

today = datetime.now().strftime("%Y-%m-%d")


# Initialize Memori (singleton pattern for Streamlit)
def init_memori():
    """Initialize Memori with memory capabilities"""
    memori = Memori(
        database_connect="sqlite:///research_memori.db",
        conscious_ingest=True,  # Working memory
        auto_ingest=True,  # Dynamic search
        verbose=False,
    )
    memori.enable()
    return memori


# Create Memori tool functions
def memory_search(query: str) -> str:
    """Search memories for relevant research information and past queries."""
    try:
        memori = init_memori()
        memory_tool = create_memory_tool(memori)
        result = memory_tool.execute(query=query)
        return str(result) if result else "No relevant research memories found."
    except Exception as e:
        return f"Memory search error: {str(e)}"


def save_research_memory(research_topic: str, report_content: str) -> str:
    """Save research information to memory for future reference."""
    try:
        init_memori()
        from litellm import completion

        research_conversation = [
            {"role": "system", "content": "Recording research session"},
            {"role": "user", "content": f"Research Topic: {research_topic}"},
            {
                "role": "assistant",
                "content": f"Research Report Generated: {report_content[:500]}...",
            },
        ]
        completion(model="gpt-4o-mini", messages=research_conversation, max_tokens=10)
        return f"Research on '{research_topic}' saved to memory"
    except Exception as e:
        return f"Memory save error: {str(e)}"


# Create the Research Agent with Memori capabilities
def create_research_agent():
    """Create a research agent with Memori memory capabilities and Exa search"""
    agent = Agent(
        model=OpenAIChat(id="gpt-4o"),
        tools=[
            ExaTools(start_published_date=today, type="keyword"),
            memory_search,
            save_research_memory,
        ],
        description=dedent(
            """\
            You are Professor X-1000, a distinguished AI research scientist with MEMORY CAPABILITIES!

            🧠 Your enhanced abilities:
            - Advanced research using real-time web search via Exa
            - Persistent memory of all research sessions
            - Ability to reference and build upon previous research
            - Creating comprehensive, fact-based research reports

            Your writing style is:
            - Clear and authoritative
            - Engaging but professional  
            - Fact-focused with proper citations
            - Accessible to educated non-specialists
            - Builds upon previous research when relevant
        """
        ),
        instructions=dedent(
            """\
            RESEARCH WORKFLOW:
            1. FIRST: Search your memory for any related previous research on this topic
            2. Run 3 distinct Exa searches to gather comprehensive current information
            3. Analyze and cross-reference sources for accuracy and relevance
            4. If you find relevant previous research, mention how this builds upon it
            5. Structure your report following academic standards but maintain readability
            6. Include only verifiable facts with proper citations
            7. Create an engaging narrative that guides the reader through complex topics
            8. End with actionable takeaways and future implications
            9. FINALLY: You MUST use save_research_memory to store BOTH the research question and the generated answer for every session, BEFORE presenting the answer to the user. This is a strict requirement.

            Always mention if you're building upon previous research sessions!
        """
        ),
        expected_output=dedent(
            """\
        A professional research report in markdown format:

        # {Compelling Title That Captures the Topic's Essence}

        ## Executive Summary
        {Brief overview of key findings and significance}
        {Note any connections to previous research if found}

        ## Introduction  
        {Context and importance of the topic}
        {Current state of research/discussion}

        ## Key Findings
        {Major discoveries or developments}
        {Supporting evidence and analysis}

        ## Implications
        {Impact on field/society}
        {Future directions}

        ## Key Takeaways
        - {Bullet point 1}
        - {Bullet point 2} 
        - {Bullet point 3}

        ## References
        - [Source 1](link) - Key finding/quote
        - [Source 2](link) - Key finding/quote
        - [Source 3](link) - Key finding/quote

        ---
        Report generated by Professor X-1000 with Memory Enhancement
        Advanced Research Systems Division
        Date: {current_date}
        """
        ),
        markdown=True,
        show_tool_calls=True,
        add_datetime_to_instructions=True,
        save_response_to_file=str(tmp.joinpath("{message}.md")),
    )
    return agent


# Create the Memory Assistant Agent
def create_memory_agent():
    """Create an agent specialized in retrieving research memories"""
    agent = Agent(
        model=OpenAIChat(id="gpt-4o-mini"),
        tools=[memory_search],
        description=dedent(
            """\
            You are the Research Memory Assistant, specialized in helping users recall their research history!

            🧠 Your capabilities:
            - Search through all past research sessions
            - Summarize previous research topics and findings
            - Help users find specific research they've done before
            - Connect related research across different sessions

            Your style:
            - Friendly and helpful
            - Organized and clear in presenting research history
            - Good at summarizing complex research into digestible insights
        """
        ),
        instructions=dedent(
            """\
            When users ask about their research history:
            1. Use memory_search to find relevant past research
            2. Organize the results chronologically or by topic
            3. Provide clear summaries of each research session
            4. Highlight key findings and connections between research
            5. If they ask for specific research, provide detailed information

            Always search memory first, then provide organized, helpful summaries!
        """
        ),
        markdown=True,
        show_tool_calls=True,
    )
    return agent
