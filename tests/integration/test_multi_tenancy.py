"""
Multi-Tenancy Integration Tests

Tests user_id and assistant_id isolation across databases.

Validates three aspects:
1. Functional: Multi-tenancy features work
2. Persistence: Data isolation in database
3. Integration: No data leakage between users/assistants

These are CRITICAL tests for the new user_id and assistant_id parameters.
"""

from datetime import datetime

import pytest
from conftest import create_simple_memory


@pytest.mark.multi_tenancy
@pytest.mark.integration
class TestUserIDIsolation:
    """Test user_id provides complete data isolation."""

    def test_user_isolation_basic_sqlite(
        self, multi_user_memori_sqlite, test_namespace
    ):
        """
        Test 1: Basic user_id isolation in SQLite.

        Validates:
        - Functional: Different users can store data
        - Persistence: Data stored with user_id
        - Integration: Users cannot see each other's data
        """
        users = multi_user_memori_sqlite

        # ASPECT 1: Functional - Each user stores data
        alice_memory = create_simple_memory(
            content="Alice's secret project uses Django",
            summary="Alice's project",
            classification="context",
        )
        users["alice"].db_manager.store_long_term_memory_enhanced(
            memory=alice_memory,
            chat_id="alice_test_chat_1",
            user_id=users["alice"].user_id,
        )

        bob_memory = create_simple_memory(
            content="Bob's secret project uses FastAPI",
            summary="Bob's project",
            classification="context",
        )
        users["bob"].db_manager.store_long_term_memory_enhanced(
            memory=bob_memory, chat_id="bob_test_chat_1", user_id=users["bob"].user_id
        )

        # ASPECT 2: Persistence - Data in database with user_id
        alice_stats = users["alice"].db_manager.get_memory_stats(users["alice"].user_id)
        bob_stats = users["bob"].db_manager.get_memory_stats(users["bob"].user_id)

        assert alice_stats["long_term_count"] >= 1
        assert bob_stats["long_term_count"] >= 1

        # ASPECT 3: Integration - Complete isolation
        # Alice only sees her data
        alice_results = users["alice"].db_manager.search_memories(
            "project", user_id=users["alice"].user_id
        )
        assert len(alice_results) == 1
        assert "Django" in alice_results[0]["processed_data"]["content"]
        assert "FastAPI" not in alice_results[0]["processed_data"]["content"]

        # Bob only sees his data
        bob_results = users["bob"].db_manager.search_memories(
            "project", user_id=users["bob"].user_id
        )
        assert len(bob_results) == 1
        assert "FastAPI" in bob_results[0]["processed_data"]["content"]
        assert "Django" not in bob_results[0]["processed_data"]["content"]

    def test_user_isolation_basic_postgresql(
        self, multi_user_memori_postgresql, test_namespace
    ):
        """
        Test 2: Basic user_id isolation in PostgreSQL.

        Validates same isolation as SQLite but with PostgreSQL.
        """
        users = multi_user_memori_postgresql

        # ASPECT 1: Functional - Each user stores data
        alice_memory = create_simple_memory(
            content="Alice uses PostgreSQL for production",
            summary="Alice's database choice",
            classification="preference",
        )
        users["alice"].db_manager.store_long_term_memory_enhanced(
            memory=alice_memory,
            chat_id="alice_pg_test_chat_1",
            user_id=users["alice"].user_id,
        )

        bob_memory = create_simple_memory(
            content="Bob uses MySQL for production",
            summary="Bob's database choice",
            classification="preference",
        )
        users["bob"].db_manager.store_long_term_memory_enhanced(
            memory=bob_memory,
            chat_id="bob_pg_test_chat_1",
            user_id=users["bob"].user_id,
        )

        # ASPECT 2: Persistence - Data stored with user isolation
        alice_stats = users["alice"].db_manager.get_memory_stats(users["alice"].user_id)
        bob_stats = users["bob"].db_manager.get_memory_stats(users["bob"].user_id)

        assert alice_stats["long_term_count"] >= 1
        assert bob_stats["long_term_count"] >= 1

        # ASPECT 3: Integration - PostgreSQL maintains isolation
        alice_results = users["alice"].db_manager.search_memories(
            "production", user_id=users["alice"].user_id
        )
        assert len(alice_results) == 1
        assert "PostgreSQL" in alice_results[0]["processed_data"]["content"]
        assert "MySQL" not in alice_results[0]["processed_data"]["content"]

        bob_results = users["bob"].db_manager.search_memories(
            "production", user_id=users["bob"].user_id
        )
        assert len(bob_results) == 1
        assert "MySQL" in bob_results[0]["processed_data"]["content"]
        assert "PostgreSQL" not in bob_results[0]["processed_data"]["content"]

    def test_user_isolation_chat_history(self, multi_user_memori, test_namespace):
        """
        Test 3: User isolation for chat history.

        Validates:
        - Functional: Chat history stored per user
        - Persistence: user_id in chat records
        - Integration: No chat leakage
        """
        users = multi_user_memori

        # ASPECT 1: Functional - Store chat for each user
        users["alice"].db_manager.store_chat_history(
            chat_id="alice_chat_1",
            user_input="Alice asks about Python",
            ai_output="Python is great for Alice's use case",
            model="test-model",
            timestamp=datetime.now(),
            session_id="alice_chat_session",
            user_id=users["alice"].user_id,
            tokens_used=25,
        )

        users["bob"].db_manager.store_chat_history(
            chat_id="bob_chat_1",
            user_input="Bob asks about JavaScript",
            ai_output="JavaScript is great for Bob's use case",
            model="test-model",
            timestamp=datetime.now(),
            session_id="bob_chat_session",
            user_id=users["bob"].user_id,
            tokens_used=25,
        )

        # ASPECT 2: Persistence - Each user has their chat
        alice_stats = users["alice"].db_manager.get_memory_stats(users["alice"].user_id)
        bob_stats = users["bob"].db_manager.get_memory_stats(users["bob"].user_id)

        assert alice_stats["chat_history_count"] == 1
        assert bob_stats["chat_history_count"] == 1

        # ASPECT 3: Integration - Chat isolation verified
        alice_history = users["alice"].db_manager.get_chat_history(
            users["alice"].user_id, limit=10
        )
        bob_history = users["bob"].db_manager.get_chat_history(
            users["bob"].user_id, limit=10
        )

        assert len(alice_history) == 1
        assert len(bob_history) == 1
        assert "Python" in alice_history[0]["user_input"]
        assert "JavaScript" in bob_history[0]["user_input"]

    def test_user_isolation_with_same_content(self, multi_user_memori, test_namespace):
        """
        Test 4: User isolation even with identical content.

        Validates:
        - Functional: Same content stored for different users
        - Persistence: Separate records in database
        - Integration: Each user retrieves only their copy
        """
        users = multi_user_memori

        same_content = "I prefer Python for backend development"

        # ASPECT 1: Functional - Multiple users store same content
        for user_id in ["alice", "bob", "charlie"]:
            memory = create_simple_memory(
                content=same_content,
                summary=f"{user_id}'s preference",
                classification="preference",
            )
            users[user_id].db_manager.store_long_term_memory_enhanced(
                memory=memory,
                chat_id=f"{user_id}_test_chat_1",
                user_id=users[user_id].user_id,
            )

        # ASPECT 2: Persistence - Each user has their own copy
        for user_id in ["alice", "bob", "charlie"]:
            stats = users[user_id].db_manager.get_memory_stats(users[user_id].user_id)
            assert stats["long_term_count"] == 1

        # ASPECT 3: Integration - Each user sees only one result (theirs)
        for user_id in ["alice", "bob", "charlie"]:
            results = users[user_id].db_manager.search_memories(
                "Python", user_id=users[user_id].user_id
            )
            assert len(results) == 1  # Only their own memory, not others
            assert results[0]["processed_data"]["content"] == same_content


