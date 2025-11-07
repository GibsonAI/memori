import os
import sys
import time

# Add parent directories to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from litellm import completion
from utils.test_utils import load_inputs

from memori import Memori

# Configure Ollama settings
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma3:1b")

print("🦙 Ollama Test with Memori")
print(f"📍 Server: {OLLAMA_BASE_URL}")
print(f"🤖 Model: {OLLAMA_MODEL}")
print("-" * 50)

# Initialize Memori with Ollama configuration
ollama_memory = Memori(
    database_connect="sqlite:///ollama_memory.db",
    conscious_ingest=True,
    auto_ingest=True,
    verbose=True,
    # Configure Memori to use Ollama for memory agents
    base_url=f"{OLLAMA_BASE_URL}/v1",  # OpenAI-compatible endpoint
    model=OLLAMA_MODEL,
    api_key="ollama",  # Ollama doesn't require a real API key
)

ollama_memory.enable()

# Load test inputs from JSON file
json_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "test_inputs.json")

# Load test inputs (limit to 10 for testing)
test_inputs = load_inputs(json_path, limit=10)

print(f"📝 Loaded {len(test_inputs)} test inputs")
print("🚀 Starting test...\n")

for i, user_input in enumerate(test_inputs, 1):
    try:
        # Use LiteLLM with Ollama configuration
        response = completion(
            model=OLLAMA_MODEL,
            messages=[{"role": "user", "content": user_input}],
            api_base=OLLAMA_BASE_URL,  # Point to Ollama server
            api_key="ollama",  # Dummy key for Ollama
            max_tokens=200,
            temperature=0.7,
        )

        print(f"[{i}/{len(test_inputs)}] User: {user_input}")
        ai_response = response.choices[0].message["content"]
        # Truncate long responses for display
        display_response = (
            ai_response[:150] + "..." if len(ai_response) > 150 else ai_response
        )
        print(f"[{i}/{len(test_inputs)}] AI: {display_response}\n")

        # Small delay to avoid overwhelming local Ollama
        time.sleep(0.5)

    except Exception as e:
        print(f"[{i}/{len(test_inputs)}] Error: {e}")

        # Check for common Ollama errors
        if "connection" in str(e).lower():
            print("❌ Connection error - make sure Ollama is running: 'ollama serve'")
            print("Exiting...")
            break
        elif "model not found" in str(e).lower():
            print(f"❌ Model '{OLLAMA_MODEL}' not found")
            print(f"💡 Install it with: ollama pull {OLLAMA_MODEL}")
            print("Exiting...")
            break
        else:
            print("Waiting 5 seconds before continuing...")
            time.sleep(5)

# Get final statistics
try:
    stats = ollama_memory.get_memory_stats()
    print("\n" + "=" * 50)
    print("📊 Final Memory Statistics:")
    print(f"   Long-term memories: {stats.get('long_term_count', 0)}")
    print(f"   Chat history entries: {stats.get('chat_history_count', 0)}")
    print("=" * 50)
except Exception as e:
    print(f"Could not retrieve memory stats: {e}")

print("\n✅ Test completed!")
print("💾 Database saved to: ollama_memory.db")

# Disable memory
ollama_memory.disable()
