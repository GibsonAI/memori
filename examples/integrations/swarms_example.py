from swarms import Agent

from memori import Memori

swarms_memory = Memori(
    database_connect="sqlite:///swarms_memory.db",
    auto_ingest=True,  # Enable automatic ingestion
    conscious_ingest=True,  # Enable conscious ingestion
    verbose=False,  # Disable verbose logging
)

swarms_memory.enable()

agent = Agent(
    model_name="gpt-4o",  # Specify the LLM
    system_prompt="You are an AI assistant with memory capabilities.",
    max_loops="auto",  # Set the number of interactions
    interactive=True,  # Enable interactive mode for real-time feedback
)

agent.run("What is my name ?")
