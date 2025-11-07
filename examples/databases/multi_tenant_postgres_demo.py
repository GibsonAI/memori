from openai import OpenAI

from memori import Memori

# Initialize OpenAI client
openai_client = OpenAI()

print("=" * 70)
print("Memori Multi-Tenant PostgreSQL Demo - User Isolation")
print("=" * 70)
print()
print("This demo demonstrates multi-tenant architecture using PostgreSQL")
print("with connection pooling and enterprise-grade features.")
print()
print("PostgreSQL Features:")
print("  - Advanced connection pooling (pool_size, max_overflow)")
print("  - Row-level security support")
print("  - Full-text search with GIN indexes")
print("  - JSONB storage for flexible metadata")
print("  - Transaction isolation and ACID compliance")
print()
print("Multi-Tenant Features:")
print("  - Multiple users sharing the same database")
print("  - Complete memory isolation by user_id")
print("  - Independent memory stats per user")
print("  - Concurrent access with connection pooling")
print()
print("=" * 70)
print()

# PostgreSQL connection string
# Format: postgresql+psycopg2://user:password@host:port/database
# Adjust this to match your PostgreSQL setup
POSTGRES_URL = "postgresql+psycopg2://postgres:@localhost:5432/memori_db"

print("Database Configuration:")
print(f"  Connection: {POSTGRES_URL}")
print("  Pool size: 5 connections")
print("  Max overflow: 10 additional connections")
print("  Pool timeout: 30 seconds")
print("  Connection recycling: 3600 seconds (1 hour)")
print()

# Create multiple users with PostgreSQL backend
# Note: Connection pooling parameters optimize concurrent access
users = {
    "alice": Memori(
        database_connect=POSTGRES_URL,
        user_id="alice",  # Primary tenant isolation
        conscious_ingest=True,
        auto_ingest=True,
        # PostgreSQL connection pool configuration
        pool_size=5,  # Base pool size
        max_overflow=10,  # Extra connections under load
        pool_timeout=30,  # Wait timeout for connections
        pool_recycle=3600,  # Recycle connections after 1 hour
        pool_pre_ping=True,  # Test connections before use
    ),
    "bob": Memori(
        database_connect=POSTGRES_URL,
        user_id="bob",  # Different tenant
        conscious_ingest=True,
        auto_ingest=True,
        pool_size=5,
        max_overflow=10,
        pool_timeout=30,
        pool_recycle=3600,
        pool_pre_ping=True,
    ),
    "charlie": Memori(
        database_connect=POSTGRES_URL,
        user_id="charlie",  # Third tenant
        conscious_ingest=True,
        auto_ingest=True,
        pool_size=5,
        max_overflow=10,
        pool_timeout=30,
        pool_recycle=3600,
        pool_pre_ping=True,
    ),
}

# Enable memory for all users
print("Initializing memory systems with PostgreSQL...")
for user_id, memori in users.items():
    print(f"  - Enabling memory for user: {user_id}")
    memori.enable()
print()

# Demonstrate multi-tenant isolation
print("=" * 70)
print("Phase 1: Creating User-Specific Memories")
print("=" * 70)
print()

# Alice - Data Scientist
print("Alice (Data Scientist):")
print("-" * 70)
alice_messages = [
    "I'm Alice, a data scientist working with PostgreSQL and Python.",
    "Currently analyzing customer behavior data using pandas and scikit-learn.",
    "Need to optimize my database queries for large-scale data processing.",
]

for msg in alice_messages:
    print(f"Alice: {msg}")
    response = openai_client.chat.completions.create(
        model="gpt-4o", messages=[{"role": "user", "content": msg}]
    )
    print(f"AI: {response.choices[0].message.content}")
    print()

# Bob - Backend Engineer
print("-" * 70)
print("Bob (Backend Engineer):")
print("-" * 70)
bob_messages = [
    "I'm Bob, a backend engineer specializing in Node.js and PostgreSQL.",
    "Building REST APIs with Express and using PostgreSQL for data persistence.",
    "Implementing connection pooling with pg-pool for better performance.",
]

for msg in bob_messages:
    print(f"Bob: {msg}")
    response = openai_client.chat.completions.create(
        model="gpt-4o", messages=[{"role": "user", "content": msg}]
    )
    print(f"AI: {response.choices[0].message.content}")
    print()

# Charlie - DevOps Engineer
print("-" * 70)
print("Charlie (DevOps Engineer):")
print("-" * 70)
charlie_messages = [
    "I'm Charlie, a DevOps engineer managing PostgreSQL infrastructure.",
    "Setting up replication and high availability for our production database.",
    "Monitoring PostgreSQL performance metrics and query optimization.",
]

for msg in charlie_messages:
    print(f"Charlie: {msg}")
    response = openai_client.chat.completions.create(
        model="gpt-4o", messages=[{"role": "user", "content": msg}]
    )
    print(f"AI: {response.choices[0].message.content}")
    print()

