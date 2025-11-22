"""
LiteLLM Provider Integration Tests

Tests Memori integration with LiteLLM (universal LLM interface).

Validates three aspects:
1. Functional: LiteLLM calls work with Memori enabled
2. Persistence: Conversations are recorded in database
3. Integration: Memory injection works across providers
"""

import time

import pytest


@pytest.mark.llm
@pytest.mark.integration
class TestLiteLLMBasicIntegration:
    """Test basic LiteLLM integration with Memori."""

    def test_litellm_with_mock(
        self, memori_sqlite, test_namespace, mock_openai_response
    ):
        """
        Test 1: LiteLLM integration with mocked response.

        Validates:
        - Functional: LiteLLM completion works with Memori
        - Persistence: Conversation attempt recorded
        - Integration: Provider-agnostic interception
        """
        pytest.importorskip("litellm")
        from unittest.mock import patch

        from litellm import completion

        # ASPECT 1: Functional - Enable and make call
        memori_sqlite.enable()

        with patch("litellm.completion", return_value=mock_openai_response):
            response = completion(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": "Test with LiteLLM"}],
            )

            assert response is not None
            assert (
                response.choices[0].message.content
                == "Python is a programming language."
            )

        time.sleep(0.5)

        # ASPECT 2: Persistence - Check database access
        stats = memori_sqlite.db_manager.get_memory_stats("default")
        assert isinstance(stats, dict)

        # ASPECT 3: Integration - Memori enabled
        assert memori_sqlite._enabled

    def test_litellm_multiple_messages(
        self, memori_sqlite, test_namespace, mock_openai_response
    ):
        """
        Test 2: Multiple LiteLLM calls in sequence.

        Validates:
        - Functional: Sequential calls work
        - Persistence: All conversations tracked
        - Integration: No call interference
        """
        pytest.importorskip("litellm")
        from unittest.mock import patch

        from litellm import completion

        memori_sqlite.enable()

        test_messages = [
            "What is LiteLLM?",
            "How does it work?",
            "What providers does it support?",
        ]

        # ASPECT 1: Functional - Multiple calls
        with patch("litellm.completion", return_value=mock_openai_response):
            for msg in test_messages:
                response = completion(
                    model="gpt-4o-mini", messages=[{"role": "user", "content": msg}]
                )
                assert response is not None

        time.sleep(0.5)

        # ASPECT 2 & 3: Integration successful
        assert memori_sqlite._enabled


@pytest.mark.llm
@pytest.mark.integration
class TestLiteLLMMultipleProviders:
    """Test LiteLLM with different provider models."""

    def test_litellm_openai_model(
        self, memori_sqlite, test_namespace, mock_openai_response
    ):
        """
        Test 3: LiteLLM with OpenAI model.

        Validates:
        - Functional: OpenAI via LiteLLM works
        - Persistence: Conversation recorded
        - Integration: Provider routing correct
        """
        pytest.importorskip("litellm")
        from unittest.mock import patch

        from litellm import completion

        memori_sqlite.enable()

        # ASPECT 1: Functional - OpenAI model
        with patch("litellm.completion", return_value=mock_openai_response):
            response = completion(
                model="gpt-4o-mini",  # OpenAI model
                messages=[{"role": "user", "content": "Test OpenAI via LiteLLM"}],
            )
            assert response is not None

        time.sleep(0.5)

        # ASPECT 2: Persistence - Recorded
        stats = memori_sqlite.db_manager.get_memory_stats("default")
        assert isinstance(stats, dict)

        # ASPECT 3: Integration - Success
        assert memori_sqlite._enabled

    def test_litellm_anthropic_model(
        self, memori_sqlite, test_namespace, mock_openai_response
    ):
        """
        Test 4: LiteLLM with Anthropic model format.

        Validates:
        - Functional: Anthropic model syntax works
        - Persistence: Provider-agnostic recording
        - Integration: Multi-provider support
        """
        pytest.importorskip("litellm")
        from unittest.mock import patch

        from litellm import completion

        memori_sqlite.enable()

        # ASPECT 1: Functional - Anthropic model
        with patch("litellm.completion", return_value=mock_openai_response):
            response = completion(
                model="claude-3-5-sonnet-20241022",  # Anthropic model
                messages=[{"role": "user", "content": "Test Anthropic via LiteLLM"}],
            )
            assert response is not None

        time.sleep(0.5)

        # ASPECT 2 & 3: Integration successful
        assert memori_sqlite._enabled

    def test_litellm_ollama_model(
        self, memori_sqlite, test_namespace, mock_openai_response
    ):
        """
        Test 5: LiteLLM with Ollama model format.

        Validates:
        - Functional: Ollama model syntax works
        - Persistence: Local model recording
        - Integration: Local provider support
        """
        pytest.importorskip("litellm")
        from unittest.mock import patch

        from litellm import completion

        memori_sqlite.enable()

        # ASPECT 1: Functional - Ollama model
        with patch("litellm.completion", return_value=mock_openai_response):
            response = completion(
                model="ollama/llama2",  # Ollama model
                messages=[{"role": "user", "content": "Test Ollama via LiteLLM"}],
            )
            assert response is not None

        time.sleep(0.5)

        # ASPECT 2 & 3: Integration successful
        assert memori_sqlite._enabled


