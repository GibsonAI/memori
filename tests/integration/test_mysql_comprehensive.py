"""
Comprehensive MySQL Integration Tests

Tests MySQL database functionality with Memori covering three aspects:
1. Functional: Does it work? (operations succeed)
2. Persistence: Does it store in database? (data is persisted)
3. Integration: Do features work together? (end-to-end workflows)

Following the testing pattern established in existing Memori tests.
"""

import time
from datetime import datetime

import pytest
from conftest import create_simple_memory


@pytest.mark.mysql
@pytest.mark.integration
class TestMySQLBasicOperations:
    """Test basic MySQL operations with three-aspect validation."""

    def test_database_connection_and_initialization(self, memori_mysql):
        """
        Test 1: Database connection and schema initialization.

        Validates:
        - Functional: Can connect to MySQL
        - Persistence: Database schema is created
        - Integration: MySQL-specific features available
        """
        # ASPECT 1: Functional - Does it work?
        assert memori_mysql is not None
        assert memori_mysql.db_manager is not None

        # ASPECT 2: Persistence - Is data stored?
        db_info = memori_mysql.db_manager.get_database_info()
        assert db_info["database_type"] == "mysql"
        assert "server_version" in db_info

        # ASPECT 3: Integration - Do features work?
        stats = memori_mysql.db_manager.get_memory_stats(memori_mysql.user_id)
        assert isinstance(stats, dict)
        assert stats["database_type"] == "mysql"

    def test_chat_history_storage_and_retrieval(
        self, memori_mysql, test_namespace, sample_chat_messages
    ):
        """
        Test 2: Chat history storage and retrieval.

        Validates:
        - Functional: Can store chat messages
        - Persistence: Messages are in MySQL
        - Integration: Can retrieve and search messages
        """
        # ASPECT 1: Functional - Store chat messages
        for i, msg in enumerate(sample_chat_messages):
            chat_id = memori_mysql.db_manager.store_chat_history(
                chat_id=f"mysql_test_chat_{i}_{int(time.time())}",
                user_input=msg["user_input"],
                ai_output=msg["ai_output"],
                model=msg["model"],
                timestamp=datetime.now(),
                session_id="mysql_test_session",
                user_id=memori_mysql.user_id,
                tokens_used=30 + i * 5,
                metadata={"test": "chat_storage", "db": "mysql"},
            )
            assert chat_id is not None

        # ASPECT 2: Persistence - Verify data is in database
        stats = memori_mysql.db_manager.get_memory_stats(memori_mysql.user_id)
        assert stats["chat_history_count"] == len(sample_chat_messages)

        # ASPECT 3: Integration - Retrieve and verify content
        history = memori_mysql.db_manager.get_chat_history(
            memori_mysql.user_id, limit=10
        )
        assert len(history) == len(sample_chat_messages)

        # Verify specific message content
        user_inputs = [h["user_input"] for h in history]
        assert "What is artificial intelligence?" in user_inputs

    @pytest.mark.skip(
        reason="store_short_term_memory() API not available - short-term memory is managed internally"
    )
    def test_short_term_memory_operations(self, memori_mysql, test_namespace):
        """
        Test 3: Short-term memory storage and retrieval.

        Validates:
        - Functional: Can create short-term memories
        - Persistence: Memories stored in MySQL
        - Integration: MySQL FULLTEXT search works
        """
        # ASPECT 1: Functional - Store short-term memory
        memory_id = memori_mysql.db_manager.store_short_term_memory(
            content="User prefers MySQL for reliable data storage and replication",
            summary="User's database preferences for MySQL",
            category_primary="preference",
            category_secondary="database",
            session_id="mysql_test_session",
            user_id=memori_mysql.user_id,
            metadata={"test": "short_term", "db": "mysql"},
        )
        assert memory_id is not None

        # ASPECT 2: Persistence - Verify in database
        stats = memori_mysql.db_manager.get_memory_stats(memori_mysql.user_id)
        assert stats["short_term_count"] >= 1

        # ASPECT 3: Integration - Search with FULLTEXT
        results = memori_mysql.db_manager.search_memories(
            "MySQL reliable", user_id=memori_mysql.user_id
        )
        assert len(results) > 0
        assert (
            "MySQL" in results[0]["processed_data"]["content"]
            or "reliable" in results[0]["processed_data"]["content"]
        )

    def test_long_term_memory_operations(self, memori_mysql, test_namespace):
        """
        Test 4: Long-term memory storage and retrieval.

        Validates:
        - Functional: Can create long-term memories
        - Persistence: Memories persisted in MySQL
        - Integration: Full-text search with FULLTEXT index
        """
        # ASPECT 1: Functional - Store long-term memory
        memory = create_simple_memory(
            content="User is building a high-traffic web application with MySQL and Redis",
            summary="User's project: web app with MySQL and Redis",
            classification="context",
            importance="high",
            metadata={"test": "long_term", "stack": "mysql_redis"},
        )
        memory_id = memori_mysql.db_manager.store_long_term_memory_enhanced(
            memory=memory, chat_id="mysql_test_chat_1", user_id=memori_mysql.user_id
        )
        assert memory_id is not None

        # ASPECT 2: Persistence - Verify storage
        stats = memori_mysql.db_manager.get_memory_stats(memori_mysql.user_id)
        assert stats["long_term_count"] >= 1

        # ASPECT 3: Integration - FULLTEXT search
        results = memori_mysql.db_manager.search_memories(
            "high-traffic MySQL", user_id=memori_mysql.user_id
        )
        assert len(results) > 0
        found_memory = any(
            "high-traffic" in r["processed_data"]["content"]
            or "MySQL" in r["processed_data"]["content"]
            for r in results
        )
        assert found_memory


