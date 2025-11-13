#!/usr/bin/env python3
"""
Database Comparison Script
Compare SQLite vs MySQL performance and features with Memori
"""

import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path

# Add the memori package to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def test_database_performance(db_type, connection_string, test_name):
    """Test database performance with various operations"""
    print(f"\n{'=' * 50}")
    print(f"🧪 Testing {test_name}")
    print(f"Connection: {connection_string}")
    print(f"{'=' * 50}")

    try:
        from memori import Memori

        # Initialize with database
        memory = Memori(
            database_connect=connection_string,
            conscious_ingest=False,
            auto_ingest=False,
            verbose=False,  # Reduce log noise for performance testing
        )

        print(f"✅ Connected to {db_type}")

        # Get database info
        db_info = memory.db_manager.get_database_info()
        print(
            f"📊 Database info: {db_info['database_type']} v{db_info.get('server_version', 'N/A')}"
        )
        print(f"🔍 FULLTEXT support: {db_info.get('supports_fulltext', 'Unknown')}")

        # Test 1: Bulk chat history insertion
        print("\n⚡ Test 1: Bulk chat insertion (10 records)")
        start_time = time.time()

        for i in range(10):
            memory.db_manager.store_chat_history(
                chat_id=f"perf_test_{db_type}_{i}",
                user_input=f"Performance test message {i} for {db_type} database testing with longer content to test text handling",
                ai_output=f"This is response {i} from the {db_type} database performance test with detailed information about database capabilities",
                model="test-gpt-3.5-turbo",
                timestamp=datetime.now(),
                session_id=f"perf_session_{db_type}",
                namespace="performance_test",
                tokens_used=50 + i,
                metadata={"test": "performance", "db_type": db_type, "iteration": i},
            )

        insert_time = time.time() - start_time
        print(
            f"   ⏱️  Insert time: {insert_time:.3f}s ({insert_time / 10:.3f}s per record)"
        )

        # Test 2: Data retrieval
        print("\n📚 Test 2: Data retrieval")
        start_time = time.time()

        history = memory.db_manager.get_chat_history("performance_test", limit=20)
        stats = memory.db_manager.get_memory_stats("performance_test")

        retrieval_time = time.time() - start_time
        print(f"   ⏱️  Retrieval time: {retrieval_time:.3f}s")
        print(f"   📊 Retrieved {len(history)} chat records")
        print(
            f"   📈 Stats: {stats['chat_history_count']} chats, {stats['database_type']} backend"
        )

        # Test 3: Search functionality
        print("\n🔍 Test 3: Search functionality")
        start_time = time.time()

        search_results = memory.db_manager.search_memories(
            "performance test database", namespace="performance_test"
        )
        search_time = time.time() - start_time

        print(f"   ⏱️  Search time: {search_time:.3f}s")
        print(f"   📊 Search results: {len(search_results)} matches")

        if search_results:
            result = search_results[0]
            print(f"   🎯 Search strategy: {result.get('search_strategy', 'unknown')}")
            print(f"   📊 Search score: {result.get('search_score', 0):.2f}")

        # Test 4: Connection handling
        print("\n🔌 Test 4: Connection handling")
        start_time = time.time()

        # Test multiple quick operations
        for _ in range(5):
            _ = memory.db_manager.get_memory_stats("performance_test")

        connection_time = time.time() - start_time
        print(f"   ⏱️  5 quick operations: {connection_time:.3f}s")

        # Cleanup and close
        memory.db_manager.clear_memory("performance_test")
        memory.db_manager.close()

        # Return performance metrics
        return {
            "db_type": db_type,
            "insert_time": insert_time,
            "retrieval_time": retrieval_time,
            "search_time": search_time,
            "connection_time": connection_time,
            "search_results": len(search_results),
            "search_strategy": (
                search_results[0].get("search_strategy", "none")
                if search_results
                else "none"
            ),
        }

    except Exception as e:
        print(f"❌ {test_name} test failed: {e}")
        import traceback

        traceback.print_exc()
        return None


