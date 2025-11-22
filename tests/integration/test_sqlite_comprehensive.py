"""
Comprehensive SQLite Integration Tests

Tests SQLite database functionality with Memori covering three aspects:
1. Functional: Does it work? (operations succeed)
2. Persistence: Does it store in database? (data is persisted)
3. Integration: Do features work together? (end-to-end workflows)

Following the testing pattern established in existing Memori tests.
"""

import time
from datetime import datetime

import pytest
from conftest import create_simple_memory


@pytest.mark.sqlite
@pytest.mark.integration
class TestSQLiteBasicOperations:
    """Test basic SQLite operations with three-aspect validation."""

    def test_database_connection_and_initialization(self, memori_sqlite):
        """
        Test 1: Database connection and schema initialization.

        Validates:
        - Functional: Can connect to SQLite
        - Persistence: Database schema is created
        - Integration: Database info is accessible
        """
        # ASPECT 1: Functional - Does it work?
        assert memori_sqlite is not None
        assert memori_sqlite.db_manager is not None

        # ASPECT 2: Persistence - Is data stored?
        db_info = memori_sqlite.db_manager.get_database_info()
        assert db_info["database_type"] == "sqlite"

        # ASPECT 3: Integration - Do features work?
        stats = memori_sqlite.db_manager.get_memory_stats(memori_sqlite.user_id)
        assert isinstance(stats, dict)
        assert "database_type" in stats

    def test_chat_history_storage_and_retrieval(
        self, memori_sqlite, test_namespace, sample_chat_messages
    ):
        """
        Test 2: Chat history storage and retrieval.

        Validates:
        - Functional: Can store chat messages
        - Persistence: Messages are in database
        - Integration: Can retrieve and search messages
        """
        # ASPECT 1: Functional - Store chat messages
        for i, msg in enumerate(sample_chat_messages):
            chat_id = memori_sqlite.db_manager.store_chat_history(
                chat_id=f"test_chat_{i}_{int(time.time())}",
                user_input=msg["user_input"],
                ai_output=msg["ai_output"],
                model=msg["model"],
                timestamp=datetime.now(),
                session_id="test_session",
                user_id=memori_sqlite.user_id,
                tokens_used=30 + i * 5,
                metadata={"test": "chat_storage", "index": i},
            )
            assert chat_id is not None

        # ASPECT 2: Persistence - Verify data is in database
        stats = memori_sqlite.db_manager.get_memory_stats(memori_sqlite.user_id)
        assert stats["chat_history_count"] == len(sample_chat_messages)

        # ASPECT 3: Integration - Retrieve and verify content
        history = memori_sqlite.db_manager.get_chat_history(
            user_id=memori_sqlite.user_id, limit=10
        )
        assert len(history) == len(sample_chat_messages)

        # Verify specific message content
        user_inputs = [h["user_input"] for h in history]
        assert "What is artificial intelligence?" in user_inputs

    @pytest.mark.skip(
        reason="store_short_term_memory() API not available - short-term memory is managed internally"
    )
    def test_short_term_memory_operations(self, memori_sqlite, test_namespace):
        """
        Test 3: Short-term memory storage and retrieval.

        Validates:
        - Functional: Can create short-term memories
        - Persistence: Memories stored in database
        - Integration: Can search and retrieve memories
        """
        # ASPECT 1: Functional - Store short-term memory
        memory_id = memori_sqlite.db_manager.store_short_term_memory(
            content="User prefers Python and FastAPI for backend development",
            summary="User's technology preferences for backend",
            category_primary="preference",
            category_secondary="technology",
            session_id="test_session",
            user_id=memori_sqlite.user_id,
            metadata={"test": "short_term", "importance": "high"},
        )
        assert memory_id is not None

        # ASPECT 2: Persistence - Verify in database
        stats = memori_sqlite.db_manager.get_memory_stats(memori_sqlite.user_id)
        assert stats["short_term_count"] >= 1

        # ASPECT 3: Integration - Search and retrieve
        results = memori_sqlite.db_manager.search_memories(
            "Python FastAPI", user_id=memori_sqlite.user_id
        )
        assert len(results) > 0
        assert (
            "Python" in results[0]["processed_data"]["content"]
            or "FastAPI" in results[0]["processed_data"]["content"]
        )

    def test_long_term_memory_operations(self, memori_sqlite, test_namespace):
        """
        Test 4: Long-term memory storage and retrieval.

        Validates:
        - Functional: Can create long-term memories
        - Persistence: Memories persisted correctly
        - Integration: Search works across memory types
        """
        # ASPECT 1: Functional - Store long-term memory
        memory = create_simple_memory(
            content="User is building an AI agent with SQLite database backend",
            summary="User's current project: AI agent with SQLite",
            classification="context",
            importance="high",
            metadata={"test": "long_term", "project": "ai_agent"},
        )
        memory_id = memori_sqlite.db_manager.store_long_term_memory_enhanced(
            memory=memory, chat_id="test_sqlite_chat_1", user_id=memori_sqlite.user_id
        )
        assert memory_id is not None

        # ASPECT 2: Persistence - Verify storage
        stats = memori_sqlite.db_manager.get_memory_stats(memori_sqlite.user_id)
        assert stats["long_term_count"] >= 1

        # ASPECT 3: Integration - Retrieve and validate
        results = memori_sqlite.db_manager.search_memories(
            "AI agent SQLite", user_id=memori_sqlite.user_id
        )
        assert len(results) > 0
        found_memory = any(
            "AI agent" in r["processed_data"]["content"] for r in results
        )
        assert found_memory


