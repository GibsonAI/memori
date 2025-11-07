"""
GibsonAI Database Demo for Memori

This demo shows how to use Memori with a GibsonAI serverless database (MySQL).

Setup Instructions:
1. Visit https://app.gibsonai.com/ and sign up for free
2. Create a New Project with a prompt like: "Create an empty database"
3. Go to Databases tab from the GibsonAI App and copy connection string for Development or Production environment
4. Replace the placeholder connection string below with your actual GibsonAI connection string
5. Install required dependencies: pip install openai memorisdk mysql-connector-python
6. Set your OpenAI API key in the environment: export OPENAI_API_KEY

The connection string format looks like:

```
mysql+mysqlconnector://username:password@mysql-assembly.gibsonai.com/database_name
```

"""

from openai import OpenAI

from memori import Memori

# Initialize OpenAI client
openai_client = OpenAI()

print("Initializing Memori with GibsonAI database...")
print("-" * 50)

try:
    # Initialize Memori with GibsonAI database
    gibsonai_memory = Memori(
        database_connect="mysql+mysqlconnector://your_username:your_password@mysql-assembly.gibsonai.com/your_database",
        conscious_ingest=True,
        auto_ingest=True,
        verbose=True,
    )

    print("Enabling memory tracking...")
    gibsonai_memory.enable()

    print("Memori GibsonAI Demo - Chat with GPT-4o while memory is being tracked")
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
            print(f"Error during chat: {e}")
            continue

except Exception as e:
    print(f"Failed to initialize Memori with GibsonAI database: {e}")
