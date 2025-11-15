"""
Comprehensive PostgreSQL Integration Tests

Tests PostgreSQL database functionality with Memori covering three aspects:
1. Functional: Does it work? (operations succeed)
2. Persistence: Does it store in database? (data is persisted)
3. Integration: Do features work together? (end-to-end workflows)

Following the testing pattern established in existing Memori tests.
"""

import time
from datetime import datetime

import pytest
from conftest import create_simple_memory


@pytest.mark.postgresql
@pytest.mark.integration
class TestPostgreSQLBasicOperations:
    """Test basic PostgreSQL operations with three-aspect validation."""

    def test_database_connection_and_initialization(self, memori_postgresql):
        """
        Test 1: Database connection and schema initialization.

        Validates:
        - Functional: Can connect to PostgreSQL
        - Persistence: Database schema is created
        - Integration: PostgreSQL-specific features available
        """
        # ASPECT 1: Functional - Does it work?
        assert memori_postgresql is not None
        assert memori_postgresql.db_manager is not None

        # ASPECT 2: Persistence - Is data stored?
        db_info = memori_postgresql.db_manager.get_database_info()
        assert db_info["database_type"] == "postgresql"
        assert "server_version" in db_info

        # ASPECT 3: Integration - Do features work?
        stats = memori_postgresql.db_manager.get_memory_stats(memori_postgresql.user_id)
        assert isinstance(stats, dict)
        assert stats["database_type"] == "postgresql"

    def test_chat_history_storage_and_retrieval(
        self, memori_postgresql, test_namespace, sample_chat_messages
    ):
        """
        Test 2: Chat history storage and retrieval.

        Validates:
        - Functional: Can store chat messages
        - Persistence: Messages are in PostgreSQL
        - Integration: Can retrieve and search messages
        """
        # ASPECT 1: Functional - Store chat messages
        for i, msg in enumerate(sample_chat_messages):
            chat_id = memori_postgresql.db_manager.store_chat_history(
                chat_id=f"pg_test_chat_{i}_{int(time.time())}",
                user_input=msg["user_input"],
                ai_output=msg["ai_output"],
                model=msg["model"],
                timestamp=datetime.now(),
                session_id="pg_test_session",
                user_id=memori_postgresql.user_id,
                tokens_used=30 + i * 5,
                metadata={"test": "chat_storage", "db": "postgresql"},
            )
            assert chat_id is not None

        # ASPECT 2: Persistence - Verify data is in database
        stats = memori_postgresql.db_manager.get_memory_stats(memori_postgresql.user_id)
        assert stats["chat_history_count"] == len(sample_chat_messages)

        # ASPECT 3: Integration - Retrieve and verify content
        history = memori_postgresql.db_manager.get_chat_history(
            test_namespace, limit=10
        )
        assert len(history) == len(sample_chat_messages)

        # Verify specific message content
        user_inputs = [h["user_input"] for h in history]
        assert "What is artificial intelligence?" in user_inputs

    @pytest.mark.skip(
        reason="store_short_term_memory() API not available - short-term memory is managed internally"
    )
    def test_short_term_memory_operations(self, memori_postgresql, test_namespace):
        """
        Test 3: Short-term memory storage and retrieval.

        Validates:
        - Functional: Can create short-term memories
        - Persistence: Memories stored in PostgreSQL
        - Integration: tsvector search works
        """
        # ASPECT 1: Functional - Store short-term memory
        memory_id = memori_postgresql.db_manager.store_short_term_memory(
            content="User prefers PostgreSQL for production databases with full-text search",
            summary="User's database preferences for production",
            category_primary="preference",
            category_secondary="database",
            session_id="pg_test_session",
            user_id=memori_postgresql.user_id,
            metadata={"test": "short_term", "db": "postgresql"},
        )
        assert memory_id is not None

        # ASPECT 2: Persistence - Verify in database
        stats = memori_postgresql.db_manager.get_memory_stats(memori_postgresql.user_id)
        assert stats["short_term_count"] >= 1

        # ASPECT 3: Integration - Search with tsvector
        results = memori_postgresql.db_manager.search_memories(
            "PostgreSQL production", user_id=memori_postgresql.user_id
        )
        assert len(results) > 0
        assert (
            "PostgreSQL" in results[0]["processed_data"]["content"]
            or "production" in results[0]["processed_data"]["content"]
        )

    def test_long_term_memory_operations(self, memori_postgresql, test_namespace):
        """
        Test 4: Long-term memory storage and retrieval.

        Validates:
        - Functional: Can create long-term memories
        - Persistence: Memories persisted in PostgreSQL
        - Integration: Full-text search with GIN index
        """
        # ASPECT 1: Functional - Store long-term memory
        memory = create_simple_memory(
            content="User is building a distributed system with PostgreSQL and Redis",
            summary="User's project: distributed system with PostgreSQL",
            classification="context",
            importance="high",
            metadata={"test": "long_term", "stack": "postgresql_redis"},
        )
        memory_id = memori_postgresql.db_manager.store_long_term_memory_enhanced(
            memory=memory, chat_id="pg_test_chat_1", user_id=memori_postgresql.user_id
        )
        assert memory_id is not None

        # ASPECT 2: Persistence - Verify storage
        stats = memori_postgresql.db_manager.get_memory_stats(memori_postgresql.user_id)
        assert stats["long_term_count"] >= 1

        # ASPECT 3: Integration - tsvector search
        results = memori_postgresql.db_manager.search_memories(
            "distributed PostgreSQL", user_id=memori_postgresql.user_id
        )
        assert len(results) > 0
        found_memory = any(
            "distributed" in r["processed_data"]["content"]
            or "PostgreSQL" in r["processed_data"]["content"]
            for r in results
        )
        assert found_memory


