from openai import OpenAI

from memori import Memori
from memori.integrations.openai_integration import set_active_memori_context

# Initialize OpenAI client
openai_client = OpenAI()

print("=" * 70)
print("Memori Multi-Assistant Demo - Assistant Isolation")
print("=" * 70)
print()
print("This demo demonstrates how multiple AI assistants can serve users")
print("with isolated memories per assistant. Each assistant maintains its")
print("own context and knowledge base using the assistant_id parameter.")
print()
print("Features demonstrated:")
print("  - Multiple assistants (CustomerSupport, SalesBot) for the same user")
print("  - Assistant-specific memory isolation")
print("  - Domain-specific knowledge retention per assistant")
print("  - Independent memory stats per assistant")
print()
print("=" * 70)
print()

# Create multiple assistants for the same user
# Each assistant has a different assistant_id for context isolation
assistants = {
    "CustomerSupport": Memori(
        database_connect="sqlite:///multi_assistant_demo.db",
        user_id="john_doe",  # Same user for all assistants
        assistant_id="CustomerSupport",  # Different assistant_id = different context
        conscious_ingest=True,
        auto_ingest=True,
    ),
    "SalesBot": Memori(
        database_connect="sqlite:///multi_assistant_demo.db",
        user_id="john_doe",  # Same user
        assistant_id="SalesBot",  # Different assistant = different memory space
        conscious_ingest=True,
        auto_ingest=True,
    ),
    "TechAdvisor": Memori(
        database_connect="sqlite:///multi_assistant_demo.db",
        user_id="john_doe",  # Same user
        assistant_id="TechAdvisor",  # Third assistant with separate context
        conscious_ingest=True,
        auto_ingest=True,
    ),
}

# Enable memory for all assistants
print("Initializing assistant memory systems...")
for assistant_name, memori in assistants.items():
    print(f"  - Enabling memory for assistant: {assistant_name}")
    memori.enable()
print()

# Demonstrate assistant-specific memories
print("=" * 70)
print("Phase 1: Creating Assistant-Specific Memories")
print("=" * 70)
print()

# CustomerSupport assistant conversation
print("CustomerSupport Assistant:")
print("-" * 70)
support_messages = [
    "I'm having trouble logging into my account.",
    "I need help resetting my password.",
    "My order #12345 hasn't arrived yet.",
]

# Set CustomerSupport context for multi-tenant isolation
set_active_memori_context(assistants["CustomerSupport"])

for msg in support_messages:
    print(f"User: {msg}")
    response = openai_client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": "You are a customer support assistant. Help users with account and order issues.",
            },
            {"role": "user", "content": msg},
        ],
    )
    print(f"CustomerSupport: {response.choices[0].message.content}")
    print()

# SalesBot assistant conversation
print("-" * 70)
print("SalesBot Assistant:")
print("-" * 70)
sales_messages = [
    "I'm interested in your premium subscription plan.",
    "What features are included in the enterprise tier?",
    "Can I get a discount for annual billing?",
]

# Set SalesBot context for multi-tenant isolation
set_active_memori_context(assistants["SalesBot"])

for msg in sales_messages:
    print(f"User: {msg}")
    response = openai_client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": "You are a sales assistant. Help users understand pricing and features.",
            },
            {"role": "user", "content": msg},
        ],
    )
    print(f"SalesBot: {response.choices[0].message.content}")
    print()

# TechAdvisor assistant conversation
print("-" * 70)
print("TechAdvisor Assistant:")
print("-" * 70)
tech_messages = [
    "How do I integrate your API with my Node.js application?",
    "What's the rate limit for API requests?",
    "Do you support webhooks for real-time updates?",
]

# Set TechAdvisor context for multi-tenant isolation
set_active_memori_context(assistants["TechAdvisor"])

for msg in tech_messages:
    print(f"User: {msg}")
    response = openai_client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": "You are a technical advisor. Help developers integrate and use our platform.",
            },
            {"role": "user", "content": msg},
        ],
    )
    print(f"TechAdvisor: {response.choices[0].message.content}")
    print()

# Display assistant memory isolation
print("=" * 70)
print("Phase 2: Demonstrating Assistant Memory Isolation")
print("=" * 70)
print()

# Get memory stats for each assistant
print("Memory Statistics per Assistant:")
print("-" * 70)
for assistant_name, memori in assistants.items():
    stats = memori.get_memory_stats()
    print(f"\n{assistant_name}:")
    print("  User ID: john_doe")
    print(f"  Assistant ID: {assistant_name}")
    print(f"  Total memories: {stats.get('total_memories', 0)}")
    print(f"  Short-term: {stats.get('short_term_count', 0)}")
    print(f"  Long-term: {stats.get('long_term_count', 0)}")

print()
print("-" * 70)

# Search memories to demonstrate isolation
print("\nMemory Search Results (demonstrating isolation):")
print("-" * 70)

