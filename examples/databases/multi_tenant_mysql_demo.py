from openai import OpenAI

from memori import Memori

# Initialize OpenAI client
openai_client = OpenAI()

print("=" * 70)
print("Memori Multi-Tenant MySQL Demo - User Isolation")
print("=" * 70)
print()
print("This demo demonstrates multi-tenant architecture using MySQL")
print("with FULLTEXT search and MySQL-specific optimizations.")
print()
print("MySQL Features:")
print("  - FULLTEXT indexes for fast text search")
print("  - InnoDB engine with ACID compliance")
print("  - Connection pooling for concurrent access")
print("  - JSON column support for flexible metadata")
print("  - Row-level locking for concurrent writes")
print()
print("Multi-Tenant Features:")
print("  - Multiple users sharing the same database")
print("  - Complete memory isolation by user_id")
print("  - Independent memory stats per user")
print("  - FULLTEXT search per tenant")
print()
print("=" * 70)
print()

# MySQL connection string
# Format: mysql+mysqlconnector://user:password@host:port/database
# Adjust this to match your MySQL setup
MYSQL_URL = "mysql+mysqlconnector://root:@127.0.0.1:3306/memori_db"

print("Database Configuration:")
print(f"  Connection: {MYSQL_URL}")
print("  Engine: InnoDB")
print("  Pool size: 5 connections")
print("  Max overflow: 10 additional connections")
print("  FULLTEXT search enabled")
print()