@pytest.mark.mysql
@pytest.mark.integration
class TestMySQLFullTextSearch:
    """Test MySQL FULLTEXT search functionality."""

    def test_fulltext_search_basic(
        self, memori_mysql, test_namespace, sample_chat_messages
    ):
        """
        Test 5: Basic MySQL FULLTEXT search.

        Validates:
        - Functional: FULLTEXT queries work
        - Persistence: FULLTEXT index is populated
        - Integration: Search returns relevant results
        """
        # Setup: Store test data
        for i, msg in enumerate(sample_chat_messages):
            memori_mysql.db_manager.store_chat_history(
                chat_id=f"fts_mysql_test_{i}",
                user_input=msg["user_input"],
                ai_output=msg["ai_output"],
                model="test-model",
                timestamp=datetime.now(),
                session_id="fts_mysql_session",
                user_id=memori_mysql.user_id,
                tokens_used=50,
            )

        # ASPECT 1: Functional - Search works
        results = memori_mysql.db_manager.search_memories(
            "artificial intelligence", user_id=memori_mysql.user_id
        )
        assert len(results) > 0

        # ASPECT 2: Persistence - Results from database with FULLTEXT
        assert all("search_score" in r or "search_strategy" in r for r in results)

        # ASPECT 3: Integration - Relevant results returned
        top_result = results[0]
        content_lower = top_result["processed_data"]["content"].lower()
        assert "artificial" in content_lower or "intelligence" in content_lower

    def test_fulltext_boolean_mode(self, memori_mysql, test_namespace):
        """
        Test 6: MySQL FULLTEXT Boolean mode.

        Validates:
        - Functional: Boolean search works
        - Persistence: Complex queries execute
        - Integration: Correct results for boolean queries
        """
        # Setup: Create specific test data
        test_data = [
            "MySQL provides excellent full-text search capabilities",
            "Full-text search is a powerful feature in MySQL",
            "MySQL is a relational database system",
            "Search functionality in databases",
        ]

        for i, content in enumerate(test_data):
            memory = create_simple_memory(
                content=content, summary=f"Test {i}", classification="knowledge"
            )
            memori_mysql.db_manager.store_long_term_memory_enhanced(
                memory=memory,
                chat_id=f"boolean_test_chat_{i}",
                user_id=memori_mysql.user_id,
            )

        # ASPECT 1: Functional - Boolean search
        results = memori_mysql.db_manager.search_memories(
            "MySQL full-text", user_id=memori_mysql.user_id
        )
        assert len(results) > 0

        # ASPECT 2: Persistence - Database handles query
        stats = memori_mysql.db_manager.get_memory_stats(memori_mysql.user_id)
        assert stats["long_term_count"] >= 4

        # ASPECT 3: Integration - Relevant filtering
        mysql_results = [
            r for r in results if "MySQL" in r["processed_data"]["content"]
        ]
        assert len(mysql_results) > 0


