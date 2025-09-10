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


class Researcher:
    """A researcher class that manages Memori initialization and agent creation"""

    def __init__(self):
        self.memori = Memori(
            database_connect="sqlite:///research_memori.db",
            conscious_ingest=True,  # Working memory
            auto_ingest=True,  # Dynamic search
            verbose=True,
        )
        self.memori.enable()
        self.memory_tool = create_memory_tool(self.memori)
        self.memory_search_function = self._create_memory_search_function()

        self.research_agent = None
        self.memory_agent = None

    def _create_memory_search_function(self):
        """Create memory search function that works with Agno agents"""

        def search_memory(query: str) -> str:
            """Search the agent's memory for past conversations and research information.

            Args:
                query: What to search for in memory (e.g., "past research on AI", "findings on quantum computing")
            """
            try:
                if not query.strip():
                    return "Please provide a search query"

                result = self.memory_tool.execute(query=query.strip())
                return str(result) if result else "No relevant memories found"

            except Exception as e:
                return f"Memory search error: {str(e)}"

        return search_memory

    def run_agent_with_memory(self, agent, user_input: str):
        """Run agent and record each internal conversation step"""
        try:
            # Store original model response method
            original_response = agent.model.response

            def memory_recording_response(messages, **kwargs):
                # Call the original response method
                result = original_response(messages, **kwargs)

                # Extract user input and AI output for recording
                user_msg = ""
                for msg in reversed(messages):
                    if isinstance(msg, dict) and msg.get("role") == "user":
                        user_msg = msg.get("content", "")
                        break
                    elif hasattr(msg, "role") and msg.role == "user":
                        user_msg = msg.content or ""
                        break

                ai_output = ""
                if hasattr(result, "content"):
                    ai_output = result.content or ""
                elif hasattr(result, "choices") and result.choices:
                    choice = result.choices[0]
                    if hasattr(choice, "message") and hasattr(
                        choice.message, "content"
                    ):
                        ai_output = choice.message.content or ""

                # Record this conversation step
                if user_msg or ai_output:
                    try:
                        self.memori.record_conversation(
                            user_input=user_msg, ai_output=ai_output
                        )
                    except Exception as e:
                        print(f"Memory recording error: {str(e)}")

                return result

            # Temporarily replace the model's response method
            agent.model.response = memory_recording_response

            # Run the agent
            result = agent.run(user_input)

            # Restore the original method
            agent.model.response = original_response

            return result

        except Exception as e:
            # Make sure to restore original method even if there's an error
            if "original_response" in locals():
                agent.model.response = original_response
            print(f"Agent execution error: {str(e)}")
            raise

    def define_agents(self):
        """Define and create research and memory agents"""
        # Create research agent
        self.research_agent = self._create_research_agent()

        # Create memory agent
        self.memory_agent = self._create_memory_agent()

        return self.research_agent, self.memory_agent

    def get_research_agent(self):
        """Get the research agent, creating it if necessary"""
        if self.research_agent is None:
            self.define_agents()
        return self.research_agent

    def get_memory_agent(self):
        """Get the memory agent, creating it if necessary"""
        if self.memory_agent is None:
            self.define_agents()
        return self.memory_agent

    def _create_research_agent(self):
        """Create a research agent with Memori memory capabilities and Exa search"""
        agent = Agent(
            model=OpenAIChat(id="gpt-4o"),
            tools=[
                ExaTools(start_published_date=today, type="keyword"),
                self.memory_search_function,
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
                1. FIRST: Use search_memory to find any related previous research on this topic
                2. Run 3 distinct Exa searches to gather comprehensive current information
                3. Analyze and cross-reference sources for accuracy and relevance
                4. If you find relevant previous research, mention how this builds upon it
                5. Structure your report following academic standards but maintain readability
                6. Include only verifiable facts with proper citations
                7. Create an engaging narrative that guides the reader through complex topics
                8. End with actionable takeaways and future implications

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
        )
        return agent

    def _create_memory_agent(self):
        """Create an agent specialized in retrieving research memories"""
        agent = Agent(
            model=OpenAIChat(id="gpt-4o"),
            tools=[self.memory_search_function],
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
                1. Use search_memory to find relevant past research
                2. Organize the results chronologically or by topic
                3. Provide clear summaries of each research session
                4. Highlight key findings and connections between research
                5. If they ask for specific research, provide detailed information

                Always search memory first, then provide organized, helpful summaries!
            """
            ),
            markdown=True,
        )
        return agent