@pytest.mark.sqlite
@pytest.mark.integration
class TestSQLiteFullTextSearch:
    """Test SQLite FTS5 full-text search functionality."""

    def test_fts_search_basic(
        self, memori_sqlite, test_namespace, sample_chat_messages
    ):
        """
        Test 5: Basic full-text search.

        Validates:
        - Functional: FTS queries work
        - Persistence: FTS index is populated
        - Integration: Search returns relevant results
        """
        from conftest import create_simple_memory

        # Setup: Store test data as long-term memories for search
        for i, msg in enumerate(sample_chat_messages):
            memory = create_simple_memory(
                content=f"{msg['user_input']} {msg['ai_output']}",
                summary=msg["user_input"][:50],
                classification="conversational",
            )
            memori_sqlite.db_manager.store_long_term_memory_enhanced(
                memory=memory, chat_id=f"fts_test_{i}", user_id=memori_sqlite.user_id
            )

        # ASPECT 1: Functional - Search works
        results = memori_sqlite.db_manager.search_memories(
            "artificial intelligence", user_id=memori_sqlite.user_id
        )
        assert len(results) > 0

        # ASPECT 2: Persistence - Results come from database
        assert all("search_score" in r or "search_strategy" in r for r in results)

        # ASPECT 3: Integration - Relevant results returned
        top_result = results[0]
        assert (
            "artificial" in top_result["processed_data"]["content"].lower()
            or "intelligence" in top_result["processed_data"]["content"].lower()
        )

    def test_fts_search_boolean_operators(self, memori_sqlite, test_namespace):
        """
        Test 6: FTS Boolean operators (AND, OR, NOT).

        Validates:
        - Functional: Boolean search works
        - Persistence: Complex queries execute
        - Integration: Correct results for complex queries
        """
        # Setup: Create specific test data
        test_data = [
            "Python is great for machine learning",
            "JavaScript is great for web development",
            "Python and JavaScript are both popular",
            "Machine learning requires Python expertise",
        ]

        for i, content in enumerate(test_data):
            memory = create_simple_memory(
                content=content, summary=f"Test content {i}", classification="knowledge"
            )
            memori_sqlite.db_manager.store_long_term_memory_enhanced(
                memory=memory,
                chat_id=f"boolean_test_chat_{i}",
                user_id=memori_sqlite.user_id,
            )

        # ASPECT 1: Functional - AND operator
        results = memori_sqlite.db_manager.search_memories(
            "Python machine", user_id=memori_sqlite.user_id
        )
        assert len(results) >= 2  # Should match "Python...machine learning" entries

        # ASPECT 2: Persistence - Database handles query
        stats = memori_sqlite.db_manager.get_memory_stats(memori_sqlite.user_id)
        assert stats["long_term_count"] >= 4

        # ASPECT 3: Integration - Correct filtering
        python_results = [
            r for r in results if "Python" in r["processed_data"]["content"]
        ]
        assert len(python_results) > 0


