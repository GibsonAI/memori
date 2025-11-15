import os

from openai import AzureOpenAI

from memori import Memori
from memori.core.providers import ProviderConfig

# Load Azure OpenAI configuration from environment variables
AZURE_API_KEY = os.getenv("AZURE_OPENAI_API_KEY", "your-azure-api-key")
AZURE_ENDPOINT = os.getenv(
    "AZURE_OPENAI_ENDPOINT", "https://your-resource-name.openai.azure.com/"
)
AZURE_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o")
AZURE_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")

# Validate configuration
if "your-" in AZURE_API_KEY or "your-" in AZURE_ENDPOINT:
    print("⚠️ WARNING: Please configure your Azure OpenAI credentials!")
    print("Set environment variables or edit the script with your actual values.")
    print("\nRequired environment variables:")
    print("- AZURE_OPENAI_API_KEY")
    print("- AZURE_OPENAI_ENDPOINT")
    print("- AZURE_OPENAI_DEPLOYMENT_NAME")
    print("- AZURE_OPENAI_API_VERSION (optional)")
    print("\nExample:")
    print("export AZURE_OPENAI_API_KEY='abc123...'")
    print("export AZURE_OPENAI_ENDPOINT='https://mycompany-openai.openai.azure.com/'")
    print("export AZURE_OPENAI_DEPLOYMENT_NAME='gpt-4-turbo'")
    print("\nProceeding with demo configuration...")

# Create explicit provider configuration for Azure OpenAI
azure_provider = ProviderConfig.from_azure(
    api_key=AZURE_API_KEY,
    azure_endpoint=AZURE_ENDPOINT,
    azure_deployment=AZURE_DEPLOYMENT,
    api_version=AZURE_API_VERSION,
    model=AZURE_DEPLOYMENT,
)

# Initialize Memori with Azure OpenAI provider configuration
# This ensures ALL components (memory agents, search engine) use Azure OpenAI
azure_memory = Memori(
    database_connect="sqlite:///azure_openai_env_memory.db",
    conscious_ingest=True,
    auto_ingest=True,
    verbose=True,
    provider_config=azure_provider,  # Pass the complete provider config
)

print("🔷 Azure OpenAI + Memori Advanced Chat Interface")
print(f"📍 Endpoint: {AZURE_ENDPOINT}")
print(f"🚀 Model: {AZURE_DEPLOYMENT}")
print(f"🔑 API Version: {AZURE_API_VERSION}")
print("Type 'quit' to exit, 'stats' for memory statistics")
print("=" * 60)

# Enable automatic interception - this will patch OpenAI module
azure_memory.enable()

# Create Azure OpenAI client - automatically intercepted!
client = AzureOpenAI(
    azure_endpoint=AZURE_ENDPOINT, api_key=AZURE_API_KEY, api_version=AZURE_API_VERSION
)

# Interactive chat loop with enhanced features
conversation_count = 0

while True:
    user_input = input(f"\n🧑 You ({conversation_count + 1}): ").strip()

    if user_input.lower() in ["quit", "exit", "q"]:
        break

    if user_input.lower() == "stats":
        stats = azure_memory.get_memory_stats()
        print("\n📊 Memory Statistics:")
        print(f"   Long-term memories: {stats.get('long_term_count', 0)}")
        print(f"   Chat history: {stats.get('chat_history_count', 0)}")
        print(f"   Conversations: {conversation_count}")
        continue

    if not user_input:
        continue

    try:
        # This call is automatically intercepted and recorded to Memori
        response = client.chat.completions.create(
            model=AZURE_DEPLOYMENT,  # Use your Azure deployment name
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful assistant with access to conversation history through Memori.",
                },
                {"role": "user", "content": user_input},
            ],
            max_tokens=2000,
            temperature=0.7,
            # Azure-specific parameters
            stream=False,
        )

        ai_response = response.choices[0].message.content
        print(f"\n🤖 GPT (Azure): {ai_response}")

        # Show token usage
        if hasattr(response, "usage") and response.usage:
            print(
                f"💰 Tokens: {response.usage.prompt_tokens}→{response.usage.completion_tokens} (Total: {response.usage.total_tokens})"
            )

        # Conversation is automatically recorded with context injection!
        print("📁 Conversation recorded to Memori with context injection")

        conversation_count += 1

    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\n🔧 Troubleshooting:")
        print("1. Verify your Azure OpenAI API key is correct")
        print("2. Check your Azure endpoint URL format")
        print("3. Ensure your deployment name exists and is deployed")
        print("4. Verify your API version is supported")
        print("5. Check Azure OpenAI service status")

        # More detailed error information
        if "401" in str(e):
            print("   → 401 Error: Invalid API key or unauthorized access")
        elif "404" in str(e):
            print("   → 404 Error: Deployment not found - check deployment name")
        elif "429" in str(e):
            print("   → 429 Error: Rate limit exceeded - wait and try again")
        elif "quota" in str(e).lower():
            print("   → Quota Error: Usage limit reached for your Azure subscription")

# Clean shutdown
print(f"\n👋 Shutting down after {conversation_count} conversations...")
azure_memory.disable()
print("✅ Memori disabled - chat history saved!")

# Final statistics
print("\n📈 Session Summary:")
final_stats = azure_memory.get_memory_stats()
print(f"   Conversations processed: {conversation_count}")
print(f"   Long-term memories created: {final_stats.get('long_term_count', 0)}")
print(f"   Total chat history entries: {final_stats.get('chat_history_count', 0)}")
print("   Database: azure_openai_env_memory.db")
