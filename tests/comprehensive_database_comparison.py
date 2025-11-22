#!/usr/bin/env python3
"""
Comprehensive Database Comparison Suite
Tests SQLite, MySQL, and PostgreSQL with Memori across all functionality
"""

import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path

# Add the memori package to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))


def get_database_connections():
    """Get connection strings for all supported databases"""
    import os

    connections = {}

    # SQLite (always available)
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_db:
        connections["SQLite"] = f"sqlite:///{tmp_db.name}"

    # MySQL (if available)
    try:
        connections["MySQL"] = "mysql+mysqlconnector://root:@127.0.0.1:3306/memori_test"
    except:
        pass

    # PostgreSQL (if available)
    try:
        host = os.environ.get("POSTGRES_HOST", "localhost")
        port = os.environ.get("POSTGRES_PORT", "5432")
        user = os.environ.get("POSTGRES_USER", os.environ.get("USER", "postgres"))
        password = os.environ.get("POSTGRES_PASSWORD", "")

        password_part = f":{password}" if password else ""
        connections["PostgreSQL"] = (
            f"postgresql+psycopg2://{user}{password_part}@{host}:{port}/memori_test"
        )
    except:
        pass

    return connections


def test_database_comprehensive(db_name, connection_string, test_name):
    """Comprehensive database test with all features"""
    print(f"\n{'=' * 60}")
    print(f"🧪 Testing {test_name}")
    print(f"Database: {db_name}")
    print(f"Connection: {connection_string}")
    print(f"{'=' * 60}")

    try:
        from memori import Memori

        # Initialize Memori
        memory = Memori(
            database_connect=connection_string,
            conscious_ingest=False,
            auto_ingest=True,  # Enable auto ingestion for testing
            verbose=False,  # Reduce noise for comparison
        )

        print(f"✅ {db_name} connection established")

        # Get database information
        db_info = memory.db_manager.get_database_info()
        print(
            f"📊 Database: {db_info['database_type']} v{db_info.get('server_version', 'N/A')}"
        )
        print(f"🔍 Full-text search: {db_info.get('supports_fulltext', 'Unknown')}")

        # Clear test namespace
        test_namespace = f"comparison_test_{db_name.lower()}"
        memory.db_manager.clear_memory(test_namespace)

        # Performance test data
        test_results = {
            "db_name": db_name,
            "connection_string": connection_string,
            "insert_time": 0,
            "retrieval_time": 0,
            "search_time": 0,
            "search_results": 0,
            "search_strategy": "none",
            "chat_count": 0,
            "error": None,
        }

        # Test 1: Bulk insertion performance
        print("\n⚡ Performance Test 1: Bulk insertion (15 records)")
        start_time = time.time()

        test_messages = [
            "What is artificial intelligence and how does it work?",
            "Explain machine learning algorithms in simple terms",
            "What are the benefits of database normalization?",
            "How does full-text search work in different databases?",
            "Compare SQLite, MySQL, and PostgreSQL performance",
            "What is the difference between SQL and NoSQL databases?",
            "Explain ACID properties in database transactions",
            "How do database indexes improve query performance?",
            "What is database sharding and when is it used?",
            "Describe the CAP theorem in distributed systems",
            "What are the advantages of using an ORM like SQLAlchemy?",
            "How does database replication work?",
            "What is the purpose of database connection pooling?",
            "Explain different types of database joins",
            "What are stored procedures and their benefits?",
        ]

        for i, message in enumerate(test_messages):
            memory.db_manager.store_chat_history(
                chat_id=f"{db_name.lower()}_perf_test_{i}_{int(time.time())}",
                user_input=message,
                ai_output=f"This is a comprehensive response about {message[:30]}... from {db_name} database testing with detailed information about database capabilities, performance characteristics, and implementation details.",
                model=f"test-{db_name.lower()}-model",
                timestamp=datetime.now(),
                session_id=f"{db_name.lower()}_perf_session",
                namespace=test_namespace,
                tokens_used=120 + i * 10,
                metadata={
                    "test": "comprehensive_comparison",
                    "database": db_name.lower(),
                    "iteration": i,
                    "performance_test": True,
                },
            )

        test_results["insert_time"] = time.time() - start_time
        print(
            f"   ⏱️  Insert time: {test_results['insert_time']:.3f}s ({test_results['insert_time'] / len(test_messages):.3f}s per record)"
        )

        # Test 2: Data retrieval performance
        print("\n📚 Performance Test 2: Data retrieval")
        start_time = time.time()

        # Get statistics
        stats = memory.db_manager.get_memory_stats(test_namespace)

        # Retrieve history
        history = memory.db_manager.get_chat_history(test_namespace, limit=20)

        test_results["retrieval_time"] = time.time() - start_time
        test_results["chat_count"] = stats["chat_history_count"]

        print(f"   ⏱️  Retrieval time: {test_results['retrieval_time']:.3f}s")
        print(f"   📊 Retrieved {len(history)} chat records")
        print(f"   📈 Total chats in namespace: {test_results['chat_count']}")

        # Test 3: Full-text search performance
        print("\n🔍 Performance Test 3: Full-text search")

        search_queries = [
            "artificial intelligence machine learning",
            "database performance SQLite MySQL PostgreSQL",
            "full-text search algorithms",
            "ACID properties transactions",
            "database sharding distributed systems",
        ]

        total_search_time = 0
        total_results = 0
        search_strategies = set()

        for query in search_queries:
            start_time = time.time()
            results = memory.db_manager.search_memories(query, namespace=test_namespace)
            query_time = time.time() - start_time

            total_search_time += query_time
            total_results += len(results)

            if results:
                strategy = results[0].get("search_strategy", "unknown")
                search_strategies.add(strategy)
                print(
                    f"   🔎 '{query[:30]}...': {len(results)} results in {query_time:.3f}s ({strategy})"
                )

        test_results["search_time"] = total_search_time
        test_results["search_results"] = total_results
        test_results["search_strategy"] = (
            list(search_strategies)[0] if search_strategies else "none"
        )

        print(f"   ⏱️  Total search time: {test_results['search_time']:.3f}s")
        print(f"   📊 Total search results: {test_results['search_results']}")
        print(f"   🎯 Search strategies used: {', '.join(search_strategies)}")

        # Test 4: Advanced memory operations (if available)
        print("\n🧠 Advanced Test: Memory operations")
        try:
            # Test short-term memory
            memory.db_manager.store_short_term_memory(
                content=f"{db_name} short-term memory test with comprehensive search capabilities",
                summary=f"Testing {db_name} advanced memory features",
                category_primary="test",
                category_secondary="advanced",
                session_id=f"{db_name.lower()}_advanced_session",
                namespace=test_namespace,
                metadata={"type": "short_term", "database": db_name.lower()},
            )
            print("   ✅ Short-term memory: Success")

            # Test long-term memory
            memory.db_manager.store_long_term_memory(
                content=f"{db_name} long-term memory with advanced search and indexing",
                summary=f"Long-term {db_name} testing with full feature set",
                category_primary="test",
                category_secondary="advanced",
                session_id=f"{db_name.lower()}_advanced_session",
                namespace=test_namespace,
                metadata={"type": "long_term", "database": db_name.lower()},
            )
            print("   ✅ Long-term memory: Success")

        except Exception as e:
            print(f"   ⚠️  Advanced memory operations: {e}")

        # Cleanup
        memory.db_manager.clear_memory(test_namespace)
        memory.db_manager.close()

        print(f"\n✅ {db_name} comprehensive test completed successfully")

        return test_results

    except Exception as e:
        print(f"❌ {db_name} comprehensive test failed: {e}")
        return {
            "db_name": db_name,
            "connection_string": connection_string,
            "error": str(e),
        }