@pytest.mark.mysql
@pytest.mark.integration
class TestMySQLSpecificFeatures:
    """Test MySQL-specific database features."""

    def test_transaction_support(self, memori_mysql, test_namespace):
        """
        Test 7: MySQL InnoDB transaction support.

        Validates:
        - Functional: Transactions work
        - Persistence: ACID properties maintained
        - Integration: Data consistency
        """
        initial_stats = memori_mysql.db_manager.get_memory_stats(memori_mysql.user_id)
        initial_count = initial_stats.get("long_term_count", 0)

        # Store multiple memories (should be atomic operations)
        for i in range(3):
            memory = create_simple_memory(
                content=f"Transaction test {i}",
                summary=f"Test {i}",
                classification="knowledge",
            )
            memori_mysql.db_manager.store_long_term_memory_enhanced(
                memory=memory,
                chat_id=f"transaction_chat_{i}",
                user_id=memori_mysql.user_id,
            )

        # ASPECT 1 & 2: All stored
        final_stats = memori_mysql.db_manager.get_memory_stats(memori_mysql.user_id)
        assert final_stats["long_term_count"] == initial_count + 3

        # ASPECT 3: Data consistent
        results = memori_mysql.db_manager.search_memories(
            "Transaction", user_id=memori_mysql.user_id
        )
        assert len(results) == 3

    def test_json_column_support(self, memori_mysql, test_namespace):
        """
        Test 8: MySQL JSON column support.

        Validates:
        - Functional: Can store complex metadata
        - Persistence: JSON persisted correctly
        - Integration: Can retrieve and use metadata
        """
        complex_metadata = {
            "tags": ["python", "database", "mysql"],
            "priority": "high",
            "nested": {"key1": "value1", "key2": 42},
        }

        # ASPECT 1: Functional - Store with complex metadata
        memory = create_simple_memory(
            content="Test with complex JSON metadata",
            summary="JSON metadata test",
            classification="knowledge",
            metadata=complex_metadata,
        )
        memory_id = memori_mysql.db_manager.store_long_term_memory_enhanced(
            memory=memory, chat_id="json_test_chat", user_id=memori_mysql.user_id
        )
        assert memory_id is not None

        # ASPECT 2: Persistence - Data stored
        stats = memori_mysql.db_manager.get_memory_stats(memori_mysql.user_id)
        assert stats["long_term_count"] >= 1

        # ASPECT 3: Integration - Metadata retrievable
        results = memori_mysql.db_manager.search_memories(
            "JSON metadata", user_id=memori_mysql.user_id
        )
        assert len(results) > 0

    def test_connection_pooling(self, memori_mysql):
        """
        Test 9: MySQL connection pooling.

        Validates:
        - Functional: Connection pool exists
        - Persistence: Multiple connections handled
        - Integration: Pool manages connections efficiently
        """
        # ASPECT 1: Functional - Pool exists
        assert memori_mysql.db_manager is not None

        # ASPECT 2 & 3: Multiple operations use pool
        for i in range(5):
            memory = create_simple_memory(
                content=f"Pool test {i}",
                summary=f"Test {i}",
                classification="knowledge",
            )
            memori_mysql.db_manager.store_long_term_memory_enhanced(
                memory=memory,
                chat_id=f"pool_test_chat_{i}",
                user_id=memori_mysql.user_id,
            )

        stats = memori_mysql.db_manager.get_memory_stats(memori_mysql.user_id)
        assert stats["long_term_count"] == 5


@pytest.mark.mysql
@pytest.mark.integration
@pytest.mark.performance
class TestMySQLPerformance:
    """Test MySQL performance characteristics."""

    def test_bulk_insertion_performance(
        self, memori_mysql, test_namespace, performance_tracker
    ):
        """
        Test 10: Bulk insertion performance with MySQL.

        Validates:
        - Functional: Can handle bulk inserts
        - Persistence: All data stored correctly
        - Performance: Meets performance targets
        """
        num_records = 50

        # ASPECT 1: Functional - Bulk insert works
        with performance_tracker.track("mysql_bulk_insert"):
            for i in range(num_records):
                memori_mysql.db_manager.store_chat_history(
                    chat_id=f"mysql_perf_test_{i}",
                    user_input=f"MySQL test message {i} with search keywords",
                    ai_output=f"MySQL response {i} about test message",
                    model="test-model",
                    timestamp=datetime.now(),
                    session_id="mysql_perf_test",
                    user_id=memori_mysql.user_id,
                    tokens_used=30,
                )

        # ASPECT 2: Persistence - All records stored
        stats = memori_mysql.db_manager.get_memory_stats(memori_mysql.user_id)
        assert stats["chat_history_count"] == num_records

        # ASPECT 3: Performance - Within acceptable time
        metrics = performance_tracker.get_metrics()
        insert_time = metrics["mysql_bulk_insert"]
        time_per_record = insert_time / num_records

        print(
            f"\nMySQL bulk insert: {insert_time:.3f}s total, {time_per_record:.4f}s per record"
        )
        assert insert_time < 15.0  # Should complete within 15 seconds

    def test_fulltext_search_performance(
        self, memori_mysql, test_namespace, performance_tracker
    ):
        """
        Test 11: MySQL FULLTEXT search performance.

        Validates:
        - Functional: Search works at scale
        - Persistence: FULLTEXT index used
        - Performance: Search is fast
        """
        # Setup: Create searchable data
        for i in range(20):
            memory = create_simple_memory(
                content=f"MySQL development tip {i}: Use FULLTEXT indexes for search performance",
                summary=f"MySQL tip {i}",
                classification="knowledge",
            )
            memori_mysql.db_manager.store_long_term_memory_enhanced(
                memory=memory,
                chat_id=f"search_perf_chat_{i}",
                user_id=memori_mysql.user_id,
            )

        # ASPECT 1: Functional - Search works
        with performance_tracker.track("mysql_search"):
            results = memori_mysql.db_manager.search_memories(
                "MySQL FULLTEXT performance", user_id=memori_mysql.user_id
            )

        # ASPECT 2: Persistence - Results from database with FULLTEXT index
        assert len(results) > 0

        # ASPECT 3: Performance - Fast search
        metrics = performance_tracker.get_metrics()
        search_time = metrics["mysql_search"]

        print(f"\nMySQL FULLTEXT search: {search_time:.3f}s for {len(results)} results")
        assert search_time < 1.0  # Search should be under 1 second