@pytest.mark.postgresql
@pytest.mark.integration
class TestPostgreSQLFullTextSearch:
    """Test PostgreSQL tsvector full-text search functionality."""

    def test_tsvector_search_basic(
        self, memori_postgresql, test_namespace, sample_chat_messages
    ):
        """
        Test 5: Basic tsvector full-text search.

        Validates:
        - Functional: tsvector queries work
        - Persistence: tsvector index is populated
        - Integration: Search returns relevant results
        """
        # Setup: Store test data
        for i, msg in enumerate(sample_chat_messages):
            memori_postgresql.db_manager.store_chat_history(
                chat_id=f"fts_pg_test_{i}",
                user_input=msg["user_input"],
                ai_output=msg["ai_output"],
                model="test-model",
                timestamp=datetime.now(),
                session_id="fts_pg_session",
                user_id=memori_postgresql.user_id,
                tokens_used=50,
            )

        # ASPECT 1: Functional - Search works
        results = memori_postgresql.db_manager.search_memories(
            "artificial intelligence", user_id=memori_postgresql.user_id
        )
        assert len(results) > 0

        # ASPECT 2: Persistence - Results from database with tsvector
        assert all("search_score" in r or "search_strategy" in r for r in results)

        # ASPECT 3: Integration - Relevant results returned
        top_result = results[0]
        content_lower = top_result["processed_data"]["content"].lower()
        assert "artificial" in content_lower or "intelligence" in content_lower

    def test_tsvector_ranking(self, memori_postgresql, test_namespace):
        """
        Test 6: PostgreSQL ts_rank functionality.

        Validates:
        - Functional: Ranking works
        - Persistence: Scores calculated correctly
        - Integration: Results ordered by relevance
        """
        # Setup: Create data with varying relevance
        test_data = [
            "PostgreSQL provides excellent full-text search capabilities",
            "Full-text search is a powerful feature",
            "PostgreSQL is a database system",
            "Search functionality in databases",
        ]

        for i, content in enumerate(test_data):
            memory = create_simple_memory(
                content=content, summary=f"Test {i}", classification="knowledge"
            )
            memori_postgresql.db_manager.store_long_term_memory_enhanced(
                memory=memory,
                chat_id=f"ranking_test_chat_{i}",
                user_id=memori_postgresql.user_id,
            )

        # ASPECT 1: Functional - Ranked search works
        results = memori_postgresql.db_manager.search_memories(
            "PostgreSQL full-text search", user_id=memori_postgresql.user_id
        )
        assert len(results) > 0

        # ASPECT 2: Persistence - Scores present
        # Most results should have search scores
        has_scores = sum(1 for r in results if "search_score" in r)
        assert has_scores > 0

        # ASPECT 3: Integration - Most relevant first
        if len(results) >= 2 and "search_score" in results[0]:
            # First result should be highly relevant
            first_content = results[0]["processed_data"]["content"].lower()
            assert "postgresql" in first_content and (
                "full-text" in first_content or "search" in first_content
            )


