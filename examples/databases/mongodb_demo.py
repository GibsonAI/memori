from openai import OpenAI

from memori import Memori

# Initialize OpenAI client
openai_client = OpenAI()

print("Initializing Memori with MongoDB database...")
memory = Memori(
    database_connect="mongodb://127.0.0.1:56145/memori",
    conscious_ingest=True,
    auto_ingest=True,
)

print("Enabling memory tracking...")
memory.enable()

print("Memori MongoDB Demo - Chat with GPT-4o while memory is being tracked")
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