# Create multiple users with MySQL backend
# MySQL FULLTEXT search provides fast memory retrieval
users = {
    "emily": Memori(
        database_connect=MYSQL_URL,
        user_id="emily",  # Primary tenant isolation
        conscious_ingest=True,
        auto_ingest=True,
        # MySQL connection pool configuration
        pool_size=5,
        max_overflow=10,
        pool_timeout=30,
        pool_recycle=3600,
        pool_pre_ping=True,
    ),
    "david": Memori(
        database_connect=MYSQL_URL,
        user_id="david",  # Different tenant
        conscious_ingest=True,
        auto_ingest=True,
        pool_size=5,
        max_overflow=10,
        pool_timeout=30,
        pool_recycle=3600,
        pool_pre_ping=True,
    ),
    "frank": Memori(
        database_connect=MYSQL_URL,
        user_id="frank",  # Third tenant
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
print("Initializing memory systems with MySQL...")
for user_id, memori in users.items():
    print(f"  - Enabling memory for user: {user_id}")
    memori.enable()
print()

# Demonstrate multi-tenant isolation with MySQL
print("=" * 70)
print("Phase 1: Creating User-Specific Memories")
print("=" * 70)
print()

# Emily - E-commerce Manager
print("Emily (E-commerce Manager):")
print("-" * 70)
emily_messages = [
    "I'm Emily, managing an e-commerce platform built with MySQL.",
    "Tracking customer orders, inventory, and sales analytics in real-time.",
    "Using MySQL's InnoDB engine for transactional consistency.",
]

for msg in emily_messages:
    print(f"Emily: {msg}")
    response = openai_client.chat.completions.create(
        model="gpt-4o", messages=[{"role": "user", "content": msg}]
    )
    print(f"AI: {response.choices[0].message.content}")
    print()

# David - Content Manager
print("-" * 70)
print("David (Content Manager):")
print("-" * 70)
david_messages = [
    "I'm David, managing a content platform with millions of articles.",
    "MySQL FULLTEXT search helps users find relevant content quickly.",
    "Optimizing database queries for high-traffic content delivery.",
]

for msg in david_messages:
    print(f"David: {msg}")
    response = openai_client.chat.completions.create(
        model="gpt-4o", messages=[{"role": "user", "content": msg}]
    )
    print(f"AI: {response.choices[0].message.content}")
    print()

# Frank - Analytics Engineer
print("-" * 70)
print("Frank (Analytics Engineer):")
print("-" * 70)
frank_messages = [
    "I'm Frank, an analytics engineer working with MySQL and Python.",
    "Building dashboards that query large datasets stored in MySQL.",
    "Leveraging MySQL partitioning for efficient time-series data.",
]

for msg in frank_messages:
    print(f"Frank: {msg}")
    response = openai_client.chat.completions.create(
        model="gpt-4o", messages=[{"role": "user", "content": msg}]
    )
    print(f"AI: {response.choices[0].message.content}")
    print()

# Display memory isolation with MySQL
print("=" * 70)
print("Phase 2: MySQL Multi-Tenant Isolation")
print("=" * 70)
print()

# Get memory stats
print("Memory Statistics (MySQL-backed):")
print("-" * 70)
for user_id, memori in users.items():
    stats = memori.get_memory_stats()
    print(f"\n{user_id.upper()}'s Memory Stats:")
    print(f"  Total memories: {stats.get('total_memories', 0)}")
    print(f"  Short-term: {stats.get('short_term_count', 0)}")
    print(f"  Long-term: {stats.get('long_term_count', 0)}")

print()
print("-" * 70)

# Demonstrate MySQL FULLTEXT search
print("\nMySQL FULLTEXT Search Results:")
print("-" * 70)

# Search Emily's memories
print("\nSearching Emily's memories for 'e-commerce':")
emily_results = users["emily"].search("e-commerce", limit=3)
print(f"Found {len(emily_results)} results for Emily")
for i, memory in enumerate(emily_results[:2], 1):
    content = memory.get("content", memory.get("searchable_content", "N/A"))
    print(f"  {i}. {content[:100]}...")

# Search David's memories
print("\nSearching David's memories for 'FULLTEXT':")
david_results = users["david"].search("FULLTEXT", limit=3)
print(f"Found {len(david_results)} results for David")
for i, memory in enumerate(david_results[:2], 1):
    content = memory.get("content", memory.get("searchable_content", "N/A"))
    print(f"  {i}. {content[:100]}...")

# Search Frank's memories
print("\nSearching Frank's memories for 'analytics':")
frank_results = users["frank"].search("analytics", limit=3)
print(f"Found {len(frank_results)} results for Frank")
for i, memory in enumerate(frank_results[:2], 1):
    content = memory.get("content", memory.get("searchable_content", "N/A"))
    print(f"  {i}. {content[:100]}...")

# Cross-user search to show isolation
print("\nSearching Emily's memories for 'analytics' (Frank's domain):")
emily_analytics = users["emily"].search("analytics", limit=3)
print(f"Found {len(emily_analytics)} results (should be 0 or very few)")
if not emily_analytics:
    print("  Perfect isolation - no analytics memories in Emily's context!")

print("\nSearching Frank's memories for 'e-commerce' (Emily's domain):")
frank_ecommerce = users["frank"].search("e-commerce", limit=3)
print(f"Found {len(frank_ecommerce)} results (should be 0 or very few)")
if not frank_ecommerce:
    print("  Perfect isolation - no e-commerce memories in Frank's context!")

print()
print("=" * 70)
print("Phase 3: MySQL FULLTEXT Search Features")
print("=" * 70)
print()
print("MySQL FULLTEXT search provides:")
print("  - Fast text search using inverted indexes")
print("  - Boolean mode operators (+, -, *, etc.)")
print("  - Natural language search with relevance ranking")
print("  - Stop word filtering for better results")
print("  - Minimum word length configuration")
print()
print("FULLTEXT indexes are created on searchable_content columns,")
print("enabling fast memory retrieval across large datasets.")
print()

print("=" * 70)
print("Phase 4: Interactive Multi-User Chat")
print("=" * 70)
print()
print("Chat as different users. Type:")
print("  'emily: <message>' to chat as Emily")
print("  'david: <message>' to chat as David")
print("  'frank: <message>' to chat as Frank")
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
            print("\nMemory Statistics (MySQL):")
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
            print("Please prefix your message with 'emily:', 'david:', or 'frank:'")
            continue

        if not message:
            print("Please provide a message after the user prefix")
            continue

        print(f"Processing as {current_user} (MySQL backend)...")
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
print("  1. MySQL provides robust multi-tenant support with InnoDB")
print("  2. FULLTEXT search enables fast memory retrieval")
print("  3. Connection pooling handles concurrent user access")
print("  4. user_id provides complete memory isolation in MySQL")
print("  5. JSON columns allow flexible metadata storage")
print("  6. Row-level locking ensures safe concurrent updates")
print()
print("Production Tips:")
print("  - Create FULLTEXT indexes on searchable columns")
print("  - Use InnoDB for ACID compliance and row-level locking")
print("  - Configure ft_min_word_len for search optimization")
print("  - Monitor connection pool for resource management")
print("  - Consider partitioning for large multi-tenant datasets")
print("  - Regular OPTIMIZE TABLE for FULLTEXT index maintenance")
print()
print("FULLTEXT Search Optimization:")
print("  - Add +word to require word in results")
print("  - Add -word to exclude word from results")
print("  - Use quotes for exact phrase matching")
print("  - * wildcard for prefix matching")
print()