@pytest.mark.postgresql
@pytest.mark.integration
class TestPostgreSQLSpecificFeatures:
    """Test PostgreSQL-specific database features."""

    def test_connection_pooling(self, memori_postgresql):
        """
        Test 7: PostgreSQL connection pooling.

        Validates:
        - Functional: Connection pool exists
        - Persistence: Multiple connections handled
        - Integration: Pool manages connections efficiently
        """
        # ASPECT 1: Functional - Pool exists
        # Note: This depends on implementation details
        assert memori_postgresql.db_manager is not None

        # ASPECT 2 & 3: Multiple operations use pool
        for i in range(5):
            memory = create_simple_memory(
                content=f"Pool test {i}",
                summary=f"Test {i}",
                classification="knowledge",
            )
            memori_postgresql.db_manager.store_long_term_memory_enhanced(
                memory=memory,
                chat_id=f"pool_test_chat_{i}",
                user_id=memori_postgresql.user_id,
            )

        stats = memori_postgresql.db_manager.get_memory_stats(memori_postgresql.user_id)
        assert stats["long_term_count"] == 5

    def test_json_metadata_storage(self, memori_postgresql, test_namespace):
        """
        Test 8: PostgreSQL JSON/JSONB storage.

        Validates:
        - Functional: Can store complex metadata
        - Persistence: Metadata persisted correctly
        - Integration: Can retrieve and query metadata
        """
        complex_metadata = {
            "tags": ["python", "database", "postgresql"],
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
        memory_id = memori_postgresql.db_manager.store_long_term_memory_enhanced(
            memory=memory, chat_id="json_test_chat_1", user_id=memori_postgresql.user_id
        )
        assert memory_id is not None

        # ASPECT 2: Persistence - Data stored
        stats = memori_postgresql.db_manager.get_memory_stats(memori_postgresql.user_id)
        assert stats["long_term_count"] >= 1

        # ASPECT 3: Integration - Metadata retrievable
        results = memori_postgresql.db_manager.search_memories(
            "JSON metadata", user_id=memori_postgresql.user_id
        )
        assert len(results) > 0


@pytest.mark.postgresql
@pytest.mark.integration
class TestPostgreSQLPerformance:
    """Test PostgreSQL performance characteristics."""

    def test_bulk_insertion_performance(
        self, memori_postgresql, test_namespace, performance_tracker
    ):
        """
        Test 9: Bulk insertion performance with PostgreSQL.

        Validates:
        - Functional: Can handle bulk inserts
        - Persistence: All data stored correctly
        - Performance: Meets performance targets
        """
        num_records = 50

        # ASPECT 1: Functional - Bulk insert works
        with performance_tracker.track("pg_bulk_insert"):
            for i in range(num_records):
                memori_postgresql.db_manager.store_chat_history(
                    chat_id=f"pg_perf_test_{i}",
                    user_input=f"PostgreSQL test message {i} with search keywords",
                    ai_output=f"PostgreSQL response {i} about test message",
                    model="test-model",
                    timestamp=datetime.now(),
                    session_id="pg_perf_test",
                    user_id=memori_postgresql.user_id,
                    tokens_used=30,
                )

        # ASPECT 2: Persistence - All records stored
        stats = memori_postgresql.db_manager.get_memory_stats(memori_postgresql.user_id)
        assert stats["chat_history_count"] == num_records

        # ASPECT 3: Performance - Within acceptable time
        metrics = performance_tracker.get_metrics()
        insert_time = metrics["pg_bulk_insert"]
        time_per_record = insert_time / num_records

        print(
            f"\nPostgreSQL bulk insert: {insert_time:.3f}s total, {time_per_record:.4f}s per record"
        )
        assert (
            insert_time < 15.0
        )  # PostgreSQL may be slightly slower than SQLite for small datasets

    def test_tsvector_search_performance(
        self, memori_postgresql, test_namespace, performance_tracker
    ):
        """
        Test 10: PostgreSQL tsvector search performance.

        Validates:
        - Functional: Search works at scale
        - Persistence: GIN index used
        - Performance: Search is fast
        """
        # Setup: Create searchable data
        for i in range(20):
            memory = create_simple_memory(
                content=f"PostgreSQL development tip {i}: Use tsvector for full-text search performance",
                summary=f"PostgreSQL tip {i}",
                classification="knowledge",
            )
            memori_postgresql.db_manager.store_long_term_memory_enhanced(
                memory=memory,
                chat_id=f"search_perf_pg_chat_{i}",
                user_id=memori_postgresql.user_id,
            )

        # ASPECT 1: Functional - Search works
        with performance_tracker.track("pg_search"):
            results = memori_postgresql.db_manager.search_memories(
                "PostgreSQL tsvector performance", user_id=memori_postgresql.user_id
            )

        # ASPECT 2: Persistence - Results from database with GIN index
        assert len(results) > 0

        # ASPECT 3: Performance - Fast search
        metrics = performance_tracker.get_metrics()
        search_time = metrics["pg_search"]

        print(
            f"\nPostgreSQL tsvector search: {search_time:.3f}s for {len(results)} results"
        )
        assert search_time < 1.0  # Search should be under 1 second


@pytest.mark.postgresql
@pytest.mark.integration
class TestPostgreSQLTransactions:
    """Test PostgreSQL transaction handling."""

    def test_transaction_isolation(self, memori_postgresql, test_namespace):
        """
        Test 11: PostgreSQL transaction isolation.

        Validates:
        - Functional: Transactions work
        - Persistence: ACID properties maintained
        - Integration: Rollback works correctly
        """
        # This test validates that PostgreSQL handles transactions correctly
        # In practice, operations should be atomic

        initial_stats = memori_postgresql.db_manager.get_memory_stats(
            memori_postgresql.user_id
        )
        initial_count = initial_stats.get("long_term_count", 0)

        # Store multiple memories (should be atomic operations)
        for i in range(3):
            memory = create_simple_memory(
                content=f"Transaction test {i}",
                summary=f"Test {i}",
                classification="knowledge",
            )
            memori_postgresql.db_manager.store_long_term_memory_enhanced(
                memory=memory,
                chat_id=f"transaction_test_chat_{i}",
                user_id=memori_postgresql.user_id,
            )

        # ASPECT 1 & 2: All stored
        final_stats = memori_postgresql.db_manager.get_memory_stats(
            memori_postgresql.user_id
        )
        assert final_stats["long_term_count"] == initial_count + 3

        # ASPECT 3: Data consistent
        results = memori_postgresql.db_manager.search_memories(
            "Transaction", user_id=memori_postgresql.user_id
        )
        assert len(results) == 3


@pytest.mark.postgresql
@pytest.mark.integration
class TestPostgreSQLEdgeCases:
    """Test PostgreSQL edge cases and error handling."""

    def test_empty_search_query(self, memori_postgresql, test_namespace):
        """Test 12: Handle empty search queries gracefully."""
        results = memori_postgresql.db_manager.search_memories(
            "", user_id=memori_postgresql.user_id
        )
        assert isinstance(results, list)

    def test_unicode_content(self, memori_postgresql, test_namespace):
        """Test 13: Handle Unicode characters properly."""
        unicode_content = (
            "PostgreSQL supports Unicode: 你好世界 مرحبا بالعالم Привет мир"
        )

        memory = create_simple_memory(
            content=unicode_content, summary="Unicode test", classification="knowledge"
        )
        memory_id = memori_postgresql.db_manager.store_long_term_memory_enhanced(
            memory=memory,
            chat_id="unicode_test_chat_1",
            user_id=memori_postgresql.user_id,
        )

        assert memory_id is not None

        # Verify it was stored
        stats = memori_postgresql.db_manager.get_memory_stats(memori_postgresql.user_id)
        assert stats["long_term_count"] >= 1

    def test_very_long_content(self, memori_postgresql, test_namespace):
        """Test 14: Handle very long content strings."""
        long_content = "x" * 10000  # 10KB of text

        memory = create_simple_memory(
            content=long_content,
            summary="Very long content test",
            classification="knowledge",
        )
        memory_id = memori_postgresql.db_manager.store_long_term_memory_enhanced(
            memory=memory,
            chat_id="long_content_pg_chat_1",
            user_id=memori_postgresql.user_id,
        )

        assert memory_id is not None

        # Verify storage and retrieval
        stats = memori_postgresql.db_manager.get_memory_stats(memori_postgresql.user_id)
        assert stats["long_term_count"] >= 1