def main():
    """Run database comparison tests"""
    print("🏎️  Database Performance Comparison")
    print("Comparing SQLite vs MySQL with Memori")
    print("=" * 60)

    results = []

    # Test 1: SQLite (existing behavior)
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_db:
        sqlite_connection = f"sqlite:///{tmp_db.name}"
        sqlite_result = test_database_performance(
            "SQLite", sqlite_connection, "SQLite Database"
        )
        if sqlite_result:
            results.append(sqlite_result)

    # Test 2: MySQL (new capability)
    try:
        mysql_connection = "mysql+mysqlconnector://root:@127.0.0.1:3306/memori_test"
        mysql_result = test_database_performance(
            "MySQL", mysql_connection, "MySQL Database"
        )
        if mysql_result:
            results.append(mysql_result)
    except Exception as e:
        print(f"⚠️  MySQL test skipped: {e}")
        print("💡 Ensure MySQL is running and setup_mysql.py has been executed")

    # Results comparison
    if len(results) >= 2:
        print(f"\n{'=' * 60}")
        print("📊 PERFORMANCE COMPARISON RESULTS")
        print(f"{'=' * 60}")

        sqlite_result = next((r for r in results if r["db_type"] == "SQLite"), None)
        mysql_result = next((r for r in results if r["db_type"] == "MySQL"), None)

        if sqlite_result and mysql_result:
            print(f"{'Metric':<20} {'SQLite':<15} {'MySQL':<15} {'Winner':<10}")
            print(f"{'-' * 60}")

            # Insert performance
            sqlite_insert = sqlite_result["insert_time"]
            mysql_insert = mysql_result["insert_time"]
            insert_winner = "SQLite" if sqlite_insert < mysql_insert else "MySQL"
            print(
                f"{'Insert (10 records)':<20} {sqlite_insert:.3f}s{'':<8} {mysql_insert:.3f}s{'':<8} {insert_winner:<10}"
            )

            # Retrieval performance
            sqlite_retrieval = sqlite_result["retrieval_time"]
            mysql_retrieval = mysql_result["retrieval_time"]
            retrieval_winner = (
                "SQLite" if sqlite_retrieval < mysql_retrieval else "MySQL"
            )
            print(
                f"{'Retrieval':<20} {sqlite_retrieval:.3f}s{'':<8} {mysql_retrieval:.3f}s{'':<8} {retrieval_winner:<10}"
            )

            # Search performance
            sqlite_search = sqlite_result["search_time"]
            mysql_search = mysql_result["search_time"]
            search_winner = "SQLite" if sqlite_search < mysql_search else "MySQL"
            print(
                f"{'Search':<20} {sqlite_search:.3f}s{'':<8} {mysql_search:.3f}s{'':<8} {search_winner:<10}"
            )

            # Connection handling
            sqlite_conn = sqlite_result["connection_time"]
            mysql_conn = mysql_result["connection_time"]
            conn_winner = "SQLite" if sqlite_conn < mysql_conn else "MySQL"
            print(
                f"{'Connections (5x)':<20} {sqlite_conn:.3f}s{'':<8} {mysql_conn:.3f}s{'':<8} {conn_winner:<10}"
            )

            print("\n🔍 Search Strategy Comparison:")
            print(
                f"   SQLite: {sqlite_result['search_strategy']} ({sqlite_result['search_results']} results)"
            )
            print(
                f"   MySQL:  {mysql_result['search_strategy']} ({mysql_result['search_results']} results)"
            )

            print("\n🎯 Key Insights:")
            print(
                "   • SQLite is typically faster for single-user, file-based operations"
            )
            print("   • MySQL provides better concurrency and enterprise features")
            print("   • Both support full-text search with different implementations")
            print("   • Cross-database compatibility maintained with identical APIs")

    elif len(results) == 1:
        result = results[0]
        print(f"\n📊 Single Database Test Results ({result['db_type']}):")
        print(f"   • Insert performance: {result['insert_time']:.3f}s for 10 records")
        print(f"   • Retrieval performance: {result['retrieval_time']:.3f}s")
        print(f"   • Search performance: {result['search_time']:.3f}s")
        print(f"   • Search strategy: {result['search_strategy']}")

    else:
        print("❌ No database tests completed successfully")
        return 1

    print("\n✅ Database comparison completed!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
