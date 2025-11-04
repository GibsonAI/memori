import os

import dotenv
from openai import OpenAI

from memori import Memori

# Load environment variables from .env file
dotenv.load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")
base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
model = os.getenv("OPENAI_MODEL", "gpt-4")

client = OpenAI(api_key=api_key, base_url=base_url)

print("Initializing Memori with OpenAI...")
openai_memory = Memori(
    database_connect="sqlite:///openai_custom_demo.db",
    conscious_ingest=True,
    auto_ingest=True,
    verbose=True,
    api_key=api_key,
    base_url=base_url,
    model=model,
)

print("Enabling memory tracking...")
openai_memory.enable()

print(f"Memori OpenAI Example - Chat with {model} while memory is being tracked")
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
        response = client.chat.completions.create(
            model=model, messages=[{"role": "user", "content": user_input}]
        )
        print(f"AI: {response.choices[0].message.content}")
        print()  # Add blank line for readability
    except (EOFError, KeyboardInterrupt):
        print("\nExiting...")
        break
    except Exception as e:
        print(f"Error: {e}")
        continue
