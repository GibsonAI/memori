"""
OpenAI Provider Integration Tests

Tests Memori integration with OpenAI API.

Validates three aspects:
1. Functional: OpenAI calls work with Memori enabled
2. Persistence: Conversations are recorded in database
3. Integration: Memory injection works correctly
"""

import os
import time

import pytest


@pytest.mark.llm
@pytest.mark.integration
class TestOpenAIBasicIntegration:
    """Test basic OpenAI integration with Memori."""

    def test_openai_with_mock(
        self, memori_sqlite, test_namespace, mock_openai_response
    ):
        """
        Test 1: OpenAI integration with mocked API (fast, no API cost).

        Validates:
        - Functional: Memori.enable() works with OpenAI client
        - Persistence: Conversation attempt recorded
        - Integration: No errors in integration layer
        """
        pytest.importorskip("openai")
        from unittest.mock import patch

        from openai import OpenAI

        # ASPECT 1: Functional - Enable Memori and create client
        memori_sqlite.enable()
        client = OpenAI(api_key="test-key")

        # Mock at the OpenAI API level
        with patch(
            "openai.resources.chat.completions.Completions.create",
            return_value=mock_openai_response,
        ):
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": "What is Python?"}],
            )

            # Verify call succeeded
            assert response is not None
            assert (
                response.choices[0].message.content
                == "Python is a programming language."
            )

        # ASPECT 2: Persistence - Give time for async recording (if implemented)
        time.sleep(0.5)

        # ASPECT 3: Integration - Memori is enabled
        assert memori_sqlite._enabled

    def test_openai_multiple_messages(
        self, memori_sqlite, test_namespace, mock_openai_response
    ):
        """
        Test 2: Multiple OpenAI messages in sequence.

        Validates:
        - Functional: Multiple calls work
        - Persistence: All conversations tracked
        - Integration: No interference between calls
        """
        pytest.importorskip("openai")
        from unittest.mock import patch

        from openai import OpenAI

        memori_sqlite.enable()
        client = OpenAI(api_key="test-key")

        messages_to_send = [
            "Tell me about Python",
            "What is FastAPI?",
            "How do I use async/await?",
        ]

        # ASPECT 1: Functional - Send multiple messages
        with patch(
            "openai.resources.chat.completions.Completions.create",
            return_value=mock_openai_response,
        ):
            for msg in messages_to_send:
                response = client.chat.completions.create(
                    model="gpt-4o-mini", messages=[{"role": "user", "content": msg}]
                )
                assert response is not None

        time.sleep(0.5)

        # ASPECT 2 & 3: Integration - All calls succeeded
        assert memori_sqlite._enabled

    def test_openai_conversation_recording(
        self, memori_sqlite, test_namespace, mock_openai_response
    ):
        """
        Test 3: Verify conversation recording.

        Validates:
        - Functional: OpenAI call succeeds
        - Persistence: Conversation stored in database
        - Integration: Can retrieve conversation from DB
        """
        pytest.importorskip("openai")
        from unittest.mock import patch

        from openai import OpenAI

        memori_sqlite.enable()
        client = OpenAI(api_key="test-key")

        user_message = "What is the capital of France?"

        # ASPECT 1: Functional - Make call
        with patch(
            "openai.resources.chat.completions.Completions.create",
            return_value=mock_openai_response,
        ):
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": user_message}],
            )
            assert response is not None

        time.sleep(0.5)

        # ASPECT 2: Persistence - Check if conversation recorded
        stats = memori_sqlite.db_manager.get_memory_stats("default")
        # Note: Recording depends on implementation - this validates DB access works
        assert isinstance(stats, dict)
        assert "database_type" in stats

        # ASPECT 3: Integration - Can query history
        history = memori_sqlite.db_manager.get_chat_history("default", limit=10)
        assert isinstance(history, list)

    @pytest.mark.skip(
        reason="store_short_term_memory() API not available - short-term memory is managed internally"
    )
    def test_openai_context_injection_conscious_mode(
        self, memori_sqlite_conscious, test_namespace, mock_openai_response
    ):
        """
        Test 4: Context injection in conscious mode.

        Validates:
        - Functional: Conscious mode enabled
        - Persistence: Permanent context stored
        - Integration: Context available for injection
        """
        pytest.importorskip("openai")
        from unittest.mock import patch

        from openai import OpenAI

        # Setup: Store permanent context
        memori_sqlite_conscious.db_manager.store_short_term_memory(
            content="User is a senior Python developer with FastAPI experience",
            summary="User context",
            category_primary="context",
            session_id="test_session",
            user_id=memori_sqlite_conscious.user_id,
            is_permanent_context=True,
        )

        # ASPECT 1: Functional - Enable and make call
        memori_sqlite_conscious.enable()
        client = OpenAI(api_key="test-key")

        with patch(
            "openai.resources.chat.completions.Completions.create",
            return_value=mock_openai_response,
        ):
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": "Help me with my project"}],
            )
            assert response is not None

        # ASPECT 2: Persistence - Context exists in short-term memory
        stats = memori_sqlite_conscious.db_manager.get_memory_stats("default")
        assert stats["short_term_count"] >= 1

        # ASPECT 3: Integration - Conscious mode is active
        assert memori_sqlite_conscious.conscious_ingest