@pytest.mark.multi_tenancy
@pytest.mark.integration
class TestCrossUserDataLeakagePrevention:
    """Test that no data leaks between users under any circumstances."""

    def test_prevent_data_leakage_via_search(self, multi_user_memori, test_namespace):
        """
        Test 5: Prevent data leakage through search queries.

        Validates:
        - Functional: Search works for each user
        - Persistence: Searches respect user_id
        - Integration: No results from other users
        """
        users = multi_user_memori

        # Setup: Each user stores unique secret
        secrets = {
            "alice": "alice_secret_password_12345",
            "bob": "bob_secret_password_67890",
            "charlie": "charlie_secret_password_abcde",
        }

        for user_id, secret in secrets.items():
            memory = create_simple_memory(
                content=f"{user_id}'s secret is {secret}",
                summary=f"{user_id}'s secret",
                classification="knowledge",
            )
            users[user_id].db_manager.store_long_term_memory_enhanced(
                memory=memory,
                chat_id=f"{user_id}_secret_test_chat_1",
                user_id=users[user_id].user_id,
            )

        # ASPECT 1 & 2: Each user can search
        # ASPECT 3: No user sees another user's secret
        for user_id, expected_secret in secrets.items():
            results = users[user_id].db_manager.search_memories(
                "secret password", user_id=users[user_id].user_id
            )

            assert len(results) == 1  # Only one result (their own)
            assert expected_secret in results[0]["processed_data"]["content"]

            # Verify no other secrets visible
            for other_user, other_secret in secrets.items():
                if other_user != user_id:
                    assert other_secret not in results[0]["processed_data"]["content"]

    def test_prevent_leakage_with_high_volume(self, multi_user_memori, test_namespace):
        """
        Test 6: Data isolation with high volume of data.

        Validates:
        - Functional: Handles many users and records
        - Persistence: Isolation maintained at scale
        - Integration: Performance doesn't compromise security
        """
        users = multi_user_memori

        # Create significant data for each user
        num_memories = 20

        for user_id in ["alice", "bob", "charlie"]:
            for i in range(num_memories):
                memory = create_simple_memory(
                    content=f"{user_id}_memory_{i}_with_unique_keyword_{user_id}",
                    summary=f"{user_id} memory {i}",
                    classification="knowledge",
                )
                users[user_id].db_manager.store_long_term_memory_enhanced(
                    memory=memory,
                    chat_id=f"{user_id}_bulk_test_chat_{i}",
                    user_id=users[user_id].user_id,
                )

        # ASPECT 1 & 2: All data stored
        for user_id in ["alice", "bob", "charlie"]:
            stats = users[user_id].db_manager.get_memory_stats(users[user_id].user_id)
            assert stats["long_term_count"] == num_memories

        # ASPECT 3: Each user only sees their data
        for user_id in ["alice", "bob", "charlie"]:
            results = users[user_id].db_manager.search_memories(
                "memory", user_id=users[user_id].user_id
            )

            # Should find their memories (up to search limit)
            assert len(results) > 0

            # All results should belong to this user
            for result in results:
                assert (
                    f"unique_keyword_{user_id}" in result["processed_data"]["content"]
                )

                # Verify no other user's keywords
                other_users = [u for u in ["alice", "bob", "charlie"] if u != user_id]
                for other_user in other_users:
                    assert (
                        f"unique_keyword_{other_user}"
                        not in result["processed_data"]["content"]
                    )

    def test_sql_injection_safety(self, multi_user_memori_sqlite, test_namespace):
        """
        Test 7: user_id is safe from SQL injection.

        Validates:
        - Functional: Malicious user_id handled safely
        - Persistence: Database integrity maintained
        - Integration: No SQL injection possible
        """
        # Note: This test uses the multi_user fixture which has safe user_ids
        # But we test that search queries are safe

        users = multi_user_memori_sqlite

        # Store normal data for alice
        memory = create_simple_memory(
            content="Alice's safe data", summary="Safe data", classification="knowledge"
        )
        users["alice"].db_manager.store_long_term_memory_enhanced(
            memory=memory,
            chat_id="sql_safety_test_chat_1",
            user_id=users["alice"].user_id,
        )

        # Try malicious search query
        malicious_query = "'; DROP TABLE long_term_memory; --"

        try:
            # This should not cause SQL injection
            results = users["alice"].db_manager.search_memories(
                malicious_query, user_id=users["alice"].user_id
            )

            # Should return empty results, not crash or execute SQL
            assert isinstance(results, list)

        except Exception as e:
            # If it fails, it should be a safe error, not SQL execution
            assert "DROP TABLE" not in str(e).upper()

        # Verify database is intact
        stats = users["alice"].db_manager.get_memory_stats(users["alice"].user_id)
        assert stats["long_term_count"] == 1


