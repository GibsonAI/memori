import os

import streamlit as st
from researcher import (
    create_memory_agent,
    create_research_agent,
)


def main():
    st.set_page_config(
        page_title="Research Agent with Memory", page_icon="🔬", layout="wide"
    )

    st.title("🔬 Research Agent with Persistent Memory")
    st.markdown("### AI Research Assistant that Remembers Everything")

    # Sidebar with navigation and info
    with st.sidebar:
        st.header("Navigation")
        tab_choice = st.radio(
            "Choose Mode:", ["🔬 Research Chat", "🧠 Memory Chat"], key="tab_choice"
        )

        st.header("About This Demo")
        st.markdown(
            """
        This demo showcases:
        - **Research Agent**: Uses Exa for real-time web research
        - **Memori Integration**: Remembers all research sessions
        - **Memory Chat**: Query your research history

        The research agent can:
        - 🔍 Conduct comprehensive research using Exa
        - 🧠 Remember all previous research 
        - 📚 Build upon past research
        - 💾 Store findings for future reference
        """
        )

        st.header("Research History")
        if st.button("�️ Clear All Memory", type="secondary"):
            import sqlite3
            db_path = os.path.join(os.path.dirname(__file__), "research_memori.db")
            try:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                # Drop all tables 
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                tables = cursor.fetchall()
                for table in tables:
                    cursor.execute(f"DROP TABLE IF EXISTS {table[0]}")
                conn.commit()
                conn.close()
                st.success("Research memory cleared!")
            except Exception as e:
                st.error(f"Error clearing memory: {e}")

    # Initialize agents
    if "research_agent" not in st.session_state:
        with st.spinner("Initializing Research Agent with Memory..."):
            st.session_state.research_agent = create_research_agent()

    if "memory_agent" not in st.session_state:
        with st.spinner("Initializing Memory Assistant..."):
            st.session_state.memory_agent = create_memory_agent()

    # Initialize chat histories
    if "research_messages" not in st.session_state:
        st.session_state.research_messages = []
    if "memory_messages" not in st.session_state:
        st.session_state.memory_messages = []

    # Research Chat Tab
    if tab_choice == "🔬 Research Chat":
        st.header("🔬 Research Agent")
        st.markdown(
            "*Ask me to research any topic and I'll create comprehensive reports while remembering everything!*"
        )

        # Display research chat messages
        for message in st.session_state.research_messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        # Research chat input
        if research_prompt := st.chat_input("What would you like me to research?"):
            st.session_state.research_messages.append({"role": "user", "content": research_prompt})
            with st.chat_message("user"):
                st.markdown(research_prompt)
            with st.chat_message("assistant"):
                with st.spinner("🔍 Conducting research and searching memory..."):
                    try:
                        response = st.session_state.research_agent.run(research_prompt)
                        st.markdown(response.content)
                        st.session_state.research_messages.append({"role": "assistant", "content": response.content})
                    except Exception as e:
                        error_message = f"Sorry, I encountered an error: {str(e)}"
                        st.error(error_message)
                        st.session_state.research_messages.append({"role": "assistant", "content": error_message})

        # Research example prompts
        if not st.session_state.research_messages:
            st.markdown("### 🔬 Example Research Topics:")
            col1, col2 = st.columns(2)

            def set_research_chat_input(prompt):
                st.session_state.research_chat_quick_input = prompt

            with col1:
                if st.button("🧠 Brain-Computer Interfaces"):
                    set_research_chat_input("Research the latest developments in brain-computer interfaces")
                if st.button("🔋 Solid-State Batteries"):
                    set_research_chat_input("Analyze the current state of solid-state batteries")

            with col2:
                if st.button("🧬 CRISPR Gene Editing"):
                    set_research_chat_input("Research recent breakthroughs in CRISPR gene editing")
                if st.button("🚗 Autonomous Vehicles"):
                    set_research_chat_input("Investigate the development of autonomous vehicles")

            # If a quick action was selected, simulate chat input
            if st.session_state.get("research_chat_quick_input"):
                quick_prompt = st.session_state.pop("research_chat_quick_input")
                st.session_state.research_messages.append({"role": "user", "content": quick_prompt})
                with st.chat_message("user"):
                    st.markdown(quick_prompt)
                with st.chat_message("assistant"):
                    with st.spinner("🔍 Conducting research and searching memory..."):
                        try:
                            response = st.session_state.research_agent.run(quick_prompt)
                            st.markdown(response.content)
                            st.session_state.research_messages.append({"role": "assistant", "content": response.content})
                        except Exception as e:
                            error_message = f"Sorry, I encountered an error: {str(e)}"
                            st.error(error_message)
                            st.session_state.research_messages.append({"role": "assistant", "content": error_message})

    # Memory Chat Tab
    elif tab_choice == "🧠 Memory Chat":
        st.header("🧠 Research Memory Assistant")
        st.markdown(
            "*Ask me about your previous research sessions and I'll help you recall everything!*"
        )

        # Display memory chat messages
        for message in st.session_state.memory_messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        # Memory chat input
        if memory_prompt := st.chat_input("What would you like to know about your research history?"):
            st.session_state.memory_messages.append({"role": "user", "content": memory_prompt})
            with st.chat_message("user"):
                st.markdown(memory_prompt)
            with st.chat_message("assistant"):
                with st.spinner("🧠 Searching through your research history..."):
                    try:
                        response = st.session_state.memory_agent.run(memory_prompt)
                        st.markdown(response.content)
                        st.session_state.memory_messages.append({"role": "assistant", "content": response.content})
                    except Exception as e:
                        error_message = f"Sorry, I encountered an error: {str(e)}"
                        st.error(error_message)
                        st.session_state.memory_messages.append({"role": "assistant", "content": error_message})

        # Memory example prompts
        if not st.session_state.memory_messages:
            st.markdown("### 🧠 Example Memory Queries:")
            col1, col2 = st.columns(2)


            def set_memory_chat_input(prompt):
                st.session_state.memory_chat_quick_input = prompt

            with col1:
                if st.button("📋 What were my last research topics?"):
                    set_memory_chat_input("What were my last research topics?")
                if st.button("🔍 Show my research on AI"):
                    set_memory_chat_input("Show me all my previous research related to artificial intelligence")

            with col2:
                if st.button("📊 Summarize my research history"):
                    set_memory_chat_input("Can you summarize my research history and main findings?")
                if st.button("🧬 Find my biotech research"):
                    set_memory_chat_input("Find all my research related to biotechnology and gene editing")

            # If a quick action was selected, simulate chat input
            if st.session_state.get("memory_chat_quick_input"):
                quick_prompt = st.session_state.pop("memory_chat_quick_input")
                st.session_state.memory_messages.append({"role": "user", "content": quick_prompt})
                with st.chat_message("user"):
                    st.markdown(quick_prompt)
                with st.chat_message("assistant"):
                    with st.spinner("🧠 Searching through your research history..."):
                        try:
                            response = st.session_state.memory_agent.run(quick_prompt)
                            st.markdown(response.content)
                            st.session_state.memory_messages.append({"role": "assistant", "content": response.content})
                        except Exception as e:
                            error_message = f"Sorry, I encountered an error: {str(e)}"
                            st.error(error_message)
                            st.session_state.memory_messages.append({"role": "assistant", "content": error_message})


if __name__ == "__main__":
    # Check for required environment variables
    if not os.getenv("OPENAI_API_KEY"):
        st.error("Please set your OPENAI_API_KEY environment variable")
        st.stop()
    if not os.getenv("EXA_API_KEY"):
        st.error("Please set your EXA_API_KEY environment variable")
        st.stop()
    main()
