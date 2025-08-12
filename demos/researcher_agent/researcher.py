"""
Research Agent Module
Contains the Agno agents for research with Memori integration
"""

import json
import os
import litellm
from datetime import datetime
from pathlib import Path
from textwrap import dedent

from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.tools.exa import ExaTools
from dotenv import load_dotenv

from memori import Memori, create_memory_tool

# Load environment variables from .env file
load_dotenv()


def create_memory_search_tool_wrapper(memori_tool):
    """Create a memory search tool function that works with Agno agents"""
    
    def memory_search(query: str) -> str:
        """Search user's memory for past research topics, findings, and personal research information.

        Use this tool to find information about previous research sessions,
        topics studied, key findings, research patterns, and any other research-related
        information that has been stored in memory.

        Args:
            query: A descriptive search query about what research information you're looking for.
                  Examples: "past research on AI", "findings about quantum computing", 
                  "research on climate change", "biotechnology studies"
        """
        try:
            if not query or not query.strip():
                return "Please provide a specific search query for memory search"

            if memori_tool is None:
                return "Memory tool not initialized"

            # Clean the query
            clean_query = query.strip()
            result = memori_tool.execute(query=clean_query)
            return str(result)
        except Exception as e:
            return f"Memory search error: {str(e)}"

    return memory_search


