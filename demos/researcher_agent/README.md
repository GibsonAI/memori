# 🧑‍🔬 Researcher Agent Demo with Agno & Memori

An advanced AI research assistant built using the Agno agent framework and Memori memory integration. This demo showcases how to create agents that remember research sessions, build upon previous findings, and provide persistent, organized research support.

## ✨ Features

### 🤖 Agent Capabilities
- **Research Agent**: Conducts real-time web research, generates comprehensive reports, and saves findings to persistent memory
- **Memory Assistant Agent**: Retrieves, summarizes, and organizes previous research sessions for easy recall

### 🧠 Memori Memory Integration
- **Persistent Memory**: All research sessions are stored and can be referenced in future interactions
- **Conscious Ingestion**: Automatically identifies and stores important research information
- **Memory Search**: Enables agents to search and build upon previous research

### 🔍 Web Search Integration
- **Exa Search Tool**: Real-time web search for up-to-date research data
- **Fact-Focused Reports**: Ensures all findings are verifiable and properly cited

### 🎨 Streamlit UI
- **Interactive Web App**: Easy-to-use interface for research and memory queries
- **Chat Modes**: Switch between research and memory assistant agents
- **History & Memory Management**: View, search, and clear research history

## 🚀 Installation

### 1. Prerequisites
```bash
# Ensure you're in the demos/memori_agno_demo directory
cd demos/researcher_agent

# Install Python dependencies
pip install -r requirements.txt
```

### 2. API Keys Required

#### OpenAI API Key
- Visit [OpenAI Platform](https://platform.openai.com/api-keys)
- Create a new API key
- Copy the key (starts with `sk-`)

#### ExaAI API Key
- Visit [ExaAI Platform](https://dashboard.exa.ai/api-keys)
- Create a new API key
- Copy the key

### 3. Environment Setup
Create a `.env` file in this directory:

```env
OPENAI_API_KEY=sk-your-openai-key-here
EXA_API_KEY==your-exa-api-key
```

## 🎯 Usage

### 1. Run the Application
```bash
streamlit run app.py
```

### 2. Research & Memory Features
- **Research Chat**: Ask the agent to research any topic. It will search memory, run web searches, and generate a professional report.
- **Memory Chat**: Query your research history, recall previous topics, and get organized summaries of past findings.
- **History Management**: View all research sessions or clear memory from the sidebar.

## 📋 Example Interactions

### Research Session
```
Input: "Research the latest breakthroughs in quantum computing."

The agent will:
1. Search its memory for previous quantum computing research
2. Run multiple Exa web searches for current developments
3. Cross-reference sources and generate a markdown report
4. Save the session to Memori for future reference
```

### Memory Query
```
Input: "Summarize my research history on AI ethics."

The memory assistant will:
- Search all past research sessions related to AI ethics
- Organize findings chronologically or by topic
- Provide a clear summary and highlight key connections
```

## 📈 Future Enhancements

### Planned Features
- **Multi-agent collaboration**: Integrate more specialized agents for different research domains
- **Advanced memory analytics**: Cluster and compare research topics over time
- **Export & share reports**: Download or share research findings
- **Integration with external databases**: Store and retrieve research from other sources

## 🤝 Contributing

This demo is part of the Memori project. To contribute:

1. Fork the repository
2. Create your feature branch
3. Test with the memori_agno_demo
4. Submit a pull request

## 🙏 Acknowledgments

- **Memori SDK**: For providing the memory layer
- **Agno**: For the agent framework
- **Streamlit**: For the user interface