@pytest.mark.sqlite
@pytest.mark.integration
class TestSQLiteMemoryLifecycle:
    """Test complete memory lifecycle workflows."""

    def test_memory_creation_to_retrieval_workflow(self, memori_sqlite, test_namespace):
        """
        Test 7: Complete memory workflow from creation to retrieval.

        Validates end-to-end workflow:
        - Create memory
        - Store in database
        - Search and retrieve
        - Verify content integrity
        """
        # Step 1: Create memory
        original_content = "User is working on a FastAPI project with SQLite database"

        memory = create_simple_memory(
            content=original_content,
            summary="User's project context",
            classification="context",
            importance="high",
        )
        memory_id = memori_sqlite.db_manager.store_long_term_memory_enhanced(
            memory=memory,
            chat_id="lifecycle_test_chat_1",
            user_id=memori_sqlite.user_id,
        )

        # ASPECT 1: Functional - Memory created
        assert memory_id is not None

        # Step 2: Verify persistence
        stats = memori_sqlite.db_manager.get_memory_stats(memori_sqlite.user_id)

        # ASPECT 2: Persistence - Memory in database
        assert stats["long_term_count"] >= 1

        # Step 3: Retrieve memory
        results = memori_sqlite.db_manager.search_memories(
            "FastAPI SQLite", user_id=memori_sqlite.user_id
        )

        # ASPECT 3: Integration - Retrieved with correct content
        assert len(results) > 0
        retrieved = results[0]
        assert "FastAPI" in retrieved["processed_data"]["content"]
        assert (
            retrieved["category_primary"] == "contextual"
        )  # Maps from "context" classification

    @pytest.mark.skip(
        reason="store_short_term_memory() API not available - short-term memory is managed internally"
    )
    def test_multiple_memory_types_interaction(self, memori_sqlite, test_namespace):
        """
        Test 8: Interaction between different memory types.

        Validates:
        - Short-term and long-term memories coexist
        - Chat history integrates with memories
        - Search works across all types
        """
        # Create different memory types
        # 1. Chat history
        memori_sqlite.db_manager.store_chat_history(
            chat_id="multi_test_chat",
            user_input="Tell me about Python",
            ai_output="Python is a versatile programming language",
            model="test-model",
            timestamp=datetime.now(),
            session_id="multi_test",
            user_id=memori_sqlite.user_id,
            tokens_used=25,
        )

        # 2. Short-term memory
        memori_sqlite.db_manager.store_short_term_memory(
            content="User asked about Python programming",
            summary="Python inquiry",
            category_primary="context",
            session_id="multi_test",
            user_id=memori_sqlite.user_id,
        )

        # 3. Long-term memory
        memory = create_simple_memory(
            content="User is interested in Python development",
            summary="User's Python interest",
            classification="preference",
        )
        memori_sqlite.db_manager.store_long_term_memory_enhanced(
            memory=memory, chat_id="multi_test_chat_2", user_id=memori_sqlite.user_id
        )

        # ASPECT 1: Functional - All types stored
        stats = memori_sqlite.db_manager.get_memory_stats(memori_sqlite.user_id)
        assert stats["chat_history_count"] >= 1
        assert stats["short_term_count"] >= 1
        assert stats["long_term_count"] >= 1

        # ASPECT 2: Persistence - Data in database
        assert stats["database_type"] == "sqlite"

        # ASPECT 3: Integration - Search finds across types
        results = memori_sqlite.db_manager.search_memories(
            "Python", user_id=memori_sqlite.user_id
        )
        assert len(results) >= 2  # Should find multiple entries


@pytest.mark.sqlite
@pytest.mark.integration
@pytest.mark.performance
class TestSQLitePerformance:
    """Test SQLite performance characteristics."""

    def test_bulk_insertion_performance(
        self, memori_sqlite, test_namespace, performance_tracker
    ):
        """
        Test 9: Bulk insertion performance.

        Validates:
        - Functional: Can handle bulk inserts
        - Persistence: All data stored correctly
        - Performance: Meets performance targets
        """
        num_records = 50

        # ASPECT 1: Functional - Bulk insert works
        with performance_tracker.track("bulk_insert"):
            for i in range(num_records):
                memori_sqlite.db_manager.store_chat_history(
                    chat_id=f"perf_test_{i}",
                    user_input=f"Test message {i} with search keywords",
                    ai_output=f"Response {i} about test message",
                    model="test-model",
                    timestamp=datetime.now(),
                    session_id="perf_test",
                    user_id=memori_sqlite.user_id,
                    tokens_used=30,
                )

        # ASPECT 2: Persistence - All records stored
        stats = memori_sqlite.db_manager.get_memory_stats(memori_sqlite.user_id)
        assert stats["chat_history_count"] == num_records

        # ASPECT 3: Performance - Within acceptable time
        metrics = performance_tracker.get_metrics()
        insert_time = metrics["bulk_insert"]
        time_per_record = insert_time / num_records

        print(
            f"\nBulk insert: {insert_time:.3f}s total, {time_per_record:.4f}s per record"
        )
        assert insert_time < 10.0  # Should complete within 10 seconds

    def test_search_performance(
        self, memori_sqlite, test_namespace, performance_tracker
    ):
        """
        Test 10: Search performance.

        Validates:
        - Functional: Search works at scale
        - Persistence: FTS index used
        - Performance: Search is fast
        """
        # Setup: Create searchable data
        for i in range(20):
            memory = create_simple_memory(
                content=f"Python development tip {i}: Use type hints for better code",
                summary=f"Python tip {i}",
                classification="knowledge",
            )
            memori_sqlite.db_manager.store_long_term_memory_enhanced(
                memory=memory,
                chat_id=f"search_perf_chat_{i}",
                user_id=memori_sqlite.user_id,
            )

        # ASPECT 1: Functional - Search works
        with performance_tracker.track("search"):
            results = memori_sqlite.db_manager.search_memories(
                "Python type hints", user_id=memori_sqlite.user_id
            )

        # ASPECT 2: Persistence - Results from database
        assert len(results) > 0

        # ASPECT 3: Performance - Fast search
        metrics = performance_tracker.get_metrics()
        search_time = metrics["search"]

        print(f"\nSearch performance: {search_time:.3f}s for {len(results)} results")
        assert search_time < 1.0  # Search should be under 1 second