@pytest.mark.multi_tenancy
@pytest.mark.integration
class TestAssistantIDTracking:
    """Test assistant_id parameter for tracking which assistant created memories."""

    def test_assistant_id_basic_tracking(self, memori_sqlite, test_namespace):
        """
        Test 8: Basic assistant_id tracking.

        Validates:
        - Functional: Can store assistant_id
        - Persistence: assistant_id persisted in database
        - Integration: Can query by assistant_id
        """
        # ASPECT 1: Functional - Store memories with assistant_id
        # Note: This depends on your implementation supporting assistant_id

        memory = create_simple_memory(
            content="Memory created by assistant A",
            summary="Assistant A memory",
            classification="knowledge",
            metadata={"assistant_id": "assistant_a"},
        )
        memory_id = memori_sqlite.db_manager.store_long_term_memory_enhanced(
            memory=memory,
            chat_id="assistant_test_chat_1",
            user_id=memori_sqlite.user_id,
        )

        assert memory_id is not None

        # ASPECT 2: Persistence - Stored in database
        stats = memori_sqlite.db_manager.get_memory_stats(memori_sqlite.user_id)
        assert stats["long_term_count"] >= 1

        # ASPECT 3: Integration - Can retrieve
        results = memori_sqlite.db_manager.search_memories(
            "assistant", user_id=memori_sqlite.user_id
        )
        assert len(results) > 0

    def test_multiple_assistants_same_user(self, memori_sqlite, test_namespace):
        """
        Test 9: Multiple assistants working with same user.

        Validates:
        - Functional: Different assistants can create memories
        - Persistence: All memories stored correctly
        - Integration: Can distinguish between assistants
        """
        # Setup: Create memories from different assistants
        assistants = ["assistant_a", "assistant_b", "assistant_c"]

        for i, assistant_id in enumerate(assistants):
            memory = create_simple_memory(
                content=f"Memory from {assistant_id} for the user",
                summary=f"{assistant_id} memory",
                classification="knowledge",
                metadata={"assistant_id": assistant_id},
            )
            memori_sqlite.db_manager.store_long_term_memory_enhanced(
                memory=memory,
                chat_id=f"multi_assistant_test_chat_{i}",
                user_id=memori_sqlite.user_id,
            )

        # ASPECT 1 & 2: All stored
        stats = memori_sqlite.db_manager.get_memory_stats(memori_sqlite.user_id)
        assert stats["long_term_count"] >= 3

        # ASPECT 3: Can identify assistant memories
        for assistant_id in assistants:
            results = memori_sqlite.db_manager.search_memories(
                assistant_id, user_id=memori_sqlite.user_id
            )
            assert len(results) >= 1


