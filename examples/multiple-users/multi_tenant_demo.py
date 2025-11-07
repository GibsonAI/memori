from openai import OpenAI

from memori import Memori
from memori.integrations.openai_integration import set_active_memori_context

# Initialize OpenAI client
openai_client = OpenAI()

print("=" * 70)
print("Memori Multi-Tenant Demo - User Isolation")
print("=" * 70)
print()
print("This demo demonstrates how multiple users can use the same database")
print("with complete memory isolation. Each user's memories are stored and")
print("retrieved independently using the user_id parameter.")
print()
print("Features demonstrated:")
print("  - Multiple users (alice, bob) sharing the same database")
print("  - Complete memory isolation between users")
print("  - Independent memory stats per user")
print("  - User-specific memory retrieval")
print()
print("=" * 70)
print()

# Simulate two different users with isolated memories
# Each Memori instance has a different user_id for tenant isolation
users = {
    "alice": Memori(
        database_connect="sqlite:///multi_tenant_demo.db",
        user_id="alice",  # Primary tenant isolation field
        conscious_ingest=True,
        auto_ingest=True,
    ),
    "bob": Memori(
        database_connect="sqlite:///multi_tenant_demo.db",
        user_id="bob",  # Different user_id = different tenant
        conscious_ingest=True,
        auto_ingest=True,
    ),
}

# Enable memory tracking for both users
print("Initializing memory systems...")
for user_id, memori in users.items():
    print(f"  - Enabling memory for user: {user_id}")
    memori.enable()
print()

# Demonstrate multi-tenant isolation with predefined conversations
print("=" * 70)
print("Phase 1: Creating User-Specific Memories")
print("=" * 70)
print()

# Alice's conversation about Python
print("Alice's conversation (about Python):")
print("-" * 70)
alice_messages = [
    "My name is Alice and I love programming in Python.",
    "I'm working on a machine learning project using scikit-learn.",
    "My favorite Python framework is Django for web development.",
]

# Set Alice's context for multi-tenant isolation
set_active_memori_context(users["alice"])

for msg in alice_messages:
    print(f"Alice: {msg}")
    response = openai_client.chat.completions.create(
        model="gpt-4o", messages=[{"role": "user", "content": msg}]
    )
    print(f"AI: {response.choices[0].message.content}")
    print()

# Bob's conversation about Java
print("-" * 70)
print("Bob's conversation (about Java):")
print("-" * 70)
bob_messages = [
    "My name is Bob and I'm a Java developer.",
    "I work with Spring Boot for building microservices.",
    "I prefer Java over other languages for enterprise applications.",
]

# Set Bob's context for multi-tenant isolation
set_active_memori_context(users["bob"])

for msg in bob_messages:
    print(f"Bob: {msg}")
    response = openai_client.chat.completions.create(
        model="gpt-4o", messages=[{"role": "user", "content": msg}]
    )
    print(f"AI: {response.choices[0].message.content}")
    print()

# Display memory isolation
print("=" * 70)
print("Phase 2: Demonstrating Memory Isolation")
print("=" * 70)
print()

# Get memory stats for each user
print("Memory Statistics (showing isolation):")
print("-" * 70)
for user_id, memori in users.items():
    stats = memori.get_memory_stats()
    print(f"\n{user_id.upper()}'s Memory Stats:")
    print(f"  Total memories: {stats.get('total_memories', 0)}")
    print(f"  Short-term memories: {stats.get('short_term_count', 0)}")
    print(f"  Long-term memories: {stats.get('long_term_count', 0)}")

print()
print("-" * 70)

# Search memories to show isolation
print("\nMemory Search Results (demonstrating isolation):")
print("-" * 70)

# Search Alice's memories for "Python"
print("\nSearching Alice's memories for 'Python':")
alice_results = users["alice"].search("Python", limit=3)
print(f"Found {len(alice_results)} results for Alice")
for i, memory in enumerate(alice_results[:2], 1):
    content = memory.get("content", memory.get("searchable_content", "N/A"))
    print(f"  {i}. {content[:100]}...")

# Search Bob's memories for "Python" (should find nothing)
print("\nSearching Bob's memories for 'Python':")
bob_results = users["bob"].search("Python", limit=3)
print(f"Found {len(bob_results)} results for Bob (should be 0 or very few)")
if bob_results:
    for i, memory in enumerate(bob_results[:2], 1):
        content = memory.get("content", memory.get("searchable_content", "N/A"))
        print(f"  {i}. {content[:100]}...")
else:
    print("  No results - Bob has no Python-related memories!")

# Search Bob's memories for "Java"
print("\nSearching Bob's memories for 'Java':")
bob_java_results = users["bob"].search("Java", limit=3)
print(f"Found {len(bob_java_results)} results for Bob")
for i, memory in enumerate(bob_java_results[:2], 1):
    content = memory.get("content", memory.get("searchable_content", "N/A"))
    print(f"  {i}. {content[:100]}...")

# Search Alice's memories for "Java" (should find nothing)
print("\nSearching Alice's memories for 'Java':")
alice_java_results = users["alice"].search("Java", limit=3)
print(f"Found {len(alice_java_results)} results for Alice (should be 0 or very few)")
if alice_java_results:
    for i, memory in enumerate(alice_java_results[:2], 1):
        content = memory.get("content", memory.get("searchable_content", "N/A"))
        print(f"  {i}. {content[:100]}...")
else:
    print("  No results - Alice has no Java-related memories!")

print()
print("=" * 70)
print("Phase 3: Interactive Multi-User Chat")
print("=" * 70)
print()
print("You can now chat as either Alice or Bob. Type:")
print("  'alice: <message>' to chat as Alice")
print("  'bob: <message>' to chat as Bob")
print("  'stats' to see memory statistics")
print("  'exit' to quit")
print("-" * 70)

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
            print("\nMemory Statistics:")
            print("-" * 70)
            for user_id, memori in users.items():
                stats = memori.get_memory_stats()
                print(f"\n{user_id.upper()}:")
                print(f"  Total: {stats.get('total_memories', 0)}")
                print(f"  Short-term: {stats.get('short_term_count', 0)}")
                print(f"  Long-term: {stats.get('long_term_count', 0)}")
            continue

        # Parse user selection
        if user_input.lower().startswith("alice:"):
            current_user = "alice"
            message = user_input[6:].strip()
        elif user_input.lower().startswith("bob:"):
            current_user = "bob"
            message = user_input[4:].strip()
        else:
            print("Please prefix your message with 'alice:' or 'bob:'")
            continue

        if not message:
            print("Please provide a message after the user prefix")
            continue

        # Set the active context for the selected user
        set_active_memori_context(users[current_user])

        print(f"Processing as {current_user}...")
        response = openai_client.chat.completions.create(
            model="gpt-4o", messages=[{"role": "user", "content": message}]
        )
        print(f"AI: {response.choices[0].message.content}")

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
print("  1. Each user_id creates a separate memory tenant")
print("  2. Memories are completely isolated between users")
print("  3. The same database can serve multiple independent users")
print("  4. Memory stats and searches are automatically filtered by user_id")
print()