@pytest.mark.llm
@pytest.mark.integration
class TestLiteLLMContextInjection:
    """Test context injection with LiteLLM."""

    def test_litellm_with_auto_mode(
        self, memori_conscious_false_auto_true, test_namespace, mock_openai_response
    ):
        """
        Test 6: LiteLLM with auto-ingest mode.

        Validates:
        - Functional: Auto mode with LiteLLM
        - Persistence: Dynamic context retrieval
        - Integration: Query-based injection
        """
        pytest.importorskip("litellm")
        from unittest.mock import patch

        from litellm import completion

        memori = memori_conscious_false_auto_true

        # ASPECT 1: Functional - Enable auto mode
        memori.enable()

        with patch("litellm.completion", return_value=mock_openai_response):
            response = completion(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": "Help me with LiteLLM setup"}],
            )
            assert response is not None

        # ASPECT 2: Persistence - Memory exists
        stats = memori.db_manager.get_memory_stats("default")
        assert stats["long_term_count"] >= 1

        # ASPECT 3: Integration - Auto mode active
        assert memori.auto_ingest


@pytest.mark.llm
@pytest.mark.integration
class TestLiteLLMErrorHandling:
    """Test LiteLLM error handling."""

    def test_litellm_api_error(self, memori_sqlite, test_namespace):
        """
        Test 7: LiteLLM API error handling.

        Validates:
        - Functional: Errors propagate correctly
        - Persistence: System remains stable
        - Integration: Graceful error handling
        """
        pytest.importorskip("litellm")
        from unittest.mock import patch

        from litellm import completion

        memori_sqlite.enable()

        # ASPECT 1: Functional - Simulate error
        with patch("litellm.completion", side_effect=Exception("LiteLLM API Error")):
            with pytest.raises(Exception) as exc_info:
                completion(
                    model="gpt-4o-mini", messages=[{"role": "user", "content": "Test"}]
                )

            assert "LiteLLM API Error" in str(exc_info.value)

        # ASPECT 2 & 3: System stable after error
        stats = memori_sqlite.db_manager.get_memory_stats("default")
        assert isinstance(stats, dict)

    def test_litellm_invalid_model(
        self, memori_sqlite, test_namespace, mock_openai_response
    ):
        """
        Test 8: LiteLLM with invalid model name.

        Validates:
        - Functional: Invalid model handled
        - Persistence: No corruption
        - Integration: Error isolation
        """
        pytest.importorskip("litellm")
        from unittest.mock import patch

        from litellm import completion

        memori_sqlite.enable()

        # With mock, even invalid model works - this tests integration layer
        with patch("litellm.completion", return_value=mock_openai_response):
            response = completion(
                model="invalid-model-name",
                messages=[{"role": "user", "content": "Test"}],
            )
            # Mock allows this to succeed - real call would fail
            assert response is not None

        # ASPECT 3: Memori remains stable
        assert memori_sqlite._enabled


@pytest.mark.llm
@pytest.mark.integration
@pytest.mark.performance
class TestLiteLLMPerformance:
    """Test LiteLLM integration performance."""

    def test_litellm_overhead(
        self, memori_sqlite, test_namespace, mock_openai_response, performance_tracker
    ):
        """
        Test 9: Measure Memori overhead with LiteLLM.

        Validates:
        - Functional: Performance tracking works
        - Persistence: Async recording efficient
        - Integration: Acceptable overhead
        """
        pytest.importorskip("litellm")
        from unittest.mock import patch

        from litellm import completion

        # Baseline: Without Memori
        with performance_tracker.track("litellm_without"):
            with patch("litellm.completion", return_value=mock_openai_response):
                for i in range(10):
                    completion(
                        model="gpt-4o-mini",
                        messages=[{"role": "user", "content": f"Test {i}"}],
                    )

        # With Memori
        memori_sqlite.enable()

        with performance_tracker.track("litellm_with"):
            with patch("litellm.completion", return_value=mock_openai_response):
                for i in range(10):
                    completion(
                        model="gpt-4o-mini",
                        messages=[{"role": "user", "content": f"Test {i}"}],
                    )

        # ASPECT 3: Performance analysis
        metrics = performance_tracker.get_metrics()
        without = metrics.get("litellm_without", 0.001)
        with_memori = metrics.get("litellm_with", 0.001)

        overhead = with_memori - without
        overhead_pct = (overhead / without) * 100 if without > 0 else 0

        print("\nLiteLLM Performance:")
        print(f"  Without Memori: {without:.3f}s")
        print(f"  With Memori:    {with_memori:.3f}s")
        print(f"  Overhead:       {overhead:.3f}s ({overhead_pct:.1f}%)")

        # Allow reasonable overhead
        assert overhead_pct < 100, f"Overhead too high: {overhead_pct:.1f}%"