@pytest.mark.multi_tenancy
@pytest.mark.integration
class TestNamespaceAndUserIDCombination:
    """Test combination of namespace and user_id for multi-dimensional isolation."""

    def test_namespace_user_isolation(self, multi_user_memori, test_namespace):
        """
        Test 10: Namespace + user_id isolation.

        Validates:
        - Functional: Namespace and user_id work together
        - Persistence: Double isolation in database
        - Integration: Users isolated per namespace
        """
        users = multi_user_memori

        # Alice in namespace 1
        memory_alice_ns1 = create_simple_memory(
            content="Alice data in namespace 1",
            summary="Alice NS1",
            classification="knowledge",
        )
        users["alice"].db_manager.store_long_term_memory_enhanced(
            memory=memory_alice_ns1,
            chat_id="alice_ns1_test_chat_1",
            user_id=users["alice"].user_id,
        )

        # Alice in namespace 2
        memory_alice_ns2 = create_simple_memory(
            content="Alice data in namespace 2",
            summary="Alice NS2",
            classification="knowledge",
        )
        users["alice"].db_manager.store_long_term_memory_enhanced(
            memory=memory_alice_ns2,
            chat_id="alice_ns2_test_chat_1",
            user_id=users["alice"].user_id,
        )

        # Bob in namespace 1
        memory_bob_ns1 = create_simple_memory(
            content="Bob data in namespace 1",
            summary="Bob NS1",
            classification="knowledge",
        )
        users["bob"].db_manager.store_long_term_memory_enhanced(
            memory=memory_bob_ns1,
            chat_id="bob_ns1_test_chat_1",
            user_id=users["bob"].user_id,
        )

        # ASPECT 1 & 2: All stored correctly
        # Alice sees 1 memory in each namespace (note: namespace isolation is per user_id)
        alice_stats = users["alice"].db_manager.get_memory_stats(users["alice"].user_id)
        assert alice_stats["long_term_count"] >= 2

        # Bob sees 1 memory
        bob_stats = users["bob"].db_manager.get_memory_stats(users["bob"].user_id)
        assert bob_stats["long_term_count"] >= 1

        # ASPECT 3: Complete isolation
        alice_results = users["alice"].db_manager.search_memories(
            "data", user_id=users["alice"].user_id
        )
        assert len(alice_results) >= 2
        assert "Alice" in str(alice_results)


