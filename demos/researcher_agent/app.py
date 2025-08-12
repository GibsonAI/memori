"""
Personalized Research Agent Streamlit App
A clean UI for the Agno-powered research assistant with Memori memory integration
"""

import os
import sqlite3

import streamlit as st
from researcher import ResearchAgent


def main():
    """Main Streamlit application"""

    st.set_page_config(
        page_title="🔬 Personalized Research Agent", page_icon="🧠", layout="wide"
    )

    st.title("🔬 Personalized Research Agent")
    st.markdown("**AI-powered research assistant with memory of your research history**")

    # Initialize the research agent
    if "research_agent" not in st.session_state:
        try:
            with st.spinner("🧠 Initializing research agent..."):
                st.session_state["research_agent"] = ResearchAgent()
                st.success("✅ Research agent initialized!")
        except ValueError as e:
            st.error(f"❌ Configuration Error: {str(e)}")
            st.info("""
            **Please set up your environment:**

            1. Create a `.env` file in this directory with:
            ```
            OPENAI_API_KEY=sk-your-openai-key-here
            EXA_API_KEY=your-exa-key-here
            ```
            
            2. Get your API keys:
            - 🔸 **OpenAI API Key**: Visit [OpenAI Platform](https://platform.openai.com/api-keys)
            - 🔸 **Exa API Key**: Visit [Exa.ai](https://exa.ai) for web search capabilities
            """)
            return
        except Exception as e:
            st.error(f"❌ Initialization Error: {str(e)}")
            st.info("Please check your .env file and dependencies.")
            return

    # Main interface
    col1, col2 = st.columns([2, 1])

    with col1:
        st.header("� Conduct Research")

        # Research request input
        research_request = st.text_area(
            "What would you like me to research?",
            placeholder="Research the latest developments in quantum computing and its potential impact on cryptography.",
            height=100,
        )

        # Additional preferences
        st.subheader("🎯 Research Preferences")

        col_pref1, col_pref2 = st.columns(2)

        with col_pref1:
            research_depth = st.selectbox(
                "Research Depth",
                [
                    "Quick Overview",
                    "Comprehensive Analysis",
                    "Deep Dive with Technical Details",
                    "Academic-level Research",
                ],
            )

            focus_area = st.selectbox(
                "Primary Focus",
                [
                    "Current Developments",
                    "Future Implications",
                    "Technical Analysis",
                    "Market Impact",
                    "Historical Context",
                    "Comparative Analysis",
                    "Mixed Approach",
                ],
            )

        with col_pref2:
            source_preference = st.selectbox(
                "Source Preference",
                [
                    "Academic Papers",
                    "Industry Reports",
                    "News & Articles",
                    "Mixed Sources",
                    "Technical Documentation",
                ],
            )

            output_style = st.selectbox(
                "Output Style",
                [
                    "Executive Summary",
                    "Detailed Report",
                    "Technical Paper",
                    "Presentation Format",
                    "Q&A Style",
                ],
            )

        # Research button
        if st.button("🚀 Conduct Research", type="primary"):
            if not research_request.strip():
                st.warning("Please describe what you'd like me to research!")
                return

            # Prepare preferences data
            user_preferences = {
                "research_depth": research_depth,
                "focus_area": focus_area,
                "source_preference": source_preference,
                "output_style": output_style,
            }

            with st.spinner("🤖 AI research agent is gathering information and analyzing..."):
                try:
                    # Use the research agent to conduct research
                    result = st.session_state["research_agent"].conduct_research(
                        research_request, user_preferences
                    )

                    # Display results
                    st.success("🎉 Your personalized research report is ready!")
                    st.markdown("---")
                    st.markdown(result)

                except Exception as e:
                    st.error(f"❌ Error conducting research: {str(e)}")
                    st.info(
                        "This might be due to API limits or connectivity issues. Please try again."
                    )

    with col2:
        st.header("🧠 Your Research Memory")

        # Memory search
        st.subheader("� Search Research History")
        memory_query = st.text_input(
            "Ask about your research history:",
            placeholder="What was my last research? Show me AI research... Research on climate change...",
        )

        if st.button("Search Memory"):
            if memory_query and "research_agent" in st.session_state:
                try:
                    with st.spinner("🧠 Searching your research memory..."):
                        results = st.session_state["research_agent"].search_memory(
                            memory_query
                        )
                    st.markdown(results)
                except Exception as e:
                    st.error(f"Search error: {str(e)}")
            elif not memory_query:
                st.warning("Please enter a question about your research history!")

        # Add example queries for better user experience
        with st.expander("💡 Example Memory Questions"):
            st.markdown("""
            **Try asking questions like:**
            - "What was my last research topic?"
            - "Show me all my AI research"
            - "What have I studied about climate change?"
            - "My recent quantum computing research"
            - "Research on biotechnology"
            - "What topics have I explored?"
            - "Findings about renewable energy"
            - "My research patterns"
            """)

        # Memory stats
        st.subheader("📊 Memory Stats")
        if "research_agent" in st.session_state:
            try:
                stats = st.session_state["research_agent"].get_memory_stats()
                for key, value in stats.items():
                    st.write(f"🔸 **{key.replace('_', ' ').title()}**: {value}")
            except:
                st.write("Memory stats loading...")

        # Clear memory option
        st.subheader("🗑️ Memory Management")
        if st.button("Clear All Research Memory", type="secondary"):
            try:
                db_path = os.path.join(os.path.dirname(__file__), "research_memori.db")
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                # Drop all tables 
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                tables = cursor.fetchall()
                for table in tables:
                    cursor.execute(f"DROP TABLE IF EXISTS {table[0]}")
                conn.commit()
                conn.close()
                st.success("✅ Research memory cleared!")
                # Reinitialize the agent
                del st.session_state["research_agent"]
                st.rerun()
            except Exception as e:
                st.error(f"Error clearing memory: {e}")

        # Quick tips
        st.subheader("💡 Tips")
        st.info("""
        **This AI remembers:**
        - Your research topics and questions
        - Key findings and insights
        - Research preferences and patterns
        - Historical research sessions
        - Citations and sources

        **The more you research, the better it gets at building upon your previous work!**
        """)

        # Environment status
        st.subheader("⚙️ Configuration")
        if "research_agent" in st.session_state:
            st.success("✅ Environment variables loaded")
            st.success("✅ Memori memory active")
            st.success("✅ Agno research agent ready")
            st.success("✅ Exa search tools active")
        else:
            st.warning("⚠️ Agent not initialized")

    # Quick Research Examples
    st.markdown("---")
    st.subheader("🎯 Quick Research Examples")
    
    col_ex1, col_ex2, col_ex3 = st.columns(3)
    
    with col_ex1:
        if st.button("🧠 AI & Machine Learning"):
            st.session_state["quick_research"] = "Research the latest breakthroughs in artificial intelligence and machine learning, focusing on large language models and their societal impact."
    
    with col_ex2:
        if st.button("🌍 Climate Technology"):
            st.session_state["quick_research"] = "Analyze recent innovations in climate technology, including carbon capture, renewable energy storage, and sustainable materials."
    
    with col_ex3:
        if st.button("🧬 Biotechnology"):
            st.session_state["quick_research"] = "Investigate current developments in biotechnology, particularly CRISPR gene editing, synthetic biology, and personalized medicine."

    # Handle quick research selections
    if "quick_research" in st.session_state and st.session_state["quick_research"]:
        quick_request = st.session_state.pop("quick_research")
        
        with st.spinner("� Conducting quick research..."):
            try:
                result = st.session_state["research_agent"].conduct_research(quick_request)
                st.success("🎉 Quick research completed!")
                st.markdown("---")
                st.markdown("### Research Results:")
                st.markdown(result)
            except Exception as e:
                st.error(f"❌ Error in quick research: {str(e)}")


if __name__ == "__main__":
    main()