class ResearchAgent:
    """Main research agent class that manages memory and research agents"""

    def __init__(self):
        """Initialize the research agent with memory and environment variables"""
        # Validate environment variables
        self._validate_environment()

        # Initialize Memori
        self.research_memory = None
        self.memory_tool = None
        self._initialize_memory()

        # Create directories
        self._setup_directories()

    def _validate_environment(self):
        """Validate that required environment variables are present"""
        required_vars = ["OPENAI_API_KEY", "EXA_API_KEY"]
        missing_vars = []

        for var in required_vars:
            if not os.getenv(var):
                missing_vars.append(var)

        if missing_vars:
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing_vars)}. "
                f"Please set them in your .env file or environment."
            )

    def _initialize_memory(self):
        """Initialize Memori instance and memory tool"""
        try:
            # Create personalized research memory
            self.research_memory = Memori(
                database_connect="sqlite:///research_memori.db",
                conscious_ingest=True,  # Enable background analysis
                auto_ingest=True,  # Enable dynamic search
                verbose=False,  # Enable it for detailed logging
                openai_api_key=os.getenv("OPENAI_API_KEY"),
                namespace="researcher_agent",  # Separate namespace for research
            )

            self.research_memory.enable()

            # Create memory tool
            self.memory_tool = create_memory_tool(self.research_memory)

        except Exception as e:
            raise RuntimeError(f"Failed to initialize memory system: {str(e)}")

    def _setup_directories(self):
        """Setup required directories for research outputs"""
        # Create tmp directory for saving reports
        cwd = Path(__file__).parent.resolve()
        self.tmp_dir = cwd.joinpath("tmp")
        if not self.tmp_dir.exists():
            self.tmp_dir.mkdir(exist_ok=True, parents=True)

    def create_research_agent(self) -> Agent:
        """Create a research agent with Memori memory capabilities and Exa search"""

        today = datetime.now().strftime("%Y-%m-%d")

        # Memory search tool wrapper for Agno
        memory_search_wrapper = create_memory_search_tool_wrapper(self.memory_tool)

        # Create the agent with tools
        agent = Agent(
            model=OpenAIChat(id="gpt-4o"),
            tools=[
                ExaTools(start_published_date=today, type="keyword"),
                memory_search_wrapper
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
                1. FIRST: Search your memory using memory_search for any related previous research on this topic
                2. Run 3 distinct Exa searches to gather comprehensive current information
                3. Analyze and cross-reference sources for accuracy and relevance
                4. If you find relevant previous research, mention how this builds upon it
                5. Structure your report following academic standards but maintain readability
                6. Include only verifiable facts with proper citations
                7. Create an engaging narrative that guides the reader through complex topics
                8. End with actionable takeaways and future implications
                9. FINALLY: You MUST use memory_tool to store BOTH the research question and the generated answer for every session, BEFORE presenting the answer to the user. This is a strict requirement.

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
            save_response_to_file=str(self.tmp_dir.joinpath("{message}.md")),
        )
        return agent

    def create_memory_agent(self) -> Agent:
        """Create an agent specialized in retrieving research memories"""

        # Memory search tool wrapper for Agno
        memory_search_wrapper = create_memory_search_tool_wrapper(self.memory_tool)

        # Create the agent with memory tools
        agent = Agent(
            model=OpenAIChat(id="gpt-4o-mini"),
            tools=[
                memory_search_wrapper,
            ],
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
                1. Use your memory tool and memory_search to search for relevant past research
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

    def conduct_research(self, research_request: str, user_preferences: dict = None) -> str:
        """
        Conduct research based on the request and preferences

        Args:
            research_request: The user's research request description
            user_preferences: Optional dictionary with user preferences

        Returns:
            Research report as string
        """
        try:
            # Store preferences in memory if provided
            if user_preferences:
                preference_data = {
                    **user_preferences,
                    "request": research_request,
                    "timestamp": datetime.now().isoformat(),
                }

                # Record preferences in memory
                memory_entry = f"Research request: {research_request}. Preferences: {json.dumps(preference_data)}. Research requested on {datetime.now().strftime('%Y-%m-%d %H:%M')}"

                # Store in memory before research
                self.research_memory.record_conversation(
                    user_input=memory_entry,
                    ai_output="Research request received and processing...",
                )

            # Create research agent
            research_agent = self.create_research_agent()

            # Prepare the full request
            full_request = research_request
            if user_preferences:
                full_request += f"\n\nResearch preferences: {json.dumps(user_preferences)}"

            # Execute the research
            result = research_agent.run(full_request)

            # Store the result in memory
            if user_preferences:
                self.research_memory.record_conversation(
                    user_input=f"Research request: {research_request}. Preferences: {json.dumps(user_preferences)}",
                    ai_output=str(result.content) if hasattr(result, 'content') else str(result),
                )

            return str(result.content) if hasattr(result, 'content') else str(result)

        except Exception as e:
            error_msg = f"Error conducting research: {str(e)}"
            print(f"ResearchAgent Error: {error_msg}")
            return error_msg

    def search_memory(self, query: str) -> str:
        """Search the research memory for past research topics and findings with user-friendly formatting"""
        try:
            if not self.memory_tool:
                return "Memory system not initialized"

            if not query or not query.strip():
                return "Please provide a specific search query"

            # Get raw results from memory
            raw_results = self.memory_tool.execute(query=query.strip())

            # If no results found
            if not raw_results or str(raw_results).strip() in [
                "",
                "None",
                "null",
                "[]",
                "{}",
            ]:
                return f"🔍 I couldn't find any information about '{query}' in your research memory yet. Try conducting some research to build up your memory!"

            # Use LiteLLM to format the results into user-friendly response
            conversation_history = [
                {
                    "role": "system",
                    "content": """You are a helpful research assistant that formats memory search results into friendly, conversational responses.

                    Your job is to take raw memory search results and present them in a clear, user-friendly way.

                    Guidelines:
                    - Be conversational and friendly
                    - Use emojis appropriately
                    - Format information clearly with bullet points or sections when helpful
                    - If the user asks about "last research" or "recent research", focus on the most recent information
                    - If asking about specific topics, highlight relevant research and findings
                    - If asking about research patterns, summarize the key research areas
                    - Keep responses concise but informative
                    - If the raw results seem technical or unclear, extract the key human-readable information
                    """,
                },
                {
                    "role": "user",
                    "content": f"""The user asked: "{query}"

                    Here are the raw memory search results:
                    {raw_results}

                    Please format this into a friendly, conversational response that directly answers their question. Focus on the most relevant information and present it in an easy-to-read format.""",
                },
            ]

            final_response = litellm.completion(
                model="gpt-4o",
                messages=conversation_history,
                api_key=os.getenv("OPENAI_API_KEY"),
            )

            return final_response.choices[0].message.content

        except Exception as e:
            return f"Memory search error: {str(e)}"

    def get_memory_stats(self) -> dict:
        """Get basic statistics about the memory system"""
        try:
            return {
                "status": "Active" if self.research_memory else "Inactive",
                "database": "research_memori.db",
                "namespace": "researcher_agent",
                "conscious_ingest": True,
                "auto_ingest": True,
            }
        except Exception as e:
            return {"error": str(e)}