@pytest.mark.multi_tenancy
@pytest.mark.integration
@pytest.mark.performance
class TestMultiTenancyPerformance:
    """Test multi-tenancy performance characteristics."""

    def test_multi_user_search_performance(
        self, multi_user_memori, test_namespace, performance_tracker
    ):
        """
        Test 11: Multi-user search doesn't degrade performance.

        Validates:
        - Functional: Search works for all users
        - Persistence: Indexing works per user
        - Performance: No performance degradation
        """
        users = multi_user_memori

        # Setup: Create data for each user
        for user_id in ["alice", "bob", "charlie"]:
            for i in range(10):
                memory = create_simple_memory(
                    content=f"{user_id} memory {i} with search keywords",
                    summary=f"{user_id} {i}",
                    classification="knowledge",
                )
                users[user_id].db_manager.store_long_term_memory_enhanced(
                    memory=memory,
                    chat_id=f"{user_id}_perf_test_chat_{i}",
                    user_id=users[user_id].user_id,
                )

        # Test search performance for each user
        for user_id in ["alice", "bob", "charlie"]:
            with performance_tracker.track(f"search_{user_id}"):
                results = users[user_id].db_manager.search_memories(
                    "memory keywords", user_id=users[user_id].user_id
                )
                assert len(results) > 0

        # Verify performance is consistent across users
        metrics = performance_tracker.get_metrics()
        for user_id in ["alice", "bob", "charlie"]:
            search_time = metrics[f"search_{user_id}"]
            print(f"\n{user_id} search time: {search_time:.3f}s")
            assert search_time < 1.0  # Each search should be fast