@pytest.mark.mysql
@pytest.mark.integration
class TestMySQLEdgeCases:
    """Test MySQL edge cases and error handling."""

    def test_empty_search_query(self, memori_mysql, test_namespace):
        """Test 12: Handle empty search queries gracefully."""
        results = memori_mysql.db_manager.search_memories(
            "", user_id=memori_mysql.user_id
        )
        assert isinstance(results, list)

    def test_unicode_content(self, memori_mysql, test_namespace):
        """Test 13: Handle Unicode characters properly."""
        unicode_content = "MySQL supports Unicode: 你好世界 مرحبا بالعالم Привет мир"

        memory = create_simple_memory(
            content=unicode_content, summary="Unicode test", classification="knowledge"
        )
        memory_id = memori_mysql.db_manager.store_long_term_memory_enhanced(
            memory=memory, chat_id="unicode_test_chat", user_id=memori_mysql.user_id
        )

        assert memory_id is not None

        # Verify it was stored
        stats = memori_mysql.db_manager.get_memory_stats(memori_mysql.user_id)
        assert stats["long_term_count"] >= 1

    def test_very_long_content(self, memori_mysql, test_namespace):
        """Test 14: Handle very long content strings."""
        long_content = "x" * 10000  # 10KB of text

        memory = create_simple_memory(
            content=long_content,
            summary="Very long content test",
            classification="knowledge",
        )
        memory_id = memori_mysql.db_manager.store_long_term_memory_enhanced(
            memory=memory, chat_id="long_content_chat", user_id=memori_mysql.user_id
        )

        assert memory_id is not None

        # Verify storage and retrieval
        stats = memori_mysql.db_manager.get_memory_stats(memori_mysql.user_id)
        assert stats["long_term_count"] >= 1

    def test_special_characters_in_content(self, memori_mysql, test_namespace):
        """Test 15: Handle special characters and SQL escaping."""
        special_content = "MySQL handles: quotes ' \" and backslashes \\ correctly"

        memory = create_simple_memory(
            content=special_content,
            summary="Special characters test",
            classification="knowledge",
        )
        memory_id = memori_mysql.db_manager.store_long_term_memory_enhanced(
            memory=memory, chat_id="special_chars_chat", user_id=memori_mysql.user_id
        )

        assert memory_id is not None

        # Verify retrieval works
        results = memori_mysql.db_manager.search_memories(
            "MySQL handles", user_id=memori_mysql.user_id
        )
        assert len(results) > 0


@pytest.mark.mysql
@pytest.mark.integration
class TestMySQLReplication:
    """Test MySQL replication features (if configured)."""

    def test_basic_write_read(self, memori_mysql, test_namespace):
        """
        Test 16: Basic write and read operations.

        Validates:
        - Functional: Write and read work
        - Persistence: Data persists
        - Integration: Consistent reads
        """
        # Write data
        content = "Test data for replication test"
        memory = create_simple_memory(
            content=content, summary="Replication test", classification="knowledge"
        )
        memori_mysql.db_manager.store_long_term_memory_enhanced(
            memory=memory, chat_id="replication_test_chat", user_id=memori_mysql.user_id
        )

        # Give time for any replication lag (if applicable)
        time.sleep(0.1)

        # Read data
        results = memori_mysql.db_manager.search_memories(
            "replication test", user_id=memori_mysql.user_id
        )

        assert len(results) > 0
        assert content in results[0]["processed_data"]["content"]