# Display memory isolation with PostgreSQL
print("=" * 70)
print("Phase 2: PostgreSQL Multi-Tenant Isolation")
print("=" * 70)
print()

# Get memory stats
print("Memory Statistics (PostgreSQL-backed):")
print("-" * 70)
for user_id, memori in users.items():
    stats = memori.get_memory_stats()
    print(f"\n{user_id.upper()}'s Memory Stats:")
    print(f"  Total memories: {stats.get('total_memories', 0)}")
    print(f"  Short-term: {stats.get('short_term_count', 0)}")
    print(f"  Long-term: {stats.get('long_term_count', 0)}")

print()
print("-" * 70)

# Demonstrate PostgreSQL full-text search
print("\nPostgreSQL Full-Text Search Results:")
print("-" * 70)

# Search Alice's memories
print("\nSearching Alice's memories for 'PostgreSQL':")
alice_results = users["alice"].search("PostgreSQL", limit=3)
print(f"Found {len(alice_results)} results for Alice")
for i, memory in enumerate(alice_results[:2], 1):
    content = memory.get("content", memory.get("searchable_content", "N/A"))
    print(f"  {i}. {content[:100]}...")

# Search Bob's memories
print("\nSearching Bob's memories for 'PostgreSQL':")
bob_results = users["bob"].search("PostgreSQL", limit=3)
print(f"Found {len(bob_results)} results for Bob")
for i, memory in enumerate(bob_results[:2], 1):
    content = memory.get("content", memory.get("searchable_content", "N/A"))
    print(f"  {i}. {content[:100]}...")

# Search Charlie's memories
print("\nSearching Charlie's memories for 'PostgreSQL':")
charlie_results = users["charlie"].search("PostgreSQL", limit=3)
print(f"Found {len(charlie_results)} results for Charlie")
for i, memory in enumerate(charlie_results[:2], 1):
    content = memory.get("content", memory.get("searchable_content", "N/A"))
    print(f"  {i}. {content[:100]}...")

# Cross-user search to show isolation
print("\nSearching Alice's memories for 'DevOps' (Charlie's domain):")
alice_devops = users["alice"].search("DevOps", limit=3)
print(f"Found {len(alice_devops)} results (should be 0 or very few)")
if not alice_devops:
    print("  Perfect isolation - no DevOps memories in Alice's context!")

print()
print("=" * 70)
print("Phase 3: PostgreSQL Connection Pool Demo")
print("=" * 70)
print()
print("The connection pool efficiently manages database connections:")
print("  - Base pool of 5 connections per Memori instance")
print("  - Up to 10 overflow connections under heavy load")
print("  - Automatic connection recycling after 1 hour")
print("  - Pre-ping ensures connections are alive before use")
print()
print("This enables concurrent access by multiple users/sessions")
print("without overwhelming the PostgreSQL server.")
print()

print("=" * 70)
print("Phase 4: Interactive Multi-User Chat")
print("=" * 70)
print()
print("Chat as different users. Type:")
print("  'alice: <message>' to chat as Alice")
print("  'bob: <message>' to chat as Bob")
print("  'charlie: <message>' to chat as Charlie")
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
            print("\nMemory Statistics (PostgreSQL):")
            print("-" * 70)
            for user_id, memori in users.items():
                stats = memori.get_memory_stats()
                print(f"\n{user_id.upper()}:")
                print(f"  Total: {stats.get('total_memories', 0)}")
                print(f"  Short-term: {stats.get('short_term_count', 0)}")
                print(f"  Long-term: {stats.get('long_term_count', 0)}")
            continue

        # Parse user selection
        current_user = None
        message = None

        for user_id in users.keys():
            if user_input.lower().startswith(f"{user_id}:"):
                current_user = user_id
                message = user_input[len(user_id) + 1 :].strip()
                break

        if not current_user:
            print("Please prefix your message with 'alice:', 'bob:', or 'charlie:'")
            continue

        if not message:
            print("Please provide a message after the user prefix")
            continue

        print(f"Processing as {current_user} (PostgreSQL backend)...")
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
print("  1. PostgreSQL provides enterprise-grade multi-tenant support")
print("  2. Connection pooling enables efficient concurrent access")
print("  3. Full-text search with GIN indexes for fast memory retrieval")
print("  4. user_id provides complete memory isolation in PostgreSQL")
print("  5. JSONB support allows flexible metadata storage")
print("  6. ACID transactions ensure data consistency across tenants")
print()
print("Production Tips:")
print("  - Use connection pooling to handle multiple concurrent users")
print("  - Consider row-level security for additional isolation")
print("  - Monitor connection pool metrics for optimization")
print("  - Set up replication for high availability")
print("  - Regular VACUUM and ANALYZE for performance")
print()
