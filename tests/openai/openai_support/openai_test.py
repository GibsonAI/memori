import os
import sys
import time

from openai import OpenAI

from memori import Memori

# Fix imports to work from any directory
script_dir = os.path.dirname(os.path.abspath(__file__))
tests_dir = os.path.dirname(os.path.dirname(script_dir))
if tests_dir not in sys.path:
    sys.path.insert(0, tests_dir)

from tests.utils.test_utils import load_inputs  # noqa: E402

openai_memory = Memori(
    database_connect="sqlite:///openai_memory_CI.db",
    conscious_ingest=True,
    verbose=True,
)

openai_memory.enable()

client = OpenAI()

# Load test inputs from JSON file
json_path = os.path.join(tests_dir, "test_inputs.json")
test_inputs = load_inputs(json_path, limit=10)  # Load only first 10 inputs

for i, user_input in enumerate(test_inputs, 1):
    try:
        response = client.chat.completions.create(
            model="gpt-4o", messages=[{"role": "user", "content": user_input}]
        )

        print(f"[{i}/{len(test_inputs)}] User: {user_input}")
        print(f"[{i}/{len(test_inputs)}] AI: {response.choices[0].message.content}\n")

        # Add small delay to avoid rate limiting
        time.sleep(1)

    except Exception as e:
        print(f"[{i}/{len(test_inputs)}] Error: {e}")
        print("Waiting 60 seconds before continuing...")
        time.sleep(60)