@pytest.mark.sqlite
@pytest.mark.integration
class TestSQLiteConcurrency:
    """Test SQLite concurrent access patterns."""

    def test_sequential_access_from_same_instance(self, memori_sqlite, test_namespace):
        """
        Test 11: Sequential database access.

        Validates:
        - Functional: Multiple operations work
        - Persistence: Data consistency maintained
        - Integration: No corruption with sequential access
        """
        # Perform multiple operations sequentially
        for i in range(10):
            # Store
            memory = create_simple_memory(
                content=f"Sequential test {i}",
                summary=f"Test {i}",
                classification="knowledge",
            )
            memori_sqlite.db_manager.store_long_term_memory_enhanced(
                memory=memory,
                chat_id=f"sequential_test_chat_{i}",
                user_id=memori_sqlite.user_id,
            )

            # Retrieve
            stats = memori_sqlite.db_manager.get_memory_stats(memori_sqlite.user_id)
            assert stats["long_term_count"] == i + 1

        # ASPECT 1: Functional - All operations succeeded
        assert True  # If we got here, all operations worked

        # ASPECT 2: Persistence - All data stored
        final_stats = memori_sqlite.db_manager.get_memory_stats(memori_sqlite.user_id)
        assert final_stats["long_term_count"] == 10

        # ASPECT 3: Integration - Data retrievable
        results = memori_sqlite.db_manager.search_memories(
            "Sequential", user_id=memori_sqlite.user_id
        )
        assert len(results) == 10


@pytest.mark.sqlite
@pytest.mark.integration
class TestSQLiteEdgeCases:
    """Test SQLite edge cases and error handling."""

    def test_empty_search_query(self, memori_sqlite, test_namespace):
        """
        Test 12: Handle empty search queries gracefully.
        """
        results = memori_sqlite.db_manager.search_memories(
            "", user_id=memori_sqlite.user_id
        )
        # Should return empty results or handle gracefully, not crash
        assert isinstance(results, list)

    def test_nonexistent_namespace(self, memori_sqlite):
        """
        Test 13: Query nonexistent namespace.
        """
        stats = memori_sqlite.db_manager.get_memory_stats("nonexistent_namespace_12345")
        # Should return stats with zero counts, not crash
        assert isinstance(stats, dict)
        assert stats.get("chat_history_count", 0) == 0

    def test_very_long_content(self, memori_sqlite, test_namespace):
        """
        Test 14: Handle very long content strings.
        """
        long_content = "x" * 10000  # 10KB of text

        memory = create_simple_memory(
            content=long_content,
            summary="Very long content test",
            classification="knowledge",
        )
        memory_id = memori_sqlite.db_manager.store_long_term_memory_enhanced(
            memory=memory,
            chat_id="long_content_test_chat_1",
            user_id=memori_sqlite.user_id,
        )

        assert memory_id is not None

        # Verify it was stored and can be retrieved
        results = memori_sqlite.db_manager.search_memories(
            "xxx", user_id=memori_sqlite.user_id
        )
        assert len(results) > 0

    def test_special_characters_in_content(self, memori_sqlite, test_namespace):
        """
        Test 15: Handle special characters properly.
        """
        special_content = "Test with special chars: @#$%^&*()[]{}|\\:;\"'<>?/"

        memory = create_simple_memory(
            content=special_content,
            summary="Special characters test",
            classification="knowledge",
        )
        memory_id = memori_sqlite.db_manager.store_long_term_memory_enhanced(
            memory=memory,
            chat_id="special_chars_test_chat_1",
            user_id=memori_sqlite.user_id,
        )

        assert memory_id is not None

        # Verify retrieval works
        stats = memori_sqlite.db_manager.get_memory_stats(memori_sqlite.user_id)
        assert stats["long_term_count"] >= 1
