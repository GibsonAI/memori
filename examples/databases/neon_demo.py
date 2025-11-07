"""
Neon Database Demo for Memori

This example demonstrates how to use Memori with Neon, a serverless PostgreSQL database.

Setup:
1. Create a Neon project at: https://console.neon.tech/
2. Get your connection string from the Neon dashboard
3. Install dependencies: pip install openai memorisdk psycopg2-binary
4. Set your OpenAI API key: export OPENAI_API_KEY="your-api-key-here"
5. Replace the connection string below with your own

Connection string format:
postgresql://username:password@hostname/database?sslmode=require&channel_binding=require

Note: SSL parameters (sslmode=require&channel_binding=require) are required for Neon connections.
"""

from openai import OpenAI

from memori import Memori

# Initialize OpenAI client
openai_client = OpenAI()

print("Initializing Memori with Neon PostgreSQL database...")
neon_memory = Memori(
    database_connect="postgresql://username:password@hostname/database?sslmode=require&channel_binding=require",
    conscious_ingest=True,
    auto_ingest=True,
)

print("Enabling memory tracking...")
neon_memory.enable()

print("Memori Neon Demo - Chat with GPT-4o while memory is being tracked")
print("Type 'exit' or press Ctrl+C to quit")
print("-" * 50)

while 1:
    try:
        user_input = input("User: ")
        if not user_input.strip():
            continue

        if user_input.lower() == "exit":
            print("Goodbye!")
            break
        print("Processing your message with memory tracking...")
        response = openai_client.chat.completions.create(
            model="gpt-4o", messages=[{"role": "user", "content": user_input}]
        )
        print(f"AI: {response.choices[0].message.content}")
        print()  # Add blank line for readability
    except (EOFError, KeyboardInterrupt):
        print("\nExiting...")
        break
    except Exception as e:
        print(f"Error: {e}")
        continue