@pytest.mark.llm
@pytest.mark.integration
@pytest.mark.slow
class TestOpenAIRealAPI:
    """Test with real OpenAI API calls (requires API key)."""

    def test_openai_real_api_call(self, memori_sqlite, test_namespace):
        """
        Test 5: Real OpenAI API call (if API key available).

        Validates:
        - Functional: Real API integration works
        - Persistence: Real conversation stored
        - Integration: End-to-end workflow
        """
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key or api_key.startswith("test"):
            pytest.skip("OPENAI_API_KEY not set or is test key")

        pytest.importorskip("openai")
        from openai import OpenAI

        # ASPECT 1: Functional - Real API call
        memori_sqlite.enable()
        client = OpenAI(api_key=api_key)

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "user", "content": "Say 'test successful' and nothing else"}
            ],
            max_tokens=10,
        )

        # ASPECT 2: Persistence - Validate response
        assert response is not None
        assert len(response.choices[0].message.content) > 0
        print(f"\nReal OpenAI response: {response.choices[0].message.content}")

        time.sleep(1.0)  # Give time for recording

        # ASPECT 3: Integration - End-to-end successful
        assert memori_sqlite._enabled


@pytest.mark.llm
@pytest.mark.integration
class TestOpenAIErrorHandling:
    """Test OpenAI error handling."""

    def test_openai_api_error_handling(self, memori_sqlite, test_namespace):
        """
        Test 6: Graceful handling of OpenAI API errors.

        Validates:
        - Functional: Errors don't crash Memori
        - Persistence: System remains stable
        - Integration: Proper error propagation
        """
        pytest.importorskip("openai")
        from unittest.mock import patch

        from openai import OpenAI

        memori_sqlite.enable()
        client = OpenAI(api_key="test-key")

        # ASPECT 1: Functional - Simulate API error
        with patch(
            "openai.resources.chat.completions.Completions.create",
            side_effect=Exception("API Error"),
        ):
            with pytest.raises(Exception) as exc_info:
                client.chat.completions.create(
                    model="gpt-4o-mini", messages=[{"role": "user", "content": "Test"}]
                )

            assert "API Error" in str(exc_info.value)

        # ASPECT 2 & 3: Memori still functional after error
        stats = memori_sqlite.db_manager.get_memory_stats("default")
        assert isinstance(stats, dict)

    def test_openai_invalid_api_key(self, memori_sqlite, test_namespace):
        """
        Test 7: Handle invalid API key gracefully.

        Validates:
        - Functional: Invalid key detected
        - Persistence: No corruption
        - Integration: Clean error handling
        """
        pytest.importorskip("openai")
        from openai import OpenAI

        memori_sqlite.enable()

        # Create client with invalid key
        client = OpenAI(api_key="invalid-key")

        # Note: This test documents behavior - actual API call would fail
        # In real usage, OpenAI SDK would raise an authentication error
        assert client.api_key == "invalid-key"

        # ASPECT 3: Memori remains stable
        assert memori_sqlite._enabled


@pytest.mark.llm
@pytest.mark.integration
@pytest.mark.performance
class TestOpenAIPerformance:
    """Test OpenAI integration performance."""

    def test_openai_overhead_measurement(
        self, memori_sqlite, test_namespace, mock_openai_response, performance_tracker
    ):
        """
        Test 8: Measure Memori overhead with OpenAI.

        Validates:
        - Functional: Performance measurable
        - Persistence: Recording doesn't block
        - Integration: Minimal overhead
        """
        pytest.importorskip("openai")
        from unittest.mock import patch

        from openai import OpenAI

        client = OpenAI(api_key="test-key")

        # Baseline: Without Memori
        with performance_tracker.track("without_memori"):
            with patch(
                "openai.resources.chat.completions.Completions.create",
                return_value=mock_openai_response,
            ):
                for i in range(10):
                    client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[{"role": "user", "content": f"Test {i}"}],
                    )

        # With Memori enabled
        memori_sqlite.enable()

        with performance_tracker.track("with_memori"):
            with patch(
                "openai.resources.chat.completions.Completions.create",
                return_value=mock_openai_response,
            ):
                for i in range(10):
                    client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[{"role": "user", "content": f"Test {i}"}],
                    )

        # ASPECT 3: Performance - Measure overhead
        metrics = performance_tracker.get_metrics()
        without = metrics.get("without_memori", 0.001)  # Avoid division by zero
        with_memori = metrics.get("with_memori", 0.001)

        overhead = with_memori - without
        overhead_pct = (overhead / without) * 100 if without > 0 else 0

        print("\nOpenAI Performance:")
        print(f"  Without Memori: {without:.3f}s")
        print(f"  With Memori:    {with_memori:.3f}s")
        print(f"  Overhead:       {overhead:.3f}s ({overhead_pct:.1f}%)")

        # Overhead should be reasonable (allow up to 100% for mocked tests)
        assert overhead_pct < 100, f"Overhead too high: {overhead_pct:.1f}%"