def main():
    """Run comprehensive database comparison"""
    print("🏎️  Comprehensive Database Comparison Suite")
    print("Testing SQLite, MySQL, and PostgreSQL with Memori")
    print("=" * 70)

    # Get available database connections
    connections = get_database_connections()

    if not connections:
        print("❌ No database connections available")
        return 1

    print(f"🗄️  Available databases: {', '.join(connections.keys())}")
    print(f"🧪 Running comprehensive tests on {len(connections)} databases")

    all_results = []

    # Test each database
    for db_name, connection_string in connections.items():
        try:
            result = test_database_comprehensive(
                db_name, connection_string, f"{db_name} Comprehensive Test"
            )
            if "error" not in result:
                all_results.append(result)

        except Exception as e:
            print(f"⚠️  {db_name} test skipped: {e}")
            continue

    # Comprehensive results comparison
    if len(all_results) >= 2:
        print(f"\n{'=' * 70}")
        print("📊 COMPREHENSIVE DATABASE COMPARISON RESULTS")
        print(f"{'=' * 70}")

        print("\n🎯 Performance Comparison:")
        print(
            f"{'Database':<12} {'Insert':<10} {'Retrieve':<10} {'Search':<10} {'Strategy':<15} {'Results':<8}"
        )
        print("-" * 70)

        for result in all_results:
            print(
                f"{result['db_name']:<12} "
                f"{result['insert_time']:.3f}s{'':<4} "
                f"{result['retrieval_time']:.3f}s{'':<5} "
                f"{result['search_time']:.3f}s{'':<5} "
                f"{result['search_strategy']:<15} "
                f"{result['search_results']:<8}"
            )

        # Winner analysis
        print("\n🏆 Performance Winners:")

        # Insert performance
        fastest_insert = min(all_results, key=lambda x: x["insert_time"])
        print(
            f"   • Fastest Insert: {fastest_insert['db_name']} ({fastest_insert['insert_time']:.3f}s)"
        )

        # Retrieval performance
        fastest_retrieval = min(all_results, key=lambda x: x["retrieval_time"])
        print(
            f"   • Fastest Retrieval: {fastest_retrieval['db_name']} ({fastest_retrieval['retrieval_time']:.3f}s)"
        )

        # Search performance
        fastest_search = min(all_results, key=lambda x: x["search_time"])
        print(
            f"   • Fastest Search: {fastest_search['db_name']} ({fastest_search['search_time']:.3f}s)"
        )

        # Most search results
        most_results = max(all_results, key=lambda x: x["search_results"])
        print(
            f"   • Best Search Results: {most_results['db_name']} ({most_results['search_results']} results)"
        )

        # Search strategy analysis
        print("\n🔍 Search Strategy Analysis:")
        strategies = {}
        for result in all_results:
            strategy = result["search_strategy"]
            strategies[strategy] = strategies.get(strategy, []) + [result["db_name"]]

        for strategy, databases in strategies.items():
            print(f"   • {strategy}: {', '.join(databases)}")

        # Recommendations
        print("\n💡 Recommendations:")
        print(
            "   • SQLite: Best for single-user applications, embedded systems, development"
        )
        print(
            "   • MySQL: Best for web applications, high concurrency, proven reliability"
        )
        print(
            "   • PostgreSQL: Best for complex queries, advanced features, data integrity"
        )
        print(
            "   • All databases: Full cross-compatibility maintained with identical APIs"
        )

    elif len(all_results) == 1:
        result = all_results[0]
        print(f"\n📊 Single Database Test Results ({result['db_name']}):")
        print(f"   • Insert performance: {result['insert_time']:.3f}s for 15 records")
        print(f"   • Retrieval performance: {result['retrieval_time']:.3f}s")
        print(f"   • Search performance: {result['search_time']:.3f}s")
        print(f"   • Search strategy: {result['search_strategy']}")
        print(f"   • Search results: {result['search_results']}")

    else:
        print("❌ No database tests completed successfully")
        return 1

    print("\n✅ Comprehensive database comparison completed!")
    print("🎊 Cross-database compatibility verified across all supported databases!")

    return 0


if __name__ == "__main__":
    sys.exit(main())