# Search CustomerSupport for "order"
print("\nSearching CustomerSupport memories for 'order':")
support_results = assistants["CustomerSupport"].search("order", limit=3)
print(f"Found {len(support_results)} results in CustomerSupport")
for i, memory in enumerate(support_results[:2], 1):
    content = memory.get("content", memory.get("searchable_content", "N/A"))
    print(f"  {i}. {content[:80]}...")

# Search SalesBot for "order" (should find less or different context)
print("\nSearching SalesBot memories for 'order':")
sales_results = assistants["SalesBot"].search("order", limit=3)
print(f"Found {len(sales_results)} results in SalesBot")
if sales_results:
    for i, memory in enumerate(sales_results[:2], 1):
        content = memory.get("content", memory.get("searchable_content", "N/A"))
        print(f"  {i}. {content[:80]}...")
else:
    print("  No order-related memories in SalesBot!")

# Search SalesBot for "subscription"
print("\nSearching SalesBot memories for 'subscription':")
subscription_results = assistants["SalesBot"].search("subscription", limit=3)
print(f"Found {len(subscription_results)} results in SalesBot")
for i, memory in enumerate(subscription_results[:2], 1):
    content = memory.get("content", memory.get("searchable_content", "N/A"))
    print(f"  {i}. {content[:80]}...")

# Search TechAdvisor for "API"
print("\nSearching TechAdvisor memories for 'API':")
api_results = assistants["TechAdvisor"].search("API", limit=3)
print(f"Found {len(api_results)} results in TechAdvisor")
for i, memory in enumerate(api_results[:2], 1):
    content = memory.get("content", memory.get("searchable_content", "N/A"))
    print(f"  {i}. {content[:80]}...")

# Search CustomerSupport for "API" (should find nothing or very few)
print("\nSearching CustomerSupport memories for 'API':")
support_api_results = assistants["CustomerSupport"].search("API", limit=3)
print(f"Found {len(support_api_results)} results in CustomerSupport")
if support_api_results:
    for i, memory in enumerate(support_api_results[:2], 1):
        content = memory.get("content", memory.get("searchable_content", "N/A"))
        print(f"  {i}. {content[:80]}...")
else:
    print("  No API-related memories in CustomerSupport!")

print()
print("=" * 70)
print("Phase 3: Interactive Multi-Assistant Chat")
print("=" * 70)
print()
print("Chat with different assistants. Type:")
print("  'support: <message>' to chat with CustomerSupport")
print("  'sales: <message>' to chat with SalesBot")
print("  'tech: <message>' to chat with TechAdvisor")
print("  'stats' to see memory statistics")
print("  'exit' to quit")
print("-" * 70)

# Assistant system prompts
assistant_prompts = {
    "support": "You are a customer support assistant. Help users with account and order issues.",
    "sales": "You are a sales assistant. Help users understand pricing and features.",
    "tech": "You are a technical advisor. Help developers integrate and use our platform.",
}

assistant_map = {
    "support": "CustomerSupport",
    "sales": "SalesBot",
    "tech": "TechAdvisor",
}

# Interactive loop
while True:
    try:
        user_input = input("\nYou: ").strip()

        if not user_input:
            continue

        if user_input.lower() == "exit":
            print("\nGoodbye!")
            break

        if user_input.lower() == "stats":
            print("\nMemory Statistics per Assistant:")
            print("-" * 70)
            for assistant_name, memori in assistants.items():
                stats = memori.get_memory_stats()
                print(f"\n{assistant_name}:")
                print(f"  Total: {stats.get('total_memories', 0)}")
                print(f"  Short-term: {stats.get('short_term_count', 0)}")
                print(f"  Long-term: {stats.get('long_term_count', 0)}")
            continue

        # Parse assistant selection
        assistant_key = None
        message = None

        for key in ["support", "sales", "tech"]:
            if user_input.lower().startswith(f"{key}:"):
                assistant_key = key
                message = user_input[len(key) + 1 :].strip()
                break

        if not assistant_key:
            print("Please prefix your message with 'support:', 'sales:', or 'tech:'")
            continue

        if not message:
            print("Please provide a message after the assistant prefix")
            continue

        assistant_name = assistant_map[assistant_key]
        print(f"Processing with {assistant_name}...")

        # Set the active context for the selected assistant
        set_active_memori_context(assistants[assistant_name])

        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": assistant_prompts[assistant_key]},
                {"role": "user", "content": message},
            ],
        )
        print(f"{assistant_name}: {response.choices[0].message.content}")

    except (EOFError, KeyboardInterrupt):
        print("\nExiting...")
        break
    except Exception as e:
        print(f"Error: {e}")
        continue

print()
print("=" * 70)
print("Demo Complete!")
print("=" * 70)
print()
print("Key Takeaways:")
print("  1. Multiple assistants can serve the same user with isolated contexts")
print("  2. Each assistant_id creates a separate memory namespace")
print("  3. Assistants maintain domain-specific knowledge independently")
print("  4. Memory isolation prevents context mixing between assistants")
print("  5. Same user_id + different assistant_id = separate memory spaces")
print()
